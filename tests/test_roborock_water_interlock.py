import asyncio

from roborock_logger.app import main as logger
from roborock_logger.app.water_interlock import (
    clear_water_state,
    schedule_timer_id,
    schedule_uses_water,
    timer_status_map,
    wash_schedule_rows,
)


def schedule(timer_id: str, water_box_mode: int, enabled: bool = True) -> dict:
    return {
        "id": f"cloud-{timer_id}",
        "enabled": enabled,
        "cron": "0 1 * * *",
        "param": {
            "params": [
                {
                    "name": timer_id,
                    "fan_power": 104,
                    "water_box_mode": water_box_mode,
                    "mop_mode": 303,
                }
            ]
        },
    }


def test_water_interlock_helpers_distinguish_wash_from_vacuum() -> None:
    vacuum = schedule("vacuum", 200)
    wash = schedule("wash", 203)

    assert schedule_timer_id(wash) == "wash"
    assert schedule_uses_water(vacuum) is False
    assert schedule_uses_water(wash) is True
    assert [row["timer_id"] for row in wash_schedule_rows([vacuum, wash])] == ["wash"]
    assert timer_status_map([["vacuum", "on"], ["wash", "off"]]) == {
        "vacuum": "on",
        "wash": "off",
    }
    assert clear_water_state({"clear_water_status": 0}) == "ok"
    assert clear_water_state({"clear_water_status": 1}) == "empty"
    assert clear_water_state({}) == "unknown"


def test_empty_dock_pauses_only_wash_schedules(monkeypatch) -> None:
    state = {
        "robots": {
            "robot-a": {
                "schedules": [schedule("vacuum", 200), schedule("wash", 203)],
            }
        },
        "water_interlocks": {},
    }
    requested = []

    async def read_statuses(_duid):
        return {"vacuum": "on", "wash": "on"}

    async def update_statuses(_duid, updates):
        requested.append(updates)
        return {
            "ok": True,
            "verified": {"vacuum": "on", "wash": "off"},
            "failed": {},
        }

    monkeypatch.setattr(logger, "read_server_timer_statuses", read_statuses)
    monkeypatch.setattr(logger, "update_server_timer_statuses", update_statuses)
    monkeypatch.setattr(logger, "append_control_log", lambda _entry: None)

    result = asyncio.run(
        logger.reconcile_water_interlock(
            "robot-a",
            "1.etg A",
            {"clear_water_status": 1},
            state,
        )
    )

    assert requested == [{"wash": "off"}]
    assert result["status"] == "blocked"
    assert result["paused_count"] == 1
    assert result["paused_schedules"][0]["timer_id"] == "wash"


def test_refilled_dock_restores_only_schedules_paused_by_interlock(monkeypatch) -> None:
    wash = schedule("wash", 203)
    state = {
        "robots": {"robot-a": {"schedules": [schedule("vacuum", 200), wash]}},
        "water_interlocks": {
            "robot-a": {
                "status": "blocked",
                "blocked_at": "2026-08-15T12:00:00+02:00",
                "paused_schedules": [{**wash_schedule_rows([wash])[0], "paused_at": "2026-08-15T12:00:00+02:00"}],
            }
        },
    }
    requested = []

    async def update_statuses(_duid, updates):
        requested.append(updates)
        return {"ok": True, "verified": {"wash": "on"}, "failed": {}}

    monkeypatch.setattr(logger, "update_server_timer_statuses", update_statuses)
    monkeypatch.setattr(logger, "append_control_log", lambda _entry: None)

    result = asyncio.run(
        logger.reconcile_water_interlock(
            "robot-a",
            "1.etg A",
            {"clear_water_status": 0},
            state,
        )
    )

    assert requested == [{"wash": "on"}]
    assert result["status"] == "ready"
    assert result["paused_count"] == 0
