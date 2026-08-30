"""Ventilation module response assembly, independent of HTTP registration."""

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from fibaro_core.export_definitions import VENT_COLUMNS
from fibaro_core.export_definitions import YR_LOG_TABLE_COLUMNS
from fibaro_core.models import ControlConfigHistory
from fibaro_core.models import VentilationEvent
from fibaro_core.models import VentilationSample
from fibaro_core.models import YrForecastSample
from fibaro_core.services.presentation import api_card
from fibaro_core.services.presentation import api_table
from fibaro_core.services.presentation import format_short_number
from fibaro_core.services.summaries.periods import add_months
from sqlalchemy import select
from typing import Any
from typing import Dict
from v2_navigation import v2_module_title


@dataclass
class Dependencies:
    VENT_TIMELINE_DEVICES: Any
    api_config_field_rows: Any
    api_config_history_rows: Any
    api_filter: Any
    api_filter_int: Any
    api_filter_value: Any
    api_pick: Any
    api_rule_rows: Any
    api_tool_row: Any
    build_temp_day: Any
    clean_display_text: Any
    config_rules: Any
    display_action: Any
    display_control_mode: Any
    empty_ventilation_day_payload: Any
    fetch_rows: Any
    get_or_create_config: Any
    hc3_fetch_switch_statuses: Any
    hc3_switch_config_for_timeline_device: Any
    merge_config_values: Any
    parse_day: Any
    percent_between: Any
    ventilation_day_payload: Any
    ventilation_latest_payload: Any
    ventilation_settings_payload: Any
    ventilation_status_payload: Any


async def render(session, request, module, view, q, day, now_dt, dependencies):
    VENT_TIMELINE_DEVICES = dependencies.VENT_TIMELINE_DEVICES
    api_config_field_rows = dependencies.api_config_field_rows
    api_config_history_rows = dependencies.api_config_history_rows
    api_filter = dependencies.api_filter
    api_filter_int = dependencies.api_filter_int
    api_filter_value = dependencies.api_filter_value
    api_pick = dependencies.api_pick
    api_rule_rows = dependencies.api_rule_rows
    api_tool_row = dependencies.api_tool_row
    build_temp_day = dependencies.build_temp_day
    clean_display_text = dependencies.clean_display_text
    config_rules = dependencies.config_rules
    display_action = dependencies.display_action
    display_control_mode = dependencies.display_control_mode
    empty_ventilation_day_payload = dependencies.empty_ventilation_day_payload
    fetch_rows = dependencies.fetch_rows
    get_or_create_config = dependencies.get_or_create_config
    hc3_fetch_switch_statuses = dependencies.hc3_fetch_switch_statuses
    hc3_switch_config_for_timeline_device = dependencies.hc3_switch_config_for_timeline_device
    merge_config_values = dependencies.merge_config_values
    parse_day = dependencies.parse_day
    percent_between = dependencies.percent_between
    ventilation_day_payload = dependencies.ventilation_day_payload
    ventilation_latest_payload = dependencies.ventilation_latest_payload
    ventilation_settings_payload = dependencies.ventilation_settings_payload
    ventilation_status_payload = dependencies.ventilation_status_payload
    params = request.query_params
    today = now_dt.date()
    tomorrow = today + timedelta(days=1)
    today_start = datetime.combine(today, time.min)
    tomorrow_start = datetime.combine(tomorrow, time.min)
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, time.min)
    previous_month_start = add_months(month_start, -1)
    previous_month_start_dt = datetime.combine(previous_month_start, time.min)
    year_start_dt = datetime.combine(date(today.year, 1, 1), time.min)
    active_view = view or "dagslogg"
    log_from_value = api_filter_value(params, "from")
    log_to_value = api_filter_value(params, "to")
    log_mode_value = api_filter_value(params, "mode")
    log_limit_value = api_filter_int(params, "limit", 120, 25, 1000)
    selected_day = parse_day(day)
    day_start = datetime.combine(selected_day, time.min)
    day_end = day_start + timedelta(days=1)
    is_today = selected_day == today
    timeline_end = min(now_dt, day_end) if is_today else day_end
    now_marker = percent_between(now_dt, day_start, day_end) if is_today and day_start <= now_dt <= day_end else None
    latest = (
        await session.execute(select(VentilationSample).order_by(VentilationSample.bucket_start.desc()).limit(1))
    ).scalars().first()
    latest_yr = (
        await session.execute(select(YrForecastSample).order_by(YrForecastSample.bucket_start.desc()).limit(1))
    ).scalars().first()
    vent_switch_configs = [
        config for device in VENT_TIMELINE_DEVICES
        if (config := hc3_switch_config_for_timeline_device(device)) is not None
    ]
    vent_hc3_statuses = await hc3_fetch_switch_statuses(vent_switch_configs)
    fan_status_items = [
        ventilation_status_payload(device, latest, vent_hc3_statuses.get(str(device.get("key"))))
        for device in VENT_TIMELINE_DEVICES
    ]
    samples = []
    yr_rows = []
    events = []
    if active_view == "temp-logg":
        samples, _ = await fetch_rows(VentilationSample, None, None, None, None, log_mode_value or None, None, log_from_value, log_to_value, log_limit_value)
    if active_view == "yr-logg":
        yr_rows, _ = await fetch_rows(YrForecastSample, None, None, None, None, None, None, log_from_value, log_to_value, log_limit_value, time_basis="utc")
    if active_view in {"dagslogg", "hendelser"}:
        events, _ = await fetch_rows(VentilationEvent, "fan_change", None, None, None, log_mode_value or None, None, log_from_value, log_to_value, log_limit_value)
    fan_on = sum(1 for item in fan_status_items if item.get("state") is True)
    temp_day = await build_temp_day(day_start, day_end, timeline_end) if active_view in {"dagslogg", "hendelser"} else None
    ventilation_data: Dict[str, Any] = {
        "view": active_view,
        "latest": ventilation_latest_payload(latest, latest_yr, fan_status_items),
        "day": ventilation_day_payload(temp_day, selected_day, is_today, now_marker) if temp_day else empty_ventilation_day_payload(selected_day, is_today, now_marker),
    }
    charts: list[Dict[str, Any]] = []
    sample_columns = [
        "bucket_start", "mode",
        "temp_1etg", "humidity_1etg", "temp_2etg", "humidity_2etg", "temp_vip", "humidity_vip",
        "temp_ute", "temp_ute_netatmo", "temp_yr", "humidity_ute", "humidity_yr",
        "temp_loft", "humidity_loft", "temp_luftinntak", "humidity_luftinntak",
        "temp_passiv", "humidity_passiv", "temp_kjeller", "humidity_kjeller",
        "fan_vip", "fan_2etg", "fan_tak", "fan_avfukter",
    ]
    day_sample_rows = [
        {
            "time": row.get("time"),
            "mode": display_control_mode(row.get("mode")),
            **{key: row.get(key) for key in sample_columns if key not in {"bucket_start", "mode"}},
        }
        for row in ventilation_data["day"]["samples"]
    ]
    event_table_rows = []
    for row in events:
        event_row = api_pick(row, VENT_COLUMNS)
        event_row["action"] = display_action(event_row.get("action"))
        event_row["mode"] = display_control_mode(event_row.get("mode"))
        event_row["reason"] = clean_display_text(event_row.get("reason"))
        event_table_rows.append(event_row)
    tables = [
        api_table("Dagsmålinger", ["time", "mode", "temp_1etg", "humidity_1etg", "temp_2etg", "humidity_2etg", "temp_vip", "humidity_vip", "temp_ute", "temp_loft", "temp_kjeller", "humidity_kjeller", "fan_vip", "fan_2etg", "fan_tak", "fan_avfukter"], day_sample_rows),
        api_table("Temperatur og fukt", sample_columns, [api_pick(row, sample_columns) for row in samples]),
        api_table("Yr", YR_LOG_TABLE_COLUMNS, [api_pick(row, YR_LOG_TABLE_COLUMNS) for row in yr_rows]),
        api_table("Hendelser", ["timestamp", "action", "device_name", "mode", "reason", "state"], event_table_rows),
    ]
    if active_view == "dagslogg":
        tables = [tables[0], tables[3]]
    elif active_view == "temp-logg":
        tables = [tables[1]]
    elif active_view == "yr-logg":
        tables = [tables[2]]
    elif active_view == "hendelser":
        tables = [tables[3]]
    elif active_view == "innstillinger":
        config = await get_or_create_config(session, "ventilation")
        values = merge_config_values("ventilation", config.values if config else {})
        history = (
            await session.execute(
                select(ControlConfigHistory)
                .where(ControlConfigHistory.config_key == "ventilation")
                .order_by(ControlConfigHistory.changed_at.desc())
                .limit(25)
            )
        ).scalars().all()
        ventilation_data["settings"] = ventilation_settings_payload(config, values, history)
        tables = [
            api_table(
                "Ventilasjonsverktøy",
                ["tool", "path", "description", "count"],
                [
                    api_tool_row("Rediger innstillinger", "/ventilasjon/innstillinger", "Rediger ventilasjonsgrenser i innstillingene.", config.version if config else None),
                    api_tool_row("Konfig API", "/api/config/ventilation", "JSON som HC3-runneren henter.", config.version if config else None),
                ],
            ),
            api_table("Aktive regler", ["rule", "description"], api_rule_rows(config_rules("ventilation", values))),
            api_table("Grenseverdier", ["group", "label", "value", "unit", "help"], api_config_field_rows("ventilation", values)),
            api_table("Endringshistorikk", ["config_key", "version", "changed_at", "changed_by", "reason"], api_config_history_rows(history)),
        ]
    return {
        "title": v2_module_title("ventilasjon", active_view),
        "subtitle": "Temperatur, fukt, Yr og viftestatus.",
        "cards": [
            api_card("Innetemp", format_short_number(latest.temp_avg_inne if latest else None, 1), "grader", "Snitt inne", "vent", href="/ventilasjon/temp-logg"),
            api_card("Kjeller", format_short_number(latest.temp_kjeller if latest else None, 1), "grader", f"Fukt {format_short_number(latest.humidity_kjeller if latest else None)}%", "vent", href="/ventilasjon/temp-logg"),
            api_card("Vifter", f"{fan_on}/{len(VENT_TIMELINE_DEVICES)}", "på", latest.mode if latest and latest.mode else "", "vent", href="/ventilasjon/dagslogg"),
            api_card("Yr", latest_yr.weather_text if latest_yr else "-", "", f"Vind {format_short_number(latest_yr.wind_speed if latest_yr else None, 1)} m/s", "weather", href="/ventilasjon/yr-logg"),
        ],
        "charts": charts,
        "tables": tables,
        "filters": [
            api_filter("from", "Fra", "datetime", log_from_value),
            api_filter("to", "Til", "datetime", log_to_value),
            api_filter("mode", "Modus", "text", log_mode_value),
            api_filter("limit", "Antall", "number", log_limit_value),
        ]
        if active_view in {"temp-logg", "yr-logg", "hendelser"}
        else [],
        "ventilation": ventilation_data,
    }

