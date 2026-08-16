from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable, Optional

from roborock_domain import (
    roborock_cron_parts,
    roborock_cron_weekdays,
    roborock_error_label,
    roborock_fan_label,
    roborock_mop_label,
    roborock_water_label,
)
from time_formatting import LOCAL_TZ, normalize_local_naive, utc_naive_to_local_naive


REPORT_START = time(22, 0)
REPORT_END = time(8, 0)
REPORT_READY_BY = time(6, 45)
SCHEDULE_EARLY_MATCH_TOLERANCE = timedelta(minutes=45)
SCHEDULE_LATE_MATCH_TOLERANCE = timedelta(minutes=90)
SCHEDULE_ON_TIME_TOLERANCE = timedelta(minutes=10)
SCHEDULE_MISSING_GRACE = timedelta(minutes=20)

WASH_MODE_LABELS = {
    0: "Lett",
    1: "Balansert",
    2: "Dyp",
    8: "Ekstra dyp",
    10: "Smart",
}

DUST_COLLECTION_MODE_LABELS = {
    0: "Smart",
    1: "Skånsom",
    2: "Balansert",
    4: "Maks",
}

NIGHT_WATER_EVENT_FIELDS = {
    "clear_water_status": "Rentvann i dokk",
    "dirty_water_status": "Skittentvann i dokk",
    "water_shortage_status": "Vann i robot",
    "clean_fluid_status": "Rengjøringsmiddel",
    "water_box_filter_status": "Vannfilter",
}

DOCK_STATE_LABELS = {
    8: "Lader i dokk",
    9: "Ladeproblem i dokk",
    22: "Tømmer støvbeholder",
    23: "Vasker mopp",
    25: "Vasker mopp",
    33: "Monterer mopp",
    34: "Tar av mopp",
    100: "Fulladet i dokk",
    202: "Tørker mopp",
}


def report_window(report_day: date) -> dict[str, datetime]:
    return {
        "start": datetime.combine(report_day - timedelta(days=1), REPORT_START),
        "end": datetime.combine(report_day, REPORT_END),
        "ready_by": datetime.combine(report_day, REPORT_READY_BY),
    }


def local_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    local = normalize_local_naive(value)
    return local.replace(tzinfo=LOCAL_TZ).isoformat() if local else None


def local_datetime_value(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return normalize_local_naive(value)
    if isinstance(value, str):
        try:
            return normalize_local_naive(datetime.fromisoformat(value))
        except ValueError:
            return None
    return None


def row_value(row: Any, field: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(field, default)
    return getattr(row, field, default)


def number(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def integer(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def dominant_value(rows: Iterable[Any], field: str) -> Any:
    values = [row_value(row, field) for row in rows if row_value(row, field) is not None]
    return Counter(values).most_common(1)[0][0] if values else None


def nearest_sample(rows: list[Any], target: datetime, *, before: bool) -> Any:
    candidates = []
    for row in rows:
        stamp = normalize_local_naive(row_value(row, "timestamp"))
        if stamp is None or (before and stamp > target) or (not before and stamp < target):
            continue
        candidates.append((abs((stamp - target).total_seconds()), row))
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1] if candidates and candidates[0][0] <= 15 * 60 else None


def probe_raw_value(probes: Iterable[Any], command: str) -> Any:
    probe = next((row for row in probes if row_value(row, "command") == command), None)
    if probe is None or row_value(probe, "ok") is not True:
        return None
    raw = row_value(probe, "raw")
    if not isinstance(raw, dict):
        return None
    return raw.get("value")


def probe_value(probes: Iterable[Any], command: str) -> dict[str, Any]:
    value = probe_raw_value(probes, command)
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def probe_integer(probes: Iterable[Any], command: str) -> Optional[int]:
    value = probe_raw_value(probes, command)
    if isinstance(value, list) and value:
        value = value[0]
    return integer(value)


def wash_settings(probes: Iterable[Any]) -> dict[str, Any]:
    smart = probe_value(probes, "GET_SMART_WASH_PARAMS")
    mode = probe_value(probes, "GET_WASH_TOWEL_MODE")
    interval_seconds = integer(smart.get("wash_interval"))
    mode_value = integer(mode.get("wash_mode"))
    supported = bool(smart or mode)
    return {
        "supported": supported,
        "intervalMinutes": round(interval_seconds / 60) if interval_seconds else None,
        "mode": mode_value,
        "modeLabel": WASH_MODE_LABELS.get(mode_value, f"Modus {mode_value}") if mode_value is not None else None,
        "automatic": integer(smart.get("smart_wash")) not in {None, 0},
    }


def robot_settings(probes: list[Any]) -> dict[str, Any]:
    wash = wash_settings(probes)
    items = []

    def add(key: str, label: str, value: Optional[str]) -> None:
        if value and value != "-":
            items.append({"key": key, "label": label, "value": value})

    fan_power = probe_integer(probes, "GET_CUSTOM_MODE")
    water = probe_value(probes, "GET_WATER_BOX_CUSTOM_MODE")
    water_mode = integer(water.get("water_box_mode"))
    add("fan", "Standard sugekraft", roborock_fan_label(fan_power) if fan_power is not None else None)
    add("water", "Standard vannmengde", roborock_water_label(water_mode) if water_mode is not None else None)

    if wash["supported"]:
        wash_parts = [wash["modeLabel"] or "Moppevask"]
        if wash["intervalMinutes"]:
            wash_parts.append(f"hvert {wash['intervalMinutes']}. min")
        if wash["automatic"]:
            wash_parts.append("automatisk")
        add("mop-wash", "Moppevask", " · ".join(wash_parts))

    dryer = probe_value(probes, "APP_GET_DRYER_SETTING")
    dryer_on = dryer.get("on") if isinstance(dryer.get("on"), dict) else {}
    dry_seconds = integer(dryer_on.get("dry_time"))
    if dry_seconds:
        dry_hours = dry_seconds / 3600
        dry_label = f"{dry_hours:g} t"
        add("dryer", "Tørketid", dry_label)

    dust_switch = probe_value(probes, "GET_DUST_COLLECTION_SWITCH_STATUS")
    dust_mode = probe_value(probes, "GET_DUST_COLLECTION_MODE")
    dust_enabled = integer(dust_switch.get("status"))
    if dust_enabled is not None:
        dust_label = "Av" if dust_enabled == 0 else "På"
        mode_value = integer(dust_mode.get("mode"))
        if dust_enabled and mode_value is not None:
            dust_label += f" · {DUST_COLLECTION_MODE_LABELS.get(mode_value, f'Modus {mode_value}')}"
        add("dust", "Støvtømming", dust_label)

    carpet = probe_value(probes, "GET_CARPET_MODE")
    carpet_enabled = integer(carpet.get("enable"))
    if carpet_enabled is not None:
        add("carpet", "Teppemodus", "På" if carpet_enabled else "Av")

    dnd = probe_value(probes, "GET_DND_TIMER")
    dnd_enabled = integer(dnd.get("enabled"))
    if dnd_enabled is not None:
        dnd_label = "Av"
        if dnd_enabled:
            dnd_label = (
                f"{integer(dnd.get('start_hour')) or 0:02d}:{integer(dnd.get('start_minute')) or 0:02d}–"
                f"{integer(dnd.get('end_hour')) or 0:02d}:{integer(dnd.get('end_minute')) or 0:02d}"
            )
        add("dnd", "Ikke forstyrr", dnd_label)

    return {**wash, "items": items}


def resource_problem(row: Any, provider: str = "roborock") -> bool:
    shortage = integer(row_value(row, "water_shortage_status"))
    if shortage not in {None, 0}:
        return True
    if provider == "dreame":
        clear_name = str(row_value(row, "clear_water_status_name") or "").strip().lower()
        if clear_name:
            return clear_name not in {"okay", "ok", "normal", "installed", "present"}
        return False
    # For Roborock, clear_water_status describes the dock. A dock that becomes
    # empty after a completed job must block future washes, not downgrade the
    # wash that the robot already completed without an internal shortage.
    return False


def build_night_water_events(events: list[Any], window: dict[str, datetime]) -> list[dict[str, Any]]:
    rows = []
    for event in events:
        field_name = str(row_value(event, "field_name") or "")
        if field_name not in NIGHT_WATER_EVENT_FIELDS:
            continue
        timestamp = normalize_local_naive(row_value(event, "timestamp"))
        if timestamp is None or not window["start"] <= timestamp <= window["end"]:
            continue
        severity = str(row_value(event, "severity") or "info").lower()
        rows.append(
            {
                "timestamp": local_iso(timestamp),
                "fieldName": field_name,
                "title": NIGHT_WATER_EVENT_FIELDS[field_name],
                "previousLabel": row_value(event, "previous_label"),
                "currentLabel": row_value(event, "current_label") or row_value(event, "current_value") or "Ukjent",
                "severity": "warning" if severity in {"warning", "critical", "error"} else "ok",
            }
        )
    return sorted(rows, key=lambda row: row["timestamp"] or "")


def job_cleaning_type(fan_power: Any, water_mode: Any, mop_mode: Any) -> tuple[str, str]:
    fan = integer(fan_power)
    water = integer(water_mode)
    mop = integer(mop_mode)
    # Roborock may retain a mop-mode code while water is explicitly off.
    wet = water not in {None, 200}
    vacuum = fan is not None and fan != 105
    if wet and vacuum:
        return "vacuum_mop", "Støvsuging og vask"
    if wet:
        return "mop", "Vask"
    return "vacuum", "Støvsuging"


def dock_state_label(sample: Any, provider: str) -> Optional[str]:
    state_code = integer(row_value(sample, "state_code"))
    if provider == "roborock" and state_code in DOCK_STATE_LABELS:
        return DOCK_STATE_LABELS[state_code]
    if row_value(sample, "is_charging") is True:
        return "Lader i dokk"
    return None


def build_dock_intervals(
    samples: list[Any],
    started_at: datetime,
    ended_at: Optional[datetime],
    provider: str,
) -> list[dict[str, Any]]:
    if ended_at is None:
        ended_at = max(
            (
                stamp
                for row in samples
                if (stamp := normalize_local_naive(row_value(row, "timestamp"))) is not None
            ),
            default=started_at,
        )
    if ended_at <= started_at:
        return []

    points = sorted(
        (
            (stamp, dock_state_label(row, provider))
            for row in samples
            if (stamp := normalize_local_naive(row_value(row, "timestamp"))) is not None
            and started_at <= stamp <= ended_at
        ),
        key=lambda item: item[0],
    )
    intervals: list[dict[str, Any]] = []
    interval_start: Optional[datetime] = None
    interval_label: Optional[str] = None
    for stamp, label in points:
        if label and interval_start is None:
            interval_start = stamp
            interval_label = label
        elif not label and interval_start is not None:
            intervals.append(
                {
                    "startedAt": local_iso(interval_start),
                    "endedAt": local_iso(stamp),
                    "label": interval_label or "I dokk",
                }
            )
            interval_start = None
            interval_label = None
        elif label and interval_start is not None and label != interval_label:
            intervals.append(
                {
                    "startedAt": local_iso(interval_start),
                    "endedAt": local_iso(stamp),
                    "label": interval_label or "I dokk",
                }
            )
            interval_start = stamp
            interval_label = label
    if interval_start is not None:
        intervals.append(
            {
                "startedAt": local_iso(interval_start),
                "endedAt": local_iso(ended_at),
                "label": interval_label or "I dokk",
            }
        )
    return [
        row
        for row in intervals
        if local_datetime_value(row["endedAt"]) > local_datetime_value(row["startedAt"])
    ]


def build_job(job: Any, samples: list[Any], settings: dict[str, Any], provider: str = "roborock") -> dict[str, Any]:
    started_at = utc_naive_to_local_naive(row_value(job, "begin_at"))
    ended_at = utc_naive_to_local_naive(row_value(job, "end_at"))
    if started_at is None:
        raise ValueError("Roborock-jobben mangler starttid")
    job_end = ended_at or started_at + timedelta(hours=4)
    observed = [
        row
        for row in samples
        if (stamp := normalize_local_naive(row_value(row, "timestamp")))
        and started_at - timedelta(minutes=3) <= stamp <= job_end + timedelta(minutes=12)
    ]
    active = [row for row in observed if row_value(row, "in_cleaning") is True]
    mode_rows = active or observed
    fan_power = dominant_value(mode_rows, "fan_power")
    water_mode = dominant_value(mode_rows, "water_box_mode")
    mop_mode = dominant_value(mode_rows, "mop_mode")
    if provider == "dreame":
        cleaning_type, cleaning_type_label = "cleaning", "Rengjøring"
    else:
        cleaning_type, cleaning_type_label = job_cleaning_type(fan_power, water_mode, mop_mode)
    start_sample = nearest_sample(observed, started_at, before=False)
    end_sample = nearest_sample(observed, job_end, before=True)
    interval_samples = [
        row
        for row in observed
        if (stamp := normalize_local_naive(row_value(row, "timestamp")))
        and started_at <= stamp <= job_end
    ]
    active_interval_samples = [row for row in interval_samples if row_value(row, "in_cleaning") is True]
    quality_samples = active_interval_samples or interval_samples
    water_samples = [row for row in quality_samples if resource_problem(row, provider)]
    error_code = integer(row_value(job, "error_code"))
    complete = row_value(job, "complete") is True
    if error_code not in {None, 0} or (ended_at is not None and not complete):
        status, status_label = "error", "Feil"
    elif ended_at is None and not complete:
        status, status_label = "running", "Pågår"
    elif water_samples:
        status, status_label = "warning", "Kontroller"
    else:
        status, status_label = "ok", "Fullført"
    duration_minutes = number(row_value(job, "duration_minutes"))
    if duration_minutes is None:
        duration_minutes = number(row_value(job, "duration_seconds"))
        duration_minutes = duration_minutes / 60 if duration_minutes is not None else None
    wash_count = integer(row_value(job, "wash_count"))
    interval = integer(settings.get("intervalMinutes"))
    expected_washes = None
    if cleaning_type != "vacuum" and duration_minutes and interval:
        expected_washes = max(1, int((duration_minutes + interval - 0.001) // interval))
    rounds = integer(row_value(job, "clean_times")) or 1
    mode_parts = []
    if provider == "dreame":
        mode_parts.append("Rapportert av Dreamehome")
    elif cleaning_type in {"vacuum", "vacuum_mop"}:
        mode_parts.append(roborock_fan_label(fan_power))
    if cleaning_type in {"mop", "vacuum_mop"}:
        mode_parts.extend([roborock_mop_label(mop_mode), f"{roborock_water_label(water_mode).lower()} vannmengde"])
    mode_parts.append(f"{rounds} {'runde' if rounds == 1 else 'runder'}")
    issue_parts = []
    if error_code not in {None, 0}:
        issue_parts.append(roborock_error_label(error_code))
    if ended_at is not None and not complete:
        issue_parts.append("Jobben er ikke markert fullført")
    if water_samples:
        water_at = normalize_local_naive(row_value(water_samples[0], "timestamp"))
        issue_parts.append(f"Vannvarsel kl. {water_at.strftime('%H:%M')}" if water_at else "Vannvarsel")
    else:
        water_at = None
    if cleaning_type == "vacuum":
        water_status, water_status_label = "not_applicable", "Ikke relevant"
    elif water_samples:
        water_status = "warning"
        water_status_label = f"Vannmangel kl. {water_at.strftime('%H:%M')}" if water_at else "Vannmangel"
    elif quality_samples:
        water_status, water_status_label = "ok", "OK"
    else:
        water_status, water_status_label = "unknown", "Ikke mottatt"
    return {
        "recordId": str(row_value(job, "record_id") or row_value(job, "id") or ""),
        "startedAt": local_iso(started_at),
        "endedAt": local_iso(ended_at),
        "durationMinutes": round(duration_minutes, 1) if duration_minutes is not None else None,
        "areaM2": round(number(row_value(job, "cleaned_area_m2")) or number(row_value(job, "area_m2")) or 0, 2),
        "complete": complete,
        "errorCode": error_code,
        "startType": integer(row_value(job, "start_type")),
        "cleaningType": cleaning_type,
        "cleaningTypeLabel": cleaning_type_label,
        "modeLabel": " · ".join(part for part in mode_parts if part and part != "-"),
        "rounds": rounds,
        "batteryStart": integer(row_value(start_sample, "battery")) if start_sample else None,
        "batteryEnd": integer(row_value(end_sample, "battery")) if end_sample else None,
        "dockIntervals": build_dock_intervals(
            interval_samples,
            started_at,
            ended_at,
            provider,
        ),
        "washCount": wash_count,
        "expectedWashCount": expected_washes,
        "waterStatus": water_status,
        "waterStatusLabel": water_status_label,
        "waterWarningAt": local_iso(water_at),
        "status": status,
        "statusLabel": status_label,
        "issues": issue_parts,
    }


def first_full_charge(samples: list[Any], after: Optional[datetime], before: datetime) -> Optional[datetime]:
    if after is None:
        return None
    for row in samples:
        stamp = normalize_local_naive(row_value(row, "timestamp"))
        battery = integer(row_value(row, "battery"))
        if stamp and after <= stamp <= before and battery is not None and battery >= 99 and row_value(row, "is_charging") is True:
            return stamp
    return None


def battery_at(samples: list[Any], target: datetime) -> Optional[int]:
    sample = nearest_sample(samples, target, before=True)
    return integer(row_value(sample, "battery")) if sample else None


def schedule_occurrences(
    schedules: list[Any],
    window: dict[str, datetime],
    provider: str = "roborock",
    include_paused: bool = False,
) -> list[dict[str, Any]]:
    occurrences = []
    current_day = window["start"].date()
    while current_day <= window["end"].date():
        for schedule in schedules:
            enabled = row_value(schedule, "enabled")
            if enabled is not True and not (include_paused and enabled is False):
                continue
            parts = roborock_cron_parts(row_value(schedule, "cron"))
            if not parts:
                continue
            minute, hour, day_field = parts
            if not 0 <= minute <= 59 or not 0 <= hour <= 23:
                continue
            weekdays = roborock_cron_weekdays(day_field)
            if weekdays == set() or (weekdays is not None and current_day.weekday() not in weekdays):
                continue
            scheduled_at = datetime.combine(current_day, time(hour, minute))
            if not window["start"] <= scheduled_at < window["end"]:
                continue
            if provider == "dreame":
                cleaning_type, cleaning_type_label = "cleaning", "Rengjøring"
            else:
                cleaning_type, cleaning_type_label = job_cleaning_type(
                    row_value(schedule, "fan_power"),
                    row_value(schedule, "water_box_mode"),
                    row_value(schedule, "mop_mode"),
                )
            rounds = integer(row_value(schedule, "repeat")) or 1
            mode_parts = []
            if provider == "dreame":
                mode_parts.append("Dreamehome-plan")
            elif cleaning_type in {"vacuum", "vacuum_mop"}:
                mode_parts.append(roborock_fan_label(row_value(schedule, "fan_power")))
            if cleaning_type in {"mop", "vacuum_mop"}:
                mode_parts.extend(
                    [
                        roborock_mop_label(row_value(schedule, "mop_mode")),
                        f"{roborock_water_label(row_value(schedule, 'water_box_mode')).lower()} vannmengde",
                    ]
                )
            mode_parts.append(f"{rounds} {'runde' if rounds == 1 else 'runder'}")
            occurrences.append(
                {
                    "scheduleId": str(row_value(schedule, "schedule_id") or row_value(schedule, "id") or ""),
                    "scheduledAtValue": scheduled_at,
                    "scheduledAt": local_iso(scheduled_at),
                    "cleaningType": cleaning_type,
                    "cleaningTypeLabel": cleaning_type_label,
                    "modeLabel": " · ".join(part for part in mode_parts if part and part != "-"),
                    "paused": enabled is False,
                }
            )
        current_day += timedelta(days=1)
    return sorted(occurrences, key=lambda row: row["scheduledAtValue"])


def schedule_snapshot_occurrences(
    snapshots: list[Any],
    window: dict[str, datetime],
    provider: str = "roborock",
    include_paused: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ordered = sorted(
        (
            (normalize_local_naive(row_value(snapshot, "captured_at")), snapshot)
            for snapshot in snapshots
        ),
        key=lambda item: item[0] or datetime.min,
    )
    ordered = [item for item in ordered if item[0] is not None and item[0] <= window["end"]]
    baseline_index = next(
        (index for index in range(len(ordered) - 1, -1, -1) if ordered[index][0] <= window["start"]),
        None,
    )
    if baseline_index is None:
        return [], {
            "historyAvailable": False,
            "snapshotAt": None,
            "basis": "Planhistorikk er ikke tilgjengelig for denne natten",
        }

    relevant = ordered[baseline_index:]
    occurrences: dict[tuple[str, str], dict[str, Any]] = {}
    for index, (captured_at, snapshot) in enumerate(relevant):
        effective_from = max(window["start"], captured_at)
        next_at = relevant[index + 1][0] if index + 1 < len(relevant) else window["end"]
        effective_to = min(window["end"], next_at)
        if effective_from >= effective_to:
            continue
        snapshot_schedules = row_value(snapshot, "schedules")
        if not isinstance(snapshot_schedules, list):
            continue
        for occurrence in schedule_occurrences(snapshot_schedules, window, provider, include_paused):
            scheduled_at = occurrence["scheduledAtValue"]
            if not effective_from <= scheduled_at < effective_to:
                continue
            key = (occurrence["scheduleId"], occurrence["scheduledAt"])
            occurrences[key] = occurrence

    baseline_at = relevant[0][0]
    return sorted(occurrences.values(), key=lambda row: row["scheduledAtValue"]), {
        "historyAvailable": True,
        "snapshotAt": local_iso(baseline_at),
        "basis": f"Lagret plan som gjaldt fra kl. {baseline_at.strftime('%H:%M')}",
    }


def schedule_job_can_match(job: Any, provider: str) -> bool:
    start_type = integer(row_value(job, "start_type"))
    if provider == "roborock" and start_type is not None:
        return start_type == 3
    return True


def build_schedule_check(
    schedules: list[Any],
    jobs: list[Any],
    samples: list[Any],
    window: dict[str, datetime],
    generated_at: datetime,
    provider: str = "roborock",
    include_paused: bool = False,
    schedule_snapshots: Optional[list[Any]] = None,
    require_history: bool = False,
) -> dict[str, Any]:
    if schedule_snapshots:
        expected, plan_meta = schedule_snapshot_occurrences(
            schedule_snapshots,
            window,
            provider,
            include_paused,
        )
    elif require_history:
        expected, plan_meta = [], {
            "historyAvailable": False,
            "snapshotAt": None,
            "basis": "Planhistorikk er ikke tilgjengelig for denne natten",
        }
    else:
        expected = schedule_occurrences(schedules, window, provider, include_paused)
        plan_meta = {
            "historyAvailable": True,
            "snapshotAt": None,
            "basis": "Gjeldende plan (historikk er ikke etablert ennå)",
        }
    actual_starts = [
        (
            index,
            utc_naive_to_local_naive(row_value(job, "begin_at")),
            str(row_value(job, "record_id") or row_value(job, "id") or ""),
            job,
        )
        for index, job in enumerate(jobs)
        if schedule_job_can_match(job, provider)
    ]
    actual_starts = [row for row in actual_starts if row[1] is not None]
    matched_actual: set[int] = set()
    pairs = sorted(
        (
            (abs((actual_at - occurrence["scheduledAtValue"]).total_seconds()), occurrence_index, actual_index, actual_at, record_id, job)
            for occurrence_index, occurrence in enumerate(expected)
            for actual_index, actual_at, record_id, job in actual_starts
            if not occurrence["paused"]
            if occurrence["scheduledAtValue"] - SCHEDULE_EARLY_MATCH_TOLERANCE
            <= actual_at
            <= occurrence["scheduledAtValue"] + SCHEDULE_LATE_MATCH_TOLERANCE
        ),
        key=lambda row: row[0],
    )
    matched_occurrences: dict[int, tuple[datetime, str, Any]] = {}
    for _, occurrence_index, actual_index, actual_at, record_id, job in pairs:
        if occurrence_index in matched_occurrences or actual_index in matched_actual:
            continue
        matched_occurrences[occurrence_index] = (actual_at, record_id, job)
        matched_actual.add(actual_index)

    rows = []
    for index, occurrence in enumerate(expected):
        scheduled_at = occurrence.pop("scheduledAtValue")
        if occurrence.pop("paused"):
            rows.append(
                {
                    **occurrence,
                    "status": "paused",
                    "statusLabel": "Satt på pause",
                    "actualStartedAt": None,
                    "actualRecordId": None,
                    "delayMinutes": None,
                }
            )
            continue
        match = matched_occurrences.get(index)
        if match:
            actual_at, record_id, actual_job = match
            delay_minutes = round((actual_at - scheduled_at).total_seconds() / 60)
            delayed = abs(actual_at - scheduled_at) > SCHEDULE_ON_TIME_TOLERANCE
            error_code = integer(row_value(actual_job, "error_code"))
            complete = row_value(actual_job, "complete") is True
            ended_at = row_value(actual_job, "end_at")
            if error_code not in {None, 0} or (ended_at is not None and not complete):
                status, status_label = "failed", "Startet, men feilet"
            elif not complete and ended_at is None:
                status, status_label = "running", "Pågår"
            else:
                status = "delayed" if delayed else "completed"
                status_label = f"Startet {delay_minutes:+d} min" if delayed else "Gjennomført"
            rows.append(
                {
                    **occurrence,
                    "status": status,
                    "statusLabel": status_label,
                    "actualStartedAt": local_iso(actual_at),
                    "actualRecordId": record_id,
                    "delayMinutes": delay_minutes,
                }
            )
            continue

        active_near_schedule = any(
            row_value(sample, "in_cleaning") is True
            and (stamp := normalize_local_naive(row_value(sample, "timestamp"))) is not None
            and scheduled_at - timedelta(minutes=5) <= stamp <= scheduled_at + SCHEDULE_LATE_MATCH_TOLERANCE
            for sample in samples
        )
        if active_near_schedule and generated_at <= window["end"]:
            status, status_label = "running", "Pågår"
        elif generated_at < scheduled_at + SCHEDULE_MISSING_GRACE:
            status, status_label = "pending", "Ikke forfalt"
        else:
            status, status_label = "missing", "Ikke registrert"
        rows.append(
            {
                **occurrence,
                "status": status,
                "statusLabel": status_label,
                "actualStartedAt": None,
                "actualRecordId": None,
                "delayMinutes": None,
            }
        )

    paused_count = sum(row["status"] == "paused" for row in rows)
    return {
        **plan_meta,
        "jobs": rows,
        "matchedRecordIds": sorted(
            row["actualRecordId"] for row in rows if row.get("actualRecordId")
        ),
        "expected": len(rows) - paused_count,
        "paused": paused_count,
        "completed": sum(row["status"] in {"completed", "delayed"} for row in rows),
        "missing": sum(row["status"] == "missing" for row in rows),
        "delayed": sum(row["status"] == "delayed" for row in rows),
        "failed": sum(row["status"] == "failed" for row in rows),
        "running": sum(row["status"] == "running" for row in rows),
        "pending": sum(row["status"] == "pending" for row in rows),
    }


def build_robot_report(
    robot: Any,
    jobs: list[Any],
    samples: list[Any],
    probes: list[Any],
    schedules: list[Any],
    schedule_snapshots: list[Any],
    water_events: list[Any],
    window: dict[str, datetime],
    generated_at: datetime,
    include_paused_schedules: bool = False,
    require_schedule_history: bool = False,
) -> dict[str, Any]:
    ordered_samples = sorted(
        samples,
        key=lambda row: normalize_local_naive(row_value(row, "timestamp")) or datetime.min,
    )
    provider = str(row_value(robot, "provider") or "roborock").strip().lower()
    if provider == "dreame":
        extra = row_value(robot, "extra")
        raw_settings = extra.get("settings") if isinstance(extra, dict) and isinstance(extra.get("settings"), dict) else {}
        setting_labels = {
            "cleaning_mode": "Rengjøringsmodus",
            "suction_level": "Sugekraft",
            "water_volume": "Vannmengde",
            "mop_wash_level": "Moppevask",
            "mop_clean_frequency": "Vaskefrekvens",
            "auto_empty_mode": "Støvtømming",
        }
        settings = {
            "supported": bool(raw_settings),
            "intervalMinutes": None,
            "mode": None,
            "modeLabel": None,
            "automatic": False,
            "items": [
                {"key": key, "label": setting_labels.get(key, key), "value": str(value)}
                for key, value in raw_settings.items()
                if value is not None and value != ""
            ],
        }
    else:
        settings = robot_settings(probes)
    job_rows = [
        build_job(job, ordered_samples, settings, provider)
        for job in sorted(jobs, key=lambda row: row_value(row, "begin_at") or datetime.min)
    ]
    schedule_check = build_schedule_check(
        schedules,
        jobs,
        ordered_samples,
        window,
        generated_at,
        provider,
        include_paused_schedules,
        schedule_snapshots=schedule_snapshots,
        require_history=require_schedule_history and not include_paused_schedules,
    )
    matched_record_ids = set(schedule_check["matchedRecordIds"])
    for job_row in job_rows:
        if job_row["recordId"] in matched_record_ids:
            job_row.update({"origin": "planned", "originLabel": "Gjeldende plan", "planned": True})
        elif schedule_check["historyAvailable"]:
            job_row.update({"origin": "other", "originLabel": "Øvrig jobb", "planned": False})
        else:
            job_row.update({"origin": "unknown", "originLabel": "Ikke klassifisert", "planned": None})

    planned_jobs = [
        job for job in jobs
        if str(row_value(job, "record_id") or row_value(job, "id") or "") in matched_record_ids
    ]
    planned_last_end = max(
        (
            utc_naive_to_local_naive(row_value(job, "end_at"))
            for job in planned_jobs
            if row_value(job, "end_at")
        ),
        default=None,
    )
    last_any_end = max(
        (utc_naive_to_local_naive(row_value(job, "end_at")) for job in jobs if row_value(job, "end_at")),
        default=None,
    )
    readiness_evaluated = bool(
        not include_paused_schedules
        and schedule_check["historyAvailable"]
        and schedule_check["expected"]
    )
    ready_before_opening: Optional[bool] = None
    if readiness_evaluated:
        plan_finished = (
            schedule_check["completed"] == schedule_check["expected"]
            and not schedule_check["missing"]
            and not schedule_check["failed"]
            and not schedule_check["running"]
            and not schedule_check["pending"]
        )
        ready_before_opening = bool(
            plan_finished
            and planned_last_end is not None
            and planned_last_end <= window["ready_by"]
        )
    full_at = first_full_charge(ordered_samples, last_any_end, window["end"])
    battery_ready = battery_at(ordered_samples, window["ready_by"])
    warning_jobs = sum(row["status"] == "warning" for row in job_rows)
    error_jobs = sum(row["status"] == "error" for row in job_rows)
    running_jobs = sum(row["status"] == "running" for row in job_rows)
    other_jobs = sum(row["origin"] == "other" for row in job_rows)
    unclassified_jobs = sum(row["origin"] == "unknown" for row in job_rows)
    if include_paused_schedules and schedule_check["expected"]:
        status, status_label = "neutral", "Planlagt"
    elif include_paused_schedules and schedule_check["paused"]:
        status, status_label = "neutral", "Plan satt på pause"
    elif error_jobs:
        status, status_label = "error", "Feil i natt"
    elif schedule_check["missing"]:
        status, status_label = "warning", "Planlagt jobb uteble"
    elif schedule_check["delayed"]:
        status, status_label = "warning", "Forsinket oppstart"
    elif warning_jobs:
        status, status_label = "warning", "Må kontrolleres"
    elif running_jobs:
        status, status_label = "neutral", "Pågår"
    elif readiness_evaluated and ready_before_opening:
        status, status_label = "ok", "Planen ferdig før åpning"
    elif readiness_evaluated:
        status, status_label = "warning", "Planen ikke ferdig før åpning"
    elif job_rows and not schedule_check["historyAvailable"]:
        status, status_label = "neutral", "Planhistorikk mangler"
    elif job_rows:
        status, status_label = "neutral", "Øvrig rengjøring registrert"
    else:
        status, status_label = "neutral", "Ingen nattjobb"

    findings = []
    for planned in schedule_check["jobs"]:
        if planned["status"] == "paused":
            scheduled_at = local_datetime_value(planned["scheduledAt"])
            findings.append(
                f"Planen kl. {scheduled_at.strftime('%H:%M') if scheduled_at else '-'} er satt på pause."
            )
        elif planned["status"] == "missing":
            scheduled_at = local_datetime_value(planned["scheduledAt"])
            findings.append(
                f"Planlagt {planned['cleaningTypeLabel'].lower()} kl. {scheduled_at.strftime('%H:%M') if scheduled_at else '-'} ble ikke registrert."
            )
        elif planned["status"] == "delayed":
            scheduled_at = local_datetime_value(planned["scheduledAt"])
            actual_at = local_datetime_value(planned["actualStartedAt"])
            findings.append(
                f"Planlagt jobb kl. {scheduled_at.strftime('%H:%M') if scheduled_at else '-'} startet kl. {actual_at.strftime('%H:%M') if actual_at else '-'}."
            )
    if error_jobs:
        findings.append(f"{error_jobs} {'jobb har' if error_jobs == 1 else 'jobber har'} feil eller mangler fullføring.")
    if warning_jobs:
        findings.append(f"{warning_jobs} {'jobb har' if warning_jobs == 1 else 'jobber har'} vannmangel i robot.")
    if running_jobs:
        running_start = min(
            (local_datetime_value(row["startedAt"]) for row in job_rows if row["status"] == "running"),
            default=None,
        )
        findings.append(f"Pågående jobb startet kl. {running_start.strftime('%H:%M') if running_start else '-'}.")
    elif readiness_evaluated and ready_before_opening and planned_last_end:
        findings.append(f"Siste planjobb var ferdig kl. {planned_last_end.strftime('%H:%M')}, før åpning kl. {window['ready_by'].strftime('%H:%M')}.")
    elif readiness_evaluated and planned_last_end:
        findings.append(f"Siste planjobb var ferdig kl. {planned_last_end.strftime('%H:%M')}, etter åpning kl. {window['ready_by'].strftime('%H:%M')}.")
    if other_jobs:
        findings.append(
            f"{other_jobs} {'øvrig jobb er' if other_jobs == 1 else 'øvrige jobber er'} markert, men inngår ikke i vurderingen mot åpningstid."
        )
    if not include_paused_schedules and not schedule_check["historyAvailable"]:
        findings.append("Planhistorikk mangler for denne natten; jobbene er derfor ikke vurdert mot åpningstid.")
    if full_at:
        findings.append(f"Batteriet var fullt igjen kl. {full_at.strftime('%H:%M')}.")
    elif battery_ready is not None:
        findings.append(f"Batteriet var {battery_ready} % ved åpning.")

    return {
        "duid": str(row_value(robot, "duid") or ""),
        "provider": provider,
        "name": str(row_value(robot, "name") or row_value(robot, "duid") or "Robot"),
        "model": row_value(robot, "model"),
        "status": status,
        "statusLabel": status_label,
        "jobs": job_rows,
        "scheduleCheck": schedule_check,
        "settings": settings,
        "waterEvents": build_night_water_events(water_events, window),
        "totals": {
            "jobs": len(job_rows),
            "plannedJobs": len(matched_record_ids),
            "otherJobs": other_jobs,
            "unclassifiedJobs": unclassified_jobs,
            "completed": sum(row["complete"] for row in job_rows),
            "durationMinutes": round(sum(row["durationMinutes"] or 0 for row in job_rows), 1),
            "areaM2": round(sum(row["areaM2"] or 0 for row in job_rows), 1),
            "washCount": sum(row["washCount"] or 0 for row in job_rows),
        },
        "readiness": {
            "evaluated": readiness_evaluated,
            "readyBeforeOpening": ready_before_opening,
            "lastJobEndedAt": local_iso(planned_last_end),
            "batteryAtOpening": battery_ready,
            "fullChargeAt": local_iso(full_at),
        },
        "findings": findings,
    }


def build_night_report(
    report_day: date,
    robots: list[Any],
    jobs: list[Any],
    samples: list[Any],
    probes: list[Any],
    generated_at: Optional[datetime] = None,
    schedules: Optional[list[Any]] = None,
    schedule_snapshots: Optional[list[Any]] = None,
    water_events: Optional[list[Any]] = None,
) -> dict[str, Any]:
    window = report_window(report_day)
    report_generated_at = normalize_local_naive(generated_at or datetime.now(LOCAL_TZ)) or datetime.now(LOCAL_TZ).replace(tzinfo=None)
    is_forecast = report_day > report_generated_at.date()
    require_schedule_history = schedule_snapshots is not None
    jobs_by_robot: dict[str, list[Any]] = {}
    samples_by_robot: dict[str, list[Any]] = {}
    probes_by_robot: dict[str, list[Any]] = {}
    schedules_by_robot: dict[str, list[Any]] = {}
    snapshots_by_robot: dict[str, list[Any]] = {}
    water_events_by_robot: dict[str, list[Any]] = {}
    for row in jobs:
        jobs_by_robot.setdefault(str(row_value(row, "robot_duid") or ""), []).append(row)
    for row in samples:
        samples_by_robot.setdefault(str(row_value(row, "robot_duid") or ""), []).append(row)
    for row in probes:
        probes_by_robot.setdefault(str(row_value(row, "robot_duid") or ""), []).append(row)
    for row in schedules or []:
        schedules_by_robot.setdefault(str(row_value(row, "robot_duid") or ""), []).append(row)
    for row in schedule_snapshots or []:
        snapshots_by_robot.setdefault(str(row_value(row, "robot_duid") or ""), []).append(row)
    for row in water_events or []:
        water_events_by_robot.setdefault(str(row_value(row, "robot_duid") or ""), []).append(row)
    robot_rows = [
        build_robot_report(
            robot,
            jobs_by_robot.get(str(row_value(robot, "duid") or ""), []),
            samples_by_robot.get(str(row_value(robot, "duid") or ""), []),
            probes_by_robot.get(str(row_value(robot, "duid") or ""), []),
            schedules_by_robot.get(str(row_value(robot, "duid") or ""), []),
            snapshots_by_robot.get(str(row_value(robot, "duid") or ""), []),
            water_events_by_robot.get(str(row_value(robot, "duid") or ""), []),
            window,
            report_generated_at,
            is_forecast,
            require_schedule_history,
        )
        for robot in robots
    ]
    jobs_count = sum(row["totals"]["jobs"] for row in robot_rows)
    error_count = sum(job["status"] == "error" for row in robot_rows for job in row["jobs"])
    warning_count = sum(job["status"] == "warning" for row in robot_rows for job in row["jobs"])
    running_count = sum(job["status"] == "running" for row in robot_rows for job in row["jobs"])
    expected_count = sum(row["scheduleCheck"]["expected"] for row in robot_rows)
    planned_completed_count = sum(row["scheduleCheck"]["completed"] for row in robot_rows)
    missing_count = sum(row["scheduleCheck"]["missing"] for row in robot_rows)
    delayed_count = sum(row["scheduleCheck"]["delayed"] for row in robot_rows)
    pending_count = sum(row["scheduleCheck"]["pending"] for row in robot_rows)
    paused_count = sum(row["scheduleCheck"]["paused"] for row in robot_rows)
    other_count = sum(row["totals"]["otherJobs"] for row in robot_rows)
    unclassified_count = sum(row["totals"]["unclassifiedJobs"] for row in robot_rows)
    ready_count = sum(
        row["readiness"]["evaluated"] and row["readiness"]["readyBeforeOpening"] is True
        for row in robot_rows
    )
    active_robot_count = sum(row["scheduleCheck"]["expected"] > 0 for row in robot_rows)
    history_robot_count = sum(row["scheduleCheck"]["historyAvailable"] for row in robot_rows)
    if is_forecast:
        conclusion_status = "warning" if paused_count else "neutral"
        conclusion_title = "Neste natts renholdsplan"
        active_text = f"{expected_count} {'aktiv start' if expected_count == 1 else 'aktive starter'}"
        paused_text = f" {paused_count} {'plan er' if paused_count == 1 else 'planer er'} satt på pause." if paused_count else ""
        conclusion_detail = f"{active_text}.{paused_text}"
    elif error_count:
        conclusion_status = "error"
        conclusion_title = "Natten har avvik som må følges opp"
        conclusion_detail = f"{error_count} {'jobb mangler' if error_count == 1 else 'jobber mangler'} fullføring eller har robotfeil."
    elif missing_count:
        conclusion_status = "warning"
        conclusion_title = "En eller flere planlagte jobber uteble"
        missing_labels = [
            f"{row['name']} kl. {local_datetime_value(job['scheduledAt']).strftime('%H:%M')}"
            for row in robot_rows
            for job in row["scheduleCheck"]["jobs"]
            if job["status"] == "missing" and local_datetime_value(job["scheduledAt"])
        ]
        conclusion_detail = f"Ikke registrert: {', '.join(missing_labels)}."
    elif delayed_count:
        conclusion_status = "warning"
        conclusion_title = "Planlagt rengjøring startet forsinket"
        conclusion_detail = f"{delayed_count} {'jobb startet' if delayed_count == 1 else 'jobber startet'} mer enn 10 minutter fra planlagt tid."
    elif warning_count:
        conclusion_status = "warning"
        conclusion_title = "Rengjøringen ble gjennomført, men manglet vann"
        conclusion_detail = f"{warning_count} {'jobb har' if warning_count == 1 else 'jobber har'} rapportert vannmangel i robot under rengjøringen."
    elif running_count:
        conclusion_status = "neutral"
        conclusion_title = "Rengjøringen pågår"
        conclusion_detail = f"{running_count} {'jobb er' if running_count == 1 else 'jobber er'} fortsatt i gang."
    elif expected_count:
        conclusion_status = "ok"
        conclusion_title = "Nattens planlagte rengjøring er gjennomført"
        conclusion_detail = f"{planned_completed_count} planlagte jobber er registrert. {ready_count} av {active_robot_count} planlagte roboter var ferdige før åpning."
        if unclassified_count:
            conclusion_detail += f" {unclassified_count} jobber kunne ikke klassifiseres fordi planhistorikk mangler."
    elif unclassified_count:
        conclusion_status = "neutral"
        conclusion_title = "Nattens rengjøring er registrert"
        conclusion_detail = f"{unclassified_count} jobber er registrert. Planhistorikk mangler, så de er ikke vurdert mot nattplanen."
    elif jobs_count:
        conclusion_status = "neutral"
        conclusion_title = "Øvrig rengjøring er registrert"
        conclusion_detail = f"{jobs_count} jobber er markert, men inngår ikke i vurderingen av nattplanen."
    else:
        conclusion_status = "neutral"
        conclusion_title = "Ingen rengjøringsjobber er registrert"
        conclusion_detail = "Det finnes ingen jobber i det valgte nattvinduet."
    return {
        "day": report_day.isoformat(),
        "previousDay": (report_day - timedelta(days=1)).isoformat(),
        "nextDay": (report_day + timedelta(days=1)).isoformat(),
        "isForecast": is_forecast,
        "generatedAt": local_iso(report_generated_at),
        "window": {
            "startAt": local_iso(window["start"]),
            "endAt": local_iso(window["end"]),
            "readyBy": local_iso(window["ready_by"]),
        },
        "conclusion": {
            "status": conclusion_status,
            "title": conclusion_title,
            "detail": conclusion_detail,
        },
        "summary": {
            "robots": len(robot_rows),
            "activeRobots": active_robot_count,
            "jobs": jobs_count,
            "otherJobs": other_count,
            "unclassifiedJobs": unclassified_count,
            "planHistoryRobots": history_robot_count,
            "completed": sum(row["totals"]["completed"] for row in robot_rows),
            "durationMinutes": round(sum(row["totals"]["durationMinutes"] for row in robot_rows), 1),
            "areaM2": round(sum(row["totals"]["areaM2"] for row in robot_rows), 1),
            "washCount": sum(row["totals"]["washCount"] for row in robot_rows),
            "warnings": warning_count + missing_count + delayed_count,
            "jobWarnings": warning_count,
            "running": running_count,
            "errors": error_count,
            "readyBeforeOpening": ready_count,
            "plannedJobs": expected_count,
            "plannedCompleted": planned_completed_count,
            "plannedMissing": missing_count,
            "plannedDelayed": delayed_count,
            "plannedPending": pending_count,
            "plannedPaused": paused_count,
        },
        "robots": robot_rows,
    }
