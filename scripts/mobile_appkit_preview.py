"""Run a mobile app with harmless preview data for local visual QA."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import uvicorn


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def maintenance_app():
    import maintenance_mobile.app.main as mobile

    async def fake_request(
        path: str,
        token: str = "",
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        timeout: int = 25,
    ) -> dict[str, Any]:
        del token, payload, timeout
        if path == "/api/auth/session" and method == "POST":
            return {"sessionToken": "preview-session"}
        return {"username": "master"}

    def fake_bootstrap(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "user": {
                "username": "master",
                "displayName": "Master",
                "role": "Administrator",
                "roleLabel": "Administrator",
            },
            "cards": [],
            "recent": [
                {
                    "id": 1,
                    "summary": "Rengjort robotvaskere",
                    "target_type": "Utstyr",
                    "target_name": "1.etg A",
                    "action_type": "Rengjort",
                    "performed_at": "2026-08-08T09:42:00+02:00",
                    "performed_by": "master",
                    "status": "Utf\u00f8rt",
                    "duration_minutes": 12,
                    "follow_up_needed": False,
                    "tags": "Robotvaskere,Mobil,Rengjort",
                },
                {
                    "id": 2,
                    "summary": "Renset filter",
                    "target_type": "Utstyr",
                    "target_name": "Varmepumpe VIP",
                    "action_type": "Vedlikehold",
                    "performed_at": "2026-08-07T16:15:00+02:00",
                    "performed_by": "master",
                    "status": "Utf\u00f8rt",
                    "duration_minutes": 8,
                    "follow_up_needed": True,
                    "follow_up_text": "Kontroller lyd ved neste bes\u00f8k",
                    "tags": "Varmepumper,Mobil",
                },
            ],
            "defaults": {
                "performed_at": "2026-08-08T10:30:00+02:00",
                "target_type": "Seng",
                "action_type": "Kontroll",
                "priority": "Normal",
                "status": "Utf\u00f8rt",
                "presence_type": "Tilstede Sun2",
            },
            "options": {
                "presence_type": [{"label": "Tilstede Sun2", "value": "Tilstede Sun2"}],
                "target_type": [
                    {"label": "Seng", "value": "Seng"},
                    {"label": "Utstyr", "value": "Utstyr"},
                ],
                "room_id": [
                    {"label": f"Solrom {room}", "value": str(room)}
                    for room in range(1, 13)
                ],
                "action_type": [{"label": "Kontroll", "value": "Kontroll"}],
                "priority": [{"label": "Normal", "value": "Normal"}],
                "status": [{"label": "Utf\u00f8rt", "value": "Utf\u00f8rt"}],
                "tags": [],
                "robots": [
                    {"label": name, "value": name}
                    for name in ("1.etg A", "1.etg B", "2.etg", "VIP")
                ],
            },
        }

    mobile.fibaro_request = fake_request
    mobile.bootstrap_payload = fake_bootstrap
    return mobile.app


def alarm_app():
    import alarm_mobile.app.main as mobile

    async def fake_request(
        path: str,
        token: str = "",
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        timeout: int = 25,
    ) -> dict[str, Any]:
        del path, token, method, payload, timeout
        return {"sessionToken": "preview-session", "username": "master"}

    async def fake_bootstrap(_token: str) -> dict[str, Any]:
        return {
            "generatedAt": "2026-08-08T10:30:00+02:00",
            "build": "preview",
            "user": {
                "username": "master",
                "displayName": "Master",
                "role": "Administrator",
            },
            "doors": {
                "summary": {"active_alarms": 1, "rooms_closed": 4, "rooms_total": 12},
                "active_alarms": [
                    {
                        "id": 42,
                        "room_id": "4",
                        "room_name": "Solrom 4",
                        "alarm_type": "closed_without_session",
                        "started_at": "2026-08-08T10:18:00+02:00",
                        "duration_seconds": 720,
                    }
                ],
                "rooms": [
                    {
                        "device_id": str(500 + room),
                        "room_id": str(room),
                        "name": f"Solrom {room}",
                        "is_open": room not in {4, 7, 9, 12},
                        "last_changed_at": "2026-08-08T10:12:00+02:00",
                    }
                    for room in range(1, 13)
                ],
                "other_doors": [],
                "history": [],
            },
            "bollards": {
                "summary": {
                    "active_incidents": 0,
                    "inspection_objects": 4,
                    "baseline_cameras": 3,
                    "calibrated_assets": 1,
                    "ai_anomalies": 0,
                },
                "settings": {},
                "runtime": {},
                "incidents": [],
                "monitors": [],
            },
            "notifications": {
                "channels": [
                    {
                        "key": "doors",
                        "name": "D\u00f8ralarmer",
                        "publishing_enabled": True,
                        "subscribe_url": "https://ntfy.sh/lilletorget-preview",
                    },
                    {
                        "key": "bollards",
                        "name": "Pullertvarsler",
                        "publishing_enabled": True,
                        "subscribe_url": "https://ntfy.sh/lilletorget-preview",
                    },
                ]
            },
            "errors": {},
        }

    mobile.fibaro_request = fake_request
    mobile.alarm_bootstrap = fake_bootstrap
    return mobile.app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("app", choices=("maintenance", "alarm"))
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    application = maintenance_app() if args.app == "maintenance" else alarm_app()
    uvicorn.run(application, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
