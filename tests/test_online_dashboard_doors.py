import os
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

from online_dashboard.app import main as online_main  # noqa: E402


class OnlineDashboardDoorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 7, 12, 12, 0, tzinfo=ZoneInfo("Europe/Oslo"))

    def test_solroom_payload_uses_operational_labels(self) -> None:
        config = online_main.SOLROOM_DOOR_BY_KEY["door_solrom_01"]
        open_row = {
            "id": 1,
            "timestamp": self.now - timedelta(minutes=4),
            "action": "OPEN",
            "state": True,
            "battery_level": 93,
            "device_name": "98.0 Rom 1",
        }
        closed_row = {
            "id": 2,
            "timestamp": self.now - timedelta(minutes=2),
            "action": "CLOSED",
            "state": False,
            "battery_level": 92,
            "device_name": "98.0 Rom 1",
        }

        open_payload = online_main.door_status_payload(config, open_row, self.now)
        closed_payload = online_main.door_status_payload(config, closed_row, self.now)

        self.assertEqual(open_payload["state"], "open")
        self.assertEqual(open_payload["state_label"], "Ledig")
        self.assertEqual(closed_payload["state"], "closed")
        self.assertEqual(closed_payload["state_label"], "I bruk")

    def test_solroom_summary_and_cards_tolerate_unknown_without_timestamp(self) -> None:
        open_payload = online_main.door_status_payload(
            online_main.SOLROOM_DOOR_BY_KEY["door_solrom_01"],
            {"timestamp": self.now, "action": "OPEN", "state": True},
            self.now,
        )
        planned_unknown = online_main.door_status_payload(
            online_main.SOLROOM_DOOR_BY_KEY["door_solrom_02"],
            None,
            self.now,
        )

        summary = online_main.render_solroom_door_summary([open_payload, planned_unknown])
        cards = online_main.render_door_dashboard_cards([planned_unknown, open_payload])

        self.assertIn("1 ledige", summary)
        self.assertIn("1 ukjent", summary)
        self.assertIn("is-solrom", cards)
        self.assertLess(cards.index("Solrom 1"), cards.index("Solrom 2"))

    def test_solroom_overview_links_to_room_details(self) -> None:
        payload = online_main.door_status_payload(
            online_main.SOLROOM_DOOR_BY_KEY["door_solrom_01"],
            {"timestamp": self.now, "action": "OPEN", "state": True},
            self.now,
        )

        html = online_main.render_door_overview([payload], "/solrom")

        self.assertIn('href="/solrom/door_solrom_01"', html)
        self.assertIn("Solrom 1", html)
        self.assertIn("Ledig", html)

    def test_door_alarm_rendering_prioritizes_active_alarm(self) -> None:
        alarm_item = {
            "title": "Solrom 4",
            "state": "closed",
            "state_label": "I bruk",
            "alarm_active": True,
            "missing_session": True,
            "duration_label": "9 min siden",
        }
        alarm_data = {
            "summary": {"alarms": 1, "watch": 0, "busy": 1, "rooms": 12},
            "alarms": [alarm_item],
            "watch": [],
            "items": [alarm_item],
        }

        self.assertEqual(online_main.render_door_alarm_summary(alarm_data), "1 alarm")
        cards = online_main.render_door_alarm_dashboard_cards(alarm_data)
        alarm_list = online_main.render_door_alarm_list(alarm_data)

        self.assertIn("Solrom 4", cards)
        self.assertIn("Alarm", cards)
        self.assertIn("uten Sun2-time", alarm_list)


if __name__ == "__main__":
    unittest.main()
