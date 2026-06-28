import unittest

from fastapi.testclient import TestClient

from v1_reference.app.main import app


class TestV1Reference(unittest.TestCase):
    def test_health_is_disconnected(self):
        response = TestClient(app).get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], "reference_only")
        self.assertEqual(payload["data_sources"], "disabled")
        self.assertGreater(payload["pages"], 30)

    def test_serves_old_routes_without_data_sources(self):
        client = TestClient(app)

        for path in ["/", "/parkering/oversikt", "/energi/laster", "/ventilasjon/dagslogg-temp"]:
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Datakilder frakoblet", response.text)
            self.assertIn("gjør ingen databasekall", response.text)
