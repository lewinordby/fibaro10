from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo


LOCAL_TZ = ZoneInfo("Europe/Oslo")


def format_local_datetime(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    if isinstance(value, (int, float)):
        value = datetime.utcfromtimestamp(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(LOCAL_TZ).strftime("%d.%m.%Y %H:%M:%S")


def format_local_time(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    if isinstance(value, (int, float)):
        value = datetime.utcfromtimestamp(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(LOCAL_TZ).strftime("%H:%M")


def format_source_datetime(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value)
    if value.tzinfo is not None:
        value = value.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return value.strftime("%d.%m.%Y %H:%M:%S")


def format_source_time(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value)
    if value.tzinfo is not None:
        value = value.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return value.strftime("%H:%M")


def format_source_datetime_short(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value)
    if value.tzinfo is not None:
        value = value.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return value.strftime("%d.%m.%Y %H:%M")
