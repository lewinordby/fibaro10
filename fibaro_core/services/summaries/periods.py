"""Calendar normalization, ISO weeks and year navigation."""

from datetime import date, datetime
from typing import Any, Dict, Optional


def normalized_stat_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def iso_week_period(stat_day: date) -> tuple[str, str]:
    iso_year, iso_week, _ = stat_day.isocalendar()
    week_start = date.fromisocalendar(iso_year, iso_week, 1)
    week_end = date.fromisocalendar(iso_year, iso_week, 7)
    if week_start.year == week_end.year:
        date_range = f"{week_start:%d.%m}-{week_end:%d.%m.%Y}"
    else:
        date_range = f"{week_start:%d.%m.%Y}-{week_end:%d.%m.%Y}"
    return f"{iso_year}-W{iso_week:02d}", f"Uke {iso_week}, {iso_year} ({date_range})"


def days_in_year(year: int) -> int:
    return (date(year + 1, 1, 1) - date(year, 1, 1)).days


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def month_label(day: date) -> str:
    month_names = [
        "januar", "februar", "mars", "april", "mai", "juni",
        "juli", "august", "september", "oktober", "november", "desember",
    ]
    return f"{month_names[day.month - 1].capitalize()} {day.year}"


def parse_anchor_year(value: Optional[str], fallback: int) -> int:
    if not value:
        return fallback
    try:
        year = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(2000, min(fallback, year))


def year_comparison_navigation(anchor_year: int, current_year: int) -> Dict[str, Any]:
    return {
        "anchor": str(anchor_year),
        "label": str(anchor_year),
        "previousAnchor": str(anchor_year - 1),
        "nextAnchor": str(anchor_year + 1),
        "canPrevious": True,
        "canNext": anchor_year < current_year,
        "previousLabel": "Forrige år",
        "nextLabel": "Neste år",
    }
