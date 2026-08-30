from __future__ import annotations

import asyncio
from http.cookiejar import CookieJar
from pathlib import Path

import httpx
from fastapi import Request
from fastapi.testclient import TestClient

from energy_app.app.main import app as energy_app
from link_app.app.main import app as link_app
from maintenance_app.app.main import app as maintenance_app
from microapp_backend.runtime import _RejectAllCookiesPolicy
import operations_app.app.main as operations_main
from operations_app.app.main import app as operations_app
from parking_app.app.main import app as parking_app
from revenue_app.app.main import app as revenue_app
from sun_app.app.main import app as sun_app
import system_app.app.main as system_main
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


def test_domain_adapters_expose_health_and_config() -> None:
    for app, service, name in APPS:
        with TestClient(app) as client:
            health = client.get("/health")
            assert health.status_code == 200
            assert health.json()["service"] == service

            config = client.get("/api/app/config")
            assert config.status_code == 200
            assert config.json() == {
                "name": name,
                "service": service,
                "mode": "api-adapter",
                "build": health.json()["build"],
                "commit": health.json()["commit"],
            }


def test_domain_adapters_do_not_serve_retired_frontends() -> None:
    for app, _, _ in APPS:
        with TestClient(app) as client:
            assert client.get("/").status_code == 404
            assert client.get("/auth/login").status_code == 404
            assert client.get("/assets/old-app.js").status_code == 404


def test_domain_adapters_reject_unscoped_core_endpoints() -> None:
    for app, _, _ in APPS:
        with TestClient(app) as client:
            response = client.get("/api/definitely-not-in-this-domain")
            assert response.status_code == 404


def test_domain_adapters_apply_security_headers() -> None:
    with TestClient(revenue_app) as client:
        response = client.get(
            "/health",
            headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "app.lilletorget.net"},
        )
    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == "max-age=31536000"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-permitted-cross-domain-policies"] == "none"


def test_domain_adapters_reject_foreign_origins_for_api_writes() -> None:
    with TestClient(system_app) as client:
        response = client.post(
            "/api/actions/system/test",
            headers={"Origin": "https://evil.example"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "Ugyldig opprinnelse for skriveoperasjon"


def test_shared_proxy_client_cannot_retain_user_session_cookies() -> None:
    sent_cookies: list[str | None] = []

    async def exercise_client() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            sent_cookies.append(request.headers.get("cookie"))
            return httpx.Response(200, headers={"set-cookie": "fibaro10_session=secret; Path=/"})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            cookies=CookieJar(policy=_RejectAllCookiesPolicy()),
        ) as client:
            await client.get("https://core.local/first")
            await client.get("https://core.local/second")
            assert list(client.cookies.jar) == []

    asyncio.run(exercise_client())
    assert sent_cookies == [None, None]


def test_adapter_images_and_downloads_remain_narrowly_scoped() -> None:
    assert sun_app.routes
    assert system_main.DOMAIN_PATTERN.fullmatch("ai/datasets/json")
    assert system_main.DOMAIN_PATTERN.fullmatch("ai/logs/json")
    assert not system_main.DOMAIN_PATTERN.fullmatch("events/json")
    assert system_main.RESOURCE_PATTERN.fullmatch("events/json")
    assert system_main.RESOURCE_PATTERN.fullmatch("events/download")
    assert system_main.RESOURCE_PATTERN.fullmatch("yr/samples/download")
    assert system_main.RESOURCE_PATTERN.fullmatch("lights/samples/download")
    assert system_main.RESOURCE_PATTERN.fullmatch("ventilation/samples/download")
    assert system_main.DOMAIN_PATTERN.fullmatch("system/health")
    assert system_main.DOMAIN_PATTERN.fullmatch("system/resources/events/json")
    assert system_main.DOMAIN_PATTERN.fullmatch("system/resources/events/download")
    assert system_main.DOMAIN_PATTERN.fullmatch("system/resources/yr/samples/download")


def test_system_tools_have_proxy_safe_core_routes() -> None:
    import main
    routes = {route.path for route in main.app.routes if "GET" in getattr(route, "methods", ())}
    for path in (
        "/api/system/health",
        "/api/system/resources/events/json",
        "/api/system/resources/events/download",
        "/api/system/resources/yr/samples/download",
        "/api/system/resources/lights/samples/download",
        "/api/system/resources/ventilation/samples/download",
    ):
        assert path in routes


def test_active_app_copy_does_not_expose_retired_v2_labels() -> None:
    root = Path(__file__).resolve().parents[1]
    source = "\n".join(path.read_text(encoding="utf-8") for path in (root / "fibaro_core").rglob("*.py"))
    assert "SUN2 soling samlet i egne V2-visninger" not in source
    assert "Rediger ventilasjonsgrenser i V2-innstillinger" not in source
    assert 'api_card("Manual", "V2"' not in source
    assert "SUN2 soling samlet i egne visninger" in source


def test_operations_adapter_keeps_operational_contracts() -> None:
    required_paths = (
        "operations/overview",
        "unifi-protect/bollards",
        "unifi-protect/bollards/mobile-notifications",
        "renhold/robots/abc-123",
        "renhold/cleaning-profiles/42",
        "renhold/water-report",
        "renhold/refill-log",
        "renhold/weekly-jobs",
    )
    for path in required_paths:
        assert operations_main.DOMAIN_PATTERN.fullmatch(path), path


def test_shared_proxy_preserves_case_sensitive_dynamic_ids() -> None:
    source = (Path(__file__).resolve().parents[1] / "microapp_backend" / "runtime.py").read_text(encoding="utf-8")
    assert 'clean_path = core_path.strip("/")' in source
    assert "normalized = clean_path.casefold()" in source
    assert 'core_request(request, f"api/{clean_path}")' in source
    assert 'core_request(request, f"api/{normalized}")' not in source


def test_adapter_images_keep_case_sensitive_resource_paths() -> None:
    source = (Path(__file__).resolve().parents[1] / "microapp_backend" / "runtime.py").read_text(encoding="utf-8")
    assert "core_request(request, normalized)" not in source
    assert "core_request(request, clean_path)" in source


def test_adapter_dockerfiles_are_python_only() -> None:
    root = Path(__file__).resolve().parents[1]
    for _, service, _ in APPS:
        dockerfile = (root / service / "Dockerfile").read_text(encoding="utf-8")
        assert "FROM python:3.12-slim" in dockerfile
        assert "FROM node" not in dockerfile
        assert "frontend" not in dockerfile


def test_operations_door_filter_uses_live_group_keys(monkeypatch) -> None:
    status_data = {
        "summary": {},
        "doors": [
            {"deviceKey": "sun", "title": "Solrom 1", "groupKey": "solrom", "isConfigured": True, "state": "open", "stateLabel": "Åpen", "lastChangedAt": "2026-08-03T12:00:00", "lastChangedLabel": "03.08.2026 12:00"},
            {"deviceKey": "entry", "title": "Inngang", "groupKey": "andre", "isConfigured": True, "state": "closed", "stateLabel": "Lukket", "lastChangedAt": "2026-08-03T13:00:00", "lastChangedLabel": "03.08.2026 13:00"},
        ],
        "changes": [
            {"deviceKey": "sun", "deviceName": "Solrom 1", "timeLabel": "12:00", "action": "OPEN", "stateLabel": "Åpen"},
            {"deviceKey": "entry", "deviceName": "Inngang", "timeLabel": "13:00", "action": "CLOSED", "stateLabel": "Lukket"},
        ],
    }

    async def fake_core_json(*_args, **_kwargs):
        return status_data

    monkeypatch.setattr(operations_main, "core_json", fake_core_json)
    request = Request({"type": "http", "method": "GET", "path": "/api/modules/dorer", "headers": [], "query_string": b"view=oversikt&door_type=andre"})
    payload = asyncio.run(operations_main.doors_module(request, None, {}))

    assert payload["filters"][0]["value"] == "andre"
    assert [row["dør"] for row in payload["tables"][0]["rows"]] == ["Inngang"]
    assert [row["dør"] for row in payload["tables"][1]["rows"]] == ["Inngang"]
    assert payload["cards"][0]["value"] == 1


def test_each_domain_rejects_another_domains_module() -> None:
    checks = [
        (revenue_app, "/api/modules/parkering"),
        (parking_app, "/api/modules/soling"),
        (sun_app, "/api/modules/energi"),
        (energy_app, "/api/modules/dorer"),
        (operations_app, "/api/modules/admin"),
        (maintenance_app, "/api/modules/omsetning"),
        (system_app, "/api/modules/parkering"),
        (link_app, "/api/modules/energi"),
    ]
    for app, path in checks:
        with TestClient(app) as client:
            assert client.get(path).status_code == 404
