from datetime import datetime
from types import SimpleNamespace

from roborock_domain import reconcile_roborock_schedule_snapshot


def schedule(schedule_id: str, *, enabled: bool = True, deleted_at=None):
    return SimpleNamespace(
        schedule_id=schedule_id,
        enabled=enabled,
        deleted_at=deleted_at,
    )


def test_missing_schedule_is_marked_deleted_and_disabled():
    removed_at = datetime(2026, 8, 14, 11, 30)
    current = schedule("current")
    removed = schedule("removed")

    deleted_count = reconcile_roborock_schedule_snapshot(
        [current, removed],
        {"current"},
        removed_at,
    )

    assert deleted_count == 1
    assert current.deleted_at is None
    assert current.enabled is True
    assert removed.deleted_at == removed_at
    assert removed.enabled is False


def test_reappearing_schedule_is_restored_without_new_deletion():
    old_deletion = datetime(2026, 8, 13, 9, 0)
    restored = schedule("restored", enabled=False, deleted_at=old_deletion)

    deleted_count = reconcile_roborock_schedule_snapshot(
        [restored],
        {"restored"},
        datetime(2026, 8, 14, 11, 30),
    )

    assert deleted_count == 0
    assert restored.deleted_at is None


def test_already_deleted_schedule_keeps_original_deletion_time():
    original_deletion = datetime(2026, 8, 12, 8, 0)
    removed = schedule("removed", enabled=False, deleted_at=original_deletion)

    deleted_count = reconcile_roborock_schedule_snapshot(
        [removed],
        set(),
        datetime(2026, 8, 14, 11, 30),
    )

    assert deleted_count == 0
    assert removed.deleted_at == original_deletion
