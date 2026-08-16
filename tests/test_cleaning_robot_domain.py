from cleaning_robot_domain import (
    cleaning_robot_is_active,
    cleaning_robot_operational_state,
    cleaning_robot_sort_key,
    cleaning_provider,
    cleaning_provider_label,
    cleaning_robot_external_id,
    cleaning_robot_uid,
    expected_dreame_summary,
)


def test_cleaning_robot_display_order_matches_the_operational_flow():
    names = ["2.etg", "VIP", "Aqua10", "1.etg A", "1.etg B"]

    assert sorted(names, key=cleaning_robot_sort_key) == ["1.etg B", "1.etg A", "VIP", "2.etg", "Aqua10"]


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


def test_cleaning_robot_operational_state_prioritizes_setup_connection_and_errors():
    assert cleaning_robot_operational_state(
        integration_status="pending",
        cloud_online=False,
        error_code=12,
        data_age_minutes=None,
        active=True,
    ) == ("pending", "Venter på oppsett")
    assert cleaning_robot_operational_state(
        cloud_online=False,
        data_age_minutes=0,
        active=True,
    ) == ("error", "Frakoblet")
    assert cleaning_robot_operational_state(
        cloud_online=True,
        error_code="12",
        data_age_minutes=0,
    ) == ("error", "Feil")


def test_cleaning_robot_operational_state_requires_fresh_data_before_active_or_ready():
    assert cleaning_robot_operational_state(
        cloud_online=True,
        data_age_minutes=None,
        active=True,
    ) == ("warning", "Utdatert status")
    assert cleaning_robot_operational_state(
        cloud_online=True,
        data_age_minutes=21,
        active=True,
    ) == ("warning", "Utdatert status")
    assert cleaning_robot_operational_state(
        cloud_online=True,
        error_code="0",
        data_age_minutes=20,
        active=True,
        active_label="Vasker mopp",
    ) == ("active", "Vasker mopp")
    assert cleaning_robot_operational_state(
        cloud_online=True,
        data_age_minutes=0,
        ready_label="Lader",
    ) == ("ok", "Lader")


def test_cleaning_robot_active_state_is_shared_across_overviews():
    assert cleaning_robot_is_active(True, 8) is True
    assert cleaning_robot_is_active(False, 7) is True
    assert cleaning_robot_is_active(None, "23") is True
    assert cleaning_robot_is_active(False, 8) is False
    assert cleaning_robot_is_active(False, 6, "dreame") is False
    assert cleaning_robot_is_active(True, 6, "dreame") is True
