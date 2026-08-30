"""Forecast models; no runtime resources are created on import."""

from datetime import date
from datetime import datetime
from datetime import time
from fibaro_core.models import ParkingSession
from fibaro_core.models import Sun2TanningSession
from fibaro_core.services.forecasts.calendar import iter_dates
from fibaro_core.services.forecasts.calendar import month_distance
from fibaro_core.services.forecasts.calendar import norwegian_holiday_name
from sqlalchemy import Date
from sqlalchemy import case
from sqlalchemy import cast
from sqlalchemy import func
from sqlalchemy import select
from typing import Any
from typing import Dict
from value_parsing import float_or_zero


SUN2_FORECAST_SEASON_WEIGHTS = (1.75, 1.35, 1.05, 0.82)


PARKING_FORECAST_SEASON_WEIGHTS = (1.85, 1.38, 1.05, 0.78)


def weighted_average(values: list[tuple[float, float]]) -> tuple[float, float, int]:
    weighted_sum = sum(value * weight for value, weight in values)
    weight_sum = sum(weight for _, weight in values)
    if weight_sum <= 0:
        return 0.0, 0.0, 0
    return weighted_sum / weight_sum, weight_sum, len(values)


def sun2_history_weight(target_day: date, historical_day: date, today: date) -> float:
    return sun2_history_weight_precomputed(
        target_day,
        historical_day,
        today,
        bool(norwegian_holiday_name(target_day)),
    )


def sun2_history_weight_precomputed(target_day: date, historical_day: date, today: date, target_holiday: bool) -> float:
    if historical_day >= today:
        return 0.0
    age_years = max(0.0, (today - historical_day).days / 365.25)
    recency = 0.72 ** age_years
    month_diff = month_distance(target_day.month, historical_day.month)
    season = {0: 1.75, 1: 1.35, 2: 1.05, 3: 0.82}.get(month_diff, 0.55)
    weekday = 1.35 if target_day.weekday() == historical_day.weekday() else 0.82
    history_holiday = bool(norwegian_holiday_name(historical_day))
    holiday = 1.8 if target_holiday and history_holiday else 1.0 if target_holiday == history_holiday else 0.55
    return max(0.0, recency * season * weekday * holiday)


def sun2_daily_model(target_day: date, history: Dict[date, Dict[str, float]], today: date) -> Dict[str, Any]:
    target_holiday_name = norwegian_holiday_name(target_day)
    target_holiday = bool(target_holiday_name)
    sessions_sum = 0.0
    paid_sum = 0.0
    minutes_sum = 0.0
    weight_sum = 0.0
    comparable_days = 0
    for historical_day, item in history.items():
        weight = sun2_history_weight_precomputed(target_day, historical_day, today, target_holiday)
        if weight <= 0:
            continue
        sessions_sum += float_or_zero(item.get("sessions")) * weight
        paid_sum += float_or_zero(item.get("paid")) * weight
        minutes_sum += float_or_zero(item.get("minutes")) * weight
        weight_sum += weight
        comparable_days += 1
    if weight_sum <= 0:
        sessions = paid = minutes = 0.0
    else:
        sessions = sessions_sum / weight_sum
        paid = paid_sum / weight_sum
        minutes = minutes_sum / weight_sum
    return {
        "day": target_day,
        "sessions": sessions,
        "paid": paid,
        "minutes": minutes,
        "weight_sum": weight_sum,
        "comparable_days": comparable_days,
        "holiday": target_holiday_name,
    }


def sun2_model_history_features(history: Dict[date, Dict[str, float]], today: date) -> list[tuple[int, int, bool, float, float, float, float]]:
    features = []
    for historical_day, item in history.items():
        if historical_day >= today:
            continue
        age_years = max(0.0, (today - historical_day).days / 365.25)
        features.append(
            (
                historical_day.month,
                historical_day.weekday(),
                bool(norwegian_holiday_name(historical_day)),
                0.72 ** age_years,
                float_or_zero(item.get("sessions")),
                float_or_zero(item.get("paid")),
                float_or_zero(item.get("minutes")),
            )
        )
    return features


def sun2_daily_model_from_features(
    target_day: date,
    features: list[tuple[int, int, bool, float, float, float, float]],
) -> Dict[str, Any]:
    target_holiday_name = norwegian_holiday_name(target_day)
    target_holiday = bool(target_holiday_name)
    target_month = target_day.month
    target_weekday = target_day.weekday()
    sessions_sum = 0.0
    paid_sum = 0.0
    minutes_sum = 0.0
    weight_sum = 0.0
    comparable_days = 0
    for history_month, history_weekday, history_holiday, recency, sessions_value, paid_value, minutes_value in features:
        raw_month_diff = abs(target_month - history_month)
        month_diff = min(raw_month_diff, 12 - raw_month_diff)
        season = SUN2_FORECAST_SEASON_WEIGHTS[month_diff] if month_diff < len(SUN2_FORECAST_SEASON_WEIGHTS) else 0.55
        weekday = 1.35 if target_weekday == history_weekday else 0.82
        holiday = 1.8 if target_holiday and history_holiday else 1.0 if target_holiday == history_holiday else 0.55
        weight = recency * season * weekday * holiday
        if weight <= 0:
            continue
        sessions_sum += sessions_value * weight
        paid_sum += paid_value * weight
        minutes_sum += minutes_value * weight
        weight_sum += weight
        comparable_days += 1
    if weight_sum <= 0:
        sessions = paid = minutes = 0.0
    else:
        sessions = sessions_sum / weight_sum
        paid = paid_sum / weight_sum
        minutes = minutes_sum / weight_sum
    return {
        "day": target_day,
        "sessions": sessions,
        "paid": paid,
        "minutes": minutes,
        "weight_sum": weight_sum,
        "comparable_days": comparable_days,
        "holiday": target_holiday_name,
    }


def sun2_period_actual(history: Dict[date, Dict[str, float]], start: date, end: date) -> Dict[str, float]:
    total = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0}
    for day in iter_dates(start, end):
        item = history.get(day) or {}
        total["sessions"] += float_or_zero(item.get("sessions"))
        total["paid"] += float_or_zero(item.get("paid"))
        total["minutes"] += float_or_zero(item.get("minutes"))
    return total


def sun2_apply_tempo(actual: float, expected: float, minimum: float = 0.62, maximum: float = 1.65) -> float:
    if expected <= 0:
        return 1.0
    return max(minimum, min(maximum, actual / expected))


def parking_apply_period_tempo(actual: float, expected: float, progress: float) -> float:
    if expected <= 0:
        return 1.0
    progress = max(0.0, min(1.0, progress))
    observed = float_or_zero(actual) / expected
    confidence = 0.12 + 0.78 * (progress ** 0.85)
    blended = 1.0 + (observed - 1.0) * confidence
    if progress < 0.18:
        minimum, maximum = 0.82, 1.25
    elif progress < 0.42:
        minimum, maximum = 0.70, 1.40
    elif progress < 0.72:
        minimum, maximum = 0.58, 1.58
    else:
        minimum, maximum = 0.45, 1.78
    return max(minimum, min(maximum, blended))


def opening_day_fraction(minute_of_day: int, opening_minute: int = 7 * 60, closing_minute: int = 23 * 60, power: float = 0.92) -> float:
    if minute_of_day <= opening_minute:
        return 0.0
    if minute_of_day >= closing_minute:
        return 1.0
    linear_fraction = (minute_of_day - opening_minute) / (closing_minute - opening_minute)
    return max(0.0, min(1.0, linear_fraction ** power))


def weighted_intraday_fraction(
    target_day: date,
    today: date,
    rows: list[tuple[date, float, float]],
    weight_fn,
    fallback_fraction: float,
    min_weighted_total: float = 25.0,
) -> float:
    elapsed_weighted = 0.0
    total_weighted = 0.0
    for historical_day, elapsed_count, total_count in rows:
        total_count = float_or_zero(total_count)
        if total_count <= 0:
            continue
        weight = weight_fn(target_day, historical_day, today)
        if weight <= 0:
            continue
        elapsed_weighted += float_or_zero(elapsed_count) * weight
        total_weighted += total_count * weight
    if total_weighted < min_weighted_total:
        return fallback_fraction
    return max(0.0, min(1.0, elapsed_weighted / total_weighted))


async def sun2_historical_day_fraction(
    session,
    target_day: date,
    today: date,
    history: Dict[date, Dict[str, float]],
    minute_of_day: int,
    fallback_fraction: float,
) -> float:
    if fallback_fraction <= 0.0 or fallback_fraction >= 1.0 or not history:
        return fallback_fraction
    first_day = min(history)
    minute_expr = func.extract("hour", Sun2TanningSession.started_at) * 60 + func.extract("minute", Sun2TanningSession.started_at)
    result = await session.execute(
        select(
            Sun2TanningSession.stat_date,
            func.coalesce(func.sum(case((minute_expr <= minute_of_day, 1), else_=0)), 0),
            func.count(Sun2TanningSession.id),
        )
        .where(Sun2TanningSession.stat_date >= first_day)
        .where(Sun2TanningSession.stat_date < today)
        .group_by(Sun2TanningSession.stat_date)
    )
    rows = [(row[0], row[1], row[2]) for row in result.all()]
    return weighted_intraday_fraction(target_day, today, rows, sun2_history_weight, fallback_fraction)


async def parking_historical_day_fraction(
    session,
    target_day: date,
    today: date,
    history: Dict[date, Dict[str, float]],
    minute_of_day: int,
    fallback_fraction: float,
) -> float:
    if fallback_fraction <= 0.0 or fallback_fraction >= 1.0 or not history:
        return fallback_fraction
    first_day = min(history)
    minute_expr = func.extract("hour", ParkingSession.start_time) * 60 + func.extract("minute", ParkingSession.start_time)
    result = await session.execute(
        select(
            cast(ParkingSession.start_time, Date),
            func.coalesce(func.sum(case((minute_expr <= minute_of_day, 1), else_=0)), 0),
            func.count(ParkingSession.id),
        )
        .where(ParkingSession.start_time >= datetime.combine(first_day, time.min))
        .where(ParkingSession.start_time < datetime.combine(today, time.min))
        .group_by(cast(ParkingSession.start_time, Date))
    )
    rows = [(row[0], row[1], row[2]) for row in result.all()]
    return weighted_intraday_fraction(target_day, today, rows, parking_history_weight, fallback_fraction)


def intraday_forecast_value(
    actual: float,
    model: float,
    day_fraction: float,
    minute_of_day: int,
    opening_minute: int,
    minimum_expected_now: float = 3.0,
) -> tuple[float, float]:
    actual = float_or_zero(actual)
    model = float_or_zero(model)
    day_fraction = max(0.01, min(1.0, day_fraction))
    if model <= 0:
        projected = actual / day_fraction if day_fraction > 0 else actual
        return max(actual, projected), 1.0

    expected_now = model * day_fraction
    if minute_of_day <= opening_minute or expected_now < minimum_expected_now:
        return max(actual, model), 1.0

    observed_tempo = actual / expected_now if expected_now > 0 else 1.0
    confidence = max(0.0, min(1.0, (day_fraction - 0.14) / 0.55))
    blended_tempo = 1.0 + (observed_tempo - 1.0) * confidence

    if day_fraction < 0.35:
        min_tempo, max_tempo = (0.78, 1.35)
    elif day_fraction < 0.65:
        min_tempo, max_tempo = (0.58, 1.55)
    else:
        min_tempo, max_tempo = (0.42, 1.75)
    tempo = max(min_tempo, min(max_tempo, blended_tempo))
    return max(actual, model * tempo), tempo


def parking_daily_model(target_day: date, history: Dict[date, Dict[str, float]], today: date) -> Dict[str, Any]:
    target_holiday_name = norwegian_holiday_name(target_day)
    target_holiday = bool(target_holiday_name)
    sessions_sum = 0.0
    paid_sum = 0.0
    minutes_sum = 0.0
    vehicles_sum = 0.0
    weight_sum = 0.0
    comparable_days = 0
    for historical_day, item in history.items():
        weight = parking_history_weight_precomputed(target_day, historical_day, today, target_holiday)
        if weight <= 0:
            continue
        sessions_sum += float_or_zero(item.get("sessions")) * weight
        paid_sum += float_or_zero(item.get("paid")) * weight
        minutes_sum += float_or_zero(item.get("minutes")) * weight
        vehicles_sum += float_or_zero(item.get("vehicles")) * weight
        weight_sum += weight
        comparable_days += 1
    if weight_sum <= 0:
        sessions = paid = minutes = vehicles = 0.0
    else:
        sessions = sessions_sum / weight_sum
        paid = paid_sum / weight_sum
        minutes = minutes_sum / weight_sum
        vehicles = vehicles_sum / weight_sum
    return {
        "day": target_day,
        "sessions": sessions,
        "paid": paid,
        "minutes": minutes,
        "vehicles": vehicles,
        "weight_sum": weight_sum,
        "comparable_days": comparable_days,
        "holiday": target_holiday_name,
    }


def parking_model_history_features(
    history: Dict[date, Dict[str, float]],
    today: date,
) -> list[tuple[int, int, bool, float, float, float, float, float]]:
    features = []
    for historical_day, item in history.items():
        if historical_day >= today:
            continue
        age_years = max(0.0, (today - historical_day).days / 365.25)
        features.append(
            (
                historical_day.month,
                historical_day.weekday(),
                bool(norwegian_holiday_name(historical_day)),
                0.74 ** age_years,
                float_or_zero(item.get("sessions")),
                float_or_zero(item.get("paid")),
                float_or_zero(item.get("minutes")),
                float_or_zero(item.get("vehicles")),
            )
        )
    return features


def parking_daily_model_from_features(
    target_day: date,
    features: list[tuple[int, int, bool, float, float, float, float, float]],
) -> Dict[str, Any]:
    target_holiday_name = norwegian_holiday_name(target_day)
    target_holiday = bool(target_holiday_name)
    target_month = target_day.month
    target_weekday = target_day.weekday()
    target_is_sunday = target_weekday == 6
    sessions_sum = 0.0
    paid_sum = 0.0
    minutes_sum = 0.0
    vehicles_sum = 0.0
    weight_sum = 0.0
    comparable_days = 0
    for history_month, history_weekday, history_holiday, recency, sessions_value, paid_value, minutes_value, vehicles_value in features:
        raw_month_diff = abs(target_month - history_month)
        month_diff = min(raw_month_diff, 12 - raw_month_diff)
        season = PARKING_FORECAST_SEASON_WEIGHTS[month_diff] if month_diff < len(PARKING_FORECAST_SEASON_WEIGHTS) else 0.48
        history_is_sunday = history_weekday == 6
        if target_is_sunday:
            weekday = 3.2 if history_is_sunday else 0.035
        elif history_is_sunday:
            weekday = 0.10
        else:
            weekday = 1.45 if target_weekday == history_weekday else 0.78
        holiday = 1.8 if target_holiday and history_holiday else 1.0 if target_holiday == history_holiday else 0.50
        weight = recency * season * weekday * holiday
        if weight <= 0:
            continue
        sessions_sum += sessions_value * weight
        paid_sum += paid_value * weight
        minutes_sum += minutes_value * weight
        vehicles_sum += vehicles_value * weight
        weight_sum += weight
        comparable_days += 1
    if weight_sum <= 0:
        sessions = paid = minutes = vehicles = 0.0
    else:
        sessions = sessions_sum / weight_sum
        paid = paid_sum / weight_sum
        minutes = minutes_sum / weight_sum
        vehicles = vehicles_sum / weight_sum
    return {
        "day": target_day,
        "sessions": sessions,
        "paid": paid,
        "minutes": minutes,
        "vehicles": vehicles,
        "weight_sum": weight_sum,
        "comparable_days": comparable_days,
        "holiday": target_holiday_name,
    }


def parking_period_actual(history: Dict[date, Dict[str, float]], start: date, end: date) -> Dict[str, float]:
    total = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0, "vehicles": 0.0}
    for day in iter_dates(start, end):
        item = history.get(day) or {}
        total["sessions"] += float_or_zero(item.get("sessions"))
        total["paid"] += float_or_zero(item.get("paid"))
        total["minutes"] += float_or_zero(item.get("minutes"))
        total["vehicles"] += float_or_zero(item.get("vehicles"))
    return total


def parking_history_weight(target_day: date, historical_day: date, today: date) -> float:
    return parking_history_weight_precomputed(
        target_day,
        historical_day,
        today,
        bool(norwegian_holiday_name(target_day)),
    )


def parking_history_weight_precomputed(target_day: date, historical_day: date, today: date, target_holiday: bool) -> float:
    if historical_day >= today:
        return 0.0
    age_years = max(0.0, (today - historical_day).days / 365.25)
    recency = 0.74 ** age_years
    month_diff = month_distance(target_day.month, historical_day.month)
    season = {0: 1.85, 1: 1.38, 2: 1.05, 3: 0.78}.get(month_diff, 0.48)

    target_weekday = target_day.weekday()
    history_weekday = historical_day.weekday()
    target_is_sunday = target_weekday == 6
    history_is_sunday = history_weekday == 6
    if target_is_sunday:
        weekday = 3.2 if history_is_sunday else 0.035
    elif history_is_sunday:
        weekday = 0.10
    else:
        weekday = 1.45 if target_weekday == history_weekday else 0.78

    history_holiday = bool(norwegian_holiday_name(historical_day))
    holiday = 1.8 if target_holiday and history_holiday else 1.0 if target_holiday == history_holiday else 0.50
    return max(0.0, recency * season * weekday * holiday)
