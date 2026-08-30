"""Sun summary calculations; sessions are supplied by the caller."""

from datetime import date, datetime, timedelta
import re
from types import SimpleNamespace
from typing import Any, Dict, Optional

from sqlalchemy import case, func, literal, select, union_all

from fibaro_core.models.sun import Sun2RoomDailyStat, Sun2TanningSession
from fibaro_core.services.summaries.periods import days_in_year, iso_week_period, normalized_stat_date
from value_parsing import float_or_zero, int_or_zero


SUN2_SUM_FIELDS = [
    "total_soletid_minutter",
    "totalt_antall_solinger",
    "solinger_medlemmer",
    "solinger_ikke_medlemmer",
    "totalt_inntjent_kr",
    "inntjent_medlemmer_kr",
    "inntjent_ikke_medlemmer_kr",
]


def empty_sun2_summary(period: str) -> Dict[str, Any]:
    return {
        "period": period,
        "period_label": period,
        "total_soletid_minutter": 0.0,
        "total_soletid_timer": 0.0,
        "totalt_antall_solinger": 0,
        "solinger_medlemmer": 0,
        "solinger_ikke_medlemmer": 0,
        "totalt_inntjent_kr": 0.0,
        "inntjent_medlemmer_kr": 0.0,
        "inntjent_ikke_medlemmer_kr": 0.0,
        "days": set(),
        "rooms": set(),
    }


def add_sun2_row_to_summary(summary: Dict[str, Any], row: Any) -> None:
    for field in SUN2_SUM_FIELDS:
        summary[field] += getattr(row, field) or 0
    if row.stat_date:
        summary["days"].add(row.stat_date)
    if row.room:
        summary["rooms"].add(row.room)


def finalize_sun2_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(summary)
    summary["total_soletid_timer"] = summary["total_soletid_minutter"] / 60
    summary["days_count"] = len(summary.pop("days", []))
    summary["rooms_count"] = len(summary.pop("rooms", []))
    return summary


def build_sun2_summaries(rows: list[Any]) -> Dict[str, Any]:
    daily: Dict[str, Dict[str, Any]] = {}
    monthly: Dict[str, Dict[str, Any]] = {}
    yearly: Dict[str, Dict[str, Any]] = {}
    weekly: Dict[str, Dict[int, Dict[str, Any]]] = {}
    total = empty_sun2_summary("Totalt")
    first_date = None
    last_date = None

    for row in rows:
        if not row.stat_date:
            continue
        first_date = row.stat_date if first_date is None else min(first_date, row.stat_date)
        last_date = row.stat_date if last_date is None else max(last_date, row.stat_date)
        day_key = row.stat_date.isoformat()
        month_key = row.stat_date.strftime("%Y-%m")
        year_key = str(row.stat_date.year)
        iso_year, iso_week, _ = row.stat_date.isocalendar()
        iso_year_key = str(iso_year)
        daily.setdefault(day_key, empty_sun2_summary(day_key))
        monthly.setdefault(month_key, empty_sun2_summary(month_key))
        yearly.setdefault(year_key, empty_sun2_summary(year_key))
        weekly.setdefault(iso_year_key, {})
        weekly[iso_year_key].setdefault(iso_week, empty_sun2_summary(f"{iso_year_key}-W{iso_week:02d}"))
        daily[day_key]["period_label"] = row.stat_date.strftime("%d.%m.%Y")
        add_sun2_row_to_summary(daily[day_key], row)
        add_sun2_row_to_summary(monthly[month_key], row)
        add_sun2_row_to_summary(yearly[year_key], row)
        add_sun2_row_to_summary(weekly[iso_year_key][iso_week], row)
        add_sun2_row_to_summary(total, row)

    daily_items = [finalize_sun2_summary(daily[key]) for key in sorted(daily, reverse=True)]
    monthly_items = [finalize_sun2_summary(monthly[key]) for key in sorted(monthly, reverse=True)]
    yearly_items = [finalize_sun2_summary(yearly[key]) for key in sorted(yearly, reverse=True)]
    top_sort = lambda item: (
        item["totalt_inntjent_kr"],
        item["totalt_antall_solinger"],
        item["total_soletid_minutter"],
    )
    count_sort = lambda item: (
        item["totalt_antall_solinger"],
        item["totalt_inntjent_kr"],
        item["total_soletid_minutter"],
    )
    weekly_chart = []
    palette = ["#3f7fbd", "#df705d", "#52a464", "#726189", "#f2b84b", "#2f8fa3", "#8b5cf6", "#ef4444"]
    for index, year_key in enumerate(sorted(weekly.keys())):
        weeks = weekly[year_key]
        weekly_chart.append(
            {
                "year": year_key,
                "color": palette[index % len(palette)],
                "revenue": [round(finalize_sun2_summary(weeks[week])["totalt_inntjent_kr"], 2) if week in weeks else None for week in range(1, 54)],
                "count": [int(finalize_sun2_summary(weeks[week])["totalt_antall_solinger"]) if week in weeks else None for week in range(1, 54)],
            }
        )

    return {
        "daily": daily_items,
        "monthly": monthly_items,
        "yearly": yearly_items,
        "weekly_chart": weekly_chart,
        "top_days": sorted(daily_items, key=top_sort, reverse=True)[:20],
        "top_months": sorted(monthly_items, key=top_sort, reverse=True)[:20],
        "top_days_by_count": sorted(daily_items, key=count_sort, reverse=True)[:20],
        "top_months_by_count": sorted(monthly_items, key=count_sort, reverse=True)[:20],
        "total": finalize_sun2_summary(total),
        "first_date": first_date,
        "last_date": last_date,
    }


def finalized_sun2_aggregate(row: Dict[str, Any], period: str, period_label: Optional[str] = None) -> Dict[str, Any]:
    item = empty_sun2_summary(period)
    item["period_label"] = period_label or period
    for field in SUN2_SUM_FIELDS:
        item[field] = float_or_zero(row.get(field))
    item["total_soletid_timer"] = item["total_soletid_minutter"] / 60
    item["days_count"] = int_or_zero(row.get("days_count"))
    item["rooms_count"] = int_or_zero(row.get("rooms_count"))
    return item


def sun2_sum_columns() -> list[Any]:
    return [func.coalesce(func.sum(getattr(Sun2RoomDailyStat, field)), 0).label(field) for field in SUN2_SUM_FIELDS]


def empty_fast_sun2_summary(period: str, period_label: Optional[str] = None) -> Dict[str, Any]:
    item = {field: 0.0 for field in SUN2_SUM_FIELDS}
    item.update(
        {
            "period": period,
            "period_label": period_label or period,
            "total_soletid_timer": 0.0,
            "days_count": 0,
            "rooms_count": 0,
            "rows_count": 0,
        }
    )
    return item


def add_fast_sun2_summary(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    for field in SUN2_SUM_FIELDS:
        target[field] += float_or_zero(source.get(field))
    target["total_soletid_timer"] = target["total_soletid_minutter"] / 60
    target["days_count"] += int_or_zero(source.get("days_count"))
    target["rows_count"] += int_or_zero(source.get("rows_count"))
    target["rooms_count"] = max(int_or_zero(target.get("rooms_count")), int_or_zero(source.get("rooms_count")))


def sun2_weekly_items(daily_items: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    weekly: Dict[str, Dict[str, Any]] = {}
    for item in daily_items:
        try:
            stat_day = date.fromisoformat(str(item.get("period") or ""))
        except ValueError:
            continue
        period, period_label = iso_week_period(stat_day)
        target = weekly.setdefault(period, empty_fast_sun2_summary(period, period_label))
        add_fast_sun2_summary(target, item)
    return [weekly[key] for key in sorted(weekly, reverse=True)]


async def build_sun2_summaries_fast(session) -> Dict[str, Any]:
    daily_rows = (
        await session.execute(
            select(
                Sun2RoomDailyStat.stat_date.label("stat_date"),
                *sun2_sum_columns(),
                func.count(Sun2RoomDailyStat.id).label("rows_count"),
                func.count(func.distinct(Sun2RoomDailyStat.room)).label("rooms_count"),
            )
            .group_by(Sun2RoomDailyStat.stat_date)
            .order_by(Sun2RoomDailyStat.stat_date.desc())
        )
    ).mappings().all()

    daily_items = []
    monthly: Dict[str, Dict[str, Any]] = {}
    yearly: Dict[str, Dict[str, Any]] = {}
    total = empty_fast_sun2_summary("Totalt")
    first_date = None
    last_date = None

    for row in daily_rows:
        stat_date = row.get("stat_date")
        if not stat_date:
            continue
        first_date = stat_date if first_date is None else min(first_date, stat_date)
        last_date = stat_date if last_date is None else max(last_date, stat_date)
        source = dict(row)
        source["days_count"] = 1
        item = finalized_sun2_aggregate(source, stat_date.isoformat(), stat_date.strftime("%d.%m.%Y"))
        item["rows_count"] = int_or_zero(row.get("rows_count"))
        daily_items.append(item)

        month_key = stat_date.strftime("%Y-%m")
        year_key = str(stat_date.year)
        monthly.setdefault(month_key, empty_fast_sun2_summary(month_key))
        yearly.setdefault(year_key, empty_fast_sun2_summary(year_key))
        add_fast_sun2_summary(monthly[month_key], item)
        add_fast_sun2_summary(yearly[year_key], item)
        add_fast_sun2_summary(total, item)

    daily_dates_subquery = select(Sun2RoomDailyStat.stat_date).distinct()
    session_filters = [Sun2TanningSession.stat_date.not_in(daily_dates_subquery)]
    customer_type = func.lower(func.coalesce(Sun2TanningSession.customer_type, ""))
    is_member = customer_type.like("%medlem%") & ~customer_type.like("%ikke%")
    live_session_query = (
        select(
            Sun2TanningSession.stat_date.label("stat_date"),
            func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("total_soletid_minutter"),
            func.count(Sun2TanningSession.id).label("totalt_antall_solinger"),
            func.coalesce(func.sum(case((is_member, 1), else_=0)), 0).label("solinger_medlemmer"),
            func.coalesce(func.sum(case((~is_member, 1), else_=0)), 0).label("solinger_ikke_medlemmer"),
            func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("totalt_inntjent_kr"),
            func.coalesce(func.sum(case((is_member, Sun2TanningSession.paid_amount_kr), else_=0)), 0).label("inntjent_medlemmer_kr"),
            func.coalesce(func.sum(case((~is_member, Sun2TanningSession.paid_amount_kr), else_=0)), 0).label("inntjent_ikke_medlemmer_kr"),
            func.count(Sun2TanningSession.id).label("rows_count"),
            func.count(func.distinct(Sun2TanningSession.room_id)).label("rooms_count"),
        )
        .group_by(Sun2TanningSession.stat_date)
        .order_by(Sun2TanningSession.stat_date.desc())
    )
    if session_filters:
        live_session_query = live_session_query.where(*session_filters)
    live_session_rows = (await session.execute(live_session_query)).mappings().all()
    for row in live_session_rows:
        stat_date = row.get("stat_date")
        if not stat_date:
            continue
        first_date = stat_date if first_date is None else min(first_date, stat_date)
        last_date = stat_date if last_date is None else max(last_date, stat_date)
        source = dict(row)
        source["days_count"] = 1
        item = finalized_sun2_aggregate(source, stat_date.isoformat(), stat_date.strftime("%d.%m.%Y"))
        item["rows_count"] = int_or_zero(row.get("rows_count"))
        daily_items.append(item)

        month_key = stat_date.strftime("%Y-%m")
        year_key = str(stat_date.year)
        monthly.setdefault(month_key, empty_fast_sun2_summary(month_key))
        yearly.setdefault(year_key, empty_fast_sun2_summary(year_key))
        add_fast_sun2_summary(monthly[month_key], item)
        add_fast_sun2_summary(yearly[year_key], item)
        add_fast_sun2_summary(total, item)

    daily_items = sorted(daily_items, key=lambda item: item["period"], reverse=True)
    monthly_items = [monthly[key] for key in sorted(monthly, reverse=True)]
    yearly_items = [yearly[key] for key in sorted(yearly, reverse=True)]
    weekly_items = sun2_weekly_items(daily_items)
    palette = ["#3f7fbd", "#df705d", "#52a464", "#726189", "#f2b84b", "#2f8fa3", "#8b5cf6", "#ef4444"]
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
                "revenue": [round(float_or_zero(weeks[week].get("totalt_inntjent_kr")), 2) if week in weeks else None for week in range(1, 54)],
                "count": [int_or_zero(weeks[week].get("totalt_antall_solinger")) if week in weeks else None for week in range(1, 54)],
            }
        )

    top_sort = lambda item: (
        item["totalt_inntjent_kr"],
        item["totalt_antall_solinger"],
        item["total_soletid_minutter"],
    )
    count_sort = lambda item: (
        item["totalt_antall_solinger"],
        item["totalt_inntjent_kr"],
        item["total_soletid_minutter"],
    )
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
        "total_rows": int_or_zero(total.get("rows_count")),
    }


async def sun2_period_snapshots(
    session,
    periods: Dict[str, tuple[date, date]],
) -> Dict[str, SimpleNamespace]:
    """Return several SUN2 periods with daily imports taking precedence over live sessions."""
    if not periods:
        return {}
    global_start = min(start_day for start_day, _ in periods.values())
    global_end = max(end_day for _, end_day in periods.values())
    daily_rows = (
        await session.execute(
            select(
                Sun2RoomDailyStat.stat_date.label("stat_date"),
                *sun2_sum_columns(),
                func.count(func.distinct(Sun2RoomDailyStat.room)).label("rooms"),
            )
            .where(Sun2RoomDailyStat.stat_date >= global_start, Sun2RoomDailyStat.stat_date < global_end)
            .group_by(Sun2RoomDailyStat.stat_date)
        )
    ).mappings().all()
    session_rows = (
        await session.execute(
            select(
                Sun2TanningSession.stat_date.label("stat_date"),
                func.count(Sun2TanningSession.id).label("sessions"),
                func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("minutes"),
                func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
            )
            .where(Sun2TanningSession.stat_date >= global_start, Sun2TanningSession.stat_date < global_end)
            .group_by(Sun2TanningSession.stat_date)
        )
    ).mappings().all()
    session_room_rows = (
        await session.execute(
            select(Sun2TanningSession.stat_date, Sun2TanningSession.room_id)
            .where(
                Sun2TanningSession.stat_date >= global_start,
                Sun2TanningSession.stat_date < global_end,
                Sun2TanningSession.room_id.is_not(None),
            )
            .distinct()
        )
    ).all()

    daily_by_date = {
        stat_day: row
        for row in daily_rows
        if (stat_day := normalized_stat_date(row.get("stat_date"))) is not None
    }
    sessions_by_date = {
        stat_day: row
        for row in session_rows
        if (stat_day := normalized_stat_date(row.get("stat_date"))) is not None
    }
    rooms_by_date: Dict[date, set[Any]] = {}
    for stat_date_value, room_id in session_room_rows:
        stat_day = normalized_stat_date(stat_date_value)
        if stat_day is not None:
            rooms_by_date.setdefault(stat_day, set()).add(room_id)

    snapshots: Dict[str, SimpleNamespace] = {}
    for key, (start_day, end_day) in periods.items():
        totals = {"sessions": 0, "minutes": 0.0, "paid": 0.0, "rooms": 0}
        imported_dates = {
            stat_day for stat_day in daily_by_date if start_day <= stat_day < end_day
        }
        for stat_day in imported_dates:
            row = daily_by_date[stat_day]
            totals["sessions"] += int_or_zero(row.get("totalt_antall_solinger"))
            totals["minutes"] += float_or_zero(row.get("total_soletid_minutter"))
            totals["paid"] += float_or_zero(row.get("totalt_inntjent_kr"))
            totals["rooms"] = max(totals["rooms"], int_or_zero(row.get("rooms")))
        session_room_ids: set[Any] = set()
        for stat_day, row in sessions_by_date.items():
            if not start_day <= stat_day < end_day or stat_day in imported_dates:
                continue
            totals["sessions"] += int_or_zero(row.get("sessions"))
            totals["minutes"] += float_or_zero(row.get("minutes"))
            totals["paid"] += float_or_zero(row.get("paid"))
            session_room_ids.update(rooms_by_date.get(stat_day, set()))
        totals["rooms"] = max(totals["rooms"], len(session_room_ids))
        snapshots[key] = SimpleNamespace(**totals)
    return snapshots


async def sun2_period_snapshot(session, start_day: date, end_day: date) -> SimpleNamespace:
    """Return one SUN2 period; retained for callers outside the optimized overview."""
    return (await sun2_period_snapshots(session, {"snapshot": (start_day, end_day)}))["snapshot"]


async def sun2_datetime_snapshots(
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
                func.count(Sun2TanningSession.id).label("sessions"),
                func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("minutes"),
                func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                func.count(func.distinct(Sun2TanningSession.room_id)).label("rooms"),
            ).where(
                Sun2TanningSession.started_at >= start_at,
                Sun2TanningSession.started_at < end_at,
            )
        )
    rows = (await session.execute(union_all(*queries))).mappings().all()
    rows_by_key = {str(row.get("period_key")): row for row in rows}
    return {
        key: SimpleNamespace(
            sessions=int_or_zero(rows_by_key.get(key, {}).get("sessions")),
            minutes=float_or_zero(rows_by_key.get(key, {}).get("minutes")),
            paid=float_or_zero(rows_by_key.get(key, {}).get("paid")),
            rooms=int_or_zero(rows_by_key.get(key, {}).get("rooms")),
        )
        for key in periods
    }


async def sun2_datetime_snapshot(session, start_at: datetime, end_at: datetime) -> SimpleNamespace:
    return (await sun2_datetime_snapshots(session, {"snapshot": (start_at, end_at)}))["snapshot"]


def sun2_daily_by_year(summaries: Dict[str, Any]) -> Dict[int, Dict[int, Dict[str, Any]]]:
    by_year: Dict[int, Dict[int, Dict[str, Any]]] = {}
    for item in summaries.get("daily", []):
        period = str(item.get("period") or "")
        try:
            stat_date = date.fromisoformat(period)
        except ValueError:
            continue
        by_year.setdefault(stat_date.year, {})[stat_date.timetuple().tm_yday] = {
            "date": stat_date,
            "amount": float_or_zero(item.get("totalt_inntjent_kr")),
            "count": int_or_zero(item.get("totalt_antall_solinger")),
            "minutes": float_or_zero(item.get("total_soletid_minutter")),
        }
    return by_year


def sun2_year_series(
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


def sun2_year_comparison_delta(current: Dict[str, Any], comparison: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "amount": round(float_or_zero(current.get("totalAmount")) - float_or_zero(comparison.get("totalAmount")), 2),
        "count": int_or_zero(current.get("totalCount")) - int_or_zero(comparison.get("totalCount")),
        "minutes": round(float_or_zero(current.get("totalMinutes")) - float_or_zero(comparison.get("totalMinutes")), 2),
    }
