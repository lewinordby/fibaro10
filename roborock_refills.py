from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Iterable, Optional

from roborock_domain import roborock_resource_status_label
from time_formatting import LOCAL_TZ, normalize_local_naive


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _local_iso(value: Optional[datetime]) -> Optional[str]:
    local = normalize_local_naive(value)
    return local.replace(tzinfo=LOCAL_TZ).isoformat() if local else None


def iso_week_key(day: date) -> str:
    iso_year, iso_week, _ = day.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def iso_week_start(value: Optional[str], *, today: Optional[date] = None) -> date:
    current = today or datetime.now(LOCAL_TZ).date()
    if not value:
        iso_year, iso_week, _ = current.isocalendar()
        return date.fromisocalendar(iso_year, iso_week, 1)
    try:
        year_text, week_text = value.strip().upper().split("-W", 1)
        return date.fromisocalendar(int(year_text), int(week_text), 1)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("Uken må oppgis som YYYY-Www") from exc


def _resource_label(value: Any, stored_label: Any) -> str:
    text = str(stored_label or "").strip()
    if text in {"OK", "Tom", "Påfyllingsfeil", "Ikke montert"}:
        return text
    return roborock_resource_status_label(value, stored_label)


def _is_refill(row: Any) -> bool:
    if str(_row_value(row, "field_name") or "") != "clear_water_status":
        return False
    previous_value = _row_value(row, "previous_value")
    current_value = _row_value(row, "current_value")
    try:
        if int(previous_value) != 0 and int(current_value) == 0:
            return True
    except (TypeError, ValueError):
        pass
    previous = _resource_label(previous_value, _row_value(row, "previous_label"))
    current = _resource_label(current_value, _row_value(row, "current_label"))
    return previous not in {"OK", "Ikke støttet"} and current == "OK"


def build_refill_log(
    week_start: date,
    robots: Iterable[Any],
    events: Iterable[Any],
    *,
    generated_at: Optional[datetime] = None,
    water_capable_duids: Optional[Iterable[str]] = None,
) -> dict[str, Any]:
    now = normalize_local_naive(generated_at or datetime.now(LOCAL_TZ)) or datetime.now(LOCAL_TZ).replace(tzinfo=None)
    current_week_start = iso_week_start(None, today=now.date())
    week_end = week_start + timedelta(days=6)
    capable = set(water_capable_duids) if water_capable_duids is not None else None
    robot_rows = [
        row
        for row in robots
        if str(_row_value(row, "provider") or "roborock") == "roborock"
        and (capable is None or str(_row_value(row, "duid") or "") in capable)
    ]
    robot_names = {
        str(_row_value(robot, "duid") or ""): str(_row_value(robot, "name") or "Robot")
        for robot in robot_rows
    }

    fills: list[dict[str, Any]] = []
    for row in events:
        if not _is_refill(row):
            continue
        stamp = normalize_local_naive(_row_value(row, "timestamp"))
        duid = str(_row_value(row, "robot_duid") or "")
        if not stamp or not duid:
            continue
        fills.append(
            {
                "id": str(_row_value(row, "id") or f"{duid}-{stamp.isoformat()}"),
                "robotDuid": duid,
                "robotName": robot_names.get(duid, "Ukjent robot"),
                "timestampValue": stamp,
                "previousLabel": _resource_label(
                    _row_value(row, "previous_value"), _row_value(row, "previous_label")
                ),
                "currentLabel": _resource_label(
                    _row_value(row, "current_value"), _row_value(row, "current_label")
                ),
            }
        )

    by_robot: dict[str, list[dict[str, Any]]] = {}
    for item in sorted(fills, key=lambda value: value["timestampValue"]):
        rows = by_robot.setdefault(item["robotDuid"], [])
        previous = rows[-1]["timestampValue"] if rows else None
        item["minutesSincePrevious"] = (
            round((item["timestampValue"] - previous).total_seconds() / 60) if previous else None
        )
        rows.append(item)

    public_events = [
        {
            "id": item["id"],
            "robotDuid": item["robotDuid"],
            "robotName": item["robotName"],
            "timestamp": _local_iso(item["timestampValue"]),
            "previousLabel": item["previousLabel"],
            "currentLabel": item["currentLabel"],
            "minutesSincePrevious": item["minutesSincePrevious"],
        }
        for item in sorted(fills, key=lambda value: value["timestampValue"], reverse=True)
    ]

    robot_summary = []
    for robot in robot_rows:
        duid = str(_row_value(robot, "duid") or "")
        rows = by_robot.get(duid, [])
        intervals = [row["minutesSincePrevious"] for row in rows if row["minutesSincePrevious"] is not None]
        robot_summary.append(
            {
                "duid": duid,
                "name": str(_row_value(robot, "name") or "Robot"),
                "count": len(rows),
                "lastAt": _local_iso(rows[-1]["timestampValue"]) if rows else None,
                "averageIntervalMinutes": round(sum(intervals) / len(intervals)) if intervals else None,
            }
        )
    robot_summary.sort(key=lambda row: (-row["count"], row["name"]))

    iso_year, iso_week, _ = week_start.isocalendar()
    next_week_start = week_start + timedelta(days=7)
    intervals = [item["minutesSincePrevious"] for item in fills if item["minutesSincePrevious"] is not None]
    return {
        "period": {
            "week": iso_week_key(week_start),
            "weekNumber": iso_week,
            "year": iso_year,
            "fromDay": week_start.isoformat(),
            "toDay": week_end.isoformat(),
            "generatedAt": _local_iso(now),
            "isCurrentWeek": week_start == current_week_start,
            "currentWeek": iso_week_key(current_week_start),
            "previousWeek": iso_week_key(week_start - timedelta(days=7)),
            "nextWeek": iso_week_key(next_week_start),
            "canNext": next_week_start <= current_week_start,
        },
        "summary": {
            "fills": len(public_events),
            "robots": len(robot_summary),
            "robotsWithFills": sum(row["count"] > 0 for row in robot_summary),
            "latestAt": public_events[0]["timestamp"] if public_events else None,
            "averageIntervalMinutes": round(sum(intervals) / len(intervals)) if intervals else None,
        },
        "robots": robot_summary,
        "events": public_events,
        "measurementNote": (
            "En påfylling registreres når dokkens rentvannstatus går fra tom til OK. "
            "Roborock rapporterer ikke liter eller eksakt fyllingsgrad, så tidspunktet er første avlesning "
            "etter at renholdspersonalet har fylt tanken."
        ),
    }
