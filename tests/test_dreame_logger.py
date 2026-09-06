import asyncio
import importlib.util
import sys
from datetime import datetime, timedelta
from enum import IntEnum
from pathlib import Path
from types import SimpleNamespace

import pytest

from dreame_logger.app import main as dreame_main
from dreame_logger.app.normalization import normalize_device_snapshot, normalize_history, normalize_schedule
from dreame_logger.app.water_interlock import clear_water_state, rewrite_schedule_states, schedule_state_map
from dreame_logger.app.telemetry_outbox import TelemetryOutbox
from dreame_logger.app.upstream import DreameCredentials, DreameUpstream
from roborock_domain import roborock_telemetry_changes
from roborock_refills import build_refill_log
from roborock_reports import resource_problem


class Value(IntEnum):
    UNKNOWN = 0
    READY = 1


class FakeStatus:
    state = Value.READY
    state_name = "Klar"
    error = Value.UNKNOWN
    charging_status = Value.READY
    suction_level = Value.READY
    water_volume = Value.READY
    cleaning_mode = Value.READY
    clean_water_tank_status = Value.READY
    clean_water_tank_status_name = "OK"
    dirty_water_tank_status = Value.READY
    dirty_water_tank_status_name = "OK"
    dust_bag_status = Value.READY
    dust_bag_status_name = "OK"
    detergent_status = Value.READY
    detergent_status_name = "OK"
    low_water_warning = Value.UNKNOWN
    water_tank = Value.READY
    started = False
    returning = False
    battery_level = 87
    cleaning_time = 25
    cleaned_area = 42.5
    docked = True
    charging = True
    has_error = False
    washing_available = True
    drying = False
    low_water = False
    main_brush_life = 92
    side_brush_life = 83
    filter_life = 76
    sensor_dirty_life = 71
    mop_life = 68
    detergent_life = 55
    serial_number = "AQUA-SERIAL"
    schedule = [{"id": "night", "time": "00:30", "repeats": "0101010", "enabled": True}]
    cleaning_history = {
        "latest": {
            "timestamp": 1786491000,
            "cleaning_time": 25,
            "cleaned_area": 42.5,
            "completed": True,
        }
    }


class FakeDevice:
    available = True
    status = FakeStatus()
    data = {"BATTERY_LEVEL": 87}


def test_dreame_snapshot_uses_shared_contract_and_provider_namespace():
    row = normalize_device_snapshot(
        FakeDevice(),
        {"did": "12345", "name": "Aqua10", "model": "dreame.vacuum.test"},
        "Europe/Oslo",
    )

    assert row["provider"] == "dreame"
    assert row["external_id"] == "12345"
    assert row["duid"] == "dreame:12345"
    assert row["name"] == "Aqua10"
    assert row["status"]["battery"] == 87
    assert row["telemetry"]["clear_water_status_name"] == "OK"
    assert row["telemetry"]["water_shortage_status"] == 0
    assert row["telemetry"]["water_box_status"] == 1
    assert row["telemetry"]["clean_fluid_status_name"] == "OK"
    assert row["consumables"]["main_brush_percent"] == 92
    assert row["schedules"][0]["id"] == "night"
    assert row["schedules"][0]["cron"] == "30 0 * * 1,3,5"
    assert row["clean_jobs"][0]["duration_minutes"] == 25


def test_dreame_history_is_utc_naive_for_fibaro10_localization():
    rows = normalize_history(
        "12345",
        {"one": {"timestamp": 1786491000, "cleaning_time": 30, "completed": True}},
        "Europe/Oslo",
    )

    assert datetime.fromisoformat(rows[0]["begin_at"]).tzinfo is None
    assert datetime.fromisoformat(rows[0]["end_at"]) - datetime.fromisoformat(rows[0]["begin_at"]) == timedelta(minutes=30)


def test_dreame_history_id_is_stable_when_response_order_changes():
    first = normalize_history(
        "12345",
        {
            "older": {"timestamp": 1786491000, "cleaning_time": 30},
            "newer": {"timestamp": 1786577400, "cleaning_time": 25},
        },
        "Europe/Oslo",
    )
    reordered = normalize_history(
        "12345",
        {
            "newer": {"timestamp": 1786577400, "cleaning_time": 25},
            "older": {"timestamp": 1786491000, "cleaning_time": 30},
        },
        "Europe/Oslo",
    )

    assert {row["id"] for row in first} == {row["id"] for row in reordered}


def test_dreame_ok_water_name_is_not_interpreted_as_roborock_error_code():
    sample = {
        "water_shortage_status": 0,
        "clear_water_status": 203,
        "clear_water_status_name": "OK",
    }

    assert resource_problem(sample, "dreame") is False


def test_dreame_snapshot_preserves_aqua10_water_and_detergent_states():
    class AquaStatus(FakeStatus):
        clean_water_tank_status = 2
        clean_water_tank_status_name = "low_water"
        dirty_water_tank_status = 0
        dirty_water_tank_status_name = "installed"
        low_water_warning = 2
        water_tank = 1
        detergent_status = 2
        detergent_status_name = "low_detergent"
        water_volume = 2

    class AquaDevice(FakeDevice):
        status = AquaStatus()

    row = normalize_device_snapshot(
        AquaDevice(),
        {"did": "aqua10", "name": "Aqua10", "model": "dreame.vacuum.r9535h"},
        "Europe/Oslo",
    )

    assert row["telemetry"]["clear_water_status_name"] == "low_water"
    assert row["telemetry"]["dirty_water_status_name"] == "installed"
    assert row["telemetry"]["water_shortage_status"] == 2
    assert row["telemetry"]["water_box_status"] == 1
    assert row["telemetry"]["clean_fluid_status_name"] == "low_detergent"
    assert row["telemetry"]["water_box_mode"] == 2


def test_dreame_job_quality_only_fails_for_blocking_water_warnings():
    low = {
        "water_shortage_status": 5,
        "clear_water_status": 2,
        "clear_water_status_name": "low_water",
    }
    empty = {**low, "water_shortage_status": 2}

    assert resource_problem(low, "dreame") is False
    assert resource_problem(empty, "dreame") is True


def test_dreame_schedule_keeps_standard_cron_unchanged():
    row = normalize_schedule({"id": 1, "cron": "30 3 * * 1-5", "enabled": True}, 0)

    assert row is not None
    assert row["cron"] == "30 3 * * 1-5"


def test_dreame_schedule_without_weekdays_is_treated_as_daily():
    row = normalize_schedule({"id": 1, "time": "03:30", "enabled": True}, 0)

    assert row is not None
    assert row["cron"] == "30 3 * * *"


def test_dreame_invalid_schedule_is_disabled_and_malformed_time_is_preserved():
    row = normalize_schedule({"id": 1, "time": "25:75", "enabled": True, "invalid": True}, 0)

    assert row is not None
    assert row["cron"] == "25:75"
    assert row["enabled"] is False


def test_dreame_schedule_state_rewrite_preserves_complete_plan_definition():
    raw = "1-1-03:05-0101010-1-11-0-0-a,b;2-2-03:05-0010101-1-11-0-0-c,d"

    paused, before, changed = rewrite_schedule_states(raw, {"1": "0", "2": "0"})

    assert before == {"1": "1", "2": "2"}
    assert changed == {"1": "0", "2": "0"}
    assert paused == "1-0-03:05-0101010-1-11-0-0-a,b;2-0-03:05-0010101-1-11-0-0-c,d"
    assert schedule_state_map(paused) == {"1": "0", "2": "0"}


def test_dreame_water_state_blocks_low_or_missing_tank_but_requires_explicit_ok_to_restore():
    assert clear_water_state({"clear_water_status": 0, "clear_water_status_name": "OK"}) == "ok"
    assert clear_water_state({"clear_water_status": 2, "clear_water_status_name": "low_water"}) == "empty"
    assert clear_water_state({"clear_water_status": 1, "clear_water_status_name": "missing"}) == "empty"
    assert clear_water_state({}) == "unknown"


def test_aqua10_low_water_pauses_active_schedules_and_refill_restores_them(monkeypatch):
    state = {"water_interlocks": {}}
    snapshot = {
        "external_id": "aqua10",
        "telemetry": {"clear_water_status": 2, "clear_water_status_name": "low_water"},
        "schedules": [
            {"id": "1", "cron": "5 3 * * 1,3,5", "enabled": True},
            {"id": "2", "cron": "5 3 * * 2,4,6", "enabled": True},
        ],
    }

    class FakeUpstream:
        def __init__(self):
            self.calls = []

        def set_schedule_states(self, external_id, requested):
            self.calls.append((external_id, requested))
            if set(requested.values()) == {"0"}:
                return {
                    "ok": True,
                    "before": {"1": "1", "2": "2"},
                    "verified": {"1": "0", "2": "0"},
                    "failed": {},
                }
            return {
                "ok": True,
                "before": {"1": "0", "2": "0"},
                "verified": requested,
                "failed": {},
            }

    fake = FakeUpstream()
    monkeypatch.setattr(dreame_main, "get_upstream", lambda: fake)

    blocked = asyncio.run(dreame_main.reconcile_water_interlock(snapshot, state))

    assert fake.calls == [("aqua10", {"1": "0", "2": "0"})]
    assert blocked["status"] == "blocked"
    assert blocked["paused_count"] == 2
    assert {row["previous_state"] for row in blocked["paused_schedules"]} == {"1", "2"}
    assert all(schedule["enabled"] is False for schedule in snapshot["schedules"])

    snapshot["telemetry"] = {"clear_water_status": 0, "clear_water_status_name": "OK"}
    restored = asyncio.run(dreame_main.reconcile_water_interlock(snapshot, state))

    assert fake.calls[-1] == ("aqua10", {"1": "1", "2": "2"})
    assert restored["status"] == "ready"
    assert restored["paused_count"] == 0
    assert all(schedule["enabled"] is True for schedule in snapshot["schedules"])


def test_aqua10_does_not_recreate_schedule_deleted_while_water_blocked(monkeypatch):
    state = {
        "water_interlocks": {
            "aqua10": {
                "status": "blocked",
                "blocked_at": "2026-09-01T10:00:00+02:00",
                "paused_schedules": [
                    {"schedule_id": "deleted", "cron": "5 3 * * *", "previous_state": "1", "paused_at": "2026-09-01T10:00:00+02:00"}
                ],
            }
        }
    }
    snapshot = {
        "external_id": "aqua10",
        "telemetry": {"clear_water_status": 0, "clear_water_status_name": "OK"},
        "schedules": [],
    }

    class UnexpectedUpstream:
        def set_schedule_states(self, *_args, **_kwargs):
            raise AssertionError("En slettet plan skal ikke gjenopprettes")

    monkeypatch.setattr(dreame_main, "get_upstream", lambda: UnexpectedUpstream())

    restored = asyncio.run(dreame_main.reconcile_water_interlock(snapshot, state))

    assert restored["status"] == "ready"
    assert restored["paused_count"] == 0


def test_aqua10_captures_refill_between_periodic_samples(monkeypatch, tmp_path):
    properties = SimpleNamespace(**{name: name for name in (
        "CLEAN_WATER_TANK_STATUS", "DIRTY_WATER_TANK_STATUS", "LOW_WATER_WARNING", "WATER_TANK",
    )})
    monkeypatch.setitem(sys.modules, "dreame.types", SimpleNamespace(DreameVacuumProperty=properties))
    outbox = TelemetryOutbox(tmp_path / "outbox")
    monkeypatch.setattr(dreame_main, "telemetry_outbox", outbox)
    monkeypatch.setattr(dreame_main, "load_state", lambda: {"water_interlocks": {}})
    adapter = DreameUpstream(DreameCredentials("test", "test"), "Europe/Oslo", dreame_main.record_telemetry)
    device = FakeDevice()
    device.status = FakeStatus()
    device.status.clean_water_tank_status = 0
    device.status.clean_water_tank_status_name = "installed"
    device._ready = True
    listeners = {}
    device.listen = lambda callback, prop: listeners.update({prop: callback})
    descriptor = {"did": "aqua", "name": "Aqua10"}
    adapter._listen_for_water_changes(device, descriptor)
    adapter._snapshot(device, descriptor, "periodic")

    device.status.clean_water_tank_status = 1
    device.status.clean_water_tank_status_name = "not_installed"
    listeners["CLEAN_WATER_TANK_STATUS"](0)
    device.status.clean_water_tank_status = 0
    device.status.clean_water_tank_status_name = "installed"
    listeners["CLEAN_WATER_TANK_STATUS"](1)
    adapter._snapshot(device, descriptor, "periodic")

    delivered = []
    outbox.flush(delivered.append)
    samples = [batch["robots"][0]["telemetry"] for batch in delivered]
    assert [sample["clear_water_status"] for sample in samples] == [0, 1, 0, 0]
    assert [sample["collection"]["reason"] for sample in samples] == [
        "periodic", "property:CLEAN_WATER_TANK_STATUS", "property:CLEAN_WATER_TANK_STATUS", "periodic",
    ]
    assert all(datetime.fromisoformat(batch["timestamp"]).tzinfo is not None for batch in delivered)
    events = []
    for previous, current, batch in zip(samples, samples[1:], delivered[1:]):
        events.extend({**change, "robot_duid": "dreame:aqua", "timestamp": datetime.fromisoformat(batch["timestamp"])}
                      for change in roborock_telemetry_changes(previous, current, "dreame"))
    today = datetime.fromisoformat(delivered[0]["timestamp"]).date()
    report = build_refill_log(today - timedelta(days=today.weekday()),
                              [{"duid": "dreame:aqua", "name": "Aqua10", "provider": "dreame"}], events)
    assert len(report["cycles"]) == 1
    assert report["cycles"][0]["tankRemovedAt"]
    assert report["cycles"][0]["status"] == "completed"


def test_dreame_outbox_retains_order_after_failure_and_restart(tmp_path):
    outbox = TelemetryOutbox(tmp_path)
    for number in range(3):
        outbox.append({"number": number})
    delivered = []

    def flaky_send(payload):
        if payload["number"] == 1:
            raise OSError("offline")
        delivered.append(payload["number"])

    with pytest.raises(OSError, match="offline"):
        outbox.flush(flaky_send)
    assert delivered == [0]
    restored = TelemetryOutbox(tmp_path)
    assert restored.count() == 2
    restored.flush(lambda payload: delivered.append(payload["number"]))
    assert delivered == [0, 1, 2]
    assert restored.count() == 0


def test_dreame_outbox_snapshots_payload_and_ignores_unfinished_writes(tmp_path):
    outbox = TelemetryOutbox(tmp_path)
    payload = {"water": {"state": 1}}
    outbox.append(payload)
    payload["water"]["state"] = 0
    (tmp_path / "unfinished.tmp").write_text("partial", encoding="utf-8")
    delivered = []
    outbox.flush(delivered.append)
    assert delivered == [{"water": {"state": 1}}]


def test_dreame_outbox_producers_are_not_blocked_by_delivery(tmp_path):
    outbox = TelemetryOutbox(tmp_path)
    outbox.append({"water": 1})

    def send(_payload):
        outbox.append({"water": 0})

    assert outbox.flush(send) == 1
    delivered = []
    outbox.flush(delivered.append)
    assert delivered == [{"water": 0}]


def test_dreame_recovery_uses_evidence_time_and_only_clean_water():
    script = Path(__file__).resolve().parents[1] / "scripts" / "recover-dreame-refill-events.py"
    spec = importlib.util.spec_from_file_location("dreame_refill_recovery", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = list(module.parse_changes(
        "2026-09-06T14:14:17.835539093Z INFO:dreame.device:Property CLEAN_WATER_TANK_STATUS Changed: 0 -> 1\n"
        "2026-09-06T14:16:34.838913846Z INFO:dreame.device:Property CLEAN_WATER_TANK_STATUS Changed: 1 -> 0\n"
        "2026-09-06T14:16:35.835447099Z INFO:dreame.device:Property DIRTY_WATER_TANK_STATUS Changed: 0 -> 1\n"
    ))
    assert len(rows) == 2
    assert rows[0][0] == datetime(2026, 9, 6, 16, 14, 17, 835539)
    assert rows[1][0] == datetime(2026, 9, 6, 16, 16, 34, 838913)
    assert rows[0][1]["current_label"] == "Ikke montert"
    assert rows[1][1]["current_label"] == "OK"
