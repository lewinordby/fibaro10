from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Iterable, Optional

from roborock_domain import roborock_resource_status_label, roborock_water_label
from roborock_reports import integer, number, probe_value, row_value, wash_settings
from time_formatting import LOCAL_TZ, normalize_local_naive, utc_naive_to_local_naive


WATER_EVENT_FIELDS = {
    "clear_water_status",
    "dirty_water_status",
    "clean_fluid_status",
    "water_shortage_status",
    "water_box_status",
    "water_box_carriage_status",
    "water_box_filter_status",
}


def local_iso(value: Optional[datetime]) -> Optional[str]:
    local = normalize_local_naive(value)
    return local.replace(tzinfo=LOCAL_TZ).isoformat() if local else None


def _status_problem(label: str) -> bool:
    return label not in {"OK", "Ikke støttet", "0", "Nei"}


def _resource(value: Any, name: Any = None) -> dict[str, Any]:
    label = roborock_resource_status_label(value, name)
    return {
        "supported": value is not None or bool(name),
        "label": label,
        "attention": _status_problem(label),
    }


def _shortage(value: Any) -> dict[str, Any]:
    status = integer(value)
    if status is None:
        return {"supported": False, "label": "Ikke støttet", "attention": False}
    return {
        "supported": True,
        "label": "OK" if status == 0 else "Vannmangel",
        "attention": status != 0,
    }


def _attached(value: Any) -> dict[str, Any]:
    status = integer(value)
    if status is None:
        return {"supported": False, "label": "Ikke støttet", "attention": False}
    return {
        "supported": True,
        "label": "Montert" if status != 0 else "Ikke montert",
        "attention": status == 0,
    }


def _interlock(telemetry: Any) -> dict[str, Any]:
    raw = row_value(telemetry, "raw")
    normalized = raw.get("normalized") if isinstance(raw, dict) else None
    value = normalized.get("water_interlock") if isinstance(normalized, dict) else None
    if not isinstance(value, dict):
        return {
            "enabled": False,
            "status": "unsupported",
            "label": "Ikke mottatt",
            "pausedCount": 0,
            "pausedSchedules": [],
        }
    return {
        "enabled": bool(value.get("enabled")),
        "status": str(value.get("status") or "unsupported"),
        "label": str(value.get("label") or "Ikke mottatt"),
        "waterStatus": value.get("water_status"),
        "checkedAt": value.get("checked_at"),
        "blockedAt": value.get("blocked_at"),
        "restoredAt": value.get("restored_at"),
        "pausedCount": integer(value.get("paused_count")) or 0,
        "pausedSchedules": value.get("paused_schedules") if isinstance(value.get("paused_schedules"), list) else [],
        "lastAction": value.get("last_action"),
        "lastError": value.get("last_error"),
    }


def _event_kind(row: Any) -> str:
    field = str(row_value(row, "field_name") or "")
    current_label = str(row_value(row, "current_label") or "")
    current_value = integer(row_value(row, "current_value"))
    if field == "clear_water_status":
        return "clean_empty" if _status_problem(current_label) else "clean_restored"
    if field == "dirty_water_status":
        return "dirty_full" if _status_problem(current_label) else "dirty_cleared"
    if field == "water_shortage_status":
        return "robot_empty" if current_value not in {None, 0} else "robot_restored"
    if field == "water_box_status":
        return "tank_removed" if current_value == 0 else "tank_mounted"
    if field == "water_box_carriage_status":
        return "mop_removed" if current_value == 0 else "mop_mounted"
    if field == "clean_fluid_status":
        return "detergent_warning" if _status_problem(current_label) else "detergent_ok"
    if field == "water_box_filter_status":
        return "filter_warning" if _status_problem(current_label) else "filter_ok"
    return "water_status"


def _latest_event(events: list[dict[str, Any]], kinds: set[str]) -> Optional[str]:
    return next((row["timestamp"] for row in events if row["kind"] in kinds), None)


def _event_value_label(field: str, value: Any, stored_label: Any) -> str:
    parsed = integer(value)
    if field == "water_shortage_status":
        return "OK" if parsed == 0 else "Vannmangel" if parsed is not None else "Ikke støttet"
    if field in {"water_box_status", "water_box_carriage_status"}:
        return "Montert" if parsed not in {None, 0} else "Ikke montert"
    return str(stored_label or "-") or "-"


def _job_local_time(row: Any) -> Optional[datetime]:
    return utc_naive_to_local_naive(row_value(row, "begin_at"))


def build_water_report(
    days: int,
    robots: Iterable[Any],
    jobs: Iterable[Any],
    telemetry_samples: Iterable[Any],
    events: Iterable[Any],
    probes: Iterable[Any],
    *,
    generated_at: Optional[datetime] = None,
) -> dict[str, Any]:
    now = normalize_local_naive(generated_at or datetime.now(LOCAL_TZ)) or datetime.now(LOCAL_TZ).replace(tzinfo=None)
    start_day = now.date() - timedelta(days=days - 1)
    robot_rows = list(robots)
    jobs_by_robot: dict[str, list[Any]] = {}
    telemetry_by_robot: dict[str, Any] = {}
    events_by_robot: dict[str, list[dict[str, Any]]] = {}
    probes_by_robot: dict[str, list[Any]] = {}

    for row in jobs:
        jobs_by_robot.setdefault(str(row_value(row, "robot_duid") or ""), []).append(row)
    for row in telemetry_samples:
        duid = str(row_value(row, "robot_duid") or "")
        current = telemetry_by_robot.get(duid)
        if current is None or (normalize_local_naive(row_value(row, "timestamp")) or datetime.min) > (
            normalize_local_naive(row_value(current, "timestamp")) or datetime.min
        ):
            telemetry_by_robot[duid] = row
    for row in probes:
        probes_by_robot.setdefault(str(row_value(row, "robot_duid") or ""), []).append(row)

    public_events: list[dict[str, Any]] = []
    robot_names = {str(row_value(robot, "duid") or ""): str(row_value(robot, "name") or "Robot") for robot in robot_rows}
    for row in events:
        field = str(row_value(row, "field_name") or "")
        if field not in WATER_EVENT_FIELDS:
            continue
        duid = str(row_value(row, "robot_duid") or "")
        stamp = normalize_local_naive(row_value(row, "timestamp"))
        item = {
            "id": str(row_value(row, "id") or ""),
            "robotDuid": duid,
            "robotName": robot_names.get(duid, "Ukjent robot"),
            "timestamp": local_iso(stamp),
            "field": field,
            "title": str(row_value(row, "title") or "Vannstatus"),
            "previousLabel": _event_value_label(
                field,
                row_value(row, "previous_value"),
                row_value(row, "previous_label"),
            ),
            "currentLabel": _event_value_label(
                field,
                row_value(row, "current_value"),
                row_value(row, "current_label"),
            ),
            "severity": str(row_value(row, "severity") or "info"),
            "kind": _event_kind(row),
        }
        public_events.append(item)
        events_by_robot.setdefault(duid, []).append(item)
    public_events.sort(key=lambda row: row["timestamp"] or "", reverse=True)
    for rows in events_by_robot.values():
        rows.sort(key=lambda row: row["timestamp"] or "", reverse=True)

    daily = {
        start_day + timedelta(days=offset): {
            "day": (start_day + timedelta(days=offset)).isoformat(),
            "jobs": 0,
            "mopJobs": 0,
            "washCount": 0,
            "areaM2": 0.0,
            "waterWarnings": 0,
        }
        for offset in range(days)
    }
    report_robots = []
    for robot in robot_rows:
        duid = str(row_value(robot, "duid") or "")
        provider = str(row_value(robot, "provider") or "roborock")
        robot_jobs = jobs_by_robot.get(duid, [])
        robot_events = events_by_robot.get(duid, [])
        robot_probes = probes_by_robot.get(duid, [])
        telemetry = telemetry_by_robot.get(duid)
        wash = wash_settings(robot_probes)
        water_probe = probe_value(robot_probes, "GET_WATER_BOX_CUSTOM_MODE")
        water_mode = integer(water_probe.get("water_box_mode"))

        clean_water = _resource(
            row_value(telemetry, "clear_water_status"),
            row_value(telemetry, "clear_water_status_name"),
        )
        dirty_water = _resource(
            row_value(telemetry, "dirty_water_status"),
            row_value(telemetry, "dirty_water_status_name"),
        )
        detergent = _resource(
            row_value(telemetry, "clean_fluid_status"),
            row_value(telemetry, "clean_fluid_status_name"),
        )
        robot_water = _shortage(row_value(telemetry, "water_shortage_status"))
        water_box = _attached(row_value(telemetry, "water_box_status"))
        mop_attached = _attached(row_value(telemetry, "water_box_carriage_status"))
        water_filter = _resource(row_value(telemetry, "water_box_filter_status"))
        interlock = _interlock(telemetry)
        dock_supported = clean_water["supported"] or dirty_water["supported"] or bool(wash["supported"])
        attention = any(item["attention"] for item in (clean_water, dirty_water, detergent, robot_water)) or interlock["status"] == "error"

        wash_count = 0
        mop_jobs = 0
        area_m2 = 0.0
        duration_minutes = 0.0
        for job in robot_jobs:
            job_washes = integer(row_value(job, "wash_count")) or 0
            job_day = _job_local_time(job)
            job_area = number(row_value(job, "cleaned_area_m2")) or number(row_value(job, "area_m2")) or 0.0
            job_duration = number(row_value(job, "duration_minutes"))
            if job_duration is None:
                seconds = number(row_value(job, "duration_seconds"))
                job_duration = seconds / 60 if seconds is not None else 0.0
            wash_count += job_washes
            if job_washes:
                mop_jobs += 1
                area_m2 += job_area
                duration_minutes += job_duration
            if job_day and job_day.date() in daily:
                day_row = daily[job_day.date()]
                day_row["jobs"] += 1
                day_row["washCount"] += job_washes
                if job_washes:
                    day_row["mopJobs"] += 1
                    day_row["areaM2"] += job_area

        for event in robot_events:
            if event["severity"] in {"warning", "critical"} and event["timestamp"]:
                event_day = datetime.fromisoformat(event["timestamp"]).date()
                if event_day in daily:
                    daily[event_day]["waterWarnings"] += 1

        if provider != "roborock":
            status, status_label = "unsupported", "Venter på vanndata"
        elif attention:
            status, status_label = "attention", "Krever kontroll"
        elif dock_supported:
            status, status_label = "ready", "Vannsystem OK"
        else:
            status, status_label = "unsupported", "Ingen vanndokk"

        report_robots.append(
            {
                "duid": duid,
                "name": str(row_value(robot, "name") or "Robot"),
                "provider": provider,
                "model": row_value(robot, "model"),
                "status": status,
                "statusLabel": status_label,
                "observedAt": local_iso(normalize_local_naive(row_value(telemetry, "timestamp"))),
                "current": {
                    "dockSupported": dock_supported,
                    "cleanWater": clean_water,
                    "dirtyWater": dirty_water,
                    "robotWater": robot_water,
                    "waterBox": water_box,
                    "mopAttached": mop_attached,
                    "waterFilter": water_filter,
                    "detergent": detergent,
                    "interlock": interlock,
                },
                "settings": {
                    "washSupported": bool(wash["supported"]),
                    "intervalMinutes": wash["intervalMinutes"],
                    "washModeLabel": wash["modeLabel"],
                    "automatic": bool(wash["automatic"]),
                    "waterMode": water_mode,
                    "waterModeLabel": roborock_water_label(water_mode) if water_mode is not None else None,
                },
                "usage": {
                    "jobs": len(robot_jobs),
                    "mopJobs": mop_jobs,
                    "washCount": wash_count,
                    "areaM2": round(area_m2, 1),
                    "durationMinutes": round(duration_minutes, 1),
                    "areaPerWashM2": round(area_m2 / wash_count, 1) if wash_count else None,
                },
                "lastCleanWaterEmptyAt": _latest_event(robot_events, {"clean_empty"}),
                "lastCleanWaterRestoredAt": _latest_event(robot_events, {"clean_restored"}),
                "lastDirtyWaterFullAt": _latest_event(robot_events, {"dirty_full"}),
                "lastDirtyWaterClearedAt": _latest_event(robot_events, {"dirty_cleared"}),
                "lastRobotWaterEmptyAt": _latest_event(robot_events, {"robot_empty"}),
                "lastRobotWaterRestoredAt": _latest_event(robot_events, {"robot_restored"}),
            }
        )

    daily_rows = []
    for day_row in daily.values():
        day_row["areaM2"] = round(day_row["areaM2"], 1)
        day_row["areaPerWashM2"] = round(day_row["areaM2"] / day_row["washCount"], 1) if day_row["washCount"] else None
        daily_rows.append(day_row)

    capable = [row for row in report_robots if row["current"]["dockSupported"]]
    total_washes = sum(row["usage"]["washCount"] for row in report_robots)
    total_area = sum(row["usage"]["areaM2"] for row in report_robots)
    warning_events = sum(row["severity"] in {"warning", "critical"} for row in public_events)
    return {
        "period": {
            "days": days,
            "fromDay": start_day.isoformat(),
            "toDay": now.date().isoformat(),
            "generatedAt": local_iso(now),
        },
        "summary": {
            "robots": len(report_robots),
            "waterCapable": len(capable),
            "dockReady": sum(row["status"] == "ready" for row in capable),
            "dockAttention": sum(row["status"] == "attention" for row in capable),
            "washCount": total_washes,
            "mopJobs": sum(row["usage"]["mopJobs"] for row in report_robots),
            "areaM2": round(total_area, 1),
            "areaPerWashM2": round(total_area / total_washes, 1) if total_washes else None,
            "waterWarnings": warning_events,
            "restoredEvents": sum(row["kind"] in {"clean_restored", "dirty_cleared", "robot_restored"} for row in public_events),
        },
        "robots": report_robots,
        "daily": daily_rows,
        "events": public_events[:250],
        "measurementNote": (
            "Roborock rapporterer status, innstillinger og moppevasker, men ikke liter. "
            "Areal per moppevask brukes derfor som en sammenlignbar belastningsindikator."
        ),
    }
