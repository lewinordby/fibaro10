from __future__ import annotations

from typing import Any

from fastapi import Request


APP_MENU_STRUCTURE: tuple[dict[str, Any], ...] = (
    {
        "id": "revenue", "name": "Omsetning", "port": 8151, "menu_variant": "Egen appmeny",
        "groups": (("Omsetning", (("Dashboard", "/"), ("Oversikt", "/oversikt"), ("Periodesammenligning", "/sammenligning"), ("\u00c5rssammenligning", "/ar"), ("M\u00e5nedsoversikt", "/maned"))),),
    },
    {
        "id": "parking", "name": "Parkering", "port": 8152, "menu_variant": "Egen appmeny",
        "groups": (("Parkering", (("Oversikt", "/"), ("Parkeringer", "/parkeringer"), ("Dagslinje", "/dagslinje"), ("Kj\u00f8ret\u00f8y", "/kjoretoy"), ("Omr\u00e5de", "/omrade"), ("Prognose", "/prognose"), ("Oppgj\u00f8r", "/oppgjor"), ("\u00c5rssammenligning", "/arsutvikling"), ("Tidspunkt", "/tidspunkt"), ("Ukesnitt", "/ukesnitt"), ("Bilstatistikk", "/bilstatistikk"), ("Oppslag", "/oppslag"))),),
    },
    {
        "id": "sun", "name": "Soling", "port": 8153, "menu_variant": "Felles appmeny",
        "groups": (("Soling", (("Oversikt", "/"), ("\u00c5rssammenligning", "/sammenligning"), ("Dagslinje", "/dagslinje"), ("Enkelttimer", "/enkeltimer"), ("Prognose", "/prognose"), ("Oppgj\u00f8r", "/oppgjor"), ("Produkter", "/produkter"), ("Senger", "/senger"), ("Medlemmer", "/medlemmer"), ("Statistikk", "/statistikk"))),),
    },
    {
        "id": "energy", "name": "Energi", "port": 8154, "menu_variant": "Felles appmeny",
        "groups": (("Energi", (("Status", "/"), ("Elvia-kontroll", "/elvia-kontroll"), ("Kurs og last", "/kurs-last"), ("Kurser", "/kurser"), ("Laster", "/laster"), ("Forbruk per seng", "/forbruk-per-seng"), ("Elvia-import", "/elvia"), ("Verkt\u00f8y", "/verktoy"))),),
    },
    {
        "id": "operations", "name": "Bygg og drift", "port": 8155, "menu_variant": "Felles appmeny",
        "groups": (
            ("Drift", (("Driftsoversikt", "/"),)),
            ("Ventilasjon", (("Dagslogg", "/ventilasjon"), ("Temperatur og fukt", "/ventilasjon/temp-logg"), ("Yr-logg", "/ventilasjon/yr-logg"), ("Hendelser", "/ventilasjon/hendelser"), ("Innstillinger", "/ventilasjon/innstillinger"))),
            ("Lys", (("Dagslogg", "/lys"), ("Lux-logging", "/lys/lux-logging"), ("Hendelser", "/lys/hendelser"), ("Innstillinger", "/lys/innstillinger"))),
            ("D\u00f8rer", (("Oversikt", "/dorer"), ("Solrom", "/dorer/solrom"), ("Romkontroll", "/dorer/romkontroll"), ("Alarm", "/dorer/alarm"), ("Avvik", "/dorer/avvik"), ("Andre d\u00f8rer", "/dorer/andre"), ("R\u00e5data", "/dorer/radata"))),
            ("Anlegg", (("Pullerter", "/pullerter"), ("Renhold", "/renhold"), ("Robotvaskere", "/renhold/roboter"))),
        ),
    },
    {
        "id": "maintenance", "name": "Vedlikehold", "port": 8156, "menu_variant": "Felles appmeny",
        "groups": (("Vedlikehold", (("Oppgaver", "/"), ("Bes\u00f8k", "/besok"))),),
    },
    {
        "id": "system", "name": "System", "port": 8157, "menu_variant": "Felles appmeny",
        "groups": (
            ("System", (("Drift", "/"), ("Datakilder", "/datakilder"), ("Systemkart", "/systemkart"), ("Undersystemer", "/undersystemer"), ("Varslinger", "/varslinger"))),
            ("Kvalitet", (("Kontroll", "/kontroll"), ("Datakvalitet", "/datakvalitet"), ("Analyse", "/analyse"), ("Oppgaver", "/oppgaver"))),
            ("Administrasjon", (("Brukere", "/brukere"), ("Buildlogg", "/build"), ("Teknisk", "/teknisk"), ("Verkt\u00f8y", "/verktoy"), ("AI", "/ai"))),
            ("Dokumentasjon", (("Manual", "/manual"), ("Daglig bruk", "/manual/daglig-bruk"), ("Datagrunnlag", "/manual/datagrunnlag"), ("Feils\u00f8king", "/manual/feilsoking"), ("Menystruktur", "/manual/menystruktur"))),
            ("Utvikling", (("Ideer", "/ideer"), ("Mobilflater", "/mobil"))),
        ),
    },
    {
        "id": "link", "name": "Koble", "port": 8158, "menu_variant": "Felles appmeny",
        "groups": (
            ("Koblinger", (("Kandidater", "/"), ("Sun2-kontroll", "/kontroll"), ("Biltreff", "/biltreff"), ("Treffgrunnlag", "/treffgrunnlag"))),
            ("Motor", (("Jobbstatus", "/jobb"),)),
        ),
    },
)


def _page_count(app: dict[str, Any]) -> int:
    return sum(len(items) for _, items in app["groups"])


def _url_depth(route: str) -> int:
    return len([part for part in route.split("/") if part])


def menu_structure_module(request: Request) -> dict[str, Any]:
    scheme = request.url.scheme or "http"
    host = request.url.hostname or "192.168.20.218"
    page_count = sum(_page_count(app) for app in APP_MENU_STRUCTURE)
    group_count = sum(len(app["groups"]) for app in APP_MENU_STRUCTURE)
    overview_rows = []
    app_tables = []

    for app in APP_MENU_STRUCTURE:
        base_url = f"{scheme}://{host}:{app['port']}"
        pages = _page_count(app)
        groups = len(app["groups"])
        overview_rows.append({
            "name": app["name"], "port": app["port"], "menygrupper": groups, "sider": pages,
            "menyvariant": app["menu_variant"],
            "kommentar": "Flere visuelle gruppetitler" if groups > 1 else "En samlet gruppetittel",
            "path": f"{base_url}/",
        })

        rows = []
        for group_name, items in app["groups"]:
            for label, route in items:
                rows.append({
                    "gruppe": group_name, "side": label, "rute": route,
                    "url_dybde": _url_depth(route), "path": f"{base_url}{route}",
                })
        app_tables.append({
            "title": f"{app['name']} \u00b7 port {app['port']} \u00b7 {pages} sider",
            "columns": ["gruppe", "side", "rute", "url_dybde", "path"], "rows": rows,
            "meta": {"disablePagination": True},
        })

    return {
        "title": "Menystruktur",
        "subtitle": "Komplett oversikt over appniv\u00e5, visuelle grupper og klikkbare sider.",
        "cards": [
            {"title": "Appvelger", "value": 1, "unit": "startside", "detail": "Port 8150"},
            {"title": "Fagapper", "value": len(APP_MENU_STRUCTURE), "unit": "apper", "detail": "Port 8151-8158"},
            {"title": "Menysider", "value": page_count, "unit": "sider", "detail": "Alle hovedmenyvalg"},
            {"title": "Visuelle grupper", "value": group_count, "unit": "grupper", "detail": "Ikke egne menyniv\u00e5er"},
            {"title": "Hovedniv\u00e5er", "value": 2, "unit": "niv\u00e5er", "detail": "App og side"},
        ],
        "tables": [
            {
                "title": "Slik skal menyen leses", "columns": ["niv\u00e5", "element", "klikkbart", "forklaring"],
                "rows": [
                    {"niv\u00e5": "1", "element": "App", "klikkbart": "Ja", "forklaring": "Velges fra appikonene i toppmenyen eller Appvelgeren."},
                    {"niv\u00e5": "-", "element": "Gruppetittel", "klikkbart": "Nei", "forklaring": "Skiller fagomr\u00e5der visuelt i venstremenyen. Dette er ikke et ekstra niv\u00e5."},
                    {"niv\u00e5": "2", "element": "Side", "klikkbart": "Ja", "forklaring": "Et ordin\u00e6rt valg i appens venstremeny."},
                    {"niv\u00e5": "Kontekst", "element": "Detaljvisning", "klikkbart": "Fra innhold", "forklaring": "\u00c5pnes fra tabeller og kort, og vises normalt ikke i hovedmenyen."},
                ], "meta": {"disablePagination": True},
            },
            {
                "title": "Sammenligning av appmenyene",
                "columns": ["name", "port", "menygrupper", "sider", "menyvariant", "kommentar"],
                "rows": overview_rows, "meta": {"disablePagination": True},
            },
            *app_tables,
        ],
    }
