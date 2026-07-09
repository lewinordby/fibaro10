from typing import Optional

from api_types import BuildLogEntryPayload, BuildLogResponsePayload
from build_log import APP_BUILD, BUILD_LOG, build_log_entry_by_build, build_log_list_row, normalized_build_log_entry


def admin_builds_payload() -> BuildLogResponsePayload:
    return {
        "currentBuild": APP_BUILD,
        "rows": [build_log_list_row(row) for row in BUILD_LOG],
    }


def admin_build_payload(build: str) -> Optional[BuildLogEntryPayload]:
    row = build_log_entry_by_build(build)
    if not row:
        return None
    return normalized_build_log_entry(row)
