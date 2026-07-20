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

        self.assertIn("Solrom 4", cards)
        self.assertIn("Alarm", cards)

    def test_mobile_door_control_shows_today_times_and_alarm_without_date(self) -> None:
        control = {
            "rows": [
                {
                    "title": "Solrom 5",
                    "closed_at": datetime(2026, 7, 20, 13, 12, 15),
                    "opened_at": datetime(2026, 7, 20, 13, 38, 6),
                    "duration_label": "25 min",
                    "expected_exit_at": datetime(2026, 7, 20, 13, 29),
                    "exit_delta_minutes": 9,
                    "severity": "alert",
                    "status": "Alarm",
                    "deviation": "Alarmgrense etter solslutt",
                    "session": {
                        "started_at": datetime(2026, 7, 20, 13, 11),
                        "ended_at": datetime(2026, 7, 20, 13, 26),
                        "duration_minutes": 12,
                        "sun2_bed_id": "644",
                    },
                    "alarm": {
                        "detected_at": datetime(2026, 7, 20, 13, 36),
                        "alarm_type": "overstay",
                        "notification_status": "sent",
                    },
                }
            ]
        }

        html = online_main.render_door_day_control(control)

        self.assertIn("Solrom 5", html)
        self.assertIn("13:12", html)
        self.assertIn("13:11–13:26", html)
        self.assertIn("Alarm 13:36 · Overtid", html)
        self.assertIn("varsel sendt", html)
        self.assertNotIn("20.07.2026", html)

    def test_mobile_door_periods_collapse_sensor_bounce(self) -> None:
        rows = [
            {"id": 1, "device_id": 479, "timestamp": datetime(2026, 7, 20, 10, 40), "state": True},
            {"id": 2, "device_id": 479, "timestamp": datetime(2026, 7, 20, 10, 42, 50), "state": False},
            {"id": 3, "device_id": 479, "timestamp": datetime(2026, 7, 20, 10, 42, 52), "state": True},
            {"id": 4, "device_id": 479, "timestamp": datetime(2026, 7, 20, 10, 42, 53), "state": False},
            {"id": 5, "device_id": 479, "timestamp": datetime(2026, 7, 20, 10, 59, 19), "state": True},
        ]

        periods = online_main.solroom_closed_periods(rows, datetime(2026, 7, 20, 11))

        self.assertEqual(len(periods), 1)
        self.assertEqual(periods[0]["closed_at"], datetime(2026, 7, 20, 10, 42, 50))
        self.assertEqual(periods[0]["opened_at"], datetime(2026, 7, 20, 10, 59, 19))

    def test_mobile_room_12_uses_physical_room_13_and_bed_681(self) -> None:
        config = online_main.SOLROOM_DOOR_BY_KEY["door_solrom_12"]

        self.assertEqual(online_main.solroom_room_id_from_config(config), "rom-13")
        self.assertEqual(config["sun2_bed_id"], "681")


if __name__ == "__main__":
    unittest.main()
