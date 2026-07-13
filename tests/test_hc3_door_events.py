import ast
import os
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from import_jobs import IMPORT_JOB_DEFINITIONS
from observability import STORAGE_TABLES


def test_door_event_api_route_is_registered():
    tree = ast.parse(Path("main.py").read_text(encoding="utf-8"))
    routes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.args
                    and isinstance(decorator.args[0], ast.Constant)
                ):
                    routes.append(decorator.args[0].value)

    assert "/api/hc3/door-events" in routes
    assert "/api/hc3/door-events/json" in routes
    assert "/api/hc3/doors/status" in routes
    assert "/api/hc3/doors/poll-sync" in routes
    assert "/api/hc3/doors/alarm" in routes


def test_door_event_datakilde_and_storage_are_registered():
    definition = IMPORT_JOB_DEFINITIONS["hc3_door_events"]
    poll_definition = IMPORT_JOB_DEFINITIONS["hc3_door_poll_sync"]

    assert definition["title"] == "Dørhendelser fra HC3"
    assert definition["source"] == "HC3"
    assert poll_definition["title"] == "HC3 dørstatus ved avvik"
    assert poll_definition["source"] == "Fibaro10 / HC3 API"
    assert poll_definition["expected_interval_minutes"] == 2
    assert "door_events" in STORAGE_TABLES


def test_hc3_door_poll_worker_is_configured():
    source = Path("main.py").read_text(encoding="utf-8")

    assert "HC3_DOOR_UNEXPECTED_CHECK_INTERVAL_SECONDS" in source
    assert "hc3_door_poll_worker" in source
    assert "run_hc3_door_unexpected_check_once" in source
    assert "run_hc3_door_poll_once" in source
    assert "HC3 POLL SYNC" in source


def test_hc3_door_lua_contains_expected_devices_and_endpoint():
    lua = Path("scripts/hc3_door_event_logger.lua").read_text(encoding="utf-8")

    expected_device_ids = (
        "459",
        "465",
        "463",
        "469",
        "471",
        "473",
        "475",
        "477",
        "479",
        "491",
        "453",
        "447",
        "413",
        "499",
        "483",
        "489",
        "487",
        "493",
        "495",
    )

    for device_id in expected_device_ids:
        assert f"{device_id} value" in lua
        assert f"[{device_id}]" in lua

    assert "/api/hc3/door-events" in lua


def test_hc3_single_door_scene_script_contains_configured_devices():
    script = Path("scripts/upsert_hc3_single_door_logger_scenes.py").read_text(encoding="utf-8")

    for device_id in (
        "459",
        "465",
        "463",
        "469",
        "471",
        "473",
        "475",
        "477",
        "479",
        "491",
        "453",
        "447",
        "413",
        "499",
        "483",
        "489",
        "487",
        "493",
        "495",
    ):
        assert f'"device_id": {device_id}' in script

    assert "door_solrom_02" not in script
    assert "door_solrom_03" not in script


class SunroomDoorTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")
        import main

        cls.main = main

    def test_expected_exit_uses_payment_delay_sun_time_and_exit_grace(self):
        row = self.main.Sun2TanningSession(
            started_at=datetime(2026, 7, 11, 12, 0),
            ended_at=datetime(2026, 7, 11, 12, 12),
            duration_minutes=12,
        )

        self.assertEqual(self.main.sunroom_session_sun_start_at(row), datetime(2026, 7, 11, 12, 3))
        self.assertEqual(self.main.sunroom_session_end_at(row), datetime(2026, 7, 11, 12, 15))
        self.assertEqual(self.main.sunroom_expected_exit_at(row), datetime(2026, 7, 11, 12, 18))

    def test_energy_evidence_confirms_expected_three_minute_start(self):
        row = self.main.Sun2TanningSession(
            id=1,
            room_id="rom-04",
            started_at=datetime(2026, 7, 11, 12, 0),
            duration_minutes=12,
        )
        samples = [
            {"time": datetime(2026, 7, 11, 11, 55), "diff_w": 800},
            {"time": datetime(2026, 7, 11, 11, 58), "diff_w": 850},
            {"time": datetime(2026, 7, 11, 12, 3), "diff_w": 7200},
            {"time": datetime(2026, 7, 11, 12, 6), "diff_w": 7350},
            {"time": datetime(2026, 7, 11, 12, 9), "diff_w": 7300},
        ]

        evidence = self.main.sunroom_session_energy_evidence(row, samples, [row])

        self.assertEqual(evidence["quality"], "clean")
        self.assertEqual(evidence["status"], "confirmed")
        self.assertEqual(evidence["startDelaySeconds"], 180)

    def test_closed_solroom_without_session_warns_before_alarm_threshold(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_solrom_04")
        now = datetime(2026, 7, 13, 12, 0)
        row = self.main.DoorEvent(
            device_id=config["device_id"],
            device_key=config["device_key"],
            timestamp=now - timedelta(minutes=6),
            action="CLOSED",
            state=False,
        )

        item = self.main.sunroom_status_item(config, row, {self.main.sunroom_room_id_for_config(config): []}, now)

        self.assertTrue(item["missingSession"])
        self.assertFalse(item["noSessionAlarmActive"])
        self.assertEqual(item["severity"], "warning")

    def test_closed_solroom_without_session_triggers_alarm_after_threshold(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_solrom_04")
        now = datetime(2026, 7, 13, 12, 0)
        row = self.main.DoorEvent(
            device_id=config["device_id"],
            device_key=config["device_key"],
            timestamp=now - timedelta(minutes=9),
            action="CLOSED",
            state=False,
        )

        item = self.main.sunroom_status_item(config, row, {self.main.sunroom_room_id_for_config(config): []}, now)

        self.assertTrue(item["missingSession"])
        self.assertTrue(item["noSessionAlarmActive"])
        self.assertEqual(item["severity"], "alert")
        self.assertEqual(item["status"], "Alarm")
