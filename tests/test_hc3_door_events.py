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
    assert "alarm_events" in STORAGE_TABLES


def test_alarm_history_schema_and_backfill_are_present():
    migration = Path("migrations/versions/20260719_2200_add_alarm_events.sql").read_text(encoding="utf-8")
    backfill = Path("scripts/backfill_sunroom_alarm_history.py").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS alarm_events" in migration
    assert "notification_status" in migration
    assert "sunroom_alarm_event_key" in backfill
    assert "notification_status=\"unknown\"" in backfill


def test_hc3_door_poll_worker_is_configured():
    source = Path("main.py").read_text(encoding="utf-8")

    assert "HC3_DOOR_UNEXPECTED_CHECK_INTERVAL_SECONDS" in source
    assert "hc3_door_poll_worker" in source
    assert "run_hc3_door_unexpected_check_once" in source
    assert "run_hc3_door_poll_once" in source
    assert "HC3 POLL SYNC" in source


def test_manual_sun2_sync_is_serialized_with_scheduled_jobs():
    source = Path("sun2_session_scraper/app/main.py").read_text(encoding="utf-8")
    sync_today_source = source[source.index('@app.post("/sync-today")'):source.index('@app.post("/sync-beds")')]
    rate_limited_source = source[
        source.index("async def run_today_sync_rate_limited"):
        source.index("def scrape_product_sales_yesterday_sync")
    ]

    assert "run_today_sync_rate_limited" in sync_today_source
    assert "async with schedule_lock" in rate_limited_source
    assert "scrape_today_sync" in rate_limited_source


def test_hc3_door_lua_contains_expected_devices_and_endpoint():
    lua = Path("scripts/hc3_door_event_logger.lua").read_text(encoding="utf-8")

    expected_device_ids = (
        "459",
        "543",
        "465",
        "463",
        "469",
        "471",
        "473",
        "475",
        "477",
        "479",
        "539",
        "453",
        "447",
        "413",
        "541",
        "483",
        "535",
        "489",
        "487",
        "537",
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
        "543",
        "465",
        "463",
        "469",
        "471",
        "473",
        "475",
        "477",
        "479",
        "539",
        "453",
        "447",
        "413",
        "541",
        "483",
        "535",
        "489",
        "487",
        "537",
        "493",
        "495",
    ):
        assert f'"device_id": {device_id}' in script

    assert "door_solrom_02" not in script
    assert '"device_key": "door_solrom_03"' in script
    assert "OBSOLETE_DOOR_DEVICE_IDS = {491, 499}" in script
    assert "disable_obsolete_door_scenes" in script
    assert "HC3_DOOR_UPSERT_DEVICE_IDS" in script


class SunroomDoorTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")
        import main

        cls.main = main

    def test_solroom_3_uses_latest_hc3_door_sensor(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_solrom_03")

        self.assertEqual(config["device_id"], 543)
        self.assertEqual(config["hc3_name"], "148.0 Door Sensor")

    def test_operations_overview_uses_friendly_door_name(self):
        result = self.main.operations_recent_door_items({
            "doors": [{"deviceId": 541, "deviceKey": "door_inngang", "title": "Inngang"}],
            "changes": [{
                "deviceId": 541,
                "deviceKey": "door_inngang",
                "deviceName": "131.0 Door Sensor",
                "stateLabel": "Lukket",
                "ageLabel": "2 min siden",
                "state": "closed",
            }],
        })

        self.assertEqual(result[0]["label"], "Inngang")

    def test_operations_overview_uses_newest_local_robot_sample_for_freshness(self):
        now = datetime(2026, 8, 14, 14, 20)
        status = self.main.RoborockStatusSample(timestamp=now - timedelta(minutes=21))
        telemetry = self.main.RoborockTelemetrySample(timestamp=now - timedelta(minutes=45))

        source = self.main.latest_cleaning_robot_sample(status, telemetry)
        source_at = self.main.normalize_local_naive(source.timestamp)

        self.assertIs(source, status)
        self.assertEqual(source_at, datetime(2026, 8, 14, 13, 59))
        self.assertEqual(self.main.minutes_since(source_at, now), 21)

    def test_expected_exit_uses_payment_delay_sun_time_and_exit_grace(self):
        row = self.main.Sun2TanningSession(
            started_at=datetime(2026, 7, 11, 12, 0),
            ended_at=datetime(2026, 7, 11, 12, 12),
            duration_minutes=12,
        )

        self.assertEqual(self.main.sunroom_session_sun_start_at(row), datetime(2026, 7, 11, 12, 3))
        self.assertEqual(self.main.sunroom_session_end_at(row), datetime(2026, 7, 11, 12, 15))
        self.assertEqual(self.main.sunroom_expected_exit_at(row), datetime(2026, 7, 11, 12, 18))

    def test_door_change_rows_collapses_sensor_bounce_into_one_closed_period(self):
        def event(row_id, at, state):
            return self.main.DoorEvent(
                id=row_id,
                device_id=479,
                timestamp=at,
                action="OPEN" if state else "CLOSED",
                state=state,
            )

        rows = [
            event(1, datetime(2026, 7, 20, 10, 40, 0), True),
            event(2, datetime(2026, 7, 20, 10, 42, 50), False),
            event(3, datetime(2026, 7, 20, 10, 42, 52), True),
            event(4, datetime(2026, 7, 20, 10, 42, 53), False),
            event(5, datetime(2026, 7, 20, 10, 42, 53), True),
            event(6, datetime(2026, 7, 20, 10, 42, 53), False),
            event(7, datetime(2026, 7, 20, 10, 59, 19), True),
        ]

        changes = self.main.door_change_rows(rows)
        periods = self.main.door_closed_periods(changes, datetime(2026, 7, 20, 11, 0))

        self.assertEqual([(row.id, row.state) for row in changes], [(1, True), (2, False), (7, True)])
        self.assertEqual(len(periods), 1)
        self.assertEqual(periods[0]["closedAt"], datetime(2026, 7, 20, 10, 42, 50))
        self.assertEqual(periods[0]["openedAt"], datetime(2026, 7, 20, 10, 59, 19))

    def test_door_change_rows_keeps_real_changes_outside_debounce_window(self):
        rows = [
            self.main.DoorEvent(id=1, device_id=469, timestamp=datetime(2026, 7, 20, 9, 0, 0), action="CLOSED", state=False),
            self.main.DoorEvent(id=2, device_id=469, timestamp=datetime(2026, 7, 20, 9, 0, 6), action="OPEN", state=True),
        ]

        changes = self.main.door_change_rows(rows)

        self.assertEqual([(row.id, row.state) for row in changes], [(1, False), (2, True)])

    def test_latest_door_status_keeps_timestamp_after_short_open_close(self):
        rows_ascending = [
            self.main.DoorEvent(id=1, device_id=447, timestamp=datetime(2026, 7, 14, 11, 57, 56), action="CLOSED", state=False),
            self.main.DoorEvent(id=2, device_id=447, timestamp=datetime(2026, 7, 23, 9, 17, 2), action="OPEN", state=True),
            self.main.DoorEvent(id=3, device_id=447, timestamp=datetime(2026, 7, 23, 9, 17, 6), action="CLOSED", state=False),
        ]

        stabilized = self.main.door_change_rows(rows_ascending)
        latest = self.main.latest_door_event_by_device(list(reversed(rows_ascending)))

        self.assertEqual([(row.id, row.state) for row in stabilized], [(1, False), (2, True), (3, False)])
        self.assertEqual(latest[447].id, 3)
        self.assertEqual(latest[447].timestamp, datetime(2026, 7, 23, 9, 17, 6))

        periods = self.main.door_open_periods(stabilized, datetime(2026, 7, 23, 9, 18))
        self.assertEqual(len(periods), 1)
        self.assertEqual(periods[0]["openedEventId"], 2)
        self.assertEqual(periods[0]["closedEventId"], 3)
        self.assertEqual(periods[0]["durationSeconds"], 4)

    def test_door_status_uses_actual_change_time_after_same_state_poll(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_solrom_03")
        now = datetime(2026, 8, 13, 23, 30)
        changed_row = self.main.DoorEvent(
            id=10,
            device_id=543,
            timestamp=datetime(2026, 8, 10, 21, 48, 41),
            action="OPEN",
            state=True,
            battery_level=98,
        )
        latest_poll = self.main.DoorEvent(
            id=11,
            device_id=543,
            timestamp=datetime(2026, 8, 13, 23, 22, 38),
            action="OPEN",
            state=True,
            raw_value="true",
            battery_level=100,
        )

        payload = self.main.door_status_payload(config, latest_poll, now, changed_row)

        self.assertEqual(payload["state"], "open")
        self.assertEqual(payload["lastChangedAt"], "2026-08-10T21:48:41")
        self.assertEqual(payload["lastChangedEventId"], 10)
        self.assertEqual(payload["eventId"], 11)
        self.assertEqual(payload["batteryLevel"], 100)

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

    def test_energy_sample_window_preserves_end_boundary_rules(self):
        samples = [
            {"time": datetime(2026, 7, 11, 12, minute), "diff_w": minute}
            for minute in range(5)
        ]
        sample_times = [item["time"] for item in samples]

        exclusive = self.main.sunroom_energy_sample_window(
            samples,
            datetime(2026, 7, 11, 12, 1),
            datetime(2026, 7, 11, 12, 3),
            sample_times,
        )
        inclusive = self.main.sunroom_energy_sample_window(
            samples,
            datetime(2026, 7, 11, 12, 1),
            datetime(2026, 7, 11, 12, 3),
            sample_times,
            include_end=True,
        )

        self.assertEqual([item["diff_w"] for item in exclusive], [1, 2])
        self.assertEqual([item["diff_w"] for item in inclusive], [1, 2, 3])

    def test_closed_solroom_without_session_warns_before_alarm_threshold(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_solrom_04")
        now = datetime(2026, 7, 13, 12, 0)
        row = self.main.DoorEvent(
            device_id=config["device_id"],
            device_key=config["device_key"],
            timestamp=now - timedelta(minutes=10),
            action="CLOSED",
            state=False,
        )

        item = self.main.sunroom_status_item(config, row, {self.main.sunroom_room_id_for_config(config): []}, now)

        self.assertTrue(item["missingSession"])
        self.assertFalse(item["noSessionAlarmActive"])
        self.assertEqual(item["severity"], "warning")

    def test_closed_solroom_without_session_waits_during_initial_grace(self):
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

        self.assertFalse(item["missingSession"])
        self.assertEqual(item["severity"], "waiting")

    def test_closed_solroom_without_session_triggers_alarm_after_threshold(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_solrom_04")
        now = datetime(2026, 7, 13, 12, 0)
        row = self.main.DoorEvent(
            device_id=config["device_id"],
            device_key=config["device_key"],
            timestamp=now - timedelta(minutes=18),
            action="CLOSED",
            state=False,
        )

        item = self.main.sunroom_status_item(config, row, {self.main.sunroom_room_id_for_config(config): []}, now)

        self.assertTrue(item["missingSession"])
        self.assertTrue(item["noSessionAlarmActive"])
        self.assertEqual(item["severity"], "alert")
        self.assertEqual(item["status"], "Alarm")
        self.assertEqual(item["alarmReason"], "closed_without_session")
        self.assertEqual(self.main.sunroom_alarm_detected_at(item, now), now - timedelta(minutes=1))

    def test_old_finished_session_does_not_cover_a_new_closed_period(self):
        now = datetime(2026, 7, 13, 12, 0)
        row = self.main.Sun2TanningSession(
            started_at=datetime(2026, 7, 13, 11, 0),
            duration_minutes=12,
        )

        self.assertFalse(
            self.main.sunroom_session_matches_closed_period(row, datetime(2026, 7, 13, 11, 30), now)
        )

    def test_active_session_covers_a_door_reclose(self):
        now = datetime(2026, 7, 13, 12, 0)
        row = self.main.Sun2TanningSession(
            started_at=datetime(2026, 7, 13, 11, 20),
            duration_minutes=30,
        )

        self.assertTrue(
            self.main.sunroom_session_matches_closed_period(row, datetime(2026, 7, 13, 11, 30), now)
        )

    def test_payment_after_door_close_matches_within_control_window(self):
        now = datetime(2026, 7, 13, 11, 43)
        row = self.main.Sun2TanningSession(
            started_at=datetime(2026, 7, 13, 11, 42),
            duration_minutes=12,
        )

        self.assertTrue(
            self.main.sunroom_session_matches_closed_period(row, datetime(2026, 7, 13, 11, 30), now)
        )

    def test_no_session_alarm_waits_for_successful_forced_sync(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_solrom_04")
        now = datetime(2026, 7, 13, 12, 0)
        row = self.main.DoorEvent(
            device_id=config["device_id"],
            device_key=config["device_key"],
            timestamp=now - timedelta(minutes=18),
            action="CLOSED",
            state=False,
        )
        raw_item = self.main.sunroom_status_item(config, row, {self.main.sunroom_room_id_for_config(config): []}, now)
        key = self.main.sunroom_door_period_key(raw_item)
        self.main.sunroom_door_verifications.pop(key, None)

        waiting = self.main.apply_sunroom_alarm_verification([raw_item], now)[0]
        self.main.sunroom_door_verifications[key] = {
            "attemptedAt": now - timedelta(minutes=2),
            "ok": True,
            "error": "",
        }
        verified = self.main.apply_sunroom_alarm_verification([raw_item], now)[0]
        self.main.sunroom_door_verifications.pop(key, None)

        self.assertEqual(waiting["severity"], "warning")
        self.assertFalse(waiting["noSessionAlarmActive"])
        self.assertEqual(verified["severity"], "alert")
        self.assertTrue(verified["noSessionAlarmActive"])

    def test_door_sync_retries_every_five_minutes_and_stops_after_limit(self):
        now = datetime(2026, 7, 13, 12, 0)
        item = {
            "deviceKey": "door_solrom_04",
            "doorChangedAt": (now - timedelta(minutes=2)).isoformat(),
            "isOccupied": True,
            "occupiedDurationSeconds": 120,
            "session": None,
        }
        key = self.main.sunroom_door_period_key(item)
        self.main.sunroom_door_verifications.pop(key, None)

        self.assertTrue(self.main.sunroom_sync_candidate_is_due(item, now))
        self.main.sunroom_door_verifications[key] = {
            "attemptedAt": now - timedelta(minutes=4),
            "attemptCount": 1,
            "ok": True,
        }
        self.assertFalse(self.main.sunroom_sync_candidate_is_due(item, now))
        self.main.sunroom_door_verifications[key]["attemptedAt"] = now - timedelta(minutes=5)
        self.assertTrue(self.main.sunroom_sync_candidate_is_due(item, now))
        self.main.sunroom_door_verifications[key]["attemptCount"] = self.main.SUNROOM_DOOR_SYNC_MAX_ATTEMPTS
        self.assertFalse(self.main.sunroom_sync_candidate_is_due(item, now))
        self.main.sunroom_door_verifications.pop(key, None)

    def test_door_sync_checks_for_new_payment_when_matched_session_predates_reclose(self):
        now = datetime(2026, 7, 13, 12, 0)
        item = {
            "deviceKey": "door_solrom_04",
            "doorChangedAt": (now - timedelta(minutes=2)).isoformat(),
            "isOccupied": True,
            "occupiedDurationSeconds": 120,
            "session": {"startedAt": (now - timedelta(minutes=20)).isoformat()},
            "alarmReason": None,
        }

        self.assertTrue(self.main.sunroom_item_may_have_new_session(item))
        self.assertEqual(self.main.sunroom_force_sync_candidates([item]), [item])

    def test_persisted_alarm_keeps_web_process_status_consistent(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_solrom_04")
        now = datetime(2026, 7, 13, 12, 0)
        row = self.main.DoorEvent(
            device_id=config["device_id"],
            device_key=config["device_key"],
            timestamp=now - timedelta(minutes=18),
            action="CLOSED",
            state=False,
        )
        raw_item = self.main.sunroom_status_item(config, row, {self.main.sunroom_room_id_for_config(config): []}, now)
        event_key = self.main.sunroom_alarm_event_key(raw_item)

        verified = self.main.apply_sunroom_alarm_verification([raw_item], now, {event_key})[0]

        self.assertEqual(verified["severity"], "alert")
        self.assertTrue(verified["noSessionAlarmActive"])

    def test_failed_sun2_sync_delays_alarm_until_twenty_minutes(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_solrom_04")
        now = datetime(2026, 7, 13, 12, 0)

        def verified_item(minutes_closed):
            row = self.main.DoorEvent(
                device_id=config["device_id"],
                device_key=config["device_key"],
                timestamp=now - timedelta(minutes=minutes_closed),
                action="CLOSED",
                state=False,
            )
            item = self.main.sunroom_status_item(config, row, {self.main.sunroom_room_id_for_config(config): []}, now)
            key = self.main.sunroom_door_period_key(item)
            self.main.sunroom_door_verifications[key] = {
                "attemptedAt": now - timedelta(minutes=1),
                "ok": False,
                "error": "testfeil",
            }
            result = self.main.apply_sunroom_alarm_verification([item], now)[0]
            self.main.sunroom_door_verifications.pop(key, None)
            return result

        before = verified_item(19)
        after = verified_item(21)

        self.assertEqual(before["severity"], "warning")
        self.assertEqual(after["severity"], "alert")
        self.assertTrue(after["sun2VerificationFailed"])
        self.assertEqual(after["alarmThresholdMinutes"], self.main.SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES)

    def test_closed_solroom_after_session_triggers_overstay_alarm(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_solrom_04")
        room_id = self.main.sunroom_room_id_for_config(config)
        bed_id = self.main.sunroom_bed_id_for_config(config)
        now = datetime(2026, 7, 13, 12, 0)
        row = self.main.DoorEvent(
            device_id=config["device_id"],
            device_key=config["device_key"],
            timestamp=datetime(2026, 7, 13, 11, 25),
            action="CLOSED",
            state=False,
        )
        tanning = self.main.Sun2TanningSession(
            id=123,
            source_session_id="stable-overstay-test",
            room_id=room_id,
            sun2_bed_id=bed_id,
            started_at=datetime(2026, 7, 13, 11, 30),
            duration_minutes=12,
        )

        item = self.main.sunroom_status_item(config, row, {room_id: [tanning]}, now)

        self.assertEqual(item["severity"], "alert")
        self.assertEqual(item["alarmReason"], "overstay")
        self.assertEqual(item["alarmTitle"], "Overtid etter solslutt")
        self.assertEqual(
            self.main.sunroom_alarm_detected_at(item, now),
            self.main.sunroom_session_end_at(tanning) + timedelta(minutes=self.main.SUNROOM_DOOR_ALERT_AFTER_END_MINUTES),
        )

    def test_old_session_overstay_waits_for_sync_after_new_session_window(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_solrom_04")
        room_id = self.main.sunroom_room_id_for_config(config)
        now = datetime(2026, 7, 13, 12, 0)
        door_closed_at = now - timedelta(minutes=20)
        door = self.main.DoorEvent(
            device_id=config["device_id"],
            device_key=config["device_key"],
            timestamp=door_closed_at,
            action="CLOSED",
            state=False,
        )
        old_session = self.main.Sun2TanningSession(
            id=123,
            source_session_id="old-session",
            room_id=room_id,
            sun2_bed_id=self.main.sunroom_bed_id_for_config(config),
            started_at=now - timedelta(minutes=27),
            duration_minutes=12,
        )
        raw_item = self.main.sunroom_status_item(config, door, {room_id: [old_session]}, now)
        key = self.main.sunroom_door_period_key(raw_item)
        self.main.sunroom_door_verifications[key] = {
            "attemptedAt": door_closed_at + timedelta(minutes=6),
            "attemptCount": 2,
            "ok": True,
            "reason": "new_session_check",
        }

        waiting = self.main.apply_sunroom_alarm_verification([raw_item], now)[0]
        self.main.sunroom_door_verifications[key]["attemptedAt"] = door_closed_at + timedelta(minutes=11)
        verified = self.main.apply_sunroom_alarm_verification([raw_item], now)[0]
        self.main.sunroom_door_verifications.pop(key, None)

        self.assertEqual(raw_item["alarmReason"], "overstay")
        self.assertEqual(waiting["status"], "Kontrollerer ny time")
        self.assertTrue(waiting["newSessionCheckActive"])
        self.assertIsNone(waiting["alarmReason"])
        self.assertEqual(verified["severity"], "alert")
        self.assertFalse(verified["newSessionCheckActive"])

    def test_new_session_on_same_room_replaces_old_session_before_alarm(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_solrom_04")
        room_id = self.main.sunroom_room_id_for_config(config)
        now = datetime(2026, 7, 13, 12, 0)
        door = self.main.DoorEvent(
            device_id=config["device_id"],
            device_key=config["device_key"],
            timestamp=now - timedelta(minutes=12),
            action="CLOSED",
            state=False,
        )
        old_session = self.main.Sun2TanningSession(
            id=123,
            source_session_id="old-session",
            room_id=room_id,
            started_at=now - timedelta(minutes=33),
            duration_minutes=12,
        )
        new_session = self.main.Sun2TanningSession(
            id=124,
            source_session_id="new-session",
            room_id=room_id,
            started_at=now - timedelta(minutes=10),
            duration_minutes=30,
        )

        item = self.main.sunroom_status_item(config, door, {room_id: [new_session, old_session]}, now)

        self.assertEqual(item["session"]["sourceSessionId"], "new-session")
        self.assertEqual(item["severity"], "active")
        self.assertIsNone(item["alarmReason"])

    def test_display_room_12_uses_physical_room_13_and_bed_681(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_solrom_12")

        self.assertEqual(config["device_id"], 539)
        self.assertEqual(self.main.sunroom_room_id_for_config(config), "rom-13")
        self.assertEqual(self.main.sunroom_bed_id_for_config(config), "681")

    def test_new_waste_room_sensor_is_an_other_door(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_soppelbod")

        self.assertEqual(config["device_id"], 537)
        self.assertEqual(config["title"], "Søppelbod")
        self.assertEqual(config["group_key"], "andre")
        self.assertEqual(config["normal_state"], "closed")

    def test_replacement_entrance_sensor_preserves_door_key(self):
        config = next(item for item in self.main.DOOR_SENSOR_CONFIG if item.get("device_key") == "door_inngang")

        self.assertEqual(config["device_id"], 541)
        self.assertEqual(config["title"], "Inngang")
        self.assertEqual(config["group_key"], "andre")
        self.assertEqual(config["normal_state"], "closed")

    def test_bed_id_is_canonical_when_session_room_id_is_stale(self):
        row = self.main.Sun2TanningSession(room_id="rom-12", sun2_bed_id="681")

        self.assertEqual(self.main.sunroom_canonical_room_id(row), "rom-13")

    def test_alert_key_uses_stable_source_session_id(self):
        base = {
            "deviceKey": "door_solrom_12",
            "alarmReason": None,
            "expectedExitAt": "2026-07-19T21:29:00",
            "severity": "alert",
        }
        first = {**base, "session": {"id": 101, "sourceSessionId": "sun2-681-20260719-2058"}}
        second = {**base, "session": {"id": 202, "sourceSessionId": "sun2-681-20260719-2058"}}

        self.assertEqual(self.main.sunroom_alert_key(first), self.main.sunroom_alert_key(second))

    def test_read_endpoint_does_not_publish_alarm(self):
        source = Path("main.py").read_text(encoding="utf-8")
        endpoint = source.split('async def api_hc3_doors_sunroom_sessions():', 1)[1].split("\n\n", 1)[0]

        self.assertIn("notify=False", endpoint)
        self.assertNotIn("notify=True", endpoint)
