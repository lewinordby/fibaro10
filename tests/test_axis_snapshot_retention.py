from datetime import datetime, timedelta
import os

from axis_camera_snapshots.app import main as axis_app


def test_default_retention_is_35_days(monkeypatch):
    monkeypatch.delenv("AXIS_RETENTION_DAYS", raising=False)
    assert axis_app.default_config().retention_days == 35


def test_snapshot_cleanup_is_throttled(monkeypatch, tmp_path):
    monkeypatch.setattr(axis_app, "SNAPSHOT_ROOT", tmp_path / "snapshots")
    monkeypatch.setattr(axis_app, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(axis_app, "last_cleanup_monotonic", 0.0)
    monkeypatch.setattr(axis_app, "CLEANUP_INTERVAL_SECONDS", 3600)
    axis_app.SNAPSHOT_ROOT.mkdir()

    old_image = axis_app.SNAPSHOT_ROOT / "old.jpg"
    old_image.write_bytes(b"jpeg")
    old_time = (datetime.now() - timedelta(days=36)).timestamp()
    os.utime(old_image, (old_time, old_time))

    assert axis_app.delete_old_snapshots_if_due(35) == 1
    assert not old_image.exists()

    second_old_image = axis_app.SNAPSHOT_ROOT / "second-old.jpg"
    second_old_image.write_bytes(b"jpeg")
    os.utime(second_old_image, (old_time, old_time))

    assert axis_app.delete_old_snapshots_if_due(35) == 0
    assert second_old_image.exists()


def test_latest_snapshot_uses_state_file_without_scanning_archive(monkeypatch, tmp_path):
    snapshot_root = tmp_path / "snapshots"
    snapshot_root.mkdir()
    latest = snapshot_root / "latest.jpg"
    latest.write_bytes(b"jpeg")

    monkeypatch.setattr(axis_app, "SNAPSHOT_ROOT", snapshot_root)
    monkeypatch.setattr(axis_app, "load_state", lambda: {"last_file": str(latest)})

    def fail_if_archive_is_scanned(*_args, **_kwargs):
        raise AssertionError("The archive must not be scanned when the state file is valid")

    monkeypatch.setattr(type(snapshot_root), "rglob", fail_if_archive_is_scanned)

    assert axis_app.latest_snapshot_file() == latest.resolve()
