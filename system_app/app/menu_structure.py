from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import Request


PACKAGED_NAVIGATION_FILE = Path(__file__).with_name("navigation.json")
SOURCE_NAVIGATION_FILE = Path(__file__).resolve().parents[2] / "packages" / "microapp-ui" / "src" / "navigation.json"
NAVIGATION_FILE = PACKAGED_NAVIGATION_FILE if PACKAGED_NAVIGATION_FILE.exists() else SOURCE_NAVIGATION_FILE
APP_MENU_STRUCTURE: tuple[dict[str, Any], ...] = tuple(json.loads(NAVIGATION_FILE.read_text(encoding="utf-8"))["apps"])


def _page_count(app: dict[str, Any]) -> int:
    return sum(len(group["items"]) for group in app["groups"])


def _url_depth(route: str) -> int:
    return len([part for part in route.split("/") if part])


def menu_structure_module(request: Request) -> dict[str, Any]:
    scheme = request.url.scheme or "http"
    host = request.url.hostname or "192.168.20.218"
    page_count = sum(_page_count(app) for app in APP_MENU_STRUCTURE)
    area_count = sum(len(app["groups"]) for app in APP_MENU_STRUCTURE)
    overview_rows = []
    app_tables = []

    for app in APP_MENU_STRUCTURE:
        base_url = f"{scheme}://{host}:{app['port']}"
        pages = _page_count(app)
        areas = len(app["groups"])
        overview_rows.append({
            "name": app["shortName"],
            "port": app["port"],
            "hovedomr\u00e5der": areas,
            "sider": pages,
            "menyvariant": "Felles navigasjon",
            "path": f"{base_url}/",
        })

        rows = []
        for group in app["groups"]:
            placement = "Horisontal meny" if len(group["items"]) > 1 else "Direkte fra venstremeny"
            for item in group["items"]:
                route = item["to"]
                rows.append({
                    "hovedomr\u00e5de": group["label"],
                    "side": item["label"],
                    "plassering": placement,
                    "rute": route,
                    "url_dybde": _url_depth(route),
                    "path": f"{base_url}{route}",
                })
        app_tables.append({
            "title": f"{app['shortName']} \u00b7 port {app['port']} \u00b7 {areas} hovedomr\u00e5der \u00b7 {pages} sider",
            "columns": ["hovedomr\u00e5de", "side", "plassering", "rute", "url_dybde", "path"],
            "rows": rows,
            "meta": {"disablePagination": True},
        })

    return {
        "title": "Menystruktur",
        "subtitle": "Felles navigasjonsmodell generert fra samme kilde som appmenyene.",
        "cards": [
            {"title": "Appvelger", "value": 1, "unit": "startside", "detail": "Global navigasjon p\u00e5 port 8150"},
            {"title": "Fagapper", "value": len(APP_MENU_STRUCTURE), "unit": "apper", "detail": "Port 8151-8158"},
            {"title": "Hovedomr\u00e5der", "value": area_count, "unit": "valg", "detail": "Vises i venstremenyen"},
            {"title": "Menysider", "value": page_count, "unit": "sider", "detail": "Direkte eller horisontalt"},
            {"title": "Niv\u00e5er i app", "value": 2, "unit": "maks", "detail": "Hovedomr\u00e5de og side"},
        ],
        "tables": [
            {
                "title": "Slik er navigasjonen bygget",
                "columns": ["niv\u00e5", "element", "plassering", "forklaring"],
                "rows": [
                    {"niv\u00e5": "Globalt", "element": "App", "plassering": "Appfeltet", "forklaring": "Bytter mellom de \u00e5tte selvstendige fagappene."},
                    {"niv\u00e5": "1", "element": "Hovedomr\u00e5de", "plassering": "Venstremeny", "forklaring": "En arbeidsflyt eller et tydelig fagomr\u00e5de i valgt app."},
                    {"niv\u00e5": "2", "element": "Side", "plassering": "Horisontal meny", "forklaring": "Beslektede sider innenfor aktivt hovedomr\u00e5de."},
                    {"niv\u00e5": "Kontekst", "element": "Detaljvisning", "plassering": "Fra innhold", "forklaring": "\u00c5pnes fra tabeller og kort og er ikke et hovedmenyvalg."},
                ],
                "meta": {"disablePagination": True},
            },
            {
                "title": "Sammenligning av appmenyene",
                "columns": ["name", "port", "hovedomr\u00e5der", "sider", "menyvariant"],
                "rows": overview_rows,
                "meta": {"disablePagination": True},
            },
            *app_tables,
        ],
    }
