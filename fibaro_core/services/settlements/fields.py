"""Individual parsed fields and their confidence/source presentation."""
from typing import Any, Dict, Optional
from fibaro_core.services.presentation import api_iso_value
from fibaro_core.services.settlements.parsing import (
    parse_settlement_number, settlement_field_confidence,
    settlement_field_source, settlement_number_value,
)

def settlement_field(
    label: str,
    field: str,
    value: Any,
    source: str,
    note: str = "",
    confidence: Optional[float] = None,
) -> Dict[str, Any]:
    payload = {
        "label": label,
        "field": field,
        "value": api_iso_value(value),
        "source": source,
        "note": note,
    }
    if confidence is not None:
        payload["confidence"] = round(max(0.0, min(1.0, confidence)), 2)
    return payload


def settlement_form_field(
    label: str,
    field: str,
    value: Any,
    parsed: Any,
    group: str,
    note: str,
    expected: Optional[float] = None,
    expected_label: str = "Beregnet",
    expected_source: str = "",
    expected_detail: str = "",
    difference_direction: str = "value_minus_expected",
) -> Dict[str, Any]:
    payload = settlement_field(
        label,
        field,
        value,
        settlement_field_source(parsed, field),
        note,
        settlement_field_confidence(parsed, field),
    )
    payload["group"] = group
    if expected is not None:
        numeric_value = parse_settlement_number(value)
        payload["expected"] = settlement_number_value(expected)
        payload["expectedLabel"] = expected_label
        if expected_source:
            payload["expectedSource"] = expected_source
        if expected_detail:
            payload["expectedDetail"] = expected_detail
        if numeric_value is not None:
            if difference_direction == "expected_minus_value":
                difference = round(expected - float(numeric_value), 2)
            else:
                difference = round(float(numeric_value) - expected, 2)
            payload["difference"] = settlement_number_value(difference)
            payload["status"] = "ok" if abs(difference) <= 1 else "warn"
        else:
            payload["status"] = "missing"
    elif value is None or value == "":
        payload["status"] = "missing"
    else:
        payload["status"] = "ok"
    return payload
