"""Parking summary calculations; sessions are supplied by the caller."""

from datetime import date, datetime, timedelta
import re
from types import SimpleNamespace
from typing import Any, Dict, Optional

from sqlalchemy import func, literal, select, union_all

from fibaro_core.models.parking import ParkingSession
from fibaro_core.services.summaries.periods import days_in_year, iso_week_period
from value_parsing import float_or_zero, int_or_zero


async def parking_datetime_snapshots(
    session,
    periods: Dict[str, tuple[datetime, datetime]],
) -> Dict[str, SimpleNamespace]:
    if not periods:
        return {}
    queries = []
    for key, (start_at, end_at) in periods.items():
        queries.append(
            select(
                literal(key).label("period_key"),
                func.count(ParkingSession.id).label("sessions"),
                func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
            ).where(
                ParkingSession.start_time >= start_at,
                ParkingSession.start_time < end_at,
            )
        )
    rows = (await session.execute(union_all(*queries))).mappings().all()
    rows_by_key = {str(row.get("period_key")): row for row in rows}
    return {
        key: SimpleNamespace(
            sessions=int_or_zero(rows_by_key.get(key, {}).get("sessions")),
            paid=float_or_zero(rows_by_key.get(key, {}).get("paid")),
        )
        for key in periods
    }


async def parking_datetime_snapshot(session, start_at: datetime, end_at: datetime) -> SimpleNamespace:
    return (await parking_datetime_snapshots(session, {"snapshot": (start_at, end_at)}))["snapshot"]


def empty_parking_summary(period: str, period_label: Optional[str] = None) -> Dict[str, Any]:
    return {
        "period": period,
        "period_label": period_label or period,
        "sessions": 0,
        "paid": 0.0,
        "minutes": 0.0,
        "vehicles": 0,
        "days_count": 0,
    }


def parking_weekly_items(daily_items: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    weekly: Dict[str, Dict[str, Any]] = {}
    for item in daily_items:
        try:
            stat_day = date.fromisoformat(str(item.get("period") or ""))
        except ValueError:
            continue
        period, period_label = iso_week_period(stat_day)
        target = weekly.setdefault(period, empty_parking_summary(period, period_label))
        target["sessions"] += int_or_zero(item.get("sessions"))
        target["paid"] += float_or_zero(item.get("paid"))
        target["minutes"] += float_or_zero(item.get("minutes"))
        target["vehicles"] = max(target["vehicles"], int_or_zero(item.get("vehicles")))
        target["days_count"] += 1
    return [weekly[key] for key in sorted(weekly, reverse=True)]


async def build_parking_summaries_fast(session) -> Dict[str, Any]:
    stat_date_expr = func.date(ParkingSession.start_time).label("stat_date")
    daily_rows = (
        await session.execute(
            select(
                stat_date_expr,
                func.count(ParkingSession.id).label("sessions"),
                func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                func.coalesce(func.sum(ParkingSession.parking_time_min), 0).label("minutes"),
                func.count(func.distinct(ParkingSession.car_license_number)).label("vehicles"),
            )
            .group_by(stat_date_expr)
            .order_by(stat_date_expr.desc())
        )
    ).mappings().all()

    daily_items = []
    monthly: Dict[str, Dict[str, Any]] = {}
    yearly: Dict[str, Dict[str, Any]] = {}
    total = empty_parking_summary("Totalt")
    first_date = None
    last_date = None

    for row in daily_rows:
        stat_day = row.get("stat_date")
        if not stat_day:
            continue
        if isinstance(stat_day, str):
            stat_day = date.fromisoformat(stat_day)
        first_date = stat_day if first_date is None else min(first_date, stat_day)
        last_date = stat_day if last_date is None else max(last_date, stat_day)
        item = empty_parking_summary(stat_day.isoformat(), stat_day.strftime("%d.%m.%Y"))
        item["sessions"] = int_or_zero(row.get("sessions"))
        item["paid"] = float_or_zero(row.get("paid"))
        item["minutes"] = float_or_zero(row.get("minutes"))
        item["vehicles"] = int_or_zero(row.get("vehicles"))
        item["days_count"] = 1
        daily_items.append(item)

        month_key = stat_day.strftime("%Y-%m")
        year_key = str(stat_day.year)
        monthly.setdefault(month_key, empty_parking_summary(month_key))
        yearly.setdefault(year_key, empty_parking_summary(year_key))
        for target in (monthly[month_key], yearly[year_key], total):
            target["sessions"] += item["sessions"]
            target["paid"] += item["paid"]
            target["minutes"] += item["minutes"]
            target["vehicles"] = max(target["vehicles"], item["vehicles"])
            target["days_count"] += 1

    monthly_items = [monthly[key] for key in sorted(monthly, reverse=True)]
    yearly_items = [yearly[key] for key in sorted(yearly, reverse=True)]
    weekly_items = parking_weekly_items(daily_items)
    palette = ["#4e8793", "#d59a18", "#071943", "#52a464", "#df705d", "#726189", "#2f8fa3", "#8b5cf6"]
    weekly_chart = []
    weekly_by_year: Dict[str, Dict[int, Dict[str, Any]]] = {}
    for item in weekly_items:
        match = re.fullmatch(r"(\d{4})-W(\d{2})", str(item.get("period") or ""))
        if match:
            weekly_by_year.setdefault(match.group(1), {})[int(match.group(2))] = item
    for index, year in enumerate(sorted(weekly_by_year.keys())):
        weeks = weekly_by_year[year]
        weekly_chart.append(
            {
                "year": year,
                "color": palette[index % len(palette)],
                "revenue": [round(float_or_zero(weeks[week].get("paid")), 2) if week in weeks else None for week in range(1, 54)],
                "count": [int_or_zero(weeks[week].get("sessions")) if week in weeks else None for week in range(1, 54)],
            }
        )
    top_sort = lambda item: (item["paid"], item["sessions"], item["minutes"])
    count_sort = lambda item: (item["sessions"], item["paid"], item["minutes"])
    return {
        "daily": daily_items,
        "monthly": monthly_items,
        "yearly": yearly_items,
        "weekly_chart": weekly_chart,
        "top_days": sorted(daily_items, key=top_sort, reverse=True)[:20],
        "top_weeks": sorted(weekly_items, key=top_sort, reverse=True)[:20],
        "top_months": sorted(monthly_items, key=top_sort, reverse=True)[:20],
        "top_days_by_count": sorted(daily_items, key=count_sort, reverse=True)[:20],
        "top_weeks_by_count": sorted(weekly_items, key=count_sort, reverse=True)[:20],
        "top_months_by_count": sorted(monthly_items, key=count_sort, reverse=True)[:20],
        "total": total,
        "first_date": first_date,
        "last_date": last_date,
    }


def parking_daily_by_year(summaries: Dict[str, Any]) -> Dict[int, Dict[int, Dict[str, Any]]]:
    by_year: Dict[int, Dict[int, Dict[str, Any]]] = {}
    for item in summaries.get("daily", []):
        period = str(item.get("period") or "")
        try:
            stat_date = date.fromisoformat(period)
        except ValueError:
            continue
        by_year.setdefault(stat_date.year, {})[stat_date.timetuple().tm_yday] = {
            "date": stat_date,
            "amount": float_or_zero(item.get("paid")),
            "count": int_or_zero(item.get("sessions")),
            "minutes": float_or_zero(item.get("minutes")),
        }
    return by_year


def parking_year_series(
    daily_by_year: Dict[int, Dict[int, Dict[str, Any]]],
    year: int,
    as_of_day: int,
    source: str,
    color: str,
) -> Dict[str, Any]:
    max_day = days_in_year(year)
    visible_day = max(1, min(as_of_day, max_day))
    daily_rows = daily_by_year.get(year, {})
    cumulative_amount = 0.0
    cumulative_count = 0
    cumulative_minutes = 0.0
    points = []
    days_with_data = 0
    for day_number in range(1, visible_day + 1):
        row = daily_rows.get(day_number)
        if row:
            days_with_data += 1
            cumulative_amount += float_or_zero(row.get("amount"))
            cumulative_count += int_or_zero(row.get("count"))
            cumulative_minutes += float_or_zero(row.get("minutes"))
        point_date = date(year, 1, 1) + timedelta(days=day_number - 1)
        points.append(
            {
                "day": day_number,
                "date": point_date.isoformat(),
                "label": point_date.strftime("%d.%m"),
                "amount": round(float_or_zero(row.get("amount")) if row else 0.0, 2),
                "count": int_or_zero(row.get("count")) if row else 0,
                "minutes": round(float_or_zero(row.get("minutes")) if row else 0.0, 2),
                "cumulativeAmount": round(cumulative_amount, 2),
                "cumulativeCount": cumulative_count,
                "cumulativeMinutes": round(cumulative_minutes, 2),
            }
        )
    return {
        "key": f"{source}-{year}",
        "source": source,
        "year": year,
        "label": str(year),
        "color": color,
        "daysInYear": max_day,
        "asOfDay": visible_day,
        "daysWithData": days_with_data,
        "totalAmount": round(cumulative_amount, 2),
        "totalCount": cumulative_count,
        "totalMinutes": round(cumulative_minutes, 2),
        "points": points,
    }


def parking_year_comparison_delta(current: Dict[str, Any], comparison: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "amount": round(float_or_zero(current.get("totalAmount")) - float_or_zero(comparison.get("totalAmount")), 2),
        "count": int_or_zero(current.get("totalCount")) - int_or_zero(comparison.get("totalCount")),
        "minutes": round(float_or_zero(current.get("totalMinutes")) - float_or_zero(comparison.get("totalMinutes")), 2),
    }
