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
SHELL_APP_URL = os.getenv("SHELL_APP_URL", "https://app.lilletorget.net:8443").rstrip("/")
MODULES = {
    "auth/me", "modules/admin", "modules/varslinger", "modules/undersystemer", "modules/ideer",
    "modules/mobil", "modules/manual",
}
DOMAIN_PATTERN = re.compile(r"(?:actions/(?:admin|system)|admin|system|builds?|data-sources?|import-status|mobile-preview|notifications?|subsystems?|manual|users?)(?:/.*)?")


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
        pwa_description="Systemstatus, datakilder, brukere, varslinger og dokumentasjon for Lilletorget.",
        pwa_theme_color="#334155",
        pwa_categories=("business", "utilities", "productivity"),
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
