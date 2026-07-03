"""Static system inventory for Fibaro10.

The inventory is deliberately code-owned so the admin UI, documentation and
tests can point to the same definition of which local apps are part of the
solution.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


SYSTEM_COMPONENTS: list[dict[str, Any]] = [
    {
        "component": "fibaro10",
        "area": "Kjerne",
        "role": "FastAPI backend, V2 API, database, importstatus og adminflater",
        "runtime": "Docker",
        "compose_service": "fibaro10",
        "health": "/health",
        "status": "Aktiv",
        "criticality": "Kritisk",
    },
    {
        "component": "desktop_v2",
        "area": "Frontend",
        "role": "React/Ant Design grensesnitt for daglig drift",
        "runtime": "Vite build levert av fibaro10",
        "compose_service": "fibaro10",
        "health": "/",
        "status": "Aktiv",
        "criticality": "Kritisk",
    },
    {
        "component": "online_dashboard",
        "area": "Mobil/ekstern",
        "role": "Eksternt dashboard med begrensede nøkkeltall",
        "runtime": "Docker",
        "compose_service": "online_dashboard",
        "health": "/health",
        "status": "Aktiv",
        "criticality": "Høy",
    },
    {
        "component": "owntracks_service",
        "area": "Lokasjon",
        "role": "Separat FastAPI-tjeneste paa owntracks.lilletorget.net for OwnTracks HTTP-inntak, lagring, waypoints og sonebesok",
        "runtime": "Docker",
        "compose_service": "owntracks_service",
        "health": "https://owntracks.lilletorget.net/health",
        "status": "Aktiv",
        "criticality": "Normal",
    },
    {
        "component": "axis_camera_snapshots",
        "area": "Bilder",
        "role": "Henter og rydder Axis snapshots til soltimer",
        "runtime": "Docker",
        "compose_service": "axis_camera_snapshots",
        "health": "Filproduksjon",
        "status": "Aktiv",
        "criticality": "Høy",
    },
    {
        "component": "car_info_lookup",
        "area": "Parkering",
        "role": "Nordiske kjøretøyoppslag etter SVV",
        "runtime": "Docker",
        "compose_service": "car_info_lookup",
        "health": "/health",
        "status": "Aktiv",
        "criticality": "Normal",
    },
    {
        "component": "sun2_session_scraper",
        "area": "Soling",
        "role": "Henter enkelttimer, senger, medlemmer og produktsalg fra Sun2",
        "runtime": "Docker",
        "compose_service": "sun2_session_scraper",
        "health": "Importjobb",
        "status": "Aktiv",
        "criticality": "Kritisk",
    },
    {
        "component": "easypark_downloader",
        "area": "Parkering",
        "role": "Nedlasting av EasyPark-data via egen app/flyt",
        "runtime": "Repo app",
        "compose_service": "",
        "health": "easypark_parking_import",
        "status": "Aktiv/ekstern",
        "criticality": "Kritisk",
    },
    {
        "component": "roborock_logger",
        "area": "Renhold",
        "role": "Logger Roborock-status og vaskehistorikk",
        "runtime": "Repo app",
        "compose_service": "",
        "health": "roborock_sync",
        "status": "Aktiv/ekstern",
        "criticality": "Normal",
    },
    {
        "component": "sun2_importer",
        "area": "Soling",
        "role": "Historisk/importverktøy for Sun2 dagssummer",
        "runtime": "Repo app",
        "compose_service": "",
        "health": "sun2_room_daily_import",
        "status": "Verktøy",
        "criticality": "Lav",
    },
    {
        "component": "sun2_backfill_downloader",
        "area": "Soling",
        "role": "Bakfylling av historiske Sun2 filer",
        "runtime": "Repo app",
        "compose_service": "",
        "health": "Manuell",
        "status": "Verktøy",
        "criticality": "Lav",
    },
    {
        "component": "browser_extensions",
        "area": "Parkering",
        "role": "Manuelle nettleserutvidelser/oppslag der API ikke dekker behov",
        "runtime": "Chrome extension",
        "compose_service": "",
        "health": "Manuell",
        "status": "Fallback",
        "criticality": "Lav",
    },
    {
        "component": "hc3_vedlikehold",
        "area": "HC3",
        "role": "Vedlikeholds- og oppsettsskript for Fibaro HC3",
        "runtime": "Repo script",
        "compose_service": "",
        "health": "Manuell",
        "status": "Verktøy",
        "criticality": "Normal",
    },
]


def system_component_rows() -> list[dict[str, Any]]:
    return [dict(component) for component in SYSTEM_COMPONENTS]


def system_component_summary() -> dict[str, Any]:
    areas = Counter(str(row["area"]) for row in SYSTEM_COMPONENTS)
    statuses = Counter(str(row["status"]) for row in SYSTEM_COMPONENTS)
    active = sum(1 for row in SYSTEM_COMPONENTS if str(row["status"]).lower().startswith("aktiv"))
    critical = sum(1 for row in SYSTEM_COMPONENTS if row["criticality"] in {"Kritisk", "Høy"})
    return {
        "components": len(SYSTEM_COMPONENTS),
        "active": active,
        "critical": critical,
        "areas": len(areas),
        "area_rows": [{"area": key, "count": value} for key, value in sorted(areas.items())],
        "status_rows": [{"status": key, "count": value} for key, value in sorted(statuses.items())],
    }
