from __future__ import annotations

from typing import Any


SUPPORTED_CLEANING_PROVIDERS = {"roborock", "dreame"}


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
