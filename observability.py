from typing import Any, Dict, Iterable, List, Optional


STORAGE_TABLES = [
    "utelys_events", "utelys_samples", "ventilasjon_events", "ventilasjon_samples",
    "yr_forecast_samples", "control_configs", "control_config_history", "event_data",
    "roborock_robots", "roborock_status_samples", "roborock_clean_jobs",
    "roborock_schedules", "roborock_consumables", "roborock_maps",
    "import_job_status", "import_job_runs",
    "sun2_room_daily_stats", "sun2_import_runs", "sun2_tanning_sessions",
    "sun2_beds", "sun2_session_import_runs", "energy_hourly_consumption",
    "energy_import_runs", "energy_fibaro_samples", "energy_circuits", "energy_loads", "hc3_meter_readings",
    "parkering", "kjoretoy", "kjoretoy_nokkeldata", "ai_query_logs", "schema_migrations",
]


def health_payload(
    *,
    app_version: str,
    app_build: str,
    app_commit: str,
    started_at: str,
    database: Dict[str, Any],
    sources: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    source_rows: List[Dict[str, Any]] = list(sources or [])
    status = "ok" if database.get("status") == "ok" else "bad"
    if any(row.get("status") == "bad" for row in source_rows):
        status = "warn" if status == "ok" else status
    return {
        "status": status,
        "app": {
            "version": str(app_version),
            "build": str(app_build),
            "commit": str(app_commit or "unknown"),
            "startedAt": started_at,
        },
        "checks": {
            "database": database,
        },
        "sources": source_rows,
        "storage": STORAGE_TABLES,
    }
