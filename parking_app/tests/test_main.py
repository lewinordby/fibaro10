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
            manifest = client.get("/manifest.webmanifest")
            icon = client.get("/pwa-icon-512.png")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["service"], "parking_app")
        self.assertEqual(config.status_code, 200)
        self.assertEqual(config.json()["name"], "Lilletorget Parkering")
        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(manifest.json()["name"], "Lilletorget Parkering")
        self.assertEqual(manifest.json()["theme_color"], "#0284c7")
        self.assertTrue(manifest.headers["content-type"].startswith("application/manifest+json"))
        self.assertEqual(icon.status_code, 200)

    def test_frontend_redirects_to_login_without_cookies(self) -> None:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get("/parkeringer")
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/auth/login")

    def test_frontend_exposes_manifest_and_apple_metadata(self) -> None:
        with TestClient(app) as client:
            response = client.get("/observerte-biler", cookies={"lilletorget_session": "test"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text.count('rel="manifest"'), 1)
        self.assertIn('rel="apple-touch-icon"', response.text)
        self.assertIn('name="theme-color"', response.text)

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

    def test_car_detection_detail_path_is_allowed(self) -> None:
        core_response = httpx.Response(
            200,
            json={"plate": "AB12345", "detections": [{"recognitionId": 42}]},
            request=httpx.Request("GET", "http://fibaro10/api/cars/day/AB12345/detections"),
        )
        with TestClient(app) as client:
            with patch.object(client.app.state.core_client, "request", new=AsyncMock(return_value=core_response)) as core_request:
                response = client.get("/api/cars/day/AB12345/detections?day=2026-08-07")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detections"][0]["recognitionId"], 42)
        self.assertEqual(str(core_request.call_args.kwargs["params"]), "day=2026-08-07")

    def test_native_lookup_worklists_are_allowed(self) -> None:
        core_response = httpx.Response(
            200,
            json={"title": "Oppslag", "cards": [], "tables": [{"title": "Mangler navn", "rows": [{"plate": "AB12345"}]}]},
            request=httpx.Request("GET", "http://fibaro10/api/modules/parkering"),
        )
        with TestClient(app) as client:
            with patch.object(client.app.state.core_client, "get", new=AsyncMock(return_value=core_response)) as core_get:
                response = client.get("/api/parkering/kjoretoy/mangler-navn?limit=100&offset=0")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rows"][0]["plate"], "AB12345")
        self.assertEqual(core_get.call_args.args, ("/api/modules/parkering",))
        self.assertEqual(core_get.call_args.kwargs["params"], {"view": "oppslag"})

    def test_area_lookup_adapter_uses_the_filtered_core_worklist(self) -> None:
        core_response = httpx.Response(
            200,
            json={
                "title": "Oppslag",
                "cards": [],
                "tables": [
                    {
                        "title": "Kjøretøy uten område",
                        "rows": [{"plate": "AB12345"}, {"plate": "XY98765"}, {"plate": "SV54321"}],
                    }
                ],
            },
            request=httpx.Request("GET", "http://fibaro10/api/modules/parkering"),
        )
        with TestClient(app) as client:
            with patch.object(client.app.state.core_client, "get", new=AsyncMock(return_value=core_response)) as core_get:
                response = client.get("/api/parkering/kjoretoy/mangler-omrade?limit=1&offset=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"count": 3, "limit": 1, "offset": 1, "rows": [{"plate": "XY98765"}]})
        self.assertEqual(core_get.call_args.kwargs["params"], {"view": "oppslag", "filter": "mangler-omrade"})

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
