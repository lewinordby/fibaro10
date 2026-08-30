"""Presentation services with explicit process dependencies."""

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.responses import StreamingResponse
from fibaro_core.export_definitions import SUN2_IMPORT_COLUMNS
from fibaro_core.export_definitions import SUN2_ROOM_COLUMNS
from fibaro_core.models import EnergyHourlyConsumption
from fibaro_core.models import Sun2Bed
from fibaro_core.models import Sun2ImportRun
from fibaro_core.models import Sun2Member
from fibaro_core.models import Sun2RoomDailyStat
from fibaro_core.models import Sun2SessionImportRun
from fibaro_core.models import Sun2TanningSession
from fibaro_core.services.forecasts.snapshots import saved_forecast_table
from fibaro_core.services.presentation import api_card
from fibaro_core.services.presentation import api_chart
from fibaro_core.services.presentation import api_table
from fibaro_core.services.presentation import api_table_meta
from fibaro_core.services.presentation import format_short_number
from fibaro_core.services.settlements.presentation import sun_settlement_module_payload
from fibaro_core.services.summaries.sun import sun2_period_snapshot
from io import StringIO
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sun2_helpers import sun2_room_label
from time_formatting import LOCAL_TZ
from time_formatting import api_local_iso
from time_formatting import local_naive_to_utc_naive
from time_formatting import parse_datetime
from typing import Any
from typing import Any, Callable
from typing import Dict
from typing import Iterable
from typing import Optional
from urllib.parse import urlencode
from v2_navigation import v2_module_title
from value_parsing import float_or_zero
from value_parsing import int_or_zero
import csv
import math


@dataclass
class Dependencies:
    DAY_ZOOM_OPTIONS: Any
    api_sun2_bed_row: Callable[..., Any]
    api_sun2_day_timeline: Callable[..., Any]
    api_sun2_forecast_rows: Callable[..., Any]
    api_sun2_member_row: Callable[..., Any]
    api_sun2_overview_tables: Callable[..., Any]
    api_sun2_session_row: Callable[..., Any]
    api_sun2_summary_row: Callable[..., Any]
    api_sun2_weekly_chart: Callable[..., Any]
    async_session: Callable[..., Any]
    build_sun2_forecast: Callable[..., Any]
    get_sun2_session_database_total: Callable[..., Any]
    get_sun2_summaries: Callable[..., Any]
    json_value: Callable[..., Any]
    sun2_product_module_payload: Callable[..., Any]
    sun2_sessions_module_payload: Callable[..., Any]


def create_service(dependencies: Dependencies):

    def parse_day(value: Optional[str]) -> date:
        if value:
            try:
                return date.fromisoformat(value)
            except ValueError:
                pass
        return datetime.now(LOCAL_TZ).date()

    def day_zoom_config(value: Optional[str]):
        DAY_ZOOM_OPTIONS = dependencies.DAY_ZOOM_OPTIONS
        for option in DAY_ZOOM_OPTIONS:
            if option["key"] == value:
                return option
        return DAY_ZOOM_OPTIONS[0]

    def day_zoom_window(selected_day: date, zoom_key: Optional[str]):
        config = day_zoom_config(zoom_key)
        day_start = datetime.combine(selected_day, time.min)
        window_start = day_start + timedelta(hours=config["start_hour"])
        window_end = day_start + timedelta(hours=config["end_hour"])
        ticks = [
            {
                "label": f"{hour:02d}" if hour < 24 else "24",
                "left": percent_between(day_start + timedelta(hours=hour), window_start, window_end),
            }
            for hour in config["ticks"]
        ]
        return config, window_start, window_end, ticks

    def display_action(action: Optional[str]) -> str:
        if action == "PAA":
            return "PÅ"
        return action or ""

    def display_control_mode(value: Any) -> str:
        normalized = str(value or "").strip().upper()
        return {
            "FORKJOLING": "Forkjøling",
            "KJOLING": "Kjøling",
            "NORMAL": "Normal",
            "UTENFOR_DRIFTSTID": "Utenfor driftstid",
        }.get(normalized, str(value or "-"))

    def clean_display_text(value: Optional[str]) -> str:
        return (value or "").replace("innbl?sing", "innblåsing").replace("innblasing", "innblåsing").replace("KJ?LING", "KJØLING").replace("KJOLING", "KJØLING").replace("kj?lebehov", "kjølebehov").replace("kjolebehov", "kjølebehov")

    def percent_between(value: datetime, start: datetime, end: datetime) -> float:
        total = (end - start).total_seconds()
        if total <= 0:
            return 0
        seconds = (value - start).total_seconds()
        return round(max(0, min(100, seconds / total * 100)), 3)

    def span_width(start_value: datetime, end_value: datetime, day_start: datetime, day_end: datetime) -> float:
        return round(max(0, percent_between(end_value, day_start, day_end) - percent_between(start_value, day_start, day_end)), 3)

    def add_segment(segments, start_value: datetime, end_value: datetime):
        if end_value <= start_value:
            return
        if segments and segments[-1]["end_dt"] == start_value:
            segments[-1]["end_dt"] = end_value
        else:
            segments.append({"start_dt": start_value, "end_dt": end_value})

    def display_segments(raw_segments, day_start: datetime, day_end: datetime):
        return [
            {
                "left": percent_between(segment["start_dt"], day_start, day_end),
                "width": span_width(segment["start_dt"], segment["end_dt"], day_start, day_end),
                "start": segment["start_dt"].strftime("%H:%M"),
                "end": segment["end_dt"].strftime("%H:%M"),
            }
            for segment in raw_segments
        ]

    def total_from_segments(segments) -> str:
        total_minutes = int(round(sum((segment["end_dt"] - segment["start_dt"]).total_seconds() / 60 for segment in segments)))
        return f"{total_minutes // 60}t {total_minutes % 60}m"

    def age_label(minutes: Optional[int]) -> str:
        if minutes is None:
            return "Ingen data"
        if minutes < 1:
            return "Akkurat nå"
        if minutes < 60:
            return f"{minutes} min siden"
        hours = minutes // 60
        rest = minutes % 60
        if hours < 24:
            return f"{hours}t {rest}m siden"
        days = hours // 24
        return f"{days}d siden"

    def normalize_month(value: Optional[str], fallback: date) -> date:
        if value:
            try:
                year_text, month_text = value.split("-", 1)
                year = int(year_text)
                month = int(month_text)
                if 1 <= month <= 12:
                    return date(year, month, 1)
            except (TypeError, ValueError):
                pass
        return fallback.replace(day=1)

    def row_to_dict(row, columns):
        out = {}
        for column in columns:
            if column == "extra":
                continue
            value = getattr(row, column)
            out[column] = value.isoformat() if isinstance(value, (datetime, date)) else value
        if hasattr(row, "extra"):
            out["extra"] = row.extra or {}
        return out

    def apply_common_filters(stmt, model, event_type, action, device_key, device_id, mode, source_contains, from_ts, to_ts):
        if event_type:
            stmt = stmt.where(model.event_type == event_type)
        if action:
            stmt = stmt.where(model.action == action)
        if device_key:
            stmt = stmt.where(model.device_key == device_key)
        if device_id is not None:
            stmt = stmt.where(model.device_id == device_id)
        if mode:
            stmt = stmt.where(model.mode == mode)
        if source_contains:
            stmt = stmt.where(model.source.ilike(f"%{source_contains}%"))
        if from_ts:
            stmt = stmt.where(model.timestamp >= from_ts)
        if to_ts:
            stmt = stmt.where(model.timestamp <= to_ts)
        return stmt

    async def fetch_rows(model, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, limit, time_basis: str = "source"):
        async_session = dependencies.async_session
        from_ts = parse_datetime(from_text)
        to_ts = parse_datetime(to_text)
        if time_basis == "utc":
            from_ts = local_naive_to_utc_naive(from_ts)
            to_ts = local_naive_to_utc_naive(to_ts)
        limit = max(1, min(limit, 10000))
        stmt = select(model).order_by(model.timestamp.desc()).limit(limit)
        stmt = apply_common_filters(stmt, model, event_type, action, device_key, device_id, mode, source_contains, from_ts, to_ts)
        async with async_session() as session:
            result = await session.execute(stmt)
            return result.scalars().all(), limit

    async def csv_response(model, columns, filename, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, time_basis: str = "source"):
        json_value = dependencies.json_value
        rows, _ = await fetch_rows(model, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, 10000, time_basis=time_basis)
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        for row in rows:
            row_dict = row_to_dict(row, columns)
            writer.writerow([json_value(row_dict.get(column)) for column in columns])
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    def redirect_keep_query(request: Request, target: str, status_code: int = 307) -> RedirectResponse:
        query = request.url.query
        if query:
            separator = "&" if "?" in target else "?"
            target = f"{target}{separator}{query}"
        return RedirectResponse(target, status_code=status_code)

    def redirect_with_query_params(request: Request, target: str, status_code: int = 303, **params: Any) -> RedirectResponse:
        query = dict(request.query_params)
        query.update({key: str(value) for key, value in params.items() if value not in (None, "")})
        if query:
            separator = "&" if "?" in target else "?"
            target = f"{target}{separator}{urlencode(query)}"
        return RedirectResponse(target, status_code=status_code)

    def api_bool_state(value: Any) -> Optional[bool]:
        if value is None:
            return None
        return bool(value)

    def api_filter(
        key: str,
        label: str,
        filter_type: str = "text",
        value: Any = "",
        placeholder: str = "",
        options: Optional[list[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "key": key,
            "label": label,
            "type": filter_type,
            "value": value if value is not None else "",
        }
        if placeholder:
            payload["placeholder"] = placeholder
        if options is not None:
            payload["options"] = options
        return payload

    def api_filter_value(params: Any, key: str, default: str = "") -> str:
        return str(params.get(key) or default).strip()

    def api_filter_int(params: Any, key: str, default: int, minimum: int = 1, maximum: int = 1000) -> int:
        try:
            value = int(params.get(key) or default)
        except (TypeError, ValueError):
            value = default
        return max(minimum, min(maximum, value))

    def api_filter_options(values: Iterable[Any]) -> list[Dict[str, Any]]:
        seen = set()
        options = []
        for value in values:
            if value is None:
                continue
            text_value = str(value).strip()
            if not text_value or text_value in seen:
                continue
            seen.add(text_value)
            options.append({"label": text_value, "value": text_value})
        return options

    def api_day_navigation(selected_day: date, today: date) -> Dict[str, Any]:
        return {
            "selectedDay": selected_day.isoformat(),
            "selectedDayLabel": selected_day.strftime("%d.%m.%Y"),
            "prevDay": (selected_day - timedelta(days=1)).isoformat(),
            "nextDay": (selected_day + timedelta(days=1)).isoformat(),
            "isToday": selected_day == today,
        }

    def decimate_rows(rows: list[Any], max_points: int) -> list[Any]:
        if max_points <= 0 or len(rows) <= max_points:
            return rows
        step = max(1, math.ceil(len(rows) / max_points))
        decimated = rows[::step]
        if decimated[-1] is not rows[-1]:
            decimated.append(rows[-1])
        return decimated

    def api_tool_row(tool: str, path: str, description: str, count: Optional[int] = None) -> Dict[str, Any]:
        return {
            "tool": tool,
            "path": path,
            "description": description,
            "count": count,
        }

    def api_saved_forecast_rows(rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        return [
            {
                "created_at": row.get("created_at"),
                "period_type": row.get("period_type"),
                "period_label": row.get("period_label"),
                "forecast_sessions": round(float_or_zero((row.get("forecast") or {}).get("sessions")), 1),
                "actual_sessions": round(float_or_zero((row.get("actual") or {}).get("sessions")), 1),
                "delta_sessions": round(float_or_zero((row.get("delta") or {}).get("sessions")), 1),
                "forecast_paid": round(float_or_zero((row.get("forecast") or {}).get("paid")), 2),
                "actual_paid": round(float_or_zero((row.get("actual") or {}).get("paid")), 2),
                "delta_paid": round(float_or_zero((row.get("delta") or {}).get("paid")), 2),
                "period_done": row.get("period_done"),
            }
            for row in rows
        ]

    async def api_v2_soling_module(
        session,
        view: str,
        today: date,
        tomorrow: date,
        month_start: date,
        selected_day: Optional[date] = None,
        params: Optional[Any] = None,
    ) -> Dict[str, Any]:
        api_sun2_bed_row = dependencies.api_sun2_bed_row
        api_sun2_day_timeline = dependencies.api_sun2_day_timeline
        api_sun2_forecast_rows = dependencies.api_sun2_forecast_rows
        api_sun2_member_row = dependencies.api_sun2_member_row
        api_sun2_overview_tables = dependencies.api_sun2_overview_tables
        api_sun2_session_row = dependencies.api_sun2_session_row
        api_sun2_summary_row = dependencies.api_sun2_summary_row
        api_sun2_weekly_chart = dependencies.api_sun2_weekly_chart
        build_sun2_forecast = dependencies.build_sun2_forecast
        get_sun2_session_database_total = dependencies.get_sun2_session_database_total
        get_sun2_summaries = dependencies.get_sun2_summaries
        sun2_product_module_payload = dependencies.sun2_product_module_payload
        sun2_sessions_module_payload = dependencies.sun2_sessions_module_payload
        params = params or {}
        view = view or "oversikt"
        if view not in {"oversikt", "dagslinje", "prognose", "statistikk", "detaljer", "enkeltimer", "senger", "medlemmer", "produkter", "oppgjor"}:
            view = "oversikt"
        if view == "oppgjor":
            return await sun_settlement_module_payload(session)
        if view == "produkter":
            return await sun2_product_module_payload(session, today, month_start, params)
        if view == "enkeltimer":
            return await sun2_sessions_module_payload(session, params)

        yesterday = today - timedelta(days=1)
        recent_start = today - timedelta(days=119)
        sun2_summaries = await get_sun2_summaries(session)
        today_sun = await sun2_period_snapshot(session, today, tomorrow)
        yesterday_sun = await sun2_period_snapshot(session, yesterday, today)
        month_sun = await sun2_period_snapshot(session, month_start, tomorrow)
        database_total = await get_sun2_session_database_total(session)
        latest_import = (
            await session.execute(
                select(Sun2ImportRun)
                .order_by(Sun2ImportRun.timestamp.desc())
                .limit(1)
            )
        ).scalars().first()
        latest_sessions = (
            await session.execute(
                select(Sun2TanningSession)
                .order_by(Sun2TanningSession.started_at.desc())
                .limit(80)
            )
        ).scalars().all()

        if view == "oversikt":
            current_year_summary = next(
                (item for item in sun2_summaries.get("yearly", []) if str(item.get("period")) == str(today.year)),
                {},
            )
            year_sessions = int_or_zero(current_year_summary.get("totalt_antall_solinger"))
            year_paid = float_or_zero(current_year_summary.get("totalt_inntjent_kr"))
            daily_rows = list(reversed(sun2_summaries.get("daily", [])[:120]))
            daily_count_chart = api_chart(
                "Solinger per dag",
                [str(row.get("period") or "") for row in daily_rows],
                [{"name": "Solinger", "data": [int_or_zero(row.get("totalt_antall_solinger")) for row in daily_rows], "type": "bar"}],
                "Siste 120 dager fra samlet SUN2-grunnlag.",
                "bar",
                300,
            )
            return {
                "title": v2_module_title("soling", "oversikt"),
                "subtitle": "SUN2 soling samlet i egne visninger for oversikt, detaljer, enkeltimer, senger, medlemmer og prognose.",
                "cards": [
                    api_card("Solinger i dag", today_sun.sessions, "stk", f"{format_short_number(today_sun.paid)} kr", "sun2", href="/soling/dagslinje"),
                    api_card(
                        "I går",
                        yesterday_sun.sessions,
                        "stk",
                        f"{format_short_number(yesterday_sun.paid)} kr",
                        "sun2",
                        href=f"/soling/enkeltimer?date_from={yesterday.isoformat()}&date_to={yesterday.isoformat()}",
                    ),
                    api_card("Måned", month_sun.sessions, "stk", f"{format_short_number(month_sun.paid)} kr", "revenue", href="/soling/periode?period=month"),
                    api_card("I år", year_sessions, "stk", f"{format_short_number(year_paid)} kr", "sun2", href="/soling/sammenligning"),
                ],
                "charts": [api_sun2_weekly_chart(sun2_summaries, "revenue"), daily_count_chart],
                "tables": api_sun2_overview_tables(
                    sun2_summaries,
                    [api_sun2_session_row(row) for row in latest_sessions],
                    [api_pick(latest_import, SUN2_IMPORT_COLUMNS)] if latest_import else [],
                ),
                "actions": [],
                "filters": [],
                "sunTimeline": None,
            }

        members = (await session.execute(select(func.count()).select_from(Sun2Member))).scalar_one()
        known_members = (
            await session.execute(
                select(func.count(func.distinct(Sun2TanningSession.sun2_user_id)))
                .where(Sun2TanningSession.sun2_user_id.is_not(None))
                .where(Sun2TanningSession.sun2_user_id != "")
            )
        ).scalar_one()
        imports = (
            await session.execute(
                select(Sun2ImportRun)
                .order_by(Sun2ImportRun.timestamp.desc())
                .limit(25)
            )
        ).scalars().all()
        session_imports = (
            await session.execute(
                select(Sun2SessionImportRun)
                .order_by(Sun2SessionImportRun.timestamp.desc())
                .limit(20)
            )
        ).scalars().all()
        today_sessions = (
            await session.execute(
                select(Sun2TanningSession)
                .where(Sun2TanningSession.stat_date == today)
                .order_by(Sun2TanningSession.started_at.asc())
                .limit(250)
            )
        ).scalars().all()
        room_rows = (
            await session.execute(
                select(Sun2RoomDailyStat)
                .order_by(Sun2RoomDailyStat.stat_date.desc(), Sun2RoomDailyStat.room.asc())
                .limit(350)
            )
        ).scalars().all()
        beds = (
            await session.execute(
                select(Sun2Bed)
                .order_by(Sun2Bed.physical_room_number, Sun2Bed.room_id, Sun2Bed.name)
            )
        ).scalars().all()
        bed_totals_rows = (
            await session.execute(
                select(
                    Sun2TanningSession.room_id.label("room_id"),
                    func.count(Sun2TanningSession.id).label("sessions_count"),
                    func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                    func.max(Sun2TanningSession.started_at).label("last_at"),
                )
                .group_by(Sun2TanningSession.room_id)
            )
        ).mappings().all()
        bed_totals = {item["room_id"]: item for item in bed_totals_rows}
        member_rows = (
            await session.execute(
                select(Sun2Member)
                .order_by(Sun2Member.last_seen_at.desc().nullslast(), Sun2Member.name.asc(), Sun2Member.sun2_user_id.asc())
                .limit(300)
            )
        ).scalars().all()
        member_ids = [member.sun2_user_id for member in member_rows if member.sun2_user_id]
        member_stats = {}
        if member_ids:
            member_stats_rows = (
                await session.execute(
                    select(
                        Sun2TanningSession.sun2_user_id.label("sun2_user_id"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                        func.max(Sun2TanningSession.started_at).label("last_session_at"),
                        func.max(Sun2TanningSession.user_name).label("session_name"),
                    )
                    .where(Sun2TanningSession.sun2_user_id.in_(member_ids))
                    .group_by(Sun2TanningSession.sun2_user_id)
                )
            ).mappings().all()
            member_stats = {item["sun2_user_id"]: item for item in member_stats_rows}

        daily_session_rows = [
            dict(item)
            for item in (
                await session.execute(
                    select(
                        Sun2TanningSession.stat_date.label("stat_date"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                        func.count(func.distinct(Sun2TanningSession.room_id)).label("rooms_count"),
                    )
                    .where(Sun2TanningSession.stat_date >= recent_start)
                    .group_by(Sun2TanningSession.stat_date)
                    .order_by(Sun2TanningSession.stat_date.asc())
                )
            ).mappings().all()
        ]
        hour_part = func.extract("hour", Sun2TanningSession.started_at)
        hourly_rows = [
            dict(item)
            for item in (
                await session.execute(
                    select(
                        hour_part.label("hour"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                    )
                    .where(Sun2TanningSession.stat_date >= recent_start)
                    .group_by(hour_part)
                    .order_by(hour_part.asc())
                )
            ).mappings().all()
        ]
        today_room_rows = [
            {
                "room_label": sun2_room_label(item.get("room_id"), item.get("source_room_name")),
                "room_id": item.get("room_id"),
                "sessions_count": int_or_zero(item.get("sessions_count")),
                "duration_hours": round(float_or_zero(item.get("duration_minutes")) / 60, 2),
                "paid_amount_kr": round(float_or_zero(item.get("paid_amount_kr")), 2),
                "first_at": item.get("first_at"),
                "last_at": item.get("last_at"),
            }
            for item in (
                await session.execute(
                    select(
                        Sun2TanningSession.room_id.label("room_id"),
                        func.max(Sun2TanningSession.room).label("source_room_name"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                        func.min(Sun2TanningSession.started_at).label("first_at"),
                        func.max(Sun2TanningSession.started_at).label("last_at"),
                    )
                    .where(Sun2TanningSession.stat_date == today)
                    .group_by(Sun2TanningSession.room_id)
                    .order_by(func.count(Sun2TanningSession.id).desc())
                )
            ).mappings().all()
        ]
        top_rooms = [
            {
                "room_label": sun2_room_label(item.get("room_id"), item.get("source_room_name")),
                "room_id": item.get("room_id"),
                "sessions_count": int_or_zero(item.get("sessions_count")),
                "duration_hours": round(float_or_zero(item.get("duration_minutes")) / 60, 2),
                "paid_amount_kr": round(float_or_zero(item.get("paid_amount_kr")), 2),
            }
            for item in (
                await session.execute(
                    select(
                        Sun2TanningSession.room_id.label("room_id"),
                        func.max(Sun2TanningSession.room).label("source_room_name"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                    )
                    .where(Sun2TanningSession.stat_date >= recent_start)
                    .group_by(Sun2TanningSession.room_id)
                    .order_by(func.count(Sun2TanningSession.id).desc())
                    .limit(15)
                )
            ).mappings().all()
        ]
        top_users = [
            {
                "sun2_user_id": item.get("sun2_user_id"),
                "user_name": item.get("user_name"),
                "sessions_count": int_or_zero(item.get("sessions_count")),
                "duration_hours": round(float_or_zero(item.get("duration_minutes")) / 60, 2),
                "paid_amount_kr": round(float_or_zero(item.get("paid_amount_kr")), 2),
                "last_at": item.get("last_at"),
            }
            for item in (
                await session.execute(
                    select(
                        Sun2TanningSession.sun2_user_id.label("sun2_user_id"),
                        func.max(Sun2TanningSession.user_name).label("user_name"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                        func.max(Sun2TanningSession.started_at).label("last_at"),
                    )
                    .where(Sun2TanningSession.sun2_user_id.is_not(None))
                    .where(Sun2TanningSession.sun2_user_id != "")
                    .where(Sun2TanningSession.stat_date >= recent_start)
                    .group_by(Sun2TanningSession.sun2_user_id)
                    .order_by(func.count(Sun2TanningSession.id).desc())
                    .limit(15)
                )
            ).mappings().all()
        ]
        payment_breakdown = [
            {
                "payment_method": item.get("payment_method") or "Ukjent",
                "sessions_count": int_or_zero(item.get("sessions_count")),
                "paid_amount_kr": round(float_or_zero(item.get("paid_amount_kr")), 2),
            }
            for item in (
                await session.execute(
                    select(
                        Sun2TanningSession.payment_method.label("payment_method"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                    )
                    .where(Sun2TanningSession.stat_date >= recent_start)
                    .group_by(Sun2TanningSession.payment_method)
                    .order_by(func.count(Sun2TanningSession.id).desc())
                    .limit(10)
                )
            ).mappings().all()
        ]
        status_breakdown = [
            {
                "status": item.get("status") or "Ukjent",
                "sessions_count": int_or_zero(item.get("sessions_count")),
            }
            for item in (
                await session.execute(
                    select(
                        Sun2TanningSession.status.label("status"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                    )
                    .where(Sun2TanningSession.stat_date >= recent_start)
                    .group_by(Sun2TanningSession.status)
                    .order_by(func.count(Sun2TanningSession.id).desc())
                    .limit(10)
                )
            ).mappings().all()
        ]
        energy_hour_rows = [
            {
                "hour": int_or_zero(item.get("hour")),
                "consumption_kwh": round(float_or_zero(item.get("consumption_kwh")), 3),
                "production_kwh": round(float_or_zero(item.get("production_kwh")), 3),
                "rows_count": int_or_zero(item.get("rows_count")),
            }
            for item in (
                await session.execute(
                    select(
                        EnergyHourlyConsumption.hour.label("hour"),
                        func.coalesce(func.sum(EnergyHourlyConsumption.consumption_kwh), 0).label("consumption_kwh"),
                        func.coalesce(func.sum(EnergyHourlyConsumption.production_kwh), 0).label("production_kwh"),
                        func.count(EnergyHourlyConsumption.id).label("rows_count"),
                    )
                    .where(EnergyHourlyConsumption.stat_date == today)
                    .group_by(EnergyHourlyConsumption.hour)
                    .order_by(EnergyHourlyConsumption.hour.asc())
                )
            ).mappings().all()
        ]

        daily_chart_rows = [row for row in daily_session_rows if row.get("stat_date")]
        daily_x = [row["stat_date"].isoformat() if hasattr(row["stat_date"], "isoformat") else str(row["stat_date"]) for row in daily_chart_rows]
        daily_count_chart = api_chart(
            "Solinger per dag",
            daily_x,
            [{"name": "Solinger", "data": [int_or_zero(row.get("sessions_count")) for row in daily_chart_rows], "type": "bar"}],
            "Siste 120 dager fra enkeltimer.",
            "bar",
            300,
        )
        daily_revenue_chart = api_chart(
            "Omsetning per dag",
            daily_x,
            [{"name": "Kr", "data": [round(float_or_zero(row.get("paid_amount_kr")), 2) for row in daily_chart_rows], "type": "bar"}],
            "Siste 120 dager fra enkeltimer.",
            "bar",
            300,
        )
        hourly_lookup = {int_or_zero(row.get("hour")): row for row in hourly_rows}
        hourly_points = [
            {
                "hour": hour,
                "hour_label": f"{hour:02d}",
                "sessions_count": int_or_zero((hourly_lookup.get(hour) or {}).get("sessions_count")),
                "duration_hours": round(float_or_zero((hourly_lookup.get(hour) or {}).get("duration_minutes")) / 60, 2),
                "paid_amount_kr": round(float_or_zero((hourly_lookup.get(hour) or {}).get("paid_amount_kr")), 2),
            }
            for hour in range(24)
        ]
        hourly_chart = api_chart(
            "Fordeling per time",
            [item["hour_label"] for item in hourly_points],
            [{"name": "Solinger", "data": [item["sessions_count"] for item in hourly_points], "type": "bar"}],
            "Siste 120 dager fra enkeltimer.",
            "bar",
            300,
        )
        room_chart = api_chart(
            "Mest brukte rom",
            [row["room_label"] for row in top_rooms],
            [{"name": "Solinger", "data": [row["sessions_count"] for row in top_rooms], "type": "bar"}],
            "Siste 120 dager.",
            "bar",
            320,
        )
        bed_chart_rows = [
            {
                "room_label": sun2_room_label(item.get("room_id"), item.get("room_id")),
                "sessions_count": int_or_zero(item.get("sessions_count")),
            }
            for item in sorted(bed_totals_rows, key=lambda row: int_or_zero(row.get("sessions_count")), reverse=True)
            if item.get("room_id")
        ][:15]
        bed_chart = api_chart(
            "Sengebruk",
            [row["room_label"] for row in bed_chart_rows],
            [{"name": "Solinger", "data": [row["sessions_count"] for row in bed_chart_rows], "type": "bar"}],
            "Alle registrerte enkeltimer.",
            "bar",
            320,
        )
        user_chart = api_chart(
            "Mest aktive medlemmer",
            [row.get("user_name") or row.get("sun2_user_id") or "-" for row in top_users],
            [{"name": "Solinger", "data": [row["sessions_count"] for row in top_users], "type": "bar"}],
            "Siste 120 dager.",
            "bar",
            320,
        )

        total_sessions = int_or_zero(database_total.get("sessions_count"))
        total_paid = float_or_zero(database_total.get("paid_amount_kr"))
        total_hours = float_or_zero(database_total.get("duration_minutes")) / 60
        cards = [
            api_card("Solinger i dag", today_sun.sessions, "stk", f"{format_short_number(today_sun.paid)} kr", "sun2", href="/soling/dagslinje"),
            api_card("I går", yesterday_sun.sessions, "stk", f"{format_short_number(yesterday_sun.paid)} kr", "sun2", href="/soling/enkeltimer"),
            api_card("Måned", month_sun.sessions, "stk", f"{format_short_number(month_sun.paid)} kr", "revenue", href="/omsetning/manedsoversikt"),
            api_card("Totalt", format_short_number(total_paid), "kr", f"{format_short_number(total_sessions)} solinger", "revenue", href="/soling/statistikk"),
        ]
        subtitle = "SUN2 soling samlet i egne visninger for oversikt, detaljer, enkeltimer, dagslinje, senger, medlemmer og prognose."
        charts = []
        tables = []
        actions = []
        filters = []
        timeline = None

        if view == "statistikk":
            charts = [api_sun2_weekly_chart(sun2_summaries, "revenue"), daily_count_chart, daily_revenue_chart]
            cards = [
                api_card("Totalt omsetning", format_short_number(total_paid), "kr", f"{format_short_number(total_sessions)} solinger", "revenue", href="/omsetning/oversikt"),
                api_card("Totalt timer", format_short_number(total_hours, 1), "t", "Fra enkeltimer", "sun2", href="/soling/enkeltimer"),
                api_card("Dager med data", sun2_summaries.get("total", {}).get("days_count", 0), "stk", "Dags- og romgrunnlag", "status", href="/soling/detaljer"),
                api_card("Rom brukt", sun2_summaries.get("total", {}).get("rooms_count", 0), "stk", "Fra dagsstatistikk", "status", href="/soling/senger"),
            ]
            tables = [
                api_table("Dager", ["period_label", "totalt_inntjent_kr", "totalt_antall_solinger", "total_soletid_timer", "rooms_count"], [api_sun2_summary_row(row) for row in sun2_summaries.get("daily", [])[:120]]),
                api_table("Måneder", ["period", "totalt_inntjent_kr", "totalt_antall_solinger", "total_soletid_timer", "days_count"], [api_sun2_summary_row(row) for row in sun2_summaries.get("monthly", [])[:60]]),
                api_table("År", ["period", "totalt_inntjent_kr", "totalt_antall_solinger", "total_soletid_timer", "days_count"], [api_sun2_summary_row(row) for row in sun2_summaries.get("yearly", [])]),
            ]
        elif view == "detaljer":
            charts = [api_sun2_weekly_chart(sun2_summaries, "revenue"), room_chart]
            tables = [
                api_table("Romstatistikk", ["stat_date", "room", "room_id", "total_soletid_minutter", "totalt_antall_solinger", "totalt_inntjent_kr", "solinger_medlemmer", "solinger_ikke_medlemmer"], [api_pick(row, SUN2_ROOM_COLUMNS) for row in room_rows]),
                api_table("Måneder", ["period", "totalt_inntjent_kr", "totalt_antall_solinger", "total_soletid_timer", "days_count", "rooms_count"], [api_sun2_summary_row(row) for row in sun2_summaries.get("monthly", [])[:80]]),
                api_table("År", ["period", "totalt_inntjent_kr", "totalt_antall_solinger", "total_soletid_timer", "days_count", "rooms_count"], [api_sun2_summary_row(row) for row in sun2_summaries.get("yearly", [])]),
                api_table("Romimporter", ["timestamp", "ok", "stat_date", "rows_count", "inserted_count", "updated_count", "message"], [api_pick(row, SUN2_IMPORT_COLUMNS) for row in imports]),
            ]
        elif view == "dagslinje":
            timeline = await api_sun2_day_timeline(session, selected_day or today)
            timeline_totals = timeline["totals"]
            session_count = int_or_zero(timeline_totals.get("sessionsCount"))
            duration_minutes = float_or_zero(timeline_totals.get("durationMinutes"))
            paid_amount = float_or_zero(timeline_totals.get("paidAmountKr"))
            average_minutes_per_session = (duration_minutes / session_count) if session_count else 0
            average_paid_per_session = (paid_amount / session_count) if session_count else 0
            top_revenue_room = timeline.get("topRevenueRoom")
            energy_summary = timeline["energySummary"]
            elvia_kwh = float_or_zero(energy_summary.get("totalKwh"))
            internal_kwh = float_or_zero(energy_summary.get("internalTotalKwh"))
            has_elvia_energy = int_or_zero(energy_summary.get("hoursCount")) > 0
            has_internal_energy = int_or_zero(energy_summary.get("internalHoursCount")) > 0
            energy_card_value = elvia_kwh if has_elvia_energy else internal_kwh if has_internal_energy else None
            energy_detail_parts = []
            if has_elvia_energy:
                energy_detail_parts.append(f"Elvia {format_short_number(elvia_kwh, 1)} kWh")
            if has_internal_energy:
                energy_detail_parts.append(
                    f"Egen {format_short_number(internal_kwh, 1)} kWh / {format_short_number(energy_summary.get('internalSamples'))} samples"
                )
            charts = []
            cards = [
                api_card("Solinger", session_count, "stk", timeline["selectedDayLabel"], "sun2", href="/soling/enkeltimer"),
                api_card(
                    "Soltid",
                    format_short_number(timeline_totals.get("durationHours"), 1),
                    "t",
                    f"{format_short_number(duration_minutes, 0)} min · snitt {format_short_number(average_minutes_per_session, 0)} min/time",
                    "sun2",
                    href="/soling/enkeltimer",
                ),
                api_card(
                    "Omsetning",
                    format_short_number(paid_amount),
                    "kr",
                    f"Snitt {format_short_number(average_paid_per_session)} kr pr soling",
                    "revenue",
                    href="/omsetning/oversikt",
                ),
                api_card(
                    "Mest brukt",
                    timeline["busiestRoom"]["label"] if timeline.get("busiestRoom") else "-",
                    "",
                    (
                        f"{timeline['busiestRoom']['count']} solinger"
                        + (
                            f" · Mest inntekt {top_revenue_room['label']} {format_short_number(top_revenue_room['paid'])} kr"
                            if top_revenue_room
                            else ""
                        )
                        if timeline.get("busiestRoom")
                        else "Ingen solinger"
                    ),
                    "sun2",
                    href="/soling/senger",
                ),
                api_card(
                    "Strømforbruk",
                    format_short_number(energy_card_value, 1) if energy_card_value is not None else "-",
                    "kWh",
                    " · ".join(energy_detail_parts) if energy_detail_parts else "Ingen energidata for valgt dag",
                    "energy",
                    href="/energi/elvia",
                ),
            ]
            tables = []
        elif view == "senger":
            charts = [bed_chart]
            cards = [
                api_card("Senger", len(beds), "stk", "Importert fra SUN2", "status", href="/soling/senger"),
                api_card("Rom med bruk", len([row for row in bed_totals_rows if int_or_zero(row.get("sessions_count"))]), "stk", "Har enkeltimer", "sun2", href="/soling/senger"),
                api_card("Solinger totalt", format_short_number(total_sessions), "stk", "Alle senger/rom", "sun2", href="/soling/enkeltimer"),
                api_card("Omsetning totalt", format_short_number(total_paid), "kr", "Alle enkeltimer", "revenue", href="/omsetning/oversikt"),
            ]
            tables = [
                api_table("Senger", ["physical_room_number", "room_label", "room_id", "name", "bed_model", "max_minutes", "current_price_per_min", "status", "lamp_status", "sessions_count", "duration_hours", "paid_amount_kr", "last_session_at", "imported_at"], [api_sun2_bed_row(row, bed_totals) for row in beds]),
            ]
        elif view == "medlemmer":
            q_value = api_filter_value(params, "q")
            customer_type_value = api_filter_value(params, "customer_type")
            status_value = api_filter_value(params, "status")
            limit_value = api_filter_int(params, "limit", 150, 25, 1000)
            page_value = api_filter_int(params, "page", 1, 1, 100000)
            offset_value = (page_value - 1) * limit_value
            member_conditions = []
            if q_value:
                like = f"%{q_value.lower()}%"
                member_conditions.append(
                    or_(
                        func.lower(func.coalesce(Sun2Member.sun2_user_id, "")).like(like),
                        func.lower(func.coalesce(Sun2Member.name, "")).like(like),
                        func.lower(func.coalesce(Sun2Member.display_name, "")).like(like),
                        func.lower(func.coalesce(Sun2Member.initials, "")).like(like),
                        func.lower(func.coalesce(Sun2Member.email, "")).like(like),
                        func.lower(func.coalesce(Sun2Member.phone, "")).like(like),
                    )
                )
            if customer_type_value:
                member_conditions.append(Sun2Member.customer_type == customer_type_value)
            if status_value:
                member_conditions.append(Sun2Member.status == status_value)
            member_stmt = (
                select(Sun2Member)
                .order_by(Sun2Member.last_seen_at.desc().nullslast(), Sun2Member.name.asc(), Sun2Member.sun2_user_id.asc())
                .offset(offset_value)
                .limit(limit_value)
            )
            member_count_stmt = select(func.count()).select_from(Sun2Member)
            if member_conditions:
                member_stmt = member_stmt.where(*member_conditions)
                member_count_stmt = member_count_stmt.where(*member_conditions)
            member_rows = (await session.execute(member_stmt)).scalars().all()
            member_count = (await session.execute(member_count_stmt)).scalar_one()
            member_ids = [member.sun2_user_id for member in member_rows if member.sun2_user_id]
            member_stats = {}
            if member_ids:
                member_stats_rows = (
                    await session.execute(
                        select(
                            Sun2TanningSession.sun2_user_id.label("sun2_user_id"),
                            func.count(Sun2TanningSession.id).label("sessions_count"),
                            func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                            func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                            func.max(Sun2TanningSession.started_at).label("last_session_at"),
                            func.max(Sun2TanningSession.user_name).label("session_name"),
                        )
                        .where(Sun2TanningSession.sun2_user_id.in_(member_ids))
                        .group_by(Sun2TanningSession.sun2_user_id)
                    )
                ).mappings().all()
                member_stats = {item["sun2_user_id"]: item for item in member_stats_rows}
            filters = [
                api_filter("q", "Søk", "text", q_value, "Navn, SUN2-id, telefon eller e-post"),
                api_filter(
                    "customer_type",
                    "Kundetype",
                    "select",
                    customer_type_value,
                    options=api_filter_options(
                        (await session.execute(select(Sun2Member.customer_type).distinct().order_by(Sun2Member.customer_type.asc()))).scalars().all()
                    ),
                ),
                api_filter(
                    "status",
                    "Status",
                    "select",
                    status_value,
                    options=api_filter_options((await session.execute(select(Sun2Member.status).distinct().order_by(Sun2Member.status.asc()))).scalars().all()),
                ),
                api_filter("limit", "Antall", "number", limit_value),
                api_filter("page", "Side", "number", page_value),
            ]
            charts = [user_chart]
            cards = [
                api_card("Treff", member_count, "stk", f"Viser {offset_value + 1 if member_rows else 0}-{min(offset_value + len(member_rows), member_count)}", "status", href="/soling/medlemmer"),
                api_card("Kjent fra soling", known_members, "stk", "Unike bruker-ID-er i enkeltimer", "sun2", href="/soling/enkeltimer"),
                api_card("Aktive i lista", len([row for row in member_rows if (member_stats.get(row.sun2_user_id) or {}).get("sessions_count")]), "stk", "Blant viste medlemmer", "sun2", href="/soling/medlemmer"),
                api_card("Sist importert", member_rows[0].imported_at if member_rows else "-", "", "Medlemsliste", "status", href="/soling/medlemmer"),
            ]
            tables = [
                api_table(
                    "Medlemmer",
                    ["sun2_user_id", "name", "customer_type", "age", "gender", "last_seen_at", "visits_count", "total_spent_kr", "balance_kr", "sessions_count", "duration_hours", "paid_amount_kr", "last_session_at", "session_name"],
                    [api_sun2_member_row(row, member_stats) for row in member_rows],
                    meta=api_table_meta(member_count, page_value, limit_value, len(member_rows)),
                ),
                api_table("Topp brukere", ["sun2_user_id", "user_name", "sessions_count", "duration_hours", "paid_amount_kr", "last_at"], top_users),
            ]
        elif view == "prognose":
            forecast = await build_sun2_forecast(session, today, datetime.now(LOCAL_TZ))
            saved_forecasts = await saved_forecast_table(session, "sun2")
            forecast_table_rows = api_sun2_forecast_rows(forecast)
            charts = [
                api_chart(
                    "Prognose mot faktisk",
                    [row["period"] for row in forecast_table_rows],
                    [
                        {"name": "Faktisk solinger", "data": [row["actual_sessions"] for row in forecast_table_rows], "type": "bar"},
                        {"name": "Prognose solinger", "data": [row["forecast_sessions"] for row in forecast_table_rows], "type": "bar"},
                    ],
                    "Faktisk verdi nå og beregnet sluttverdi.",
                    "bar",
                    300,
                )
            ]
            cards = [
                api_card("Dagsprognose", forecast_table_rows[0]["forecast_sessions"], "stk", f"{format_short_number(forecast_table_rows[0]['forecast_paid'])} kr", "sun2", href="/soling/prognose"),
                api_card("Månedsprognose", forecast_table_rows[1]["forecast_sessions"], "stk", f"{format_short_number(forecast_table_rows[1]['forecast_paid'])} kr", "revenue", href="/soling/prognose"),
                api_card("Årsprognose", forecast_table_rows[2]["forecast_sessions"], "stk", f"{format_short_number(forecast_table_rows[2]['forecast_paid'])} kr", "revenue", href="/soling/prognose"),
                api_card("Lagrede", len(saved_forecasts), "stk", "Prognosesnapshots", "status", href="/soling/prognose"),
            ]
            tables = [
                api_table("Nåværende prognose", ["period", "label", "actual_sessions", "forecast_sessions", "actual_paid", "forecast_paid", "actual_hours", "forecast_hours", "tempo", "remaining_days"], forecast_table_rows),
                api_table("Lagrede prognoser", ["created_at", "period_type", "period_label", "actual_sessions", "forecast_sessions", "delta_sessions", "actual_paid", "forecast_paid", "delta_paid", "period_done"], api_saved_forecast_rows(saved_forecasts)),
            ]
            actions = [
                {
                    "key": "sun2-save-forecast",
                    "label": "Lagre solingprognose",
                    "method": "POST",
                    "path": "/api/actions/soling/save-forecast",
                    "confirm": "Lagre prognosesnapshot for soling nå?",
                    "tone": "primary",
                }
            ]

        return {
            "title": v2_module_title("soling", view),
            "subtitle": subtitle,
            "cards": cards,
            "charts": charts,
            "tables": tables,
            "actions": actions,
            "filters": filters,
            "sunTimeline": timeline,
        }

    def api_rule_rows(rules: list[str]) -> list[Dict[str, Any]]:
        return [{"rule": index + 1, "description": rule} for index, rule in enumerate(rules)]

    def api_pick(row: Any, columns: list[str]) -> Dict[str, Any]:
        payload = row_to_dict(row, columns)
        if "extra" not in columns:
            payload.pop("extra", None)
        return payload

    def api_data_quality_row(
        domain: str,
        metric: str,
        status: str,
        value: Any,
        target: str,
        coverage_percent: Optional[float],
        missing_count: Optional[int],
        sample_count: Optional[int],
        detail: str,
        path: str,
        recommended_action: str,
    ) -> Dict[str, Any]:
        return {
            "domain": domain,
            "metric": metric,
            "status": status,
            "value": value,
            "target": target,
            "coverage_percent": coverage_percent,
            "missing_count": missing_count,
            "sample_count": sample_count,
            "detail": detail,
            "path": path,
            "recommended_action": recommended_action,
        }

    def api_detail_field(label: str, value: Any, detail: str = "") -> Dict[str, Any]:
        if isinstance(value, datetime):
            value = api_local_iso(value)
        elif isinstance(value, date):
            value = value.isoformat()
        return {"label": label, "value": value if value not in (None, "") else "-", "detail": detail}

    return {
        "add_segment": add_segment,
        "age_label": age_label,
        "api_bool_state": api_bool_state,
        "api_data_quality_row": api_data_quality_row,
        "api_day_navigation": api_day_navigation,
        "api_detail_field": api_detail_field,
        "api_filter": api_filter,
        "api_filter_int": api_filter_int,
        "api_filter_options": api_filter_options,
        "api_filter_value": api_filter_value,
        "api_pick": api_pick,
        "api_rule_rows": api_rule_rows,
        "api_saved_forecast_rows": api_saved_forecast_rows,
        "api_tool_row": api_tool_row,
        "api_v2_soling_module": api_v2_soling_module,
        "apply_common_filters": apply_common_filters,
        "clean_display_text": clean_display_text,
        "csv_response": csv_response,
        "day_zoom_config": day_zoom_config,
        "day_zoom_window": day_zoom_window,
        "decimate_rows": decimate_rows,
        "display_action": display_action,
        "display_control_mode": display_control_mode,
        "display_segments": display_segments,
        "fetch_rows": fetch_rows,
        "normalize_month": normalize_month,
        "parse_day": parse_day,
        "percent_between": percent_between,
        "redirect_keep_query": redirect_keep_query,
        "redirect_with_query_params": redirect_with_query_params,
        "row_to_dict": row_to_dict,
        "span_width": span_width,
        "total_from_segments": total_from_segments,
    }
