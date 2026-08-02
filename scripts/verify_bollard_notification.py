from __future__ import annotations

import argparse
import hashlib
import json
import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def resolved_topic() -> tuple[str, str]:
    dedicated = os.getenv("PROTECT_BOLLARD_NTFY_TOPIC", "").strip()
    if dedicated:
        return dedicated, "dedicated"
    master_hash = os.getenv("MASTER_ACCESS_KEY_HASH", "").strip()
    if master_hash:
        topic_hash = hashlib.sha256(f"protect-bollards:{master_hash}".encode()).hexdigest()[:24]
        return f"protect-pullerter-{topic_hash}", "derived_dedicated"
    return "", "missing"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send-test", action="store_true")
    args = parser.parse_args()
    base_url = os.getenv("NTFY_BASE_URL", "https://ntfy.sh").rstrip("/")
    topic, source = resolved_topic()
    status = {
        "configured": bool(topic),
        "channel_source": source,
        "notification_host": urlparse(base_url).hostname,
        "test_sent": False,
    }
    if args.send_test:
        if not topic:
            raise RuntimeError("No bollard notification topic is configured")
        request = Request(
            f"{base_url}/{topic}",
            data=(
                "Test fra Protect Ledger: mobilvarsling for pullertovervåkingen er aktiv. "
                "Dette er bare en test; ingen hendelse er registrert."
            ).encode("utf-8"),
            headers={
                "Title": "Testvarsel – pullerter ved solstudio",
                "Priority": "4",
                "Tags": "white_check_mark,car",
            },
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f"Notification service returned HTTP {response.status}")
        status["test_sent"] = True
    print(json.dumps(status))


if __name__ == "__main__":
    main()
