from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import httpx
from fastapi import Request

from microapp_backend import DomainAppConfig, create_domain_app
from system_app.app.menu_structure import menu_structure_module


APP_DIR = Path(__file__).resolve().parents[1]
SHELL_BASE_URL = os.getenv("SHELL_BASE_URL", "http://shell_app:8150").rstrip("/")
SHELL_APP_URL = os.getenv("SHELL_APP_URL", "http://192.168.20.218:8150").rstrip("/")
MODULES = {
    "auth/me", "modules/admin", "modules/varslinger", "modules/undersystemer", "modules/ideer",
    "modules/mobil", "modules/manual",
}
DOMAIN_PATTERN = re.compile(r"(?:actions/(?:admin|system)|admin|system|builds?|data-sources?|notifications?|subsystems?|manual|users?)(?:/.*)?")


def card(title: str, value: Any, unit: str = "", detail: str = "", tone: str = "status") -> dict[str, Any]:
    return {"title": title, "value": value, "unit": unit, "detail": detail, "tone": tone}


async def core_json(client: httpx.AsyncClient, headers: dict[str, str], path: str) -> dict[str, Any]:
    response = await client.get(path, headers=headers)
    response.raise_for_status()
    return response.json()


async def subsystems_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    data = await core_json(client, headers, "/api/system/subsystems")
    subsystem_rows = list(data.get("subsystems", []))
    known_components = {str(row.get("component") or "") for row in subsystem_rows}
    if "shell_app" not in known_components:
        subsystem_rows.append({
            "component": "shell_app",
            "area": "Plattform",
            "role": "Intern appvelger og samlet helsestatus for fagappene",
            "runtime": "Docker",
            "compose_service": "shell_app",
            "status": "Aktiv",
            "criticality": "Normal",
            "primary_url": SHELL_APP_URL,
            "local_url": SHELL_APP_URL,
            "health_url": f"{SHELL_APP_URL}/health",
        })
        known_components.add("shell_app")
    try:
        app_catalog = await core_json(client, headers, f"{SHELL_BASE_URL}/api/apps")
    except (httpx.RequestError, httpx.HTTPStatusError):
        app_catalog = {"apps": []}
    for app_row in app_catalog.get("apps", []):
        component = f'{app_row.get("id")}_app'
        if component in known_components:
            continue
        app_url = str(app_row.get("url") or "").rstrip("/")
        subsystem_rows.append({
            "component": component,
            "area": app_row.get("category"),
            "role": app_row.get("description"),
            "runtime": "Docker",
            "compose_service": component,
            "status": f'Aktiv · build {app_row.get("build") or "-"}' if app_row.get("status") == "ok" else app_row.get("statusText"),
            "criticality": "Høy" if app_row.get("id") in {"parking", "sun", "energy", "operations"} else "Normal",
            "primary_url": app_url,
            "local_url": app_url,
            "health_url": f"{app_url}/health" if app_url else "",
        })
        known_components.add(component)
    summary = data.get("summary", {})
    active_count = sum(1 for row in subsystem_rows if str(row.get("status") or "").lower().startswith("aktiv"))
    cards = [
        card("Komponenter", len(subsystem_rows), "stk", "Apper og tjenester"),
        card("Aktive", active_count, "stk", "I daglig drift"),
        card("Kritiske", summary.get("critical", 0), "stk", "P\u00e5virker datagrunnlaget"),
        card("Webflater", sum(1 for row in subsystem_rows if row.get("primary_url") or row.get("local_url") or row.get("web_url")), "stk", "Kan \u00e5pnes direkte"),
    ]
    rows = [{
        "komponent": row.get("component"), "omr\u00e5de": row.get("area"), "rolle": row.get("role"),
        "runtime": row.get("runtime"), "tjeneste": row.get("compose_service"), "status": row.get("status"),
        "kritikalitet": row.get("criticality"), "url": row.get("primary_url") or row.get("local_url") or row.get("web_url"),
        "health": row.get("health_url"),
    } for row in subsystem_rows]
    return {"title": "Undersystemer", "subtitle": "Alle apper, tjenester og webflater i Lilletorget-l\u00f8sningen", "cards": cards, "tables": [{"title": "Systemkatalog", "columns": ["komponent", "omr\u00e5de", "rolle", "runtime", "tjeneste", "status", "kritikalitet", "url", "health"], "rows": rows}]}


async def notifications_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    data = await core_json(client, headers, "/api/system/notifications")
    summary = data.get("summary", {})
    cards = [
        card("Kanaler", summary.get("channels", 0), "stk", "Tilgjengelige abonnement"),
        card("Konfigurert", summary.get("configured", 0), "stk", "Klar til bruk"),
        card("Publiserer", summary.get("publishing", 0), "stk", "Aktive varsler"),
        card("Tjeneste", data.get("provider", "ntfy"), "", "Varslingstjeneste"),
    ]
    rows = [{
        "kanal": row.get("title"), "omr\u00e5de": row.get("area"), "forklaring": row.get("description"),
        "utl\u00f8ses av": row.get("triggers"), "prioritet": row.get("priority"), "konfigurert": row.get("configured"),
        "publiserer": row.get("publishingEnabled"), "abonner": row.get("subscribeUrl"), "historikk": row.get("webUrl"),
    } for row in data.get("subscriptions", [])]
    setup_rows = [{"trinn": index + 1, "forklaring": value} for index, value in enumerate(data.get("setup", []))]
    return {"title": "Varslinger og abonnement", "subtitle": data.get("privacy", "ntfy-kanaler for varsler fra l\u00f8sningen"), "cards": cards, "tables": [{"title": "Kanaler", "columns": ["kanal", "omr\u00e5de", "forklaring", "utl\u00f8ses av", "prioritet", "konfigurert", "publiserer", "abonner", "historikk"], "rows": rows}, {"title": "Slik abonnerer du", "columns": ["trinn", "forklaring"], "rows": setup_rows}]}


def scalar_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: " \u00b7 ".join(str(item) for item in value) if isinstance(value, list) else value
        for key, value in row.items()
        if not isinstance(value, dict)
    }


async def manual_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    view = request.query_params.get("view", "oversikt")
    if view == "menystruktur":
        return menu_structure_module(request)

    data = await core_json(client, headers, "/api/manual")
    chapters = data.get("chapters", [])
    if view == "oversikt":
        rows = [{"kapittel": chapter.get("number"), "tittel": chapter.get("title"), "id": chapter.get("id"), "merknad": chapter.get("note", "")} for chapter in chapters]
        return {"title": data.get("title", "Manual"), "subtitle": data.get("description", ""), "cards": [card("Build", data.get("build", "-")), card("Kapitler", len(chapters), "stk"), card("Daglig bruk", "02", "", "Anbefalt start"), card("Feils\u00f8king", "10", "", "Ved feil eller gamle data")], "tables": [{"title": "Kapitler", "columns": ["kapittel", "tittel", "id", "merknad"], "rows": rows}]}

    chapter_id = {"daglig-bruk": "daglig-bruk", "datagrunnlag": "datagrunnlag", "feilsoking": "feilsoking"}.get(view, view)
    chapter = next((item for item in chapters if item.get("id") == chapter_id), None)
    if not chapter:
        return {"title": "Manual", "subtitle": "Kapittelet finnes ikke", "cards": [], "tables": []}
    tables = []
    labels = {"startLinks": "Start her", "flow": "Arbeidsflyt", "dataSources": "Datakilder", "troubleshooting": "Feils\u00f8king", "checklists": "Sjekklister", "principles": "Prinsipper"}
    for key, value in chapter.items():
        if not isinstance(value, list) or not value or not isinstance(value[0], dict):
            continue
        rows = [scalar_row(row) for row in value]
        columns = list(dict.fromkeys(column for row in rows for column in row.keys()))
        tables.append({"title": labels.get(key, key), "columns": columns, "rows": rows})
    if chapter.get("note"):
        tables.append({"title": "Merknad", "columns": ["tekst"], "rows": [{"tekst": chapter["note"]}]})
    return {"title": chapter.get("title", "Manual"), "subtitle": f'Kapittel {chapter.get("number", "")}', "cards": [], "tables": tables}


async def mobile_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    data = await core_json(client, headers, "/api/mobile-preview/screens")
    rows = [{"skjerm": row.get("title"), "forklaring": row.get("subtitle"), "kilde": row.get("sourcePath"), "forh\u00e5ndsvisning": row.get("frameUrl")} for row in data.get("screens", [])]
    return {"title": "Mobilflater", "subtitle": f'Oppdateres hvert {data.get("refreshSeconds", 0)}. sekund', "cards": [card("Skjermer", len(rows), "stk", "Speiler mobilappen")], "tables": [{"title": "Tilgjengelige skjermer", "columns": ["skjerm", "forklaring", "kilde", "forh\u00e5ndsvisning"], "rows": rows}]}


async def ideas_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    rows = [
        {"omr\u00e5de": "Omsetning", "forslag": "Endringsforklaring", "nytte": "H\u00f8y", "status": "Klar \u00e5 bygge", "m\u00e5l": "Vis hvorfor omsetningen endret seg mellom importer."},
        {"omr\u00e5de": "Omsetning", "forslag": "Samlet oppgj\u00f8rskontroll", "nytte": "H\u00f8y", "status": "B\u00f8r vurderes", "m\u00e5l": "Parkering, soling og produkter i ett kontrollbilde."},
        {"omr\u00e5de": "Parkering", "forslag": "Kildeavstemming", "nytte": "H\u00f8y", "status": "Klar \u00e5 bygge", "m\u00e5l": "EasyPark, Flowbird, kj\u00f8ret\u00f8y og omr\u00e5de mot hverandre."},
        {"omr\u00e5de": "Soling", "forslag": "Bildekontrollk\u00f8", "nytte": "Middels", "status": "Klar \u00e5 bygge", "m\u00e5l": "Rask kontroll av manglende og usikre hovedbilder."},
        {"omr\u00e5de": "Koble", "forslag": "Forklarbar sannsynlighet", "nytte": "H\u00f8y", "status": "Eksperiment", "m\u00e5l": "Vis positive og negative bevis for bil mot Sun2-ID."},
        {"omr\u00e5de": "Drift", "forslag": "Importkalender", "nytte": "Middels", "status": "Klar \u00e5 bygge", "m\u00e5l": "Planlagt mot faktisk kj\u00f8ring med varighet og avvik."},
        {"omr\u00e5de": "Energi", "forslag": "Energi mot inntekt", "nytte": "Middels", "status": "Krever datagrunnlag", "m\u00e5l": "Kostnad og margin per dag, time og solseng."},
        {"omr\u00e5de": "System", "forslag": "Datakvalitet som innboks", "nytte": "H\u00f8y", "status": "B\u00f8r vurderes", "m\u00e5l": "Samle avvik som m\u00e5 rettes, bekreftes eller f\u00f8lges opp."},
    ]
    ready = sum(1 for row in rows if row["status"] == "Klar \u00e5 bygge")
    high = sum(1 for row in rows if row["nytte"] == "H\u00f8y")
    return {"title": "Ideer", "subtitle": "Vurderingsflate f\u00f8r funksjoner flyttes til riktig fagapp", "cards": [card("Forslag", len(rows), "stk"), card("Klar \u00e5 bygge", ready, "stk"), card("H\u00f8y nytte", high, "stk"), card("Omr\u00e5der", len({row["omr\u00e5de"] for row in rows}), "stk")], "tables": [{"title": "Forslag", "columns": ["omr\u00e5de", "forslag", "nytte", "status", "m\u00e5l"], "rows": rows}]}

app = create_domain_app(
    DomainAppConfig(
        name="Lilletorget System",
        short_name="System",
        service="system_app",
        build_env="SYSTEM_APP_BUILD",
        commit_env="SYSTEM_APP_COMMIT",
        app_dir=APP_DIR,
        port=8157,
        allowed_paths={"GET": MODULES},
        allowed_patterns={method: (DOMAIN_PATTERN,) for method in ("GET", "POST", "PATCH", "PUT", "DELETE")},
        adapters={
            "modules/undersystemer": subsystems_module,
            "modules/varslinger": notifications_module,
            "modules/manual": manual_module,
            "modules/mobil": mobile_module,
            "modules/ideer": ideas_module,
        },
    )
)
