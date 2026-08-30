"""Parking services with explicit process dependencies."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from dateutil import parser as dtparser
from fastapi import Request
from fibaro_core.models import ForecastSnapshot
from fibaro_core.models import ParkingSession
from fibaro_core.models import ParkingVehicle
from fibaro_core.models import ParkingVehicleDetails
from fibaro_core.services.comparisons.windows import status_timeline_position
from fibaro_core.services.forecasts import builders as forecast_builders
from fibaro_core.services.forecasts.snapshots import forecast_chart_time_label
from fibaro_core.services.forecasts.snapshots import forecast_snapshot_stamp
from fibaro_core.services.forecasts.snapshots import save_forecast_snapshots
from fibaro_core.services.presentation import api_chart
from fibaro_core.services.presentation import api_table
from fibaro_core.services.presentation import format_short_number
from fibaro_core.services.summaries.periods import add_months
from fibaro_core.services.summaries.periods import month_label
from io import StringIO
from parking_vehicle_helpers import CAR_INFO_IMPORT_JOB_BY_COUNTRY
from parking_vehicle_helpers import DANISH_LICENSE_PLATE_SQL_REGEX
from parking_vehicle_helpers import SWEDISH_LICENSE_PLATE_SQL_REGEX
from parking_vehicle_helpers import car_info_confirmed_foreign
from parking_vehicle_helpers import car_info_confirmed_swedish
from parking_vehicle_helpers import car_info_country_code
from parking_vehicle_helpers import car_info_field_value
from parking_vehicle_helpers import car_info_import_ok
from parking_vehicle_helpers import car_info_lookup_country_code
from parking_vehicle_helpers import car_info_status_label
from parking_vehicle_helpers import compact_plate
from parking_vehicle_helpers import compact_plate_sql
from parking_vehicle_helpers import first_value
from parking_vehicle_helpers import is_danish_license_plate
from parking_vehicle_helpers import is_supported_foreign_license_plate
from parking_vehicle_helpers import is_swedish_license_plate
from parking_vehicle_helpers import normalize_plate
from parking_vehicle_helpers import parking_current_ownership_warning
from parking_vehicle_helpers import parking_day_time_label
from parking_vehicle_helpers import parking_vehicle_display_year
from parking_vehicle_helpers import parking_vehicle_summary
from parking_vehicle_helpers import svv_current_ownership_at
from parking_vehicle_helpers import svv_detail_values
from sqlalchemy import and_
from sqlalchemy import case
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import text as sql_text
from sqlalchemy import tuple_
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from time_formatting import LOCAL_TZ
from time_formatting import api_local_iso
from time_formatting import local_now_naive
from time_formatting import normalize_local_naive
from time_formatting import parse_datetime
from typing import Any
from typing import Any, Callable
from typing import Dict
from typing import Mapping
from typing import Optional
from unifi_protect import unifi_protect_parking_timelapse_url
from urllib.parse import quote
from urllib.parse import quote_plus
from urllib.parse import urlencode
from value_parsing import float_or_zero
from value_parsing import int_or_zero
import asyncio
import csv
import json
import math
import re
import urllib.request


@dataclass
class Dependencies:
    CAR_INFO_APP_TOKEN: Any
    CAR_INFO_AUTO_TRIGGER_ENABLED: Any
    CAR_INFO_AUTO_TRIGGER_MAX_PER_SVV_RUN: Any
    CAR_INFO_CANDIDATE_RETRY_HOURS: Any
    CAR_INFO_CANDIDATE_TRANSIENT_RETRY_MINUTES: Any
    CAR_INFO_LOOKUP_TIMEOUT_SECONDS: Any
    CAR_INFO_LOOKUP_URL: Any
    EASYPARK_DOWNLOADER_URL: Any
    EASYPARK_REQUIRED_COLUMNS: Any
    PARKING_OCCUPANCY_SCALE_MAX: Any
    PARKING_TIMELINE_CAPACITY: Any
    PARKING_TIMELINE_ROWS: Any
    PARKING_TIME_PERIOD_OPTIONS: Any
    PARKING_TIME_WEEKDAYS: Any
    PARKING_WEEKLY_AVERAGE_PERIOD_OPTIONS: Any
    SUMMARY_CACHE: Any
    SVV_API_AUTH_HEADER: Any
    SVV_API_AUTH_PREFIX: Any
    SVV_API_KEY: Any
    SVV_API_URL: Any
    SVV_PERMANENT_NO_DATA_STATUSES: Any
    SVV_RETRY_AFTER_HOURS: Any
    SVV_SYNC_BATCH_SIZE: Any
    SVV_SYNC_INTERVAL_MINUTES: Any
    SVV_TRANSIENT_RETRY_AFTER_MINUTES: Any
    SVV_TRANSIENT_STATUSES: Any
    api_filter_value: Callable[..., Any]
    async_session: Callable[..., Any]
    clear_summary_cache: Callable[..., Any]
    exact_search_text: Callable[..., Any]
    exact_word_match: Callable[..., Any]
    get_parking_summaries: Callable[..., Any]
    is_not_found_marker: Callable[..., Any]
    parse_day: Callable[..., Any]
    parse_optional_date: Callable[..., Any]
    record_import_job: Callable[..., Any]
    require_settings_access: Callable[..., Any]


def create_service(dependencies: Dependencies):
    SVV_SYNC_BATCH_SIZE = dependencies.SVV_SYNC_BATCH_SIZE

    def has_car_info_app_access(request: Request) -> bool:
        CAR_INFO_APP_TOKEN = dependencies.CAR_INFO_APP_TOKEN
        token = (request.headers.get("x-car-info-token") or request.query_params.get("car_info_token") or "").strip()
        return bool(CAR_INFO_APP_TOKEN and token and token == CAR_INFO_APP_TOKEN)

    def is_car_info_app_request_path(path: str) -> bool:
        return path == "/api/parkering/kjoretoy/car-info-kandidater" or bool(
            re.fullmatch(r"/api/parkering/kjoretoy/[A-Za-z0-9]+/car-info", path or "")
        )

    def require_settings_or_car_info_access(request: Request):
        require_settings_access = dependencies.require_settings_access
        if has_car_info_app_access(request):
            return None
        return require_settings_access(request)

    def parking_departure_slot_delta_minutes(row: ParkingSession) -> Optional[int]:
        if not row.start_time or not row.end_time:
            return None
        status = (row.status or "").strip().lower()
        if status in {"ongoing", "active", "aktiv", "pågående"}:
            return None
        actual_minutes = (row.end_time - row.start_time).total_seconds() / 60
        if actual_minutes < 0:
            return None
        paid_slot_minutes = math.ceil(actual_minutes / 30) * 30 if actual_minutes else 0
        return int(round(actual_minutes - paid_slot_minutes))

    def status_parking_timeline_event(row: ParkingSession, period_start: datetime, lane_end: datetime, axis_seconds: float) -> Optional[Dict[str, Any]]:
        start_at = normalize_local_naive(row.start_time)
        if not start_at:
            return None
        end_at = normalize_local_naive(row.end_time)
        if not end_at:
            end_at = start_at + timedelta(minutes=float_or_zero(row.parking_time_min) or 15)
        if end_at <= start_at:
            end_at = start_at + timedelta(minutes=max(1.0, float_or_zero(row.parking_time_min) or 1.0))
        position = status_timeline_position(start_at, end_at, period_start, lane_end, axis_seconds)
        if not position:
            return None
        paid = float_or_zero(row.fee_inc_vat)
        plate = str(row.car_license_number or "").strip()
        title_parts = [f"{start_at:%d.%m %H:%M}-{end_at:%H:%M}", f"{float_or_zero(row.parking_time_min):.0f} min"]
        if plate:
            title_parts.append(plate)
        if row.parking_area:
            title_parts.append(str(row.parking_area))
        if paid:
            title_parts.append(f"{paid:.0f} kr")
        href = f"/parkering/parkeringer?day={start_at.date().isoformat()}"
        if plate:
            href += f"&plate={quote_plus(plate)}"
        return {
            "id": f"parking-{row.id}",
            "kind": "parking",
            "left": position["left"],
            "width": position["width"],
            "label": plate or str(row.area_number),
            "title": " | ".join(title_parts),
            "start": api_local_iso(start_at),
            "end": api_local_iso(end_at),
            "amount": paid,
            "href": href,
        }

    async def build_parking_forecast(session, today: date, now_local: datetime) -> Dict[str, Any]:
        SUMMARY_CACHE = dependencies.SUMMARY_CACHE
        get_parking_summaries = dependencies.get_parking_summaries
        return await forecast_builders.build_parking_forecast(
            session, today, now_local, cache=SUMMARY_CACHE, summaries_getter=get_parking_summaries,
        )

    async def save_parking_forecast_after_import(session, created_by: str = "EasyPark import") -> Dict[str, Any]:
        clear_summary_cache = dependencies.clear_summary_cache
        clear_summary_cache("parking")
        now_local = datetime.now(LOCAL_TZ)
        forecast = await build_parking_forecast(session, now_local.date(), now_local)
        await save_forecast_snapshots(session, "parking", forecast, created_by)
        day_forecast = (forecast.get("day") or {}).get("forecast") or {}
        month_forecast = (forecast.get("month") or {}).get("forecast") or {}
        year_forecast = (forecast.get("year") or {}).get("forecast") or {}
        return {
            "generated_at": api_local_iso(forecast.get("generated_at")),
            "day": {
                "sessions": round(float_or_zero(day_forecast.get("sessions")), 1),
                "paid": round(float_or_zero(day_forecast.get("paid")), 2),
            },
            "month": {
                "sessions": round(float_or_zero(month_forecast.get("sessions")), 1),
                "paid": round(float_or_zero(month_forecast.get("paid")), 2),
            },
            "year": {
                "sessions": round(float_or_zero(year_forecast.get("sessions")), 1),
                "paid": round(float_or_zero(year_forecast.get("paid")), 2),
            },
        }

    def api_parking_forecast_evolution_chart(rows: list[ForecastSnapshot]) -> Optional[Dict[str, Any]]:
        if not rows:
            return None
        ordered = sorted(rows, key=lambda row: (forecast_snapshot_stamp(row) or datetime.min, row.id or 0))
        groups: Dict[str, Dict[str, Any]] = {}
        for row in ordered:
            stamp_value = forecast_snapshot_stamp(row)
            key = stamp_value.isoformat() if stamp_value else str(row.id)
            group = groups.setdefault(key, {"stamp": stamp_value, "rows": {}})
            group["rows"][row.period_type] = row

        period_labels = {"day": "Dag", "month": "Måned", "year": "År"}
        period_colors = {"day": "#4e8793", "month": "#d59a18", "year": "#071943"}
        group_items = list(groups.values())
        x_values = [forecast_chart_time_label(item["stamp"]) for item in group_items]

        def series_for(field: str, unit: str) -> list[Dict[str, Any]]:
            series = []
            for period_type in ("day", "month", "year"):
                values = []
                for item in group_items:
                    row = item["rows"].get(period_type)
                    values.append(round(float_or_zero(getattr(row, field, None)), 2) if row else None)
                series.append(
                    {
                        "name": period_labels[period_type],
                        "data": values,
                        "color": period_colors[period_type],
                        "unit": unit,
                    }
                )
            return series

        revenue_series = series_for("forecast_paid", "kr")
        return api_chart(
            "Prognoseutvikling parkering",
            x_values,
            revenue_series,
            "Lagrede prognoser over tid. Nytt punkt lagres etter hver EasyPark-import.",
            "line",
            340,
            metrics=[
                {"key": "revenue", "label": "Omsetning", "unit": "kr", "series": revenue_series},
                {"key": "count", "label": "Antall", "unit": "stk", "series": series_for("forecast_sessions", "stk")},
            ],
            default_metric="revenue",
        )

    async def fallback_car_info_import_status(session, job_name: str) -> Dict[str, Any]:
        country_code = next(
            (country for country, current_job_name in CAR_INFO_IMPORT_JOB_BY_COUNTRY.items() if current_job_name == job_name),
            "",
        )
        if not country_code:
            return {}
        rows = (
            await session.execute(
                select(ParkingVehicle)
                .where(ParkingVehicle.car_info_fetched_at.isnot(None))
                .order_by(ParkingVehicle.car_info_fetched_at.desc())
                .limit(500)
            )
        ).scalars().all()
        row = next((vehicle for vehicle in rows if car_info_lookup_country_code(vehicle.car_info_data, vehicle.plate) == country_code), None)
        if not row:
            return {"message": "Ingen oppslag registrert ennå"}
        payload = {
            "message": f"{row.plate}: {car_info_status_label(row.car_info_status, row.car_info_data)}",
            "records_total": 1,
            "records_imported": 1 if row.car_info_status == 200 and car_info_confirmed_foreign(row.car_info_data) else 0,
        }
        if car_info_import_ok(row.car_info_status):
            payload["last_success_at"] = row.car_info_fetched_at
        else:
            payload["last_failed_at"] = row.car_info_fetched_at
        return payload

    async def unpaid_registered_vehicle_stays_payload(
        source_report: Mapping[str, Any],
        period_start: date,
        period_end: date,
    ) -> dict[str, Any]:
        async_session = dependencies.async_session
        source_days = [item for item in source_report.get("days") or [] if isinstance(item, Mapping)]
        plate_values = sorted(
            {
                compact_plate(vehicle.get("plate"))
                for source_day in source_days
                for vehicle in source_day.get("vehicles") or []
                if isinstance(vehicle, Mapping) and compact_plate(vehicle.get("plate"))
            }
        )
        parking_by_plate: Dict[str, list[ParkingSession]] = defaultdict(list)
        vehicle_by_plate: Dict[str, Dict[str, Any]] = {}
        if plate_values:
            query_start = datetime.combine(period_start - timedelta(days=7), time.min)
            query_end = datetime.combine(period_end, time.min)
            normalized_session_plate = compact_plate_sql(ParkingSession.car_license_number)
            async with async_session() as session:
                parking_rows = (
                    await session.execute(
                        select(ParkingSession)
                        .where(normalized_session_plate.in_(plate_values))
                        .where(ParkingSession.start_time < query_end)
                        .where(
                            or_(
                                ParkingSession.end_time.is_(None),
                                ParkingSession.end_time >= query_start,
                            )
                        )
                        .order_by(ParkingSession.start_time.asc(), ParkingSession.id.asc())
                    )
                ).scalars().all()
                vehicle_rows = (
                    await session.execute(
                        select(ParkingVehicle, ParkingVehicleDetails)
                        .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                        .where(compact_plate_sql(ParkingVehicle.plate).in_(plate_values))
                    )
                ).all()
            for parking in parking_rows:
                plate = compact_plate(parking.car_license_number)
                if plate:
                    parking_by_plate[plate].append(parking)
            for vehicle, details in vehicle_rows:
                plate = compact_plate(vehicle.plate)
                if plate:
                    vehicle_by_plate[plate] = {
                        "name": vehicle.navn,
                        "area": vehicle.omrade,
                        "title": parking_vehicle_summary(details, vehicle.car_info_data),
                        "path": f"/parkering/kjoretoy/{quote(vehicle.plate or plate, safe='')}",
                    }

        days: list[dict[str, Any]] = []
        unique_plates: set[str] = set()
        observation_count = 0
        observed_minutes = 0.0
        excluded_paid_vehicle_days = 0
        for source_day in source_days:
            try:
                day_value = date.fromisoformat(str(source_day.get("date")))
            except (TypeError, ValueError):
                continue
            day_start = datetime.combine(day_value, time.min)
            day_end = day_start + timedelta(days=1)
            vehicles: list[dict[str, Any]] = []
            for source_vehicle in source_day.get("vehicles") or []:
                if not isinstance(source_vehicle, Mapping):
                    continue
                plate = compact_plate(source_vehicle.get("plate"))
                if not plate:
                    continue
                paid_same_day = any(
                    float_or_zero(parking.fee_inc_vat) > 0
                    and (start_at := normalize_local_naive(parking.start_time)) is not None
                    and start_at < day_end
                    and (
                        (end_at := normalize_local_naive(parking.end_time)) is None
                        or end_at >= day_start
                    )
                    for parking in parking_by_plate.get(plate, [])
                )
                if paid_same_day:
                    excluded_paid_vehicle_days += 1
                    continue
                local_vehicle = vehicle_by_plate.get(plate) or {}
                duration_minutes = float_or_zero(source_vehicle.get("duration_minutes"))
                observations = int_or_zero(source_vehicle.get("observation_count"))
                unique_plates.add(plate)
                observation_count += observations
                observed_minutes += duration_minutes
                vehicles.append(
                    {
                        "id": source_vehicle.get("id") or f"{plate.lower()}-{day_value.isoformat()}",
                        "plate": plate,
                        "displayName": source_vehicle.get("display_name") or plate,
                        "vehicleLabel": local_vehicle.get("title") or source_vehicle.get("vehicle_label") or "Kjøretøy funnet i register",
                        "ownerName": local_vehicle.get("name"),
                        "area": local_vehicle.get("area"),
                        "vehiclePath": local_vehicle.get("path"),
                        "countryCode": source_vehicle.get("country_code"),
                        "registrySource": source_vehicle.get("registry_source"),
                        "firstObservedAt": source_vehicle.get("first_observed_at"),
                        "lastObservedAt": source_vehicle.get("last_observed_at"),
                        "durationMinutes": duration_minutes,
                        "observationCount": observations,
                        "cameraNames": list(source_vehicle.get("camera_names") or []),
                    }
                )
            if vehicles:
                days.append(
                    {
                        "date": day_value.isoformat(),
                        "label": day_value.strftime("%d.%m"),
                        "weekdayLabel": ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"][day_value.weekday()],
                        "isWeekend": day_value.weekday() >= 5,
                        "vehicleCount": len(vehicles),
                        "observationCount": sum(item["observationCount"] for item in vehicles),
                        "vehicles": vehicles,
                    }
                )

        source_policy = source_report.get("policy") if isinstance(source_report.get("policy"), Mapping) else {}
        source_summary = source_report.get("summary") if isinstance(source_report.get("summary"), Mapping) else {}
        return {
            "policy": {
                "minDurationMinutes": int_or_zero(source_policy.get("min_duration_minutes")) or 10,
                "countryCodes": list(source_policy.get("country_codes") or ["NO", "SE", "DK"]),
                "paymentMatch": "same_calendar_day",
                "label": "Registerfunnet uten betaling",
                "detail": (
                    "Kjøretøyet er bekreftet i kjøretøyregister for Norge, Sverige eller Danmark, "
                    "er observert i mer enn 10 minutter samme dag og har ingen positiv "
                    "parkeringsbetaling som overlapper kalenderdagen."
                ),
            },
            "summary": {
                "vehicleDayCount": sum(day["vehicleCount"] for day in days),
                "activeDays": len(days),
                "uniqueVehicleCount": len(unique_plates),
                "observationCount": observation_count,
                "observedMinutes": round(observed_minutes, 1),
                "sourceVehicleDayCount": int_or_zero(source_summary.get("vehicle_day_count")),
                "excludedPaidVehicleDays": excluded_paid_vehicle_days,
            },
            "days": days,
        }

    def api_parking_weekly_chart(summaries: Dict[str, Any]) -> Dict[str, Any]:
        chart_rows = summaries.get("weekly_chart", [])

        def metric_series(metric: str) -> list[Dict[str, Any]]:
            return [
                {
                    "name": row["year"],
                    "data": row[metric],
                    "color": row.get("color"),
                    "unit": "kr" if metric == "revenue" else "stk",
                }
                for row in chart_rows
            ]

        current_year = local_now_naive().year
        return api_chart(
            "Ukesutvikling parkering",
            [str(week) for week in range(1, 54)],
            metric_series("revenue"),
            "Velg omsetning eller antall. I år og i fjor vises ved åpning; andre år slås på i forklaringen.",
            "line",
            360,
            metrics=[
                {"key": "revenue", "label": "Omsetning", "unit": "kr", "series": metric_series("revenue")},
                {"key": "count", "label": "Antall", "unit": "stk", "series": metric_series("count")},
            ],
            default_metric="revenue",
            default_visible_series=[str(current_year), str(current_year - 1)],
        )

    def api_parking_summary_row(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "period": item.get("period"),
            "period_label": item.get("period_label") or item.get("period"),
            "paid": round(float_or_zero(item.get("paid")), 2),
            "sessions": int_or_zero(item.get("sessions")),
            "vehicles": int_or_zero(item.get("vehicles")),
            "minutes": round(float_or_zero(item.get("minutes")), 2),
            "days_count": int_or_zero(item.get("days_count")),
        }

    def api_parking_overview_tables(summaries: Dict[str, Any], latest_rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        return [
            api_table(
                "Topp dager omsetning",
                ["period_label", "paid", "sessions", "vehicles", "minutes"],
                [api_parking_summary_row(row) for row in summaries.get("top_days", [])],
            ),
            api_table(
                "Topp uker omsetning",
                ["period_label", "paid", "sessions", "minutes", "days_count"],
                [api_parking_summary_row(row) for row in summaries.get("top_weeks", [])],
            ),
            api_table(
                "Topp m\u00e5neder omsetning",
                ["period", "paid", "sessions", "vehicles", "minutes", "days_count"],
                [api_parking_summary_row(row) for row in summaries.get("top_months", [])],
            ),
            api_table(
                "Topp dager antall",
                ["period_label", "sessions", "paid", "vehicles", "minutes"],
                [api_parking_summary_row(row) for row in summaries.get("top_days_by_count", [])],
            ),
            api_table(
                "Topp uker antall",
                ["period_label", "sessions", "paid", "minutes", "days_count"],
                [api_parking_summary_row(row) for row in summaries.get("top_weeks_by_count", [])],
            ),
            api_table(
                "Topp m\u00e5neder antall",
                ["period", "sessions", "paid", "vehicles", "minutes", "days_count"],
                [api_parking_summary_row(row) for row in summaries.get("top_months_by_count", [])],
            ),
            api_table(
                "Siste parkeringer",
                ["status", "start_time", "end_time", "car_license_number", "vehicle_make", "vehicle_type", "vehicle_color", "vehicle_owner", "fee_inc_vat", "parking_time_min"],
                latest_rows,
                meta={"rowLinkColumn": "car_license_number"},
            ),
        ]

    def parking_time_distribution_period(params: Any, today: date) -> Dict[str, Any]:
        PARKING_TIME_PERIOD_OPTIONS = dependencies.PARKING_TIME_PERIOD_OPTIONS
        api_filter_value = dependencies.api_filter_value
        parse_optional_date = dependencies.parse_optional_date
        requested = api_filter_value(params, "period", "this_month")
        valid_periods = {item["key"] for item in PARKING_TIME_PERIOD_OPTIONS}
        period_key = requested if requested in valid_periods else "this_month"
        custom_from = parse_optional_date(api_filter_value(params, "date_from"))
        custom_to = parse_optional_date(api_filter_value(params, "date_to"))

        if period_key == "this_year":
            start_day = date(today.year, 1, 1)
            end_day = today
            label = f"{today.year}"
        elif period_key == "last_90_days":
            start_day = today - timedelta(days=89)
            end_day = today
            label = "Siste 90 dager"
        elif period_key == "previous_month":
            start_day = add_months(today.replace(day=1), -1)
            end_day = today.replace(day=1) - timedelta(days=1)
            label = month_label(start_day)
        elif period_key == "last_year":
            start_day = date(today.year - 1, 1, 1)
            end_day = date(today.year - 1, 12, 31)
            label = str(today.year - 1)
        elif period_key == "custom" and custom_from and custom_to:
            start_day, end_day = sorted([custom_from, custom_to])
            label = f"{start_day:%d.%m.%Y} - {end_day:%d.%m.%Y}"
        else:
            period_key = "this_month" if period_key == "custom" else period_key
            start_day = today.replace(day=1)
            end_day = today
            label = month_label(start_day)

        end_exclusive = end_day + timedelta(days=1)
        days_count = max(0, (end_day - start_day).days + 1)
        return {
            "key": period_key,
            "label": label,
            "dateFrom": start_day.isoformat(),
            "dateTo": end_day.isoformat(),
            "start": datetime.combine(start_day, time.min),
            "end": datetime.combine(end_exclusive, time.min),
            "daysCount": days_count,
            "options": PARKING_TIME_PERIOD_OPTIONS,
        }

    def parking_time_weekday_day_counts(start_day: date, end_day: date) -> list[int]:
        PARKING_TIME_WEEKDAYS = dependencies.PARKING_TIME_WEEKDAYS
        counts = [0 for _ in PARKING_TIME_WEEKDAYS]
        cursor = start_day
        while cursor <= end_day:
            counts[cursor.weekday()] += 1
            cursor += timedelta(days=1)
        return counts

    async def api_parking_time_distribution(session, params: Any, now_dt: datetime) -> Dict[str, Any]:
        PARKING_TIME_WEEKDAYS = dependencies.PARKING_TIME_WEEKDAYS
        period = parking_time_distribution_period(params, now_dt.date())
        start_day = date.fromisoformat(period["dateFrom"])
        end_day = date.fromisoformat(period["dateTo"])
        weekday_day_counts = parking_time_weekday_day_counts(start_day, end_day)
        rows = (
            await session.execute(
                select(
                    ParkingSession.start_time,
                    ParkingSession.end_time,
                    ParkingSession.parking_time_min,
                    ParkingSession.fee_inc_vat,
                )
                .where(ParkingSession.start_time >= period["start"])
                .where(ParkingSession.start_time < period["end"])
                .order_by(ParkingSession.start_time.asc())
            )
        ).all()

        buckets = [
            [
                {
                    "weekdayIndex": weekday_index,
                    "weekday": PARKING_TIME_WEEKDAYS[weekday_index],
                    "hour": hour,
                    "hourLabel": f"{hour:02d}:00",
                    "sessions": 0,
                    "paid": 0.0,
                    "minutes": 0.0,
                }
                for hour in range(24)
            ]
            for weekday_index in range(7)
        ]
        weekday_totals = [
            {
                "weekdayIndex": weekday_index,
                "weekday": PARKING_TIME_WEEKDAYS[weekday_index],
                "days": weekday_day_counts[weekday_index],
                "sessions": 0,
                "paid": 0.0,
                "minutes": 0.0,
            }
            for weekday_index in range(7)
        ]
        hour_totals = [
            {
                "hour": hour,
                "hourLabel": f"{hour:02d}:00",
                "sessions": 0,
                "paid": 0.0,
                "minutes": 0.0,
            }
            for hour in range(24)
        ]

        for start_time, end_time, parking_time_min, fee_inc_vat in rows:
            start_at = normalize_local_naive(start_time)
            if not start_at:
                continue
            paid = float_or_zero(fee_inc_vat)
            minutes = float_or_zero(parking_time_min)
            if minutes <= 0:
                end_at = normalize_local_naive(end_time)
                if end_at and end_at > start_at:
                    minutes = (end_at - start_at).total_seconds() / 60
            weekday_index = start_at.weekday()
            hour = start_at.hour
            for target in (buckets[weekday_index][hour], weekday_totals[weekday_index], hour_totals[hour]):
                target["sessions"] += 1
                target["paid"] += paid
                target["minutes"] += minutes

        def finalize_bucket(item: Dict[str, Any], days: int = 0) -> Dict[str, Any]:
            sessions = int_or_zero(item.get("sessions"))
            paid = round(float_or_zero(item.get("paid")), 2)
            minutes = round(float_or_zero(item.get("minutes")), 1)
            item["sessions"] = sessions
            item["paid"] = paid
            item["minutes"] = minutes
            item["hours"] = round(minutes / 60, 2)
            item["avgPaidPerSession"] = round(paid / sessions, 2) if sessions else 0.0
            item["avgMinutesPerSession"] = round(minutes / sessions, 1) if sessions else 0.0
            item["avgPaidPerDay"] = round(paid / days, 2) if days else 0.0
            item["avgSessionsPerDay"] = round(sessions / days, 2) if days else 0.0
            item["avgMinutesPerDay"] = round(minutes / days, 1) if days else 0.0
            return item

        finalized_weekdays = []
        finalized_cells = []
        for weekday_index, weekday in enumerate(PARKING_TIME_WEEKDAYS):
            days = weekday_day_counts[weekday_index]
            hours = [finalize_bucket(item, days) for item in buckets[weekday_index]]
            finalized_cells.extend(hours)
            finalized_weekdays.append({**finalize_bucket(weekday_totals[weekday_index], days), "hours": hours})
        finalized_hours = [finalize_bucket(item, max(1, period["daysCount"])) for item in hour_totals]
        total_sessions = sum(item["sessions"] for item in finalized_weekdays)
        total_paid = round(sum(item["paid"] for item in finalized_weekdays), 2)
        total_minutes = round(sum(item["minutes"] for item in finalized_weekdays), 1)
        max_values = {
            "paid": max([item["paid"] for item in finalized_cells] + [1.0]),
            "minutes": max([item["minutes"] for item in finalized_cells] + [1.0]),
            "sessions": max([item["sessions"] for item in finalized_cells] + [1]),
            "avgPaidPerDay": max([item["avgPaidPerDay"] for item in finalized_cells] + [1.0]),
            "avgMinutesPerDay": max([item["avgMinutesPerDay"] for item in finalized_cells] + [1.0]),
        }
        top_slots = sorted(finalized_cells, key=lambda item: (item["paid"], item["sessions"], item["minutes"]), reverse=True)[:20]
        return {
            "generatedAt": api_local_iso(now_dt),
            "period": {
                **{key: value for key, value in period.items() if key not in {"start", "end"}},
                "detail": f"{period['daysCount']} dager - fordelt etter starttidspunkt",
            },
            "summary": {
                "sessions": total_sessions,
                "paid": total_paid,
                "minutes": total_minutes,
                "hours": round(total_minutes / 60, 2),
                "avgPaidPerSession": round(total_paid / total_sessions, 2) if total_sessions else 0.0,
                "avgMinutesPerSession": round(total_minutes / total_sessions, 1) if total_sessions else 0.0,
                "avgPaidPerDay": round(total_paid / max(1, period["daysCount"]), 2),
                "avgSessionsPerDay": round(total_sessions / max(1, period["daysCount"]), 2),
            },
            "max": max_values,
            "weekdays": finalized_weekdays,
            "hours": finalized_hours,
            "topSlots": top_slots,
        }

    def parking_timeline_end(row: ParkingSession, timeline_end: datetime) -> datetime:
        start_at = normalize_local_naive(row.start_time) or timeline_end
        end_at = normalize_local_naive(row.end_time)
        status = (row.status or "").strip().lower()
        if end_at:
            return end_at
        if status in {"ongoing", "active", "started"}:
            return timeline_end
        if row.parking_time_min and row.parking_time_min > 0:
            return start_at + timedelta(minutes=float(row.parking_time_min))
        return start_at + timedelta(minutes=30)

    async def api_parking_day_timeline(session, selected: date, now_dt: datetime) -> Dict[str, Any]:
        PARKING_OCCUPANCY_SCALE_MAX = dependencies.PARKING_OCCUPANCY_SCALE_MAX
        PARKING_TIMELINE_CAPACITY = dependencies.PARKING_TIMELINE_CAPACITY
        PARKING_TIMELINE_ROWS = dependencies.PARKING_TIMELINE_ROWS
        day_start = datetime.combine(selected, time.min)
        day_end = day_start + timedelta(days=1)
        is_today = selected == now_dt.date()
        timeline_end = min(now_dt, day_end) if is_today else day_end
        normalized_session_plate = func.upper(func.replace(ParkingSession.car_license_number, " ", ""))
        query_start = day_start - timedelta(days=7)
        rows = (
            await session.execute(
                select(ParkingSession, ParkingVehicle)
                .outerjoin(ParkingVehicle, ParkingVehicle.plate == normalized_session_plate)
                .where(ParkingSession.start_time >= query_start)
                .where(ParkingSession.start_time < day_end)
                .where(
                    or_(
                        ParkingSession.start_time >= day_start,
                        ParkingSession.end_time.is_(None),
                        ParkingSession.end_time >= day_start,
                    )
                )
                .order_by(ParkingSession.start_time.asc(), ParkingSession.id.asc())
            )
        ).all()

        spaces = []
        slot_to_space: Dict[int, Dict[str, Any]] = {}
        slot_index = 0
        for row_def in PARKING_TIMELINE_ROWS:
            row_spaces = []
            for number in range(1, int(row_def["count"]) + 1):
                label = f"{number:02d}"
                space = {
                    "spaceId": f"space-{label}",
                    "label": label,
                    "rowKey": row_def["key"],
                    "rowLabel": row_def["label"],
                    "sessions": [],
                    "count": 0,
                    "minutes": 0.0,
                    "paid": 0.0,
                }
                row_spaces.append(space)
                slot_to_space[slot_index] = space
                slot_index += 1
            spaces.append({**row_def, "spaces": row_spaces})

        event_candidates = []
        for row, vehicle in rows:
            start_at = normalize_local_naive(row.start_time)
            if not start_at:
                continue
            end_at = parking_timeline_end(row, timeline_end)
            if end_at <= start_at:
                end_at = start_at + timedelta(minutes=max(1.0, float_or_zero(row.parking_time_min) or 1.0))
            clamped_start = max(day_start, min(day_end, start_at))
            clamped_end = max(clamped_start, min(day_end, end_at))
            duration_minutes = max(0.0, (clamped_end - clamped_start).total_seconds() / 60)
            if duration_minutes <= 0:
                continue
            plate = normalize_plate(row.car_license_number)
            paid = float_or_zero(row.fee_inc_vat)
            status = (row.status or "").strip()
            status_key = status.lower()
            if status_key in {"ongoing", "active", "started"} and not row.end_time:
                kind = "ongoing"
            elif paid <= 0:
                kind = "unpaid"
            else:
                kind = "paid"
            title_parts = [
                f"{parking_day_time_label(start_at, selected)}-{parking_day_time_label(end_at, selected)}",
                f"{duration_minutes:.0f} min",
            ]
            if paid:
                title_parts.append(f"{paid:.0f} kr")
            if vehicle and vehicle.navn:
                title_parts.append(str(vehicle.navn))
            if vehicle and vehicle.omrade:
                title_parts.append(str(vehicle.omrade))
            if row.parking_area:
                title_parts.append(str(row.parking_area))
            if status:
                title_parts.append(status)
            event_candidates.append(
                {
                    "_start": clamped_start,
                    "_end": clamped_end,
                    "id": f"parking-{row.id}",
                    "left": round(((clamped_start - day_start).total_seconds() / 86400) * 100, 4),
                    "width": max(0.12, round(((clamped_end - clamped_start).total_seconds() / 86400) * 100, 4)),
                    "label": "",
                    "plate": plate,
                    "title": " | ".join(title_parts),
                    "kind": kind,
                    "start": api_local_iso(start_at),
                    "end": api_local_iso(end_at),
                    "durationMinutes": round(duration_minutes, 1),
                    "paid": round(paid, 2),
                    "status": status,
                    "area": row.parking_area,
                    "owner": vehicle.navn if vehicle else None,
                    "ownerArea": vehicle.omrade if vehicle else None,
                    "href": (
                        f"/parkering/parkeringer?day={selected.isoformat()}&plate={quote(plate, safe='')}"
                        if plate
                        else f"/parkering/parkeringer?day={selected.isoformat()}"
                    ),
                }
            )

        slot_available = [day_start for _ in range(PARKING_TIMELINE_CAPACITY)]
        overflow_sessions = []
        assigned_events = []
        for item in sorted(event_candidates, key=lambda event: (event["_start"], event["_end"])):
            free_slots = [index for index, available_at in enumerate(slot_available) if available_at <= item["_start"]]
            slot = max(free_slots, key=lambda index: (slot_available[index], -index)) if free_slots else None
            payload = {key: value for key, value in item.items() if not key.startswith("_")}
            if slot is None:
                payload["kind"] = "overflow"
                overflow_sessions.append(payload)
                assigned_events.append(item)
                continue
            space = slot_to_space[slot]
            payload["spaceId"] = space["spaceId"]
            space["sessions"].append(payload)
            space["count"] += 1
            space["minutes"] += item["durationMinutes"]
            space["paid"] += item["paid"]
            slot_available[slot] = item["_end"]
            assigned_events.append(item)

        occupancy = []
        peak_count = 0
        peak_time_label = None
        for index in range(96):
            bucket_start = day_start + timedelta(minutes=index * 15)
            bucket_end = bucket_start + timedelta(minutes=15)
            bucket_mid = bucket_start + timedelta(minutes=7.5)
            count = sum(1 for item in assigned_events if item["_start"] <= bucket_mid < item["_end"])
            if count > peak_count:
                peak_count = count
                peak_time_label = bucket_start.strftime("%H:%M")
            occupancy.append(
                {
                    "left": round(index / 96 * 100, 4),
                    "width": round(100 / 96, 4),
                    "count": count,
                    "height": round((min(count, PARKING_OCCUPANCY_SCALE_MAX) / PARKING_OCCUPANCY_SCALE_MAX) * 100, 2),
                    "title": f"{bucket_start:%H:%M}-{bucket_end:%H:%M} | {count} biler | skala 25, kapasitet 23",
                }
            )

        total_minutes = round(sum(item["durationMinutes"] for item in assigned_events), 1)
        total_paid = round(sum(item["paid"] for item in assigned_events), 2)
        total_sessions = len(assigned_events)
        utilization_percent = round((total_minutes / (PARKING_TIMELINE_CAPACITY * 1440)) * 100, 1) if PARKING_TIMELINE_CAPACITY else 0
        avg_minutes = round(total_minutes / total_sessions, 1) if total_sessions else 0
        today = datetime.now(LOCAL_TZ).date()
        now_marker = None
        if selected == today:
            now_local = datetime.now(LOCAL_TZ).replace(tzinfo=None)
            now_marker = round(max(0, min(100, ((now_local - day_start).total_seconds() / 86400) * 100)), 3)
        ticks = [{"label": f"{hour:02d}", "left": round(hour / 24 * 100, 4)} for hour in range(0, 25, 2)]
        return {
            "selectedDay": selected.isoformat(),
            "selectedDayLabel": selected.strftime("%d.%m.%Y"),
            "prevDay": (selected - timedelta(days=1)).isoformat(),
            "nextDay": (selected + timedelta(days=1)).isoformat(),
            "capacity": PARKING_TIMELINE_CAPACITY,
            "occupancyScaleMax": PARKING_OCCUPANCY_SCALE_MAX,
            "layout": [{"key": row["key"], "label": row["label"], "count": row["count"]} for row in PARKING_TIMELINE_ROWS],
            "spaceRows": spaces,
            "overflowSessions": overflow_sessions,
            "occupancy": occupancy,
            "ticks": ticks,
            "nowMarker": now_marker,
            "summary": {
                "sessionsCount": total_sessions,
                "paidAmountKr": total_paid,
                "durationMinutes": total_minutes,
                "durationHours": round(total_minutes / 60, 2),
                "avgMinutes": avg_minutes,
                "peakCount": peak_count,
                "peakTimeLabel": peak_time_label,
                "utilizationPercent": utilization_percent,
                "overflowCount": len(overflow_sessions),
            },
        }

    def api_parking_forecast_rows(forecast: Dict[str, Any]) -> list[Dict[str, Any]]:
        rows = []
        for key, label in [("day", "I dag"), ("month", "Måned"), ("year", "År")]:
            item = forecast.get(key) or {}
            actual = item.get("actual") or {}
            forecast_values = item.get("forecast") or {}
            rows.append(
                {
                    "period": label,
                    "label": item.get("label") or label,
                    "actual_parkeringer": round(float_or_zero(actual.get("sessions")), 1),
                    "forecast_parkeringer": round(float_or_zero(forecast_values.get("sessions")), 1),
                    "actual_paid": round(float_or_zero(actual.get("paid")), 2),
                    "forecast_paid": round(float_or_zero(forecast_values.get("paid")), 2),
                    "actual_minutes": round(float_or_zero(actual.get("minutes")), 1),
                    "forecast_minutes": round(float_or_zero(forecast_values.get("minutes")), 1),
                    "actual_vehicles": round(float_or_zero(actual.get("vehicles")), 1),
                    "forecast_vehicles": round(float_or_zero(forecast_values.get("vehicles")), 1),
                    "tempo": round(float_or_zero(item.get("tempo")) * 100, 1) if item.get("tempo") is not None else None,
                    "remaining_days": item.get("remaining_days"),
                }
            )
        return rows

    def api_parking_saved_forecast_rows(rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        return [
            {
                "created_at": row.get("created_at"),
                "period_type": row.get("period_type"),
                "period_label": row.get("period_label"),
                "forecast_parkeringer": round(float_or_zero((row.get("forecast") or {}).get("sessions")), 1),
                "actual_parkeringer": round(float_or_zero((row.get("actual") or {}).get("sessions")), 1),
                "delta_parkeringer": round(float_or_zero((row.get("delta") or {}).get("sessions")), 1),
                "forecast_paid": round(float_or_zero((row.get("forecast") or {}).get("paid")), 2),
                "actual_paid": round(float_or_zero((row.get("actual") or {}).get("paid")), 2),
                "delta_paid": round(float_or_zero((row.get("delta") or {}).get("paid")), 2),
                "forecast_vehicles": round(float_or_zero((row.get("forecast") or {}).get("vehicles")), 1),
                "actual_vehicles": round(float_or_zero((row.get("actual") or {}).get("vehicles")), 1),
                "period_done": row.get("period_done"),
            }
            for row in rows
        ]

    def parking_row_api(
        row: ParkingSession,
        vehicle: Optional[ParkingVehicle] = None,
        details: Optional[ParkingVehicleDetails] = None,
        previous_stats: Optional[Dict[str, Any]] = None,
        unifi_before_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        owner_warning = parking_current_ownership_warning(vehicle, row.start_time)
        vehicle_make = first_value(details.merke if details else None, car_info_field_value(vehicle.car_info_data if vehicle else None, "make", "brand"))
        vehicle_type = first_value(
            details.typebetegnelse if details else None,
            details.modell if details else None,
            car_info_field_value(vehicle.car_info_data if vehicle else None, "vehicle_type", "model", "classification"),
        )
        vehicle_color = first_value(details.farge if details else None, car_info_field_value(vehicle.car_info_data if vehicle else None, "color"))
        vehicle_title = parking_vehicle_summary(details, vehicle.car_info_data if vehicle else None)
        if not vehicle_title:
            vehicle_parts = [str(part).strip() for part in [vehicle_make, vehicle_type] if str(part or "").strip()]
            vehicle_title = " ".join(vehicle_parts) or None
            if vehicle_title and vehicle_color:
                vehicle_title = f"{vehicle_title} - {vehicle_color}"
        data = {
            "id": row.id,
            "start_time": row.start_time.isoformat() if row.start_time else None,
            "end_time": row.end_time.isoformat() if row.end_time else None,
            "end_delta_min": parking_departure_slot_delta_minutes(row),
            "parking_time_min": row.parking_time_min,
            "fee_inc_vat": row.fee_inc_vat,
            "car_license_number": row.car_license_number,
            "owner_warning": owner_warning["text"] if owner_warning else "",
            "parking_area": row.parking_area,
            "source_system": row.source_system,
            "user_interface": row.user_interface,
            "subtype": row.subtype,
            "status": row.status,
            "vehicle_title": vehicle_title,
            "path": (
                f"/parkering/kjoretoy/{quote(compact_plate(row.car_license_number), safe='')}"
                if compact_plate(row.car_license_number)
                else ""
            ),
            "unifi_start_url": unifi_protect_parking_timelapse_url(row.start_time, unifi_before_seconds),
            "unifi_end_url": unifi_protect_parking_timelapse_url(row.end_time, unifi_before_seconds),
        }
        if previous_stats:
            data.update(
                {
                    "previous_parking_count": int_or_zero(previous_stats.get("count")),
                    "previous_paid_total": round(float_or_zero(previous_stats.get("paid")), 2),
                }
            )
        if vehicle:
            data.update(
                {
                    "navn": vehicle.navn,
                    "vehicle_owner": vehicle.navn,
                    "omrade": vehicle.omrade,
                    "path": f"/parkering/kjoretoy/{quote(vehicle.plate or '', safe='')}",
                }
            )
        data.update(
            {
                "vehicle_make": vehicle_make,
                "vehicle_type": vehicle_type,
                "vehicle_color": vehicle_color,
            }
        )
        return data

    async def parking_previous_stats_for_rows(session, rows: list[ParkingSession]) -> Dict[int, Dict[str, Any]]:
        candidates = [
            row
            for row in rows
            if row.id is not None and row.start_time is not None and compact_plate(row.car_license_number)
        ]
        if not candidates:
            return {}

        selected_ids = {row.id for row in candidates}
        selected_plates = {compact_plate(row.car_license_number) for row in candidates}
        latest_start = max(row.start_time for row in candidates if row.start_time is not None)
        plate_expr = func.upper(func.replace(ParkingSession.car_license_number, " ", ""))
        history_rows = (
            await session.execute(
                select(ParkingSession.id, ParkingSession.car_license_number, ParkingSession.fee_inc_vat)
                .where(plate_expr.in_(selected_plates))
                .where(ParkingSession.start_time <= latest_start)
                .order_by(plate_expr.asc(), ParkingSession.start_time.asc(), ParkingSession.id.asc())
            )
        ).all()

        running: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "paid": 0.0})
        previous_by_id: Dict[int, Dict[str, Any]] = {}
        for session_id, plate, paid in history_rows:
            compact = compact_plate(plate)
            if not compact:
                continue
            current = running[compact]
            if session_id in selected_ids:
                previous_by_id[int(session_id)] = {"count": current["count"], "paid": current["paid"]}
            current["count"] += 1
            current["paid"] += float_or_zero(paid)
        return previous_by_id

    def parking_vehicle_row_api(vehicle: ParkingVehicle, details: Optional[ParkingVehicleDetails]) -> Dict[str, Any]:
        ownership_at = svv_current_ownership_at(vehicle.svv_data)
        return {
            "plate": vehicle.plate,
            "vehicle_title": parking_vehicle_summary(details, vehicle.car_info_data),
            "navn": vehicle.navn,
            "omrade": vehicle.omrade,
            "sun2_id": vehicle.sun2_id,
            "current_ownership_at": api_local_iso(ownership_at),
            "parkering_count": vehicle.parkering_count,
            "paid_total": vehicle.paid_total,
            "first_seen": api_local_iso(vehicle.first_seen),
            "last_seen": api_local_iso(vehicle.last_seen),
            "svv_status": vehicle.svv_status,
            "car_info_status": vehicle.car_info_status,
            "car_info_confirmed_swedish": car_info_confirmed_swedish(vehicle.car_info_data),
            "car_info_confirmed_foreign": car_info_confirmed_foreign(vehicle.car_info_data),
            "car_info_country_code": car_info_country_code(vehicle.car_info_data) or None,
            "notat": vehicle.notat,
            "path": f"/parkering/kjoretoy/{quote(vehicle.plate or '', safe='')}",
        }

    def parking_vehicle_search_condition(query: Optional[str]):
        exact_search_text = dependencies.exact_search_text
        exact_word_match = dependencies.exact_word_match
        text_value = (query or "").strip()
        if not text_value:
            return None
        exact_value = exact_search_text(text_value)
        if exact_value:
            plate_value = compact_plate(exact_value)
            return or_(
                func.upper(func.coalesce(ParkingVehicle.plate, "")) == plate_value if plate_value else False,
                exact_word_match(ParkingVehicle.navn, exact_value),
                exact_word_match(ParkingVehicle.omrade, exact_value),
                exact_word_match(ParkingVehicle.sun2_id, exact_value),
                exact_word_match(ParkingVehicle.notat, exact_value),
                exact_word_match(ParkingVehicleDetails.merke, exact_value),
                exact_word_match(ParkingVehicleDetails.modell, exact_value),
                exact_word_match(ParkingVehicleDetails.typebetegnelse, exact_value),
                exact_word_match(ParkingVehicleDetails.farge, exact_value),
                exact_word_match(ParkingVehicleDetails.kjoretoyklasse_navn, exact_value),
            )
        like = f"%{text_value.upper()}%"
        plate_like = f"%{compact_plate(text_value)}%" if compact_plate(text_value) else like
        return or_(
            func.upper(func.coalesce(ParkingVehicle.plate, "")).like(plate_like),
            func.upper(func.coalesce(ParkingVehicle.navn, "")).like(like),
            func.upper(func.coalesce(ParkingVehicle.omrade, "")).like(like),
            func.upper(func.coalesce(ParkingVehicle.sun2_id, "")).like(like),
            func.upper(func.coalesce(ParkingVehicle.notat, "")).like(like),
            func.upper(func.coalesce(ParkingVehicleDetails.merke, "")).like(like),
            func.upper(func.coalesce(ParkingVehicleDetails.modell, "")).like(like),
            func.upper(func.coalesce(ParkingVehicleDetails.typebetegnelse, "")).like(like),
            func.upper(func.coalesce(ParkingVehicleDetails.farge, "")).like(like),
            func.upper(func.coalesce(ParkingVehicleDetails.kjoretoyklasse_navn, "")).like(like),
        )

    def parking_valid_vehicle_area_condition():
        normalized = func.lower(func.trim(func.coalesce(ParkingVehicle.omrade, "")))
        return and_(normalized != "", normalized != "ikke funnet")

    def parking_area_period(date_from_value: str = "", date_to_value: str = "") -> Dict[str, Any]:
        parse_day = dependencies.parse_day
        from_value = (date_from_value or "").strip()
        to_value = (date_to_value or "").strip()
        if not from_value and not to_value:
            return {
                "date_from": "",
                "date_to": "",
                "start_at": None,
                "end_at": None,
                "label": "Hele historikken",
                "detail": "Alle importerte parkeringer",
                "is_all": True,
            }

        from_day = parse_day(from_value) if from_value else None
        to_day = parse_day(to_value) if to_value else None
        if from_day and not to_day:
            to_day = from_day
        if from_day and to_day and to_day < from_day:
            from_day, to_day = to_day, from_day

        start_at = datetime.combine(from_day, time.min) if from_day else None
        end_at = datetime.combine(to_day + timedelta(days=1), time.min) if to_day else None
        if from_day and to_day and from_day == to_day:
            label = from_day.strftime("%d.%m.%Y")
            detail = "Valgt dato"
        elif from_day and to_day:
            label = f"{from_day:%d.%m.%Y} - {to_day:%d.%m.%Y}"
            detail = "Valgt tidsrom"
        elif to_day:
            label = f"Til og med {to_day:%d.%m.%Y}"
            detail = "Fra første import til valgt dato"
        else:
            label = "Hele historikken"
            detail = "Alle importerte parkeringer"

        return {
            "date_from": from_day.isoformat() if from_day else "",
            "date_to": "" if from_day and to_day and from_day == to_day else (to_day.isoformat() if to_day else ""),
            "start_at": start_at,
            "end_at": end_at,
            "label": label,
            "detail": detail,
            "is_all": False,
        }

    def parking_area_period_conditions(period: Dict[str, Any]) -> list[Any]:
        conditions = []
        if period.get("start_at"):
            conditions.append(ParkingSession.start_time >= period["start_at"])
        if period.get("end_at"):
            conditions.append(ParkingSession.start_time < period["end_at"])
        return conditions

    def parking_area_row_api(row: Any, vehicle_with_area: int, parking_with_area: int) -> Dict[str, Any]:
        vehicle_count = int_or_zero(getattr(row, "vehicle_count", 0))
        parking_count = int_or_zero(getattr(row, "parking_count", 0))
        paid_total = float_or_zero(getattr(row, "paid_total", 0))
        vehicle_share = round((vehicle_count / vehicle_with_area) * 100, 1) if vehicle_with_area else 0
        parking_share = round((parking_count / parking_with_area) * 100, 1) if parking_with_area else 0
        return {
            "omrade": getattr(row, "omrade", None),
            "vehicle_count": vehicle_count,
            "vehicles": vehicle_count,
            "vehicle_share": vehicle_share,
            "parking_count": parking_count,
            "parkeringer": parking_count,
            "parking_share": parking_share,
            "paid_total": paid_total,
            "paid": paid_total,
            "last_seen": getattr(row, "last_seen", None),
        }

    async def parking_area_overview_data(session, date_from_value: str = "", date_to_value: str = "") -> Dict[str, Any]:
        period = parking_area_period(date_from_value, date_to_value)
        valid_area_condition = parking_valid_vehicle_area_condition()
        area_expr = func.trim(ParkingVehicle.omrade)
        normalized_session_plate = func.upper(func.replace(ParkingSession.car_license_number, " ", ""))
        period_conditions = parking_area_period_conditions(period)

        if period["is_all"]:
            raw_rows = (
                await session.execute(
                    select(
                        area_expr.label("omrade"),
                        func.count(func.distinct(ParkingVehicle.plate)).label("vehicle_count"),
                        func.coalesce(func.sum(ParkingVehicle.parkering_count), 0).label("parking_count"),
                        func.coalesce(func.sum(ParkingVehicle.paid_total), 0).label("paid_total"),
                        func.max(ParkingVehicle.last_seen).label("last_seen"),
                    )
                    .where(valid_area_condition)
                    .group_by(area_expr)
                    .order_by(func.count(func.distinct(ParkingVehicle.plate)).desc(), area_expr.asc())
                )
            ).all()
            vehicle_total = (
                await session.execute(select(func.count(func.distinct(ParkingVehicle.plate))))
            ).scalar_one()
            vehicle_with_area = (
                await session.execute(select(func.count(func.distinct(ParkingVehicle.plate))).where(valid_area_condition))
            ).scalar_one()
            totals = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("parking_total"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid_total"),
                    )
                )
            ).one()
        else:
            raw_rows = (
                await session.execute(
                    select(
                        area_expr.label("omrade"),
                        func.count(func.distinct(ParkingVehicle.plate)).label("vehicle_count"),
                        func.count(ParkingSession.id).label("parking_count"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid_total"),
                        func.max(ParkingSession.start_time).label("last_seen"),
                    )
                    .select_from(ParkingSession)
                    .outerjoin(ParkingVehicle, ParkingVehicle.plate == normalized_session_plate)
                    .where(*period_conditions, valid_area_condition)
                    .group_by(area_expr)
                    .order_by(func.count(ParkingSession.id).desc(), area_expr.asc())
                )
            ).all()
            vehicle_total = (
                await session.execute(
                    select(func.count(func.distinct(normalized_session_plate)))
                    .select_from(ParkingSession)
                    .where(*period_conditions, normalized_session_plate != "")
                )
            ).scalar_one()
            vehicle_with_area = (
                await session.execute(
                    select(func.count(func.distinct(ParkingVehicle.plate)))
                    .select_from(ParkingSession)
                    .outerjoin(ParkingVehicle, ParkingVehicle.plate == normalized_session_plate)
                    .where(*period_conditions, valid_area_condition)
                )
            ).scalar_one()
            totals = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id).label("parking_total"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid_total"),
                    ).where(*period_conditions)
                )
            ).one()

        parking_with_area = sum(int_or_zero(getattr(row, "parking_count", 0)) for row in raw_rows)
        vehicle_total = int_or_zero(vehicle_total)
        vehicle_with_area = int_or_zero(vehicle_with_area)
        return {
            "period": period,
            "rows": [parking_area_row_api(row, vehicle_with_area, parking_with_area) for row in raw_rows],
            "vehicle_total": vehicle_total,
            "vehicle_with_area": vehicle_with_area,
            "missing_area": max(vehicle_total - vehicle_with_area, 0),
            "parking_total": int_or_zero(getattr(totals, "parking_total", 0)),
            "parking_with_area": parking_with_area,
            "paid_total": float_or_zero(getattr(totals, "paid_total", 0)),
            "coverage_percent": round((vehicle_with_area / vehicle_total) * 100, 1) if vehicle_total else 0,
        }

    async def parking_area_missing_rows_for_period(session, period: Dict[str, Any], limit: int = 100) -> list[Dict[str, Any]]:
        normalized_area = func.lower(func.trim(func.coalesce(ParkingVehicle.omrade, "")))
        missing_vehicle_area = or_(normalized_area == "", normalized_area == "ikke funnet")
        if period.get("is_all"):
            rows = (
                await session.execute(
                    select(
                        ParkingVehicle.plate.label("plate"),
                        ParkingVehicle.navn.label("navn"),
                        ParkingVehicle.parkering_count.label("parkering_count"),
                        ParkingVehicle.paid_total.label("paid_total"),
                        ParkingVehicle.last_seen.label("last_seen"),
                    )
                    .where(missing_vehicle_area)
                    .order_by(ParkingVehicle.last_seen.desc().nullslast(), ParkingVehicle.plate.asc())
                    .limit(limit)
                )
            ).all()
            return [
                {
                    "plate": row.plate,
                    "navn": row.navn,
                    "parkering_count": int_or_zero(row.parkering_count),
                    "paid_total": float_or_zero(row.paid_total),
                    "last_seen": row.last_seen,
                }
                for row in rows
            ]

        normalized_session_plate = func.upper(func.replace(ParkingSession.car_license_number, " ", ""))
        period_conditions = parking_area_period_conditions(period)
        rows = (
            await session.execute(
                select(
                    normalized_session_plate.label("plate"),
                    func.max(ParkingVehicle.navn).label("navn"),
                    func.count(ParkingSession.id).label("parkering_count"),
                    func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid_total"),
                    func.max(ParkingSession.start_time).label("last_seen"),
                )
                .select_from(ParkingSession)
                .outerjoin(ParkingVehicle, ParkingVehicle.plate == normalized_session_plate)
                .where(
                    *period_conditions,
                    normalized_session_plate != "",
                    or_(ParkingVehicle.plate.is_(None), missing_vehicle_area),
                )
                .group_by(normalized_session_plate)
                .order_by(func.count(ParkingSession.id).desc(), normalized_session_plate.asc())
                .limit(limit)
            )
        ).all()
        return [
            {
                "plate": row.plate,
                "navn": row.navn,
                "parkering_count": int_or_zero(row.parkering_count),
                "paid_total": float_or_zero(row.paid_total),
                "last_seen": row.last_seen,
            }
            for row in rows
        ]

    def parking_weekly_average_period(params: Any, today: date) -> Dict[str, Any]:
        PARKING_WEEKLY_AVERAGE_PERIOD_OPTIONS = dependencies.PARKING_WEEKLY_AVERAGE_PERIOD_OPTIONS
        api_filter_value = dependencies.api_filter_value
        parse_optional_date = dependencies.parse_optional_date
        requested = api_filter_value(params, "period", "this_year")
        valid_periods = {item["key"] for item in PARKING_WEEKLY_AVERAGE_PERIOD_OPTIONS}
        period_key = requested if requested in valid_periods else "this_year"
        custom_from = parse_optional_date(api_filter_value(params, "date_from"))
        custom_to = parse_optional_date(api_filter_value(params, "date_to"))

        if period_key == "last_12_months":
            start_day = today - timedelta(days=364)
            end_day = today
            label = "Siste 12 måneder"
        elif period_key == "last_24_months":
            start_day = today - timedelta(days=729)
            end_day = today
            label = "Siste 24 måneder"
        elif period_key == "last_year":
            start_day = date(today.year - 1, 1, 1)
            end_day = date(today.year - 1, 12, 31)
            label = str(today.year - 1)
        elif period_key == "custom" and custom_from and custom_to:
            start_day, end_day = sorted([custom_from, custom_to])
            label = f"{start_day:%d.%m.%Y} - {end_day:%d.%m.%Y}"
        else:
            period_key = "this_year"
            start_day = date(today.year, 1, 1)
            end_day = today
            label = str(today.year)

        return {
            "key": period_key,
            "label": label,
            "dateFrom": start_day.isoformat(),
            "dateTo": end_day.isoformat(),
            "start": datetime.combine(start_day, time.min),
            "end": datetime.combine(end_day + timedelta(days=1), time.min),
            "options": PARKING_WEEKLY_AVERAGE_PERIOD_OPTIONS,
        }

    def parking_weekly_average_payload(rows: Any, period: Dict[str, Any], now_dt: datetime) -> Dict[str, Any]:
        start_day = date.fromisoformat(period["dateFrom"])
        end_day = date.fromisoformat(period["dateTo"])
        first_week = start_day - timedelta(days=start_day.weekday())
        last_week = end_day - timedelta(days=end_day.weekday())
        buckets: Dict[date, Dict[str, Any]] = {}
        cursor = first_week
        while cursor <= last_week:
            iso_year, iso_week, _ = cursor.isocalendar()
            buckets[cursor] = {
                "weekStart": cursor,
                "weekEnd": cursor + timedelta(days=6),
                "isoYear": iso_year,
                "isoWeek": iso_week,
                "sessions": 0,
                "paid": 0.0,
                "minutes": 0.0,
                "durationSessions": 0,
            }
            cursor += timedelta(days=7)

        for start_time, end_time, parking_time_min, fee_inc_vat in rows:
            start_at = normalize_local_naive(start_time)
            if not start_at:
                continue
            week_start = start_at.date() - timedelta(days=start_at.weekday())
            bucket = buckets.get(week_start)
            if not bucket:
                continue
            bucket["sessions"] += 1
            bucket["paid"] += float_or_zero(fee_inc_vat)
            minutes = float_or_zero(parking_time_min)
            if minutes <= 0:
                end_at = normalize_local_naive(end_time)
                if end_at and end_at > start_at:
                    minutes = (end_at - start_at).total_seconds() / 60
            if minutes > 0:
                bucket["minutes"] += minutes
                bucket["durationSessions"] += 1

        def format_week_range(week_start: date, week_end: date) -> str:
            if week_start.year == week_end.year:
                return f"{week_start:%d.%m}–{week_end:%d.%m.%Y}"
            return f"{week_start:%d.%m.%Y}–{week_end:%d.%m.%Y}"

        points = []
        for bucket in buckets.values():
            sessions = int_or_zero(bucket["sessions"])
            duration_sessions = int_or_zero(bucket["durationSessions"])
            paid = round(float_or_zero(bucket["paid"]), 2)
            minutes = round(float_or_zero(bucket["minutes"]), 1)
            week_start = bucket["weekStart"]
            week_end = bucket["weekEnd"]
            is_partial = week_start < start_day or week_end > end_day or week_end >= now_dt.date()
            points.append(
                {
                    "key": f"{bucket['isoYear']}-W{bucket['isoWeek']:02d}",
                    "label": f"Uke {bucket['isoWeek']}",
                    "shortLabel": f"U{bucket['isoWeek']}",
                    "rangeLabel": format_week_range(week_start, week_end),
                    "weekStart": week_start.isoformat(),
                    "weekEnd": week_end.isoformat(),
                    "isoYear": bucket["isoYear"],
                    "isoWeek": bucket["isoWeek"],
                    "sessions": sessions,
                    "paid": paid,
                    "minutes": minutes,
                    "durationSessions": duration_sessions,
                    "durationCoveragePct": round(duration_sessions * 100 / sessions, 1) if sessions else 0.0,
                    "avgPaidPerSession": round(paid / sessions, 2) if sessions else None,
                    "avgMinutesPerSession": round(minutes / duration_sessions, 1) if duration_sessions else None,
                    "isPartial": is_partial,
                }
            )

        points_with_data = [item for item in points if item["sessions"] > 0]
        latest = points_with_data[-1] if points_with_data else None
        previous = points_with_data[-2] if len(points_with_data) > 1 else None
        total_sessions = sum(int_or_zero(item["sessions"]) for item in points)
        total_paid = round(sum(float_or_zero(item["paid"]) for item in points), 2)
        duration_sessions = sum(int_or_zero(item["durationSessions"]) for item in points)
        total_minutes = round(sum(float_or_zero(item["minutes"]) for item in points), 1)

        def delta_pct(current: Any, reference: Any) -> Optional[float]:
            reference_value = float_or_zero(reference)
            if reference_value == 0:
                return None
            return round((float_or_zero(current) - reference_value) * 100 / reference_value, 1)

        return {
            "generatedAt": api_local_iso(now_dt),
            "period": {
                **{key: value for key, value in period.items() if key not in {"start", "end"}},
                "detail": f"{len(points_with_data)} uker med parkeringer",
            },
            "summary": {
                "sessions": total_sessions,
                "paid": total_paid,
                "minutes": total_minutes,
                "durationSessions": duration_sessions,
                "durationCoveragePct": round(duration_sessions * 100 / total_sessions, 1) if total_sessions else 0.0,
                "avgPaidPerSession": round(total_paid / total_sessions, 2) if total_sessions else 0.0,
                "avgMinutesPerSession": round(total_minutes / duration_sessions, 1) if duration_sessions else 0.0,
                "weeksWithData": len(points_with_data),
            },
            "latest": latest,
            "previous": previous,
            "delta": {
                "paidPct": delta_pct(
                    latest.get("avgPaidPerSession") if latest else None,
                    previous.get("avgPaidPerSession") if previous else None,
                ),
                "minutesPct": delta_pct(
                    latest.get("avgMinutesPerSession") if latest else None,
                    previous.get("avgMinutesPerSession") if previous else None,
                ),
            },
            "weeks": points,
        }

    def parking_weekly_selected_years(
        requested: Optional[str],
        available_years: list[int],
        current_iso_year: int,
    ) -> list[int]:
        available = sorted({int_or_zero(value) for value in available_years if int_or_zero(value) > 0}, reverse=True)
        available_set = set(available)
        selected = []
        for value in str(requested or "").split(","):
            parsed = int_or_zero(value.strip())
            if parsed in available_set and parsed not in selected:
                selected.append(parsed)
        if selected:
            return selected

        anchor = current_iso_year if current_iso_year in available_set else (available[0] if available else current_iso_year)
        previous = next((year for year in available if year < anchor), None)
        return [year for year in (anchor, previous) if year is not None]

    def parking_calendar_comparison_week(day_value: date) -> int:
        return ((day_value.timetuple().tm_yday - 1) // 7) + 1

    def parking_calendar_comparison_week_ranges(year_value: int) -> Dict[int, tuple[date, date]]:
        dates_by_week: Dict[int, list[date]] = defaultdict(list)
        cursor = date(year_value, 1, 1)
        end_day = date(year_value, 12, 31)
        while cursor <= end_day:
            dates_by_week[parking_calendar_comparison_week(cursor)].append(cursor)
            cursor += timedelta(days=1)
        return {week: (days[0], days[-1]) for week, days in dates_by_week.items()}

    def parking_weekly_year_comparison_payload(
        rows: Any,
        available_years: list[int],
        selected_years: list[int],
        now_dt: datetime,
    ) -> Dict[str, Any]:
        current_year = now_dt.year
        current_week = parking_calendar_comparison_week(now_dt.date())
        grouped: Dict[tuple[int, int], Dict[str, Any]] = {}
        for iso_year, iso_week, sessions, paid, minutes, duration_sessions in rows:
            year_value = int_or_zero(iso_year)
            week_value = int_or_zero(iso_week)
            if year_value <= 0 or week_value <= 0:
                continue
            grouped[(year_value, week_value)] = {
                "sessions": int_or_zero(sessions),
                "paid": round(float_or_zero(paid), 2),
                "minutes": round(float_or_zero(minutes), 1),
                "durationSessions": int_or_zero(duration_sessions),
            }

        colors = ["#2563eb", "#64748b", "#0f766e", "#7c3aed", "#be123c", "#0891b2", "#ea580c", "#f59e0b"]
        series = []
        for index, year_value in enumerate(selected_years):
            week_ranges = parking_calendar_comparison_week_ranges(year_value)
            points = []
            for week_value in range(1, 54):
                bucket = grouped.get((year_value, week_value), {})
                sessions = int_or_zero(bucket.get("sessions"))
                duration_sessions = int_or_zero(bucket.get("durationSessions"))
                paid = round(float_or_zero(bucket.get("paid")), 2)
                minutes = round(float_or_zero(bucket.get("minutes")), 1)
                week_range = week_ranges.get(week_value)
                week_start = week_range[0] if week_range else None
                week_end = week_range[1] if week_range else None
                points.append(
                    {
                        "week": week_value,
                        "label": f"U{week_value}",
                        "rangeLabel": f"{week_start:%d.%m.%Y} - {week_end:%d.%m.%Y}" if week_start and week_end else "",
                        "sessions": sessions,
                        "paid": paid,
                        "minutes": minutes,
                        "durationSessions": duration_sessions,
                        "durationCoveragePct": round(duration_sessions * 100 / sessions, 1) if sessions else 0.0,
                        "avgPaidPerSession": round(paid / sessions, 2) if sessions else None,
                        "avgMinutesPerSession": round(minutes / duration_sessions, 1) if duration_sessions else None,
                        "isPartial": year_value == current_year and week_value == current_week,
                        "isAvailable": week_range is not None,
                    }
                )

            year_sessions = sum(int_or_zero(point["sessions"]) for point in points)
            year_paid = round(sum(float_or_zero(point["paid"]) for point in points), 2)
            year_duration_sessions = sum(int_or_zero(point["durationSessions"]) for point in points)
            year_minutes = round(sum(float_or_zero(point["minutes"]) for point in points), 1)
            series.append(
                {
                    "year": year_value,
                    "label": str(year_value),
                    "color": colors[index % len(colors)],
                    "sessions": year_sessions,
                    "weeksWithData": sum(1 for point in points if point["sessions"] > 0),
                    "durationCoveragePct": round(year_duration_sessions * 100 / year_sessions, 1) if year_sessions else 0.0,
                    "avgPaidPerSession": round(year_paid / year_sessions, 2) if year_sessions else 0.0,
                    "avgMinutesPerSession": round(year_minutes / year_duration_sessions, 1) if year_duration_sessions else 0.0,
                    "points": points,
                }
            )

        default_years = parking_weekly_selected_years(None, available_years, current_year)
        return {
            "generatedAt": api_local_iso(now_dt),
            "currentYear": current_year,
            "currentWeek": current_week,
            "availableYears": sorted({int_or_zero(value) for value in available_years if int_or_zero(value) > 0}, reverse=True),
            "defaultYears": default_years,
            "selectedYears": selected_years,
            "series": series,
        }

    def parking_vehicle_not_found_field_labels(vehicle: ParkingVehicle) -> list[str]:
        is_not_found_marker = dependencies.is_not_found_marker
        labels = []
        if is_not_found_marker(vehicle.navn):
            labels.append("navn")
        if is_not_found_marker(vehicle.omrade):
            labels.append("område")
        return labels

    def decode_easypark_csv(content: bytes) -> str:
        if not content:
            return ""
        if content.startswith(b"\xff\xfe") or content.startswith(b"\xfe\xff"):
            return content.decode("utf-16", errors="replace")
        if len(content) > 2 and content[1] == 0:
            return content.decode("utf-16le", errors="replace")
        for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return content.decode("utf-8", errors="replace")

    def clean_easypark_value(value: Any) -> str:
        return str(value or "").replace("\x00", "").strip().strip('"').strip()

    def easypark_float(value: Any) -> Optional[float]:
        text_value = clean_easypark_value(value).replace("\xa0", " ").replace(" ", "")
        if not text_value:
            return None
        text_value = text_value.replace(",", ".")
        try:
            return float(text_value)
        except ValueError:
            return None

    def easypark_int(value: Any) -> Optional[int]:
        number = easypark_float(value)
        if number is None:
            text_value = re.sub(r"\D+", "", clean_easypark_value(value))
            return int(text_value) if text_value else None
        return int(number)

    def easypark_timestamp(value: Any) -> Optional[datetime]:
        text_value = clean_easypark_value(value)
        if not text_value:
            return None
        parsed = dtparser.parse(text_value)
        if parsed.tzinfo is not None:
            return parsed.astimezone(LOCAL_TZ).replace(tzinfo=None)
        return parsed.replace(tzinfo=None)

    def easypark_minutes(value: Any, start_at: Optional[datetime], end_at: Optional[datetime]) -> Optional[float]:
        explicit = easypark_float(value)
        if explicit is not None:
            return explicit
        if start_at and end_at:
            return round((end_at - start_at).total_seconds() / 60, 2)
        return None

    def parse_easypark_csv(content: bytes, filename: str) -> Dict[str, Any]:
        EASYPARK_REQUIRED_COLUMNS = dependencies.EASYPARK_REQUIRED_COLUMNS
        text_value = decode_easypark_csv(content)
        sample = text_value[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        except csv.Error:
            dialect = csv.excel()
            dialect.delimiter = ";"
        reader = csv.DictReader(StringIO(text_value), dialect=dialect)
        fieldnames = [clean_easypark_value(name) for name in (reader.fieldnames or [])]
        missing = sorted(EASYPARK_REQUIRED_COLUMNS - set(fieldnames))
        if missing:
            raise ValueError(f"EasyPark-filen mangler kolonner: {', '.join(missing)}")

        rows: list[Dict[str, Any]] = []
        skipped = 0
        for raw_row in reader:
            row = {clean_easypark_value(key): clean_easypark_value(value) for key, value in raw_row.items() if key is not None}
            parking_id = easypark_int(row.get("Parking ID"))
            area_number = easypark_int(row.get("Area number"))
            start_at = easypark_timestamp(row.get("Start date"))
            if not parking_id or not area_number or not start_at:
                skipped += 1
                continue
            end_at = easypark_timestamp(row.get("End date"))
            rows.append(
                {
                    "parking_area": row.get("Parking area") or "",
                    "source_system": row.get("Source parking system") or "EasyPark",
                    "area_number": area_number,
                    "parking_id": parking_id,
                    "start_time": start_at,
                    "end_time": end_at,
                    "parking_time_min": easypark_minutes(row.get("Parking time"), start_at, end_at),
                    "fee_ex_vat": easypark_float(row.get("Parking fee excluding VAT")),
                    "fee_inc_vat": easypark_float(row.get("Parking fee including VAT")),
                    "fee_vat": easypark_float(row.get("Parking fee VAT")),
                    "car_license_number": normalize_plate(row.get("Car license number")) or None,
                    "user_interface": row.get("User interface") or None,
                    "subtype": row.get("SubType") or None,
                    "status": row.get("Status") or "Ukjent",
                    "imported_at": datetime.utcnow(),
                    "raw_filename": filename,
                }
            )
        return {"rows": rows, "skipped": skipped, "filename": filename}

    async def ingest_easypark_csv(session, content: bytes, filename: str) -> Dict[str, Any]:
        parsed = parse_easypark_csv(content, filename)
        rows = parsed["rows"]
        if not rows:
            return {"total": 0, "inserted": 0, "updated": 0, "unchanged": 0, "skipped": parsed["skipped"], "first_at": None, "last_at": None}

        inserted_count = 0
        updated_count = 0
        for start in range(0, len(rows), 1000):
            chunk = rows[start:start + 1000]
            keys = [(row["source_system"], row["parking_id"]) for row in chunk]
            existing_keys = {
                tuple(row)
                for row in (
                    await session.execute(
                        select(ParkingSession.source_system, ParkingSession.parking_id).where(
                            tuple_(ParkingSession.source_system, ParkingSession.parking_id).in_(keys)
                        )
                    )
                ).all()
            }
            insert_stmt = pg_insert(ParkingSession).values(chunk)
            excluded = insert_stmt.excluded
            update_where = or_(
                ParkingSession.end_time.is_(None),
                func.lower(func.coalesce(ParkingSession.status, "")).in_(["ongoing", "active", "started"]),
                ParkingSession.parking_area.is_distinct_from(excluded.parking_area),
                ParkingSession.area_number.is_distinct_from(excluded.area_number),
                ParkingSession.start_time.is_distinct_from(excluded.start_time),
                ParkingSession.end_time.is_distinct_from(excluded.end_time),
                ParkingSession.parking_time_min.is_distinct_from(excluded.parking_time_min),
                ParkingSession.fee_ex_vat.is_distinct_from(excluded.fee_ex_vat),
                ParkingSession.fee_inc_vat.is_distinct_from(excluded.fee_inc_vat),
                ParkingSession.fee_vat.is_distinct_from(excluded.fee_vat),
                ParkingSession.car_license_number.is_distinct_from(excluded.car_license_number),
                ParkingSession.user_interface.is_distinct_from(excluded.user_interface),
                ParkingSession.subtype.is_distinct_from(excluded.subtype),
                ParkingSession.status.is_distinct_from(excluded.status),
            )
            stmt = (
                insert_stmt
                .on_conflict_do_update(
                    index_elements=["source_system", "parking_id"],
                    set_={
                        "parking_area": excluded.parking_area,
                        "area_number": excluded.area_number,
                        "start_time": excluded.start_time,
                        "end_time": excluded.end_time,
                        "parking_time_min": excluded.parking_time_min,
                        "fee_ex_vat": excluded.fee_ex_vat,
                        "fee_inc_vat": excluded.fee_inc_vat,
                        "fee_vat": excluded.fee_vat,
                        "car_license_number": excluded.car_license_number,
                        "user_interface": excluded.user_interface,
                        "subtype": excluded.subtype,
                        "status": excluded.status,
                        "imported_at": excluded.imported_at,
                        "raw_filename": excluded.raw_filename,
                    },
                    where=update_where,
                )
                .returning(ParkingSession.source_system, ParkingSession.parking_id)
            )
            affected_keys = {tuple(row) for row in (await session.execute(stmt)).all()}
            inserted_count += len(affected_keys - existing_keys)
            updated_count += len(affected_keys & existing_keys)
        first_at = min(row["start_time"] for row in rows)
        last_at = max(row["start_time"] for row in rows)
        return {
            "total": len(rows),
            "inserted": inserted_count,
            "updated": updated_count,
            "unchanged": len(rows) - inserted_count - updated_count,
            "skipped": parsed["skipped"],
            "first_at": first_at,
            "last_at": last_at,
        }

    async def refresh_parking_vehicle_summary(session) -> int:
        result = await session.execute(
            sql_text(
                """
            INSERT INTO kjoretoy (plate, first_seen, last_seen, parkering_count, paid_total, updated_at)
            SELECT
                upper(regexp_replace(car_license_number, '\\s+', '', 'g')) AS plate,
                min(start_time) AS first_seen,
                max(start_time) AS last_seen,
                count(*) AS parkering_count,
                round(sum(coalesce(fee_inc_vat, 0))::numeric, 2)::float AS paid_total,
                now() AS updated_at
            FROM parkering
            WHERE car_license_number IS NOT NULL AND btrim(car_license_number) <> ''
            GROUP BY 1
            ON CONFLICT (plate) DO UPDATE SET
                first_seen = coalesce(least(kjoretoy.first_seen, EXCLUDED.first_seen), kjoretoy.first_seen, EXCLUDED.first_seen),
                last_seen = coalesce(greatest(kjoretoy.last_seen, EXCLUDED.last_seen), kjoretoy.last_seen, EXCLUDED.last_seen),
                parkering_count = EXCLUDED.parkering_count,
                paid_total = EXCLUDED.paid_total,
                updated_at = now()
            RETURNING plate
            """
            )
        )
        return len(result.fetchall())

    def svv_api_lookup_sync(plate: str) -> Dict[str, Any]:
        SVV_API_AUTH_HEADER = dependencies.SVV_API_AUTH_HEADER
        SVV_API_AUTH_PREFIX = dependencies.SVV_API_AUTH_PREFIX
        SVV_API_KEY = dependencies.SVV_API_KEY
        SVV_API_URL = dependencies.SVV_API_URL
        if not SVV_API_KEY:
            raise RuntimeError("SVV_API_KEY mangler.")
        params = urlencode({"kjennemerke": compact_plate(plate)})
        url = f"{SVV_API_URL}?{params}"
        auth_value = " ".join(part for part in [SVV_API_AUTH_PREFIX, SVV_API_KEY] if part).strip()
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                SVV_API_AUTH_HEADER: auth_value,
                "User-Agent": "fibaro10/1.0",
            },
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            status_code = response.getcode()
            payload = response.read().decode("utf-8", errors="replace")
        if status_code == 204 or not payload.strip():
            raise LookupError("Ingen kjøretøydata fra SVV")
        return json.loads(payload)

    async def svv_candidate_plates(session, limit: int) -> list[str]:
        SVV_PERMANENT_NO_DATA_STATUSES = dependencies.SVV_PERMANENT_NO_DATA_STATUSES
        SVV_RETRY_AFTER_HOURS = dependencies.SVV_RETRY_AFTER_HOURS
        SVV_TRANSIENT_RETRY_AFTER_MINUTES = dependencies.SVV_TRANSIENT_RETRY_AFTER_MINUTES
        SVV_TRANSIENT_STATUSES = dependencies.SVV_TRANSIENT_STATUSES
        retry_before = datetime.utcnow() - timedelta(hours=SVV_RETRY_AFTER_HOURS)
        transient_retry_before = datetime.utcnow() - timedelta(minutes=SVV_TRANSIENT_RETRY_AFTER_MINUTES)
        permanent_no_data = list(SVV_PERMANENT_NO_DATA_STATUSES)
        transient_statuses = list(SVV_TRANSIENT_STATUSES)
        rows = (
            await session.execute(
                select(ParkingVehicle.plate)
                .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                .where(ParkingVehicle.plate.isnot(None))
                .where(ParkingVehicle.plate != "")
                .where(
                    or_(
                        ParkingVehicle.svv_status.is_(None),
                        ParkingVehicle.svv_fetched_at.is_(None),
                        and_(
                            ParkingVehicleDetails.plate.is_(None),
                            ParkingVehicle.svv_status.notin_(permanent_no_data),
                            ParkingVehicle.svv_status.notin_(transient_statuses),
                        ),
                        and_(
                            ParkingVehicle.svv_status.notin_([200, *permanent_no_data]),
                            ParkingVehicle.svv_status.notin_(transient_statuses),
                            ParkingVehicle.svv_fetched_at < retry_before,
                        ),
                        and_(
                            ParkingVehicle.svv_status.in_(transient_statuses),
                            ParkingVehicle.svv_fetched_at < transient_retry_before,
                        ),
                    )
                )
                .order_by(
                    case((ParkingVehicleDetails.plate.is_(None), 0), else_=1),
                    ParkingVehicle.svv_fetched_at.asc().nullsfirst(),
                    ParkingVehicle.last_seen.desc().nullslast(),
                )
                .limit(limit)
            )
        ).scalars().all()
        return [plate for plate in rows if compact_plate(plate)]

    async def parking_vehicle_by_plate_or_compact(session, plate: str) -> Optional[ParkingVehicle]:
        plate_value = compact_plate(plate)
        if not plate_value:
            return None
        vehicle = (
            await session.execute(
                select(ParkingVehicle).where(ParkingVehicle.plate == plate_value)
            )
        ).scalars().first()
        if vehicle:
            return vehicle
        return (
            await session.execute(
                select(ParkingVehicle)
                .where(compact_plate_sql(ParkingVehicle.plate) == plate_value)
                .order_by(ParkingVehicle.last_seen.desc().nullslast(), ParkingVehicle.plate.asc())
                .limit(1)
            )
        ).scalars().first()

    async def upsert_vehicle_svv_data(session, plate: str, raw: Dict[str, Any], status_code: int = 200, error: Optional[str] = None) -> bool:
        plate_value = compact_plate(plate)
        vehicle = await parking_vehicle_by_plate_or_compact(session, plate_value)
        if not vehicle:
            return False
        now = datetime.utcnow()
        vehicle.svv_fetched_at = now
        vehicle.svv_status = status_code
        vehicle.svv_error = error
        vehicle.svv_data = raw if raw else None
        vehicle.updated_at = now
        if status_code != 200 or not raw:
            return False
        values = svv_detail_values(plate_value, raw)
        values["plate"] = vehicle.plate
        detail = (await session.execute(select(ParkingVehicleDetails).where(ParkingVehicleDetails.plate == vehicle.plate))).scalars().first()
        if not detail:
            detail = ParkingVehicleDetails(plate=vehicle.plate)
            session.add(detail)
        for key, value in values.items():
            setattr(detail, key, value)
        return True

    async def run_vehicle_svv_sync(limit: int = SVV_SYNC_BATCH_SIZE, source: str = "background") -> Dict[str, Any]:
        SVV_API_KEY = dependencies.SVV_API_KEY
        SVV_PERMANENT_NO_DATA_STATUSES = dependencies.SVV_PERMANENT_NO_DATA_STATUSES
        SVV_TRANSIENT_RETRY_AFTER_MINUTES = dependencies.SVV_TRANSIENT_RETRY_AFTER_MINUTES
        SVV_TRANSIENT_STATUSES = dependencies.SVV_TRANSIENT_STATUSES
        async_session = dependencies.async_session
        record_import_job = dependencies.record_import_job
        started_at = local_now_naive()
        if not SVV_API_KEY:
            async with async_session() as session:
                await record_import_job(
                    session,
                    "parking_vehicle_svv_sync",
                    ok=False,
                    source=source,
                    started_at=started_at,
                    records_imported=0,
                    records_total=0,
                    message="SVV_API_KEY mangler.",
                )
                await session.commit()
            return {"ok": False, "processed": 0, "updated": 0, "failed": 0, "message": "SVV_API_KEY mangler."}
        processed = updated = no_data = failed = 0
        errors: list[str] = []
        foreign_no_data_plates: list[str] = []
        async with async_session() as session:
            plates = await svv_candidate_plates(session, limit)
            if not plates:
                transient_retry_before = datetime.utcnow() - timedelta(minutes=SVV_TRANSIENT_RETRY_AFTER_MINUTES)
                transient_waiting = (
                    await session.execute(
                        select(func.count())
                        .select_from(ParkingVehicle)
                        .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                        .where(ParkingVehicleDetails.plate.is_(None))
                        .where(ParkingVehicle.svv_status.in_(list(SVV_TRANSIENT_STATUSES)))
                        .where(ParkingVehicle.svv_fetched_at >= transient_retry_before)
                    )
                ).scalar_one()
                if transient_waiting:
                    message = f"SVV svarte midlertidig feil sist. {transient_waiting} kj\u00f8ret\u00f8y venter p\u00e5 ny pr\u00f8ve."
                    await record_import_job(
                        session,
                        "parking_vehicle_svv_sync",
                        ok=False,
                        source=source,
                        started_at=started_at,
                        records_imported=0,
                        records_total=transient_waiting,
                        message=message,
                        raw={"transient_waiting": transient_waiting},
                    )
                    await session.commit()
                    return {"ok": False, "processed": 0, "updated": 0, "no_data": 0, "failed": transient_waiting, "errors": [message]}
            for plate in plates:
                processed += 1
                try:
                    raw = await asyncio.to_thread(svv_api_lookup_sync, plate)
                    if await upsert_vehicle_svv_data(session, plate, raw, 200, None):
                        updated += 1
                except LookupError as exc:
                    no_data += 1
                    if is_supported_foreign_license_plate(plate):
                        foreign_no_data_plates.append(compact_plate(plate))
                    message = str(exc)[:240] or "Ingen kjøretøydata fra SVV"
                    await upsert_vehicle_svv_data(session, plate, {}, 204, message)
                except urllib.error.HTTPError as exc:
                    message = "Ikke funnet eller ugyldig kjennemerke hos SVV" if exc.code in SVV_PERMANENT_NO_DATA_STATUSES else f"HTTP {exc.code}"
                    if exc.code not in SVV_PERMANENT_NO_DATA_STATUSES:
                        body = exc.read().decode("utf-8", errors="replace").strip()[:160]
                        if body:
                            message = f"{message}: {body}"
                    if exc.code in SVV_PERMANENT_NO_DATA_STATUSES:
                        no_data += 1
                        if is_supported_foreign_license_plate(plate):
                            foreign_no_data_plates.append(compact_plate(plate))
                    else:
                        failed += 1
                        errors.append(f"{plate}: {message}")
                    await upsert_vehicle_svv_data(session, plate, {}, exc.code, message)
                    if exc.code in SVV_TRANSIENT_STATUSES:
                        await session.commit()
                        break
                except json.JSONDecodeError:
                    no_data += 1
                    if is_supported_foreign_license_plate(plate):
                        foreign_no_data_plates.append(compact_plate(plate))
                    message = "Tomt eller uleselig svar fra SVV"
                    await upsert_vehicle_svv_data(session, plate, {}, 204, message)
                except Exception as exc:
                    failed += 1
                    message = str(exc)[:240]
                    errors.append(f"{plate}: {message}")
                    await upsert_vehicle_svv_data(session, plate, {}, 0, message)
                await session.commit()
            job_ok = failed == 0
            await record_import_job(
                session,
                "parking_vehicle_svv_sync",
                ok=job_ok,
                source=source,
                started_at=started_at,
                records_imported=updated,
                records_total=processed,
                message=f"{updated} oppdatert, {no_data} uten treff, {failed} feilet, {processed} behandlet.",
                raw={"errors": errors[:20], "no_data": no_data},
            )
            await session.commit()
        result_payload = {
            "ok": failed == 0,
            "processed": processed,
            "updated": updated,
            "no_data": no_data,
            "failed": failed,
            "errors": errors[:20],
            "foreign_no_data": foreign_no_data_plates[:20],
            "swedish_no_data": [plate for plate in foreign_no_data_plates if is_swedish_license_plate(plate)][:20],
            "danish_no_data": [plate for plate in foreign_no_data_plates if is_danish_license_plate(plate)][:20],
        }
        car_info_auto = await trigger_car_info_after_svv_no_data(foreign_no_data_plates, source)
        if car_info_auto:
            result_payload["car_info_auto_trigger"] = car_info_auto
        return result_payload

    async def parking_vehicle_svv_worker() -> None:
        SVV_SYNC_BATCH_SIZE = dependencies.SVV_SYNC_BATCH_SIZE
        SVV_SYNC_INTERVAL_MINUTES = dependencies.SVV_SYNC_INTERVAL_MINUTES
        await asyncio.sleep(30)
        while True:
            try:
                await run_vehicle_svv_sync(SVV_SYNC_BATCH_SIZE, "SVV bakgrunn")
            except Exception:
                pass
            await asyncio.sleep(SVV_SYNC_INTERVAL_MINUTES * 60)

    async def parking_period_summary(session, label: str, start_at: datetime, end_at: datetime) -> Dict[str, Any]:
        row = (
            await session.execute(
                select(
                    func.count(ParkingSession.id),
                    func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0),
                ).where(
                    ParkingSession.start_time >= start_at,
                    ParkingSession.start_time < end_at,
                )
            )
        ).first()
        return {"label": label, "count": row[0] or 0, "paid": row[1] or 0}

    def easypark_recent_period() -> tuple[date, date]:
        today = local_now_naive().date()
        return today - timedelta(days=1), today

    def easypark_downloader_request(path: str, params: Dict[str, Any], timeout_seconds: int = 180) -> Dict[str, Any]:
        EASYPARK_DOWNLOADER_URL = dependencies.EASYPARK_DOWNLOADER_URL
        query = urlencode({key: value for key, value in params.items() if value is not None})
        url = f"{EASYPARK_DOWNLOADER_URL}{path}"
        if query:
            url = f"{url}?{query}"
        request = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read().decode("utf-8", errors="replace")
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ugyldig svar fra EasyPark-downloader: {payload[:240]}") from exc

    def easypark_downloader_status() -> Dict[str, Any]:
        EASYPARK_DOWNLOADER_URL = dependencies.EASYPARK_DOWNLOADER_URL
        try:
            with urllib.request.urlopen(f"{EASYPARK_DOWNLOADER_URL}/status", timeout=2) as response:
                payload = response.read().decode("utf-8", errors="replace")
            return json.loads(payload)
        except Exception:
            return {}

    def easypark_next_run_at_from_status(status: Dict[str, Any]) -> Optional[datetime]:
        schedule = status.get("schedule") if isinstance(status, dict) else None
        next_run_at = schedule.get("next_run_at") if isinstance(schedule, dict) else status.get("next_run_at")
        parsed = parse_datetime(next_run_at) if next_run_at else None
        if not parsed:
            return None
        if parsed.tzinfo is not None:
            return parsed.astimezone(LOCAL_TZ).replace(tzinfo=None)
        return parsed

    def car_info_lookup_request(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        CAR_INFO_APP_TOKEN = dependencies.CAR_INFO_APP_TOKEN
        CAR_INFO_LOOKUP_TIMEOUT_SECONDS = dependencies.CAR_INFO_LOOKUP_TIMEOUT_SECONDS
        CAR_INFO_LOOKUP_URL = dependencies.CAR_INFO_LOOKUP_URL
        query = urlencode({key: value for key, value in params.items() if value is not None})
        url = f"{CAR_INFO_LOOKUP_URL}{path}"
        if query:
            url = f"{url}?{query}"
        request = urllib.request.Request(url, method="POST", headers={"Accept": "application/json"})
        if CAR_INFO_APP_TOKEN:
            request.add_header("x-car-info-token", CAR_INFO_APP_TOKEN)
        with urllib.request.urlopen(request, timeout=CAR_INFO_LOOKUP_TIMEOUT_SECONDS) as response:
            payload = response.read().decode("utf-8", errors="replace")
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ugyldig svar fra nordisk biloppslag: {payload[:240]}") from exc

    async def trigger_car_info_after_svv_no_data(plates: list[str], source: str) -> Optional[Dict[str, Any]]:
        CAR_INFO_AUTO_TRIGGER_ENABLED = dependencies.CAR_INFO_AUTO_TRIGGER_ENABLED
        CAR_INFO_AUTO_TRIGGER_MAX_PER_SVV_RUN = dependencies.CAR_INFO_AUTO_TRIGGER_MAX_PER_SVV_RUN
        if not CAR_INFO_AUTO_TRIGGER_ENABLED or CAR_INFO_AUTO_TRIGGER_MAX_PER_SVV_RUN <= 0:
            return None
        candidates: list[str] = []
        seen: set[str] = set()
        for plate in plates:
            compact = compact_plate(plate)
            if compact and compact not in seen and is_supported_foreign_license_plate(compact):
                candidates.append(compact)
                seen.add(compact)
        if not candidates:
            return None

        selected = candidates[:CAR_INFO_AUTO_TRIGGER_MAX_PER_SVV_RUN]
        results: list[Dict[str, Any]] = []
        errors: list[str] = []
        for plate in selected:
            try:
                result = await asyncio.to_thread(car_info_lookup_request, f"/api/run-plate/{plate}", {})
                results.append(result)
                if result.get("status") == "error":
                    errors.append(f"{plate}: {str(result.get('message') or 'nordisk biloppslag-feil')[:240]}")
                    break
                if result.get("status") in {"backoff", "busy"} or result.get("rate_limited"):
                    break
            except Exception as exc:
                errors.append(f"{plate}: {str(exc)[:240]}")
                break

        ok = not errors
        return {"ok": ok, "candidates": candidates, "triggered": selected, "results": results, "errors": errors}

    async def clear_parking_vehicle_not_found_area(session) -> int:
        result = await session.execute(
            update(ParkingVehicle)
            .where(func.lower(func.trim(func.coalesce(ParkingVehicle.omrade, ""))) == "ikke funnet")
            .values(
                omrade=None,
                omrade_kilde=None,
                omrade_oppdatert=None,
            )
        )
        return int_or_zero(result.rowcount)

    async def clear_parking_vehicle_not_found_fields(session, plate_value: str) -> Optional[list[str]]:
        is_not_found_marker = dependencies.is_not_found_marker
        vehicle = (await session.execute(select(ParkingVehicle).where(ParkingVehicle.plate == plate_value))).scalars().first()
        if not vehicle:
            return None
        cleared_fields = []
        if is_not_found_marker(vehicle.navn):
            vehicle.navn = None
            cleared_fields.append("navn")
        if is_not_found_marker(vehicle.omrade):
            vehicle.omrade = None
            vehicle.omrade_kilde = None
            vehicle.omrade_oppdatert = None
            cleared_fields.append("område")
        if cleared_fields:
            vehicle.updated_at = datetime.utcnow()
        return cleared_fields

    def vehicle_blank_name_condition():
        normalized = func.lower(func.trim(func.coalesce(ParkingVehicle.navn, "")))
        return normalized == ""

    def vehicle_name_not_found_condition():
        normalized = func.lower(func.trim(func.coalesce(ParkingVehicle.navn, "")))
        return normalized == "ikke funnet"

    def vehicle_missing_name_condition():
        return or_(vehicle_blank_name_condition(), vehicle_name_not_found_condition())

    def vehicle_blank_area_condition():
        normalized = func.lower(func.trim(func.coalesce(ParkingVehicle.omrade, "")))
        return normalized == ""

    def vehicle_area_not_found_condition():
        normalized = func.lower(func.trim(func.coalesce(ParkingVehicle.omrade, "")))
        return normalized == "ikke funnet"

    def vehicle_missing_area_condition():
        return or_(vehicle_blank_area_condition(), vehicle_area_not_found_condition())

    async def parking_vehicle_count_stats(session) -> Dict[str, int]:
        row = (
            await session.execute(
                select(
                    func.count(ParkingVehicle.plate).label("vehicle_count"),
                    func.coalesce(func.sum(case((vehicle_blank_name_condition(), 1), else_=0)), 0).label("blank_name"),
                    func.coalesce(func.sum(case((vehicle_name_not_found_condition(), 1), else_=0)), 0).label("name_not_found"),
                    func.coalesce(func.sum(case((vehicle_blank_area_condition(), 1), else_=0)), 0).label("blank_area"),
                    func.coalesce(func.sum(case((vehicle_area_not_found_condition(), 1), else_=0)), 0).label("area_not_found"),
                )
            )
        ).mappings().one()
        blank_name = int_or_zero(row["blank_name"])
        name_not_found = int_or_zero(row["name_not_found"])
        blank_area = int_or_zero(row["blank_area"])
        area_not_found = int_or_zero(row["area_not_found"])
        return {
            "vehicle_count": int_or_zero(row["vehicle_count"]),
            "vehicle_blank_name_count": blank_name,
            "vehicle_name_not_found_count": name_not_found,
            "vehicle_missing_name_count": blank_name + name_not_found,
            "vehicle_blank_area_count": blank_area,
            "vehicle_area_not_found_count": area_not_found,
            "vehicle_missing_area_count": blank_area + area_not_found,
        }

    def api_parking_default_actions() -> list[Dict[str, Any]]:
        return [
            {
                "key": "easypark-refresh",
                "label": "Oppdater EasyPark",
                "method": "POST",
                "path": "/api/actions/parkering/refresh",
                "confirm": "Starte EasyPark-oppdatering for siste periode?",
                "tone": "primary",
            },
            {
                "key": "svv-sync",
                "label": "Kj\u00f8r SVV-sync",
                "method": "POST",
                "path": "/api/actions/parkering/svv-sync",
                "confirm": "Starte SVV-synk for kj\u00f8ret\u00f8y?",
                "tone": "default",
            },
        ]

    def api_parking_clear_area_not_found_action(vehicle_area_not_found_count: int) -> Dict[str, Any]:
        return {
            "key": "clear-area-not-found",
            "label": "Fjern omr\u00e5de 'ikke funnet'",
            "method": "POST",
            "path": "/api/actions/parkering/clear-area-not-found",
            "confirm": (
                f"Nullstille omr\u00e5de p\u00e5 {format_short_number(vehicle_area_not_found_count)} kj\u00f8ret\u00f8y "
                "der omr\u00e5de er satt til 'ikke funnet'? De blir liggende som blanke og kan sl\u00e5s opp p\u00e5 nytt."
            ),
            "tone": "default",
        }

    def vehicle_car_info_due_condition():
        CAR_INFO_CANDIDATE_RETRY_HOURS = dependencies.CAR_INFO_CANDIDATE_RETRY_HOURS
        CAR_INFO_CANDIDATE_TRANSIENT_RETRY_MINUTES = dependencies.CAR_INFO_CANDIDATE_TRANSIENT_RETRY_MINUTES
        retry_before = datetime.utcnow() - timedelta(hours=CAR_INFO_CANDIDATE_RETRY_HOURS)
        transient_retry_before = datetime.utcnow() - timedelta(minutes=CAR_INFO_CANDIDATE_TRANSIENT_RETRY_MINUTES)
        return or_(
            ParkingVehicle.car_info_fetched_at.is_(None),
            ParkingVehicle.car_info_status.is_(None),
            and_(
                ParkingVehicle.car_info_status.in_([0, 429, 500, 502, 503, 504]),
                ParkingVehicle.car_info_fetched_at < transient_retry_before,
            ),
            and_(
                ParkingVehicle.car_info_status.notin_([200]),
                ParkingVehicle.car_info_fetched_at < retry_before,
            ),
        )

    def vehicle_car_info_candidate_condition():
        compact = compact_plate_sql(ParkingVehicle.plate)
        return and_(
            ParkingVehicle.svv_fetched_at.isnot(None),
            ParkingVehicleDetails.plate.is_(None),
            or_(
                compact.op("~")(SWEDISH_LICENSE_PLATE_SQL_REGEX),
                compact.op("~")(DANISH_LICENSE_PLATE_SQL_REGEX),
            ),
            vehicle_car_info_due_condition(),
        )

    def vehicle_car_info_country_condition(country: Optional[str]):
        key = (country or "").strip().upper()
        compact = compact_plate_sql(ParkingVehicle.plate)
        if key in {"S", "SE", "SWE", "SVERIGE", "SWEDEN"}:
            return compact.op("~")(SWEDISH_LICENSE_PLATE_SQL_REGEX)
        if key in {"DK", "DANMARK", "DENMARK"}:
            return compact.op("~")(DANISH_LICENSE_PLATE_SQL_REGEX)
        return None

    async def parking_car_info_candidate_rows(session, limit: int, offset: int = 0, country: Optional[str] = None):
        condition = vehicle_car_info_candidate_condition()
        country_condition = vehicle_car_info_country_condition(country)
        if country_condition is not None:
            condition = and_(condition, country_condition)
        return (
            await session.execute(
                select(ParkingVehicle, ParkingVehicleDetails)
                .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                .where(condition)
                .order_by(
                    ParkingVehicle.car_info_fetched_at.asc().nullsfirst(),
                    ParkingVehicle.last_seen.desc().nullslast(),
                    ParkingVehicle.plate.asc(),
                )
                .offset(offset)
                .limit(limit)
            )
        ).all()

    async def parking_missing_name_rows(session, limit: int, offset: int = 0, include_not_found: bool = True):
        condition = vehicle_missing_name_condition() if include_not_found else vehicle_blank_name_condition()
        return (
            await session.execute(
                select(ParkingVehicle, ParkingVehicleDetails)
                .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                .where(condition)
                .order_by(ParkingVehicle.last_seen.desc().nullslast(), ParkingVehicle.plate.asc())
                .offset(offset)
                .limit(limit)
            )
        ).all()

    async def parking_missing_area_rows(session, limit: int, offset: int = 0, include_not_found: bool = True):
        condition = vehicle_missing_area_condition() if include_not_found else vehicle_blank_area_condition()
        return (
            await session.execute(
                select(ParkingVehicle, ParkingVehicleDetails)
                .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                .where(condition)
                .order_by(ParkingVehicle.last_seen.desc().nullslast(), ParkingVehicle.plate.asc())
                .offset(offset)
                .limit(limit)
            )
        ).all()

    def parking_vehicle_lookup_payload(vehicle: ParkingVehicle, details: Optional[ParkingVehicleDetails] = None) -> Dict[str, Any]:
        return {
            "plate": vehicle.plate,
            "navn": vehicle.navn,
            "omrade": vehicle.omrade,
            "sun2_id": vehicle.sun2_id,
            "notat": vehicle.notat,
            "last_seen": vehicle.last_seen.isoformat() if vehicle.last_seen else None,
            "parkering_count": vehicle.parkering_count,
            "vehicle": parking_vehicle_summary(details, vehicle.car_info_data),
            "make": details.merke if details else None,
            "model": details.modell if details else None,
            "year": parking_vehicle_display_year(details, vehicle.car_info_data),
            "svv_status": vehicle.svv_status,
            "svv_fetched_at": vehicle.svv_fetched_at.isoformat() if vehicle.svv_fetched_at else None,
            "car_info_status": vehicle.car_info_status,
            "car_info_fetched_at": vehicle.car_info_fetched_at.isoformat() if vehicle.car_info_fetched_at else None,
            "car_info_url": vehicle.car_info_url,
            "car_info_confirmed_swedish": car_info_confirmed_swedish(vehicle.car_info_data),
            "car_info_confirmed_foreign": car_info_confirmed_foreign(vehicle.car_info_data),
            "car_info_country_code": car_info_country_code(vehicle.car_info_data) or None,
        }

    return {
        "api_parking_clear_area_not_found_action": api_parking_clear_area_not_found_action,
        "api_parking_day_timeline": api_parking_day_timeline,
        "api_parking_default_actions": api_parking_default_actions,
        "api_parking_forecast_evolution_chart": api_parking_forecast_evolution_chart,
        "api_parking_forecast_rows": api_parking_forecast_rows,
        "api_parking_overview_tables": api_parking_overview_tables,
        "api_parking_saved_forecast_rows": api_parking_saved_forecast_rows,
        "api_parking_summary_row": api_parking_summary_row,
        "api_parking_time_distribution": api_parking_time_distribution,
        "api_parking_weekly_chart": api_parking_weekly_chart,
        "build_parking_forecast": build_parking_forecast,
        "car_info_lookup_request": car_info_lookup_request,
        "clean_easypark_value": clean_easypark_value,
        "clear_parking_vehicle_not_found_area": clear_parking_vehicle_not_found_area,
        "clear_parking_vehicle_not_found_fields": clear_parking_vehicle_not_found_fields,
        "decode_easypark_csv": decode_easypark_csv,
        "easypark_downloader_request": easypark_downloader_request,
        "easypark_downloader_status": easypark_downloader_status,
        "easypark_float": easypark_float,
        "easypark_int": easypark_int,
        "easypark_minutes": easypark_minutes,
        "easypark_next_run_at_from_status": easypark_next_run_at_from_status,
        "easypark_recent_period": easypark_recent_period,
        "easypark_timestamp": easypark_timestamp,
        "fallback_car_info_import_status": fallback_car_info_import_status,
        "has_car_info_app_access": has_car_info_app_access,
        "ingest_easypark_csv": ingest_easypark_csv,
        "is_car_info_app_request_path": is_car_info_app_request_path,
        "parking_area_missing_rows_for_period": parking_area_missing_rows_for_period,
        "parking_area_overview_data": parking_area_overview_data,
        "parking_area_period": parking_area_period,
        "parking_area_period_conditions": parking_area_period_conditions,
        "parking_area_row_api": parking_area_row_api,
        "parking_calendar_comparison_week": parking_calendar_comparison_week,
        "parking_calendar_comparison_week_ranges": parking_calendar_comparison_week_ranges,
        "parking_car_info_candidate_rows": parking_car_info_candidate_rows,
        "parking_departure_slot_delta_minutes": parking_departure_slot_delta_minutes,
        "parking_missing_area_rows": parking_missing_area_rows,
        "parking_missing_name_rows": parking_missing_name_rows,
        "parking_period_summary": parking_period_summary,
        "parking_previous_stats_for_rows": parking_previous_stats_for_rows,
        "parking_row_api": parking_row_api,
        "parking_time_distribution_period": parking_time_distribution_period,
        "parking_time_weekday_day_counts": parking_time_weekday_day_counts,
        "parking_timeline_end": parking_timeline_end,
        "parking_valid_vehicle_area_condition": parking_valid_vehicle_area_condition,
        "parking_vehicle_by_plate_or_compact": parking_vehicle_by_plate_or_compact,
        "parking_vehicle_count_stats": parking_vehicle_count_stats,
        "parking_vehicle_lookup_payload": parking_vehicle_lookup_payload,
        "parking_vehicle_not_found_field_labels": parking_vehicle_not_found_field_labels,
        "parking_vehicle_row_api": parking_vehicle_row_api,
        "parking_vehicle_search_condition": parking_vehicle_search_condition,
        "parking_vehicle_svv_worker": parking_vehicle_svv_worker,
        "parking_weekly_average_payload": parking_weekly_average_payload,
        "parking_weekly_average_period": parking_weekly_average_period,
        "parking_weekly_selected_years": parking_weekly_selected_years,
        "parking_weekly_year_comparison_payload": parking_weekly_year_comparison_payload,
        "parse_easypark_csv": parse_easypark_csv,
        "refresh_parking_vehicle_summary": refresh_parking_vehicle_summary,
        "require_settings_or_car_info_access": require_settings_or_car_info_access,
        "run_vehicle_svv_sync": run_vehicle_svv_sync,
        "save_parking_forecast_after_import": save_parking_forecast_after_import,
        "status_parking_timeline_event": status_parking_timeline_event,
        "svv_api_lookup_sync": svv_api_lookup_sync,
        "svv_candidate_plates": svv_candidate_plates,
        "trigger_car_info_after_svv_no_data": trigger_car_info_after_svv_no_data,
        "unpaid_registered_vehicle_stays_payload": unpaid_registered_vehicle_stays_payload,
        "upsert_vehicle_svv_data": upsert_vehicle_svv_data,
        "vehicle_area_not_found_condition": vehicle_area_not_found_condition,
        "vehicle_blank_area_condition": vehicle_blank_area_condition,
        "vehicle_blank_name_condition": vehicle_blank_name_condition,
        "vehicle_car_info_candidate_condition": vehicle_car_info_candidate_condition,
        "vehicle_car_info_country_condition": vehicle_car_info_country_condition,
        "vehicle_car_info_due_condition": vehicle_car_info_due_condition,
        "vehicle_missing_area_condition": vehicle_missing_area_condition,
        "vehicle_missing_name_condition": vehicle_missing_name_condition,
        "vehicle_name_not_found_condition": vehicle_name_not_found_condition,
    }
