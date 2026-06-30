from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from time_formatting import (
    LOCAL_TZ,
    format_source_datetime,
    local_naive_to_utc_naive,
    normalize_local_naive,
    sample_bucket,
    utc_naive_to_local_naive,
)


class TimeFormattingTests(unittest.TestCase):
    def test_source_datetime_keeps_local_naive_time(self):
        value = datetime(2026, 6, 26, 15, 52, 0)

        self.assertEqual(format_source_datetime(value), "26.06.2026 15:52:00")

    def test_normalize_local_naive_converts_aware_timestamp(self):
        value = datetime(2026, 6, 26, 13, 52, 0, tzinfo=ZoneInfo("UTC"))

        self.assertEqual(normalize_local_naive(value), datetime(2026, 6, 26, 15, 52, 0))

    def test_utc_and_local_naive_conversion_roundtrip(self):
        local_value = datetime(2026, 6, 26, 15, 52, 0)

        utc_value = local_naive_to_utc_naive(local_value)

        self.assertEqual(utc_value, datetime(2026, 6, 26, 13, 52, 0))
        self.assertEqual(utc_naive_to_local_naive(utc_value), local_value)

    def test_sample_bucket_rounds_down_to_five_minutes(self):
        value = datetime(2026, 6, 26, 15, 59, 41, 123456, tzinfo=LOCAL_TZ)

        self.assertEqual(sample_bucket(value), datetime(2026, 6, 26, 15, 55, 0, tzinfo=LOCAL_TZ))


if __name__ == "__main__":
    unittest.main()
