from pathlib import Path

import pytest
from fastapi import HTTPException

from roborock_logger.app import main as logger


def test_control_active_state_only_matches_floor_work():
    assert logger.control_is_active({"state_name": "cleaning"}) is True
    assert logger.control_is_active({"state_name": "segment_cleaning"}) is True
    assert logger.control_is_active({"state_name": "charging", "in_cleaning": 1}) is False
    assert logger.control_is_active({"state_name": "returning_home", "in_cleaning": 1}) is False


def test_control_start_rejects_active_error_and_low_battery():
    with pytest.raises(HTTPException, match="rengjør allerede"):
        logger.validate_control_start({"state_name": "cleaning", "battery": 90, "error_code": 0})
    with pytest.raises(HTTPException, match="aktiv feil"):
        logger.validate_control_start({"state_name": "idle", "battery": 90, "error_code": 12})
    with pytest.raises(HTTPException, match="for lavt"):
        logger.validate_control_start({"state_name": "idle", "battery": 20, "error_code": 0})
    logger.validate_control_start({"state_name": "charging", "battery": 80, "error_code": 0})


def test_core_control_route_is_master_protected_and_audited():
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    route = source[source.index('@app.post("/api/renhold/robots/{duid}/control")'):]
    assert "require_master(request)" in route[:1200]
    assert "RoborockCommandRun(" in route[:2500]
    assert '"confirmation": f"CONFIRM:{duid}:{action}"' in route[:4000]


def test_logger_control_route_requires_shared_token():
    source = (Path(__file__).resolve().parents[1] / "roborock_logger" / "app" / "main.py").read_text(
        encoding="utf-8"
    )
    route = source[source.index('@app.post("/api/control/{duid}")'):]
    assert "secrets.compare_digest" in route[:1000]
    assert "async with sync_lock" in route[:1200]
