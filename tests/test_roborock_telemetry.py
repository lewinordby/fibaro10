from roborock_domain import (
    roborock_dock_error_label,
    roborock_dock_type_label,
    roborock_telemetry_changes,
    roborock_telemetry_value_label,
)


def test_roborock_resource_labels_are_readable():
    assert roborock_telemetry_value_label("clear_water_status", 0, "okay") == "OK"
    assert roborock_telemetry_value_label("dirty_water_status", 1, "full_not_installed") == "Full eller ikke montert"
    assert roborock_telemetry_value_label("dust_bag_status", 34, "full") == "Full"
    assert roborock_dock_type_label(8) == "Qrevo P10-dokk"
    assert roborock_dock_error_label(38) == "Rentvann mangler"


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
