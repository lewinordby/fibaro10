import os
import unittest
from datetime import datetime

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

from online_dashboard.app import main as online_main  # noqa: E402


class OnlineDashboardSolingTests(unittest.TestCase):
    def test_count_performance_uses_count_comparisons_and_supporting_stats(self) -> None:
        html = online_main.render_count_performance(
            modifier="sun",
            label="Solinger så langt i dag",
            current_count=20,
            updated_text="Oppdatert kl 14:25",
            yesterday_same_time=18,
            yesterday_total=27,
            last_week_same_time=25,
            last_week_total=31,
            href="/soling",
            stats=[("Soltid", "6,7 t", "20 min i snitt"), ("Omsetning", "4 060 kr", "203 kr i snitt")],
        )

        self.assertIn("detail-performance-sun", html)
        self.assertIn("Solinger så langt i dag", html)
        self.assertIn("+2 stk", html)
        self.assertIn("-5 stk", html)
        self.assertIn("7 igjen til hele gårsdagen", html)
        self.assertIn("Soltid", html)
        self.assertIn("Omsetning", html)
        self.assertEqual(html.count('class="dashboard-performance-stat"'), 2)
        self.assertIn('<span>Soltid</span><strong>6,7 t</strong><small>20 min i snitt</small>', html)

    def test_room_display_name_does_not_duplicate_prefix(self) -> None:
        self.assertEqual(online_main.room_display_name("Rom 6 Super+"), "Rom 6 Super+")
        self.assertEqual(online_main.room_display_name("6 Super+"), "Rom 6 Super+")
        self.assertEqual(online_main.room_display_name(None), "")

    def test_today_session_list_shows_clock_without_date(self) -> None:
        html = online_main.render_today_soling_list(
            [
                {
                    "started_at": datetime(2026, 7, 20, 14, 25),
                    "room": "Rom 4",
                    "duration_minutes": 20,
                    "paid_amount_kr": 210,
                }
            ],
            can_view_money=True,
        )

        self.assertIn("kl. 14:25", html)
        self.assertNotIn("20.07", html)
        self.assertIn("Rom 4", html)
        self.assertIn("20 min", html)


if __name__ == "__main__":
    unittest.main()
