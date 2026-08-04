from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from parking_app.app.main import app


class ParkingAppTest(unittest.TestCase):
    def test_health_and_config_are_available_without_login(self) -> None:
        with TestClient(app) as client:
            health = client.get("/health")
            config = client.get("/api/app/config")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["service"], "parking_app")
        self.assertEqual(config.status_code, 200)
        self.assertEqual(config.json()["name"], "Lilletorget Parkering")

    def test_frontend_redirects_to_login_without_cookies(self) -> None:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get("/parkeringer")
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/auth/login")

    def test_proxy_rejects_unrelated_endpoints(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/modules/soling")
        self.assertEqual(response.status_code, 404)

    def test_allowed_module_proxy_forwards_query_and_cookie(self) -> None:
        core_response = httpx.Response(
            200,
            json={"title": "Parkering"},
            request=httpx.Request("GET", "http://fibaro10:8110/api/modules/parkering"),
        )
        with TestClient(app) as client:
            with patch.object(client.app.state.core_client, "request", new=AsyncMock(return_value=core_response)) as core_request:
                response = client.get(
                    "/api/modules/parkering?view=parkeringer&day=2026-08-02",
                    headers={"cookie": "fibaro10_access_username=master; fibaro10_access_password=test"},
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Parkering")
        args, kwargs = core_request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(args[1], "/api/modules/parkering")
        self.assertEqual(str(kwargs["params"]), "view=parkeringer&day=2026-08-02")
        self.assertIn("fibaro10_access_username=master", kwargs["headers"]["Cookie"])

    def test_dynamic_vehicle_and_settlement_paths_are_allowed(self) -> None:
        responses = [
            httpx.Response(200, json={"plate": "AB12345"}, request=httpx.Request("GET", "http://fibaro10/api/parking/vehicles/ab12345")),
            httpx.Response(200, json={"id": 42}, request=httpx.Request("GET", "http://fibaro10/api/settlements/42")),
        ]
        with TestClient(app) as client:
            with patch.object(client.app.state.core_client, "request", new=AsyncMock(side_effect=responses)):
                vehicle = client.get("/api/parking/vehicles/AB12345")
                settlement = client.get("/api/settlements/42")
        self.assertEqual(vehicle.status_code, 200)
        self.assertEqual(settlement.status_code, 200)

    def test_native_lookup_worklists_are_allowed(self) -> None:
        core_response = httpx.Response(
            200,
            json={"count": 1, "limit": 100, "offset": 0, "rows": [{"plate": "AB12345"}]},
            request=httpx.Request("GET", "http://fibaro10/api/parkering/kjoretoy/mangler-navn"),
        )
        with TestClient(app) as client:
            with patch.object(client.app.state.core_client, "request", new=AsyncMock(return_value=core_response)) as core_request:
                response = client.get("/api/parkering/kjoretoy/mangler-navn?limit=100&offset=0")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rows"][0]["plate"], "AB12345")
        self.assertEqual(core_request.call_args.args[:2], ("GET", "/api/parkering/kjoretoy/mangler-navn"))

    def test_allowed_action_is_forwarded_as_post(self) -> None:
        core_response = httpx.Response(202, json={"message": "Startet"}, request=httpx.Request("POST", "http://fibaro10/api/actions/parkering/refresh"))
        with TestClient(app) as client:
            with patch.object(client.app.state.core_client, "request", new=AsyncMock(return_value=core_response)) as core_request:
                response = client.post("/api/actions/parkering/refresh")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["message"], "Startet")
        self.assertEqual(core_request.await_count, 1)
        self.assertEqual(core_request.call_args.args[:2], ("POST", "/api/actions/parkering/refresh"))


if __name__ == "__main__":
    unittest.main()
