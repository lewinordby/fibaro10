"""Combined revenue, rankings and year curves without database access."""

from datetime import date, timedelta
from typing import Any, Dict, Optional

from fibaro_core.services.summaries.periods import days_in_year
from value_parsing import float_or_zero, int_or_zero


def combine_business_summaries(sun: Dict[str, Any], parking: Dict[str, Any]) -> Dict[str, Any]:
    def combine_items(left: list[Dict[str, Any]], right: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        combined: Dict[str, Dict[str, Any]] = {}
        for item in left:
            key = item["period"]
            combined.setdefault(
                key,
                {
                    "period": key,
                    "period_label": item.get("period_label", key),
                    "sun_paid": 0.0,
                    "parking_paid": 0.0,
                    "sun_count": 0,
                    "parking_count": 0,
                },
            )
            combined[key]["sun_paid"] += float_or_zero(item.get("totalt_inntjent_kr"))
            combined[key]["sun_count"] += int_or_zero(item.get("totalt_antall_solinger"))
        for item in right:
            key = item["period"]
            combined.setdefault(
                key,
                {
                    "period": key,
                    "period_label": item.get("period_label", key),
                    "sun_paid": 0.0,
                    "parking_paid": 0.0,
                    "sun_count": 0,
                    "parking_count": 0,
                },
            )
            combined[key]["parking_paid"] += float_or_zero(item.get("paid"))
            combined[key]["parking_count"] += int_or_zero(item.get("sessions"))
        for item in combined.values():
            item["total_paid"] = item["sun_paid"] + item["parking_paid"]
            item["total_count"] = item["sun_count"] + item["parking_count"]
        return list(combined.values())

    daily = combine_items(sun.get("daily", []), parking.get("daily", []))
    monthly = combine_items(sun.get("monthly", []), parking.get("monthly", []))
    yearly = combine_items(sun.get("yearly", []), parking.get("yearly", []))
    weekly_items_by_period: Dict[str, Dict[str, Any]] = {}
    for item in daily:
        try:
            stat_day = date.fromisoformat(str(item.get("period") or ""))
        except ValueError:
            continue
        iso_year, iso_week, _ = stat_day.isocalendar()
        week_start = date.fromisocalendar(iso_year, iso_week, 1)
        week_end = date.fromisocalendar(iso_year, iso_week, 7)
        period = f"{iso_year}-W{iso_week:02d}"
        if week_start.year == week_end.year:
            date_range = f"{week_start:%d.%m}-{week_end:%d.%m.%Y}"
        else:
            date_range = f"{week_start:%d.%m.%Y}-{week_end:%d.%m.%Y}"
        weekly_item = weekly_items_by_period.setdefault(
            period,
            {
                "period": period,
                "period_label": f"Uke {iso_week}, {iso_year} ({date_range})",
                "sun_paid": 0.0,
                "parking_paid": 0.0,
                "sun_count": 0,
                "parking_count": 0,
                "total_paid": 0.0,
                "total_count": 0,
            },
        )
        for field in ("sun_paid", "parking_paid", "total_paid"):
            weekly_item[field] += float_or_zero(item.get(field))
        for field in ("sun_count", "parking_count", "total_count"):
            weekly_item[field] += int_or_zero(item.get(field))
    weekly_items = list(weekly_items_by_period.values())
    weekly: Dict[str, Dict[str, Any]] = {}
    palette = ["#4e8793", "#d59a18", "#071943", "#52a464", "#df705d", "#726189", "#2f8fa3", "#8b5cf6"]
    for source in (sun.get("weekly_chart", []), parking.get("weekly_chart", [])):
        for series in source:
            year = str(series.get("year") or "")
            if not year.isdigit() or int(year) < 2023:
                continue
            weekly.setdefault(
                year,
                {
                    "year": year,
                    "revenue": [0.0 for _ in range(53)],
                    "count": [0 for _ in range(53)],
                    "has_value": [False for _ in range(53)],
                },
            )
            for index in range(53):
                revenue_values = series.get("revenue") or []
                count_values = series.get("count") or []
                revenue = revenue_values[index] if index < len(revenue_values) else None
                count = count_values[index] if index < len(count_values) else None
                if revenue is not None:
                    weekly[year]["revenue"][index] += float_or_zero(revenue)
                    weekly[year]["has_value"][index] = True
                if count is not None:
                    weekly[year]["count"][index] += int_or_zero(count)
                    weekly[year]["has_value"][index] = True
    weekly_chart = []
    for index, year in enumerate(sorted(weekly.keys())):
        item = weekly[year]
        weekly_chart.append(
            {
                "year": year,
                "color": palette[index % len(palette)],
                "revenue": [
                    round(item["revenue"][week], 2) if item["has_value"][week] else None
                    for week in range(53)
                ],
                "count": [
                    item["count"][week] if item["has_value"][week] else None
                    for week in range(53)
                ],
            }
        )
    top_sort = lambda item: (item["total_paid"], item["total_count"])
    return {
        "daily": sorted(daily, key=lambda item: str(item.get("period") or ""), reverse=True),
        "weekly": sorted(weekly_items, key=lambda item: str(item.get("period") or ""), reverse=True),
        "monthly": sorted(monthly, key=lambda item: str(item.get("period") or ""), reverse=True),
        "top_days": sorted(daily, key=top_sort, reverse=True)[:20],
        "top_weeks": sorted(weekly_items, key=top_sort, reverse=True)[:20],
        "top_months": sorted(monthly, key=top_sort, reverse=True)[:20],
        "yearly": sorted(yearly, key=lambda item: str(item.get("period") or ""), reverse=True),
        "weekly_chart": weekly_chart,
    }


def period_rank_summary(
    items: list[Dict[str, Any]],
    current_value_raw: Any,
    current_period: str,
    period_label: str,
    value_key: str,
    basis: str,
) -> Optional[Dict[str, Any]]:
    current_value = float_or_zero(current_value_raw)
    historical_totals = [
        float_or_zero(item.get(value_key))
        for item in items
        if str(item.get("period") or "") < current_period and float_or_zero(item.get(value_key)) > 0
    ]
    if not historical_totals:
        return None

    rank = sum(1 for total in historical_totals if total > current_value) + 1
    return {
        "rank": rank,
        "label": f"{rank}. beste",
        "basis": f"Rangert mot historiske hele {period_label} etter {basis}",
        "totalPeriods": len(historical_totals) + 1,
        "bestTotal": round(max(historical_totals), 2),
        "currentTotal": round(current_value, 2),
    }


def revenue_period_rank_summary(
    items: list[Dict[str, Any]],
    current_total: Any,
    current_period: str,
    period_label: str,
) -> Optional[Dict[str, Any]]:
    result = period_rank_summary(items, current_total, current_period, period_label, "total_paid", "omsetning")
    if result is not None:
        result["basis"] = f"Rangert mot historiske hele {period_label}"
    return result


def count_period_rank_summary(
    items: list[Dict[str, Any]],
    current_count: Any,
    current_period: str,
    period_label: str,
    basis: str,
) -> Optional[Dict[str, Any]]:
    return period_rank_summary(items, current_count, current_period, period_label, "total_count", basis)


def revenue_day_rank_summary(summaries: Dict[str, Any], current_total: Any, today: date) -> Optional[Dict[str, Any]]:
    result = revenue_period_rank_summary(summaries.get("daily", []), current_total, today.isoformat(), "dager")
    if result is not None:
        result["totalDays"] = result["totalPeriods"]
    return result


def count_day_rank_summary(
    summaries: Dict[str, Any],
    current_count: Any,
    today: date,
    basis: str,
) -> Optional[Dict[str, Any]]:
    result = count_period_rank_summary(summaries.get("daily", []), current_count, today.isoformat(), "dager", basis)
    if result is not None:
        result["totalDays"] = result["totalPeriods"]
    return result


def revenue_daily_by_year(summaries: Dict[str, Any]) -> Dict[int, Dict[int, Dict[str, Any]]]:
    by_year: Dict[int, Dict[int, Dict[str, Any]]] = {}
    for item in summaries.get("daily", []):
        period = str(item.get("period") or "")
        try:
            stat_date = date.fromisoformat(period)
        except ValueError:
            continue
        by_year.setdefault(stat_date.year, {})[stat_date.timetuple().tm_yday] = {
            "date": stat_date,
            "amount": float_or_zero(item.get("total_paid")),
        }
    return by_year


def revenue_year_series(
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
    points = []
    days_with_data = 0
    for day_number in range(1, visible_day + 1):
        row = daily_rows.get(day_number)
        if row:
            days_with_data += 1
            cumulative_amount += float_or_zero(row.get("amount"))
        point_date = date(year, 1, 1) + timedelta(days=day_number - 1)
        points.append(
            {
                "day": day_number,
                "date": point_date.isoformat(),
                "label": point_date.strftime("%d.%m"),
                "amount": round(float_or_zero(row.get("amount")) if row else 0.0, 2),
                "count": 0,
                "minutes": 0.0,
                "cumulativeAmount": round(cumulative_amount, 2),
                "cumulativeCount": 0,
                "cumulativeMinutes": 0.0,
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
        "totalCount": 0,
        "totalMinutes": 0.0,
        "points": points,
    }


def revenue_year_comparison_delta(current: Dict[str, Any], comparison: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "amount": round(float_or_zero(current.get("totalAmount")) - float_or_zero(comparison.get("totalAmount")), 2),
        "count": 0,
        "minutes": 0.0,
    }
