from pathlib import Path
import asyncio
import importlib

import pytest
from fastapi import HTTPException

from roborock_logger.app import main as logger
from roborock_profiles import cleaning_profile_summary, validate_cleaning_profile


def test_control_active_state_only_matches_floor_work():
    assert logger.control_is_active({"state_name": "cleaning"}) is True
    assert logger.control_is_active({"state_name": "segment_cleaning"}) is True
    assert logger.control_is_active({"state_name": "washing_the_mop"}) is True
    assert logger.control_is_active({"state_name": "segment_clean_mop_mopping"}) is True
    assert logger.control_is_active({"state_name": "charging", "in_cleaning": 1}) is False
    assert logger.control_is_active({"state_name": "returning_home", "in_cleaning": 1}) is False


def test_segment_clean_params_supports_one_or_more_robot_segments():
    assert logger.segment_clean_params(18) == [{"segments": [18], "repeat": 1}]
    assert logger.segment_clean_params(18, 2) == [{"segments": [18], "repeat": 2}]
    assert logger.segment_clean_params([18, 25], 1) == [{"segments": [18, 25], "repeat": 1}]
    assert logger.segment_clean_params([18, 18, 25], 2) == [{"segments": [18, 25], "repeat": 2}]


def test_zone_control_request_requires_valid_zone_and_segment():
    request = logger.ControlRequest(
        action="clean_zone",
        request_id="request-123",
        confirmation="CONFIRM:robot:clean_zone",
        zone_number=1,
        segment_id=18,
        profile={
            "id": 1,
            "name": "Vanlig kombi",
            "cleaning_type": "vacuum_mop",
            "fan_power": 102,
            "water_box_mode": 202,
            "mop_mode": 300,
            "repeat": 1,
        },
    )
    assert request.zone_number == 1
    assert request.segment_id == 18
    assert request.profile and request.profile.cleaning_type == "vacuum_mop"


def test_zone_control_request_accepts_parallel_zone_and_segment_lists():
    request = logger.ControlRequest(
        action="clean_zone",
        request_id="request-multi-123",
        confirmation="CONFIRM:robot:clean_zone",
        zone_numbers=[1, 2],
        segment_ids=[25, 26],
        profile={
            "id": 1,
            "name": "Vanlig støvsuging",
            "cleaning_type": "vacuum",
            "fan_power": 102,
            "water_box_mode": 200,
            "mop_mode": 300,
            "repeat": 1,
        },
    )
    assert request.zone_numbers == [1, 2]
    assert request.segment_ids == [25, 26]


def test_profile_validation_keeps_cleaning_type_and_levels_consistent():
    values = validate_cleaning_profile(
        {
            "cleaning_type": "vacuum_mop",
            "fan_power": 104,
            "water_box_mode": 203,
            "mop_mode": 303,
            "repeat": 2,
        }
    )
    assert values["repeat"] == 2
    assert cleaning_profile_summary(values) == "Støvsug + vask · Maks · Dyp+ · Høy vann · 2 runder"

    with pytest.raises(ValueError, match="aktiv suging"):
        validate_cleaning_profile({**values, "cleaning_type": "vacuum", "fan_power": 105, "water_box_mode": 200})


def test_logger_profile_rejects_conflicting_cleaning_settings():
    profile = logger.CleaningProfileRequest(
        id=1,
        name="Feil kombi",
        cleaning_type="vacuum_mop",
        fan_power=105,
        water_box_mode=203,
        mop_mode=300,
        repeat=1,
    )
    with pytest.raises(HTTPException, match="motstridende"):
        logger.validated_profile_settings(profile)


def test_logger_applies_and_verifies_every_profile_setting(monkeypatch):
    importlib.import_module("roborock.roborock_typing")
    calls = []

    class Rpc:
        async def send_command(self, command, params=None):
            calls.append((command.value, params))
            return ["ok"]

    async def verified_state(*_args, **_kwargs):
        return {"fan_power": 104, "water_box_mode": 203, "mop_mode": 303}

    monkeypatch.setattr(logger, "wait_for_control_state", verified_state)
    profile = logger.CleaningProfileRequest(
        id=2,
        name="Intensiv kombi",
        cleaning_type="vacuum_mop",
        fan_power=104,
        water_box_mode=203,
        mop_mode=303,
        repeat=2,
    )
    result = asyncio.run(logger.apply_cleaning_profile(Rpc(), "roborock.vacuum.a75", profile))

    assert calls == [
        ("set_custom_mode", [104]),
        ("set_water_box_custom_mode", [203]),
        ("set_mop_mode", [303]),
    ]
    assert result["verified"]["mop_mode"] == 303


def test_mop_wash_settings_accept_only_supported_modes_and_intervals():
    assert logger.validated_mop_wash_settings(1, 10) == {
        "wash_mode": 1,
        "wash_interval_minutes": 10,
        "wash_interval_seconds": 600,
        "smart_wash": 0,
    }
    with pytest.raises(HTTPException, match="styrke"):
        logger.validated_mop_wash_settings(10, 10)
    with pytest.raises(HTTPException, match="intervall"):
        logger.validated_mop_wash_settings(1, 12)


def test_logger_applies_and_reads_back_mop_wash_settings(monkeypatch):
    importlib.import_module("roborock.roborock_typing")
    calls = []
    state = {"wash_mode": 1, "smart_wash": 0, "wash_interval": 600}

    class Rpc:
        async def send_command(self, command, params=None):
            calls.append((command.value, params))
            if command.value == "set_wash_towel_mode":
                state["wash_mode"] = params["wash_mode"]
                return ["ok"]
            if command.value == "set_smart_wash_params":
                state.update(params)
                return ["ok"]
            if command.value == "get_wash_towel_mode":
                return {"wash_mode": state["wash_mode"]}
            if command.value == "get_smart_wash_params":
                return {"smart_wash": state["smart_wash"], "wash_interval": state["wash_interval"]}
            raise AssertionError(command.value)

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(logger.asyncio, "sleep", no_sleep)
    result = asyncio.run(logger.apply_mop_wash_settings(Rpc(), 2, 15))

    assert calls == [
        ("set_wash_towel_mode", {"wash_mode": 2}),
        ("set_smart_wash_params", {"smart_wash": 0, "wash_interval": 900}),
        ("get_wash_towel_mode", None),
        ("get_smart_wash_params", None),
    ]
    assert result["settings"]["wash_mode_label"] == "Dyp"
    assert result["settings"]["wash_interval_minutes"] == 15
    assert result["probes"]["GET_SMART_WASH_PARAMS"]["wash_interval"] == 900


def test_control_start_rejects_active_error_and_low_battery():
    with pytest.raises(HTTPException, match="rengjør allerede"):
        logger.validate_control_start({"state_name": "cleaning", "battery": 90, "error_code": 0})
    with pytest.raises(HTTPException, match="aktiv feil"):
        logger.validate_control_start({"state_name": "idle", "battery": 90, "error_code": 12})
    with pytest.raises(HTTPException, match="for lavt"):
        logger.validate_control_start({"state_name": "idle", "battery": 20, "error_code": 0})
    logger.validate_control_start({"state_name": "charging", "battery": 80, "error_code": 0})


def test_core_control_route_is_master_protected_and_audited():
    import inspect
    import main
    route = inspect.getsource(main.api_cleaning_robot_control)
    assert "require_master(request)" in route
    assert "RoborockCleaningZoneMapping.robot_duid == duid" in route
    assert "RoborockCommandRun(" in route
    assert '"confirmation": f"CONFIRM:{duid}:{action}"' in route
    assert '"segment_id": segment_id' in route
    assert '"profile": {' in route
    assert '"set_mop_wash"' in route
    assert '"wash_interval_minutes": values.wash_interval_minutes' in route
    assert 'source="local-telemetry"' in route


def test_logger_control_route_requires_shared_token():
    source = (Path(__file__).resolve().parents[1] / "roborock_logger" / "app" / "main.py").read_text(
        encoding="utf-8"
    )
    route = source[source.index('@app.post("/api/control/{duid}")'):]
    assert "secrets.compare_digest" in route[:1000]
    assert "async with sync_lock" in route[:1200]
