from __future__ import annotations

from datetime import date, datetime
import math
from typing import Any, Iterable, Optional


RECONCILIATION_STATUSES = {"ok", "warning", "critical", "missing", "info"}
STATUS_LABELS = {
    "ok": "Stemmer",
    "warning": "Kontroller",
    "critical": "Avvik",
    "missing": "Mangler grunnlag",
    "info": "Til oppfolging",
}
STATUS_PRIORITY = {
    "critical": 0,
    "warning": 1,
    "missing": 2,
    "info": 3,
    "ok": 4,
}


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _serialized(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def reconciliation_difference(actual: Any, reference: Any) -> Optional[float]:
    actual_value = _number(actual)
    reference_value = _number(reference)
    if actual_value is None or reference_value is None:
        return None
    return round(actual_value - reference_value, 3)


def reconciliation_difference_percent(difference: Any, reference: Any) -> Optional[float]:
    difference_value = _number(difference)
    reference_value = _number(reference)
    if difference_value is None or reference_value in {None, 0.0}:
        return None
    return round((difference_value / abs(reference_value)) * 100, 2)


def reconciliation_allowed_difference(
    reference: Any,
    *,
    absolute_tolerance: float = 0.0,
    percent_tolerance: float = 0.0,
) -> float:
    reference_value = _number(reference)
    percent_limit = abs(reference_value or 0.0) * max(0.0, percent_tolerance) / 100
    return round(max(max(0.0, absolute_tolerance), percent_limit), 3)


def evaluate_reconciliation(
    *,
    check_id: str,
    domain: str,
    title: str,
    actual_label: str,
    actual_value: Any,
    reference_label: str,
    reference_value: Any,
    unit: str,
    period: str = "",
    absolute_tolerance: float = 0.0,
    percent_tolerance: float = 0.0,
    critical_multiplier: float = 3.0,
    confidence: Optional[float] = None,
    detail: str = "",
    path: str = "",
    updated_at: Any = None,
) -> dict[str, Any]:
    actual = _number(actual_value)
    reference = _number(reference_value)
    difference = reconciliation_difference(actual, reference)
    difference_percent = reconciliation_difference_percent(difference, reference)
    allowed_difference = reconciliation_allowed_difference(
        reference,
        absolute_tolerance=absolute_tolerance,
        percent_tolerance=percent_tolerance,
    )

    if actual is None or reference is None:
        status = "missing"
    elif abs(difference or 0.0) <= allowed_difference:
        status = "ok"
    elif allowed_difference > 0 and abs(difference or 0.0) <= allowed_difference * max(1.0, critical_multiplier):
        status = "warning"
    else:
        status = "critical"

    parsed_confidence = _number(confidence)
    return {
        "id": check_id,
        "domain": domain,
        "title": title,
        "period": period,
        "status": status,
        "status_label": STATUS_LABELS[status],
        "actual_label": actual_label,
        "actual_value": actual,
        "reference_label": reference_label,
        "reference_value": reference,
        "difference": difference,
        "difference_percent": difference_percent,
        "unit": unit,
        "absolute_tolerance": round(max(0.0, absolute_tolerance), 3),
        "percent_tolerance": round(max(0.0, percent_tolerance), 3),
        "allowed_difference": allowed_difference,
        "confidence": round(max(0.0, min(100.0, parsed_confidence)), 1) if parsed_confidence is not None else None,
        "detail": detail,
        "path": path,
        "updated_at": _serialized(updated_at),
    }


def state_reconciliation(
    *,
    check_id: str,
    domain: str,
    title: str,
    status: str,
    value_label: str,
    value: Any,
    unit: str = "",
    period: str = "",
    detail: str = "",
    path: str = "",
    updated_at: Any = None,
    confidence: Optional[float] = None,
) -> dict[str, Any]:
    normalized_status = str(status or "missing").strip().lower()
    if normalized_status not in RECONCILIATION_STATUSES:
        normalized_status = "missing"
    parsed_confidence = _number(confidence)
    return {
        "id": check_id,
        "domain": domain,
        "title": title,
        "period": period,
        "status": normalized_status,
        "status_label": STATUS_LABELS[normalized_status],
        "actual_label": value_label,
        "actual_value": _number(value),
        "reference_label": "",
        "reference_value": None,
        "difference": None,
        "difference_percent": None,
        "unit": unit,
        "absolute_tolerance": 0.0,
        "percent_tolerance": 0.0,
        "allowed_difference": 0.0,
        "confidence": round(max(0.0, min(100.0, parsed_confidence)), 1) if parsed_confidence is not None else None,
        "detail": detail,
        "path": path,
        "updated_at": _serialized(updated_at),
    }


def reconciliation_summary(checks: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(checks)
    counts = {status: 0 for status in RECONCILIATION_STATUSES}
    for row in rows:
        status = str(row.get("status") or "missing")
        counts[status if status in counts else "missing"] += 1
    attention = counts["critical"] + counts["warning"] + counts["missing"]
    overall_status = min(
        (str(row.get("status") or "missing") for row in rows),
        key=lambda status: STATUS_PRIORITY.get(status, STATUS_PRIORITY["missing"]),
        default="missing",
    )
    return {
        "total": len(rows),
        "ok": counts["ok"],
        "warning": counts["warning"],
        "critical": counts["critical"],
        "missing": counts["missing"],
        "info": counts["info"],
        "attention": attention,
        "overall_status": overall_status,
        "overall_label": STATUS_LABELS[overall_status],
    }


def reconciliation_group(
    group_id: str,
    title: str,
    description: str,
    checks: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    rows = sorted(
        list(checks),
        key=lambda row: (
            STATUS_PRIORITY.get(str(row.get("status") or "missing"), STATUS_PRIORITY["missing"]),
            str(row.get("period") or ""),
            str(row.get("title") or ""),
        ),
    )
    return {
        "id": group_id,
        "title": title,
        "description": description,
        "summary": reconciliation_summary(rows),
        "checks": rows,
    }
