"""System HTTP routes; runtime services are supplied by composition."""

from api_contracts import admin_build_payload
from api_contracts import admin_builds_payload
from build_log import APP_BUILD
from build_log import APP_VERSION
from dataclasses import dataclass
from datetime import datetime
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fibaro_core.export_definitions import AI_QUERY_COLUMNS
from fibaro_core.export_definitions import GENERIC_COLUMNS
from fibaro_core.models import AiQueryLog
from fibaro_core.models import AssetRegistryItem
from fibaro_core.models import ControlConfig
from fibaro_core.models import ControlConfigHistory
from fibaro_core.models import GenericEvent
from fibaro_core.models import MaintenanceLogEntry
from fibaro_core.models import OperationalIncidentReview
from fibaro_core.models import ParkingVehicle
from fibaro_core.models import Sun2TanningSession
from fibaro_core.routers.bundle import RouterBundle
from observability import health_payload
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import text as sql_text
from system_inventory import system_component_summary
from system_inventory import system_subsystem_rows
from time_formatting import api_local_iso
from time_formatting import local_now_naive
from typing import Any
from typing import Any, Callable
from typing import Dict
from urllib.parse import quote
import json


@dataclass
class Dependencies:
    ACCESS_LOG_FAILURE_RETENTION_DAYS: Any
    ACCESS_LOG_SUCCESS_RETENTION_DAYS: Any
    AI_CONFIG_KEY: Any
    APP_COMMIT: Any
    APP_STARTED_AT: Any
    AUTH_SESSION_RETENTION_DAYS: Any
    FIBARO10_BACKGROUND_TASKS_ENABLED: Any
    FIBARO10_PROCESS_ROLE: Any
    IMPORT_JOB_FAILURE_RETENTION_DAYS: Any
    IMPORT_JOB_SUCCESS_RETENTION_DAYS: Any
    MOBILE_PREVIEW_REFRESH_SECONDS: Any
    NOTIFICATION_SENT_RETENTION_DAYS: Any
    NTFY_BASE_URL: Any
    OPENAI_MODEL: Any
    OPERATIONAL_RETENTION_ENABLED: Any
    OPERATIONAL_RETENTION_INTERVAL_HOURS: Any
    OPERATIONAL_RETENTION_STATE: Any
    admin_manual_payload: Callable[..., Any]
    ai_dataset_overview: Callable[..., Any]
    ask_ai: Callable[..., Any]
    async_session: Callable[..., Any]
    background_tasks: Any
    build_operational_incident_center: Callable[..., Any]
    csv_response: Callable[..., Any]
    effective_openai_settings: Callable[..., Any]
    import_status_rows: Callable[..., Any]
    incident_state: Any
    logger: Any
    mask_secret: Callable[..., Any]
    minutes_since: Callable[..., Any]
    mobile_preview_screen_payload: Callable[..., Any]
    mobile_preview_screens_for_request: Callable[..., Any]
    notification_outbox_status: Callable[..., Any]
    ntfy_host: Callable[..., Any]
    ntfy_subscription_rows: Callable[..., Any]
    operational_incident_review_payload: Callable[..., Any]
    parse_form_body: Callable[..., Any]
    protect_ledger_json: Callable[..., Any]
    recent_ai_logs: Callable[..., Any]
    redirect_keep_query: Callable[..., Any]
    render_mobile_preview_screen: Callable[..., Any]
    require_settings_access: Callable[..., Any]
    row_to_dict: Callable[..., Any]
    templates: Any


def create_router(dependencies: Dependencies) -> RouterBundle:
    router = APIRouter()


    @router.get("/health")
    @router.get("/api/system/health")
    async def health(details: bool = Query(False)):
        ACCESS_LOG_FAILURE_RETENTION_DAYS = dependencies.ACCESS_LOG_FAILURE_RETENTION_DAYS
        ACCESS_LOG_SUCCESS_RETENTION_DAYS = dependencies.ACCESS_LOG_SUCCESS_RETENTION_DAYS
        APP_COMMIT = dependencies.APP_COMMIT
        APP_STARTED_AT = dependencies.APP_STARTED_AT
        AUTH_SESSION_RETENTION_DAYS = dependencies.AUTH_SESSION_RETENTION_DAYS
        FIBARO10_BACKGROUND_TASKS_ENABLED = dependencies.FIBARO10_BACKGROUND_TASKS_ENABLED
        FIBARO10_PROCESS_ROLE = dependencies.FIBARO10_PROCESS_ROLE
        IMPORT_JOB_FAILURE_RETENTION_DAYS = dependencies.IMPORT_JOB_FAILURE_RETENTION_DAYS
        IMPORT_JOB_SUCCESS_RETENTION_DAYS = dependencies.IMPORT_JOB_SUCCESS_RETENTION_DAYS
        NOTIFICATION_SENT_RETENTION_DAYS = dependencies.NOTIFICATION_SENT_RETENTION_DAYS
        OPERATIONAL_RETENTION_ENABLED = dependencies.OPERATIONAL_RETENTION_ENABLED
        OPERATIONAL_RETENTION_INTERVAL_HOURS = dependencies.OPERATIONAL_RETENTION_INTERVAL_HOURS
        OPERATIONAL_RETENTION_STATE = dependencies.OPERATIONAL_RETENTION_STATE
        async_session = dependencies.async_session
        background_tasks = dependencies.background_tasks
        import_status_rows = dependencies.import_status_rows
        logger = dependencies.logger
        minutes_since = dependencies.minutes_since
        notification_outbox_status = dependencies.notification_outbox_status
        database = {"status": "ok", "detail": "SELECT 1 OK"}
        sources = []
        notifications = None
        status_code = 200
        try:
            async with async_session() as session:
                await session.execute(sql_text("SELECT 1"))
                if details:
                    notifications = await notification_outbox_status(session)
                    rows = await import_status_rows(session)
                    for row in rows:
                        stamp = row.get("last_success_at") or row.get("last_run_at")
                        sources.append(
                            {
                                "sourceNo": row.get("source_no"),
                                "jobName": row.get("job_name"),
                                "title": row.get("title"),
                                "label": row.get("title"),
                                "category": row.get("category"),
                                "source": row.get("source"),
                                "status": row.get("status"),
                                "statusText": row.get("status_text"),
                                "detail": row.get("age") or row.get("status_text") or "",
                                "lastRunAt": api_local_iso(row.get("last_run_at")),
                                "lastSuccessAt": api_local_iso(row.get("last_success_at")),
                                "lastFailedAt": api_local_iso(row.get("last_failed_at")),
                                "nextExpectedAt": api_local_iso(row.get("next_expected_at")),
                                "ageMinutes": minutes_since(stamp),
                                "recordsImported": row.get("records_imported"),
                                "recordsTotal": row.get("records_total"),
                                "durationSeconds": row.get("duration_seconds"),
                                "message": row.get("message") or "",
                            }
                        )
        except Exception as exc:
            logger.warning("Health database check failed: %s", exc, exc_info=True)
            database = {"status": "bad", "detail": str(exc)}
            status_code = 503
        payload = health_payload(
            app_version=APP_VERSION,
            app_build=APP_BUILD,
            app_commit=APP_COMMIT,
            started_at=APP_STARTED_AT,
            database=database,
            sources=sources,
        )
        if notifications is not None:
            payload["notifications"] = notifications
        payload["runtime"] = {
            "role": FIBARO10_PROCESS_ROLE,
            "backgroundTasksEnabled": FIBARO10_BACKGROUND_TASKS_ENABLED,
            "backgroundTasks": list(background_tasks.running_names()),
        }
        if details:
            payload["maintenance"] = {
                "retention": {
                    **OPERATIONAL_RETENTION_STATE,
                    "enabled": OPERATIONAL_RETENTION_ENABLED,
                    "intervalHours": OPERATIONAL_RETENTION_INTERVAL_HOURS,
                    "policyDays": {
                        "successfulAccessLogs": ACCESS_LOG_SUCCESS_RETENTION_DAYS,
                        "failedAccessLogs": ACCESS_LOG_FAILURE_RETENTION_DAYS,
                        "successfulImportRuns": IMPORT_JOB_SUCCESS_RETENTION_DAYS,
                        "failedImportRuns": IMPORT_JOB_FAILURE_RETENTION_DAYS,
                        "sentNotifications": NOTIFICATION_SENT_RETENTION_DAYS,
                        "expiredAuthSessions": AUTH_SESSION_RETENTION_DAYS,
                    },
                }
            }
        if status_code == 200:
            return payload
        return JSONResponse(payload, status_code=status_code)

    @router.get("/favicon.ico")
    async def favicon():
        return FileResponse(
            "static/favicon.ico",
            media_type="image/x-icon",
            headers={"Cache-Control": "public, max-age=604800, immutable"},
        )

    @router.get("/api/admin/builds")
    async def api_admin_builds():
        return admin_builds_payload()

    @router.get("/api/manual")
    async def api_manual():
        admin_manual_payload = dependencies.admin_manual_payload
        return admin_manual_payload()

    @router.get("/api/admin/manual")
    async def api_admin_manual():
        admin_manual_payload = dependencies.admin_manual_payload
        return admin_manual_payload()

    @router.get("/api/system/notifications")
    async def api_system_notifications():
        NTFY_BASE_URL = dependencies.NTFY_BASE_URL
        async_session = dependencies.async_session
        build_operational_incident_center = dependencies.build_operational_incident_center
        incident_state = dependencies.incident_state
        logger = dependencies.logger
        ntfy_host = dependencies.ntfy_host
        ntfy_subscription_rows = dependencies.ntfy_subscription_rows
        protect_ledger_json = dependencies.protect_ledger_json
        now_dt = local_now_naive()
        bollard_status = None
        bollard_error = None
        try:
            bollard_status = await protect_ledger_json("bollards")
            incident_state.bollard_failure_started_at = None
        except Exception as exc:
            bollard_error = str(getattr(exc, "detail", None) or exc or "Pullerttjenesten svarer ikke")
            if incident_state.bollard_failure_started_at is None:
                incident_state.bollard_failure_started_at = now_dt
            logger.debug("Kunne ikke lese pullertstatus for ntfy-oversikten", exc_info=True)
        subscriptions = ntfy_subscription_rows(bollard_status)
        async with async_session() as session:
            incident_center = await build_operational_incident_center(
                session,
                now_dt,
                bollard_status,
                bollard_error,
                incident_state.bollard_failure_started_at,
            )
        return {
            "generatedAt": api_local_iso(now_dt),
            "provider": ntfy_host(),
            "providerUrl": NTFY_BASE_URL,
            "summary": {
                "channels": len(subscriptions),
                "configured": sum(1 for row in subscriptions if row["configured"]),
                "publishing": sum(1 for row in subscriptions if row["publishingEnabled"]),
            },
            "incidentSummary": incident_center["summary"],
            "controls": incident_center["controls"],
            "incidents": incident_center["incidents"],
            "delivery": incident_center["delivery"],
            "subscriptions": subscriptions,
            "setup": [
                "Installer ntfy-appen på telefonen eller nettbrettet.",
                "Trykk Abonner på kanalene du vil motta.",
                "Godkjenn varslinger for ntfy i operativsystemet.",
                "Bruk Åpne kanal for å kontrollere meldingshistorikken i nettleseren.",
            ],
            "privacy": "Abonnementslenkene inneholder private kanalnavn. Ikke del dem. Fibaro10 sender bare varseltekst til ntfy; kamera- og analysedata forblir lokale.",
        }

    @router.post("/api/system/incidents/{incident_key}/review")
    async def api_system_incident_review(request: Request, incident_key: str):
        async_session = dependencies.async_session
        operational_incident_review_payload = dependencies.operational_incident_review_payload
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        try:
            payload = await request.json()
        except (ValueError, json.JSONDecodeError):
            payload = {}
        state = str(payload.get("state") or "acknowledged").strip().lower() if isinstance(payload, dict) else ""
        note = str(payload.get("note") or "").strip() if isinstance(payload, dict) else ""
        if state not in {"acknowledged", "open"}:
            raise HTTPException(status_code=400, detail="Ugyldig kvitteringsstatus")
        if len(note) > 2000:
            raise HTTPException(status_code=400, detail="Kommentaren kan ikke være lengre enn 2000 tegn")
        normalized_key = str(incident_key or "").strip()
        if not normalized_key or len(normalized_key) > 500:
            raise HTTPException(status_code=400, detail="Ugyldig hendelsesnøkkel")
        now_dt = local_now_naive()
        username = getattr(request.state, "access_key_name", "") or "master"
        async with async_session() as session:
            row = (
                await session.execute(
                    select(OperationalIncidentReview).where(
                        OperationalIncidentReview.incident_key == normalized_key
                    )
                )
            ).scalars().first()
            if row is None:
                row = OperationalIncidentReview(
                    incident_key=normalized_key,
                    created_at=now_dt,
                )
                session.add(row)
            row.status = state
            row.note = note or None
            row.reviewed_at = now_dt
            row.reviewed_by = username
            row.updated_at = now_dt
            await session.commit()
            await session.refresh(row)
        return {
            "status": "ok",
            "message": "Hendelsen er kvittert." if state == "acknowledged" else "Hendelsen er åpnet igjen.",
            "review": operational_incident_review_payload(row),
        }

    @router.get("/api/system/search")
    async def api_system_search(q: str = Query(min_length=2, max_length=120)):
        async_session = dependencies.async_session
        needle = q.strip()
        if len(needle) < 2:
            raise HTTPException(status_code=400, detail="Søket må inneholde minst to tegn")
        pattern = f"%{needle}%"
        results: list[Dict[str, Any]] = []
        async with async_session() as session:
            vehicles = (
                await session.execute(
                    select(ParkingVehicle)
                    .where(or_(ParkingVehicle.plate.ilike(pattern), ParkingVehicle.navn.ilike(pattern), ParkingVehicle.omrade.ilike(pattern)))
                    .order_by(ParkingVehicle.last_seen.desc())
                    .limit(20)
                )
            ).scalars().all()
            sessions = (
                await session.execute(
                    select(Sun2TanningSession)
                    .where(
                        or_(
                            Sun2TanningSession.user_name.ilike(pattern),
                            Sun2TanningSession.user_identifier.ilike(pattern),
                            Sun2TanningSession.sun2_user_id.ilike(pattern),
                            Sun2TanningSession.room.ilike(pattern),
                        )
                    )
                    .order_by(Sun2TanningSession.started_at.desc())
                    .limit(20)
                )
            ).scalars().all()
            maintenance = (
                await session.execute(
                    select(MaintenanceLogEntry)
                    .where(
                        or_(
                            MaintenanceLogEntry.summary.ilike(pattern),
                            MaintenanceLogEntry.target_name.ilike(pattern),
                            MaintenanceLogEntry.follow_up_text.ilike(pattern),
                        )
                    )
                    .order_by(MaintenanceLogEntry.performed_at.desc())
                    .limit(20)
                )
            ).scalars().all()
            assets = (
                await session.execute(
                    select(AssetRegistryItem)
                    .where(
                        or_(
                            AssetRegistryItem.name.ilike(pattern),
                            AssetRegistryItem.location.ilike(pattern),
                            AssetRegistryItem.manufacturer.ilike(pattern),
                            AssetRegistryItem.model.ilike(pattern),
                            AssetRegistryItem.serial_no.ilike(pattern),
                        )
                    )
                    .order_by(AssetRegistryItem.updated_at.desc())
                    .limit(20)
                )
            ).scalars().all()
        results.extend(
            {"type": "Kjøretøy", "tittel": row.plate, "detalj": " · ".join(filter(None, [row.navn, row.omrade])), "oppdatert": api_local_iso(row.last_seen), "path": f"/parkering/kjoretoy/{quote(row.plate)}"}
            for row in vehicles
        )
        results.extend(
            {"type": "Soltime", "tittel": row.user_name or row.user_identifier or row.sun2_user_id or "Ukjent bruker", "detalj": f"{row.room or 'Ukjent rom'} · {row.started_at:%d.%m.%Y %H:%M}", "oppdatert": api_local_iso(row.started_at), "path": "/soling/enkeltimer"}
            for row in sessions
        )
        results.extend(
            {"type": "Vedlikehold", "tittel": row.summary, "detalj": row.target_name or row.action_type or "", "oppdatert": api_local_iso(row.performed_at), "path": f"/vedlikehold/besok/{row.site_visit_id}" if row.site_visit_id else "/vedlikehold/"}
            for row in maintenance
        )
        results.extend(
            {"type": "Eiendel", "tittel": row.name, "detalj": " · ".join(filter(None, [row.category, row.location, row.model])), "oppdatert": api_local_iso(row.updated_at), "path": "/eiendeler/"}
            for row in assets
        )
        results.sort(key=lambda row: str(row.get("oppdatert") or ""), reverse=True)
        return {"generatedAt": api_local_iso(local_now_naive()), "query": needle, "count": len(results), "results": results[:60]}

    @router.get("/api/system/subsystems")
    async def api_system_subsystems():
        rows = system_subsystem_rows()
        return {
            "generatedAt": api_local_iso(local_now_naive()),
            "summary": system_component_summary(),
            "subsystems": rows,
        }

    @router.get("/api/admin/builds/{build}")
    async def api_admin_build(build: str):
        payload = admin_build_payload(build)
        if not payload:
            raise HTTPException(status_code=404, detail="Build finnes ikke")
        return payload

    @router.get("/ai")
    async def ai_redirect(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/admin/ai", status_code=303)

    @router.get("/ai/sok", response_class=HTMLResponse)
    async def ai_search_view(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/admin/ai", status_code=303)

    @router.post("/ai/sok", response_class=HTMLResponse)
    async def ai_search_submit(request: Request):
        ai_dataset_overview = dependencies.ai_dataset_overview
        ask_ai = dependencies.ask_ai
        async_session = dependencies.async_session
        effective_openai_settings = dependencies.effective_openai_settings
        logger = dependencies.logger
        parse_form_body = dependencies.parse_form_body
        recent_ai_logs = dependencies.recent_ai_logs
        templates = dependencies.templates
        form = await parse_form_body(request)
        question = (form.get("question") or "").strip()
        username = getattr(request.state, "access_key_name", "") or ""
        try:
            result = await ask_ai(question, username)
        except Exception as exc:
            logger.exception("AI-sok feilet for bruker %s", username or "-")
            result = {"ok": False, "answer": "", "error": str(exc), "tool_calls": []}
        async with async_session() as session:
            session.add(
                AiQueryLog(
                    username=username,
                    question=question,
                    answer=result.get("answer") or None,
                    ok=bool(result.get("ok")),
                    error=result.get("error") or None,
                    tool_calls_count=len(result.get("tool_calls") or []),
                    raw={"tool_calls": result.get("tool_calls") or []},
                )
            )
            await session.commit()
        openai_settings = await effective_openai_settings()
        context = {
            "question": question,
            "result": result,
            "datasets": ai_dataset_overview(),
            "logs": await recent_ai_logs(),
            "api_ready": bool(openai_settings["api_key"]),
            "model": openai_settings["model"],
        }
        return templates.TemplateResponse(request, "ai_search.html", context)

    @router.get("/ai/innstillinger", response_class=HTMLResponse)
    async def ai_settings_view(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/admin/ai", status_code=303)

    @router.post("/ai/innstillinger", response_class=HTMLResponse)
    async def ai_settings_update(request: Request):
        AI_CONFIG_KEY = dependencies.AI_CONFIG_KEY
        OPENAI_MODEL = dependencies.OPENAI_MODEL
        async_session = dependencies.async_session
        effective_openai_settings = dependencies.effective_openai_settings
        mask_secret = dependencies.mask_secret
        parse_form_body = dependencies.parse_form_body
        require_settings_access = dependencies.require_settings_access
        templates = dependencies.templates
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        form = await parse_form_body(request)
        new_key = (form.get("openai_api_key") or "").strip()
        model = (form.get("openai_model") or OPENAI_MODEL).strip() or OPENAI_MODEL
        clear_key = form.get("clear_openai_api_key") == "1"
        if new_key and not new_key.startswith("sk-"):
            settings = await effective_openai_settings()
            settings["model"] = model
            return templates.TemplateResponse(
                request,
                "ai_settings.html",
                {
                    "settings": settings,
                    "saved": False,
                    "error": "Nøkkelen ser ikke ut som en OpenAI API key. Den starter normalt med sk-.",
                    "openai_key_url": "https://platform.openai.com/api-keys",
                },
                status_code=400,
            )
        changed_by = getattr(request.state, "access_key_name", "") or "master"
        async with async_session() as session:
            row = (await session.execute(select(ControlConfig).where(ControlConfig.key == AI_CONFIG_KEY))).scalars().first()
            if not row:
                row = ControlConfig(
                    key=AI_CONFIG_KEY,
                    version=1,
                    values={"openai_api_key": "", "openai_model": model},
                    updated_by=changed_by,
                )
                session.add(row)
                await session.flush()
            values = dict(row.values or {})
            if clear_key:
                values["openai_api_key"] = ""
            elif new_key:
                values["openai_api_key"] = new_key
            values["openai_model"] = model
            row.values = values
            row.version = (row.version or 1) + 1
            row.updated_at = datetime.utcnow()
            row.updated_by = changed_by
            history_values = dict(values)
            if history_values.get("openai_api_key"):
                history_values["openai_api_key"] = mask_secret(history_values["openai_api_key"])
            session.add(
                ControlConfigHistory(
                    config_key=AI_CONFIG_KEY,
                    version=row.version,
                    values=history_values,
                    changed_by=changed_by,
                    reason="AI-innstillinger endret",
                )
            )
            await session.commit()
        settings = await effective_openai_settings()
        return templates.TemplateResponse(
            request,
            "ai_settings.html",
            {
                "settings": settings,
                "saved": True,
                "error": "",
                "openai_key_url": "https://platform.openai.com/api-keys",
            },
        )

    @router.get("/api/ai/datasets/json")
    async def ai_datasets_json():
        ai_dataset_overview = dependencies.ai_dataset_overview
        return {"datasets": ai_dataset_overview()}

    @router.get("/api/ai/logs/json")
    async def ai_logs_json(limit: int = Query(25, ge=1, le=200)):
        recent_ai_logs = dependencies.recent_ai_logs
        row_to_dict = dependencies.row_to_dict
        logs = await recent_ai_logs(limit)
        return {"rows": [row_to_dict(row, AI_QUERY_COLUMNS) for row in logs]}

    @router.get("/konto/oversikt", response_class=HTMLResponse)
    async def account_view(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/admin/brukere", status_code=303)

    @router.get("/konto/build", response_class=HTMLResponse)
    async def account_build_view(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/admin/build", status_code=303)

    @router.get("/konto/teknisk", response_class=HTMLResponse)
    async def account_technical_view(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/admin/teknisk", status_code=303)

    @router.get("/konto/manual", response_class=HTMLResponse)
    async def account_manual_view(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/manual/oversikt", status_code=303)

    @router.get("/")
    async def root_service_info():
        return {
            "service": "fibaro10",
            "role": "backend-api",
            "ui": "https://app.lilletorget.net/",
            "health": "/health",
        }

    @router.get("/api/mobile-preview/screens")
    async def api_mobile_preview_screens(request: Request):
        MOBILE_PREVIEW_REFRESH_SECONDS = dependencies.MOBILE_PREVIEW_REFRESH_SECONDS
        mobile_preview_screen_payload = dependencies.mobile_preview_screen_payload
        mobile_preview_screens_for_request = dependencies.mobile_preview_screens_for_request
        return {
            "refreshSeconds": MOBILE_PREVIEW_REFRESH_SECONDS,
            "screens": [mobile_preview_screen_payload(screen) for screen in mobile_preview_screens_for_request(request)],
        }

    @router.get("/api/mobile-preview/frame/{screen_key}", response_class=HTMLResponse)
    async def api_mobile_preview_frame(request: Request, screen_key: str):
        render_mobile_preview_screen = dependencies.render_mobile_preview_screen
        return await render_mobile_preview_screen(request, screen_key)

    @router.get("/download")
    @router.get("/events/download")
    @router.get("/api/system/resources/events/download")
    async def generic_download():
        csv_response = dependencies.csv_response
        return await csv_response(GenericEvent, GENERIC_COLUMNS, "event_data.csv", None, None, None, None, None, None, None, None)

    @router.get("/events/json")
    @router.get("/api/system/resources/events/json")
    async def events_json(limit: int = 1000):
        async_session = dependencies.async_session
        row_to_dict = dependencies.row_to_dict
        limit = max(1, min(limit, 10000))
        async with async_session() as session:
            result = await session.execute(select(GenericEvent).order_by(GenericEvent.timestamp.desc()).limit(limit))
            rows = result.scalars().all()
        return {"count": len(rows), "rows": [row_to_dict(row, GENERIC_COLUMNS) for row in rows]}

    return RouterBundle(router, {
        "account_build_view": account_build_view,
        "account_manual_view": account_manual_view,
        "account_technical_view": account_technical_view,
        "account_view": account_view,
        "ai_datasets_json": ai_datasets_json,
        "ai_logs_json": ai_logs_json,
        "ai_redirect": ai_redirect,
        "ai_search_submit": ai_search_submit,
        "ai_search_view": ai_search_view,
        "ai_settings_update": ai_settings_update,
        "ai_settings_view": ai_settings_view,
        "api_admin_build": api_admin_build,
        "api_admin_builds": api_admin_builds,
        "api_admin_manual": api_admin_manual,
        "api_manual": api_manual,
        "api_mobile_preview_frame": api_mobile_preview_frame,
        "api_mobile_preview_screens": api_mobile_preview_screens,
        "api_system_incident_review": api_system_incident_review,
        "api_system_notifications": api_system_notifications,
        "api_system_search": api_system_search,
        "api_system_subsystems": api_system_subsystems,
        "events_json": events_json,
        "favicon": favicon,
        "generic_download": generic_download,
        "health": health,
        "root_service_info": root_service_info,
    }, dependencies)
