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
                "last_success_at": None,
            }
        )

        with patch.object(linker, "fibaro_post", new=AsyncMock(return_value={"ok": True})):
            asyncio.run(linker.post_status({"generation": 2}, "ajour", "Ingen flere ubehandlede parkeringer."))

        self.assertIsNone(linker.state["last_error"])
        self.assertIsNotNone(linker.state["last_success_at"])


if __name__ == "__main__":
    unittest.main()
