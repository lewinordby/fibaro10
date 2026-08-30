import os
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch


os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

import main


class FakeResult:
    def __init__(self, rowcount: int = 1):
        self.rowcount = rowcount


class FakeSession:
    def __init__(self):
        self.statements = []
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, statement):
        self.statements.append(statement)
        return FakeResult()

    async def commit(self):
        self.committed = True


class OperationalMaintenanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_met_status_is_recorded_only_for_real_refresh(self) -> None:
        session = FakeSession()
        now_value = datetime.now(timezone.utc).replace(tzinfo=None)
        forecast = {
            "text": "Lettskyet",
            "raw_endpoint": "https://api.met.no/test",
            "forecast_time": now_value,
            "expires_at": now_value + timedelta(minutes=30),
        }
        main.MET_WEATHER_CACHE.update(expires=datetime.min, value=None)
        main.process_locks.met_weather_fetch_lock = None
        with (
            patch("main.asyncio.to_thread", new=AsyncMock(return_value=forecast)) as fetch,
            patch.object(main.weather_dependencies, "async_session", return_value=session),
            patch("main.record_import_job", new=AsyncMock()) as record,
        ):
            first = await main.met_weather_cached()
            second = await main.met_weather_cached()

        self.assertIs(first, forecast)
        self.assertIs(second, forecast)
        fetch.assert_awaited_once()
        record.assert_awaited_once()
        self.assertEqual(record.await_args.args[1], "yr_weather_refresh")
        raw = record.await_args.kwargs["raw"]
        self.assertEqual(raw["forecastTime"], now_value.isoformat())
        json.dumps(raw)
        self.assertTrue(session.committed)

    async def test_retention_only_deletes_operational_history(self) -> None:
        session = FakeSession()
        with patch.object(main.system_dependencies, "async_session", return_value=session):
            deleted = await main.cleanup_operational_history_once(datetime(2026, 8, 7, 12, 0))

        self.assertTrue(session.committed)
        self.assertEqual(set(deleted), {
            "accessLogsSuccess",
            "accessLogsFailure",
            "importRunsSuccess",
            "importRunsFailure",
            "notificationsSent",
            "authSessions",
        })
        statements = "\n".join(str(statement) for statement in session.statements)
        self.assertIn("access_logs", statements)
        self.assertIn("import_job_runs", statements)
        self.assertIn("notification_outbox", statements)
        self.assertIn("auth_sessions", statements)
        self.assertNotIn("parkering", statements)
        self.assertNotIn("sun2_tanning_sessions", statements)


if __name__ == "__main__":
    unittest.main()
