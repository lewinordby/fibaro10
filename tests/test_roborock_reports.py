from datetime import date, datetime
from types import SimpleNamespace

from roborock_reports import build_night_report, report_window


def row(**values):
    return SimpleNamespace(**values)


def test_report_window_covers_evening_to_morning() -> None:
    window = report_window(date(2026, 8, 14))
    assert window["start"] == datetime(2026, 8, 13, 20, 0)
    assert window["ready_by"] == datetime(2026, 8, 14, 6, 45)
    assert window["end"] == datetime(2026, 8, 14, 8, 0)


def test_night_report_summarizes_modes_battery_and_mop_washes() -> None:
    robot = row(duid="robot-a", name="1.etg A", model="Qrevo")
    job = row(
        robot_duid="robot-a",
        record_id="job-1",
        begin_at=datetime(2026, 8, 13, 23, 0),  # UTC: 01:00 in Oslo
        end_at=datetime(2026, 8, 14, 0, 4),
        duration_minutes=64.0,
        duration_seconds=3840,
        cleaned_area_m2=38.5,
        area_m2=38.5,
        complete=True,
        error_code=0,
        wash_count=7,
        clean_times=1,
    )
    samples = [
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 1, 0), in_cleaning=True, battery=100, fan_power=105, water_box_mode=203, mop_mode=301, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=False),
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 2, 4), in_cleaning=True, battery=75, fan_power=105, water_box_mode=203, mop_mode=301, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=False),
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 6, 44), in_cleaning=False, battery=96, fan_power=105, water_box_mode=203, mop_mode=301, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=True),
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 7, 0), in_cleaning=False, battery=100, fan_power=105, water_box_mode=203, mop_mode=301, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=True),
    ]
    probes = [
        row(robot_duid="robot-a", command="GET_SMART_WASH_PARAMS", ok=True, raw={"value": {"smart_wash": 0, "wash_interval": 600}}),
        row(robot_duid="robot-a", command="GET_WASH_TOWEL_MODE", ok=True, raw={"value": {"wash_mode": 1}}),
    ]

    report = build_night_report(date(2026, 8, 14), [robot], [job], samples, probes)

    result = report["robots"][0]
    assert report["conclusion"]["status"] == "ok"
    assert report["summary"]["jobs"] == 1
    assert result["jobs"][0]["cleaningType"] == "mop"
    assert result["jobs"][0]["modeLabel"] == "Dyp · høy vannmengde · 1 runde"
    assert result["jobs"][0]["batteryStart"] == 100
    assert result["jobs"][0]["batteryEnd"] == 75
    assert result["jobs"][0]["expectedWashCount"] == 7
    assert result["settings"]["modeLabel"] == "Balansert"
    assert result["readiness"]["batteryAtOpening"] == 96
    assert result["readiness"]["fullChargeAt"].startswith("2026-08-14T07:00")


def test_water_shortage_is_reported_without_marking_completed_job_as_failed() -> None:
    robot = row(duid="robot-a", name="VIP", model="Qrevo")
    job = row(
        robot_duid="robot-a", record_id="job-2",
        begin_at=datetime(2026, 8, 14, 2, 0), end_at=datetime(2026, 8, 14, 3, 0),
        duration_minutes=60.0, duration_seconds=3600, cleaned_area_m2=30.0, area_m2=30.0,
        complete=True, error_code=0, wash_count=5, clean_times=1,
    )
    samples = [
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 4, 1), in_cleaning=True, battery=90, fan_power=105, water_box_mode=203, mop_mode=303, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=False),
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 5, 0), in_cleaning=True, battery=75, fan_power=105, water_box_mode=203, mop_mode=303, water_shortage_status=1, clear_water_status=1, clear_water_status_name="out_of_water", dock_error_status=0, is_charging=False),
    ]

    report = build_night_report(date(2026, 8, 14), [robot], [job], samples, [])

    result = report["robots"][0]["jobs"][0]
    assert report["conclusion"]["status"] == "warning"
    assert result["complete"] is True
    assert result["status"] == "warning"
    assert result["issues"] == ["Vannvarsel kl. 05:00"]
