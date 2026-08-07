import asyncio
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.request = lambda *args, **kwargs: None
    sys.modules["requests"] = requests_stub

from parking_sun_linker.app import main as linker


class ParkingSunLinkerHealthTests(unittest.TestCase):
    def test_successful_status_report_clears_stale_error(self) -> None:
        linker.state.update(
            {
                "last_action": "error",
                "last_error": "temporary startup error",
                "last_error_at": linker.utcnow_iso(),
                "consecutive_errors": 1,
                "last_success_at": None,
            }
        )

        with patch.object(linker, "fibaro_post", new=AsyncMock(return_value={"ok": True})):
            asyncio.run(linker.post_status({"generation": 2}, "ajour", "Ingen flere ubehandlede parkeringer."))

        self.assertIsNone(linker.state["last_error"])
        self.assertIsNone(linker.state["last_error_at"])
        self.assertEqual(linker.state["consecutive_errors"], 0)
        self.assertIsNotNone(linker.state["last_success_at"])

    def test_recent_single_dependency_error_is_transient(self) -> None:
        linker.state.update(
            {
                "last_error": "502 from Fibaro10 during rollout",
                "last_error_at": linker.utcnow_iso(),
                "consecutive_errors": 1,
            }
        )

        payload = asyncio.run(linker.health())

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["transient"])

    def test_repeated_dependency_error_fails_health(self) -> None:
        linker.state.update(
            {
                "last_error": "Fibaro10 is still unavailable",
                "last_error_at": linker.utcnow_iso(),
                "consecutive_errors": 4,
            }
        )

        payload = asyncio.run(linker.health())

        self.assertFalse(payload["ok"])
        self.assertFalse(payload["transient"])


if __name__ == "__main__":
    unittest.main()
