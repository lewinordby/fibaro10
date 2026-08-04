from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import httpx
from fastapi import Request

from microapp_backend import DomainAppConfig, create_domain_app


APP_DIR = Path(__file__).resolve().parents[1]
MODULES = {
    "auth/me", "overview", "modules/ventilasjon", "modules/lys", "modules/dorer",
    "modules/solrom", "modules/solrom-2", "modules/dorer2", "modules/pullerter", "modules/renhold",
}
DOMAIN_PATTERN = re.compile(r"(?:actions/(?:ventilasjon|lys|dorer|solrom|pullerter|renhold)|unifi-protect/bollards|renhold/robots|ventilation|lights?|doors?|solrooms?|bollards?|roborock|hc3)(?:/.*)?")


def card(title: str, value: Any, unit: str = "", detail: str = "", tone: str = "status") -> dict[str, Any]:
    return {"title": title, "value": value, "unit": unit, "detail": detail, "tone": tone}


async def core_json(client: httpx.AsyncClient, headers: dict[str, str], path: str, params: Any = None) -> dict[str, Any]:
    response = await client.get(path, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def door_cards(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        card("D\u00f8rer", summary.get("total", 0), "stk", f'{summary.get("configured", 0)} konfigurert'),
        card("\u00c5pne", summary.get("open", 0), "stk", "N\u00e5status", "warning"),
        card("Lukkede", summary.get("closed", 0), "stk", "N\u00e5status", "success"),
        card("Sist endret", summary.get("latestLabel", "-"), "", summary.get("latestChangeText", "")),
    ]


def door_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "d\u00f8r": row.get("title") or row.get("deviceName"),
            "avdeling": row.get("sectionTitle") or row.get("groupTitle"),
            "status": row.get("stateLabel"),
            "sist endret": row.get("lastChangedLabel"),
            "varighet": row.get("ageLabel"),
            "batteri": row.get("batteryLabel"),
        }
        for row in rows
    ]


def filtered_door_cards(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    configured = [row for row in rows if row.get("isConfigured")]
    latest = max(configured, key=lambda row: str(row.get("lastChangedAt") or ""), default={})
    return [
        card("D\u00f8rer", len(rows), "stk", f"{len(configured)} konfigurert"),
        card("\u00c5pne", sum(row.get("state") == "open" for row in configured), "stk", "N\u00e5status", "warning"),
        card("Lukkede", sum(row.get("state") == "closed" for row in configured), "stk", "N\u00e5status", "success"),
        card(
            "Sist endret",
            latest.get("lastChangedLabel", "-"),
            "",
            f'{latest.get("title", "")} {str(latest.get("stateLabel") or "").lower()}'.strip(),
        ),
    ]


async def doors_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    view = request.query_params.get("view", "oversikt")
    status_data = await core_json(client, headers, "/api/hc3/doors/status", {"history_limit": 150, "period_limit": 150})
    summary = status_data.get("summary", {})
    cards = door_cards(summary)
    tables: list[dict[str, Any]] = []
    filters: list[dict[str, Any]] = []

    if view == "solrom":
        data = await core_json(client, headers, "/api/hc3/doors/sunroom-sessions")
        room_rows = []
        for row in data.get("rooms", []):
            session = row.get("session") or {}
            room_rows.append({
                "rom": row.get("title"), "avdeling": row.get("sectionTitle"), "d\u00f8r": row.get("doorStateLabel"),
                "siden": row.get("doorAgeLabel"), "status": row.get("status"), "soltime": session.get("startedLabel"),
                "forventet ut": row.get("expectedExitLabel"), "gjenst\u00e5r": row.get("remainingLabel") or row.get("overstayLabel"),
            })
        tables = [{"title": "Solrom akkurat n\u00e5", "columns": ["rom", "avdeling", "d\u00f8r", "siden", "status", "soltime", "forventet ut", "gjenst\u00e5r"], "rows": room_rows}]
    elif view == "romkontroll-ny2":
        params = {"days": request.query_params.get("days", "2")}
        if day := request.query_params.get("day"):
            params["day"] = day
        data = await core_json(client, headers, "/api/hc3/doors/sunroom-overview", params)
        room_rows = []
        for room in data.get("rooms", []):
            state = room.get("status") or {}
            counts = room.get("summary") or {}
            room_rows.append({
                "rom": room.get("title"), "avdeling": room.get("sectionTitle"), "d\u00f8r": state.get("doorStateLabel"),
                "status": state.get("status"), "soltimer": counts.get("sessions"), "matchet": counts.get("matched"),
                "varsler": counts.get("warnings"), "alarmer": counts.get("alerts"), "effekt bekreftet": counts.get("energyConfirmed"),
            })
        tables = [{"title": f'Romkontroll {data.get("dayDate", "")}', "columns": ["rom", "avdeling", "d\u00f8r", "status", "soltimer", "matchet", "varsler", "alarmer", "effekt bekreftet"], "rows": room_rows}]
    elif view in {"alarm", "avvik"}:
        params = {"history_limit": "250"}
        if day := request.query_params.get("day"):
            params["day"] = day
        data = await core_json(client, headers, "/api/hc3/doors/alarm", params)
        alarm_summary = data.get("summary", {})
        cards = [
            card("Aktive", alarm_summary.get("active", 0), "stk", "Krever oppf\u00f8lging", "warning"),
            card("I dag", alarm_summary.get("today", 0), "stk", "Registrerte alarmer"),
            card("Historikk", len(data.get("history", [])), "stk", "Viste hendelser"),
            card("Regel", f'{data.get("rules", {}).get("noSessionMinutes", 8)} min', "", "Lukket uten soltime"),
        ]
        alarm_rows = [{
            "tid": row.get("detectedLabel"), "rom": row.get("title"), "type": row.get("alarmType"),
            "status": row.get("status"), "alvorlighet": row.get("severity"), "detalj": row.get("detail"),
            "utfall": row.get("outcome"), "varsling": row.get("notificationStatus"),
        } for row in data.get("history", [])]
        tables = [{"title": "Alarmhistorikk", "columns": ["tid", "rom", "type", "status", "alvorlighet", "detalj", "utfall", "varsling"], "rows": alarm_rows}]
        if view == "avvik":
            period_rows = [{
                "d\u00f8r": row.get("title"), "lukket": row.get("closedLabel"), "\u00e5pnet": row.get("openedLabel"),
                "varighet": row.get("durationLabel"), "status": row.get("stateLabel"),
            } for row in status_data.get("periods", [])]
            tables.insert(0, {"title": "D\u00f8rperioder", "columns": ["d\u00f8r", "lukket", "\u00e5pnet", "varighet", "status"], "rows": period_rows})
    elif view == "radata":
        event_rows = [{
            "tid": row.get("timeLabel"), "d\u00f8r": row.get("deviceName"), "hendelse": row.get("action"),
            "status": row.get("stateLabel"), "kilde": row.get("source"), "batteri": row.get("batteryLevel"),
        } for row in status_data.get("events", [])]
        tables = [{"title": "R\u00e5hendelser", "columns": ["tid", "d\u00f8r", "hendelse", "status", "kilde", "batteri"], "rows": event_rows}]
    else:
        rows = status_data.get("doors", [])
        door_type = request.query_params.get("door_type", "")
        if view == "andre":
            door_type = "andre"
        door_type = {"other": "andre", "sunrooms": "solrom"}.get(door_type, door_type)
        if door_type in {"solrom", "andre"}:
            rows = [row for row in rows if row.get("groupKey") == door_type]
            cards = filtered_door_cards(rows)
        selected_keys = {row.get("deviceKey") for row in rows}
        changes = status_data.get("changes", [])
        if door_type in {"solrom", "andre"}:
            changes = [row for row in changes if row.get("deviceKey") in selected_keys]
        filters = [{
            "key": "door_type",
            "label": "D\u00f8rtype",
            "type": "select",
            "value": door_type,
            "options": [
                {"label": "Solrom", "value": "solrom"},
                {"label": "Andre d\u00f8rer", "value": "andre"},
            ],
        }]
        tables = [
            {"title": "D\u00f8rstatus", "columns": ["d\u00f8r", "avdeling", "status", "sist endret", "varighet", "batteri"], "rows": door_rows(rows)},
            {"title": "Siste endringer", "columns": ["tid", "d\u00f8r", "hendelse", "status"], "rows": [{"tid": row.get("timeLabel"), "d\u00f8r": row.get("deviceName"), "hendelse": row.get("action"), "status": row.get("stateLabel")} for row in changes]},
        ]

    return {"title": "D\u00f8rer", "subtitle": f'Sist endret {summary.get("latestAgeLabel", "-")}', "cards": cards, "tables": tables, "filters": filters}


async def bollards_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    data = await core_json(client, headers, "/api/unifi-protect/bollards")
    summary = data.get("summary", {})
    cards = [
        card("Kameraer", summary.get("connected_cameras", 0), f'/ {summary.get("target_cameras", 0)}', "Tilkoblet"),
        card("Kontrollobjekter", summary.get("inspection_objects", 0), "stk", "Pullerter, fasade og trapp"),
        card("Aktive avvik", summary.get("active_incidents", 0), "stk", "Krever kontroll", "warning"),
        card("AI-profiler", summary.get("ai_profiles_ready", 0), f'/ {summary.get("ai_profiles_total", 0)}', "Klare for analyse"),
    ]
    camera_rows = [{"kamera": row.get("name"), "status": row.get("state"), "siste hendelse": row.get("last_event_at"), "deteksjoner": ", ".join(row.get("smart_detect_types") or [])} for row in data.get("cameras", [])]
    incident_rows = [{"objekt": row.get("display_name"), "status": row.get("status"), "alvorlighet": row.get("severity"), "oppdaget": row.get("detected_at"), "sist sett": row.get("last_observed_at"), "varsling": row.get("notification_status")} for row in data.get("incidents", [])]
    return {"title": "Pullerter og fasade", "subtitle": "Lokal visuell kontroll og AI-analyse fra UniFi Protect", "cards": cards, "tables": [{"title": "Kameraer", "columns": ["kamera", "status", "siste hendelse", "deteksjoner"], "rows": camera_rows}, {"title": "Aktive og historiske avvik", "columns": ["objekt", "status", "alvorlighet", "oppdaget", "sist sett", "varsling"], "rows": incident_rows}]}

app = create_domain_app(
    DomainAppConfig(
        name="Lilletorget Bygg og drift",
        short_name="Bygg og drift",
        service="operations_app",
        build_env="OPERATIONS_APP_BUILD",
        commit_env="OPERATIONS_APP_COMMIT",
        app_dir=APP_DIR,
        port=8155,
        allowed_paths={"GET": MODULES},
        allowed_patterns={method: (DOMAIN_PATTERN,) for method in ("GET", "POST", "PATCH", "PUT", "DELETE")},
        adapters={"modules/dorer": doors_module, "modules/pullerter": bollards_module},
    )
)
