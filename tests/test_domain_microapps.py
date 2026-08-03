from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from energy_app.app.main import app as energy_app
from link_app.app.main import app as link_app
from maintenance_app.app.main import app as maintenance_app
from operations_app.app.main import app as operations_app
from parking_app.app.main import app as parking_app
from revenue_app.app.main import app as revenue_app
from sun_app.app.main import app as sun_app
from system_app.app.main import app as system_app


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


def test_all_microapps_bundle_the_shared_inter_font() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    font_import = 'import "@lilletorget/mosaic-theme/font.css";'
    for app_name in FRONTEND_APPS:
        main_source = (repo_root / app_name / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
        assert font_import in main_source, f"{app_name} mangler delt Inter-font"


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
    assert dock.count("port: 815") == 8
    for port in range(8151, 8159):
        assert f"port: {port}" in dock
    assert 'aria-label="Bytt app"' in dock
    assert "border-r" in dock

    shared_layout = (repo_root / "packages" / "microapp-ui" / "src" / "components" / "Layout.tsx").read_text(encoding="utf-8")
    revenue_layout = (repo_root / "revenue_app" / "frontend" / "src" / "components" / "Layout.tsx").read_text(encoding="utf-8")
    parking_layout = (repo_root / "parking_app" / "frontend" / "src" / "components" / "Layout.tsx").read_text(encoding="utf-8")
    assert "<AppDock activeApp={activeApp}" in shared_layout
    assert '<AppDock activeApp="revenue"' in revenue_layout
    assert '<AppDock activeApp="parking"' in parking_layout


def test_shared_domain_layout_uses_the_header_for_the_active_page_title() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "packages" / "microapp-ui" / "src" / "components" / "Layout.tsx").read_text(encoding="utf-8")
    assert "<Header title={item.label}" in source
    assert ">{title}</span>" in source
    assert "item.description" not in source
    assert "<h1" not in source


def test_parking_layout_uses_the_header_for_the_active_page_title() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "parking_app" / "frontend" / "src" / "components" / "Layout.tsx").read_text(encoding="utf-8")
    assert "<Header open={sidebarOpen}" in source
    assert "title={title}" in source
    assert ">{title}</span>" in source
    assert "heading.description" not in source
    assert "<h1" not in source


def test_revenue_dashboard_names_both_driver_references() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "revenue_app" / "frontend" / "src" / "pages" / "DashboardPage.tsx").read_text(encoding="utf-8")
    assert "Mot første referanse" not in source
    assert "driverComparisons.map" in source
    assert 'if (periodKey === "today" && index === 1) return "Forrige uke";' in source
    assert "driverComparisonLabel(period.key, comparison, index)" in source


def test_revenue_layout_uses_the_header_for_the_active_page_title() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "revenue_app" / "frontend" / "src" / "components" / "Layout.tsx").read_text(encoding="utf-8")
    assert 'title={title}' in source
    assert '>{title}</span>' in source
    assert "heading.description" not in source
    assert "text-2xl md:text-3xl" not in source


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
