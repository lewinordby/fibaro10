from datetime import date, datetime, timedelta

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


def test_automation_requires_count_closed_door_and_quiet_period():
    now = datetime(2026, 8, 13, 14, 0)
    base = {
        "now": now,
        "enabled": True,
        "open_at": datetime(2026, 8, 13, 7, 0),
        "close_at": datetime(2026, 8, 13, 23, 0),
        "opening_threshold": 10,
        "quiet_minutes": 60,
        "validation_issues": [],
    }
    counting = automation_decision(
        **base,
        opening_count=9,
        last_opening_at=now - timedelta(hours=2),
        door_is_open=False,
    )
    assert counting["key"] == "counting"

    quiet = automation_decision(
        **base,
        opening_count=10,
        last_opening_at=now - timedelta(minutes=40),
        door_is_open=False,
    )
    assert quiet["key"] == "quiet_period"

    ready = automation_decision(
        **base,
        opening_count=10,
        last_opening_at=now - timedelta(minutes=61),
        door_is_open=False,
    )
    assert ready["eligible"] is True


def test_automation_never_starts_outside_opening_hours_or_with_bad_config():
    common = {
        "enabled": True,
        "open_at": datetime(2026, 8, 13, 7, 0),
        "close_at": datetime(2026, 8, 13, 23, 0),
        "opening_count": 12,
        "opening_threshold": 10,
        "quiet_minutes": 60,
        "last_opening_at": datetime(2026, 8, 13, 20, 0),
        "door_is_open": False,
    }
    outside = automation_decision(now=datetime(2026, 8, 13, 23, 5), validation_issues=[], **common)
    assert outside["key"] == "outside_hours"
    invalid = automation_decision(
        now=datetime(2026, 8, 13, 22, 0),
        validation_issues=["Velg nøyaktig 2 soner."],
        **common,
    )
    assert invalid["key"] == "configuration_error"


def test_unique_ints_preserves_order_and_removes_duplicates():
    assert unique_ints([2, "1", 2, 0, None, "bad"]) == [2, 1]
