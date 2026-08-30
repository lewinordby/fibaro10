"""Maintenance HTTP routes; runtime services are supplied by composition."""

from dataclasses import dataclass
from fastapi import APIRouter, HTTPException, Query, Request
from fibaro_core.models import MaintenanceLogEntry, SiteVisit
from fibaro_core.routers.bundle import RouterBundle
from fibaro_core.schemas import MaintenanceLogInput, MaintenanceSiteVisitInput
from fibaro_core.services.presentation import api_card, api_table, format_short_number
from sqlalchemy import func, select
from time_formatting import format_source_datetime_short, local_now_naive
from typing import Any, Callable
import urllib.request


@dataclass
class Dependencies:
    MAINTENANCE_ACTION_OPTIONS: Any
    MAINTENANCE_PRIORITY_OPTIONS: Any
    MAINTENANCE_STATUS_OPTIONS: Any
    MAINTENANCE_TARGET_OPTIONS: Any
    OWNTRACKS_SITE_VISIT_LOCATION_KEY: Any
    api_maintenance_log_edit: Callable[..., Any]
    async_session: Callable[..., Any]
    clean_maintenance_option: Callable[..., Any]
    find_site_visit_for_maintenance: Callable[..., Any]
    logger: Any
    maintenance_datetime_value: Callable[..., Any]
    maintenance_log_row: Callable[..., Any]
    maintenance_room_value: Callable[..., Any]
    maintenance_target_name: Callable[..., Any]
    normalize_maintenance_tags: Callable[..., Any]
    require_settings_access: Callable[..., Any]
    run_owntracks_site_visit_sync: Callable[..., Any]
    site_visit_confidence_percent: Callable[..., Any]
    site_visit_display_duration: Callable[..., Any]
    site_visit_is_stale: Callable[..., Any]
    site_visit_label: Callable[..., Any]
    site_visit_row: Callable[..., Any]
    site_visit_status_label: Callable[..., Any]


def create_router(dependencies: Dependencies) -> RouterBundle:
    router = APIRouter()


    @router.post("/api/maintenance/logs")
    async def api_v2_maintenance_log_create(request: Request, data: MaintenanceLogInput):
        MAINTENANCE_ACTION_OPTIONS = dependencies.MAINTENANCE_ACTION_OPTIONS
        MAINTENANCE_PRIORITY_OPTIONS = dependencies.MAINTENANCE_PRIORITY_OPTIONS
        MAINTENANCE_STATUS_OPTIONS = dependencies.MAINTENANCE_STATUS_OPTIONS
        MAINTENANCE_TARGET_OPTIONS = dependencies.MAINTENANCE_TARGET_OPTIONS
        async_session = dependencies.async_session
        clean_maintenance_option = dependencies.clean_maintenance_option
        find_site_visit_for_maintenance = dependencies.find_site_visit_for_maintenance
        maintenance_datetime_value = dependencies.maintenance_datetime_value
        maintenance_room_value = dependencies.maintenance_room_value
        maintenance_target_name = dependencies.maintenance_target_name
        normalize_maintenance_tags = dependencies.normalize_maintenance_tags
        values = data.dict(exclude_unset=True)
        summary = str(values.get("summary") or "").strip()
        if not summary:
            raise HTTPException(status_code=400, detail="Hva ble gjort må fylles ut.")
        now_value = local_now_naive().replace(second=0, microsecond=0)
        status = str(values.get("status") or "Utført").strip() or "Utført"
        if status not in MAINTENANCE_STATUS_OPTIONS:
            status = "Utført"
        target_type = clean_maintenance_option(values.get("target_type"), MAINTENANCE_TARGET_OPTIONS, "Seng")
        room_id = maintenance_room_value(values.get("room_id"))
        target_name = maintenance_target_name(target_type, room_id, values.get("target_name"))
        performed_by = str(values.get("performed_by") or getattr(request.state, "access_key_name", "") or "").strip() or None
        row = MaintenanceLogEntry(
            performed_at=maintenance_datetime_value(values.get("performed_at")),
            performed_by=performed_by,
            presence_type=str(values.get("presence_type") or "Tilstede Sun2").strip() or None,
            target_type=target_type,
            room_id=room_id,
            target_name=target_name,
            action_type=clean_maintenance_option(values.get("action_type"), MAINTENANCE_ACTION_OPTIONS, "Kontroll"),
            priority=clean_maintenance_option(values.get("priority"), MAINTENANCE_PRIORITY_OPTIONS, "Normal"),
            summary=summary,
            tags=normalize_maintenance_tags(values.get("tags")),
            status=status,
            duration_minutes=values.get("duration_minutes"),
            follow_up_needed=bool(values.get("follow_up_needed")),
            follow_up_text=str(values.get("follow_up_text") or "").strip() or None,
            created_by=getattr(request.state, "access_key_name", None),
            updated_by=getattr(request.state, "access_key_name", None),
            created_at=now_value,
            updated_at=now_value,
        )
        async with async_session() as session:
            explicit_site_visit_id = values.get("site_visit_id") if "site_visit_id" in values else None
            visit = await find_site_visit_for_maintenance(session, row.performed_at, explicit_site_visit_id)
            if explicit_site_visit_id and not visit:
                raise HTTPException(status_code=400, detail="Besøket finnes ikke.")
            row.site_visit_id = visit.id if visit else None
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return {"status": "ok", "message": "Vedlikeholdslogg er opprettet.", "id": row.id}

    @router.patch("/api/maintenance/logs/{log_id}")
    async def api_v2_maintenance_log_update(request: Request, log_id: int, data: MaintenanceLogInput):
        MAINTENANCE_ACTION_OPTIONS = dependencies.MAINTENANCE_ACTION_OPTIONS
        MAINTENANCE_PRIORITY_OPTIONS = dependencies.MAINTENANCE_PRIORITY_OPTIONS
        MAINTENANCE_STATUS_OPTIONS = dependencies.MAINTENANCE_STATUS_OPTIONS
        MAINTENANCE_TARGET_OPTIONS = dependencies.MAINTENANCE_TARGET_OPTIONS
        async_session = dependencies.async_session
        clean_maintenance_option = dependencies.clean_maintenance_option
        find_site_visit_for_maintenance = dependencies.find_site_visit_for_maintenance
        maintenance_datetime_value = dependencies.maintenance_datetime_value
        maintenance_room_value = dependencies.maintenance_room_value
        maintenance_target_name = dependencies.maintenance_target_name
        normalize_maintenance_tags = dependencies.normalize_maintenance_tags
        values = data.dict(exclude_unset=True)
        async with async_session() as session:
            row = await session.get(MaintenanceLogEntry, log_id)
            if not row:
                raise HTTPException(status_code=404, detail="Vedlikeholdslogg ikke funnet")
            if "performed_at" in values:
                row.performed_at = maintenance_datetime_value(values.get("performed_at"))
            if "performed_by" in values:
                row.performed_by = str(values.get("performed_by") or "").strip() or None
            if "presence_type" in values:
                row.presence_type = str(values.get("presence_type") or "").strip() or None
            if "target_type" in values:
                row.target_type = clean_maintenance_option(values.get("target_type"), MAINTENANCE_TARGET_OPTIONS, row.target_type or "Generelt")
            if "room_id" in values:
                row.room_id = maintenance_room_value(values.get("room_id"))
            if "target_name" in values:
                row.target_name = maintenance_target_name(row.target_type, row.room_id, values.get("target_name"))
            if "action_type" in values:
                row.action_type = clean_maintenance_option(values.get("action_type"), MAINTENANCE_ACTION_OPTIONS, row.action_type or "Kontroll")
            if "priority" in values:
                row.priority = clean_maintenance_option(values.get("priority"), MAINTENANCE_PRIORITY_OPTIONS, row.priority or "Normal")
            if "summary" in values:
                summary = str(values.get("summary") or "").strip()
                if not summary:
                    raise HTTPException(status_code=400, detail="Hva ble gjort må fylles ut.")
                row.summary = summary
            if "tags" in values:
                row.tags = normalize_maintenance_tags(values.get("tags"))
            if "status" in values:
                status = str(values.get("status") or "Utført").strip() or "Utført"
                row.status = status if status in MAINTENANCE_STATUS_OPTIONS else "Utført"
            if "duration_minutes" in values:
                row.duration_minutes = values.get("duration_minutes")
            if "follow_up_needed" in values:
                row.follow_up_needed = bool(values.get("follow_up_needed"))
            if "follow_up_text" in values:
                row.follow_up_text = str(values.get("follow_up_text") or "").strip() or None
            if "site_visit_id" in values:
                explicit_site_visit_id = values.get("site_visit_id")
                if explicit_site_visit_id in (None, 0):
                    row.site_visit_id = None
                else:
                    visit = await find_site_visit_for_maintenance(session, row.performed_at, explicit_site_visit_id)
                    if not visit:
                        raise HTTPException(status_code=400, detail="Besøket finnes ikke.")
                    row.site_visit_id = visit.id
            elif "performed_at" in values and not row.site_visit_id:
                visit = await find_site_visit_for_maintenance(session, row.performed_at)
                if visit:
                    row.site_visit_id = visit.id
            row.updated_by = getattr(request.state, "access_key_name", None)
            row.updated_at = local_now_naive().replace(second=0, microsecond=0)
            await session.commit()
        return {"status": "ok", "message": "Vedlikeholdslogg er lagret."}

    @router.get("/api/maintenance/site-visits/{visit_id:int}")
    async def api_v2_maintenance_site_visit_detail(visit_id: int):
        OWNTRACKS_SITE_VISIT_LOCATION_KEY = dependencies.OWNTRACKS_SITE_VISIT_LOCATION_KEY
        api_maintenance_log_edit = dependencies.api_maintenance_log_edit
        async_session = dependencies.async_session
        maintenance_log_row = dependencies.maintenance_log_row
        site_visit_confidence_percent = dependencies.site_visit_confidence_percent
        site_visit_display_duration = dependencies.site_visit_display_duration
        site_visit_is_stale = dependencies.site_visit_is_stale
        site_visit_label = dependencies.site_visit_label
        site_visit_row = dependencies.site_visit_row
        site_visit_status_label = dependencies.site_visit_status_label
        async with async_session() as session:
            visit = await session.get(SiteVisit, visit_id)
            if not visit or visit.location_key != OWNTRACKS_SITE_VISIT_LOCATION_KEY:
                raise HTTPException(status_code=404, detail="Besok ikke funnet")
            task_rows = (
                await session.execute(
                    select(MaintenanceLogEntry)
                    .where(MaintenanceLogEntry.site_visit_id == visit.id)
                    .order_by(MaintenanceLogEntry.performed_at.desc(), MaintenanceLogEntry.id.desc())
                )
            ).scalars().all()
        task_edit = api_maintenance_log_edit((visit.started_at or local_now_naive()).replace(second=0, microsecond=0))
        for field in task_edit.get("fields", []):
            if field.get("key") == "site_visit_id":
                field["defaultValue"] = visit.id
            elif field.get("key") == "presence_type":
                field["defaultValue"] = "Tilstede Sun2"
        visit_row = site_visit_row(visit, len(task_rows))
        task_api_rows = [maintenance_log_row(row, visit) for row in task_rows]
        title_time = format_source_datetime_short(visit.started_at) if visit.started_at else f"#{visit.id}"
        confidence_percent = site_visit_confidence_percent(visit.confidence)
        confidence_label = f"{format_short_number(confidence_percent, 1)} %" if confidence_percent is not None else "-"
        end_label = (
            format_source_datetime_short(visit.ended_at)
            if visit.ended_at
            else "Mangler avslutning" if site_visit_is_stale(visit) else "Pågående"
        )
        return {
            "status": "ok",
            "title": f"Lilletorget-besøk {title_time}",
            "subtitle": site_visit_label(visit) or "OwnTracks-besøk",
            "visit": visit_row,
            "cards": [
                api_card("Start", format_source_datetime_short(visit.started_at) if visit.started_at else "-", "", "Kom inn", "status"),
                api_card("Slutt", end_label, "", "Dro ut", "status"),
                api_card("Varighet", site_visit_display_duration(visit), "", site_visit_status_label(visit), "status"),
                api_card("Oppgaver", len(task_rows), "stk", "Koblet til dette besøket", "status"),
            ],
            "fields": [
                {"label": "Sted", "value": visit.location_name},
                {"label": "Status", "value": site_visit_status_label(visit)},
                {"label": "Bruker", "value": visit.username},
                {"label": "Enhet", "value": visit.device},
                {"label": "Sikkerhet", "value": confidence_label},
                {"label": "Sist synket", "value": visit.last_synced_at.isoformat(timespec="minutes") if visit.last_synced_at else None},
            ],
            "taskTable": api_table(
                "Oppgaver",
                [
                    "performed_at",
                    "target_type",
                    "target_name",
                    "action_type",
                    "priority",
                    "status",
                    "summary",
                    "tags",
                    "follow_up_needed",
                    "follow_up_text",
                ],
                task_api_rows,
                edit=task_edit,
            ),
            "taskEdit": task_edit,
            "visitEdit": {
                "kind": "site-visit-note",
                "title": "besøksnotat",
                "idField": "id",
                "endpoint": "/api/maintenance/site-visits/{id}",
                "method": "PATCH",
                "fields": [
                    {"key": "notes", "label": "Notat for besøket", "type": "textarea", "rows": 8},
                ],
            },
            "raw": visit.raw or {},
        }

    @router.patch("/api/maintenance/site-visits/{visit_id:int}")
    async def api_v2_maintenance_site_visit_update(visit_id: int, data: MaintenanceSiteVisitInput):
        OWNTRACKS_SITE_VISIT_LOCATION_KEY = dependencies.OWNTRACKS_SITE_VISIT_LOCATION_KEY
        async_session = dependencies.async_session
        values = data.dict(exclude_unset=True)
        async with async_session() as session:
            visit = await session.get(SiteVisit, visit_id)
            if not visit or visit.location_key != OWNTRACKS_SITE_VISIT_LOCATION_KEY:
                raise HTTPException(status_code=404, detail="Besok ikke funnet")
            if "notes" in values:
                visit.notes = str(values.get("notes") or "").strip() or None
            visit.updated_at = local_now_naive().replace(second=0, microsecond=0)
            await session.commit()
        return {"status": "ok", "message": "Besøksnotat er lagret."}

    @router.get("/api/maintenance/site-visits")
    async def api_v2_maintenance_site_visits(limit: int = Query(100, ge=1, le=1000)):
        OWNTRACKS_SITE_VISIT_LOCATION_KEY = dependencies.OWNTRACKS_SITE_VISIT_LOCATION_KEY
        async_session = dependencies.async_session
        site_visit_row = dependencies.site_visit_row
        async with async_session() as session:
            visits = (
                await session.execute(
                    select(SiteVisit)
                    .where(SiteVisit.location_key == OWNTRACKS_SITE_VISIT_LOCATION_KEY)
                    .order_by(SiteVisit.started_at.desc(), SiteVisit.id.desc())
                    .limit(limit)
                )
            ).scalars().all()
            counts = {
                int(row.visit_id): int(row.tasks_count)
                for row in (
                    await session.execute(
                        select(MaintenanceLogEntry.site_visit_id.label("visit_id"), func.count(MaintenanceLogEntry.id).label("tasks_count"))
                        .where(MaintenanceLogEntry.site_visit_id.isnot(None))
                        .group_by(MaintenanceLogEntry.site_visit_id)
                    )
                )
            }
        return {"status": "ok", "rows": [site_visit_row(row, counts.get(int(row.id or 0), 0)) for row in visits]}

    @router.post("/api/maintenance/site-visits/sync")
    async def api_v2_maintenance_site_visits_sync(request: Request):
        logger = dependencies.logger
        require_settings_access = dependencies.require_settings_access
        run_owntracks_site_visit_sync = dependencies.run_owntracks_site_visit_sync
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        try:
            result = await run_owntracks_site_visit_sync(reason="manual")
        except urllib.error.URLError as exc:
            raise HTTPException(status_code=502, detail=f"OwnTracks svarte ikke: {exc}") from exc
        except Exception as exc:
            logger.warning("Manual OwnTracks site visit sync failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return result

    return RouterBundle(router, {
        "api_v2_maintenance_log_create": api_v2_maintenance_log_create,
        "api_v2_maintenance_log_update": api_v2_maintenance_log_update,
        "api_v2_maintenance_site_visit_detail": api_v2_maintenance_site_visit_detail,
        "api_v2_maintenance_site_visit_update": api_v2_maintenance_site_visit_update,
        "api_v2_maintenance_site_visits": api_v2_maintenance_site_visits,
        "api_v2_maintenance_site_visits_sync": api_v2_maintenance_site_visits_sync,
    }, dependencies)
