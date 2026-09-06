"""Civil-time coverage without inventing the fold lost by legacy local timestamps."""

from collections import Counter
from datetime import datetime, time, timedelta, timezone
from math import isfinite
from zoneinfo import ZoneInfo


def local_hour_occurrences(day):
    zone = ZoneInfo("Europe/Oslo")
    cursor = datetime.combine(day, time.min, zone).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(timezone.utc)
    hours = Counter()
    while cursor < end:
        hours[cursor.astimezone(zone).hour] += 1
        cursor += timedelta(hours=1)
    return dict(sorted(hours.items()))


def valid_consumption(value):
    try:
        number = float(value)
        return number if isfinite(number) and number >= 0 else None
    except (TypeError, ValueError):
        return None
