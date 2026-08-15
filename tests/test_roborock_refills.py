from datetime import date, datetime
from types import SimpleNamespace

import pytest

from roborock_refills import build_refill_log, iso_week_key, iso_week_start


def row(**values):
    return SimpleNamespace(**values)


def test_refill_log_only_includes_clean_water_restored_events() -> None:
    robots = [
        row(duid="a", name="1.etg A", provider="roborock"),
        row(duid="b", name="Aqua10", provider="dreame"),
    ]
    events = [
        row(id=1, robot_duid="a", timestamp=datetime(2026, 8, 10, 8), field_name="clear_water_status", previous_value="0", current_value="1", previous_label="OK", current_label="Tom"),
        row(id=2, robot_duid="a", timestamp=datetime(2026, 8, 10, 9), field_name="clear_water_status", previous_value="1", current_value="0", previous_label="Tom", current_label="OK"),
        row(id=3, robot_duid="a", timestamp=datetime(2026, 8, 11, 9), field_name="dirty_water_status", previous_value="1", current_value="0", previous_label="Full", current_label="OK"),
        row(id=4, robot_duid="a", timestamp=datetime(2026, 8, 12, 9), field_name="state_code", previous_value="23", current_value="8", previous_label="Vasker mopp", current_label="Lader"),
    ]

    report = build_refill_log(
        date(2026, 8, 10),
        robots,
        events,
        generated_at=datetime(2026, 8, 15, 12),
    )

    assert report["summary"]["fills"] == 1
    assert report["summary"]["robots"] == 1
    assert report["summary"]["robotsWithFills"] == 1
    assert report["events"][0]["robotName"] == "1.etg A"
    assert report["events"][0]["previousLabel"] == "Tom"
    assert report["events"][0]["currentLabel"] == "OK"
    assert report["events"][0]["timestamp"].startswith("2026-08-10T09:00")
    assert "moppevask" not in report["measurementNote"].lower()


def test_refill_log_calculates_intervals_per_dock() -> None:
    robots = [
        row(duid="a", name="1.etg A", provider="roborock"),
        row(duid="b", name="VIP", provider="roborock"),
    ]
    events = [
        row(id=1, robot_duid="a", timestamp=datetime(2026, 8, 10, 8), field_name="clear_water_status", previous_value="1", current_value="0", previous_label="Tom", current_label="OK"),
        row(id=2, robot_duid="b", timestamp=datetime(2026, 8, 10, 10), field_name="clear_water_status", previous_value="1", current_value="0", previous_label="Tom", current_label="OK"),
        row(id=3, robot_duid="a", timestamp=datetime(2026, 8, 11, 8), field_name="clear_water_status", previous_value="1", current_value="0", previous_label="Tom", current_label="OK"),
    ]

    report = build_refill_log(
        date(2026, 8, 10),
        robots,
        events,
        generated_at=datetime(2026, 8, 15, 12),
    )

    assert report["events"][0]["minutesSincePrevious"] == 1440
    assert report["events"][1]["minutesSincePrevious"] is None
    assert report["robots"][0]["name"] == "1.etg A"
    assert report["robots"][0]["count"] == 2
    assert report["robots"][0]["averageIntervalMinutes"] == 1440
    assert report["summary"]["averageIntervalMinutes"] == 1440


def test_refill_log_can_limit_summary_to_water_capable_docks() -> None:
    robots = [
        row(duid="a", name="1.etg A", provider="roborock"),
        row(duid="b", name="1.etg B", provider="roborock"),
    ]
    report = build_refill_log(
        date(2026, 8, 10),
        robots,
        [],
        generated_at=datetime(2026, 8, 15, 12),
        water_capable_duids={"a"},
    )

    assert report["summary"]["robots"] == 1
    assert [robot["name"] for robot in report["robots"]] == ["1.etg A"]


def test_iso_week_navigation_handles_year_boundaries_and_invalid_values() -> None:
    assert iso_week_start("2026-W01") == date(2025, 12, 29)
    assert iso_week_key(date(2025, 12, 29)) == "2026-W01"
    assert iso_week_start(None, today=date(2026, 8, 15)) == date(2026, 8, 10)
    with pytest.raises(ValueError, match="YYYY-Www"):
        iso_week_start("uke-33")
