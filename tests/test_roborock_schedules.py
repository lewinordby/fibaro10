from datetime import datetime
from types import SimpleNamespace

from roborock_domain import (
    LOCAL_TZ,
    roborock_cron_weekdays,
    roborock_next_schedule_at,
    roborock_next_schedule_score,
    roborock_next_schedule_text,
)


def schedule(cron: str):
    return SimpleNamespace(cron=cron)


def test_weekday_parser_supports_names_numbers_lists_and_ranges():
    assert roborock_cron_weekdays("?") is None
    assert roborock_cron_weekdays("MON,WED,5") == {0, 2, 4}
    assert roborock_cron_weekdays("1-5") == {0, 1, 2, 3, 4}
    assert roborock_cron_weekdays("6-1") == {5, 6, 0}
    assert roborock_cron_weekdays("BAD") == set()


def test_next_schedule_respects_weekday_instead_of_only_clock_time():
    monday = datetime(2026, 8, 10, 22, 0, tzinfo=LOCAL_TZ)

    next_at = roborock_next_schedule_at(schedule("30 23 * * 3"), monday)

    assert next_at == datetime(2026, 8, 12, 23, 30, tzinfo=LOCAL_TZ)
    assert roborock_next_schedule_text(schedule("30 23 * * 3"), monday) == "onsdag kl. 23:30"


def test_daily_schedule_rolls_to_tomorrow_after_the_time_has_passed():
    now = datetime(2026, 8, 10, 23, 31, tzinfo=LOCAL_TZ)

    next_at = roborock_next_schedule_at(schedule("30 23 * * ?"), now)

    assert next_at == datetime(2026, 8, 11, 23, 30, tzinfo=LOCAL_TZ)
    assert roborock_next_schedule_text(schedule("30 23 * * ?"), now) == "I morgen kl. 23:30"
    assert roborock_next_schedule_score(schedule("30 23 * * ?"), now) == 23 * 60 * 60 + 59 * 60


def test_invalid_schedule_is_sorted_after_valid_schedules():
    now = datetime(2026, 8, 10, 10, 0, tzinfo=LOCAL_TZ)

    assert roborock_next_schedule_at(schedule("99 25 * * ?"), now) is None
    assert roborock_next_schedule_score(schedule("99 25 * * ?"), now) == 8 * 24 * 60 * 60
