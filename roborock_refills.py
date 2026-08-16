from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Iterable, Optional

from cleaning_robot_domain import cleaning_robot_sort_key
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


def _transition_kind(row: Any) -> Optional[str]:
    if str(_row_value(row, "field_name") or "") != "clear_water_status":
        return None
    previous_value = _row_value(row, "previous_value")
    current_value = _row_value(row, "current_value")
    previous = _resource_label(previous_value, _row_value(row, "previous_label"))
    current = _resource_label(current_value, _row_value(row, "current_label"))
    if previous == "OK" and current == "Tom":
        return "empty"
    if previous == "Tom" and current == "OK":
        return "refilled"
    if previous in {"OK", "Tom", "Påfyllingsfeil", "Ikke montert"} or current in {
        "OK",
        "Tom",
        "Påfyllingsfeil",
        "Ikke montert",
    }:
        return None
    try:
        if int(previous_value) == 0 and int(current_value) != 0:
            return "empty"
        if int(previous_value) != 0 and int(current_value) == 0:
            return "refilled"
    except (TypeError, ValueError):
        pass
    return None


def _in_period(value: Optional[datetime], start: datetime, end: datetime) -> bool:
    return value is not None and start <= value < end


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
    period_start = datetime.combine(week_start, time.min)
    period_end = period_start + timedelta(days=7)
    week_end = week_start + timedelta(days=6)
    capable = set(water_capable_duids) if water_capable_duids is not None else None
    robot_rows = sorted(
        (
            row
            for row in robots
            if str(_row_value(row, "provider") or "roborock") == "roborock"
            and (capable is None or str(_row_value(row, "duid") or "") in capable)
        ),
        key=cleaning_robot_sort_key,
    )
    robot_names = {
        str(_row_value(robot, "duid") or ""): str(_row_value(robot, "name") or "Robot")
        for robot in robot_rows
    }

    transitions_by_robot: dict[str, list[dict[str, Any]]] = {}
    for row in events:
        kind = _transition_kind(row)
        stamp = normalize_local_naive(_row_value(row, "timestamp"))
        duid = str(_row_value(row, "robot_duid") or "")
        if not kind or not stamp or duid not in robot_names:
            continue
        transitions_by_robot.setdefault(duid, []).append(
            {
                "id": str(_row_value(row, "id") or f"{duid}-{stamp.isoformat()}"),
                "kind": kind,
                "timestamp": stamp,
            }
        )

    all_cycles: list[dict[str, Any]] = []
    for duid, transitions in transitions_by_robot.items():
        pending: Optional[dict[str, Any]] = None
        for transition in sorted(transitions, key=lambda item: item["timestamp"]):
            if transition["kind"] == "empty":
                if pending is None:
                    pending = {
                        "id": f"empty-{transition['id']}",
                        "robotDuid": duid,
                        "robotName": robot_names[duid],
                        "emptyAtValue": transition["timestamp"],
                        "refilledAtValue": None,
                    }
                    all_cycles.append(pending)
                continue
            if pending is not None:
                pending["refilledAtValue"] = transition["timestamp"]
                pending = None
            else:
                all_cycles.append(
                    {
                        "id": f"refill-{transition['id']}",
                        "robotDuid": duid,
                        "robotName": robot_names[duid],
                        "emptyAtValue": None,
                        "refilledAtValue": transition["timestamp"],
                    }
                )

    period_cycles = [
        cycle
        for cycle in all_cycles
        if _in_period(cycle["emptyAtValue"], period_start, period_end)
        or _in_period(cycle["refilledAtValue"], period_start, period_end)
    ]
    for cycle in period_cycles:
        empty_at = cycle["emptyAtValue"]
        refilled_at = cycle["refilledAtValue"]
        if empty_at and refilled_at:
            cycle["emptyMinutes"] = round((refilled_at - empty_at).total_seconds() / 60)
        elif empty_at and week_start == current_week_start:
            cycle["emptyMinutes"] = max(0, round((now - empty_at).total_seconds() / 60))
        else:
            cycle["emptyMinutes"] = None
        cycle["status"] = "completed" if refilled_at else "pending"

    public_cycles = [
        {
            "id": cycle["id"],
            "robotDuid": cycle["robotDuid"],
            "robotName": cycle["robotName"],
            "emptyAt": _local_iso(cycle["emptyAtValue"]),
            "refilledAt": _local_iso(cycle["refilledAtValue"]),
            "emptyMinutes": cycle["emptyMinutes"],
            "status": cycle["status"],
        }
        for cycle in sorted(
            period_cycles,
            key=lambda item: item["emptyAtValue"] or item["refilledAtValue"] or datetime.min,
            reverse=True,
        )
    ]

    robot_summary = []
    for robot in robot_rows:
        duid = str(_row_value(robot, "duid") or "")
        cycles = [cycle for cycle in period_cycles if cycle["robotDuid"] == duid]
        empty_rows = [cycle for cycle in cycles if _in_period(cycle["emptyAtValue"], period_start, period_end)]
        fill_rows = [cycle for cycle in cycles if _in_period(cycle["refilledAtValue"], period_start, period_end)]
        durations = [cycle["emptyMinutes"] for cycle in empty_rows if cycle["emptyMinutes"] is not None and cycle["refilledAtValue"]]
        last_empty = max((cycle["emptyAtValue"] for cycle in empty_rows), default=None)
        last_fill = max((cycle["refilledAtValue"] for cycle in fill_rows), default=None)
        pending = next((cycle for cycle in empty_rows if cycle["status"] == "pending"), None)
        robot_summary.append(
            {
                "duid": duid,
                "name": str(_row_value(robot, "name") or "Robot"),
                "empties": len(empty_rows),
                "fills": len(fill_rows),
                "pending": pending is not None,
                "currentEmptySince": _local_iso(pending["emptyAtValue"]) if pending else None,
                "lastEmptyAt": _local_iso(last_empty),
                "lastFillAt": _local_iso(last_fill),
                "averageEmptyMinutes": round(sum(durations) / len(durations)) if durations else None,
            }
        )
    robot_summary.sort(key=cleaning_robot_sort_key)

    empty_cycles = [cycle for cycle in period_cycles if _in_period(cycle["emptyAtValue"], period_start, period_end)]
    fill_cycles = [cycle for cycle in period_cycles if _in_period(cycle["refilledAtValue"], period_start, period_end)]
    completed_durations = [
        cycle["emptyMinutes"]
        for cycle in empty_cycles
        if cycle["emptyMinutes"] is not None and cycle["refilledAtValue"] is not None
    ]
    latest_fill = max((cycle["refilledAtValue"] for cycle in fill_cycles), default=None)
    iso_year, iso_week, _ = week_start.isocalendar()
    next_week_start = week_start + timedelta(days=7)
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
            "empties": len(empty_cycles),
            "fills": len(fill_cycles),
            "robots": len(robot_summary),
            "pending": sum(cycle["status"] == "pending" for cycle in empty_cycles),
            "latestFillAt": _local_iso(latest_fill),
            "averageEmptyMinutes": (
                round(sum(completed_durations) / len(completed_durations)) if completed_durations else None
            ),
        },
        "robots": robot_summary,
        "cycles": public_cycles,
        "measurementNote": (
            "Tom registreres ved første avlesning der dokkens rentvannstatus går fra OK til Tom. "
            "Fylt registreres når statusen senere går fra Tom til OK. Roborock rapporterer ikke liter eller "
            "eksakt fyllingsgrad, så klokkeslettene kan avvike med opptil ett innsamlingsintervall."
        ),
    }
