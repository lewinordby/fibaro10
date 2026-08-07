from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterable, Mapping, Optional


INCIDENT_SEVERITIES = {"critical", "warning", "info"}
INCIDENT_SEVERITY_PRIORITY = {"critical": 0, "warning": 1, "info": 2}
CONTROL_STATUSES = {"ok", "warning", "critical", "unknown"}


def _serialized_time(value: Any) -> Optional[str]:
    return value.isoformat() if isinstance(value, datetime) else (str(value) if value else None)


def parse_status_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip():
            values[key.strip()] = value.strip()
    return values


def parse_status_timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    for pattern in ("%Y%m%d-%H%M%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], pattern)
        except ValueError:
            continue
    return None


def backup_control(
    *,
    key: str,
    title: str,
    values: Mapping[str, Any],
    now: datetime,
    warning_after_hours: float,
    critical_after_hours: float,
    path: str = "/manual/oversikt",
) -> dict[str, Any]:
    raw_status = str(values.get("status") or "missing").strip().lower()
    finished_at = parse_status_timestamp(values.get("finished"))
    started_at = parse_status_timestamp(values.get("started"))
    observed_at = finished_at or started_at
    age_hours = max(0.0, (now - observed_at).total_seconds() / 3600) if observed_at else None

    if raw_status in {"error", "failed", "missing"} or observed_at is None:
        status = "critical"
    elif age_hours is not None and age_hours > critical_after_hours:
        status = "critical"
    elif raw_status in {"warning", "running"} or (
        age_hours is not None and age_hours > warning_after_hours
    ):
        status = "warning"
    else:
        status = "ok"

    if observed_at is None:
        detail = "Ingen gyldig backupstatus funnet."
    elif raw_status == "running":
        detail = f"Kjører nå, startet {started_at.strftime('%d.%m %H:%M')}."
    else:
        age_label = f"{age_hours:.1f} t siden" if age_hours is not None else "ukjent alder"
        detail = f"Sist fullført {observed_at.strftime('%d.%m %H:%M')} ({age_label})."
        if values.get("replica_status") == "error":
            detail += " Ekstern kopi feilet."

    return {
        "key": key,
        "title": title,
        "status": status if status in CONTROL_STATUSES else "unknown",
        "statusLabel": {"ok": "OK", "warning": "Kontroller", "critical": "Feil", "unknown": "Ukjent"}[status],
        "detail": detail,
        "updatedAt": _serialized_time(observed_at),
        "path": path,
        "rawStatus": raw_status,
        "ageHours": round(age_hours, 1) if age_hours is not None else None,
    }


def operational_incident(
    *,
    key: str,
    domain: str,
    title: str,
    detail: str,
    severity: str,
    source: str,
    started_at: Any,
    observed_at: Any = None,
    recommended_action: str = "",
    path: str = "",
    metadata: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    normalized_severity = str(severity or "warning").strip().lower()
    if normalized_severity not in INCIDENT_SEVERITIES:
        normalized_severity = "warning"
    return {
        "key": str(key),
        "domain": str(domain),
        "title": str(title),
        "detail": str(detail or ""),
        "severity": normalized_severity,
        "severityLabel": {"critical": "Kritisk", "warning": "Kontroller", "info": "Informasjon"}[
            normalized_severity
        ],
        "source": str(source or domain),
        "startedAt": _serialized_time(started_at),
        "observedAt": _serialized_time(observed_at or started_at),
        "recommendedAction": str(recommended_action or ""),
        "path": str(path or ""),
        "metadata": dict(metadata or {}),
        "reviewState": "open",
        "reviewedAt": None,
        "reviewedBy": None,
        "reviewNote": "",
    }


def apply_incident_reviews(
    incidents: Iterable[dict[str, Any]],
    reviews: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for incident in incidents:
        row = dict(incident)
        review = reviews.get(str(row.get("key") or ""))
        if review:
            reviewed_at = parse_status_timestamp(review.get("reviewed_at") or review.get("reviewedAt"))
            started_at = parse_status_timestamp(row.get("startedAt"))
            applies = not started_at or not reviewed_at or reviewed_at >= started_at
            if applies:
                state = str(review.get("status") or "open").strip().lower()
                row["reviewState"] = "acknowledged" if state == "acknowledged" else "open"
                row["reviewedAt"] = _serialized_time(reviewed_at)
                row["reviewedBy"] = review.get("reviewed_by") or review.get("reviewedBy")
                row["reviewNote"] = str(review.get("note") or review.get("reviewNote") or "")
        rows.append(row)
    return sort_incidents(rows)


def sort_incidents(incidents: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        list(incidents),
        key=lambda row: (
            1 if row.get("reviewState") == "acknowledged" else 0,
            INCIDENT_SEVERITY_PRIORITY.get(str(row.get("severity") or "warning"), 1),
            str(row.get("startedAt") or ""),
            str(row.get("title") or ""),
        ),
        reverse=False,
    )


def incident_summary(incidents: Iterable[dict[str, Any]]) -> dict[str, int]:
    rows = list(incidents)
    return {
        "active": len(rows),
        "critical": sum(1 for row in rows if row.get("severity") == "critical"),
        "warning": sum(1 for row in rows if row.get("severity") == "warning"),
        "info": sum(1 for row in rows if row.get("severity") == "info"),
        "acknowledged": sum(1 for row in rows if row.get("reviewState") == "acknowledged"),
        "unreviewed": sum(1 for row in rows if row.get("reviewState") != "acknowledged"),
        "domains": len({str(row.get("domain") or "") for row in rows if row.get("domain")}),
    }
