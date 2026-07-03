import unittest
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

from main import (
    OwnTracksWaypointEvent,
    owntracks_duration_label,
    owntracks_normalized_event_type,
    owntracks_waypoint_visit_rows,
    owntracks_waypoint_name_from_payload,
    owntracks_waypoint_names,
    owntracks_waypoint_state_for_event,
)
from datetime import datetime


class OwnTracksWaypointTests(unittest.TestCase):
    def test_region_names_are_normalized_and_deduplicated(self) -> None:
        self.assertEqual(owntracks_waypoint_names(["Hjemme", "hjemme", "", None, "Sun2"]), ["Hjemme", "Sun2"])

    def test_region_names_accept_single_value(self) -> None:
        self.assertEqual(owntracks_waypoint_names("Lilletorget"), ["Lilletorget"])

    def test_waypoint_name_prefers_description(self) -> None:
        self.assertEqual(
            owntracks_waypoint_name_from_payload({"desc": "Hjemme", "rid": "abc123"}),
            "Hjemme",
        )

    def test_event_state_mapping(self) -> None:
        self.assertEqual(owntracks_waypoint_state_for_event("enter"), ("inside", True))
        self.assertEqual(owntracks_waypoint_state_for_event("leave"), ("outside", False))
        self.assertEqual(owntracks_waypoint_state_for_event("defined"), ("defined", None))
        self.assertEqual(owntracks_waypoint_state_for_event("entry"), ("inside", True))
        self.assertEqual(owntracks_waypoint_state_for_event("exit"), ("outside", False))

    def test_event_aliases_are_normalized(self) -> None:
        self.assertEqual(owntracks_normalized_event_type("entry"), "enter")
        self.assertEqual(owntracks_normalized_event_type("departure"), "leave")

    def test_visit_rows_pair_enter_and_leave(self) -> None:
        rows = [
            OwnTracksWaypointEvent(
                id=1,
                topic="owntracks/lewi/iphone",
                username="lewi",
                device="iphone",
                waypoint_name="Lilletorget 3",
                event_type="enter",
                timestamp=datetime(2026, 7, 3, 10, 0),
                received_at=datetime(2026, 7, 3, 10, 0, 1),
                source_message_type="transition",
            ),
            OwnTracksWaypointEvent(
                id=2,
                topic="owntracks/lewi/iphone",
                username="lewi",
                device="iphone",
                waypoint_name="Lilletorget 3",
                event_type="leave",
                timestamp=datetime(2026, 7, 3, 11, 15),
                received_at=datetime(2026, 7, 3, 11, 15, 1),
                source_message_type="transition",
            ),
        ]
        visits = owntracks_waypoint_visit_rows(rows, datetime(2026, 7, 3, 12, 0))
        self.assertEqual(len(visits), 1)
        self.assertEqual(visits[0]["waypoint_name"], "Lilletorget 3")
        self.assertEqual(visits[0]["duration"], "1 t 15 min")
        self.assertEqual(visits[0]["status"], "Avsluttet")

    def test_duration_label_for_short_visit(self) -> None:
        self.assertEqual(
            owntracks_duration_label(datetime(2026, 7, 3, 10, 0), datetime(2026, 7, 3, 10, 9, 40)),
            "10 min",
        )


if __name__ == "__main__":
    unittest.main()
