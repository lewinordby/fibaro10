from datetime import datetime, timezone
from typing import Any, Dict, Optional

from time_formatting import parse_datetime


def bool_value(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "ja"}:
            return True
        if normalized in {"0", "false", "no", "off", "nei"}:
            return False
    return None


def int_value(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def float_value(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        normalized = value.strip().replace("\u00a0", "").replace(" ", "")
        if "," in normalized and "." in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        elif "," in normalized:
            normalized = normalized.replace(",", ".")
        value = normalized
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def timestamp_value(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc).replace(tzinfo=None)
    if isinstance(value, str):
        parsed = parse_datetime(value)
        if parsed:
            return parsed
        try:
            return datetime.fromtimestamp(int(value), timezone.utc).replace(tzinfo=None)
        except (TypeError, ValueError):
            return None
    return None


def area_m2_from_payload(value: Any) -> Optional[float]:
    number = float_value(value)
    if number is None:
        return None
    if number > 100000:
        return round(number / 1_000_000, 2)
    return number


def first_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    if isinstance(value, dict):
        return value
    return {}
