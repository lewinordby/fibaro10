from __future__ import annotations

from typing import Any, Iterable


ACTIVE_SCHEDULE_STATES = {"1", "2"}
VALID_SCHEDULE_STATES = {"0", "1", "2"}


def int_value(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def clear_water_state(telemetry: dict[str, Any]) -> str:
    label = str(telemetry.get("clear_water_status_name") or "").strip().lower()
    code = int_value(telemetry.get("clear_water_status"))
    if label in {"ok", "okay", "full", "installed"} or code == 0:
        return "ok"
    if label or code is not None:
        return "empty"
    return "unknown"


def schedule_state_map(raw_schedule: Any) -> dict[str, str]:
    states: dict[str, str] = {}
    for task in str(raw_schedule or "").split(";"):
        if not task:
            continue
        parts = task.split("-", 8)
        if len(parts) < 2 or not parts[0]:
            continue
        states[str(parts[0])] = str(parts[1])
    return states


def rewrite_schedule_states(raw_schedule: Any, requested: dict[str, str]) -> tuple[str, dict[str, str], dict[str, str]]:
    before = schedule_state_map(raw_schedule)
    normalized = {
        str(schedule_id): str(state)
        for schedule_id, state in requested.items()
        if str(state) in VALID_SCHEDULE_STATES
    }
    tasks: list[str] = []
    changed: dict[str, str] = {}
    for task in str(raw_schedule or "").split(";"):
        if not task:
            continue
        parts = task.split("-", 8)
        schedule_id = str(parts[0]) if parts else ""
        target = normalized.get(schedule_id)
        if len(parts) >= 2 and target is not None and parts[1] != "3" and parts[1] != target:
            parts[1] = target
            task = "-".join(parts)
            changed[schedule_id] = target
        tasks.append(task)
    return ";".join(tasks), before, changed


def active_schedule_rows(schedules: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for schedule in schedules:
        if not isinstance(schedule, dict) or not schedule.get("enabled"):
            continue
        schedule_id = str(schedule.get("id") or schedule.get("schedule_id") or "").strip()
        if not schedule_id:
            continue
        rows.append(
            {
                "schedule_id": schedule_id,
                "cron": schedule.get("cron"),
                "enabled": True,
            }
        )
    return rows


def interlock_label(status: str, paused_count: int = 0) -> str:
    if status == "blocked":
        return f"Vannsperre aktiv ({paused_count} planer)"
    if status == "error":
        return "Vannsperre har feil"
    if status == "disabled":
        return "Vannsperre avslått"
    if status == "unsupported":
        return "Vannsperre mangler vannstatus"
    return "Vaskeplaner klare"
