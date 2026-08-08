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
        "dashboard_highlight": (
            '<section class="dashboard-performance">'
            '<div class="dashboard-performance-head"><div><span>Dagen så langt</span>'
            '<strong>11 840 kr</strong></div><small>Soling kl 14:27 · parkering kl 14:00</small></div>'
            '<div class="dashboard-performance-comparisons">'
            '<a href="#"><span>I går samme tidspunkt</span><strong class="is-positive">+920 kr <em>+8%</em></strong>'
            '<small>1 760 kr igjen til hele gårsdagen</small></a>'
            '<a href="#"><span>Samme ukedag forrige uke</span><strong class="is-negative">-640 kr <em>-5%</em></strong>'
            '<small>2 310 kr igjen til hele referansedagen</small></a></div>'
            '<div class="dashboard-performance-split">'
            '<span>Soling <strong>4 120 kr</strong><small>35%</small></span>'
            '<span>Parkering <strong>7 720 kr</strong><small>65%</small></span></div></section>'
        ),
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

    parking_html = mobile.DETAIL_HTML
    parking_body = mobile.render_count_performance(
        modifier="parking",
        label="Parkeringer så langt i dag",
        current_count=42,
        updated_text="Oppdatert kl 14:00 · neste import kl 16:00",
        yesterday_same_time=38,
        yesterday_total=51,
        last_week_same_time=44,
        last_week_total=57,
        href="#",
        stats=[("Omsetning", "3 528 kr", "84 kr i snitt"), ("Aktive nå", "8", "pågående parkeringer")],
    )
    parking_body += mobile.detail_stats(
        [
            ("I dag", "42", "4 220 kr - 11 % over forrige uke"),
            ("I går", "38", "3 870 kr"),
            ("Denne uken", "211", "21 480 kr"),
            ("Denne måneden", "612", "62 940 kr"),
        ]
    )
    parking_body += '<p class="detail-updated-line">Sist oppdatert 14:00 - neste import 16:00</p>'
    parking_values = {
        "title": "Parkering",
        "subtitle": "Dagens parkeringer",
        "body": parking_body,
        "detail_icon": mobile.metric_icon("parking"),
        "detail_class": "detail-parking",
        "hero_note": "",
        "mobile_nav": mobile.mobile_nav("parking"),
    }
    for key, value in parking_values.items():
        parking_html = parking_html.replace("{{ " + key + " }}", value)

    @preview.get("/parkering", response_class=HTMLResponse)
    async def parking() -> HTMLResponse:
        return HTMLResponse(parking_html)

    soling_html = mobile.DETAIL_HTML
    soling_body = mobile.render_count_performance(
        modifier="sun",
        label="Solinger så langt i dag",
        current_count=20,
        updated_text="Oppdatert kl 14:27",
        yesterday_same_time=18,
        yesterday_total=27,
        last_week_same_time=25,
        last_week_total=31,
        href="#",
        stats=[("Soltid", "6,7 t", "20 min i snitt"), ("Omsetning", "4 060 kr", "203 kr i snitt")],
    )
    soling_body += mobile.detail_stats(
        [
            ("I dag", "20", "4 060 kr - 5 færre enn forrige uke"),
            ("I går", "27", "5 120 kr"),
            ("Denne uken", "116", "23 740 kr"),
            ("Denne måneden", "383", "78 330 kr"),
        ]
    )
    soling_values = {
        "title": "Soling",
        "subtitle": "Dagens solinger",
        "body": soling_body,
        "detail_icon": mobile.metric_icon("sun"),
        "detail_class": "detail-sun",
        "hero_note": "",
        "mobile_nav": mobile.mobile_nav("sun"),
    }
    for key, value in soling_values.items():
        soling_html = soling_html.replace("{{ " + key + " }}", value)

    @preview.get("/soling", response_class=HTMLResponse)
    async def soling() -> HTMLResponse:
        return HTMLResponse(soling_html)

    energy_html = mobile.DETAIL_HTML
    energy_body = mobile.render_performance_panel(
        modifier="energy",
        label="Forbruk hittil i dag",
        main_value="42,8 kWh",
        updated_text="Per kl. 14:28",
        comparisons=[
            ("I g\u00e5r samme tidspunkt", "+4,7 kWh", "+12%", "is-negative", "8,6 kWh igjen til hele g\u00e5rsdagen", "#"),
            ("Samme ukedag forrige uke", "-2,4 kWh", "-5%", "is-positive", "13,2 kWh igjen til hele referansedagen", "#"),
        ],
        stats=[("Effekt n\u00e5", "12,6 kW", "fra HC3"), ("Uforklart", "0,8 kW", "beregnet diff")],
    )
    energy_body += mobile.detail_stats(
        [("Belysning", "1,4 kW", "n\u00e5"), ("Varmepumper", "2,8 kW", "n\u00e5"), ("Avfukter", "0,3 kW", "n\u00e5")]
    )
    energy_values = {
        "title": "Energi",
        "subtitle": "Str\u00f8mstatus",
        "body": energy_body,
        "detail_icon": mobile.metric_icon("energy"),
        "detail_class": "detail-energy",
        "hero_note": "",
        "mobile_nav": mobile.mobile_nav("energy"),
    }
    for key, value in energy_values.items():
        energy_html = energy_html.replace("{{ " + key + " }}", value)

    @preview.get("/energi", response_class=HTMLResponse)
    async def energy() -> HTMLResponse:
        return HTMLResponse(energy_html)

    drift_html = mobile.DETAIL_HTML
    drift_body = mobile.render_performance_panel(
        modifier="drift",
        label="Drift akkurat n\u00e5",
        main_value="Normal",
        updated_text="Oppdatert kl. 14:27",
        comparisons=[
            ("Klima", "23,1\u00b0", "", "", "Ute 21,4\u00b0", "#"),
            ("Ventilasjon", "1 av 4 p\u00e5", "", "", "NORMAL", "#"),
        ],
        stats=[("Solrom", "7 ledige", "5 i bruk"), ("Andre d\u00f8rer", "4 lukket", "1 \u00e5pen")],
    )
    drift_body += mobile.detail_stats(
        [("Loft n\u00e5", "25,3\u00b0", "22,1\u00b0 - 26,4\u00b0"), ("Kjeller n\u00e5", "16,5\u00b0", "Fukt 63%")]
    )
    drift_values = {
        "title": "Drift",
        "subtitle": "Klima og ventilasjon",
        "body": drift_body,
        "detail_icon": mobile.metric_icon("temperature"),
        "detail_class": "detail-temperature",
        "hero_note": "",
        "mobile_nav": mobile.mobile_nav("temperature"),
    }
    for key, value in drift_values.items():
        drift_html = drift_html.replace("{{ " + key + " }}", value)

    @preview.get("/temperatur", response_class=HTMLResponse)
    async def drift() -> HTMLResponse:
        return HTMLResponse(drift_html)

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
