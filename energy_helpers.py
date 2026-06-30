from datetime import date, datetime
from typing import Any, Dict, Optional
from urllib.parse import urlencode
import calendar
import json
import re

from value_parsing import bool_value, float_value


def form_text(form, key: str) -> Optional[str]:
    value = form.get(key)
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def form_int(form, key: str) -> Optional[int]:
    value = form_text(form, key)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def form_float(form, key: str) -> Optional[float]:
    value = form_text(form, key)
    if value is None:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def form_bool(form, key: str, default: bool = False) -> bool:
    if key not in form:
        return default
    return str(form.get(key)).strip().lower() in {"1", "true", "on", "yes", "ja"}


def circuit_technical_label(circuit: Any) -> str:
    parts = []
    if circuit.breaker_type:
        parts.append(circuit.breaker_type)
    if circuit.breaker_rating_a is not None:
        parts.append(f"{circuit.breaker_rating_a:g} A")
    if circuit.breaker_characteristic:
        parts.append(str(circuit.breaker_characteristic))
    return " / ".join(parts) if parts else "-"


def energy_circuit_is_sunbed(circuit: Any) -> bool:
    if circuit.is_sunbed is not None:
        return bool(circuit.is_sunbed)
    return "solseng" in (circuit.description or "").strip().lower()


def normalize_energy_sunbed_filter(value: Optional[str]) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"hide", "skjul", "exclude", "nei", "0"}:
        return "hide"
    if normalized in {"only", "kun", "ja", "1"}:
        return "only"
    return ""


def filter_energy_circuits_by_sunbed(circuits: list[Any], sunbeds: Optional[str]) -> list[Any]:
    sunbed_filter = normalize_energy_sunbed_filter(sunbeds)
    if sunbed_filter == "hide":
        return [row for row in circuits if not energy_circuit_is_sunbed(row)]
    if sunbed_filter == "only":
        return [row for row in circuits if energy_circuit_is_sunbed(row)]
    return circuits


def energy_query_url(path: str, **params: Any) -> str:
    clean = {key: value for key, value in params.items() if value not in (None, "", False)}
    query = urlencode(clean)
    return f"{path}?{query}" if query else path


def _consumption_value(value: Any) -> Optional[float]:
    if not isinstance(value, dict):
        return None
    return float_value(value.get("Value"))


def meter_id_from_filename(filename: Optional[str]) -> str:
    match = re.match(r"(\d+)", filename or "")
    return match.group(1) if match else "elvia"


def parse_elvia_json_payload(content: bytes, filename: str) -> Dict[str, Any]:
    data = json.loads(content.decode("utf-8-sig"))
    meter_id = meter_id_from_filename(filename)
    rows: list[Dict[str, Any]] = []
    day_ids = set()
    month_days: Dict[str, set[int]] = {}
    estimated_hours = 0

    for year_data in data.get("Years") or []:
        for month_data in year_data.get("Months") or []:
            for day_data in month_data.get("Days") or []:
                day = date(int(day_data["Year"]), int(day_data["Month"]), int(day_data["Day"]))
                day_ids.add(day)
                month_key = f"{day.year:04d}-{day.month:02d}"
                month_days.setdefault(month_key, set()).add(day.day)
                for hour_data in day_data.get("Hours") or []:
                    measured_at = datetime(
                        int(hour_data["Year"]),
                        int(hour_data["Month"]),
                        int(hour_data["Day"]),
                        int(hour_data["Hour"]),
                    )
                    consumption = _consumption_value(hour_data.get("Consumption"))
                    if consumption is None:
                        continue
                    production = _consumption_value(hour_data.get("Production"))
                    status = (hour_data.get("Consumption") or {}).get("Status")
                    is_estimated = status != "OK"
                    if is_estimated:
                        estimated_hours += 1
                    rows.append(
                        {
                            "meter_id": meter_id,
                            "measured_at": measured_at,
                            "stat_date": measured_at.date(),
                            "year": measured_at.year,
                            "month": measured_at.month,
                            "day": measured_at.day,
                            "hour": measured_at.hour,
                            "consumption_kwh": consumption,
                            "production_kwh": production,
                            "status": status,
                            "is_verified": bool_value((hour_data.get("Consumption") or {}).get("IsVerified")),
                            "is_estimated": is_estimated,
                            "is_public_holiday": bool_value(hour_data.get("IsPublicHoliday")),
                            "use_weekend_prices": bool_value(hour_data.get("UseWeekendPrices")),
                            "raw": hour_data,
                        }
                    )

    rows.sort(key=lambda item: item["measured_at"])
    first_at = rows[0]["measured_at"] if rows else None
    last_at = rows[-1]["measured_at"] if rows else None
    partial_months = []
    for month_key, days in sorted(month_days.items()):
        year_number, month_number = [int(part) for part in month_key.split("-")]
        expected_days = calendar.monthrange(year_number, month_number)[1]
        if len(days) != expected_days:
            partial_months.append(
                {
                    "month": month_key,
                    "days": len(days),
                    "expected_days": expected_days,
                    "first_day": min(days),
                    "last_day": max(days),
                }
            )
    return {
        "meter_id": meter_id,
        "rows": rows,
        "first_at": first_at,
        "last_at": last_at,
        "days_count": len(day_ids),
        "hours_count": len(rows),
        "total_kwh": sum(row["consumption_kwh"] for row in rows),
        "estimated_hours_count": estimated_hours,
        "partial_months": partial_months,
        "source_file": filename,
    }
