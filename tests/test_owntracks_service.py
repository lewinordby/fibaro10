import os
import tempfile
import unittest
import base64

_tmpdir = tempfile.mkdtemp(prefix="owntracks-service-test-")
os.environ.setdefault("OWNTRACKS_DATA_DIR", _tmpdir)
os.environ.setdefault("OWNTRACKS_DATABASE_URL", f"sqlite:///{os.path.join(_tmpdir, 'owntracks-test.db')}")

from owntracks_service.app import main as owntracks_main  # noqa: E402
from owntracks_service.app.main import (  # noqa: E402
    normalized_event_type,
    waypoint_items_from_plural,
    waypoint_name_from_payload,
    waypoint_names,
    waypoint_state_for_event,
)
from fastapi.testclient import TestClient  # noqa: E402

app = owntracks_main.app


class OwnTracksServiceTests(unittest.TestCase):
    def test_region_names_are_normalized_and_deduplicated(self) -> None:
        self.assertEqual(waypoint_names(["Hjemme", "hjemme", "", None, "Sun2"]), ["Hjemme", "Sun2"])

    def test_event_aliases_are_normalized(self) -> None:
        self.assertEqual(normalized_event_type("entry"), "enter")
        self.assertEqual(normalized_event_type("departure"), "leave")
        self.assertEqual(waypoint_state_for_event("exit"), ("outside", False))

    def test_waypoint_name_prefers_description(self) -> None:
        self.assertEqual(waypoint_name_from_payload({"desc": "Hjemme", "rid": "abc123"}), "Hjemme")

    def test_plural_waypoints_accept_list_and_dict(self) -> None:
        list_payload = {"waypoints": [{"desc": "A"}, {"desc": "B"}]}
        dict_payload = {"waypoints": {"a": {"desc": "A"}, "b": {"desc": "B"}}}
        self.assertEqual([item["desc"] for item in waypoint_items_from_plural(list_payload)], ["A", "B"])
        self.assertEqual([item["desc"] for item in waypoint_items_from_plural(dict_payload)], ["A", "B"])

    def test_http_publish_stores_location(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/owntracks/pub?user=tester&device=android",
                json={"_type": "location", "lat": 61.115, "lon": 10.466, "acc": 7, "tst": 1783080000},
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["stored"])
            health = client.get("/health").json()
            self.assertGreaterEqual(health["counts"]["locations"], 1)
            self.assertGreaterEqual(health["counts"]["devices"], 1)

    def test_admin_ui_is_closed_when_token_is_not_configured(self) -> None:
        original_token = owntracks_main.HTTP_TOKEN
        owntracks_main.HTTP_TOKEN = ""
        try:
            with TestClient(app) as client:
                page = client.get("/owntracks")
                self.assertEqual(page.status_code, 503)
        finally:
            owntracks_main.HTTP_TOKEN = original_token

    def test_admin_ui_and_external_api_require_and_accept_token(self) -> None:
        original_token = owntracks_main.HTTP_TOKEN
        owntracks_main.HTTP_TOKEN = "test-token"
        basic_auth = base64.b64encode(b"admin:test-token").decode("ascii")
        try:
            with TestClient(app) as client:
                missing = client.get("/owntracks")
                self.assertEqual(missing.status_code, 401)
                self.assertIn("WWW-Authenticate", missing.headers)

                page = client.get("/owntracks", headers={"Authorization": f"Basic {basic_auth}"})
                self.assertEqual(page.status_code, 200)
                self.assertIn("OwnTracks", page.text)

                module = client.get("/owntracks/api/module?token=test-token")
                self.assertEqual(module.status_code, 200)
                self.assertIn("tables", module.json())
        finally:
            owntracks_main.HTTP_TOKEN = original_token

if __name__ == "__main__":
    unittest.main()
