"""Read-only preparation for the next night, using the existing schedule decoder."""

from datetime import time, timedelta
from roborock_reports import report_window, schedule_occurrences


def night_preparation(robot, schedules, now):
    report_day = now.date() if now.time() < time(8) else now.date() + timedelta(days=1)
    window = report_window(report_day)
    readiness = robot.get("readiness") or {}
    interlock = readiness.get("water_interlock") or {}
    paused_ids = {str(row.get("schedule_id")) for row in interlock.get("paused_schedules") or []}
    selected = [row for row in schedules if row.enabled is True or str(row.schedule_id) in paused_ids]
    occurrences = schedule_occurrences(selected, window, provider=robot.get("provider", "roborock"), include_paused=True)
    future = [row for row in occurrences if row["scheduledAtValue"] >= now]
    for row in future:
        row.pop("scheduledAtValue", None)
        row["paused"] = row["paused"] or row["scheduleId"] in paused_ids
    issues = list(readiness.get("issues") or [])
    paused = sum(row["paused"] for row in future)
    if paused:
        issues.append(f"{paused} planer er satt på pause")
    if interlock.get("last_error"):
        issues.append("Feil i vannsperre: " + str(interlock["last_error"]))
    if robot.get("integration_status") == "pending" or readiness.get("telemetry_at") is None:
        issues.append("Mangler oppdatert robotgrunnlag")
    if robot.get("cloud_online") is False:
        issues.append("Roboten er frakoblet")
    return {
        "day": report_day.isoformat(), "plans": future,
        "status": "attention" if issues else "planned" if future else "unplanned",
        "label": "Krever kontroll" if issues else "Planlagt" if future else "Ingen gjenstående nattplan",
        "issues": list(dict.fromkeys(issues)),
    }
