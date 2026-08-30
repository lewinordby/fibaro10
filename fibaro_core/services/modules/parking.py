"""Parking module response assembly, independent of HTTP registration."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fibaro_core.models import ImportJobStatus, ParkingSession, ParkingVehicle, ParkingVehicleDetails
from fibaro_core.services.forecasts.snapshots import forecast_snapshot_history, saved_forecast_table
from fibaro_core.services.presentation import (
    api_card,
    api_chart,
    api_table,
    api_table_meta,
    format_short_number,
)
from fibaro_core.services.settlements.presentation import parking_settlement_module_payload
from fibaro_core.services.summaries.parking import parking_datetime_snapshots
from fibaro_core.services.summaries.periods import add_months
from parking_vehicle_helpers import compact_plate
from sqlalchemy import and_, case, func, or_, select
from time_formatting import LOCAL_TZ, format_source_datetime
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote
from v2_navigation import v2_module_title
from value_parsing import int_or_zero


@dataclass
class Dependencies:
    api_day_navigation: Any
    api_filter: Any
    api_filter_int: Any
    api_filter_options: Any
    api_filter_value: Any
    api_parking_clear_area_not_found_action: Any
    api_parking_day_timeline: Any
    api_parking_default_actions: Any
    api_parking_forecast_evolution_chart: Any
    api_parking_forecast_rows: Any
    api_parking_overview_tables: Any
    api_parking_saved_forecast_rows: Any
    api_parking_weekly_chart: Any
    api_tool_row: Any
    build_parking_forecast: Any
    get_parking_summaries: Any
    import_job_age: Any
    import_job_updated_ago: Any
    parking_area_missing_rows_for_period: Any
    parking_area_overview_data: Any
    parking_missing_area_rows: Any
    parking_previous_stats_for_rows: Any
    parking_row_api: Any
    parking_vehicle_count_stats: Any
    parking_vehicle_row_api: Any
    parking_vehicle_search_condition: Any
    parse_day: Any
    row_to_dict: Any


async def render(session, request, module, view, q, day, now_dt, dependencies):
    api_day_navigation = dependencies.api_day_navigation
    api_filter = dependencies.api_filter
    api_filter_int = dependencies.api_filter_int
    api_filter_options = dependencies.api_filter_options
    api_filter_value = dependencies.api_filter_value
    api_parking_clear_area_not_found_action = dependencies.api_parking_clear_area_not_found_action
    api_parking_day_timeline = dependencies.api_parking_day_timeline
    api_parking_default_actions = dependencies.api_parking_default_actions
    api_parking_forecast_evolution_chart = dependencies.api_parking_forecast_evolution_chart
    api_parking_forecast_rows = dependencies.api_parking_forecast_rows
    api_parking_overview_tables = dependencies.api_parking_overview_tables
    api_parking_saved_forecast_rows = dependencies.api_parking_saved_forecast_rows
    api_parking_weekly_chart = dependencies.api_parking_weekly_chart
    api_tool_row = dependencies.api_tool_row
    build_parking_forecast = dependencies.build_parking_forecast
    get_parking_summaries = dependencies.get_parking_summaries
    import_job_age = dependencies.import_job_age
    import_job_updated_ago = dependencies.import_job_updated_ago
    parking_area_missing_rows_for_period = dependencies.parking_area_missing_rows_for_period
    parking_area_overview_data = dependencies.parking_area_overview_data
    parking_missing_area_rows = dependencies.parking_missing_area_rows
    parking_previous_stats_for_rows = dependencies.parking_previous_stats_for_rows
    parking_row_api = dependencies.parking_row_api
    parking_vehicle_count_stats = dependencies.parking_vehicle_count_stats
    parking_vehicle_row_api = dependencies.parking_vehicle_row_api
    parking_vehicle_search_condition = dependencies.parking_vehicle_search_condition
    parse_day = dependencies.parse_day
    row_to_dict = dependencies.row_to_dict
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
    if view == "oppgjor":
        return await parking_settlement_module_payload(session)
    normalized_session_plate = func.upper(func.replace(ParkingSession.car_license_number, " ", ""))
    if view == "parkeringer":
        selected_parking_day = parse_day(api_filter_value(params, "day"))
        selected_parking_start = datetime.combine(selected_parking_day, time.min)
        selected_parking_end = selected_parking_start + timedelta(days=1)
        day_navigation = api_day_navigation(selected_parking_day, today)
        parking_import_status = (
            await session.execute(
                select(ImportJobStatus).where(ImportJobStatus.job_name == "easypark_parking_import")
            )
        ).scalars().first()
        if parking_import_status and parking_import_status.last_success_at:
            day_navigation["context"] = {
                "label": "Sist oppdatert",
                "value": format_source_datetime(parking_import_status.last_success_at),
                "detail": import_job_age(parking_import_status),
            }
        plate_value = compact_plate(api_filter_value(params, "plate"))
        status_value = api_filter_value(params, "status")
        session_conditions = [
            ParkingSession.start_time >= selected_parking_start,
            ParkingSession.start_time < selected_parking_end,
        ]
        if plate_value:
            session_conditions.append(func.upper(func.replace(ParkingSession.car_license_number, " ", "")).like(f"%{plate_value.upper()}%"))
        if status_value:
            session_conditions.append(ParkingSession.status == status_value)
        session_stmt = (
            select(ParkingSession, ParkingVehicle, ParkingVehicleDetails)
            .outerjoin(ParkingVehicle, ParkingVehicle.plate == normalized_session_plate)
            .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == normalized_session_plate)
            .order_by(ParkingSession.start_time.desc())
            .where(*session_conditions)
        )
        parking_rows = (await session.execute(session_stmt)).all()
        previous_stats = await parking_previous_stats_for_rows(session, [row for row, _, _ in parking_rows])
        status_options = api_filter_options(
            (await session.execute(select(ParkingSession.status).distinct().order_by(ParkingSession.status.asc()))).scalars().all()
        )
        parking_status_labels = {"ongoing": "Pågående", "ended": "Avsluttet"}
        status_options = [
            {
                **option,
                "label": parking_status_labels.get(str(option["value"]).casefold(), option["label"]),
            }
            for option in status_options
        ]
        return {
            "title": v2_module_title("parkering", view),
            "subtitle": "EasyPark, aktive parkeringer og kj\u00f8ret\u00f8ygrunnlag.",
            "cards": [],
            "charts": [],
            "tables": [
                api_table(
                    "Parkeringer",
                    [
                        "status",
                        "start_time",
                        "end_time",
                        "end_delta_min",
                        "car_license_number",
                        "vehicle_title",
                        "navn",
                        "fee_inc_vat",
                        "parking_time_min",
                        "previous_parking_count",
                        "previous_paid_total",
                    ],
                    [
                        parking_row_api(row, vehicle, details, previous_stats=previous_stats.get(row.id), unifi_before_seconds=60)
                        for row, vehicle, details in parking_rows
                    ],
                    meta={
                        "disablePagination": True,
                        "totalRows": len(parking_rows),
                        "rowLinkColumn": "car_license_number",
                    },
                )
            ],
            "actions": api_parking_default_actions()[:1],
            "filters": [
                api_filter("plate", "Reg.nr", "text", plate_value, "Hele eller del av reg.nr"),
                api_filter("status", "Status", "select", status_value, options=status_options),
            ],
            "dayNavigation": day_navigation,
            "parkingTimeline": None,
        }
    if view == "kjoretoy":
        q_value = q or api_filter_value(params, "q")
        limit_value = api_filter_int(params, "limit", 250, 25, 1000)
        page_value = api_filter_int(params, "page", 1, 1, 100000)
        offset_value = (page_value - 1) * limit_value
        vehicle_search = parking_vehicle_search_condition(q_value)
        vehicle_stats = await parking_vehicle_count_stats(session)
        vehicle_stmt = (
            select(ParkingVehicle, ParkingVehicleDetails)
            .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
            .order_by(ParkingVehicle.last_seen.desc().nullslast(), ParkingVehicle.plate.asc())
            .offset(offset_value)
            .limit(limit_value)
        )
        if vehicle_search is not None:
            vehicle_stmt = vehicle_stmt.where(vehicle_search)
            vehicle_count_stmt = select(func.count(ParkingVehicle.plate)).outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
            vehicle_count_stmt = vehicle_count_stmt.where(vehicle_search)
            vehicle_filtered_count = (await session.execute(vehicle_count_stmt)).scalar_one()
        else:
            vehicle_filtered_count = vehicle_stats["vehicle_count"]
        vehicle_detail_rows = (await session.execute(vehicle_stmt)).all()
        actions = api_parking_default_actions()[1:]
        if int_or_zero(vehicle_stats["vehicle_area_not_found_count"]) > 0:
            actions.append(api_parking_clear_area_not_found_action(vehicle_stats["vehicle_area_not_found_count"]))
        return {
            "title": v2_module_title("parkering", view),
            "subtitle": "EasyPark, aktive parkeringer og kj\u00f8ret\u00f8ygrunnlag.",
            "cards": [
                api_card("Treff", vehicle_filtered_count, "stk", f"Viser {offset_value + 1 if vehicle_detail_rows else 0}-{min(offset_value + len(vehicle_detail_rows), vehicle_filtered_count)}", "parking", href="/parkering/kjoretoy"),
                api_card("Kj\u00f8ret\u00f8y totalt", vehicle_stats["vehicle_count"], "stk", "Registrert i kj\u00f8ret\u00f8ytabellen", "status", href="/parkering/kjoretoy"),
                api_card(
                    "Mangler navn",
                    vehicle_stats["vehicle_missing_name_count"],
                    "stk",
                    f"{format_short_number(vehicle_stats['vehicle_blank_name_count'])} blanke / {format_short_number(vehicle_stats['vehicle_name_not_found_count'])} ikke funnet",
                    "status",
                    href="/parkering/oppslag",
                ),
                api_card("Ikke funnet navn", vehicle_stats["vehicle_name_not_found_count"], "stk", "Inng\u00e5r i mangler navn", "status", href="/parkering/oppslag"),
                api_card(
                    "Mangler omr\u00e5de",
                    vehicle_stats["vehicle_missing_area_count"],
                    "stk",
                    f"{format_short_number(vehicle_stats['vehicle_blank_area_count'])} blanke / {format_short_number(vehicle_stats['vehicle_area_not_found_count'])} ikke funnet",
                    "status",
                    href="/parkering/oppslag?filter=mangler-omrade",
                ),
                api_card("Ikke funnet omr\u00e5de", vehicle_stats["vehicle_area_not_found_count"], "stk", "Inng\u00e5r i mangler omr\u00e5de", "status", href="/parkering/oppslag?filter=mangler-omrade"),
            ],
            "charts": [],
            "tables": [
                api_table(
                    "Kj\u00f8ret\u00f8y",
                    ["plate", "vehicle_title", "navn", "omrade", "parkering_count"],
                    [parking_vehicle_row_api(vehicle, details) for vehicle, details in vehicle_detail_rows],
                    meta=api_table_meta(vehicle_filtered_count, page_value, limit_value, len(vehicle_detail_rows)),
                )
            ],
            "actions": actions,
            "filters": [
                api_filter("q", "S\u00f8k", "text", q_value, "Reg.nr, bil, eier eller omr\u00e5de"),
                api_filter("page", "Side", "number", page_value),
                api_filter("limit", "Antall", "number", limit_value),
            ],
            "dayNavigation": None,
            "parkingTimeline": None,
        }
    overview_context = view in ("", "oversikt")
    parking_summaries = await get_parking_summaries(session) if overview_context else {}
    latest_rows = []
    if overview_context:
        latest_rows = (
            await session.execute(
                select(ParkingSession, ParkingVehicle, ParkingVehicleDetails)
                .outerjoin(ParkingVehicle, ParkingVehicle.plate == normalized_session_plate)
                .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == normalized_session_plate)
                .order_by(ParkingSession.start_time.desc())
                .limit(120)
            )
        ).all()
    parking_periods = (
        await parking_datetime_snapshots(
            session,
            {
                "today": (today_start, tomorrow_start),
                "month": (month_start_dt, tomorrow_start),
            },
        )
        if overview_context
        else {
            "today": SimpleNamespace(sessions=0, paid=0.0),
            "month": SimpleNamespace(sessions=0, paid=0.0),
        }
    )
    today_summary = {
        "label": "I dag",
        "count": parking_periods["today"].sessions,
        "paid": parking_periods["today"].paid,
    }
    month_summary = {
        "label": "Denne måneden",
        "count": parking_periods["month"].sessions,
        "paid": parking_periods["month"].paid,
    }
    parking_import_status = None
    if overview_context or view == "dagslinje":
        parking_import_status = (
            await session.execute(
                select(ImportJobStatus).where(ImportJobStatus.job_name == "easypark_parking_import")
            )
        ).scalars().first()
    active = 0
    if overview_context:
        active = (
            await session.execute(
                select(func.count(ParkingSession.id)).where(
                    ParkingSession.start_time <= now_dt,
                    or_(
                        ParkingSession.end_time.is_(None),
                        ParkingSession.end_time >= now_dt,
                        func.lower(func.coalesce(ParkingSession.status, "")) == "ongoing",
                    ),
                )
            )
        ).scalar_one()
    vehicle_stats = {
        "vehicle_count": 0,
        "vehicle_blank_name_count": 0,
        "vehicle_name_not_found_count": 0,
        "vehicle_missing_name_count": 0,
        "vehicle_blank_area_count": 0,
        "vehicle_area_not_found_count": 0,
        "vehicle_missing_area_count": 0,
    }
    if overview_context or view in {"omrade", "oppslag", "bilstatistikk"}:
        vehicle_stats = await parking_vehicle_count_stats(session)
    vehicle_count = vehicle_stats["vehicle_count"]
    new_vehicle_counts = {"month": 0, "previous_month": 0, "year": 0}
    if overview_context:
        new_vehicle_counts = (
            await session.execute(
                select(
                    func.count(
                        case(
                            (
                                and_(
                                    ParkingVehicle.first_seen >= month_start_dt,
                                    ParkingVehicle.first_seen < tomorrow_start,
                                ),
                                ParkingVehicle.plate,
                            ),
                            else_=None,
                        )
                    ).label("month"),
                    func.count(
                        case(
                            (
                                and_(
                                    ParkingVehicle.first_seen >= previous_month_start_dt,
                                    ParkingVehicle.first_seen < month_start_dt,
                                ),
                                ParkingVehicle.plate,
                            ),
                            else_=None,
                        )
                    ).label("previous_month"),
                    func.count(
                        case(
                            (
                                and_(
                                    ParkingVehicle.first_seen >= year_start_dt,
                                    ParkingVehicle.first_seen < tomorrow_start,
                                ),
                                ParkingVehicle.plate,
                            ),
                            else_=None,
                        )
                    ).label("year"),
                )
            )
        ).mappings().one()
    new_vehicle_month_count = int_or_zero(new_vehicle_counts.get("month"))
    new_vehicle_previous_month_count = int_or_zero(new_vehicle_counts.get("previous_month"))
    new_vehicle_year_count = int_or_zero(new_vehicle_counts.get("year"))
    vehicle_blank_name_count = vehicle_stats["vehicle_blank_name_count"]
    vehicle_name_not_found_count = vehicle_stats["vehicle_name_not_found_count"]
    vehicle_missing_name_count = vehicle_stats["vehicle_missing_name_count"]
    vehicle_blank_area_count = vehicle_stats["vehicle_blank_area_count"]
    vehicle_area_not_found_count = vehicle_stats["vehicle_area_not_found_count"]
    vehicle_missing_area_count = vehicle_stats["vehicle_missing_area_count"]
    vehicle_rows = []
    most_used_vehicle = None
    if view == "bilstatistikk":
        vehicle_rows = (
            await session.execute(
                select(ParkingVehicle, ParkingVehicleDetails)
                .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                .order_by(
                    ParkingVehicle.paid_total.desc().nullslast(),
                    ParkingVehicle.parkering_count.desc().nullslast(),
                    ParkingVehicle.plate.asc(),
                )
                .limit(250)
            )
        ).all()
        most_used_vehicle = (
            await session.execute(
                select(ParkingVehicle)
                .order_by(
                    ParkingVehicle.parkering_count.desc().nullslast(),
                    ParkingVehicle.paid_total.desc().nullslast(),
                    ParkingVehicle.plate.asc(),
                )
                .limit(1)
            )
        ).scalars().first()
    tables = api_parking_overview_tables(
        parking_summaries,
        [parking_row_api(row, vehicle, details, unifi_before_seconds=15) for row, vehicle, details in latest_rows],
    )
    cards = [
        api_card(
            "Sist oppdatert",
            format_source_datetime(parking_import_status.last_success_at) if parking_import_status and parking_import_status.last_success_at else "-",
            "",
            f"EasyPark import - {import_job_age(parking_import_status)}" if parking_import_status else "Ingen importstatus",
            "status",
            href="/admin/datakilder",
        ),
        api_card("Parkeringer i dag", today_summary["count"], "stk", f"{format_short_number(today_summary['paid'])} kr", "parking", href="/parkering/dagslinje"),
        api_card("Pågående", active, "stk", import_job_updated_ago(parking_import_status), "parking", href="/parkering/dagslinje"),
        api_card("Måned", month_summary["count"], "stk", f"{format_short_number(month_summary['paid'])} kr", "revenue", href="/parkering/periode?period=month"),
        api_card("Kjøretøy", vehicle_count, "stk", "Registrert i kjøretøytabellen", "status", href="/parkering/kjoretoy"),
        api_card(
            "Nye kj\u00f8ret\u00f8y",
            new_vehicle_month_count,
            "stk",
            f"Forrige mnd {format_short_number(new_vehicle_previous_month_count)} - i \u00e5r {format_short_number(new_vehicle_year_count)} stk",
            "parking",
            href="/parkering/kjoretoy",
        ),
    ]
    actions = api_parking_default_actions()
    filters = []
    charts = [api_parking_weekly_chart(parking_summaries)] if view in ("", "oversikt") else []
    parking_timeline = None
    day_navigation = None
    if view == "dagslinje":
        actions = api_parking_default_actions()[:1]
        selected_parking_day = parse_day(day)
        parking_timeline = await api_parking_day_timeline(session, selected_parking_day, now_dt)
        summary = parking_timeline["summary"]
        cards = [
            api_card(
                "Toppbelegg",
                f"{summary['peakCount']}/{parking_timeline['capacity']}",
                "plasser",
                f"Kl {summary['peakTimeLabel']}" if summary["peakTimeLabel"] else "Ingen registrert topp",
                "parking",
                href="/parkering/dagslinje",
            ),
            api_card(
                "Parkeringer",
                summary["sessionsCount"],
                "stk",
                f"{format_short_number(summary['paidAmountKr'])} kr",
                "parking",
                href="/parkering/parkeringer",
            ),
            api_card(
                "Beleggstid",
                format_short_number(summary["durationHours"], 1),
                "timer",
                f"{format_short_number(summary['utilizationPercent'], 1)}% av 23 plasser gjennom døgnet",
                "parking",
                href="/parkering/dagslinje",
            ),
            api_card(
                "Snittvarighet",
                format_short_number(summary["avgMinutes"], 0),
                "min",
                f"{summary['overflowCount']} over kapasitet" if summary["overflowCount"] else "Alle fikk plass i 23-sporsoppsettet",
                "status",
                href="/parkering/parkeringer",
            ),
        ]
        timeline_rows = []
        for row_group in parking_timeline["spaceRows"]:
            for space in row_group["spaces"]:
                for item in space["sessions"]:
                    timeline_rows.append(
                        {
                            "space": space["label"],
                            "start": item.get("start"),
                            "end": item.get("end"),
                            "plate": item.get("plate"),
                            "duration_minutes": item.get("durationMinutes"),
                            "paid": item.get("paid"),
                            "status": item.get("status"),
                            "area": item.get("area"),
                            "owner": item.get("owner"),
                        }
                    )
        tables = [
            api_table(
                "Dagslinje parkeringer",
                ["space", "start", "end", "plate", "duration_minutes", "paid", "status", "area", "owner"],
                timeline_rows,
            )
        ]
    elif view == "omrade":
        actions = api_parking_default_actions()[1:]
        date_from_value = api_filter_value(params, "date_from")
        date_to_value = api_filter_value(params, "date_to")
        area_context = await parking_area_overview_data(session, date_from_value, date_to_value)
        area_period = area_context["period"]
        missing_area_rows = await parking_area_missing_rows_for_period(session, area_period, 100)
        filters = [
            api_filter("date_from", "Dato / fra", "date", area_period["date_from"], "Tom = hele historikken"),
            api_filter("date_to", "Til dato", "date", area_period["date_to"], "Valgfritt tidsrom"),
        ]
        cards = [
            api_card("Periode", area_period["label"], "", area_period["detail"], "parking", href="/parkering/omrade"),
            api_card(
                "Unike biler",
                area_context["vehicle_total"],
                "stk",
                f"{format_short_number(area_context['parking_total'])} parkeringer i grunnlaget",
                "parking",
                href="/parkering/omrade",
            ),
            api_card(
                "Har område",
                area_context["vehicle_with_area"],
                "stk",
                f"{area_context['coverage_percent']} % dekning",
                "status",
                href="/parkering/omrade",
            ),
            api_card(
                "Mangler område",
                area_context["missing_area"],
                "stk",
                "Blankt, ikke funnet eller mangler kjøretøyrad",
                "status",
                href="/parkering/oppslag?filter=mangler-omrade",
            ),
            api_card(
                "Beløp",
                format_short_number(area_context["paid_total"]),
                "kr",
                "Parkering i valgt grunnlag",
                "revenue",
                href="/omsetning/oversikt",
            ),
        ]
        tables = [
            api_table(
                "Områder",
                ["omrade", "vehicles", "vehicle_share", "parkeringer", "parking_share", "paid", "last_seen"],
                area_context["rows"],
            ),
            api_table(
                "Kjøretøy uten område",
                ["plate", "navn", "parkering_count", "paid_total", "last_seen"],
                missing_area_rows,
            ),
        ]
    elif view == "bilstatistikk":
        actions = []
        revenue_leader = vehicle_rows[0][0] if vehicle_rows else None
        cards = [
            api_card("Kjøretøy", vehicle_count, "stk", "Registrert i kjøretøyregisteret", "status", href="/parkering/kjoretoy"),
            api_card(
                "Høyest omsetning",
                format_short_number(revenue_leader.paid_total if revenue_leader else 0),
                "kr",
                f"{revenue_leader.plate} · {format_short_number(revenue_leader.parkering_count)} parkeringer" if revenue_leader else "Ingen data",
                "revenue",
                href=f"/parkering/kjoretoy/{quote(revenue_leader.plate or '', safe='')}" if revenue_leader else "/parkering/kjoretoy",
            ),
            api_card(
                "Flest parkeringer",
                most_used_vehicle.parkering_count if most_used_vehicle else 0,
                "stk",
                f"{most_used_vehicle.plate} · {format_short_number(most_used_vehicle.paid_total)} kr" if most_used_vehicle else "Ingen data",
                "parking",
                href=f"/parkering/kjoretoy/{quote(most_used_vehicle.plate or '', safe='')}" if most_used_vehicle else "/parkering/kjoretoy",
            ),
            api_card("Toppliste", len(vehicle_rows), "biler", "Sortert etter samlet parkeringsomsetning", "parking", href="/parkering/bilstatistikk"),
        ]
        tables = [
            api_table(
                "Kjøretøy etter omsetning",
                ["plate", "vehicle_title", "navn", "omrade", "parkering_count", "paid_total", "first_seen", "last_seen"],
                [parking_vehicle_row_api(vehicle, details) for vehicle, details in vehicle_rows],
                meta={"rowLinkColumn": "plate", "totalRows": len(vehicle_rows)},
            )
        ]
    elif view == "prognose":
        parking_forecast = await build_parking_forecast(session, today, datetime.now(LOCAL_TZ))
        saved_forecasts = await saved_forecast_table(session, "parking")
        forecast_history_rows = await forecast_snapshot_history(session, "parking", 180)
        forecast_table_rows = api_parking_forecast_rows(parking_forecast)
        charts = []
        evolution_chart = api_parking_forecast_evolution_chart(forecast_history_rows)
        if evolution_chart:
            charts.append(evolution_chart)
        charts.append(
            api_chart(
                "Nåværende prognose mot faktisk",
                [row["period"] for row in forecast_table_rows],
                [
                    {"name": "Faktisk parkeringer", "data": [row["actual_parkeringer"] for row in forecast_table_rows], "type": "bar"},
                    {"name": "Prognose parkeringer", "data": [row["forecast_parkeringer"] for row in forecast_table_rows], "type": "bar"},
                ],
                "Siste beregning for dag, måned og år.",
                "bar",
                300,
            )
        )
        cards = [
            api_card("Dagsprognose", forecast_table_rows[0]["forecast_parkeringer"], "stk", f"{format_short_number(forecast_table_rows[0]['forecast_paid'])} kr", "parking", href="/parkering/prognose"),
            api_card("Månedsprognose", forecast_table_rows[1]["forecast_parkeringer"], "stk", f"{format_short_number(forecast_table_rows[1]['forecast_paid'])} kr", "revenue", href="/parkering/prognose"),
            api_card("Årsprognose", forecast_table_rows[2]["forecast_parkeringer"], "stk", f"{format_short_number(forecast_table_rows[2]['forecast_paid'])} kr", "revenue", href="/parkering/prognose"),
            api_card("Lagrede", len(saved_forecasts), "stk", "Parkeringssnapshots", "status", href="/parkering/prognose"),
        ]
        tables = [
            api_table(
                "Nåværende parkeringsprognose",
                ["period", "label", "actual_parkeringer", "forecast_parkeringer", "actual_paid", "forecast_paid", "actual_minutes", "forecast_minutes", "actual_vehicles", "forecast_vehicles", "tempo", "remaining_days"],
                forecast_table_rows,
            ),
            api_table(
                "Lagrede parkeringsprognoser",
                ["created_at", "period_type", "period_label", "actual_parkeringer", "forecast_parkeringer", "delta_parkeringer", "actual_paid", "forecast_paid", "delta_paid", "actual_vehicles", "forecast_vehicles", "period_done"],
                api_parking_saved_forecast_rows(saved_forecasts),
            ),
        ]
        actions = [
            {
                "key": "parking-save-forecast",
                "label": "Lagre parkeringsprognose",
                "method": "POST",
                "path": "/api/actions/parkering/save-forecast",
                "confirm": "Lagre prognosesnapshot for parkering nå?",
                "tone": "primary",
            },
            {
                "key": "easypark-refresh",
                "label": "Oppdater EasyPark",
                "method": "POST",
                "path": "/api/actions/parkering/refresh",
                "confirm": "Starte EasyPark-oppdatering for siste periode?",
                "tone": "default",
            },
        ]
    elif view == "oppslag":
        actions = api_parking_default_actions()[1:]
        oppslag_filter = api_filter_value(params, "filter").lower()
        area_only = oppslag_filter in {"mangler-omrade", "mangler-område", "missing-area"}
        if area_only:
            vehicles_missing_area = await parking_missing_area_rows(session, 1000)
            cards = [
                api_card("Mangler område", vehicle_missing_area_count, "stk", "Blanke og ikke funnet", "status", href="/parkering/oppslag?filter=mangler-omrade"),
                api_card("Blanke", vehicle_blank_area_count, "stk", "Kan fylles via områdeoppslag", "status", href="/parkering/oppslag?filter=mangler-omrade"),
                api_card("Ikke funnet", vehicle_area_not_found_count, "stk", "Kan nullstilles og slås opp på nytt", "status", href="/parkering/oppslag?filter=mangler-omrade"),
                api_card("Viser", len(vehicles_missing_area), "stk", "Maks 1000 i listen", "parking", href="/parkering/oppslag?filter=mangler-omrade"),
            ]
            tables = [
                api_table(
                    "Kjøretøy uten område",
                    ["plate", "navn", "omrade", "parkering_count", "paid_total", "last_seen", "path"],
                    [
                        {
                            **row_to_dict(row, ["plate", "navn", "omrade", "parkering_count", "paid_total", "last_seen"]),
                            "path": f"/parkering/kjoretoy/{quote(row.plate or '', safe='')}",
                        }
                        for row, _ in vehicles_missing_area
                    ],
                )
            ]
        else:
            cards = [
                api_card(
                    "Mangler navn",
                    vehicle_missing_name_count,
                    "biler",
                    f"{format_short_number(vehicle_blank_name_count)} blanke · {format_short_number(vehicle_name_not_found_count)} ikke funnet",
                    "status",
                    href="/parkering/navn-oppslag",
                ),
                api_card(
                    "Mangler område",
                    vehicle_missing_area_count,
                    "biler",
                    f"{format_short_number(vehicle_blank_area_count)} blanke · {format_short_number(vehicle_area_not_found_count)} ikke funnet",
                    "status",
                    href="/parkering/omrade-oppslag",
                ),
                api_card(
                    "Navn ikke funnet",
                    vehicle_name_not_found_count,
                    "biler",
                    "Kan kontrolleres i navnearbeidslisten",
                    "status",
                    href="/parkering/navn-oppslag",
                ),
                api_card(
                    "Område ikke funnet",
                    vehicle_area_not_found_count,
                    "biler",
                    "Kan nullstilles og slås opp på nytt",
                    "status",
                    href="/parkering/omrade-oppslag",
                ),
            ]
            tables = [
                api_table(
                    "Arbeidslister",
                    ["tool", "path", "description", "count"],
                    [
                        api_tool_row(
                            "Navnoppslag",
                            "/parkering/navn-oppslag",
                            f"Koble kjøretøy mot navn/SUN2. {format_short_number(vehicle_name_not_found_count)} er ikke funnet.",
                            vehicle_missing_name_count,
                        ),
                        api_tool_row(
                            "Områdeoppslag",
                            "/parkering/omrade-oppslag",
                            f"Sett område på kjøretøy. {format_short_number(vehicle_area_not_found_count)} er ikke funnet.",
                            vehicle_missing_area_count,
                        ),
                        api_tool_row("Kjøretøyoversikt", "/parkering/kjoretoy", "Kjøretøyregister med redigering og detaljer.", vehicle_count),
                    ],
                ),
            ]
    if int_or_zero(vehicle_area_not_found_count) > 0 and view in ("", "oversikt", "kjoretoy", "omrade", "oppslag"):
        actions.append(
            {
                "key": "clear-area-not-found",
                "label": "Fjern område 'ikke funnet'",
                "method": "POST",
                "path": "/api/actions/parkering/clear-area-not-found",
                "confirm": (
                    f"Nullstille område på {format_short_number(vehicle_area_not_found_count)} kjøretøy "
                    "der område er satt til 'ikke funnet'? De blir liggende som blanke og kan slås opp på nytt."
                ),
                "tone": "default",
            }
        )
    return {
        "title": v2_module_title("parkering", view),
        "subtitle": {
            "dagslinje": "Kapasitet, toppbelegg og parkeringsforløp gjennom valgt dag.",
            "omrade": "Geografisk fordeling av kjøretøy og parkeringer i valgt periode.",
            "bilstatistikk": "Kjøretøy rangert etter samlet parkeringsomsetning og antall besøk.",
            "prognose": "Forventet parkeringsutvikling sammenlignet med faktisk resultat.",
            "oppslag": "Samlet status og arbeidslister for manglende kjøretøyopplysninger.",
        }.get(view, "EasyPark, aktive parkeringer og kjøretøygrunnlag."),
        "cards": cards,
        "charts": charts,
        "tables": tables,
        "actions": actions,
        "filters": filters,
        "dayNavigation": day_navigation,
        "parkingTimeline": parking_timeline,
    }

