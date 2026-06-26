from datetime import datetime
import unittest

from time_formatting import format_source_datetime


class TimeFormattingTests(unittest.TestCase):
    def test_source_datetime_keeps_local_naive_time(self):
        value = datetime(2026, 6, 26, 15, 52, 0)

        self.assertEqual(format_source_datetime(value), "26.06.2026 15:52:00")


if __name__ == "__main__":
    unittest.main()
