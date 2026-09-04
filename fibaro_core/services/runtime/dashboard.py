"""Dashboard services with explicit process dependencies."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fibaro_core.models import ParkingSession, Sun2TanningSession
from fibaro_core.services.presentation import (
    api_chart,
    api_table,
    format_short_number,
    format_signed_short_number,
)
from fibaro_core.services.summaries.periods import add_months, month_label
from sqlalchemy import Date, cast, func, select
from time_formatting import api_local_iso, local_now_naive, normalize_local_naive
from typing import Any, Callable, Dict, Optional
from value_parsing import float_or_zero, int_or_zero


def _revenue_day_rankings(
    sol_by_day: Dict[date, float], parking_by_day: Dict[date, float]
) -> Dict[date, Dict[str, int]]:
    totals = {
        day: float_or_zero(sol_by_day.get(day)) + float_or_zero(parking_by_day.get(day))
        for day in sol_by_day.keys() | parking_by_day.keys()
    }
    totals = {day: total for day, total in totals.items() if total > 0}
    if not totals:
        return {}

    ordered_totals = sorted(totals.values(), reverse=True)
    year_rank_by_total: Dict[float, int] = {}
    for index, total in enumerate(ordered_totals, start=1):
        year_rank_by_total.setdefault(total, index)

    weekday_totals: Dict[int, list[float]] = {}
    for day, total in totals.items():
        weekday_totals.setdefault(day.weekday(), []).append(total)

    weekday_rank_by_total: Dict[int, Dict[float, int]] = {}
    for weekday, values in weekday_totals.items():
        ranks: Dict[float, int] = {}
        for index, total in enumerate(sorted(values, reverse=True), start=1):
            ranks.setdefault(total, index)
        weekday_rank_by_total[weekday] = ranks

    return {
        day: {
            "year_rank": year_rank_by_total[total],
            "year_day_count": len(totals),
            "weekday_rank": weekday_rank_by_total[day.weekday()][total],
            "weekday_day_count": len(weekday_totals[day.weekday()]),
        }
        for day, total in totals.items()
    }


@dataclass
class Dependencies:
    age_label: Callable[..., Any]
    async_session: Callable[..., Any]
    average_value: Callable[..., Any]
    latest_timestamp_from: Callable[..., Any]
    normalize_month: Callable[..., Any]
    weather_from_rows: Callable[..., Any]


def create_service(dependencies: Dependencies):

    def minutes_since(value: Optional[datetime], now_value: Optional[datetime] = None) -> Optional[int]:
        if not value:
            return None
        value = normalize_local_naive(value)
        now_value = normalize_local_naive(now_value) or local_now_naive()
        if not value:
            return None
        delta = now_value - value
        return max(0, int(delta.total_seconds() // 60))

    def build_now_status(latest_sample, latest_light_sample, latest_light, latest_yr_sample=None):
        average_value = dependencies.average_value
        latest_timestamp_from = dependencies.latest_timestamp_from
        weather_from_rows = dependencies.weather_from_rows
        indoor_values = [
            {"label": "1.etg", "value": latest_sample.temp_1etg if latest_sample else None},
            {"label": "2.etg", "value": latest_sample.temp_2etg if latest_sample else None},
            {"label": "VIP", "value": latest_sample.temp_vip if latest_sample else None},
            {"label": "Kjeller", "value": latest_sample.temp_kjeller if latest_sample else None},
        ]
        humidity_values = [
            {"label": "1.etg", "value": latest_sample.humidity_1etg if latest_sample else None},
            {"label": "2.etg", "value": latest_sample.humidity_2etg if latest_sample else None},
            {"label": "VIP", "value": latest_sample.humidity_vip if latest_sample else None},
            {"label": "Loft", "value": latest_sample.humidity_loft if latest_sample else None},
            {"label": "Kjeller", "value": latest_sample.humidity_kjeller if latest_sample else None},
            {"label": "Yr", "value": latest_sample.humidity_yr if latest_sample else None},
        ]
        outdoor_ute = None
        outdoor_yr = None
        if latest_sample:
            outdoor_ute = latest_sample.temp_ute if latest_sample.temp_ute is not None else latest_sample.temp_ute_netatmo
            outdoor_yr = latest_sample.temp_yr
        outdoor_yr_api = latest_yr_sample.air_temperature if latest_yr_sample else None
        outdoor_values = [
            {"label": "Ute", "value": outdoor_ute},
            {"label": "Yr HC3", "value": outdoor_yr},
            {"label": "Yr API", "value": outdoor_yr_api},
        ]
        lux = None
        if latest_light_sample and latest_light_sample.lux is not None:
            lux = latest_light_sample.lux
        elif latest_light and latest_light.lux is not None:
            lux = latest_light.lux
        timestamp = latest_timestamp_from(latest_sample, latest_light_sample, latest_light, latest_yr_sample)
        weather = weather_from_rows(latest_yr_sample, latest_light_sample, latest_sample, latest_light)
        outdoor_avg_values = [outdoor_ute, outdoor_yr_api if outdoor_yr_api is not None else outdoor_yr]
        weather_card = {
            "text": weather,
            "temperature": latest_yr_sample.air_temperature if latest_yr_sample else None,
            "temp_6h": latest_yr_sample.temp_6h if latest_yr_sample else None,
            "humidity": latest_yr_sample.relative_humidity if latest_yr_sample else None,
            "wind": latest_yr_sample.wind_speed if latest_yr_sample else None,
            "precipitation": latest_yr_sample.precipitation_next_1h if latest_yr_sample else None,
            "clouds": latest_yr_sample.cloud_area_fraction if latest_yr_sample else None,
            "basement_humidity": latest_sample.humidity_kjeller if latest_sample else None,
            "timestamp": latest_yr_sample.timestamp if latest_yr_sample else None,
            "api_updated_at": latest_yr_sample.api_updated_at if latest_yr_sample else None,
            "expires_at": latest_yr_sample.expires_at if latest_yr_sample else None,
            "next_fetch_after": latest_yr_sample.next_fetch_after if latest_yr_sample else None,
        }
        return {
            "timestamp": timestamp,
            "mode": latest_sample.mode if latest_sample else None,
            "indoor_avg": average_value([item["value"] for item in indoor_values]),
            "indoor_values": indoor_values,
            "humidity_values": humidity_values,
            "outdoor_avg": average_value(outdoor_avg_values),
            "outdoor_values": outdoor_values,
            "lux": lux,
            "weather": weather,
            "weather_card": weather_card,
            "has_data": any(
                value is not None
                for value in [
                    lux,
                    weather,
                    *[item["value"] for item in indoor_values],
                    *[item["value"] for item in outdoor_values],
                ]
            ),
        }

    def freshness_item(name: str, row, expected_minutes: int, warning_minutes: Optional[int] = None):
        age_label = dependencies.age_label
        warning_minutes = warning_minutes or expected_minutes * 2
        stamp = row.timestamp if row else None
        age_minutes = minutes_since(stamp)
        if age_minutes is None:
            status = "bad"
            status_text = "Mangler"
        elif age_minutes <= expected_minutes:
            status = "ok"
            status_text = "OK"
        elif age_minutes <= warning_minutes:
            status = "warn"
            status_text = "Treg"
        else:
            status = "bad"
            status_text = "Gammel"
        return {
            "name": name,
            "age": age_label(age_minutes),
            "status": status,
            "status_text": status_text,
            "timestamp": stamp,
        }

    def dashboard_compare_detail(
        label: str,
        current_count: Any,
        current_paid: Any,
        previous_count: Any,
        previous_paid: Any,
    ) -> str:
        count_delta = float_or_zero(current_count) - float_or_zero(previous_count)
        paid_delta = float_or_zero(current_paid) - float_or_zero(previous_paid)
        return f"vs {label}: {format_signed_short_number(count_delta)} stk / {format_signed_short_number(paid_delta)} kr"

    def dashboard_compare_value(current: Any, previous: Any) -> str:
        return f"{format_short_number(current)}/{format_short_number(previous)}"

    def dashboard_money_compare(current: Any, previous: Any) -> str:
        return f"{format_short_number(current)}/{format_short_number(previous)} kr"

    def operating_window(now: datetime) -> Dict[str, Any]:
        open_at = datetime.combine(now.date(), time.min).replace(hour=7)
        close_at = datetime.combine(now.date(), time.min).replace(hour=23)
        if now < open_at:
            return {"label": "Stengt", "detail": "Åpner 07:00", "progress": 0}
        if now >= close_at:
            return {"label": "Stengt", "detail": "Stengte 23:00", "progress": 100}
        total_seconds = (close_at - open_at).total_seconds()
        progress = int(((now - open_at).total_seconds() / total_seconds) * 100)
        return {"label": "Åpent", "detail": "Stenger 23:00", "progress": max(0, min(100, progress))}

    def dashboard_alert(level: str, title: str, detail: str, href: str = "/admin/datakilder") -> Dict[str, str]:
        return {"level": level, "title": title, "detail": detail, "href": href}

    def api_revenue_day(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "day": row["day"].isoformat(),
            "dayLabel": row["day_label"],
            "weekday": row["weekday"],
            "sol": row["sol"],
            "solCount": row["sol_count"],
            "parking": row["parking"],
            "parkingCount": row["parking_count"],
            "total": row["total"],
            "isToday": row["is_today"],
            "isWeekend": row["is_weekend"],
            "yearRank": row.get("year_rank"),
            "yearDayCount": row.get("year_day_count"),
            "weekdayRank": row.get("weekday_rank"),
            "weekdayDayCount": row.get("weekday_day_count"),
        }

    async def build_revenue_month_context(month: Optional[str] = None) -> Dict[str, Any]:
        async_session = dependencies.async_session
        normalize_month = dependencies.normalize_month
        today = local_now_naive().date()
        month_start = normalize_month(month, today)
        next_month = add_months(month_start, 1)
        previous_month = add_months(month_start, -1)
        days_in_month = (next_month - month_start).days
        year_start = date(month_start.year, 1, 1)
        year_end = date(month_start.year + 1, 1, 1)
        if month_start.year < today.year:
            ranking_end = year_end
        elif month_start.year == today.year:
            ranking_end = today + timedelta(days=1)
        else:
            ranking_end = year_start
        async with async_session() as session:
            sol_rows = (
                await session.execute(
                    select(
                        Sun2TanningSession.stat_date.label("day"),
                        func.count(Sun2TanningSession.id).label("count"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("amount"),
                    )
                    .where(Sun2TanningSession.stat_date >= year_start)
                    .where(Sun2TanningSession.stat_date < ranking_end)
                    .group_by(Sun2TanningSession.stat_date)
                )
            ).mappings().all()
            parking_day = cast(ParkingSession.start_time, Date)
            parking_rows = (
                await session.execute(
                    select(
                        parking_day.label("day"),
                        func.count(ParkingSession.id).label("count"),
                        func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("amount"),
                    )
                    .where(ParkingSession.start_time >= datetime.combine(year_start, time.min))
                    .where(ParkingSession.start_time < datetime.combine(ranking_end, time.min))
                    .group_by(parking_day)
                )
            ).mappings().all()

        sol_by_day = {row["day"]: float_or_zero(row["amount"]) for row in sol_rows}
        sol_count_by_day = {row["day"]: int_or_zero(row["count"]) for row in sol_rows}
        parking_by_day = {row["day"]: float_or_zero(row["amount"]) for row in parking_rows}
        parking_count_by_day = {row["day"]: int_or_zero(row["count"]) for row in parking_rows}
        day_rankings = _revenue_day_rankings(sol_by_day, parking_by_day)
        rows = []
        for offset in range(days_in_month):
            day = month_start + timedelta(days=offset)
            sol_amount = sol_by_day.get(day, 0.0)
            parking_amount = parking_by_day.get(day, 0.0)
            rows.append(
                {
                    "day": day,
                    "day_label": day.strftime("%d.%m"),
                    "weekday": ["Man", "Tir", "Ons", "Tor", "Fre", "Lor", "Son"][day.weekday()],
                    "sol": sol_amount,
                    "sol_count": sol_count_by_day.get(day, 0),
                    "parking": parking_amount,
                    "parking_count": parking_count_by_day.get(day, 0),
                    "total": sol_amount + parking_amount,
                    "is_today": day == today,
                    "is_weekend": day.weekday() >= 5,
                    **day_rankings.get(day, {}),
                }
            )
        max_total = max([row["total"] for row in rows] + [1.0])
        for row in rows:
            row["sol_pct"] = 0.0 if row["sol"] <= 0 else max(4.0, row["sol"] / max_total * 100)
            row["parking_pct"] = 0.0 if row["parking"] <= 0 else max(4.0, row["parking"] / max_total * 100)
            if row["sol_pct"] + row["parking_pct"] > 100:
                scale = 100.0 / (row["sol_pct"] + row["parking_pct"])
                row["sol_pct"] *= scale
                row["parking_pct"] *= scale
        total_sol = sum(row["sol"] for row in rows)
        total_parking = sum(row["parking"] for row in rows)
        if month_start <= today < next_month:
            average_day_count = (today - month_start).days + 1
        elif month_start < today.replace(day=1):
            average_day_count = days_in_month
        else:
            average_day_count = 0
        average_per_day = (total_sol + total_parking) / average_day_count if average_day_count else 0.0
        top_day = max(rows, key=lambda row: row["total"], default=None)
        today_row = next((row for row in rows if row["day"] == today), None)
        return {
            "rows": rows,
            "summary": {
                "label": month_label(month_start),
                "month": month_start.strftime("%Y-%m"),
                "previous_month": previous_month.strftime("%Y-%m"),
                "next_month": next_month.strftime("%Y-%m"),
                "current_month": today.replace(day=1).strftime("%Y-%m"),
                "total": total_sol + total_parking,
                "sol": total_sol,
                "parking": total_parking,
                "sol_count": sum(row["sol_count"] for row in rows),
                "parking_count": sum(row["parking_count"] for row in rows),
                "average_day_count": average_day_count,
                "average_per_day": average_per_day,
                "max_total": max_total,
                "top_day": top_day,
                "today_row": today_row,
            },
        }

    def operations_area_status(
        key: str,
        label: str,
        status: str,
        status_label: str,
        detail: str,
        href: str,
        updated_at: Optional[datetime],
        metrics: list[Dict[str, Any]],
        items: list[Dict[str, Any]],
        issues: Optional[list[str]] = None,
        recent_jobs: Optional[list[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return {
            "key": key,
            "label": label,
            "status": status,
            "statusLabel": status_label,
            "detail": detail,
            "href": href,
            "updatedAt": api_local_iso(updated_at),
            "metrics": metrics,
            "items": items,
            "issues": issues or [],
            "recentJobs": recent_jobs or [],
        }

    def operations_metric(label: str, value: Any, detail: str = "") -> Dict[str, Any]:
        return {"label": label, "value": value, "detail": detail}

    def operations_switch_item(label: str, state: Optional[bool]) -> Dict[str, Any]:
        return {
            "label": label,
            "value": "På" if state is True else "Av" if state is False else "Ukjent",
            "state": "on" if state is True else "off" if state is False else "unknown",
        }

    def api_revenue_weekly_chart(summaries: Dict[str, Any]) -> Dict[str, Any]:
        chart_rows = summaries.get("weekly_chart", [])

        def metric_series(metric: str) -> list[Dict[str, Any]]:
            return [
                {
                    "name": row["year"],
                    "data": row[metric],
                    "color": row.get("color"),
                    "unit": "kr" if metric == "revenue" else "stk",
                }
                for row in chart_rows
            ]

        current_year = local_now_naive().year
        return api_chart(
            "Sum omsetning ukesutvikling",
            [str(week) for week in range(1, 54)],
            metric_series("revenue"),
            "Samlet omsetning fra soling og parkering.",
            "line",
            360,
            metrics=[
                {"key": "revenue", "label": "Omsetning", "unit": "kr", "series": metric_series("revenue")},
            ],
            default_metric="revenue",
            default_visible_series=[str(current_year), str(current_year - 1)],
        )

    def api_revenue_summary_row(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "period": item.get("period"),
            "period_label": item.get("period_label") or item.get("period"),
            "sun_paid": round(float_or_zero(item.get("sun_paid")), 2),
            "parking_paid": round(float_or_zero(item.get("parking_paid")), 2),
            "total_paid": round(float_or_zero(item.get("total_paid")), 2),
            "sun_count": int_or_zero(item.get("sun_count")),
            "parking_count": int_or_zero(item.get("parking_count")),
            "total_count": int_or_zero(item.get("total_count")),
        }

    def api_revenue_overview_tables(summaries: Dict[str, Any]) -> list[Dict[str, Any]]:
        revenue_columns = ["period_label", "total_paid", "parking_paid", "parking_count", "sun_paid", "sun_count"]
        return [
            api_table("Topp dager omsetning", revenue_columns, [api_revenue_summary_row(row) for row in summaries.get("top_days", [])]),
            api_table("Topp uker omsetning", revenue_columns, [api_revenue_summary_row(row) for row in summaries.get("top_weeks", [])]),
            api_table("Topp m\u00e5neder omsetning", ["period", *revenue_columns[1:]], [api_revenue_summary_row(row) for row in summaries.get("top_months", [])]),
        ]

    return {
        "api_revenue_day": api_revenue_day,
        "api_revenue_overview_tables": api_revenue_overview_tables,
        "api_revenue_summary_row": api_revenue_summary_row,
        "api_revenue_weekly_chart": api_revenue_weekly_chart,
        "build_now_status": build_now_status,
        "build_revenue_month_context": build_revenue_month_context,
        "dashboard_alert": dashboard_alert,
        "dashboard_compare_detail": dashboard_compare_detail,
        "dashboard_compare_value": dashboard_compare_value,
        "dashboard_money_compare": dashboard_money_compare,
        "freshness_item": freshness_item,
        "minutes_since": minutes_since,
        "operating_window": operating_window,
        "operations_area_status": operations_area_status,
        "operations_metric": operations_metric,
        "operations_switch_item": operations_switch_item,
    }
