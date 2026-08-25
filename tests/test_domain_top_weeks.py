from datetime import date
import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

import main


class DomainTopWeeksTests(unittest.TestCase):
    def test_parking_weeks_are_aggregated_and_rankable(self) -> None:
        rows = [
            {"period": "2026-01-05", "paid": 100, "sessions": 2, "minutes": 80, "vehicles": 2},
            {"period": "2026-01-07", "paid": 250, "sessions": 4, "minutes": 160, "vehicles": 4},
            {"period": "2026-01-12", "paid": 500, "sessions": 5, "minutes": 210, "vehicles": 5},
        ]

        weeks = main.parking_weekly_items(rows)
        ranked = sorted(weeks, key=lambda item: (item["paid"], item["sessions"]), reverse=True)

        self.assertEqual([item["period"] for item in ranked], ["2026-W03", "2026-W02"])
        self.assertEqual(ranked[1]["period_label"], "Uke 2, 2026 (05.01-11.01.2026)")
        self.assertEqual(ranked[1]["paid"], 350)
        self.assertEqual(ranked[1]["sessions"], 6)
        self.assertEqual(ranked[1]["minutes"], 240)
        self.assertEqual(ranked[1]["days_count"], 2)

    def test_sun_weeks_keep_revenue_count_and_duration(self) -> None:
        rows = [
            {
                "period": "2026-01-05",
                "totalt_inntjent_kr": 200,
                "totalt_antall_solinger": 2,
                "total_soletid_minutter": 40,
                "days_count": 1,
                "rooms_count": 2,
            },
            {
                "period": "2026-01-06",
                "totalt_inntjent_kr": 450,
                "totalt_antall_solinger": 3,
                "total_soletid_minutter": 75,
                "days_count": 1,
                "rooms_count": 3,
            },
        ]

        week = main.sun2_weekly_items(rows)[0]

        self.assertEqual(week["period"], "2026-W02")
        self.assertEqual(week["totalt_inntjent_kr"], 650)
        self.assertEqual(week["totalt_antall_solinger"], 5)
        self.assertEqual(week["total_soletid_timer"], 115 / 60)
        self.assertEqual(week["days_count"], 2)
        self.assertEqual(week["rooms_count"], 3)

    def test_overview_tables_include_both_week_rankings(self) -> None:
        parking_tables = main.api_parking_overview_tables(
            {"top_weeks": [], "top_weeks_by_count": []}, []
        )
        sun_tables = main.api_sun2_overview_tables(
            {"top_weeks": [], "top_weeks_by_count": []}, [], []
        )

        self.assertIn("Topp uker omsetning", [table["title"] for table in parking_tables])
        self.assertIn("Topp uker antall", [table["title"] for table in parking_tables])
        self.assertIn("Topp uker omsetning", [table["title"] for table in sun_tables])
        self.assertIn("Topp uker antall", [table["title"] for table in sun_tables])

    def test_table_meta_can_select_the_link_column(self) -> None:
        table = main.api_table(
            "Parkeringer",
            ["start_time", "car_license_number"],
            [{"start_time": "2026-08-24T10:00:00", "car_license_number": "AB12345"}],
            meta={"rowLinkColumn": "car_license_number"},
        )

        self.assertEqual(table["meta"]["rowLinkColumn"], "car_license_number")

    def test_parking_overview_links_the_registration_number(self) -> None:
        tables = main.api_parking_overview_tables({}, [])
        latest = next(table for table in tables if table["title"] == "Siste parkeringer")

        self.assertEqual(latest["meta"]["rowLinkColumn"], "car_license_number")


if __name__ == "__main__":
    unittest.main()
