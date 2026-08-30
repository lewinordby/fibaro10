"""Common services with explicit process dependencies."""

from dataclasses import dataclass
from datetime import date, datetime
from fibaro_core.schemas import EventDataIn
from pydantic import BaseModel
from sqlalchemy import func
from time_formatting import local_now_naive, normalize_local_naive
from typing import Any, Callable, Dict, Optional
import json
import re


@dataclass
class Dependencies:
    pass


def create_service(dependencies: Dependencies):

    def json_safe_model_payload(model: BaseModel) -> Dict[str, Any]:
        if hasattr(model, "model_dump"):
            return model.model_dump(mode="json")
        return json.loads(model.json())

    def value_from_payload(data: EventDataIn, key: str):
        explicit = getattr(data, key)
        if explicit is not None:
            return explicit
        return data.values.get(key)

    def json_value(value):
        if isinstance(value, (dict, list)):
            import json

            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value

    def minute_bucket(value: Optional[datetime]) -> datetime:
        stamp = normalize_local_naive(value) or local_now_naive()
        return stamp.replace(second=0, microsecond=0)

    def time_minutes(value: str) -> Optional[int]:
        try:
            hour, minute = str(value).split(":", 1)
            return int(hour) * 60 + int(minute)
        except (TypeError, ValueError):
            return None

    def average_value(values):
        present = [value for value in values if value is not None]
        if not present:
            return None
        return sum(present) / len(present)

    def latest_timestamp_from(*rows):
        timestamps = [row.timestamp for row in rows if row is not None and row.timestamp is not None]
        if not timestamps:
            return None
        return max(timestamps)

    def nested_extra_value(value, keys):
        if value is None:
            return None
        if isinstance(value, dict):
            for key in keys:
                found = value.get(key)
                if found not in (None, ""):
                    if isinstance(found, (dict, list)):
                        nested = nested_extra_value(found, keys)
                        if nested not in (None, ""):
                            return nested
                        continue
                    return found
            for child in value.values():
                found = nested_extra_value(child, keys)
                if found not in (None, ""):
                    return found
        elif isinstance(value, list):
            for child in value:
                found = nested_extra_value(child, keys)
                if found not in (None, ""):
                    return found
        return None

    def parse_boolish(value: Any) -> Optional[bool]:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            if value == 1:
                return True
            if value == 0:
                return False
        text = str(value).strip().lower()
        if text in {"true", "1", "yes", "ja", "on", "open", "opened", "åpen", "aapen"}:
            return True
        if text in {"false", "0", "no", "nei", "off", "closed", "close", "lukket", "stengt"}:
            return False
        return None

    def parse_optional_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value).strip())
        except ValueError:
            return None

    def exact_search_text(query: Optional[str]) -> Optional[str]:
        text_value = (query or "").strip()
        if len(text_value) >= 2 and text_value[0] == text_value[-1] and text_value[0] in {'"', "'"}:
            exact_value = text_value[1:-1].strip()
            return exact_value or None
        return None

    def normalized_exact_search_text(value: str) -> str:
        return re.sub(r"[^0-9A-Za-zÆØÅæøå_]+", " ", value).strip().lower()

    def exact_word_match(column, value: str):
        normalized_value = normalized_exact_search_text(value)
        if not normalized_value:
            return False
        normalized_column = func.lower(
            func.concat(
                " ",
                func.regexp_replace(func.coalesce(column, ""), r"[^[:alnum:]_]+", " ", "g"),
                " ",
            )
        )
        return normalized_column.like(f"% {normalized_value} %")

    def is_not_found_marker(value: Optional[str]) -> bool:
        return (value or "").strip().lower() == "ikke funnet"

    return {
        "average_value": average_value,
        "exact_search_text": exact_search_text,
        "exact_word_match": exact_word_match,
        "is_not_found_marker": is_not_found_marker,
        "json_safe_model_payload": json_safe_model_payload,
        "json_value": json_value,
        "latest_timestamp_from": latest_timestamp_from,
        "minute_bucket": minute_bucket,
        "nested_extra_value": nested_extra_value,
        "normalized_exact_search_text": normalized_exact_search_text,
        "parse_boolish": parse_boolish,
        "parse_optional_date": parse_optional_date,
        "time_minutes": time_minutes,
        "value_from_payload": value_from_payload,
    }
