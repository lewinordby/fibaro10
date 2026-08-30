"""Building HTTP routes; runtime services are supplied by composition."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from datetime import time
from datetime import timedelta
from fastapi import APIRouter
from fastapi import Query
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fibaro_core.export_definitions import LIGHT_COLUMNS
from fibaro_core.export_definitions import LIGHT_SAMPLE_COLUMNS
from fibaro_core.export_definitions import VENT_COLUMNS
from fibaro_core.export_definitions import VENT_SAMPLE_COLUMNS
from fibaro_core.export_definitions import YR_SAMPLE_COLUMNS
from fibaro_core.models import ControlConfigHistory
from fibaro_core.models import OutdoorLightEvent
from fibaro_core.models import OutdoorLightSample
from fibaro_core.models import VentilationEvent
from fibaro_core.models import VentilationSample
from fibaro_core.models import YrForecastSample
from fibaro_core.routers.bundle import RouterBundle
from time_formatting import local_now_naive
from typing import Any, Callable
from typing import Optional


@dataclass
class Dependencies:
    CONFIG_DEFINITIONS: Any
    async_session: Callable[..., Any]
    build_light_chart_markers: Callable[..., Any]
    build_lux_day: Callable[..., Any]
    build_temp_day: Callable[..., Any]
    config_payload: Callable[..., Any]
    config_values_from_payload: Callable[..., Any]
    csv_response: Callable[..., Any]
    fetch_lux_samples: Callable[..., Any]
    fetch_rows: Callable[..., Any]
    get_or_create_config: Callable[..., Any]
    parse_day: Callable[..., Any]
    percent_between: Callable[..., Any]
    redirect_keep_query: Callable[..., Any]
    require_settings_access: Callable[..., Any]
    row_to_dict: Callable[..., Any]
    templates: Any
    validate_config_values: Callable[..., Any]


def create_router(dependencies: Dependencies) -> RouterBundle:
    router = APIRouter()


    @router.get("/lys")
    async def lights_redirect(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/lys/dagslogg", status_code=307)

    @router.get("/ventilasjon")
    async def ventilation_redirect(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/ventilasjon/dagslogg", status_code=307)

    @router.get("/api/config")
    async def api_control_configs():
        CONFIG_DEFINITIONS = dependencies.CONFIG_DEFINITIONS
        async_session = dependencies.async_session
        config_payload = dependencies.config_payload
        get_or_create_config = dependencies.get_or_create_config
        async with async_session() as session:
            rows = [await get_or_create_config(session, config_key) for config_key in CONFIG_DEFINITIONS]
        return {"configs": [config_payload(row) for row in rows if row]}

    @router.get("/api/config/{config_key}")
    async def api_control_config(config_key: str):
        CONFIG_DEFINITIONS = dependencies.CONFIG_DEFINITIONS
        async_session = dependencies.async_session
        config_payload = dependencies.config_payload
        get_or_create_config = dependencies.get_or_create_config
        if config_key not in CONFIG_DEFINITIONS:
            return JSONResponse({"detail": "Ukjent konfigurasjon"}, status_code=404)
        async with async_session() as session:
            row = await get_or_create_config(session, config_key)
        return config_payload(row)

    @router.patch("/api/config/{config_key}")
    async def api_control_config_update(request: Request, config_key: str):
        CONFIG_DEFINITIONS = dependencies.CONFIG_DEFINITIONS
        async_session = dependencies.async_session
        config_payload = dependencies.config_payload
        config_values_from_payload = dependencies.config_values_from_payload
        get_or_create_config = dependencies.get_or_create_config
        require_settings_access = dependencies.require_settings_access
        validate_config_values = dependencies.validate_config_values
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        if config_key not in CONFIG_DEFINITIONS:
            return JSONResponse({"detail": "Ukjent konfigurasjon"}, status_code=404)
        payload = await request.json()
        values = config_values_from_payload(config_key, payload if isinstance(payload, dict) else {})
        errors = validate_config_values(config_key, values)
        if errors:
            return JSONResponse({"detail": "Ugyldige innstillinger", "errors": errors}, status_code=400)
        reason = str(payload.get("reason") or "Endret i grensesnittet").strip() if isinstance(payload, dict) else "Endret i grensesnittet"
        changed_by = getattr(request.state, "access_key_name", "") or "master"
        async with async_session() as session:
            row = await get_or_create_config(session, config_key)
            row.values = values
            row.version = (row.version or 1) + 1
            row.updated_at = datetime.utcnow()
            row.updated_by = changed_by
            session.add(
                ControlConfigHistory(
                    config_key=config_key,
                    version=row.version,
                    values=deepcopy(values),
                    changed_by=changed_by,
                    reason=reason,
                )
            )
            await session.commit()
            await session.refresh(row)
        return {"status": "ok", "message": "Innstillinger lagret.", "config": config_payload(row)}

    @router.get("/lys/dagslogg-lux", response_class=HTMLResponse)
    async def day_lux_view(request: Request, day: Optional[str] = None, compare_previous: bool = False):
        build_light_chart_markers = dependencies.build_light_chart_markers
        build_lux_day = dependencies.build_lux_day
        fetch_lux_samples = dependencies.fetch_lux_samples
        parse_day = dependencies.parse_day
        percent_between = dependencies.percent_between
        templates = dependencies.templates
        selected_day = parse_day(day)
        day_start = datetime.combine(selected_day, time.min)
        day_end = day_start + timedelta(days=1)
        previous_day_start = day_start - timedelta(days=1)
        previous_day_end = day_start
        now_local = local_now_naive()
        is_today = selected_day == now_local.date()
        timeline_end = min(now_local, day_end) if is_today else day_end
        now_marker = percent_between(now_local, day_start, day_end) if is_today else None
        previous_lux_day = None
        if compare_previous:
            _, current_values = await fetch_lux_samples(day_start, timeline_end)
            _, previous_values = await fetch_lux_samples(previous_day_start, previous_day_end)
            lux_values = current_values + previous_values
            lux_day = await build_lux_day(day_start, day_end, timeline_end, lux_values)
            previous_lux_day = await build_lux_day(previous_day_start, previous_day_end, previous_day_end, lux_values)
        else:
            lux_day = await build_lux_day(day_start, day_end, timeline_end)
        light_chart = await build_light_chart_markers(day_start, day_end, timeline_end)
        compare_query = "&compare_previous=1" if compare_previous else ""
        return templates.TemplateResponse(
            request,
            "day_lux.html",
            {
                "selected_day": selected_day.isoformat(),
                "prev_day": (selected_day - timedelta(days=1)).isoformat(),
                "next_day": (selected_day + timedelta(days=1)).isoformat(),
                "compare_previous": compare_previous,
                "compare_query": compare_query,
                "previous_day_label": (selected_day - timedelta(days=1)).strftime("%d.%m.%Y"),
                "is_today": is_today,
                "now_marker": now_marker,
                "now_label": now_local.strftime("%H:%M") if is_today else "",
                "lux_day": lux_day,
                "light_chart": light_chart,
                "previous_lux_day": previous_lux_day,
                "ticks": [
                    {"label": "00", "x": 0},
                    {"label": "06", "x": 250},
                    {"label": "12", "x": 500},
                    {"label": "18", "x": 750},
                    {"label": "24", "x": 1000},
                ],
            },
        )

    @router.get("/ventilasjon/dagslogg-temp", response_class=HTMLResponse)
    async def day_temp_view(request: Request, day: Optional[str] = None):
        build_temp_day = dependencies.build_temp_day
        parse_day = dependencies.parse_day
        percent_between = dependencies.percent_between
        templates = dependencies.templates
        selected_day = parse_day(day)
        day_start = datetime.combine(selected_day, time.min)
        day_end = day_start + timedelta(days=1)
        now_local = local_now_naive()
        is_today = selected_day == now_local.date()
        timeline_end = min(now_local, day_end) if is_today else day_end
        now_marker = percent_between(now_local, day_start, day_end) if is_today else None
        temp_day = await build_temp_day(day_start, day_end, timeline_end)
        return templates.TemplateResponse(
            request,
            "day_temp.html",
            {
                "selected_day": selected_day.isoformat(),
                "prev_day": (selected_day - timedelta(days=1)).isoformat(),
                "next_day": (selected_day + timedelta(days=1)).isoformat(),
                "is_today": is_today,
                "now_marker": now_marker,
                "now_label": now_local.strftime("%H:%M") if is_today else "",
                "temp_day": temp_day,
                "ticks": [
                    {"label": "00", "x": 0},
                    {"label": "06", "x": 250},
                    {"label": "12", "x": 500},
                    {"label": "18", "x": 750},
                    {"label": "24", "x": 1000},
                ],
            },
        )

    @router.get("/lys/hendelser", response_class=HTMLResponse)
    async def lights_view(
        request: Request,
        event_type: Optional[str] = None,
        action: Optional[str] = None,
        device_key: Optional[str] = None,
        device_id: Optional[int] = None,
        mode: Optional[str] = None,
        source_contains: Optional[str] = None,
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
        limit: int = 300,
    ):
        fetch_rows = dependencies.fetch_rows
        templates = dependencies.templates
        rows, limit = await fetch_rows(OutdoorLightEvent, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, limit)
        filters = {"event_type": event_type or "", "action": action or "", "device_key": device_key or "", "device_id": device_id or "", "mode": mode or "", "source_contains": source_contains or "", "from": from_text or "", "to": to_text or "", "limit": limit}
        return templates.TemplateResponse(request, "lights.html", {"rows": rows, "filters": filters})

    @router.get("/lights/json")
    async def lights_json(
        event_type: Optional[str] = None,
        action: Optional[str] = None,
        device_key: Optional[str] = None,
        device_id: Optional[int] = None,
        mode: Optional[str] = None,
        source_contains: Optional[str] = None,
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
        limit: int = 1000,
    ):
        fetch_rows = dependencies.fetch_rows
        row_to_dict = dependencies.row_to_dict
        rows, _ = await fetch_rows(OutdoorLightEvent, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, limit)
        return {"count": len(rows), "rows": [row_to_dict(row, LIGHT_COLUMNS) for row in rows]}

    @router.get("/lights/download")
    async def lights_download(
        event_type: Optional[str] = None,
        action: Optional[str] = None,
        device_key: Optional[str] = None,
        device_id: Optional[int] = None,
        mode: Optional[str] = None,
        source_contains: Optional[str] = None,
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
    ):
        csv_response = dependencies.csv_response
        return await csv_response(OutdoorLightEvent, LIGHT_COLUMNS, "utelys_events.csv", event_type, action, device_key, device_id, mode, source_contains, from_text, to_text)

    @router.get("/lights/samples/json")
    async def light_samples_json(
        mode: Optional[str] = None,
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
        limit: int = 1000,
    ):
        fetch_rows = dependencies.fetch_rows
        row_to_dict = dependencies.row_to_dict
        rows, _ = await fetch_rows(OutdoorLightSample, None, None, None, None, mode, None, from_text, to_text, limit)
        return {"count": len(rows), "rows": [row_to_dict(row, LIGHT_SAMPLE_COLUMNS) for row in rows]}

    @router.get("/lys/lux-logging", response_class=HTMLResponse)
    async def light_samples_view(
        request: Request,
        mode: Optional[str] = None,
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
        limit: int = 200,
    ):
        fetch_rows = dependencies.fetch_rows
        templates = dependencies.templates
        rows, limit = await fetch_rows(OutdoorLightSample, None, None, None, None, mode, None, from_text, to_text, limit)
        filters = {"mode": mode or "", "from": from_text or "", "to": to_text or "", "limit": limit}
        return templates.TemplateResponse(request, "light_samples.html", {"rows": rows, "filters": filters})

    @router.get("/lights/samples/download")
    @router.get("/api/system/resources/lights/samples/download")
    async def light_samples_download(
        mode: Optional[str] = None,
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
    ):
        csv_response = dependencies.csv_response
        return await csv_response(OutdoorLightSample, LIGHT_SAMPLE_COLUMNS, "utelys_samples.csv", None, None, None, None, mode, None, from_text, to_text)

    @router.get("/ventilasjon/hendelser", response_class=HTMLResponse)
    async def ventilation_view(
        request: Request,
        event_type: Optional[str] = None,
        action: Optional[str] = None,
        device_key: Optional[str] = None,
        device_id: Optional[int] = None,
        mode: Optional[str] = None,
        source_contains: Optional[str] = None,
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
        limit: int = 300,
    ):
        fetch_rows = dependencies.fetch_rows
        templates = dependencies.templates
        rows, limit = await fetch_rows(VentilationEvent, "fan_change", action, device_key, device_id, mode, source_contains, from_text, to_text, limit)
        filters = {"event_type": "fan_change", "action": action or "", "device_key": device_key or "", "device_id": device_id or "", "mode": mode or "", "source_contains": source_contains or "", "from": from_text or "", "to": to_text or "", "limit": limit}
        return templates.TemplateResponse(request, "ventilation.html", {"rows": rows, "filters": filters})

    @router.get("/ventilation/json")
    async def ventilation_json(
        event_type: Optional[str] = None,
        action: Optional[str] = None,
        device_key: Optional[str] = None,
        device_id: Optional[int] = None,
        mode: Optional[str] = None,
        source_contains: Optional[str] = None,
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
        limit: int = 1000,
    ):
        fetch_rows = dependencies.fetch_rows
        row_to_dict = dependencies.row_to_dict
        rows, _ = await fetch_rows(VentilationEvent, "fan_change", action, device_key, device_id, mode, source_contains, from_text, to_text, limit)
        return {"count": len(rows), "rows": [row_to_dict(row, VENT_COLUMNS) for row in rows]}

    @router.get("/ventilation/download")
    async def ventilation_download(
        event_type: Optional[str] = None,
        action: Optional[str] = None,
        device_key: Optional[str] = None,
        device_id: Optional[int] = None,
        mode: Optional[str] = None,
        source_contains: Optional[str] = None,
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
    ):
        csv_response = dependencies.csv_response
        return await csv_response(VentilationEvent, VENT_COLUMNS, "ventilasjon_events.csv", "fan_change", action, device_key, device_id, mode, source_contains, from_text, to_text)

    @router.get("/ventilasjon/temp-logg", response_class=HTMLResponse)
    async def ventilation_samples_view(
        request: Request,
        mode: Optional[str] = None,
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
        limit: int = 200,
    ):
        fetch_rows = dependencies.fetch_rows
        templates = dependencies.templates
        rows, limit = await fetch_rows(VentilationSample, None, None, None, None, mode, None, from_text, to_text, limit)
        filters = {"mode": mode or "", "from": from_text or "", "to": to_text or "", "limit": limit}
        return templates.TemplateResponse(request, "ventilation_samples.html", {"rows": rows, "filters": filters})

    @router.get("/ventilation/samples/json")
    async def ventilation_samples_json(
        mode: Optional[str] = None,
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
        limit: int = 1000,
    ):
        fetch_rows = dependencies.fetch_rows
        row_to_dict = dependencies.row_to_dict
        rows, _ = await fetch_rows(VentilationSample, None, None, None, None, mode, None, from_text, to_text, limit)
        return {"count": len(rows), "rows": [row_to_dict(row, VENT_SAMPLE_COLUMNS) for row in rows]}

    @router.get("/ventilation/samples/download")
    @router.get("/api/system/resources/ventilation/samples/download")
    async def ventilation_samples_download(
        mode: Optional[str] = None,
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
    ):
        csv_response = dependencies.csv_response
        return await csv_response(VentilationSample, VENT_SAMPLE_COLUMNS, "ventilasjon_samples.csv", None, None, None, None, mode, None, from_text, to_text)

    @router.get("/ventilasjon/yr-logg", response_class=HTMLResponse)
    async def yr_samples_view(
        request: Request,
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
        limit: int = 500,
    ):
        fetch_rows = dependencies.fetch_rows
        templates = dependencies.templates
        rows, limit = await fetch_rows(YrForecastSample, None, None, None, None, None, None, from_text, to_text, limit, time_basis="utc")
        filters = {"from": from_text or "", "to": to_text or "", "limit": limit}
        return templates.TemplateResponse(request, "yr_samples.html", {"rows": rows, "filters": filters})

    @router.get("/yr/samples/json")
    async def yr_samples_json(
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
        limit: int = 1000,
    ):
        fetch_rows = dependencies.fetch_rows
        row_to_dict = dependencies.row_to_dict
        rows, _ = await fetch_rows(YrForecastSample, None, None, None, None, None, None, from_text, to_text, limit, time_basis="utc")
        return {"count": len(rows), "rows": [row_to_dict(row, YR_SAMPLE_COLUMNS) for row in rows]}

    @router.get("/yr/samples/download")
    @router.get("/api/system/resources/yr/samples/download")
    async def yr_samples_download(
        from_text: Optional[str] = Query(default=None, alias="from"),
        to_text: Optional[str] = Query(default=None, alias="to"),
    ):
        csv_response = dependencies.csv_response
        return await csv_response(YrForecastSample, YR_SAMPLE_COLUMNS, "yr_forecast_samples.csv", None, None, None, None, None, None, from_text, to_text, time_basis="utc")

    @router.get("/classic/lys/innstillinger", response_class=HTMLResponse)
    async def classic_light_settings_view(request: Request):
        return dependencies.redirect_keep_query(request, "https://app.lilletorget.net/bygg/lys/innstillinger")

    return RouterBundle(router, {
        "api_control_config": api_control_config,
        "api_control_config_update": api_control_config_update,
        "api_control_configs": api_control_configs,
        "classic_light_settings_view": classic_light_settings_view,
        "day_lux_view": day_lux_view,
        "day_temp_view": day_temp_view,
        "light_samples_download": light_samples_download,
        "light_samples_json": light_samples_json,
        "light_samples_view": light_samples_view,
        "lights_download": lights_download,
        "lights_json": lights_json,
        "lights_redirect": lights_redirect,
        "lights_view": lights_view,
        "ventilation_download": ventilation_download,
        "ventilation_json": ventilation_json,
        "ventilation_redirect": ventilation_redirect,
        "ventilation_samples_download": ventilation_samples_download,
        "ventilation_samples_json": ventilation_samples_json,
        "ventilation_samples_view": ventilation_samples_view,
        "ventilation_view": ventilation_view,
        "yr_samples_download": yr_samples_download,
        "yr_samples_json": yr_samples_json,
        "yr_samples_view": yr_samples_view,
    }, dependencies)
