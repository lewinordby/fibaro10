"""Presentation domain services."""

from api_types import ModuleCardPayload
from api_types import ModuleTablePayload
from datetime import date
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Optional
from value_parsing import float_or_zero


def format_file_size(value: Optional[int]) -> str:
    if not value:
        return "-"
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.1f} MB"


def api_iso_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def api_card(title: str, value: Any, unit: str = "", detail: str = "", tone: str = "status", href: str = "") -> ModuleCardPayload:
    card = {
        "title": title,
        "value": str(value if value is not None else "-"),
        "unit": unit,
        "detail": detail,
        "tone": tone,
    }
    if href:
        card["href"] = href
    return card


def api_table(
    title: str,
    columns: list[str],
    rows: list[Dict[str, Any]],
    edit: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> ModuleTablePayload:
    payload = {
        "title": title,
        "columns": columns,
        "rows": rows,
    }
    if edit:
        payload["edit"] = edit
    if meta:
        payload["meta"] = meta
    return payload


def api_table_meta(total_rows: int, page: int, page_size: int, shown_rows: int) -> Dict[str, Any]:
    offset = max(0, (page - 1) * page_size)
    first_row = offset + 1 if total_rows and shown_rows else 0
    last_row = offset + shown_rows if shown_rows else 0
    return {
        "totalRows": total_rows,
        "page": page,
        "pageSize": page_size,
        "offset": offset,
        "shownRows": shown_rows,
        "firstRow": first_row,
        "lastRow": min(last_row, total_rows),
        "hasPrevious": page > 1,
        "hasMore": offset + shown_rows < total_rows,
    }


def api_chart(
    title: str,
    x: list[str],
    series: list[Dict[str, Any]],
    subtitle: str = "",
    chart_type: str = "line",
    height: int = 330,
    metrics: Optional[list[Dict[str, Any]]] = None,
    default_metric: Optional[str] = None,
    default_visible_series: Optional[list[str]] = None,
    x_axis_type: str = "category",
    x_axis_min: Optional[str] = None,
    x_axis_max: Optional[str] = None,
    disable_zoom: bool = False,
    day_navigation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "title": title,
        "subtitle": subtitle,
        "type": chart_type,
        "x": x,
        "height": height,
        "series": series,
    }
    if metrics:
        payload["metrics"] = metrics
    if default_metric:
        payload["defaultMetric"] = default_metric
    if default_visible_series:
        payload["defaultVisibleSeries"] = default_visible_series
    if x_axis_type != "category":
        payload["xAxisType"] = x_axis_type
    if x_axis_min:
        payload["xAxisMin"] = x_axis_min
    if x_axis_max:
        payload["xAxisMax"] = x_axis_max
    if disable_zoom:
        payload["disableZoom"] = True
    if day_navigation:
        payload["dayNavigation"] = day_navigation
    return payload


def format_short_number(value: Any, decimals: int = 0) -> str:
    number = float_or_zero(value)
    if decimals:
        return f"{number:,.{decimals}f}".replace(",", " ")
    return f"{round(number):,}".replace(",", " ")


def format_signed_short_number(value: Any, decimals: int = 0) -> str:
    number = float_or_zero(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{format_short_number(number, decimals)}"
