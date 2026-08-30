import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from api_types import BuildLogEntryPayload, BuildLogListRowPayload, BuildLogTableRowPayload


APP_VERSION = os.getenv("APP_VERSION", "1")
BUILD_FILE = Path(__file__).with_name("BUILD")
DEFAULT_BUILD = BUILD_FILE.read_text(encoding="utf-8").strip() if BUILD_FILE.exists() else "1634"
APP_BUILD = os.getenv("APP_BUILD", DEFAULT_BUILD)
BUILD_LOG = json.loads(Path(__file__).with_name("build_history").joinpath("entries.json").read_text(encoding="utf-8"))


def normalized_build_log_entry(row: Dict[str, Any]) -> BuildLogEntryPayload:
    applications = row.get("applications") or []
    if not isinstance(applications, list):
        applications = [str(applications)] if applications else []
    changes = row.get("changes") or []
    if not isinstance(changes, list):
        changes = [str(changes)] if changes else []
    build = str(row.get("build", ""))
    description = row.get("description") or " ".join(str(item) for item in changes)
    return {
        "version": str(row.get("version", APP_VERSION)),
        "build": build,
        "date": str(row.get("date", "")),
        "headline": str(row.get("headline") or row.get("title") or f"Build {build}"),
        "title": str(row.get("title") or row.get("headline") or f"Build {build}"),
        "description": str(description or ""),
        "applications": [str(item) for item in applications],
        "changes": [str(item) for item in changes],
        "request": str(row.get("request") or ""),
        "workDuration": str(row.get("work_duration") or row.get("workDuration") or "Ikke registrert"),
        "creditsUsed": str(row.get("credits_used") or row.get("creditsUsed") or "Ikke registrert"),
        "path": f"/admin/build/{build}",
        "isCurrent": build == str(APP_BUILD),
    }


def build_log_list_row(row: Dict[str, Any]) -> BuildLogListRowPayload:
    build = str(row.get("build", ""))
    return {
        "build": build,
        "date": str(row.get("date", "")),
        "headline": str(row.get("headline") or row.get("title") or f"Build {build}"),
        "path": f"/admin/build/{build}",
        "isCurrent": build == str(APP_BUILD),
    }


def api_build_log_row(row: Dict[str, Any]) -> BuildLogTableRowPayload:
    normalized = normalized_build_log_entry(row)
    applications_text = "; ".join(normalized["applications"])
    return {
        "build": normalized["build"],
        "date": normalized["date"],
        "headline": normalized["headline"],
        "title": normalized["title"],
        "description": normalized["description"],
        "applications": applications_text,
        "request": normalized["request"],
        "work_duration": normalized["workDuration"],
        "credits_used": normalized["creditsUsed"],
        "path": normalized["path"],
    }


def build_log_entry_by_build(build: str) -> Optional[Dict[str, Any]]:
    build_value = str(build)
    for row in BUILD_LOG:
        if str(row.get("build", "")) == build_value:
            return row
    return None
