from datetime import date, datetime
import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")
import main


class _MappingRows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def one(self):
        return self.rows


class _Result:
    def __init__(self, *, mappings=None, rows=None):
        self._mappings = mappings
        self._rows = rows

    def mappings(self):
        return _MappingRows(self._mappings)

    def all(self):
        return self._rows


class _Session:
    def __init__(self, *results):
        self.results = list(results)
        self.execute_count = 0

    async def execute(self, _statement):
        self.execute_count += 1
        return self.results.pop(0)


class OverviewBatchQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_sun_periods_use_imported_day_and_fill_only_missing_days(self):
        first = date(2026, 8, 1)
        second = date(2026, 8, 2)
        session = _Session(
            _Result(
                mappings=[
                    {
                        "stat_date": first,
                        "totalt_antall_solinger": 10,
                        "total_soletid_minutter": 100,
                        "totalt_inntjent_kr": 1_000,
                        "rooms": 2,
                    }
                ]
            ),
            _Result(
                mappings=[
                    {"stat_date": first, "sessions": 99, "minutes": 999, "paid": 9_999},
                    {"stat_date": second, "sessions": 3, "minutes": 30, "paid": 300},
                ]
            ),
            _Result(rows=[(first, 9), (second, 1), (second, 2), (second, 3)]),
        )

        snapshots = await main.sun2_period_snapshots(
            session,
            {
                "both": (first, date(2026, 8, 3)),
                "imported": (first, second),
            },
        )

        self.assertEqual(session.execute_count, 3)
        self.assertEqual(snapshots["both"].sessions, 13)
        self.assertEqual(snapshots["both"].minutes, 130)
        self.assertEqual(snapshots["both"].paid, 1_300)
        self.assertEqual(snapshots["both"].rooms, 3)
        self.assertEqual(snapshots["imported"].sessions, 10)
        self.assertEqual(snapshots["imported"].paid, 1_000)

    async def test_datetime_batches_return_all_requested_windows_in_one_query(self):
        session = _Session(
            _Result(
                mappings={
                    "today_sessions": 4,
                    "today_minutes": 60,
                    "today_paid": 800,
                    "today_rooms": 3,
                    "week_sessions": 15,
                    "week_minutes": 210,
                    "week_paid": 2_600,
                    "week_rooms": 7,
                }
            )
        )
        start = datetime(2026, 8, 3)

        snapshots = await main.sun2_datetime_snapshots(
            session,
            {
                "today": (start, datetime(2026, 8, 4)),
                "week": (start, datetime(2026, 8, 10)),
            },
        )

        self.assertEqual(session.execute_count, 1)
        self.assertEqual(snapshots["today"].paid, 800)
        self.assertEqual(snapshots["week"].sessions, 15)
        self.assertEqual(snapshots["week"].rooms, 7)

    async def test_parking_batches_return_all_requested_windows_in_one_query(self):
        session = _Session(
            _Result(mappings={"today_sessions": 12, "today_paid": 1_250, "year_sessions": 900, "year_paid": 92_000})
        )
        start = datetime(2026, 8, 3)

        snapshots = await main.parking_datetime_snapshots(
            session,
            {
                "today": (start, datetime(2026, 8, 4)),
                "year": (datetime(2026, 1, 1), datetime(2027, 1, 1)),
            },
        )

        self.assertEqual(session.execute_count, 1)
        self.assertEqual(snapshots["today"].sessions, 12)
        self.assertEqual(snapshots["year"].paid, 92_000)


class EnergyChartOptimizationTests(unittest.TestCase):
    def test_cumulative_total_is_calculated_before_chart_decimation(self):
        rows = [
            SimpleNamespace(bucket_start=datetime(2026, 8, 3, 0, minute), inntak_delta_kwh=value)
            for minute, value in enumerate((1.0, 2.0, 3.0, 4.0))
        ]

        points = main.decimate_rows(main.cumulative_energy_points(rows, "inntak_delta_kwh"), 2)

        self.assertEqual(points[-1][1], 10.0)


if __name__ == "__main__":
    unittest.main()
