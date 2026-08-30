"""Revenue HTTP routes; runtime services are supplied by composition."""

from cleaning_robot_domain import cleaning_provider
from cleaning_robot_domain import cleaning_robot_is_active
from cleaning_robot_domain import cleaning_robot_operational_state
from cleaning_robot_domain import cleaning_robot_sort_key
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.responses import Response
from fibaro_core.models import AlarmEvent
from fibaro_core.models import EnergyFibaroSample
from fibaro_core.models import EnergyHourlyConsumption
from fibaro_core.models import ImportJobRun
from fibaro_core.models import OutdoorLightEvent
from fibaro_core.models import OutdoorLightSample
from fibaro_core.models import ParkingSession
from fibaro_core.models import RoborockCleanJob
from fibaro_core.models import RoborockRobot
from fibaro_core.models import RoborockSchedule
from fibaro_core.models import RoborockStatusSample
from fibaro_core.models import RoborockTelemetrySample
from fibaro_core.models import SettlementImport
from fibaro_core.models import Sun2TanningSession
from fibaro_core.models import VentilationEvent
from fibaro_core.models import VentilationSample
from fibaro_core.models import YrForecastSample
from fibaro_core.routers.bundle import RouterBundle
from fibaro_core.services.comparisons.chart import build_status_comparison
from fibaro_core.services.comparisons.overview import build_overview_cards
from fibaro_core.services.comparisons.overview import load_overview_comparisons
from fibaro_core.services.comparisons.overview import overview_comparison_plan
from fibaro_core.services.comparisons.windows import cutoff_label
from fibaro_core.services.comparisons.windows import parse_anchor_day
from fibaro_core.services.comparisons.windows import period_cutoff
from fibaro_core.services.comparisons.windows import shifted_period_cutoff
from fibaro_core.services.comparisons.windows import source_as_of
from fibaro_core.services.comparisons.years import build_revenue_year_comparison
from fibaro_core.services.presentation import format_short_number
from fibaro_core.services.settlements.parsing import PARKING_SETTLEMENT_PROVIDER
from fibaro_core.services.settlements.presentation import settlement_detail_payload
from fibaro_core.services.summaries.parking import parking_datetime_snapshot
from fibaro_core.services.summaries.periods import parse_anchor_year
from fibaro_core.services.summaries.revenue import combine_business_summaries
from fibaro_core.services.summaries.sun import sun2_datetime_snapshot
from fibaro_core.services.summaries.sun import sun2_period_snapshot
from import_jobs import IMPORT_JOB_DEFINITIONS
from import_jobs import IMPORT_JOB_NUMBER_BY_NAME
from roborock_domain import roborock_job_status
from roborock_domain import roborock_next_schedule_score
from roborock_domain import roborock_schedule_text
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from time_formatting import api_local_iso
from time_formatting import local_naive_to_utc_naive
from time_formatting import local_now_naive
from time_formatting import normalize_local_naive
from time_formatting import utc_naive_to_local_naive
from typing import Any
from typing import Any, Callable
from typing import Dict
from typing import Optional
from urllib.parse import quote
from value_parsing import float_or_zero
import asyncio
import mimetypes


@dataclass
class Dependencies:
    DAY_ZOOM_OPTIONS: Any
    DREAME_EXPECTED_ROBOT_NAME: Any
    LIGHT_TIMELINE_DEVICES: Any
    NTFY_LIGHTS_TOPIC: Any
    NTFY_VENTILATION_TOPIC: Any
    VENT_TIMELINE_DEVICES: Any
    api_bool_state: Callable[..., Any]
    api_hc3_doors_status: Callable[..., Any]
    api_revenue_day: Callable[..., Any]
    api_unifi_protect_bollards: Callable[..., Any]
    async_session: Callable[..., Any]
    build_light_timeline_group: Callable[..., Any]
    build_lux_sparkline: Callable[..., Any]
    build_now_status: Callable[..., Any]
    build_revenue_month_context: Callable[..., Any]
    build_timeline_group: Callable[..., Any]
    dashboard_alert: Callable[..., Any]
    dashboard_compare_value: Callable[..., Any]
    dashboard_money_compare: Callable[..., Any]
    day_zoom_window: Callable[..., Any]
    event_device_key: Callable[..., Any]
    freshness_item: Callable[..., Any]
    get_parking_summaries: Callable[..., Any]
    get_sun2_summaries: Callable[..., Any]
    hc3_fetch_switch_statuses: Callable[..., Any]
    hc3_switch_config_for_timeline_device: Callable[..., Any]
    import_status_rows: Callable[..., Any]
    latest_cleaning_robot_sample: Callable[..., Any]
    light_sample_state: Callable[..., Any]
    minutes_since: Callable[..., Any]
    ntfy_subscribe_url: Callable[..., Any]
    ntfy_topic_url: Callable[..., Any]
    operating_window: Callable[..., Any]
    operations_area_status: Callable[..., Any]
    operations_metric: Callable[..., Any]
    operations_recent_door_items: Callable[..., Any]
    operations_switch_item: Callable[..., Any]
    parse_day: Callable[..., Any]
    percent_between: Callable[..., Any]
    state_from_event: Callable[..., Any]
    status_timeline_lane: Callable[..., Any]
    templates: Any
    ventilation_status_payload: Callable[..., Any]
    weather_from_rows: Callable[..., Any]


def create_router(dependencies: Dependencies) -> RouterBundle:
    router = APIRouter()


    @router.get("/status/dashboard", response_class=HTMLResponse)
    async def index(request: Request):
        LIGHT_TIMELINE_DEVICES = dependencies.LIGHT_TIMELINE_DEVICES
        NTFY_LIGHTS_TOPIC = dependencies.NTFY_LIGHTS_TOPIC
        NTFY_VENTILATION_TOPIC = dependencies.NTFY_VENTILATION_TOPIC
        VENT_TIMELINE_DEVICES = dependencies.VENT_TIMELINE_DEVICES
        async_session = dependencies.async_session
        build_lux_sparkline = dependencies.build_lux_sparkline
        build_now_status = dependencies.build_now_status
        dashboard_alert = dependencies.dashboard_alert
        dashboard_compare_value = dependencies.dashboard_compare_value
        dashboard_money_compare = dependencies.dashboard_money_compare
        event_device_key = dependencies.event_device_key
        freshness_item = dependencies.freshness_item
        hc3_fetch_switch_statuses = dependencies.hc3_fetch_switch_statuses
        hc3_switch_config_for_timeline_device = dependencies.hc3_switch_config_for_timeline_device
        import_status_rows = dependencies.import_status_rows
        light_sample_state = dependencies.light_sample_state
        ntfy_subscribe_url = dependencies.ntfy_subscribe_url
        ntfy_topic_url = dependencies.ntfy_topic_url
        state_from_event = dependencies.state_from_event
        templates = dependencies.templates
        ventilation_status_payload = dependencies.ventilation_status_payload
        today = local_now_naive().date()
        async with async_session() as session:
            lights = (await session.execute(select(OutdoorLightEvent).order_by(OutdoorLightEvent.timestamp.desc()).limit(200))).scalars().all()
            light_samples = (await session.execute(select(OutdoorLightSample).order_by(OutdoorLightSample.timestamp.desc()).limit(1))).scalars().all()
            ventilation = (await session.execute(select(VentilationEvent).order_by(VentilationEvent.timestamp.desc()).limit(100))).scalars().all()
            samples = (await session.execute(select(VentilationSample).order_by(VentilationSample.timestamp.desc()).limit(1))).scalars().all()
            yr_samples = (await session.execute(select(YrForecastSample).order_by(YrForecastSample.timestamp.desc()).limit(1))).scalars().all()
            import_rows = await import_status_rows(session)
            today = local_now_naive().date()
            yesterday = today - timedelta(days=1)
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            year_start = today.replace(month=1, day=1)
            previous_week_start = week_start - timedelta(days=7)
            previous_month_last = month_start - timedelta(days=1)
            previous_month_start = previous_month_last.replace(day=1)
            previous_year_start = date(today.year - 1, 1, 1)
            today_start = datetime.combine(today, time.min)
            yesterday_start = today_start - timedelta(days=1)
            tomorrow_start = today_start + timedelta(days=1)
            week_start_dt = datetime.combine(week_start, time.min)
            month_start_dt = datetime.combine(month_start, time.min)
            year_start_dt = datetime.combine(year_start, time.min)
            previous_week_start_dt = datetime.combine(previous_week_start, time.min)
            previous_month_start_dt = datetime.combine(previous_month_start, time.min)
            previous_year_start_dt = datetime.combine(previous_year_start, time.min)
            current_week_span = tomorrow_start - week_start_dt
            current_month_span = tomorrow_start - month_start_dt
            current_year_span = tomorrow_start - year_start_dt
            previous_week_end_dt = previous_week_start_dt + current_week_span
            previous_month_end_dt = min(previous_month_start_dt + current_month_span, month_start_dt)
            previous_year_end_dt = min(previous_year_start_dt + current_year_span, year_start_dt)
            now_dt = local_now_naive()
            lux_spark_rows = (
                await session.execute(
                    select(OutdoorLightSample)
                    .where(OutdoorLightSample.timestamp >= today_start)
                    .where(OutdoorLightSample.timestamp < min(now_dt, tomorrow_start))
                    .order_by(OutdoorLightSample.timestamp.asc())
                )
            ).scalars().all()
            today_sun = (
                await session.execute(
                    select(
                        func.count(Sun2TanningSession.id).label("sessions"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                        func.count(func.distinct(Sun2TanningSession.room_id)).label("rooms"),
                    ).where(Sun2TanningSession.stat_date == today)
                )
            ).one()
            week_sun = (
                await session.execute(
                    select(
                        func.count(Sun2TanningSession.id).label("sessions"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                    ).where(
                        Sun2TanningSession.stat_date >= week_start,
                        Sun2TanningSession.stat_date <= today,
                    )
                )
            ).one()
            month_sun = (
                await session.execute(
                    select(
                        func.count(Sun2TanningSession.id).label("sessions"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                        func.count(func.distinct(Sun2TanningSession.room_id)).label("rooms"),
                    ).where(
                        Sun2TanningSession.stat_date >= month_start,
                        Sun2TanningSession.stat_date <= today,
                    )
                )
            ).one()
            year_sun = (
                await session.execute(
                    select(
                        func.count(Sun2TanningSession.id).label("sessions"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                        func.count(func.distinct(Sun2TanningSession.room_id)).label("rooms"),
                    ).where(
                        Sun2TanningSession.stat_date >= year_start,
                        Sun2TanningSession.stat_date <= today,
                    )
                )
            ).one()
            yesterday_sun = (
                await session.execute(
                    select(
                        func.count(Sun2TanningSession.id).label("sessions"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                    ).where(Sun2TanningSession.stat_date == yesterday)
                )
            ).one()
            previous_week_sun = (
                await session.execute(
                    select(
                        func.count(Sun2TanningSession.id).label("sessions"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                    ).where(
                        Sun2TanningSession.stat_date >= previous_week_start,
                        Sun2TanningSession.stat_date < previous_week_end_dt.date(),
                    )
                )
            ).one()
            previous_month_sun = (
                await session.execute(
                    select(
                        func.count(Sun2TanningSession.id).label("sessions"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                    ).where(
                        Sun2TanningSession.stat_date >= previous_month_start,
                        Sun2TanningSession.stat_date < previous_month_end_dt.date(),
                    )
                )
            ).one()
            previous_year_sun = (
                await session.execute(
                    select(
                        func.count(Sun2TanningSession.id).label("sessions"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                    ).where(
                        Sun2TanningSession.stat_date >= previous_year_start,
                        Sun2TanningSession.stat_date < previous_year_end_dt.date(),
                    )
                )
            ).one()
            tomorrow = today + timedelta(days=1)
            today_sun = await sun2_period_snapshot(session, today, tomorrow)
            yesterday_sun = await sun2_period_snapshot(session, yesterday, today)
            week_sun = await sun2_period_snapshot(session, week_start, tomorrow)
            month_sun = await sun2_period_snapshot(session, month_start, tomorrow)
            year_sun = await sun2_period_snapshot(session, year_start, tomorrow)
            previous_week_sun = await sun2_period_snapshot(session, previous_week_start, previous_week_end_dt.date())
            previous_month_sun = await sun2_period_snapshot(session, previous_month_start, previous_month_end_dt.date())
            previous_year_sun = await sun2_period_snapshot(session, previous_year_start, previous_year_end_dt.date())
            today_parking = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("sessions"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                    ).where(
                        ParkingSession.start_time >= today_start,
                        ParkingSession.start_time < tomorrow_start,
                    )
                )
            ).one()
            week_parking = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("sessions"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                    ).where(
                        ParkingSession.start_time >= week_start_dt,
                        ParkingSession.start_time < tomorrow_start,
                    )
                )
            ).one()
            month_parking = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("sessions"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                    ).where(
                        ParkingSession.start_time >= month_start_dt,
                        ParkingSession.start_time < tomorrow_start,
                    )
                )
            ).one()
            year_parking = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("sessions"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                    ).where(
                        ParkingSession.start_time >= year_start_dt,
                        ParkingSession.start_time < tomorrow_start,
                    )
                )
            ).one()
            yesterday_parking = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("sessions"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                    ).where(
                        ParkingSession.start_time >= yesterday_start,
                        ParkingSession.start_time < today_start,
                    )
                )
            ).one()
            previous_week_parking = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("sessions"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                    ).where(
                        ParkingSession.start_time >= previous_week_start_dt,
                        ParkingSession.start_time < previous_week_end_dt,
                    )
                )
            ).one()
            previous_month_parking = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("sessions"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                    ).where(
                        ParkingSession.start_time >= previous_month_start_dt,
                        ParkingSession.start_time < previous_month_end_dt,
                    )
                )
            ).one()
            previous_year_parking = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("sessions"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                    ).where(
                        ParkingSession.start_time >= previous_year_start_dt,
                        ParkingSession.start_time < previous_year_end_dt,
                    )
                )
            ).one()
            active_parking = (
                await session.execute(
                    select(func.count(ParkingSession.id)).where(
                        ParkingSession.start_time <= now_dt,
                        or_(
                            ParkingSession.end_time.is_(None),
                            ParkingSession.end_time >= now_dt,
                            func.lower(func.coalesce(ParkingSession.status, "")) == "ongoing",
                        ),
                    )
                )
            ).scalar_one()
            today_energy = (
                await session.execute(
                    select(
                        func.coalesce(func.sum(EnergyHourlyConsumption.consumption_kwh), 0).label("kwh"),
                        func.count(EnergyHourlyConsumption.id).label("hours"),
                        func.max(EnergyHourlyConsumption.measured_at).label("last_at"),
                    ).where(EnergyHourlyConsumption.stat_date == today)
                )
            ).one()
            latest_energy_sample = (
                await session.execute(
                    select(EnergyFibaroSample)
                    .order_by(EnergyFibaroSample.bucket_start.desc())
                    .limit(1)
                )
            ).scalars().first()
            today_energy_fibaro = (
                await session.execute(
                    select(
                        func.coalesce(func.sum(EnergyFibaroSample.inntak_delta_kwh), 0).label("kwh"),
                        func.count(EnergyFibaroSample.id).label("samples"),
                    )
                    .where(EnergyFibaroSample.bucket_start >= datetime.combine(today, time.min))
                    .where(EnergyFibaroSample.bucket_start < datetime.combine(today, time.min) + timedelta(days=1))
                )
            ).one()
            robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
            robots.sort(key=cleaning_robot_sort_key)
            schedules = (
                await session.execute(
                    select(RoborockSchedule)
                    .where(RoborockSchedule.enabled == True)
                    .where(RoborockSchedule.deleted_at.is_(None))
                    .order_by(RoborockSchedule.cron)
                )
            ).scalars().all()

        latest_light_by_key = {}
        for row in lights:
            key = event_device_key(row, LIGHT_TIMELINE_DEVICES)
            if key and key not in latest_light_by_key:
                latest_light_by_key[key] = row

        latest_vent_by_key = {}
        for row in ventilation:
            key = event_device_key(row, VENT_TIMELINE_DEVICES)
            if key and key not in latest_vent_by_key:
                latest_vent_by_key[key] = row

        latest_sample = samples[0] if samples else None
        latest_light_sample = light_samples[0] if light_samples else None
        latest_yr_sample = yr_samples[0] if yr_samples else None
        latest_light = lights[0] if lights else None
        now_status = build_now_status(latest_sample, latest_light_sample, latest_light, latest_yr_sample)
        lux_sparkline = build_lux_sparkline(lux_spark_rows, today_start, tomorrow_start)

        light_status = []
        for device in LIGHT_TIMELINE_DEVICES:
            row = latest_light_by_key.get(device["key"])
            light_sample_value = light_sample_state(latest_light_sample, device) if latest_light_sample else None
            event_state = state_from_event(row) if row else None
            light_status.append(
                {
                    "id": device["key"],
                    "name": device["name"],
                    "row": row,
                    "state": light_sample_value if light_sample_value is not None else event_state,
                    "sample_time": latest_light_sample.timestamp if light_sample_value is not None else None,
                    "lux": row.lux if row and row.lux is not None else (
                        latest_light_sample.lux
                        if latest_light_sample and latest_light_sample.lux is not None
                        else None
                    ),
                }
            )
        vent_switch_configs = [
            config for device in VENT_TIMELINE_DEVICES
            if (config := hc3_switch_config_for_timeline_device(device)) is not None
        ]
        vent_hc3_statuses = await hc3_fetch_switch_statuses(vent_switch_configs)
        vent_status = []
        for device in VENT_TIMELINE_DEVICES:
            status_payload = ventilation_status_payload(device, latest_sample, vent_hc3_statuses.get(str(device.get("key"))))
            vent_status.append(
                {
                    "id": device["key"],
                    "name": device["name"],
                    "row": latest_vent_by_key.get(device["key"]),
                    "state": status_payload.get("state"),
                    "status_source": status_payload.get("statusSource"),
                    "checked_at": status_payload.get("checkedAt"),
                    "tooltip": status_payload.get("tooltip"),
                }
            )
        vent_status.append(
            {
                "id": "loft_recovery",
                "name": "Loft > 1.etg gjenvinning",
                "row": None,
                "state": False,
                "dummy_reason": "Planlagt varmegjenvinning fra loft til 1.etg. Ikke koblet til styring ennå.",
            }
        )
        freshness_items = [
            freshness_item("Temperatur og fukt", latest_sample, 7, 15),
            freshness_item("Lux-logg", latest_light_sample, 7, 15),
            freshness_item("Yr API", latest_yr_sample, 70, 130),
            freshness_item("Lys-hendelser", lights[0] if lights else None, 120, 360),
            freshness_item("Ventilasjonshendelser", ventilation[0] if ventilation else None, 120, 360),
        ]
        import_counts = {
            "ok": sum(1 for row in import_rows if row["status"] == "ok"),
            "warn": sum(1 for row in import_rows if row["status"] == "warn"),
            "bad": sum(1 for row in import_rows if row["status"] == "bad"),
            "total": len(import_rows),
        }
        attention_items = []
        event_freshness_names = {"Lys-hendelser", "Ventilasjonshendelser"}
        for item in freshness_items:
            if item["name"] in event_freshness_names:
                continue
            if item["status"] in {"warn", "bad"}:
                attention_items.append(
                    dashboard_alert(
                        item["status"],
                        item["name"],
                        f"{item['status_text']} - sist sett {item['age']}.",
                        "/admin/datakilder",
                    )
                )
        for row in import_rows:
            if row["status"] in {"warn", "bad"}:
                attention_items.append(
                    dashboard_alert(
                        row["status"],
                        row["title"],
                        f"{row['status_text']} - {row['age']}.",
                        "/admin/datakilder",
                    )
                )
        missing_light_status = [item["name"] for item in light_status if item["state"] is None]
        if missing_light_status:
            attention_items.append(
                dashboard_alert(
                    "warn",
                    "Lysstatus",
                    f"Mangler sikker status for {len(missing_light_status)} lys.",
                    "/lys/hendelser",
                )
            )
        missing_vent_status = [item["name"] for item in vent_status if item["state"] is None]
        if missing_vent_status:
            attention_items.append(
                dashboard_alert(
                    "warn",
                    "Ventilasjonsstatus",
                    f"Mangler sikker status for {len(missing_vent_status)} vifter.",
                    "/ventilasjon/hendelser",
                )
            )
        attention_items = attention_items[:6]

        recent_robot_cutoff = local_now_naive() - timedelta(minutes=20)
        active_robots = [
            robot for robot in robots
            if robot.last_seen_at and robot.last_seen_at >= recent_robot_cutoff
        ]
        next_schedule = sorted(schedules, key=roborock_next_schedule_score)[0] if schedules else None
        focus_cards = [
            {
                "title": "Solinger i dag",
                "value": dashboard_compare_value(today_sun.sessions, yesterday_sun.sessions),
                "unit": "stk",
                "detail": f"{dashboard_money_compare(today_sun.paid, yesterday_sun.paid)} - {format_short_number(today_sun.minutes / 60, 1)} t - {today_sun.rooms or 0} rom",
                "href": "/soling/prognose",
                "tone": "sun2",
                "compare": True,
            },
            {
                "title": "Parkering i dag",
                "value": dashboard_compare_value(today_parking.sessions, yesterday_parking.sessions),
                "unit": "stk",
                "detail": f"{dashboard_money_compare(today_parking.paid, yesterday_parking.paid)} - {active_parking or 0} aktive naa",
                "href": f"/parkering/parkeringer?day={today.isoformat()}",
                "tone": "parking",
                "compare": True,
            },
            {
                "title": "Sol uke",
                "value": dashboard_compare_value(week_sun.sessions, previous_week_sun.sessions),
                "unit": "sol",
                "href": "/soling/prognose",
                "detail": f"{dashboard_money_compare(week_sun.paid, previous_week_sun.paid)} hittil",
                "tone": "week",
                "compare": True,
            },
            {
                "title": "Parkering uke",
                "value": dashboard_compare_value(week_parking.sessions, previous_week_parking.sessions),
                "unit": "stk",
                "detail": f"{dashboard_money_compare(week_parking.paid, previous_week_parking.paid)} - {active_parking or 0} aktive naa",
                "href": f"/parkering/parkeringer?day={today.isoformat()}",
                "tone": "parking",
                "compare": True,
            },
            {
                "title": "Sol hittil mnd",
                "value": dashboard_compare_value(month_sun.sessions, previous_month_sun.sessions),
                "unit": "stk",
                "detail": f"{dashboard_money_compare(month_sun.paid, previous_month_sun.paid)} - {format_short_number(month_sun.minutes / 60, 1)} t - {month_sun.rooms or 0} rom",
                "href": "/soling/prognose",
                "tone": "sun2",
                "compare": True,
            },
            {
                "title": "Parkering hittil mnd",
                "value": dashboard_compare_value(month_parking.sessions, previous_month_parking.sessions),
                "unit": "stk",
                "detail": f"{format_short_number(month_parking.paid)} kr hittil denne måneden",
                "href": f"/parkering/parkeringer?day={today.isoformat()}",
                "tone": "parking",
                "compare": True,
            },
            {
                "title": "Sol hittil år",
                "value": format_short_number(year_sun.sessions),
                "unit": "stk",
                "detail": f"{format_short_number(year_sun.paid)} kr - {format_short_number(year_sun.minutes / 60, 1)} t",
                "href": "/soling/prognose",
                "tone": "sun2",
            },
            {
                "title": "Parkering hittil år",
                "value": format_short_number(year_parking.sessions),
                "unit": "stk",
                "detail": f"{format_short_number(year_parking.paid)} kr hittil i år",
                "href": "/parkering/sammenligning",
                "tone": "parking",
            },
        ]
        focus_cards[6]["title"] = f"Sol hittil {today.year}"
        focus_cards[7]["title"] = f"Parkering hittil {today.year}"
        focus_cards[0]["value"] = dashboard_compare_value(today_sun.sessions, yesterday_sun.sessions)
        focus_cards[0]["detail"] = f"{dashboard_money_compare(today_sun.paid, yesterday_sun.paid)} - {format_short_number(today_sun.minutes / 60, 1)} t - {today_sun.rooms or 0} rom"
        focus_cards[1]["value"] = dashboard_compare_value(today_parking.sessions, yesterday_parking.sessions)
        focus_cards[1]["detail"] = f"{dashboard_money_compare(today_parking.paid, yesterday_parking.paid)} - {active_parking or 0} aktive naa"
        focus_cards[2]["value"] = dashboard_compare_value(week_sun.sessions, previous_week_sun.sessions)
        focus_cards[2]["detail"] = f"{dashboard_money_compare(week_sun.paid, previous_week_sun.paid)} hittil"
        focus_cards[3]["value"] = dashboard_compare_value(week_parking.sessions, previous_week_parking.sessions)
        focus_cards[3]["detail"] = f"{dashboard_money_compare(week_parking.paid, previous_week_parking.paid)} - {active_parking or 0} aktive naa"
        focus_cards[4]["value"] = dashboard_compare_value(month_sun.sessions, previous_month_sun.sessions)
        focus_cards[4]["detail"] = f"{dashboard_money_compare(month_sun.paid, previous_month_sun.paid)} - {format_short_number(month_sun.minutes / 60, 1)} t - {month_sun.rooms or 0} rom"
        focus_cards[5]["value"] = dashboard_compare_value(month_parking.sessions, previous_month_parking.sessions)
        focus_cards[5]["detail"] = f"{dashboard_money_compare(month_parking.paid, previous_month_parking.paid)} hittil"
        focus_cards[6]["value"] = dashboard_compare_value(year_sun.sessions, previous_year_sun.sessions)
        focus_cards[6]["detail"] = f"{dashboard_money_compare(year_sun.paid, previous_year_sun.paid)} - {format_short_number(year_sun.minutes / 60, 1)} t"
        focus_cards[7]["value"] = dashboard_compare_value(year_parking.sessions, previous_year_parking.sessions)
        focus_cards[7]["detail"] = f"{dashboard_money_compare(year_parking.paid, previous_year_parking.paid)} hittil"
        for card in focus_cards:
            card["compare"] = True
        ops_cards = [
            {
                "title": "Datakilder",
                "value": f"{import_counts['ok']}/{import_counts['total']}",
                "unit": "OK",
                "detail": f"{import_counts['warn']} treg, {import_counts['bad']} feil/gammel",
                "href": "/admin/datakilder",
                "tone": "status",
            },
            {
                "title": "Soling i dag",
                "value": format_short_number(today_sun.sessions),
                "unit": "stk",
                "detail": f"{format_short_number(today_sun.minutes / 60, 1)} t - {format_short_number(today_sun.paid)} kr - {today_sun.rooms or 0} rom",
                "href": f"/soling/dagslinje?day={today.isoformat()}",
                "tone": "sun2",
            },
            {
                "title": "Strøm i dag",
                "value": format_short_number(today_energy_fibaro.kwh if today_energy_fibaro.samples else today_energy.kwh, 1),
                "unit": "kWh",
                "detail": (
                    f"Nå {format_short_number(latest_energy_sample.inntak_w)} W - {today_energy_fibaro.samples or 0} 30-sekundersmålinger"
                    if latest_energy_sample
                    else f"{today_energy.hours or 0} timer importert" + (f" - sist {today_energy.last_at.strftime('%H:%M')}" if today_energy.last_at else "")
                ),
                "href": "/energi/status",
                "tone": "energy",
            },
            {
                "title": "Renhold",
                "value": f"{len(active_robots)}/{len(robots)}",
                "unit": "aktive",
                "detail": f"Neste: {roborock_schedule_text(next_schedule)}" if next_schedule else "Ingen aktiv plan funnet",
                "href": "/renhold/oversikt",
                "tone": "cleaning",
            },
        ]

        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "latest_light": latest_light,
                "latest_light_sample": latest_light_sample,
                "latest_vent": ventilation[0] if ventilation else None,
                "latest_sample": latest_sample,
                "latest_yr_sample": latest_yr_sample,
                "now_status": now_status,
                "light_status": light_status,
                "ntfy_lights_subscribe_url": ntfy_subscribe_url(NTFY_LIGHTS_TOPIC, "SUN2 lys"),
                "ntfy_lights_web_url": ntfy_topic_url(NTFY_LIGHTS_TOPIC),
                "ntfy_ventilation_subscribe_url": ntfy_subscribe_url(NTFY_VENTILATION_TOPIC, "SUN2 ventilasjon"),
                "ntfy_ventilation_web_url": ntfy_topic_url(NTFY_VENTILATION_TOPIC),
                "vent_status": vent_status,
                "freshness_items": freshness_items,
                "focus_cards": focus_cards,
                "ops_cards": ops_cards,
                "lux_sparkline": lux_sparkline,
                "attention_items": attention_items,
            },
        )

    @router.get("/status/nokkeltall", response_class=HTMLResponse)
    async def status_key_metrics_view(request: Request):
        LIGHT_TIMELINE_DEVICES = dependencies.LIGHT_TIMELINE_DEVICES
        VENT_TIMELINE_DEVICES = dependencies.VENT_TIMELINE_DEVICES
        async_session = dependencies.async_session
        build_now_status = dependencies.build_now_status
        dashboard_compare_value = dependencies.dashboard_compare_value
        dashboard_money_compare = dependencies.dashboard_money_compare
        hc3_fetch_switch_statuses = dependencies.hc3_fetch_switch_statuses
        hc3_switch_config_for_timeline_device = dependencies.hc3_switch_config_for_timeline_device
        import_status_rows = dependencies.import_status_rows
        light_sample_state = dependencies.light_sample_state
        operating_window = dependencies.operating_window
        templates = dependencies.templates
        ventilation_status_payload = dependencies.ventilation_status_payload
        weather_from_rows = dependencies.weather_from_rows
        now_dt = local_now_naive()
        today = now_dt.date()
        yesterday = today - timedelta(days=1)
        last_week_same_day = today - timedelta(days=7)
        two_weeks_same_day = today - timedelta(days=14)
        week_start = today - timedelta(days=today.weekday())
        previous_week_start = week_start - timedelta(days=7)
        previous_week_end = week_start
        month_start = today.replace(day=1)
        previous_month_end = month_start
        previous_month_start = (month_start - timedelta(days=1)).replace(day=1)
        tomorrow = today + timedelta(days=1)
        today_start = datetime.combine(today, time.min)
        tomorrow_start = datetime.combine(tomorrow, time.min)
        yesterday_start = datetime.combine(yesterday, time.min)
        last_week_same_day_start = datetime.combine(last_week_same_day, time.min)
        last_week_same_day_end = last_week_same_day_start + timedelta(days=1)
        two_weeks_same_day_start = datetime.combine(two_weeks_same_day, time.min)
        two_weeks_same_day_end = two_weeks_same_day_start + timedelta(days=1)
        week_start_dt = datetime.combine(week_start, time.min)
        previous_week_start_dt = datetime.combine(previous_week_start, time.min)
        previous_week_end_dt = datetime.combine(previous_week_end, time.min)
        month_start_dt = datetime.combine(month_start, time.min)
        previous_month_start_dt = datetime.combine(previous_month_start, time.min)
        previous_month_end_dt = datetime.combine(previous_month_end, time.min)
        async with async_session() as session:
            latest_light_sample = (
                await session.execute(select(OutdoorLightSample).order_by(OutdoorLightSample.timestamp.desc()).limit(1))
            ).scalars().first()
            latest_light = (
                await session.execute(select(OutdoorLightEvent).order_by(OutdoorLightEvent.timestamp.desc()).limit(1))
            ).scalars().first()
            latest_sample = (
                await session.execute(select(VentilationSample).order_by(VentilationSample.timestamp.desc()).limit(1))
            ).scalars().first()
            latest_yr_sample = (
                await session.execute(select(YrForecastSample).order_by(YrForecastSample.timestamp.desc()).limit(1))
            ).scalars().first()
            import_rows = await import_status_rows(session)
            sun_as_of = source_as_of(import_rows, "sun2_sessions_import", now_dt)
            parking_as_of = source_as_of(import_rows, "easypark_parking_import", now_dt)
            sun_today_cutoff = period_cutoff(today_start, tomorrow_start, sun_as_of)
            sun_week_cutoff = period_cutoff(week_start_dt, tomorrow_start, sun_as_of)
            sun_month_cutoff = period_cutoff(month_start_dt, tomorrow_start, sun_as_of)
            sun_last_week_same_cutoff = shifted_period_cutoff(
                today_start,
                sun_today_cutoff,
                last_week_same_day_start,
                last_week_same_day_end,
            )
            parking_today_cutoff = period_cutoff(today_start, tomorrow_start, parking_as_of)
            parking_week_cutoff = period_cutoff(week_start_dt, tomorrow_start, parking_as_of)
            parking_month_cutoff = period_cutoff(month_start_dt, tomorrow_start, parking_as_of)
            parking_last_week_same_cutoff = shifted_period_cutoff(
                today_start,
                parking_today_cutoff,
                last_week_same_day_start,
                last_week_same_day_end,
            )
            today_sun = await sun2_datetime_snapshot(session, today_start, sun_today_cutoff)
            yesterday_sun = await sun2_period_snapshot(session, yesterday, today)
            last_week_sun = await sun2_period_snapshot(session, last_week_same_day, last_week_same_day + timedelta(days=1))
            two_weeks_sun = await sun2_period_snapshot(session, two_weeks_same_day, two_weeks_same_day + timedelta(days=1))
            week_sun = await sun2_datetime_snapshot(session, week_start_dt, sun_week_cutoff)
            previous_week_sun = await sun2_period_snapshot(session, previous_week_start, previous_week_end)
            month_sun = await sun2_datetime_snapshot(session, month_start_dt, sun_month_cutoff)
            previous_month_sun = await sun2_period_snapshot(session, previous_month_start, previous_month_end)
            same_time_sun = await sun2_datetime_snapshot(session, last_week_same_day_start, sun_last_week_same_cutoff)
            latest_soling = (
                await session.execute(
                    select(Sun2TanningSession)
                    .where(Sun2TanningSession.stat_date == today)
                    .order_by(Sun2TanningSession.started_at.desc())
                    .limit(1)
                )
            ).scalars().first()
            today_parking = await parking_datetime_snapshot(session, today_start, parking_today_cutoff)
            yesterday_parking = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("sessions"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                    ).where(
                        ParkingSession.start_time >= yesterday_start,
                        ParkingSession.start_time < today_start,
                    )
                )
            ).one()
            last_week_parking = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("sessions"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                    ).where(
                        ParkingSession.start_time >= last_week_same_day_start,
                        ParkingSession.start_time < last_week_same_day_end,
                    )
                )
            ).one()
            same_time_parking = await parking_datetime_snapshot(
                session,
                last_week_same_day_start,
                parking_last_week_same_cutoff,
            )
            two_weeks_parking = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("sessions"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                    ).where(
                        ParkingSession.start_time >= two_weeks_same_day_start,
                        ParkingSession.start_time < two_weeks_same_day_end,
                    )
                )
            ).one()
            week_parking = await parking_datetime_snapshot(session, week_start_dt, parking_week_cutoff)
            previous_week_parking = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("sessions"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                    ).where(
                        ParkingSession.start_time >= previous_week_start_dt,
                        ParkingSession.start_time < previous_week_end_dt,
                    )
                )
            ).one()
            month_parking = await parking_datetime_snapshot(session, month_start_dt, parking_month_cutoff)
            previous_month_parking = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("sessions"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                    ).where(
                        ParkingSession.start_time >= previous_month_start_dt,
                        ParkingSession.start_time < previous_month_end_dt,
                    )
                )
            ).one()
            active_parking = (
                await session.execute(
                    select(func.count(ParkingSession.id)).where(
                        ParkingSession.start_time <= now_dt,
                        or_(
                            ParkingSession.end_time.is_(None),
                            ParkingSession.end_time >= now_dt,
                            func.lower(func.coalesce(ParkingSession.status, "")) == "ongoing",
                        ),
                    )
                )
            ).scalar_one()
            latest_parking = (
                await session.execute(
                    select(ParkingSession)
                    .where(ParkingSession.start_time >= today_start)
                    .where(ParkingSession.start_time < tomorrow_start)
                    .order_by(ParkingSession.start_time.desc())
                    .limit(1)
                )
            ).scalars().first()
            latest_energy_sample = (
                await session.execute(select(EnergyFibaroSample).order_by(EnergyFibaroSample.bucket_start.desc()).limit(1))
            ).scalars().first()
            today_energy_fibaro = (
                await session.execute(
                    select(
                        func.coalesce(func.sum(EnergyFibaroSample.inntak_delta_kwh), 0).label("kwh"),
                        func.count(EnergyFibaroSample.id).label("samples"),
                    )
                    .where(EnergyFibaroSample.bucket_start >= today_start)
                    .where(EnergyFibaroSample.bucket_start < tomorrow_start)
                )
            ).one()
            temp_ranges = (
                await session.execute(
                    select(
                        func.min(VentilationSample.temp_avg_inne).label("min_inne"),
                        func.max(VentilationSample.temp_avg_inne).label("max_inne"),
                        func.min(VentilationSample.temp_ute).label("min_ute"),
                        func.max(VentilationSample.temp_ute).label("max_ute"),
                        func.min(VentilationSample.temp_loft).label("min_loft"),
                        func.max(VentilationSample.temp_loft).label("max_loft"),
                    )
                    .where(VentilationSample.bucket_start >= today_start)
                    .where(VentilationSample.bucket_start < tomorrow_start)
                )
            ).one()

        now_status = build_now_status(latest_sample, latest_light_sample, latest_light, latest_yr_sample)
        import_counts = {
            "ok": sum(1 for row in import_rows if row["status"] == "ok"),
            "warn": sum(1 for row in import_rows if row["status"] == "warn"),
            "bad": sum(1 for row in import_rows if row["status"] == "bad"),
            "total": len(import_rows),
        }
        light_items = [
            {"label": device["name"], "state": light_sample_state(latest_light_sample, device) if latest_light_sample else None}
            for device in LIGHT_TIMELINE_DEVICES
        ]
        vent_switch_configs = [
            config for device in VENT_TIMELINE_DEVICES
            if (config := hc3_switch_config_for_timeline_device(device)) is not None
        ]
        vent_hc3_statuses = await hc3_fetch_switch_statuses(vent_switch_configs)
        fan_items = [
            ventilation_status_payload(device, latest_sample, vent_hc3_statuses.get(str(device.get("key"))))
            for device in VENT_TIMELINE_DEVICES
        ]
        revenue_today = float_or_zero(today_sun.paid) + float_or_zero(today_parking.paid)
        revenue_yesterday = float_or_zero(yesterday_sun.paid) + float_or_zero(yesterday_parking.paid)
        revenue_last_week = float_or_zero(last_week_sun.paid) + float_or_zero(last_week_parking.paid)
        revenue_two_weeks = float_or_zero(two_weeks_sun.paid) + float_or_zero(two_weeks_parking.paid)
        revenue_week = float_or_zero(week_sun.paid) + float_or_zero(week_parking.paid)
        revenue_previous_week = float_or_zero(previous_week_sun.paid) + float_or_zero(previous_week_parking.paid)
        revenue_month = float_or_zero(month_sun.paid) + float_or_zero(month_parking.paid)
        revenue_previous_month = float_or_zero(previous_month_sun.paid) + float_or_zero(previous_month_parking.paid)
        cards = [
            {
                "group": "Drift",
                "title": "Apning",
                "value": operating_window(now_dt)["label"],
                "unit": "",
                "detail": operating_window(now_dt)["detail"],
                "href": "/status/omsetning",
                "tone": "status",
            },
            {
                "group": "Drift",
                "title": "Datakilder",
                "value": f"{import_counts['ok']}/{import_counts['total']}",
                "unit": "OK",
                "detail": f"{import_counts['warn']} treg, {import_counts['bad']} feil/gammel",
                "href": "/admin/datakilder",
                "tone": "status",
            },
            {
                "group": "Omsetning",
                "title": "Omsetning i dag",
                "value": dashboard_compare_value(revenue_today, revenue_yesterday),
                "unit": "kr",
                "detail": f"Sol {format_short_number(today_sun.paid)} kr - park {format_short_number(today_parking.paid)} kr",
                "href": "/omsetning/oversikt",
                "tone": "revenue",
            },
            {
                "group": "Omsetning",
                "title": "Samme dag forrige uke",
                "value": format_short_number(revenue_last_week),
                "unit": "kr",
                "detail": f"Sol {format_short_number(last_week_sun.paid)} kr - park {format_short_number(last_week_parking.paid)} kr",
                "href": "/omsetning/oversikt",
                "tone": "revenue",
            },
            {
                "group": "Omsetning",
                "title": "Samme to uker siden",
                "value": format_short_number(revenue_two_weeks),
                "unit": "kr",
                "detail": f"Sol {format_short_number(two_weeks_sun.paid)} kr - park {format_short_number(two_weeks_parking.paid)} kr",
                "href": "/omsetning/oversikt",
                "tone": "revenue",
            },
            {
                "group": "Omsetning",
                "title": "Uke",
                "value": dashboard_compare_value(revenue_week, revenue_previous_week),
                "unit": "kr",
                "detail": "Denne / forrige uke",
                "href": "/omsetning/oversikt",
                "tone": "revenue",
            },
            {
                "group": "Omsetning",
                "title": "Maned",
                "value": dashboard_compare_value(revenue_month, revenue_previous_month),
                "unit": "kr",
                "detail": "Denne / forrige maned",
                "href": "/omsetning/oversikt",
                "tone": "revenue",
            },
            {
                "group": "Soling",
                "title": "Soling i dag",
                "value": dashboard_compare_value(today_sun.sessions, yesterday_sun.sessions),
                "unit": "stk",
                "detail": f"{format_short_number(today_sun.minutes / 60, 1)} t - til {cutoff_label(sun_today_cutoff, today)}",
                "href": f"/soling/dagslinje?day={today.isoformat()}",
                "tone": "sun2",
            },
            {
                "group": "Soling",
                "title": "Samme tid forrige uke",
                "value": format_short_number(same_time_sun.sessions),
                "unit": "stk",
                "detail": f"{format_short_number(same_time_sun.paid)} kr til {cutoff_label(sun_last_week_same_cutoff, today)}",
                "href": "/soling/dagslinje",
                "tone": "sun2",
            },
            {
                "group": "Soling",
                "title": "Samme dag forrige uke",
                "value": format_short_number(last_week_sun.sessions),
                "unit": "stk",
                "detail": f"{format_short_number(last_week_sun.paid)} kr - {format_short_number(last_week_sun.minutes / 60, 1)} t",
                "href": "/soling/dagslinje",
                "tone": "sun2",
            },
            {
                "group": "Soling",
                "title": "Samme to uker siden",
                "value": format_short_number(two_weeks_sun.sessions),
                "unit": "stk",
                "detail": f"{format_short_number(two_weeks_sun.paid)} kr - {format_short_number(two_weeks_sun.minutes / 60, 1)} t",
                "href": "/soling/dagslinje",
                "tone": "sun2",
            },
            {
                "group": "Soling",
                "title": "Sol uke",
                "value": dashboard_compare_value(week_sun.sessions, previous_week_sun.sessions),
                "unit": "stk",
                "detail": f"{dashboard_money_compare(week_sun.paid, previous_week_sun.paid)} denne / forrige",
                "href": "/soling/prognose",
                "tone": "sun2",
            },
            {
                "group": "Soling",
                "title": "Sol mnd",
                "value": dashboard_compare_value(month_sun.sessions, previous_month_sun.sessions),
                "unit": "stk",
                "detail": f"{dashboard_money_compare(month_sun.paid, previous_month_sun.paid)} denne / forrige",
                "href": "/soling/oversikt",
                "tone": "sun2",
            },
            {
                "group": "Parkering",
                "title": "Parkering i dag",
                "value": dashboard_compare_value(today_parking.sessions, yesterday_parking.sessions),
                "unit": "stk",
                "detail": f"{format_short_number(today_parking.paid)} kr til {cutoff_label(parking_today_cutoff, today)} - {active_parking or 0} aktive na",
                "href": f"/parkering/parkeringer?day={today.isoformat()}",
                "tone": "parking",
            },
            {
                "group": "Parkering",
                "title": "Samme tid forrige uke",
                "value": format_short_number(same_time_parking.sessions),
                "unit": "stk",
                "detail": f"{format_short_number(same_time_parking.paid)} kr til {cutoff_label(parking_last_week_same_cutoff, today)}",
                "href": "/parkering/parkeringer",
                "tone": "parking",
            },
            {
                "group": "Parkering",
                "title": "Samme dag forrige uke",
                "value": format_short_number(last_week_parking.sessions),
                "unit": "stk",
                "detail": f"{format_short_number(last_week_parking.paid)} kr",
                "href": "/parkering/sammenligning",
                "tone": "parking",
            },
            {
                "group": "Parkering",
                "title": "Samme to uker siden",
                "value": format_short_number(two_weeks_parking.sessions),
                "unit": "stk",
                "detail": f"{format_short_number(two_weeks_parking.paid)} kr",
                "href": "/parkering/sammenligning",
                "tone": "parking",
            },
            {
                "group": "Parkering",
                "title": "Parkering uke",
                "value": dashboard_compare_value(week_parking.sessions, previous_week_parking.sessions),
                "unit": "stk",
                "detail": f"{dashboard_money_compare(week_parking.paid, previous_week_parking.paid)} denne / forrige",
                "href": "/parkering/sammenligning",
                "tone": "parking",
            },
            {
                "group": "Parkering",
                "title": "Parkering mnd",
                "value": dashboard_compare_value(month_parking.sessions, previous_month_parking.sessions),
                "unit": "stk",
                "detail": f"{dashboard_money_compare(month_parking.paid, previous_month_parking.paid)} denne / forrige",
                "href": "/parkering/sammenligning",
                "tone": "parking",
            },
            {
                "group": "Energi",
                "title": "Strom na",
                "value": format_short_number(latest_energy_sample.inntak_w if latest_energy_sample else 0),
                "unit": "W",
                "detail": f"{format_short_number(today_energy_fibaro.kwh, 1)} kWh i dag - {today_energy_fibaro.samples or 0} samples",
                "href": "/energi/status",
                "tone": "energy",
            },
            {
                "group": "Energi",
                "title": "Belysning",
                "value": format_short_number(latest_energy_sample.belysning_w if latest_energy_sample else 0),
                "unit": "W",
                "detail": "Realtime oppsamling",
                "href": "/energi/status",
                "tone": "energy",
            },
            {
                "group": "Energi",
                "title": "Varmepumper",
                "value": format_short_number(latest_energy_sample.varmepumper_w if latest_energy_sample else 0),
                "unit": "W",
                "detail": "Realtime oppsamling",
                "href": "/energi/status",
                "tone": "energy",
            },
            {
                "group": "Energi",
                "title": "Avfukter",
                "value": format_short_number(latest_energy_sample.avfukter_w if latest_energy_sample else 0),
                "unit": "W",
                "detail": "Separat logget og med i Annet",
                "href": "/energi/status",
                "tone": "energy",
            },
            {
                "group": "Energi",
                "title": "Diff",
                "value": format_short_number(latest_energy_sample.differanse_beregnet_w if latest_energy_sample else 0),
                "unit": "W",
                "detail": "Beregnet fra realtime malere",
                "href": "/energi/status",
                "tone": "energy",
            },
            {
                "group": "Temperatur",
                "title": "Innetemp",
                "value": format_short_number(now_status.get("indoor_avg"), 1),
                "unit": "grader",
                "detail": f"I dag {format_short_number(temp_ranges.min_inne, 1)} - {format_short_number(temp_ranges.max_inne, 1)}",
                "href": "/ventilasjon/temp-logg",
                "tone": "vent",
            },
            {
                "group": "Temperatur",
                "title": "Utetemp",
                "value": format_short_number(now_status.get("outdoor_avg"), 1),
                "unit": "grader",
                "detail": f"I dag {format_short_number(temp_ranges.min_ute, 1)} - {format_short_number(temp_ranges.max_ute, 1)}",
                "href": "/ventilasjon/yr-logg",
                "tone": "weather",
            },
            {
                "group": "Temperatur",
                "title": "Loft",
                "value": format_short_number(latest_sample.temp_loft if latest_sample else None, 1),
                "unit": "grader",
                "detail": f"I dag {format_short_number(temp_ranges.min_loft, 1)} - {format_short_number(temp_ranges.max_loft, 1)}",
                "href": "/ventilasjon/temp-logg",
                "tone": "vent",
            },
            {
                "group": "Temperatur",
                "title": "Kjeller",
                "value": format_short_number(latest_sample.temp_kjeller if latest_sample else None, 1),
                "unit": "grader",
                "detail": f"Fukt {format_short_number(latest_sample.humidity_kjeller if latest_sample else None)}%",
                "href": "/ventilasjon/temp-logg",
                "tone": "vent",
            },
            {
                "group": "Temperatur",
                "title": "Fukt inne",
                "value": format_short_number(latest_sample.humidity_1etg if latest_sample else None),
                "unit": "%",
                "detail": f"2.etg {format_short_number(latest_sample.humidity_2etg if latest_sample else None)}% - VIP {format_short_number(latest_sample.humidity_vip if latest_sample else None)}%",
                "href": "/ventilasjon/temp-logg",
                "tone": "vent",
            },
            {
                "group": "Temperatur",
                "title": "Yr",
                "value": weather_from_rows(latest_yr_sample, latest_light_sample, latest_sample, latest_light) or "-",
                "unit": "",
                "detail": f"Vind {format_short_number(latest_yr_sample.wind_speed if latest_yr_sample else None, 1)} m/s - sky {format_short_number(latest_yr_sample.cloud_area_fraction if latest_yr_sample else None)}%",
                "href": "/ventilasjon/yr-logg",
                "tone": "weather",
            },
            {
                "group": "Lys",
                "title": "Lux",
                "value": format_short_number(now_status.get("lux")),
                "unit": "",
                "detail": f"{sum(1 for item in light_items if item['state'] is True)} pa / {sum(1 for item in light_items if item['state'] is False)} av",
                "href": "/lys/dagslogg-lux",
                "tone": "light",
            },
            {
                "group": "Ventilasjon",
                "title": "Vifter",
                "value": f"{sum(1 for item in fan_items if item['state'] is True)}/{len(fan_items)}",
                "unit": "pa",
                "detail": f"Modus {latest_sample.mode if latest_sample and latest_sample.mode else '-'}",
                "href": "/ventilasjon/dagslogg-temp",
                "tone": "vent",
            },
        ]
        latest_items = [
            {
                "label": "Siste soling",
                "value": latest_soling.started_at.strftime("%H:%M") if latest_soling and latest_soling.started_at else "-",
                "detail": f"Rom {latest_soling.room}" if latest_soling and latest_soling.room else "",
                "href": "/soling/dagslinje",
            },
            {
                "label": "Siste parkering",
                "value": latest_parking.start_time.strftime("%H:%M") if latest_parking and latest_parking.start_time else "-",
                "detail": latest_parking.car_license_number if latest_parking and latest_parking.car_license_number else "",
                "href": "/parkering/parkeringer",
            },
            {
                "label": "Energi sist lest",
                "value": latest_energy_sample.bucket_start.strftime("%H:%M") if latest_energy_sample and latest_energy_sample.bucket_start else "-",
                "detail": f"{format_short_number(latest_energy_sample.inntak_w)} W" if latest_energy_sample else "",
                "href": "/energi/status",
            },
            {
                "label": "Temp sist lest",
                "value": now_status["timestamp"].strftime("%H:%M") if now_status.get("timestamp") else "-",
                "detail": now_status.get("weather") or "",
                "href": "/ventilasjon/temp-logg",
            },
        ]
        grouped_cards = defaultdict(list)
        for card in cards:
            grouped_cards[card["group"]].append(card)
        return templates.TemplateResponse(
            request,
            "status_key_metrics.html",
            {
                "now": now_dt,
                "cards_by_group": dict(grouped_cards),
                "latest_items": latest_items,
                "light_items": light_items,
                "fan_items": fan_items,
                "now_status": now_status,
            },
        )

    @router.get("/api/status/comparison")
    async def api_v2_status_comparison(
        period: str = Query("today"),
        compare: str = Query("previous"),
        anchor: Optional[str] = Query(None),
        references: str = Query("auto"),
    ):
        async_session = dependencies.async_session
        import_status_rows = dependencies.import_status_rows
        status_timeline_lane = dependencies.status_timeline_lane
        now_dt = local_now_naive()
        today = now_dt.date()
        anchor_day = parse_anchor_day(anchor, today)
        async with async_session() as session:
            import_rows = await import_status_rows(session)
            return await build_status_comparison(
                session, import_rows, now_dt, period, compare, anchor_day, references,
                timeline_lane=status_timeline_lane,
            )

    @router.get("/api/omsetning/year-comparison")
    async def api_v2_revenue_year_comparison(year: Optional[str] = Query(None)):
        async_session = dependencies.async_session
        get_parking_summaries = dependencies.get_parking_summaries
        get_sun2_summaries = dependencies.get_sun2_summaries
        now_dt = local_now_naive()
        anchor_year = parse_anchor_year(year, now_dt.year)
        async with async_session() as session:
            sun_summaries = await get_sun2_summaries(session)
            parking_summaries = await get_parking_summaries(session)
        summaries = combine_business_summaries(sun_summaries, parking_summaries)
        return build_revenue_year_comparison(summaries, now_dt, anchor_year)

    @router.get("/api/operations/overview")
    async def api_operations_overview():
        DREAME_EXPECTED_ROBOT_NAME = dependencies.DREAME_EXPECTED_ROBOT_NAME
        LIGHT_TIMELINE_DEVICES = dependencies.LIGHT_TIMELINE_DEVICES
        VENT_TIMELINE_DEVICES = dependencies.VENT_TIMELINE_DEVICES
        api_hc3_doors_status = dependencies.api_hc3_doors_status
        api_unifi_protect_bollards = dependencies.api_unifi_protect_bollards
        async_session = dependencies.async_session
        hc3_fetch_switch_statuses = dependencies.hc3_fetch_switch_statuses
        hc3_switch_config_for_timeline_device = dependencies.hc3_switch_config_for_timeline_device
        latest_cleaning_robot_sample = dependencies.latest_cleaning_robot_sample
        light_sample_state = dependencies.light_sample_state
        minutes_since = dependencies.minutes_since
        operating_window = dependencies.operating_window
        operations_area_status = dependencies.operations_area_status
        operations_metric = dependencies.operations_metric
        operations_recent_door_items = dependencies.operations_recent_door_items
        operations_switch_item = dependencies.operations_switch_item
        ventilation_status_payload = dependencies.ventilation_status_payload
        now_dt = local_now_naive()
        today_start = datetime.combine(now_dt.date(), time.min)
        tomorrow_start = today_start + timedelta(days=1)
        jobs_from = local_naive_to_utc_naive(today_start)
        jobs_to = local_naive_to_utc_naive(tomorrow_start)

        door_task = asyncio.create_task(api_hc3_doors_status(history_limit=20, period_limit=20))
        bollard_task = asyncio.create_task(api_unifi_protect_bollards())
        vent_switch_configs = [
            config
            for device in VENT_TIMELINE_DEVICES
            if (config := hc3_switch_config_for_timeline_device(device)) is not None
        ]
        fan_task = asyncio.create_task(hc3_fetch_switch_statuses(vent_switch_configs))

        async with async_session() as session:
            latest_light = (
                await session.execute(select(OutdoorLightSample).order_by(OutdoorLightSample.bucket_start.desc()).limit(1))
            ).scalars().first()
            latest_ventilation = (
                await session.execute(select(VentilationSample).order_by(VentilationSample.bucket_start.desc()).limit(1))
            ).scalars().first()
            robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
            robots.sort(key=cleaning_robot_sort_key)
            robot_duids = [robot.duid for robot in robots]
            latest_statuses: list[RoborockStatusSample] = []
            latest_telemetry: list[RoborockTelemetrySample] = []
            jobs: list[RoborockCleanJob] = []
            recent_jobs: list[RoborockCleanJob] = []
            if robot_duids:
                latest_status_subquery = (
                    select(
                        RoborockStatusSample.robot_duid.label("robot_duid"),
                        func.max(RoborockStatusSample.id).label("latest_id"),
                    )
                    .where(RoborockStatusSample.robot_duid.in_(robot_duids))
                    .group_by(RoborockStatusSample.robot_duid)
                    .subquery()
                )
                latest_statuses = (
                    await session.execute(
                        select(RoborockStatusSample).join(
                            latest_status_subquery,
                            RoborockStatusSample.id == latest_status_subquery.c.latest_id,
                        )
                    )
                ).scalars().all()
                latest_telemetry_subquery = (
                    select(
                        RoborockTelemetrySample.robot_duid.label("robot_duid"),
                        func.max(RoborockTelemetrySample.id).label("latest_id"),
                    )
                    .where(RoborockTelemetrySample.robot_duid.in_(robot_duids))
                    .group_by(RoborockTelemetrySample.robot_duid)
                    .subquery()
                )
                latest_telemetry = (
                    await session.execute(
                        select(RoborockTelemetrySample).join(
                            latest_telemetry_subquery,
                            RoborockTelemetrySample.id == latest_telemetry_subquery.c.latest_id,
                        )
                    )
                ).scalars().all()
                jobs = (
                    await session.execute(
                        select(RoborockCleanJob)
                        .where(
                            RoborockCleanJob.robot_duid.in_(robot_duids),
                            RoborockCleanJob.begin_at >= jobs_from,
                            RoborockCleanJob.begin_at < jobs_to,
                        )
                        .order_by(RoborockCleanJob.begin_at.desc())
                    )
                ).scalars().all()
                recent_jobs = (
                    await session.execute(
                        select(RoborockCleanJob)
                        .where(RoborockCleanJob.robot_duid.in_(robot_duids))
                        .order_by(
                            RoborockCleanJob.begin_at.desc().nullslast(),
                            RoborockCleanJob.id.desc(),
                        )
                        .limit(5)
                    )
                ).scalars().all()
            active_door_alarms = (
                await session.execute(
                    select(AlarmEvent)
                    .where(AlarmEvent.domain == "doors", AlarmEvent.status == "active")
                    .order_by(AlarmEvent.detected_at.desc())
                    .limit(10)
                )
            ).scalars().all()

        door_result, bollard_result, fan_statuses = await asyncio.gather(
            door_task,
            bollard_task,
            fan_task,
            return_exceptions=True,
        )

        areas: list[Dict[str, Any]] = []
        incidents: list[Dict[str, Any]] = []

        fan_lookup = fan_statuses if isinstance(fan_statuses, dict) else {}
        fan_items = [
            ventilation_status_payload(device, latest_ventilation, fan_lookup.get(str(device.get("key"))))
            for device in VENT_TIMELINE_DEVICES
        ]
        fan_unknown = [item for item in fan_items if item.get("state") is None]
        fan_errors = [item for item in fan_items if item.get("error")]
        vent_updated = normalize_local_naive(
            (latest_ventilation.bucket_start or latest_ventilation.timestamp) if latest_ventilation else None
        )
        vent_age = minutes_since(vent_updated, now_dt)
        vent_issues = [str(item.get("error")) for item in fan_errors if item.get("error")]
        if latest_ventilation is None:
            vent_status, vent_label = "error", "Ingen data"
            vent_issues.append("Ventilasjonsloggeren har ikke levert målinger.")
        elif vent_age is not None and vent_age > 10:
            vent_status, vent_label = "warning", "Data er forsinket"
            vent_issues.append(f"Siste ventilasjonsmåling er {vent_age} minutter gammel.")
        elif fan_errors or fan_unknown:
            vent_status, vent_label = "warning", "Delvis status"
            if fan_unknown:
                vent_issues.append(f"Status mangler for {len(fan_unknown)} vifte(r).")
        else:
            vent_status, vent_label = "ok", "Normal drift"
        for issue in vent_issues:
            incidents.append({"area": "Ventilasjon", "severity": vent_status, "title": issue, "href": "/ventilasjon"})
        fan_on = sum(item.get("state") is True for item in fan_items)
        areas.append(operations_area_status(
            "ventilation",
            "Ventilasjon",
            vent_status,
            vent_label,
            latest_ventilation.mode if latest_ventilation and latest_ventilation.mode else "Styringsmodus er ikke rapportert",
            "/ventilasjon",
            vent_updated,
            [
                operations_metric("Vifter på", f"{fan_on} / {len(fan_items)}"),
                operations_metric("Inne", f"{latest_ventilation.temp_avg_inne:.1f} °C" if latest_ventilation and latest_ventilation.temp_avg_inne is not None else "-"),
                operations_metric("Ute", f"{latest_ventilation.temp_ute:.1f} °C" if latest_ventilation and latest_ventilation.temp_ute is not None else "-"),
                operations_metric("Kjeller", f"{latest_ventilation.humidity_kjeller:.0f} %" if latest_ventilation and latest_ventilation.humidity_kjeller is not None else "-", "luftfuktighet"),
            ],
            [
                {"label": item.get("label"), "value": "På" if item.get("state") is True else "Av" if item.get("state") is False else "Ukjent", "state": "on" if item.get("state") is True else "off" if item.get("state") is False else "unknown"}
                for item in fan_items
            ],
            vent_issues,
        ))

        light_updated = normalize_local_naive((latest_light.bucket_start or latest_light.timestamp) if latest_light else None)
        light_age = minutes_since(light_updated, now_dt)
        light_items = [
            operations_switch_item(device["name"], light_sample_state(latest_light, device) if latest_light else None)
            for device in LIGHT_TIMELINE_DEVICES
        ]
        light_unknown = sum(item["state"] == "unknown" for item in light_items)
        light_issues: list[str] = []
        if latest_light is None:
            light_status, light_label = "error", "Ingen data"
            light_issues.append("Lysloggeren har ikke levert målinger.")
        elif light_age is not None and light_age > 10:
            light_status, light_label = "warning", "Data er forsinket"
            light_issues.append(f"Siste lysmåling er {light_age} minutter gammel.")
        elif light_unknown:
            light_status, light_label = "warning", "Delvis status"
            light_issues.append(f"Status mangler for {light_unknown} lyspunkt(er).")
        else:
            light_status, light_label = "ok", "Normal drift"
        for issue in light_issues:
            incidents.append({"area": "Lys", "severity": light_status, "title": issue, "href": "/lys"})
        light_on = sum(item["state"] == "on" for item in light_items)
        areas.append(operations_area_status(
            "lights",
            "Lys",
            light_status,
            light_label,
            latest_light.mode if latest_light and latest_light.mode else "Automatisk lysstyring",
            "/lys",
            light_updated,
            [
                operations_metric("Lyspunkter på", f"{light_on} / {len(light_items)}"),
                operations_metric("Lux", f"{latest_light.lux:.0f}" if latest_light and latest_light.lux is not None else "-"),
                operations_metric("Modus", latest_light.mode if latest_light and latest_light.mode else "-"),
            ],
            light_items,
            light_issues,
        ))

        if isinstance(door_result, Exception):
            door_summary: Dict[str, Any] = {}
            door_rows: list[Dict[str, Any]] = []
            door_status, door_label = "error", "Status utilgjengelig"
            door_issues = [f"Dørstatus kunne ikke hentes: {door_result}"]
            door_updated = None
        else:
            door_summary = door_result.get("summary") or {}
            door_rows = door_result.get("doors") or []
            door_updated = normalize_local_naive(datetime.fromisoformat(door_result["generatedAt"])) if door_result.get("generatedAt") else None
            unknown_doors = [door for door in door_rows if door.get("isConfigured") and door.get("state") == "unknown"]
            abnormal_doors = [
                door for door in door_rows
                if door.get("isConfigured") and door.get("groupKey") != "solrom" and door.get("state") not in {"unknown", door.get("normalState")}
            ]
            door_issues = []
            if active_door_alarms:
                door_status, door_label = "error", f"{len(active_door_alarms)} aktiv alarm"
                door_issues.extend(alarm.title for alarm in active_door_alarms[:3])
            elif abnormal_doors or unknown_doors:
                door_status, door_label = "warning", "Krever oppmerksomhet"
                door_issues.extend(f"{door.get('title')}: {str(door.get('stateLabel') or 'ukjent').lower()}" for door in abnormal_doors[:3])
                if unknown_doors:
                    door_issues.append(f"{len(unknown_doors)} konfigurert dør har ukjent status.")
            else:
                door_status, door_label = "ok", "Normal status"
        for issue in door_issues:
            incidents.append({"area": "Dører", "severity": door_status, "title": issue, "href": "/dorer/alarm" if active_door_alarms else "/dorer"})
        solroom_rows = [door for door in door_rows if door.get("groupKey") == "solrom"]
        other_rows = [door for door in door_rows if door.get("groupKey") != "solrom" and door.get("isConfigured")]
        recent_door_items = [] if isinstance(door_result, Exception) else operations_recent_door_items(door_result)
        areas.append(operations_area_status(
            "doors",
            "Dører",
            door_status,
            door_label,
            door_summary.get("latestChangeText") or "Status fra magnetsensorene",
            "/dorer",
            door_updated,
            [
                operations_metric("Solrom ledige", sum(door.get("state") == "open" for door in solroom_rows), f"av {len(solroom_rows)}"),
                operations_metric("Solrom i bruk", sum(door.get("state") == "closed" for door in solroom_rows)),
                operations_metric("Andre åpne", sum(door.get("state") == "open" for door in other_rows), f"av {len(other_rows)}"),
                operations_metric("Alarmer", len(active_door_alarms)),
            ],
            recent_door_items,
            door_issues,
        ))

        if isinstance(bollard_result, Exception):
            bollard_summary: Dict[str, Any] = {}
            bollard_status, bollard_label = "error", "Kontroll utilgjengelig"
            bollard_issues = [f"Pullertkontrollen kunne ikke hentes: {bollard_result}"]
            bollard_updated = None
            bollard_items: list[Dict[str, Any]] = []
        else:
            bollard_summary = bollard_result.get("summary") or {}
            active_incidents = [row for row in (bollard_result.get("incidents") or []) if str(row.get("status") or "").lower() in {"active", "open", "new"}]
            active_count = int(bollard_summary.get("active_incidents") or len(active_incidents))
            bollard_issues = [str(row.get("display_name") or row.get("title") or "Visuelt avvik") for row in active_incidents[:3]]
            if active_count:
                bollard_status, bollard_label = "error", f"{active_count} aktivt avvik"
                if not bollard_issues:
                    bollard_issues.append(f"{active_count} kontrollobjekt krever visuell kontroll.")
            elif not bollard_result.get("runtime", {}).get("last_success_at"):
                bollard_status, bollard_label = "warning", "Venter på kontroll"
                bollard_issues.append("Det finnes ikke et tidspunkt for siste vellykkede bildekontroll.")
            else:
                bollard_status, bollard_label = "ok", "Ingen aktive avvik"
            runtime_at = bollard_result.get("runtime", {}).get("last_success_at")
            bollard_updated = normalize_local_naive(datetime.fromisoformat(runtime_at)) if runtime_at else None
            bollard_items = [
                {"label": row.get("display_name") or row.get("name"), "value": row.get("status") or "Kontrollert", "state": "warning" if row in active_incidents else "ok"}
                for row in (bollard_result.get("asset_monitors") or bollard_result.get("camera_monitors") or [])[:4]
            ]
        for issue in bollard_issues:
            incidents.append({"area": "Pullerter", "severity": bollard_status, "title": issue, "href": "/pullerter"})
        areas.append(operations_area_status(
            "bollards",
            "Pullerter og fasade",
            bollard_status,
            bollard_label,
            "Lokal bildeanalyse og visuell kontroll",
            "/pullerter",
            bollard_updated,
            [
                operations_metric("Kontrollobjekter", int(bollard_summary.get("inspection_objects") or 0)),
                operations_metric("Kameraer", f"{int(bollard_summary.get('connected_cameras') or 0)} / {int(bollard_summary.get('target_cameras') or 0)}"),
                operations_metric("Aktive avvik", int(bollard_summary.get("active_incidents") or 0)),
                operations_metric("AI-profiler", f"{int(bollard_summary.get('ai_profiles_ready') or 0)} / {int(bollard_summary.get('ai_profiles_total') or 0)}"),
            ],
            bollard_items,
            bollard_issues,
        ))

        status_by_robot = {row.robot_duid: row for row in latest_statuses}
        telemetry_by_robot = {row.robot_duid: row for row in latest_telemetry}
        robot_name_by_duid = {robot.duid: robot.name for robot in robots}
        robot_items = []
        cleaning_issues: list[str] = []
        cleaning_updated_values: list[datetime] = []
        for robot in robots:
            telemetry = telemetry_by_robot.get(robot.duid)
            status_row = status_by_robot.get(robot.duid)
            source_row = latest_cleaning_robot_sample(status_row, telemetry)
            source_at = normalize_local_naive(source_row.timestamp) if source_row and source_row.timestamp else None
            if source_at:
                cleaning_updated_values.append(source_at)
            state_name = source_row.state_name if source_row else None
            battery = source_row.battery if source_row else None
            error_code = source_row.error_code if source_row else None
            active = cleaning_robot_is_active(
                source_row.in_cleaning if source_row else None,
                source_row.state_code if source_row else None,
                robot.provider,
            )
            age = minutes_since(source_at, now_dt)
            state_key, state_label = cleaning_robot_operational_state(
                integration_status=robot.integration_status,
                cloud_online=robot.cloud_online,
                last_error=robot.last_error,
                error_code=error_code,
                data_age_minutes=age,
                active=active,
                active_label=state_name,
                ready_label=state_name,
            )
            if state_key == "error" and robot.cloud_online is False:
                cleaning_issues.append(f"{robot.name} er frakoblet.")
            elif state_key == "error":
                cleaning_issues.append(f"{robot.name}: {robot.last_error or f'feilkode {error_code}'}")
            elif state_key == "warning":
                cleaning_issues.append(f"{robot.name} har ikke levert fersk status.")
            robot_items.append({
                "label": robot.name,
                "value": state_label,
                "detail": f"{battery} %" if battery is not None else robot.model or "",
                "state": state_key,
                "href": f"/renhold/robot/{quote(robot.duid, safe='')}",
            })
        if not any(cleaning_provider(robot.provider) == "dreame" for robot in robots):
            robot_items.append({"label": DREAME_EXPECTED_ROBOT_NAME, "value": "Venter på konto", "detail": "Dreame", "state": "pending", "href": "/renhold/dreame"})
        cleaning_errors = sum(item["state"] == "error" for item in robot_items)
        cleaning_warnings = sum(item["state"] == "warning" for item in robot_items)
        cleaning_active = sum(item["state"] == "active" for item in robot_items)
        if cleaning_errors:
            cleaning_status, cleaning_label = "error", f"{cleaning_errors} robot med feil"
        elif cleaning_warnings:
            cleaning_status, cleaning_label = "warning", "Krever oppmerksomhet"
        elif cleaning_active:
            cleaning_status, cleaning_label = "active", f"{cleaning_active} rengjør nå"
        else:
            cleaning_status, cleaning_label = "ok", "Robotparken er klar"
        for issue in cleaning_issues:
            incidents.append({"area": "Renhold", "severity": cleaning_status, "title": issue, "href": "/renhold"})
        recent_cleaning_jobs = []
        for job in recent_jobs:
            status_key, status_label = roborock_job_status(job.complete, job.error_code, job.end_at)
            recent_cleaning_jobs.append({
                "robotName": robot_name_by_duid.get(job.robot_duid, job.robot_duid),
                "startedAt": api_local_iso(utc_naive_to_local_naive(job.begin_at)),
                "endedAt": api_local_iso(utc_naive_to_local_naive(job.end_at)),
                "durationMinutes": job.duration_minutes,
                "areaM2": job.cleaned_area_m2 if job.cleaned_area_m2 is not None else job.area_m2,
                "status": status_key,
                "statusLabel": status_label,
                "href": f"/renhold/robot/{quote(job.robot_duid, safe='')}",
            })
        areas.append(operations_area_status(
            "cleaning",
            "Renhold",
            cleaning_status,
            cleaning_label,
            "Roborock og Dreame samlet",
            "/renhold",
            max(cleaning_updated_values, default=None),
            [
                operations_metric("Tilkoblet", sum(item["state"] not in {"pending", "error"} for item in robot_items), f"av {len(robot_items)}"),
                operations_metric("Rengjør nå", cleaning_active),
                operations_metric("Jobber i dag", len(jobs)),
                operations_metric("Areal i dag", f"{sum(float(job.cleaned_area_m2 if job.cleaned_area_m2 is not None else job.area_m2 or 0) for job in jobs):.0f} m²"),
            ],
            robot_items,
            cleaning_issues,
            recent_cleaning_jobs,
        ))

        critical_count = sum(area["status"] == "error" for area in areas)
        attention_count = sum(area["status"] in {"warning", "unknown"} for area in areas)
        normal_count = len(areas) - critical_count - attention_count
        overall_status = "error" if critical_count else "warning" if attention_count else "ok"
        overall_label = "Kritiske avvik" if critical_count else "Noe krever oppmerksomhet" if attention_count else "Normal drift"
        operating = operating_window(now_dt)
        return {
            "generatedAt": api_local_iso(now_dt),
            "operatingWindow": {
                "label": operating["label"],
                "detail": operating["detail"],
                "open": operating["label"] == "Åpent",
            },
            "summary": {
                "status": overall_status,
                "label": overall_label,
                "normal": normal_count,
                "attention": attention_count,
                "critical": critical_count,
                "total": len(areas),
            },
            "areas": areas,
            "incidents": incidents,
        }

    @router.get("/api/overview")
    async def api_v2_overview(scope: Optional[str] = None):
        LIGHT_TIMELINE_DEVICES = dependencies.LIGHT_TIMELINE_DEVICES
        VENT_TIMELINE_DEVICES = dependencies.VENT_TIMELINE_DEVICES
        api_bool_state = dependencies.api_bool_state
        async_session = dependencies.async_session
        build_now_status = dependencies.build_now_status
        dashboard_compare_value = dependencies.dashboard_compare_value
        dashboard_money_compare = dependencies.dashboard_money_compare
        get_parking_summaries = dependencies.get_parking_summaries
        get_sun2_summaries = dependencies.get_sun2_summaries
        hc3_fetch_switch_statuses = dependencies.hc3_fetch_switch_statuses
        hc3_switch_config_for_timeline_device = dependencies.hc3_switch_config_for_timeline_device
        import_status_rows = dependencies.import_status_rows
        light_sample_state = dependencies.light_sample_state
        minutes_since = dependencies.minutes_since
        operating_window = dependencies.operating_window
        ventilation_status_payload = dependencies.ventilation_status_payload
        weather_from_rows = dependencies.weather_from_rows
        business_only = scope in {"revenue", "parking", "sun"}
        now_dt = local_now_naive()
        today = now_dt.date()
        today_start = datetime.combine(today, time.min)
        tomorrow_start = today_start + timedelta(days=1)
        vent_switch_configs = [
            config
            for device in VENT_TIMELINE_DEVICES
            if (config := hc3_switch_config_for_timeline_device(device)) is not None
        ] if not business_only else []
        vent_status_task = asyncio.create_task(hc3_fetch_switch_statuses(vent_switch_configs)) if not business_only else None
        async with async_session() as session:
            latest_light_sample = None
            latest_light = None
            latest_sample = None
            latest_yr_sample = None
            if not business_only:
                latest_light_sample = (
                    await session.execute(select(OutdoorLightSample).order_by(OutdoorLightSample.timestamp.desc()).limit(1))
                ).scalars().first()
                latest_light = (
                    await session.execute(select(OutdoorLightEvent).order_by(OutdoorLightEvent.timestamp.desc()).limit(1))
                ).scalars().first()
                latest_sample = (
                    await session.execute(select(VentilationSample).order_by(VentilationSample.timestamp.desc()).limit(1))
                ).scalars().first()
                latest_yr_sample = (
                    await session.execute(select(YrForecastSample).order_by(YrForecastSample.timestamp.desc()).limit(1))
                ).scalars().first()
            import_rows = await import_status_rows(session)
            comparison_plan = overview_comparison_plan(import_rows, now_dt)
            comparison_data = await load_overview_comparisons(session, comparison_plan)
            active_parking = 0
            latest_parking = None
            latest_soling = None
            latest_energy_sample = None
            today_energy_fibaro = None
            if not business_only:
                active_parking = (
                    await session.execute(
                        select(func.count(ParkingSession.id)).where(
                            ParkingSession.start_time <= now_dt,
                            or_(
                                ParkingSession.end_time.is_(None),
                                ParkingSession.end_time >= now_dt,
                                func.lower(func.coalesce(ParkingSession.status, "")) == "ongoing",
                            ),
                        )
                    )
                ).scalar_one()
                latest_parking = (
                    await session.execute(
                        select(ParkingSession)
                        .where(ParkingSession.start_time >= today_start, ParkingSession.start_time < tomorrow_start)
                        .order_by(ParkingSession.start_time.desc())
                        .limit(1)
                    )
                ).scalars().first()
                latest_soling = (
                    await session.execute(
                        select(Sun2TanningSession)
                        .where(Sun2TanningSession.stat_date == today)
                        .order_by(Sun2TanningSession.started_at.desc())
                        .limit(1)
                    )
                ).scalars().first()
                latest_energy_sample = (
                    await session.execute(select(EnergyFibaroSample).order_by(EnergyFibaroSample.bucket_start.desc()).limit(1))
                ).scalars().first()
                today_energy_fibaro = (
                    await session.execute(
                        select(
                            func.coalesce(func.sum(EnergyFibaroSample.inntak_delta_kwh), 0).label("kwh"),
                            func.count(EnergyFibaroSample.id).label("samples"),
                        ).where(EnergyFibaroSample.bucket_start >= today_start, EnergyFibaroSample.bucket_start < tomorrow_start)
                    )
                ).one()
            revenue_sun_summaries = await get_sun2_summaries(session)
            revenue_parking_summaries = await get_parking_summaries(session)

        now_status = build_now_status(latest_sample, latest_light_sample, latest_light, latest_yr_sample)
        operating = operating_window(now_dt)
        import_counts = {
            "ok": sum(1 for row in import_rows if row["status"] == "ok"),
            "warn": sum(1 for row in import_rows if row["status"] == "warn"),
            "bad": sum(1 for row in import_rows if row["status"] == "bad"),
            "total": len(import_rows),
        }
        status_periods = build_overview_cards(comparison_data, revenue_sun_summaries, revenue_parking_summaries, scope)
        if business_only:
            services = [
                {
                    "sourceNo": row["source_no"],
                    "jobName": row["job_name"],
                    "label": row["title"],
                    "status": row["status"] if row["status"] in {"ok", "warn", "bad"} else "unknown",
                    "detail": row["age"] or row["status_text"],
                    "ageMinutes": minutes_since(row["last_success_at"]) if row.get("last_success_at") else None,
                    "lastSuccessAt": api_local_iso(row.get("last_success_at")),
                    "nextExpectedAt": api_local_iso(row.get("next_expected_at")),
                }
                for row in import_rows
            ]
            return {
                "generatedAt": api_local_iso(now_dt),
                "statusPeriods": status_periods,
                "services": services,
            }

        today_sun = comparison_data.sun_at_cutoff["today"]
        yesterday_sun = comparison_data.sun_full["yesterday"]
        week_sun = comparison_data.sun_at_cutoff["week"]
        previous_week_sun = comparison_data.sun_full["previous_week"]
        month_sun = comparison_data.sun_at_cutoff["month"]
        previous_month_sun = comparison_data.sun_full["previous_month"]
        today_parking = comparison_data.parking["today"]
        yesterday_parking = comparison_data.parking["yesterday_full"]
        last_week_parking = comparison_data.parking["last_week_same_day_full"]
        revenue_today, revenue_week, revenue_month = (item["total"] for item in status_periods[:3])
        revenue_yesterday, revenue_previous_week, revenue_previous_month = (item["previousFullTotal"] for item in status_periods[:3])
        light_items = [
            {"label": device["name"], "state": api_bool_state(light_sample_state(latest_light_sample, device) if latest_light_sample else None)}
            for device in LIGHT_TIMELINE_DEVICES
        ]
        vent_hc3_statuses = await vent_status_task if vent_status_task is not None else {}
        fan_items = [
            ventilation_status_payload(device, latest_sample, vent_hc3_statuses.get(str(device.get("key"))))
            for device in VENT_TIMELINE_DEVICES
        ]
        cards = [
            {"group": "Drift", "title": "\u00c5pning", "value": operating["label"], "detail": operating["detail"], "href": "/status/drift", "tone": "status"},
            {"group": "Drift", "title": "Datakilder", "value": f"{import_counts['ok']}/{import_counts['total']}", "unit": "OK", "detail": f"{import_counts['warn']} treg, {import_counts['bad']} feil/gammel", "href": "/admin/drift", "tone": "status"},
            {"group": "Omsetning", "title": "I dag", "value": dashboard_compare_value(revenue_today, revenue_yesterday), "unit": "kr", "detail": f"Sol {format_short_number(today_sun.paid)} kr - park {format_short_number(today_parking.paid)} kr", "href": "/omsetning/oversikt", "tone": "revenue"},
            {"group": "Omsetning", "title": "Uke", "value": dashboard_compare_value(revenue_week, revenue_previous_week), "unit": "kr", "detail": "Denne / forrige uke", "href": "/omsetning/oversikt", "tone": "revenue"},
            {"group": "Omsetning", "title": "M\u00e5ned", "value": dashboard_compare_value(revenue_month, revenue_previous_month), "unit": "kr", "detail": "Denne / forrige m\u00e5ned", "href": "/omsetning/oversikt", "tone": "revenue"},
            {"group": "Soling", "title": "Soling i dag", "value": dashboard_compare_value(today_sun.sessions, yesterday_sun.sessions), "unit": "stk", "detail": f"{format_short_number(today_sun.minutes / 60, 1)} t - {today_sun.rooms or 0} rom", "href": "/soling", "tone": "sun2"},
            {"group": "Soling", "title": "Sol uke", "value": dashboard_compare_value(week_sun.sessions, previous_week_sun.sessions), "unit": "stk", "detail": f"{dashboard_money_compare(week_sun.paid, previous_week_sun.paid)}", "href": "/soling", "tone": "sun2"},
            {"group": "Parkering", "title": "Parkering i dag", "value": dashboard_compare_value(today_parking.sessions, yesterday_parking.sessions), "unit": "stk", "detail": f"{format_short_number(today_parking.paid)} kr - {active_parking or 0} aktive n\u00e5", "href": "/parkering", "tone": "parking"},
            {"group": "Parkering", "title": "Samme dag forrige uke", "value": format_short_number(last_week_parking.sessions), "unit": "stk", "detail": f"{format_short_number(last_week_parking.paid)} kr", "href": "/parkering", "tone": "parking"},
            {"group": "Energi", "title": "Str\u00f8m n\u00e5", "value": format_short_number(latest_energy_sample.inntak_w if latest_energy_sample else 0), "unit": "W", "detail": f"{format_short_number(today_energy_fibaro.kwh, 1)} kWh i dag - {today_energy_fibaro.samples or 0} samples", "href": "/energi", "tone": "energy"},
            {"group": "Energi", "title": "Diff", "value": format_short_number(latest_energy_sample.differanse_beregnet_w if latest_energy_sample else 0), "unit": "W", "detail": "Beregnet fra realtime m\u00e5lere", "href": "/energi", "tone": "energy"},
            {"group": "Temperatur", "title": "Innetemp", "value": format_short_number(now_status.get("indoor_avg"), 1), "unit": "grader", "detail": f"Ute {format_short_number(now_status.get('outdoor_avg'), 1)} grader", "href": "/ventilasjon", "tone": "vent"},
            {"group": "Temperatur", "title": "Kjeller", "value": format_short_number(latest_sample.temp_kjeller if latest_sample else None, 1), "unit": "grader", "detail": f"Fukt {format_short_number(latest_sample.humidity_kjeller if latest_sample else None)}%", "href": "/ventilasjon", "tone": "vent"},
            {"group": "V\u00e6r", "title": "Yr", "value": weather_from_rows(latest_yr_sample, latest_light_sample, latest_sample, latest_light) or "-", "detail": f"Vind {format_short_number(latest_yr_sample.wind_speed if latest_yr_sample else None, 1)} m/s - sky {format_short_number(latest_yr_sample.cloud_area_fraction if latest_yr_sample else None)}%", "href": "/ventilasjon", "tone": "weather"},
        ]
        latest_items = [
            {"label": "Siste soling", "value": latest_soling.started_at.strftime("%H:%M") if latest_soling and latest_soling.started_at else "-", "detail": f"Rom {latest_soling.room}" if latest_soling and latest_soling.room else "", "href": "/soling"},
            {"label": "Siste parkering", "value": latest_parking.start_time.strftime("%H:%M") if latest_parking and latest_parking.start_time else "-", "detail": latest_parking.car_license_number if latest_parking and latest_parking.car_license_number else "", "href": "/parkering"},
            {"label": "Energi sist lest", "value": latest_energy_sample.bucket_start.strftime("%H:%M") if latest_energy_sample and latest_energy_sample.bucket_start else "-", "detail": f"{format_short_number(latest_energy_sample.inntak_w)} W" if latest_energy_sample else "", "href": "/energi"},
            {"label": "Temp sist lest", "value": now_status["timestamp"].strftime("%H:%M") if now_status.get("timestamp") else "-", "detail": now_status.get("weather") or "", "href": "/ventilasjon"},
        ]
        services = [
            {
                "sourceNo": row["source_no"],
                "jobName": row["job_name"],
                "label": row["title"],
                "status": row["status"] if row["status"] in {"ok", "warn", "bad"} else "unknown",
                "detail": row["age"] or row["status_text"],
                "ageMinutes": minutes_since(row["last_success_at"]) if row.get("last_success_at") else None,
                "lastSuccessAt": api_local_iso(row.get("last_success_at")),
                "nextExpectedAt": api_local_iso(row.get("next_expected_at")),
            }
            for row in import_rows
        ]
        return {
            "generatedAt": api_local_iso(now_dt),
            "operatingWindow": {"label": operating["label"], "detail": operating["detail"], "open": operating["label"] == "Åpent"},
            "cards": cards,
            "statusPeriods": status_periods,
            "latestItems": latest_items,
            "services": services,
            "lightItems": light_items,
            "fanItems": fan_items,
        }

    @router.get("/api/revenue/month")
    async def api_v2_revenue_month(month: Optional[str] = None):
        api_revenue_day = dependencies.api_revenue_day
        build_revenue_month_context = dependencies.build_revenue_month_context
        context = await build_revenue_month_context(month)
        summary = context["summary"]
        return {
            "summary": {
                "label": summary["label"],
                "month": summary["month"],
                "previousMonth": summary["previous_month"],
                "nextMonth": summary["next_month"],
                "currentMonth": summary["current_month"],
                "total": summary["total"],
                "sol": summary["sol"],
                "parking": summary["parking"],
                "solCount": summary["sol_count"],
                "parkingCount": summary["parking_count"],
                "averageDayCount": summary["average_day_count"],
                "averagePerDay": summary["average_per_day"],
                "maxTotal": summary["max_total"],
                "topDay": api_revenue_day(summary["top_day"]) if summary["top_day"] else None,
                "todayRow": api_revenue_day(summary["today_row"]) if summary["today_row"] else None,
            },
            "rows": [api_revenue_day(row) for row in context["rows"]],
        }

    @router.get("/api/settlements/{settlement_id}")
    async def api_v2_settlement_detail(settlement_id: int):
        async_session = dependencies.async_session
        async with async_session() as session:
            row = await session.get(SettlementImport, settlement_id)
            if not row or row.provider != PARKING_SETTLEMENT_PROVIDER:
                raise HTTPException(status_code=404, detail="Oppgjør ikke funnet")
            return await settlement_detail_payload(session, row)

    @router.get("/api/settlements/{settlement_id}/attachment")
    async def api_v2_settlement_attachment(settlement_id: int, download: bool = False):
        async_session = dependencies.async_session
        async with async_session() as session:
            row = await session.get(SettlementImport, settlement_id)
            if not row or row.provider != PARKING_SETTLEMENT_PROVIDER:
                raise HTTPException(status_code=404, detail="Oppgjør ikke funnet")
            filename = row.attachment_filename or f"oppgjor-{row.id}"
            content_type = row.attachment_content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
            disposition_type = "attachment" if download else "inline"
            quoted_filename = quote(filename)
            return Response(
                content=row.attachment_bytes,
                media_type=content_type,
                headers={
                    "Content-Disposition": f"{disposition_type}; filename*=UTF-8''{quoted_filename}",
                    "Cache-Control": "private, max-age=300",
                },
            )

    @router.get("/status/omsetning", response_class=HTMLResponse)
    async def status_revenue_month_view(request: Request, month: Optional[str] = None):
        build_revenue_month_context = dependencies.build_revenue_month_context
        templates = dependencies.templates
        context = await build_revenue_month_context(month)
        return templates.TemplateResponse(
            request,
            "status_revenue_month.html",
            {
                "rows": context["rows"],
                "summary": context["summary"],
            },
        )

    @router.get("/status/statistikk", response_class=HTMLResponse)
    async def status_statistics_view(request: Request):
        async_session = dependencies.async_session
        get_parking_summaries = dependencies.get_parking_summaries
        get_sun2_summaries = dependencies.get_sun2_summaries
        templates = dependencies.templates
        async with async_session() as session:
            sun_summaries = await get_sun2_summaries(session)
            parking_summaries = await get_parking_summaries(session)
        combined_stats = combine_business_summaries(sun_summaries, parking_summaries)
        return templates.TemplateResponse(
            request,
            "status_statistics.html",
            {"combined_stats": combined_stats},
        )

    @router.get("/status/datakilder", response_class=HTMLResponse)
    async def import_status_view(request: Request):
        async_session = dependencies.async_session
        import_status_rows = dependencies.import_status_rows
        templates = dependencies.templates
        async with async_session() as session:
            rows = await import_status_rows(session)
            runs = (
                await session.execute(
                    select(ImportJobRun)
                    .where(ImportJobRun.job_name.in_(list(IMPORT_JOB_DEFINITIONS)))
                    .where(
                        or_(
                            ImportJobRun.job_name != "easypark_parking_import",
                            ImportJobRun.source != "EasyPark downloader",
                            ImportJobRun.ok.is_(False),
                        )
                    )
                    .order_by(ImportJobRun.finished_at.desc())
                    .limit(80)
                )
            ).scalars().all()
        counts = {
            "ok": sum(1 for row in rows if row["status"] == "ok"),
            "warn": sum(1 for row in rows if row["status"] == "warn"),
            "bad": sum(1 for row in rows if row["status"] == "bad"),
            "total": len(rows),
        }
        return templates.TemplateResponse(
            request,
            "import_status.html",
            {"rows": rows, "runs": runs, "counts": counts, "source_numbers": IMPORT_JOB_NUMBER_BY_NAME},
        )

    @router.get("/status/dagslinje", response_class=HTMLResponse)
    async def day_view(request: Request, day: Optional[str] = None, zoom: Optional[str] = "all"):
        DAY_ZOOM_OPTIONS = dependencies.DAY_ZOOM_OPTIONS
        VENT_TIMELINE_DEVICES = dependencies.VENT_TIMELINE_DEVICES
        build_light_timeline_group = dependencies.build_light_timeline_group
        build_timeline_group = dependencies.build_timeline_group
        day_zoom_window = dependencies.day_zoom_window
        parse_day = dependencies.parse_day
        percent_between = dependencies.percent_between
        templates = dependencies.templates
        selected_day = parse_day(day)
        zoom_config, window_start, window_end, ticks = day_zoom_window(selected_day, zoom)
        now_local = local_now_naive()
        is_today = selected_day == now_local.date()
        if is_today:
            if now_local < window_start:
                timeline_end = window_start
            elif now_local > window_end:
                timeline_end = window_end
            else:
                timeline_end = now_local
        else:
            timeline_end = window_end
        now_marker = percent_between(now_local, window_start, window_end) if is_today and window_start <= now_local <= window_end else None
        light_items = await build_light_timeline_group(window_start, window_end, timeline_end)
        vent_items = await build_timeline_group(VentilationEvent, VENT_TIMELINE_DEVICES, "ventilasjon", window_start, window_end, timeline_end)
        return templates.TemplateResponse(
            request,
            "day.html",
            {
                "selected_day": selected_day.isoformat(),
                "prev_day": (selected_day - timedelta(days=1)).isoformat(),
                "next_day": (selected_day + timedelta(days=1)).isoformat(),
                "zoom": zoom_config["key"],
                "zoom_label": zoom_config["label"],
                "zoom_options": DAY_ZOOM_OPTIONS,
                "is_today": is_today,
                "now_marker": now_marker,
                "now_label": now_local.strftime("%H:%M") if is_today else "",
                "light_items": light_items,
                "vent_items": vent_items,
                "ticks": ticks,
            },
        )

    return RouterBundle(router, {
        "api_operations_overview": api_operations_overview,
        "api_v2_overview": api_v2_overview,
        "api_v2_revenue_month": api_v2_revenue_month,
        "api_v2_revenue_year_comparison": api_v2_revenue_year_comparison,
        "api_v2_settlement_attachment": api_v2_settlement_attachment,
        "api_v2_settlement_detail": api_v2_settlement_detail,
        "api_v2_status_comparison": api_v2_status_comparison,
        "day_view": day_view,
        "import_status_view": import_status_view,
        "index": index,
        "status_key_metrics_view": status_key_metrics_view,
        "status_revenue_month_view": status_revenue_month_view,
        "status_statistics_view": status_statistics_view,
    }, dependencies)
