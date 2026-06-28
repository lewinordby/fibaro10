from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo
import os


LOCAL_TZ = ZoneInfo("Europe/Oslo")
UNIFI_PROTECT_BASE_URL = os.getenv("UNIFI_PROTECT_BASE_URL", "https://unifi.ui.com").rstrip("/")
UNIFI_PROTECT_CONSOLE_ID = os.getenv(
    "UNIFI_PROTECT_CONSOLE_ID",
    "28704E24487D000000000821D3930000000008902F110000000066747401:303733909",
).strip()
UNIFI_PROTECT_PARKING_CAMERA_ID = os.getenv("UNIFI_PROTECT_PARKING_CAMERA_ID", "6a35340e009cef03e402fcb1").strip()
UNIFI_PROTECT_PARKING_PREVIEW_BEFORE_SECONDS = max(
    0,
    int(os.getenv("UNIFI_PROTECT_PARKING_PREVIEW_BEFORE_SECONDS", "120")),
)
UNIFI_PROTECT_PARKING_PREVIEW_AFTER_SECONDS = max(
    0,
    int(os.getenv("UNIFI_PROTECT_PARKING_PREVIEW_AFTER_SECONDS", "300")),
)


def unifi_protect_parking_timelapse_url(
    target_at: Optional[datetime],
    before_seconds: Optional[int] = None,
) -> Optional[str]:
    if not target_at or not UNIFI_PROTECT_CONSOLE_ID or not UNIFI_PROTECT_PARKING_CAMERA_ID:
        return None
    preview_before_seconds = max(
        0,
        int(before_seconds if before_seconds is not None else UNIFI_PROTECT_PARKING_PREVIEW_BEFORE_SECONDS),
    )
    if target_at.tzinfo is None:
        target_local = target_at.replace(tzinfo=LOCAL_TZ)
    else:
        target_local = target_at.astimezone(LOCAL_TZ)
    start_at = target_local - timedelta(seconds=preview_before_seconds)
    end_at = target_local + timedelta(seconds=UNIFI_PROTECT_PARKING_PREVIEW_AFTER_SECONDS)
    params = urlencode(
        {
            "end": int(end_at.timestamp() * 1000),
            "start": int(start_at.timestamp() * 1000),
            "time": int(start_at.timestamp() * 1000),
        }
    )
    console_id = quote(UNIFI_PROTECT_CONSOLE_ID, safe=":")
    camera_id = quote(UNIFI_PROTECT_PARKING_CAMERA_ID, safe="")
    return f"{UNIFI_PROTECT_BASE_URL}/consoles/{console_id}/protect/timelapse/{camera_id}?{params}"
