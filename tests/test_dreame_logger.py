from datetime import datetime, timedelta
from enum import IntEnum

from dreame_logger.app.normalization import normalize_device_snapshot, normalize_history, normalize_schedule
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
