import importlib.util
import os
import unittest
from datetime import datetime


@unittest.skipUnless(
    importlib.util.find_spec("fastapi") and importlib.util.find_spec("sqlalchemy"),
    "FastAPI/SQLAlchemy dev dependencies are not installed in this Python environment.",
)
class Sun2AxisSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")
        import main

        cls.main = main

    def test_minute_precision_sun2_time_uses_middle_of_minute_before_lead(self) -> None:
        row = self.main.Sun2TanningSession(
            started_at=datetime(2026, 6, 13, 17, 46),
            raw={"Tidspunkt": "2026-06-13 17:46"},
        )

        self.assertEqual(
            self.main.sun2_session_axis_target_at(row),
            datetime(2026, 6, 13, 17, 46, 25),
        )

    def test_second_precision_sun2_time_uses_actual_second_before_lead(self) -> None:
        row = self.main.Sun2TanningSession(
            started_at=datetime(2026, 6, 13, 17, 46, 41),
            raw={"Tidspunkt": "2026-06-13 17:46:41"},
        )

        self.assertEqual(
            self.main.sun2_session_axis_target_at(row),
            datetime(2026, 6, 13, 17, 46, 36),
        )
