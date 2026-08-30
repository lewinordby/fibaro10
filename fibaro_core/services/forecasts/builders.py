"""Forecast builders; no runtime resources are created on import."""

from datetime import date
from datetime import datetime
from datetime import timedelta
from fibaro_core.services.forecasts.calendar import iter_dates
from fibaro_core.services.forecasts.calendar import month_end
from fibaro_core.services.forecasts.calendar import norwegian_holiday_name
from fibaro_core.services.forecasts.models import intraday_forecast_value
from fibaro_core.services.forecasts.models import opening_day_fraction
from fibaro_core.services.forecasts.models import parking_apply_period_tempo
from fibaro_core.services.forecasts.models import parking_daily_model_from_features
from fibaro_core.services.forecasts.models import parking_historical_day_fraction
from fibaro_core.services.forecasts.models import parking_model_history_features
from fibaro_core.services.forecasts.models import parking_period_actual
from fibaro_core.services.forecasts.models import sun2_apply_tempo
from fibaro_core.services.forecasts.models import sun2_daily_model_from_features
from fibaro_core.services.forecasts.models import sun2_historical_day_fraction
from fibaro_core.services.forecasts.models import sun2_model_history_features
from fibaro_core.services.forecasts.models import sun2_period_actual
from typing import Any
from typing import Dict
from value_parsing import float_or_zero


async def build_sun2_forecast(session, today: date, now_local: datetime, *, cache, summaries_getter) -> Dict[str, Any]:
    cache_key = f"sun2_forecast:{today.isoformat()}:{now_local.hour:02d}:{now_local.minute // 5}"
    now_utc = datetime.utcnow()
    cached = cache.get(cache_key)
    if cached and cached.get("expires", datetime.min) > now_utc:
        return cached["value"]

    summaries = await summaries_getter(session)
    history: Dict[date, Dict[str, float]] = {}
    for item in summaries.get("daily", []):
        period = item.get("period")
        try:
            day = date.fromisoformat(period)
        except (TypeError, ValueError):
            continue
        history[day] = {
            "sessions": float_or_zero(item.get("totalt_antall_solinger")),
            "paid": float_or_zero(item.get("totalt_inntjent_kr")),
            "minutes": float_or_zero(item.get("total_soletid_minutter")),
        }
    model_cutoff = today - timedelta(days=1461)
    model_history = {
        day: item
        for day, item in history.items()
        if model_cutoff <= day < today
    }
    if len(model_history) < 180:
        model_history = {day: item for day, item in history.items() if day < today}

    actual_today = history.get(today, {"sessions": 0.0, "paid": 0.0, "minutes": 0.0})
    minute_of_day = now_local.hour * 60 + now_local.minute
    opening_minute = 7 * 60
    closing_minute = 23 * 60
    day_fraction = opening_day_fraction(minute_of_day, opening_minute, closing_minute, power=0.86)
    day_fraction = await sun2_historical_day_fraction(session, today, today, model_history, minute_of_day, day_fraction)
    model_features = sun2_model_history_features(model_history, today)
    daily_model_cache: Dict[date, Dict[str, Any]] = {}

    def model_for(day: date) -> Dict[str, Any]:
        model = daily_model_cache.get(day)
        if model is None:
            model = sun2_daily_model_from_features(day, model_features)
            daily_model_cache[day] = model
        return model

    model_today = model_for(today)
    actual_sessions = float_or_zero(actual_today.get("sessions"))
    actual_paid = float_or_zero(actual_today.get("paid"))
    actual_minutes = float_or_zero(actual_today.get("minutes"))
    day_sessions, session_tempo = intraday_forecast_value(
        actual_sessions,
        model_today["sessions"],
        day_fraction,
        minute_of_day,
        opening_minute,
        minimum_expected_now=3.0,
    )
    day_paid = max(actual_paid, float_or_zero(model_today.get("paid")) * session_tempo)
    day_minutes = max(actual_minutes, float_or_zero(model_today.get("minutes")) * session_tempo)

    def forecast_period(start: date, end: date, label: str) -> Dict[str, Any]:
        actual_end = min(today, end)
        actual = sun2_period_actual(history, start, actual_end) if actual_end >= start else {"sessions": 0.0, "paid": 0.0, "minutes": 0.0}
        expected_so_far = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0}
        remaining_base = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0}
        today_remaining = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0}
        future_days = []
        for day in iter_dates(start, end):
            model = model_for(day)
            if day < today:
                expected_so_far["sessions"] += model["sessions"]
                expected_so_far["paid"] += model["paid"]
                expected_so_far["minutes"] += model["minutes"]
            elif day == today:
                expected_so_far["sessions"] += model["sessions"] * day_fraction
                expected_so_far["paid"] += model["paid"] * day_fraction
                expected_so_far["minutes"] += model["minutes"] * day_fraction
            else:
                remaining_base["sessions"] += model["sessions"]
                remaining_base["paid"] += model["paid"]
                remaining_base["minutes"] += model["minutes"]
                future_days.append(model)
        tempo_sessions = sun2_apply_tempo(actual["sessions"], expected_so_far["sessions"])
        tempo_paid = sun2_apply_tempo(actual["paid"], expected_so_far["paid"])
        tempo_minutes = sun2_apply_tempo(actual["minutes"], expected_so_far["minutes"])
        if start <= today <= end:
            actual["sessions"] = max(actual["sessions"], actual_sessions)
            actual["paid"] = max(actual["paid"], actual_paid)
            actual["minutes"] = max(actual["minutes"], actual_minutes)
            today_remaining["sessions"] = max(0.0, day_sessions - actual_sessions)
            today_remaining["paid"] = max(0.0, day_paid - actual_paid)
            today_remaining["minutes"] = max(0.0, day_minutes - actual_minutes)
        forecast = {
            "sessions": actual["sessions"] + today_remaining["sessions"] + remaining_base["sessions"] * tempo_sessions,
            "paid": actual["paid"] + today_remaining["paid"] + remaining_base["paid"] * tempo_paid,
            "minutes": actual["minutes"] + today_remaining["minutes"] + remaining_base["minutes"] * tempo_minutes,
        }
        important_days = sorted(
            [item for item in future_days if item.get("holiday")],
            key=lambda item: item["day"],
        )[:8]
        return {
            "label": label,
            "start": start,
            "end": end,
            "actual": actual,
            "expected_so_far": expected_so_far,
            "forecast": forecast,
            "tempo": tempo_sessions,
            "remaining_days": max(0, (end - today).days),
            "important_days": important_days,
        }

    month_start = date(today.year, today.month, 1)
    year_start = date(today.year, 1, 1)
    month = forecast_period(month_start, month_end(today), "Inneværende måned")
    year = forecast_period(year_start, date(today.year, 12, 31), "Inneværende år")
    weekday_names = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
    day = {
        "label": "I dag",
        "date": today,
        "weekday": weekday_names[today.weekday()],
        "holiday": norwegian_holiday_name(today),
        "actual": actual_today,
        "forecast": {"sessions": day_sessions, "paid": day_paid, "minutes": day_minutes},
        "model": model_today,
        "day_fraction": day_fraction,
        "remaining_fraction": max(0.0, 1.0 - day_fraction),
        "comparable_days": model_today["comparable_days"],
    }
    value = {
        "day": day,
        "month": month,
        "year": year,
        "history_first_date": summaries.get("first_date"),
        "history_last_date": summaries.get("last_date"),
        "generated_at": now_local,
    }
    cache[cache_key] = {"expires": now_utc + timedelta(minutes=3), "value": value}
    return value


async def build_parking_forecast(session, today: date, now_local: datetime, *, cache, summaries_getter) -> Dict[str, Any]:
    cache_key = f"parking_forecast:{today.isoformat()}:{now_local.hour:02d}:{now_local.minute // 5}"
    now_utc = datetime.utcnow()
    cached = cache.get(cache_key)
    if cached and cached.get("expires", datetime.min) > now_utc:
        return cached["value"]

    summaries = await summaries_getter(session)
    history: Dict[date, Dict[str, float]] = {}
    for item in summaries.get("daily", []):
        period = item.get("period")
        try:
            day = date.fromisoformat(period)
        except (TypeError, ValueError):
            continue
        history[day] = {
            "sessions": float_or_zero(item.get("sessions")),
            "paid": float_or_zero(item.get("paid")),
            "minutes": float_or_zero(item.get("minutes")),
            "vehicles": float_or_zero(item.get("vehicles")),
        }

    model_cutoff = today - timedelta(days=1461)
    model_history = {
        day: item
        for day, item in history.items()
        if model_cutoff <= day < today
    }
    if len(model_history) < 180:
        model_history = {day: item for day, item in history.items() if day < today}

    actual_today = history.get(today, {"sessions": 0.0, "paid": 0.0, "minutes": 0.0, "vehicles": 0.0})
    minute_of_day = now_local.hour * 60 + now_local.minute
    opening_minute = 7 * 60
    closing_minute = 23 * 60
    day_fraction = opening_day_fraction(minute_of_day, opening_minute, closing_minute, power=0.9)
    day_fraction = await parking_historical_day_fraction(session, today, today, model_history, minute_of_day, day_fraction)

    model_features = parking_model_history_features(model_history, today)
    daily_model_cache: Dict[date, Dict[str, Any]] = {}

    def model_for(day: date) -> Dict[str, Any]:
        model = daily_model_cache.get(day)
        if model is None:
            model = parking_daily_model_from_features(day, model_features)
            daily_model_cache[day] = model
        return model

    model_today = model_for(today)
    actual_sessions = float_or_zero(actual_today.get("sessions"))
    actual_paid = float_or_zero(actual_today.get("paid"))
    actual_minutes = float_or_zero(actual_today.get("minutes"))
    actual_vehicles = float_or_zero(actual_today.get("vehicles"))
    day_sessions, session_tempo = intraday_forecast_value(
        actual_sessions,
        model_today["sessions"],
        day_fraction,
        minute_of_day,
        opening_minute,
        minimum_expected_now=4.0,
    )
    day_paid, _ = intraday_forecast_value(
        actual_paid,
        model_today["paid"],
        day_fraction,
        minute_of_day,
        opening_minute,
        minimum_expected_now=80.0,
    )
    day_minutes, _ = intraday_forecast_value(
        actual_minutes,
        model_today["minutes"],
        day_fraction,
        minute_of_day,
        opening_minute,
        minimum_expected_now=60.0,
    )
    day_vehicles, _ = intraday_forecast_value(
        actual_vehicles,
        model_today["vehicles"],
        day_fraction,
        minute_of_day,
        opening_minute,
        minimum_expected_now=3.0,
    )

    def forecast_period(start: date, end: date, label: str) -> Dict[str, Any]:
        actual_end = min(today, end)
        actual = parking_period_actual(history, start, actual_end) if actual_end >= start else {"sessions": 0.0, "paid": 0.0, "minutes": 0.0, "vehicles": 0.0}
        expected_so_far = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0, "vehicles": 0.0}
        remaining_base = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0, "vehicles": 0.0}
        today_remaining = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0, "vehicles": 0.0}
        future_days = []
        for day in iter_dates(start, end):
            model = model_for(day)
            if day < today:
                expected_so_far["sessions"] += model["sessions"]
                expected_so_far["paid"] += model["paid"]
                expected_so_far["minutes"] += model["minutes"]
                expected_so_far["vehicles"] += model["vehicles"]
            elif day == today:
                expected_so_far["sessions"] += model["sessions"] * day_fraction
                expected_so_far["paid"] += model["paid"] * day_fraction
                expected_so_far["minutes"] += model["minutes"] * day_fraction
                expected_so_far["vehicles"] += model["vehicles"] * day_fraction
            else:
                remaining_base["sessions"] += model["sessions"]
                remaining_base["paid"] += model["paid"]
                remaining_base["minutes"] += model["minutes"]
                remaining_base["vehicles"] += model["vehicles"]
                future_days.append(model)

        def model_progress(metric: str) -> float:
            total = expected_so_far[metric] + remaining_base[metric]
            return expected_so_far[metric] / total if total > 0 else 1.0

        tempo_sessions = parking_apply_period_tempo(actual["sessions"], expected_so_far["sessions"], model_progress("sessions"))
        tempo_paid = parking_apply_period_tempo(actual["paid"], expected_so_far["paid"], model_progress("paid"))
        tempo_minutes = parking_apply_period_tempo(actual["minutes"], expected_so_far["minutes"], model_progress("minutes"))
        tempo_vehicles = parking_apply_period_tempo(actual["vehicles"], expected_so_far["vehicles"], model_progress("vehicles"))
        if start <= today <= end:
            actual["sessions"] = max(actual["sessions"], actual_sessions)
            actual["paid"] = max(actual["paid"], actual_paid)
            actual["minutes"] = max(actual["minutes"], actual_minutes)
            actual["vehicles"] = max(actual["vehicles"], actual_vehicles)
            today_remaining["sessions"] = max(0.0, day_sessions - actual_sessions)
            today_remaining["paid"] = max(0.0, day_paid - actual_paid)
            today_remaining["minutes"] = max(0.0, day_minutes - actual_minutes)
            today_remaining["vehicles"] = max(0.0, day_vehicles - actual_vehicles)
        forecast = {
            "sessions": actual["sessions"] + today_remaining["sessions"] + remaining_base["sessions"] * tempo_sessions,
            "paid": actual["paid"] + today_remaining["paid"] + remaining_base["paid"] * tempo_paid,
            "minutes": actual["minutes"] + today_remaining["minutes"] + remaining_base["minutes"] * tempo_minutes,
            "vehicles": actual["vehicles"] + today_remaining["vehicles"] + remaining_base["vehicles"] * tempo_vehicles,
        }
        important_days = sorted(
            [item for item in future_days if item.get("holiday")],
            key=lambda item: item["day"],
        )[:8]
        return {
            "label": label,
            "start": start,
            "end": end,
            "actual": actual,
            "expected_so_far": expected_so_far,
            "forecast": forecast,
            "tempo": tempo_sessions,
            "remaining_days": max(0, (end - today).days),
            "important_days": important_days,
        }

    month_start = date(today.year, today.month, 1)
    year_start = date(today.year, 1, 1)
    month = forecast_period(month_start, month_end(today), "Inneværende måned")
    year = forecast_period(year_start, date(today.year, 12, 31), "Inneværende år")
    weekday_names = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
    day = {
        "label": "I dag",
        "date": today,
        "weekday": weekday_names[today.weekday()],
        "holiday": norwegian_holiday_name(today),
        "actual": actual_today,
        "forecast": {"sessions": day_sessions, "paid": day_paid, "minutes": day_minutes, "vehicles": day_vehicles},
        "model": model_today,
        "day_fraction": day_fraction,
        "remaining_fraction": max(0.0, 1.0 - day_fraction),
        "comparable_days": model_today["comparable_days"],
    }
    value = {
        "day": day,
        "month": month,
        "year": year,
        "history_first_date": summaries.get("first_date"),
        "history_last_date": summaries.get("last_date"),
        "generated_at": now_local,
    }
    cache[cache_key] = {"expires": now_utc + timedelta(minutes=3), "value": value}
    return value
