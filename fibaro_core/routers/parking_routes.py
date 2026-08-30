"""Parking HTTP routes; runtime services are supplied by composition."""

from cars_domain import cars_confidence_level
from cars_domain import cars_daily_payment_metrics
from cars_domain import cars_group_daily_recognitions
from cars_domain import cars_public_detection
from cars_domain import cars_recognition_local_datetime
from cars_domain import cars_unifi_score
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from datetime import timezone
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import Response
from fastapi.responses import StreamingResponse
from fibaro_core.models import ImportJobStatus
from fibaro_core.models import ParkingSession
from fibaro_core.models import ParkingVehicle
from fibaro_core.models import ParkingVehicleDetails
from fibaro_core.routers.bundle import RouterBundle
from fibaro_core.schemas import ParkingVehicleAreaUpdate
from fibaro_core.schemas import ParkingVehicleCarInfoUpdate
from fibaro_core.schemas import ParkingVehicleNameUpdate
from fibaro_core.services.comparisons.years import build_parking_year_comparison
from fibaro_core.services.forecasts.snapshots import save_forecast_snapshots
from fibaro_core.services.forecasts.snapshots import saved_forecast_table
from fibaro_core.services.presentation import api_card
from fibaro_core.services.presentation import format_short_number
from fibaro_core.services.settlements.mail import fetch_parking_settlements_from_gmail
from fibaro_core.services.summaries.periods import add_months
from fibaro_core.services.summaries.periods import month_label
from fibaro_core.services.summaries.periods import parse_anchor_year
from parking_vehicle_helpers import car_info_area_label
from parking_vehicle_helpers import car_info_confirmed_foreign
from parking_vehicle_helpers import car_info_confirmed_swedish
from parking_vehicle_helpers import car_info_field_value
from parking_vehicle_helpers import car_info_import_job_name
from parking_vehicle_helpers import car_info_import_ok
from parking_vehicle_helpers import car_info_lookup_country_code
from parking_vehicle_helpers import car_info_provider_label
from parking_vehicle_helpers import car_info_source_label
from parking_vehicle_helpers import car_info_status_label
from parking_vehicle_helpers import compact_plate
from parking_vehicle_helpers import compact_plate_sql
from parking_vehicle_helpers import is_supported_foreign_license_plate
from parking_vehicle_helpers import normalize_plate
from parking_vehicle_helpers import parking_current_ownership_warning
from parking_vehicle_helpers import parking_duration_minutes
from parking_vehicle_helpers import parking_row_context
from parking_vehicle_helpers import parking_slot_remainder_minutes
from parking_vehicle_helpers import parking_vehicle_display_class
from parking_vehicle_helpers import parking_vehicle_display_color
from parking_vehicle_helpers import parking_vehicle_display_inspection_deadline
from parking_vehicle_helpers import parking_vehicle_display_label
from parking_vehicle_helpers import parking_vehicle_display_registration_status
from parking_vehicle_helpers import parking_vehicle_display_source
from parking_vehicle_helpers import parking_vehicle_display_year
from parking_vehicle_helpers import parking_vehicle_summary
from parking_vehicle_helpers import parking_vehicle_year
from parking_vehicle_helpers import svv_current_ownership_at
from sqlalchemy import Integer
from sqlalchemy import and_
from sqlalchemy import case
from sqlalchemy import cast
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from time_formatting import LOCAL_TZ
from time_formatting import api_local_iso
from time_formatting import local_now_naive
from time_formatting import normalize_local_naive
from typing import Any
from typing import Any, Callable
from typing import Dict
from typing import Mapping
from typing import Optional
from urllib.parse import quote
from value_parsing import float_or_zero
from value_parsing import int_or_zero
import asyncio
import imaplib
import json


@dataclass
class Dependencies:
    CARS_DAY_CACHE_TTL: Any
    CARS_HISTORY_CACHE_TTL: Any
    SUMMARY_CACHE: Any
    SVV_API_KEY: Any
    SVV_IMPORT_SYNC_BATCH_SIZE: Any
    SVV_SYNC_BATCH_SIZE: Any
    SVV_SYNC_ENABLED: Any
    api_detail_field: Callable[..., Any]
    api_parking_time_distribution: Callable[..., Any]
    async_session: Callable[..., Any]
    build_parking_forecast: Callable[..., Any]
    car_info_lookup_request: Callable[..., Any]
    clear_parking_vehicle_not_found_area: Callable[..., Any]
    clear_parking_vehicle_not_found_fields: Callable[..., Any]
    clear_summary_cache: Callable[..., Any]
    easypark_downloader_request: Callable[..., Any]
    easypark_recent_period: Callable[..., Any]
    get_parking_summaries: Callable[..., Any]
    import_counts_for_json: Callable[..., Any]
    import_job_definition: Callable[..., Any]
    import_job_status_from_age: Callable[..., Any]
    ingest_easypark_csv: Callable[..., Any]
    is_not_found_marker: Callable[..., Any]
    logger: Any
    normalize_month: Callable[..., Any]
    parking_area_overview_data: Callable[..., Any]
    parking_car_info_candidate_rows: Callable[..., Any]
    parking_missing_area_rows: Callable[..., Any]
    parking_missing_name_rows: Callable[..., Any]
    parking_period_summary: Callable[..., Any]
    parking_row_api: Callable[..., Any]
    parking_timeline_end: Callable[..., Any]
    parking_vehicle_by_plate_or_compact: Callable[..., Any]
    parking_vehicle_lookup_payload: Callable[..., Any]
    parking_vehicle_not_found_field_labels: Callable[..., Any]
    parking_weekly_average_payload: Callable[..., Any]
    parking_weekly_average_period: Callable[..., Any]
    parking_weekly_selected_years: Callable[..., Any]
    parking_weekly_year_comparison_payload: Callable[..., Any]
    parse_day: Callable[..., Any]
    protect_ledger_json: Callable[..., Any]
    record_import_job: Callable[..., Any]
    redirect_keep_query: Callable[..., Any]
    redirect_with_query_params: Callable[..., Any]
    refresh_parking_vehicle_summary: Callable[..., Any]
    require_settings_access: Callable[..., Any]
    require_settings_or_car_info_access: Callable[..., Any]
    run_vehicle_svv_sync: Callable[..., Any]
    save_parking_forecast_after_import: Callable[..., Any]
    templates: Any
    unpaid_registered_vehicle_stays_payload: Callable[..., Any]
    vehicle_blank_area_condition: Callable[..., Any]
    vehicle_blank_name_condition: Callable[..., Any]
    vehicle_car_info_candidate_condition: Callable[..., Any]
    vehicle_car_info_country_condition: Callable[..., Any]
    vehicle_missing_area_condition: Callable[..., Any]
    vehicle_missing_name_condition: Callable[..., Any]


def create_router(dependencies: Dependencies) -> RouterBundle:
    router = APIRouter()

    SVV_SYNC_BATCH_SIZE = dependencies.SVV_SYNC_BATCH_SIZE

    @router.get("/api/cars/parking-control-report")
    async def api_parking_control_report(
        response: Response,
        period: str = Query(default="month", pattern="^(week|month)$"),
        month: Optional[str] = None,
        week: Optional[str] = None,
        gap_minutes: int = Query(default=60, ge=5, le=180),
    ) -> dict[str, Any]:
        normalize_month = dependencies.normalize_month
        protect_ledger_json = dependencies.protect_ledger_json
        unpaid_registered_vehicle_stays_payload = dependencies.unpaid_registered_vehicle_stays_payload
        response.headers["Cache-Control"] = "no-store, max-age=0"
        today = datetime.now(LOCAL_TZ).date()
        current_week_start = today - timedelta(days=today.weekday())
        if period == "week":
            period_start = current_week_start
            if week:
                try:
                    parsed_week = datetime.strptime(f"{week}-1", "%G-W%V-%u").date()
                    if parsed_week.strftime("%G-W%V") == week:
                        period_start = parsed_week
                except (TypeError, ValueError):
                    pass
            period_end = period_start + timedelta(days=7)
            period_value = period_start.strftime("%G-W%V")
            previous_period = (period_start - timedelta(days=7)).strftime("%G-W%V")
            next_period = period_end.strftime("%G-W%V")
            current_period = current_week_start.strftime("%G-W%V")
            period_label_value = (
                f"Uke {period_start.isocalendar().week} · "
                f"{period_start.strftime('%d.%m')}-{(period_end - timedelta(days=1)).strftime('%d.%m.%Y')}"
            )
        else:
            period_start = normalize_month(month, today)
            period_end = add_months(period_start, 1)
            period_value = period_start.strftime("%Y-%m")
            previous_period = add_months(period_start, -1).strftime("%Y-%m")
            next_period = period_end.strftime("%Y-%m")
            current_period = today.strftime("%Y-%m")
            period_label_value = month_label(period_start)
        from_at = datetime.combine(period_start, time.min).replace(tzinfo=LOCAL_TZ)
        to_at = datetime.combine(period_end, time.min).replace(tzinfo=LOCAL_TZ)
        ledger, known_stays, registered_stays = await asyncio.gather(
            protect_ledger_json(
                "known_vehicle_report",
                identity="PARKNORDIC",
                **{
                    "from": from_at.isoformat(),
                    "to": to_at.isoformat(),
                    "gap_minutes": gap_minutes,
                    "timezone": "Europe/Oslo",
                },
            ),
            protect_ledger_json(
                "known_vehicle_stays_report",
                **{
                    "from": from_at.isoformat(),
                    "to": to_at.isoformat(),
                    "min_duration_minutes": 10,
                    "timezone": "Europe/Oslo",
                },
            ),
            protect_ledger_json(
                "registered_vehicle_stays_report",
                **{
                    "from": from_at.isoformat(),
                    "to": to_at.isoformat(),
                    "min_duration_minutes": 10,
                    "timezone": "Europe/Oslo",
                },
            ),
        )
        unpaid_registered_vehicles = await unpaid_registered_vehicle_stays_payload(
            registered_stays,
            period_start,
            period_end,
        )

        def visit_payload(item: Mapping[str, Any]) -> dict[str, Any]:
            return {
                "id": item.get("id"),
                "startAt": item.get("start_at"),
                "endAt": item.get("end_at"),
                "durationMinutes": float_or_zero(item.get("duration_minutes")),
                "observationCount": int_or_zero(item.get("observation_count")),
                "cameraNames": list(item.get("camera_names") or []),
                "isSingleObservation": bool(item.get("is_single_observation")),
                "observations": [
                    {
                        "recognitionId": observation.get("recognition_id"),
                        "occurredAt": observation.get("occurred_at"),
                        "cameraId": observation.get("camera_id"),
                        "cameraName": observation.get("camera_name") or observation.get("camera_id") or "Ukjent kamera",
                    }
                    for observation in item.get("observations") or []
                    if isinstance(observation, Mapping)
                ],
            }

        source_summary = ledger.get("summary") if isinstance(ledger.get("summary"), Mapping) else {}
        source_policy = ledger.get("policy") if isinstance(ledger.get("policy"), Mapping) else {}
        known_summary = known_stays.get("summary") if isinstance(known_stays.get("summary"), Mapping) else {}
        known_policy = known_stays.get("policy") if isinstance(known_stays.get("policy"), Mapping) else {}
        days = []
        for source_day in ledger.get("days") or []:
            if not isinstance(source_day, Mapping):
                continue
            day_value = date.fromisoformat(str(source_day.get("date")))
            days.append(
                {
                    "date": day_value.isoformat(),
                    "label": day_value.strftime("%d.%m"),
                    "weekdayLabel": ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"][day_value.weekday()],
                    "isWeekend": day_value.weekday() >= 5,
                    "visitCount": int_or_zero(source_day.get("visit_count")),
                    "observationCount": int_or_zero(source_day.get("observation_count")),
                    "observedMinutes": float_or_zero(source_day.get("observed_minutes")),
                    "visits": [
                        visit_payload(item)
                        for item in source_day.get("visits") or []
                        if isinstance(item, Mapping)
                    ],
                }
            )
        known_vehicle_days = []
        for source_day in known_stays.get("days") or []:
            if not isinstance(source_day, Mapping):
                continue
            day_value = date.fromisoformat(str(source_day.get("date")))
            vehicles = []
            for source_vehicle in source_day.get("vehicles") or []:
                if not isinstance(source_vehicle, Mapping):
                    continue
                vehicles.append(
                    {
                        "id": source_vehicle.get("id"),
                        "identity": source_vehicle.get("identity"),
                        "displayName": source_vehicle.get("display_name") or source_vehicle.get("identity") or "Kjent kjøretøy",
                        "firstObservedAt": source_vehicle.get("first_observed_at"),
                        "lastObservedAt": source_vehicle.get("last_observed_at"),
                        "durationMinutes": float_or_zero(source_vehicle.get("duration_minutes")),
                        "observationCount": int_or_zero(source_vehicle.get("observation_count")),
                        "cameraNames": list(source_vehicle.get("camera_names") or []),
                    }
                )
            known_vehicle_days.append(
                {
                    "date": day_value.isoformat(),
                    "label": day_value.strftime("%d.%m"),
                    "weekdayLabel": ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"][day_value.weekday()],
                    "isWeekend": day_value.weekday() >= 5,
                    "vehicleCount": len(vehicles),
                    "observationCount": int_or_zero(source_day.get("observation_count")),
                    "vehicles": vehicles,
                }
            )
        return {
            "generatedAt": ledger.get("generated_at"),
            "identity": ledger.get("identity") or "PARKNORDIC",
            "displayName": ledger.get("display_name") or "Park Nordic",
            "periodType": period,
            "periodValue": period_value,
            "periodLabel": period_label_value,
            "previousPeriod": previous_period,
            "nextPeriod": next_period,
            "currentPeriod": current_period,
            "isCurrentPeriod": period_value == current_period,
            "rangeStart": period_start.isoformat(),
            "rangeEnd": (period_end - timedelta(days=1)).isoformat(),
            "month": period_start.strftime("%Y-%m"),
            "monthLabel": month_label(period_start),
            "prevMonth": add_months(period_start.replace(day=1), -1).strftime("%Y-%m"),
            "nextMonth": add_months(period_start.replace(day=1), 1).strftime("%Y-%m"),
            "isCurrentMonth": period_start.replace(day=1) == today.replace(day=1),
            "policy": {
                "gapMinutes": int_or_zero(source_policy.get("gap_minutes")) or gap_minutes,
                "label": source_policy.get("label") or f"Under {gap_minutes} min mellom observasjoner",
                "detail": source_policy.get("detail") or "Varighet er estimert fra kameraobservasjonene.",
            },
            "summary": {
                "visitCount": int_or_zero(source_summary.get("visit_count")),
                "activeDays": int_or_zero(source_summary.get("active_days")),
                "observationCount": int_or_zero(source_summary.get("observation_count")),
                "observedMinutes": float_or_zero(source_summary.get("observed_minutes")),
                "averageVisitMinutes": float_or_zero(source_summary.get("average_visit_minutes")),
                "firstObservedAt": source_summary.get("first_observed_at"),
                "lastObservedAt": source_summary.get("last_observed_at"),
            },
            "days": days,
            "knownVehicles": {
                "policy": {
                    "minDurationMinutes": int_or_zero(known_policy.get("min_duration_minutes")) or 10,
                    "label": known_policy.get("label") or "Mer enn 10 minutter",
                    "detail": known_policy.get("detail") or "Tidsrommet beregnes fra første til siste kameraobservasjon samme dag.",
                },
                "summary": {
                    "vehicleDayCount": int_or_zero(known_summary.get("vehicle_day_count")),
                    "activeDays": int_or_zero(known_summary.get("active_days")),
                    "uniqueVehicleCount": int_or_zero(known_summary.get("unique_vehicle_count")),
                    "observationCount": int_or_zero(known_summary.get("observation_count")),
                    "observedMinutes": float_or_zero(known_summary.get("observed_minutes")),
                },
                "days": known_vehicle_days,
            },
            "unpaidRegisteredVehicles": unpaid_registered_vehicles,
        }

    @router.get("/api/cars/day")
    async def api_cars_day(response: Response, day: Optional[str] = None) -> dict[str, Any]:
        CARS_DAY_CACHE_TTL = dependencies.CARS_DAY_CACHE_TTL
        CARS_HISTORY_CACHE_TTL = dependencies.CARS_HISTORY_CACHE_TTL
        SUMMARY_CACHE = dependencies.SUMMARY_CACHE
        async_session = dependencies.async_session
        parking_timeline_end = dependencies.parking_timeline_end
        parse_day = dependencies.parse_day
        protect_ledger_json = dependencies.protect_ledger_json
        response.headers["Cache-Control"] = "no-store, max-age=0"
        selected_day = parse_day(day)
        today = datetime.now(LOCAL_TZ).date()
        cache_key = f"cars_day:{selected_day.isoformat()}"
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        cached = SUMMARY_CACHE.get(cache_key)
        if cached and cached.get("expires", datetime.min) > now_utc:
            response.headers["X-Data-Cache"] = "hit"
            return deepcopy(cached["value"])
        response.headers["X-Data-Cache"] = "miss"
        day_start = datetime.combine(selected_day, time.min)
        day_end = day_start + timedelta(days=1)
        day_start_aware = day_start.replace(tzinfo=LOCAL_TZ)
        day_end_aware = day_end.replace(tzinfo=LOCAL_TZ)
        ledger = await protect_ledger_json(
            "daily_license_plates",
            **{
                "from": day_start_aware.isoformat(),
                "to": day_end_aware.isoformat(),
                "include_detections": False,
            },
        )
        recognition_items = cars_group_daily_recognitions(list(ledger.get("items") or []))
        plate_values = sorted(
            {
                compact_plate(item.get("plate") or item.get("display_value"))
                for item in recognition_items
                if compact_plate(item.get("plate") or item.get("display_value"))
            }
        )

        parking_by_plate: Dict[str, list[Dict[str, Any]]] = defaultdict(list)
        vehicle_by_plate: Dict[str, Dict[str, Any]] = {}
        if plate_values:
            normalized_session_plate = compact_plate_sql(ParkingSession.car_license_number)
            async with async_session() as session:
                parking_rows = (
                    await session.execute(
                        select(ParkingSession)
                        .where(normalized_session_plate.in_(plate_values))
                        .where(ParkingSession.start_time >= day_start - timedelta(days=7))
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
                ).scalars().all()
                vehicle_rows = (
                    await session.execute(
                        select(ParkingVehicle, ParkingVehicleDetails)
                        .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                        .where(compact_plate_sql(ParkingVehicle.plate).in_(plate_values))
                    )
                ).all()

            timeline_end = min(local_now_naive(), day_end) if selected_day == today else day_end
            for row in parking_rows:
                plate_value = compact_plate(row.car_license_number)
                start_at = normalize_local_naive(row.start_time)
                end_at = parking_timeline_end(row, timeline_end)
                if not start_at or end_at <= day_start or start_at >= day_end:
                    continue
                paid = float_or_zero(row.fee_inc_vat)
                parking_by_plate[plate_value].append(
                    {
                        "id": row.id,
                        "startAt": api_local_iso(start_at),
                        "endAt": api_local_iso(end_at),
                        "durationMinutes": round(float_or_zero(parking_duration_minutes(row, timeline_end)), 1),
                        "amountKr": round(paid, 2),
                        "isPaid": paid > 0,
                        "status": row.status,
                        "source": row.source_system,
                        "area": row.parking_area,
                        "_startAt": start_at,
                        "_endAt": end_at,
                    }
                )
            for vehicle, details in vehicle_rows:
                plate_value = compact_plate(vehicle.plate)
                vehicle_by_plate[plate_value] = {
                    "name": vehicle.navn,
                    "area": vehicle.omrade,
                    "title": parking_vehicle_summary(details, vehicle.car_info_data),
                    "path": f"/parkering/kjoretoy/{quote(vehicle.plate or plate_value, safe='')}",
                }

        items: list[Dict[str, Any]] = []
        for source_item in recognition_items:
            plate_value = compact_plate(source_item.get("plate") or source_item.get("display_value"))
            if not plate_value:
                continue
            detections = []
            detection_datetimes = []
            unifi_scores = []
            raw_detections = source_item.get("detections") or []
            if isinstance(raw_detections, str):
                try:
                    raw_detections = json.loads(raw_detections)
                except (TypeError, ValueError):
                    raw_detections = []
            for detection in raw_detections:
                if not isinstance(detection, dict):
                    continue
                public_detection = cars_public_detection(detection, plate_value)
                unifi_score = public_detection["unifiScore"]
                if unifi_score is not None:
                    unifi_scores.append(unifi_score)
                detections.append(public_detection)

            detection_datetimes = [
                value
                for value in (
                    cars_recognition_local_datetime(raw_value)
                    for raw_value in source_item.get("detection_times") or []
                )
                if value
            ] or [
                value
                for value in (cars_recognition_local_datetime(item.get("occurredAt")) for item in detections)
                if value
            ]

            parking_sessions = parking_by_plate.get(plate_value, [])
            paid_sessions = [parking for parking in parking_sessions if parking["isPaid"]]
            has_paid_session = bool(paid_sessions)
            payment_metrics = cars_daily_payment_metrics(detection_datetimes, paid_sessions)

            def public_parking_row(row: Dict[str, Any]) -> Dict[str, Any]:
                return {key: value for key, value in row.items() if not key.startswith("_")}

            first_detected_at = min(detection_datetimes) if detection_datetimes else cars_recognition_local_datetime(source_item.get("first_detected_at"))
            last_detected_at = max(detection_datetimes) if detection_datetimes else cars_recognition_local_datetime(source_item.get("last_detected_at"))
            average_unifi_score = cars_unifi_score(source_item.get("average_unifi_score"))
            if average_unifi_score is None and unifi_scores:
                average_unifi_score = round(sum(unifi_scores) / len(unifi_scores), 1)
            minimum_unifi_score = cars_unifi_score(source_item.get("minimum_unifi_score"))
            maximum_unifi_score = cars_unifi_score(source_item.get("maximum_unifi_score"))
            registry_validation = source_item.get("validation") if isinstance(source_item.get("validation"), dict) else {
                "status": "pending",
                "is_valid": None,
                "likely_misread": False,
                "message": "Venter på validering i Protect Ledger",
                "sources": {},
            }
            public_registry_validation = {
                key: value
                for key, value in registry_validation.items()
                if key != "sources"
            }
            ledger_variant_candidates = source_item.get("ocr_variant_candidates") or []
            items.append(
                {
                    "plate": plate_value,
                    "displayValue": source_item.get("display_value") or plate_value,
                    "detectionCount": int_or_zero(source_item.get("detection_count")) or len(detections),
                    "firstDetectedAt": api_local_iso(first_detected_at),
                    "lastDetectedAt": api_local_iso(last_detected_at),
                    "knownInProtect": bool(source_item.get("known_in_protect")),
                    "cameraNames": list(source_item.get("camera_names") or []),
                    "detections": [],
                    "averageUnifiScore": average_unifi_score,
                    "minimumUnifiScore": minimum_unifi_score if minimum_unifi_score is not None else (min(unifi_scores) if unifi_scores else None),
                    "maximumUnifiScore": maximum_unifi_score if maximum_unifi_score is not None else (max(unifi_scores) if unifi_scores else None),
                    "scoredDetectionCount": int_or_zero(source_item.get("scored_detection_count")) or len(unifi_scores),
                    "confidenceLevel": cars_confidence_level(average_unifi_score),
                    "matchingReadCount": int_or_zero(source_item.get("detection_count")) or len(detections),
                    "observedPlateValues": list(source_item.get("observed_plate_values") or [plate_value]),
                    "mergedVariantCount": int_or_zero(source_item.get("merged_variant_count")),
                    "ocrWarning": bool(ledger_variant_candidates),
                    "isLikelyOcrVariant": bool(source_item.get("is_likely_ocr_variant")),
                    "likelyCanonicalPlate": source_item.get("likely_canonical_plate") or plate_value,
                    "ocrVariantCandidates": [
                        {
                            "plate": candidate.get("plate"),
                            "editDistance": candidate.get("edit_distance"),
                            "detectionCount": candidate.get("detection_count"),
                        }
                        for candidate in ledger_variant_candidates
                        if isinstance(candidate, dict)
                    ],
                    "registryValidation": public_registry_validation,
                    "likelyMisread": bool(source_item.get("likely_misread")),
                    "presentationStatus": source_item.get("presentation_status") or "pending_review",
                    "requiresReview": bool(source_item.get("requires_review")),
                    "vehicle": vehicle_by_plate.get(plate_value),
                    "hasParkingSession": bool(parking_sessions),
                    "hasPaidSession": has_paid_session,
                    "paidSessionCount": len(paid_sessions),
                    "paidTotalKr": round(sum(float_or_zero(parking["amountKr"]) for parking in paid_sessions), 2),
                    **payment_metrics,
                    "parkingSessions": [public_parking_row(parking) for parking in parking_sessions],
                    "paidSessions": [public_parking_row(parking) for parking in paid_sessions],
                }
            )

        items.sort(key=lambda item: (item.get("lastDetectedAt") or "", item["plate"]), reverse=True)
        covered_count = sum(1 for item in items if item["coveredDetectionCount"] > 0)
        paid_count = sum(1 for item in items if item["hasPaidSession"])
        observation_datetimes = [
            value
            for item in items
            for value in (
                cars_recognition_local_datetime(item.get("firstDetectedAt")),
                cars_recognition_local_datetime(item.get("lastDetectedAt")),
            )
        ]
        observation_datetimes = [value for value in observation_datetimes if value]
        observation_start_at = min(observation_datetimes) if observation_datetimes else None
        observation_end_at = max(observation_datetimes) if observation_datetimes else None
        value = {
            "generatedAt": api_local_iso(local_now_naive()),
            "selectedDay": selected_day.isoformat(),
            "selectedDayLabel": selected_day.strftime("%d.%m.%Y"),
            "prevDay": (selected_day - timedelta(days=1)).isoformat(),
            "nextDay": (selected_day + timedelta(days=1)).isoformat(),
            "isToday": selected_day == today,
            "matchPolicy": {
                "mode": "same_calendar_day",
                "label": "Samme bil og samme dag",
                "detail": "Betaling matches mot bilen for hele kalenderdagen, uavhengig av hvor lenge sjåføren ventet før betaling.",
            },
            "observationWindow": {
                "firstDetectedAt": api_local_iso(observation_start_at),
                "lastDetectedAt": api_local_iso(observation_end_at),
                "spanMinutes": round((observation_end_at - observation_start_at).total_seconds() / 60, 1)
                if observation_start_at and observation_end_at
                else 0,
            },
            "summary": {
                "uniquePlates": len(items),
                "detections": sum(int_or_zero(item["detectionCount"]) for item in items),
                "paidPlates": paid_count,
                "coveredPlates": covered_count,
                "withoutPayment": len(items) - paid_count,
                "mergedOcrVariants": sum(int_or_zero(item.get("mergedVariantCount")) for item in items),
                "scoredDetections": sum(int_or_zero(item["scoredDetectionCount"]) for item in items),
                "lowConfidencePlates": sum(1 for item in items if item["confidenceLevel"] in {"low", "unscored"}),
                "ocrWarningPlates": sum(1 for item in items if item["ocrWarning"]),
                "reviewPlates": sum(1 for item in items if item["requiresReview"]),
                "validatedPlates": sum(1 for item in items if item["registryValidation"].get("is_valid") is True),
                "likelyMisreads": sum(1 for item in items if item["likelyMisread"]),
                "pendingValidation": sum(1 for item in items if item["registryValidation"].get("is_valid") is None),
            },
            "items": items,
        }
        cache_ttl = CARS_DAY_CACHE_TTL if selected_day == today else CARS_HISTORY_CACHE_TTL
        SUMMARY_CACHE[cache_key] = {"expires": now_utc + cache_ttl, "value": deepcopy(value)}
        return value

    @router.get("/api/cars/day/{plate}/detections")
    async def api_cars_day_detections(plate: str, day: Optional[str] = None) -> dict[str, Any]:
        CARS_DAY_CACHE_TTL = dependencies.CARS_DAY_CACHE_TTL
        CARS_HISTORY_CACHE_TTL = dependencies.CARS_HISTORY_CACHE_TTL
        SUMMARY_CACHE = dependencies.SUMMARY_CACHE
        parse_day = dependencies.parse_day
        protect_ledger_json = dependencies.protect_ledger_json
        selected_day = parse_day(day)
        plate_value = compact_plate(plate)
        if not plate_value:
            raise HTTPException(status_code=400, detail="Registreringsnummer mangler")
        today = datetime.now(LOCAL_TZ).date()
        cache_key = f"cars_day_detections:{selected_day.isoformat()}:{plate_value}"
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        cached = SUMMARY_CACHE.get(cache_key)
        if cached and cached.get("expires", datetime.min) > now_utc:
            return deepcopy(cached["value"])

        day_start = datetime.combine(selected_day, time.min).replace(tzinfo=LOCAL_TZ)
        day_end = (datetime.combine(selected_day, time.min) + timedelta(days=1)).replace(tzinfo=LOCAL_TZ)
        ledger = await protect_ledger_json(
            "daily_license_plates",
            **{
                "from": day_start.isoformat(),
                "to": day_end.isoformat(),
                "include_detections": True,
                "plate": plate_value,
            },
        )
        grouped = cars_group_daily_recognitions(list(ledger.get("items") or []))
        source_item = next(
            (
                item
                for item in grouped
                if compact_plate(item.get("plate") or item.get("display_value")) == plate_value
            ),
            None,
        )
        raw_detections = list((source_item or {}).get("detections") or [])
        detections = [
            cars_public_detection(detection, plate_value)
            for detection in raw_detections
            if isinstance(detection, Mapping)
        ]
        value = {
            "plate": plate_value,
            "selectedDay": selected_day.isoformat(),
            "detectionCount": int_or_zero((source_item or {}).get("detection_count")) or len(detections),
            "detections": detections,
        }
        cache_ttl = CARS_DAY_CACHE_TTL if selected_day == today else CARS_HISTORY_CACHE_TTL
        SUMMARY_CACHE[cache_key] = {"expires": now_utc + cache_ttl, "value": deepcopy(value)}
        return value

    @router.get("/api/parkering/year-comparison")
    async def api_v2_parking_year_comparison(year: Optional[str] = Query(None)):
        async_session = dependencies.async_session
        get_parking_summaries = dependencies.get_parking_summaries
        now_dt = local_now_naive()
        anchor_year = parse_anchor_year(year, now_dt.year)
        async with async_session() as session:
            summaries = await get_parking_summaries(session)
        return build_parking_year_comparison(summaries, now_dt, anchor_year)

    @router.get("/api/parkering/time-distribution")
    async def api_v2_parking_time_distribution(request: Request):
        api_parking_time_distribution = dependencies.api_parking_time_distribution
        async_session = dependencies.async_session
        now_dt = local_now_naive()
        async with async_session() as session:
            return await api_parking_time_distribution(session, request.query_params, now_dt)

    @router.get("/api/parkering/weekly-averages")
    async def api_v2_parking_weekly_averages(request: Request):
        async_session = dependencies.async_session
        parking_weekly_average_payload = dependencies.parking_weekly_average_payload
        parking_weekly_average_period = dependencies.parking_weekly_average_period
        now_dt = local_now_naive()
        period = parking_weekly_average_period(request.query_params, now_dt.date())
        async with async_session() as session:
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
        return parking_weekly_average_payload(rows, period, now_dt)

    @router.get("/api/parkering/weekly-averages/years")
    async def api_v2_parking_weekly_average_years(years: Optional[str] = Query(None)):
        async_session = dependencies.async_session
        parking_weekly_selected_years = dependencies.parking_weekly_selected_years
        parking_weekly_year_comparison_payload = dependencies.parking_weekly_year_comparison_payload
        now_dt = local_now_naive()
        calendar_year_expr = cast(func.extract("year", ParkingSession.start_time), Integer)
        comparison_week_expr = cast(
            func.floor((func.extract("doy", ParkingSession.start_time) - 1) / 7) + 1,
            Integer,
        )
        duration_expr = case(
            (ParkingSession.parking_time_min > 0, ParkingSession.parking_time_min),
            (
                and_(
                    ParkingSession.end_time.is_not(None),
                    ParkingSession.end_time > ParkingSession.start_time,
                ),
                func.extract("epoch", ParkingSession.end_time - ParkingSession.start_time) / 60.0,
            ),
            else_=None,
        )

        async with async_session() as session:
            available_rows = (
                await session.execute(
                    select(calendar_year_expr)
                    .where(ParkingSession.start_time.is_not(None))
                    .distinct()
                    .order_by(calendar_year_expr.desc())
                )
            ).scalars().all()
            available_years = sorted({int_or_zero(value) for value in available_rows if int_or_zero(value) > 0}, reverse=True)
            selected_years = parking_weekly_selected_years(years, available_years, now_dt.year)

            aggregate_rows = []
            if selected_years:
                aggregate_rows = (
                    await session.execute(
                        select(
                            calendar_year_expr.label("calendar_year"),
                            comparison_week_expr.label("comparison_week"),
                            func.count(ParkingSession.id).label("sessions"),
                            func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                            func.coalesce(func.sum(duration_expr), 0).label("minutes"),
                            func.count(duration_expr).label("duration_sessions"),
                        )
                        .where(calendar_year_expr.in_(selected_years))
                        .group_by(calendar_year_expr, comparison_week_expr)
                        .order_by(calendar_year_expr.desc(), comparison_week_expr.asc())
                    )
                ).all()

        return parking_weekly_year_comparison_payload(
            aggregate_rows,
            available_years,
            selected_years,
            now_dt,
        )

    @router.get("/api/parking/vehicles/{plate}")
    async def api_v2_parking_vehicle_detail(plate: str):
        api_detail_field = dependencies.api_detail_field
        async_session = dependencies.async_session
        parking_row_api = dependencies.parking_row_api
        parking_vehicle_not_found_field_labels = dependencies.parking_vehicle_not_found_field_labels
        plate_value = normalize_plate(plate)
        if not plate_value:
            raise HTTPException(status_code=404, detail="Mangler registreringsnummer")

        normalized_session_plate = func.upper(func.replace(ParkingSession.car_license_number, " ", ""))
        async with async_session() as session:
            result = (
                await session.execute(
                    select(ParkingVehicle, ParkingVehicleDetails)
                    .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                    .where(ParkingVehicle.plate == plate_value)
                )
            ).first()
            if not result:
                raise HTTPException(status_code=404, detail="Kjøretøy ikke funnet")
            vehicle, details = result
            stats = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0),
                        func.coalesce(func.sum(ParkingSession.parking_time_min), 0),
                        func.min(ParkingSession.start_time),
                        func.max(ParkingSession.start_time),
                    ).where(normalized_session_plate == plate_value)
                )
            ).first()
            session_rows = (
                await session.execute(
                    select(ParkingSession)
                    .where(normalized_session_plate == plate_value)
                    .order_by(ParkingSession.start_time.desc())
                )
            ).scalars().all()

        ownership_at = svv_current_ownership_at(vehicle.svv_data)
        first_seen = stats[3] if stats else None
        last_seen = stats[4] if stats else None
        ownership_warning = parking_current_ownership_warning(vehicle, first_seen)
        fields = [
            api_detail_field("Eier/navn", vehicle.navn),
            api_detail_field("Område", vehicle.omrade),
            api_detail_field("SUN2-ID", vehicle.sun2_id),
            api_detail_field("Sist eierskifte", ownership_at),
            api_detail_field("Kjøretøy", parking_vehicle_display_label(details, vehicle.car_info_data), parking_vehicle_display_source(details, vehicle.car_info_data)),
            api_detail_field("Årsmodell", parking_vehicle_display_year(details, vehicle.car_info_data)),
            api_detail_field("Farge", parking_vehicle_display_color(details, vehicle.car_info_data)),
            api_detail_field("Kjøretøyklasse", parking_vehicle_display_class(details, vehicle.car_info_data)),
            api_detail_field("Registreringsstatus", parking_vehicle_display_registration_status(details, vehicle.car_info_data)),
            api_detail_field("Førstegangsregistrert Norge", details.forstegangsregistrert_norge if details else None),
            api_detail_field("PKK/kontrollfrist", parking_vehicle_display_inspection_deadline(details, vehicle.car_info_data)),
            api_detail_field("SVV hentet", vehicle.svv_fetched_at),
            api_detail_field("Notat", vehicle.notat),
        ]
        if vehicle.car_info_fetched_at or vehicle.car_info_data or vehicle.car_info_status:
            provider_label = car_info_provider_label(vehicle.car_info_data)
            area_label = car_info_area_label(vehicle.car_info_data)
            fields.extend(
                [
                    api_detail_field("Utenlandsk kilde status", car_info_status_label(vehicle.car_info_status, vehicle.car_info_data), provider_label),
                    api_detail_field("Utenlandsk kilde hentet", vehicle.car_info_fetched_at),
                    api_detail_field("Bekreftet land", area_label if car_info_confirmed_foreign(vehicle.car_info_data) else "Nei"),
                    api_detail_field("Først registrert", car_info_field_value(vehicle.car_info_data, "first_registered", "first_registration")),
                    api_detail_field("Siste eierbytte", car_info_field_value(vehicle.car_info_data, "latest_owner_change")),
                    api_detail_field("Biltype", car_info_field_value(vehicle.car_info_data, "vehicle_type", "body_type", "class")),
                    api_detail_field("Drivstoff/motor", car_info_field_value(vehicle.car_info_data, "fuel", "engine")),
                    api_detail_field("Girkasse", car_info_field_value(vehicle.car_info_data, "transmission")),
                    api_detail_field("Drivlinje", car_info_field_value(vehicle.car_info_data, "drivetrain")),
                    api_detail_field("Effekt", car_info_field_value(vehicle.car_info_data, "power")),
                    api_detail_field("Klassifisering", car_info_field_value(vehicle.car_info_data, "classification")),
                    api_detail_field("Generasjon", car_info_field_value(vehicle.car_info_data, "generation")),
                    api_detail_field("Kilometerstand", car_info_field_value(vehicle.car_info_data, "mileage")),
                    api_detail_field("Kontrollfrist", car_info_field_value(vehicle.car_info_data, "inspection_valid_to", "next_inspection")),
                    api_detail_field("Forbruk blandet", car_info_field_value(vehicle.car_info_data, "fuel_consumption_combined")),
                    api_detail_field("CO2 blandet", car_info_field_value(vehicle.car_info_data, "co2_combined")),
                    api_detail_field("Seter", car_info_field_value(vehicle.car_info_data, "seats")),
                    api_detail_field("Kilde URL", vehicle.car_info_url),
                ]
            )
        not_found_fields = parking_vehicle_not_found_field_labels(vehicle)
        actions = []
        if not_found_fields:
            actions.append(
                {
                    "key": "clear-not-found",
                    "label": "Fjern 'ikke funnet'",
                    "method": "POST",
                    "path": f"/api/parking/vehicles/{quote(plate_value, safe='')}/clear-not-found",
                    "confirm": f"Nullstille {', '.join(not_found_fields)} for {plate_value}? Feltet blir blankt og kan behandles på nytt.",
                    "tone": "primary",
                }
            )
        return {
            "plate": plate_value,
            "title": parking_vehicle_display_label(details, vehicle.car_info_data),
            "subtitle": "Kjøretøy, eierfelt og komplett parkeringshistorikk.",
            "cards": [
                api_card("Parkeringer", stats[0] if stats else 0, "stk", "Alle registrerte", "parking"),
                api_card("Beløp", format_short_number(stats[1] if stats else 0), "kr", "Totalt EasyPark-beløp", "revenue"),
                api_card("Tid", format_short_number((stats[2] or 0) / 60 if stats else 0, 1), "t", "Registrert parkeringstid", "status"),
                api_card("Sist eierskifte", ownership_at.strftime("%d.%m.%Y") if ownership_at else "-", "", "Fra SVV-rådata", "status"),
            ],
            "fields": fields,
            "warnings": [ownership_warning["text"]] if ownership_warning else [],
            "sessions": [parking_row_api(row, vehicle) for row in session_rows],
            "actions": actions,
        }

    @router.post("/api/actions/parkering/fetch-settlements")
    async def api_v2_fetch_parking_settlements(
        request: Request,
        since_days: int = Query(370, ge=1, le=2000),
        limit: int = Query(80, ge=1, le=500),
    ):
        async_session = dependencies.async_session
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        async with async_session() as session:
            try:
                result = await fetch_parking_settlements_from_gmail(session, since_days=since_days, limit=limit)
            except RuntimeError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except imaplib.IMAP4.error as exc:
                raise HTTPException(status_code=502, detail=f"Gmail IMAP feilet: {exc}") from exc
            await session.commit()
        return {
            "status": "ok",
            "message": f"Importerte {result['imported']} nye parkeringsoppgjør. {result['skipped']} ble hoppet over.",
            "result": result,
        }

    @router.post("/api/actions/parkering/save-forecast")
    async def api_v2_parking_save_forecast(request: Request):
        async_session = dependencies.async_session
        build_parking_forecast = dependencies.build_parking_forecast
        clear_summary_cache = dependencies.clear_summary_cache
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        now_local = datetime.now(LOCAL_TZ)
        today_value = now_local.date()
        async with async_session() as session:
            forecast = await build_parking_forecast(session, today_value, now_local)
            await save_forecast_snapshots(session, "parking", forecast, getattr(request.state, "access_key_name", None))
            await session.commit()
        clear_summary_cache("parking")
        return {"status": "ok", "message": "Parkeringsprognose lagret."}

    @router.post("/api/actions/parkering/refresh")
    async def api_v2_parking_refresh(request: Request):
        async_session = dependencies.async_session
        easypark_downloader_request = dependencies.easypark_downloader_request
        easypark_recent_period = dependencies.easypark_recent_period
        logger = dependencies.logger
        record_import_job = dependencies.record_import_job
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        from_day, to_day = easypark_recent_period()
        started_at = local_now_naive()
        try:
            result = await asyncio.to_thread(
                easypark_downloader_request,
                "/queue-sync-period",
                {"from_date": from_day.isoformat(), "to_date": to_day.isoformat()},
                10,
            )
            status = result.get("status")
            if status == "busy":
                message = "EasyPark-downloader kjører allerede."
            elif status == "error":
                raise RuntimeError(str(result.get("detail") or result.get("last_error") or "EasyPark-import feilet"))
            else:
                message = "EasyPark-oppdatering er startet. Datakilden oppdateres når importen er ferdig."
            return {"status": "ok", "message": message, "result": result}
        except Exception as exc:
            logger.exception("EasyPark-import feilet for periode %s til %s", from_day.isoformat(), to_day.isoformat())
            async with async_session() as session:
                await record_import_job(
                    session,
                    "easypark_parking_import",
                    ok=False,
                    source="EasyPark downloader",
                    started_at=started_at,
                    records_imported=0,
                    records_total=0,
                    message=str(exc),
                    raw={"period": {"from": from_day.isoformat(), "to": to_day.isoformat()}},
                )
                await session.commit()
            return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)

    @router.post("/api/actions/parkering/svv-sync")
    async def api_v2_parking_svv_sync(request: Request, limit: int = Query(SVV_SYNC_BATCH_SIZE, ge=1, le=500)):
        require_settings_access = dependencies.require_settings_access
        run_vehicle_svv_sync = dependencies.run_vehicle_svv_sync
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        result = await run_vehicle_svv_sync(limit, "V2")
        return {"status": "ok", "message": "SVV-sync er kjørt.", "result": result}

    @router.post("/api/actions/parkering/car-info-sync")
    async def api_v2_parking_car_info_sync(request: Request, limit: int = Query(1, ge=1, le=5)):
        car_info_lookup_request = dependencies.car_info_lookup_request
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        try:
            result = await asyncio.to_thread(car_info_lookup_request, "/api/run-once", {"limit": limit})
        except Exception as exc:
            return JSONResponse({"status": "error", "message": str(exc)}, status_code=502)
        return {"status": "ok", "message": "Nordisk biloppslag er startet/kjort.", "result": result}

    @router.post("/api/actions/parkering/clear-area-not-found")
    async def api_v2_parking_clear_area_not_found(request: Request):
        async_session = dependencies.async_session
        clear_parking_vehicle_not_found_area = dependencies.clear_parking_vehicle_not_found_area
        clear_summary_cache = dependencies.clear_summary_cache
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        async with async_session() as session:
            cleared = await clear_parking_vehicle_not_found_area(session)
            await session.commit()
        clear_summary_cache("parking")
        return {
            "status": "ok",
            "message": f"{cleared} kjøretøy fikk fjernet område 'ikke funnet'.",
            "cleared": cleared,
        }

    @router.post("/api/parking/vehicles/{plate}/clear-not-found")
    async def api_v2_parking_vehicle_clear_not_found(request: Request, plate: str):
        async_session = dependencies.async_session
        clear_parking_vehicle_not_found_fields = dependencies.clear_parking_vehicle_not_found_fields
        clear_summary_cache = dependencies.clear_summary_cache
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        plate_value = normalize_plate(plate)
        if not plate_value:
            raise HTTPException(status_code=400, detail="Mangler registreringsnummer")
        async with async_session() as session:
            cleared_fields = await clear_parking_vehicle_not_found_fields(session, plate_value)
            if cleared_fields is None:
                raise HTTPException(status_code=404, detail="Kjøretøy ikke funnet")
            await session.commit()
        clear_summary_cache("parking")
        if not cleared_fields:
            return {"status": "ok", "message": f"{plate_value} hadde ingen felt satt til 'ikke funnet'.", "cleared": []}
        return {
            "status": "ok",
            "message": f"{plate_value}: fjernet 'ikke funnet' fra {', '.join(cleared_fields)}.",
            "cleared": cleared_fields,
        }

    @router.get("/parkering")
    async def parking_redirect(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/parkering/oversikt", status_code=307)

    @router.post("/api/parkering/import-csv")
    async def parking_easypark_import_csv(request: Request):
        SVV_API_KEY = dependencies.SVV_API_KEY
        SVV_IMPORT_SYNC_BATCH_SIZE = dependencies.SVV_IMPORT_SYNC_BATCH_SIZE
        SVV_SYNC_ENABLED = dependencies.SVV_SYNC_ENABLED
        async_session = dependencies.async_session
        clear_summary_cache = dependencies.clear_summary_cache
        import_counts_for_json = dependencies.import_counts_for_json
        ingest_easypark_csv = dependencies.ingest_easypark_csv
        record_import_job = dependencies.record_import_job
        refresh_parking_vehicle_summary = dependencies.refresh_parking_vehicle_summary
        run_vehicle_svv_sync = dependencies.run_vehicle_svv_sync
        save_parking_forecast_after_import = dependencies.save_parking_forecast_after_import
        started_at = local_now_naive()
        filename = "easypark.csv"
        try:
            form = await request.form()
            upload = form.get("file")
            if not upload or not hasattr(upload, "read"):
                raise ValueError("Velg en CSV-fil fra EasyPark.")
            filename = getattr(upload, "filename", None) or filename
            content = await upload.read()
            if not content:
                raise ValueError("Filen er tom.")
            async with async_session() as session:
                counts = await ingest_easypark_csv(session, content, filename)
                vehicle_count = await refresh_parking_vehicle_summary(session)
                forecast_raw: Dict[str, Any] = {"saved": False}
                try:
                    forecast_raw = {"saved": True, **await save_parking_forecast_after_import(session)}
                except Exception as forecast_exc:
                    forecast_raw = {"saved": False, "error": str(forecast_exc)}
                message = (
                    f"{counts['inserted']} nye, {counts['updated']} oppdatert, {counts['unchanged']} uendret, "
                    f"{counts['skipped']} hoppet over fra {filename}"
                )
                if forecast_raw.get("saved"):
                    message += ", prognose lagret"
                await record_import_job(
                    session,
                    "easypark_parking_import",
                    ok=True,
                    source="EasyPark CSV",
                    started_at=started_at,
                    records_imported=counts["inserted"] + counts["updated"],
                    records_total=counts["total"],
                    message=message,
                    raw={
                        "filename": filename,
                        "counts": import_counts_for_json(counts),
                        "vehicles_refreshed": vehicle_count,
                        "forecast": forecast_raw,
                    },
                )
                await session.commit()
            clear_summary_cache("parking")
            if SVV_IMPORT_SYNC_BATCH_SIZE and SVV_API_KEY and SVV_SYNC_ENABLED:
                asyncio.create_task(run_vehicle_svv_sync(SVV_IMPORT_SYNC_BATCH_SIZE, "EasyPark import"))
            return {"status": "ok", **counts, "vehicles_refreshed": vehicle_count, "forecast": forecast_raw}
        except Exception as exc:
            async with async_session() as session:
                await record_import_job(
                    session,
                    "easypark_parking_import",
                    ok=False,
                    source="EasyPark CSV",
                    started_at=started_at,
                    records_imported=0,
                    records_total=0,
                    message=str(exc),
                    raw={"filename": filename},
                )
                await session.commit()
            return JSONResponse({"status": "error", "detail": str(exc)}, status_code=400)

    @router.post("/api/parkering/svv-sync")
    async def parking_vehicle_svv_sync_api(request: Request, limit: int = Query(SVV_SYNC_BATCH_SIZE, ge=1, le=500)):
        require_settings_access = dependencies.require_settings_access
        run_vehicle_svv_sync = dependencies.run_vehicle_svv_sync
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        result = await run_vehicle_svv_sync(limit, "Manuell")
        return result

    @router.post("/parkering/refresh")
    async def parking_refresh(request: Request):
        async_session = dependencies.async_session
        easypark_downloader_request = dependencies.easypark_downloader_request
        easypark_recent_period = dependencies.easypark_recent_period
        record_import_job = dependencies.record_import_job
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        from_day, to_day = easypark_recent_period()
        started_at = local_now_naive()
        try:
            result = await asyncio.to_thread(
                easypark_downloader_request,
                "/queue-sync-period",
                {"from_date": from_day.isoformat(), "to_date": to_day.isoformat()},
                10,
            )
            status = result.get("status")
            if status == "busy":
                outcome = "busy"
            elif status == "error":
                raise RuntimeError(str(result.get("detail") or result.get("last_error") or "EasyPark-import feilet"))
            else:
                outcome = "ok"
        except Exception as exc:
            async with async_session() as session:
                await record_import_job(
                    session,
                    "easypark_parking_import",
                    ok=False,
                    source="EasyPark downloader",
                    started_at=started_at,
                    records_imported=0,
                    records_total=0,
                    message=str(exc),
                    raw={"period": {"from": from_day.isoformat(), "to": to_day.isoformat()}},
                )
                await session.commit()
            outcome = "error"
        day = request.query_params.get("day")
        suffix = f"?day={quote(day)}&refresh={outcome}" if day else f"?refresh={outcome}"
        return RedirectResponse(f"/parkering/oversikt{suffix}", status_code=303)

    @router.get("/parkering/oversikt", response_class=HTMLResponse)
    async def parking_overview_view(
        request: Request,
        refresh: Optional[str] = None,
        day: Optional[date] = Query(None),
    ):
        async_session = dependencies.async_session
        easypark_recent_period = dependencies.easypark_recent_period
        import_job_definition = dependencies.import_job_definition
        import_job_status_from_age = dependencies.import_job_status_from_age
        parking_period_summary = dependencies.parking_period_summary
        templates = dependencies.templates
        now = local_now_naive()
        today = now.date()
        selected_day = day or today
        selected_start = datetime.combine(selected_day, time.min)
        selected_end = selected_start + timedelta(days=1)
        today_start = datetime.combine(today, time.min)
        tomorrow_start = today_start + timedelta(days=1)
        yesterday_start = today_start - timedelta(days=1)
        month_start = today.replace(day=1)
        month_start_dt = datetime.combine(month_start, time.min)
        previous_month_end = month_start_dt
        previous_month_start = datetime.combine((month_start - timedelta(days=1)).replace(day=1), time.min)
        week_start = today_start - timedelta(days=today.weekday())
        previous_week_start = week_start - timedelta(days=7)
        normalized_session_plate = func.upper(func.replace(ParkingSession.car_license_number, " ", ""))
        async with async_session() as session:
            period_cards = [
                await parking_period_summary(session, "I dag", today_start, tomorrow_start),
                await parking_period_summary(session, "I går", yesterday_start, today_start),
                await parking_period_summary(session, "Denne uken", week_start, tomorrow_start),
                await parking_period_summary(session, "Forrige uke", previous_week_start, week_start),
                await parking_period_summary(session, "Denne måneden", month_start_dt, tomorrow_start),
                await parking_period_summary(session, "Forrige måned", previous_month_start, previous_month_end),
            ]
            today_rows = (
                await session.execute(
                    select(ParkingSession, ParkingVehicle, ParkingVehicleDetails)
                    .outerjoin(ParkingVehicle, ParkingVehicle.plate == normalized_session_plate)
                    .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == normalized_session_plate)
                    .where(
                        ParkingSession.start_time < selected_end,
                        or_(
                            ParkingSession.end_time.is_(None),
                            ParkingSession.end_time >= selected_start,
                            func.lower(func.coalesce(ParkingSession.status, "")) == "ongoing",
                        ),
                    )
                    .order_by(ParkingSession.start_time.desc())
                )
            ).all()
            ongoing_today = [
                parking_row_context(row, vehicle, details, now, selected_day)
                for row, vehicle, details in today_rows
                if (row.status or "").strip().lower() == "ongoing"
            ]
            completed_today = [
                parking_row_context(row, vehicle, details, now, selected_day)
                for row, vehicle, details in today_rows
                if (row.status or "").strip().lower() != "ongoing"
            ]
            last_parking_at = (
                await session.execute(
                    select(func.max(ParkingSession.imported_at))
                )
            ).scalar_one()
            easypark_row = (
                await session.execute(
                    select(ImportJobStatus).where(ImportJobStatus.job_name == "easypark_parking_import")
                )
            ).scalars().first()
            easypark_status = None
            if easypark_row:
                definition = import_job_definition("easypark_parking_import")
                if easypark_row.status == "running":
                    status, status_text = "running", "Kjører"
                else:
                    status, status_text = import_job_status_from_age(
                        easypark_row.last_success_at,
                        definition.get("expected_interval_minutes"),
                        definition.get("warning_after_minutes"),
                    )
                easypark_status = {
                    "status": status,
                    "status_text": status_text,
                    "last_success_at": easypark_row.last_success_at,
                    "records_total": easypark_row.records_total,
                    "message": easypark_row.message,
                }
        refresh_messages = {
            "ok": {"level": "good", "text": "EasyPark er hentet for i går og i dag."},
            "busy": {"level": "warn", "text": "EasyPark-importen kjører allerede. Prøv igjen litt senere."},
            "error": {"level": "bad", "text": "EasyPark-importen feilet. Se datakilder for detaljer."},
        }
        refresh_from, refresh_to = easypark_recent_period()
        return templates.TemplateResponse(
            request,
            "parking_overview.html",
            {
                "today": today,
                "selected_day": selected_day,
                "previous_day": selected_day - timedelta(days=1),
                "next_day": selected_day + timedelta(days=1),
                "period_cards": period_cards,
                "ongoing_today": ongoing_today,
                "completed_today": completed_today,
                "last_parking_at": last_parking_at,
                "easypark_status": easypark_status,
                "refresh_period": {"from_day": refresh_from, "to_day": refresh_to},
                "refresh_message": refresh_messages.get(refresh or ""),
                "can_settings": getattr(request.state, "auth_can_settings", False),
            },
        )

    @router.get("/parkering/statistikk", response_class=HTMLResponse)
    async def parking_statistics_view(request: Request):
        async_session = dependencies.async_session
        get_parking_summaries = dependencies.get_parking_summaries
        templates = dependencies.templates
        async with async_session() as session:
            summaries = await get_parking_summaries(session)
        return templates.TemplateResponse(
            request,
            "parking_statistics.html",
            {
                "top_days": summaries["top_days"],
                "top_months": summaries["top_months"],
                "top_days_by_count": summaries["top_days_by_count"],
                "top_months_by_count": summaries["top_months_by_count"],
                "weekly_chart": summaries["weekly_chart"],
                "grand_total": summaries["total"],
                "first_date": summaries["first_date"],
                "last_date": summaries["last_date"],
            },
        )

    @router.get("/parkering/prognose", response_class=HTMLResponse)
    async def parking_forecast_view(request: Request):
        async_session = dependencies.async_session
        build_parking_forecast = dependencies.build_parking_forecast
        templates = dependencies.templates
        now_local = datetime.now(LOCAL_TZ)
        today = now_local.date()
        async with async_session() as session:
            forecast = await build_parking_forecast(session, today, now_local)
            saved_forecasts = await saved_forecast_table(session, "parking")
        response = templates.TemplateResponse(
            request,
            "parking_forecast.html",
            {
                "forecast": forecast,
                "day": forecast["day"],
                "month": forecast["month"],
                "year": forecast["year"],
                "saved_forecasts": saved_forecasts,
                "saved": request.query_params.get("saved") == "1",
            },
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @router.post("/parkering/prognose/lagre")
    async def parking_forecast_save(request: Request):
        async_session = dependencies.async_session
        build_parking_forecast = dependencies.build_parking_forecast
        now_local = datetime.now(LOCAL_TZ)
        today = now_local.date()
        async with async_session() as session:
            forecast = await build_parking_forecast(session, today, now_local)
            await save_forecast_snapshots(session, "parking", forecast, getattr(request.state, "access_key_name", None))
            await session.commit()
        return RedirectResponse("/parkering/prognose?saved=1", status_code=303)

    @router.get("/parkering/bilstatistikk", response_class=HTMLResponse)
    async def parking_vehicle_statistics_view(request: Request):
        async_session = dependencies.async_session
        templates = dependencies.templates
        async with async_session() as session:
            top_plates = (
                await session.execute(
                    select(
                        ParkingVehicle.plate,
                        ParkingVehicle.parkering_count,
                        ParkingVehicle.paid_total,
                        ParkingVehicleDetails.merke,
                        ParkingVehicleDetails.modell,
                        ParkingVehicleDetails.kjoretoyklasse_navn,
                        ParkingVehicle.navn,
                        ParkingVehicle.omrade,
                    )
                    .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                    .order_by(ParkingVehicle.parkering_count.desc().nullslast(), ParkingVehicle.paid_total.desc().nullslast())
                    .limit(50)
                )
            ).all()
            make_expr = func.coalesce(ParkingVehicleDetails.merke, "Ukjent")
            top_makes = (
                await session.execute(
                    select(
                        make_expr,
                        func.count(ParkingVehicleDetails.plate),
                    )
                    .group_by(make_expr)
                    .order_by(func.count(ParkingVehicleDetails.plate).desc())
                    .limit(50)
                )
            ).all()
            vehicle_total = (
                await session.execute(select(func.count(func.distinct(ParkingVehicle.plate))))
            ).scalar_one()
            vehicle_with_details = (
                await session.execute(select(func.count(func.distinct(ParkingVehicleDetails.plate))))
            ).scalar_one()
        return templates.TemplateResponse(
            request,
            "parking_vehicle_statistics.html",
            {
                "top_plates": top_plates,
                "top_makes": top_makes,
                "vehicle_total": vehicle_total,
                "vehicle_with_details": vehicle_with_details,
            },
        )

    @router.get("/parkering/omrade", response_class=HTMLResponse)
    async def parking_area_overview_view(request: Request, date_from: Optional[str] = None, date_to: Optional[str] = None):
        async_session = dependencies.async_session
        parking_area_overview_data = dependencies.parking_area_overview_data
        templates = dependencies.templates
        async with async_session() as session:
            area_context = await parking_area_overview_data(session, date_from or "", date_to or "")
        period = area_context["period"]
        return templates.TemplateResponse(
            request,
            "parking_areas.html",
            {
                "rows": area_context["rows"],
                "vehicle_total": area_context["vehicle_total"],
                "vehicle_with_area": area_context["vehicle_with_area"],
                "missing_area": area_context["missing_area"],
                "parking_with_area": area_context["parking_with_area"],
                "parking_total": area_context["parking_total"],
                "paid_total": area_context["paid_total"],
                "coverage_percent": area_context["coverage_percent"],
                "period": period,
                "filters": {"date_from": period["date_from"], "date_to": period["date_to"]},
            },
        )

    @router.get("/parkering/parkeringer", response_class=HTMLResponse)
    async def parking_sessions_view(
        request: Request,
        plate: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = Query(100, ge=1, le=500),
    ):
        async_session = dependencies.async_session
        parse_day = dependencies.parse_day
        templates = dependencies.templates
        conditions = []
        plate_value = normalize_plate(plate)
        if plate_value:
            conditions.append(func.upper(func.replace(ParkingSession.car_license_number, " ", "")) == plate_value)
        from_day = parse_day(date_from) if date_from else None
        to_day = parse_day(date_to) if date_to else None
        if from_day:
            conditions.append(ParkingSession.start_time >= datetime.combine(from_day, time.min))
        if to_day:
            conditions.append(ParkingSession.start_time < datetime.combine(to_day + timedelta(days=1), time.min))
        if status:
            conditions.append(ParkingSession.status == status)

        normalized_session_plate = func.upper(func.replace(ParkingSession.car_license_number, " ", ""))
        async with async_session() as session:
            stmt = (
                select(ParkingSession, ParkingVehicle, ParkingVehicleDetails)
                .outerjoin(ParkingVehicle, ParkingVehicle.plate == normalized_session_plate)
                .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == normalized_session_plate)
                .order_by(ParkingSession.start_time.desc())
                .limit(limit)
            )
            count_stmt = select(func.count(ParkingSession.id))
            if conditions:
                stmt = stmt.where(*conditions)
                count_stmt = count_stmt.where(*conditions)
            result_rows = (await session.execute(stmt)).all()
            count = (await session.execute(count_stmt)).scalar_one()
            statuses = (
                await session.execute(
                    select(ParkingSession.status)
                    .group_by(ParkingSession.status)
                    .order_by(ParkingSession.status)
                )
            ).scalars().all()
        return templates.TemplateResponse(
            request,
            "parking_sessions.html",
            {
                "rows": [
                    {
                        "session": row,
                        "vehicle": vehicle,
                        "details": details,
                        "year": parking_vehicle_display_year(details, vehicle.car_info_data if vehicle else None),
                        "early_minutes": parking_slot_remainder_minutes(row),
                        "plate": normalize_plate(row.car_license_number),
                        "owner_warning": parking_current_ownership_warning(vehicle, row.start_time),
                    }
                    for row, vehicle, details in result_rows
                ],
                "count": count,
                "statuses": statuses,
                "filters": {
                    "plate": plate or "",
                    "date_from": date_from or "",
                    "date_to": date_to or "",
                    "status": status or "",
                    "limit": limit,
                },
            },
        )

    @router.get("/parkering/kjoretoy", response_class=HTMLResponse)
    async def parking_vehicles_view(
        request: Request,
        plate: Optional[str] = None,
        navn: Optional[str] = None,
        omrade: Optional[str] = None,
        sun2_id: Optional[str] = None,
        merke: Optional[str] = None,
        modell: Optional[str] = None,
        ryddet: Optional[int] = None,
        limit: int = Query(100, ge=1, le=500),
    ):
        async_session = dependencies.async_session
        templates = dependencies.templates
        conditions = []

        def add_contains(column, value: Optional[str]):
            query = (value or "").strip()
            if query:
                conditions.append(func.upper(func.coalesce(column, "")).like(f"%{query.upper()}%"))

        plate_query = compact_plate(plate or "")
        if plate_query:
            conditions.append(func.upper(func.replace(ParkingVehicle.plate, " ", "")).like(f"%{plate_query.upper()}%"))

        add_contains(ParkingVehicle.navn, navn)
        add_contains(ParkingVehicle.omrade, omrade)
        add_contains(ParkingVehicle.sun2_id, sun2_id)
        add_contains(ParkingVehicleDetails.merke, merke)

        model_query = (modell or "").strip()
        if model_query:
            like = f"%{model_query.upper()}%"
            conditions.append(
                or_(
                    func.upper(func.coalesce(ParkingVehicleDetails.modell, "")).like(like),
                    func.upper(func.coalesce(ParkingVehicleDetails.typebetegnelse, "")).like(like),
                )
            )

        async with async_session() as session:
            stmt = (
                select(ParkingVehicle, ParkingVehicleDetails)
                .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                .order_by(ParkingVehicle.last_seen.desc().nullslast())
                .limit(limit)
            )
            count_stmt = select(func.count(ParkingVehicle.plate)).outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
            if conditions:
                stmt = stmt.where(*conditions)
                count_stmt = count_stmt.where(*conditions)
            rows = (await session.execute(stmt)).all()
            count = (await session.execute(count_stmt)).scalar_one()
            valid_area_condition = and_(
                func.trim(func.coalesce(ParkingVehicle.omrade, "")) != "",
                func.lower(func.trim(func.coalesce(ParkingVehicle.omrade, ""))) != "ikke funnet",
            )
            vehicle_total = (
                await session.execute(select(func.count(func.distinct(ParkingVehicle.plate))))
            ).scalar_one()
            vehicle_with_area = (
                await session.execute(
                    select(func.count(func.distinct(ParkingVehicle.plate))).where(valid_area_condition)
                )
            ).scalar_one()
        return templates.TemplateResponse(
            request,
            "parking_vehicles.html",
            {
                "rows": rows,
                "count": count,
                "vehicle_area_stats": {
                    "total": vehicle_total,
                    "with_area": vehicle_with_area,
                    "missing_area": max((vehicle_total or 0) - (vehicle_with_area or 0), 0),
                    "coverage_percent": round((vehicle_with_area / vehicle_total) * 100, 1) if vehicle_total else 0,
                },
                "filters": {
                    "plate": plate or "",
                    "navn": navn or "",
                    "omrade": omrade or "",
                    "sun2_id": sun2_id or "",
                    "merke": merke or "",
                    "modell": modell or "",
                    "limit": limit,
                },
                "cleanup_count": ryddet,
            },
        )

    @router.post("/parkering/kjoretoy/rydd-ikke-funnet")
    async def parking_vehicle_clear_not_found_area(request: Request):
        async_session = dependencies.async_session
        clear_parking_vehicle_not_found_area = dependencies.clear_parking_vehicle_not_found_area
        redirect_with_query_params = dependencies.redirect_with_query_params
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        async with async_session() as session:
            cleared = await clear_parking_vehicle_not_found_area(session)
            await session.commit()
        return redirect_with_query_params(request, "/parkering/kjoretoy", ryddet=cleared)

    @router.get("/parkering/navn-oppslag", response_class=HTMLResponse)
    async def parking_name_lookup_view(request: Request, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
        async_session = dependencies.async_session
        parking_missing_name_rows = dependencies.parking_missing_name_rows
        templates = dependencies.templates
        vehicle_blank_name_condition = dependencies.vehicle_blank_name_condition
        async with async_session() as session:
            rows = await parking_missing_name_rows(session, limit, offset, include_not_found=False)
            count = (
                await session.execute(
                    select(func.count(ParkingVehicle.plate)).where(vehicle_blank_name_condition())
                )
            ).scalar_one()
        plates = "\n".join(vehicle.plate for vehicle, _ in rows)
        return templates.TemplateResponse(
            request,
            "parking_name_lookup.html",
            {
                "rows": rows,
                "count": count,
                "plates": plates,
                "limit": limit,
                "offset": offset,
                "next_offset": offset + limit,
                "prev_offset": max(0, offset - limit),
            },
        )

    @router.get("/parkering/omrade-oppslag", response_class=HTMLResponse)
    async def parking_area_lookup_view(request: Request, limit: int = Query(1000, ge=1, le=1000), offset: int = Query(0, ge=0)):
        async_session = dependencies.async_session
        parking_missing_area_rows = dependencies.parking_missing_area_rows
        templates = dependencies.templates
        vehicle_blank_area_condition = dependencies.vehicle_blank_area_condition
        async with async_session() as session:
            rows = await parking_missing_area_rows(session, limit, offset, include_not_found=False)
            count = (
                await session.execute(
                    select(func.count(ParkingVehicle.plate)).where(vehicle_blank_area_condition())
                )
            ).scalar_one()
        plates = "\n".join(vehicle.plate for vehicle, _ in rows)
        return templates.TemplateResponse(
            request,
            "parking_name_lookup.html",
            {
                "rows": rows,
                "count": count,
                "plates": plates,
                "limit": limit,
                "offset": offset,
                "next_offset": offset + limit,
                "prev_offset": max(0, offset - limit),
                "mode": "omrade",
                "title": "Områdeoppslag",
                "description": "biler mangler område. Denne siden gir extensionen neste pakke på",
            },
        )

    @router.get("/api/parkering/kjoretoy/car-info-kandidater")
    async def parking_car_info_candidates_api(
        request: Request,
        limit: int = Query(1, ge=1, le=10),
        offset: int = Query(0, ge=0),
        country: Optional[str] = Query(None),
        format: str = "json",
    ):
        async_session = dependencies.async_session
        parking_car_info_candidate_rows = dependencies.parking_car_info_candidate_rows
        parking_vehicle_lookup_payload = dependencies.parking_vehicle_lookup_payload
        require_settings_or_car_info_access = dependencies.require_settings_or_car_info_access
        vehicle_car_info_candidate_condition = dependencies.vehicle_car_info_candidate_condition
        vehicle_car_info_country_condition = dependencies.vehicle_car_info_country_condition
        forbidden = require_settings_or_car_info_access(request)
        if forbidden:
            return forbidden
        condition = vehicle_car_info_candidate_condition()
        country_condition = vehicle_car_info_country_condition(country)
        if country_condition is not None:
            condition = and_(condition, country_condition)
        async with async_session() as session:
            rows = await parking_car_info_candidate_rows(session, limit, offset, country)
            count = (
                await session.execute(
                    select(func.count(ParkingVehicle.plate))
                    .select_from(ParkingVehicle)
                    .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                    .where(condition)
                )
            ).scalar_one()
        payload = [parking_vehicle_lookup_payload(vehicle, details) for vehicle, details in rows]
        if format == "txt":
            text_body = "\n".join(item["plate"] for item in payload) + ("\n" if payload else "")
            return StreamingResponse(iter([text_body]), media_type="text/plain; charset=utf-8")
        return {"count": count, "country": country, "limit": limit, "offset": offset, "rows": payload}

    @router.get("/api/parkering/kjoretoy/mangler-navn")
    async def parking_missing_names_api(
        request: Request,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        include_not_found: bool = False,
        format: str = "json",
    ):
        async_session = dependencies.async_session
        parking_missing_name_rows = dependencies.parking_missing_name_rows
        parking_vehicle_lookup_payload = dependencies.parking_vehicle_lookup_payload
        vehicle_blank_name_condition = dependencies.vehicle_blank_name_condition
        vehicle_missing_name_condition = dependencies.vehicle_missing_name_condition
        condition = vehicle_missing_name_condition() if include_not_found else vehicle_blank_name_condition()
        async with async_session() as session:
            rows = await parking_missing_name_rows(session, limit, offset, include_not_found=include_not_found)
            count = (
                await session.execute(
                    select(func.count(ParkingVehicle.plate)).where(condition)
                )
            ).scalar_one()
        payload = [parking_vehicle_lookup_payload(vehicle, details) for vehicle, details in rows]
        if format == "txt":
            text_body = "\n".join(item["plate"] for item in payload) + ("\n" if payload else "")
            return StreamingResponse(iter([text_body]), media_type="text/plain; charset=utf-8")
        return {"count": count, "limit": limit, "offset": offset, "rows": payload}

    @router.get("/api/parkering/kjoretoy/mangler-omrade")
    async def parking_missing_areas_api(
        request: Request,
        limit: int = Query(1000, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        include_not_found: bool = False,
        format: str = "json",
    ):
        async_session = dependencies.async_session
        parking_missing_area_rows = dependencies.parking_missing_area_rows
        parking_vehicle_lookup_payload = dependencies.parking_vehicle_lookup_payload
        vehicle_blank_area_condition = dependencies.vehicle_blank_area_condition
        vehicle_missing_area_condition = dependencies.vehicle_missing_area_condition
        condition = vehicle_missing_area_condition() if include_not_found else vehicle_blank_area_condition()
        async with async_session() as session:
            rows = await parking_missing_area_rows(session, limit, offset, include_not_found=include_not_found)
            count = (
                await session.execute(
                    select(func.count(ParkingVehicle.plate)).where(condition)
                )
            ).scalar_one()
        payload = [parking_vehicle_lookup_payload(vehicle, details) for vehicle, details in rows]
        if format == "txt":
            text_body = "\n".join(item["plate"] for item in payload) + ("\n" if payload else "")
            return StreamingResponse(iter([text_body]), media_type="text/plain; charset=utf-8")
        return {"count": count, "limit": limit, "offset": offset, "rows": payload}

    @router.post("/api/parkering/kjoretoy/{plate}/navn")
    async def parking_vehicle_name_api(request: Request, plate: str, data: ParkingVehicleNameUpdate):
        async_session = dependencies.async_session
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        plate_value = normalize_plate(plate)
        name = (data.navn or "").strip()
        if not plate_value:
            return JSONResponse({"detail": "Mangler registreringsnummer"}, status_code=400)
        if not name:
            return JSONResponse({"detail": "Navn mangler"}, status_code=400)
        async with async_session() as session:
            vehicle = (await session.execute(select(ParkingVehicle).where(ParkingVehicle.plate == plate_value))).scalars().first()
            if not vehicle:
                return JSONResponse({"detail": "Kjøretøy ikke funnet"}, status_code=404)
            vehicle.navn = name
            if data.sun2_id is not None:
                vehicle.sun2_id = data.sun2_id.strip() or None
            if data.notat is not None:
                vehicle.notat = data.notat.strip() or None
            note_bits = []
            if data.source:
                note_bits.append(f"kilde={data.source.strip()}")
            if data.raw:
                note_bits.append(f"raw={json.dumps(data.raw, ensure_ascii=False)[:1000]}")
            if note_bits:
                base_note = vehicle.notat.strip() if vehicle.notat else ""
                auto_note = f"Automatisk navneoppslag {local_now_naive().strftime('%Y-%m-%d %H:%M')}: " + " | ".join(note_bits)
                vehicle.notat = f"{base_note}\n{auto_note}".strip()
            vehicle.updated_at = datetime.utcnow()
            await session.commit()
        return {"status": "ok", "plate": plate_value, "navn": name}

    @router.post("/api/parkering/kjoretoy/{plate}/omrade")
    async def parking_vehicle_area_api(request: Request, plate: str, data: ParkingVehicleAreaUpdate):
        async_session = dependencies.async_session
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        plate_value = normalize_plate(plate)
        area = (data.omrade or "").strip()
        if not plate_value:
            return JSONResponse({"detail": "Mangler registreringsnummer"}, status_code=400)
        if not area:
            return JSONResponse({"detail": "Område mangler"}, status_code=400)
        async with async_session() as session:
            vehicle = (await session.execute(select(ParkingVehicle).where(ParkingVehicle.plate == plate_value))).scalars().first()
            if not vehicle:
                return JSONResponse({"detail": "Kjøretøy ikke funnet"}, status_code=404)
            vehicle.omrade = area
            vehicle.omrade_kilde = (data.source or "manual-browser-helper").strip() or "manual-browser-helper"
            vehicle.omrade_oppdatert = datetime.utcnow()
            vehicle.updated_at = datetime.utcnow()
            await session.commit()
        return {"status": "ok", "plate": plate_value, "omrade": area}

    @router.post("/api/parkering/kjoretoy/{plate}/car-info")
    async def parking_vehicle_car_info_api(request: Request, plate: str, data: ParkingVehicleCarInfoUpdate):
        async_session = dependencies.async_session
        clear_summary_cache = dependencies.clear_summary_cache
        is_not_found_marker = dependencies.is_not_found_marker
        parking_vehicle_by_plate_or_compact = dependencies.parking_vehicle_by_plate_or_compact
        record_import_job = dependencies.record_import_job
        require_settings_or_car_info_access = dependencies.require_settings_or_car_info_access
        forbidden = require_settings_or_car_info_access(request)
        if forbidden:
            return forbidden
        plate_value = normalize_plate(plate)
        if not plate_value:
            return JSONResponse({"detail": "Mangler registreringsnummer"}, status_code=400)
        if not is_supported_foreign_license_plate(plate_value):
            return JSONResponse({"detail": "Registreringsnummer matcher ikke svensk eller dansk standardformat"}, status_code=400)

        now = datetime.utcnow()
        async with async_session() as session:
            vehicle = await parking_vehicle_by_plate_or_compact(session, plate_value)
            if not vehicle:
                return JSONResponse({"detail": "Kjøretøy ikke funnet"}, status_code=404)
            vehicle.car_info_fetched_at = now
            vehicle.car_info_status = int(data.status or 0)
            vehicle.car_info_error = (data.error or "").strip()[:1000] or None
            vehicle.car_info_url = (data.url or "").strip()[:1000] or None
            vehicle.car_info_data = data.data or None
            area_updated = False
            area_label = car_info_area_label(data.data)
            if data.status == 200 and area_label and car_info_confirmed_foreign(data.data):
                current_area = (vehicle.omrade or "").strip()
                if not current_area or is_not_found_marker(current_area):
                    vehicle.omrade = area_label
                    vehicle.omrade_kilde = car_info_source_label(data.data, plate_value)
                    vehicle.omrade_oppdatert = now
                    area_updated = True
            vehicle.updated_at = now
            await record_import_job(
                session,
                car_info_import_job_name(data.data, plate_value),
                ok=car_info_import_ok(data.status),
                source=car_info_source_label(data.data, plate_value),
                records_imported=1 if data.status == 200 and car_info_confirmed_foreign(data.data) else 0,
                records_total=1,
                message=f"{plate_value}: {car_info_status_label(data.status, data.data)}",
                raw={
                    "plate": vehicle.plate,
                    "lookup_plate": plate_value if vehicle.plate != plate_value else None,
                    "status": data.status,
                    "confirmed_swedish": car_info_confirmed_swedish(data.data),
                    "confirmed_foreign": car_info_confirmed_foreign(data.data),
                    "country_code": car_info_lookup_country_code(data.data, plate_value) or None,
                    "area_updated": area_updated,
                    "error": vehicle.car_info_error,
                },
            )
            await session.commit()
        clear_summary_cache("parking")
        return {
            "status": "ok",
            "plate": vehicle.plate,
            "lookup_plate": plate_value if vehicle.plate != plate_value else None,
            "car_info_status": data.status,
            "confirmed_swedish": car_info_confirmed_swedish(data.data),
            "confirmed_foreign": car_info_confirmed_foreign(data.data),
            "country_code": car_info_lookup_country_code(data.data, plate_value) or None,
            "omrade": area_label if area_updated else None,
        }

    @router.get("/parkering/kjoretoy/{plate}", response_class=HTMLResponse)
    async def parking_vehicle_detail_view(request: Request, plate: str, saved: Optional[str] = None):
        async_session = dependencies.async_session
        templates = dependencies.templates
        plate_value = normalize_plate(plate)
        if not plate_value:
            raise HTTPException(status_code=404, detail="Mangler registreringsnummer")

        normalized_session_plate = func.upper(func.replace(ParkingSession.car_license_number, " ", ""))
        async with async_session() as session:
            result = (
                await session.execute(
                    select(ParkingVehicle, ParkingVehicleDetails)
                    .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                    .where(ParkingVehicle.plate == plate_value)
                )
            ).first()
            if not result:
                raise HTTPException(status_code=404, detail="Kjøretøy ikke funnet")
            vehicle, details = result
            stats = (
                await session.execute(
                    select(
                        func.count(ParkingSession.id),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0),
                        func.coalesce(func.sum(ParkingSession.parking_time_min), 0),
                        func.min(ParkingSession.start_time),
                        func.max(ParkingSession.start_time),
                    ).where(normalized_session_plate == plate_value)
                )
            ).first()
            recent_sessions_result = (
                await session.execute(
                    select(ParkingSession)
                    .where(normalized_session_plate == plate_value)
                    .order_by(ParkingSession.start_time.desc())
                    .limit(20)
                )
            ).scalars().all()

        current_ownership_at = svv_current_ownership_at(vehicle.svv_data)
        detail_rows = []
        if details:
            detail_rows = [
                ("Merke", details.merke),
                ("Modell", details.modell),
                ("Typebetegnelse", details.typebetegnelse),
                ("Årsmodell", parking_vehicle_year(details)),
                ("Farge", details.farge),
                ("Kjøretøyklasse", details.kjoretoyklasse_navn),
                ("Registreringsstatus", details.registreringsstatus_tekst),
                ("Nåværende eierskap fra", current_ownership_at),
                ("Førstegangsregistrert Norge", details.forstegangsregistrert_norge),
                ("PKK kontrollfrist", details.pkk_kontrollfrist),
                ("Egenvekt", f"{details.egenvekt_kg} kg" if details.egenvekt_kg is not None else None),
                ("Nyttelast", f"{details.nyttelast_kg} kg" if details.nyttelast_kg is not None else None),
                ("Tillatt totalvekt", f"{details.tillatt_totalvekt_kg} kg" if details.tillatt_totalvekt_kg is not None else None),
                ("Seter", details.seter_totalt),
                ("Lengde", f"{details.lengde_mm} mm" if details.lengde_mm is not None else None),
                ("Bredde", f"{details.bredde_mm} mm" if details.bredde_mm is not None else None),
                ("Høyde", f"{details.hoyde_mm} mm" if details.hoyde_mm is not None else None),
                ("Rekkevidde WLTP", f"{details.rekkevidde_wltp_km} km" if details.rekkevidde_wltp_km is not None else None),
                ("Elforbruk WLTP", f"{details.elforbruk_wltp_wh_km} Wh/km" if details.elforbruk_wltp_wh_km is not None else None),
                ("Motoreffekt", f"{details.motoreffekt_samlet_kw} kW" if details.motoreffekt_samlet_kw is not None else None),
                ("SVV teknisk gyldig fra", details.svv_teknisk_gyldig_fra),
                ("Sist synkronisert", details.sist_synkronisert),
                ("VIN", details.vin),
            ]
        detail_rows = [(label, value) for label, value in detail_rows if value not in (None, "")]

        return templates.TemplateResponse(
            request,
            "parking_vehicle_detail.html",
            {
                "plate": plate_value,
                "vehicle": vehicle,
                "details": details,
                "title": parking_vehicle_display_label(details, vehicle.car_info_data),
                "year": parking_vehicle_display_year(details, vehicle.car_info_data),
                "stats": {
                    "sessions": stats[0] or 0,
                    "paid": stats[1] or 0,
                    "minutes": stats[2] or 0,
                    "first": stats[3],
                    "last": stats[4],
                },
                "recent_sessions": [
                    {
                        "session": row,
                        "early_minutes": parking_slot_remainder_minutes(row),
                        "owner_warning": parking_current_ownership_warning(vehicle, row.start_time),
                    }
                    for row in recent_sessions_result
                ],
                "detail_rows": detail_rows,
                "ownership_warning": parking_current_ownership_warning(vehicle, stats[3]),
                "saved": saved == "1",
            },
        )

    @router.post("/parkering/kjoretoy/{plate}", response_class=HTMLResponse)
    async def parking_vehicle_detail_save(request: Request, plate: str):
        async_session = dependencies.async_session
        redirect_keep_query = dependencies.redirect_keep_query
        if not getattr(request.state, "auth_can_settings", False):
            raise HTTPException(status_code=403, detail="Du må ha innstillingstilgang for å endre kjøretøyfelt.")
        plate_value = normalize_plate(plate)
        form = await request.form()
        async with async_session() as session:
            vehicle = (await session.execute(select(ParkingVehicle).where(ParkingVehicle.plate == plate_value))).scalars().first()
            if not vehicle:
                raise HTTPException(status_code=404, detail="Kjøretøy ikke funnet")
            vehicle.navn = (form.get("navn") or "").strip() or None
            previous_area = vehicle.omrade
            vehicle.omrade = (form.get("omrade") or "").strip() or None
            if vehicle.omrade and vehicle.omrade != previous_area:
                vehicle.omrade_kilde = "manuell"
                vehicle.omrade_oppdatert = datetime.utcnow()
            vehicle.sun2_id = (form.get("sun2_id") or "").strip() or None
            vehicle.notat = (form.get("notat") or "").strip() or None
            vehicle.updated_at = datetime.utcnow()
            await session.commit()
        return redirect_keep_query(request, f"/parkering/kjoretoy/{quote(plate_value)}?saved=1", status_code=303)

    @router.get("/classic/parkering/kjoretoy", response_class=HTMLResponse)
    async def classic_parking_vehicles_view(
        request: Request,
        plate: Optional[str] = None,
        navn: Optional[str] = None,
        omrade: Optional[str] = None,
        sun2_id: Optional[str] = None,
        merke: Optional[str] = None,
        modell: Optional[str] = None,
        ryddet: Optional[int] = None,
        limit: int = Query(100, ge=1, le=500),
    ):
        return await parking_vehicles_view(request, plate, navn, omrade, sun2_id, merke, modell, ryddet, limit)

    @router.get("/classic/parkering/navn-oppslag", response_class=HTMLResponse)
    async def classic_parking_name_lookup_view(request: Request, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
        return await parking_name_lookup_view(request, limit, offset)

    @router.get("/classic/parkering/omrade-oppslag", response_class=HTMLResponse)
    async def classic_parking_area_lookup_view(request: Request, limit: int = Query(1000, ge=1, le=1000), offset: int = Query(0, ge=0)):
        return await parking_area_lookup_view(request, limit, offset)

    @router.get("/classic/parkering/kjoretoy/{plate}", response_class=HTMLResponse)
    async def classic_parking_vehicle_detail_view(request: Request, plate: str, saved: Optional[str] = None):
        return await parking_vehicle_detail_view(request, plate, saved)

    return RouterBundle(router, {
        "api_cars_day": api_cars_day,
        "api_cars_day_detections": api_cars_day_detections,
        "api_parking_control_report": api_parking_control_report,
        "api_v2_fetch_parking_settlements": api_v2_fetch_parking_settlements,
        "api_v2_parking_car_info_sync": api_v2_parking_car_info_sync,
        "api_v2_parking_clear_area_not_found": api_v2_parking_clear_area_not_found,
        "api_v2_parking_refresh": api_v2_parking_refresh,
        "api_v2_parking_save_forecast": api_v2_parking_save_forecast,
        "api_v2_parking_svv_sync": api_v2_parking_svv_sync,
        "api_v2_parking_time_distribution": api_v2_parking_time_distribution,
        "api_v2_parking_vehicle_clear_not_found": api_v2_parking_vehicle_clear_not_found,
        "api_v2_parking_vehicle_detail": api_v2_parking_vehicle_detail,
        "api_v2_parking_weekly_average_years": api_v2_parking_weekly_average_years,
        "api_v2_parking_weekly_averages": api_v2_parking_weekly_averages,
        "api_v2_parking_year_comparison": api_v2_parking_year_comparison,
        "classic_parking_area_lookup_view": classic_parking_area_lookup_view,
        "classic_parking_name_lookup_view": classic_parking_name_lookup_view,
        "classic_parking_vehicle_detail_view": classic_parking_vehicle_detail_view,
        "classic_parking_vehicles_view": classic_parking_vehicles_view,
        "parking_area_lookup_view": parking_area_lookup_view,
        "parking_area_overview_view": parking_area_overview_view,
        "parking_car_info_candidates_api": parking_car_info_candidates_api,
        "parking_easypark_import_csv": parking_easypark_import_csv,
        "parking_forecast_save": parking_forecast_save,
        "parking_forecast_view": parking_forecast_view,
        "parking_missing_areas_api": parking_missing_areas_api,
        "parking_missing_names_api": parking_missing_names_api,
        "parking_name_lookup_view": parking_name_lookup_view,
        "parking_overview_view": parking_overview_view,
        "parking_redirect": parking_redirect,
        "parking_refresh": parking_refresh,
        "parking_sessions_view": parking_sessions_view,
        "parking_statistics_view": parking_statistics_view,
        "parking_vehicle_area_api": parking_vehicle_area_api,
        "parking_vehicle_car_info_api": parking_vehicle_car_info_api,
        "parking_vehicle_clear_not_found_area": parking_vehicle_clear_not_found_area,
        "parking_vehicle_detail_save": parking_vehicle_detail_save,
        "parking_vehicle_detail_view": parking_vehicle_detail_view,
        "parking_vehicle_name_api": parking_vehicle_name_api,
        "parking_vehicle_statistics_view": parking_vehicle_statistics_view,
        "parking_vehicle_svv_sync_api": parking_vehicle_svv_sync_api,
        "parking_vehicles_view": parking_vehicles_view,
    }, dependencies)
