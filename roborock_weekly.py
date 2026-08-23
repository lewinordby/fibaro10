from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Iterable, Optional

from cleaning_robot_domain import cleaning_robot_sort_key
from roborock_refills import iso_week_key, iso_week_start
from roborock_reports import build_job, row_value
from time_formatting import LOCAL_TZ, normalize_local_naive, utc_naive_to_local_naive


def _local_iso(value: Optional[datetime]) -> Optional[str]:
    local = normalize_local_naive(value)
    return local.replace(tzinfo=LOCAL_TZ).isoformat() if local else None


def build_weekly_job_log(
    selected_week: date,
    robots: Iterable[Any],
    jobs: Iterable[Any],
    telemetry_samples: Iterable[Any],
    *,
    generated_at: Optional[datetime] = None,
) -> dict[str, Any]:
    now = normalize_local_naive(generated_at or datetime.now(LOCAL_TZ)) or datetime.now(LOCAL_TZ).replace(tzinfo=None)
    week_start = iso_week_start(iso_week_key(selected_week), today=now.date())
    week_end = week_start + timedelta(days=6)
    current_week = iso_week_start(None, today=now.date())
    robot_rows = sorted(list(robots), key=cleaning_robot_sort_key)
    robot_by_duid = {str(row_value(robot, "duid") or ""): robot for robot in robot_rows}
    samples_by_duid: dict[str, list[Any]] = {}
    for sample in telemetry_samples:
        samples_by_duid.setdefault(str(row_value(sample, "robot_duid") or ""), []).append(sample)

    rows: list[dict[str, Any]] = []
    for job in jobs:
        if row_value(job, "complete") is not True or row_value(job, "end_at") is None:
            continue
        error_code = row_value(job, "error_code")
        if error_code not in {None, 0, "0"}:
            continue
        duid = str(row_value(job, "robot_duid") or "")
        robot = robot_by_duid.get(duid)
        provider = str(row_value(robot, "provider") or "roborock").lower() if robot else "roborock"
        robot_samples = samples_by_duid.get(duid, [])
        details = build_job(job, robot_samples, {}, provider)
        started_at = utc_naive_to_local_naive(row_value(job, "begin_at"))
        ended_at = utc_naive_to_local_naive(row_value(job, "end_at"))
        elapsed_minutes = (
            round(max(0, (ended_at - started_at).total_seconds()) / 60, 1)
            if started_at and ended_at
            else details.get("durationMinutes")
        )
        details["elapsedMinutes"] = elapsed_minutes
        has_job_telemetry = any(
            started_at
            and ended_at
            and (stamp := normalize_local_naive(row_value(sample, "timestamp"))) is not None
            and started_at - timedelta(minutes=3) <= stamp <= ended_at + timedelta(minutes=12)
            for sample in robot_samples
        )
        if provider == "roborock" and not has_job_telemetry:
            details["cleaningType"] = "unknown"
            details["cleaningTypeLabel"] = "Rengjøring"
            details["modeLabel"] = "Type ikke logget"
        rows.append(
            {
                **details,
                "id": f"{duid}-{details['recordId']}",
                "robotDuid": duid,
                "robotName": str(row_value(robot, "name") or "Ukjent robot"),
                "robotModel": row_value(robot, "model"),
                "provider": provider,
            }
        )

    rows.sort(key=lambda row: row.get("startedAt") or "", reverse=True)
    elapsed_minutes = sum(float(row.get("elapsedMinutes") or 0) for row in rows)
    area_m2 = sum(float(row.get("areaM2") or 0) for row in rows)
    active_robots = {str(row.get("robotDuid") or "") for row in rows}
    next_week = min(week_start + timedelta(days=7), current_week)
    iso_year, iso_week, _ = week_start.isocalendar()
    return {
        "generatedAt": _local_iso(now),
        "period": {
            "week": iso_week_key(week_start),
            "weekNumber": iso_week,
            "year": iso_year,
            "startDate": week_start.isoformat(),
            "endDate": week_end.isoformat(),
            "previousWeek": iso_week_key(week_start - timedelta(days=7)),
            "nextWeek": iso_week_key(next_week),
            "canNext": week_start < current_week,
            "isCurrent": week_start == current_week,
        },
        "summary": {
            "jobs": len(rows),
            "elapsedMinutes": round(elapsed_minutes, 1),
            "areaM2": round(area_m2, 1),
            "robots": len(active_robots),
        },
        "jobs": rows,
    }
