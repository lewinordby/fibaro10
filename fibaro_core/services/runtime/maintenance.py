"""Maintenance services with explicit process dependencies."""

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from fibaro_core.models import MaintenanceLogEntry
from fibaro_core.models import SiteVisit
from sqlalchemy import and_
from sqlalchemy import or_
from sqlalchemy import select
from sun2_helpers import SUN2_ROOM_OPTIONS
from sun2_helpers import normalize_room_id
from sun2_helpers import sun2_room_label
from time_formatting import LOCAL_TZ
from time_formatting import format_source_datetime_short
from time_formatting import local_now_naive
from time_formatting import normalize_local_naive
from time_formatting import parse_datetime
from typing import Any
from typing import Any, Callable
from typing import Dict
from typing import Optional
from urllib.parse import urlencode
from value_parsing import float_value
import asyncio
import json
import re
import urllib.request


@dataclass
class Dependencies:
    MAINTENANCE_ACTION_OPTIONS: Any
    MAINTENANCE_PRESENCE_OPTIONS: Any
    MAINTENANCE_PRIORITY_OPTIONS: Any
    MAINTENANCE_STATUS_OPTIONS: Any
    MAINTENANCE_TAG_OPTIONS: Any
    MAINTENANCE_TARGET_OPTIONS: Any
    OWNTRACKS_LILLETORGET_WAYPOINTS: Any
    OWNTRACKS_SERVICE_URL: Any
    OWNTRACKS_SITE_VISIT_LOCATION_KEY: Any
    OWNTRACKS_SITE_VISIT_LOCATION_NAME: Any
    OWNTRACKS_VISIT_SYNC_ENABLED: Any
    OWNTRACKS_VISIT_SYNC_INTERVAL_SECONDS: Any
    OWNTRACKS_VISIT_SYNC_LOOKBACK_HOURS: Any
    OWNTRACKS_VISIT_SYNC_TIMEOUT_SECONDS: Any
    SITE_VISIT_ACTIVE_MAX_HOURS: Any
    SITE_VISIT_MAINTENANCE_LINK_MARGIN_MINUTES: Any
    async_session: Callable[..., Any]
    logger: Any
    process_locks: Any
    record_import_job: Callable[..., Any]


def create_service(dependencies: Dependencies):

    def normalize_maintenance_tags(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            items = re.split(r"[,;\n]+", value)
        elif isinstance(value, list):
            items = value
        else:
            items = [value]
        tags: list[str] = []
        seen: set[str] = set()
        for item in items:
            tag = str(item or "").strip()
            if not tag:
                continue
            normalized = tag.casefold()
            if normalized in seen:
                continue
            seen.add(normalized)
            tags.append(tag[:60])
        return tags[:20]

    def maintenance_datetime_value(value: Optional[str]) -> datetime:
        parsed = normalize_local_naive(parse_datetime(value)) if value else None
        return parsed or local_now_naive().replace(second=0, microsecond=0)

    def clean_maintenance_option(value: Any, options: list[str], default: str = "") -> Optional[str]:
        text = str(value or default or "").strip()
        return text if text in options else (default or None)

    def maintenance_room_value(value: Any) -> Optional[str]:
        return normalize_room_id(value)

    def maintenance_target_name(target_type: Optional[str], room_id: Optional[str], value: Any) -> Optional[str]:
        text = str(value or "").strip()
        if text:
            return text[:160]
        if target_type == "Seng" and room_id:
            return f"Seng {sun2_room_label(room_id)}"
        if target_type == "Rom" and room_id:
            return sun2_room_label(room_id)
        return None

    def site_visit_duration_label(seconds: Optional[int], started_at: Optional[datetime] = None, ended_at: Optional[datetime] = None) -> str:
        value = seconds
        if value is None and started_at:
            end_value = ended_at or local_now_naive()
            value = max(0, int((end_value - started_at).total_seconds()))
        if value is None:
            return "-"
        value = max(0, int(value))
        hours = value // 3600
        minutes = (value % 3600) // 60
        if hours:
            return f"{hours}t {minutes:02d}m"
        if minutes:
            return f"{minutes}m"
        return f"{value}s"

    def owntracks_iso_to_local_naive(value: Any) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(LOCAL_TZ).replace(tzinfo=None, microsecond=0)

    def owntracks_visit_request(waypoint_name: str) -> Dict[str, Any]:
        OWNTRACKS_SERVICE_URL = dependencies.OWNTRACKS_SERVICE_URL
        OWNTRACKS_VISIT_SYNC_LOOKBACK_HOURS = dependencies.OWNTRACKS_VISIT_SYNC_LOOKBACK_HOURS
        OWNTRACKS_VISIT_SYNC_TIMEOUT_SECONDS = dependencies.OWNTRACKS_VISIT_SYNC_TIMEOUT_SECONDS
        params = {
            "hours": OWNTRACKS_VISIT_SYNC_LOOKBACK_HOURS,
            "limit": 1000,
            "include_short": "false",
        }
        if waypoint_name:
            params["waypointName"] = waypoint_name
        url = f"{OWNTRACKS_SERVICE_URL}/api/owntracks/visits?{urlencode(params)}"
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=OWNTRACKS_VISIT_SYNC_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))

    async def fetch_owntracks_lilletorget_visits() -> list[Dict[str, Any]]:
        OWNTRACKS_LILLETORGET_WAYPOINTS = dependencies.OWNTRACKS_LILLETORGET_WAYPOINTS
        waypoint_names = OWNTRACKS_LILLETORGET_WAYPOINTS or [""]
        visits_by_key: Dict[str, Dict[str, Any]] = {}
        for waypoint_name in waypoint_names:
            payload = await asyncio.to_thread(owntracks_visit_request, waypoint_name)
            for row in payload.get("visits") or []:
                if not isinstance(row, dict):
                    continue
                key = str(row.get("id") or "").strip()
                if not key:
                    continue
                visits_by_key[key] = row
        return sorted(
            visits_by_key.values(),
            key=lambda row: str(row.get("startedAt") or ""),
            reverse=True,
        )

    def site_visit_status_label(row: SiteVisit) -> str:
        if site_visit_is_stale(row):
            return "Mangler avslutning"
        return "Aktiv" if row.status == "open" else "Avsluttet"

    def site_visit_is_stale(row: SiteVisit, now_value: Optional[datetime] = None) -> bool:
        SITE_VISIT_ACTIVE_MAX_HOURS = dependencies.SITE_VISIT_ACTIVE_MAX_HOURS
        if row.status != "open" or not row.started_at:
            return False
        return row.started_at < (now_value or local_now_naive()) - timedelta(hours=SITE_VISIT_ACTIVE_MAX_HOURS)

    def site_visit_is_current(row: SiteVisit, now_value: Optional[datetime] = None) -> bool:
        return row.status == "open" and not site_visit_is_stale(row, now_value)

    def site_visit_display_duration(row: SiteVisit) -> str:
        if site_visit_is_stale(row):
            return "Ukjent"
        return site_visit_duration_label(row.duration_seconds, row.started_at, row.ended_at)

    def site_visit_confidence_percent(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return round(numeric * 100 if 0 <= numeric <= 1 else numeric, 1)

    def site_visit_label(row: Optional[SiteVisit]) -> Optional[str]:
        if not row:
            return None
        started = format_source_datetime_short(row.started_at) if row.started_at else "-"
        duration = site_visit_display_duration(row)
        return f"{row.location_name} {started} ({duration})"

    def site_visit_row(row: SiteVisit, tasks_count: int = 0) -> Dict[str, Any]:
        path = f"/vedlikehold/besok/{row.id}" if row.id else None
        return {
            "id": row.id,
            "path": path,
            "started_at_url": path,
            "source": row.source,
            "source_visit_id": row.source_visit_id,
            "location_key": row.location_key,
            "location_name": row.location_name,
            "started_at": row.started_at.isoformat(timespec="minutes") if row.started_at else None,
            "ended_at": row.ended_at.isoformat(timespec="minutes") if row.ended_at else None,
            "duration": site_visit_display_duration(row),
            "duration_seconds": row.duration_seconds,
            "status": site_visit_status_label(row),
            "tasks_count": tasks_count,
            "topic": row.topic,
            "username": row.username,
            "device": row.device,
            "confidence": site_visit_confidence_percent(row.confidence),
            "enter_source": row.enter_source,
            "leave_source": row.leave_source,
            "notes": row.notes,
            "last_synced_at": row.last_synced_at.isoformat(timespec="minutes") if row.last_synced_at else None,
            "created_at": row.created_at.isoformat(timespec="minutes") if row.created_at else None,
            "updated_at": row.updated_at.isoformat(timespec="minutes") if row.updated_at else None,
        }

    async def find_site_visit_for_maintenance(
        session,
        performed_at: Optional[datetime],
        explicit_site_visit_id: Optional[int] = None,
    ) -> Optional[SiteVisit]:
        OWNTRACKS_SITE_VISIT_LOCATION_KEY = dependencies.OWNTRACKS_SITE_VISIT_LOCATION_KEY
        OWNTRACKS_VISIT_SYNC_LOOKBACK_HOURS = dependencies.OWNTRACKS_VISIT_SYNC_LOOKBACK_HOURS
        SITE_VISIT_MAINTENANCE_LINK_MARGIN_MINUTES = dependencies.SITE_VISIT_MAINTENANCE_LINK_MARGIN_MINUTES
        if explicit_site_visit_id is not None:
            try:
                visit_id = int(explicit_site_visit_id)
            except (TypeError, ValueError):
                visit_id = 0
            if visit_id <= 0:
                return None
            return await session.get(SiteVisit, visit_id)
        if not performed_at:
            return None
        margin = timedelta(minutes=SITE_VISIT_MAINTENANCE_LINK_MARGIN_MINUTES)
        open_visit_max_age = timedelta(hours=max(24, OWNTRACKS_VISIT_SYNC_LOOKBACK_HOURS))
        stmt = (
            select(SiteVisit)
            .where(SiteVisit.location_key == OWNTRACKS_SITE_VISIT_LOCATION_KEY)
            .where(SiteVisit.started_at <= performed_at + margin)
            .where(
                or_(
                    and_(SiteVisit.ended_at.isnot(None), SiteVisit.ended_at >= performed_at - margin),
                    and_(SiteVisit.ended_at.is_(None), SiteVisit.started_at >= performed_at - open_visit_max_age),
                )
            )
            .order_by(SiteVisit.started_at.desc(), SiteVisit.id.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalars().first()

    async def link_unassigned_maintenance_logs_to_site_visits(session, since: Optional[datetime] = None, limit: int = 500) -> int:
        stmt = (
            select(MaintenanceLogEntry)
            .where(MaintenanceLogEntry.site_visit_id.is_(None))
            .where(MaintenanceLogEntry.performed_at.isnot(None))
            .order_by(MaintenanceLogEntry.performed_at.desc(), MaintenanceLogEntry.id.desc())
            .limit(limit)
        )
        if since:
            stmt = stmt.where(MaintenanceLogEntry.performed_at >= since)
        logs = (await session.execute(stmt)).scalars().all()
        linked = 0
        for log_row in logs:
            visit = await find_site_visit_for_maintenance(session, log_row.performed_at)
            if visit:
                log_row.site_visit_id = visit.id
                linked += 1
        return linked

    async def sync_owntracks_site_visits_once(reason: str = "manual") -> Dict[str, Any]:
        OWNTRACKS_LILLETORGET_WAYPOINTS = dependencies.OWNTRACKS_LILLETORGET_WAYPOINTS
        OWNTRACKS_SITE_VISIT_LOCATION_KEY = dependencies.OWNTRACKS_SITE_VISIT_LOCATION_KEY
        OWNTRACKS_SITE_VISIT_LOCATION_NAME = dependencies.OWNTRACKS_SITE_VISIT_LOCATION_NAME
        OWNTRACKS_VISIT_SYNC_ENABLED = dependencies.OWNTRACKS_VISIT_SYNC_ENABLED
        OWNTRACKS_VISIT_SYNC_LOOKBACK_HOURS = dependencies.OWNTRACKS_VISIT_SYNC_LOOKBACK_HOURS
        async_session = dependencies.async_session
        record_import_job = dependencies.record_import_job
        if not OWNTRACKS_VISIT_SYNC_ENABLED:
            return {"status": "disabled", "message": "OwnTracks-besøkssynk er deaktivert."}
        job_started_at = local_now_naive().replace(microsecond=0)
        visits = await fetch_owntracks_lilletorget_visits()
        now_value = local_now_naive().replace(microsecond=0)
        created = 0
        updated = 0
        skipped = 0
        async with async_session() as session:
            for raw in visits:
                source_visit_id = str(raw.get("id") or "").strip()
                visit_started_at = owntracks_iso_to_local_naive(raw.get("startedAt"))
                if not source_visit_id or not visit_started_at:
                    skipped += 1
                    continue
                existing = (
                    await session.execute(
                        select(SiteVisit)
                        .where(SiteVisit.source == "owntracks")
                        .where(SiteVisit.source_visit_id == source_visit_id)
                        .limit(1)
                    )
                ).scalars().first()
                if existing:
                    row = existing
                    updated += 1
                else:
                    row = SiteVisit(source="owntracks", source_visit_id=source_visit_id, created_at=now_value)
                    session.add(row)
                    created += 1
                row.location_key = OWNTRACKS_SITE_VISIT_LOCATION_KEY
                row.location_name = OWNTRACKS_SITE_VISIT_LOCATION_NAME
                row.topic = str(raw.get("topic") or "").strip() or None
                row.username = str(raw.get("username") or "").strip() or None
                row.device = str(raw.get("device") or "").strip() or None
                row.started_at = visit_started_at
                row.ended_at = owntracks_iso_to_local_naive(raw.get("endedAt"))
                row.duration_seconds = int(raw.get("durationSeconds")) if raw.get("durationSeconds") is not None else None
                row.status = "open" if str(raw.get("status") or "").strip().lower() == "open" else "closed"
                row.confidence = float_value(raw.get("confidence"))
                row.enter_source = str(raw.get("enterSource") or "").strip() or None
                row.leave_source = str(raw.get("leaveSource") or "").strip() or None
                row.raw = raw
                row.last_synced_at = now_value
                row.updated_at = now_value
            since = now_value - timedelta(hours=OWNTRACKS_VISIT_SYNC_LOOKBACK_HOURS + 24)
            linked = await link_unassigned_maintenance_logs_to_site_visits(session, since=since)
            await record_import_job(
                session,
                "owntracks_site_visits",
                ok=True,
                started_at=job_started_at,
                finished_at=now_value,
                records_imported=created + updated,
                records_total=len(visits),
                duration_seconds=max(0.0, (now_value - job_started_at).total_seconds()),
                message=f"Hentet {len(visits)} Lilletorget-besøk fra OwnTracks. Opprettet {created}, oppdatert {updated}, koblet {linked} vedlikehold.",
                raw={
                    "reason": reason,
                    "created": created,
                    "updated": updated,
                    "skipped": skipped,
                    "maintenanceLinked": linked,
                    "waypoints": OWNTRACKS_LILLETORGET_WAYPOINTS,
                },
            )
            await session.commit()
        return {
            "status": "ok",
            "reason": reason,
            "fetched": len(visits),
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "maintenanceLinked": linked,
            "syncedAt": now_value.isoformat(timespec="seconds"),
            "waypoints": OWNTRACKS_LILLETORGET_WAYPOINTS,
        }

    async def record_owntracks_site_visit_sync_failure(message: str) -> None:
        OWNTRACKS_LILLETORGET_WAYPOINTS = dependencies.OWNTRACKS_LILLETORGET_WAYPOINTS
        async_session = dependencies.async_session
        logger = dependencies.logger
        record_import_job = dependencies.record_import_job
        try:
            now_value = local_now_naive().replace(microsecond=0)
            async with async_session() as session:
                await record_import_job(
                    session,
                    "owntracks_site_visits",
                    ok=False,
                    started_at=now_value,
                    finished_at=now_value,
                    records_imported=0,
                    records_total=0,
                    duration_seconds=0,
                    message=message[:1000],
                    raw={
                        "error": message[:4000],
                        "waypoints": OWNTRACKS_LILLETORGET_WAYPOINTS,
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.warning("Could not record OwnTracks site visit sync failure: %s", exc, exc_info=True)

    async def run_owntracks_site_visit_sync(reason: str = "manual") -> Dict[str, Any]:
        process_locks = dependencies.process_locks
        if process_locks.owntracks_visit_sync_lock is None:
            process_locks.owntracks_visit_sync_lock = asyncio.Lock()
        if process_locks.owntracks_visit_sync_lock.locked():
            return {"status": "busy", "message": "OwnTracks-besøkssynk kjører allerede."}
        async with process_locks.owntracks_visit_sync_lock:
            try:
                return await sync_owntracks_site_visits_once(reason=reason)
            except Exception as exc:
                await record_owntracks_site_visit_sync_failure(str(exc))
                raise

    async def owntracks_site_visit_sync_worker() -> None:
        OWNTRACKS_VISIT_SYNC_INTERVAL_SECONDS = dependencies.OWNTRACKS_VISIT_SYNC_INTERVAL_SECONDS
        logger = dependencies.logger
        await asyncio.sleep(10)
        while True:
            try:
                result = await run_owntracks_site_visit_sync(reason="worker")
                if result.get("status") == "ok":
                    logger.info("OwnTracks site visit sync: %s", result)
            except Exception as exc:
                logger.warning("OwnTracks site visit sync failed: %s", exc, exc_info=True)
            await asyncio.sleep(OWNTRACKS_VISIT_SYNC_INTERVAL_SECONDS)

    def maintenance_log_row(row: MaintenanceLogEntry, site_visit: Optional[SiteVisit] = None) -> Dict[str, Any]:
        tags = normalize_maintenance_tags(row.tags)
        return {
            "id": row.id,
            "site_visit_id": row.site_visit_id,
            "site_visit": site_visit_label(site_visit),
            "performed_at": row.performed_at.isoformat(timespec="minutes") if row.performed_at else None,
            "performed_by": row.performed_by,
            "presence_type": row.presence_type,
            "target_type": row.target_type,
            "room_id": row.room_id,
            "target_name": row.target_name,
            "action_type": row.action_type,
            "priority": row.priority,
            "summary": row.summary,
            "tags": ", ".join(tags),
            "status": row.status,
            "duration_minutes": row.duration_minutes,
            "follow_up_needed": bool(row.follow_up_needed),
            "follow_up_text": row.follow_up_text,
            "created_at": row.created_at.isoformat(timespec="minutes") if row.created_at else None,
            "updated_at": row.updated_at.isoformat(timespec="minutes") if row.updated_at else None,
        }

    def api_maintenance_log_edit(default_performed_at: datetime) -> Dict[str, Any]:
        MAINTENANCE_ACTION_OPTIONS = dependencies.MAINTENANCE_ACTION_OPTIONS
        MAINTENANCE_PRESENCE_OPTIONS = dependencies.MAINTENANCE_PRESENCE_OPTIONS
        MAINTENANCE_PRIORITY_OPTIONS = dependencies.MAINTENANCE_PRIORITY_OPTIONS
        MAINTENANCE_STATUS_OPTIONS = dependencies.MAINTENANCE_STATUS_OPTIONS
        MAINTENANCE_TAG_OPTIONS = dependencies.MAINTENANCE_TAG_OPTIONS
        MAINTENANCE_TARGET_OPTIONS = dependencies.MAINTENANCE_TARGET_OPTIONS
        tag_options = [{"label": label, "value": label} for label in MAINTENANCE_TAG_OPTIONS]
        status_options = [{"label": label, "value": label} for label in MAINTENANCE_STATUS_OPTIONS]
        presence_options = [{"label": label, "value": label} for label in MAINTENANCE_PRESENCE_OPTIONS]
        target_options = [{"label": label, "value": label} for label in MAINTENANCE_TARGET_OPTIONS]
        action_options = [{"label": label, "value": label} for label in MAINTENANCE_ACTION_OPTIONS]
        priority_options = [{"label": label, "value": label} for label in MAINTENANCE_PRIORITY_OPTIONS]
        room_options = [{"label": option["label"], "value": option["value"]} for option in SUN2_ROOM_OPTIONS]
        fields = [
            {
                "key": "performed_at",
                "label": "Tidspunkt",
                "type": "datetime",
                "required": True,
                "defaultValue": default_performed_at.isoformat(timespec="minutes"),
                "section": "meta",
            },
            {"key": "performed_by", "label": "Utført av", "type": "text", "placeholder": "Navn eller bruker", "section": "meta"},
            {"key": "site_visit_id", "label": "Besøks-ID", "type": "number", "placeholder": "Fylles automatisk fra OwnTracks", "section": "meta"},
            {"key": "presence_type", "label": "Type", "type": "select", "options": presence_options, "defaultValue": "Tilstede Sun2", "section": "meta"},
            {"key": "target_type", "label": "Objekt", "type": "select", "options": target_options, "defaultValue": "Seng", "section": "meta"},
            {"key": "room_id", "label": "Seng / rom", "type": "select", "options": room_options, "placeholder": "Velg rom ved seng/rom", "section": "meta"},
            {"key": "target_name", "label": "Objektnavn", "type": "text", "placeholder": "Blankt gir f.eks. Seng Rom 12", "section": "meta"},
            {"key": "action_type", "label": "Tiltak", "type": "select", "options": action_options, "defaultValue": "Kontroll", "section": "meta"},
            {"key": "priority", "label": "Prioritet", "type": "select", "options": priority_options, "defaultValue": "Normal", "section": "meta"},
            {"key": "status", "label": "Status", "type": "select", "options": status_options, "defaultValue": "Utført", "section": "meta"},
            {"key": "duration_minutes", "label": "Varighet min", "type": "number", "section": "meta"},
            {"key": "summary", "label": "Hva ble gjort", "type": "textarea", "required": True, "rows": 8, "section": "main"},
            {"key": "tags", "label": "Tagger", "type": "tags", "options": tag_options, "placeholder": "Velg eller skriv tagger", "section": "main"},
            {"key": "follow_up_needed", "label": "Må følges opp", "type": "boolean", "section": "main"},
            {"key": "follow_up_text", "label": "Oppfølging", "type": "textarea", "rows": 4, "section": "main"},
        ]
        return {
            "kind": "maintenance-log",
            "title": "vedlikeholdslogg",
            "layout": "split",
            "width": 980,
            "idField": "id",
            "endpoint": "/api/maintenance/logs/{id}",
            "method": "PATCH",
            "createEndpoint": "/api/maintenance/logs",
            "fields": fields,
        }

    return {
        "api_maintenance_log_edit": api_maintenance_log_edit,
        "clean_maintenance_option": clean_maintenance_option,
        "fetch_owntracks_lilletorget_visits": fetch_owntracks_lilletorget_visits,
        "find_site_visit_for_maintenance": find_site_visit_for_maintenance,
        "link_unassigned_maintenance_logs_to_site_visits": link_unassigned_maintenance_logs_to_site_visits,
        "maintenance_datetime_value": maintenance_datetime_value,
        "maintenance_log_row": maintenance_log_row,
        "maintenance_room_value": maintenance_room_value,
        "maintenance_target_name": maintenance_target_name,
        "normalize_maintenance_tags": normalize_maintenance_tags,
        "owntracks_iso_to_local_naive": owntracks_iso_to_local_naive,
        "owntracks_site_visit_sync_worker": owntracks_site_visit_sync_worker,
        "owntracks_visit_request": owntracks_visit_request,
        "record_owntracks_site_visit_sync_failure": record_owntracks_site_visit_sync_failure,
        "run_owntracks_site_visit_sync": run_owntracks_site_visit_sync,
        "site_visit_confidence_percent": site_visit_confidence_percent,
        "site_visit_display_duration": site_visit_display_duration,
        "site_visit_duration_label": site_visit_duration_label,
        "site_visit_is_current": site_visit_is_current,
        "site_visit_is_stale": site_visit_is_stale,
        "site_visit_label": site_visit_label,
        "site_visit_row": site_visit_row,
        "site_visit_status_label": site_visit_status_label,
        "sync_owntracks_site_visits_once": sync_owntracks_site_visits_once,
    }
