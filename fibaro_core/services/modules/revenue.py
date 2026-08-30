"""Revenue module response assembly, independent of HTTP registration."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fibaro_core.services.presentation import api_card, api_table, format_short_number
from fibaro_core.services.summaries.periods import add_months
from fibaro_core.services.summaries.revenue import combine_business_summaries
from fibaro_core.services.summaries.sun import sun2_period_snapshot
from typing import Any, Dict
from v2_navigation import v2_module_title
from value_parsing import float_or_zero, int_or_zero
import math


@dataclass
class Dependencies:
    api_revenue_accumulated_year_chart: Any
    api_revenue_overview_tables: Any
    api_revenue_weekly_chart: Any
    get_parking_summaries: Any
    get_sun2_summaries: Any
    parking_period_summary: Any


async def render(session, request, module, view, q, day, now_dt, dependencies):
    api_revenue_accumulated_year_chart = dependencies.api_revenue_accumulated_year_chart
    api_revenue_overview_tables = dependencies.api_revenue_overview_tables
    api_revenue_weekly_chart = dependencies.api_revenue_weekly_chart
    get_parking_summaries = dependencies.get_parking_summaries
    get_sun2_summaries = dependencies.get_sun2_summaries
    parking_period_summary = dependencies.parking_period_summary
    params = request.query_params
    today = now_dt.date()
    tomorrow = today + timedelta(days=1)
    today_start = datetime.combine(today, time.min)
    tomorrow_start = datetime.combine(tomorrow, time.min)
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, time.min)
    previous_month_start = add_months(month_start, -1)
    previous_month_start_dt = datetime.combine(previous_month_start, time.min)
    year_start_dt = datetime.combine(date(today.year, 1, 1), time.min)
    sun2_summaries = await get_sun2_summaries(session)
    parking_summaries = await get_parking_summaries(session)
    combined_stats = combine_business_summaries(sun2_summaries, parking_summaries)
    week_start = today - timedelta(days=today.weekday())
    week_start_dt = datetime.combine(week_start, time.min)

    if view == "akkumulert":
        current_year = today.year

        def year_summary(year: int) -> Dict[str, Any]:
            row = next((item for item in combined_stats.get("weekly_chart", []) if str(item.get("year")) == str(year)), None)
            revenue = sum(float_or_zero(value) for value in ((row or {}).get("revenue") or []) if value is not None)
            count = sum(int_or_zero(value) for value in ((row or {}).get("count") or []) if value is not None)
            return {"period_label": str(year), "total_paid": round(revenue, 2), "total_count": count}

        current_year_summary = year_summary(current_year)
        previous_year_summary = year_summary(current_year - 1)
        diff_paid = current_year_summary["total_paid"] - previous_year_summary["total_paid"]
        year_rows = [
            year_summary(int(row["year"]))
            for row in sorted(
                [item for item in combined_stats.get("weekly_chart", []) if str(item.get("year", "")).isdigit()],
                key=lambda item: int(item["year"]),
                reverse=True,
            )
        ]
        return {
            "title": v2_module_title("omsetning", "akkumulert"),
            "subtitle": "Løpende akkumulert utvikling per uke, bygget på samme grunnlag som Omsetning oversikt.",
            "cards": [
                api_card("I år", format_short_number(current_year_summary["total_paid"]), "kr", f"{format_short_number(current_year_summary['total_count'])} hendelser", "revenue", href="/omsetning/akkumulert"),
                api_card("I fjor", format_short_number(previous_year_summary["total_paid"]), "kr", f"{format_short_number(previous_year_summary['total_count'])} hendelser", "status", href="/omsetning/akkumulert"),
                api_card("Differanse", format_short_number(diff_paid), "kr", f"{current_year} mot {current_year - 1}", "revenue" if diff_paid >= 0 else "status", href="/omsetning/akkumulert"),
            ],
            "charts": [api_revenue_accumulated_year_chart(combined_stats)],
            "tables": [
                api_table("Årssummer", ["period_label", "total_paid", "total_count"], year_rows),
            ],
        }

    today_sun = await sun2_period_snapshot(session, today, tomorrow)
    week_sun = await sun2_period_snapshot(session, week_start, tomorrow)
    month_sun = await sun2_period_snapshot(session, month_start, tomorrow)
    today_parking = await parking_period_summary(session, "I dag", today_start, tomorrow_start)
    week_parking = await parking_period_summary(session, "Denne uken", week_start_dt, tomorrow_start)
    month_parking = await parking_period_summary(session, "Denne måneden", month_start_dt, tomorrow_start)

    current_year_key = str(today.year)
    current_year_revenue = next(
        (item for item in combined_stats.get("yearly", []) if str(item.get("period")) == current_year_key),
        {},
    )
    year_sun_paid = float_or_zero(current_year_revenue.get("sun_paid"))
    year_parking_paid = float_or_zero(current_year_revenue.get("parking_paid"))
    year_sun_count = int_or_zero(current_year_revenue.get("sun_count"))
    year_parking_count = int_or_zero(current_year_revenue.get("parking_count"))
    year_total_paid = year_sun_paid + year_parking_paid
    elapsed_year_days = max(1, (today - date(today.year, 1, 1)).days + 1)
    elapsed_week_count = max(1, math.ceil(elapsed_year_days / 7))
    average_week_paid = year_total_paid / elapsed_week_count
    average_week_sun_paid = year_sun_paid / elapsed_week_count
    average_week_parking_paid = year_parking_paid / elapsed_week_count

    cards = [
        api_card(
            "I dag",
            format_short_number(float_or_zero(today_sun.paid) + float_or_zero(today_parking["paid"])),
            "kr",
            f"Sol {format_short_number(today_sun.paid)} kr - parkering {format_short_number(today_parking['paid'])} kr",
            "revenue",
            href="/omsetning/sammenligning?period=today",
        ),
        api_card(
            "Uke",
            format_short_number(float_or_zero(week_sun.paid) + float_or_zero(week_parking["paid"])),
            "kr",
            f"Sol {format_short_number(week_sun.paid)} kr - parkering {format_short_number(week_parking['paid'])} kr",
            "revenue",
            href="/omsetning/sammenligning?period=week",
        ),
        api_card(
            "Måned",
            format_short_number(float_or_zero(month_sun.paid) + float_or_zero(month_parking["paid"])),
            "kr",
            f"Sol {format_short_number(month_sun.paid)} kr - parkering {format_short_number(month_parking['paid'])} kr",
            "revenue",
            href="/omsetning/manedsoversikt",
        ),
        api_card(
            "I år",
            format_short_number(year_total_paid),
            "kr",
            f"Sol {format_short_number(year_sun_paid)} kr - parkering {format_short_number(year_parking_paid)} kr",
            "revenue",
            href="/omsetning/akkumulert",
        ),
        api_card(
            "Snitt pr uke",
            format_short_number(average_week_paid),
            "kr",
            f"Sol {format_short_number(average_week_sun_paid)} kr - parkering {format_short_number(average_week_parking_paid)} kr ({elapsed_week_count} uker)",
            "revenue",
            href="/omsetning/akkumulert",
        ),
        api_card(
            "Soling i år",
            format_short_number(year_sun_paid),
            "kr",
            f"{format_short_number(year_sun_count)} solinger",
            "sun2",
            href="/soling/oversikt",
        ),
        api_card(
            "Parkering i år",
            format_short_number(year_parking_paid),
            "kr",
            f"{format_short_number(year_parking_count)} parkeringer",
            "parking",
            href="/parkering/sammenligning",
        ),
    ]

    return {
        "title": v2_module_title("omsetning", view),
        "subtitle": "Samlet omsetning fra soling og parkering.",
        "cards": cards,
        "charts": [api_revenue_weekly_chart(combined_stats)],
        "tables": api_revenue_overview_tables(combined_stats),
    }

