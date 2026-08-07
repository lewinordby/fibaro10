from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from shell_app.app.main import app


def response(url: str, payload: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json=payload, request=httpx.Request("GET", url))


class ShellAppTest(unittest.TestCase):
    def test_health_and_config_are_public(self) -> None:
        with TestClient(app) as client:
            health = client.get("/health")
            config = client.get("/api/app/config")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["service"], "shell_app")
        self.assertEqual(config.json()["shellUrl"], "http://192.168.20.218:8150")

    def test_frontend_redirects_without_login(self) -> None:
        with TestClient(app, follow_redirects=False) as client:
            result = client.get("/")
        self.assertEqual(result.status_code, 303)
        self.assertEqual(result.headers["location"], "/auth/login")

    def test_app_registry_requires_login(self) -> None:
        with TestClient(app) as client:
            result = client.get("/api/apps")
        self.assertEqual(result.status_code, 401)

    def test_app_registry_reports_all_domain_apps_as_live(self) -> None:
        async def fake_get(url: str, **_kwargs):
            if url.endswith("/api/auth/me"):
                return response(url, {"username": "master", "roleLabel": "Master"})
            if "revenue_app" in url:
                return response(url, {"ok": True, "build": "4"})
            if "parking_app" in url:
                return response(url, {"ok": True, "build": "1"})
            if any(service in url for service in ("sun_app", "energy_app", "operations_app", "maintenance_app", "system_app", "link_app")):
                return response(url, {"ok": True, "build": "1"})
            raise AssertionError(f"Uventet statusoppslag: {url}")

        cookies = {
            "fibaro10_session": "opaque-test-session",
        }
        with TestClient(app) as client:
            with patch.object(client.app.state.http, "get", new=AsyncMock(side_effect=fake_get)):
                result = client.get("/api/apps", cookies=cookies)

        self.assertEqual(result.status_code, 200)
        payload = result.json()
        self.assertEqual(payload["summary"], {"available": 8, "healthy": 8, "planned": 0})
        rows = {row["id"]: row for row in payload["apps"]}
        self.assertNotIn("fibaro10", rows)
        self.assertEqual(rows["revenue"]["build"], "4")
        self.assertEqual(rows["parking"]["status"], "ok")
        self.assertEqual(rows["parking"]["build"], "1")


if __name__ == "__main__":
    unittest.main()
