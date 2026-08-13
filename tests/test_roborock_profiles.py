import pytest

from roborock_profiles import (
    DEFAULT_CLEANING_PROFILES,
    cleaning_profile_options,
    validate_cleaning_profile,
)


def test_all_default_profiles_are_valid_and_cover_each_type_and_level():
    validated = [validate_cleaning_profile(profile) for profile in DEFAULT_CLEANING_PROFILES]
    assert len(validated) == 6
    assert {(row["cleaning_type"], row["repeat"]) for row in validated} == {
        ("vacuum", 1),
        ("vacuum", 2),
        ("mop", 1),
        ("mop", 2),
        ("vacuum_mop", 1),
        ("vacuum_mop", 2),
    }


def test_profile_options_only_expose_deterministic_modes_supported_by_current_robots():
    options = cleaning_profile_options("roborock.vacuum.a75")
    assert [row["value"] for row in options["fanPower"]] == [105, 101, 102, 103, 104, 108]
    assert [row["value"] for row in options["waterBoxMode"]] == [200, 201, 202, 203]
    assert [row["value"] for row in options["mopMode"]] == [300, 301, 303, 304]
    assert options["excludedModes"]


@pytest.mark.parametrize(
    "values, message",
    [
        ({"cleaning_type": "vacuum", "fan_power": 102, "water_box_mode": 203, "mop_mode": 300, "repeat": 1}, "vannmengde Av"),
        ({"cleaning_type": "mop", "fan_power": 103, "water_box_mode": 203, "mop_mode": 300, "repeat": 1}, "sugekraft Av"),
        ({"cleaning_type": "vacuum_mop", "fan_power": 103, "water_box_mode": 200, "mop_mode": 300, "repeat": 1}, "både aktiv suging og vann"),
    ],
)
def test_conflicting_profile_combinations_are_rejected(values, message):
    with pytest.raises(ValueError, match=message):
        validate_cleaning_profile(values)
