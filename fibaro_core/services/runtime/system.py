"""System services with explicit process dependencies."""

from api_types import ModuleCardPayload, ModuleTablePayload
from build_log import APP_BUILD
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from energy_helpers import parse_elvia_json_payload
from fastapi import Request
from fibaro_core.models import (
    AccessKey,
    AccessLog,
    AlarmEvent,
    AuthSession,
    DoorEvent,
    EnergyFibaroSample,
    EnergyImportRun,
    ImportJobRun,
    ImportJobStatus,
    NotificationOutbox,
    OperationalIncidentReview,
    OutdoorLightSample,
    ParkingSession,
    ParkingVehicle,
    RoborockSyncRun,
    Sun2Bed,
    Sun2FinanceSettlement,
    Sun2ImportRun,
    Sun2Member,
    Sun2ProductSale,
    Sun2SessionImportRun,
    Sun2TanningSession,
    Sun2TanningSessionImage,
    VentilationSample,
    YrForecastSample,
)
from fibaro_core.services.presentation import api_card, api_chart, api_table, format_short_number
from fibaro_core.services.settlements.reconciliation import revenue_settlement_reconciliation_rows
from import_jobs import IMPORT_JOB_DEFINITIONS, IMPORT_JOB_NUMBER_BY_NAME
from incident_domain import (
    apply_incident_reviews,
    backup_control,
    incident_summary,
    operational_incident,
    parse_status_text,
)
from operational_retention import execute_retention_statements
from parking_vehicle_helpers import CAR_INFO_IMPORT_JOB_BY_COUNTRY
from pathlib import Path
from reconciliation_domain import (
    evaluate_reconciliation,
    reconciliation_group,
    reconciliation_summary,
    state_reconciliation,
)
from sqlalchemy import Date, and_, cast, delete, func, or_, select
from system_inventory import system_component_summary, system_web_interface_rows
from time_formatting import api_local_iso, local_now_naive, normalize_local_naive, utc_naive_to_local_naive
from typing import Any, Callable, Dict, Mapping, Optional
from urllib.parse import quote
from value_parsing import float_or_zero, int_or_zero
import asyncio
import json
import math


@dataclass
class Dependencies:
    ADMIN_TASK_SEVERITY_SORT: Any
    FULL_BACKUP_STATUS_PATH: Any
    NIGHTLY_BACKUP_STATUS_PATH: Any
    NTFY_ACCESS_COOLDOWN_MINUTES: Any
    NTFY_ACCESS_TOPIC: Any
    OPERATIONAL_RETENTION_INITIAL_DELAY_SECONDS: Any
    OPERATIONAL_RETENTION_INTERVAL_HOURS: Any
    OPERATIONAL_RETENTION_POLICY: Any
    OPERATIONAL_RETENTION_STATE: Any
    SUN2_SESSIONS_QUIET_END_HOUR: Any
    age_label: Callable[..., Any]
    api_data_quality_row: Callable[..., Any]
    async_session: Callable[..., Any]
    clear_summary_cache: Callable[..., Any]
    easypark_downloader_status: Callable[..., Any]
    easypark_next_run_at_from_status: Callable[..., Any]
    fallback_car_info_import_status: Callable[..., Any]
    get_parking_sun_link_state: Callable[..., Any]
    ingest_elvia_hours: Callable[..., Any]
    latest_energy_reconciliation_check: Callable[..., Any]
    logger: Any
    manual_energy_quickapp_report: Callable[..., Any]
    minutes_since: Callable[..., Any]
    notification_outbox_status: Callable[..., Any]
    ntfy_subscribe_url: Callable[..., Any]
    ntfy_topic_url: Callable[..., Any]
    sun2_sessions_active_minutes_since: Callable[..., Any]
    sunroom_door_alarm_payload: Callable[..., Any]
    vehicle_area_not_found_condition: Callable[..., Any]
    vehicle_blank_area_condition: Callable[..., Any]
    vehicle_blank_name_condition: Callable[..., Any]
    vehicle_missing_area_condition: Callable[..., Any]
    vehicle_missing_name_condition: Callable[..., Any]
    vehicle_name_not_found_condition: Callable[..., Any]


def create_service(dependencies: Dependencies):

    async def cleanup_operational_history_once(now_value: Optional[datetime] = None) -> dict[str, int]:
        OPERATIONAL_RETENTION_POLICY = dependencies.OPERATIONAL_RETENTION_POLICY
        async_session = dependencies.async_session
        now_value = now_value or datetime.now(timezone.utc).replace(tzinfo=None)
        cutoffs = OPERATIONAL_RETENTION_POLICY.cutoffs(now_value)
        statements = {
            "accessLogsSuccess": delete(AccessLog).where(
                AccessLog.success.is_(True),
                AccessLog.timestamp < cutoffs["access_success"],
            ),
            "accessLogsFailure": delete(AccessLog).where(
                AccessLog.success.is_not(True),
                AccessLog.timestamp < cutoffs["access_failure"],
            ),
            "importRunsSuccess": delete(ImportJobRun).where(
                ImportJobRun.ok.is_(True),
                ImportJobRun.finished_at < cutoffs["import_success"],
            ),
            "importRunsFailure": delete(ImportJobRun).where(
                ImportJobRun.ok.is_not(True),
                ImportJobRun.finished_at < cutoffs["import_failure"],
            ),
            "notificationsSent": delete(NotificationOutbox).where(
                NotificationOutbox.status == "sent",
                NotificationOutbox.sent_at < cutoffs["notification_sent"],
            ),
            "authSessions": delete(AuthSession).where(
                or_(
                    AuthSession.expires_at < cutoffs["auth_session"],
                    and_(AuthSession.revoked_at.isnot(None), AuthSession.revoked_at < cutoffs["auth_session"]),
                )
            ),
        }
        return await execute_retention_statements(async_session, statements)

    async def operational_retention_worker() -> None:
        OPERATIONAL_RETENTION_INITIAL_DELAY_SECONDS = dependencies.OPERATIONAL_RETENTION_INITIAL_DELAY_SECONDS
        OPERATIONAL_RETENTION_INTERVAL_HOURS = dependencies.OPERATIONAL_RETENTION_INTERVAL_HOURS
        OPERATIONAL_RETENTION_STATE = dependencies.OPERATIONAL_RETENTION_STATE
        logger = dependencies.logger
        await asyncio.sleep(OPERATIONAL_RETENTION_INITIAL_DELAY_SECONDS)
        while True:
            run_at = datetime.now(timezone.utc).replace(tzinfo=None)
            OPERATIONAL_RETENTION_STATE["status"] = "running"
            OPERATIONAL_RETENTION_STATE["lastRunAt"] = api_local_iso(run_at)
            try:
                deleted = await cleanup_operational_history_once(run_at)
                OPERATIONAL_RETENTION_STATE.update(
                    status="ok",
                    lastSuccessAt=api_local_iso(datetime.now(timezone.utc).replace(tzinfo=None)),
                    lastError=None,
                    deleted=deleted,
                )
                if any(deleted.values()):
                    logger.info("Operational retention removed rows: %s", deleted)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                OPERATIONAL_RETENTION_STATE.update(status="error", lastError=str(exc)[:1000])
                logger.exception("Operational retention failed")
            await asyncio.sleep(OPERATIONAL_RETENTION_INTERVAL_HOURS * 3600)

    def import_job_definition(job_name: str) -> Dict[str, Any]:
        fallback = {
            "title": job_name.replace("_", " ").title(),
            "category": "Annet",
            "source": None,
            "expected_interval_minutes": None,
            "warning_after_minutes": None,
            "description": "",
            "data_flow": "",
            "dependencies": [],
        }
        return {**fallback, **IMPORT_JOB_DEFINITIONS.get(job_name, {})}

    def import_job_interval_text(minutes: Optional[int]) -> Optional[str]:
        if minutes is None:
            return None
        if minutes < 60:
            return f"{minutes} min"
        if minutes % (24 * 60) == 0:
            days = minutes // (24 * 60)
            return "1 dag" if days == 1 else f"{days} dager"
        if minutes % 60 == 0:
            hours = minutes // 60
            return "1 time" if hours == 1 else f"{hours} timer"
        hours = minutes // 60
        rest = minutes % 60
        return f"{hours} t {rest} min"

    def import_job_schedule_text(
        job_name: str,
        definition: Dict[str, Any],
        easypark_status: Optional[Dict[str, Any]] = None,
    ) -> str:
        if job_name == "easypark_parking_import" and isinstance(easypark_status, dict):
            schedule = easypark_status.get("schedule") if isinstance(easypark_status.get("schedule"), dict) else {}
            run_times = schedule.get("run_times")
            if isinstance(run_times, list) and run_times:
                times = ", ".join(str(item) for item in run_times)
                return f"Fast plan fra EasyPark-downloader: {times}. Neste kjøring beregnes fra downloaderens /status."

        if job_name == "sun2_sessions_import":
            return (
                "Kjøres ved lukking av solromdør, tidligst ett minutt etter hendelsen og med minst fem minutter "
                "mellom oppslag. Et 30-minutters sikkerhetsnett kjører i åpningstiden. Varselgrense: 60 min."
            )

        expected_minutes = definition.get("expected_interval_minutes")
        warning_minutes = definition.get("warning_after_minutes")
        expected_text = import_job_interval_text(expected_minutes)
        warning_text = import_job_interval_text(warning_minutes)
        if expected_text and warning_text:
            return f"Forventet ny vellykket oppdatering minst hver {expected_text}. Varselgrense: {warning_text}."
        if expected_text:
            return f"Forventet ny vellykket oppdatering minst hver {expected_text}."
        return "Ingen fast intervallovervåking. Datakilden kjøres manuelt, ved behov eller som del av en separat bakgrunnsjobb."

    def import_job_status_from_age(stamp: Optional[datetime], expected_minutes: Optional[int], warning_minutes: Optional[int]) -> tuple[str, str]:
        minutes_since = dependencies.minutes_since
        age_minutes = minutes_since(stamp)
        return import_job_status_from_minutes(age_minutes, expected_minutes, warning_minutes)

    def import_job_status_from_minutes(age_minutes: Optional[int], expected_minutes: Optional[int], warning_minutes: Optional[int]) -> tuple[str, str]:
        if age_minutes is None:
            return "bad", "Mangler"
        if expected_minutes is None:
            return "ok", "OK"
        warning_minutes = warning_minutes or expected_minutes * 2
        if age_minutes <= expected_minutes:
            return "ok", "OK"
        if age_minutes <= warning_minutes:
            return "warn", "Treg"
        return "bad", "Gammel"

    def import_job_age(row: Optional[ImportJobStatus]) -> str:
        age_label = dependencies.age_label
        minutes_since = dependencies.minutes_since
        stamp = row.last_success_at if row else None
        return age_label(minutes_since(stamp))

    def import_job_updated_ago(row: Optional[ImportJobStatus]) -> str:
        age_label = dependencies.age_label
        minutes_since = dependencies.minutes_since
        stamp = row.last_success_at if row else None
        minutes = minutes_since(stamp)
        if minutes is None:
            return "Ingen importstatus"
        if minutes < 1:
            return "Oppdatert under 1 min siden"
        return f"Oppdatert {age_label(minutes)}"

    async def record_import_job(
        session,
        job_name: str,
        *,
        ok: bool = True,
        title: Optional[str] = None,
        category: Optional[str] = None,
        source: Optional[str] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        next_expected_at: Optional[datetime] = None,
        expected_interval_minutes: Optional[int] = None,
        warning_after_minutes: Optional[int] = None,
        records_imported: Optional[int] = None,
        records_total: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        message: Optional[str] = None,
        raw: Optional[Dict[str, Any]] = None,
    ) -> ImportJobStatus:
        definition = import_job_definition(job_name)
        finished_at = finished_at or local_now_naive()
        title = title or definition["title"]
        category = category or definition["category"]
        source = source or definition.get("source")
        expected_interval_minutes = expected_interval_minutes if expected_interval_minutes is not None else definition.get("expected_interval_minutes")
        warning_after_minutes = warning_after_minutes if warning_after_minutes is not None else definition.get("warning_after_minutes")
        if next_expected_at is None and ok and expected_interval_minutes:
            next_expected_at = finished_at + timedelta(minutes=expected_interval_minutes)
        status = "ok" if ok else "bad"
        status_text = "OK" if ok else "Feil"

        session.add(
            ImportJobRun(
                job_name=job_name,
                title=title,
                category=category,
                source=source,
                started_at=started_at,
                finished_at=finished_at,
                ok=ok,
                status=status,
                records_imported=records_imported,
                records_total=records_total,
                duration_seconds=duration_seconds,
                message=message,
                raw=raw or {},
            )
        )

        existing = (
            await session.execute(select(ImportJobStatus).where(ImportJobStatus.job_name == job_name))
        ).scalars().first()
        if not existing:
            existing = ImportJobStatus(job_name=job_name, title=title, category=category)
            session.add(existing)
        existing.title = title
        existing.category = category
        existing.source = source
        existing.status = status
        existing.status_text = status_text
        existing.last_started_at = started_at or existing.last_started_at
        existing.last_run_at = finished_at
        if ok:
            existing.last_success_at = finished_at
        else:
            existing.last_failed_at = finished_at
        existing.next_expected_at = next_expected_at
        existing.expected_interval_minutes = expected_interval_minutes
        existing.warning_after_minutes = warning_after_minutes
        existing.records_imported = records_imported
        existing.records_total = records_total
        existing.duration_seconds = duration_seconds
        existing.message = message
        existing.raw = raw or {}
        return existing

    async def mark_import_job_running(
        session,
        job_name: str,
        *,
        message: Optional[str] = None,
        source: Optional[str] = None,
        raw: Optional[Dict[str, Any]] = None,
    ) -> ImportJobStatus:
        definition = import_job_definition(job_name)
        started_at = local_now_naive()
        existing = (
            await session.execute(select(ImportJobStatus).where(ImportJobStatus.job_name == job_name))
        ).scalars().first()
        if not existing:
            existing = ImportJobStatus(job_name=job_name, title=definition["title"], category=definition["category"])
            session.add(existing)
        existing.title = definition["title"]
        existing.category = definition["category"]
        existing.source = source or definition.get("source")
        existing.status = "running"
        existing.status_text = "Kjører"
        existing.last_started_at = started_at
        existing.last_run_at = started_at
        existing.message = message or "Import kjører"
        existing.raw = raw or {}
        return existing

    async def fallback_import_job_status(session, job_name: str) -> Dict[str, Any]:
        fallback_car_info_import_status = dependencies.fallback_car_info_import_status
        if job_name in CAR_INFO_IMPORT_JOB_BY_COUNTRY.values():
            return await fallback_car_info_import_status(session, job_name)
        if job_name == "hc3_light_5min":
            row = (await session.execute(select(OutdoorLightSample).order_by(OutdoorLightSample.timestamp.desc()).limit(1))).scalars().first()
            return {"last_success_at": row.timestamp if row else None, "message": "Sist funnet i luxloggen" if row else ""}
        if job_name == "hc3_ventilation_5min":
            row = (await session.execute(select(VentilationSample).order_by(VentilationSample.timestamp.desc()).limit(1))).scalars().first()
            return {"last_success_at": row.timestamp if row else None, "message": "Sist funnet i temploggen" if row else ""}
        if job_name == "yr_weather_refresh":
            row = (await session.execute(select(YrForecastSample).order_by(YrForecastSample.timestamp.desc()).limit(1))).scalars().first()
            return {"last_success_at": utc_naive_to_local_naive(row.timestamp) if row else None, "message": row.weather_text if row else ""}
        if job_name == "hc3_energy_1min":
            row = (await session.execute(select(EnergyFibaroSample).order_by(EnergyFibaroSample.bucket_start.desc()).limit(1))).scalars().first()
            return {
                "last_success_at": row.bucket_start if row else None,
                "message": f"Inntak {format_short_number(row.inntak_w)} W" if row and row.inntak_w is not None else "Sist funnet i energiloggen" if row else "",
            }
        if job_name == "hc3_door_events":
            row = (await session.execute(select(DoorEvent).order_by(DoorEvent.timestamp.desc()).limit(1))).scalars().first()
            return {
                "last_success_at": row.timestamp if row else None,
                "message": f"{row.device_name or row.device_key or row.device_id}: {row.action}" if row else "",
            }
        if job_name == "roborock_sync":
            row = (await session.execute(select(RoborockSyncRun).order_by(RoborockSyncRun.timestamp.desc()).limit(1))).scalars().first()
            return {"last_success_at": row.timestamp if row and row.ok is not False else None, "last_failed_at": row.timestamp if row and row.ok is False else None, "message": row.message if row else "", "records_total": row.robots_count if row else None}
        if job_name == "sun2_room_daily_import":
            row = (await session.execute(select(Sun2ImportRun).order_by(Sun2ImportRun.timestamp.desc()).limit(1))).scalars().first()
            return {"last_success_at": row.timestamp if row and row.ok is not False else None, "last_failed_at": row.timestamp if row and row.ok is False else None, "message": row.message if row else "", "records_total": row.rows_count if row else None}
        if job_name == "sun2_sessions_import":
            row = (await session.execute(select(Sun2SessionImportRun).order_by(Sun2SessionImportRun.timestamp.desc()).limit(1))).scalars().first()
            return {"last_success_at": row.timestamp if row and row.ok is not False else None, "last_failed_at": row.timestamp if row and row.ok is False else None, "message": row.message if row else "", "records_total": row.rows_count if row else None}
        if job_name == "sun2_beds_import":
            row = (await session.execute(select(Sun2Bed).order_by(Sun2Bed.imported_at.desc()).limit(1))).scalars().first()
            count = (await session.execute(select(func.count()).select_from(Sun2Bed))).scalar_one()
            return {"last_success_at": row.imported_at if row else None, "message": "Sist funnet i senger-tabellen" if row else "", "records_total": count}
        if job_name == "sun2_members_import":
            row = (await session.execute(select(Sun2Member).order_by(Sun2Member.imported_at.desc()).limit(1))).scalars().first()
            count = (await session.execute(select(func.count()).select_from(Sun2Member))).scalar_one()
            return {"last_success_at": row.imported_at if row else None, "message": "Sist funnet i medlemstabellen" if row else "", "records_total": count}
        if job_name in {"sun2_product_sales_daily_import", "sun2_product_sales_monthly_import"}:
            monthly = job_name == "sun2_product_sales_monthly_import"
            query = select(Sun2ProductSale)
            if monthly:
                query = query.where(Sun2ProductSale.period_start != Sun2ProductSale.period_end)
            else:
                query = query.where(Sun2ProductSale.period_start == Sun2ProductSale.period_end)
            row = (await session.execute(query.order_by(Sun2ProductSale.imported_at.desc()).limit(1))).scalars().first()
            if not row:
                return {"message": "Ingen produktsalg importert ennå"}
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(Sun2ProductSale)
                    .where(Sun2ProductSale.source_file == row.source_file)
                )
            ).scalar_one()
            return {
                "last_success_at": row.imported_at,
                "message": f"Sist funnet i {row.source_file}",
                "records_total": count,
            }
        if job_name == "sun2_finance_settlement_monthly_import":
            row = (
                await session.execute(
                    select(Sun2FinanceSettlement).order_by(Sun2FinanceSettlement.imported_at.desc()).limit(1)
                )
            ).scalars().first()
            if not row:
                return {"message": "Ingen Sun2 finansoppgjør importert ennå"}
            return {
                "last_success_at": row.imported_at,
                "message": f"Sist funnet i {row.payout_label or row.source_file or row.source_payout_id}",
                "records_total": 1,
            }
        if job_name == "elvia_monthly_import":
            row = (await session.execute(select(EnergyImportRun).order_by(EnergyImportRun.timestamp.desc()).limit(1))).scalars().first()
            return {"last_success_at": row.timestamp if row and row.ok is not False else None, "last_failed_at": row.timestamp if row and row.ok is False else None, "message": row.message if row else "", "records_total": row.hours_count if row else None}
        return {}

    async def import_status_rows(session) -> list[Dict[str, Any]]:
        SUN2_SESSIONS_QUIET_END_HOUR = dependencies.SUN2_SESSIONS_QUIET_END_HOUR
        age_label = dependencies.age_label
        easypark_downloader_status = dependencies.easypark_downloader_status
        easypark_next_run_at_from_status = dependencies.easypark_next_run_at_from_status
        minutes_since = dependencies.minutes_since
        sun2_sessions_active_minutes_since = dependencies.sun2_sessions_active_minutes_since
        existing = {
            row.job_name: row
            for row in (
                await session.execute(select(ImportJobStatus))
            ).scalars().all()
        }
        easypark_status = easypark_downloader_status()
        easypark_next_run_at = easypark_next_run_at_from_status(easypark_status)
        rows = []
        for job_name, definition in IMPORT_JOB_DEFINITIONS.items():
            row = existing.get(job_name)
            fallback = {} if row else await fallback_import_job_status(session, job_name)
            stamp = row.last_success_at if row else fallback.get("last_success_at")
            last_failed_at = row.last_failed_at if row else fallback.get("last_failed_at")
            expected_minutes = definition.get("expected_interval_minutes")
            warning_minutes = definition.get("warning_after_minutes")
            next_expected_at = row.next_expected_at if row else None
            if expected_minutes is None:
                next_expected_at = None
            if stamp and expected_minutes:
                calculated_next = stamp + timedelta(minutes=expected_minutes)
                if not next_expected_at or abs((next_expected_at - calculated_next).total_seconds()) > 60:
                    next_expected_at = calculated_next
            if job_name == "sun2_sessions_import" and expected_minutes:
                now_for_sun2 = local_now_naive()
                live_start_today = datetime.combine(now_for_sun2.date(), time(hour=SUN2_SESSIONS_QUIET_END_HOUR))
                if now_for_sun2 < live_start_today:
                    next_expected_at = live_start_today
                elif stamp and stamp < live_start_today:
                    next_expected_at = live_start_today + timedelta(minutes=expected_minutes)
            if job_name == "easypark_parking_import" and easypark_next_run_at:
                next_expected_at = easypark_next_run_at
            if row and row.status == "running":
                status, status_text = "running", "Kjører"
            elif job_name == "sun2_sessions_import":
                active_age_minutes = sun2_sessions_active_minutes_since(stamp)
                status, status_text = import_job_status_from_minutes(
                    active_age_minutes,
                    expected_minutes,
                    warning_minutes,
                )
            else:
                status, status_text = import_job_status_from_age(
                    stamp,
                    expected_minutes,
                    warning_minutes,
                )
            if row and row.status != "running" and last_failed_at and (not stamp or last_failed_at > stamp):
                status, status_text = "bad", "Feil"
            rows.append(
                {
                    "source_no": IMPORT_JOB_NUMBER_BY_NAME.get(job_name),
                    "job_name": job_name,
                    "title": row.title if row else definition["title"],
                    "category": row.category if row else definition["category"],
                    "source": row.source if row and row.source else definition.get("source"),
                    "description": definition.get("description", ""),
                    "data_flow": definition.get("data_flow") or definition.get("description", ""),
                    "dependencies": definition.get("dependencies", []),
                    "schedule_text": import_job_schedule_text(job_name, definition, easypark_status),
                    "expected_interval_minutes": expected_minutes,
                    "warning_after_minutes": warning_minutes,
                    "status": status,
                    "status_text": status_text,
                    "age": age_label(sun2_sessions_active_minutes_since(stamp)) if job_name == "sun2_sessions_import" else (import_job_age(row) if row else age_label(minutes_since(stamp))),
                    "last_success_at": stamp,
                    "success_time_basis": "import_log" if row else "stored_data" if stamp else "unknown",
                    "last_run_at": row.last_run_at if row else stamp,
                    "last_failed_at": last_failed_at,
                    "next_expected_at": next_expected_at,
                    "next_expected_kind": "scheduled" if job_name == "easypark_parking_import" and easypark_next_run_at else "freshness_deadline" if next_expected_at else "none",
                    "records_imported": row.records_imported if row else None,
                    "records_total": row.records_total if row else fallback.get("records_total"),
                    "duration_seconds": row.duration_seconds if row else None,
                    "message": row.message if row else fallback.get("message", ""),
                }
            )
        return rows

    async def run_elvia_import_background(content: bytes, filename: str):
        async_session = dependencies.async_session
        clear_summary_cache = dependencies.clear_summary_cache
        ingest_elvia_hours = dependencies.ingest_elvia_hours
        logger = dependencies.logger
        started_at = local_now_naive()
        batch_time = datetime.utcnow()
        try:
            parsed = parse_elvia_json_payload(content, filename)
            if not parsed["rows"]:
                raise ValueError("Filen inneholder ingen timeverdier som kan importeres.")
            async with async_session() as session:
                counts = await ingest_elvia_hours(session, parsed, batch_time)
                message = (
                    f"{counts['inserted']} nye, {counts['updated']} oppdatert, "
                    f"{counts['skipped']} uendret for måler {parsed['meter_id']}."
                )
                session.add(
                    EnergyImportRun(
                        timestamp=batch_time,
                        meter_id=parsed["meter_id"],
                        source="elvia",
                        ok=True,
                        source_file=filename,
                        period_first=parsed["first_at"],
                        period_last=parsed["last_at"],
                        days_count=parsed["days_count"],
                        hours_count=parsed["hours_count"],
                        inserted_count=counts["inserted"],
                        updated_count=counts["updated"],
                        skipped_count=counts["skipped"],
                        total_kwh=parsed["total_kwh"],
                        estimated_hours_count=parsed["estimated_hours_count"],
                        message=message,
                        raw={"partial_months": parsed["partial_months"]},
                    )
                )
                await record_import_job(
                    session,
                    "elvia_monthly_import",
                    source="elvia",
                    started_at=started_at,
                    finished_at=local_now_naive(),
                    records_imported=counts["inserted"] + counts["updated"],
                    records_total=parsed["hours_count"],
                    duration_seconds=(local_now_naive() - started_at).total_seconds(),
                    message=message,
                    raw={"source_file": filename, "partial_months": parsed["partial_months"], "counts": counts},
                )
                await session.commit()
            clear_summary_cache("energy")
        except (json.JSONDecodeError, UnicodeDecodeError):
            error = "Filen kunne ikke leses som gyldig JSON."
            async with async_session() as session:
                session.add(EnergyImportRun(timestamp=batch_time, source="elvia", ok=False, source_file=filename, message=error))
                await record_import_job(
                    session,
                    "elvia_monthly_import",
                    ok=False,
                    source="elvia",
                    started_at=started_at,
                    finished_at=local_now_naive(),
                    duration_seconds=(local_now_naive() - started_at).total_seconds(),
                    message=error,
                    raw={"source_file": filename},
                )
                await session.commit()
        except Exception as exc:
            logger.exception("Elvia-import feilet for %s", filename)
            error = str(exc)
            async with async_session() as session:
                session.add(EnergyImportRun(timestamp=batch_time, source="elvia", ok=False, source_file=filename, message=error))
                await record_import_job(
                    session,
                    "elvia_monthly_import",
                    ok=False,
                    source="elvia",
                    started_at=started_at,
                    finished_at=local_now_naive(),
                    duration_seconds=(local_now_naive() - started_at).total_seconds(),
                    message=error,
                    raw={"source_file": filename},
                )
                await session.commit()

    def admin_manual_payload() -> Dict[str, Any]:
        manual_energy_quickapp_report = dependencies.manual_energy_quickapp_report
        economy_areas = [
            {
                "title": "Omsetning",
                "marker": "OM",
                "tone": "revenue",
                "path": "/omsetning/",
                "purpose": "Samler økonomien på tvers av parkering og soling, med sammenligninger på samme datagrunnlag og tidspunkt.",
                "canSee": [
                    "omsetning hittil i dag, uke, måned og år",
                    "sammenligning mot relevante referanseperioder",
                    "toppdager, toppuker og toppmåneder",
                    "månedsoversikt og årssammenligning",
                ],
                "canDo": ["følge utvikling gjennom dagen", "sammenligne perioder", "gå fra total til parkering eller soling"],
            },
            {
                "title": "Parkering",
                "marker": "P",
                "tone": "parking",
                "path": "/parkering/parkeringer",
                "purpose": "Viser EasyPark/Flowbird-grunnlaget, kjøretøy, betaling, områder og historikk per bil.",
                "canSee": [
                    "dagens parkeringer, pågående og avsluttede",
                    "kjøretøyinfo, eier, område, bilmerke, type og farge",
                    "UniFi Protect-lenker for start og slutt",
                    "oppgjør, prognose, årsutvikling, ukesnitt og tidspunktfordeling",
                ],
                "canDo": ["oppdatere EasyPark", "søke etter bil/eier", "kontrollere område og biloppslag", "åpne bilhistorikk"],
            },
            {
                "title": "Soling",
                "marker": "S",
                "tone": "sun",
                "path": "/soling/dagslinje",
                "purpose": "Viser SUN2-data, enkelttimer, produkter, senger, medlemmer, bilder og oppgjør.",
                "canSee": [
                    "dagslinje per rom og seng",
                    "enkeltimer med SUN2-ID, rom, bilde og betaling",
                    "produktsalg og oppgjørskontroll",
                    "årssammenligning, prognoser og statistikk",
                    "bildearkiv fra Axis knyttet til soltimer",
                ],
                "canDo": ["bla i bilder", "sette hovedbilde", "kontrollere romkobling", "sjekke produkter og medlemmer"],
            },
            {
                "title": "Koble",
                "marker": "K",
                "tone": "link",
                "path": "/koble/",
                "purpose": "Finner sannsynlige koblinger mellom bilnummer og SUN2-ID når samme mønster skjer flere ganger.",
                "canSee": [
                    "kandidater der samme bil og SUN2-ID matcher minst to parkeringer",
                    "hvor mange parkeringer som har soltreff",
                    "hvilke biler som peker mot samme SUN2-ID",
                    "jobbstatus og parametere for koblingsmotoren",
                ],
                "canDo": ["bekrefte eller avvise koblinger", "justere parametere", "starte jobben på nytt fra nyeste parkering"],
            },
        ]

        operations_areas = [
            {
                "title": "Energi",
                "marker": "EL",
                "tone": "energy",
                "path": "/energi/",
                "purpose": "Samler sanntidseffekt fra HC3, kurser, laster, Elvia-kontroll og solsengforbruk.",
                "canSee": ["inntak, varmepumper, belysning, massasje, annet og diff", "kurser og målere", "Elvia mot HC3", "forbruk per seng"],
                "canDo": ["kontrollere strømavvik", "importere Elvia", "beregne forbruk per seng", "vedlikeholde laster og kursinfo"],
            },
            {
                "title": "Bygg",
                "marker": "DR",
                "tone": "building",
                "path": "/bygg/",
                "purpose": "Samler ventilasjon, klima og lys i én fagapp.",
                "canSee": ["driftsstatus for ventilasjon og lys", "temperatur, fukt, vær og vifter", "lux og styringshendelser"],
                "canDo": ["åpne fagdetaljer", "kontrollere måleverdier", "endre godkjente innstillinger", "følge historikk"],
            },
            {
                "title": "Renhold",
                "marker": "R",
                "tone": "building",
                "path": "/renhold/",
                "purpose": "Samler robotstatus, planer, nattjobber, vann og renholdslogger.",
                "canSee": ["status for alle roboter", "planlagte og gjennomførte jobber", "batteri, vann, dokk og forbruksdeler"],
                "canDo": ["starte manuelle jobber", "kontrollere nattplan", "vedlikeholde profiler", "følge vannstatus"],
            },
            {
                "title": "Kontroll",
                "marker": "K",
                "tone": "admin",
                "path": "/kontroll/",
                "purpose": "Samler dører, solrom, alarmer og fysisk kontroll av pullerter og fasade.",
                "canSee": ["dør- og solromstatus", "alarmer og avvik", "pullert-, trapp- og fasadekontroll"],
                "canDo": ["åpne hendelser", "kontrollere bilder", "følge alarmhistorikk", "kvittere avvik"],
            },
            {
                "title": "Vedlikehold",
                "marker": "VD",
                "tone": "maintenance",
                "path": "/vedlikehold/",
                "purpose": "Logger besøk på Lilletorget og oppgavene som blir gjort under hvert besøk.",
                "canSee": ["besøk fra OwnTracks/Lilletorget", "oppgaver per besøk", "notater, tagger, oppfølging og status"],
                "canDo": ["redigere besøk", "skrive notat", "legge til eller endre oppgaver", "følge opp åpne punkter"],
            },
            {
                "title": "Operasjonssentral",
                "marker": "OP",
                "tone": "admin",
                "path": "/operasjon/",
                "purpose": "Samler hendelser, datakvalitet, kontroller og oppfølging som krever handling.",
                "canSee": ["prioritert arbeidskø", "kritiske hendelser", "operative kontroller", "behandlet historikk"],
                "canDo": ["kvittere og kommentere hendelser", "finne datakvalitetsfeil", "søke på tvers av løsningen"],
            },
            {
                "title": "Eiendeler og rapporter",
                "marker": "ER",
                "tone": "admin",
                "path": "/eiendeler/",
                "purpose": "Gir teknisk eiendelsregister og samlet inngang til operative og økonomiske rapporter.",
                "canSee": ["utstyr, plassering, modell og service", "garanti og vedlikeholdsintervall", "rapportkatalog med direkte faglenker"],
                "canDo": ["vedlikeholde eiendeler", "synkronisere kjente enheter", "åpne rapporter i riktig fagapp"],
            },
        ]

        system_areas = [
            {
                "title": "Manual",
                "marker": "M",
                "tone": "manual",
                "path": "/system/manual",
                "purpose": "Egen dokumentasjonsdel med forklaring av hovedområder, datakilder, rutiner og feilsøking.",
                "canSee": ["kapitteldelt manual", "menyforklaringer", "daglige rutiner", "datagrunnlag og feilsøking"],
                "canDo": ["slå opp hvordan en side brukes", "finne riktig startpunkt", "følge kontrollrutiner"],
            },
            {
                "title": "System",
                "marker": "SY",
                "tone": "admin",
                "path": "/system/",
                "purpose": "Drifts- og administrasjonsområde for datakilder, jobber, buildlogg, brukere, manual og systemkart.",
                "canSee": ["datakilder", "buildlogg", "systemkart", "brukere", "teknisk drift", "AI og verktøy"],
                "canDo": ["feilsøke tjenester", "kontrollere tilgang", "finne URL-er og health", "lese hva som er endret"],
            },
        ]

        return {
            "build": APP_BUILD,
            "title": "Lilletorget manual",
            "description": "Gjeldende bruker- og driftsmanual for Mantis-appene på app.lilletorget.net. Fibaro10 er kjerne/API.",
            "chapters": [
                {
                    "id": "hva-losningen-er",
                    "number": "01",
                    "title": "Hva løsningen er",
                    "paragraphs": [
                        "Den gjeldende brukerflaten er tretten Mantis-apper under https://app.lilletorget.net. Appene deler innlogging, design og navigasjonsprinsipper, men er delt etter fagområde.",
                        "Fibaro10-kjernen eier API, forretningsregler, database, jobber og integrasjoner. API-adapterne avgrenser tilgangen for hver Mantis-app og har ingen egne desktopflater.",
                    ],
                    "principles": [
                        {"marker": "DB", "title": "Database først", "text": "Appen viser normalt data fra egen database, ikke direkte fra tredjepart i øyeblikket."},
                        {"marker": "OK", "title": "Datakilder er fasit", "text": "Når tall virker feil, kontroller først om kilden faktisk har levert ferske data."},
                        {"marker": "SPOR", "title": "Alt skal kunne spores", "text": "Systemkart, buildlogg og oppgjør gjør det mulig å finne kilde, endring og kontrollgrunnlag."},
                    ],
                },
                {
                    "id": "daglig-bruk",
                    "number": "02",
                    "title": "Slik bruker du den daglig",
                    "startLinks": [
                        {"label": "Omsetning", "path": "/omsetning/", "note": "Dagens økonomiske status og relevante sammenligninger."},
                        {"label": "Operasjonssentral", "path": "/operasjon/", "note": "Hendelser og avvik som krever oppfølging."},
                        {"label": "Datakilder", "path": "/system/datakilder", "note": "Første stopp når tall mangler eller virker gamle."},
                        {"label": "Systemkart", "path": "/system/systemkart", "note": "Apper, tjenester, URL-er og avhengigheter."},
                        {"label": "Buildlogg", "path": "/system/build", "note": "Hva som er endret, hvorfor og hvordan det ble testet."},
                    ],
                    "flow": [
                        {"title": "Start med Omsetning", "text": "Se om parkering, soling og totalsum ligger normalt an."},
                        {"title": "Gå til fagområdet", "text": "Åpne parkering, soling, energi, lys, ventilasjon eller dører for forklaringen."},
                        {"title": "Sjekk datakilden", "text": "Hvis noe ikke stemmer, kontroller alder og melding før du tolker tallene."},
                        {"title": "Bruk buildlogg", "text": "Hvis noe oppfører seg annerledes enn før, se hvilken build som endret det."},
                    ],
                },
                {
                    "id": "menyvalg",
                    "number": "03",
                    "title": "Menyvalg",
                    "menuGroups": [
                        {"title": "Omsetning", "path": "/omsetning/", "text": "Dashboard, oversikt, måned, år og periodesammenligning."},
                        {"title": "Parkering", "path": "/parkering/", "text": "Parkeringer, kjøretøy, oppgjør, analyse, prognose og datakvalitet."},
                        {"title": "Soling", "path": "/soling/", "text": "Soltimer, bilder, dagslinje, senger, medlemmer, produkter, oppgjør og analyse."},
                        {"title": "Koble", "path": "/koble/", "text": "Kandidater og kontroll av koblinger mellom bilnummer og SUN2-ID."},
                        {"title": "Bygg", "path": "/bygg/", "text": "Ventilasjon, klima, lys og styringshendelser."},
                        {"title": "Renhold", "path": "/renhold/", "text": "Roboter, planer, jobber, vann og renholdslogger."},
                        {"title": "Kontroll", "path": "/kontroll/", "text": "Dører, solrom, alarmer, pullerter og fysisk kontroll."},
                        {"title": "Energi", "path": "/energi/", "text": "Sanntidsstatus, Elvia, kurs/last, målere og solsengforbruk."},
                        {"title": "Vedlikehold", "path": "/vedlikehold/", "text": "Oppgaver, besøk, notater og redigering."},
                        {"title": "Operasjonssentral", "path": "/operasjon/", "text": "Arbeidskø, kritiske hendelser, datakvalitet, automatisering og søk."},
                        {"title": "Eiendeler", "path": "/eiendeler/", "text": "Teknisk register med plassering, modell, service og garanti."},
                        {"title": "Rapporter", "path": "/rapporter/", "text": "Samlet inngang til operative, økonomiske og tekniske rapporter."},
                        {"title": "System", "path": "/system/", "text": "Datakilder, jobber, brukere, buildlogg, varslinger, verktøy og manual."},
                    ],
                    "note": "Menyvalgene er organisert etter fagområde. Dashboard er status først, fagmenyene forklarer tallene, og Admin brukes til drift, kontroll og systemforståelse.",
                },
                {"id": "okonomi", "number": "04", "title": "Økonomi", "areas": economy_areas},
                {"id": "bygg-drift", "number": "05", "title": "Bygg og drift", "areas": operations_areas},
                {
                    "id": "system-underapper",
                    "number": "06",
                    "title": "System og underapper",
                    "areas": system_areas,
                    "subapps": [
                        {"title": "Varslinger", "text": "Alle ntfy-abonnementer finnes samlet under System -> Varslinger.", "path": "/system/varslinger"},
                        {"title": "Undersystemer", "text": "Alle klikkbare systemflater og interne tjenester finnes under System -> Undersystemer.", "path": "/system/undersystemer"},
                        {"title": "Mantis", "text": "Gjeldende brukerflate med tretten fagapper på app.lilletorget.net."},
                        {"title": "Fibaro10", "text": "FastAPI-kjerne, database, autentisering, forretningsregler og bakgrunnsjobber."},
                        {"title": "lilletorget_kiosk", "text": "Fast statusflate for robotrenhold på kiosk.lilletorget.net."},
                        {"title": "online_dashboard", "text": "Ekstern mobilvisning på online.lilletorget.net."},
                        {"title": "maintenance_mobile", "text": "Mobil vedlikeholdsapp på vedl.lilletorget.net."},
                        {"title": "alarm_mobile", "text": "Mobil alarm- og kontrollflate på alarm.lilletorget.net."},
                        {"title": "owntracks_service", "text": "Lokasjon, waypoints og sonebesøk på owntracks.lilletorget.net."},
                        {"title": "axis_camera_snapshots", "text": "Henter og rydder Axis-bilder til soltimer."},
                        {"title": "sun2_session_scraper", "text": "Henter SUN2 enkelttimer, produkter, senger og medlemmer."},
                        {"title": "easypark_downloader", "text": "Henter EasyPark-data og holder parkeringsgrunnlaget oppdatert."},
                        {"title": "parking_sun_linker", "text": "Bakgrunnsmotor for kobling mellom parkering og SUN2-ID."},
                        {"title": "roborock_logger / dreame_logger", "text": "Separate tjenester for robotstatus, telemetri, planer og vaskehistorikk."},
                    ],
                },
                {
                    "id": "datagrunnlag",
                    "number": "07",
                    "title": "Datagrunnlag",
                    "dataSources": [
                        {"title": "HC3", "text": "Poster energi, lys, ventilasjon og dørhendelser inn i Fibaro10."},
                        {"title": "EasyPark/Flowbird", "text": "Gir parkeringsgrunnlag, kilder, betalinger, tidspunkt og oppgjørskontroll."},
                        {"title": "SUN2", "text": "Gir soltimer, produkter, medlemmer, senger, rom og økonomigrunnlag."},
                        {"title": "Axis", "text": "Leverer snapshots som kobles til soltimer og bildearkiv."},
                        {"title": "UniFi Protect", "text": "Gir tidslenker, hendelser og bilder til parkering og fysisk kontroll."},
                        {"title": "Yr", "text": "Gir vær, temperatur, fukt, vind, skydekke og nedbør til analyse og styring."},
                        {"title": "Elvia", "text": "Manuell import som brukes som kontroll mot HC3-forbruk."},
                        {"title": "Roborock og Dreame", "text": "Logger roboter, telemetri, vannstatus, planer og vaskehistorikk."},
                        {"title": "OwnTracks", "text": "Egen tjeneste for lokasjon, waypoints og besøk på kjente steder."},
                        {"title": "Kjøretøyoppslag", "text": "SVV brukes først, deretter svenske og danske oppslag for aktuelle registreringsnumre."},
                        {"title": "Lokal visuell analyse", "text": "Faste utsnitt og lokal modell brukes som støtte ved kontroll av pullerter, fasade og trapp."},
                        {"title": "HC3 energioppsamlinger", "text": "Detaljert rapport over QuickApps, målte medlemmer og målere som ikke er direkte med.", "path": "/system/manual/hc3-energi"},
                    ],
                    "note": "Bruk System -> Datakilder for operativ status, System -> Undersystemer for webflater og System -> Systemkart for avhengigheter.",
                },
                {
                    "id": "hc3-energi",
                    "number": "08",
                    "title": "HC3 energioppsamlinger",
                    "energyQuickappReport": manual_energy_quickapp_report(),
                    "note": "Rapporten bygger på siste avleste HC3-inventar i outputs/hc3_inventory. Den skiller mellom reelle hull og underenheter som ikke skal summeres direkte.",
                },
                {
                    "id": "rutiner",
                    "number": "09",
                    "title": "Rutiner og kontroll",
                    "checklists": [
                        {"title": "Daglig økonomi", "path": "/omsetning/", "text": "Sjekk omsetning hittil i dag, referanseperioder og tidspunkt for siste parkerings- og soloppdatering."},
                        {"title": "Daglig parkering", "path": "/parkering/parkeringer", "text": "Sjekk dagens parkeringer, pågående parkeringer, nye kjøretøy, manglende område og om EasyPark er oppdatert."},
                        {"title": "Daglig soling", "path": "/soling/dagslinje", "text": "Sjekk dagslinje, enkelttimer, bilder og eventuelle rom som ikke passer med dør/strøm."},
                        {"title": "Drift gjennom dagen", "path": "/system/datakilder", "text": "Hvis noe virker feil, sjekk datakildene før du tolker tallene. Alder og sist OK er viktigere enn grafen når data er gamle."},
                        {"title": "Operative hendelser", "path": "/operasjon/", "text": "Følg opp åpne hendelser, kritiske avvik og datakvalitet i prioritert rekkefølge."},
                        {"title": "Ukentlig kontroll", "path": "/omsetning/sammenligning", "text": "Bruk periodesammenligning og årssammenligning for å se om ukeutviklingen er logisk på soling, parkering og samlet omsetning."},
                        {"title": "Månedlig kontroll", "path": "/omsetning/oversikt", "text": "Kontroller månedstall, parkering oppgjør, soling oppgjør, Elvia mot HC3 og eventuelle avvik før tall brukes videre."},
                        {"title": "Vedlikehold", "path": "/vedlikehold/besok", "text": "Kontroller at besøk fra OwnTracks er registrert, og at oppgaver ligger på riktig besøk."},
                        {"title": "Etter endringer", "path": "/system/build", "text": "Les buildlogg for siste endring. Den skal vise bestilling, berørte apper, tester og deploy."},
                    ],
                    "note": "Bruk denne delen som arbeidsgang: start bredt, gå til fagområdet, sjekk datakilde, og bruk buildlogg når atferd har endret seg.",
                },
                {
                    "id": "feilsoking",
                    "number": "10",
                    "title": "Feilsøking",
                    "troubleshooting": [
                        {"title": "Tall mangler eller virker gamle", "path": "/system/datakilder", "text": "Sjekk sist OK, alder, melding og neste planlagte jobb før du vurderer grafen."},
                        {"title": "Parkering stemmer ikke", "path": "/parkering/parkeringer", "text": "Sjekk EasyPark-import, dagens liste, kilde og oppgjør."},
                        {"title": "Soling stemmer ikke", "path": "/soling/enkeltimer", "text": "Sjekk enkelttimer, dagslinje, produkter, bildearkiv og SUN2-scraper."},
                        {"title": "Strøm avviker", "path": "/energi/elvia-kontroll", "text": "Sammenlign HC3 og Elvia, og se etter hull eller nullstilling på målere."},
                        {"title": "Lys eller ventilasjon virker feil", "path": "/bygg/", "text": "Sjekk dagslogg, vær, måleverdier, hendelser og gjeldende innstillinger."},
                        {"title": "Robot eller nattjobb virker feil", "path": "/renhold/rapport", "text": "Sjekk plan, faktisk jobb, batteri, dokkperioder, vannstatus og telemetri."},
                        {"title": "Underapp svarer ikke", "path": "/system/systemkart", "text": "Åpne riktig tjeneste, health-lenke og avhengighetsoversikt."},
                    ],
                    "note": "Praktisk regel: feilsøk først om datagrunnlaget er ferskt, deretter om faglogikken er riktig, og til slutt om visningen/grafen presenterer tallene feil.",
                },
            ],
        }

    def operational_incident_review_payload(row: OperationalIncidentReview) -> Dict[str, Any]:
        return {
            "status": row.status,
            "note": row.note or "",
            "reviewed_at": row.reviewed_at,
            "reviewed_by": row.reviewed_by,
        }

    def read_operational_status_file(path: Path) -> dict[str, str]:
        try:
            return parse_status_text(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            return {}

    def import_incident_recommended_action(row: Mapping[str, Any]) -> str:
        status_text = str(row.get("status_text") or "").casefold()
        if "feil" in status_text:
            return "Åpne datakilden, les siste feilmelding og kjør jobben på nytt når årsaken er rettet."
        if "mangler" in status_text:
            return "Kontroller at kilden er konfigurert og at første vellykkede import er gjennomført."
        return "Kontroller tidsplan, avhengigheter og siste vellykkede kjøring før tallene brukes."

    def backup_incident_from_control(control: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        status = str(control.get("status") or "unknown")
        if status == "ok":
            return None
        observed_at = control.get("updatedAt") or datetime(2000, 1, 1)
        return operational_incident(
            key=f"backup:{control.get('key')}",
            domain="Backup",
            title=str(control.get("title") or "Backup"),
            detail=str(control.get("detail") or "Backupstatus må kontrolleres."),
            severity="critical" if status == "critical" else "warning",
            source="QNAP backup",
            started_at=observed_at,
            observed_at=observed_at,
            recommended_action="Kontroller siste statusfil, diskplass og backupjobben før neste planlagte kjøring.",
            path=str(control.get("path") or "/manual/oversikt"),
        )

    async def build_operational_incident_center(
        session,
        now_dt: datetime,
        bollard_status: Optional[Mapping[str, Any]],
        bollard_error: Optional[str],
        bollard_error_started_at: Optional[datetime],
    ) -> Dict[str, Any]:
        FULL_BACKUP_STATUS_PATH = dependencies.FULL_BACKUP_STATUS_PATH
        NIGHTLY_BACKUP_STATUS_PATH = dependencies.NIGHTLY_BACKUP_STATUS_PATH
        notification_outbox_status = dependencies.notification_outbox_status
        import_rows = await import_status_rows(session)
        delivery = await notification_outbox_status(session)
        controls: list[Dict[str, Any]] = []
        incidents: list[Dict[str, Any]] = []

        bad_sources = [row for row in import_rows if row.get("status") == "bad"]
        warning_sources = [row for row in import_rows if row.get("status") == "warn"]
        source_control_status = "critical" if bad_sources else "warning" if warning_sources else "ok"
        controls.append(
            {
                "key": "data-sources",
                "title": "Datakilder",
                "status": source_control_status,
                "statusLabel": "OK" if source_control_status == "ok" else "Feil" if bad_sources else "Kontroller",
                "detail": f"{len(import_rows) - len(bad_sources) - len(warning_sources)}/{len(import_rows)} OK; {len(warning_sources)} trege; {len(bad_sources)} feil eller gamle.",
                "updatedAt": api_local_iso(now_dt),
                "path": "/admin/datakilder",
            }
        )
        for row in bad_sources + warning_sources:
            status = str(row.get("status") or "bad")
            started_at = row.get("last_failed_at") or row.get("last_run_at") or row.get("last_success_at")
            if status == "warn" and row.get("last_success_at") and row.get("expected_interval_minutes"):
                started_at = row["last_success_at"] + timedelta(minutes=int(row["expected_interval_minutes"]))
            started_at = started_at or datetime(2000, 1, 1)
            detail_parts = [str(row.get("status_text") or "Datakilden må kontrolleres")]
            if row.get("age"):
                detail_parts.append(f"alder {row['age']}")
            if row.get("message"):
                detail_parts.append(str(row["message"]))
            incidents.append(
                operational_incident(
                    key=f"source:{row.get('job_name')}",
                    domain="Datakilder",
                    title=str(row.get("title") or row.get("job_name") or "Datakilde"),
                    detail=" · ".join(detail_parts),
                    severity="critical" if status == "bad" else "warning",
                    source=str(row.get("source") or row.get("category") or "Import"),
                    started_at=started_at,
                    observed_at=row.get("last_failed_at") or row.get("last_run_at") or row.get("last_success_at"),
                    recommended_action=import_incident_recommended_action(row),
                    path=f"/admin/datakilder/{quote(str(row.get('job_name') or ''))}",
                    metadata={"status": status, "sourceNo": row.get("source_no")},
                )
            )

        nightly_control = backup_control(
            key="nightly-backup",
            title="Nattbackup",
            values=read_operational_status_file(NIGHTLY_BACKUP_STATUS_PATH),
            now=now_dt,
            warning_after_hours=24,
            critical_after_hours=26,
        )
        restore_control = backup_control(
            key="full-restore-backup",
            title="Gjenopprettingsbackup",
            values=read_operational_status_file(FULL_BACKUP_STATUS_PATH),
            now=now_dt,
            warning_after_hours=48,
            critical_after_hours=49,
        )
        controls.extend([nightly_control, restore_control])
        incidents.extend(
            incident
            for incident in (
                backup_incident_from_control(nightly_control),
                backup_incident_from_control(restore_control),
            )
            if incident is not None
        )

        delivery_status = str(delivery.get("status") or "ok")
        controls.append(
            {
                "key": "notification-delivery",
                "title": "Varselutsending",
                "status": "warning" if delivery_status == "warning" else "ok",
                "statusLabel": "Kontroller" if delivery_status == "warning" else "OK",
                "detail": f"{int_or_zero(delivery.get('pending'))} venter; {int_or_zero(delivery.get('retrying'))} prøves på nytt.",
                "updatedAt": delivery.get("oldestPendingAt"),
                "path": "/varslinger/oversikt",
            }
        )
        if int_or_zero(delivery.get("retrying")):
            incidents.append(
                operational_incident(
                    key="notifications:delivery-retry",
                    domain="Varslinger",
                    title="Varsler prøves på nytt",
                    detail=f"{int_or_zero(delivery.get('retrying'))} varsler ligger i retry-kø.",
                    severity="warning",
                    source="ntfy-utkø",
                    started_at=delivery.get("oldestPendingAt") or now_dt,
                    observed_at=now_dt,
                    recommended_action="Kontroller ntfy-tilgang og siste feilmelding dersom køen ikke tømmes automatisk.",
                    path="/varslinger/oversikt",
                )
            )

        door_rows = (
            await session.execute(
                select(AlarmEvent)
                .where(AlarmEvent.domain == "doors", AlarmEvent.status == "active")
                .order_by(AlarmEvent.detected_at.desc(), AlarmEvent.id.desc())
            )
        ).scalars().all()
        for row in door_rows:
            incidents.append(
                operational_incident(
                    key=f"door:{row.event_key}",
                    domain="Dører",
                    title=row.title,
                    detail=row.detail or "Aktiv døralarm.",
                    severity="critical" if row.severity == "alert" else "warning",
                    source="Solromkontroll",
                    started_at=row.detected_at,
                    observed_at=row.last_observed_at,
                    recommended_action="Kontroller rommet og den tilhørende soltimen. Alarmen løses automatisk når tilstanden opphører.",
                    path=f"/dorer/alarm?alarm={row.id}",
                    metadata={"alarmId": row.id, "notificationStatus": row.notification_status},
                )
            )

        bollard_incidents = list((bollard_status or {}).get("incidents") or [])
        active_bollards = [
            row for row in bollard_incidents if str(row.get("status") or "").strip().lower() in {"active", "acknowledged"}
        ]
        if bollard_error:
            controls.append(
                {
                    "key": "bollards",
                    "title": "Pullertkontroll",
                    "status": "critical",
                    "statusLabel": "Feil",
                    "detail": bollard_error,
                    "updatedAt": api_local_iso(now_dt),
                    "path": "/pullerter/oversikt",
                }
            )
            incidents.append(
                operational_incident(
                    key="bollards:service-unavailable",
                    domain="Pullerter",
                    title="Pullertkontrollen svarer ikke",
                    detail=bollard_error,
                    severity="critical",
                    source="Protect Ledger",
                    started_at=bollard_error_started_at or now_dt,
                    observed_at=now_dt,
                    recommended_action="Åpne pullertoversikten og kontroller Protect Ledger-tjenesten og kameraene.",
                    path="/pullerter/oversikt",
                )
            )
        else:
            runtime = dict((bollard_status or {}).get("runtime") or {})
            ready = bool(dict((bollard_status or {}).get("summary") or {}).get("monitoring_ready"))
            control_status = "critical" if not runtime.get("running", True) or not ready else "warning" if active_bollards else "ok"
            controls.append(
                {
                    "key": "bollards",
                    "title": "Pullertkontroll",
                    "status": control_status,
                    "statusLabel": "OK" if control_status == "ok" else "Kontroller" if control_status == "warning" else "Feil",
                    "detail": f"{len(active_bollards)} aktive hendelser; siste kontroll {runtime.get('last_success_at') or runtime.get('last_run_at') or '-'}.",
                    "updatedAt": runtime.get("last_success_at") or runtime.get("last_run_at"),
                    "path": "/pullerter/oversikt",
                }
            )
            for row in active_bollards:
                severity = str(row.get("severity") or "warning").lower()
                incidents.append(
                    operational_incident(
                        key=f"bollard:{row.get('incident_id')}",
                        domain="Pullerter",
                        title=str(row.get("display_name") or "Visuell endring"),
                        detail="Bekreftet visuell endring som fortsatt er aktiv.",
                        severity="critical" if severity in {"critical", "alert", "high"} else "warning",
                        source="Protect Ledger",
                        started_at=row.get("detected_at") or now_dt,
                        observed_at=row.get("last_observed_at") or row.get("detected_at"),
                        recommended_action="Sammenlign referanse og siste bilde, og kvitter hendelsen etter fysisk eller visuell kontroll.",
                        path="/pullerter/oversikt",
                        metadata={"incidentId": row.get("incident_id")},
                    )
                )

        review_rows = (await session.execute(select(OperationalIncidentReview))).scalars().all()
        review_by_key = {row.incident_key: operational_incident_review_payload(row) for row in review_rows}
        reviewed_incidents = apply_incident_reviews(incidents, review_by_key)
        return {
            "summary": incident_summary(reviewed_incidents),
            "controls": controls,
            "incidents": reviewed_incidents,
            "delivery": delivery,
        }

    async def admin_keys_context(
        request: Request,
        session,
        created_username: str = "",
        created_key: str = "",
        error: str = "",
    ) -> Dict[str, Any]:
        NTFY_ACCESS_COOLDOWN_MINUTES = dependencies.NTFY_ACCESS_COOLDOWN_MINUTES
        NTFY_ACCESS_TOPIC = dependencies.NTFY_ACCESS_TOPIC
        ntfy_subscribe_url = dependencies.ntfy_subscribe_url
        ntfy_topic_url = dependencies.ntfy_topic_url
        key_rows = (await session.execute(select(AccessKey).order_by(AccessKey.created_at.desc()))).scalars().all()
        selected_key = None
        try:
            selected_key_id = int(request.query_params.get("key_id") or "0")
        except ValueError:
            selected_key_id = 0
        if selected_key_id:
            selected_key = next((key for key in key_rows if key.id == selected_key_id), None)

        log_query = select(AccessLog).order_by(AccessLog.timestamp.desc()).limit(200)
        if selected_key:
            log_query = (
                select(AccessLog)
                .where((AccessLog.access_key_id == selected_key.id) | (AccessLog.key_name == selected_key.name))
                .order_by(AccessLog.timestamp.desc())
                .limit(200)
            )
        log_rows = (await session.execute(log_query)).scalars().all()
        return {
            "keys": key_rows,
            "logs": log_rows,
            "selected_key": selected_key,
            "created_username": created_username,
            "created_key": created_key,
            "error": error,
            "ntfy_access_subscribe_url": ntfy_subscribe_url(NTFY_ACCESS_TOPIC, "SUN2 tilgang"),
            "ntfy_access_web_url": ntfy_topic_url(NTFY_ACCESS_TOPIC),
            "ntfy_access_cooldown_minutes": int(NTFY_ACCESS_COOLDOWN_MINUTES),
        }

    def api_import_status_row(row: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(row)
        for key in ("last_success_at", "last_run_at", "last_failed_at", "next_expected_at"):
            payload[key] = api_local_iso(payload.get(key))
        if payload.get("job_name"):
            payload["path"] = f"/admin/datakilder/{quote(str(payload['job_name']))}"
        return payload

    def api_import_status_rows(rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        return [api_import_status_row(row) for row in rows]

    def api_import_job_run_row(row: ImportJobRun) -> Dict[str, Any]:
        return {
            "id": row.id,
            "job_name": row.job_name,
            "title": row.title,
            "category": row.category,
            "source": row.source,
            "started_at": api_local_iso(row.started_at),
            "finished_at": api_local_iso(row.finished_at),
            "ok": row.ok,
            "status": row.status,
            "records_imported": row.records_imported,
            "records_total": row.records_total,
            "duration_seconds": row.duration_seconds,
            "message": row.message,
        }

    def api_admin_manual_payload(import_rows: list[Dict[str, Any]], access_keys: list[Any]) -> tuple[list[ModuleCardPayload], list[ModuleTablePayload]]:
        inventory = system_component_summary()
        cards = [
            api_card("Manual", "Kort", "", "Overblikk over hva du kan se og gjøre", "status", href="/manual/oversikt"),
            api_card("Systemkart", inventory["components"], "stk", "Apper, tjenester og webflater", "status", href="/admin/systemkart"),
            api_card("Datakilder", len(import_rows), "stk", "Ferskhet og feilsøking", "status", href="/admin/datakilder"),
            api_card("Build", APP_BUILD, "", "Siste endringspakke", "status", href="/admin/build"),
        ]
        tables = [
            api_table(
                "Start her",
                ["area", "path", "role", "recommended_action"],
                [
                    {
                        "area": "Daglig drift",
                        "path": "/status/omsetning",
                        "role": "Dashboard for omsetning, parkering, soling og drift akkurat nå.",
                        "recommended_action": "Start her når du vil vite om dagen ligger foran eller bak.",
                    },
                    {
                        "area": "Datagrunnlag",
                        "path": "/admin/datakilder",
                        "role": "Viser om importjobber, HC3, SUN2, EasyPark, Yr og underapper er ferske.",
                        "recommended_action": "Sjekk denne først når tall mangler eller virker feil.",
                    },
                    {
                        "area": "System",
                        "path": "/admin/systemkart",
                        "role": "Klikkbar oversikt over apper, underapper, porter, URL-er og health-lenker.",
                        "recommended_action": "Brukes når du skal finne hvor en tjeneste bor.",
                    },
                    {
                        "area": "Endringer",
                        "path": "/admin/build",
                        "role": "Buildlogg med bestilling, endringer, berørte applikasjoner og tester.",
                        "recommended_action": "Brukes når du lurer på hva som sist ble endret.",
                    },
                    {
                        "area": "Tilgang",
                        "path": "/admin/brukere",
                        "role": "Brukere, roller, master-funksjoner og tilgangslogg.",
                        "recommended_action": "Brukes for passord, aktive brukere og innloggingskontroll.",
                    },
                ],
            ),
            api_table(
                "Hva du kan se og gjøre",
                ["area", "path", "role", "recommended_action"],
                [
                    {
                        "area": "Omsetning",
                        "path": "/omsetning/oversikt",
                        "role": "År, måned, dag, toppdager, toppmåneder og samlet kontroll mot oppgjør.",
                        "recommended_action": "Brukes for økonomisk oversikt og avvik.",
                    },
                    {
                        "area": "Parkering",
                        "path": "/parkering/parkeringer",
                        "role": "Dagens parkeringer, kjøretøy, eier, bilinfo, områder, kamera og oppgjør.",
                        "recommended_action": "Brukes for daglig kontroll av EasyPark og biler.",
                    },
                    {
                        "area": "Soling",
                        "path": "/soling/dagslinje",
                        "role": "Soltimer, rom, senger, medlemmer, produkter, bilder, prognoser og oppgjør.",
                        "recommended_action": "Brukes for å kontrollere soltimer og bildegrunnlag.",
                    },
                    {
                        "area": "Koble",
                        "path": "/koble/oversikt",
                        "role": "Finner sannsynlige koblinger mellom bilnummer og SUN2-ID basert på tidstreff.",
                        "recommended_action": "Brukes for visuell kontroll og bekreftelse av kandidater.",
                    },
                    {
                        "area": "Energi",
                        "path": "/energi/status",
                        "role": "Realtime HC3-forbruk, kurser, laster, Elvia-kontroll og forbruk per seng.",
                        "recommended_action": "Brukes for strømavvik, solsengforbruk og målerkontroll.",
                    },
                    {
                        "area": "Ventilasjon",
                        "path": "/ventilasjon/dagslogg",
                        "role": "Temperatur, fuktighet, Yr, viftehendelser og ventilasjonsinnstillinger.",
                        "recommended_action": "Brukes for å forstå kjøling, lufting og avfukter.",
                    },
                    {
                        "area": "Lys",
                        "path": "/lys/dagslogg",
                        "role": "Lux, skydekke, solhøyde, lysstatus, hendelser og styringsregler.",
                        "recommended_action": "Brukes når lys virker feil eller terskler skal vurderes.",
                    },
                    {
                        "area": "Solrom",
                        "path": "/solrom/oversikt",
                        "role": "Nåstatus, forventet ut, romdetaljer og dagskontroll for solrom 1-12.",
                        "recommended_action": "Brukes for romkontroll og varsel ved for lenge lukket/opptatt rom.",
                    },
                    {
                        "area": "Solrom-2",
                        "path": "/solrom-2/oversikt",
                        "role": "Ny arbeidsflate for solrom med nåstatus, dagsmatrise, avvikskontroll og romdetalj.",
                        "recommended_action": "Brukes for å vurdere beste endelige romkontrollflate mot Solrom og Dører2.",
                    },
                    {
                        "area": "Dører2",
                        "path": "/dorer2/oversikt",
                        "role": "Ny situasjonsflate for rom og byggdører med avvik først, romkart, tidslinje og detaljvisning.",
                        "recommended_action": "Brukes når du trenger rask operativ vurdering av romstatus og døravvik.",
                    },
                    {
                        "area": "Dører",
                        "path": "/dorer/oversikt",
                        "role": "Byggdører, andre dører, åpne/lukke-historikk, rådata og synlige romkontrollvarianter.",
                        "recommended_action": "Brukes for statuskontroll, feilsøking og sammenligning av ulike romkontrollflater.",
                    },
                    {
                        "area": "Vedlikehold",
                        "path": "/vedlikehold/besok",
                        "role": "Besøk på Lilletorget og oppgaver utført under hvert besøk.",
                        "recommended_action": "Brukes for notater, historikk og oppfølging.",
                    },
                    {
                        "area": "Renhold",
                        "path": "/renhold/oversikt",
                        "role": "Roborock-status, siste jobber, robotdetaljer og loggerstatus.",
                        "recommended_action": "Brukes når robotvaskere må sjekkes.",
                    },
                    {
                        "area": "Mobil og iPad",
                        "path": "/mobil/oversikt",
                        "role": "Samlet visning av mobilkortene og inngang til egne mobil/iPad-flater.",
                        "recommended_action": "Brukes for å kontrollere hva de lette grensesnittene viser.",
                    },
                    {
                        "area": "Ideer",
                        "path": "/ideer/oversikt",
                        "role": "Forslag, analyseideer og mulige forbedringer før de flyttes inn i fagområder.",
                        "recommended_action": "Brukes som venteliste for nye funksjoner.",
                    },
                ],
            ),
            api_table(
                "Når noe ser feil ut",
                ["problem", "path", "first_check", "recommended_action"],
                [
                    {
                        "problem": "Tall mangler eller virker gamle",
                        "path": "/admin/datakilder",
                        "first_check": "Se sist OK, alder, melding og neste planlagte jobb.",
                        "recommended_action": "Feilsøk kilden før du vurderer selve grafen.",
                    },
                    {
                        "problem": "Parkering stemmer ikke",
                        "path": "/parkering/parkeringer",
                        "first_check": "Sist EasyPark-import, dagens liste og kilde EasyPark/flowbird-parknordic.",
                        "recommended_action": "Trigger import hvis den er gammel, og sjekk oppgjør ved månedsavvik.",
                    },
                    {
                        "problem": "Soling stemmer ikke",
                        "path": "/soling/enkeltimer",
                        "first_check": "Enkelttimer, dagslinje, produkter og bildearkiv.",
                        "recommended_action": "Sjekk SUN2-scraper og om bildetidspunkt/romkobling er riktig.",
                    },
                    {
                        "problem": "Strøm eller forbruk avviker",
                        "path": "/energi/elvia-kontroll",
                        "first_check": "HC3 realtime, Elvia-import og om målere har hull/nullstilling.",
                        "recommended_action": "Bruk Elvia som kontroll og HC3 som løpende datagrunnlag.",
                    },
                    {
                        "problem": "Lys eller ventilasjon oppfører seg uventet",
                        "path": "/lys/dagslogg",
                        "first_check": "Lux, skydekke, solhøyde, temperatur, fukt og hendelser samme dag.",
                        "recommended_action": "Sjekk innstillinger etter at datagrunnlaget er bekreftet ferskt.",
                    },
                    {
                        "problem": "En underapp svarer ikke",
                        "path": "/admin/systemkart",
                        "first_check": "Health-lenke, lokal URL og compose-service.",
                        "recommended_action": "Bruk QNAP-status/deploy-script hvis tjenesten ikke er healthy.",
                    },
                ],
            ),
            api_table(
                "Underapper med webgrensesnitt",
                ["component", "area", "interface", "web_url", "local_url", "health_url", "status"],
                system_web_interface_rows(),
            ),
        ]
        return cards, tables

    def api_import_job_status(row: Optional[ImportJobStatus]) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        return {
            "jobName": row.job_name,
            "title": row.title,
            "status": row.status,
            "statusText": row.status_text,
            "source": row.source,
            "message": row.message,
            "lastRunAt": api_local_iso(row.last_run_at),
            "lastStartedAt": api_local_iso(row.last_started_at),
            "lastSuccessAt": api_local_iso(row.last_success_at),
            "lastFailedAt": api_local_iso(row.last_failed_at),
            "recordsImported": row.records_imported,
            "recordsTotal": row.records_total,
            "durationSeconds": row.duration_seconds,
        }

    def api_admin_task_row(
        task_key: str,
        severity: str,
        domain: str,
        item: str,
        problem: str,
        detail: str,
        count: Optional[int],
        path: str,
        recommended_action: str,
    ) -> Dict[str, Any]:
        ADMIN_TASK_SEVERITY_SORT = dependencies.ADMIN_TASK_SEVERITY_SORT
        return {
            "task_key": task_key,
            "severity": severity,
            "domain": domain,
            "item": item,
            "problem": problem,
            "detail": detail,
            "count": count,
            "path": path,
            "recommended_action": recommended_action,
            "_sort": ADMIN_TASK_SEVERITY_SORT.get(severity, 9),
        }

    def admin_task_import_severity(status: str) -> str:
        if status == "bad":
            return "Kritisk"
        if status == "warn":
            return "Høy"
        return "Medium"

    async def build_admin_task_rows(session, import_rows: list[Dict[str, Any]], now_dt: datetime) -> list[Dict[str, Any]]:
        age_label = dependencies.age_label
        minutes_since = dependencies.minutes_since
        vehicle_area_not_found_condition = dependencies.vehicle_area_not_found_condition
        vehicle_blank_area_condition = dependencies.vehicle_blank_area_condition
        vehicle_blank_name_condition = dependencies.vehicle_blank_name_condition
        vehicle_name_not_found_condition = dependencies.vehicle_name_not_found_condition
        task_rows: list[Dict[str, Any]] = []

        for row in import_rows:
            status = str(row.get("status") or "")
            if status not in {"bad", "warn"}:
                continue
            task_rows.append(
                api_admin_task_row(
                    f"import:{row.get('job_name') or row.get('title') or 'unknown'}",
                    admin_task_import_severity(status),
                    "Datakilde",
                    str(row.get("title") or row.get("job_name") or "-"),
                    str(row.get("status_text") or status),
                    f"{row.get('age') or 'Ingen alder'} - {row.get('message') or row.get('description') or 'Ingen melding'}",
                    int_or_zero(row.get("records_total")) if row.get("records_total") is not None else None,
                    "/admin/datakilder",
                    "Sjekk siste kjøring, feilmelding og planlagt oppdatering.",
                )
            )

        vehicle_blank_name_count = int_or_zero(
            (await session.execute(select(func.count(ParkingVehicle.plate)).where(vehicle_blank_name_condition()))).scalar_one()
        )
        vehicle_name_not_found_count = int_or_zero(
            (await session.execute(select(func.count(ParkingVehicle.plate)).where(vehicle_name_not_found_condition()))).scalar_one()
        )
        vehicle_blank_area_count = int_or_zero(
            (await session.execute(select(func.count(ParkingVehicle.plate)).where(vehicle_blank_area_condition()))).scalar_one()
        )
        vehicle_area_not_found_count = int_or_zero(
            (await session.execute(select(func.count(ParkingVehicle.plate)).where(vehicle_area_not_found_condition()))).scalar_one()
        )
        if vehicle_blank_name_count:
            task_rows.append(
                api_admin_task_row(
                    "parking:vehicle-name-blank",
                    "Medium",
                    "Parkering",
                    "Kjøretøy uten navn",
                    "Mangler eiernavn",
                    "Blankt navn i kjøretøytabellen.",
                    vehicle_blank_name_count,
                    "/parkering/oppslag",
                    "Kjør SVV-sync eller oppdater kjøretøy manuelt.",
                )
            )
        if vehicle_name_not_found_count:
            task_rows.append(
                api_admin_task_row(
                    "parking:vehicle-name-not-found",
                    "Lav",
                    "Parkering",
                    "Kjøretøy med navn ikke funnet",
                    "SVV fant ikke navn",
                    "Disse inngår i hovedtallet mangler navn, men vises separat.",
                    vehicle_name_not_found_count,
                    "/parkering/oppslag",
                    "Kontroller om registreringsnummeret er korrekt eller la posten stå som ikke funnet.",
                )
            )
        if vehicle_blank_area_count:
            task_rows.append(
                api_admin_task_row(
                    "parking:vehicle-area-blank",
                    "Medium",
                    "Parkering",
                    "Kjøretøy uten område",
                    "Mangler område",
                    "Blankt område i kjøretøytabellen.",
                    vehicle_blank_area_count,
                    "/parkering/omrade",
                    "Bruk områdeoversikten for å sette område eller rydde grunnlaget.",
                )
            )
        if vehicle_area_not_found_count:
            task_rows.append(
                api_admin_task_row(
                    "parking:vehicle-area-not-found",
                    "Medium",
                    "Parkering",
                    "Kjøretøy med område ikke funnet",
                    "Områdeoppslag ga ikke treff",
                    "Kan gi svakere områdestatistikk og rapportering.",
                    vehicle_area_not_found_count,
                    "/parkering/oppslag",
                    "Rydd ikke funnet-verdier eller legg inn område manuelt.",
                )
            )

        sun_image_cutoff = now_dt - timedelta(days=14)
        sun_sessions_without_images = int_or_zero(
            (
                await session.execute(
                    select(func.count(Sun2TanningSession.id))
                    .outerjoin(Sun2TanningSessionImage, Sun2TanningSessionImage.session_id == Sun2TanningSession.id)
                    .where(Sun2TanningSession.started_at >= sun_image_cutoff)
                    .where(Sun2TanningSessionImage.id.is_(None))
                )
            ).scalar_one()
        )
        if sun_sessions_without_images:
            task_rows.append(
                api_admin_task_row(
                    "sun2:sessions-without-image",
                    "Høy",
                    "Soling",
                    "Solinger uten bilde",
                    "Mangler Axis-bilde",
                    "Gjelder soltimer siste 14 dager.",
                    sun_sessions_without_images,
                    "/soling/enkeltimer",
                    "Kontroller bildeinnlesing og koble riktig bilde til timen.",
                )
            )

        latest_energy = (
            await session.execute(select(EnergyFibaroSample).order_by(EnergyFibaroSample.bucket_start.desc()).limit(1))
        ).scalars().first()
        energy_age_minutes = minutes_since(latest_energy.bucket_start if latest_energy else None, now_dt)
        if energy_age_minutes is None or energy_age_minutes > 3:
            task_rows.append(
                api_admin_task_row(
                    "energy:realtime-stale",
                    "Kritisk" if energy_age_minutes is None or energy_age_minutes > 10 else "Høy",
                    "Energi",
                    "Realtime energilogging",
                    "Siste sample er for gammel",
                    age_label(energy_age_minutes),
                    None,
                    "/energi/status",
                    "Kontroller HC3-logging, scheduler og Fibaro API.",
                )
            )
        if latest_energy and abs(float_or_zero(latest_energy.differanse_beregnet_w)) >= 1000:
            task_rows.append(
                api_admin_task_row(
                    "energy:diff-over-1000w",
                    "Medium",
                    "Energi",
                    "Uforklart effektdifferanse",
                    "Diff over 1000 W",
                    f"{format_short_number(latest_energy.differanse_beregnet_w)} W ved {latest_energy.bucket_start.strftime('%H:%M')}",
                    None,
                    "/energi/status",
                    "Sjekk umålte laster, takvifte, kursgrunnlag og aktive solsenger.",
                )
            )

        task_rows.sort(key=lambda item: (item.get("_sort", 9), item.get("domain") or "", item.get("item") or ""))
        for row in task_rows:
            row.pop("_sort", None)
        return task_rows

    def quality_percent(ok_count: int, total_count: int) -> Optional[float]:
        if total_count <= 0:
            return None
        return round(max(0.0, min(100.0, (ok_count / total_count) * 100.0)), 1)

    def quality_status_from_percent(value: Optional[float], warn_below: float = 98.0, bad_below: float = 90.0) -> str:
        if value is None:
            return "bad"
        if value < bad_below:
            return "bad"
        if value < warn_below:
            return "warn"
        return "ok"

    def quality_status_from_age(minutes: Optional[int], warn_after: int, bad_after: int) -> str:
        if minutes is None:
            return "bad"
        if minutes > bad_after:
            return "bad"
        if minutes > warn_after:
            return "warn"
        return "ok"

    async def build_admin_data_quality(session, import_rows: list[Dict[str, Any]], now_dt: datetime) -> Dict[str, Any]:
        age_label = dependencies.age_label
        api_data_quality_row = dependencies.api_data_quality_row
        minutes_since = dependencies.minutes_since
        vehicle_missing_area_condition = dependencies.vehicle_missing_area_condition
        vehicle_missing_name_condition = dependencies.vehicle_missing_name_condition
        today_start = datetime.combine(now_dt.date(), time.min)
        import_total = len(import_rows)
        import_ok = sum(1 for row in import_rows if row.get("status") == "ok")
        import_coverage = quality_percent(import_ok, import_total)

        vehicle_count = int_or_zero((await session.execute(select(func.count(ParkingVehicle.plate)))).scalar_one())
        vehicle_missing_name = int_or_zero(
            (await session.execute(select(func.count(ParkingVehicle.plate)).where(vehicle_missing_name_condition()))).scalar_one()
        )
        vehicle_missing_area = int_or_zero(
            (await session.execute(select(func.count(ParkingVehicle.plate)).where(vehicle_missing_area_condition()))).scalar_one()
        )
        vehicle_name_coverage = quality_percent(max(0, vehicle_count - vehicle_missing_name), vehicle_count)
        vehicle_area_coverage = quality_percent(max(0, vehicle_count - vehicle_missing_area), vehicle_count)

        parking_count = int_or_zero((await session.execute(select(func.count(ParkingSession.id)))).scalar_one())
        parking_missing_plate = int_or_zero(
            (
                await session.execute(
                    select(func.count(ParkingSession.id)).where(
                        func.trim(func.coalesce(ParkingSession.car_license_number, "")) == ""
                    )
                )
            ).scalar_one()
        )
        parking_plate_coverage = quality_percent(max(0, parking_count - parking_missing_plate), parking_count)

        sun_cutoff = now_dt - timedelta(days=14)
        sun_recent_count = int_or_zero(
            (
                await session.execute(
                    select(func.count(Sun2TanningSession.id)).where(Sun2TanningSession.started_at >= sun_cutoff)
                )
            ).scalar_one()
        )
        sun_without_image = int_or_zero(
            (
                await session.execute(
                    select(func.count(Sun2TanningSession.id))
                    .outerjoin(Sun2TanningSessionImage, Sun2TanningSessionImage.session_id == Sun2TanningSession.id)
                    .where(Sun2TanningSession.started_at >= sun_cutoff)
                    .where(Sun2TanningSessionImage.id.is_(None))
                )
            ).scalar_one()
        )
        sun_image_coverage = quality_percent(max(0, sun_recent_count - sun_without_image), sun_recent_count)

        sun_missing_room = int_or_zero(
            (
                await session.execute(
                    select(func.count(Sun2TanningSession.id)).where(
                        and_(
                            func.trim(func.coalesce(Sun2TanningSession.room_id, "")) == "",
                            func.trim(func.coalesce(Sun2TanningSession.room, "")) == "",
                        )
                    )
                )
            ).scalar_one()
        )
        sun_total_count = int_or_zero((await session.execute(select(func.count(Sun2TanningSession.id)))).scalar_one())
        sun_room_coverage = quality_percent(max(0, sun_total_count - sun_missing_room), sun_total_count)

        latest_energy = (
            await session.execute(select(EnergyFibaroSample).order_by(EnergyFibaroSample.bucket_start.desc()).limit(1))
        ).scalars().first()
        energy_age = minutes_since(latest_energy.bucket_start if latest_energy else None, now_dt)
        energy_today_count = int_or_zero(
            (
                await session.execute(
                    select(func.count(EnergyFibaroSample.id)).where(EnergyFibaroSample.bucket_start >= today_start)
                )
            ).scalar_one()
        )
        expected_energy_samples = max(1, int(max(60, (now_dt - today_start).total_seconds()) // 30))
        energy_sample_coverage = round(min(100.0, (energy_today_count / expected_energy_samples) * 100.0), 1)

        latest_ventilation = (
            await session.execute(select(VentilationSample).order_by(VentilationSample.bucket_start.desc()).limit(1))
        ).scalars().first()
        latest_yr = (
            await session.execute(select(YrForecastSample).order_by(YrForecastSample.bucket_start.desc()).limit(1))
        ).scalars().first()
        latest_light = (
            await session.execute(select(OutdoorLightSample).order_by(OutdoorLightSample.bucket_start.desc()).limit(1))
        ).scalars().first()
        ventilation_age = minutes_since(latest_ventilation.bucket_start if latest_ventilation else None, now_dt)
        yr_age = minutes_since(latest_yr.bucket_start if latest_yr else None, now_dt)
        light_age = minutes_since(latest_light.bucket_start if latest_light else None, now_dt)

        rows = [
            api_data_quality_row(
                "Datakilder",
                "Importstatus",
                quality_status_from_percent(import_coverage, warn_below=100.0, bad_below=90.0),
                f"{import_ok}/{import_total}",
                "Alle kilder OK",
                import_coverage,
                import_total - import_ok,
                import_total,
                "Basert på import_job_status og fallback-kilder.",
                "/admin/datakilder",
                "Sjekk kilder med advarsel eller feil.",
            ),
            api_data_quality_row(
                "Parkering",
                "Kjøretøy med eiernavn",
                quality_status_from_percent(vehicle_name_coverage, warn_below=98.0, bad_below=90.0),
                f"{max(0, vehicle_count - vehicle_missing_name)}/{vehicle_count}",
                "Minst 98 % dekning",
                vehicle_name_coverage,
                vehicle_missing_name,
                vehicle_count,
                "Blankt navn og 'ikke funnet' regnes som mangler.",
                "/parkering/oppslag",
                "Kjør SVV-sync og behandle kjøretøy som fortsatt mangler navn.",
            ),
            api_data_quality_row(
                "Parkering",
                "Kjøretøy med område",
                quality_status_from_percent(vehicle_area_coverage, warn_below=98.0, bad_below=90.0),
                f"{max(0, vehicle_count - vehicle_missing_area)}/{vehicle_count}",
                "Minst 98 % dekning",
                vehicle_area_coverage,
                vehicle_missing_area,
                vehicle_count,
                "Blankt område og 'ikke funnet' regnes som mangler.",
                "/parkering/omrade",
                "Sett område eller nullstill 'ikke funnet' for ny behandling.",
            ),
            api_data_quality_row(
                "Parkering",
                "Parkeringer med reg.nr",
                quality_status_from_percent(parking_plate_coverage, warn_below=99.5, bad_below=98.0),
                f"{max(0, parking_count - parking_missing_plate)}/{parking_count}",
                "Minst 99,5 % dekning",
                parking_plate_coverage,
                parking_missing_plate,
                parking_count,
                "Kontrollerer at EasyPark-rader har registreringsnummer.",
                "/parkering/parkeringer",
                "Sjekk importgrunnlaget hvis det finnes parkeringer uten reg.nr.",
            ),
            api_data_quality_row(
                "Soling",
                "Soltimer med bilde siste 14 dager",
                quality_status_from_percent(sun_image_coverage, warn_below=98.0, bad_below=90.0),
                f"{max(0, sun_recent_count - sun_without_image)}/{sun_recent_count}",
                "Minst 98 % dekning",
                sun_image_coverage,
                sun_without_image,
                sun_recent_count,
                "Måler Axis-bilder koblet til soltimer siste 14 dager.",
                "/soling/enkeltimer",
                "Kjør bildekobling og kontroller Axis-arkivet ved manglende treff.",
            ),
            api_data_quality_row(
                "Soling",
                "Soltimer med rom",
                quality_status_from_percent(sun_room_coverage, warn_below=99.5, bad_below=98.0),
                f"{max(0, sun_total_count - sun_missing_room)}/{sun_total_count}",
                "Minst 99,5 % dekning",
                sun_room_coverage,
                sun_missing_room,
                sun_total_count,
                "Rom-ID eller romnavn må finnes for analyse per seng.",
                "/soling/enkeltimer",
                "Sjekk SUN2-import hvis rom mangler.",
            ),
            api_data_quality_row(
                "Energi",
                "Realtime samples i dag",
                quality_status_from_percent(energy_sample_coverage, warn_below=95.0, bad_below=85.0),
                f"{energy_today_count}/{expected_energy_samples}",
                "Minst 95 % av forventet 30-sek logging",
                energy_sample_coverage,
                max(0, expected_energy_samples - energy_today_count),
                energy_today_count,
                f"Siste sample: {age_label(energy_age)}.",
                "/energi/status",
                "Kontroller HC3-logger og scheduler hvis dekningen faller.",
            ),
            api_data_quality_row(
                "Energi",
                "Realtime ferskhet",
                quality_status_from_age(energy_age, warn_after=3, bad_after=10),
                age_label(energy_age),
                "Maks 3 min gammel",
                None,
                None,
                energy_today_count,
                f"Siste bucket: {latest_energy.bucket_start.strftime('%d.%m %H:%M') if latest_energy else '-'}",
                "/energi/status",
                "Sjekk energilogging hvis siste sample er for gammel.",
            ),
            api_data_quality_row(
                "Ventilasjon",
                "Ventilasjon ferskhet",
                quality_status_from_age(ventilation_age, warn_after=3, bad_after=10),
                age_label(ventilation_age),
                "Maks 3 min gammel",
                None,
                None,
                None,
                f"Siste sample: {latest_ventilation.bucket_start.strftime('%d.%m %H:%M') if latest_ventilation else '-'}",
                "/ventilasjon/dagslogg",
                "Kontroller HC3 ventilasjonslogger hvis sample stopper.",
            ),
            api_data_quality_row(
                "Vær",
                "Yr ferskhet",
                quality_status_from_age(yr_age, warn_after=90, bad_after=180),
                age_label(yr_age),
                "Maks 90 min gammel",
                None,
                None,
                None,
                f"Siste vær: {latest_yr.weather_text if latest_yr else '-'}",
                "/ventilasjon/yr-logg",
                "Sjekk Yr API og importstatus ved gammel værdata.",
            ),
            api_data_quality_row(
                "Lys",
                "Lys/lux ferskhet",
                quality_status_from_age(light_age, warn_after=3, bad_after=10),
                age_label(light_age),
                "Maks 3 min gammel",
                None,
                None,
                None,
                f"Siste lux: {format_short_number(latest_light.lux) if latest_light and latest_light.lux is not None else '-'}",
                "/lys/dagslogg",
                "Kontroller lyslogger hvis sample stopper.",
            ),
        ]
        bad_count = sum(1 for row in rows if row["status"] == "bad")
        warn_count = sum(1 for row in rows if row["status"] == "warn")
        ok_count = sum(1 for row in rows if row["status"] == "ok")
        score = round(((ok_count + warn_count * 0.6) / len(rows)) * 100.0, 0) if rows else 0
        issue_rows = [row for row in rows if row["status"] != "ok"]
        return {
            "score": score,
            "ok_count": ok_count,
            "warn_count": warn_count,
            "bad_count": bad_count,
            "rows": rows,
            "issue_rows": issue_rows,
        }

    def pearson_correlation(pairs: list[tuple[float, float]]) -> Optional[float]:
        if len(pairs) < 7:
            return None
        xs = [pair[0] for pair in pairs]
        ys = [pair[1] for pair in pairs]
        mean_x = sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
        denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
        denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
        denominator = denom_x * denom_y
        if denominator == 0:
            return None
        return numerator / denominator

    def correlation_strength(value: Optional[float]) -> str:
        if value is None:
            return "For lite data"
        absolute = abs(value)
        if absolute >= 0.7:
            return "Sterk"
        if absolute >= 0.4:
            return "Moderat"
        if absolute >= 0.2:
            return "Svak"
        return "Lav"

    def correlation_direction(value: Optional[float]) -> str:
        if value is None:
            return "-"
        if value > 0.05:
            return "Positiv"
        if value < -0.05:
            return "Negativ"
        return "Nøytral"

    async def build_admin_relation_analysis(session, now_dt: datetime) -> Dict[str, Any]:
        end_day = now_dt.date()
        start_day = end_day - timedelta(days=89)
        start_dt = datetime.combine(start_day, time.min)
        end_dt = datetime.combine(end_day + timedelta(days=1), time.min)

        sun_rows = (
            await session.execute(
                select(
                    Sun2TanningSession.stat_date.label("day"),
                    func.count(Sun2TanningSession.id).label("sun_count"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("sun_paid"),
                    func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("sun_minutes"),
                )
                .where(Sun2TanningSession.stat_date >= start_day)
                .where(Sun2TanningSession.stat_date <= end_day)
                .group_by(Sun2TanningSession.stat_date)
            )
        ).mappings().all()
        parking_day = cast(ParkingSession.start_time, Date)
        parking_rows = (
            await session.execute(
                select(
                    parking_day.label("day"),
                    func.count(ParkingSession.id).label("parking_count"),
                    func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("parking_paid"),
                    func.coalesce(func.sum(ParkingSession.parking_time_min), 0).label("parking_minutes"),
                )
                .where(ParkingSession.start_time >= start_dt)
                .where(ParkingSession.start_time < end_dt)
                .group_by(parking_day)
            )
        ).mappings().all()
        yr_day = cast(YrForecastSample.bucket_start, Date)
        yr_rows = (
            await session.execute(
                select(
                    yr_day.label("day"),
                    func.avg(YrForecastSample.air_temperature).label("air_temperature"),
                    func.avg(YrForecastSample.relative_humidity).label("relative_humidity"),
                    func.avg(YrForecastSample.wind_speed).label("wind_speed"),
                    func.avg(YrForecastSample.cloud_area_fraction).label("cloud_area_fraction"),
                    func.count(YrForecastSample.id).label("weather_samples"),
                )
                .where(YrForecastSample.bucket_start >= start_dt)
                .where(YrForecastSample.bucket_start < end_dt)
                .group_by(yr_day)
            )
        ).mappings().all()
        energy_day = cast(EnergyFibaroSample.bucket_start, Date)
        energy_rows = (
            await session.execute(
                select(
                    energy_day.label("day"),
                    func.avg(EnergyFibaroSample.inntak_w).label("avg_inntak_w"),
                    func.avg(EnergyFibaroSample.differanse_beregnet_w).label("avg_diff_w"),
                    func.count(EnergyFibaroSample.id).label("energy_samples"),
                )
                .where(EnergyFibaroSample.bucket_start >= start_dt)
                .where(EnergyFibaroSample.bucket_start < end_dt)
                .group_by(energy_day)
            )
        ).mappings().all()

        days: Dict[date, Dict[str, Any]] = {}
        weekday_labels = ["Man", "Tir", "Ons", "Tor", "Fre", "Lør", "Søn"]
        for offset in range((end_day - start_day).days + 1):
            current_day = start_day + timedelta(days=offset)
            days[current_day] = {
                "day": current_day.isoformat(),
                "weekday": weekday_labels[current_day.weekday()],
                "weekday_index": current_day.weekday() + 1,
                "is_weekend": 1 if current_day.weekday() >= 5 else 0,
                "sun_count": 0,
                "sun_paid": 0.0,
                "sun_minutes": 0.0,
                "parking_count": 0,
                "parking_paid": 0.0,
                "parking_minutes": 0.0,
                "air_temperature": None,
                "relative_humidity": None,
                "wind_speed": None,
                "cloud_area_fraction": None,
                "avg_inntak_w": None,
                "avg_diff_w": None,
                "weather_samples": 0,
                "energy_samples": 0,
            }
        for row in sun_rows:
            item = days.get(row["day"])
            if item is not None:
                item["sun_count"] = int_or_zero(row["sun_count"])
                item["sun_paid"] = round(float_or_zero(row["sun_paid"]), 2)
                item["sun_minutes"] = round(float_or_zero(row["sun_minutes"]), 1)
        for row in parking_rows:
            item = days.get(row["day"])
            if item is not None:
                item["parking_count"] = int_or_zero(row["parking_count"])
                item["parking_paid"] = round(float_or_zero(row["parking_paid"]), 2)
                item["parking_minutes"] = round(float_or_zero(row["parking_minutes"]), 1)
        for row in yr_rows:
            item = days.get(row["day"])
            if item is not None:
                item["air_temperature"] = round(float_or_zero(row["air_temperature"]), 2) if row["air_temperature"] is not None else None
                item["relative_humidity"] = round(float_or_zero(row["relative_humidity"]), 2) if row["relative_humidity"] is not None else None
                item["wind_speed"] = round(float_or_zero(row["wind_speed"]), 2) if row["wind_speed"] is not None else None
                item["cloud_area_fraction"] = round(float_or_zero(row["cloud_area_fraction"]), 2) if row["cloud_area_fraction"] is not None else None
                item["weather_samples"] = int_or_zero(row["weather_samples"])
        for row in energy_rows:
            item = days.get(row["day"])
            if item is not None:
                item["avg_inntak_w"] = round(float_or_zero(row["avg_inntak_w"]), 2) if row["avg_inntak_w"] is not None else None
                item["avg_diff_w"] = round(float_or_zero(row["avg_diff_w"]), 2) if row["avg_diff_w"] is not None else None
                item["energy_samples"] = int_or_zero(row["energy_samples"])

        day_rows = []
        for item in days.values():
            total_paid = float_or_zero(item["sun_paid"]) + float_or_zero(item["parking_paid"])
            day_rows.append({**item, "total_paid": round(total_paid, 2)})

        target_defs = [
            ("sun_count", "Solinger"),
            ("sun_paid", "Soling omsetning"),
            ("parking_count", "Parkeringer"),
            ("parking_paid", "Parkering omsetning"),
            ("total_paid", "Total omsetning"),
        ]
        factor_defs = [
            ("weekday_index", "Ukedag"),
            ("is_weekend", "Helg"),
            ("air_temperature", "Ute temperatur"),
            ("relative_humidity", "Relativ fuktighet"),
            ("wind_speed", "Vind"),
            ("cloud_area_fraction", "Skydekke"),
            ("avg_inntak_w", "Snitt strømforbruk"),
            ("avg_diff_w", "Snitt uforklart diff"),
        ]
        correlation_rows = []
        for target_key, target_label in target_defs:
            for factor_key, factor_label in factor_defs:
                pairs = []
                for row in day_rows:
                    target_value = row.get(target_key)
                    factor_value = row.get(factor_key)
                    if target_value is None or factor_value is None:
                        continue
                    pairs.append((float(target_value), float(factor_value)))
                corr = pearson_correlation(pairs)
                if corr is None:
                    continue
                correlation_rows.append(
                    {
                        "target": target_label,
                        "factor": factor_label,
                        "correlation": round(corr, 3),
                        "strength": correlation_strength(corr),
                        "direction": correlation_direction(corr),
                        "sample_days": len(pairs),
                        "detail": "Korrelasjon er indikasjon, ikke årsaksbevis.",
                    }
                )
        correlation_rows.sort(key=lambda row: abs(float_or_zero(row.get("correlation"))), reverse=True)

        def strongest_for(target: str) -> Optional[Dict[str, Any]]:
            for row in correlation_rows:
                if row["target"] == target:
                    return row
            return None

        strongest_sun = strongest_for("Solinger")
        strongest_parking = strongest_for("Parkeringer")
        strongest_revenue = strongest_for("Total omsetning")
        chart_days = day_rows[-45:]
        chart = api_chart(
            "Daglig utvikling og analysegrunnlag",
            [row["day"] for row in chart_days],
            [
                {"name": "Solinger", "type": "bar", "data": [row["sun_count"] for row in chart_days], "color": "#f59e0b"},
                {"name": "Parkeringer", "type": "bar", "data": [row["parking_count"] for row in chart_days], "color": "#2563eb"},
            ],
            subtitle="Siste 45 dager. Bruk tabellene under for korrelasjoner.",
            chart_type="bar",
            height=320,
            metrics=[
                {
                    "key": "count",
                    "label": "Antall",
                    "unit": "stk",
                    "series": [
                        {"name": "Solinger", "type": "bar", "data": [row["sun_count"] for row in chart_days], "color": "#f59e0b"},
                        {"name": "Parkeringer", "type": "bar", "data": [row["parking_count"] for row in chart_days], "color": "#2563eb"},
                    ],
                },
                {
                    "key": "revenue",
                    "label": "Omsetning",
                    "unit": "kr",
                    "series": [
                        {"name": "Soling", "type": "line", "data": [row["sun_paid"] for row in chart_days], "color": "#f59e0b"},
                        {"name": "Parkering", "type": "line", "data": [row["parking_paid"] for row in chart_days], "color": "#2563eb"},
                        {"name": "Sum", "type": "line", "data": [row["total_paid"] for row in chart_days], "color": "#dc2626"},
                    ],
                },
                {
                    "key": "weather",
                    "label": "Vær",
                    "unit": "",
                    "series": [
                        {"name": "Temp", "type": "line", "data": [row["air_temperature"] for row in chart_days], "color": "#0ea5e9"},
                        {"name": "Skydekke", "type": "line", "data": [row["cloud_area_fraction"] for row in chart_days], "color": "#64748b"},
                        {"name": "Vind", "type": "line", "data": [row["wind_speed"] for row in chart_days], "color": "#14b8a6"},
                    ],
                },
            ],
            default_metric="count",
            disable_zoom=True,
        )
        analysed_days = len([row for row in day_rows if row["sun_count"] or row["parking_count"]])
        weather_days = len([row for row in day_rows if row["weather_samples"]])
        energy_days = len([row for row in day_rows if row["energy_samples"]])
        return {
            "start_day": start_day,
            "end_day": end_day,
            "analysed_days": analysed_days,
            "weather_days": weather_days,
            "energy_days": energy_days,
            "strongest_sun": strongest_sun,
            "strongest_parking": strongest_parking,
            "strongest_revenue": strongest_revenue,
            "correlation_rows": correlation_rows,
            "day_rows": list(reversed(day_rows)),
            "chart": chart,
        }

    async def build_reconciliation_control(session, now_dt: datetime) -> Dict[str, Any]:
        get_parking_sun_link_state = dependencies.get_parking_sun_link_state
        latest_energy_reconciliation_check = dependencies.latest_energy_reconciliation_check
        sunroom_door_alarm_payload = dependencies.sunroom_door_alarm_payload
        settlement_rows = await revenue_settlement_reconciliation_rows(session, limit=6)
        settlement_checks: list[Dict[str, Any]] = []
        for row in settlement_rows:
            period_label = str(row.get("period_label") or row.get("period_start") or "Ukjent periode")
            parking_id = row.get("parking_settlement_id")
            sun_id = row.get("sun_settlement_id")
            settlement_checks.append(
                evaluate_reconciliation(
                    check_id=f"parking-settlement-{row.get('period_start')}",
                    domain="Parkering",
                    title="Parkeringsoppgjør",
                    actual_label="EasyPark + Flowbird",
                    actual_value=row.get("parking_system_ex_vat"),
                    reference_label="ParkNordic-oppgjør",
                    reference_value=row.get("parking_settlement_ex_vat"),
                    unit="kr eks. mva",
                    period=period_label,
                    absolute_tolerance=1.0,
                    critical_multiplier=3.0,
                    confidence=100 if parking_id else None,
                    detail="Kontrollerer månedssum i Fibaro10 mot brutto mynt/kort og EasyPark i originalbilaget.",
                    path=f"/parkering/oppgjor/{parking_id}" if parking_id else "/parkering/oppgjor",
                    updated_at=row.get("parking_settlement_imported_at"),
                )
            )
            settlement_checks.append(
                evaluate_reconciliation(
                    check_id=f"sun-settlement-{row.get('period_start')}",
                    domain="Soling",
                    title="Solingsoppgjør",
                    actual_label="SUN2 solomsetning",
                    actual_value=row.get("sun_system_ex_vat"),
                    reference_label="Altera-oppgjør",
                    reference_value=row.get("sun_settlement_ex_vat"),
                    unit="kr eks. mva",
                    period=period_label,
                    absolute_tolerance=1.0,
                    critical_multiplier=3.0,
                    confidence=100 if sun_id else None,
                    detail="Kontrollerer intern SUN2-omsetning mot solomsetning lest fra kreditnotaen.",
                    path=f"/soling/oppgjor/{sun_id}" if sun_id else "/soling/oppgjor",
                    updated_at=row.get("sun_settlement_imported_at"),
                )
            )

        energy_check = await latest_energy_reconciliation_check(session)
        door_payload = await sunroom_door_alarm_payload(session, history_limit=50)
        door_summary = dict(door_payload.get("summary") or {})
        active_door_alarms = int_or_zero(door_summary.get("alarm"))
        watched_doors = int_or_zero(door_summary.get("watch"))
        door_status = "critical" if active_door_alarms else "warning" if watched_doors else "ok"
        door_check = state_reconciliation(
            check_id="doors-sun-session-control",
            domain="Dører",
            title="Solromdør mot soltime",
            status=door_status,
            value_label="Aktive alarmer",
            value=active_door_alarms,
            unit="stk",
            period="Nå",
            detail=f"{watched_doors} rom venter på soltime; {int_or_zero(door_summary.get('historyActive'))} aktive historikkposter.",
            path="/dorer/alarm",
            updated_at=door_payload.get("generatedAt"),
            confidence=100,
        )

        link_state = await get_parking_sun_link_state(session)
        worker_age_seconds = (
            max(0.0, (now_dt - normalize_local_naive(link_state.last_worker_seen_at)).total_seconds())
            if link_state.last_worker_seen_at
            else None
        )
        if link_state.last_error:
            link_status = "critical"
        elif not link_state.enabled or worker_age_seconds is None or worker_age_seconds > 180:
            link_status = "warning"
        else:
            link_status = "ok"
        link_check = state_reconciliation(
            check_id="parking-sun-link-worker",
            domain="Koble",
            title="Parkering mot SUN2",
            status=link_status,
            value_label="Sterke kandidater",
            value=int_or_zero(link_state.strong_candidate_count),
            unit="stk",
            period=f"Generasjon {int_or_zero(link_state.generation)}",
            detail=(
                link_state.last_error
                or f"{int_or_zero(link_state.processed_count)} parkeringer kontrollert; "
                f"{int_or_zero(link_state.candidate_count)} kandidater. {link_state.status_text or ''}".strip()
            ),
            path="/koble/oversikt",
            updated_at=link_state.last_worker_seen_at or link_state.updated_at,
            confidence=100 if link_status == "ok" else 70,
        )

        groups = [
            reconciliation_group(
                "settlements",
                "Oppgjør",
                "De seks nyeste periodene, sammenlignet mot originalbilag.",
                settlement_checks,
            ),
            reconciliation_group(
                "operations",
                "Løpende kontroller",
                "Energi, solrom og koblingsmotor vurdert med samme statusmodell.",
                [energy_check, door_check, link_check],
            ),
        ]
        checks = [check for group in groups for check in group["checks"]]
        return {
            "generated_at": api_local_iso(now_dt),
            "summary": reconciliation_summary(checks),
            "groups": groups,
        }

    def import_counts_for_json(counts: Dict[str, Any]) -> Dict[str, Any]:
        return {
            key: (value.isoformat() if isinstance(value, datetime) else value)
            for key, value in counts.items()
        }

    return {
        "admin_keys_context": admin_keys_context,
        "admin_manual_payload": admin_manual_payload,
        "admin_task_import_severity": admin_task_import_severity,
        "api_admin_manual_payload": api_admin_manual_payload,
        "api_admin_task_row": api_admin_task_row,
        "api_import_job_run_row": api_import_job_run_row,
        "api_import_job_status": api_import_job_status,
        "api_import_status_row": api_import_status_row,
        "api_import_status_rows": api_import_status_rows,
        "backup_incident_from_control": backup_incident_from_control,
        "build_admin_data_quality": build_admin_data_quality,
        "build_admin_relation_analysis": build_admin_relation_analysis,
        "build_admin_task_rows": build_admin_task_rows,
        "build_operational_incident_center": build_operational_incident_center,
        "build_reconciliation_control": build_reconciliation_control,
        "cleanup_operational_history_once": cleanup_operational_history_once,
        "correlation_direction": correlation_direction,
        "correlation_strength": correlation_strength,
        "fallback_import_job_status": fallback_import_job_status,
        "import_counts_for_json": import_counts_for_json,
        "import_incident_recommended_action": import_incident_recommended_action,
        "import_job_age": import_job_age,
        "import_job_definition": import_job_definition,
        "import_job_interval_text": import_job_interval_text,
        "import_job_schedule_text": import_job_schedule_text,
        "import_job_status_from_age": import_job_status_from_age,
        "import_job_status_from_minutes": import_job_status_from_minutes,
        "import_job_updated_ago": import_job_updated_ago,
        "import_status_rows": import_status_rows,
        "mark_import_job_running": mark_import_job_running,
        "operational_incident_review_payload": operational_incident_review_payload,
        "operational_retention_worker": operational_retention_worker,
        "pearson_correlation": pearson_correlation,
        "quality_percent": quality_percent,
        "quality_status_from_age": quality_status_from_age,
        "quality_status_from_percent": quality_status_from_percent,
        "read_operational_status_file": read_operational_status_file,
        "record_import_job": record_import_job,
        "run_elvia_import_background": run_elvia_import_background,
    }
