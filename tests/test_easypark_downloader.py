import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from easypark_downloader.app import main as collector


@pytest.fixture(autouse=True)
def isolated_collector(monkeypatch, tmp_path):
    monkeypatch.setattr(collector, "state", {"running": False, "last_success_at": "2026-08-29T10:00:00+00:00"})
    monkeypatch.setattr(collector, "lock", asyncio.Lock())
    monkeypatch.setattr(collector, "AUTH_STATE_PATH", tmp_path / "auth.json")
    monkeypatch.setattr(collector, "report_failure_to_fibaro10", lambda *args: None)
    monkeypatch.setattr(collector, "schedule_self_restart", lambda *args: None)


def test_manual_requests_are_coalesced_before_background_task_starts(monkeypatch):
    async def scenario():
        finished = asyncio.Event()
        started = []

        async def run(*args, **kwargs):
            started.append(args)
            await finished.wait()
            collector.set_state(running=False)

        monkeypatch.setattr(collector, "run_download_import", run)
        first = collector.queue_import()
        second = collector.queue_import()
        await asyncio.sleep(0)
        assert first["status"] == "started"
        assert second["status"] == "busy"
        assert len(started) == 1
        finished.set()
        await asyncio.sleep(0)
        assert not collector.import_is_active()

    asyncio.run(scenario())


def test_failed_background_import_releases_lock_without_advancing_success(monkeypatch):
    async def scenario():
        monkeypatch.setattr(collector, "run_download_import", AsyncMock(side_effect=RuntimeError("upstream unavailable")))
        await collector.run_import_background()
        assert collector.state["last_success_at"] == "2026-08-29T10:00:00+00:00"
        assert collector.state["last_action"] == "error"
        assert not collector.import_is_active()
        monkeypatch.setattr(collector, "run_download_import", AsyncMock(return_value={"ok": True}))
        assert await collector.run_once() == {"ok": True}

    asyncio.run(scenario())


def test_timeout_keeps_previous_success_and_reports_failure(monkeypatch):
    async def fail(*args, **kwargs):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(collector, "_run_download_import", fail)
    with pytest.raises(RuntimeError, match="sekunder"):
        asyncio.run(collector.run_download_import())
    assert collector.state["last_action"] == "timeout"
    assert collector.state["last_success_at"] == "2026-08-29T10:00:00+00:00"
    assert not collector.state["running"]


@pytest.mark.parametrize("now, expected", [
    ("2026-08-30T07:59:00+02:00", "2026-08-30T08:00:00+02:00"),
    ("2026-08-30T10:00:00+02:00", "2026-08-30T12:00:00+02:00"),
    ("2026-08-30T23:01:00+02:00", "2026-08-31T08:00:00+02:00"),
    ("2026-10-24T23:01:00+02:00", "2026-10-25T08:00:00+01:00"),
])
def test_schedule_uses_oslo_time_and_calendar_day(monkeypatch, now, expected):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            value = datetime.fromisoformat(now)
            return value.astimezone(tz or timezone.utc)

    monkeypatch.setattr(collector, "datetime", Clock)
    monkeypatch.setattr(collector, "RUN_TIMES", "08:00,10:00,12:00,14:00,16:00,18:00,20:00,23:00")
    assert collector.next_run_at().isoformat() == expected


def test_auth_state_survives_new_read_and_preserves_existing_fields():
    collector.write_auth_state(last_login_at="2026-08-30T01:00:00+00:00", marker="test-only")
    collector.write_auth_state(last_good_profile_at="2026-08-30T02:00:00+00:00")
    assert collector.read_auth_state() == {
        "last_login_at": "2026-08-30T01:00:00+00:00", "marker": "test-only",
        "last_good_profile_at": "2026-08-30T02:00:00+00:00",
    }
