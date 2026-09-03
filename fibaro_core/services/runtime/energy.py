"""Energy services with explicit process dependencies."""

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fastapi import HTTPException
from fibaro_core.export_definitions import ENERGY_HOURLY_COLUMNS, ENERGY_IMPORT_COLUMNS
from fibaro_core.models import (
    EnergyCircuit,
    EnergyFibaroSample,
    EnergyHourlyConsumption,
    EnergyImportRun,
    EnergyLoad,
    EnergyNode,
    ImportJobStatus,
    Sun2Bed,
    Sun2TanningSession,
    VentilationSample,
)
from fibaro_core.schemas import EnergyFibaroIn, EventDataIn
from fibaro_core.services.presentation import (
    api_card,
    api_chart,
    api_iso_value,
    api_table,
    format_short_number,
    format_signed_short_number,
)
from fibaro_core.services.settlements.parsing import parse_settlement_number
from fibaro_core.services.summaries.energy import empty_fast_energy_summary
from pathlib import Path
from reconciliation_domain import evaluate_reconciliation
from sqlalchemy import func, or_, select
from statistics import median
from sun2_helpers import normalize_room_id, sun2_room_label
from time_formatting import (
    LOCAL_TZ,
    api_local_iso,
    format_local_datetime,
    format_source_datetime,
    local_now_naive,
    normalize_local_naive,
)
from typing import Any, Callable, Dict, Iterable, Optional
from v2_navigation import v2_module_title
from value_parsing import float_or_zero, float_value, int_or_zero
import asyncio
import json
import math


@dataclass
class Dependencies:
    ENERGY_ACCUMULATED_ID_BY_POWER_ID: Any
    ENERGY_ACCUMULATED_KEYS: Any
    ENERGY_AGGREGATE_GROUP_BY_POWER_ID: Any
    ENERGY_AGGREGATE_HC3_MEMBERS: Any
    ENERGY_AGGREGATE_METERS: Any
    ENERGY_AGGREGATE_METERS_BY_KEY: Any
    ENERGY_CIRCUIT_SEED_ROWS: Any
    ENERGY_CIRCUIT_SEED_SOURCE: Any
    ENERGY_FIBARO_AREAS: Any
    ENERGY_HC3_HOURLY_DISPLAY_OFFSET: Any
    ENERGY_HOURLY_COMPARE_FIELDS: Any
    ENERGY_LOAD_POWER_PROFILES: Any
    ENERGY_NODE_TYPES: Any
    ENERGY_REALTIME_MAX_DELTA_SECONDS: Any
    ENERGY_SUB_KEYS: Any
    HC3_ENERGY_LIVE_TIMEOUT_SECONDS: Any
    ROOF_EXHAUST_UNMETERED_W: Any
    SUMMARY_CACHE: Any
    SUNBED_ANALYSIS_VENTILATION_MATCH_SECONDS: Any
    SUNBED_POWER_ANALYSIS_CACHE_TTL: Any
    api_config_value_rows: Callable[..., Any]
    api_day_navigation: Callable[..., Any]
    api_import_job_status: Callable[..., Any]
    api_pick: Callable[..., Any]
    async_session: Callable[..., Any]
    get_energy_summaries: Callable[..., Any]
    hc3_api_is_configured: Callable[..., Any]
    hc3_cached_device_request: Callable[..., Any]
    hc3_first_present: Callable[..., Any]
    logger: Any
    nested_extra_value: Callable[..., Any]
    parse_boolish: Callable[..., Any]
    parse_day: Callable[..., Any]


def create_service(dependencies: Dependencies):

    def energy_sample_bucket(value: Optional[datetime]) -> datetime:
        stamp = normalize_local_naive(value) or local_now_naive()
        second = 30 if stamp.second >= 30 else 0
        return stamp.replace(second=second, microsecond=0)

    async def seed_energy_circuits(session) -> None:
        ENERGY_CIRCUIT_SEED_ROWS = dependencies.ENERGY_CIRCUIT_SEED_ROWS
        ENERGY_CIRCUIT_SEED_SOURCE = dependencies.ENERGY_CIRCUIT_SEED_SOURCE
        count = await session.scalar(select(func.count(EnergyCircuit.id)))
        if count:
            return
        now_value = datetime.utcnow()
        for row in ENERGY_CIRCUIT_SEED_ROWS:
            status = row.get("status") or ("aktiv" if row.get("breaker_rating_a") else "ukjent")
            session.add(
                EnergyCircuit(
                    circuit_no=row["circuit_no"],
                    description=row.get("description"),
                    breaker_type=row.get("breaker_type"),
                    breaker_rating_a=row.get("breaker_rating_a"),
                    breaker_characteristic=row.get("breaker_characteristic"),
                    cable_spec=row.get("cable_spec"),
                    cable_length_m=row.get("cable_length_m"),
                    install_method=row.get("install_method"),
                    terminal_ref=row.get("terminal_ref"),
                    rcd_ma=row.get("rcd_ma"),
                    note=row.get("note"),
                    status=status,
                    source=ENERGY_CIRCUIT_SEED_SOURCE,
                    imported_at=now_value,
                    updated_at=now_value,
                )
            )

    def sum_optional(values: list[Optional[float]]) -> Optional[float]:
        if any(value is None for value in values):
            return None
        return sum(float(value or 0) for value in values)

    def calculated_difference(main_value: Optional[float], values: list[Optional[float]]) -> Optional[float]:
        sub_sum = sum_optional(values)
        if main_value is None or sub_sum is None:
            return None
        return float(main_value) - sub_sum

    def accumulated_delta(current: Optional[float], previous: Optional[float]) -> tuple[Optional[float], bool]:
        if current is None:
            return None, False
        if previous is None:
            return None, False
        current_value = float(current)
        previous_value = float(previous)
        if current_value + 0.0001 >= previous_value:
            return max(current_value - previous_value, 0.0), False
        return max(current_value, 0.0), True

    def realtime_power_delta_kwh(
        current_w: Optional[float],
        previous_w: Optional[float],
        current_time: Optional[datetime],
        previous_time: Optional[datetime],
    ) -> Optional[float]:
        ENERGY_REALTIME_MAX_DELTA_SECONDS = dependencies.ENERGY_REALTIME_MAX_DELTA_SECONDS
        if current_w is None or current_time is None or previous_time is None:
            return None
        seconds = (current_time - previous_time).total_seconds()
        if seconds <= 0 or seconds > ENERGY_REALTIME_MAX_DELTA_SECONDS:
            return None
        if previous_w is None:
            average_w = float(current_w)
        else:
            average_w = (float(previous_w) + float(current_w)) / 2
        return max(average_w, 0.0) * seconds / 3600000

    def energy_hour_has_changed(existing: EnergyHourlyConsumption, row: Dict[str, Any]) -> bool:
        ENERGY_HOURLY_COMPARE_FIELDS = dependencies.ENERGY_HOURLY_COMPARE_FIELDS
        for field in ENERGY_HOURLY_COMPARE_FIELDS:
            current = getattr(existing, field)
            incoming = row.get(field)
            if isinstance(current, float) or isinstance(incoming, float):
                if current is None or incoming is None:
                    if current != incoming:
                        return True
                elif abs(float(current) - float(incoming)) > 0.000001:
                    return True
            elif current != incoming:
                return True
        return False

    def energy_fibaro_sample_payload(data: EnergyFibaroIn, previous: Optional[EnergyFibaroSample]) -> Dict[str, Any]:
        ENERGY_ACCUMULATED_KEYS = dependencies.ENERGY_ACCUMULATED_KEYS
        ENERGY_REALTIME_MAX_DELTA_SECONDS = dependencies.ENERGY_REALTIME_MAX_DELTA_SECONDS
        ENERGY_SUB_KEYS = dependencies.ENERGY_SUB_KEYS
        timestamp = normalize_local_naive(data.timestamp) or local_now_naive()
        bucket_start = energy_sample_bucket(data.bucket_start or timestamp)
        values: Dict[str, Any] = {
            "timestamp": timestamp,
            "bucket_start": bucket_start,
            "source": data.source,
            "inntak_w": data.inntak_w,
            "varmepumper_w": data.varmepumper_w,
            "belysning_w": data.belysning_w,
            "massasje_w": data.massasje_w,
            "annet_w": data.annet_w,
            "avfukter_w": data.avfukter_w,
            "differanse_fibaro_w": None,
            "inntak_kwh": data.inntak_kwh,
            "varmepumper_kwh": data.varmepumper_kwh,
            "belysning_kwh": data.belysning_kwh,
            "massasje_kwh": data.massasje_kwh,
            "annet_kwh": data.annet_kwh,
            "avfukter_kwh": data.avfukter_kwh,
            "differanse_fibaro_kwh": None,
            "extra": data.extra or {},
        }
        values["differanse_beregnet_w"] = calculated_difference(
            values["inntak_w"],
            [values[f"{key}_w"] for key in ENERGY_SUB_KEYS],
        )
        values["differanse_beregnet_kwh"] = calculated_difference(
            values["inntak_kwh"],
            [values[f"{key}_kwh"] for key in ENERGY_SUB_KEYS],
        )

        reset_flags: Dict[str, bool] = {}
        accumulated_control_deltas: Dict[str, Optional[float]] = {}
        for key in ENERGY_ACCUMULATED_KEYS:
            delta, reset = accumulated_delta(
                values.get(f"{key}_kwh"),
                getattr(previous, f"{key}_kwh", None) if previous else None,
            )
            accumulated_control_deltas[key] = delta
            values[f"{key}_delta_kwh"] = realtime_power_delta_kwh(
                values.get(f"{key}_w"),
                getattr(previous, f"{key}_w", None) if previous else None,
                timestamp,
                previous.timestamp if previous else None,
            )
            values[f"{key}_reset"] = reset
            reset_flags[key] = reset

        values["differanse_beregnet_delta_kwh"] = realtime_power_delta_kwh(
            values.get("differanse_beregnet_w"),
            getattr(previous, "differanse_beregnet_w", None) if previous else None,
            timestamp,
            previous.timestamp if previous else None,
        )
        values["extra"] = {
            **(values.get("extra") or {}),
            "reset_flags": reset_flags,
            "accumulated_control_deltas": accumulated_control_deltas,
            "delta_source": "realtime_w",
            "delta_max_interval_seconds": ENERGY_REALTIME_MAX_DELTA_SECONDS,
            "calculated_by": "fibaro10",
        }
        return values

    async def upsert_energy_fibaro_sample(session, data: EnergyFibaroIn) -> EnergyFibaroSample:
        timestamp = normalize_local_naive(data.timestamp) or local_now_naive()
        bucket_start = energy_sample_bucket(data.bucket_start or timestamp)
        previous = (
            await session.execute(
                select(EnergyFibaroSample)
                .where(EnergyFibaroSample.bucket_start < bucket_start)
                .order_by(EnergyFibaroSample.bucket_start.desc())
                .limit(1)
            )
        ).scalars().first()
        values = energy_fibaro_sample_payload(
            EnergyFibaroIn(**{**data.dict(), "timestamp": timestamp, "bucket_start": bucket_start}),
            previous,
        )
        existing = (
            await session.execute(
                select(EnergyFibaroSample)
                .where(EnergyFibaroSample.bucket_start == bucket_start)
                .limit(1)
            )
        ).scalars().first()
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
            return existing
        record = EnergyFibaroSample(**values)
        session.add(record)
        return record

    def energy_area_cards(latest: Optional[EnergyFibaroSample], totals: Dict[str, float], reset_counts: Dict[str, int]) -> list[Dict[str, Any]]:
        ENERGY_FIBARO_AREAS = dependencies.ENERGY_FIBARO_AREAS
        cards = []
        for area in ENERGY_FIBARO_AREAS:
            key = area["key"]
            cards.append(
                {
                    **area,
                    "power_w": getattr(latest, f"{key}_w", None) if latest else None,
                    "energy_kwh": getattr(latest, f"{key}_kwh", None) if latest else None,
                    "today_kwh": totals.get(f"{key}_delta_kwh", 0.0),
                    "resets_today": reset_counts.get(key, 0),
                }
            )
        return cards

    def percentile(values: list[float], percent: float) -> Optional[float]:
        if not values:
            return None
        ordered = sorted(values)
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * percent
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[int(position)]
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)

    def sunbed_session_bounds(row: Sun2TanningSession) -> tuple[datetime, datetime] | None:
        if not row.started_at:
            return None
        start_at = normalize_local_naive(row.started_at)
        end_at = normalize_local_naive(row.ended_at)
        if not start_at:
            return None
        if not end_at:
            end_at = start_at + timedelta(minutes=float(row.duration_minutes or 15))
        if end_at <= start_at:
            end_at = start_at + timedelta(minutes=max(1.0, float(row.duration_minutes or 1)))
        return start_at, end_at

    def build_sunbed_power_analysis(
        sessions: list[Sun2TanningSession],
        samples: list[Any],
        bed_lookup: Dict[str, Any],
        ventilation_samples: Optional[list[Any]] = None,
    ) -> Dict[str, Any]:
        ROOF_EXHAUST_UNMETERED_W = dependencies.ROOF_EXHAUST_UNMETERED_W
        SUNBED_ANALYSIS_VENTILATION_MATCH_SECONDS = dependencies.SUNBED_ANALYSIS_VENTILATION_MATCH_SECONDS
        warmup_minutes = 2
        cooldown_minutes = 3
        stop_before_end_minutes = 1
        min_samples_per_session = 3
        session_items = []
        for row in sessions:
            room_id = normalize_room_id(row.room_id)
            bounds = sunbed_session_bounds(row)
            if not room_id or not bounds:
                continue
            start_at, end_at = bounds
            session_items.append(
                {
                    "id": row.id,
                    "room_id": room_id,
                    "sun2_bed_id": row.sun2_bed_id,
                    "start": start_at,
                    "end": end_at,
                    "measure_start": start_at + timedelta(minutes=warmup_minutes),
                    "measure_end": end_at - timedelta(minutes=stop_before_end_minutes),
                    "occupied_end": end_at + timedelta(minutes=cooldown_minutes),
                    "duration_minutes": max(0.0, (end_at - start_at).total_seconds() / 60),
                }
            )

        events = []
        sessions_by_id = {}
        for item in session_items:
            sessions_by_id[item["id"]] = item
            events.append((item["start"], 1, item["id"]))
            events.append((item["occupied_end"], -1, item["id"]))
        events.sort(key=lambda item: (item[0], item[1]))

        ventilation_items: list[tuple[datetime, bool]] = []
        for row in ventilation_samples or []:
            bucket = row.get("bucket_start") if isinstance(row, dict) else getattr(row, "bucket_start", None)
            bucket = normalize_local_naive(bucket)
            fan_tak = row.get("fan_tak") if isinstance(row, dict) else getattr(row, "fan_tak", None)
            if bucket is not None:
                ventilation_items.append((bucket, bool(fan_tak)))
        ventilation_items.sort(key=lambda item: item[0])

        sample_items: list[tuple[datetime, float]] = []
        for sample in samples:
            bucket = sample.get("bucket_start") if isinstance(sample, dict) else getattr(sample, "bucket_start", None)
            bucket = normalize_local_naive(bucket)
            value = sample.get("differanse_beregnet_w") if isinstance(sample, dict) else getattr(sample, "differanse_beregnet_w", None)
            try:
                diff_w = float(value)
            except (TypeError, ValueError):
                continue
            if bucket is not None:
                sample_items.append((bucket, diff_w))
        sample_items.sort(key=lambda item: item[0])
        sample_interval_candidates = []
        for left, right in zip(sample_items, sample_items[1:]):
            seconds = (right[0] - left[0]).total_seconds()
            if 5 <= seconds <= 300:
                sample_interval_candidates.append(seconds)
        sample_interval_seconds = float(median(sample_interval_candidates)) if sample_interval_candidates else 30.0

        active: set[int] = set()
        event_index = 0
        ventilation_index = 0
        single_samples: list[tuple[datetime, float, float, int]] = []
        baseline_by_day_hour: Dict[tuple[date, int], list[float]] = defaultdict(list)
        baseline_by_day: Dict[date, list[float]] = defaultdict(list)
        baseline_global: list[float] = []
        overlap_samples = 0
        roof_exhaust_adjusted_samples = 0

        for sample_time, diff_w in sample_items:
            while (
                ventilation_index < len(ventilation_items)
                and ventilation_items[ventilation_index][0] < sample_time
            ):
                ventilation_index += 1
            nearest = None
            if ventilation_index < len(ventilation_items):
                nearest = ventilation_items[ventilation_index]
            if ventilation_index > 0:
                previous = ventilation_items[ventilation_index - 1]
                # Prefer the following sample on an exact tie, as before.
                if nearest is None or sample_time - previous[0] < nearest[0] - sample_time:
                    nearest = previous
            adjustment_w = 0.0
            if nearest is not None:
                nearest_time, nearest_fan_tak = nearest
                if (
                    nearest_fan_tak
                    and abs((sample_time - nearest_time).total_seconds()) <= SUNBED_ANALYSIS_VENTILATION_MATCH_SECONDS
                ):
                    adjustment_w = ROOF_EXHAUST_UNMETERED_W
                    roof_exhaust_adjusted_samples += 1
            analysis_diff_w = diff_w - adjustment_w

            while event_index < len(events) and events[event_index][0] <= sample_time:
                _, action, session_id = events[event_index]
                if action == 1:
                    active.add(session_id)
                else:
                    active.discard(session_id)
                event_index += 1
            if len(active) == 0:
                baseline_by_day_hour[(sample_time.date(), sample_time.hour)].append(analysis_diff_w)
                baseline_by_day[sample_time.date()].append(analysis_diff_w)
                baseline_global.append(analysis_diff_w)
            elif len(active) == 1:
                single_samples.append((sample_time, diff_w, analysis_diff_w, next(iter(active))))
            else:
                overlap_samples += 1

        global_baseline = median(baseline_global) if baseline_global else None
        baseline_by_day_hour_median = {
            key: median(values)
            for key, values in baseline_by_day_hour.items()
            if values
        }
        baseline_by_day_median = {
            key: median(values)
            for key, values in baseline_by_day.items()
            if values
        }
        per_room: Dict[str, Dict[str, Any]] = {}
        per_session: Dict[int, Dict[str, Any]] = {}
        candidate_sessions: Dict[int, Dict[str, Any]] = {}
        used_samples = 0
        rejected_low = 0
        missing_baseline = 0
        rejected_warmup_cooldown = 0
        rejected_short_sessions = 0
        rejected_short_samples = 0

        for sample_time, diff_w, analysis_diff_w, session_id in single_samples:
            session_item = sessions_by_id.get(session_id)
            if not session_item:
                continue
            if not (session_item["measure_start"] <= sample_time < session_item["measure_end"]):
                rejected_warmup_cooldown += 1
                continue
            baseline = baseline_by_day_hour_median.get((sample_time.date(), sample_time.hour))
            if baseline is None:
                baseline = baseline_by_day_median.get(sample_time.date(), global_baseline)
            if baseline is None:
                missing_baseline += 1
                continue
            net_w = analysis_diff_w - baseline
            if net_w <= 500:
                rejected_low += 1
                continue

            if session_id not in candidate_sessions:
                candidate_sessions[session_id] = {
                    **session_item,
                    "net_values": [],
                    "observed_values": [],
                    "baseline_values": [],
                }
            candidate_sessions[session_id]["net_values"].append(net_w)
            candidate_sessions[session_id]["observed_values"].append(diff_w)
            candidate_sessions[session_id]["baseline_values"].append(baseline)

        for session_id, session_item in candidate_sessions.items():
            net_values = session_item["net_values"]
            if len(net_values) < min_samples_per_session:
                rejected_short_sessions += 1
                rejected_short_samples += len(net_values)
                continue
            room_id = session_item["room_id"]
            bed = bed_lookup.get(room_id)
            if room_id not in per_room:
                per_room[room_id] = {
                    "room_id": room_id,
                    "label": sun2_room_label(room_id, getattr(bed, "name", None) if bed else None),
                    "sun2_bed_id": getattr(bed, "sun2_bed_id", None) if bed else session_item.get("sun2_bed_id"),
                    "bed_model": getattr(bed, "bed_model", None) if bed else None,
                    "samples_count": 0,
                    "sessions": set(),
                    "net_values": [],
                    "observed_values": [],
                    "baseline_values": [],
                    "estimated_kwh": 0.0,
                    "duration_minutes": 0.0,
                }
            target = per_room[room_id]
            target["samples_count"] += len(net_values)
            target["sessions"].add(session_id)
            target["net_values"].extend(net_values)
            target["observed_values"].extend(session_item["observed_values"])
            target["baseline_values"].extend(session_item["baseline_values"])
            target["estimated_kwh"] += sum(net_values) * sample_interval_seconds / 3600 / 1000
            used_samples += len(net_values)
            per_session[session_id] = {
                **session_item,
                "label": target["label"],
                "net_values": list(net_values),
                "observed_values": list(session_item["observed_values"]),
                "baseline_values": list(session_item["baseline_values"]),
            }

        rooms = []
        for item in per_room.values():
            net_values = item.pop("net_values")
            observed_values = item.pop("observed_values")
            baseline_values = item.pop("baseline_values")
            session_count = len(item.pop("sessions"))
            avg_w = sum(net_values) / len(net_values) if net_values else None
            median_w = median(net_values) if net_values else None
            estimate_w = median_w
            item.update(
                {
                    "sessions_count": session_count,
                    "avg_w": avg_w,
                    "median_w": median_w,
                    "estimate_w": estimate_w,
                    "p25_w": percentile(net_values, 0.25),
                    "p75_w": percentile(net_values, 0.75),
                    "min_w": min(net_values) if net_values else None,
                    "max_w": max(net_values) if net_values else None,
                    "avg_observed_w": sum(observed_values) / len(observed_values) if observed_values else None,
                    "avg_baseline_w": sum(baseline_values) / len(baseline_values) if baseline_values else None,
                    "kwh_10_min": (estimate_w or 0) / 1000 * (10 / 60),
                    "kwh_15_min": (estimate_w or 0) / 1000 * (15 / 60),
                    "kwh_20_min": (estimate_w or 0) / 1000 * (20 / 60),
                    "confidence": "Høy" if len(net_values) >= 60 and session_count >= 5 else "Middels" if len(net_values) >= 20 and session_count >= 2 else "Lav",
                }
            )
            rooms.append(item)
        rooms.sort(key=lambda item: (item.get("room_id") or ""))

        observations = []
        for item in per_session.values():
            net_values = item["net_values"]
            if not net_values:
                continue
            observations.append(
                {
                    "session_id": item["id"],
                    "room_id": item["room_id"],
                    "label": item["label"],
                    "start": item["start"],
                    "end": item["end"],
                    "duration_minutes": item["duration_minutes"],
                    "samples_count": len(net_values),
                    "avg_w": sum(net_values) / len(net_values),
                    "median_w": median(net_values),
                    "avg_observed_w": sum(item["observed_values"]) / len(item["observed_values"]),
                    "avg_baseline_w": sum(item["baseline_values"]) / len(item["baseline_values"]),
                    "estimated_kwh": sum(net_values) * sample_interval_seconds / 3600 / 1000,
                }
            )
        observations.sort(key=lambda item: item["start"], reverse=True)

        return {
            "rooms": rooms,
            "observations": observations[:80],
            "summary": {
                "sessions_total": len(session_items),
                "energy_samples_total": len(sample_items),
                "roof_exhaust_adjusted_samples": roof_exhaust_adjusted_samples,
                "roof_exhaust_adjustment_w": ROOF_EXHAUST_UNMETERED_W,
                "baseline_samples": len(baseline_global),
                "single_samples": used_samples,
                "overlap_samples": overlap_samples,
                "missing_baseline_samples": missing_baseline,
                "rejected_low_samples": rejected_low,
                "rejected_warmup_cooldown_samples": rejected_warmup_cooldown,
                "rejected_short_sessions": rejected_short_sessions,
                "rejected_short_samples": rejected_short_samples,
                "global_baseline_w": global_baseline,
                "rooms_count": len(rooms),
                "warmup_minutes": warmup_minutes,
                "cooldown_minutes": cooldown_minutes,
                "stop_before_end_minutes": stop_before_end_minutes,
                "min_samples_per_session": min_samples_per_session,
                "sample_interval_seconds": sample_interval_seconds,
            },
        }

    def sunbed_analysis_date_range(
        date_from: Optional[str],
        date_to: Optional[str],
        today: date,
        max_days: int = 120,
    ) -> tuple[date, date, int]:
        parse_day = dependencies.parse_day
        end_day = parse_day(date_to) if date_to else today
        start_day = parse_day(date_from) if date_from else end_day - timedelta(days=30)
        if start_day > end_day:
            start_day, end_day = end_day, start_day
        if (end_day - start_day).days > max_days:
            start_day = end_day - timedelta(days=max_days)
        return start_day, end_day, max_days

    async def load_sunbed_power_analysis(
        session,
        date_from: Optional[str],
        date_to: Optional[str],
        today: date,
    ) -> Dict[str, Any]:
        SUMMARY_CACHE = dependencies.SUMMARY_CACHE
        SUNBED_POWER_ANALYSIS_CACHE_TTL = dependencies.SUNBED_POWER_ANALYSIS_CACHE_TTL
        start_day, end_day, max_days = sunbed_analysis_date_range(date_from, date_to, today)
        cache_key = f"sunbed_power_analysis:{start_day.isoformat()}:{end_day.isoformat()}"
        now_utc = datetime.utcnow()
        cached = SUMMARY_CACHE.get(cache_key)
        if cached and cached.get("expires", datetime.min) > now_utc:
            return deepcopy(cached["value"])
        start_at = datetime.combine(start_day, time.min)
        end_at = datetime.combine(end_day + timedelta(days=1), time.min)
        session_rows = (
            await session.execute(
                select(Sun2TanningSession)
                .where(Sun2TanningSession.started_at >= start_at)
                .where(Sun2TanningSession.started_at < end_at)
                .where(Sun2TanningSession.room_id.is_not(None))
                .order_by(Sun2TanningSession.started_at.asc())
            )
        ).scalars().all()
        energy_rows = (
            await session.execute(
                select(
                    EnergyFibaroSample.bucket_start.label("bucket_start"),
                    EnergyFibaroSample.differanse_beregnet_w.label("differanse_beregnet_w"),
                )
                .where(EnergyFibaroSample.bucket_start >= start_at)
                .where(EnergyFibaroSample.bucket_start < end_at)
                .order_by(EnergyFibaroSample.bucket_start.asc())
            )
        ).mappings().all()
        ventilation_rows = (
            await session.execute(
                select(
                    VentilationSample.bucket_start.label("bucket_start"),
                    VentilationSample.fan_tak.label("fan_tak"),
                )
                .where(VentilationSample.bucket_start >= start_at)
                .where(VentilationSample.bucket_start < end_at)
                .order_by(VentilationSample.bucket_start.asc())
            )
        ).mappings().all()
        bed_rows = (
            await session.execute(
                select(Sun2Bed).where(Sun2Bed.room_id.is_not(None))
            )
        ).scalars().all()
        bed_lookup = {bed.room_id: bed for bed in bed_rows if bed.room_id}
        analysis = await asyncio.to_thread(
            build_sunbed_power_analysis,
            session_rows,
            [dict(row) for row in energy_rows],
            bed_lookup,
            [dict(row) for row in ventilation_rows],
        )
        max_power = max([float_or_zero(room.get("estimate_w")) for room in analysis["rooms"]] or [0.0])
        value = {
            "dateFrom": start_day.isoformat(),
            "dateTo": end_day.isoformat(),
            "maxDays": max_days,
            "maxPower": max_power,
            **analysis,
        }
        SUMMARY_CACHE[cache_key] = {"expires": now_utc + SUNBED_POWER_ANALYSIS_CACHE_TTL, "value": deepcopy(value)}
        return value

    async def sunbed_power_cache_warm_worker() -> None:
        SUNBED_POWER_ANALYSIS_CACHE_TTL = dependencies.SUNBED_POWER_ANALYSIS_CACHE_TTL
        async_session = dependencies.async_session
        logger = dependencies.logger
        refresh_seconds = max(60.0, SUNBED_POWER_ANALYSIS_CACHE_TTL.total_seconds() / 2)
        while True:
            try:
                async with async_session() as session:
                    await load_sunbed_power_analysis(
                        session,
                        None,
                        None,
                        datetime.now(LOCAL_TZ).date(),
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("Kunne ikke varme cache for energiforbruk per seng", exc_info=True)
            await asyncio.sleep(refresh_seconds)

    def payload_weather_symbol(data: EventDataIn) -> Optional[str]:
        nested_extra_value = dependencies.nested_extra_value
        return (
            data.weather_symbol
            or data.yr_symbol
            or nested_extra_value(data.extra, ["weather_symbol", "yr_symbol", "symbol_code", "next_1_hours_symbol_code"])
            or nested_extra_value(data.values, ["weather_symbol", "yr_symbol", "symbol_code", "next_1_hours_symbol_code"])
        )

    def payload_weather_text(data: EventDataIn) -> Optional[str]:
        nested_extra_value = dependencies.nested_extra_value
        return (
            data.weather_text
            or data.weather_type
            or data.yr_weather
            or nested_extra_value(data.extra, ["weather_text", "weather_type", "yr_weather", "weather", "condition_text", "condition"])
            or nested_extra_value(data.values, ["weather_text", "weather_type", "yr_weather", "weather", "condition_text", "condition"])
        )

    def hc3_energy_device_summary(device: Dict[str, Any]) -> Dict[str, Any]:
        hc3_first_present = dependencies.hc3_first_present
        parse_boolish = dependencies.parse_boolish
        properties = device.get("properties") if isinstance(device.get("properties"), dict) else {}
        device_type = str(device.get("type") or "")
        base_type = str(device.get("baseType") or "")
        raw_value = hc3_first_present(properties.get("value"), device.get("value"))
        power_raw = hc3_first_present(properties.get("power"), device.get("power"))
        if power_raw is None and "powermeter" in device_type.lower():
            power_raw = raw_value
        energy_raw = hc3_first_present(properties.get("energy"), device.get("energy"))
        if energy_raw is None and "energymeter" in device_type.lower():
            energy_raw = raw_value
        current_power = float_value(power_raw) if power_raw is not None and not isinstance(power_raw, bool) else None
        current_energy = float_value(energy_raw) if energy_raw is not None and not isinstance(energy_raw, bool) else None
        switch_capable = "binaryswitch" in device_type.lower() or isinstance(raw_value, bool)
        return {
            "id": int(device.get("id")) if device.get("id") is not None else None,
            "name": hc3_first_present(device.get("name"), properties.get("name")),
            "type": device_type or None,
            "baseType": base_type or None,
            "parentId": int(device.get("parentId")) if device.get("parentId") is not None else None,
            "roomId": int(device.get("roomID")) if device.get("roomID") is not None else None,
            "manufacturer": hc3_first_present(
                properties.get("manufacturer"),
                properties.get("manufacturerName"),
                device.get("manufacturer"),
            ),
            "model": hc3_first_present(
                properties.get("model"),
                properties.get("modelIdentifier"),
                properties.get("productLabel"),
                device.get("model"),
            ),
            "value": raw_value,
            "powerW": current_power,
            "energyKwh": current_energy,
            "switchState": parse_boolish(raw_value) if switch_capable else None,
            "hasPower": current_power is not None or "powermeter" in device_type.lower() or "power" in properties,
            "hasEnergy": current_energy is not None or "energymeter" in device_type.lower() or "energy" in properties,
            "hasSwitch": switch_capable,
            "dead": parse_boolish(hc3_first_present(properties.get("dead"), device.get("dead"))),
            "enabled": parse_boolish(hc3_first_present(properties.get("enabled"), device.get("enabled"))),
            "visible": parse_boolish(hc3_first_present(device.get("visible"), properties.get("visible"))),
        }

    async def hc3_energy_nodes_live(nodes: list[EnergyNode]) -> Dict[str, Any]:
        ENERGY_AGGREGATE_METERS = dependencies.ENERGY_AGGREGATE_METERS
        HC3_ENERGY_LIVE_TIMEOUT_SECONDS = dependencies.HC3_ENERGY_LIVE_TIMEOUT_SECONDS
        hc3_api_is_configured = dependencies.hc3_api_is_configured
        hc3_cached_device_request = dependencies.hc3_cached_device_request
        checked_at = api_local_iso(local_now_naive())
        if not hc3_api_is_configured():
            return {
                "checkedAt": checked_at,
                "configured": False,
                "nodes": {
                    str(node.id): {
                        "nodeId": node.id,
                        "status": "unavailable",
                        "checkedAt": checked_at,
                        "error": "HC3-tilgang er ikke konfigurert.",
                    }
                    for node in nodes
                    if node.id is not None
                },
                "aggregateMeters": {},
            }

        device_ids = {
            int(device_id)
            for node in nodes
            for device_id in (
                node.hc3_device_id,
                node.hc3_power_device_id,
                node.hc3_energy_device_id,
                node.hc3_switch_device_id,
            )
            if device_id is not None
        }
        device_ids.update(
            int(device_id)
            for group in ENERGY_AGGREGATE_METERS
            for device_id in (group["realtimeId"], group["accumulatedId"])
        )
        semaphore = asyncio.Semaphore(8)

        async def fetch_one(device_id: int) -> tuple[int, Optional[Dict[str, Any]], Optional[str]]:
            async with semaphore:
                try:
                    device = await asyncio.to_thread(hc3_cached_device_request, device_id, HC3_ENERGY_LIVE_TIMEOUT_SECONDS)
                    return device_id, hc3_energy_device_summary(device), None
                except Exception as exc:
                    return device_id, None, str(exc)

        fetched = await asyncio.gather(*(fetch_one(device_id) for device_id in sorted(device_ids)))
        devices = {device_id: payload for device_id, payload, error in fetched if payload is not None and error is None}
        errors = {device_id: error for device_id, payload, error in fetched if error}
        live_nodes: Dict[str, Dict[str, Any]] = {}
        for node in nodes:
            if node.id is None:
                continue
            power_id = node.hc3_power_device_id or (node.hc3_device_id if node.has_meter else None)
            energy_id = node.hc3_energy_device_id
            switch_id = node.hc3_switch_device_id or (node.hc3_device_id if node.has_switch else None)
            identity = devices.get(int(node.hc3_device_id)) if node.hc3_device_id is not None else None
            power = devices.get(int(power_id)) if power_id is not None else None
            energy = devices.get(int(energy_id)) if energy_id is not None else None
            if energy is None and power is not None and power.get("hasEnergy"):
                energy = power
            switch = devices.get(int(switch_id)) if switch_id is not None else None
            configured_ids = [value for value in (node.hc3_device_id, power_id, energy_id, switch_id) if value is not None]
            node_errors = [errors[int(value)] for value in configured_ids if int(value) in errors]
            configuration_errors: list[str] = []
            if power_id is not None and power is not None and not power.get("hasPower"):
                configuration_errors.append(f"HC3-enhet {power_id} rapporterer ikke watt.")
            if energy_id is not None and energy is not None and not energy.get("hasEnergy"):
                configuration_errors.append(f"HC3-enhet {energy_id} rapporterer ikke akkumulert kWh.")
            if switch_id is not None and switch is not None and not switch.get("hasSwitch"):
                configuration_errors.append(f"HC3-enhet {switch_id} rapporterer ikke av/på-status.")
            unavailable = [item for item in (identity, power, energy, switch) if item and item.get("dead") is True]
            disabled = [item for item in (identity, power, energy, switch) if item and item.get("enabled") is False]
            if unavailable:
                configuration_errors.append("En eller flere HC3-enheter er utilgjengelige.")
            if disabled:
                configuration_errors.append("En eller flere HC3-enheter er deaktivert.")
            if not configured_ids:
                status = "unconfigured"
            elif configuration_errors:
                status = "error"
            elif node_errors and not any((identity, power, energy, switch)):
                status = "error"
            elif node_errors:
                status = "partial"
            else:
                status = "ok"
            live_nodes[str(node.id)] = {
                "nodeId": node.id,
                "status": status,
                "checkedAt": checked_at,
                "currentPowerW": power.get("powerW") if power else None,
                "currentEnergyKwh": energy.get("energyKwh") if energy else None,
                "switchState": switch.get("switchState") if switch else None,
                "deviceName": identity.get("name") if identity else None,
                "powerDeviceName": power.get("name") if power else None,
                "energyDeviceName": energy.get("name") if energy else None,
                "switchDeviceName": switch.get("name") if switch else None,
                "dead": any(item.get("dead") is True for item in (identity, power, energy, switch) if item),
                "enabled": all(item.get("enabled") is not False for item in (identity, power, energy, switch) if item),
                "error": " · ".join(dict.fromkeys([*configuration_errors, *node_errors])) if configuration_errors or node_errors else None,
            }
        aggregate_live = {}
        for group in ENERGY_AGGREGATE_METERS:
            power_id = int(group["realtimeId"])
            energy_id = int(group["accumulatedId"])
            power = devices.get(power_id)
            energy = devices.get(energy_id)
            group_errors = [errors[device_id] for device_id in (power_id, energy_id) if device_id in errors]
            if power is not None and not power.get("hasPower"):
                group_errors.append(f"HC3-enhet {power_id} rapporterer ikke watt.")
            if energy is not None and not energy.get("hasEnergy"):
                group_errors.append(f"HC3-enhet {energy_id} rapporterer ikke akkumulert kWh.")
            if group_errors and not power and not energy:
                status = "error"
            elif group_errors or not power or not energy:
                status = "partial"
            else:
                status = "ok"
            aggregate_live[group["key"]] = {
                "key": group["key"],
                "status": status,
                "currentPowerW": power.get("powerW") if power else None,
                "currentEnergyKwh": energy.get("energyKwh") if energy else None,
                "error": " · ".join(dict.fromkeys(group_errors)) if group_errors else None,
            }
        return {"checkedAt": checked_at, "configured": True, "nodes": live_nodes, "aggregateMeters": aggregate_live}

    async def ingest_elvia_hours(session, parsed: Dict[str, Any], batch_time: datetime) -> Dict[str, int]:
        rows = parsed["rows"]
        if not rows:
            return {"inserted": 0, "updated": 0, "skipped": 0}

        meter_id = parsed["meter_id"]
        first_at = parsed["first_at"]
        last_at = parsed["last_at"]
        existing_rows = (
            await session.execute(
                select(EnergyHourlyConsumption)
                .where(EnergyHourlyConsumption.meter_id == meter_id)
                .where(EnergyHourlyConsumption.measured_at >= first_at)
                .where(EnergyHourlyConsumption.measured_at <= last_at)
            )
        ).scalars().all()
        existing_by_time = {row.measured_at: row for row in existing_rows}
        inserted = 0
        updated = 0
        skipped = 0

        for row in rows:
            existing = existing_by_time.get(row["measured_at"])
            if not existing:
                existing = EnergyHourlyConsumption(meter_id=meter_id, measured_at=row["measured_at"])
                session.add(existing)
                inserted += 1
            else:
                if not energy_hour_has_changed(existing, row):
                    skipped += 1
                    continue
                updated += 1

            existing.stat_date = row["stat_date"]
            existing.year = row["year"]
            existing.month = row["month"]
            existing.day = row["day"]
            existing.hour = row["hour"]
            existing.consumption_kwh = row["consumption_kwh"]
            existing.production_kwh = row["production_kwh"]
            existing.status = row["status"]
            existing.is_verified = row["is_verified"]
            existing.is_estimated = row["is_estimated"]
            existing.is_public_holiday = row["is_public_holiday"]
            existing.use_weekend_prices = row["use_weekend_prices"]
            existing.source = "elvia"
            existing.source_file = parsed["source_file"]
            existing.imported_at = batch_time
            existing.raw = row["raw"]

        return {"inserted": inserted, "updated": updated, "skipped": skipped}

    def manual_energy_quickapp_report() -> Dict[str, Any]:
        logger = dependencies.logger
        inventory_dir = Path("outputs/hc3_inventory")
        inventory_files = sorted(
            inventory_dir.glob("energy_quickapps_current_*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        snapshot_path = Path("docs/hc3-energy-inventory-current.json")
        data: Dict[str, Any] = {}
        inventory_path = ""

        def load_inventory_file(path: Path) -> Dict[str, Any] | None:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                    if isinstance(loaded, dict):
                        return loaded
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Kunne ikke lese HC3 energiinventar %s: %s", path.as_posix(), exc)
            return None

        inventory_candidates = [*inventory_files]
        if snapshot_path.exists():
            inventory_candidates.append(snapshot_path)
        for candidate in inventory_candidates:
            loaded = load_inventory_file(candidate)
            if loaded and isinstance(loaded.get("all_devices"), list):
                data = loaded
                inventory_path = candidate.as_posix()
                break
        if not data:
            for candidate in inventory_candidates:
                loaded = load_inventory_file(candidate)
                if loaded:
                    data = loaded
                    inventory_path = candidate.as_posix()
                    break

        group_meta = {
            "237": {"category": "Varmepumper", "kind": "Realtime W", "role": "Summerer faktisk effekt fra varmepumper."},
            "335": {"category": "Varmepumper", "kind": "Akkumulert kWh", "role": "Kontrollverdi for akkumulert energi fra varmepumper."},
            "305": {"category": "Belysning", "kind": "Realtime W", "role": "Summerer faktisk effekt fra lys og fasadebelysning."},
            "336": {"category": "Belysning", "kind": "Akkumulert kWh", "role": "Kontrollverdi for akkumulert energi fra lys."},
            "333": {"category": "Massasje", "kind": "Realtime W", "role": "Summerer effekt fra massasje, bad og varmtvann."},
            "337": {"category": "Massasje", "kind": "Akkumulert kWh", "role": "Kontrollverdi for akkumulert energi fra massasjegruppen."},
            "332": {"category": "Annet", "kind": "Realtime W", "role": "Summerer øvrige målte laster som TV, dataskap, ventilasjon, avfukter og Kurs 6."},
            "328": {"category": "Annet", "kind": "Akkumulert kWh", "role": "Kontrollverdi for akkumulert energi fra øvrige målte laster, inkludert Kurs 6."},
            "331": {"category": "Differanse", "kind": "Realtime W", "role": "HC3-kontroll. Fibaro10 beregner differanse selv og logger ikke denne som grunnlag."},
            "334": {"category": "Differanse", "kind": "Akkumulert kWh", "role": "HC3-kontroll. Brukes ikke som grunnlag for Fibaro10-forbruk."},
        }
        ordered_group_ids = ["237", "335", "305", "336", "333", "337", "332", "328", "331", "334"]
        groups_raw = data.get("groups") if isinstance(data.get("groups"), dict) else {}
        course6_covered_devices = {
            511: "Vifte VIP ligger bak Kurs 6 og forbruket inngår i 530 realtime / 529 akkumulert sammen med Lys loft massasje og bredbandsruter.",
            512: "Lys loft massasje ligger bak Kurs 6 og forbruket inngår i 530 realtime / 529 akkumulert sammen med Vifte VIP og bredbandsruter.",
        }

        included_parents: Dict[int, list[Dict[str, Any]]] = defaultdict(list)
        accumulated_group_ids = {"335", "336", "337", "328"}
        realtime_group_ids = {"237", "305", "333", "332"}
        for group_id in ordered_group_ids:
            group = groups_raw.get(group_id) if isinstance(groups_raw.get(group_id), dict) else {}
            for member in group.get("members") or []:
                if not isinstance(member, dict):
                    continue
                parent_id = member.get("parentId")
                if isinstance(parent_id, int) and parent_id > 0:
                    included_parents[parent_id].append(
                        {
                            "groupId": group_id,
                            "groupName": group.get("name") or group_meta.get(group_id, {}).get("category") or group_id,
                            "kind": group_meta.get(group_id, {}).get("kind", ""),
                            "memberId": member.get("id"),
                            "memberName": member.get("name"),
                        }
                    )

        def meter_value_label(row: Dict[str, Any]) -> str:
            for key in ("value", "power", "energy"):
                value = row.get(key)
                if isinstance(value, (int, float)):
                    return f"{value:g}"
            return ""

        groups: list[Dict[str, Any]] = []
        for group_id in ordered_group_ids:
            raw_group = groups_raw.get(group_id) if isinstance(groups_raw.get(group_id), dict) else {}
            meta = group_meta[group_id]
            members = []
            for member in raw_group.get("members") or []:
                if not isinstance(member, dict):
                    continue
                members.append(
                    {
                        "id": member.get("id"),
                        "name": member.get("name") or "",
                        "type": member.get("type") or "",
                        "room": member.get("room") or "",
                        "parentId": member.get("parentId"),
                        "value": meter_value_label(member),
                        "dead": bool(member.get("dead")),
                        "visible": member.get("visible"),
                        "note": "Direkte med i QuickApp-koden.",
                    }
                )
            groups.append(
                {
                    "id": int(group_id),
                    "name": raw_group.get("name") or meta["category"],
                    "category": meta["category"],
                    "kind": meta["kind"],
                    "role": meta["role"],
                    "memberCount": len(members),
                    "ids": raw_group.get("ids") or [member.get("id") for member in members],
                    "members": members,
                }
            )

        uncovered: list[Dict[str, Any]] = []
        for row in data.get("not_in_groups") or []:
            if not isinstance(row, dict):
                continue
            parent_id = row.get("parentId")
            parent_matches = included_parents.get(parent_id, []) if isinstance(parent_id, int) and parent_id > 0 else []
            parent_group_ids = {str(item.get("groupId") or "") for item in parent_matches}
            row_type = str(row.get("type") or "")
            dead = bool(row.get("dead"))
            status = "Ikke vurdert"
            severity = "info"
            note = ""
            if dead:
                status = "Død/utkoblet"
                severity = "muted"
                note = "HC3 markerer enheten som død. Den skal ikke legges til uten ny fysisk kontroll."
            elif row_type.endswith("energyMeter") and parent_group_ids & realtime_group_ids and not (parent_group_ids & accumulated_group_ids):
                status = "Mangler i akkumulert"
                severity = "bad"
                note = "Samme node har realtime-måler i oppsamling, men denne kWh-måleren ligger ikke i akkumulert gruppe."
            elif "electricMeter" in row_type:
                status = "Underverdi"
                severity = "muted"
                note = "Elektrisk underverdi, typisk spenning/strøm. Skal normalt ikke summeres i forbruk."
            elif parent_matches:
                status = "Dekket via node"
                severity = "ok"
                note = "Samme Z-Wave-node har en synlig kanal i oppsamling. Denne raden er normalt skjult/master/søskenkanal."
            else:
                status = "Ikke med"
                severity = "warn"
                note = "Ingen direkte oppsamling funnet. Bør vurderes hvis dette er en aktiv last."

            uncovered.append(
                {
                    "id": row.get("id"),
                    "name": row.get("name") or "",
                    "type": row_type,
                    "parentId": parent_id,
                    "parentName": row.get("parentName") or "",
                    "value": meter_value_label(row),
                    "status": status,
                    "severity": severity,
                    "coveredBy": ", ".join(
                        f"{item.get('groupName')} ({item.get('kind')})" for item in parent_matches[:4]
                    ),
                    "note": note,
                    "dead": dead,
                    "visible": row.get("visible"),
                }
            )

        gaps = [row for row in uncovered if row.get("severity") in {"bad", "warn"}]
        uncovered_by_id = {
            int(row["id"]): row
            for row in uncovered
            if isinstance(row.get("id"), int)
        }
        direct_by_id: Dict[int, list[Dict[str, Any]]] = defaultdict(list)
        for group in groups:
            for member in group.get("members") or []:
                member_id = member.get("id")
                if not isinstance(member_id, int):
                    continue
                direct_by_id[member_id].append(
                    {
                        "groupId": group.get("id"),
                        "groupName": group.get("name"),
                        "kind": group.get("kind"),
                        "category": group.get("category"),
                    }
                )
        quickapp_ids = {int(group_id) for group_id in ordered_group_ids}

        def row_is_energy_like(row: Dict[str, Any]) -> bool:
            row_type = f"{row.get('type') or ''} {row.get('baseType') or ''}"
            if any(marker in row_type for marker in ("powerMeter", "energyMeter", "electricMeter")):
                return True
            return any(isinstance(row.get(key), (int, float)) for key in ("power", "energy"))

        all_devices: list[Dict[str, Any]] = []
        for row in data.get("all_devices") or []:
            if not isinstance(row, dict):
                continue
            row_id = row.get("id")
            parent_id = row.get("parentId")
            direct_matches = direct_by_id.get(row_id, []) if isinstance(row_id, int) else []
            parent_matches = included_parents.get(parent_id, []) if isinstance(parent_id, int) and parent_id > 0 else []
            uncovered_row = uncovered_by_id.get(row_id) if isinstance(row_id, int) else None
            status = "Ikke energi"
            severity = "muted"
            note = "Ikke relevant for energisummering."
            covered_by = ""
            group_label = ""

            if isinstance(row_id, int) and row_id in quickapp_ids:
                status = "QuickApp"
                severity = "info"
                note = "Summerende HC3 QuickApp."
            elif direct_matches:
                status = "Med i oppsamling"
                severity = "ok"
                note = "Direkte medlem i QuickApp-kode."
                group_label = ", ".join(
                    f"{item.get('groupName')} ({item.get('kind')})" for item in direct_matches[:4]
                )
                covered_by = group_label
            elif isinstance(row_id, int) and row_id in course6_covered_devices:
                status = "Dekket av Kurs 6"
                severity = "ok"
                note = course6_covered_devices[row_id]
                covered_by = "Annet R (530 Kurs 6), Annet A (529 Kurs 6)"
            elif uncovered_row:
                status = str(uncovered_row.get("status") or "Ikke med")
                severity = str(uncovered_row.get("severity") or "info")
                note = str(uncovered_row.get("note") or "")
                covered_by = str(uncovered_row.get("coveredBy") or "")
            elif parent_matches:
                status = "Samme node"
                severity = "muted"
                note = "Samme Z-Wave-node har kanal i oppsamling."
                covered_by = ", ".join(
                    f"{item.get('groupName')} ({item.get('kind')})" for item in parent_matches[:4]
                )
            elif row_is_energy_like(row):
                status = "Ikke med"
                severity = "warn"
                note = "Energi-/effektenhet uten oppsamlingstreff."

            all_devices.append(
                {
                    "id": row_id,
                    "name": row.get("name") or "",
                    "type": row.get("type") or "",
                    "baseType": row.get("baseType") or "",
                    "room": row.get("room") or "",
                    "parentId": parent_id,
                    "parentName": row.get("parentName") or "",
                    "value": meter_value_label(row),
                    "status": status,
                    "severity": severity,
                    "groups": group_label,
                    "coveredBy": covered_by,
                    "note": note,
                    "dead": bool(row.get("dead")),
                    "visible": row.get("visible"),
                    "enabled": row.get("enabled"),
                }
            )

        direct_member_count = sum(group["memberCount"] for group in groups if group["id"] not in {331, 334})
        quickapp_count = len([group for group in groups if group["id"] not in {331, 334}])
        diff_count = len([group for group in groups if group["id"] in {331, 334}])
        bad_gap_count = len([row for row in gaps if row.get("severity") == "bad"])

        findings = [
            {
                "title": "Hovedstatus",
                "text": (
                    f"{quickapp_count} summerende QuickApps er kontrollert: realtime og akkumulert for varmepumper, "
                    "belysning, massasje og annet. Rapporten viser også komplett HC3-enhetsliste fra /api/devices."
                ),
            },
            {
                "title": "Reell mangel",
                "text": (
                    f"{bad_gap_count} måler peker seg ut som reell mangel. Se listen under for hvilke målere som bør vurderes."
                    if bad_gap_count
                    else "Ingen reelle hull ble funnet i siste inventar."
                ),
            },
            {
                "title": "Ikke direkte med",
                "text": (
                    "Listen over ikke direkte med inneholder også skjulte masterkanaler, spenning/strøm-underenheter "
                    "og døde noder. De skal normalt ikke legges inn i summeringen fordi det kan gi dobbeltelling."
                ),
            },
            {
                "title": "Differanse",
                "text": (
                    f"{diff_count} differanse-QuickApps finnes i HC3 som kontroll, men Fibaro10 bruker egne beregninger "
                    "fra 30-sekunders realtime samples som forbruksgrunnlag."
                ),
            },
        ]

        return {
            "createdAt": data.get("created_at") or "",
            "inventoryFile": inventory_path,
            "summary": {
                "quickApps": quickapp_count,
                "diffQuickApps": diff_count,
                "directMembers": direct_member_count,
                "notDirectlyIncluded": len(uncovered),
                "gaps": len(gaps),
                "realGaps": bad_gap_count,
                "energyDevices": data.get("energy_device_count"),
                "allDevices": len(all_devices) or data.get("all_device_count"),
            },
            "findings": findings,
            "groups": groups,
            "gaps": gaps,
            "notDirectlyIncluded": uncovered,
            "allDevices": all_devices,
        }

    def api_revenue_accumulated_year_chart(summaries: Dict[str, Any]) -> Dict[str, Any]:
        chart_rows = summaries.get("weekly_chart", [])

        def cumulative(values: list[Any]) -> list[Optional[float]]:
            total = 0.0
            result: list[Optional[float]] = []
            normalized = list(values[:53])
            last_value_index = max((index for index, value in enumerate(normalized) if value is not None), default=-1)
            for index in range(53):
                value = normalized[index] if index < len(normalized) else None
                if index > last_value_index:
                    result.append(None)
                    continue
                total += float_or_zero(value)
                result.append(round(total, 2))
            return result

        def metric_series(metric: str) -> list[Dict[str, Any]]:
            return [
                {
                    "name": row["year"],
                    "data": cumulative(row.get(metric) or []),
                    "color": row.get("color"),
                    "unit": "kr" if metric == "revenue" else "stk",
                    "smooth": False,
                    "step": "end",
                }
                for row in chart_rows
            ]

        current_year = local_now_naive().year
        return api_chart(
            "Akkumulert år",
            [str(week) for week in range(1, 54)],
            metric_series("revenue"),
            "Løpende sum uke for uke fra samme grunnlag som Omsetning oversikt.",
            "line",
            520,
            metrics=[
                {"key": "revenue", "label": "Omsetning", "unit": "kr", "series": metric_series("revenue")},
                {"key": "count", "label": "Antall", "unit": "stk", "series": metric_series("count")},
            ],
            default_metric="revenue",
            default_visible_series=[str(current_year), str(current_year - 1)],
        )

    def cumulative_energy_series(rows: list[EnergyFibaroSample], attr: str) -> list[float]:
        total = 0.0
        values = []
        for row in rows:
            total += float_or_zero(getattr(row, attr, None))
            values.append(round(total, 3))
        return values

    def cumulative_energy_points(rows: list[EnergyFibaroSample], attr: str) -> list[list[Any]]:
        total = 0.0
        points = []
        for row in rows:
            stamp = api_local_iso(row.bucket_start)
            if not stamp:
                continue
            total += float_or_zero(getattr(row, attr, None))
            points.append([stamp, round(total, 3)])
        return points

    def api_energy_circuit_edit() -> Dict[str, Any]:
        return {
            "kind": "energy-circuit",
            "title": "kurs",
            "idField": "circuit_no",
            "endpoint": "/api/energy/circuits/{circuit_no}",
            "method": "PATCH",
            "fields": [
                {"key": "description", "label": "Beskrivelse", "type": "textarea", "required": True},
                {"key": "breaker_type", "label": "Vern/type", "type": "text"},
                {"key": "breaker_rating_a", "label": "Ampere", "type": "number"},
                {"key": "breaker_characteristic", "label": "Karakteristikk", "type": "text"},
                {"key": "cable_spec", "label": "Kabel", "type": "text"},
                {"key": "cable_length_m", "label": "Kabellengde m", "type": "number"},
                {"key": "install_method", "label": "Forlegning", "type": "text"},
                {"key": "terminal_ref", "label": "Terminal/ref", "type": "text"},
                {"key": "rcd_ma", "label": "Jordfeilvern mA", "type": "number"},
                {"key": "is_sunbed", "label": "Solsengkurs", "type": "boolean"},
                {"key": "status", "label": "Status", "type": "text"},
                {"key": "note", "label": "Notat", "type": "textarea"},
            ],
        }

    def api_energy_load_edit() -> Dict[str, Any]:
        return {
            "kind": "energy-load",
            "title": "last",
            "idField": "id",
            "endpoint": "/api/energy/loads/{id}",
            "method": "PATCH",
            "createEndpoint": "/api/energy/loads",
            "fields": [
                {"key": "name", "label": "Navn", "type": "text", "required": True},
                {"key": "load_type", "label": "Type", "type": "text"},
                {"key": "area", "label": "Område", "type": "text"},
                {"key": "circuit_no", "label": "Kurs", "type": "number"},
                {
                    "key": "power_profile",
                    "label": "Effektprofil",
                    "type": "select",
                    "options": [
                        {"label": "Ikke kjent", "value": "unknown"},
                        {"label": "Fast effekt", "value": "fixed"},
                        {"label": "Variabel effekt", "value": "variable"},
                    ],
                },
                {"key": "min_power_w", "label": "Minimum W", "type": "number"},
                {"key": "expected_power_w", "label": "Normal/fast W", "type": "number"},
                {"key": "max_power_w", "label": "Maksimum W", "type": "number"},
                {"key": "measured_direct", "label": "Direktemålt", "type": "boolean"},
                {"key": "fibaro_device_id", "label": "HC3 enhet", "type": "number"},
                {"key": "fibaro_meter_id", "label": "HC3 måler", "type": "number"},
                {"key": "zwave_switch_id", "label": "Z-Wave bryter", "type": "number"},
                {"key": "controllable", "label": "Styrbar", "type": "boolean"},
                {"key": "critical", "label": "Kritisk", "type": "boolean"},
                {"key": "active", "label": "Aktiv", "type": "boolean"},
                {"key": "note", "label": "Notat", "type": "textarea"},
            ],
        }

    def api_energy_summary_item(item: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        item = item or empty_fast_energy_summary("-")
        return {
            "period": item.get("period"),
            "period_label": item.get("period_label"),
            "consumption_kwh": float_or_zero(item.get("consumption_kwh")),
            "production_kwh": float_or_zero(item.get("production_kwh")),
            "hours_count": int_or_zero(item.get("hours_count")),
            "estimated_hours_count": int_or_zero(item.get("estimated_hours_count")),
            "days_count": int_or_zero(item.get("days_count")),
        }

    def api_energy_elvia_payload(
        summaries: Dict[str, Any],
        imports: list[EnergyImportRun],
        rows: list[EnergyHourlyConsumption],
        status: Optional[ImportJobStatus],
    ) -> Dict[str, Any]:
        api_import_job_status = dependencies.api_import_job_status
        api_pick = dependencies.api_pick
        latest_import = imports[0] if imports else None
        return {
            "summary": {
                "total": api_energy_summary_item(summaries.get("total")),
                "firstAt": api_iso_value(summaries.get("first_at")),
                "lastAt": api_iso_value(summaries.get("last_at")),
            },
            "yearly": [api_energy_summary_item(item) for item in summaries.get("yearly", [])],
            "topDays": [api_energy_summary_item(item) for item in summaries.get("top_days", [])],
            "topMonths": [api_energy_summary_item(item) for item in summaries.get("top_months", [])],
            "imports": [api_pick(row, ENERGY_IMPORT_COLUMNS) for row in imports],
            "rows": [api_pick(row, ENERGY_HOURLY_COLUMNS) for row in rows],
            "latestImport": api_pick(latest_import, ENERGY_IMPORT_COLUMNS) if latest_import else None,
            "status": api_import_job_status(status),
            "uploadEndpoint": "/api/energy/elvia/upload",
        }

    def circuit_row_api(row: EnergyCircuit) -> Dict[str, Any]:
        return {
            "id": row.id,
            "circuit_no": row.circuit_no,
            "description": row.description,
            "breaker": f"{row.breaker_rating_a:g} A" if row.breaker_rating_a is not None else None,
            "breaker_type": row.breaker_type,
            "breaker_rating_a": row.breaker_rating_a,
            "breaker_characteristic": row.breaker_characteristic,
            "cable_spec": row.cable_spec,
            "cable_length_m": row.cable_length_m,
            "install_method": row.install_method,
            "terminal_ref": row.terminal_ref,
            "rcd_ma": row.rcd_ma,
            "is_sunbed": bool(row.is_sunbed),
            "status": row.status,
            "note": row.note,
        }

    def load_row_api(row: EnergyLoad) -> Dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "load_type": row.load_type,
            "area": row.area,
            "circuit_no": row.circuit_no,
            "power_profile": row.power_profile,
            "expected_power_w": row.expected_power_w,
            "min_power_w": row.min_power_w,
            "max_power_w": row.max_power_w,
            "measured_direct": row.measured_direct,
            "energy_node_id": row.energy_node_id,
            "fibaro_device_id": row.fibaro_device_id,
            "fibaro_meter_id": row.fibaro_meter_id,
            "zwave_switch_id": row.zwave_switch_id,
            "controllable": row.controllable,
            "critical": row.critical,
            "active": row.active,
            "note": row.note,
        }

    def energy_load_hierarchy_item(row: EnergyLoad) -> Dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "loadType": row.load_type,
            "area": row.area,
            "powerProfile": row.power_profile or ("fixed" if row.expected_power_w is not None else "unknown"),
            "expectedPowerW": row.expected_power_w,
            "minPowerW": row.min_power_w,
            "maxPowerW": row.max_power_w,
            "measuredDirect": row.measured_direct,
            "energyNodeId": row.energy_node_id,
            "fibaroDeviceId": row.fibaro_device_id,
            "fibaroMeterId": row.fibaro_meter_id,
            "zwaveSwitchId": row.zwave_switch_id,
            "controllable": row.controllable,
            "critical": row.critical,
            "active": row.active,
            "note": row.note,
        }

    def _legacy_energy_circuit_loads_payload(circuits: list[EnergyCircuit], loads: list[EnergyLoad]) -> Dict[str, Any]:
        loads_by_circuit: Dict[Optional[int], list[EnergyLoad]] = defaultdict(list)
        for load in loads:
            loads_by_circuit[load.circuit_no].append(load)

        known_circuit_numbers = {row.circuit_no for row in circuits if row.circuit_no is not None}
        circuit_rows: list[Dict[str, Any]] = []
        summary = {
            "circuits": len(circuits),
            "loads": len(loads),
            "activeLoads": sum(1 for row in loads if row.active is not False),
            "expectedPowerW": sum(float_or_zero(row.expected_power_w) for row in loads if row.active is not False),
            "circuitMeterCount": 0,
            "sharedMeterCount": 0,
            "directMeterLoadCount": 0,
            "unmeteredLoadCount": 0,
        }

        def make_groups(circuit_loads: list[EnergyLoad]) -> tuple[list[Dict[str, Any]], str, str, int, int, float]:
            active_loads = [row for row in circuit_loads if row.active is not False]
            expected_power = sum(float_or_zero(row.expected_power_w) for row in active_loads)
            measured_load_count = sum(1 for row in active_loads if row.fibaro_meter_id is not None or row.measured_direct)
            unmeasured_loads = [row for row in active_loads if row.fibaro_meter_id is None and not row.measured_direct]
            unmeasured_load_count = len(unmeasured_loads)

            meter_groups: Dict[int, list[EnergyLoad]] = defaultdict(list)
            for load in active_loads:
                if load.fibaro_meter_id is not None:
                    meter_groups[int(load.fibaro_meter_id)].append(load)

            groups: list[Dict[str, Any]] = []
            if active_loads and len(meter_groups) == 1 and len(next(iter(meter_groups.values()))) == len(active_loads):
                meter_id, group_loads = next(iter(meter_groups.items()))
                summary["circuitMeterCount"] += 1
                groups.append(
                    {
                        "key": f"meter-{meter_id}",
                        "label": "Kursmåler - dekker hele kursen",
                        "type": "circuit_meter",
                        "meterId": meter_id,
                        "loadCount": len(group_loads),
                        "expectedPowerW": sum(float_or_zero(row.expected_power_w) for row in group_loads),
                        "loads": [energy_load_hierarchy_item(row) for row in sorted(group_loads, key=lambda item: item.name or "")],
                    }
                )
                return groups, "Kursmålt", "Kurs -> måler -> alle aktive laster.", measured_load_count, unmeasured_load_count, expected_power

            for meter_id, group_loads in sorted(meter_groups.items(), key=lambda item: (len(item[1]) == 1, item[0])):
                is_shared = len(group_loads) > 1
                if is_shared:
                    summary["sharedMeterCount"] += 1
                else:
                    summary["directMeterLoadCount"] += 1
                groups.append(
                    {
                        "key": f"meter-{meter_id}",
                        "label": "Undermåler - flere laster" if is_shared else "Egen lastmåler",
                        "type": "shared_meter" if is_shared else "direct_meter",
                        "meterId": meter_id,
                        "loadCount": len(group_loads),
                        "expectedPowerW": sum(float_or_zero(row.expected_power_w) for row in group_loads),
                        "loads": [energy_load_hierarchy_item(row) for row in sorted(group_loads, key=lambda item: item.name or "")],
                    }
                )

            direct_without_meter = [row for row in active_loads if row.fibaro_meter_id is None and row.measured_direct]
            if direct_without_meter:
                summary["directMeterLoadCount"] += len(direct_without_meter)
                groups.append(
                    {
                        "key": "direct-without-meter-id",
                        "label": "Direktemålt last uten måler-ID",
                        "type": "direct_meter",
                        "meterId": None,
                        "loadCount": len(direct_without_meter),
                        "expectedPowerW": sum(float_or_zero(row.expected_power_w) for row in direct_without_meter),
                        "loads": [energy_load_hierarchy_item(row) for row in sorted(direct_without_meter, key=lambda item: item.name or "")],
                    }
                )

            if unmeasured_loads:
                summary["unmeteredLoadCount"] += len(unmeasured_loads)
                groups.append(
                    {
                        "key": "unmetered",
                        "label": "Direkte på kurs uten måler",
                        "type": "unmetered",
                        "meterId": None,
                        "loadCount": len(unmeasured_loads),
                        "expectedPowerW": sum(float_or_zero(row.expected_power_w) for row in unmeasured_loads),
                        "loads": [energy_load_hierarchy_item(row) for row in sorted(unmeasured_loads, key=lambda item: item.name or "")],
                    }
                )

            if not active_loads:
                return groups, "Ingen aktive laster", "Kurset har ingen aktive laster registrert.", measured_load_count, unmeasured_load_count, expected_power
            if unmeasured_load_count and measured_load_count:
                return groups, "Delvis målt", "Kurs -> en eller flere målere -> laster, pluss laster direkte på kurs.", measured_load_count, unmeasured_load_count, expected_power
            if measured_load_count:
                return groups, "Lastmålt", "Kurs -> målere/undermålere -> laster.", measured_load_count, unmeasured_load_count, expected_power
            return groups, "Ikke målt", "Kurs -> laster direkte på kurs uten registrert energimåler.", measured_load_count, unmeasured_load_count, expected_power

        for circuit in circuits:
            circuit_loads = loads_by_circuit.get(circuit.circuit_no, [])
            groups, mode, detail, measured_count, unmeasured_count, expected_power = make_groups(circuit_loads)
            circuit_rows.append(
                {
                    "key": f"circuit-{circuit.circuit_no}",
                    "circuitNo": circuit.circuit_no,
                    "description": circuit.description,
                    "breaker": f"{circuit.breaker_rating_a:g} A" if circuit.breaker_rating_a is not None else None,
                    "breakerType": circuit.breaker_type,
                    "status": circuit.status,
                    "isSunbed": bool(circuit.is_sunbed),
                    "note": circuit.note,
                    "loadCount": len(circuit_loads),
                    "activeLoadCount": sum(1 for row in circuit_loads if row.active is not False),
                    "expectedPowerW": expected_power,
                    "measuredLoadCount": measured_count,
                    "unmeasuredLoadCount": unmeasured_count,
                    "measurementMode": mode,
                    "measurementDetail": detail,
                    "measurementGroups": groups,
                }
            )

        unassigned_loads = [
            row for circuit_no, grouped_loads in loads_by_circuit.items()
            if circuit_no is None or circuit_no not in known_circuit_numbers
            for row in grouped_loads
        ]
        if unassigned_loads:
            groups, mode, detail, measured_count, unmeasured_count, expected_power = make_groups(unassigned_loads)
            circuit_rows.append(
                {
                    "key": "unassigned",
                    "circuitNo": None,
                    "description": "Uten gyldig kurs",
                    "breaker": None,
                    "breakerType": None,
                    "status": "Mangler kurskobling",
                    "isSunbed": False,
                    "note": "Laster som mangler kursnummer eller peker på en kurs som ikke finnes.",
                    "loadCount": len(unassigned_loads),
                    "activeLoadCount": sum(1 for row in unassigned_loads if row.active is not False),
                    "expectedPowerW": expected_power,
                    "measuredLoadCount": measured_count,
                    "unmeasuredLoadCount": unmeasured_count,
                    "measurementMode": mode,
                    "measurementDetail": detail,
                    "measurementGroups": groups,
                }
            )

        circuit_rows.sort(key=lambda row: (row["circuitNo"] is None, row["circuitNo"] or 9999))
        return {"summary": summary, "circuits": circuit_rows}

    def _meter_based_energy_circuit_loads_payload(
        circuits: list[EnergyCircuit],
        loads: list[EnergyLoad],
        meters: Optional[list[Any]] = None,
    ) -> Dict[str, Any]:
        meters = meters or []
        loads_by_circuit: Dict[Optional[int], list[EnergyLoad]] = defaultdict(list)
        for load in loads:
            loads_by_circuit[load.circuit_no].append(load)

        meters_by_circuit: Dict[Optional[int], list[Any]] = defaultdict(list)
        for meter in meters:
            meters_by_circuit[meter.circuit_no].append(meter)

        known_circuit_numbers = {row.circuit_no for row in circuits if row.circuit_no is not None}
        circuit_rows: list[Dict[str, Any]] = []
        summary = {
            "circuits": len(circuits),
            "loads": len(loads),
            "activeLoads": sum(1 for row in loads if row.active is not False),
            "expectedPowerW": sum(float_or_zero(row.expected_power_w) for row in loads if row.active is not False),
            "meterCount": sum(1 for row in meters if row.active is not False),
            "circuitMeterCount": 0,
            "sharedMeterCount": 0,
            "directMeterLoadCount": 0,
            "unmeteredLoadCount": 0,
        }

        def meter_display_name(meter: Any) -> str:
            if meter.name:
                return meter.name
            if meter.fibaro_meter_id is not None:
                return f"Måler HC3 {meter.fibaro_meter_id}"
            return "Måler uten HC3-ID"

        def meter_group_type(meter: Any, group_loads: list[EnergyLoad], active_loads: list[EnergyLoad]) -> str:
            explicit = (meter.meter_type or "").strip().lower()
            if explicit in {"circuit", "kurs", "kursmåler", "kursmaler"}:
                return "circuit_meter"
            if active_loads and group_loads and len(group_loads) == len(active_loads):
                return "circuit_meter"
            return "meter"

        def meter_group_label(group_type: str, group_loads: list[EnergyLoad]) -> str:
            if group_type == "circuit_meter":
                return "Kursmåler"
            if len(group_loads) > 1:
                return "Undermåler"
            return "Måler"

        def make_groups(
            circuit_no: Optional[int],
            circuit_loads: list[EnergyLoad],
            circuit_meters: list[Any],
        ) -> tuple[list[Dict[str, Any]], str, str, int, int, float]:
            active_loads = [row for row in circuit_loads if row.active is not False]
            active_meters = [row for row in circuit_meters if row.active is not False]
            expected_power = sum(float_or_zero(row.expected_power_w) for row in active_loads)
            loads_by_meter_id: Dict[int, list[EnergyLoad]] = defaultdict(list)
            legacy_meter_groups: Dict[int, list[EnergyLoad]] = defaultdict(list)
            direct_without_meter: list[EnergyLoad] = []
            unmeasured_loads: list[EnergyLoad] = []
            for load in active_loads:
                if load.energy_meter_id is not None:
                    loads_by_meter_id[int(load.energy_meter_id)].append(load)
                elif load.fibaro_meter_id is not None:
                    legacy_meter_groups[int(load.fibaro_meter_id)].append(load)
                elif load.measured_direct:
                    direct_without_meter.append(load)
                else:
                    unmeasured_loads.append(load)

            groups: list[Dict[str, Any]] = []
            used_legacy_meter_ids: set[int] = set()
            for meter in sorted(active_meters, key=lambda item: (item.fibaro_meter_id is None, item.fibaro_meter_id or 0, item.name or "")):
                group_loads = list(loads_by_meter_id.get(int(meter.id or 0), []))
                if meter.fibaro_meter_id is not None and int(meter.fibaro_meter_id) in legacy_meter_groups:
                    group_loads.extend(legacy_meter_groups[int(meter.fibaro_meter_id)])
                    used_legacy_meter_ids.add(int(meter.fibaro_meter_id))
                group_type = meter_group_type(meter, group_loads, active_loads)
                if group_type == "circuit_meter":
                    summary["circuitMeterCount"] += 1
                elif len(group_loads) > 1:
                    summary["sharedMeterCount"] += 1
                else:
                    summary["directMeterLoadCount"] += len(group_loads)
                groups.append(
                    {
                        "key": f"meter-db-{meter.id}",
                        "label": meter_display_name(meter),
                        "type": group_type,
                        "meterLabel": meter_group_label(group_type, group_loads),
                        "meterDbId": meter.id,
                        "meterId": meter.id,
                        "fibaroMeterId": meter.fibaro_meter_id,
                        "meterType": meter.meter_type,
                        "area": meter.area,
                        "active": meter.active,
                        "note": meter.note,
                        "loadCount": len(group_loads),
                        "expectedPowerW": sum(float_or_zero(row.expected_power_w) for row in group_loads),
                        "loads": [energy_load_hierarchy_item(row) for row in sorted(group_loads, key=lambda item: item.name or "")],
                    }
                )

            for meter_id, group_loads in sorted(legacy_meter_groups.items(), key=lambda item: (len(item[1]) == 1, item[0])):
                if meter_id in used_legacy_meter_ids:
                    continue
                group_type = "circuit_meter" if active_loads and len(group_loads) == len(active_loads) else "meter"
                if group_type == "circuit_meter":
                    summary["circuitMeterCount"] += 1
                elif len(group_loads) > 1:
                    summary["sharedMeterCount"] += 1
                else:
                    summary["directMeterLoadCount"] += len(group_loads)
                groups.append(
                    {
                        "key": f"legacy-meter-{circuit_no}-{meter_id}",
                        "label": f"Måler HC3 {meter_id}",
                        "type": group_type,
                        "meterLabel": "Måler fra eldre lastdata",
                        "meterDbId": None,
                        "meterId": None,
                        "fibaroMeterId": meter_id,
                        "meterType": None,
                        "area": None,
                        "active": True,
                        "note": "Automatisk gruppert fra fibaro_meter_id på last.",
                        "loadCount": len(group_loads),
                        "expectedPowerW": sum(float_or_zero(row.expected_power_w) for row in group_loads),
                        "loads": [energy_load_hierarchy_item(row) for row in sorted(group_loads, key=lambda item: item.name or "")],
                    }
                )

            if direct_without_meter:
                summary["directMeterLoadCount"] += len(direct_without_meter)
                groups.append(
                    {
                        "key": "direct-without-meter-id",
                        "label": "Målt uten registrert målepunkt",
                        "type": "direct_meter",
                        "meterLabel": "Direktemålt",
                        "meterId": None,
                        "meterDbId": None,
                        "fibaroMeterId": None,
                        "loadCount": len(direct_without_meter),
                        "expectedPowerW": sum(float_or_zero(row.expected_power_w) for row in direct_without_meter),
                        "loads": [energy_load_hierarchy_item(row) for row in sorted(direct_without_meter, key=lambda item: item.name or "")],
                    }
                )

            if unmeasured_loads:
                summary["unmeteredLoadCount"] += len(unmeasured_loads)
                groups.append(
                    {
                        "key": "unmetered",
                        "label": "Direkte på kurs",
                        "type": "unmetered",
                        "meterLabel": "Ingen måler",
                        "meterId": None,
                        "meterDbId": None,
                        "fibaroMeterId": None,
                        "loadCount": len(unmeasured_loads),
                        "expectedPowerW": sum(float_or_zero(row.expected_power_w) for row in unmeasured_loads),
                        "loads": [energy_load_hierarchy_item(row) for row in sorted(unmeasured_loads, key=lambda item: item.name or "")],
                    }
                )

            measured_load_count = sum(len(group["loads"]) for group in groups if group["type"] != "unmetered")
            unmeasured_load_count = len(unmeasured_loads)
            if not active_loads:
                if active_meters:
                    return groups, "Måler klar", "Kurs -> måler. Legg laster under måleren når de er kartlagt.", measured_load_count, unmeasured_load_count, expected_power
                return groups, "Ingen aktive laster", "Kurset har ingen aktive laster registrert.", measured_load_count, unmeasured_load_count, expected_power
            if unmeasured_load_count and measured_load_count:
                return groups, "Delvis målt", "Kurs -> målere -> laster, pluss laster direkte på kurs uten måler.", measured_load_count, unmeasured_load_count, expected_power
            if measured_load_count:
                return groups, "Målt", "Kurs -> måler(e) -> laster.", measured_load_count, unmeasured_load_count, expected_power
            return groups, "Ikke målt", "Kurs -> laster direkte på kurs uten registrert energimåler.", measured_load_count, unmeasured_load_count, expected_power

        for circuit in circuits:
            circuit_loads = loads_by_circuit.get(circuit.circuit_no, [])
            circuit_meters = meters_by_circuit.get(circuit.circuit_no, [])
            groups, mode, detail, measured_count, unmeasured_count, expected_power = make_groups(circuit.circuit_no, circuit_loads, circuit_meters)
            circuit_rows.append(
                {
                    "key": f"circuit-{circuit.circuit_no}",
                    "circuitNo": circuit.circuit_no,
                    "description": circuit.description,
                    "breaker": f"{circuit.breaker_rating_a:g} A" if circuit.breaker_rating_a is not None else None,
                    "breakerType": circuit.breaker_type,
                    "status": circuit.status,
                    "isSunbed": bool(circuit.is_sunbed),
                    "note": circuit.note,
                    "loadCount": len(circuit_loads),
                    "activeLoadCount": sum(1 for row in circuit_loads if row.active is not False),
                    "expectedPowerW": expected_power,
                    "measuredLoadCount": measured_count,
                    "unmeasuredLoadCount": unmeasured_count,
                    "measurementMode": mode,
                    "measurementDetail": detail,
                    "measurementGroups": groups,
                }
            )

        unassigned_loads = [
            row for circuit_no, grouped_loads in loads_by_circuit.items()
            if circuit_no is None or circuit_no not in known_circuit_numbers
            for row in grouped_loads
        ]
        unassigned_meters = [
            row for circuit_no, grouped_meters in meters_by_circuit.items()
            if circuit_no is None or circuit_no not in known_circuit_numbers
            for row in grouped_meters
        ]
        if unassigned_loads or unassigned_meters:
            groups, mode, detail, measured_count, unmeasured_count, expected_power = make_groups(None, unassigned_loads, unassigned_meters)
            circuit_rows.append(
                {
                    "key": "unassigned",
                    "circuitNo": None,
                    "description": "Uten gyldig kurs",
                    "breaker": None,
                    "breakerType": None,
                    "status": "Mangler kurskobling",
                    "isSunbed": False,
                    "note": "Laster og målere som mangler kursnummer eller peker på en kurs som ikke finnes.",
                    "loadCount": len(unassigned_loads),
                    "activeLoadCount": sum(1 for row in unassigned_loads if row.active is not False),
                    "expectedPowerW": expected_power,
                    "measuredLoadCount": measured_count,
                    "unmeasuredLoadCount": unmeasured_count,
                    "measurementMode": mode,
                    "measurementDetail": detail,
                    "measurementGroups": groups,
                }
            )

        circuit_rows.sort(key=lambda row: (row["circuitNo"] is None, row["circuitNo"] or 9999))
        return {"summary": summary, "circuits": circuit_rows}

    def default_energy_node_name(circuit_no: Optional[int], hc3_power_device_id: Optional[int], loads: list[EnergyLoad]) -> str:
        prefix = f"K{circuit_no} " if circuit_no is not None else ""
        if hc3_power_device_id is not None:
            if len(loads) == 1 and loads[0].name:
                return f"{prefix}HC3 {hc3_power_device_id} - {loads[0].name}"
            return f"{prefix}HC3 {hc3_power_device_id}"
        return f"{prefix}Tilkoblingspunkt".strip()

    async def ensure_energy_node_backfill(session) -> Dict[str, int]:
        ENERGY_ACCUMULATED_ID_BY_POWER_ID = dependencies.ENERGY_ACCUMULATED_ID_BY_POWER_ID
        ENERGY_AGGREGATE_GROUP_BY_POWER_ID = dependencies.ENERGY_AGGREGATE_GROUP_BY_POWER_ID
        nodes = (await session.execute(select(EnergyNode))).scalars().all()
        now_value = datetime.utcnow()
        updated = 0
        for node in nodes:
            changed = False
            if node.circuit_no == 29 and node.hc3_power_device_id == 398:
                node.hc3_power_device_id = 399
                changed = True
            if node.circuit_no == 29 and node.hc3_power_device_id == 399:
                if node.hc3_switch_device_id == 84:
                    node.hc3_switch_device_id = None
                    node.has_switch = False
                    changed = True
                if node.source == "backfill" and node.name and "HC3 398" in node.name:
                    node.name = node.name.replace("HC3 398", "HC3 399")
                    changed = True
            power_id = int(node.hc3_power_device_id) if node.hc3_power_device_id is not None else None
            if power_id is not None:
                expected_energy_id = ENERGY_ACCUMULATED_ID_BY_POWER_ID.get(power_id)
                expected_group_key = ENERGY_AGGREGATE_GROUP_BY_POWER_ID.get(power_id)
                if node.hc3_energy_device_id is None and expected_energy_id is not None:
                    node.hc3_energy_device_id = expected_energy_id
                    changed = True
                if node.aggregate_group_key is None and expected_group_key is not None:
                    node.aggregate_group_key = expected_group_key
                    changed = True
            if changed:
                node.updated_at = now_value
                updated += 1
        node_by_id = {row.id: row for row in nodes if row.id is not None}
        node_by_key = {
            (row.circuit_no, int(row.hc3_power_device_id)): row
            for row in nodes
            if row.hc3_power_device_id is not None
        }
        loads = (
            await session.execute(
                select(EnergyLoad)
                .where(or_(EnergyLoad.fibaro_meter_id.isnot(None), EnergyLoad.energy_node_id.isnot(None)))
                .order_by(EnergyLoad.circuit_no.asc(), EnergyLoad.name.asc())
            )
        ).scalars().all()
        created = 0
        linked = 0
        grouped: Dict[tuple[Optional[int], int], list[EnergyLoad]] = defaultdict(list)
        for load in loads:
            if load.energy_node_id is not None and load.energy_node_id in node_by_id:
                node = node_by_id[load.energy_node_id]
                if load.fibaro_meter_id is None and node.hc3_power_device_id is not None:
                    load.fibaro_meter_id = node.hc3_power_device_id
                elif node.circuit_no == 29 and node.hc3_power_device_id == 399 and load.fibaro_meter_id == 398:
                    load.fibaro_meter_id = 399
                continue
            if load.fibaro_meter_id is not None:
                grouped[(load.circuit_no, int(load.fibaro_meter_id))].append(load)

        for key, group_loads in grouped.items():
            circuit_no, hc3_power_device_id = key
            node = node_by_key.get(key)
            if node is None:
                device_ids = {row.fibaro_device_id for row in group_loads if row.fibaro_device_id is not None}
                switch_ids = {row.zwave_switch_id for row in group_loads if row.zwave_switch_id is not None}
                node = EnergyNode(
                    name=default_energy_node_name(circuit_no, hc3_power_device_id, group_loads),
                    circuit_no=circuit_no,
                    node_type="zwave_device",
                    hc3_device_id=next(iter(device_ids)) if len(device_ids) == 1 else None,
                    hc3_power_device_id=hc3_power_device_id,
                    hc3_energy_device_id=ENERGY_ACCUMULATED_ID_BY_POWER_ID.get(hc3_power_device_id),
                    hc3_switch_device_id=next(iter(switch_ids)) if len(switch_ids) == 1 else None,
                    aggregate_group_key=ENERGY_AGGREGATE_GROUP_BY_POWER_ID.get(hc3_power_device_id),
                    has_meter=True,
                    has_switch=bool(switch_ids),
                    active=True,
                    source="backfill",
                    created_at=now_value,
                    updated_at=now_value,
                )
                session.add(node)
                await session.flush()
                node_by_key[key] = node
                node_by_id[node.id] = node
                created += 1
            for load in group_loads:
                if load.energy_node_id != node.id:
                    load.energy_node_id = node.id
                    linked += 1
        return {"created": created, "linked": linked, "updated": updated}

    def build_energy_circuit_loads_payload(
        circuits: list[EnergyCircuit],
        loads: list[EnergyLoad],
        nodes: Optional[list[EnergyNode]] = None,
    ) -> Dict[str, Any]:
        ENERGY_AGGREGATE_HC3_MEMBERS = dependencies.ENERGY_AGGREGATE_HC3_MEMBERS
        ENERGY_AGGREGATE_METERS = dependencies.ENERGY_AGGREGATE_METERS
        ENERGY_AGGREGATE_METERS_BY_KEY = dependencies.ENERGY_AGGREGATE_METERS_BY_KEY
        nodes = nodes or []
        aggregate_counts = {
            group["key"]: sum(
                1
                for node in nodes
                if node.active is not False and node.aggregate_group_key == group["key"]
            )
            for group in ENERGY_AGGREGATE_METERS
        }
        aggregate_meters = [
            {
                **group,
                "mappedNodeCount": aggregate_counts[group["key"]],
                "memberPowerIds": list(ENERGY_AGGREGATE_HC3_MEMBERS.get(group["key"], ())),
            }
            for group in ENERGY_AGGREGATE_METERS
        ]
        loads_by_circuit: Dict[Optional[int], list[EnergyLoad]] = defaultdict(list)
        nodes_by_circuit: Dict[Optional[int], list[EnergyNode]] = defaultdict(list)
        for load in loads:
            loads_by_circuit[load.circuit_no].append(load)
        for node in nodes:
            nodes_by_circuit[node.circuit_no].append(node)

        known_circuit_numbers = {row.circuit_no for row in circuits if row.circuit_no is not None}

        def circuit_payload(circuit: Optional[EnergyCircuit], circuit_no: Optional[int]) -> Dict[str, Any]:
            circuit_loads = loads_by_circuit.get(circuit_no, [])
            circuit_nodes = nodes_by_circuit.get(circuit_no, [])
            node_by_id = {row.id: row for row in circuit_nodes if row.id is not None}
            loads_by_node: Dict[int, list[EnergyLoad]] = defaultdict(list)
            direct_loads: list[EnergyLoad] = []
            for load in circuit_loads:
                if load.energy_node_id is not None and load.energy_node_id in node_by_id:
                    loads_by_node[int(load.energy_node_id)].append(load)
                else:
                    direct_loads.append(load)

            children_by_parent: Dict[int, list[EnergyNode]] = defaultdict(list)
            roots: list[EnergyNode] = []
            for node in circuit_nodes:
                if node.parent_node_id is not None and node.parent_node_id in node_by_id and node.parent_node_id != node.id:
                    children_by_parent[int(node.parent_node_id)].append(node)
                else:
                    roots.append(node)

            def node_has_measurement(node_id: Optional[int]) -> bool:
                seen: set[int] = set()
                current_id = node_id
                while current_id is not None and current_id in node_by_id and current_id not in seen:
                    seen.add(current_id)
                    current = node_by_id[current_id]
                    if current.active is not False and (current.has_meter or current.hc3_power_device_id is not None):
                        return True
                    current_id = current.parent_node_id
                return False

            def serialize_node(node: EnergyNode, ancestors: Optional[set[int]] = None) -> Dict[str, Any]:
                ancestors = set(ancestors or set())
                node_id = int(node.id or 0)
                cycle = node_id in ancestors
                ancestors.add(node_id)
                own_loads = sorted(loads_by_node.get(node_id, []), key=lambda item: (item.active is False, item.name or ""))
                child_rows = [] if cycle else [
                    serialize_node(child, ancestors)
                    for child in sorted(children_by_parent.get(node_id, []), key=lambda item: (item.name or "", item.id or 0))
                ]
                own_expected = sum(float_or_zero(row.expected_power_w) for row in own_loads if row.active is not False)
                total_expected = own_expected + sum(float_or_zero(row.get("expectedPowerW")) for row in child_rows)
                active_own_loads = sum(1 for row in own_loads if row.active is not False)
                total_active_loads = active_own_loads + sum(int(row.get("activeLoadCount") or 0) for row in child_rows)
                return {
                    "id": node.id,
                    "name": node.name,
                    "circuitNo": node.circuit_no,
                    "parentNodeId": node.parent_node_id,
                    "nodeType": node.node_type or "zwave_device",
                    "manufacturer": node.manufacturer,
                    "model": node.model,
                    "deviceType": node.device_type,
                    "hc3DeviceId": node.hc3_device_id,
                    "hc3PowerDeviceId": node.hc3_power_device_id,
                    "hc3EnergyDeviceId": node.hc3_energy_device_id,
                    "hc3SwitchDeviceId": node.hc3_switch_device_id,
                    "aggregateGroupKey": node.aggregate_group_key,
                    "aggregateMeter": ENERGY_AGGREGATE_METERS_BY_KEY.get(node.aggregate_group_key),
                    "endpointKey": node.endpoint_key,
                    "hasMeter": bool(node.has_meter or node.hc3_power_device_id is not None),
                    "hasSwitch": bool(node.has_switch or node.hc3_switch_device_id is not None),
                    "area": node.area,
                    "active": node.active is not False,
                    "note": node.note,
                    "loadCount": len(own_loads),
                    "activeLoadCount": total_active_loads,
                    "expectedPowerW": total_expected,
                    "currentPowerW": None,
                    "switchState": None,
                    "liveStatus": "pending" if node.active is not False else "inactive",
                    "liveCheckedAt": None,
                    "topologyWarning": "Syklus i tilkoblingsstrukturen" if cycle else None,
                    "loads": [energy_load_hierarchy_item(row) for row in own_loads],
                    "children": child_rows,
                }

            active_loads = [row for row in circuit_loads if row.active is not False]
            measured_load_count = sum(
                1
                for row in active_loads
                if node_has_measurement(row.energy_node_id) or row.fibaro_meter_id is not None or bool(row.measured_direct)
            )
            unmeasured_load_count = max(0, len(active_loads) - measured_load_count)
            expected_power = sum(float_or_zero(row.expected_power_w) for row in active_loads)
            node_rows = [serialize_node(row) for row in sorted(roots, key=lambda item: (item.name or "", item.id or 0))]
            if not active_loads and circuit_nodes:
                measurement_mode = "Enheter klare"
                measurement_detail = "Kurset har registrerte enheter, men ingen aktive laster."
            elif not active_loads:
                measurement_mode = "Ikke kartlagt"
                measurement_detail = "Kurset har ingen registrerte enheter eller aktive laster."
            elif measured_load_count == len(active_loads):
                measurement_mode = "Målt"
                measurement_detail = "Alle aktive laster ligger på eller under et målepunkt."
            elif measured_load_count:
                measurement_mode = "Delvis målt"
                measurement_detail = f"{measured_load_count} av {len(active_loads)} aktive laster har måledekning."
            else:
                measurement_mode = "Ikke målt"
                measurement_detail = "Aktive laster mangler målepunkt i strukturen."
            return {
                "key": f"circuit-{circuit_no}" if circuit_no is not None else "unassigned",
                "circuitNo": circuit_no,
                "description": circuit.description if circuit else "Uten gyldig kurs",
                "breaker": f"{circuit.breaker_rating_a:g} A" if circuit and circuit.breaker_rating_a is not None else None,
                "breakerType": circuit.breaker_type if circuit else None,
                "status": circuit.status if circuit else "Mangler kurskobling",
                "isSunbed": bool(circuit.is_sunbed) if circuit else False,
                "note": circuit.note if circuit else "Laster eller enheter mangler gyldig kurskobling.",
                "loadCount": len(circuit_loads),
                "activeLoadCount": len(active_loads),
                "nodeCount": len(circuit_nodes),
                "expectedPowerW": expected_power,
                "currentPowerW": None,
                "measuredLoadCount": measured_load_count,
                "unmeasuredLoadCount": unmeasured_load_count,
                "measurementMode": measurement_mode,
                "measurementDetail": measurement_detail,
                "directLoads": [energy_load_hierarchy_item(row) for row in sorted(direct_loads, key=lambda item: (item.active is False, item.name or ""))],
                "nodes": node_rows,
            }

        circuit_rows = [circuit_payload(row, row.circuit_no) for row in circuits]
        has_unassigned = any(key is None or key not in known_circuit_numbers for key in set(loads_by_circuit) | set(nodes_by_circuit))
        if has_unassigned:
            orphan_loads = [row for key, values in loads_by_circuit.items() if key is None or key not in known_circuit_numbers for row in values]
            orphan_nodes = [row for key, values in nodes_by_circuit.items() if key is None or key not in known_circuit_numbers for row in values]
            loads_by_circuit[None] = orphan_loads
            nodes_by_circuit[None] = orphan_nodes
            circuit_rows.append(circuit_payload(None, None))

        circuit_rows.sort(key=lambda row: (row["circuitNo"] is None, row["circuitNo"] or 9999))
        active_load_count = sum(1 for row in loads if row.active is not False)
        measured_load_count = sum(int(row["measuredLoadCount"]) for row in circuit_rows)
        return {
            "summary": {
                "circuits": len(circuits),
                "loads": len(loads),
                "activeLoads": active_load_count,
                "nodes": len(nodes),
                "expectedPowerW": sum(float_or_zero(row.expected_power_w) for row in loads if row.active is not False),
                "measuredLoadCount": measured_load_count,
                "unmeteredLoadCount": max(0, active_load_count - measured_load_count),
                "circuitMeterCount": sum(1 for row in circuit_rows if row["activeLoadCount"] and row["unmeasuredLoadCount"] == 0),
                "sharedMeterCount": sum(1 for row in nodes if row.active is not False and row.has_meter),
                "directMeterLoadCount": sum(1 for row in loads if row.active is not False and row.measured_direct),
            },
            "aggregateMeters": aggregate_meters,
            "circuits": circuit_rows,
        }

    async def latest_energy_reconciliation_check(session) -> Dict[str, Any]:
        ENERGY_HC3_HOURLY_DISPLAY_OFFSET = dependencies.ENERGY_HC3_HOURLY_DISPLAY_OFFSET
        latest_day = (
            await session.execute(select(func.max(EnergyHourlyConsumption.stat_date)))
        ).scalar_one_or_none()
        if not latest_day:
            return evaluate_reconciliation(
                check_id="energy-elvia-hc3-missing",
                domain="Energi",
                title="Elvia mot HC3",
                actual_label="HC3 realtime",
                actual_value=None,
                reference_label="Elvia",
                reference_value=None,
                unit="kWh",
                detail="Ingen Elvia-timer er importert.",
                path="/energi/elvia-kontroll",
            )

        day_start = datetime.combine(latest_day, time.min)
        day_end = day_start + timedelta(days=1)
        compare_start = day_start + ENERGY_HC3_HOURLY_DISPLAY_OFFSET
        compare_end = day_end + ENERGY_HC3_HOURLY_DISPLAY_OFFSET
        elvia_result = (
            await session.execute(
                select(
                    func.sum(EnergyHourlyConsumption.consumption_kwh),
                    func.count(func.distinct(EnergyHourlyConsumption.hour)),
                    func.max(EnergyHourlyConsumption.measured_at),
                ).where(EnergyHourlyConsumption.stat_date == latest_day)
            )
        ).one()
        hc3_result = (
            await session.execute(
                select(
                    func.sum(EnergyFibaroSample.inntak_delta_kwh),
                    func.count(EnergyFibaroSample.id),
                    func.max(EnergyFibaroSample.bucket_start),
                )
                .where(EnergyFibaroSample.bucket_start >= compare_start)
                .where(EnergyFibaroSample.bucket_start < compare_end)
            )
        ).one()
        elvia_total = parse_settlement_number(elvia_result[0])
        hc3_total = parse_settlement_number(hc3_result[0])
        elvia_hours = int_or_zero(elvia_result[1])
        hc3_samples = int_or_zero(hc3_result[1])
        confidence = min(100.0, round((elvia_hours / 24) * 100, 1)) if elvia_hours else 0.0
        return evaluate_reconciliation(
            check_id=f"energy-elvia-hc3-{latest_day.isoformat()}",
            domain="Energi",
            title="Elvia mot HC3",
            actual_label="HC3 realtime",
            actual_value=hc3_total,
            reference_label="Elvia",
            reference_value=elvia_total,
            unit="kWh",
            period=latest_day.isoformat(),
            absolute_tolerance=1.0,
            percent_tolerance=2.0,
            critical_multiplier=3.0,
            confidence=confidence,
            detail=f"{elvia_hours}/24 Elvia-timer og {hc3_samples} HC3-samples. HC3-delta er tidsjustert -1 time.",
            path=f"/energi/elvia-kontroll?day={latest_day.isoformat()}",
            updated_at=max(
                [value for value in (elvia_result[2], hc3_result[2]) if value is not None],
                default=None,
            ),
        )

    async def energy_elvia_control_module_payload(session, selected_day: date, today: date) -> Dict[str, Any]:
        ENERGY_HC3_HOURLY_DISPLAY_OFFSET = dependencies.ENERGY_HC3_HOURLY_DISPLAY_OFFSET
        ENERGY_REALTIME_MAX_DELTA_SECONDS = dependencies.ENERGY_REALTIME_MAX_DELTA_SECONDS
        api_config_value_rows = dependencies.api_config_value_rows
        api_day_navigation = dependencies.api_day_navigation
        day_start = datetime.combine(selected_day, time.min)
        day_end = day_start + timedelta(days=1)
        compare_start = day_start + ENERGY_HC3_HOURLY_DISPLAY_OFFSET
        compare_end = day_end + ENERGY_HC3_HOURLY_DISPLAY_OFFSET

        latest_hc3 = (
            await session.execute(
                select(EnergyFibaroSample)
                .order_by(EnergyFibaroSample.bucket_start.desc())
                .limit(1)
            )
        ).scalars().first()
        compare_rows = (
            await session.execute(
                select(EnergyFibaroSample)
                .where(EnergyFibaroSample.bucket_start >= compare_start)
                .where(EnergyFibaroSample.bucket_start < compare_end)
                .order_by(EnergyFibaroSample.bucket_start.asc())
            )
        ).scalars().all()
        elvia_rows = (
            await session.execute(
                select(EnergyHourlyConsumption)
                .where(EnergyHourlyConsumption.stat_date == selected_day)
                .order_by(EnergyHourlyConsumption.hour.asc(), EnergyHourlyConsumption.measured_at.asc())
            )
        ).scalars().all()
        latest_elvia = (
            await session.execute(
                select(EnergyHourlyConsumption)
                .order_by(EnergyHourlyConsumption.measured_at.desc())
                .limit(1)
            )
        ).scalars().first()

        hc3_by_hour = {hour: 0.0 for hour in range(24)}
        hc3_samples_by_hour = {hour: 0 for hour in range(24)}
        hc3_valid_samples_by_hour = {hour: 0 for hour in range(24)}
        for row in compare_rows:
            if row.bucket_start is None:
                continue
            display_time = row.bucket_start - ENERGY_HC3_HOURLY_DISPLAY_OFFSET
            if display_time.date() != selected_day:
                continue
            hour = display_time.hour
            delta_value = row.inntak_delta_kwh
            hc3_samples_by_hour[hour] += 1
            if delta_value is not None:
                hc3_valid_samples_by_hour[hour] += 1
                hc3_by_hour[hour] += float_or_zero(delta_value)

        elvia_by_hour = {hour: 0.0 for hour in range(24)}
        elvia_status_by_hour: dict[int, set[str]] = defaultdict(set)
        elvia_present = set()
        for row in elvia_rows:
            if row.hour is None:
                continue
            hour = int(row.hour)
            if hour < 0 or hour > 23:
                continue
            elvia_present.add(hour)
            elvia_by_hour[hour] += float_or_zero(row.consumption_kwh)
            if row.status:
                elvia_status_by_hour[hour].add(str(row.status))
            if row.is_estimated:
                elvia_status_by_hour[hour].add("estimert")

        hourly_rows = []
        hour_labels = []
        hc3_values = []
        elvia_values = []
        diff_values = []
        hc3_cumulative = []
        elvia_cumulative = []
        diff_cumulative = []
        hc3_total = 0.0
        elvia_total = 0.0
        for hour in range(24):
            hour_label = f"{hour:02d}:00"
            hc3_kwh = round(hc3_by_hour[hour], 3)
            elvia_kwh = round(elvia_by_hour[hour], 3)
            diff_kwh = round(hc3_kwh - elvia_kwh, 3)
            diff_percent = round((diff_kwh / elvia_kwh) * 100, 1) if elvia_kwh else None
            hc3_total += hc3_kwh
            elvia_total += elvia_kwh
            hour_labels.append(hour_label)
            hc3_values.append(hc3_kwh)
            elvia_values.append(elvia_kwh if hour in elvia_present else None)
            diff_values.append(diff_kwh if hour in elvia_present or hc3_kwh else None)
            hc3_cumulative.append(round(hc3_total, 3))
            elvia_cumulative.append(round(elvia_total, 3) if hour in elvia_present or elvia_total else None)
            diff_cumulative.append(round(hc3_total - elvia_total, 3) if hour in elvia_present or hc3_total else None)
            status_text = " / ".join(sorted(elvia_status_by_hour[hour])) if hour in elvia_present else "Mangler"
            hourly_rows.append(
                {
                    "hour_label": f"{hour:02d}:00-{(hour + 1) % 24:02d}:00",
                    "hc3_kwh": hc3_kwh,
                    "elvia_kwh": elvia_kwh if hour in elvia_present else None,
                    "diff_kwh": diff_kwh if hour in elvia_present or hc3_kwh else None,
                    "diff_percent": diff_percent,
                    "hc3_samples": hc3_samples_by_hour[hour],
                    "hc3_delta_samples": hc3_valid_samples_by_hour[hour],
                    "elvia_status": status_text,
                }
            )

        hc3_total = round(hc3_total, 3)
        elvia_total = round(elvia_total, 3)
        diff_total = round(hc3_total - elvia_total, 3)
        diff_percent_total = round((diff_total / elvia_total) * 100, 1) if elvia_total else None
        abs_diff = abs(diff_total)
        ok_limit = max(1.0, elvia_total * 0.02)
        has_elvia = bool(elvia_present)
        control_status = "OK" if has_elvia and abs_diff <= ok_limit else "Avvik" if has_elvia else "Mangler Elvia"
        diff_detail = (
            f"{format_signed_short_number(diff_percent_total, 1)} % mot Elvia"
            if diff_percent_total is not None
            else "Mangler Elvia-grunnlag"
        )
        sample_detail = f"{sum(hc3_valid_samples_by_hour.values())}/{sum(hc3_samples_by_hour.values())} samples med delta"
        latest_elvia_detail = (
            f"Siste Elvia-time {format_source_datetime(latest_elvia.measured_at)}"
            if latest_elvia and latest_elvia.measured_at
            else "Ingen Elvia-time importert"
        )

        chart = api_chart(
            f"Elvia mot HC3 {selected_day.strftime('%d.%m.%Y')}",
            hour_labels,
            [
                {"name": "HC3", "data": hc3_values, "type": "bar", "color": "#15803d", "unit": "kWh"},
                {"name": "Elvia", "data": elvia_values, "type": "bar", "color": "#5b6b84", "unit": "kWh"},
                {"name": "Avvik", "data": diff_values, "type": "line", "color": "#dc2626", "unit": "kWh", "smooth": False},
            ],
            "HC3 er beregnet fra hovedinntakets effektkanal (enhet 221) i samme lokale klokktime som Elvia.",
            "bar",
            430,
            metrics=[
                {
                    "key": "hourly",
                    "label": "Per time",
                    "unit": "kWh",
                    "series": [
                        {"name": "HC3", "data": hc3_values, "type": "bar", "color": "#15803d", "unit": "kWh"},
                        {"name": "Elvia", "data": elvia_values, "type": "bar", "color": "#5b6b84", "unit": "kWh"},
                        {"name": "Avvik", "data": diff_values, "type": "line", "color": "#dc2626", "unit": "kWh", "smooth": False},
                    ],
                },
                {
                    "key": "cumulative",
                    "label": "Akkumulert",
                    "unit": "kWh",
                    "series": [
                        {"name": "HC3 akk.", "data": hc3_cumulative, "type": "line", "color": "#15803d", "unit": "kWh", "smooth": False},
                        {"name": "Elvia akk.", "data": elvia_cumulative, "type": "line", "color": "#5b6b84", "unit": "kWh", "smooth": False},
                        {"name": "Avvik akk.", "data": diff_cumulative, "type": "line", "color": "#dc2626", "unit": "kWh", "smooth": False},
                    ],
                },
            ],
            default_metric="hourly",
            disable_zoom=True,
        )

        return {
            "title": v2_module_title("energi", "elvia-kontroll"),
            "subtitle": "Kontroll av Elvia-timesforbruk mot hovedinntakets effektmåler i HC3.",
            "cards": [
                api_card("HC3 valgt dag", format_short_number(hc3_total, 1), "kWh", sample_detail, "energy", href="/energi/status"),
                api_card("Elvia valgt dag", format_short_number(elvia_total, 1), "kWh", f"{len(elvia_present)}/24 timer importert", "status", href="/energi/elvia"),
                api_card("Avvik", format_signed_short_number(diff_total, 1), "kWh", diff_detail, "energy" if control_status == "OK" else "status", href="/energi/elvia-kontroll"),
                api_card("Status", control_status, "", latest_elvia_detail, "energy" if control_status == "OK" else "status", href="/energi/elvia-kontroll"),
                api_card("Målegrunnlag", "Inntak - R", "", "HC3 221 · 30 s effektmåling", "status", href="/energi/status"),
            ],
            "charts": [chart],
            "tables": [
                api_table(
                    "Timekontroll",
                    ["hour_label", "hc3_kwh", "elvia_kwh", "diff_kwh", "diff_percent", "hc3_samples", "hc3_delta_samples", "elvia_status"],
                    hourly_rows,
                ),
                api_table(
                    "Kontrollgrunnlag",
                    ["key", "value"],
                    api_config_value_rows(
                        {
                            "valgt_dag": selected_day.isoformat(),
                            "hc3_periode_fra": compare_start,
                            "hc3_periode_til": compare_end,
                            "elvia_dato": selected_day.isoformat(),
                            "delta_kilde": "HC3 221 Inntak - R (realtime_w)",
                            "maks_intervall_sek": ENERGY_REALTIME_MAX_DELTA_SECONDS,
                            "timeforskyvning": "Ingen; samme lokale klokktime",
                            "siste_hc3_sample": latest_hc3.bucket_start if latest_hc3 else None,
                            "siste_elvia_time": latest_elvia.measured_at if latest_elvia else None,
                        }
                    ),
                ),
            ],
            "filters": [],
            "dayNavigation": api_day_navigation(selected_day, today),
            "energyElvia": None,
            "energySunbeds": None,
        }

    async def energy_elvia_module_payload(session) -> Dict[str, Any]:
        get_energy_summaries = dependencies.get_energy_summaries
        elvia_rows = (
            await session.execute(
                select(EnergyHourlyConsumption)
                .order_by(EnergyHourlyConsumption.measured_at.desc())
                .limit(120)
            )
        ).scalars().all()
        elvia_imports = (
            await session.execute(
                select(EnergyImportRun)
                .order_by(EnergyImportRun.timestamp.desc())
                .limit(80)
            )
        ).scalars().all()
        summaries = await get_energy_summaries(session)
        elvia_status = (
            await session.execute(
                select(ImportJobStatus)
                .where(ImportJobStatus.job_name == "elvia_monthly_import")
            )
        ).scalars().first()
        energy_elvia_data = api_energy_elvia_payload(
            summaries,
            elvia_imports,
            elvia_rows,
            elvia_status,
        )
        total = summaries.get("total") or {}
        latest_import = elvia_imports[0] if elvia_imports else None
        period_detail = "-"
        if summaries.get("first_at") and summaries.get("last_at"):
            period_detail = (
                f"{format_local_datetime(summaries['first_at'])} - "
                f"{format_local_datetime(summaries['last_at'])}"
            )
        latest_detail = "Ingen import ennå"
        if latest_import:
            latest_period = format_source_datetime(latest_import.period_last) if latest_import.period_last else "-"
            latest_detail = f"Data til {latest_period}"
        return {
            "title": v2_module_title("energi", "elvia"),
            "subtitle": "Elvia-timesdata, importhistorikk og kontrollgrunnlag.",
            "cards": [
                api_card("Totalt forbruk", format_short_number(total.get("consumption_kwh")), "kWh", f"{int_or_zero(total.get('hours_count'))} timer", "energy", href="/energi/elvia"),
                api_card("Periode", int_or_zero(total.get("days_count")), "dager", period_detail, "energy", href="/energi/elvia"),
                api_card("Estimerte timer", int_or_zero(total.get("estimated_hours_count")), "stk", "Elvia-status ulik OK", "status", href="/energi/elvia"),
                api_card("Siste import", format_local_datetime(latest_import.timestamp) if latest_import else "-", "", latest_detail, "status", href="/energi/elvia"),
            ],
            "charts": [],
            "tables": [],
            "filters": [],
            "energyElvia": energy_elvia_data,
            "energySunbeds": None,
        }

    async def validate_energy_node_parent(
        session,
        circuit_no: Optional[int],
        parent_node_id: Optional[int],
        node_id: Optional[int] = None,
    ) -> Optional[EnergyNode]:
        if parent_node_id is None:
            return None
        parent = await session.get(EnergyNode, int(parent_node_id))
        if not parent:
            raise HTTPException(status_code=404, detail="Overordnet enhet finnes ikke.")
        if parent.circuit_no != circuit_no:
            raise HTTPException(status_code=400, detail="Overordnet enhet må ligge på samme kurs.")
        seen: set[int] = set()
        current = parent
        while current is not None and current.id is not None and current.id not in seen:
            if node_id is not None and int(current.id) == int(node_id):
                raise HTTPException(status_code=400, detail="En enhet kan ikke ligge under seg selv eller en av sine underenheter.")
            seen.add(int(current.id))
            current = await session.get(EnergyNode, int(current.parent_node_id)) if current.parent_node_id is not None else None
        return parent

    def clean_energy_node_values(values: Dict[str, Any]) -> Dict[str, Any]:
        ENERGY_AGGREGATE_METERS_BY_KEY = dependencies.ENERGY_AGGREGATE_METERS_BY_KEY
        ENERGY_NODE_TYPES = dependencies.ENERGY_NODE_TYPES
        cleaned = dict(values)
        text_fields = {
            "name", "node_type", "manufacturer", "model", "device_type",
            "endpoint_key", "aggregate_group_key", "area", "note",
        }
        number_fields = {
            "circuit_no", "parent_node_id", "hc3_device_id", "hc3_power_device_id",
            "hc3_energy_device_id", "hc3_switch_device_id",
        }
        for key in text_fields:
            if key in cleaned:
                cleaned[key] = str(cleaned.get(key) or "").strip() or None
        for key in number_fields:
            if cleaned.get(key) is not None:
                cleaned[key] = int(cleaned[key])
        if "node_type" in cleaned and cleaned.get("node_type") is not None:
            node_type = str(cleaned["node_type"]).strip().lower()
            node_type = {"zwave_point": "zwave_device"}.get(node_type, node_type)
            if node_type not in ENERGY_NODE_TYPES:
                raise HTTPException(status_code=400, detail="Ugyldig type tilkoblingspunkt.")
            cleaned["node_type"] = node_type
        if cleaned.get("hc3_power_device_id") is not None and "has_meter" not in cleaned:
            cleaned["has_meter"] = True
        if cleaned.get("hc3_switch_device_id") is not None and "has_switch" not in cleaned:
            cleaned["has_switch"] = True
        aggregate_group_key = cleaned.get("aggregate_group_key")
        if aggregate_group_key is not None and aggregate_group_key not in ENERGY_AGGREGATE_METERS_BY_KEY:
            raise HTTPException(status_code=400, detail="Ugyldig HC3-samlemåler.")
        return cleaned

    def validate_energy_node_profile_values(values: Dict[str, Any]) -> None:
        node_type = str(values.get("node_type") or "zwave_device")
        if node_type in {"output", "child_device"} and values.get("parent_node_id") is None:
            label = "Utgang" if node_type == "output" else "Underenhet"
            raise HTTPException(status_code=400, detail=f"{label} må ha en overordnet enhet.")
        if node_type == "output" and not str(values.get("endpoint_key") or "").strip():
            raise HTTPException(status_code=400, detail="Utgang må ha kanal eller utgangsnummer.")
        if node_type == "meter" and values.get("hc3_power_device_id") is None:
            raise HTTPException(status_code=400, detail="Målepunkt må kobles til en HC3-enhet som rapporterer watt.")

    def clean_energy_load_values(values: Dict[str, Any]) -> Dict[str, Any]:
        ENERGY_LOAD_POWER_PROFILES = dependencies.ENERGY_LOAD_POWER_PROFILES
        cleaned = dict(values)
        for key in ("name", "load_type", "area", "note"):
            if key in cleaned:
                cleaned[key] = str(cleaned.get(key) or "").strip() or None
        if "power_profile" in cleaned:
            profile = str(cleaned.get("power_profile") or "unknown").strip().lower()
            if profile not in ENERGY_LOAD_POWER_PROFILES:
                raise HTTPException(status_code=400, detail="Effektprofil må være ukjent, fast eller variabel.")
            cleaned["power_profile"] = profile
        for key in ("expected_power_w", "min_power_w", "max_power_w"):
            if key not in cleaned or cleaned.get(key) is None:
                continue
            value = float(cleaned[key])
            if value < 0:
                raise HTTPException(status_code=400, detail="Effektverdier kan ikke være negative.")
            cleaned[key] = value
        return cleaned

    def validate_energy_load_power_values(values: Dict[str, Any], existing: Optional[EnergyLoad] = None) -> Dict[str, Any]:
        profile_was_provided = "power_profile" in values
        profile = values.get("power_profile", existing.power_profile if existing else None)
        expected = values.get("expected_power_w", existing.expected_power_w if existing else None)
        minimum = values.get("min_power_w", existing.min_power_w if existing else None)
        maximum = values.get("max_power_w", existing.max_power_w if existing else None)
        if not profile or (
            not profile_was_provided
            and profile == "unknown"
            and "expected_power_w" in values
            and expected is not None
            and minimum is None
            and maximum is None
        ):
            profile = "fixed" if expected is not None else "unknown"
            values["power_profile"] = profile
        if profile == "unknown" and profile_was_provided:
            expected = minimum = maximum = None
            values.update(expected_power_w=None, min_power_w=None, max_power_w=None)
        elif profile == "fixed" and profile_was_provided:
            minimum = maximum = None
            values.update(min_power_w=None, max_power_w=None)
        if minimum is not None and maximum is not None and minimum > maximum:
            raise HTTPException(status_code=400, detail="Minimum effekt kan ikke være høyere enn maksimum effekt.")
        if profile == "fixed" and expected is None:
            raise HTTPException(status_code=400, detail="Fast last må ha en registrert effekt.")
        if profile == "variable" and minimum is None and expected is None and maximum is None:
            raise HTTPException(status_code=400, detail="Variabel last må ha minst én effektverdi.")
        if expected is not None and minimum is not None and expected < minimum:
            raise HTTPException(status_code=400, detail="Normal effekt kan ikke være lavere enn minimum effekt.")
        if expected is not None and maximum is not None and expected > maximum:
            raise HTTPException(status_code=400, detail="Normal effekt kan ikke være høyere enn maksimum effekt.")
        return values

    def energy_node_branch_ids(nodes: Iterable[EnergyNode], root_id: int) -> set[int]:
        children_by_parent: Dict[int, list[int]] = defaultdict(list)
        for candidate in nodes:
            if candidate.id is None or candidate.parent_node_id is None:
                continue
            children_by_parent[int(candidate.parent_node_id)].append(int(candidate.id))
        branch_ids = {int(root_id)}
        pending = [int(root_id)]
        while pending:
            current_id = pending.pop()
            for child_id in children_by_parent.get(current_id, []):
                if child_id in branch_ids:
                    continue
                branch_ids.add(child_id)
                pending.append(child_id)
        return branch_ids

    def energy_node_from_values(values: Dict[str, Any], name: str, now_value: datetime) -> EnergyNode:
        power_id = values.get("hc3_power_device_id")
        switch_id = values.get("hc3_switch_device_id")
        return EnergyNode(
            name=name,
            circuit_no=values.get("circuit_no"),
            parent_node_id=values.get("parent_node_id"),
            node_type=str(values.get("node_type") or "zwave_device").strip() or "zwave_device",
            manufacturer=values.get("manufacturer"),
            model=values.get("model"),
            device_type=values.get("device_type"),
            hc3_device_id=values.get("hc3_device_id"),
            hc3_power_device_id=power_id,
            hc3_energy_device_id=values.get("hc3_energy_device_id"),
            hc3_switch_device_id=switch_id,
            aggregate_group_key=values.get("aggregate_group_key"),
            endpoint_key=values.get("endpoint_key"),
            has_meter=values.get("has_meter") if values.get("has_meter") is not None else power_id is not None,
            has_switch=values.get("has_switch") if values.get("has_switch") is not None else switch_id is not None,
            area=values.get("area"),
            active=values.get("active") is not False,
            note=values.get("note"),
            source="manual",
            created_at=now_value,
            updated_at=now_value,
        )

    async def validate_energy_node_link_uniqueness(
        session,
        power_id: Optional[int],
        energy_id: Optional[int],
        switch_id: Optional[int],
        node_id: Optional[int] = None,
    ) -> None:
        checks = (
            (EnergyNode.hc3_power_device_id, power_id, "effekt-ID-en"),
            (EnergyNode.hc3_energy_device_id, energy_id, "energi-ID-en"),
            (EnergyNode.hc3_switch_device_id, switch_id, "bryter-ID-en"),
        )
        for column, device_id, label in checks:
            if device_id is None:
                continue
            query = select(EnergyNode).where(column == int(device_id))
            if node_id is not None:
                query = query.where(EnergyNode.id != int(node_id))
            duplicate = (await session.execute(query.limit(1))).scalars().first()
            if duplicate:
                raise HTTPException(
                    status_code=409,
                    detail=f"Tilkoblingspunktet {duplicate.name} bruker allerede denne HC3-{label}.",
                )

    async def validate_energy_node_hc3_values(values: Dict[str, Any]) -> None:
        HC3_ENERGY_LIVE_TIMEOUT_SECONDS = dependencies.HC3_ENERGY_LIVE_TIMEOUT_SECONDS
        hc3_api_is_configured = dependencies.hc3_api_is_configured
        hc3_cached_device_request = dependencies.hc3_cached_device_request
        configured = {
            "hc3_device_id": ("hovedenhet", False, False, False),
            "hc3_power_device_id": ("effektmåler", True, False, False),
            "hc3_energy_device_id": ("energimåler", False, True, False),
            "hc3_switch_device_id": ("bryter", False, False, True),
        }
        selected = {key: int(values[key]) for key in configured if values.get(key) is not None}
        if values.get("has_meter") and values.get("hc3_power_device_id") is None:
            raise HTTPException(status_code=400, detail="Enhet med måling må kobles til en HC3-enhet som rapporterer watt.")
        if values.get("has_switch") and values.get("hc3_switch_device_id") is None:
            raise HTTPException(status_code=400, detail="Enhet med bryter må kobles til en HC3-enhet som rapporterer av/på-status.")
        if not selected:
            return
        if not hc3_api_is_configured():
            raise HTTPException(status_code=503, detail="HC3-tilgang er ikke konfigurert. Koblingen kan ikke kontrolleres.")
        summaries: Dict[int, Dict[str, Any]] = {}
        for device_id in sorted(set(selected.values())):
            try:
                device = await asyncio.to_thread(hc3_cached_device_request, device_id, HC3_ENERGY_LIVE_TIMEOUT_SECONDS)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"HC3-enhet {device_id} kunne ikke kontrolleres: {exc}") from exc
            summaries[device_id] = hc3_energy_device_summary(device)
        for key, device_id in selected.items():
            label, requires_power, requires_energy, requires_switch = configured[key]
            summary = summaries[device_id]
            if requires_power and not summary.get("hasPower"):
                raise HTTPException(status_code=400, detail=f"HC3-enhet {device_id} kan ikke brukes som effektmåler fordi den ikke rapporterer watt.")
            if requires_energy and not summary.get("hasEnergy"):
                raise HTTPException(status_code=400, detail=f"HC3-enhet {device_id} kan ikke brukes som energimåler fordi den ikke rapporterer akkumulert kWh.")
            if requires_switch and not summary.get("hasSwitch"):
                raise HTTPException(status_code=400, detail=f"HC3-enhet {device_id} kan ikke brukes som bryter fordi den ikke rapporterer av/på-status.")
            if summary.get("dead") is True:
                raise HTTPException(status_code=400, detail=f"Valgt HC3-{label} {device_id} er markert som utilgjengelig.")
            if summary.get("enabled") is False:
                raise HTTPException(status_code=400, detail=f"Valgt HC3-{label} {device_id} er deaktivert.")

    async def find_or_create_energy_node_for_load(session, values: Dict[str, Any]) -> Optional[EnergyNode]:
        if "energy_node_id" in values:
            energy_node_id = values.get("energy_node_id")
            if energy_node_id is None:
                return None
            node = await session.get(EnergyNode, int(energy_node_id))
            if not node:
                raise HTTPException(status_code=404, detail="Tilkoblingspunkt ikke funnet.")
            if values.get("circuit_no") is not None and node.circuit_no is not None and int(values["circuit_no"]) != int(node.circuit_no):
                raise HTTPException(status_code=400, detail="Last og tilkoblingspunkt må ligge på samme kurs.")
            values["circuit_no"] = node.circuit_no
            values["measured_direct"] = False
            return node

        legacy_power_id = values.get("fibaro_meter_id")
        if legacy_power_id is None:
            return None
        circuit_no = values.get("circuit_no")
        existing = (
            await session.execute(
                select(EnergyNode)
                .where(EnergyNode.circuit_no == circuit_no)
                .where(EnergyNode.hc3_power_device_id == int(legacy_power_id))
                .limit(1)
            )
        ).scalars().first()
        if existing:
            values["energy_node_id"] = existing.id
            values["measured_direct"] = False
            return existing
        now_value = datetime.utcnow()
        node = EnergyNode(
            name=default_energy_node_name(circuit_no, int(legacy_power_id), []),
            circuit_no=circuit_no,
            node_type="zwave_device",
            hc3_device_id=values.get("fibaro_device_id"),
            hc3_power_device_id=int(legacy_power_id),
            hc3_switch_device_id=values.get("zwave_switch_id"),
            has_meter=True,
            has_switch=values.get("zwave_switch_id") is not None,
            active=True,
            source="load-api-backfill",
            created_at=now_value,
            updated_at=now_value,
        )
        session.add(node)
        await session.flush()
        values["energy_node_id"] = node.id
        values["measured_direct"] = False
        return node

    return {
        "_legacy_energy_circuit_loads_payload": _legacy_energy_circuit_loads_payload,
        "_meter_based_energy_circuit_loads_payload": _meter_based_energy_circuit_loads_payload,
        "accumulated_delta": accumulated_delta,
        "api_energy_circuit_edit": api_energy_circuit_edit,
        "api_energy_elvia_payload": api_energy_elvia_payload,
        "api_energy_load_edit": api_energy_load_edit,
        "api_energy_summary_item": api_energy_summary_item,
        "api_revenue_accumulated_year_chart": api_revenue_accumulated_year_chart,
        "build_energy_circuit_loads_payload": build_energy_circuit_loads_payload,
        "build_sunbed_power_analysis": build_sunbed_power_analysis,
        "calculated_difference": calculated_difference,
        "circuit_row_api": circuit_row_api,
        "clean_energy_load_values": clean_energy_load_values,
        "clean_energy_node_values": clean_energy_node_values,
        "cumulative_energy_points": cumulative_energy_points,
        "cumulative_energy_series": cumulative_energy_series,
        "default_energy_node_name": default_energy_node_name,
        "energy_area_cards": energy_area_cards,
        "energy_elvia_control_module_payload": energy_elvia_control_module_payload,
        "energy_elvia_module_payload": energy_elvia_module_payload,
        "energy_fibaro_sample_payload": energy_fibaro_sample_payload,
        "energy_hour_has_changed": energy_hour_has_changed,
        "energy_load_hierarchy_item": energy_load_hierarchy_item,
        "energy_node_branch_ids": energy_node_branch_ids,
        "energy_node_from_values": energy_node_from_values,
        "energy_sample_bucket": energy_sample_bucket,
        "ensure_energy_node_backfill": ensure_energy_node_backfill,
        "find_or_create_energy_node_for_load": find_or_create_energy_node_for_load,
        "hc3_energy_device_summary": hc3_energy_device_summary,
        "hc3_energy_nodes_live": hc3_energy_nodes_live,
        "ingest_elvia_hours": ingest_elvia_hours,
        "latest_energy_reconciliation_check": latest_energy_reconciliation_check,
        "load_row_api": load_row_api,
        "load_sunbed_power_analysis": load_sunbed_power_analysis,
        "manual_energy_quickapp_report": manual_energy_quickapp_report,
        "payload_weather_symbol": payload_weather_symbol,
        "payload_weather_text": payload_weather_text,
        "percentile": percentile,
        "realtime_power_delta_kwh": realtime_power_delta_kwh,
        "seed_energy_circuits": seed_energy_circuits,
        "sum_optional": sum_optional,
        "sunbed_analysis_date_range": sunbed_analysis_date_range,
        "sunbed_power_cache_warm_worker": sunbed_power_cache_warm_worker,
        "sunbed_session_bounds": sunbed_session_bounds,
        "upsert_energy_fibaro_sample": upsert_energy_fibaro_sample,
        "validate_energy_load_power_values": validate_energy_load_power_values,
        "validate_energy_node_hc3_values": validate_energy_node_hc3_values,
        "validate_energy_node_link_uniqueness": validate_energy_node_link_uniqueness,
        "validate_energy_node_parent": validate_energy_node_parent,
        "validate_energy_node_profile_values": validate_energy_node_profile_values,
    }
