"""Lights module response assembly, independent of HTTP registration."""

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from fibaro_core.models import ControlConfigHistory
from fibaro_core.models import OutdoorLightEvent
from fibaro_core.models import OutdoorLightSample
from fibaro_core.services.presentation import api_card
from fibaro_core.services.presentation import api_chart
from fibaro_core.services.presentation import api_table
from fibaro_core.services.presentation import format_short_number
from fibaro_core.services.summaries.periods import add_months
from sqlalchemy import select
from time_formatting import api_local_iso
from typing import Any
from v2_navigation import v2_module_title


@dataclass
class Dependencies:
    LIGHT_TIMELINE_DEVICES: Any
    api_day_navigation: Any
    api_filter: Any
    api_filter_int: Any
    api_filter_value: Any
    api_pick: Any
    build_lux_day: Any
    build_solar_elevation_samples: Any
    control_settings_payload: Any
    fetch_rows: Any
    fetch_yr_cloud_samples: Any
    get_or_create_config: Any
    light_sample_state: Any
    merge_config_values: Any
    parse_day: Any


async def render(session, request, module, view, q, day, now_dt, dependencies):
    LIGHT_TIMELINE_DEVICES = dependencies.LIGHT_TIMELINE_DEVICES
    api_day_navigation = dependencies.api_day_navigation
    api_filter = dependencies.api_filter
    api_filter_int = dependencies.api_filter_int
    api_filter_value = dependencies.api_filter_value
    api_pick = dependencies.api_pick
    build_lux_day = dependencies.build_lux_day
    build_solar_elevation_samples = dependencies.build_solar_elevation_samples
    control_settings_payload = dependencies.control_settings_payload
    fetch_rows = dependencies.fetch_rows
    fetch_yr_cloud_samples = dependencies.fetch_yr_cloud_samples
    get_or_create_config = dependencies.get_or_create_config
    light_sample_state = dependencies.light_sample_state
    merge_config_values = dependencies.merge_config_values
    parse_day = dependencies.parse_day
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
    control_settings = None
    log_from_value = api_filter_value(params, "from")
    log_to_value = api_filter_value(params, "to")
    log_mode_value = api_filter_value(params, "mode")
    log_limit_value = api_filter_int(params, "limit", 120, 25, 1000)
    selected_day = parse_day(day)
    selected_day_start = datetime.combine(selected_day, time.min)
    selected_day_end = selected_day_start + timedelta(days=1)
    selected_day_limit = 10000
    selected_day_from = selected_day_start.isoformat(timespec="minutes")
    selected_day_to = selected_day_end.isoformat(timespec="minutes")
    use_selected_day_rows = view in {"", "dagslogg"}
    sample_from_value = selected_day_from if use_selected_day_rows else log_from_value
    sample_to_value = selected_day_to if use_selected_day_rows else log_to_value
    sample_limit_value = selected_day_limit if use_selected_day_rows else log_limit_value
    latest = (
        await session.execute(select(OutdoorLightSample).order_by(OutdoorLightSample.bucket_start.desc()).limit(1))
    ).scalars().first()
    samples, _ = await fetch_rows(OutdoorLightSample, None, None, None, None, log_mode_value or None, None, sample_from_value, sample_to_value, sample_limit_value)
    events, _ = await fetch_rows(OutdoorLightEvent, None, None, None, None, log_mode_value or None, None, sample_from_value, sample_to_value, sample_limit_value)
    light_on = sum(1 for device in LIGHT_TIMELINE_DEVICES if latest and light_sample_state(latest, device) is True)
    selected_timeline_end = min(now_dt, selected_day_end) if selected_day == today else selected_day_end
    lux_day = await build_lux_day(selected_day_start, selected_day_end, selected_timeline_end)
    cloud_samples = await fetch_yr_cloud_samples(selected_day_start, selected_day_end)
    solar_samples = build_solar_elevation_samples(selected_day_start, selected_day_end)
    lux_series = [
        {
            "name": "Lux",
            "data": [[api_local_iso(row["time_dt"]), row["lux"]] for row in lux_day["points"] if row.get("time_dt")],
            "color": "#ca8a04",
            "unit": "lux",
        }
    ]
    cloud_series = [
        {
            "name": "Skydekke",
            "data": [[api_local_iso(row["time_dt"]), row["cloud_area_fraction"]] for row in cloud_samples if row.get("time_dt")],
            "color": "#64748b",
            "unit": "%",
            "yAxisIndex": 1,
            "smooth": True,
        }
    ]
    solar_series = [
        {
            "name": "Solhøyde",
            "data": [[api_local_iso(row["time_dt"]), row["solar_elevation"]] for row in solar_samples if row.get("time_dt")],
            "color": "#ea580c",
            "unit": "grader",
            "yAxisIndex": 1,
            "smooth": True,
        }
    ]
    charts = [
        api_chart(
            "Dagslogg lys",
            [],
            lux_series + cloud_series + solar_series,
            f"{selected_day.strftime('%d.%m.%Y')} vises som helt døgn. Slå Lux, Skydekke og Solhøyde av/på i grafen.",
            "line",
            340,
            default_visible_series=["Lux", "Skydekke", "Solhøyde"],
            x_axis_type="time",
            x_axis_min=api_local_iso(selected_day_start),
            x_axis_max=api_local_iso(selected_day_end),
            disable_zoom=True,
            day_navigation=api_day_navigation(selected_day, today),
        )
    ]
    light_sample_table_columns = [
        "bucket_start", "mode", "lux", "light_lyslist", "light_reklame",
        "light_spot_glass_275", "light_spot_glass_299", "light_spot_inngang",
        "light_parkering", "weather_text",
    ]
    light_event_table_columns = ["timestamp", "action", "device_name", "mode", "reason", "lux", "state"]
    tables = [
        api_table("Lux-samples", light_sample_table_columns, [api_pick(row, light_sample_table_columns) for row in samples]),
        api_table("Hendelser", light_event_table_columns, [api_pick(row, light_event_table_columns) for row in events]),
    ]
    if view == "hendelser":
        tables = [tables[1]]
    elif view in {"lux-logging", "dagslogg"}:
        tables = [tables[0]]
    elif view == "innstillinger":
        config = await get_or_create_config(session, "lights")
        values = merge_config_values("lights", config.values if config else {})
        history = (
            await session.execute(
                select(ControlConfigHistory)
                .where(ControlConfigHistory.config_key == "lights")
                .order_by(ControlConfigHistory.changed_at.desc())
                .limit(25)
            )
        ).scalars().all()
        control_settings = control_settings_payload("lights", config, values, history) if config else None
        charts = []
        tables = []
    return {
        "title": v2_module_title("lys", view),
        "subtitle": "Utelys, lux, modus og hendelser.",
        "cards": [
            api_card("Lux", format_short_number(latest.lux if latest else None), "", latest.mode if latest and latest.mode else "", "light", href="/lys/lux-logging"),
            api_card("Lys på", f"{light_on}/{len(LIGHT_TIMELINE_DEVICES)}", "stk", "Fra siste sample", "light", href="/lys/dagslogg"),
            api_card("Siste sample", latest.bucket_start.strftime("%H:%M") if latest and latest.bucket_start else "-", "", "Dagslogg", "status", href="/lys/dagslogg"),
            api_card("Hendelser", len(events), "siste", "Siste loggede lysendringer", "status", href="/lys/hendelser"),
        ],
        "charts": charts,
        "tables": tables,
        "filters": [
            api_filter("from", "Fra", "datetime", log_from_value),
            api_filter("to", "Til", "datetime", log_to_value),
            api_filter("mode", "Modus", "text", log_mode_value),
            api_filter("limit", "Antall", "number", log_limit_value),
        ]
        if view in {"lux-logging", "hendelser"}
        else [],
        "controlSettings": control_settings,
    }

