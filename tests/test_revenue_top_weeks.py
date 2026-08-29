from datetime import date, timedelta
import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

import main


def sun_day(stat_day: date, paid: float, count: int) -> dict:
    return {
        "period": stat_day.isoformat(),
        "period_label": stat_day.strftime("%d.%m.%Y"),
        "totalt_inntjent_kr": paid,
        "totalt_antall_solinger": count,
    }


def parking_day(stat_day: date, paid: float, count: int) -> dict:
    return {
        "period": stat_day.isoformat(),
        "period_label": stat_day.strftime("%d.%m.%Y"),
        "paid": paid,
        "sessions": count,
    }


class RevenueTopWeeksTests(unittest.TestCase):
    def test_combines_sun_and_parking_by_iso_week_and_ranks_revenue(self) -> None:
        sun = {
            "daily": [
                sun_day(date(2026, 1, 5), 100, 2),
                sun_day(date(2026, 1, 7), 200, 3),
                sun_day(date(2026, 1, 12), 500, 5),
            ],
        }
        parking = {
            "daily": [
                parking_day(date(2026, 1, 5), 50, 1),
                parking_day(date(2026, 1, 7), 130, 2),
                parking_day(date(2026, 1, 12), 100, 1),
            ],
        }

        summaries = main.combine_business_summaries(sun, parking)

        self.assertEqual([row["period"] for row in summaries["weekly"]], ["2026-W03", "2026-W02"])
        self.assertEqual([row["period"] for row in summaries["top_weeks"]], ["2026-W03", "2026-W02"])
        best = summaries["top_weeks"][0]
        self.assertEqual(best["period_label"], "Uke 3, 2026 (12.01-18.01.2026)")
        self.assertEqual(best["total_paid"], 600)
        self.assertEqual(best["sun_paid"], 500)
        self.assertEqual(best["parking_paid"], 100)
        self.assertEqual(best["sun_count"], 5)
        self.assertEqual(best["parking_count"], 1)

    def test_top_weeks_are_limited_to_twenty(self) -> None:
        first_monday = date(2025, 1, 6)
        sun = {
            "daily": [sun_day(first_monday + timedelta(weeks=index), index + 1, 1) for index in range(25)],
        }

        summaries = main.combine_business_summaries(sun, {"daily": []})

        self.assertEqual(len(summaries["top_weeks"]), 20)
        self.assertEqual(summaries["top_weeks"][0]["total_paid"], 25)
        self.assertEqual(len(summaries["weekly"]), 25)

    def test_period_rank_uses_all_completed_periods(self) -> None:
        rank = main.revenue_period_rank_summary(
            [
                {"period": "2026-W30", "total_paid": 1200},
                {"period": "2026-W31", "total_paid": 800},
                {"period": "2026-W32", "total_paid": 1000},
                {"period": "2026-W33", "total_paid": 9999},
            ],
            900,
            "2026-W33",
            "uker",
        )

        self.assertIsNotNone(rank)
        self.assertEqual(rank["rank"], 3)
        self.assertEqual(rank["label"], "3. beste")
        self.assertEqual(rank["totalPeriods"], 4)
        self.assertEqual(rank["basis"], "Rangert mot historiske hele uker")

    def test_day_rank_keeps_legacy_day_count(self) -> None:
        rank = main.revenue_day_rank_summary(
            {
                "daily": [
                    {"period": "2026-08-27", "total_paid": 1000},
                    {"period": "2026-08-28", "total_paid": 500},
                    {"period": "2026-08-29", "total_paid": 9999},
                ]
            },
            750,
            date(2026, 8, 29),
        )

        self.assertIsNotNone(rank)
        self.assertEqual(rank["rank"], 2)
        self.assertEqual(rank["totalDays"], 3)

    def test_revenue_overview_places_weeks_between_days_and_months(self) -> None:
        tables = main.api_revenue_overview_tables(
            {
                "top_days": [],
                "top_weeks": [
                    {
                        "period": "2026-W03",
                        "period_label": "Uke 3, 2026 (12.01-18.01.2026)",
                        "total_paid": 600,
                        "sun_paid": 500,
                        "parking_paid": 100,
                        "sun_count": 5,
                        "parking_count": 1,
                    }
                ],
                "top_months": [],
            }
        )

        self.assertEqual([table["title"] for table in tables], [
            "Topp dager omsetning",
            "Topp uker omsetning",
            "Topp måneder omsetning",
        ])
        self.assertEqual(tables[1]["rows"][0]["total_paid"], 600)


if __name__ == "__main__":
    unittest.main()
