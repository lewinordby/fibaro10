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


def menu_structure_module(_request: Request) -> dict[str, Any]:
    page_count = sum(_page_count(app) for app in APP_MENU_STRUCTURE)
    area_count = sum(len(app["groups"]) for app in APP_MENU_STRUCTURE)
    overview_rows = []
    app_tables = []

    for app in APP_MENU_STRUCTURE:
        base_url = app["url"].rstrip("/")
        pages = _page_count(app)
        areas = len(app["groups"])
        overview_rows.append({
            "name": app["shortName"],
            "adresse": base_url.removeprefix("https://"),
            "hovedomr\u00e5der": areas,
            "sider": pages,
            "menyvariant": "Mantis-fagmeny",
            "path": f"{base_url}/",
        })

        rows = []
        for group in app["groups"]:
            placement = "Side i fagområde" if len(group["items"]) > 1 else "Direkte fagvalg"
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
            "title": f"{app['shortName']} \u00b7 {areas} hovedomr\u00e5der \u00b7 {pages} sider",
            "columns": ["hovedomr\u00e5de", "side", "plassering", "rute", "url_dybde", "path"],
            "rows": rows,
            "meta": {"disablePagination": True},
        })

    return {
        "title": "Menystruktur",
        "subtitle": "Gjeldende Mantis-struktur, versjonert fra samme definisjon som appmenyene.",
        "cards": [
            {"title": "Origin", "value": 1, "unit": "domene", "detail": "https://ny.lilletorget.net"},
            {"title": "Fagapper", "value": len(APP_MENU_STRUCTURE), "unit": "apper", "detail": "Stier under samme HTTPS-origin"},
            {"title": "Hovedomr\u00e5der", "value": area_count, "unit": "valg", "detail": "Grupper i appmenyen"},
            {"title": "Menysider", "value": page_count, "unit": "sider", "detail": "Registrerte navigasjonsruter"},
            {"title": "Niv\u00e5er i app", "value": 2, "unit": "maks", "detail": "Hovedomr\u00e5de og side"},
        ],
        "tables": [
            {
                "title": "Slik er navigasjonen bygget",
                "columns": ["niv\u00e5", "element", "plassering", "forklaring"],
                "rows": [
                    {"niv\u00e5": "Globalt", "element": "App", "plassering": "Appfeltet", "forklaring": "Bytter mellom de elleve appene under samme origin."},
                    {"niv\u00e5": "1", "element": "Hovedomr\u00e5de", "plassering": "Appmeny", "forklaring": "En arbeidsflyt eller et tydelig fagomr\u00e5de i valgt app."},
                    {"niv\u00e5": "2", "element": "Side", "plassering": "Fagområde", "forklaring": "Beslektede sider innenfor aktivt hovedomr\u00e5de."},
                    {"niv\u00e5": "Kontekst", "element": "Detaljvisning", "plassering": "Fra innhold", "forklaring": "\u00c5pnes fra tabeller og kort og er ikke et hovedmenyvalg."},
                ],
                "meta": {"disablePagination": True},
            },
            {
                "title": "Sammenligning av appmenyene",
                "columns": ["name", "adresse", "hovedomr\u00e5der", "sider", "menyvariant"],
                "rows": overview_rows,
                "meta": {"disablePagination": True},
            },
            *app_tables,
        ],
    }
