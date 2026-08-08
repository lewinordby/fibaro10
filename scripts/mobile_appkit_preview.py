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


def online_app():
    import os
    import re

    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles

    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://preview:preview@127.0.0.1/preview")
    import online_dashboard.app.main as mobile

    preview = FastAPI(title="Online dashboard preview")
    preview.mount("/static", StaticFiles(directory=REPO_ROOT / "static"), name="static")
    preview.mount("/appkit-assets", StaticFiles(directory=REPO_ROOT / "packages" / "mobile-appkit"), name="appkit-assets")

    values = {
        "open_label": "Åpent",
        "open_detail": "Stenger 23:00",
        "energy_watt": "12,6 kW",
        "energy_kwh": "42,8 kWh",
        "energy_samples": "1 204",
        "energy_diff": "0,8 kW",
        "energy_time": "08.08 14:28",
        "soling_count": "27",
        "soling_yesterday_count": "31",
        "soling_time": "08.08 14:27",
        "parking_count": "42",
        "parking_yesterday_count": "38",
        "parking_active": "8",
        "parking_time": "08.08 14:00",
        "inside_avg": "23,1°",
        "outside": "21,4°",
        "sun_icon": mobile.metric_icon("sun"),
        "parking_icon": mobile.metric_icon("parking"),
        "energy_icon": mobile.metric_icon("energy"),
        "revenue_card": (
            '<article class="metric-card accent-revenue revenue-card">'
            '<a class="card-link revenue-main-link" href="#">'
            f'<div class="metric-head"><span>Omsetning</span>{mobile.metric_icon("revenue")}</div>'
            '<strong>11 840 kr</strong>'
            '<small>I går 10 920 kr</small>'
            '<small class="updated-line">Oppdatert 08.08 14:27</small></a></article>'
        ),
        "mobile_nav": mobile.mobile_nav("status"),
    }

    html = mobile.DASHBOARD_HTML
    for key, value in values.items():
        html = html.replace("{{ " + key + " }}", value)
    html = re.sub(r"\{\{\s*[^}]+\s*\}\}", "-", html)

    @preview.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(html)

    return preview


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("app", choices=("maintenance", "alarm", "online"))
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    application = {
        "maintenance": maintenance_app,
        "alarm": alarm_app,
        "online": online_app,
    }[args.app]()
    uvicorn.run(application, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
