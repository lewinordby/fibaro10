from typing import Any, Optional
from urllib.parse import urlencode


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
