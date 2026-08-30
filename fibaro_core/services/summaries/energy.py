"""Energy summary calculations; sessions are supplied by the caller."""

from typing import Any, Dict, Optional

from sqlalchemy import case, func, select

from fibaro_core.models.energy import EnergyHourlyConsumption
from value_parsing import float_or_zero, int_or_zero


def empty_energy_summary(period: str) -> Dict[str, Any]:
    return {
        "period": period,
        "period_label": period,
        "consumption_kwh": 0.0,
        "production_kwh": 0.0,
        "hours_count": 0,
        "estimated_hours_count": 0,
        "days": set(),
    }


def add_energy_row_to_summary(summary: Dict[str, Any], row: Any) -> None:
    summary["consumption_kwh"] += row.consumption_kwh or 0
    summary["production_kwh"] += row.production_kwh or 0
    summary["hours_count"] += 1
    if row.is_estimated:
        summary["estimated_hours_count"] += 1
    if row.stat_date:
        summary["days"].add(row.stat_date)


def finalize_energy_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(summary)
    summary["days_count"] = len(summary.pop("days", []))
    return summary


def build_energy_summaries(rows: list[Any]) -> Dict[str, Any]:
    daily: Dict[str, Dict[str, Any]] = {}
    monthly: Dict[str, Dict[str, Any]] = {}
    yearly: Dict[str, Dict[str, Any]] = {}
    total = empty_energy_summary("Totalt")
    first_at = None
    last_at = None

    for row in rows:
        if not row.measured_at:
            continue
        first_at = row.measured_at if first_at is None else min(first_at, row.measured_at)
        last_at = row.measured_at if last_at is None else max(last_at, row.measured_at)
        day_key = row.stat_date.isoformat()
        month_key = f"{row.year:04d}-{row.month:02d}"
        year_key = str(row.year)
        daily.setdefault(day_key, empty_energy_summary(day_key))
        monthly.setdefault(month_key, empty_energy_summary(month_key))
        yearly.setdefault(year_key, empty_energy_summary(year_key))
        daily[day_key]["period_label"] = row.stat_date.strftime("%d.%m.%Y")
        add_energy_row_to_summary(daily[day_key], row)
        add_energy_row_to_summary(monthly[month_key], row)
        add_energy_row_to_summary(yearly[year_key], row)
        add_energy_row_to_summary(total, row)

    daily_items = [finalize_energy_summary(daily[key]) for key in sorted(daily, reverse=True)]
    monthly_items = [finalize_energy_summary(monthly[key]) for key in sorted(monthly, reverse=True)]
    yearly_items = [finalize_energy_summary(yearly[key]) for key in sorted(yearly, reverse=True)]
    top_sort = lambda item: (item["consumption_kwh"], item["hours_count"])

    return {
        "daily": daily_items,
        "monthly": monthly_items,
        "yearly": yearly_items,
        "top_days": sorted(daily_items, key=top_sort, reverse=True)[:10],
        "top_months": sorted(monthly_items, key=top_sort, reverse=True)[:10],
        "total": finalize_energy_summary(total),
        "first_at": first_at,
        "last_at": last_at,
    }


def finalized_energy_aggregate(row: Dict[str, Any], period: str, period_label: Optional[str] = None) -> Dict[str, Any]:
    item = empty_energy_summary(period)
    item["period_label"] = period_label or period
    item["consumption_kwh"] = float_or_zero(row.get("consumption_kwh"))
    item["production_kwh"] = float_or_zero(row.get("production_kwh"))
    item["hours_count"] = int_or_zero(row.get("hours_count"))
    item["estimated_hours_count"] = int_or_zero(row.get("estimated_hours_count"))
    item["days_count"] = int_or_zero(row.get("days_count"))
    return item


def energy_sum_columns() -> list[Any]:
    return [
        func.coalesce(func.sum(EnergyHourlyConsumption.consumption_kwh), 0).label("consumption_kwh"),
        func.coalesce(func.sum(EnergyHourlyConsumption.production_kwh), 0).label("production_kwh"),
        func.count(EnergyHourlyConsumption.id).label("hours_count"),
        func.coalesce(
            func.sum(case((EnergyHourlyConsumption.is_estimated.is_(True), 1), else_=0)),
            0,
        ).label("estimated_hours_count"),
    ]


def empty_fast_energy_summary(period: str, period_label: Optional[str] = None) -> Dict[str, Any]:
    return {
        "period": period,
        "period_label": period_label or period,
        "consumption_kwh": 0.0,
        "production_kwh": 0.0,
        "hours_count": 0,
        "estimated_hours_count": 0,
        "days_count": 0,
    }


def add_fast_energy_summary(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    target["consumption_kwh"] += float_or_zero(source.get("consumption_kwh"))
    target["production_kwh"] += float_or_zero(source.get("production_kwh"))
    target["hours_count"] += int_or_zero(source.get("hours_count"))
    target["estimated_hours_count"] += int_or_zero(source.get("estimated_hours_count"))
    target["days_count"] += int_or_zero(source.get("days_count"))


async def build_energy_summaries_fast(session) -> Dict[str, Any]:
    daily_rows = (
        await session.execute(
            select(
                EnergyHourlyConsumption.stat_date.label("stat_date"),
                *energy_sum_columns(),
            )
            .group_by(EnergyHourlyConsumption.stat_date)
            .order_by(EnergyHourlyConsumption.stat_date.desc())
        )
    ).mappings().all()

    daily_items = []
    monthly: Dict[str, Dict[str, Any]] = {}
    yearly: Dict[str, Dict[str, Any]] = {}
    total = empty_fast_energy_summary("Totalt")
    first_at = None
    last_at = None

    for row in daily_rows:
        stat_date = row.get("stat_date")
        if not stat_date:
            continue
        item = finalized_energy_aggregate(dict(row, days_count=1), stat_date.isoformat(), stat_date.strftime("%d.%m.%Y"))
        daily_items.append(item)
        month_key = stat_date.strftime("%Y-%m")
        year_key = str(stat_date.year)
        monthly.setdefault(month_key, empty_fast_energy_summary(month_key))
        yearly.setdefault(year_key, empty_fast_energy_summary(year_key))
        add_fast_energy_summary(monthly[month_key], item)
        add_fast_energy_summary(yearly[year_key], item)
        add_fast_energy_summary(total, item)

    bounds = (
        await session.execute(
            select(
                func.min(EnergyHourlyConsumption.measured_at).label("first_at"),
                func.max(EnergyHourlyConsumption.measured_at).label("last_at"),
            )
        )
    ).mappings().first() or {}
    first_at = bounds.get("first_at")
    last_at = bounds.get("last_at")
    monthly_items = [monthly[key] for key in sorted(monthly, reverse=True)]
    yearly_items = [yearly[key] for key in sorted(yearly, reverse=True)]
    top_sort = lambda item: (item["consumption_kwh"], item["hours_count"])

    return {
        "daily": daily_items,
        "monthly": monthly_items,
        "yearly": yearly_items,
        "top_days": sorted(daily_items, key=top_sort, reverse=True)[:10],
        "top_months": sorted(monthly_items, key=top_sort, reverse=True)[:10],
        "total": total,
        "first_at": first_at,
        "last_at": last_at,
    }
