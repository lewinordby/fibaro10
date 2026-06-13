import importlib.util
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


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
            datetime(2026, 6, 13, 17, 46, 15),
        )

    def test_second_precision_sun2_time_uses_actual_second_before_lead(self) -> None:
        row = self.main.Sun2TanningSession(
            started_at=datetime(2026, 6, 13, 17, 46, 41),
            raw={"Tidspunkt": "2026-06-13 17:46:41"},
        )

        self.assertEqual(
            self.main.sun2_session_axis_target_at(row),
            datetime(2026, 6, 13, 17, 46, 26),
        )

    def test_session_axis_target_series_uses_five_images_around_primary(self) -> None:
        row = self.main.Sun2TanningSession(
            started_at=datetime(2026, 6, 13, 17, 46),
            raw={"Tidspunkt": "2026-06-13 17:46"},
        )

        series = self.main.sun2_session_axis_target_series(row)

        self.assertEqual([item[0] for item in series], [-25, -20, -15, -10, -5])
        self.assertEqual([item[1].strftime("%H:%M:%S") for item in series], ["17:46:05", "17:46:10", "17:46:15", "17:46:20", "17:46:25"])
        self.assertEqual([item[2] for item in series], [False, False, True, False, False])

    def test_axis_snapshot_id_roundtrip(self) -> None:
        captured_at = datetime(2026, 6, 13, 17, 46, 27)

        snapshot_id = self.main.axis_snapshot_id(captured_at)

        self.assertEqual(snapshot_id, "20260613174627")
        self.assertEqual(self.main.parse_axis_snapshot_id(snapshot_id), captured_at)
        self.assertIsNone(self.main.parse_axis_snapshot_id("../axis_2026"))

    def test_axis_snapshot_path_for_id_uses_day_folder(self) -> None:
        captured_at = datetime(2026, 6, 13, 17, 46, 27)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            day = root / "2026-06-13"
            day.mkdir()
            path = day / "axis_2026-06-13_17-46-27.jpg"
            path.write_bytes(b"\xff\xd8test")

            found = self.main.axis_snapshot_path_for_id("20260613174627", root)

        self.assertIsNotNone(found)
        found_at, found_path = found
        self.assertEqual(found_at, captured_at)
        self.assertEqual(found_path.name, "axis_2026-06-13_17-46-27.jpg")
