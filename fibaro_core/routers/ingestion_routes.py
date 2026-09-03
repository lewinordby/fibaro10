"""Ingestion HTTP routes; runtime services are supplied by composition."""

from cleaning_robot_domain import cleaning_provider
from dataclasses import dataclass
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fibaro_core.models import (
    GenericEvent,
    Hc3MeterReading,
    ImportJobRun,
    RoborockSyncRun,
    Sun2ImportRun,
    Sun2SessionImportRun,
)
from fibaro_core.routers.bundle import RouterBundle
from fibaro_core.schemas import (
    DoorEventIn,
    EnergyFibaroIn,
    EventDataIn,
    Hc3MeterReadingIn,
    ImportStatusReportIn,
    LegacyLogIn,
    RoborockIngestIn,
    RoborockTelemetryIn,
    Sun2BedsIngestIn,
    Sun2FinanceSettlementsIngestIn,
    Sun2MembersIngestIn,
    Sun2ProductSalesIngestIn,
    Sun2RoomStatsIngestIn,
    Sun2TanningSessionsIngestIn,
)
from fibaro_core.services.presentation import format_short_number
from sqlalchemy import select
from time_formatting import api_local_iso, local_now_naive, normalize_local_naive
from typing import Any, Callable


@dataclass
class Dependencies:
    api_import_job_run_row: Callable[..., Any]
    api_import_status_row: Callable[..., Any]
    api_import_status_rows: Callable[..., Any]
    async_session: Callable[..., Any]
    clear_summary_cache: Callable[..., Any]
    door_event_from_payload: Callable[..., Any]
    generic_from_payload: Callable[..., Any]
    import_job_definition: Callable[..., Any]
    import_status_rows: Callable[..., Any]
    ingest_roborock_robot: Callable[..., Any]
    ingest_roborock_telemetry_robot: Callable[..., Any]
    ingest_sun2_beds: Callable[..., Any]
    ingest_sun2_finance_settlements: Callable[..., Any]
    ingest_sun2_members: Callable[..., Any]
    ingest_sun2_product_sales: Callable[..., Any]
    ingest_sun2_room_stats: Callable[..., Any]
    ingest_sun2_tanning_sessions: Callable[..., Any]
    json_safe_model_payload: Callable[..., Any]
    light_from_payload: Callable[..., Any]
    light_ntfy_payload: Callable[..., Any]
    light_sample_from_payload: Callable[..., Any]
    met_weather_cached: Callable[..., Any]
    payload_weather_symbol: Callable[..., Any]
    payload_weather_text: Callable[..., Any]
    record_import_job: Callable[..., Any]
    save_record: Callable[..., Any]
    save_yr_sample_for_payload: Callable[..., Any]
    schedule_sun2_axis_snapshot_link: Callable[..., Any]
    sun2_duplicate_session_id_payload: Callable[..., Any]
    upsert_door_event_status: Callable[..., Any]
    upsert_energy_fibaro_sample: Callable[..., Any]
    upsert_kjeller_measurement_sample: Callable[..., Any]
    vent_from_payload: Callable[..., Any]
    vent_sample_from_payload: Callable[..., Any]
    ventilation_ntfy_payload: Callable[..., Any]


def create_router(dependencies: Dependencies) -> RouterBundle:
    router = APIRouter()


    @router.post("/log")
    async def legacy_log_data(data: LegacyLogIn):
        save_record = dependencies.save_record
        record = GenericEvent(
            timestamp=data.timestamp,
            system="legacy",
            event_type="legacy_log",
            source=data.source,
            value=data.temperature,
            extra={"temperature": data.temperature, "humidity": data.humidity},
        )
        event_id = await save_record(record)
        return {"status": "ok", "id": event_id, "table": "event_data"}

    @router.post("/api/hc3/measurements/log")
    async def hc3_meter_reading_log(data: Hc3MeterReadingIn):
        async_session = dependencies.async_session
        json_safe_model_payload = dependencies.json_safe_model_payload
        record_import_job = dependencies.record_import_job
        upsert_kjeller_measurement_sample = dependencies.upsert_kjeller_measurement_sample
        timestamp = normalize_local_naive(data.ts) or local_now_naive()
        reading = Hc3MeterReading(
            timestamp=timestamp,
            kilde=data.kilde,
            status=data.status,
            fibaroid=data.fibaroid,
            verdi1=data.verdi1,
            verdi2=data.verdi2,
            forklaring=data.forklaring,
            source=data.source or "HC3",
            raw=json_safe_model_payload(data),
        )
        async with async_session() as session:
            session.add(reading)
            await session.flush()
            kjeller_sample_id = await upsert_kjeller_measurement_sample(
                session,
                timestamp,
                data.fibaroid,
                data.verdi1,
                data.source or "HC3",
            )
            await record_import_job(
                session,
                "hc3_meter_readings",
                source=data.source or "HC3",
                records_imported=1,
                records_total=1,
                message=f"{data.status} {data.kilde} {data.verdi1:g}",
                raw={
                    "id": reading.id,
                    "fibaroid": data.fibaroid,
                    "kilde": data.kilde,
                    "status": data.status,
                    "kjeller_sample_id": kjeller_sample_id,
                },
            )
            await session.commit()
            return {"status": "ok", "id": reading.id, "table": "hc3_meter_readings", "kjeller_sample_id": kjeller_sample_id}

    @router.post("/events")
    async def log_event(data: EventDataIn):
        async_session = dependencies.async_session
        generic_from_payload = dependencies.generic_from_payload
        light_from_payload = dependencies.light_from_payload
        light_ntfy_payload = dependencies.light_ntfy_payload
        light_sample_from_payload = dependencies.light_sample_from_payload
        met_weather_cached = dependencies.met_weather_cached
        payload_weather_symbol = dependencies.payload_weather_symbol
        payload_weather_text = dependencies.payload_weather_text
        record_import_job = dependencies.record_import_job
        save_record = dependencies.save_record
        save_yr_sample_for_payload = dependencies.save_yr_sample_for_payload
        vent_from_payload = dependencies.vent_from_payload
        vent_sample_from_payload = dependencies.vent_sample_from_payload
        ventilation_ntfy_payload = dependencies.ventilation_ntfy_payload
        system = (data.system or "").lower()
        if system in {"utelys", "ute_lys", "lys"}:
            if data.event_type in {"sample", "sample_5min", "learning_sample"}:
                met_weather = None
                if not payload_weather_symbol(data) and not payload_weather_text(data):
                    met_weather = await met_weather_cached()
                yr_sample_id = await save_yr_sample_for_payload(data, met_weather)
                event_id = await save_record(light_sample_from_payload(data, met_weather))
                async with async_session() as session:
                    await record_import_job(
                        session,
                        "hc3_light_5min",
                        source=data.source or "HC3",
                        records_imported=1,
                        records_total=1,
                        message=f"Lux {data.lux:.0f}" if data.lux is not None else "5-minutters sample mottatt",
                        raw={"event_id": event_id, "yr_sample_id": yr_sample_id},
                    )
                    await session.commit()
                return {"status": "ok", "id": event_id, "table": "utelys_samples", "yr_sample_id": yr_sample_id}
            event = light_from_payload(data)
            notification = light_ntfy_payload(event)
            event_id = await save_record(event, notification=notification)
            return {
                "status": "ok",
                "id": event_id,
                "table": "utelys_events",
                "ntfy_queued": notification is not None,
            }
        if system in {"ventilasjon", "ventilation", "vent"}:
            if data.event_type in {"sample", "sample_5min", "sample_15min", "learning_sample"}:
                yr_sample_id = await save_yr_sample_for_payload(data)
                event_id = await save_record(vent_sample_from_payload(data))
                async with async_session() as session:
                    await record_import_job(
                        session,
                        "hc3_ventilation_5min",
                        source=data.source or "HC3",
                        records_imported=1,
                        records_total=1,
                        message=f"Modus {data.mode}" if data.mode else "5-minutters sample mottatt",
                        raw={"event_id": event_id, "yr_sample_id": yr_sample_id},
                    )
                    await session.commit()
                return {"status": "ok", "id": event_id, "table": "ventilasjon_samples", "yr_sample_id": yr_sample_id}
            event = vent_from_payload(data)
            notification = ventilation_ntfy_payload(event)
            event_id = await save_record(event, notification=notification)
            return {
                "status": "ok",
                "id": event_id,
                "table": "ventilasjon_events",
                "ntfy_queued": notification is not None,
            }
        event_id = await save_record(generic_from_payload(data))
        return {"status": "ok", "id": event_id, "table": "event_data"}

    @router.post("/api/hc3/door-events")
    async def api_hc3_door_event(data: DoorEventIn):
        async_session = dependencies.async_session
        door_event_from_payload = dependencies.door_event_from_payload
        record_import_job = dependencies.record_import_job
        upsert_door_event_status = dependencies.upsert_door_event_status
        row = door_event_from_payload(data)
        async with async_session() as session:
            session.add(row)
            await session.flush()
            await upsert_door_event_status(session, row)
            await record_import_job(
                session,
                "hc3_door_events",
                source=data.source or "HC3",
                records_imported=1,
                records_total=1,
                message=f"{row.device_name or row.device_key or row.device_id or 'Dør'} {row.action}",
                raw={
                    "id": row.id,
                    "device_id": row.device_id,
                    "device_key": row.device_key,
                    "action": row.action,
                    "state": row.state,
                    "raw_value": row.raw_value,
                },
            )
            await session.commit()
            await session.refresh(row)
        return {"status": "ok", "id": row.id, "table": "door_events", "action": row.action, "state": row.state}

    @router.post("/api/import-status/report")
    async def import_status_report(data: ImportStatusReportIn):
        async_session = dependencies.async_session
        import_job_definition = dependencies.import_job_definition
        record_import_job = dependencies.record_import_job
        definition = import_job_definition(data.job_name)
        ok = data.ok if data.ok is not None else (data.status not in {"bad", "failed", "error"})
        finished_at = data.finished_at or local_now_naive()
        async with async_session() as session:
            row = await record_import_job(
                session,
                data.job_name,
                ok=bool(ok),
                title=data.title or definition["title"],
                category=data.category or definition["category"],
                source=data.source or definition.get("source"),
                started_at=data.started_at,
                finished_at=finished_at,
                next_expected_at=data.next_expected_at,
                expected_interval_minutes=data.expected_interval_minutes,
                warning_after_minutes=data.warning_after_minutes,
                records_imported=data.records_imported,
                records_total=data.records_total,
                duration_seconds=data.duration_seconds,
                message=data.message,
                raw=data.raw,
            )
            await session.commit()
            await session.refresh(row)
        return {"status": "ok", "job_name": row.job_name, "job_status": row.status, "last_success_at": api_local_iso(row.last_success_at)}

    @router.get("/api/import-status/json")
    async def import_status_json():
        api_import_status_rows = dependencies.api_import_status_rows
        async_session = dependencies.async_session
        import_status_rows = dependencies.import_status_rows
        async with async_session() as session:
            rows = await import_status_rows(session)
        return {"rows": api_import_status_rows(rows)}

    @router.get("/api/import-status/{job_name}")
    async def import_status_detail(job_name: str):
        from fibaro_core.services.source_evidence import source_data_evidence
        api_import_job_run_row = dependencies.api_import_job_run_row
        api_import_status_row = dependencies.api_import_status_row
        async_session = dependencies.async_session
        import_status_rows = dependencies.import_status_rows
        async with async_session() as session:
            rows = await import_status_rows(session)
            row = next((item for item in rows if item.get("job_name") == job_name), None)
            if not row:
                raise HTTPException(status_code=404, detail="Datakilde ikke funnet")
            evidence = await source_data_evidence(session, job_name)
            runs = (
                await session.execute(
                    select(ImportJobRun)
                    .where(ImportJobRun.job_name == job_name)
                    .order_by(ImportJobRun.finished_at.desc().nullslast(), ImportJobRun.id.desc())
                    .limit(50)
                )
            ).scalars().all()
        api_row = api_import_status_row(row)
        total_runs = len(runs)
        ok_runs = sum(1 for run in runs if run.ok is True)
        failed_runs = sum(1 for run in runs if run.ok is False)
        return {
            "source": api_row,
            "evidence": evidence,
            "runs": [api_import_job_run_row(run) for run in runs],
            "summary": {
                "runs": total_runs,
                "ok": ok_runs,
                "failed": failed_runs,
                "unknown": total_runs - ok_runs - failed_runs,
            },
        }

    @router.post("/api/renhold/ingest")
    async def roborock_ingest(data: RoborockIngestIn):
        async_session = dependencies.async_session
        ingest_roborock_robot = dependencies.ingest_roborock_robot
        record_import_job = dependencies.record_import_job
        batch_time = normalize_local_naive(data.timestamp) or local_now_naive()
        batch_provider = cleaning_provider(
            next(
                (
                    robot.get("provider") if isinstance(robot, dict) else getattr(robot, "provider", None)
                    for robot in data.robots
                    if (robot.get("provider") if isinstance(robot, dict) else getattr(robot, "provider", None))
                ),
                None,
            ),
            data.source,
        )
        import_job_name = "dreame_sync" if batch_provider == "dreame" else "roborock_sync"
        results = []
        async with async_session() as session:
            session.add(
                RoborockSyncRun(
                    timestamp=batch_time,
                    collector_id=data.collector_id,
                    source=data.source,
                    ok=data.ok,
                    robots_count=len(data.robots),
                    message=data.message,
                    raw={"extra": data.extra},
                )
            )
            for robot in data.robots:
                results.append(await ingest_roborock_robot(session, robot, batch_time, data.source))
            await record_import_job(
                session,
                import_job_name,
                ok=data.ok,
                source=data.source,
                records_imported=len(data.robots),
                records_total=len(data.robots),
                message=data.message or f"{len(data.robots)} roboter synkronisert",
                raw={"collector_id": data.collector_id, "provider": batch_provider, "extra": data.extra},
            )
            await session.commit()
        return {"status": "ok", "robots": results}

    @router.post("/api/renhold/telemetry/ingest")
    async def roborock_telemetry_ingest(data: RoborockTelemetryIn):
        async_session = dependencies.async_session
        ingest_roborock_telemetry_robot = dependencies.ingest_roborock_telemetry_robot
        batch_time = normalize_local_naive(data.timestamp) or local_now_naive()
        results = []
        async with async_session() as session:
            for robot in data.robots:
                results.append(await ingest_roborock_telemetry_robot(session, robot, batch_time, data.source))
            await session.commit()
        return {
            "status": "ok" if data.ok else "partial",
            "robots": results,
            "events": sum(int(item.get("events") or 0) for item in results),
        }

    @router.post("/api/sun2/room-stats/ingest")
    async def sun2_room_stats_ingest(data: Sun2RoomStatsIngestIn):
        async_session = dependencies.async_session
        clear_summary_cache = dependencies.clear_summary_cache
        ingest_sun2_room_stats = dependencies.ingest_sun2_room_stats
        record_import_job = dependencies.record_import_job
        batch_time = data.timestamp or datetime.utcnow()
        async with async_session() as session:
            counts = await ingest_sun2_room_stats(session, data, batch_time)
            session.add(
                Sun2ImportRun(
                    timestamp=batch_time,
                    collector_id=data.collector_id,
                    source=data.source,
                    ok=data.ok,
                    stat_date=data.stat_date,
                    source_file=data.source_file,
                    rows_count=len(data.rows),
                    inserted_count=counts["inserted"],
                    updated_count=counts["updated"],
                    message=data.message,
                    raw={"extra": data.extra},
                )
            )
            await record_import_job(
                session,
                "sun2_room_daily_import",
                ok=data.ok,
                source=data.source,
                records_imported=counts["inserted"] + counts["updated"],
                records_total=len(data.rows),
                message=data.message or f"{len(data.rows)} romrader for {data.stat_date or '-'}",
                raw={"collector_id": data.collector_id, "source_file": data.source_file, "counts": counts},
            )
            await session.commit()
        clear_summary_cache("sun2")
        return {"status": "ok", **counts, "rows": len(data.rows)}

    @router.post("/api/sun2/sessions/ingest")
    async def sun2_sessions_ingest(data: Sun2TanningSessionsIngestIn):
        async_session = dependencies.async_session
        clear_summary_cache = dependencies.clear_summary_cache
        ingest_sun2_tanning_sessions = dependencies.ingest_sun2_tanning_sessions
        record_import_job = dependencies.record_import_job
        schedule_sun2_axis_snapshot_link = dependencies.schedule_sun2_axis_snapshot_link
        sun2_duplicate_session_id_payload = dependencies.sun2_duplicate_session_id_payload
        batch_time = data.timestamp or datetime.utcnow()
        period_first = min((row.started_at for row in data.rows if row.started_at), default=None)
        period_last = max((row.started_at for row in data.rows if row.started_at), default=None)
        duplicate_source_session_ids = sun2_duplicate_session_id_payload(data.rows)
        if duplicate_source_session_ids:
            message = (
                f"Avvist Sun2 session-import: {len(duplicate_source_session_ids)} duplikat "
                f"source_session_id i {data.source_file or 'ukjent fil'}"
            )
            async with async_session() as session:
                session.add(
                    Sun2SessionImportRun(
                        timestamp=batch_time,
                        collector_id=data.collector_id,
                        source=data.source,
                        ok=False,
                        source_file=data.source_file,
                        period_first=period_first,
                        period_last=period_last,
                        rows_count=len(data.rows),
                        inserted_count=0,
                        updated_count=0,
                        skipped_count=len(data.rows),
                        message=message,
                        raw={"extra": data.extra, "duplicate_source_session_ids": duplicate_source_session_ids},
                    )
                )
                await record_import_job(
                    session,
                    "sun2_sessions_import",
                    ok=False,
                    source=data.source,
                    records_imported=0,
                    records_total=len(data.rows),
                    message=message,
                    raw={
                        "collector_id": data.collector_id,
                        "source_file": data.source_file,
                        "duplicate_source_session_ids": duplicate_source_session_ids,
                    },
                )
                await session.commit()
            raise HTTPException(status_code=409, detail=message)

        async with async_session() as session:
            counts = await ingest_sun2_tanning_sessions(session, data, batch_time)
            session.add(
                Sun2SessionImportRun(
                    timestamp=batch_time,
                    collector_id=data.collector_id,
                    source=data.source,
                    ok=data.ok,
                    source_file=data.source_file,
                    period_first=period_first,
                    period_last=period_last,
                    rows_count=len(data.rows),
                    inserted_count=counts["inserted"],
                    updated_count=counts["updated"],
                    skipped_count=counts["skipped"],
                    message=data.message,
                    raw={"extra": data.extra},
                )
            )
            await record_import_job(
                session,
                "sun2_sessions_import",
                ok=data.ok,
                source=data.source,
                records_imported=counts["inserted"] + counts["updated"],
                records_total=len(data.rows),
                message=data.message or f"{len(data.rows)} enkelttimer mottatt",
                raw={"collector_id": data.collector_id, "source_file": data.source_file, "counts": counts},
            )
            await session.commit()
        clear_summary_cache("sun2", "sun2_sessions", "sun2_session_options", "sun2_session_database_total")
        if counts["inserted"] or counts["updated"] or counts.get("replaced"):
            schedule_sun2_axis_snapshot_link("sun2_sessions_ingest")
        return {"status": "ok", **counts, "rows": len(data.rows)}

    @router.post("/api/sun2/beds/ingest")
    async def sun2_beds_ingest(data: Sun2BedsIngestIn):
        async_session = dependencies.async_session
        clear_summary_cache = dependencies.clear_summary_cache
        ingest_sun2_beds = dependencies.ingest_sun2_beds
        record_import_job = dependencies.record_import_job
        batch_time = data.timestamp or datetime.utcnow()
        async with async_session() as session:
            counts = await ingest_sun2_beds(session, data, batch_time)
            await record_import_job(
                session,
                "sun2_beds_import",
                ok=data.ok,
                source=data.source,
                records_imported=counts["inserted"] + counts["updated"],
                records_total=len(data.beds),
                message=data.message or f"{len(data.beds)} senger mottatt",
                raw={"collector_id": data.collector_id, "counts": counts},
            )
            await session.commit()
        clear_summary_cache("sun2_session_options")
        return {"status": "ok", **counts, "beds": len(data.beds)}

    @router.post("/api/sun2/members/ingest")
    async def sun2_members_ingest(data: Sun2MembersIngestIn):
        async_session = dependencies.async_session
        clear_summary_cache = dependencies.clear_summary_cache
        ingest_sun2_members = dependencies.ingest_sun2_members
        record_import_job = dependencies.record_import_job
        batch_time = data.timestamp or datetime.utcnow()
        async with async_session() as session:
            counts = await ingest_sun2_members(session, data, batch_time)
            await record_import_job(
                session,
                "sun2_members_import",
                ok=data.ok,
                source=data.source,
                records_imported=counts["inserted"] + counts["updated"],
                records_total=len(data.members),
                message=data.message or f"{len(data.members)} medlemmer mottatt",
                raw={"collector_id": data.collector_id, "counts": counts},
            )
            await session.commit()
        clear_summary_cache("sun2_members")
        return {"status": "ok", **counts, "members": len(data.members)}

    @router.post("/api/sun2/product-sales/ingest")
    async def sun2_product_sales_ingest(data: Sun2ProductSalesIngestIn):
        async_session = dependencies.async_session
        clear_summary_cache = dependencies.clear_summary_cache
        ingest_sun2_product_sales = dependencies.ingest_sun2_product_sales
        record_import_job = dependencies.record_import_job
        batch_time = data.timestamp or datetime.utcnow()
        row_dates = [row.stat_date or (row.sold_at.date() if row.sold_at else None) for row in data.rows]
        row_dates = [item for item in row_dates if item is not None]
        period_first = min(row_dates, default=None)
        period_last = max(row_dates, default=None)
        scope = str((data.extra or {}).get("scope") or "").strip().lower()
        job_name = "sun2_product_sales_monthly_import" if scope == "monthly" else "sun2_product_sales_daily_import"
        async with async_session() as session:
            counts = await ingest_sun2_product_sales(session, data, batch_time)
            await record_import_job(
                session,
                job_name,
                ok=data.ok,
                source=data.source,
                records_imported=counts["inserted"] + counts["updated"],
                records_total=len(data.rows),
                message=data.message or f"{len(data.rows)} produktsalg mottatt",
                raw={
                    "collector_id": data.collector_id,
                    "source_file": data.source_file,
                    "scope": scope or "daily",
                    "period_first": period_first.isoformat() if period_first else None,
                    "period_last": period_last.isoformat() if period_last else None,
                    "counts": counts,
                },
            )
            await session.commit()
        clear_summary_cache("sun2", "sun2_product_sales")
        return {"status": "ok", **counts, "rows": len(data.rows)}

    @router.post("/api/sun2/finance-settlements/ingest")
    async def sun2_finance_settlements_ingest(data: Sun2FinanceSettlementsIngestIn):
        async_session = dependencies.async_session
        clear_summary_cache = dependencies.clear_summary_cache
        ingest_sun2_finance_settlements = dependencies.ingest_sun2_finance_settlements
        record_import_job = dependencies.record_import_job
        batch_time = data.timestamp or datetime.utcnow()
        async with async_session() as session:
            counts = await ingest_sun2_finance_settlements(session, data, batch_time)
            await record_import_job(
                session,
                "sun2_finance_settlement_monthly_import",
                ok=data.ok,
                source=data.source,
                records_imported=counts["inserted"] + counts["updated"],
                records_total=len(data.rows),
                message=data.message or f"{len(data.rows)} Sun2 finansoppgjor mottatt",
                raw={
                    "collector_id": data.collector_id,
                    "source_file": data.source_file,
                    "counts": counts,
                    "extra": data.extra,
                },
            )
            await session.commit()
        clear_summary_cache("sun2", "sun2_finance_settlements")
        return {"status": "ok", **counts, "rows": len(data.rows)}

    @router.post("/api/energi/fibaro")
    async def energy_fibaro_ingest(data: EnergyFibaroIn):
        async_session = dependencies.async_session
        record_import_job = dependencies.record_import_job
        upsert_energy_fibaro_sample = dependencies.upsert_energy_fibaro_sample
        async with async_session() as session:
            record = await upsert_energy_fibaro_sample(session, data)
            await session.flush()
            await record_import_job(
                session,
                "hc3_energy_1min",
                source=data.source or "HC3",
                records_imported=1,
                records_total=1,
                message=f"Inntak {format_short_number(record.inntak_w)} W" if record.inntak_w is not None else "Energisample mottatt",
                raw={"sample_id": record.id, "bucket_start": record.bucket_start.isoformat() if record.bucket_start else None},
            )
            await session.commit()
            await session.refresh(record)
        return {
            "status": "ok",
            "id": record.id,
            "bucket_start": record.bucket_start.isoformat() if record.bucket_start else None,
            "differanse_beregnet_w": record.differanse_beregnet_w,
            "resets": {
                "inntak": record.inntak_reset,
                "varmepumper": record.varmepumper_reset,
                "belysning": record.belysning_reset,
                "massasje": record.massasje_reset,
                "annet": record.annet_reset,
                "avfukter": record.avfukter_reset,
            },
        }

    return RouterBundle(router, {
        "api_hc3_door_event": api_hc3_door_event,
        "energy_fibaro_ingest": energy_fibaro_ingest,
        "hc3_meter_reading_log": hc3_meter_reading_log,
        "import_status_detail": import_status_detail,
        "import_status_json": import_status_json,
        "import_status_report": import_status_report,
        "legacy_log_data": legacy_log_data,
        "log_event": log_event,
        "roborock_ingest": roborock_ingest,
        "roborock_telemetry_ingest": roborock_telemetry_ingest,
        "sun2_beds_ingest": sun2_beds_ingest,
        "sun2_finance_settlements_ingest": sun2_finance_settlements_ingest,
        "sun2_members_ingest": sun2_members_ingest,
        "sun2_product_sales_ingest": sun2_product_sales_ingest,
        "sun2_room_stats_ingest": sun2_room_stats_ingest,
        "sun2_sessions_ingest": sun2_sessions_ingest,
    }, dependencies)
