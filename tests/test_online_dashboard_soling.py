import os
import unittest
from datetime import datetime

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

from online_dashboard.app import main as online_main  # noqa: E402


class OnlineDashboardSolingTests(unittest.TestCase):
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
