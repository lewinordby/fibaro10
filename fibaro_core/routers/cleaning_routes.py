"""Cleaning HTTP routes; runtime services are supplied by composition."""

from cleaning_robot_domain import (
    cleaning_provider,
    cleaning_provider_label,
    cleaning_robot_external_id,
    cleaning_robot_sort_key,
)
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fibaro_core.export_definitions import (
    ROBOROCK_JOB_COLUMNS,
    ROBOROCK_MAP_COLUMNS,
    ROBOROCK_ROBOT_COLUMNS,
    ROBOROCK_SCHEDULE_COLUMNS,
    ROBOROCK_STATUS_COLUMNS,
    ROBOROCK_TELEMETRY_COLUMNS,
    ROBOROCK_TELEMETRY_DISPLAY_FIELDS,
    ROBOROCK_TELEMETRY_EVENT_COLUMNS,
)
from fibaro_core.models import (
    CleaningZone,
    RoborockCleanJob,
    RoborockCleaningProfile,
    RoborockCleaningZoneMapping,
    RoborockCommandRun,
    RoborockConsumableSnapshot,
    RoborockDoorAutomation,
    RoborockMapSnapshot,
    RoborockProbeResult,
    RoborockRobot,
    RoborockSchedule,
    RoborockScheduleSnapshot,
    RoborockStatusSample,
    RoborockTelemetryEvent,
    RoborockTelemetrySample,
)
from fibaro_core.routers.bundle import RouterBundle
from fibaro_core.schemas import RoborockCleaningProfileIn, RoborockControlIn, RoborockDoorAutomationIn
from roborock_domain import (
    cleaning_water_mode_label,
    format_seconds_as_hours,
    roborock_bool_label,
    roborock_charge_label,
    roborock_dock_error_label,
    roborock_dock_type_label,
    roborock_error_label,
    roborock_fan_label,
    roborock_job_status,
    roborock_mop_label,
    roborock_next_schedule_score,
    roborock_next_schedule_text,
    roborock_rounds_label,
    roborock_schedule_text,
    roborock_signal_label,
    roborock_state_label,
    roborock_telemetry_value_label,
)
from roborock_door_automation import unique_ints
from roborock_profiles import cleaning_profile_options
from roborock_refills import build_refill_log, iso_week_start as refill_iso_week_start
from roborock_reports import build_night_report, report_window
from roborock_water import build_water_report
from roborock_weekly import build_weekly_job_log
from roborock_zones import RoborockZoneScheduleError
from sqlalchemy import func, or_, select
from time_formatting import (
    LOCAL_TZ,
    api_local_iso,
    local_naive_to_utc_naive,
    local_now_naive,
    utc_naive_to_local_naive,
)
from typing import Any, Callable, Dict, Optional
from value_parsing import int_value
import asyncio
import json
import secrets


@dataclass
class Dependencies:
    DREAME_CONTROL_TOKEN: Any
    ROBOROCK_CONTROL_TOKEN: Any
    api_roborock_active_cycle: Callable[..., Any]
    apply_roborock_cleaning_profile_values: Callable[..., Any]
    async_session: Callable[..., Any]
    ensure_default_roborock_door_automation: Callable[..., Any]
    import_roborock_cleaning_zones: Callable[..., Any]
    post_dreame_control: Callable[..., Any]
    post_roborock_control: Callable[..., Any]
    require_master: Callable[..., Any]
    roborock_cleaning_profile_payload: Callable[..., Any]
    roborock_door_automation_payload: Callable[..., Any]
    roborock_water_interlock_from_sample: Callable[..., Any]
    row_to_dict: Callable[..., Any]
    templates: Any


def create_router(dependencies: Dependencies) -> RouterBundle:
    router = APIRouter()


    @router.get("/renhold/oversikt", response_class=HTMLResponse)
    async def cleaning_overview(request: Request):
        async_session = dependencies.async_session
        templates = dependencies.templates
        async with async_session() as session:
            robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
            robots.sort(key=cleaning_robot_sort_key)
            latest_status = {}
            latest_jobs = {}
            next_schedules = {}
            robot_duids = [robot.duid for robot in robots]
            if robot_duids:
                latest_status_subq = (
                    select(
                        RoborockStatusSample.robot_duid.label("robot_duid"),
                        func.max(RoborockStatusSample.timestamp).label("latest_at"),
                    )
                    .where(RoborockStatusSample.robot_duid.in_(robot_duids))
                    .group_by(RoborockStatusSample.robot_duid)
                    .subquery()
                )
                status_rows = (
                    await session.execute(
                        select(RoborockStatusSample).join(
                            latest_status_subq,
                            (RoborockStatusSample.robot_duid == latest_status_subq.c.robot_duid)
                            & (RoborockStatusSample.timestamp == latest_status_subq.c.latest_at),
                        )
                    )
                ).scalars().all()
                latest_status = {row.robot_duid: row for row in status_rows}

                latest_job_subq = (
                    select(
                        RoborockCleanJob.robot_duid.label("robot_duid"),
                        func.max(RoborockCleanJob.begin_at).label("latest_at"),
                    )
                    .where(RoborockCleanJob.robot_duid.in_(robot_duids))
                    .group_by(RoborockCleanJob.robot_duid)
                    .subquery()
                )
                job_rows = (
                    await session.execute(
                        select(RoborockCleanJob).join(
                            latest_job_subq,
                            (RoborockCleanJob.robot_duid == latest_job_subq.c.robot_duid)
                            & (RoborockCleanJob.begin_at == latest_job_subq.c.latest_at),
                        )
                    )
                ).scalars().all()
                latest_jobs = {row.robot_duid: row for row in job_rows}

                schedule_rows = (
                    await session.execute(
                        select(RoborockSchedule)
                        .where(RoborockSchedule.robot_duid.in_(robot_duids))
                        .where(RoborockSchedule.enabled == True)
                        .where(RoborockSchedule.deleted_at.is_(None))
                    )
                ).scalars().all()
                schedules_by_robot: Dict[str, list[RoborockSchedule]] = {}
                for schedule in schedule_rows:
                    schedules_by_robot.setdefault(schedule.robot_duid, []).append(schedule)
                next_schedules = {
                    duid: min(schedules, key=roborock_next_schedule_score)
                    for duid, schedules in schedules_by_robot.items()
                    if schedules
                }
        return templates.TemplateResponse(
            request,
            "cleaning_overview.html",
            {
                "robots": robots,
                "latest_status": latest_status,
                "latest_jobs": latest_jobs,
                "next_schedules": next_schedules,
            },
        )

    @router.get("/api/renhold/night-report")
    async def api_cleaning_night_report(day: Optional[str] = None):
        async_session = dependencies.async_session
        today = datetime.now(LOCAL_TZ).date()
        latest_day = today + timedelta(days=1)
        try:
            selected_day = date.fromisoformat(day) if day else today
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Ugyldig dato. Bruk YYYY-MM-DD.") from exc
        if selected_day > latest_day:
            raise HTTPException(status_code=400, detail="Rapporten kan bare vise neste planlagte natt.")

        window = report_window(selected_day)
        job_start = local_naive_to_utc_naive(window["start"])
        job_end = local_naive_to_utc_naive(window["end"])
        telemetry_start = window["start"] - timedelta(minutes=15)
        telemetry_end = window["end"] + timedelta(minutes=15)
        async with async_session() as session:
            robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
            robots.sort(key=cleaning_robot_sort_key)
            robot_duids = [robot.duid for robot in robots]
            jobs = (
                await session.execute(
                    select(RoborockCleanJob)
                    .where(RoborockCleanJob.robot_duid.in_(robot_duids or [""]))
                    .where(RoborockCleanJob.begin_at >= job_start)
                    .where(RoborockCleanJob.begin_at < job_end)
                    .order_by(RoborockCleanJob.robot_duid, RoborockCleanJob.begin_at)
                )
            ).scalars().all()
            telemetry_samples = (
                await session.execute(
                    select(RoborockTelemetrySample)
                    .where(RoborockTelemetrySample.robot_duid.in_(robot_duids or [""]))
                    .where(RoborockTelemetrySample.timestamp >= telemetry_start)
                    .where(RoborockTelemetrySample.timestamp <= telemetry_end)
                    .order_by(RoborockTelemetrySample.robot_duid, RoborockTelemetrySample.timestamp)
                )
            ).scalars().all()
            water_events = (
                await session.execute(
                    select(RoborockTelemetryEvent)
                    .where(RoborockTelemetryEvent.robot_duid.in_(robot_duids or [""]))
                    .where(RoborockTelemetryEvent.category == "vann")
                    .where(RoborockTelemetryEvent.timestamp >= window["start"])
                    .where(RoborockTelemetryEvent.timestamp <= window["end"])
                    .order_by(
                        RoborockTelemetryEvent.robot_duid,
                        RoborockTelemetryEvent.timestamp,
                        RoborockTelemetryEvent.id,
                    )
                )
            ).scalars().all()
            schedules = (
                await session.execute(
                    select(RoborockSchedule)
                    .where(RoborockSchedule.robot_duid.in_(robot_duids or [""]))
                    .where(RoborockSchedule.deleted_at.is_(None))
                    .order_by(RoborockSchedule.robot_duid, RoborockSchedule.cron)
                )
            ).scalars().all()
            schedule_snapshots = (
                await session.execute(
                    select(RoborockScheduleSnapshot)
                    .where(RoborockScheduleSnapshot.robot_duid.in_(robot_duids or [""]))
                    .where(RoborockScheduleSnapshot.captured_at <= window["end"])
                    .order_by(
                        RoborockScheduleSnapshot.robot_duid,
                        RoborockScheduleSnapshot.captured_at,
                        RoborockScheduleSnapshot.id,
                    )
                )
            ).scalars().all()
            latest_probe_subq = (
                select(func.max(RoborockProbeResult.id).label("latest_id"))
                .where(RoborockProbeResult.robot_duid.in_(robot_duids or [""]))
                .where(RoborockProbeResult.source == "local-telemetry")
                .where(RoborockProbeResult.timestamp <= window["end"])
                .group_by(RoborockProbeResult.robot_duid, RoborockProbeResult.command)
                .subquery()
            )
            probes = (
                await session.execute(
                    select(RoborockProbeResult)
                    .join(latest_probe_subq, RoborockProbeResult.id == latest_probe_subq.c.latest_id)
                    .where(
                        RoborockProbeResult.command.in_(
                            [
                                "GET_SMART_WASH_PARAMS",
                                "GET_WASH_TOWEL_MODE",
                                "GET_CUSTOM_MODE",
                                "GET_WATER_BOX_CUSTOM_MODE",
                                "APP_GET_DRYER_SETTING",
                                "GET_DUST_COLLECTION_MODE",
                                "GET_DUST_COLLECTION_SWITCH_STATUS",
                                "GET_CARPET_MODE",
                                "GET_DND_TIMER",
                            ]
                        )
                    )
                )
            ).scalars().all()
        return build_night_report(
            selected_day,
            list(robots),
            list(jobs),
            list(telemetry_samples),
            list(probes),
            generated_at=local_now_naive(),
            schedules=list(schedules),
            schedule_snapshots=list(schedule_snapshots),
            water_events=list(water_events),
        )

    @router.get("/api/renhold/weekly-jobs")
    async def api_cleaning_weekly_jobs(week: Optional[str] = Query(default=None)):
        async_session = dependencies.async_session
        now = local_now_naive()
        try:
            selected_week = refill_iso_week_start(week, today=now.date())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        current_week = refill_iso_week_start(None, today=now.date())
        if selected_week > current_week:
            raise HTTPException(status_code=422, detail="Ukesloggen kan ikke vise en fremtidig uke.")

        period_start = datetime.combine(selected_week, time.min)
        period_end = period_start + timedelta(days=7)
        job_start = local_naive_to_utc_naive(period_start)
        job_end = local_naive_to_utc_naive(period_end)
        telemetry_start = period_start - timedelta(minutes=3)
        telemetry_end = period_end + timedelta(minutes=12)
        async with async_session() as session:
            robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
            robots.sort(key=cleaning_robot_sort_key)
            robot_duids = [robot.duid for robot in robots]
            jobs = (
                await session.execute(
                    select(RoborockCleanJob)
                    .where(RoborockCleanJob.robot_duid.in_(robot_duids or [""]))
                    .where(RoborockCleanJob.begin_at >= job_start)
                    .where(RoborockCleanJob.begin_at < job_end)
                    .where(RoborockCleanJob.end_at.is_not(None))
                    .where(RoborockCleanJob.complete.is_(True))
                    .where(or_(RoborockCleanJob.error_code.is_(None), RoborockCleanJob.error_code == 0))
                    .order_by(RoborockCleanJob.begin_at.desc(), RoborockCleanJob.id.desc())
                )
            ).scalars().all()
            telemetry_samples = (
                await session.execute(
                    select(RoborockTelemetrySample)
                    .where(RoborockTelemetrySample.robot_duid.in_(robot_duids or [""]))
                    .where(RoborockTelemetrySample.timestamp >= telemetry_start)
                    .where(RoborockTelemetrySample.timestamp < telemetry_end)
                    .where(RoborockTelemetrySample.in_cleaning.is_(True))
                    .order_by(RoborockTelemetrySample.robot_duid, RoborockTelemetrySample.timestamp)
                )
            ).scalars().all()
        return build_weekly_job_log(
            selected_week,
            list(robots),
            list(jobs),
            list(telemetry_samples),
            generated_at=now,
        )

    @router.get("/api/renhold/water-report")
    async def api_cleaning_water_report(days: int = Query(default=7, ge=1, le=90)):
        async_session = dependencies.async_session
        now = local_now_naive()
        period_start = datetime.combine(now.date() - timedelta(days=days - 1), time.min)
        job_start = local_naive_to_utc_naive(period_start)
        job_end = local_naive_to_utc_naive(now)
        async with async_session() as session:
            robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
            robots.sort(key=cleaning_robot_sort_key)
            robot_duids = [robot.duid for robot in robots]
            jobs = (
                await session.execute(
                    select(RoborockCleanJob)
                    .where(RoborockCleanJob.robot_duid.in_(robot_duids or [""]))
                    .where(RoborockCleanJob.begin_at >= job_start)
                    .where(RoborockCleanJob.begin_at <= job_end)
                    .order_by(RoborockCleanJob.robot_duid, RoborockCleanJob.begin_at)
                )
            ).scalars().all()
            events = (
                await session.execute(
                    select(RoborockTelemetryEvent)
                    .where(RoborockTelemetryEvent.robot_duid.in_(robot_duids or [""]))
                    .where(RoborockTelemetryEvent.category == "vann")
                    .where(RoborockTelemetryEvent.timestamp >= period_start)
                    .where(RoborockTelemetryEvent.timestamp <= now)
                    .order_by(RoborockTelemetryEvent.timestamp.desc(), RoborockTelemetryEvent.id.desc())
                    .limit(1000)
                )
            ).scalars().all()
            latest_telemetry_subq = (
                select(func.max(RoborockTelemetrySample.id).label("latest_id"))
                .where(RoborockTelemetrySample.robot_duid.in_(robot_duids or [""]))
                .group_by(RoborockTelemetrySample.robot_duid)
                .subquery()
            )
            telemetry_samples = (
                await session.execute(
                    select(RoborockTelemetrySample).join(
                        latest_telemetry_subq,
                        RoborockTelemetrySample.id == latest_telemetry_subq.c.latest_id,
                    )
                )
            ).scalars().all()
            latest_probe_subq = (
                select(func.max(RoborockProbeResult.id).label("latest_id"))
                .where(RoborockProbeResult.robot_duid.in_(robot_duids or [""]))
                .where(RoborockProbeResult.source == "local-telemetry")
                .group_by(RoborockProbeResult.robot_duid, RoborockProbeResult.command)
                .subquery()
            )
            probes = (
                await session.execute(
                    select(RoborockProbeResult)
                    .join(latest_probe_subq, RoborockProbeResult.id == latest_probe_subq.c.latest_id)
                    .where(
                        RoborockProbeResult.command.in_(
                            ["GET_SMART_WASH_PARAMS", "GET_WASH_TOWEL_MODE", "GET_WATER_BOX_CUSTOM_MODE"]
                        )
                    )
                )
            ).scalars().all()
        return build_water_report(
            days,
            list(robots),
            list(jobs),
            list(telemetry_samples),
            list(events),
            list(probes),
            generated_at=now,
        )

    @router.get("/api/renhold/refill-log")
    async def api_cleaning_refill_log(week: Optional[str] = Query(default=None)):
        async_session = dependencies.async_session
        now = local_now_naive()
        try:
            selected_week = refill_iso_week_start(week, today=now.date())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        period_start = datetime.combine(selected_week, time.min)
        period_end = datetime.combine(selected_week + timedelta(days=7), time.min)
        query_start = period_start - timedelta(days=7)
        query_end = min(period_end + timedelta(days=7), now)
        async with async_session() as session:
            robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
            robots.sort(key=cleaning_robot_sort_key)
            robot_duids = [robot.duid for robot in robots]
            latest_telemetry_subq = (
                select(func.max(RoborockTelemetrySample.id).label("latest_id"))
                .where(RoborockTelemetrySample.robot_duid.in_(robot_duids or [""]))
                .where(RoborockTelemetrySample.clear_water_status.is_not(None))
                .group_by(RoborockTelemetrySample.robot_duid)
                .subquery()
            )
            telemetry_samples = (
                await session.execute(
                    select(RoborockTelemetrySample).join(
                        latest_telemetry_subq,
                        RoborockTelemetrySample.id == latest_telemetry_subq.c.latest_id,
                    )
                )
            ).scalars().all()
            events = (
                await session.execute(
                    select(RoborockTelemetryEvent)
                    .where(RoborockTelemetryEvent.robot_duid.in_(robot_duids or [""]))
                    .where(RoborockTelemetryEvent.field_name == "clear_water_status")
                    .where(RoborockTelemetryEvent.timestamp >= query_start)
                    .where(RoborockTelemetryEvent.timestamp < query_end)
                    .order_by(RoborockTelemetryEvent.timestamp, RoborockTelemetryEvent.id)
                )
            ).scalars().all()
        water_capable_duids = {
            row.robot_duid for row in telemetry_samples if row.clear_water_status is not None
        }
        return build_refill_log(
            selected_week,
            list(robots),
            list(events),
            generated_at=now,
            water_capable_duids=water_capable_duids,
        )

    @router.get("/api/renhold/robots/{duid}")
    async def api_cleaning_robot_detail(request: Request, duid: str):
        DREAME_CONTROL_TOKEN = dependencies.DREAME_CONTROL_TOKEN
        ROBOROCK_CONTROL_TOKEN = dependencies.ROBOROCK_CONTROL_TOKEN
        api_roborock_active_cycle = dependencies.api_roborock_active_cycle
        async_session = dependencies.async_session
        ensure_default_roborock_door_automation = dependencies.ensure_default_roborock_door_automation
        roborock_cleaning_profile_payload = dependencies.roborock_cleaning_profile_payload
        roborock_door_automation_payload = dependencies.roborock_door_automation_payload
        roborock_water_interlock_from_sample = dependencies.roborock_water_interlock_from_sample
        row_to_dict = dependencies.row_to_dict
        async with async_session() as session:
            robot = (await session.execute(select(RoborockRobot).where(RoborockRobot.duid == duid))).scalars().first()
            if not robot:
                raise HTTPException(status_code=404, detail="Ukjent robot")
            statuses = (
                await session.execute(
                    select(RoborockStatusSample)
                    .where(RoborockStatusSample.robot_duid == duid)
                    .order_by(RoborockStatusSample.timestamp.desc())
                    .limit(400)
                )
            ).scalars().all()
            jobs = (
                await session.execute(
                    select(RoborockCleanJob)
                    .where(RoborockCleanJob.robot_duid == duid)
                    .order_by(RoborockCleanJob.begin_at.desc())
                    .limit(50)
                )
            ).scalars().all()
            schedules = (
                await session.execute(
                    select(RoborockSchedule)
                    .where(RoborockSchedule.robot_duid == duid)
                    .order_by(RoborockSchedule.cron)
                )
            ).scalars().all()
            cleaning_zone_pairs = (
                await session.execute(
                    select(RoborockCleaningZoneMapping, CleaningZone)
                    .join(CleaningZone, CleaningZone.id == RoborockCleaningZoneMapping.zone_id)
                    .where(RoborockCleaningZoneMapping.robot_duid == duid)
                    .order_by(CleaningZone.zone_number)
                )
            ).all()
            consumables = (
                await session.execute(
                    select(RoborockConsumableSnapshot)
                    .where(RoborockConsumableSnapshot.robot_duid == duid)
                    .order_by(RoborockConsumableSnapshot.timestamp.desc())
                    .limit(1)
                )
            ).scalars().first()
            latest_map = (
                await session.execute(
                    select(RoborockMapSnapshot)
                    .where(RoborockMapSnapshot.robot_duid == duid)
                    .order_by(RoborockMapSnapshot.timestamp.desc())
                    .limit(1)
                )
            ).scalars().first()
            telemetry_samples = (
                await session.execute(
                    select(RoborockTelemetrySample)
                    .where(RoborockTelemetrySample.robot_duid == duid)
                    .order_by(RoborockTelemetrySample.timestamp.desc(), RoborockTelemetrySample.id.desc())
                    .limit(120)
                )
            ).scalars().all()
            telemetry_events = (
                await session.execute(
                    select(RoborockTelemetryEvent)
                    .where(RoborockTelemetryEvent.robot_duid == duid)
                    .order_by(RoborockTelemetryEvent.timestamp.desc(), RoborockTelemetryEvent.id.desc())
                    .limit(150)
                )
            ).scalars().all()
            latest_probe_subq = (
                select(func.max(RoborockProbeResult.id).label("latest_id"))
                .where(RoborockProbeResult.robot_duid == duid)
                .where(RoborockProbeResult.source == "local-telemetry")
                .group_by(RoborockProbeResult.command)
                .subquery()
            )
            telemetry_probes = (
                await session.execute(
                    select(RoborockProbeResult)
                    .join(latest_probe_subq, RoborockProbeResult.id == latest_probe_subq.c.latest_id)
                    .order_by(RoborockProbeResult.command)
                )
            ).scalars().all()
            command_runs = (
                await session.execute(
                    select(RoborockCommandRun)
                    .where(RoborockCommandRun.robot_duid == duid)
                    .order_by(RoborockCommandRun.requested_at.desc(), RoborockCommandRun.id.desc())
                    .limit(30)
                )
            ).scalars().all()
            cleaning_profiles = (
                await session.execute(
                    select(RoborockCleaningProfile).order_by(
                        RoborockCleaningProfile.active.desc(),
                        RoborockCleaningProfile.cleaning_type,
                        RoborockCleaningProfile.name,
                    )
                )
            ).scalars().all()
            door_automation = (
                await session.execute(
                    select(RoborockDoorAutomation).where(RoborockDoorAutomation.robot_duid == duid)
                )
            ).scalars().first()
            if not door_automation and str(robot.name or "").strip().lower() == "1.etg b":
                door_automation = await ensure_default_roborock_door_automation(session)
                await session.commit()
            door_automation_data = None
            if door_automation:
                door_automation_data, _ = await roborock_door_automation_payload(session, door_automation)

        latest_status = statuses[0] if statuses else None
        metadata = ((robot.extra or {}).get("metadata") or {}) if isinstance(robot.extra, dict) else {}
        cleaning_zone_import = (
            (robot.extra or {}).get("cleaning_zone_import") or {}
            if isinstance(robot.extra, dict)
            else {}
        )
        latest_raw = latest_status.raw if latest_status and isinstance(latest_status.raw, dict) else {}
        network = latest_raw.get("network") if isinstance(latest_raw.get("network"), dict) else {}
        provider = cleaning_provider(robot.provider)
        status_rows = []
        for row in statuses:
            item = row_to_dict(row, [column for column in ROBOROCK_STATUS_COLUMNS if column != "raw"])
            item.update(
                {
                    "state_label": row.state_name if provider == "dreame" and row.state_name else roborock_state_label(row.state_code),
                    "error_label": roborock_error_label(row.error_code),
                    "fan_label": roborock_fan_label(row.fan_power),
                    "mop_label": roborock_mop_label(row.mop_mode),
                    "charge_label": roborock_charge_label(row.charge_status),
                    "signal_label": roborock_signal_label(row.rssi),
                }
            )
            status_rows.append(item)
        job_rows = []
        for row in jobs:
            item = row_to_dict(row, [column for column in ROBOROCK_JOB_COLUMNS if column != "raw"])
            # Roborock job timestamps are Unix instants stored as UTC-naive values.
            # Add an explicit Oslo offset before they reach browsers, which otherwise
            # interpret the bare timestamp as local time and show it two hours early.
            item["begin_at"] = api_local_iso(utc_naive_to_local_naive(row.begin_at))
            item["end_at"] = api_local_iso(utc_naive_to_local_naive(row.end_at))
            job_status_key, job_status_label = roborock_job_status(row.complete, row.error_code, row.end_at)
            item.update(
                {
                    "status": job_status_key,
                    "status_label": job_status_label,
                    "complete_label": roborock_bool_label(row.complete),
                    "error_label": roborock_error_label(row.error_code),
                    "rounds_label": roborock_rounds_label(row.clean_times),
                }
            )
            job_rows.append(item)
        schedule_rows = []
        for row in schedules:
            item = row_to_dict(row, [column for column in ROBOROCK_SCHEDULE_COLUMNS if column != "raw"])
            item["updated_at"] = api_local_iso(row.updated_at)
            item["deleted_at"] = api_local_iso(row.deleted_at)
            item.update(
                {
                    "schedule_label": roborock_schedule_text(row),
                    "next_label": roborock_next_schedule_text(row) if row.enabled and not row.deleted_at else None,
                    "enabled_label": "Slettet" if row.deleted_at else roborock_bool_label(row.enabled),
                    "rounds_label": roborock_rounds_label(row.repeat),
                    "fan_label": roborock_fan_label(row.fan_power),
                    "mop_label": roborock_mop_label(row.mop_mode),
                    "water_label": cleaning_water_mode_label(row.water_box_mode, provider),
                }
            )
            schedule_rows.append(item)
        consumable_data = None
        if consumables:
            raw_consumables = consumables.raw if isinstance(consumables.raw, dict) else {}
            if raw_consumables.get("unit") == "percent_remaining":
                def percent_label(value: Any) -> Optional[str]:
                    normalized = int_value(value)
                    return f"{normalized} % igjen" if normalized is not None else None
                consumable_data = {
                    "timestamp": api_local_iso(consumables.timestamp),
                    "main_brush": percent_label(raw_consumables.get("main_brush_percent")),
                    "side_brush": percent_label(raw_consumables.get("side_brush_percent")),
                    "filter": percent_label(raw_consumables.get("filter_percent")),
                    "sensor": percent_label(raw_consumables.get("sensor_percent")),
                    "mop": percent_label(raw_consumables.get("mop_percent")),
                    "detergent": percent_label(raw_consumables.get("detergent_percent")),
                }
            else:
                consumable_data = {
                    "timestamp": api_local_iso(consumables.timestamp),
                    "main_brush": format_seconds_as_hours(consumables.main_brush_work_time),
                    "side_brush": format_seconds_as_hours(consumables.side_brush_work_time),
                    "filter": format_seconds_as_hours(consumables.filter_work_time),
                    "sensor": format_seconds_as_hours(consumables.sensor_dirty_time),
                    "dust_collection": consumables.dust_collection_work_times,
                }
        map_data = None
        if latest_map:
            map_data = {
                **row_to_dict(latest_map, [column for column in ROBOROCK_MAP_COLUMNS if column != "raw"]),
                "imageDataUrl": f"data:image/png;base64,{latest_map.image_base64}" if latest_map.image_base64 else None,
            }
        telemetry_rows = []
        for row in telemetry_samples:
            item = row_to_dict(row, [column for column in ROBOROCK_TELEMETRY_COLUMNS if column != "raw"])
            item.update(
                {
                    "state_label": row.state_name if cleaning_provider(robot.provider) == "dreame" and row.state_name else roborock_state_label(row.state_code),
                    "error_label": roborock_error_label(row.error_code),
                    "charge_label": roborock_telemetry_value_label("is_charging", row.is_charging),
                    "dock_label": roborock_dock_type_label(row.dock_type),
                    "dock_error_label": roborock_dock_error_label(row.dock_error_status),
                    "clear_water_label": roborock_telemetry_value_label(
                        "clear_water_status", row.clear_water_status, row.clear_water_status_name
                    ),
                    "dirty_water_label": roborock_telemetry_value_label(
                        "dirty_water_status", row.dirty_water_status, row.dirty_water_status_name
                    ),
                    "dust_bag_label": roborock_telemetry_value_label(
                        "dust_bag_status", row.dust_bag_status, row.dust_bag_status_name
                    ),
                    "robot_water_label": roborock_telemetry_value_label(
                        "water_shortage_status", row.water_shortage_status, provider=provider
                    ),
                    "water_box_label": roborock_telemetry_value_label(
                        "water_box_status", row.water_box_status
                    ),
                    "mop_attached_label": roborock_telemetry_value_label(
                        "water_box_carriage_status", row.water_box_carriage_status
                    ),
                    "water_filter_label": roborock_telemetry_value_label(
                        "water_box_filter_status", row.water_box_filter_status
                    ),
                    "water_interlock": roborock_water_interlock_from_sample(row) or None,
                    "signal_label": roborock_signal_label(row.rssi),
                }
            )
            telemetry_rows.append(item)
        latest_telemetry = telemetry_samples[0] if telemetry_samples else None
        telemetry_fields = []
        raw_status_fields = []
        if latest_telemetry:
            latest_values = row_to_dict(latest_telemetry, ROBOROCK_TELEMETRY_COLUMNS)
            for category, field_name, label, name_field in ROBOROCK_TELEMETRY_DISPLAY_FIELDS:
                value = latest_values.get(field_name)
                name = latest_values.get(name_field) if name_field else None
                telemetry_fields.append(
                    {
                        "category": category,
                        "field": field_name,
                        "label": label,
                        "value": value,
                        "valueLabel": roborock_telemetry_value_label(field_name, value, name, provider),
                        "supported": value is not None or name is not None,
                    }
                )
            telemetry_raw = latest_telemetry.raw if isinstance(latest_telemetry.raw, dict) else {}
            raw_status = telemetry_raw.get("status_raw") if isinstance(telemetry_raw.get("status_raw"), dict) else {}
            raw_status_fields = [
                {
                    "field": key,
                    "value": json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                    if isinstance(value, (dict, list))
                    else value,
                }
                for key, value in sorted(raw_status.items())
            ]
        event_rows = [
            row_to_dict(row, [column for column in ROBOROCK_TELEMETRY_EVENT_COLUMNS if column != "raw"])
            for row in telemetry_events
        ]
        latest_probe_by_command: Dict[str, RoborockProbeResult] = {}
        for probe in telemetry_probes:
            if probe.command and probe.command not in latest_probe_by_command:
                latest_probe_by_command[probe.command] = probe
        probe_rows = []
        for command, probe in sorted(latest_probe_by_command.items()):
            raw = probe.raw if isinstance(probe.raw, dict) else {}
            probe_rows.append(
                {
                    "command": command,
                    "supported": probe.ok is True,
                    "status": (
                        "Støttet"
                        if probe.ok is True
                        else "Ikke støttet"
                        if any(
                            marker in str(probe.error or "").lower()
                            for marker in ("not recognized", "unknown method", "not supported", "unsupported")
                        )
                        else "Feil"
                    ),
                    "checkedAt": api_local_iso(probe.timestamp),
                    "resultType": probe.result_type,
                    "value": raw.get("value"),
                    "error": probe.error,
                }
            )
        robot_data = row_to_dict(robot, [column for column in ROBOROCK_ROBOT_COLUMNS if column not in {"extra", "capabilities"}])
        robot_data.update(
            {
                "provider": provider,
                "provider_label": cleaning_provider_label(provider),
                "shared_label": roborock_bool_label(robot.shared),
                "cloud_label": roborock_bool_label(robot.cloud_online),
            }
        )
        command_rows = [
            {
                "id": row.id,
                "request_id": row.request_id,
                "action": row.action,
                "requested_at": api_local_iso(utc_naive_to_local_naive(row.requested_at)),
                "finished_at": api_local_iso(utc_naive_to_local_naive(row.finished_at)),
                "requested_by": row.requested_by,
                "status": row.status,
                "message": row.message,
                "before_state": row.before_state,
                "after_state": row.after_state,
                "profile": ((row.result or {}).get("target") or {}).get("profile")
                if isinstance(row.result, dict)
                else None,
            }
            for row in command_runs
        ]
        cleaning_zone_rows = [
            {
                "zoneNumber": zone.zone_number,
                "name": zone.name,
                "segmentId": mapping.segment_id,
                "sourceScheduleId": mapping.source_schedule_id,
                "sourceCron": mapping.source_cron,
                "importedAt": api_local_iso(utc_naive_to_local_naive(mapping.imported_at)),
                "importedBy": mapping.imported_by,
            }
            for mapping, zone in cleaning_zone_pairs
        ]
        return {
            "robot": robot_data,
            "metadata": metadata,
            "network": network,
            "latestStatus": status_rows[0] if status_rows else None,
            "activeCycle": api_roborock_active_cycle(statuses),
            "statuses": status_rows[:60],
            "jobs": job_rows,
            "schedules": schedule_rows,
            "consumables": consumable_data,
            "latestMap": map_data,
            "latestTelemetry": telemetry_rows[0] if telemetry_rows else None,
            "telemetrySamples": telemetry_rows,
            "telemetryEvents": event_rows,
            "telemetryFields": telemetry_fields,
            "rawStatusFields": raw_status_fields,
            "telemetryProbes": probe_rows,
            "canControl": bool(
                (DREAME_CONTROL_TOKEN if provider == "dreame" else ROBOROCK_CONTROL_TOKEN)
                and getattr(request.state, "auth_is_master", False)
            ),
            "canManageCleaningZones": bool(provider == "roborock" and getattr(request.state, "auth_is_master", False)),
            "controlHistory": command_rows,
            "cleaningZones": cleaning_zone_rows,
            "cleaningZoneImport": cleaning_zone_import,
            "cleaningProfiles": [roborock_cleaning_profile_payload(row) for row in cleaning_profiles],
            "cleaningProfileOptions": cleaning_profile_options(robot.model),
            "doorAutomation": door_automation_data,
        }

    @router.put("/api/renhold/robots/{duid}/door-automation")
    async def api_update_roborock_door_automation(
        request: Request,
        duid: str,
        values: RoborockDoorAutomationIn,
    ):
        async_session = dependencies.async_session
        require_master = dependencies.require_master
        roborock_door_automation_payload = dependencies.roborock_door_automation_payload
        forbidden = require_master(request)
        if forbidden:
            return forbidden
        zone_numbers = unique_ints(values.zone_numbers)
        if not zone_numbers:
            raise HTTPException(status_code=400, detail="Velg minst én sone")
        async with async_session() as session:
            robot = (
                await session.execute(select(RoborockRobot).where(RoborockRobot.duid == duid))
            ).scalars().first()
            if not robot:
                raise HTTPException(status_code=404, detail="Ukjent robot")
            automation = (
                await session.execute(
                    select(RoborockDoorAutomation).where(RoborockDoorAutomation.robot_duid == duid)
                )
            ).scalars().first()
            if not automation:
                raise HTTPException(status_code=404, detail="Roboten har ikke inngangsstyrt automatikk")
            profile = await session.get(RoborockCleaningProfile, values.profile_id)
            if not profile or not profile.active or profile.cleaning_type != "vacuum":
                raise HTTPException(status_code=400, detail="Velg en aktiv profil for bare støvsuging")
            mapped_zone_numbers = set(
                (
                    await session.execute(
                        select(CleaningZone.zone_number)
                        .join(
                            RoborockCleaningZoneMapping,
                            RoborockCleaningZoneMapping.zone_id == CleaningZone.id,
                        )
                        .where(
                            RoborockCleaningZoneMapping.robot_duid == duid,
                            CleaningZone.zone_number.in_(zone_numbers),
                        )
                    )
                ).scalars().all()
            )
            if values.enabled and mapped_zone_numbers != set(zone_numbers):
                missing = sorted(set(zone_numbers) - mapped_zone_numbers)
                raise HTTPException(
                    status_code=409,
                    detail=f"Kan ikke aktivere før Sone {', '.join(str(value) for value in missing)} er kartlagt",
                )
            now = local_now_naive()
            automation.enabled = values.enabled
            automation.opening_threshold = values.opening_threshold
            automation.minimum_interval_minutes = values.minimum_interval_minutes
            automation.zone_numbers = zone_numbers
            automation.profile_id = values.profile_id
            automation.last_error = None
            automation.status = "counting" if values.enabled else "disabled"
            automation.updated_at = now
            await session.commit()
            payload, _ = await roborock_door_automation_payload(session, automation, now)
        return {"status": "ok", "message": "Automatikken er lagret. Telleren er beholdt.", "automation": payload}

    @router.post("/api/renhold/robots/{duid}/door-automation/reset-counter")
    async def api_reset_roborock_door_automation_counter(request: Request, duid: str):
        async_session = dependencies.async_session
        require_master = dependencies.require_master
        roborock_door_automation_payload = dependencies.roborock_door_automation_payload
        forbidden = require_master(request)
        if forbidden:
            return forbidden
        async with async_session() as session:
            automation = (
                await session.execute(
                    select(RoborockDoorAutomation).where(RoborockDoorAutomation.robot_duid == duid)
                )
            ).scalars().first()
            if not automation:
                raise HTTPException(status_code=404, detail="Roboten har ikke inngangsstyrt automatikk")
            now = local_now_naive()
            automation.counter_reset_at = now
            automation.last_error = None
            automation.status = "counting" if automation.enabled else "disabled"
            automation.updated_at = now
            await session.commit()
            payload, _ = await roborock_door_automation_payload(session, automation, now)
        return {"status": "ok", "message": "Telleren er nullstilt", "automation": payload}

    @router.post("/api/renhold/robots/{duid}/cleaning-zones/import-test-schedules")
    async def api_import_roborock_cleaning_zones(request: Request, duid: str):
        async_session = dependencies.async_session
        import_roborock_cleaning_zones = dependencies.import_roborock_cleaning_zones
        require_master = dependencies.require_master
        forbidden = require_master(request)
        if forbidden:
            return forbidden
        actor = getattr(request.state, "access_key_name", None) or "master"
        async with async_session() as session:
            robot = (await session.execute(select(RoborockRobot).where(RoborockRobot.duid == duid))).scalars().first()
            if not robot:
                raise HTTPException(status_code=404, detail="Ukjent robot")
            robot_name = robot.name
            schedules = (
                await session.execute(
                    select(RoborockSchedule)
                    .where(RoborockSchedule.robot_duid == duid)
                    .where(RoborockSchedule.deleted_at.is_(None))
                    .order_by(RoborockSchedule.updated_at.desc(), RoborockSchedule.schedule_id)
                )
            ).scalars().all()
            latest_schedule_at = max((row.updated_at for row in schedules if row.updated_at), default=None)
            current_schedules = [row for row in schedules if row.updated_at == latest_schedule_at] if latest_schedule_at else []
            try:
                result = await import_roborock_cleaning_zones(session, duid, current_schedules, actor)
            except RoborockZoneScheduleError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            if not result["imported"]:
                raise HTTPException(
                    status_code=404,
                    detail="Fant ingen deaktiverte testplaner mellom 12:01 og 12:59 i siste Roborock-synkronisering",
                )
            await session.commit()
        return {
            "status": "ok",
            "message": f"Leste inn {result['imported']} soner for {robot_name}",
            "scheduleUpdatedAt": api_local_iso(latest_schedule_at),
            **result,
        }

    @router.post("/api/renhold/cleaning-profiles")
    async def api_create_roborock_cleaning_profile(request: Request, values: RoborockCleaningProfileIn):
        apply_roborock_cleaning_profile_values = dependencies.apply_roborock_cleaning_profile_values
        async_session = dependencies.async_session
        require_master = dependencies.require_master
        roborock_cleaning_profile_payload = dependencies.roborock_cleaning_profile_payload
        forbidden = require_master(request)
        if forbidden:
            return forbidden
        profile = RoborockCleaningProfile(
            slug=f"custom-{secrets.token_hex(8)}",
            builtin=False,
            created_at=datetime.utcnow(),
        )
        apply_roborock_cleaning_profile_values(profile, values)
        async with async_session() as session:
            session.add(profile)
            await session.commit()
            await session.refresh(profile)
            return {"status": "ok", "profile": roborock_cleaning_profile_payload(profile)}

    @router.put("/api/renhold/cleaning-profiles/{profile_id}")
    async def api_update_roborock_cleaning_profile(
        request: Request,
        profile_id: int,
        values: RoborockCleaningProfileIn,
    ):
        apply_roborock_cleaning_profile_values = dependencies.apply_roborock_cleaning_profile_values
        async_session = dependencies.async_session
        require_master = dependencies.require_master
        roborock_cleaning_profile_payload = dependencies.roborock_cleaning_profile_payload
        forbidden = require_master(request)
        if forbidden:
            return forbidden
        async with async_session() as session:
            profile = await session.get(RoborockCleaningProfile, profile_id)
            if not profile:
                raise HTTPException(status_code=404, detail="Ukjent rengjøringsprofil")
            apply_roborock_cleaning_profile_values(profile, values)
            await session.commit()
            await session.refresh(profile)
            return {"status": "ok", "profile": roborock_cleaning_profile_payload(profile)}

    @router.delete("/api/renhold/cleaning-profiles/{profile_id}")
    async def api_delete_roborock_cleaning_profile(request: Request, profile_id: int):
        async_session = dependencies.async_session
        require_master = dependencies.require_master
        forbidden = require_master(request)
        if forbidden:
            return forbidden
        async with async_session() as session:
            profile = await session.get(RoborockCleaningProfile, profile_id)
            if not profile:
                raise HTTPException(status_code=404, detail="Ukjent rengjøringsprofil")
            if profile.builtin:
                raise HTTPException(status_code=409, detail="Standardprofiler kan redigeres, men ikke slettes")
            await session.delete(profile)
            await session.commit()
        return {"status": "ok", "message": "Rengjøringsprofilen er slettet"}

    @router.post("/api/renhold/robots/{duid}/control")
    async def api_cleaning_robot_control(request: Request, duid: str, values: RoborockControlIn):
        DREAME_CONTROL_TOKEN = dependencies.DREAME_CONTROL_TOKEN
        ROBOROCK_CONTROL_TOKEN = dependencies.ROBOROCK_CONTROL_TOKEN
        async_session = dependencies.async_session
        post_dreame_control = dependencies.post_dreame_control
        post_roborock_control = dependencies.post_roborock_control
        require_master = dependencies.require_master
        roborock_cleaning_profile_payload = dependencies.roborock_cleaning_profile_payload
        forbidden = require_master(request)
        if forbidden:
            return forbidden
        allowed_actions = {
            "dry_run",
            "start",
            "pause",
            "resume",
            "stop",
            "dock",
            "test_start_stop",
            "clean_zone",
            "set_mop_wash",
        }
        action = values.action.strip().lower()
        if action not in allowed_actions:
            raise HTTPException(status_code=400, detail="Ukjent robotkommando")
        if action == "clean_zone" and (values.zone_number is None or values.profile_id is None):
            raise HTTPException(status_code=400, detail="Sone og rengjøringsprofil må velges")
        if action == "set_mop_wash":
            if values.wash_mode not in {0, 1, 2, 8}:
                raise HTTPException(status_code=400, detail="Ugyldig styrke for moppevask")
            if values.wash_interval_minutes not in {10, 15, 20, 25}:
                raise HTTPException(status_code=400, detail="Ugyldig intervall for moppevask")

        actor = getattr(request.state, "access_key_name", None) or "master"
        request_id = f"fibaro10-{secrets.token_hex(12)}"
        zone_name: Optional[str] = None
        segment_id: Optional[int] = None
        profile_payload: Optional[Dict[str, Any]] = None
        async with async_session() as session:
            robot = (await session.execute(select(RoborockRobot).where(RoborockRobot.duid == duid))).scalars().first()
            if not robot:
                raise HTTPException(status_code=404, detail="Ukjent robot")
            provider = cleaning_provider(robot.provider)
            external_id = robot.external_id or cleaning_robot_external_id(provider, robot.duid)
            if provider == "dreame":
                if not DREAME_CONTROL_TOKEN:
                    raise HTTPException(status_code=503, detail="Dreame-styring er ikke konfigurert")
                if action not in {"start", "pause", "resume", "stop", "dock"}:
                    raise HTTPException(status_code=400, detail="Denne kommandoen er ikke tilgjengelig for Dreame ennå")
            elif not ROBOROCK_CONTROL_TOKEN:
                raise HTTPException(status_code=503, detail="Roborock-styring er ikke konfigurert")
            robot_name = robot.name
            if action == "clean_zone":
                zone_pair = (
                    await session.execute(
                        select(RoborockCleaningZoneMapping, CleaningZone)
                        .join(CleaningZone, CleaningZone.id == RoborockCleaningZoneMapping.zone_id)
                        .where(
                            RoborockCleaningZoneMapping.robot_duid == duid,
                            CleaningZone.zone_number == values.zone_number,
                        )
                    )
                ).first()
                if not zone_pair:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Sone {values.zone_number} er ikke koblet til {robot_name}",
                    )
                mapping, zone = zone_pair
                zone_name = zone.name
                try:
                    segment_id = int(mapping.segment_id)
                except (TypeError, ValueError) as exc:
                    raise HTTPException(
                        status_code=409,
                        detail=f"{zone_name} har et ugyldig robotsegment",
                    ) from exc
                profile = await session.get(RoborockCleaningProfile, values.profile_id)
                if not profile or not profile.active:
                    raise HTTPException(status_code=404, detail="Rengjøringsprofilen finnes ikke eller er deaktivert")
                profile_payload = roborock_cleaning_profile_payload(profile)
            command_run = RoborockCommandRun(
                request_id=request_id,
                robot_duid=duid,
                action=action,
                requested_at=datetime.utcnow(),
                requested_by=actor,
                status="running",
                message=f"Kommando sendt til {cleaning_provider_label(provider)}-loggeren",
            )
            session.add(command_run)
            await session.commit()
            command_id = command_run.id

        try:
            control_sender = post_dreame_control if provider == "dreame" else post_roborock_control
            control_identity = external_id if provider == "dreame" else duid
            result = await asyncio.to_thread(
                control_sender,
                control_identity,
                {
                    "action": action,
                    "request_id": request_id,
                    "actor": actor,
                    "confirmation": f"CONFIRM:{duid}:{action}",
                    "test_duration_seconds": values.test_duration_seconds,
                    "zone_number": values.zone_number,
                    "segment_id": segment_id,
                    "wash_mode": values.wash_mode,
                    "wash_interval_minutes": values.wash_interval_minutes,
                    "profile": {
                        "id": profile_payload["id"],
                        "name": profile_payload["name"],
                        "cleaning_type": profile_payload["cleaningType"],
                        "fan_power": profile_payload["fanPower"],
                        "water_box_mode": profile_payload["waterBoxMode"],
                        "mop_mode": profile_payload["mopMode"],
                        "repeat": profile_payload["repeat"],
                        "summary": profile_payload["summary"],
                    }
                    if profile_payload
                    else None,
                },
            )
            command_status = str(result.get("status") or "ok")
            message = (
                "Kontrolltest fullført"
                if action == "test_start_stop"
                else "Moppevaskinnstillingene er lagret og kontrollert mot roboten"
                if action == "set_mop_wash"
                else f"{profile_payload['name']} startet i {zone_name} på {robot_name}"
                if action == "clean_zone"
                else "Robotkommando utført"
            )
            before_state = result.get("before")
            after_state = result.get("after")
        except Exception as exc:
            result = {"error": str(exc)}
            command_status = "error"
            message = str(exc)
            before_state = None
            after_state = None

        async with async_session() as session:
            command_run = await session.get(RoborockCommandRun, command_id)
            if command_run:
                command_run.finished_at = datetime.utcnow()
                command_run.status = command_status
                command_run.message = message
                command_run.before_state = before_state
                command_run.after_state = after_state
                command_run.result = result
                if action == "set_mop_wash" and command_status == "ok":
                    control_result = result.get("result") if isinstance(result, dict) else None
                    probes = control_result.get("probes") if isinstance(control_result, dict) else None
                    if isinstance(probes, dict):
                        probe_timestamp = local_now_naive()
                        for command, value in probes.items():
                            session.add(
                                RoborockProbeResult(
                                    robot_duid=duid,
                                    timestamp=probe_timestamp,
                                    source="local-telemetry",
                                    command=command,
                                    ok=True,
                                    result_type="dict",
                                    raw={"value": value},
                                )
                            )
                await session.commit()

        if command_status != "ok":
            raise HTTPException(status_code=502, detail=message)
        return {
            "status": command_status,
            "message": message,
            "requestId": request_id,
            "before": before_state,
            "after": after_state,
            "zoneNumber": values.zone_number if action == "clean_zone" else None,
            "segmentId": segment_id,
            "profile": profile_payload,
            "settings": result.get("result", {}).get("settings")
            if action == "set_mop_wash" and isinstance(result.get("result"), dict)
            else None,
        }

    @router.get("/renhold/robot/{duid}", response_class=HTMLResponse)
    async def cleaning_robot_detail(request: Request, duid: str):
        async_session = dependencies.async_session
        templates = dependencies.templates
        async with async_session() as session:
            robot = (await session.execute(select(RoborockRobot).where(RoborockRobot.duid == duid))).scalars().first()
            if not robot:
                return JSONResponse({"detail": "Ukjent robot"}, status_code=404)
            statuses = (
                await session.execute(
                    select(RoborockStatusSample)
                    .where(RoborockStatusSample.robot_duid == duid)
                    .order_by(RoborockStatusSample.timestamp.desc())
                    .limit(100)
                )
            ).scalars().all()
            jobs = (
                await session.execute(
                    select(RoborockCleanJob)
                    .where(RoborockCleanJob.robot_duid == duid)
                    .order_by(RoborockCleanJob.begin_at.desc())
                    .limit(50)
                )
            ).scalars().all()
            schedules = (
                await session.execute(
                    select(RoborockSchedule)
                    .where(RoborockSchedule.robot_duid == duid)
                    .where(RoborockSchedule.deleted_at.is_(None))
                    .order_by(RoborockSchedule.cron)
                )
            ).scalars().all()
            consumables = (
                await session.execute(
                    select(RoborockConsumableSnapshot)
                    .where(RoborockConsumableSnapshot.robot_duid == duid)
                    .order_by(RoborockConsumableSnapshot.timestamp.desc())
                    .limit(1)
                )
            ).scalars().first()
            latest_map = (
                await session.execute(
                    select(RoborockMapSnapshot)
                    .where(RoborockMapSnapshot.robot_duid == duid)
                    .order_by(RoborockMapSnapshot.timestamp.desc())
                    .limit(1)
                )
            ).scalars().first()
        return templates.TemplateResponse(
            request,
            "cleaning_robot.html",
            {
                "robot": robot,
                "latest_status": statuses[0] if statuses else None,
                "statuses": statuses,
                "jobs": jobs,
                "schedules": schedules,
                "consumables": consumables,
                "latest_map": latest_map,
            },
        )

    @router.get("/renhold/json")
    async def cleaning_json(limit: int = 100):
        async_session = dependencies.async_session
        row_to_dict = dependencies.row_to_dict
        limit = max(1, min(limit, 1000))
        async with async_session() as session:
            robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
            robots.sort(key=cleaning_robot_sort_key)
            jobs = (await session.execute(select(RoborockCleanJob).order_by(RoborockCleanJob.begin_at.desc()).limit(limit))).scalars().all()
            statuses = (await session.execute(select(RoborockStatusSample).order_by(RoborockStatusSample.timestamp.desc()).limit(limit))).scalars().all()
        job_rows = []
        for row in jobs:
            item = row_to_dict(row, ROBOROCK_JOB_COLUMNS)
            item["begin_at"] = api_local_iso(utc_naive_to_local_naive(row.begin_at))
            item["end_at"] = api_local_iso(utc_naive_to_local_naive(row.end_at))
            job_rows.append(item)
        return {
            "robots": [row_to_dict(row, ROBOROCK_ROBOT_COLUMNS) for row in robots],
            "jobs": job_rows,
            "statuses": [row_to_dict(row, ROBOROCK_STATUS_COLUMNS) for row in statuses],
        }

    @router.get("/classic/renhold/oversikt", response_class=HTMLResponse)
    async def classic_cleaning_overview(request: Request):
        return await cleaning_overview(request)

    @router.get("/classic/renhold/robot/{duid}", response_class=HTMLResponse)
    async def classic_cleaning_robot_detail(request: Request, duid: str):
        return await cleaning_robot_detail(request, duid)

    @router.get("/classic/renhold/json")
    async def classic_cleaning_json(limit: int = 100):
        return await cleaning_json(limit)

    return RouterBundle(router, {
        "api_cleaning_night_report": api_cleaning_night_report,
        "api_cleaning_refill_log": api_cleaning_refill_log,
        "api_cleaning_robot_control": api_cleaning_robot_control,
        "api_cleaning_robot_detail": api_cleaning_robot_detail,
        "api_cleaning_water_report": api_cleaning_water_report,
        "api_cleaning_weekly_jobs": api_cleaning_weekly_jobs,
        "api_create_roborock_cleaning_profile": api_create_roborock_cleaning_profile,
        "api_delete_roborock_cleaning_profile": api_delete_roborock_cleaning_profile,
        "api_import_roborock_cleaning_zones": api_import_roborock_cleaning_zones,
        "api_reset_roborock_door_automation_counter": api_reset_roborock_door_automation_counter,
        "api_update_roborock_cleaning_profile": api_update_roborock_cleaning_profile,
        "api_update_roborock_door_automation": api_update_roborock_door_automation,
        "classic_cleaning_json": classic_cleaning_json,
        "classic_cleaning_overview": classic_cleaning_overview,
        "classic_cleaning_robot_detail": classic_cleaning_robot_detail,
        "cleaning_json": cleaning_json,
        "cleaning_overview": cleaning_overview,
        "cleaning_robot_detail": cleaning_robot_detail,
    }, dependencies)
