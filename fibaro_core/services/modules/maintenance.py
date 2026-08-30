"""Maintenance module response assembly, independent of HTTP registration."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fibaro_core.models import ImportJobStatus, MaintenanceLogEntry, SiteVisit
from fibaro_core.services.presentation import api_card, api_table
from fibaro_core.services.summaries.periods import add_months
from sqlalchemy import func, select
from time_formatting import format_source_datetime_short
from typing import Any, Dict
from v2_navigation import v2_module_title


@dataclass
class Dependencies:
    OWNTRACKS_SITE_VISIT_LOCATION_KEY: Any
    SITE_VISIT_ACTIVE_MAX_HOURS: Any
    api_maintenance_log_edit: Any
    maintenance_log_row: Any
    site_visit_is_current: Any
    site_visit_is_stale: Any
    site_visit_label: Any
    site_visit_row: Any


async def render(session, request, module, view, q, day, now_dt, dependencies):
    OWNTRACKS_SITE_VISIT_LOCATION_KEY = dependencies.OWNTRACKS_SITE_VISIT_LOCATION_KEY
    SITE_VISIT_ACTIVE_MAX_HOURS = dependencies.SITE_VISIT_ACTIVE_MAX_HOURS
    api_maintenance_log_edit = dependencies.api_maintenance_log_edit
    maintenance_log_row = dependencies.maintenance_log_row
    site_visit_is_current = dependencies.site_visit_is_current
    site_visit_is_stale = dependencies.site_visit_is_stale
    site_visit_label = dependencies.site_visit_label
    site_visit_row = dependencies.site_visit_row
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
    edit_config = api_maintenance_log_edit(now_dt.replace(second=0, microsecond=0))
    if view == "besok":
        site_visits = (
            await session.execute(
                select(SiteVisit)
                .where(SiteVisit.location_key == OWNTRACKS_SITE_VISIT_LOCATION_KEY)
                .order_by(SiteVisit.started_at.desc(), SiteVisit.id.desc())
                .limit(200)
            )
        ).scalars().all()
        site_visit_import_status = (
            await session.execute(
                select(ImportJobStatus)
                .where(ImportJobStatus.job_name == "owntracks_site_visits")
                .limit(1)
            )
        ).scalars().first()
        site_visit_counts = {
            int(row.visit_id): int(row.tasks_count)
            for row in (
                await session.execute(
                    select(
                        MaintenanceLogEntry.site_visit_id.label("visit_id"),
                        func.count(MaintenanceLogEntry.id).label("tasks_count"),
                    )
                    .where(MaintenanceLogEntry.site_visit_id.isnot(None))
                    .group_by(MaintenanceLogEntry.site_visit_id)
                )
            )
            if row.visit_id is not None
        }
        today_visit_count = sum(
            1
            for row in site_visits
            if row.started_at and today_start <= row.started_at < tomorrow_start
        )
        active_visit = next(
            (row for row in site_visits if site_visit_is_current(row, now_dt)),
            None,
        )
        stale_visits = [row for row in site_visits if site_visit_is_stale(row, now_dt)]
        latest_visit_sync = (
            site_visit_import_status.last_success_at
            if site_visit_import_status and site_visit_import_status.last_success_at
            else max((row.last_synced_at for row in site_visits if row.last_synced_at), default=None)
        )
        site_visit_sync_detail = (
            site_visit_import_status.message
            if site_visit_import_status and site_visit_import_status.message
            else "Fra OwnTracks API"
        )
        visit_rows = [
            site_visit_row(row, site_visit_counts.get(int(row.id or 0), 0))
            for row in site_visits
        ]
        return {
            "title": v2_module_title("vedlikehold", view),
            "subtitle": "Lilletorget-besøk fra OwnTracks med oppgaver og besøksnotater.",
            "cards": [
                api_card("Besøk i dag", today_visit_count, "stk", "Registrert fra OwnTracks", "status", href="/vedlikehold/besok"),
                api_card(
                    "Aktivt besøk",
                    "Ja" if active_visit else "Nei",
                    "",
                    site_visit_label(active_visit) or "Ingen aktivt besøk",
                    "status",
                    href="/vedlikehold/besok",
                ),
                api_card(
                    "Mangler avslutning",
                    len(stale_visits),
                    "stk",
                    f"Åpne lenger enn {SITE_VISIT_ACTIVE_MAX_HOURS} timer",
                    "danger" if stale_visits else "status",
                    href="/vedlikehold/besok",
                ),
                api_card(
                    "Sist synket",
                    format_source_datetime_short(latest_visit_sync) if latest_visit_sync else "-",
                    "",
                    site_visit_sync_detail[:120],
                    "status",
                    href="/vedlikehold/besok",
                ),
            ],
            "tables": [
                api_table(
                    "Lilletorget-besøk",
                    ["started_at", "ended_at", "duration", "status", "tasks_count", "notes"],
                    visit_rows,
                ),
            ],
        }

    logs = (
        await session.execute(
            select(MaintenanceLogEntry)
            .order_by(MaintenanceLogEntry.performed_at.desc(), MaintenanceLogEntry.id.desc())
            .limit(300)
        )
    ).scalars().all()
    linked_visit_ids = sorted({int(row.site_visit_id) for row in logs if row.site_visit_id})
    site_visit_by_id: Dict[int, SiteVisit] = {}
    if linked_visit_ids:
        linked_visits = (
            await session.execute(
                select(SiteVisit).where(SiteVisit.id.in_(linked_visit_ids))
            )
        ).scalars().all()
        site_visit_by_id = {int(row.id): row for row in linked_visits if row.id}
    today_count = sum(
        1
        for row in logs
        if row.performed_at and today_start <= row.performed_at < tomorrow_start
    )
    month_count = sum(
        1
        for row in logs
        if row.performed_at and month_start_dt <= row.performed_at < tomorrow_start
    )
    follow_up_logs = [
        row
        for row in logs
        if row.follow_up_needed and (row.status or "").strip().casefold() != "lukket"
    ]
    sunbed_month_count = sum(
        1
        for row in logs
        if (row.target_type or "").strip().casefold() == "seng"
        and row.performed_at
        and month_start_dt <= row.performed_at < tomorrow_start
    )
    latest = logs[0] if logs else None
    log_rows = [
        maintenance_log_row(row, site_visit_by_id.get(int(row.site_visit_id or 0)))
        for row in logs
    ]
    follow_up_edit = dict(edit_config)
    follow_up_edit.pop("createEndpoint", None)
    return {
        "title": v2_module_title("vedlikehold", view),
        "subtitle": "Arbeid, observasjoner og oppfølgingspunkter på Lilletorget.",
        "cards": [
            api_card("Må følges opp", len(follow_up_logs), "stk", "Åpne punkter som krever handling", "danger" if follow_up_logs else "status", href="/vedlikehold/oversikt"),
            api_card("I dag", today_count, "stk", "Registrerte aktiviteter", "status", href="/vedlikehold/oversikt"),
            api_card("Denne måneden", month_count, "stk", f"{sunbed_month_count} gjelder solsenger", "status", href="/vedlikehold/oversikt"),
            api_card("Sist logget", format_source_datetime_short(latest.performed_at) if latest else "-", "", latest.summary[:80] if latest and latest.summary else "Ingen registreringer", "status", href="/vedlikehold/oversikt"),
        ],
        "tables": [
            api_table(
                "Krever oppfølging",
                ["performed_at", "target_name", "priority", "summary", "follow_up_text", "status"],
                [
                    maintenance_log_row(
                        row,
                        site_visit_by_id.get(int(row.site_visit_id or 0)),
                    )
                    for row in follow_up_logs
                ],
                edit=follow_up_edit,
            ),
            api_table(
                "Siste vedlikehold",
                ["performed_at", "target_name", "action_type", "summary", "status", "performed_by"],
                log_rows,
                edit=edit_config,
            ),
        ],
    }

