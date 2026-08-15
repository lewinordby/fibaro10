from datetime import datetime
from types import SimpleNamespace

from roborock_water import build_water_report


def row(**values):
    return SimpleNamespace(**values)


def test_water_report_combines_settings_usage_and_resource_events() -> None:
    robot = row(duid="robot-a", name="1.etg A", provider="roborock", model="Qrevo")
    telemetry = row(
        robot_duid="robot-a",
        timestamp=datetime(2026, 8, 15, 11, 55),
        clear_water_status=1,
        clear_water_status_name="out_of_water",
        dirty_water_status=0,
        dirty_water_status_name="okay",
        dust_bag_status=0,
        dust_bag_status_name="okay",
        clean_fluid_status=0,
        clean_fluid_status_name="okay",
        dock_error_status=0,
        water_shortage_status=0,
        water_box_status=1,
        water_box_carriage_status=1,
        water_box_filter_status=0,
        raw={
            "normalized": {
                "water_interlock": {
                    "enabled": True,
                    "status": "blocked",
                    "label": "Vannsperre aktiv (2 planer)",
                    "paused_count": 2,
                    "paused_schedules": [{"timer_id": "one"}, {"timer_id": "two"}],
                }
            }
        },
    )
    probes = [
        row(robot_duid="robot-a", command="GET_SMART_WASH_PARAMS", ok=True, raw={"value": {"smart_wash": 0, "wash_interval": 600}}),
        row(robot_duid="robot-a", command="GET_WASH_TOWEL_MODE", ok=True, raw={"value": {"wash_mode": 1}}),
        row(robot_duid="robot-a", command="GET_WATER_BOX_CUSTOM_MODE", ok=True, raw={"value": {"water_box_mode": 203}}),
    ]
    jobs = [
        row(robot_duid="robot-a", begin_at=datetime(2026, 8, 15, 6), wash_count=3, cleaned_area_m2=30, area_m2=30, duration_minutes=45),
        row(robot_duid="robot-a", begin_at=datetime(2026, 8, 14, 6), wash_count=2, cleaned_area_m2=20, area_m2=20, duration_minutes=30),
    ]
    events = [
        row(id=1, robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 8), field_name="clear_water_status", title="Rentvann", previous_label="Tom", current_label="OK", current_value="0", severity="info"),
        row(id=2, robot_duid="robot-a", timestamp=datetime(2026, 8, 15, 10), field_name="clear_water_status", title="Rentvann", previous_label="OK", current_label="Tom", current_value="1", severity="warning"),
    ]

    report = build_water_report(
        7,
        [robot],
        jobs,
        [telemetry],
        events,
        probes,
        generated_at=datetime(2026, 8, 15, 12),
    )

    result = report["robots"][0]
    assert result["status"] == "attention"
    assert result["current"]["cleanWater"]["label"] == "Tom"
    assert result["current"]["dustBag"]["label"] == "OK"
    assert result["current"]["dockStatus"]["label"] == "Ingen feil"
    assert result["current"]["dockStatus"]["attention"] is False
    assert result["current"]["waterBox"]["label"] == "Montert"
    assert result["current"]["mopAttached"]["label"] == "Montert"
    assert result["current"]["waterFilter"]["label"] == "OK"
    assert result["current"]["interlock"]["status"] == "blocked"
    assert result["current"]["interlock"]["pausedCount"] == 2
    assert result["settings"]["intervalMinutes"] == 10
    assert result["settings"]["washModeLabel"] == "Balansert"
    assert result["settings"]["waterModeLabel"] == "Høy"
    assert result["usage"] == {
        "jobs": 2,
        "mopJobs": 2,
        "washCount": 5,
        "areaM2": 50.0,
        "durationMinutes": 75.0,
        "areaPerWashM2": 10.0,
    }
    assert result["lastCleanWaterEmptyAt"].startswith("2026-08-15T10:00")
    assert result["lastCleanWaterRestoredAt"].startswith("2026-08-14T08:00")
    assert report["summary"]["waterWarnings"] == 1
    assert report["summary"]["restoredEvents"] == 1
    assert report["daily"][-1]["washCount"] == 3


def test_water_report_marks_a_robot_without_water_dock_as_unsupported() -> None:
    robot = row(duid="robot-b", name="1.etg B", provider="roborock", model="Q5")
    telemetry = row(
        robot_duid="robot-b",
        timestamp=datetime(2026, 8, 15, 11, 55),
        clear_water_status=None,
        clear_water_status_name=None,
        dirty_water_status=None,
        dirty_water_status_name=None,
        clean_fluid_status=None,
        clean_fluid_status_name=None,
        water_shortage_status=0,
    )

    report = build_water_report(1, [robot], [], [telemetry], [], [], generated_at=datetime(2026, 8, 15, 12))

    assert report["robots"][0]["status"] == "unsupported"
    assert report["robots"][0]["statusLabel"] == "Ingen vanndokk"
    assert report["summary"]["waterCapable"] == 0
