"""Acquisition health is independent of the last visual inspection result."""

from datetime import datetime
from time_formatting import normalize_local_naive


def bollard_collection_issues(payload: dict, now: datetime) -> tuple[list[str], datetime | None]:
    runtime = payload.get("runtime") or {}
    settings = payload.get("settings") or {}
    summary = payload.get("summary") or {}
    issues = []
    try:
        updated = normalize_local_naive(datetime.fromisoformat(runtime.get("last_success_at") or ""))
    except (ValueError, TypeError):
        updated = None
    if settings.get("monitoring_enabled") is False:
        issues.append("Bildekontrollen er deaktivert.")
    if runtime.get("running") is False:
        issues.append("Bildekontrollen kjører ikke.")
    if runtime.get("last_error"):
        issues.append(f"Siste kontroll feilet: {str(runtime['last_error'])[:200]}")
    if updated is None:
        issues.append("Tidspunktet for siste vellykkede bildekontroll mangler.")
    else:
        interval = max(60, int(settings.get("analysis_interval_seconds") or 300))
        age = (normalize_local_naive(now) - updated).total_seconds()
        if age < -60:
            issues.append("Kontrollens tidspunkt ligger frem i tid; kontroller systemklokken.")
        elif age > interval * 2 + 60:
            issues.append(f"Siste vellykkede bildekontroll er {int(age // 60)} minutter gammel.")
    target = int(summary.get("target_cameras") or 0)
    connected = summary.get("connected_cameras")
    if target and (connected is None or int(connected) < target):
        issues.append(f"Kamerastatus viser {connected if connected is not None else '?'} av {target} tilkoblet; må kontrolleres mot siste bildekontroll.")
    return issues, updated
