"""Forecast calendar; no runtime resources are created on import."""

from datetime import date
from datetime import timedelta
from functools import lru_cache
import calendar


@lru_cache(maxsize=64)
def easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


@lru_cache(maxsize=4096)
def norwegian_holiday_name(day: date) -> str:
    easter = easter_sunday(day.year)
    holidays = {
        date(day.year, 1, 1): "Nyttårsdag",
        easter - timedelta(days=3): "Skjærtorsdag",
        easter - timedelta(days=2): "Langfredag",
        easter: "1. påskedag",
        easter + timedelta(days=1): "2. påskedag",
        date(day.year, 5, 1): "Arbeidernes dag",
        date(day.year, 5, 17): "17. mai",
        easter + timedelta(days=39): "Kristi himmelfartsdag",
        easter + timedelta(days=49): "1. pinsedag",
        easter + timedelta(days=50): "2. pinsedag",
        date(day.year, 12, 25): "1. juledag",
        date(day.year, 12, 26): "2. juledag",
    }
    return holidays.get(day, "")


def month_distance(a: int, b: int) -> int:
    raw = abs(a - b)
    return min(raw, 12 - raw)


def iter_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def month_end(day: date) -> date:
    return date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])
