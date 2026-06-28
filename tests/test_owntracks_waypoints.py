import unittest
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

from main import (
    owntracks_waypoint_name_from_payload,
    owntracks_waypoint_names,
    owntracks_waypoint_state_for_event,
)


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


if __name__ == "__main__":
    unittest.main()
