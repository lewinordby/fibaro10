import os
import tempfile
import unittest
import base64
from datetime import datetime

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
            locations = client.get("/api/owntracks/map?hours=0&limit=10").json()["locations"]
            stored = next(row for row in locations if row["topic"] == "owntracks/tester/android")
            self.assertEqual(stored["origin"], "phone")
            self.assertFalse(stored["isSynthetic"])

    def test_map_api_filters_specific_time_range(self) -> None:
        topic = "owntracks/time-filter/android"
        with TestClient(app) as client:
            for lat, created_at in [
                (61.111, "2026-01-01T10:00:00Z"),
                (61.222, "2026-01-01T11:00:00Z"),
            ]:
                response = client.post(
                    "/pub",
                    json={"_type": "location", "topic": topic, "lat": lat, "lon": 10.466, "acc": 7, "created_at": created_at},
                )
                self.assertEqual(response.status_code, 200)

            payload = client.get("/api/owntracks/map?hours=0&start=2026-01-01T10:30:00Z&end=2026-01-01T11:30:00Z").json()
            rows = [row for row in payload["locations"] if row["topic"] == topic]
            self.assertEqual(payload["filterMode"], "custom")
            self.assertEqual(payload["start"], "2026-01-01T10:30:00Z")
            self.assertEqual(payload["end"], "2026-01-01T11:30:00Z")
            self.assertEqual([row["timestamp"] for row in rows], ["2026-01-01T11:00:00Z"])

            all_payload = client.get("/api/owntracks/map?hours=0&limit=0").json()
            all_rows = [row for row in all_payload["locations"] if row["topic"] == topic]
            self.assertIsNone(all_rows[0]["distanceFromPreviousM"])
            self.assertGreater(all_rows[1]["distanceFromPreviousM"], 12000)
            self.assertLess(all_rows[1]["distanceFromPreviousM"], 13000)

    def test_map_keeps_raw_poor_accuracy_but_excludes_it_from_calculations(self) -> None:
        topic = "owntracks/poor-accuracy/android"
        with TestClient(app) as client:
            response = client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 61.115, "lon": 10.466, "acc": 90, "tst": 1783080400},
            )
            self.assertEqual(response.status_code, 200)

            payload = client.get("/api/owntracks/map?hours=0&limit=0").json()
            raw_rows = [row for row in payload["locations"] if row["topic"] == topic]
            map_rows = [row for row in payload["mapLocations"] if row["topic"] == topic]
            self.assertEqual(len(raw_rows), 1)
            self.assertEqual(map_rows, [])
            self.assertFalse(raw_rows[0]["usableForCalculation"])
            self.assertEqual(raw_rows[0]["accuracyLimitM"], owntracks_main.MAX_CALCULATION_ACCURACY_M)
            self.assertGreaterEqual(payload["qualityPolicy"]["ignoredForAccuracy"], 1)

    def test_map_keeps_waypoint_definitions_out_of_track_line(self) -> None:
        topic = "owntracks/waypoint-not-track/android"
        with TestClient(app) as client:
            location = client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 61.115, "lon": 10.466, "acc": 5, "tst": 1783080450},
            )
            self.assertEqual(location.status_code, 200)

            waypoint = client.post(
                "/pub",
                json={
                    "_type": "waypoint",
                    "topic": f"{topic}/waypoint",
                    "desc": "Nytt sted",
                    "lat": 60.391,
                    "lon": 5.322,
                    "rad": 100,
                    "tst": 1783080460,
                },
            )
            self.assertEqual(waypoint.status_code, 200)

            payload = client.get("/api/owntracks/map?hours=0&limit=0").json()
            raw_rows = [row for row in payload["locations"] if row["topic"] == topic]
            map_rows = [row for row in payload["mapLocations"] if row["topic"] == topic]
            self.assertEqual([row["messageType"] for row in map_rows], ["location"])
            self.assertEqual(len([row for row in raw_rows if row["messageType"] == "waypoint"]), 1)
            raw_waypoint = next(row for row in raw_rows if row["messageType"] == "waypoint")
            self.assertFalse(raw_waypoint["usableForCalculation"])

    def test_waypoint_definition_does_not_move_device_last_position(self) -> None:
        topic = "owntracks/device-waypoint/android"
        with TestClient(app) as client:
            response = client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 61.115, "lon": 10.466, "acc": 5, "tst": 1783080470},
            )
            self.assertEqual(response.status_code, 200)

            waypoint = client.post(
                "/pub",
                json={
                    "_type": "waypoint",
                    "topic": f"{topic}/waypoint",
                    "desc": "Ikke siste posisjon",
                    "lat": 60.391,
                    "lon": 5.322,
                    "rad": 100,
                    "tst": 1783080480,
                },
            )
            self.assertEqual(waypoint.status_code, 200)

            devices = client.get("/api/owntracks/devices").json()["devices"]
            device = next(row for row in devices if row["topic"] == topic)
            self.assertEqual(device["lastLat"], 61.115)
            self.assertEqual(device["lastLon"], 10.466)

    def test_poor_accuracy_location_does_not_open_zone_visit(self) -> None:
        topic = "owntracks/poor-zone/android"
        with TestClient(app) as client:
            waypoint = client.post(
                "/pub",
                json={
                    "_type": "waypoint",
                    "topic": f"{topic}/waypoint",
                    "desc": "Presisjonstest",
                    "lat": 61.115,
                    "lon": 10.466,
                    "rad": 100,
                    "tst": 1783080500,
                },
            )
            self.assertEqual(waypoint.status_code, 200)

            location = client.post(
                "/pub",
                json={
                    "_type": "location",
                    "topic": topic,
                    "lat": 61.115,
                    "lon": 10.466,
                    "acc": 90,
                    "inregions": ["Presisjonstest"],
                    "tst": 1783080560,
                },
            )
            self.assertEqual(location.status_code, 200)

            visits = client.get("/api/owntracks/map?hours=0&limit=0").json()["zoneVisits"]
            matching_visits = [
                row
                for row in visits
                if row["topic"] == topic and row["waypointName"] == "Presisjonstest"
            ]
            self.assertEqual(matching_visits, [])

    def test_poor_accuracy_leave_is_raw_event_but_does_not_close_visit(self) -> None:
        topic = "owntracks/poor-leave/android"
        with TestClient(app) as client:
            client.post(
                "/pub",
                json={
                    "_type": "waypoint",
                    "topic": f"{topic}/waypoint",
                    "desc": "Hjemme",
                    "lat": 61.115,
                    "lon": 10.466,
                    "rad": 100,
                    "tst": 1783080600,
                },
            )
            inside = client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 61.115, "lon": 10.466, "acc": 5, "inregions": ["Hjemme"], "tst": 1783080660},
            )
            self.assertEqual(inside.status_code, 200)

            poor_leave = client.post(
                "/pub",
                json={
                    "_type": "transition",
                    "topic": f"{topic}/event",
                    "desc": "Hjemme",
                    "event": "leave",
                    "lat": 61.116,
                    "lon": 10.466,
                    "acc": 95,
                    "tst": 1783080720,
                },
            )
            self.assertEqual(poor_leave.status_code, 200)

            good_enter = client.post(
                "/pub",
                json={
                    "_type": "transition",
                    "topic": f"{topic}/event",
                    "desc": "Hjemme",
                    "event": "enter",
                    "lat": 61.115,
                    "lon": 10.466,
                    "acc": 5,
                    "tst": 1783080780,
                },
            )
            self.assertEqual(good_enter.status_code, 200)

            payload = client.get("/api/owntracks/map?hours=0&limit=0").json()
            matching_visits = [row for row in payload["zoneVisits"] if row["topic"] == topic and row["waypointName"] == "Hjemme"]
            self.assertEqual(len(matching_visits), 1)
            self.assertEqual(matching_visits[0]["status"], "open")

            waypoints = client.get("/api/owntracks/waypoints").json()
            waypoint = next(row for row in waypoints["waypoints"] if row["topic"] == topic and row["waypointName"] == "Hjemme")
            self.assertTrue(waypoint["isInside"])
            ignored_leave = next(row for row in waypoints["events"] if row["topic"] == topic and row["eventType"] == "leave")
            self.assertTrue(ignored_leave["ignoredForState"])
            self.assertIn("Lav presisjon", ignored_leave["ignoredReason"])

    def test_zone_visit_uses_hysteresis_before_closing(self) -> None:
        topic = "owntracks/hysteresis/android"
        with TestClient(app) as client:
            client.post(
                "/pub",
                json={"_type": "waypoint", "topic": f"{topic}/waypoint", "desc": "Kontor", "lat": 61.115, "lon": 10.466, "rad": 100, "tst": 1783080800},
            )
            client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 61.115, "lon": 10.466, "acc": 5, "tst": 1783080860},
            )
            # About 117 m east at this latitude: outside enter radius, but inside radius + buffer.
            client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 61.115, "lon": 10.4682, "acc": 5, "tst": 1783080920},
            )
            still_open = client.get("/api/owntracks/map?hours=0&limit=0").json()["zoneVisits"]
            matching_open = [row for row in still_open if row["topic"] == topic and row["waypointName"] == "Kontor"]
            self.assertEqual(len(matching_open), 1)
            self.assertEqual(matching_open[0]["status"], "open")

            # Clearly outside radius + buffer.
            client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 61.115, "lon": 10.4694, "acc": 5, "tst": 1783080980},
            )
            closed = client.get("/api/owntracks/map?hours=0&limit=0").json()["zoneVisits"]
            matching_closed = [row for row in closed if row["topic"] == topic and row["waypointName"] == "Kontor"]
            self.assertEqual(len(matching_closed), 1)
            self.assertEqual(matching_closed[0]["status"], "closed")
            self.assertEqual(matching_closed[0]["leaveSource"], "computed-position")

    def test_closed_zone_visits_under_one_minute_are_hidden_from_overviews(self) -> None:
        topic = "owntracks/short-visit/android"
        with TestClient(app) as client:
            client.post(
                "/pub",
                json={"_type": "waypoint", "topic": f"{topic}/waypoint", "desc": "Kort stopp", "lat": 61.115, "lon": 10.466, "rad": 30, "tst": 1783081100},
            )
            client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 61.115, "lon": 10.466, "acc": 5, "tst": 1783081110},
            )
            client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 61.116, "lon": 10.466, "acc": 5, "tst": 1783081140},
            )

            map_payload = client.get("/api/owntracks/map?hours=0&limit=0").json()
            matching_visits = [row for row in map_payload["zoneVisits"] if row["topic"] == topic and row["waypointName"] == "Kort stopp"]
            self.assertEqual(matching_visits, [])
            self.assertGreaterEqual(map_payload["qualityPolicy"]["hiddenShortVisits"], 1)
            self.assertEqual(map_payload["qualityPolicy"]["minOverviewVisitSeconds"], owntracks_main.MIN_OVERVIEW_VISIT_SECONDS)

            summary = client.get("/api/owntracks/zone-summary?hours=0&limit=100").json()
            matching_summary = [row for row in summary["summary"] if row["topic"] == topic and row["waypointName"] == "Kort stopp"]
            self.assertEqual(matching_summary, [])
            self.assertGreaterEqual(summary["totals"]["hiddenShortVisits"], 1)

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
            matching_events = [row for row in payload["events"] if row["topic"] == "owntracks/transition-only/android"]
            event_names = {row["waypointName"] for row in matching_events}
            self.assertNotIn("Udefinert", state_names)
            self.assertIn("Udefinert", event_names)
            self.assertTrue(all(row["origin"] == "phone" for row in matching_events))
            self.assertTrue(all(row["isSynthetic"] is False for row in matching_events))

    def test_inregions_and_computed_position_do_not_open_duplicate_zone_visit(self) -> None:
        topic = "owntracks/zone-dup/android"
        with TestClient(app) as client:
            waypoint = client.post(
                "/pub",
                json={
                    "_type": "waypoint",
                    "topic": f"{topic}/waypoint",
                    "desc": "Kontor",
                    "lat": 61.115,
                    "lon": 10.466,
                    "rad": 100,
                    "tst": 1783081000,
                },
            )
            self.assertEqual(waypoint.status_code, 200)

            location = client.post(
                "/pub",
                json={
                    "_type": "location",
                    "topic": topic,
                    "lat": 61.115,
                    "lon": 10.466,
                    "acc": 5,
                    "inregions": ["Kontor"],
                    "tst": 1783081060,
                },
            )
            self.assertEqual(location.status_code, 200)

            visits = client.get("/api/owntracks/map?hours=0&limit=0").json()["zoneVisits"]
            matching_visits = [
                row
                for row in visits
                if row["topic"] == topic and row["waypointName"] == "Kontor"
            ]
            self.assertEqual(len(matching_visits), 1)

    def test_transition_does_not_move_waypoint_or_reopen_computed_visit(self) -> None:
        topic = "owntracks/transition-zone/android"
        with TestClient(app) as client:
            waypoint = client.post(
                "/pub",
                json={
                    "_type": "waypoint",
                    "topic": f"{topic}/waypoint",
                    "desc": "Hjem",
                    "lat": 61.115,
                    "lon": 10.466,
                    "rad": 30,
                    "tst": 1783082000,
                },
            )
            self.assertEqual(waypoint.status_code, 200)

            inside = client.post(
                "/pub",
                json={
                    "_type": "location",
                    "topic": topic,
                    "lat": 61.115,
                    "lon": 10.466,
                    "acc": 5,
                    "inregions": ["Hjem"],
                    "tst": 1783082060,
                },
            )
            self.assertEqual(inside.status_code, 200)

            leave = client.post(
                "/pub",
                json={
                    "_type": "transition",
                    "topic": f"{topic}/event",
                    "desc": "Hjem",
                    "event": "leave",
                    "lat": 61.1154,
                    "lon": 10.466,
                    "acc": 5,
                    "tst": 1783082120,
                },
            )
            self.assertEqual(leave.status_code, 200)

            map_payload = client.get("/api/owntracks/map?hours=0&limit=0").json()
            matching_visits = [
                row
                for row in map_payload["zoneVisits"]
                if row["topic"] == topic and row["waypointName"] == "Hjem"
            ]
            self.assertEqual(len(matching_visits), 1)
            self.assertEqual(matching_visits[0]["status"], "closed")
            self.assertEqual(matching_visits[0]["enterSource"], "inregions")
            self.assertEqual(matching_visits[0]["leaveSource"], "transition")

            waypoints = client.get("/api/owntracks/waypoints").json()["waypoints"]
            saved = next(row for row in waypoints if row["topic"] == topic and row["waypointName"] == "Hjem")
            self.assertEqual(saved["lat"], 61.115)
            self.assertEqual(saved["lon"], 10.466)

    def test_transition_enter_is_merged_into_computed_visit(self) -> None:
        topic = "owntracks/transition-enter-merge/android"
        with TestClient(app) as client:
            client.post(
                "/pub",
                json={"_type": "waypoint", "topic": f"{topic}/waypoint", "desc": "Arbeid", "lat": 61.115, "lon": 10.466, "rad": 30, "tst": 1783102000},
            )
            client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 61.115, "lon": 10.466, "acc": 5, "tst": 1783102060},
            )
            client.post(
                "/pub",
                json={
                    "_type": "transition",
                    "topic": f"{topic}/event",
                    "desc": "Arbeid",
                    "event": "enter",
                    "lat": 61.115,
                    "lon": 10.466,
                    "acc": 5,
                    "tst": 1783102090,
                },
            )

            visits = client.get("/api/owntracks/map?hours=0&limit=0").json()["zoneVisits"]
            matching = [row for row in visits if row["topic"] == topic and row["waypointName"] == "Arbeid"]
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0]["status"], "open")
            self.assertEqual(matching[0]["enterSource"], "transition+computed-position")

    def test_late_transition_leave_is_merged_into_closed_computed_visit(self) -> None:
        topic = "owntracks/transition-leave-merge/android"
        with TestClient(app) as client:
            client.post(
                "/pub",
                json={"_type": "waypoint", "topic": f"{topic}/waypoint", "desc": "Butikk", "lat": 61.115, "lon": 10.466, "rad": 30, "tst": 1783103000},
            )
            client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 61.115, "lon": 10.466, "acc": 5, "tst": 1783103060},
            )
            client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 61.116, "lon": 10.466, "acc": 5, "tst": 1783103180},
            )
            client.post(
                "/pub",
                json={
                    "_type": "transition",
                    "topic": f"{topic}/event",
                    "desc": "Butikk",
                    "event": "leave",
                    "lat": 61.116,
                    "lon": 10.466,
                    "acc": 5,
                    "tst": 1783103160,
                },
            )

            visits = client.get("/api/owntracks/map?hours=0&limit=0").json()["zoneVisits"]
            matching = [row for row in visits if row["topic"] == topic and row["waypointName"] == "Butikk"]
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0]["status"], "closed")
            self.assertEqual(matching[0]["leaveSource"], "transition+computed-position")
            self.assertEqual(matching[0]["durationSeconds"], 100)

    def test_local_waypoint_can_be_created_and_rebuilds_visits(self) -> None:
        topic = "owntracks/local-zone/android"
        with TestClient(app) as client:
            first = client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 62.111, "lon": 11.222, "acc": 5, "tst": 1783090000},
            )
            second = client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 62.1111, "lon": 11.2221, "acc": 5, "tst": 1783090600},
            )
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)

            created = client.post(
                "/api/owntracks/waypoints",
                json={
                    "topic": topic,
                    "name": "Lokalt teststed",
                    "lat": 62.111,
                    "lon": 11.222,
                    "radiusM": 100,
                    "address": "Testveien 1",
                },
            )
            self.assertEqual(created.status_code, 200)
            self.assertEqual(created.json()["waypoint"]["source"], "server-manual")
            self.assertGreaterEqual(created.json()["locationsProcessed"], 2)

            visits = client.get("/api/owntracks/map?hours=0&limit=0").json()["zoneVisits"]
            matching = [row for row in visits if row["topic"] == topic and row["waypointName"] == "Lokalt teststed"]
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0]["enterSource"], "computed-position")

    def test_local_waypoint_can_be_patched_and_disabled(self) -> None:
        topic = "owntracks/local-zone-edit/android"
        with TestClient(app) as client:
            client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 62.211, "lon": 11.322, "acc": 5, "tst": 1783091000},
            )
            created = client.post(
                "/api/owntracks/waypoints",
                json={"topic": topic, "name": "Redigerbar", "category": "Testkategori", "lat": 62.211, "lon": 11.322, "radiusM": 90},
            )
            self.assertEqual(created.status_code, 200)
            waypoint_id = created.json()["waypoint"]["id"]
            self.assertEqual(created.json()["waypoint"]["category"], "Testkategori")

            patched = client.patch(
                f"/api/owntracks/waypoints/{waypoint_id}",
                json={"name": "Redigert", "category": "Oppdatert", "radiusM": 120, "notes": "Test", "rebuildHistory": False},
            )
            self.assertEqual(patched.status_code, 200)
            self.assertEqual(patched.json()["waypoint"]["waypointName"], "Redigert")
            self.assertEqual(patched.json()["waypoint"]["category"], "Oppdatert")
            self.assertEqual(patched.json()["waypoint"]["radiusM"], 120)

            disabled = client.delete(f"/api/owntracks/waypoints/{waypoint_id}?rebuild=false")
            self.assertEqual(disabled.status_code, 200)
            rows = client.get("/api/owntracks/waypoints").json()["waypoints"]
            saved = next(row for row in rows if row["id"] == waypoint_id)
            self.assertFalse(saved["isActive"])

    def test_zone_summary_returns_grouped_duration(self) -> None:
        topic = "owntracks/zone-summary/android"
        with TestClient(app) as client:
            client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 62.311, "lon": 11.422, "acc": 5, "tst": 1783092000},
            )
            client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 62.311, "lon": 11.422, "acc": 5, "tst": 1783092300},
            )
            created = client.post(
                "/api/owntracks/waypoints",
                json={"topic": topic, "name": "Oppsummert", "lat": 62.311, "lon": 11.422, "radiusM": 100},
            )
            self.assertEqual(created.status_code, 200)

            payload = client.get("/api/owntracks/zone-summary?hours=0").json()
            rows = [row for row in payload["summary"] if row["topic"] == topic and row["waypointName"] == "Oppsummert"]
            self.assertEqual(len(rows), 1)
            self.assertGreaterEqual(rows[0]["visits"], 1)
            self.assertGreaterEqual(rows[0]["totalDurationSeconds"], 0)
            self.assertIn("totalDuration", rows[0])

    def test_fibaro_summary_returns_compact_active_place_and_quality(self) -> None:
        topic = "owntracks/fibaro-summary/android"
        with TestClient(app) as client:
            client.post(
                "/pub",
                json={"_type": "location", "topic": topic, "lat": 62.411, "lon": 11.522, "acc": 5, "tst": 1783094000},
            )
            created = client.post(
                "/api/owntracks/waypoints",
                json={"topic": topic, "name": "Fibaro teststed", "category": "Test", "lat": 62.411, "lon": 11.522, "radiusM": 100},
            )
            self.assertEqual(created.status_code, 200)

            payload = client.get("/api/owntracks/fibaro-summary?hours=0").json()
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["activePlace"]["waypointName"], "Fibaro teststed")
            self.assertEqual(payload["activePlace"]["category"], "Test")
            self.assertIn("quality", payload)
            self.assertGreaterEqual(payload["quality"]["usableLocations"], 1)

    def test_stop_suggestions_find_stationary_cluster_without_geocode(self) -> None:
        topic = "owntracks/stop-suggestion/android"
        with TestClient(app) as client:
            for offset, lat, lon in (
                (0, 62.50100, 11.70100),
                (600, 62.50105, 11.70102),
                (1200, 62.50108, 11.70101),
            ):
                response = client.post(
                    "/pub",
                    json={"_type": "location", "topic": topic, "lat": lat, "lon": lon, "acc": 8, "tst": 1783100000 + offset},
                )
                self.assertEqual(response.status_code, 200)

            payload = client.get(
                "/api/owntracks/waypoint-suggestions?hours=0&min_minutes=10&radius_m=120&include_address=false"
            ).json()
            suggestions = [row for row in payload["suggestions"] if row["topic"] == topic]
            self.assertGreaterEqual(len(suggestions), 1)
            self.assertGreaterEqual(suggestions[0]["totalDurationSeconds"], 600)
            self.assertEqual(suggestions[0]["visits"], 1)

    def test_diagnostics_flags_stale_positions_and_large_gaps(self) -> None:
        topic = "owntracks/diagnostics/android"
        with TestClient(app) as client:
            for offset, lat in ((0, 62.60100), (60, 62.60200)):
                response = client.post(
                    "/pub",
                    json={"_type": "location", "topic": topic, "lat": lat, "lon": 11.80100, "acc": 8, "tst": 1783105000 + offset},
                )
                self.assertEqual(response.status_code, 200)

            with owntracks_main.SessionLocal() as session:
                rows = (
                    session.query(owntracks_main.OwnTracksLocation)
                    .filter(owntracks_main.OwnTracksLocation.topic == topic)
                    .order_by(owntracks_main.OwnTracksLocation.id.asc())
                    .all()
                )
                self.assertEqual(len(rows), 2)
                rows[0].timestamp = datetime(2026, 1, 1, 10, 0, 0)
                rows[0].received_at = datetime(2026, 1, 1, 10, 30, 0)
                rows[1].timestamp = datetime(2026, 1, 1, 10, 1, 0)
                rows[1].received_at = datetime(2026, 1, 1, 11, 30, 0)
                session.commit()

            payload = client.get("/api/owntracks/diagnostics?hours=0&stale_minutes=10&gap_minutes=20").json()
            self.assertGreaterEqual(payload["counts"]["staleLocations"], 2)
            self.assertGreaterEqual(payload["counts"]["largeGaps"], 1)
            self.assertTrue(any(row["severity"] in {"bad", "warning"} for row in payload["recommendations"]))


if __name__ == "__main__":
    unittest.main()
