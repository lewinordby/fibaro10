from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
from fastapi import Request

from microapp_backend import DomainAppConfig, create_domain_app
from system_app.app.menu_structure import menu_structure_module


APP_DIR = Path(__file__).resolve().parents[1]
MODULES = {
    "auth/me", "modules/admin", "modules/varslinger", "modules/undersystemer", "modules/ideer",
    "modules/mobil", "modules/manual", "modules/operasjon", "modules/eiendeler",
    "modules/automatisering", "modules/rapporter", "modules/sok", "modules/datakvalitet",
}
DOMAIN_PATTERN = re.compile(
    r"(?:actions/(?:admin|system)|admin|system|builds?|data-sources?|import-status|mobile-preview|"
    r"notifications?|subsystems?|manual|users?|ai/(?:datasets/json|logs/json))(?:/.*)?"
)
RESOURCE_PATTERN = re.compile(r"(?:events/(?:json|download)|(?:lights|ventilation|yr)/samples/download)")


def card(title: str, value: Any, unit: str = "", detail: str = "", tone: str = "status") -> dict[str, Any]:
    return {"title": title, "value": value, "unit": unit, "detail": detail, "tone": tone}


async def core_json(client: httpx.AsyncClient, headers: dict[str, str], path: str, params: Any = None) -> dict[str, Any]:
    response = await client.get(path, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


async def subsystems_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    data = await core_json(client, headers, "/api/system/subsystems")
    subsystem_rows = list(data.get("subsystems", []))
    for row in subsystem_rows:
        component = str(row.get("component") or "ukjent")
        primary_url = str(row.get("primary_url") or row.get("web_url") or row.get("local_url") or "")
        local_url = str(row.get("local_url") or "")
        health_url = str(row.get("health_url") or "")
        row.setdefault("title", component.replace("_", " ").title())
        row.setdefault("primary_url", primary_url)
        row.setdefault("access", "external" if row.get("web_url") else "local" if primary_url or local_url else "internal")
        if not isinstance(row.get("links"), list):
            links = []
            if primary_url:
                links.append({"kind": "local", "label": "Åpne", "url": primary_url})
            if health_url and health_url not in {primary_url, local_url}:
                links.append({"kind": "health", "label": "Helsesjekk", "url": health_url})
            row["links"] = links
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
    return {
        "title": "Undersystemer",
        "subtitle": "Alle apper, tjenester og webflater i Lilletorget-l\u00f8sningen",
        "cards": cards,
        "tables": [{"title": "Systemkatalog", "columns": ["komponent", "omr\u00e5de", "rolle", "runtime", "tjeneste", "status", "kritikalitet", "url", "health"], "rows": rows}],
        "systemSubsystems": {
            "summary": {
                **summary,
                "components": len(subsystem_rows),
                "active": active_count,
                "web_interfaces": sum(1 for row in subsystem_rows if row.get("primary_url") or row.get("local_url") or row.get("web_url")),
            },
            "subsystems": subsystem_rows,
        },
    }


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
    return {
        "title": "Varslinger og abonnement",
        "subtitle": data.get("privacy", "ntfy-kanaler for varsler fra l\u00f8sningen"),
        "cards": cards,
        "tables": [{"title": "Kanaler", "columns": ["kanal", "omr\u00e5de", "forklaring", "utl\u00f8ses av", "prioritet", "konfigurert", "publiserer", "abonner", "historikk"], "rows": rows}, {"title": "Slik abonnerer du", "columns": ["trinn", "forklaring"], "rows": setup_rows}],
        "systemNotifications": data,
    }


async def operations_center_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    payload = await notifications_module(request, client, headers)
    view = request.query_params.get("view", "arbeidsko")
    titles = {
        "arbeidsko": "Arbeidskø",
        "kritisk": "Kritiske hendelser",
        "kontroller": "Operative kontroller",
        "historikk": "Behandlet historikk",
    }
    payload["title"] = titles.get(view, "Operasjonssentral")
    payload["subtitle"] = "Én prioritert arbeidsflate for avvik, alarmer, datakilder, backup og varsling"
    payload["operationView"] = view
    return payload


ASSET_EDIT_FIELDS = [
    {"key": "name", "label": "Navn", "type": "text", "required": True},
    {"key": "category", "label": "Kategori", "type": "select", "required": True, "defaultValue": "Annet", "options": [
        {"label": value, "value": value} for value in ("Solseng", "Robotvasker", "Z-Wave-enhet", "Kamera", "Ventilasjon", "Lys", "Bygg", "IT", "Annet")
    ]},
    {"key": "location", "label": "Plassering", "type": "text"},
    {"key": "status", "label": "Status", "type": "select", "required": True, "defaultValue": "I drift", "options": [
        {"label": value, "value": value} for value in ("I drift", "Til kontroll", "Ute av drift", "Lager", "Utfaset")
    ]},
    {"key": "manufacturer", "label": "Produsent", "type": "text"},
    {"key": "model", "label": "Modell", "type": "text"},
    {"key": "serial_no", "label": "Serienummer", "type": "text"},
    {"key": "hc3_device_id", "label": "HC3-ID", "type": "number"},
    {"key": "owner_app", "label": "Ansvarlig app", "type": "text"},
    {"key": "installed_at", "label": "Installert", "type": "date"},
    {"key": "warranty_until", "label": "Garanti til", "type": "date"},
    {"key": "service_interval_days", "label": "Serviceintervall i dager", "type": "number"},
    {"key": "last_service_at", "label": "Sist vedlikehold", "type": "date"},
    {"key": "notes", "label": "Notat", "type": "textarea", "rows": 4},
]


async def assets_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    params = {key: value for key in ("q", "category", "status") if (value := request.query_params.get(key))}
    data = await core_json(client, headers, "/api/system/assets", params)
    rows = []
    for row in data.get("assets", []):
        rows.append({
            **row,
            "name": row.get("navn"),
            "category": row.get("kategori"),
            "location": row.get("plassering"),
            "manufacturer": row.get("produsent"),
            "model": row.get("modell"),
            "serial_no": row.get("serienummer"),
            "hc3_device_id": row.get("HC3-ID"),
            "owner_app": row.get("eierapp"),
            "installed_at": row.get("installert"),
            "warranty_until": row.get("garanti til"),
            "service_interval_days": row.get("serviceintervall dager"),
            "last_service_at": row.get("sist vedlikehold"),
            "notes": row.get("notat"),
        })
    now = date.today()
    overdue = sum(1 for row in rows if row.get("neste vedlikehold") and str(row["neste vedlikehold"]) < now.isoformat())
    warranty = sum(1 for row in rows if row.get("garanti til") and now.isoformat() <= str(row["garanti til"]) <= (now + timedelta(days=90)).isoformat())
    categories = sorted({str(row.get("kategori")) for row in rows if row.get("kategori")})
    return {
        "title": "Eiendelsregister",
        "subtitle": "Utstyr, plassering, teknisk identitet, garanti og vedlikeholdsbehov",
        "cards": [
            card("Eiendeler", len(rows), "stk", "Registrert i felles register"),
            card("Kategorier", len(categories), "stk", "Faglig gruppering"),
            card("Forfalt service", overdue, "stk", "Bør følges opp", "warning" if overdue else "success"),
            card("Garanti 90 dager", warranty, "stk", "Utløper snart", "warning" if warranty else "status"),
        ],
        "filters": [
            {"key": "q", "label": "Søk", "type": "text", "value": request.query_params.get("q", "")},
            {"key": "category", "label": "Kategori", "type": "select", "value": request.query_params.get("category", ""), "options": [{"label": value, "value": value} for value in categories]},
            {"key": "status", "label": "Status", "type": "select", "value": request.query_params.get("status", ""), "options": [{"label": value, "value": value} for value in ("I drift", "Til kontroll", "Ute av drift", "Lager", "Utfaset")]},
        ],
        "actions": [{"key": "discover", "label": "Synkroniser kjente enheter", "method": "POST", "path": "api/system/assets/discover", "confirm": "Legg til nye solsenger, robotvaskere og energi-/Z-Wave-enheter i registeret?"}],
        "tables": [{
            "title": "Alle eiendeler",
            "columns": ["navn", "kategori", "plassering", "produsent", "modell", "HC3-ID", "status", "neste vedlikehold", "garanti til", "oppdatert"],
            "rows": rows,
            "edit": {"kind": "asset", "title": "eiendel", "endpoint": "api/system/assets/{id}", "method": "PATCH", "createEndpoint": "api/system/assets", "layout": "split", "fields": ASSET_EDIT_FIELDS},
        }],
    }


AUTOMATION_EDIT_FIELDS = [
    {"key": "name", "label": "Navn", "type": "text", "required": True},
    {"key": "domain", "label": "Område", "type": "select", "required": True, "defaultValue": "Drift", "options": [{"label": value, "value": value} for value in ("Drift", "Parkering", "Soling", "Energi", "Dører", "Renhold", "Ventilasjon", "Lys", "System")]},
    {"key": "mode", "label": "Modus", "type": "select", "required": True, "defaultValue": "Utkast", "options": [{"label": value, "value": value} for value in ("Utkast", "Observer", "Aktiv", "Pauset")]},
    {"key": "enabled", "label": "Aktivert", "type": "boolean"},
    {"key": "trigger_type", "label": "Type utløser", "type": "select", "required": True, "defaultValue": "Hendelse", "options": [{"label": value, "value": value} for value in ("Hendelse", "Tidsplan", "Terskel", "Datakilde", "Manuell")]},
    {"key": "cooldown_minutes", "label": "Minste intervall i minutter", "type": "number", "defaultValue": 0},
    {"key": "description", "label": "Formål", "type": "textarea", "rows": 3},
    {"key": "trigger", "label": "Utløser", "type": "textarea", "rows": 3},
    {"key": "conditions", "label": "Betingelser", "type": "textarea", "rows": 4},
    {"key": "actions", "label": "Handlinger", "type": "textarea", "rows": 4},
]


async def automations_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    data = await core_json(client, headers, "/api/system/automations")
    rows = []
    for row in data.get("automations", []):
        rows.append({
            **row,
            "name": row.get("navn"),
            "domain": row.get("område"),
            "description": row.get("beskrivelse"),
            "trigger_type": row.get("utløser"),
            "conditions": row.get("betingelser"),
            "actions": row.get("handlinger"),
            "mode": row.get("modus"),
            "enabled": row.get("aktiv"),
            "cooldown_minutes": row.get("ventetid min"),
        })
    enabled = sum(bool(row.get("aktiv")) for row in rows)
    observe = sum(str(row.get("modus")) == "Observer" for row in rows)
    return {
        "title": "Automatiseringsverksted",
        "subtitle": "Beskriv, kvalitetssikre og forvalt regler før de eventuelt får styre fysisk utstyr",
        "cards": [card("Regler", len(rows), "stk"), card("Aktive", enabled, "stk", "Eksplisitt aktivert"), card("Observerer", observe, "stk", "Logger uten å styre"), card("Utkast", sum(str(row.get("modus")) == "Utkast" for row in rows), "stk")],
        "tables": [{
            "title": "Regler og forslag",
            "columns": ["navn", "område", "utløser", "modus", "aktiv", "ventetid min", "beskrivelse", "sist evaluert", "siste resultat"],
            "rows": rows,
            "edit": {"kind": "automation", "title": "automatisering", "endpoint": "api/system/automations/{id}", "method": "PATCH", "createEndpoint": "api/system/automations", "layout": "split", "fields": AUTOMATION_EDIT_FIELDS},
        }],
    }


async def reports_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    rows = [
        {"rapport": "Driftsstatus", "område": "Operasjon", "periode": "Akkurat nå", "formål": "Avvik, datakilder, backup og varsler", "path": "/operasjon/"},
        {"rapport": "Nattrapport renhold", "område": "Renhold", "periode": "Natt", "formål": "Planlagte og utførte robotjobber, batteri og vann", "path": "/renhold/rapport"},
        {"rapport": "Parkeringsoppgjør", "område": "Parkering", "periode": "Måned", "formål": "Oppgjør mot EasyPark og Flowbird/ParkNordic", "path": "/parkering/oppgjor"},
        {"rapport": "Soloppgjør", "område": "Soling", "periode": "Måned", "formål": "Soling og produkter mot kreditnota", "path": "/soling/oppgjor"},
        {"rapport": "Elvia-kontroll", "område": "Energi", "periode": "Valgt periode", "formål": "Elvia mot lokale målinger og manglende last", "path": "/energi/elvia-kontroll"},
        {"rapport": "Besøksanalyse", "område": "Parkering", "periode": "Valgt periode", "formål": "Tidspunkt, ukedag, varighet og omsetning", "path": "/parkering/besoksanalyse"},
        {"rapport": "Pris- og tiltaksanalyse", "område": "Parkering", "periode": "Flere år", "formål": "Utvikling før og etter prisendringer", "path": "/parkering/pris-analyse"},
        {"rapport": "Datakvalitet", "område": "System", "periode": "Akkurat nå", "formål": "Manglende, gamle og inkonsistente data", "path": "/operasjon/datakvalitet"},
    ]
    return {
        "title": "Rapportsenter",
        "subtitle": "Én inngang til operative rapporter og kontroller, alltid basert på samme fagdata",
        "cards": [card("Rapporter", len(rows), "stk"), card("Daglig drift", 3, "stk"), card("Økonomi", 2, "stk"), card("Analyse", 3, "stk")],
        "tables": [{"title": "Tilgjengelige rapporter", "columns": ["rapport", "område", "periode", "formål", "path"], "rows": rows}],
    }


async def search_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    query = request.query_params.get("q", "").strip()
    data = {"results": [], "count": 0}
    if len(query) >= 2:
        data = await core_json(client, headers, "/api/system/search", {"q": query})
    return {
        "title": "Universalsøk",
        "subtitle": "Søk samlet i kjøretøy, soltimer, vedlikehold og eiendeler",
        "cards": [card("Treff", data.get("count", 0), "stk", f'Søk: {query}' if query else "Skriv minst to tegn")],
        "filters": [{"key": "q", "label": "Søk i hele løsningen", "type": "text", "value": query, "placeholder": "Reg.nr., navn, Sun2-ID, rom, utstyr eller oppgave"}],
        "tables": [{"title": "Søkeresultater", "columns": ["type", "tittel", "detalj", "oppdatert", "path"], "rows": data.get("results", [])}],
    }


async def data_quality_module(request: Request, client: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    return await core_json(client, headers, "/api/modules/admin?view=datakvalitet")


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
        rows = [
            {
                "kapittel": chapter.get("number"),
                "tittel": chapter.get("title"),
                "merknad": chapter.get("note", ""),
                "path": f'/system/manual/{chapter.get("id")}',
            }
            for chapter in chapters
            if chapter.get("id")
        ]
        return {"title": data.get("title", "Manual"), "subtitle": data.get("description", ""), "cards": [card("Build", data.get("build", "-")), card("Kapitler", len(chapters), "stk"), card("Daglig bruk", "02", "", "Anbefalt start"), card("Feils\u00f8king", "10", "", "Ved feil eller gamle data")], "tables": [{"title": "Kapitler", "columns": ["kapittel", "tittel", "merknad", "path"], "rows": rows}]}

    chapter_id = {"daglig-bruk": "daglig-bruk", "datagrunnlag": "datagrunnlag", "feilsoking": "feilsoking"}.get(view, view)
    chapter = next((item for item in chapters if item.get("id") == chapter_id), None)
    if not chapter:
        return {"title": "Manual", "subtitle": "Kapittelet finnes ikke", "cards": [], "tables": []}
    if chapter_id == "hc3-energi" and isinstance(chapter.get("energyQuickappReport"), dict):
        report = chapter["energyQuickappReport"]
        summary = report.get("summary") or {}
        report_tables = []
        for key, title in (
            ("findings", "Konklusjoner"),
            ("groups", "QuickApps og oppsamlinger"),
            ("gaps", "Reelle og mulige hull"),
            ("notDirectlyIncluded", "Ikke direkte med"),
            ("allDevices", "Alle HC3-enheter"),
        ):
            values = report.get(key) or []
            if not values or not isinstance(values[0], dict):
                continue
            rows = [scalar_row(row) for row in values]
            columns = list(dict.fromkeys(column for row in rows for column in row.keys()))
            report_tables.append({"title": title, "columns": columns, "rows": rows})
        return {
            "title": chapter.get("title", "HC3 energioppsamlinger"),
            "subtitle": f'Sist bygget fra {report.get("createdAt") or "siste HC3-inventar"}',
            "cards": [
                card("QuickApps", summary.get("quickApps", 0), "stk", "Summerende oppsamlinger"),
                card("Direkte medlemmer", summary.get("directMembers", 0), "stk", "Målere i oppsamlingene"),
                card("Reelle hull", summary.get("realGaps", 0), "stk", "Bør kontrolleres"),
                card("Alle enheter", summary.get("allDevices", 0), "stk", "Komplett HC3-inventar"),
            ],
            "tables": report_tables,
        }
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
        {"id": "revenue-change-ledger", "kategori": "kontroll", "område": "Omsetning", "forslag": "Endringsforklaring for omsetning", "oppsummering": "Vis hvorfor dagens omsetning endret seg siden forrige oppdatering, med kilde og før/etter-tall.", "nytte": "Høy", "status": "Klar å bygge", "mål": "Omsetning og Dashboard", "hvorfor": "EasyPark og Sun2 kan oppdatere gamle rader slik at totalen flytter seg uten nye hendelser.", "må_bygges": ["Periodiske snapshots av nøkkeltall", "Endring per datakilde", "Skille ny, oppdatert og korrigert rad"], "kontrollpunkter": ["Samme kuttetidspunkt som dashboard", "Beløp og antall må avstemmes"]},
        {"id": "settlement-control-center", "kategori": "kontroll,innsikt", "område": "Omsetning", "forslag": "Oppgjørskontroll samlet", "oppsummering": "Ett kontrollbilde for parkering, soling og produkter mot innleste oppgjør.", "nytte": "Høy", "status": "Bør vurderes", "mål": "Omsetning", "hvorfor": "En samlet flate gjør det enkelt å se om en måned er ferdig avstemt.", "må_bygges": ["Samle kontrollstatus fra fagappene", "Avvik og status per måned", "Lenke til originalbilag"], "kontrollpunkter": ["Detaljsidene beholdes", "Filter på år og status"]},
        {"id": "parking-source-reconciliation", "kategori": "kontroll,automatisering", "område": "Parkering", "forslag": "Parkeringskilde-avstemming", "oppsummering": "Kontroller EasyPark, Flowbird/ParkNordic, kjøretøyoppslag og område mot hverandre.", "nytte": "Høy", "status": "Klar å bygge", "mål": "Parkering", "hvorfor": "Manglende område eller kjøretøydata kan gi feil analyser og bør samles i en arbeidsliste.", "må_bygges": ["Liste manglende område, kjøretøy og eier", "Skille SVV, Sverige og Danmark", "Vise siste og neste forsøk"], "kontrollpunkter": ["Oppslag kjøres i bakgrunnen", "Manuell overstyring må være tydelig"]},
        {"id": "sun-image-review-queue", "kategori": "automatisering,arbeidsflyt", "område": "Soling", "forslag": "Bildekontrollkø for soltimer", "oppsummering": "Rask arbeidsflate for soltimer som mangler eller har usikkert hovedbilde.", "nytte": "Middels", "status": "Klar å bygge", "mål": "Soling", "hvorfor": "Detaljvisningen er tung når mange timer skal kontrolleres etter hverandre.", "må_bygges": ["Kø med usikre bilder", "Fem kandidater og tastaturstyring", "Sett hovedbilde, hopp over og marker OK"], "kontrollpunkter": ["Ingen arkivbilder endres uten lagring", "Sun2-ID, rom og tid vises tydelig"]},
        {"id": "link-confidence-lab", "kategori": "innsikt,arbeidsflyt", "område": "Koble", "forslag": "Koblingslab for parkering og soling", "oppsummering": "Forklar hvorfor en bil og en Sun2-ID sannsynligvis hører sammen.", "nytte": "Høy", "status": "Eksperiment", "mål": "Koble", "hvorfor": "Forslag er først nyttige når det er raskt å forstå hvorfor koblingen er sterk eller svak.", "må_bygges": ["Felles tidslinje", "Forklarbare scorekriterier", "Lære av bekreftede koblinger"], "kontrollpunkter": ["Vise positive og negative bevis", "Aldri automatisk bekrefte"]},
        {"id": "import-calendar", "kategori": "automatisering", "område": "Drift", "forslag": "Importkalender og neste kjøring", "oppsummering": "Vis planlagte og faktiske importer med varighet og avvik.", "nytte": "Middels", "status": "Klar å bygge", "mål": "System og Dashboard", "hvorfor": "Manglende eller forsinkede importer bør oppdages uten å lese logger.", "må_bygges": ["Samle planlagte tidspunkt", "Vise faktisk kjøring og forsinkelse", "Varsle når en kilde er gammel"], "kontrollpunkter": ["Skille faste tidspunkt og intervaller", "All tid vises som lokal tid"]},
        {"id": "energy-revenue-model", "kategori": "innsikt", "område": "Energi", "forslag": "Energi mot inntekt", "oppsummering": "Koble strøm, Elvia, soltimer og omsetning for å se margin og avvik.", "nytte": "Middels", "status": "Krever datagrunnlag", "mål": "Energi", "hvorfor": "Forbruk per seng sammen med inntekt kan avdekke målefeil, driftsavvik og svak prising.", "må_bygges": ["Kostnad per dag, time og seng", "Koble forbruk mot soltid", "Forventet mot målt forbruk"], "kontrollpunkter": ["Håndtere umålte laster", "Vise kvalitet på grunnlaget"]},
        {"id": "data-quality-inbox", "kategori": "kontroll,automatisering,arbeidsflyt", "område": "System", "forslag": "Datakvalitet som innboks", "oppsummering": "Felles innboks for ting som må rettes, bekreftes eller følges opp.", "nytte": "Høy", "status": "Bør vurderes", "mål": "System", "hvorfor": "Arbeidslister ligger i dag på flere sider og bør kunne håndteres samlet.", "må_bygges": ["Oppgaver fra dataavvik", "Ansvar, alvorlighet og lenke", "Automatisk lukking når avvik er rettet"], "kontrollpunkter": ["Ikke lage parallell datamodell", "Støtte raske massehandlinger"]},
        {"id": "forecast-explainer", "kategori": "innsikt", "område": "Omsetning", "forslag": "Forklarbar prognose", "oppsummering": "Vis hvilke faktorer som trekker prognosen opp eller ned.", "nytte": "Middels", "status": "Eksperiment", "mål": "Omsetning, Parkering og Soling", "hvorfor": "Prognosen er mer nyttig når vær, ukedag, historikk og datakvalitet er synlig.", "må_bygges": ["Faktorbidrag per kjøring", "Endring fra forrige prognose", "Markere svakt datagrunnlag"], "kontrollpunkter": ["Unngå falsk presisjon", "Start med forklaring før modellendring"]},
        {"id": "alert-rules", "kategori": "automatisering", "område": "Drift", "forslag": "Varslingsregler", "oppsummering": "Egne regler for importstopp, omsetningsfall, oppslagsfeil og energiavvik.", "nytte": "Middels", "status": "Bør vurderes", "mål": "System", "hvorfor": "Feil bør bli operative varsler før de oppdages tilfeldig.", "må_bygges": ["Terskel, stillhetstid og alvorlighet", "Varslingskanaler", "Historikk og falske positive"], "kontrollpunkter": ["Lett å dempe støy", "Ta hensyn til åpningstid"]},
        {"id": "audit-safe-actions", "kategori": "kontroll,arbeidsflyt", "område": "System", "forslag": "Sikker handlingslogg", "oppsummering": "Logg manuelle endringer, hvem som gjorde dem og hva som ble endret.", "nytte": "Høy", "status": "Klar å bygge", "mål": "System", "hvorfor": "Redigering av bilder, oppgjør og koblinger bør være sporbar.", "må_bygges": ["Felles audit-tabell", "Historikk på detaljsider", "Før- og etterverdi"], "kontrollpunkter": ["Ikke logge hemmeligheter", "Kobles til innlogging"]},
        {"id": "api-health-map", "kategori": "arbeidsflyt", "område": "Drift", "forslag": "Avhengighetskart for datakilder", "oppsummering": "Vis hvilke tjenester, containere, API-er og jobber hver side er avhengig av.", "nytte": "Lav", "status": "Bør vurderes", "mål": "System", "hvorfor": "Ved feil må konsekvens og berørte sider kunne finnes raskt.", "må_bygges": ["Kartlegge datakilder", "Vise tilstand og siste feil", "Lenke til berørte sider"], "kontrollpunkter": ["Oppdateres med nye jobber", "Start med kritiske importer"]},
    ]
    view = request.query_params.get("view", "oversikt")
    selected = rows if view == "oversikt" else [row for row in rows if view in row["kategori"].split(",")]
    ready = sum(1 for row in selected if row["status"] == "Klar å bygge")
    high = sum(1 for row in selected if row["nytte"] == "Høy")
    titles = {"kontroll": "Kontroll og avvik", "innsikt": "Analyse og innsikt", "automatisering": "Automatisering", "arbeidsflyt": "Arbeidsflyt"}
    return {"title": titles.get(view, "Ideer"), "subtitle": "Vurderingsflate før funksjoner flyttes til riktig fagapp", "cards": [card("Forslag", len(selected), "stk"), card("Klar å bygge", ready, "stk"), card("Høy nytte", high, "stk"), card("Områder", len({row["område"] for row in selected}), "stk")], "tables": [{"title": "Forslag", "columns": ["område", "forslag", "oppsummering", "nytte", "status", "mål", "hvorfor", "må_bygges", "kontrollpunkter"], "rows": selected}]}

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
        resource_patterns=(RESOURCE_PATTERN,),
        adapters={
            "modules/undersystemer": subsystems_module,
            "modules/varslinger": notifications_module,
            "modules/manual": manual_module,
            "modules/mobil": mobile_module,
            "modules/ideer": ideas_module,
            "modules/operasjon": operations_center_module,
            "modules/eiendeler": assets_module,
            "modules/automatisering": automations_module,
            "modules/rapporter": reports_module,
            "modules/sok": search_module,
            "modules/datakvalitet": data_quality_module,
        },
    )
)
