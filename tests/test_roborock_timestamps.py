from datetime import datetime

from time_formatting import utc_naive_to_local_naive


def test_roborock_summer_job_is_converted_from_utc_to_oslo_time():
    assert utc_naive_to_local_naive(datetime(2026, 8, 12, 21, 30)) == datetime(2026, 8, 12, 23, 30)


def test_roborock_winter_job_is_converted_from_utc_to_oslo_time():
    assert utc_naive_to_local_naive(datetime(2026, 1, 12, 22, 30)) == datetime(2026, 1, 12, 23, 30)
