from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unifi_protect_client import ProtectLedgerClient


def main() -> int:
    client = ProtectLedgerClient(
        os.environ["UNIFI_PROTECT_EVENTS_URL"],
        os.environ["UNIFI_PROTECT_READ_API_TOKEN"],
    )
    status = client.status()
    stats = client.stats()
    capabilities = client.capabilities()
    events = client.events(limit=10, has_snapshot=True)
    recognitions = client.recognitions(limit=10)
    item = events["items"][0] if events["items"] else None
    recognition = recognitions["items"][0] if recognitions["items"] else None
    recognition_detail = client.recognition_detail(recognition["recognition_id"]) if recognition else None
    content = b""
    content_type = ""
    if item:
        content, content_type = client.snapshot(item["source_event_id"])
    print(f"internal_api_status={status['status']}")
    print(f"local_only={status['local_only']}")
    print(f"events_with_snapshot={len(events['items'])}")
    print(f"stats_event_count={stats['events'].get('event_count', 0)}")
    print(f"capability_types={len(capabilities.get('detection_types', []))}")
    print(f"recognitions={len(recognitions['items'])}")
    print(f"recognition_detail={bool(recognition_detail)}")
    print(f"snapshot_jpeg={bool(content.startswith(bytes((0xFF, 0xD8))) and content_type == 'image/jpeg')}")
    print(f"snapshot_bytes={len(content)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
