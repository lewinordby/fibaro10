from datetime import datetime
import unittest

from solar_position import solar_elevation_degrees


LILLETORGET_LAT = 61.1153
LILLETORGET_LON = 10.4662


class SolarPositionTests(unittest.TestCase):
    def test_summer_solstice_peak_is_high_for_lillehammer(self) -> None:
        elevation = solar_elevation_degrees(datetime(2026, 6, 21, 13, 20), LILLETORGET_LAT, LILLETORGET_LON)

        self.assertGreater(elevation, 51)
        self.assertLess(elevation, 54)

    def test_winter_solstice_noon_is_low_for_lillehammer(self) -> None:
        elevation = solar_elevation_degrees(datetime(2026, 12, 21, 12, 0), LILLETORGET_LAT, LILLETORGET_LON)

        self.assertGreater(elevation, 4)
        self.assertLess(elevation, 7)

    def test_summer_midnight_is_below_horizon(self) -> None:
        elevation = solar_elevation_degrees(datetime(2026, 6, 21, 0, 0), LILLETORGET_LAT, LILLETORGET_LON)

        self.assertLess(elevation, 0)


if __name__ == "__main__":
    unittest.main()
