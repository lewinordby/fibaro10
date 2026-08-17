from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from revenue_app.app.main import app


class RevenueAppTest(unittest.TestCase):
    def test_health_and_config_are_available_without_login(self) -> None:
        with TestClient(app) as client:
            health = client.get("/health")
            config = client.get("/api/app/config")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["service"], "revenue_app")
        self.assertEqual(config.status_code, 200)
        self.assertEqual(config.json()["name"], "Lilletorget Omsetning")

    def test_frontend_redirects_to_login_without_cookies(self) -> None:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get("/oversikt")
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/auth/login")

    def test_proxy_rejects_non_revenue_endpoints(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/modules/parkering")
        self.assertEqual(response.status_code, 404)

    def test_allowed_proxy_forwards_query_and_cookie(self) -> None:
        core_response = httpx.Response(
            200,
            json={"title": "Omsetning"},
            request=httpx.Request("GET", "http://fibaro10:8110/api/modules/omsetning"),
        )
        with TestClient(app) as client:
            with patch.object(client.app.state.core_client, "request", new=AsyncMock(return_value=core_response)) as core_request:
                response = client.get(
                    "/api/modules/omsetning?view=oversikt",
                    headers={"cookie": "fibaro10_access_username=master; fibaro10_access_password=test"},
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Omsetning")
        args, kwargs = core_request.call_args
        self.assertEqual(args[0], "GET")
        self.assertEqual(args[1], "/api/modules/omsetning")
        self.assertEqual(str(kwargs["params"]), "view=oversikt")
        self.assertIn("fibaro10_access_username=master", kwargs["headers"]["Cookie"])

    def test_login_forwards_public_origin_and_relays_shared_cookie(self) -> None:
        core_response = httpx.Response(
            303,
            headers={
                "location": "/status/omsetning",
                "set-cookie": "lilletorget_session=shared-token; Domain=.lilletorget.net; Path=/; HttpOnly; Secure; SameSite=lax",
            },
            request=httpx.Request("POST", "http://fibaro10:8110/auth/login"),
        )
        auth_client = AsyncMock()
        auth_client.post.return_value = core_response
        auth_client.__aenter__.return_value = auth_client
        auth_client.__aexit__.return_value = None
        with TestClient(app, follow_redirects=False) as client:
            with patch("microapp_backend.runtime.httpx.AsyncClient", return_value=auth_client):
                response = client.post(
                    "/auth/login",
                    data={"username": "master", "password": "secret"},
                    headers={"host": "omsetning.lilletorget.net", "x-forwarded-proto": "https"},
                )

        self.assertEqual(response.status_code, 303)
        self.assertIn("domain=.lilletorget.net", response.headers["set-cookie"].lower())
        _, kwargs = auth_client.post.call_args
        self.assertEqual(kwargs["headers"]["X-Forwarded-Host"], "omsetning.lilletorget.net")
        self.assertEqual(kwargs["headers"]["X-Forwarded-Proto"], "https")
        self.assertEqual(kwargs["headers"]["X-Lilletorget-Public-Host"], "omsetning.lilletorget.net")
        self.assertEqual(kwargs["headers"]["X-Lilletorget-Public-Proto"], "https")


if __name__ == "__main__":
    unittest.main()
