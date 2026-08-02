from __future__ import annotations

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
