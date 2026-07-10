import unittest
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

import main


class ParkingSunLinkLogicTests(unittest.TestCase):
    def test_single_parking_match_waits_for_more_evidence(self) -> None:
        assessment = main.parking_sun_link_assessment(
            main.PARKING_SUN_LINK_PENDING,
            54.0,
            min_matches=2,
            parking_match_count=1,
            plate_candidate_count=1,
            sun2_candidate_count=1,
            competitor_matches_count=0,
        )

        self.assertIn("Venter", assessment)
        self.assertIn("1/2", assessment)

    def test_multiple_sun_sessions_on_one_parking_still_stays_low_confidence(self) -> None:
        probability = main.parking_sun_link_probability(
            matches_count=3,
            avg_delta_minutes=0.4,
            min_matches=2,
            parking_match_count=1,
            match_days_count=1,
            plate_candidate_count=1,
            sun2_candidate_count=1,
            competitor_matches_count=0,
        )

        self.assertLessEqual(probability, 55.0)


if __name__ == "__main__":
    unittest.main()
