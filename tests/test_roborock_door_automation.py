from datetime import date, datetime, timedelta
from pathlib import Path

from roborock_door_automation import (
    automation_counter_start,
    automation_decision,
    opening_window,
    unique_ints,
)


def test_opening_window_and_daily_counter_do_not_carry_previous_day():
    open_at, close_at = opening_window(date(2026, 8, 13), "07:00", "23:00")
    assert open_at == datetime(2026, 8, 13, 7, 0)
    assert close_at == datetime(2026, 8, 13, 23, 0)
    assert automation_counter_start(
        open_at,
        datetime(2026, 8, 12, 18, 0),
        datetime(2026, 8, 13, 9, 15),
    ) == datetime(2026, 8, 13, 9, 15)


def test_automation_requires_count_closed_door_and_minimum_interval():
    now = datetime(2026, 8, 13, 14, 0)
    base = {
        "now": now,
        "enabled": True,
        "open_at": datetime(2026, 8, 13, 7, 0),
        "close_at": datetime(2026, 8, 13, 23, 0),
        "opening_threshold": 10,
        "minimum_interval_minutes": 60,
        "validation_issues": [],
    }
    counting = automation_decision(
        **base,
        opening_count=9,
        last_started_at=now - timedelta(hours=2),
        door_is_open=False,
    )
    assert counting["key"] == "counting"

    waiting = automation_decision(
        **base,
        opening_count=10,
        last_started_at=now - timedelta(minutes=40),
        door_is_open=False,
    )
    assert waiting["key"] == "minimum_interval"
    assert waiting["pending"] is True
    assert waiting["remaining_interval_seconds"] == 20 * 60

    ready = automation_decision(
        **base,
        opening_count=10,
        last_started_at=now - timedelta(minutes=61),
        door_is_open=False,
    )
    assert ready["eligible"] is True

    first_run = automation_decision(
        **base,
        opening_count=10,
        last_started_at=None,
        door_is_open=False,
    )
    assert first_run["eligible"] is True


def test_reached_threshold_starts_when_minimum_interval_expires_without_new_opening():
    last_started_at = datetime(2026, 8, 13, 13, 20)
    common = {
        "enabled": True,
        "open_at": datetime(2026, 8, 13, 7, 0),
        "close_at": datetime(2026, 8, 13, 23, 0),
        "opening_count": 10,
        "opening_threshold": 10,
        "minimum_interval_minutes": 60,
        "last_started_at": last_started_at,
        "door_is_open": False,
        "validation_issues": [],
    }
    waiting = automation_decision(now=datetime(2026, 8, 13, 14, 0), **common)
    ready = automation_decision(now=datetime(2026, 8, 13, 14, 20), **common)

    assert waiting["key"] == "minimum_interval"
    assert waiting["pending"] is True
    assert ready["key"] == "ready"
    assert ready["eligible"] is True


def test_saving_door_automation_does_not_reset_the_counter():
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    update_handler = source.split("async def api_update_roborock_door_automation(", 1)[1].split(
        '@app.post("/api/renhold/robots/{duid}/door-automation/reset-counter")', 1
    )[0]

    assert "automation.counter_reset_at =" not in update_handler
    assert "Telleren er beholdt" in update_handler


def test_automation_never_starts_outside_opening_hours_or_with_bad_config():
    common = {
        "enabled": True,
        "open_at": datetime(2026, 8, 13, 7, 0),
        "close_at": datetime(2026, 8, 13, 23, 0),
        "opening_count": 12,
        "opening_threshold": 10,
        "minimum_interval_minutes": 60,
        "last_started_at": datetime(2026, 8, 13, 20, 0),
        "door_is_open": False,
    }
    outside = automation_decision(now=datetime(2026, 8, 13, 23, 5), validation_issues=[], **common)
    assert outside["key"] == "outside_hours"
    invalid = automation_decision(
        now=datetime(2026, 8, 13, 22, 0),
        validation_issues=["Velg minst én sone."],
        **common,
    )
    assert invalid["key"] == "configuration_error"


def test_unique_ints_preserves_order_and_removes_duplicates():
    assert unique_ints([2, "1", 2, 0, None, "bad"]) == [2, 1]
