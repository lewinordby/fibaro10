"""Sun module response assembly, independent of HTTP registration."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fibaro_core.services.summaries.periods import add_months
from typing import Any


@dataclass
class Dependencies:
    api_v2_soling_module: Any


async def render(session, request, module, view, q, day, now_dt, dependencies):
    api_v2_soling_module = dependencies.api_v2_soling_module
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
    selected_day = None
    if day:
        try:
            selected_day = date.fromisoformat(day)
        except ValueError:
            selected_day = None
    return await api_v2_soling_module(session, view, today, tomorrow, month_start, selected_day, params)

