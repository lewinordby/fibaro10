from datetime import date, datetime
from types import SimpleNamespace

import pytest

from roborock_refills import build_refill_log, iso_week_key, iso_week_start


def row(**values):
    return SimpleNamespace(**values)


def water_event(event_id: int, duid: str, timestamp: datetime, *, empty: bool):
    return row(
        id=event_id,
        robot_duid=duid,
        timestamp=timestamp,
        field_name="clear_water_status",
        previous_value="0" if empty else "1",
        current_value="1" if empty else "0",
        previous_label="OK" if empty else "Tom",
        current_label="Tom" if empty else "OK",
    )


def test_refill_log_pairs_empty_and_refilled_times() -> None:
    robots = [
        row(duid="a", name="1.etg A", provider="roborock"),
        row(duid="b", name="Aqua10", provider="dreame"),
    ]
    events = [
        water_event(1, "a", datetime(2026, 8, 10, 8), empty=True),
        water_event(2, "a", datetime(2026, 8, 10, 9), empty=False),
        row(id=3, robot_duid="a", timestamp=datetime(2026, 8, 11, 9), field_name="dirty_water_status", previous_value="1", current_value="0", previous_label="Full", current_label="OK"),
        row(id=4, robot_duid="a", timestamp=datetime(2026, 8, 12, 9), field_name="state_code", previous_value="23", current_value="8", previous_label="Vasker mopp", current_label="Lader"),
    ]

    report = build_refill_log(
        date(2026, 8, 10),
        robots,
        events,
        generated_at=datetime(2026, 8, 15, 12),
    )

    assert report["summary"]["empties"] == 1
    assert report["summary"]["fills"] == 1
    assert report["summary"]["pending"] == 0
    assert report["summary"]["robots"] == 2
    assert [robot["name"] for robot in report["robots"]] == ["1.etg A", "Aqua10"]
    assert len(report["cycles"]) == 1
    assert report["cycles"][0]["robotName"] == "1.etg A"
    assert report["cycles"][0]["emptyAt"].startswith("2026-08-10T08:00")
    assert report["cycles"][0]["refilledAt"].startswith("2026-08-10T09:00")
    assert report["cycles"][0]["emptyMinutes"] == 60
    assert report["cycles"][0]["status"] == "completed"


def test_refill_log_calculates_empty_duration_per_dock() -> None:
    robots = [
        row(duid="a", name="1.etg A", provider="roborock"),
        row(duid="b", name="VIP", provider="roborock"),
    ]
    events = [
        water_event(1, "a", datetime(2026, 8, 10, 8), empty=True),
        water_event(2, "a", datetime(2026, 8, 10, 9), empty=False),
        water_event(3, "b", datetime(2026, 8, 10, 10), empty=True),
        water_event(4, "b", datetime(2026, 8, 10, 12), empty=False),
        water_event(5, "a", datetime(2026, 8, 11, 8), empty=True),
        water_event(6, "a", datetime(2026, 8, 11, 10), empty=False),
    ]

    report = build_refill_log(
        date(2026, 8, 10),
        robots,
        events,
        generated_at=datetime(2026, 8, 15, 12),
    )

    assert report["summary"]["averageEmptyMinutes"] == 100
    robot_a = next(robot for robot in report["robots"] if robot["name"] == "1.etg A")
    assert robot_a["empties"] == 2
    assert robot_a["fills"] == 2
    assert robot_a["averageEmptyMinutes"] == 90


def test_refill_log_keeps_current_empty_dock_pending() -> None:
    robot = row(duid="a", name="1.etg A", provider="roborock")
    report = build_refill_log(
        date(2026, 8, 10),
        [robot],
        [water_event(1, "a", datetime(2026, 8, 15, 6), empty=True)],
        generated_at=datetime(2026, 8, 15, 12),
    )

    assert report["summary"]["pending"] == 1
    assert report["cycles"][0]["refilledAt"] is None
    assert report["cycles"][0]["emptyMinutes"] == 360
    assert report["robots"][0]["pending"] is True
    assert report["robots"][0]["currentEmptySince"].startswith("2026-08-15T06:00")


def test_refill_log_does_not_treat_other_water_errors_as_empty() -> None:
    robot = row(duid="a", name="1.etg A", provider="roborock")
    report = build_refill_log(
        date(2026, 8, 10),
        [robot],
        [
            row(
                id=1,
                robot_duid="a",
                timestamp=datetime(2026, 8, 15, 6),
                field_name="clear_water_status",
                previous_value="0",
                current_value="2",
                previous_label="OK",
                current_label="Påfyllingsfeil",
            )
        ],
        generated_at=datetime(2026, 8, 15, 12),
    )

    assert report["summary"]["empties"] == 0
    assert report["summary"]["pending"] == 0
    assert report["cycles"] == []


def test_refill_log_pairs_a_refill_with_an_empty_event_before_the_week() -> None:
    robot = row(duid="a", name="1.etg A", provider="roborock")
    report = build_refill_log(
        date(2026, 8, 10),
        [robot],
        [
            water_event(1, "a", datetime(2026, 8, 9, 23), empty=True),
            water_event(2, "a", datetime(2026, 8, 10, 8), empty=False),
        ],
        generated_at=datetime(2026, 8, 15, 12),
    )

    assert report["summary"]["empties"] == 0
    assert report["summary"]["fills"] == 1
    assert report["cycles"][0]["emptyAt"].startswith("2026-08-09T23:00")
    assert report["cycles"][0]["refilledAt"].startswith("2026-08-10T08:00")


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


def test_refill_log_uses_aqua10_tank_removal_and_replacement_as_refill_cycle() -> None:
    robot = row(duid="dreame:aqua10", name="Aqua10", provider="dreame")
    events = [
        row(
            id=1,
            robot_duid=robot.duid,
            timestamp=datetime(2026, 8, 12, 8),
            field_name="clear_water_status",
            previous_value="0",
            current_value="2",
            previous_label="OK",
            current_label="Lite",
        ),
        row(
            id=2,
            robot_duid=robot.duid,
            timestamp=datetime(2026, 8, 12, 8, 5),
            field_name="clear_water_status",
            previous_value="2",
            current_value="1",
            previous_label="Lite",
            current_label="Ikke montert",
        ),
        row(
            id=3,
            robot_duid=robot.duid,
            timestamp=datetime(2026, 8, 12, 8, 10),
            field_name="clear_water_status",
            previous_value="1",
            current_value="0",
            previous_label="Ikke montert",
            current_label="OK",
        ),
    ]

    report = build_refill_log(
        date(2026, 8, 10),
        [robot],
        events,
        generated_at=datetime(2026, 8, 15, 12),
    )

    assert report["summary"] == {
        "empties": 1,
        "fills": 1,
        "robots": 1,
        "pending": 0,
        "latestFillAt": "2026-08-12T08:10:00+02:00",
        "averageEmptyMinutes": 5,
    }
    assert report["cycles"][0]["robotName"] == "Aqua10"
    assert report["cycles"][0]["emptyAt"].startswith("2026-08-12T08:05")
    assert report["cycles"][0]["refilledAt"].startswith("2026-08-12T08:10")


def test_refill_log_does_not_mark_aqua10_low_water_as_empty() -> None:
    robot = row(duid="dreame:aqua10", name="Aqua10", provider="dreame")
    event = row(
        id=1,
        robot_duid=robot.duid,
        timestamp=datetime(2026, 8, 12, 8),
        field_name="clear_water_status",
        previous_value="0",
        current_value="2",
        previous_label="OK",
        current_label="Lite",
    )

    report = build_refill_log(
        date(2026, 8, 10),
        [robot],
        [event],
        generated_at=datetime(2026, 8, 15, 12),
    )

    assert report["summary"]["robots"] == 1
    assert report["summary"]["empties"] == 0
    assert report["summary"]["fills"] == 0
    assert report["cycles"] == []


def test_iso_week_navigation_handles_year_boundaries_and_invalid_values() -> None:
    assert iso_week_start("2026-W01") == date(2025, 12, 29)
    assert iso_week_key(date(2025, 12, 29)) == "2026-W01"
    assert iso_week_start(None, today=date(2026, 8, 15)) == date(2026, 8, 10)
    with pytest.raises(ValueError, match="YYYY-Www"):
        iso_week_start("uke-33")
