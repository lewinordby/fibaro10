from __future__ import annotations

from typing import Any


SUPPORTED_CLEANING_PROVIDERS = {"roborock", "dreame"}
CLEANING_ROBOT_STATUS_STALE_AFTER_MINUTES = 20
CLEANING_ROBOT_ACTIVE_STATE_CODES = {6, 7, 11, 15, 16, 17, 18, 22, 23, 26, 28}
CLEANING_ROBOT_DISPLAY_ORDER = {
    "1.etg b": 0,
    "1.etg a": 1,
    "vip": 2,
    "2.etg": 3,
}


def _cleaning_robot_has_error_code(value: Any) -> bool:
    if value is None:
        return False
    try:
        return float(value) != 0
    except (TypeError, ValueError):
        return bool(str(value).strip())


def cleaning_robot_sort_key(value: Any) -> tuple[int, str]:
    if isinstance(value, dict):
        name = value.get("name")
    else:
        name = getattr(value, "name", value)
    normalized_name = str(name or "").strip().casefold()
    return (
        CLEANING_ROBOT_DISPLAY_ORDER.get(normalized_name, len(CLEANING_ROBOT_DISPLAY_ORDER)),
        normalized_name,
    )


def cleaning_robot_is_active(in_cleaning: Any, state_code: Any = None, provider: Any = None) -> bool:
    if in_cleaning is True:
        return True
    if cleaning_provider(provider) != "roborock":
        return False
    try:
        normalized_state_code = int(state_code) if state_code is not None else None
    except (TypeError, ValueError):
        normalized_state_code = None
    return normalized_state_code in CLEANING_ROBOT_ACTIVE_STATE_CODES


def cleaning_robot_operational_state(
    *,
    integration_status: Any = None,
    cloud_online: Any = None,
    last_error: Any = None,
    error_code: Any = None,
    data_age_minutes: Any = None,
    active: bool = False,
    pending_label: Any = None,
    active_label: Any = None,
    ready_label: Any = None,
    stale_after_minutes: float = CLEANING_ROBOT_STATUS_STALE_AFTER_MINUTES,
) -> tuple[str, str]:
    """Return the shared operational status used by cleaning-robot overviews."""
    integration = str(integration_status or "active").strip().lower()
    if integration == "pending":
        return "pending", str(pending_label or "Venter på oppsett")
    if cloud_online is False:
        return "error", "Frakoblet"
    if last_error or _cleaning_robot_has_error_code(error_code):
        return "error", "Feil"
    try:
        age_minutes = float(data_age_minutes) if data_age_minutes is not None else None
    except (TypeError, ValueError):
        age_minutes = None
    if age_minutes is None or age_minutes > stale_after_minutes:
        return "warning", "Utdatert status"
    if active:
        return "active", str(active_label or "Rengjør")
    return "ok", str(ready_label or "Klar")


def cleaning_provider(value: Any = None, source: Any = None) -> str:
    explicit = str(value or "").strip().lower()
    if explicit in SUPPORTED_CLEANING_PROVIDERS:
        return explicit
    source_name = str(source or "").strip().lower()
    return "dreame" if source_name.startswith("dreame") else "roborock"


def cleaning_robot_uid(provider: Any, external_id: Any) -> str:
    provider_name = cleaning_provider(provider)
    identity = str(external_id or "").strip()
    if not identity:
        return ""
    if provider_name == "roborock" or identity.startswith(f"{provider_name}:"):
        return identity
    return f"{provider_name}:{identity}"


def cleaning_robot_external_id(provider: Any, value: Any) -> str:
    provider_name = cleaning_provider(provider)
    identity = str(value or "").strip()
    prefix = f"{provider_name}:"
    return identity[len(prefix):] if identity.startswith(prefix) else identity


def cleaning_provider_label(provider: Any) -> str:
    return "Dreame" if cleaning_provider(provider) == "dreame" else "Roborock"


def expected_dreame_summary(name: str = "Aqua10") -> dict[str, Any]:
    return {
        "duid": "pending:dreame:aqua10",
        "external_id": None,
        "provider": "dreame",
        "provider_label": "Dreame",
        "name": name,
        "model": "Dreame Aqua10",
        "integration_status": "pending",
        "cloud_online": None,
        "last_seen_at": None,
        "last_error": None,
        "state_name": "Venter på tilkobling",
        "battery": None,
        "status_at": None,
        "latest_job_today": None,
        "latest_job_yesterday": None,
        "today": {
            "job_count": 0,
            "completed_count": 0,
            "running_count": 0,
            "error_count": 0,
            "duration_minutes": 0,
            "cleaned_area_m2": 0,
        },
        "yesterday": {
            "job_count": 0,
            "completed_count": 0,
            "running_count": 0,
            "error_count": 0,
            "duration_minutes": 0,
            "cleaned_area_m2": 0,
        },
        "active_cycle": None,
        "readiness": {
            "status": "pending",
            "label": "Ikke koblet til",
            "issues": ["Legg Aqua10 til i Dreamehome og konfigurer Dreame-loggeren."],
            "telemetry_at": None,
            "data_age_minutes": None,
            "charge_label": "Venter på data",
            "clear_water_label": "Venter på data",
            "dirty_water_label": "Venter på data",
            "dust_bag_label": "Venter på data",
            "dock_error_label": "Venter på data",
            "signal_label": "-",
        },
        "consumables": None,
        "schedules": {"active_count": 0, "next_label": None, "rounds_label": None},
    }
