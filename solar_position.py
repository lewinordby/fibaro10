from datetime import datetime, timezone
from math import asin, atan2, cos, degrees, pi, radians, sin
from zoneinfo import ZoneInfo


DEFAULT_LOCAL_TZ = ZoneInfo("Europe/Oslo")


def _aware_local_time(value: datetime, local_tz=DEFAULT_LOCAL_TZ) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=local_tz)
    return value.astimezone(local_tz)


def _normalize_radians(value: float) -> float:
    while value < -pi:
        value += 2 * pi
    while value > pi:
        value -= 2 * pi
    return value


def solar_elevation_degrees(
    moment: datetime,
    latitude: float,
    longitude: float,
    local_tz=DEFAULT_LOCAL_TZ,
) -> float:
    """Approximate solar elevation above the horizon in degrees.

    The calculation uses the NOAA-style solar position approximation and is
    sufficiently accurate for charting daily sun height against lux samples.
    Positive longitude is east.
    """
    local_time = _aware_local_time(moment, local_tz)
    utc_time = local_time.astimezone(timezone.utc)
    julian_day = utc_time.timestamp() / 86400.0 + 2440587.5
    days_since_j2000 = julian_day - 2451545.0

    mean_longitude = (280.46 + 0.9856474 * days_since_j2000) % 360.0
    mean_anomaly = radians((357.528 + 0.9856003 * days_since_j2000) % 360.0)
    ecliptic_longitude = radians(
        (mean_longitude + 1.915 * sin(mean_anomaly) + 0.020 * sin(2 * mean_anomaly)) % 360.0
    )
    obliquity = radians(23.439 - 0.0000004 * days_since_j2000)

    right_ascension = atan2(cos(obliquity) * sin(ecliptic_longitude), cos(ecliptic_longitude))
    declination = asin(sin(obliquity) * sin(ecliptic_longitude))

    greenwich_sidereal_time = (280.46061837 + 360.98564736629 * (julian_day - 2451545.0)) % 360.0
    local_sidereal_time = radians((greenwich_sidereal_time + longitude) % 360.0)
    hour_angle = _normalize_radians(local_sidereal_time - right_ascension)

    latitude_rad = radians(latitude)
    elevation = asin(
        sin(latitude_rad) * sin(declination)
        + cos(latitude_rad) * cos(declination) * cos(hour_angle)
    )
    return degrees(elevation)
