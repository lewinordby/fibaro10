import os
import unittest
from datetime import datetime

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

from online_dashboard.app import main as online_main  # noqa: E402


class OnlineDashboardParkingTests(unittest.TestCase):
    def test_today_parking_list_shows_clock_without_date(self) -> None:
        html = online_main.render_parking_vehicle_list(
            [
                {
                    "start_time": datetime(2026, 7, 20, 14, 25),
                    "car_license_number": "AB12345",
                    "status": "Ongoing",
                    "merke": "Volvo",
                    "modell": "XC60",
                    "typebetegnelse": "T8",
                    "farge": "Svart",
                    "forstegangsregistrert_norge": datetime(2022, 3, 1),
                    "parking_time_min": 45,
                    "fee_inc_vat": 84,
                    "previous_parking_count": 12,
                }
            ],
            can_view_money=True,
        )

        self.assertIn("14:25", html)
        self.assertNotIn("20.07", html)
        self.assertIn("AB12345", html)
        self.assertIn("2022 Volvo XC60 T8 - Svart", html)
        self.assertIn("84 kr", html)
        self.assertIn("45 min", html)
        self.assertIn("Parkert 12 ganger f\u00f8r", html)
        self.assertIn("P\u00e5g\u00e5r", html)
        self.assertNotIn("Ongoing", html)
        self.assertIn('class="parking-status is-active"', html)

    def test_easypark_statuses_are_presented_in_norwegian(self) -> None:
        self.assertEqual(online_main.parking_status_label("Ongoing"), "P\u00e5g\u00e5r")
        self.assertEqual(online_main.parking_status_label("Ended"), "Avsluttet")
        self.assertEqual(online_main.parking_status_label("Ukjent"), "Ukjent")

    def test_active_parking_is_always_rendered_first(self) -> None:
        html = online_main.render_parking_vehicle_list(
            [
                {
                    "start_time": datetime(2026, 7, 20, 15, 10),
                    "car_license_number": "AVSLUTTET",
                    "status": "Ended",
                },
                {
                    "start_time": datetime(2026, 7, 20, 14, 5),
                    "car_license_number": "PAGAAR",
                    "status": "Ongoing",
                },
            ],
            can_view_money=False,
        )

        self.assertLess(html.index("PAGAAR"), html.index("AVSLUTTET"))

    def test_previous_parking_count_has_clear_singular_and_empty_labels(self) -> None:
        self.assertEqual(online_main.parking_previous_count_label(0), "F\u00f8rste parkering")
        self.assertEqual(online_main.parking_previous_count_label(1), "Parkert 1 gang f\u00f8r")
        self.assertEqual(online_main.parking_previous_count_label(1234), "Parkert 1 234 ganger f\u00f8r")

    def test_today_parking_list_hides_money_for_viewer(self) -> None:
        html = online_main.render_parking_vehicle_list(
            [
                {
                    "start_time": datetime(2026, 7, 20, 9, 5),
                    "car_license_number": "CD67890",
                    "parking_time_min": 30,
                    "fee_inc_vat": 60,
                }
            ],
            can_view_money=False,
        )

        self.assertIn("09:05", html)
        self.assertIn("30 min", html)
        self.assertNotIn("60 kr", html)


if __name__ == "__main__":
    unittest.main()
