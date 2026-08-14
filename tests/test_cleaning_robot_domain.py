from cleaning_robot_domain import (
    cleaning_provider,
    cleaning_provider_label,
    cleaning_robot_external_id,
    cleaning_robot_uid,
    expected_dreame_summary,
)


def test_cleaning_provider_is_explicit_and_source_aware():
    assert cleaning_provider("dreame", "anything") == "dreame"
    assert cleaning_provider(None, "dreame_logger") == "dreame"
    assert cleaning_provider(None, "Roborock_logger") == "roborock"
    assert cleaning_provider_label("dreame") == "Dreame"


def test_dreame_ids_are_namespaced_without_changing_legacy_roborock_ids():
    assert cleaning_robot_uid("dreame", "12345") == "dreame:12345"
    assert cleaning_robot_uid("dreame", "dreame:12345") == "dreame:12345"
    assert cleaning_robot_external_id("dreame", "dreame:12345") == "12345"
    assert cleaning_robot_uid("roborock", "abc") == "abc"


def test_expected_aqua10_is_a_pending_slot_without_fabricated_telemetry():
    row = expected_dreame_summary("Aqua10")

    assert row["name"] == "Aqua10"
    assert row["provider"] == "dreame"
    assert row["integration_status"] == "pending"
    assert row["battery"] is None
    assert row["cloud_online"] is None
    assert row["readiness"]["status"] == "pending"

