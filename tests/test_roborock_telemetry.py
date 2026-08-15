from datetime import datetime

from roborock_domain import (
    roborock_active_cycle_summary,
    roborock_dock_error_label,
    roborock_dock_type_label,
    roborock_job_status,
    roborock_operational_readiness,
    roborock_resource_issues,
    roborock_telemetry_changes,
    roborock_telemetry_value_label,
)


def test_roborock_active_cycle_tracks_floor_return_and_dock_pause():
    history = [
        {"timestamp": datetime(2026, 8, 13, 6, 56), "state_code": 8, "in_cleaning": True, "battery": 41, "clean_time_seconds": 7300, "clean_area_m2": 64.62, "clean_percent": 76},
        {"timestamp": datetime(2026, 8, 13, 5, 53), "state_code": 8, "in_cleaning": True, "battery": 20, "clean_time_seconds": 7300, "clean_area_m2": 64.62, "clean_percent": 76},
        {"timestamp": datetime(2026, 8, 13, 5, 48), "state_code": 6, "in_cleaning": True, "in_returning": True, "clean_time_seconds": 7300},
        {"timestamp": datetime(2026, 8, 13, 5, 43), "state_code": 18, "in_cleaning": True, "in_returning": False, "clean_time_seconds": 7240},
        {"timestamp": datetime(2026, 8, 13, 3, 3), "state_code": 18, "in_cleaning": True, "in_returning": False, "clean_time_seconds": 60},
        {"timestamp": datetime(2026, 8, 13, 2, 58), "state_code": 8, "in_cleaning": False},
    ]

    cycle = roborock_active_cycle_summary(history)

    assert cycle is not None
    assert cycle["started_at"] == datetime(2026, 8, 13, 3, 2)
    assert cycle["last_floor_at"] == datetime(2026, 8, 13, 5, 43)
    assert cycle["dock_since"] == datetime(2026, 8, 13, 5, 53)
    assert cycle["phase"] == "charging_pause"
    assert cycle["phase_label"] == "Lader i dokk under pågående jobb"
    assert cycle["active_minutes"] == 121.7
    assert cycle["progress_percent"] == 76


def test_roborock_active_cycle_is_absent_after_job_finishes():
    history = [
        {"timestamp": datetime(2026, 8, 13, 7, 5), "state_code": 8, "in_cleaning": False},
        {"timestamp": datetime(2026, 8, 13, 7, 0), "state_code": 8, "in_cleaning": True},
    ]

    assert roborock_active_cycle_summary(history) is None


def test_roborock_job_status_distinguishes_completed_running_stopped_and_failed_jobs():
    assert roborock_job_status(True, 0, "2026-08-12T08:00:00") == ("complete", "Fullført")
    assert roborock_job_status(False, 0, None) == ("running", "Pågår")
    assert roborock_job_status(False, 0, "2026-08-12T08:00:00") == ("stopped", "Avbrutt")
    assert roborock_job_status(True, 12, "2026-08-12T08:00:00") == ("error", "Feil")


def test_roborock_resource_labels_are_readable():
    assert roborock_telemetry_value_label("clear_water_status", 0, "okay") == "OK"
    assert roborock_telemetry_value_label("dirty_water_status", 1, "full_not_installed") == "Full eller ikke montert"
    assert roborock_telemetry_value_label("dust_bag_status", 34, "full") == "Full"
    assert roborock_dock_type_label(8) == "Qrevo P10-dokk"
    assert roborock_dock_error_label(38) == "Rentvann mangler"


def test_roborock_readiness_ignores_unsupported_values_and_marks_active_robot():
    readiness = roborock_operational_readiness(
        cloud_online=True,
        last_error=None,
        error_code=0,
        dock_error="Ingen feil",
        clear_water="Ikke støttet",
        dirty_water="Ikke støttet",
        dust_bag="OK",
        active=True,
        data_age_minutes=1,
    )

    assert readiness == {"status": "active", "label": "Rengjør nå", "issues": []}


def test_roborock_readiness_collects_actionable_resource_problems():
    readiness = roborock_operational_readiness(
        cloud_online=True,
        last_error=None,
        error_code=0,
        dock_error="Rentvann mangler",
        clear_water="Tom",
        dirty_water="OK",
        dust_bag="Full",
        active=False,
        data_age_minutes=1,
    )

    assert readiness["status"] == "attention"
    assert readiness["label"] == "Krever tilsyn"
    assert readiness["issues"] == ["Rentvann mangler", "Støvpose: Full"]


def test_roborock_readiness_marks_stale_telemetry_for_follow_up():
    readiness = roborock_operational_readiness(
        cloud_online=True,
        last_error=None,
        error_code=0,
        dock_error="Ingen feil",
        clear_water="OK",
        dirty_water="OK",
        dust_bag="OK",
        active=False,
        data_age_minutes=17,
    )

    assert readiness["status"] == "attention"
    assert readiness["issues"] == ["Telemetri er 17 min gammel"]


def test_roborock_readiness_accepts_shared_twenty_minute_freshness_window():
    readiness = roborock_operational_readiness(
        cloud_online=True,
        last_error=None,
        error_code=0,
        dock_error="Ingen feil",
        clear_water="OK",
        dirty_water="OK",
        dust_bag="OK",
        active=False,
        data_age_minutes=17,
        stale_after_minutes=20,
    )

    assert readiness == {"status": "ready", "label": "Klar", "issues": []}


def test_roborock_resource_issues_deduplicates_dock_and_container_status():
    assert roborock_resource_issues("Rentvann mangler", "Tom", "OK", "Full") == [
        "Rentvann mangler",
        "Støvpose: Full",
    ]


def test_roborock_telemetry_changes_only_emits_changed_operational_values():
    previous = {
        "state_code": 8,
        "is_charging": True,
        "clear_water_status": 0,
        "clear_water_status_name": "okay",
        "dirty_water_status": 0,
        "dirty_water_status_name": "okay",
    }
    current = {
        **previous,
        "state_code": 6,
        "is_charging": False,
        "clear_water_status": 1,
        "clear_water_status_name": "out_of_water",
    }

    changes = roborock_telemetry_changes(previous, current)

    assert [change["field_name"] for change in changes] == ["state_code", "is_charging", "clear_water_status"]
    water_change = changes[-1]
    assert water_change["previous_label"] == "OK"
    assert water_change["current_label"] == "Tom"
    assert water_change["severity"] == "warning"


def test_initial_roborock_telemetry_sample_does_not_create_fake_events():
    assert roborock_telemetry_changes(None, {"state_code": 8, "is_charging": True}) == []
