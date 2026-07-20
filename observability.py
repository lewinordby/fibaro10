from typing import Iterable, List, Optional

from api_types import HealthCheckPayload, HealthPayload, HealthSourcePayload, HealthStatus


ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"
STATIC_CACHE_CONTROL = "public, max-age=3600, must-revalidate"


def cache_control_for_path(path: str) -> Optional[str]:
    normalized = str(path or "")
    if normalized.startswith("/assets/"):
        return ASSET_CACHE_CONTROL
    if normalized.startswith("/static/"):
        return STATIC_CACHE_CONTROL
    return None


def response_timing_headers(duration_ms: float) -> dict[str, str]:
    normalized = max(0.0, float(duration_ms))
    return {
        "Server-Timing": f"app;dur={normalized:.1f}",
        "X-Response-Time": f"{normalized:.1f}ms",
    }


STORAGE_TABLES = [
    "utelys_events", "utelys_samples", "ventilasjon_events", "ventilasjon_samples",
    "yr_forecast_samples", "control_configs", "control_config_history", "event_data", "door_events", "alarm_events",
    "roborock_robots", "roborock_status_samples", "roborock_clean_jobs",
    "roborock_schedules", "roborock_consumables", "roborock_maps",
    "import_job_status", "import_job_runs", "owntracks_devices", "owntracks_locations",
    "owntracks_waypoints", "owntracks_waypoint_events",
    "sun2_room_daily_stats", "sun2_import_runs", "sun2_tanning_sessions",
    "sun2_beds", "sun2_session_import_runs", "sun2_product_sales", "sun2_finance_settlements", "energy_hourly_consumption",
    "energy_import_runs", "energy_fibaro_samples", "energy_circuits", "energy_loads", "hc3_meter_readings",
    "parkering", "kjoretoy", "kjoretoy_nokkeldata", "ai_query_logs", "schema_migrations",
]


def health_payload(
    *,
    app_version: str,
    app_build: str,
    app_commit: str,
    started_at: str,
    database: HealthCheckPayload,
    sources: Optional[Iterable[HealthSourcePayload]] = None,
) -> HealthPayload:
    source_rows: List[HealthSourcePayload] = list(sources or [])
    source_counts = {
        "total": len(source_rows),
        "ok": sum(1 for row in source_rows if row.get("status") == "ok"),
        "warn": sum(1 for row in source_rows if row.get("status") == "warn"),
        "bad": sum(1 for row in source_rows if row.get("status") == "bad"),
        "unknown": sum(1 for row in source_rows if row.get("status") not in {"ok", "warn", "bad"}),
    }
    status: HealthStatus = "ok" if database.get("status") == "ok" else "bad"
    if any(row.get("status") == "bad" for row in source_rows):
        status = "warn" if status == "ok" else status
    elif any(row.get("status") == "warn" for row in source_rows):
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
        "summary": {
            "sources": source_counts,
        },
        "sources": source_rows,
        "storage": STORAGE_TABLES,
    }
