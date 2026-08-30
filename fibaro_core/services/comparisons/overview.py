"""Dashboard periods, batched source reads and the four comparison cards."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Optional

from fibaro_core.services.comparisons.windows import (
    cutoff_label, period_cutoff, shifted_period_cutoff, source_as_of, status_comparison_windows,
)
from fibaro_core.services.summaries.periods import add_months
from fibaro_core.services.summaries.sun import sun2_period_snapshots, sun2_datetime_snapshots
from fibaro_core.services.summaries.parking import parking_datetime_snapshots
from fibaro_core.services.summaries.revenue import combine_business_summaries, period_rank_summary
from value_parsing import float_or_zero, int_or_zero


@dataclass(frozen=True)
class ComparisonWindow:
    key: str
    start: datetime
    end: datetime
    sun_end: datetime
    parking_end: datetime
    label: str = ""
    full_label: str = ""


@dataclass(frozen=True)
class DashboardPeriod:
    key: str
    title: str
    current: ComparisonWindow
    previous: ComparisonWindow
    extra: ComparisonWindow


@dataclass(frozen=True)
class OverviewPlan:
    today: date
    periods: tuple[DashboardPeriod, ...]


@dataclass(frozen=True)
class OverviewComparisons:
    plan: OverviewPlan
    sun_full: dict[str, Any]
    sun_at_cutoff: dict[str, Any]
    parking: dict[str, Any]


def overview_comparison_plan(import_rows: list[dict[str, Any]], now_dt: datetime) -> OverviewPlan:
    windows = status_comparison_windows(import_rows, now_dt)
    titles = {"today": "I dag", "week": "Denne uke", "month": "Denne måned"}
    previous_names = {"today": ("yesterday", "i går"), "week": ("previous_week", "forrige uke"),
                      "month": ("previous_month", "forrige måned")}
    extra_names = {"today": "last_week_same_day", "week": "same_week_last_year", "month": "same_month_last_year"}
    periods = []
    for key in ("today", "week", "month"):
        config = windows[key]
        current = config["current"]
        previous, extra = config["comparisons"]

        def end(config):
            start = config["start"]
            if key == "month":
                return datetime.combine(add_months(start.date(), 1), time.min)
            return start + timedelta(days=1 if key == "today" else 7)

        def window(name, config, label="", full_label=""):
            return ComparisonWindow(name, config["start"], end(config), config["sunEnd"], config["parkingEnd"], label, full_label)

        previous_key, previous_label = previous_names[key]
        extra_label = extra["label"].lower()
        extra_prefix = "Sammenlignet med " if key == "today" else "Sammenlignet med tilsvarende datatidspunkt "
        periods.append(DashboardPeriod(
            key, titles[key], window(key, current),
            window(previous_key, previous, f"Sammenlignet med tilsvarende datatidspunkt {previous_label}", f"Hele {previous_label}"),
            window(extra_names[key], extra, extra_prefix + extra_label, "Hele " + extra_label),
        ))

    year = now_dt.year
    start = datetime(year, 1, 1)
    end = datetime(year + 1, 1, 1)
    sun_end = period_cutoff(start, end, source_as_of(import_rows, "sun2_sessions_import", now_dt))
    parking_end = period_cutoff(start, end, source_as_of(import_rows, "easypark_parking_import", now_dt))

    def year_reference(offset, key):
        ref_start, ref_end = datetime(year - offset, 1, 1), datetime(year - offset + 1, 1, 1)
        return ComparisonWindow(
            key, ref_start, ref_end,
            shifted_period_cutoff(start, sun_end, ref_start, ref_end),
            shifted_period_cutoff(start, parking_end, ref_start, ref_end),
            f"Sammenlignet med tilsvarende datatidspunkt i {year - offset}", f"Hele {year - offset}",
        )

    periods.append(DashboardPeriod("year", "Dette år", ComparisonWindow("year", start, end, sun_end, parking_end),
                                   year_reference(1, "previous_year"), year_reference(2, "two_years")))
    return OverviewPlan(now_dt.date(), tuple(periods))


async def load_overview_comparisons(session, plan: OverviewPlan) -> OverviewComparisons:
    references = {window.key: window for period in plan.periods for window in (period.previous, period.extra)}
    full_keys = ("yesterday", "previous_week", "previous_month", "previous_year", "two_years",
                 "last_week_same_day", "same_week_last_year", "same_month_last_year")
    all_windows = {period.key: period.current for period in plan.periods} | references
    cutoff_keys = ("today", "week", "month", "year", "yesterday", "last_week_same_day", "previous_week",
                   "same_week_last_year", "previous_month", "same_month_last_year", "previous_year", "two_years")
    full_periods = {key: (references[key].start.date(), references[key].end.date()) for key in full_keys}
    sun_periods = {key: (all_windows[key].start, all_windows[key].sun_end) for key in cutoff_keys}
    parking_periods = {key: (window.start, window.parking_end) for key, window in all_windows.items()}
    parking_periods.update({key + "_full": (window.start, window.end) for key, window in references.items()})
    sun_full = await sun2_period_snapshots(session, full_periods)
    sun_at_cutoff = await sun2_datetime_snapshots(session, sun_periods)
    parking = await parking_datetime_snapshots(session, parking_periods)
    return OverviewComparisons(plan, sun_full, sun_at_cutoff, parking)


def _amounts(sun, parking) -> dict[str, Any]:
    sol, paid = float_or_zero(sun.paid), float_or_zero(parking.paid)
    return {"sol": sol, "solCount": int_or_zero(sun.sessions), "parking": paid,
            "parkingCount": int_or_zero(parking.sessions), "total": sol + paid}


def build_overview_cards(
    data: OverviewComparisons,
    sun_summaries: dict[str, Any],
    parking_summaries: dict[str, Any],
    scope: Optional[str],
) -> list[dict[str, Any]]:
    rank_summaries = combine_business_summaries(sun_summaries, parking_summaries)
    rank_basis, rank_value_key = "omsetning", "total_paid"
    if scope == "parking":
        rank_summaries = combine_business_summaries({}, parking_summaries)
        rank_basis, rank_value_key = "antall parkeringer", "total_count"
    elif scope == "sun":
        rank_summaries = combine_business_summaries(sun_summaries, {})
        rank_basis, rank_value_key = "antall solinger", "total_count"

    today = data.plan.today
    iso_year, iso_week, _ = today.isocalendar()
    rank_periods = {
        "today": ("daily", today.isoformat(), "dager"),
        "week": ("weekly", f"{iso_year}-W{iso_week:02d}", "uker"),
        "month": ("monthly", today.strftime("%Y-%m"), "måneder"),
        "year": ("yearly", str(today.year), "år"),
    }
    cards = []
    for period in data.plan.periods:
        current, previous, extra = period.current, period.previous, period.extra
        values = _amounts(data.sun_at_cutoff[period.key], data.parking[period.key])
        previous_values = _amounts(data.sun_at_cutoff[previous.key], data.parking[previous.key])
        previous_full = _amounts(data.sun_full[previous.key], data.parking[previous.key + "_full"])
        extra_values = _amounts(data.sun_at_cutoff[extra.key], data.parking[extra.key])
        extra_full = _amounts(data.sun_full[extra.key], data.parking[extra.key + "_full"])
        rank_source, rank_period, rank_label = rank_periods[period.key]
        rank_value = values["parkingCount"] if scope == "parking" else values["solCount"] if scope == "sun" else values["total"]
        rank = period_rank_summary(rank_summaries.get(rank_source, []), rank_value, rank_period,
                                   rank_label, rank_value_key, rank_basis)
        if period.key == "today" and rank is not None:
            rank["totalDays"] = rank["totalPeriods"]
        card = {"key": period.key, "title": period.title, **values, "rank": rank,
                "previousLabel": previous.label, "previousFullLabel": previous.full_label,
                "solAsOfLabel": cutoff_label(current.sun_end, today),
                "parkingAsOfLabel": cutoff_label(current.parking_end, today),
                "previousSolAsOfLabel": cutoff_label(previous.sun_end, today),
                "previousParkingAsOfLabel": cutoff_label(previous.parking_end, today)}
        for key, value in previous_values.items():
            card["previous" + key[0].upper() + key[1:]] = value
        for key, value in previous_full.items():
            card["previousFull" + key[0].upper() + key[1:]] = value
        extra_payload = {"label": extra.label, **extra_values, "fullLabel": extra.full_label,
                         "solAsOfLabel": cutoff_label(extra.sun_end, today),
                         "parkingAsOfLabel": cutoff_label(extra.parking_end, today)}
        for key, value in extra_full.items():
            extra_payload["full" + key[0].upper() + key[1:]] = value
        card["extraComparisons"] = [extra_payload]
        cards.append(card)
    return cards
