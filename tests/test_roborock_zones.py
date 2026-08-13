from types import SimpleNamespace

import pytest

from roborock_zones import RoborockZoneScheduleError, discover_roborock_zone_candidates


def schedule(schedule_id: str, cron: str, segments: str, enabled: bool = False):
    return SimpleNamespace(schedule_id=schedule_id, cron=cron, segments=segments, enabled=enabled)


def test_disabled_1201_plan_maps_to_global_zone_one():
    candidates = discover_roborock_zone_candidates([schedule("a", "1 12 * * ?", "19")])
    assert [(item.zone_number, item.segment_id) for item in candidates] == [(1, "19")]


def test_active_and_unrelated_plans_are_ignored():
    candidates = discover_roborock_zone_candidates(
        [
            schedule("active", "1 12 * * ?", "19", enabled=True),
            schedule("night", "30 23 * * ?", "16,17"),
        ]
    )
    assert candidates == []


def test_test_plan_must_contain_exactly_one_segment():
    with pytest.raises(RoborockZoneScheduleError, match="nøyaktig ett segment"):
        discover_roborock_zone_candidates([schedule("bad", "2 12 * * ?", "16,17")])


def test_same_segment_cannot_be_assigned_to_two_zones_for_one_robot():
    with pytest.raises(RoborockZoneScheduleError, match="både Sone 1 og Sone 2"):
        discover_roborock_zone_candidates(
            [schedule("one", "1 12 * * ?", "19"), schedule("two", "2 12 * * ?", "19")]
        )


def test_same_global_zone_can_use_different_segments_on_different_robots():
    first_robot = discover_roborock_zone_candidates([schedule("first", "1 12 * * ?", "19")])
    second_robot = discover_roborock_zone_candidates([schedule("second", "1 12 * * ?", "26")])
    assert first_robot[0].zone_number == second_robot[0].zone_number == 1
    assert first_robot[0].segment_id != second_robot[0].segment_id


def test_raw_roborock_schedule_payload_is_supported():
    candidates = discover_roborock_zone_candidates(
        [
            {
                "id": 42,
                "cron": "3 12 * * ?",
                "enabled": False,
                "param": {"params": [{"segments": "26"}]},
            }
        ]
    )
    assert (candidates[0].zone_number, candidates[0].segment_id, candidates[0].schedule_id) == (3, "26", "42")
