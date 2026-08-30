"""Source-specific cutoffs, comparison calendars and timeline coordinates."""

from datetime import date, datetime, time, timedelta
import math
from typing import Any, Dict, Optional

from fastapi import HTTPException
from fibaro_core.services.summaries.periods import add_months, month_label
from time_formatting import api_local_iso, normalize_local_naive
from value_parsing import float_or_zero, int_or_zero


def import_row_stamp(import_rows: list[Dict[str, Any]], job_name: str) -> Optional[datetime]:
    for row in import_rows:
        if row.get("job_name") == job_name:
            return normalize_local_naive(row.get("last_success_at"))
    return None


def source_as_of(
    import_rows: list[Dict[str, Any]],
    job_name: str,
    now_dt: datetime,
    fallback: Optional[datetime] = None,
) -> datetime:
    stamp = import_row_stamp(import_rows, job_name) or normalize_local_naive(fallback) or now_dt
    if stamp > now_dt:
        return now_dt
    return stamp


def period_cutoff(period_start: datetime, period_end: datetime, as_of: datetime) -> datetime:
    if as_of <= period_start:
        return period_start
    return min(as_of, period_end)


def shifted_period_cutoff(
    current_start: datetime,
    current_cutoff: datetime,
    previous_start: datetime,
    previous_end: datetime,
) -> datetime:
    elapsed = max(timedelta(0), current_cutoff - current_start)
    return min(previous_start + elapsed, previous_end)


def cutoff_label(value: datetime, today: date) -> str:
    if value.date() == today:
        return f"kl {value.strftime('%H:%M')}"
    return value.strftime("%d.%m kl %H:%M")


def parse_anchor_day(value: Optional[str], fallback: date) -> date:
    if value is None:
        return fallback
    if not isinstance(value, str):
        return fallback
    if not value.strip():
        return fallback
    try:
        return date.fromisoformat(value.strip()[:10])
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Ugyldig ankerdato")


def iso_week_start(target_year: int, iso_week: int) -> date:
    week = iso_week
    while week > 1:
        try:
            return date.fromisocalendar(target_year, week, 1)
        except ValueError:
            week -= 1
    return date.fromisocalendar(target_year, 1, 1)


def same_iso_week_previous_year(value: date) -> tuple[date, int]:
    iso = value.isocalendar()
    target_year = iso.year - 1
    return iso_week_start(target_year, iso.week), target_year


def week_label(value: date) -> str:
    iso = value.isocalendar()
    return f"Uke {iso.week}, {iso.year}"


def status_navigation(
    period_key: str,
    anchor: date,
    max_anchor: date,
    label: str,
) -> Dict[str, Any]:
    if period_key == "today":
        previous_anchor = anchor - timedelta(days=1)
        next_anchor = anchor + timedelta(days=1)
        previous_label = "Forrige dag"
        next_label = "Neste dag"
    elif period_key == "week":
        previous_anchor = anchor - timedelta(days=7)
        next_anchor = anchor + timedelta(days=7)
        previous_label = "Forrige uke"
        next_label = "Neste uke"
    else:
        previous_anchor = add_months(anchor, -1)
        next_anchor = add_months(anchor, 1)
        previous_label = "Forrige m\u00e5ned"
        next_label = "Neste m\u00e5ned"
    return {
        "anchor": anchor.isoformat(),
        "label": label,
        "previousAnchor": previous_anchor.isoformat(),
        "nextAnchor": next_anchor.isoformat(),
        "canPrevious": True,
        "canNext": next_anchor <= max_anchor,
        "previousLabel": previous_label,
        "nextLabel": next_label,
    }


def selected_period_cutoff(period_start: datetime, period_end: datetime, as_of: datetime, is_current_period: bool) -> datetime:
    if is_current_period:
        return period_cutoff(period_start, period_end, as_of)
    return period_end


def status_comparison_windows(
    import_rows: list[Dict[str, Any]],
    now_dt: datetime,
    anchor_day: Optional[date] = None,
) -> Dict[str, Any]:
    today = now_dt.date()
    selected_day = min(anchor_day or today, today)
    yesterday = selected_day - timedelta(days=1)
    last_week_same_day = selected_day - timedelta(days=7)
    current_week_start = today - timedelta(days=today.weekday())
    week_start = selected_day - timedelta(days=selected_day.weekday())
    previous_week_start = week_start - timedelta(days=7)
    same_week_last_year_start, same_week_last_year = same_iso_week_previous_year(week_start)
    current_month_start = today.replace(day=1)
    month_start = selected_day.replace(day=1)
    previous_month_start = add_months(month_start, -1)
    same_month_last_year_start = date(month_start.year - 1, month_start.month, 1)
    same_month_last_year = same_month_last_year_start.year
    tomorrow = selected_day + timedelta(days=1)

    day_start = datetime.combine(selected_day, time.min)
    tomorrow_start = datetime.combine(tomorrow, time.min)
    yesterday_start = datetime.combine(yesterday, time.min)
    last_week_same_day_start = datetime.combine(last_week_same_day, time.min)
    last_week_same_day_end = last_week_same_day_start + timedelta(days=1)
    week_start_dt = datetime.combine(week_start, time.min)
    week_end_dt = week_start_dt + timedelta(days=7)
    previous_week_start_dt = datetime.combine(previous_week_start, time.min)
    same_week_last_year_start_dt = datetime.combine(same_week_last_year_start, time.min)
    same_week_last_year_end_dt = same_week_last_year_start_dt + timedelta(days=7)
    month_start_dt = datetime.combine(month_start, time.min)
    month_end_dt = datetime.combine(add_months(month_start, 1), time.min)
    previous_month_start_dt = datetime.combine(previous_month_start, time.min)
    same_month_last_year_start_dt = datetime.combine(same_month_last_year_start, time.min)
    same_month_last_year_end_dt = datetime.combine(add_months(same_month_last_year_start, 1), time.min)

    is_current_day = selected_day == today
    is_current_week = week_start == current_week_start
    is_current_month = month_start == current_month_start

    sun_as_of = source_as_of(import_rows, "sun2_sessions_import", now_dt)
    parking_as_of = source_as_of(import_rows, "easypark_parking_import", now_dt)
    sun_day_cutoff = selected_period_cutoff(day_start, tomorrow_start, sun_as_of, is_current_day)
    sun_week_cutoff = selected_period_cutoff(week_start_dt, week_end_dt, sun_as_of, is_current_week)
    sun_month_cutoff = selected_period_cutoff(month_start_dt, month_end_dt, sun_as_of, is_current_month)
    parking_day_cutoff = selected_period_cutoff(day_start, tomorrow_start, parking_as_of, is_current_day)
    parking_week_cutoff = selected_period_cutoff(week_start_dt, week_end_dt, parking_as_of, is_current_week)
    parking_month_cutoff = selected_period_cutoff(month_start_dt, month_end_dt, parking_as_of, is_current_month)

    day_label = "I dag" if is_current_day else selected_day.strftime("%d.%m.%Y")
    week_current_label = "Denne uken" if is_current_week else week_label(week_start)
    month_current_label = "Denne m\u00e5neden" if is_current_month else month_label(month_start)

    def current(label: str, start: datetime, sun_end: datetime, parking_end: datetime) -> Dict[str, Any]:
        return {"label": label, "start": start, "sunEnd": sun_end, "parkingEnd": parking_end}

    def compare(
        key: str,
        label: str,
        start: datetime,
        end: datetime,
        current_start: datetime,
        current_sun_end: datetime,
        current_parking_end: datetime,
    ) -> Dict[str, Any]:
        return {
            "key": key,
            "label": label,
            "start": start,
            "sunEnd": shifted_period_cutoff(current_start, current_sun_end, start, end),
            "parkingEnd": shifted_period_cutoff(current_start, current_parking_end, start, end),
        }

    return {
        "today": {
            "title": day_label,
            "anchor": selected_day.isoformat(),
            "navigation": status_navigation("today", selected_day, today, day_label),
            "current": current(day_label, day_start, sun_day_cutoff, parking_day_cutoff),
            "comparisons": [
                compare(
                    "previous",
                    "Tilsvarende datatidspunkt i g\u00e5r" if is_current_day else "Dagen f\u00f8r",
                    yesterday_start,
                    day_start,
                    day_start,
                    sun_day_cutoff,
                    parking_day_cutoff,
                ),
                compare(
                    "same-weekday-last-week",
                    "Samme dag forrige uke" if is_current_day else "Samme ukedag forrige uke",
                    last_week_same_day_start,
                    last_week_same_day_end,
                    day_start,
                    sun_day_cutoff,
                    parking_day_cutoff,
                ),
            ],
        },
        "week": {
            "title": "Uke",
            "anchor": week_start.isoformat(),
            "navigation": status_navigation("week", week_start, current_week_start, week_current_label),
            "current": current(week_current_label, week_start_dt, sun_week_cutoff, parking_week_cutoff),
            "comparisons": [
                compare(
                    "previous",
                    "Tilsvarende datatidspunkt forrige uke" if is_current_week else "Forrige uke",
                    previous_week_start_dt,
                    week_start_dt,
                    week_start_dt,
                    sun_week_cutoff,
                    parking_week_cutoff,
                ),
                compare(
                    "same-week-last-year",
                    f"Samme uke {same_week_last_year}",
                    same_week_last_year_start_dt,
                    same_week_last_year_end_dt,
                    week_start_dt,
                    sun_week_cutoff,
                    parking_week_cutoff,
                ),
            ],
        },
        "month": {
            "title": "M\u00e5ned",
            "anchor": month_start.isoformat(),
            "navigation": status_navigation("month", month_start, current_month_start, month_current_label),
            "current": current(month_current_label, month_start_dt, sun_month_cutoff, parking_month_cutoff),
            "comparisons": [
                compare(
                    "previous",
                    "Tilsvarende datatidspunkt forrige m\u00e5ned" if is_current_month else "Forrige m\u00e5ned",
                    previous_month_start_dt,
                    month_start_dt,
                    month_start_dt,
                    sun_month_cutoff,
                    parking_month_cutoff,
                ),
                compare(
                    "same-month-last-year",
                    f"Samme m\u00e5ned {same_month_last_year}",
                    same_month_last_year_start_dt,
                    same_month_last_year_end_dt,
                    month_start_dt,
                    sun_month_cutoff,
                    parking_month_cutoff,
                ),
            ],
        },
    }


def status_period_summary(label: str, start: datetime, sun_end: datetime, parking_end: datetime, sun_row: Any, parking_row: Any, today: date) -> Dict[str, Any]:
    sol = float_or_zero(sun_row.paid)
    parking = float_or_zero(parking_row.paid)
    return {
        "label": label,
        "start": api_local_iso(start),
        "sunEnd": api_local_iso(sun_end),
        "parkingEnd": api_local_iso(parking_end),
        "solAsOfLabel": cutoff_label(sun_end, today),
        "parkingAsOfLabel": cutoff_label(parking_end, today),
        "sol": sol,
        "solCount": int_or_zero(sun_row.sessions),
        "parking": parking,
        "parkingCount": int_or_zero(parking_row.sessions),
        "total": sol + parking,
    }


def status_timeline_ticks(start: datetime, axis_seconds: float) -> list[Dict[str, Any]]:
    if axis_seconds <= 0:
        return [{"label": start.strftime("%H:%M"), "left": 0}]
    axis_end = start + timedelta(seconds=axis_seconds)
    ticks: list[Dict[str, Any]] = []
    if axis_seconds <= 36 * 3600:
        cursor = start.replace(minute=0, second=0, microsecond=0)
        while cursor < start:
            cursor += timedelta(hours=1)
        if cursor.hour % 2:
            cursor += timedelta(hours=1)
        while cursor <= axis_end:
            left = ((cursor - start).total_seconds() / axis_seconds) * 100
            ticks.append({"label": cursor.strftime("%H"), "left": round(max(0, min(100, left)), 4)})
            cursor += timedelta(hours=2)
    else:
        span_days = max(1, math.ceil(axis_seconds / 86400))
        step_days = 1 if span_days <= 10 else max(1, math.ceil(span_days / 8))
        cursor = datetime.combine(start.date(), time.min)
        while cursor < start:
            cursor += timedelta(days=step_days)
        while cursor <= axis_end:
            left = ((cursor - start).total_seconds() / axis_seconds) * 100
            ticks.append({"label": cursor.strftime("%d.%m"), "left": round(max(0, min(100, left)), 4)})
            cursor += timedelta(days=step_days)
    if not ticks or ticks[0]["left"] > 0:
        ticks.insert(0, {"label": start.strftime("%H:%M" if axis_seconds <= 36 * 3600 else "%d.%m"), "left": 0})
    if ticks[-1]["left"] < 99:
        ticks.append({"label": axis_end.strftime("%H:%M" if axis_seconds <= 36 * 3600 else "%d.%m"), "left": 100})
    return ticks


def status_timeline_position(start_at: datetime, end_at: datetime, period_start: datetime, lane_end: datetime, axis_seconds: float) -> Optional[Dict[str, float]]:
    if axis_seconds <= 0:
        return None
    clamped_start = max(period_start, min(lane_end, start_at))
    clamped_end = max(clamped_start, min(lane_end, end_at))
    if clamped_end <= period_start:
        return None
    left = ((clamped_start - period_start).total_seconds() / axis_seconds) * 100
    width = ((clamped_end - clamped_start).total_seconds() / axis_seconds) * 100
    return {
        "left": round(max(0, min(100, left)), 4),
        "width": round(max(0.16, min(100, width)), 4),
    }
