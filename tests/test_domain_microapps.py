from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import Request
from fastapi.testclient import TestClient

from energy_app.app.main import app as energy_app
from link_app.app.main import app as link_app
from maintenance_app.app.main import app as maintenance_app
import operations_app.app.main as operations_main
from operations_app.app.main import app as operations_app
from parking_app.app.main import app as parking_app
from revenue_app.app.main import app as revenue_app
from sun_app.app.main import app as sun_app
from system_app.app.main import app as system_app
from system_app.app.menu_structure import APP_MENU_STRUCTURE


APPS = [
    (revenue_app, "revenue_app", "Lilletorget Omsetning"),
    (parking_app, "parking_app", "Lilletorget Parkering"),
    (sun_app, "sun_app", "Lilletorget Soling"),
    (energy_app, "energy_app", "Lilletorget Energi"),
    (operations_app, "operations_app", "Lilletorget Bygg og drift"),
    (maintenance_app, "maintenance_app", "Lilletorget Vedlikehold"),
    (system_app, "system_app", "Lilletorget System"),
    (link_app, "link_app", "Lilletorget Koble"),
]

FRONTEND_APPS = [
    "shell_app",
    "revenue_app",
    "parking_app",
    "sun_app",
    "energy_app",
    "operations_app",
    "maintenance_app",
    "system_app",
    "link_app",
]


def test_domain_apps_expose_health_and_config() -> None:
    for app, service, name in APPS:
        with TestClient(app) as client:
            health = client.get("/health")
            assert health.status_code == 200
            assert health.json()["service"] == service
            config = client.get("/api/app/config")
            assert config.status_code == 200
            assert config.json()["name"] == name


def test_domain_apps_require_login_for_frontend() -> None:
    for app, _, _ in APPS:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get("/")
            assert response.status_code == 303
            assert response.headers["location"] == "/auth/login"


def test_domain_apps_reject_unscoped_core_endpoints() -> None:
    for app, _, _ in APPS:
        with TestClient(app) as client:
            response = client.get("/api/definitely-not-in-this-domain")
            assert response.status_code == 404


def test_domain_apps_compress_larger_responses() -> None:
    with TestClient(revenue_app) as client:
        response = client.get("/auth/login", headers={"Accept-Encoding": "gzip"})
        assert response.status_code == 200
        assert response.headers["content-encoding"] == "gzip"


def test_domain_apps_use_the_shared_branded_login_page() -> None:
    for app, _, name in APPS:
        with TestClient(app) as client:
            response = client.get("/auth/login")
        assert response.status_code == 200
        assert "Alt samlet." in response.text
        assert "Én innlogging gjelder i alle Lilletorget-appene." in response.text
        assert name.removeprefix("Lilletorget ") in response.text


def test_all_microapps_bundle_the_shared_inter_font() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    font_import = 'import "@lilletorget/mosaic-theme/font.css";'
    for app_name in FRONTEND_APPS:
        main_source = (repo_root / app_name / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
        assert font_import in main_source, f"{app_name} mangler delt Inter-font"


def test_all_microapps_scan_the_shared_ui_styles() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_directive = '@source "../../../packages/microapp-ui/src";'
    for app_name in FRONTEND_APPS:
        style_source = (repo_root / app_name / "frontend" / "src" / "style.css").read_text(encoding="utf-8")
        assert source_directive in style_source, f"{app_name} mangler delt UI-kilde i Tailwind"


def test_sun_sessions_keep_the_interactive_image_workflow() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sun_main = (repo_root / "sun_app" / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    session_view = (repo_root / "sun_app" / "frontend" / "src" / "components" / "SunSessionsSpecial.tsx").read_text(encoding="utf-8")
    sun_api = (repo_root / "sun_app" / "frontend" / "src" / "api.ts").read_text(encoding="utf-8")

    assert 'module === "soling" && view === "enkeltimer"' in sun_main
    assert "<SunSessionsSpecial" in sun_main
    assert "Sett som hovedbilde" in session_view
    assert "Finn bilde i arkivet" in session_view
    assert "SUN2-ID / medlemsnummer" in session_view
    assert "fetchSunSessionImages" in sun_api
    assert "selectSunSessionImage" in sun_api


def test_sun_app_has_a_narrow_proxy_for_saved_session_images() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sun_backend = (repo_root / "sun_app" / "app" / "main.py").read_text(encoding="utf-8")
    shared_runtime = (repo_root / "microapp_backend" / "runtime.py").read_text(encoding="utf-8")

    assert "SESSION_IMAGE_PATTERN" in sun_backend
    assert "resource_patterns=(SESSION_IMAGE_PATTERN,)" in sun_backend
    assert "if any(pattern.fullmatch(normalized) for pattern in config.resource_patterns)" in shared_runtime


def test_app_selector_has_only_the_header_refresh_control() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "shell_app" / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    assert 'title="Oppdater status"' in source
    assert "<span>Oppdater</span>" not in source
    assert ">Alle apper</span>" in source
    assert "<h1" not in source
    assert "<AppDock shellUrl={shellUrl}" in source


def test_every_microapp_header_uses_the_shared_app_dock() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    dock = (repo_root / "packages" / "microapp-ui" / "src" / "components" / "AppDock.tsx").read_text(encoding="utf-8")
    navigation = json.loads((repo_root / "packages" / "microapp-ui" / "src" / "navigation.json").read_text(encoding="utf-8"))
    assert sorted(app["port"] for app in navigation["apps"]) == list(range(8151, 8159))
    assert [app["url"] for app in navigation["apps"]] == [
        "https://app.lilletorget.net/omsetning/",
        "https://app.lilletorget.net/parkering/",
        "https://app.lilletorget.net/soling/",
        "https://app.lilletorget.net/koble/",
        "https://app.lilletorget.net/drift/",
        "https://app.lilletorget.net/energi/",
        "https://app.lilletorget.net/vedlikehold/",
        "https://app.lilletorget.net/system/",
    ]
    assert [app["basePath"] for app in navigation["apps"]] == [
        "/omsetning", "/parkering", "/soling", "/koble", "/drift", "/energi", "/vedlikehold", "/system",
    ]
    assert 'aria-label="Bytt app"' in dock
    assert "border-r" in dock
    assert "appDefinitions.map" in dock
    assert "resolveAppUrl(app)" in dock
    assert "url.port = String(port)" not in dock

    shared_layout = (repo_root / "packages" / "microapp-ui" / "src" / "components" / "Layout.tsx").read_text(encoding="utf-8")
    assert "<AppDock activeApp={activeApp}" in shared_layout
    for app_name in ("revenue_app", "parking_app"):
        app_source = (repo_root / app_name / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
        assert "<DomainLayout config={navigation}>" in app_source
        assert not (repo_root / app_name / "frontend" / "src" / "components" / "Layout.tsx").exists()


def test_documented_menu_structure_matches_every_microapp_navigation() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    navigation = json.loads((repo_root / "packages" / "microapp-ui" / "src" / "navigation.json").read_text(encoding="utf-8"))["apps"]
    assert tuple(navigation) == APP_MENU_STRUCTURE
    assert [app["id"] for app in navigation] == ["revenue", "parking", "sun", "link", "operations", "energy", "maintenance", "system"]

    generic_apps = ("sun", "energy", "operations", "maintenance", "system", "link")
    for app_id in generic_apps:
        main_source = (repo_root / f"{app_id}_app" / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
        assert f'getDomainConfig("{app_id}")' in main_source
    for app_id in ("revenue", "parking"):
        app_source = (repo_root / f"{app_id}_app" / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
        assert f'getDomainConfig("{app_id}")' in app_source

    for app in navigation:
        routes = [item["to"] for group in app["groups"] for item in group["items"]]
        assert len(routes) == len(set(routes)), f"Dupliserte ruter i {app['shortName']}"
        assert all(group["items"] for group in app["groups"])


def test_system_menu_structure_page_is_available_without_core_data() -> None:
    with TestClient(system_app) as client:
        response = client.get("/api/modules/manual?view=menystruktur")
        assert response.status_code == 200
        payload = response.json()
        assert payload["title"] == "Menystruktur"
        assert len(payload["tables"]) == len(APP_MENU_STRUCTURE) + 2
        assert sum(len(group["items"]) for app in APP_MENU_STRUCTURE for group in app["groups"]) == 110


def test_parity_critical_specialized_views_are_kept_in_microapps() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    module_content = (repo_root / "packages" / "microapp-ui" / "src" / "components" / "ModuleContent.tsx").read_text(encoding="utf-8")
    operations_entry = (repo_root / "operations_app" / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    energy_entry = (repo_root / "energy_app" / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    link_entry = (repo_root / "link_app" / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    system_entry = (repo_root / "system_app" / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    navigation = json.loads((repo_root / "packages" / "microapp-ui" / "src" / "navigation.json").read_text(encoding="utf-8"))["apps"]
    routes = {app["id"]: {item["to"] for group in app["groups"] for item in group["items"]} for app in navigation}

    assert "Special" not in module_content
    for marker in ("<BollardsSpecial", "<DoorsSpecial", "<RoborockSpecial"):
        assert marker in operations_entry
    assert "<EnergyElviaSpecial" in energy_entry
    assert "<LinkReviewSpecial" in link_entry
    for marker in ("<MobilePreviewSpecial", "<IdeasSpecial", "<NotificationsSpecial", "<SubsystemsSpecial"):
        assert marker in system_entry
    assert "extensions={operationsExtensions}" in operations_entry
    assert "/observerte-biler" in routes["parking"]
    assert {"/", "/oversikt", "/periode", "/arsutvikling"} <= routes["parking"]
    assert {"/", "/oversikt", "/periode", "/sammenligning"} <= routes["sun"]
    assert "/detaljer" in routes["sun"]
    assert {"/dorer/andre", "/dorer/romkontroll", "/dorer/alarm", "/dorer/radata"} <= routes["operations"]
    assert "/dorer/soltimer" not in routes["operations"]
    assert "/dorer/avvik" not in routes["operations"]
    assert {
        "/dorer/oversikt-kompakt",
        "/dorer/romkontroll-original",
        "/dorer/dagsmatrise",
        "/dorer/solrom-kompakt",
        "/solrom/dagskontroll",
        "/solrom2/oversikt",
        "/solrom2/dagskontroll",
        "/solrom2/avvik",
        "/dorer2/situasjon",
        "/dorer2/bygg",
    } <= routes["operations"]
    assert {"/oppslag/navn", "/oppslag/omrade"} <= routes["parking"]
    assert {"/ideer/kontroll", "/ideer/innsikt", "/ideer/automatisering", "/ideer/arbeidsflyt"} <= routes["system"]
    assert "/kandidater" in routes["link"]
    assert "/manual/hc3-energi" in routes["system"]


def test_shared_tables_keep_search_sorting_and_local_pagination() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shared = (repo_root / "packages" / "microapp-ui" / "src" / "components" / "ModuleContent.tsx").read_text(encoding="utf-8")
    parking = (repo_root / "parking_app" / "frontend" / "src" / "components" / "ModuleContent.tsx").read_text(encoding="utf-8")
    table_utils = (repo_root / "packages" / "microapp-ui" / "src" / "table.ts").read_text(encoding="utf-8")
    for source in (shared, parking):
        assert "filterTableRows" in source
        assert "sortTableRows" in source
        assert "Søk i tabellen" in source
        assert "Rader per side" in source
        assert "toggleSort" in source
    assert "exactPattern" in table_utils
    assert "localeCompare" in table_utils
    assert 'row.id ?? row.path ?? "row"' in shared
    assert 'row.id ?? row.plate ?? row.path ?? "row"' in parking


def test_energy_topology_editor_keeps_full_hc3_workflow() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "energy_app" / "frontend" / "src" / "components" / "EnergyCircuitLoads.tsx").read_text(encoding="utf-8")
    for marker in (
        "/api/energy/hc3-devices",
        "/api/energy/nodes/live",
        "aggregate_group_key",
        "hc3_power_device_id",
        "hc3_energy_device_id",
        "hc3_switch_device_id",
        "Kartlagt",
        "Mangler måling",
        "Åpne alle",
        "Oppdater nå",
        "Utgang / kanal",
        "Logisk samling",
    ):
        assert marker in source


def test_system_ideas_restore_the_complete_evaluation_content() -> None:
    with TestClient(system_app) as client:
        response = client.get("/api/modules/ideer?view=oversikt")
        assert response.status_code == 200
        payload = response.json()
        rows = payload["tables"][0]["rows"]
        assert len(rows) == 12
        assert all(row.get("hvorfor") for row in rows)
        assert all(row.get("må_bygges") for row in rows)
        assert all(row.get("kontrollpunkter") for row in rows)
        assert {row["id"] for row in rows} >= {"revenue-change-ledger", "forecast-explainer", "api-health-map"}


def test_parking_and_sun_have_domain_specific_dashboards_and_comparisons() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    domain_app = (repo_root / "packages" / "microapp-ui" / "src" / "DomainApp.tsx").read_text(encoding="utf-8")
    parking_app = (repo_root / "parking_app" / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    parking_backend = (repo_root / "parking_app" / "app" / "main.py").read_text(encoding="utf-8")
    sun_backend = (repo_root / "sun_app" / "app" / "main.py").read_text(encoding="utf-8")
    sun_app = (repo_root / "sun_app" / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")

    assert "<CountDashboardSpecial" not in domain_app
    assert "<CountComparisonSpecial" not in domain_app
    assert "<YearComparisonSpecial" not in domain_app
    assert "<CountDashboardSpecial" in sun_app
    assert "<CountComparisonSpecial" in sun_app
    assert "<YearComparisonSpecial" in sun_app
    assert "<CountDashboardSpecial domain=\"parking\"" in parking_app
    assert "<CountComparisonSpecial domain=\"parking\"" in parking_app
    assert '"overview"' in parking_backend
    assert '"status/comparison"' in parking_backend
    assert '"soling/year-comparison"' in sun_backend
    assert '"status/comparison"' in sun_backend


def test_detail_routes_do_not_fall_back_to_generic_module_pages() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    domain_app = (repo_root / "packages" / "microapp-ui" / "src" / "DomainApp.tsx").read_text(encoding="utf-8")
    maintenance = (repo_root / "maintenance_app" / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    system = (repo_root / "system_app" / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    sun = (repo_root / "sun_app" / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    assert "isExtensionRoute" in domain_app
    assert "renderRoute" in domain_app
    assert "MaintenanceVisitDetailPage" in maintenance
    assert "SystemDetailRoute" in system
    assert "SettlementDetailPage" in sun


def test_self_loading_operations_views_do_not_fetch_the_generic_module_first() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    operations = (repo_root / "operations_app" / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    assert 'item.module === "dorer" || item.module === "pullerter"' in operations
    assert "skipModuleLoad" in operations


def test_shared_ui_has_no_domain_owned_specialists() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shared = (repo_root / "packages" / "microapp-ui" / "src")
    source = "\n".join(path.read_text(encoding="utf-8") for path in shared.rglob("*") if path.suffix in {".ts", ".tsx"})
    for marker in (
        "RoborockSpecial", "DoorsSpecial", "BollardsSpecial", "SunSessionsSpecial",
        "LinkReviewSpecial", "EnergyCircuitLoadsSpecial", "SystemSpecial",
        "sunTimeline", "kobleReview", "energyElvia", "systemNotifications", "roborock",
    ):
        assert marker not in source


def test_shared_tables_link_build_rows_to_their_detail_page() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "packages" / "microapp-ui" / "src" / "components" / "ModuleContent.tsx").read_text(encoding="utf-8")
    assert 'column === "build"' in source
    assert 'column === "headline"' in source


def test_shared_links_support_native_app_schemes() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "packages" / "microapp-ui" / "src" / "components" / "ModuleContent.tsx").read_text(encoding="utf-8")
    notifications = (repo_root / "system_app" / "frontend" / "src" / "components" / "SystemSpecial.tsx").read_text(encoding="utf-8")
    assert "[a-z0-9+.-]*" in source
    assert "channel.subscribeUrl" in notifications
    assert "Abonner" in notifications
    assert "Åpne kanal" in notifications


def test_roborock_details_no_longer_depend_on_the_classic_ui() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    core = (repo_root / "main.py").read_text(encoding="utf-8")
    detail = (repo_root / "operations_app" / "frontend" / "src" / "components" / "RoborockSpecial.tsx").read_text(encoding="utf-8")
    assert '@app.get("/api/renhold/robots/{duid}")' in core
    assert '"roborock": {' in core
    for marker in ("Siste kart", "Forbruksdeler", "Planlagte jobber", "Rengjøringshistorikk", "Statushistorikk"):
        assert marker in detail
    assert "/api/renhold/robots/" in detail
    assert '"latest_job_today"' in core
    assert '"latest_job_yesterday"' in core
    assert '"today": overview_day' in core
    assert '"yesterday": overview_day' in core
    assert '"readiness": overview_readiness' in core
    assert '"summary": overview_summary' in core
    assert "OverviewStrip" in detail
    assert "DayActivity" in detail
    assert "ReadinessGrid" in detail
    assert '"consumables": overview_consumables' in core
    assert '"schedules": overview_schedules' in core
    assert "ScheduleRows" in detail
    assert "Teknisk informasjon og API-diagnostikk" in detail


def test_roborock_night_report_is_available_in_operations() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    core = (repo_root / "main.py").read_text(encoding="utf-8")
    operations = (repo_root / "operations_app" / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    detail = (repo_root / "operations_app" / "frontend" / "src" / "components" / "RoborockSpecial.tsx").read_text(encoding="utf-8")
    assert '@app.get("/api/renhold/night-report")' in core
    assert 'to: "/renhold/rapport"' in operations
    assert "function NightReport()" in detail
    assert "Nattforløp" in detail


def test_roborock_overview_includes_the_full_day_timeline() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    core = (repo_root / "main.py").read_text(encoding="utf-8")
    operations = (repo_root / "operations_app" / "frontend" / "src" / "components" / "RoborockSpecial.tsx").read_text(encoding="utf-8")

    assert '"timeline": {' in core
    assert '"startAt": api_local_iso(timeline_window["start"])' in core
    assert "function DayTimeline" in operations
    assert "I dag · 00:00–24:00" in operations
    assert "Ikke-planlagte og automatisk utløste dagjobber vises også." in operations


def test_specialized_views_have_narrow_proxy_access() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    parking_backend = (repo_root / "parking_app" / "app" / "main.py").read_text(encoding="utf-8")
    system_backend = (repo_root / "system_app" / "app" / "main.py").read_text(encoding="utf-8")
    assert '"cars/day"' in parking_backend
    assert "unifi-protect/recognitions" in parking_backend
    assert "import-status" in system_backend
    assert "mobile-preview" in system_backend


def test_core_links_are_resolved_to_the_owning_microapp() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    navigation = (repo_root / "packages" / "microapp-ui" / "src" / "navigation.ts").read_text(encoding="utf-8")
    shared_module = (repo_root / "packages" / "microapp-ui" / "src" / "components" / "ModuleContent.tsx").read_text(encoding="utf-8")
    parking_module = (repo_root / "parking_app" / "frontend" / "src" / "components" / "ModuleContent.tsx").read_text(encoding="utf-8")
    assert "export function resolveCorePath" in navigation
    assert "coreRouteMatches" in navigation
    assert "isLocalDevelopmentHost" in navigation
    assert "new URL(app.url)" in navigation
    assert "target.port" not in navigation
    assert "resolveCorePath(path, config.appId)" in shared_module
    assert 'resolveCorePath(path || undefined, "parking")' in parking_module


def test_menu_documentation_uses_canonical_microapp_urls() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "system_app" / "app" / "menu_structure.py").read_text(encoding="utf-8")
    assert 'base_url = app["url"].rstrip("/")' in source
    assert "app['port']" not in source


def test_operations_proxy_allows_bollard_workbench_endpoints() -> None:
    assert operations_main.DOMAIN_PATTERN.fullmatch("unifi-protect/bollards")
    assert operations_main.DOMAIN_PATTERN.fullmatch("unifi-protect/bollards/mobile-notifications")
    assert operations_main.DOMAIN_PATTERN.fullmatch("unifi-protect/bollards/mobile-notifications/test")


def test_operations_proxy_allows_the_dedicated_dashboard_endpoint() -> None:
    assert operations_main.DOMAIN_PATTERN.fullmatch("operations/overview")


def test_operations_dashboard_covers_every_operational_area() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    core = (repo_root / "main.py").read_text(encoding="utf-8")
    entry = (repo_root / "operations_app" / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    dashboard = (repo_root / "operations_app" / "frontend" / "src" / "components" / "OperationsDashboard.tsx").read_text(encoding="utf-8")

    assert '@app.get("/api/operations/overview")' in core
    assert '"ventilation"' in core
    assert '"lights"' in core
    assert '"doors"' in core
    assert '"bollards"' in core
    assert '"cleaning"' in core
    assert 'domainApi.get<OperationsDashboardResponse>("/api/operations/overview")' in entry
    assert "<OperationsDashboard" in entry
    assert "Prioritert oppfølging" in dashboard
    assert "Ingen aktive driftsavvik" in dashboard


def test_operations_proxy_allows_roborock_detail_endpoint() -> None:
    assert operations_main.DOMAIN_PATTERN.fullmatch("renhold/robots/abc-123")
    assert operations_main.DOMAIN_PATTERN.fullmatch("renhold/robots")


def test_operations_proxy_allows_roborock_cleaning_profile_endpoints() -> None:
    assert operations_main.DOMAIN_PATTERN.fullmatch("renhold/cleaning-profiles")
    assert operations_main.DOMAIN_PATTERN.fullmatch("renhold/cleaning-profiles/42")


def test_shared_proxy_preserves_case_sensitive_dynamic_ids() -> None:
    source = (Path(__file__).resolve().parents[1] / "microapp_backend" / "runtime.py").read_text(encoding="utf-8")
    assert 'clean_path = core_path.strip("/")' in source
    assert "normalized = clean_path.casefold()" in source
    assert 'core_request(request, f"api/{clean_path}")' in source
    assert 'core_request(request, f"api/{normalized}")' not in source


def test_operations_door_filter_uses_live_group_keys(monkeypatch) -> None:
    status_data = {
        "summary": {},
        "doors": [
            {"deviceKey": "sun", "title": "Solrom 1", "groupKey": "solrom", "isConfigured": True, "state": "open", "stateLabel": "\u00c5pen", "lastChangedAt": "2026-08-03T12:00:00", "lastChangedLabel": "03.08.2026 12:00"},
            {"deviceKey": "entry", "title": "Inngang", "groupKey": "andre", "isConfigured": True, "state": "closed", "stateLabel": "Lukket", "lastChangedAt": "2026-08-03T13:00:00", "lastChangedLabel": "03.08.2026 13:00"},
        ],
        "changes": [
            {"deviceKey": "sun", "deviceName": "Solrom 1", "timeLabel": "12:00", "action": "OPEN", "stateLabel": "\u00c5pen"},
            {"deviceKey": "entry", "deviceName": "Inngang", "timeLabel": "13:00", "action": "CLOSED", "stateLabel": "Lukket"},
        ],
    }

    async def fake_core_json(*_args, **_kwargs):
        return status_data

    monkeypatch.setattr(operations_main, "core_json", fake_core_json)
    request = Request({"type": "http", "method": "GET", "path": "/api/modules/dorer", "headers": [], "query_string": b"view=oversikt&door_type=andre"})
    payload = asyncio.run(operations_main.doors_module(request, None, {}))

    assert payload["filters"][0]["value"] == "andre"
    assert [row["d\u00f8r"] for row in payload["tables"][0]["rows"]] == ["Inngang"]
    assert [row["d\u00f8r"] for row in payload["tables"][1]["rows"]] == ["Inngang"]
    assert payload["cards"][0]["value"] == 1


def test_shared_domain_layout_uses_the_header_for_the_active_page_title() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "packages" / "microapp-ui" / "src" / "components" / "Layout.tsx").read_text(encoding="utf-8")
    assert "<Header title={item.title || item.label}" in source
    assert ">{title}</span>" in source
    assert "item.description" not in source
    assert "<h1" not in source


def test_shared_layout_uses_area_navigation_and_horizontal_sibling_pages() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "packages" / "microapp-ui" / "src" / "components" / "Layout.tsx").read_text(encoding="utf-8")
    assert "config.navigation.map((group)" in source
    assert "to={group.items[0].to}" in source
    assert "<ContextNavigation group={group}" in source
    assert "group.items.length < 2" in source


def test_revenue_dashboard_names_both_driver_references() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "revenue_app" / "frontend" / "src" / "pages" / "DashboardPage.tsx").read_text(encoding="utf-8")
    assert "Mot første referanse" not in source
    assert "driverComparisons.map" in source
    assert 'if (periodKey === "today" && index === 1) return "Forrige uke";' in source
    assert "driverComparisonLabel(period.key, comparison, index)" in source


def test_each_domain_rejects_another_domains_module() -> None:
    cases = [
        (revenue_app, "/api/modules/parkering"),
        (parking_app, "/api/modules/soling"),
        (sun_app, "/api/modules/energi"),
        (energy_app, "/api/modules/soling"),
        (operations_app, "/api/modules/admin"),
        (maintenance_app, "/api/modules/parkering"),
        (system_app, "/api/modules/vedlikehold"),
        (link_app, "/api/modules/energi"),
    ]
    for app, path in cases:
        with TestClient(app) as client:
            assert client.get(path).status_code == 404
