"""Forecast snapshots; no runtime resources are created on import."""

from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from fibaro_core.models import ForecastSnapshot
from fibaro_core.models import ParkingSession
from fibaro_core.services.summaries.sun import sun2_period_snapshot
from sqlalchemy import func
from sqlalchemy import select
from time_formatting import LOCAL_TZ
from time_formatting import local_now_naive
from typing import Any
from typing import Dict
from typing import Optional
from value_parsing import float_or_zero
from zoneinfo import ZoneInfo


def forecast_period_label(period_type: str, start: date, end: date) -> str:
    if period_type == "day":
        return start.strftime("%d.%m.%Y")
    if period_type == "month":
        return start.strftime("%m.%Y")
    if period_type == "year":
        return str(start.year)
    return f"{start.strftime('%d.%m.%Y')} - {end.strftime('%d.%m.%Y')}"


def db_naive_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return value


async def actual_for_forecast_period(session, domain: str, start: date, end: date) -> Dict[str, float]:
    if domain == "sun2":
        row = await sun2_period_snapshot(session, start, end + timedelta(days=1))
        return {
            "sessions": float_or_zero(row.sessions),
            "paid": float_or_zero(row.paid),
            "minutes": float_or_zero(row.minutes),
            "vehicles": 0.0,
        }

    start_at = datetime.combine(start, time.min)
    end_at = datetime.combine(end + timedelta(days=1), time.min)
    row = (
        await session.execute(
            select(
                func.count(ParkingSession.id).label("sessions"),
                func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                func.coalesce(func.sum(ParkingSession.parking_time_min), 0).label("minutes"),
                func.count(func.distinct(ParkingSession.car_license_number)).label("vehicles"),
            ).where(
                ParkingSession.start_time >= start_at,
                ParkingSession.start_time < end_at,
            )
        )
    ).one()
    return {
        "sessions": float_or_zero(row.sessions),
        "paid": float_or_zero(row.paid),
        "minutes": float_or_zero(row.minutes),
        "vehicles": float_or_zero(row.vehicles),
    }


def forecast_snapshot_from_period(
    *,
    domain: str,
    period_type: str,
    start: date,
    end: date,
    period: Dict[str, Any],
    generated_at: Optional[datetime],
    created_by: Optional[str],
) -> ForecastSnapshot:
    forecast = period.get("forecast") or {}
    actual = period.get("actual") or {}
    model = period.get("model") or {}
    return ForecastSnapshot(
        domain=domain,
        period_type=period_type,
        period_start=start,
        period_end=end,
        generated_at=db_naive_utc(generated_at),
        created_by=created_by,
        forecast_sessions=float_or_zero(forecast.get("sessions")),
        forecast_paid=float_or_zero(forecast.get("paid")),
        forecast_minutes=float_or_zero(forecast.get("minutes")),
        forecast_vehicles=float_or_zero(forecast.get("vehicles")),
        actual_sessions_at_save=float_or_zero(actual.get("sessions")),
        actual_paid_at_save=float_or_zero(actual.get("paid")),
        actual_minutes_at_save=float_or_zero(actual.get("minutes")),
        actual_vehicles_at_save=float_or_zero(actual.get("vehicles")),
        model_sessions=float_or_zero(model.get("sessions")),
        day_fraction=period.get("day_fraction"),
        tempo=period.get("tempo"),
        raw={
            "label": period.get("label"),
            "holiday": period.get("holiday"),
            "comparable_days": period.get("comparable_days"),
            "remaining_days": period.get("remaining_days"),
        },
    )


async def save_forecast_snapshots(session, domain: str, forecast: Dict[str, Any], created_by: Optional[str]) -> None:
    today = forecast["day"]["date"]
    month = forecast["month"]
    year = forecast["year"]
    session.add(
        forecast_snapshot_from_period(
            domain=domain,
            period_type="day",
            start=today,
            end=today,
            period=forecast["day"],
            generated_at=forecast.get("generated_at"),
            created_by=created_by,
        )
    )
    session.add(
        forecast_snapshot_from_period(
            domain=domain,
            period_type="month",
            start=month["start"],
            end=month["end"],
            period=month,
            generated_at=forecast.get("generated_at"),
            created_by=created_by,
        )
    )
    session.add(
        forecast_snapshot_from_period(
            domain=domain,
            period_type="year",
            start=year["start"],
            end=year["end"],
            period=year,
            generated_at=forecast.get("generated_at"),
            created_by=created_by,
        )
    )


async def saved_forecast_table(session, domain: str, limit: int = 18) -> list[Dict[str, Any]]:
    rows = (
        await session.execute(
            select(ForecastSnapshot)
            .where(ForecastSnapshot.domain == domain)
            .order_by(ForecastSnapshot.created_at.desc(), ForecastSnapshot.id.desc())
            .limit(limit)
        )
    ).scalars().all()
    today = local_now_naive().date()
    actual_by_period: Dict[tuple[date, date], Dict[str, float]] = {}
    for row in rows:
        period_key = (row.period_start, row.period_end)
        if period_key not in actual_by_period:
            actual_by_period[period_key] = await actual_for_forecast_period(
                session,
                domain,
                row.period_start,
                row.period_end,
            )
    items = []
    for row in rows:
        actual = actual_by_period[(row.period_start, row.period_end)]
        forecast = {
            "sessions": float_or_zero(row.forecast_sessions),
            "paid": float_or_zero(row.forecast_paid),
            "minutes": float_or_zero(row.forecast_minutes),
            "vehicles": float_or_zero(row.forecast_vehicles),
        }
        items.append(
            {
                "id": row.id,
                "created_at": row.created_at,
                "created_by": row.created_by,
                "period_type": row.period_type,
                "period_label": forecast_period_label(row.period_type, row.period_start, row.period_end),
                "period_done": row.period_end < today,
                "forecast": forecast,
                "actual": actual,
                "delta": {
                    "sessions": actual["sessions"] - forecast["sessions"],
                    "paid": actual["paid"] - forecast["paid"],
                    "minutes": actual["minutes"] - forecast["minutes"],
                },
            }
        )
    return items


async def forecast_snapshot_history(session, domain: str, limit: int = 180) -> list[ForecastSnapshot]:
    return (
        await session.execute(
            select(ForecastSnapshot)
            .where(ForecastSnapshot.domain == domain)
            .order_by(ForecastSnapshot.created_at.desc(), ForecastSnapshot.id.desc())
            .limit(limit)
        )
    ).scalars().all()


def forecast_snapshot_stamp(row: ForecastSnapshot) -> Optional[datetime]:
    return row.generated_at or row.created_at


def forecast_chart_time_label(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(LOCAL_TZ).strftime("%d.%m %H:%M")
