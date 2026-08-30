"""Existing annual comparison payloads, independent of runtime and cache."""

from datetime import date, datetime, timedelta
from typing import Any, Dict
from fibaro_core.services.summaries.periods import days_in_year, year_comparison_navigation
from time_formatting import api_local_iso
from fibaro_core.services.summaries.sun import sun2_daily_by_year, sun2_year_series, sun2_year_comparison_delta
from fibaro_core.services.summaries.parking import parking_daily_by_year, parking_year_series, parking_year_comparison_delta
from fibaro_core.services.summaries.revenue import revenue_daily_by_year, revenue_year_series, revenue_year_comparison_delta


YEAR_COMPARISON_COLORS = ["#f59e0b", "#64748b", "#0f766e", "#7c3aed", "#be123c", "#0891b2", "#ea580c", "#2563eb"]


def build_sun2_year_comparison(summaries: Dict[str, Any], now_dt: datetime, anchor_year: int) -> Dict[str, Any]:
    today = now_dt.date()
    current_year = today.year
    comparison_year = anchor_year - 1
    selected_as_of_day = today.timetuple().tm_yday if anchor_year == current_year else days_in_year(anchor_year)
    comparison_as_of_day = min(selected_as_of_day, days_in_year(comparison_year))
    selected_as_of_date = date(anchor_year, 1, 1) + timedelta(days=selected_as_of_day - 1)
    comparison_as_of_date = date(comparison_year, 1, 1) + timedelta(days=comparison_as_of_day - 1)
    daily_by_year = sun2_daily_by_year(summaries)
    selected_series = sun2_year_series(daily_by_year, anchor_year, selected_as_of_day, "current", "#f59e0b")
    comparison_series = sun2_year_series(daily_by_year, comparison_year, comparison_as_of_day, "comparison", "#64748b")
    comparison_full_series = sun2_year_series(
        daily_by_year,
        comparison_year,
        days_in_year(comparison_year),
        "comparison-full",
        "#94a3b8",
    )
    available_years = sorted(set(daily_by_year.keys()) | {anchor_year, comparison_year}, reverse=True)
    all_series = []
    for index, series_year in enumerate(available_years):
        series_as_of_day = today.timetuple().tm_yday if series_year == current_year else days_in_year(series_year)
        if series_year == anchor_year:
            source = "current"
        elif series_year == comparison_year:
            source = "comparison"
        else:
            source = "reference"
        all_series.append(
            sun2_year_series(
                daily_by_year,
                series_year,
                series_as_of_day,
                source,
                YEAR_COMPARISON_COLORS[index % len(YEAR_COMPARISON_COLORS)],
            )
        )
    axis_days = max([selected_series["daysInYear"], comparison_full_series["daysInYear"], *(item["daysInYear"] for item in all_series)])
    month_names = ["Jan", "Feb", "Mar", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Des"]
    ticks = []
    for month_index, month_name in enumerate(month_names, start=1):
        tick_date = date(anchor_year, month_index, 1)
        ticks.append({"label": month_name, "day": tick_date.timetuple().tm_yday})
    return {
        "generatedAt": api_local_iso(now_dt),
        "title": "Soling · Årssammenligning",
        "anchorYear": anchor_year,
        "comparisonYear": comparison_year,
        "navigation": year_comparison_navigation(anchor_year, current_year),
        "axis": {"days": axis_days, "ticks": ticks},
        "availableYears": available_years,
        "series": all_series,
        "selected": selected_series,
        "comparison": comparison_series,
        "comparisonFull": comparison_full_series,
        "delta": sun2_year_comparison_delta(selected_series, comparison_series),
        "asOf": {
            "selectedLabel": "Hittil i år" if anchor_year == current_year else "Hele året",
            "selectedDate": selected_as_of_date.isoformat(),
            "comparisonLabel": "Til samme dag i året",
            "comparisonDate": comparison_as_of_date.isoformat(),
        },
    }


def build_parking_year_comparison(summaries: Dict[str, Any], now_dt: datetime, anchor_year: int) -> Dict[str, Any]:
    today = now_dt.date()
    current_year = today.year
    comparison_year = anchor_year - 1
    selected_as_of_day = today.timetuple().tm_yday if anchor_year == current_year else days_in_year(anchor_year)
    comparison_as_of_day = min(selected_as_of_day, days_in_year(comparison_year))
    selected_as_of_date = date(anchor_year, 1, 1) + timedelta(days=selected_as_of_day - 1)
    comparison_as_of_date = date(comparison_year, 1, 1) + timedelta(days=comparison_as_of_day - 1)
    daily_by_year = parking_daily_by_year(summaries)
    selected_series = parking_year_series(daily_by_year, anchor_year, selected_as_of_day, "current", "#2563eb")
    comparison_series = parking_year_series(daily_by_year, comparison_year, comparison_as_of_day, "comparison", "#64748b")
    comparison_full_series = parking_year_series(
        daily_by_year,
        comparison_year,
        days_in_year(comparison_year),
        "comparison-full",
        "#94a3b8",
    )
    available_years = sorted(set(daily_by_year.keys()) | {anchor_year, comparison_year}, reverse=True)
    parking_colors = ["#2563eb", "#64748b", "#0f766e", "#7c3aed", "#be123c", "#0891b2", "#ea580c", "#f59e0b"]
    all_series = []
    for index, series_year in enumerate(available_years):
        series_as_of_day = today.timetuple().tm_yday if series_year == current_year else days_in_year(series_year)
        if series_year == anchor_year:
            source = "current"
        elif series_year == comparison_year:
            source = "comparison"
        else:
            source = "reference"
        all_series.append(
            parking_year_series(
                daily_by_year,
                series_year,
                series_as_of_day,
                source,
                parking_colors[index % len(parking_colors)],
            )
        )
    axis_days = max([selected_series["daysInYear"], comparison_full_series["daysInYear"], *(item["daysInYear"] for item in all_series)])
    month_names = ["Jan", "Feb", "Mar", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Des"]
    ticks = []
    for month_index, month_name in enumerate(month_names, start=1):
        tick_date = date(anchor_year, month_index, 1)
        ticks.append({"label": month_name, "day": tick_date.timetuple().tm_yday})
    return {
        "generatedAt": api_local_iso(now_dt),
        "title": "Parkering · Årssammenligning",
        "anchorYear": anchor_year,
        "comparisonYear": comparison_year,
        "navigation": year_comparison_navigation(anchor_year, current_year),
        "axis": {"days": axis_days, "ticks": ticks},
        "availableYears": available_years,
        "series": all_series,
        "selected": selected_series,
        "comparison": comparison_series,
        "comparisonFull": comparison_full_series,
        "delta": parking_year_comparison_delta(selected_series, comparison_series),
        "asOf": {
            "selectedLabel": "Hittil i år" if anchor_year == current_year else "Hele året",
            "selectedDate": selected_as_of_date.isoformat(),
            "comparisonLabel": "Til samme dag i året",
            "comparisonDate": comparison_as_of_date.isoformat(),
        },
    }


def build_revenue_year_comparison(summaries: Dict[str, Any], now_dt: datetime, anchor_year: int) -> Dict[str, Any]:
    today = now_dt.date()
    current_year = today.year
    comparison_year = anchor_year - 1
    selected_as_of_day = today.timetuple().tm_yday if anchor_year == current_year else days_in_year(anchor_year)
    comparison_as_of_day = min(selected_as_of_day, days_in_year(comparison_year))
    selected_as_of_date = date(anchor_year, 1, 1) + timedelta(days=selected_as_of_day - 1)
    comparison_as_of_date = date(comparison_year, 1, 1) + timedelta(days=comparison_as_of_day - 1)
    daily_by_year = revenue_daily_by_year(summaries)
    selected_series = revenue_year_series(daily_by_year, anchor_year, selected_as_of_day, "current", "#dc2626")
    comparison_series = revenue_year_series(daily_by_year, comparison_year, comparison_as_of_day, "comparison", "#64748b")
    comparison_full_series = revenue_year_series(
        daily_by_year,
        comparison_year,
        days_in_year(comparison_year),
        "comparison-full",
        "#94a3b8",
    )
    available_years = sorted(set(daily_by_year.keys()) | {anchor_year, comparison_year}, reverse=True)
    revenue_colors = ["#dc2626", "#64748b", "#0f766e", "#7c3aed", "#be123c", "#0891b2", "#ea580c", "#2563eb"]
    all_series = []
    for index, series_year in enumerate(available_years):
        series_as_of_day = today.timetuple().tm_yday if series_year == current_year else days_in_year(series_year)
        if series_year == anchor_year:
            source = "current"
        elif series_year == comparison_year:
            source = "comparison"
        else:
            source = "reference"
        all_series.append(
            revenue_year_series(
                daily_by_year,
                series_year,
                series_as_of_day,
                source,
                revenue_colors[index % len(revenue_colors)],
            )
        )
    axis_days = max([selected_series["daysInYear"], comparison_full_series["daysInYear"], *(item["daysInYear"] for item in all_series)])
    month_names = ["Jan", "Feb", "Mar", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Des"]
    ticks = []
    for month_index, month_name in enumerate(month_names, start=1):
        tick_date = date(anchor_year, month_index, 1)
        ticks.append({"label": month_name, "day": tick_date.timetuple().tm_yday})
    return {
        "generatedAt": api_local_iso(now_dt),
        "title": "Omsetning · Årssammenligning",
        "anchorYear": anchor_year,
        "comparisonYear": comparison_year,
        "navigation": year_comparison_navigation(anchor_year, current_year),
        "axis": {"days": axis_days, "ticks": ticks},
        "availableYears": available_years,
        "series": all_series,
        "selected": selected_series,
        "comparison": comparison_series,
        "comparisonFull": comparison_full_series,
        "delta": revenue_year_comparison_delta(selected_series, comparison_series),
        "asOf": {
            "selectedLabel": "Hittil i år" if anchor_year == current_year else "Hele året",
            "selectedDate": selected_as_of_date.isoformat(),
            "comparisonLabel": "Til samme dag i året",
            "comparisonDate": comparison_as_of_date.isoformat(),
        },
    }
