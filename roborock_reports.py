from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable, Optional

from roborock_domain import (
    roborock_error_label,
    roborock_fan_label,
    roborock_mop_label,
    roborock_water_label,
)
from time_formatting import LOCAL_TZ, normalize_local_naive, utc_naive_to_local_naive


REPORT_START = time(20, 0)
REPORT_END = time(8, 0)
REPORT_READY_BY = time(6, 45)

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


def resource_problem(row: Any) -> bool:
    shortage = integer(row_value(row, "water_shortage_status"))
    clear_name = str(row_value(row, "clear_water_status_name") or "").strip().lower()
    clear_status = integer(row_value(row, "clear_water_status"))
    return (
        shortage not in {None, 0}
        or clear_status not in {None, 0}
        or clear_name not in {"", "okay", "ok"}
    )


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


def build_job(job: Any, samples: list[Any], settings: dict[str, Any]) -> dict[str, Any]:
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
    cleaning_type, cleaning_type_label = job_cleaning_type(fan_power, water_mode, mop_mode)
    start_sample = nearest_sample(observed, started_at, before=False)
    end_sample = nearest_sample(observed, job_end, before=True)
    water_samples = [row for row in observed if resource_problem(row)]
    dock_error_samples = [
        row for row in observed if integer(row_value(row, "dock_error_status")) not in {None, 0}
    ]
    error_code = integer(row_value(job, "error_code"))
    complete = row_value(job, "complete") is True
    status = "error" if error_code not in {None, 0} or not complete else "warning" if water_samples or dock_error_samples else "ok"
    status_label = "Feil" if status == "error" else "Kontroller" if status == "warning" else "Fullført"
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
    if cleaning_type in {"vacuum", "vacuum_mop"}:
        mode_parts.append(roborock_fan_label(fan_power))
    if cleaning_type in {"mop", "vacuum_mop"}:
        mode_parts.extend([roborock_mop_label(mop_mode), f"{roborock_water_label(water_mode).lower()} vannmengde"])
    mode_parts.append(f"{rounds} {'runde' if rounds == 1 else 'runder'}")
    issue_parts = []
    if error_code not in {None, 0}:
        issue_parts.append(roborock_error_label(error_code))
    if not complete:
        issue_parts.append("Jobben er ikke markert fullført")
    if water_samples:
        water_at = normalize_local_naive(row_value(water_samples[0], "timestamp"))
        issue_parts.append(f"Vannvarsel kl. {water_at.strftime('%H:%M')}" if water_at else "Vannvarsel")
    if dock_error_samples:
        dock_at = normalize_local_naive(row_value(dock_error_samples[0], "timestamp"))
        issue_parts.append(f"Dokkfeil kl. {dock_at.strftime('%H:%M')}" if dock_at else "Dokkfeil")
    return {
        "recordId": str(row_value(job, "record_id") or row_value(job, "id") or ""),
        "startedAt": local_iso(started_at),
        "endedAt": local_iso(ended_at),
        "durationMinutes": round(duration_minutes, 1) if duration_minutes is not None else None,
        "areaM2": round(number(row_value(job, "cleaned_area_m2")) or number(row_value(job, "area_m2")) or 0, 2),
        "complete": complete,
        "errorCode": error_code,
        "cleaningType": cleaning_type,
        "cleaningTypeLabel": cleaning_type_label,
        "modeLabel": " · ".join(part for part in mode_parts if part and part != "-"),
        "rounds": rounds,
        "batteryStart": integer(row_value(start_sample, "battery")) if start_sample else None,
        "batteryEnd": integer(row_value(end_sample, "battery")) if end_sample else None,
        "washCount": wash_count,
        "expectedWashCount": expected_washes,
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


def build_robot_report(
    robot: Any,
    jobs: list[Any],
    samples: list[Any],
    probes: list[Any],
    window: dict[str, datetime],
) -> dict[str, Any]:
    ordered_samples = sorted(
        samples,
        key=lambda row: normalize_local_naive(row_value(row, "timestamp")) or datetime.min,
    )
    settings = robot_settings(probes)
    job_rows = [build_job(job, ordered_samples, settings) for job in sorted(jobs, key=lambda row: row_value(row, "begin_at") or datetime.min)]
    last_end = max(
        (utc_naive_to_local_naive(row_value(job, "end_at")) for job in jobs if row_value(job, "end_at")),
        default=None,
    )
    full_at = first_full_charge(ordered_samples, last_end, window["end"])
    battery_ready = battery_at(ordered_samples, window["ready_by"])
    ready_before_opening = bool(last_end is None or last_end <= window["ready_by"])
    warning_jobs = sum(row["status"] == "warning" for row in job_rows)
    error_jobs = sum(row["status"] == "error" for row in job_rows)
    if error_jobs:
        status, status_label = "error", "Feil i natt"
    elif warning_jobs:
        status, status_label = "warning", "Må kontrolleres"
    elif job_rows and ready_before_opening:
        status, status_label = "ok", "Ferdig før åpning"
    elif job_rows:
        status, status_label = "warning", "Ferdig etter åpning"
    else:
        status, status_label = "neutral", "Ingen nattjobb"

    findings = []
    if error_jobs:
        findings.append(f"{error_jobs} {'jobb har' if error_jobs == 1 else 'jobber har'} feil eller mangler fullføring.")
    if warning_jobs:
        findings.append(f"{warning_jobs} {'jobb har' if warning_jobs == 1 else 'jobber har'} vann- eller dokkvarsel.")
    if job_rows and ready_before_opening:
        findings.append(f"Siste jobb var ferdig kl. {last_end.strftime('%H:%M')}, før åpning kl. {window['ready_by'].strftime('%H:%M')}.")
    elif job_rows and last_end:
        findings.append(f"Siste jobb var ferdig kl. {last_end.strftime('%H:%M')}, etter åpning kl. {window['ready_by'].strftime('%H:%M')}.")
    if full_at:
        findings.append(f"Batteriet var fullt igjen kl. {full_at.strftime('%H:%M')}.")
    elif battery_ready is not None:
        findings.append(f"Batteriet var {battery_ready} % ved åpning.")

    return {
        "duid": str(row_value(robot, "duid") or ""),
        "name": str(row_value(robot, "name") or row_value(robot, "duid") or "Robot"),
        "model": row_value(robot, "model"),
        "status": status,
        "statusLabel": status_label,
        "jobs": job_rows,
        "settings": settings,
        "totals": {
            "jobs": len(job_rows),
            "completed": sum(row["complete"] for row in job_rows),
            "durationMinutes": round(sum(row["durationMinutes"] or 0 for row in job_rows), 1),
            "areaM2": round(sum(row["areaM2"] or 0 for row in job_rows), 1),
            "washCount": sum(row["washCount"] or 0 for row in job_rows),
        },
        "readiness": {
            "readyBeforeOpening": ready_before_opening,
            "lastJobEndedAt": local_iso(last_end),
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
) -> dict[str, Any]:
    window = report_window(report_day)
    jobs_by_robot: dict[str, list[Any]] = {}
    samples_by_robot: dict[str, list[Any]] = {}
    probes_by_robot: dict[str, list[Any]] = {}
    for row in jobs:
        jobs_by_robot.setdefault(str(row_value(row, "robot_duid") or ""), []).append(row)
    for row in samples:
        samples_by_robot.setdefault(str(row_value(row, "robot_duid") or ""), []).append(row)
    for row in probes:
        probes_by_robot.setdefault(str(row_value(row, "robot_duid") or ""), []).append(row)
    robot_rows = [
        build_robot_report(
            robot,
            jobs_by_robot.get(str(row_value(robot, "duid") or ""), []),
            samples_by_robot.get(str(row_value(robot, "duid") or ""), []),
            probes_by_robot.get(str(row_value(robot, "duid") or ""), []),
            window,
        )
        for robot in robots
    ]
    jobs_count = sum(row["totals"]["jobs"] for row in robot_rows)
    error_count = sum(job["status"] == "error" for row in robot_rows for job in row["jobs"])
    warning_count = sum(job["status"] == "warning" for row in robot_rows for job in row["jobs"])
    ready_count = sum(row["readiness"]["readyBeforeOpening"] and bool(row["jobs"]) for row in robot_rows)
    active_robot_count = sum(bool(row["jobs"]) for row in robot_rows)
    if error_count:
        conclusion_status = "error"
        conclusion_title = "Natten har avvik som må følges opp"
        conclusion_detail = f"{error_count} {'jobb mangler' if error_count == 1 else 'jobber mangler'} fullføring eller har robotfeil."
    elif warning_count:
        conclusion_status = "warning"
        conclusion_title = "Rengjøringen ble gjennomført, men har varsler"
        conclusion_detail = f"{warning_count} {'jobb har' if warning_count == 1 else 'jobber har'} vann- eller dokkvarsel som bør kontrolleres."
    elif jobs_count:
        conclusion_status = "ok"
        conclusion_title = "Nattens rengjøring er gjennomført"
        conclusion_detail = f"{jobs_count} jobber er registrert. {ready_count} av {active_robot_count} aktive roboter var ferdige før åpning."
    else:
        conclusion_status = "neutral"
        conclusion_title = "Ingen rengjøringsjobber er registrert"
        conclusion_detail = "Det finnes ingen jobber i det valgte nattvinduet."
    return {
        "day": report_day.isoformat(),
        "previousDay": (report_day - timedelta(days=1)).isoformat(),
        "nextDay": (report_day + timedelta(days=1)).isoformat(),
        "generatedAt": local_iso(generated_at or datetime.now(LOCAL_TZ)),
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
            "completed": sum(row["totals"]["completed"] for row in robot_rows),
            "durationMinutes": round(sum(row["totals"]["durationMinutes"] for row in robot_rows), 1),
            "areaM2": round(sum(row["totals"]["areaM2"] for row in robot_rows), 1),
            "warnings": warning_count,
            "errors": error_count,
            "readyBeforeOpening": ready_count,
        },
        "robots": robot_rows,
    }
