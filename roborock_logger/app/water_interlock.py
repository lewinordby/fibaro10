from __future__ import annotations

from typing import Any, Iterable


def int_value(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def schedule_params(schedule: dict[str, Any]) -> dict[str, Any]:
    param = schedule.get("param")
    if not isinstance(param, dict):
        return {}
    params = param.get("params")
    if not isinstance(params, list):
        return {}
    return next((row for row in params if isinstance(row, dict)), {})


def schedule_timer_id(schedule: dict[str, Any]) -> str | None:
    value = schedule_params(schedule).get("name")
    text = str(value or "").strip()
    return text or None


def schedule_uses_water(schedule: dict[str, Any]) -> bool:
    return int_value(schedule_params(schedule).get("water_box_mode")) not in {None, 200}


def wash_schedule_rows(schedules: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for schedule in schedules:
        if not isinstance(schedule, dict) or not schedule_uses_water(schedule):
            continue
        timer_id = schedule_timer_id(schedule)
        if not timer_id:
            continue
        params = schedule_params(schedule)
        rows.append(
            {
                "schedule_id": str(schedule.get("id") or schedule.get("schedule_id") or timer_id),
                "timer_id": timer_id,
                "cron": schedule.get("cron"),
                "enabled": bool(schedule.get("enabled")),
                "water_box_mode": int_value(params.get("water_box_mode")),
                "fan_power": int_value(params.get("fan_power")),
                "mop_mode": int_value(params.get("mop_mode")),
            }
        )
    return rows


def timer_status_map(value: Any) -> dict[str, str]:
    if not isinstance(value, list):
        return {}
    statuses: dict[str, str] = {}
    for row in value:
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        timer_id = str(row[0] or "").strip()
        status = str(row[1] or "").strip().lower()
        if timer_id and status in {"on", "off"}:
            statuses[timer_id] = status
    return statuses


def clear_water_state(telemetry: dict[str, Any]) -> str:
    code = int_value(telemetry.get("clear_water_status"))
    if code is None:
        return "unknown"
    return "ok" if code == 0 else "empty"


def interlock_label(status: str, paused_count: int = 0) -> str:
    if status == "blocked":
        return f"Vannsperre aktiv ({paused_count} planer)"
    if status == "error":
        return "Vannsperre har feil"
    if status == "disabled":
        return "Vannsperre avslått"
    if status == "unsupported":
        return "Vannsperre ikke støttet"
    return "Vaskeplaner klare"
