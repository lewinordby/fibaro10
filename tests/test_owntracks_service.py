import os
import tempfile
import unittest
import base64

_tmpdir = tempfile.mkdtemp(prefix="owntracks-service-test-")
os.environ.setdefault("OWNTRACKS_DATA_DIR", _tmpdir)
os.environ.setdefault("OWNTRACKS_DATABASE_URL", f"sqlite:///{os.path.join(_tmpdir, 'owntracks-test.db')}")

from owntracks_service.app import main as owntracks_main  # noqa: E402
from owntracks_service.app.main import (  # noqa: E402
    canonical_owntracks_topic,
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

    def test_owntracks_topic_suffixes_are_canonicalized(self) -> None:
        self.assertEqual(canonical_owntracks_topic("owntracks/lewi/Lewi/waypoints"), "owntracks/lewi/Lewi")
        self.assertEqual(canonical_owntracks_topic("owntracks/lewi/Lewi/event"), "owntracks/lewi/Lewi")
        self.assertEqual(canonical_owntracks_topic("owntracks/lewi/Lewi"), "owntracks/lewi/Lewi")

    def test_http_publish_stores_location(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/pub?user=tester&device=android",
                json={"_type": "location", "lat": 61.115, "lon": 10.466, "acc": 7, "tst": 1783080000},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
            health = client.get("/health").json()
            self.assertEqual(health["app"]["build"], owntracks_main.owntracks_build_summary()["build"])
            self.assertEqual(health["ingest"]["path"], "/pub")
            self.assertGreaterEqual(health["counts"]["locations"], 1)
            self.assertGreaterEqual(health["counts"]["devices"], 1)

    def test_admin_ui_is_closed_when_token_is_not_configured(self) -> None:
        original_token = owntracks_main.HTTP_TOKEN
        owntracks_main.HTTP_TOKEN = ""
        try:
            with TestClient(app) as client:
                page = client.get("/owntracks")
                self.assertEqual(page.status_code, 503)
                root = client.get("/")
                self.assertEqual(root.status_code, 503)
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

                root = client.get("/", headers={"Authorization": f"Basic {basic_auth}"})
                self.assertEqual(root.status_code, 200)
                self.assertIn("Build", root.text)

                page = client.get("/owntracks", headers={"Authorization": f"Basic {basic_auth}"})
                self.assertEqual(page.status_code, 200)
                self.assertIn("OwnTracks", page.text)

                module = client.get("/owntracks/api/module?token=test-token")
                self.assertEqual(module.status_code, 200)
                self.assertIn("tables", module.json())
                self.assertIn("buildLog", module.json()["metadata"])

                build_log = client.get("/owntracks/api/build-log?token=test-token")
                self.assertEqual(build_log.status_code, 200)
                self.assertEqual(build_log.json()["currentBuild"], owntracks_main.owntracks_build_summary()["build"])
        finally:
            owntracks_main.HTTP_TOKEN = original_token

    def test_query_token_is_accepted_even_if_basic_auth_is_wrong(self) -> None:
        original_token = owntracks_main.HTTP_TOKEN
        owntracks_main.HTTP_TOKEN = "test-token"
        wrong_basic_auth = base64.b64encode(b"admin:wrong-token").decode("ascii")
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/pub?token=test-token&user=tester&device=android",
                    headers={"Authorization": f"Basic {wrong_basic_auth}"},
                    json={"_type": "location", "lat": 61.115, "lon": 10.466, "acc": 7, "tst": 1783080300},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), [])
        finally:
            owntracks_main.HTTP_TOKEN = original_token

    def test_legacy_publish_route_is_removed(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/owntracks/pub?user=tester&device=android",
                json={"_type": "location", "lat": 61.115, "lon": 10.466, "acc": 7, "tst": 1783080350},
            )
            self.assertEqual(response.status_code, 404)

    def test_publish_waypoints_accepts_plain_list_payload(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/pub?user=waypoint-list&device=android",
                json=[
                    {"desc": "Hjemme", "lat": 61.111, "lon": 10.444, "rad": 125},
                    {"desc": "Sun2", "lat": 61.222, "lng": 10.555, "radius": 80},
                ],
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])

            rows = client.get("/api/owntracks/waypoints").json()["waypoints"]
            by_name = {
                row["waypointName"]: row
                for row in rows
                if row["topic"] == "owntracks/waypoint-list/android"
            }
            self.assertEqual(set(by_name), {"Hjemme", "Sun2"})
            self.assertEqual(by_name["Sun2"]["lon"], 10.555)

    def test_publish_waypoints_accepts_wrapped_payload_without_type(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/pub?user=waypoint-wrapped&device=android",
                json={"data": {"a": {"desc": "Kontor", "lat": 61.333, "lon": 10.666, "rad": 70}}},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])

            rows = client.get("/api/owntracks/waypoints").json()["waypoints"]
            names = {row["waypointName"] for row in rows if row["topic"] == "owntracks/waypoint-wrapped/android"}
            self.assertIn("Kontor", names)

    def test_payload_topic_suffix_is_stored_on_base_topic(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/pub",
                json={
                    "_type": "waypoints",
                    "topic": "owntracks/lewi/Lewi/waypoints",
                    "waypoints": [{"desc": "Lilletorget", "lat": 61.1, "lon": 10.4, "rad": 50}],
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])

            rows = client.get("/api/owntracks/waypoints").json()["waypoints"]
            names = {row["waypointName"] for row in rows if row["topic"] == "owntracks/lewi/Lewi"}
            self.assertIn("Lilletorget", names)

    def test_transition_without_defined_waypoint_does_not_create_waypoint_state(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/pub",
                json={
                    "_type": "transition",
                    "topic": "owntracks/transition-only/android/event",
                    "desc": "Udefinert",
                    "event": "enter",
                    "lat": 61.1,
                    "lon": 10.4,
                    "tst": 1783080900,
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])

            payload = client.get("/api/owntracks/waypoints").json()
            state_names = {row["waypointName"] for row in payload["waypoints"] if row["topic"] == "owntracks/transition-only/android"}
            event_names = {row["waypointName"] for row in payload["events"] if row["topic"] == "owntracks/transition-only/android"}
            self.assertNotIn("Udefinert", state_names)
            self.assertIn("Udefinert", event_names)


if __name__ == "__main__":
    unittest.main()
