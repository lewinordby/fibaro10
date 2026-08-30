"""Cleaning module response assembly, independent of HTTP registration."""

from cleaning_robot_domain import (
    CLEANING_ROBOT_STATUS_STALE_AFTER_MINUTES,
    cleaning_provider,
    cleaning_provider_label,
    cleaning_robot_is_active,
    cleaning_robot_sort_key,
    expected_dreame_summary,
)
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fibaro_core.models import (
    ControlConfig,
    RoborockCleanJob,
    RoborockConsumableSnapshot,
    RoborockRobot,
    RoborockSchedule,
    RoborockStatusSample,
    RoborockTelemetrySample,
)
from fibaro_core.services.presentation import api_card, api_table
from fibaro_core.services.summaries.periods import add_months
from roborock_domain import (
    format_seconds_as_hours,
    roborock_active_cycle_summary,
    roborock_dock_error_label,
    roborock_error_label,
    roborock_job_status,
    roborock_next_schedule_score,
    roborock_next_schedule_text,
    roborock_operational_readiness,
    roborock_rounds_label,
    roborock_schedule_text,
    roborock_signal_label,
    roborock_telemetry_value_label,
)
from roborock_door_automation import opening_window
from roborock_reports import build_schedule_check
from sqlalchemy import func, select
from time_formatting import (
    LOCAL_TZ,
    api_local_iso,
    local_naive_to_utc_naive,
    local_now_naive,
    normalize_local_naive,
    utc_naive_to_local_naive,
)
from typing import Any, Dict, Optional
from urllib.parse import quote
from v2_navigation import v2_module_title
from value_parsing import int_or_zero, int_value


@dataclass
class Dependencies:
    DREAME_EXPECTED_ROBOT_NAME: Any
    api_pick: Any
    api_roborock_active_cycle: Any
    api_tool_row: Any
    config_defaults: Any
    latest_cleaning_robot_sample: Any
    merge_config_values: Any
    roborock_water_interlock_from_sample: Any


async def render(session, request, module, view, q, day, now_dt, dependencies):
    DREAME_EXPECTED_ROBOT_NAME = dependencies.DREAME_EXPECTED_ROBOT_NAME
    api_pick = dependencies.api_pick
    api_roborock_active_cycle = dependencies.api_roborock_active_cycle
    api_tool_row = dependencies.api_tool_row
    config_defaults = dependencies.config_defaults
    latest_cleaning_robot_sample = dependencies.latest_cleaning_robot_sample
    merge_config_values = dependencies.merge_config_values
    roborock_water_interlock_from_sample = dependencies.roborock_water_interlock_from_sample
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
    robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
    robots.sort(key=cleaning_robot_sort_key)
    robot_duids = [robot.duid for robot in robots]
    today_local = datetime.now(LOCAL_TZ).date()
    yesterday_local = today_local - timedelta(days=1)
    tomorrow_local = today_local + timedelta(days=1)
    jobs_from = local_naive_to_utc_naive(datetime.combine(yesterday_local, time.min))
    jobs_to = local_naive_to_utc_naive(datetime.combine(tomorrow_local, time.min))
    jobs = (
        await session.execute(
            select(RoborockCleanJob)
            .where(RoborockCleanJob.robot_duid.in_(robot_duids or [""]))
            .where(RoborockCleanJob.begin_at >= jobs_from)
            .where(RoborockCleanJob.begin_at < jobs_to)
            .order_by(RoborockCleanJob.begin_at.desc(), RoborockCleanJob.id.desc())
        )
    ).scalars().all()

    latest_status_subq = (
        select(
            RoborockStatusSample.robot_duid.label("robot_duid"),
            func.max(RoborockStatusSample.id).label("latest_id"),
        )
        .where(RoborockStatusSample.robot_duid.in_(robot_duids or [""]))
        .group_by(RoborockStatusSample.robot_duid)
        .subquery()
    )
    statuses = (
        await session.execute(
            select(RoborockStatusSample)
            .join(latest_status_subq, RoborockStatusSample.id == latest_status_subq.c.latest_id)
            .order_by(RoborockStatusSample.timestamp.desc())
        )
    ).scalars().all()

    latest_telemetry_subq = (
        select(
            RoborockTelemetrySample.robot_duid.label("robot_duid"),
            func.max(RoborockTelemetrySample.id).label("latest_id"),
        )
        .where(RoborockTelemetrySample.robot_duid.in_(robot_duids or [""]))
        .group_by(RoborockTelemetrySample.robot_duid)
        .subquery()
    )
    telemetry_samples = (
        await session.execute(
            select(RoborockTelemetrySample)
            .join(latest_telemetry_subq, RoborockTelemetrySample.id == latest_telemetry_subq.c.latest_id)
            .order_by(RoborockTelemetrySample.timestamp.desc())
        )
    ).scalars().all()

    latest_consumable_subq = (
        select(
            RoborockConsumableSnapshot.robot_duid.label("robot_duid"),
            func.max(RoborockConsumableSnapshot.id).label("latest_id"),
        )
        .where(RoborockConsumableSnapshot.robot_duid.in_(robot_duids or [""]))
        .group_by(RoborockConsumableSnapshot.robot_duid)
        .subquery()
    )
    consumables = (
        await session.execute(
            select(RoborockConsumableSnapshot)
            .join(latest_consumable_subq, RoborockConsumableSnapshot.id == latest_consumable_subq.c.latest_id)
            .order_by(RoborockConsumableSnapshot.timestamp.desc())
        )
    ).scalars().all()
    schedules = (
        await session.execute(
            select(RoborockSchedule)
            .where(RoborockSchedule.enabled == True)
            .where(RoborockSchedule.deleted_at.is_(None))
            .order_by(RoborockSchedule.robot_duid, RoborockSchedule.schedule_id)
        )
    ).scalars().all()
    online = sum(1 for row in robots if row.cloud_online is not False)
    latest_status_by_robot: Dict[str, RoborockStatusSample] = {}
    for status in statuses:
        if status.robot_duid not in latest_status_by_robot:
            latest_status_by_robot[status.robot_duid] = status
    latest_telemetry_by_robot: Dict[str, RoborockTelemetrySample] = {}
    for telemetry_sample in telemetry_samples:
        latest_telemetry_by_robot.setdefault(telemetry_sample.robot_duid, telemetry_sample)
    active_robot_duids = [
        robot.duid
        for robot in robots
        if (
            latest_telemetry_by_robot.get(robot.duid)
            and latest_telemetry_by_robot[robot.duid].in_cleaning is True
        )
        or (
            (
                latest_telemetry_by_robot.get(robot.duid) is None
                or latest_telemetry_by_robot[robot.duid].in_cleaning is None
            )
            and latest_status_by_robot.get(robot.duid)
            and latest_status_by_robot[robot.duid].in_cleaning is True
        )
    ]
    status_history = statuses
    if active_robot_duids:
        status_history = (
            await session.execute(
                select(RoborockStatusSample)
                .where(RoborockStatusSample.robot_duid.in_(active_robot_duids))
                .where(RoborockStatusSample.timestamp >= local_now_naive() - timedelta(hours=36))
                .order_by(RoborockStatusSample.timestamp.desc())
            )
        ).scalars().all()
    statuses_by_robot: Dict[str, list[RoborockStatusSample]] = defaultdict(list)
    for status in status_history:
        statuses_by_robot[status.robot_duid].append(status)
    latest_consumables_by_robot: Dict[str, RoborockConsumableSnapshot] = {}
    for consumable in consumables:
        latest_consumables_by_robot.setdefault(consumable.robot_duid, consumable)
    schedules_by_robot: Dict[str, list[RoborockSchedule]] = defaultdict(list)
    for schedule in schedules:
        schedules_by_robot[schedule.robot_duid].append(schedule)
    latest_job_by_robot_day: Dict[tuple[str, date], RoborockCleanJob] = {}
    jobs_by_robot_day: Dict[tuple[str, date], list[RoborockCleanJob]] = defaultdict(list)
    for job in jobs:
        local_begin = utc_naive_to_local_naive(job.begin_at)
        if not local_begin or local_begin.date() not in {today_local, yesterday_local}:
            continue
        jobs_by_robot_day[(job.robot_duid, local_begin.date())].append(job)
        latest_job_by_robot_day.setdefault((job.robot_duid, local_begin.date()), job)

    def overview_job(job: Optional[RoborockCleanJob]) -> Optional[Dict[str, Any]]:
        if not job:
            return None
        status_key, status_label = roborock_job_status(job.complete, job.error_code, job.end_at)
        return {
            "begin_at": api_local_iso(utc_naive_to_local_naive(job.begin_at)),
            "end_at": api_local_iso(utc_naive_to_local_naive(job.end_at)),
            "duration_minutes": job.duration_minutes,
            "cleaned_area_m2": job.cleaned_area_m2 if job.cleaned_area_m2 is not None else job.area_m2,
            "status": status_key,
            "status_label": status_label,
            "error_label": roborock_error_label(job.error_code) if status_key == "error" else None,
        }

    def overview_consumables(robot_duid: str) -> Optional[Dict[str, Any]]:
        consumable = latest_consumables_by_robot.get(robot_duid)
        if not consumable:
            return None
        raw = consumable.raw if isinstance(consumable.raw, dict) else {}
        if raw.get("unit") == "percent_remaining":
            def percent_label(value: Any) -> Optional[str]:
                normalized = int_value(value)
                return f"{normalized} % igjen" if normalized is not None else None
            return {
                "main_brush": percent_label(raw.get("main_brush_percent")),
                "side_brush": percent_label(raw.get("side_brush_percent")),
                "filter": percent_label(raw.get("filter_percent")),
                "sensor": percent_label(raw.get("sensor_percent")),
                "mop": percent_label(raw.get("mop_percent")),
                "detergent": percent_label(raw.get("detergent_percent")),
                "captured_at": api_local_iso(consumable.timestamp),
            }
        return {
            "main_brush": format_seconds_as_hours(consumable.main_brush_work_time),
            "side_brush": format_seconds_as_hours(consumable.side_brush_work_time),
            "filter": format_seconds_as_hours(consumable.filter_work_time),
            "sensor": format_seconds_as_hours(consumable.sensor_dirty_time),
            "captured_at": api_local_iso(consumable.timestamp),
        }

    def overview_day(
        robot_duid: str,
        selected_day: date,
        active_cycle: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        day_jobs = jobs_by_robot_day.get((robot_duid, selected_day), [])
        statuses_for_day = [roborock_job_status(row.complete, row.error_code, row.end_at)[0] for row in day_jobs]
        include_active = bool(
            active_cycle
            and active_cycle.get("started_at")
            and active_cycle["started_at"].date() == selected_day
            and "running" not in statuses_for_day
        )
        return {
            "job_count": len(day_jobs) + int(include_active),
            "completed_count": statuses_for_day.count("complete"),
            "running_count": statuses_for_day.count("running") + int(include_active),
            "error_count": statuses_for_day.count("error"),
            "duration_minutes": round(
                sum(float(row.duration_minutes or 0) for row in day_jobs)
                + (float(active_cycle.get("active_minutes") or 0) if include_active and active_cycle else 0),
                1,
            ),
            "cleaned_area_m2": round(
                sum(float(row.cleaned_area_m2 if row.cleaned_area_m2 is not None else row.area_m2 or 0) for row in day_jobs)
                + (float(active_cycle.get("cleaned_area_m2") or 0) if include_active and active_cycle else 0),
                1,
            ),
        }

    def overview_readiness(
        robot: RoborockRobot,
        status: Optional[RoborockStatusSample],
        telemetry: Optional[RoborockTelemetrySample],
        active_cycle: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        source = latest_cleaning_robot_sample(status, telemetry)
        error_code = source.error_code if source else None
        dock_error = roborock_dock_error_label(telemetry.dock_error_status) if telemetry else "Ikke støttet"
        clear_water = roborock_telemetry_value_label(
            "clear_water_status", telemetry.clear_water_status, telemetry.clear_water_status_name
        ) if telemetry else "Ikke støttet"
        dirty_water = roborock_telemetry_value_label(
            "dirty_water_status", telemetry.dirty_water_status, telemetry.dirty_water_status_name
        ) if telemetry else "Ikke støttet"
        dust_bag = roborock_telemetry_value_label(
            "dust_bag_status", telemetry.dust_bag_status, telemetry.dust_bag_status_name
        ) if telemetry else "Ikke støttet"
        robot_water = roborock_telemetry_value_label(
            "water_shortage_status",
            telemetry.water_shortage_status,
            provider=robot.provider,
        ) if telemetry else "Ikke støttet"
        water_box = roborock_telemetry_value_label(
            "water_box_status", telemetry.water_box_status
        ) if telemetry else "Ikke støttet"
        mop_attached = roborock_telemetry_value_label(
            "water_box_carriage_status", telemetry.water_box_carriage_status
        ) if telemetry else "Ikke støttet"
        water_filter = roborock_telemetry_value_label(
            "water_box_filter_status", telemetry.water_box_filter_status
        ) if telemetry else "Ikke støttet"
        water_interlock = roborock_water_interlock_from_sample(telemetry) if telemetry else {}
        active = cleaning_robot_is_active(
            source.in_cleaning if source else None,
            source.state_code if source else None,
            robot.provider,
        )
        telemetry_at = normalize_local_naive(telemetry.timestamp) if telemetry and telemetry.timestamp else None
        telemetry_age_minutes = (
            max(0, round((local_now_naive() - telemetry_at).total_seconds() / 60))
            if telemetry_at
            else None
        )
        readiness = roborock_operational_readiness(
            cloud_online=robot.cloud_online,
            last_error=robot.last_error,
            error_code=error_code,
            dock_error=dock_error,
            clear_water=clear_water,
            dirty_water=dirty_water,
            dust_bag=dust_bag,
            active=active,
            data_age_minutes=telemetry_age_minutes,
            robot_water=robot_water,
            robot_water_title="Vannvarsel" if cleaning_provider(robot.provider) == "dreame" else "Vann i robot",
            stale_after_minutes=CLEANING_ROBOT_STATUS_STALE_AFTER_MINUTES,
        )
        if readiness["status"] == "active" and active_cycle and active_cycle.get("phase") == "charging_pause":
            readiness["label"] = "Pågår – lader"
        if water_interlock.get("status") == "error":
            readiness["status"] = "attention"
            readiness["label"] = "Krever tilsyn"
            readiness["issues"] = list(
                dict.fromkeys([*readiness["issues"], "Automatisk vannsperre har feil"])
            )
        return {
            **readiness,
            "telemetry_at": api_local_iso(telemetry.timestamp) if telemetry else None,
            "data_age_minutes": telemetry_age_minutes,
            "charge_label": roborock_telemetry_value_label("is_charging", telemetry.is_charging) if telemetry else "Ikke støttet",
            "clear_water_label": clear_water,
            "dirty_water_label": dirty_water,
            "dust_bag_label": dust_bag,
            "dock_error_label": dock_error,
            "robot_water_label": robot_water,
            "water_box_label": water_box,
            "mop_attached_label": mop_attached,
            "water_filter_label": water_filter,
            "water_interlock": water_interlock or None,
            "signal_label": roborock_signal_label(telemetry.rssi) if telemetry else "-",
        }

    def overview_schedules(
        robot_duid: str,
        water_interlock: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        configured = schedules_by_robot.get(robot_duid, [])
        paused_rows = (
            water_interlock.get("paused_schedules")
            if isinstance(water_interlock, dict)
            and isinstance(water_interlock.get("paused_schedules"), list)
            else []
        )
        paused_ids = {
            str(row.get("schedule_id"))
            for row in paused_rows
            if isinstance(row, dict) and row.get("schedule_id") is not None
        }
        active = [
            schedule
            for schedule in configured
            if str(schedule.schedule_id) not in paused_ids
        ]
        next_schedule = min(active, key=roborock_next_schedule_score) if active else None
        return {
            "active_count": len(active),
            "configured_count": len(configured),
            "paused_count": len(paused_rows),
            "paused_schedules": paused_rows,
            "next_label": roborock_next_schedule_text(next_schedule) if next_schedule else None,
            "schedule_label": roborock_schedule_text(next_schedule) if next_schedule else None,
            "rounds_label": roborock_rounds_label(next_schedule.repeat) if next_schedule else None,
        }
    robot_summaries = []
    for robot in robots:
        status = latest_status_by_robot.get(robot.duid)
        telemetry = latest_telemetry_by_robot.get(robot.duid)
        source = latest_cleaning_robot_sample(status, telemetry)
        cycle_history: list[Any] = list(statuses_by_robot.get(robot.duid, []))
        if telemetry and telemetry.in_cleaning is not None:
            cycle_history.append(telemetry)
        active_cycle = roborock_active_cycle_summary(cycle_history)
        overview_readiness_data = overview_readiness(robot, status, telemetry, active_cycle)
        water_interlock = overview_readiness_data.get("water_interlock") or {}
        overview_schedules_data = overview_schedules(robot.duid, water_interlock)
        paused_schedules = (
            water_interlock.get("paused_schedules")
            if isinstance(water_interlock.get("paused_schedules"), list)
            else []
        )
        overview_schedules_data["paused_count"] = max(
            int_or_zero(water_interlock.get("paused_count")),
            len(paused_schedules),
        )
        robot_summaries.append(
            {
                "duid": robot.duid,
                "provider": cleaning_provider(robot.provider),
                "provider_label": cleaning_provider_label(robot.provider),
                "external_id": robot.external_id,
                "integration_status": robot.integration_status or "active",
                "name": robot.name,
                "model": robot.model,
                "cloud_online": robot.cloud_online,
                "local_ip": robot.local_ip,
                "last_seen_at": robot.last_seen_at,
                "last_error": robot.last_error,
                "state_name": active_cycle.get("phase_label") if active_cycle else source.state_name if source else None,
                "battery": source.battery if source else None,
                "error_code": source.error_code if source else None,
                "status_at": api_local_iso(source.timestamp if source else None),
                "latest_job_today": overview_job(latest_job_by_robot_day.get((robot.duid, today_local))),
                "latest_job_yesterday": overview_job(latest_job_by_robot_day.get((robot.duid, yesterday_local))),
                "today": overview_day(robot.duid, today_local, active_cycle),
                "yesterday": overview_day(robot.duid, yesterday_local, active_cycle),
                "active_cycle": api_roborock_active_cycle(cycle_history),
                "readiness": overview_readiness_data,
                "consumables": overview_consumables(robot.duid),
                "schedules": overview_schedules_data,
            }
        )
    if not any(cleaning_provider(robot.provider) == "dreame" for robot in robots):
        robot_summaries.append(expected_dreame_summary(DREAME_EXPECTED_ROBOT_NAME))
    timeline_now = local_now_naive()
    ventilation_config = (
        await session.execute(select(ControlConfig).where(ControlConfig.key == "ventilation"))
    ).scalars().first()
    ventilation_values = merge_config_values(
        "ventilation",
        ventilation_config.values if ventilation_config else config_defaults("ventilation"),
    )
    timeline_open_at, timeline_close_at = opening_window(
        today_local,
        ventilation_values.get("open_from"),
        ventilation_values.get("close_at"),
    )
    timeline_window = {
        "start": timeline_open_at,
        "end": timeline_close_at,
        "ready_by": timeline_close_at,
    }
    timeline_robot = next(
        (robot for robot in robots if (robot.name or "").strip().casefold() == "1.etg b"),
        None,
    )
    timeline_robots = []
    for robot in [timeline_robot] if timeline_robot else []:
        day_jobs = sorted(
            (
                job
                for job in jobs_by_robot_day.get((robot.duid, today_local), [])
                if (
                    (local_begin := utc_naive_to_local_naive(job.begin_at)) is not None
                    and local_begin < timeline_window["end"]
                    and (
                        utc_naive_to_local_naive(job.end_at)
                        or timeline_now
                    ) >= timeline_window["start"]
                )
            ),
            key=lambda row: row.begin_at or datetime.min,
        )
        schedule_check = build_schedule_check(
            schedules_by_robot.get(robot.duid, []),
            day_jobs,
            [],
            timeline_window,
            timeline_now,
        )
        plan_by_record = {
            row["actualRecordId"]: row
            for row in schedule_check["jobs"]
            if row.get("actualRecordId")
        }
        actual_jobs = []
        for job in day_jobs:
            record_id = str(job.record_id or job.id or "")
            plan = plan_by_record.get(record_id)
            status_key, status_label = roborock_job_status(job.complete, job.error_code, job.end_at)
            actual_jobs.append(
                {
                    "recordId": record_id,
                    "startedAt": api_local_iso(utc_naive_to_local_naive(job.begin_at)),
                    "endedAt": api_local_iso(utc_naive_to_local_naive(job.end_at)),
                    "cleaningType": plan["cleaningType"] if plan else "cleaning",
                    "cleaningTypeLabel": plan["cleaningTypeLabel"] if plan else "Rengjøring",
                    "status": status_key,
                    "statusLabel": status_label,
                    "planned": bool(plan),
                    "areaM2": round(float(job.cleaned_area_m2 if job.cleaned_area_m2 is not None else job.area_m2 or 0), 1),
                }
            )
        timeline_robots.append(
            {
                "duid": robot.duid,
                "name": robot.name,
                "planned": schedule_check["jobs"],
                "jobs": actual_jobs,
            }
        )
    timeline_summary = {
        "planned": sum(len(row["planned"]) for row in timeline_robots),
        "plannedCompleted": sum(
            planned["status"] in {"completed", "delayed"}
            for row in timeline_robots
            for planned in row["planned"]
        ),
        "missing": sum(
            planned["status"] == "missing"
            for row in timeline_robots
            for planned in row["planned"]
        ),
        "pending": sum(
            planned["status"] == "pending"
            for row in timeline_robots
            for planned in row["planned"]
        ),
        "actual": sum(len(row["jobs"]) for row in timeline_robots),
    }
    overview_updates = [
        row["readiness"]["telemetry_at"] or row["status_at"]
        for row in robot_summaries
        if row["readiness"]["telemetry_at"] or row["status_at"]
    ]
    overview_summary = {
        "robot_count": len(robot_summaries),
        "connected_count": sum(1 for row in robot_summaries if row.get("integration_status") == "active"),
        "pending_count": sum(1 for row in robot_summaries if row.get("integration_status") == "pending"),
        "ready_count": sum(1 for row in robot_summaries if row["readiness"]["status"] == "ready"),
        "active_count": sum(1 for row in robot_summaries if row["readiness"]["status"] == "active"),
        "attention_count": sum(1 for row in robot_summaries if row["readiness"]["status"] == "attention"),
        "offline_count": sum(1 for row in robot_summaries if row["readiness"]["status"] == "offline"),
        "jobs_today": sum(int(row["today"]["job_count"]) for row in robot_summaries),
        "duration_today": round(sum(float(row["today"]["duration_minutes"]) for row in robot_summaries), 1),
        "area_today": round(sum(float(row["today"]["cleaned_area_m2"]) for row in robot_summaries), 1),
        "paused_plan_count": sum(
            int_or_zero((row.get("schedules") or {}).get("paused_count"))
            for row in robot_summaries
        ),
        "water_blocked_count": sum(
            ((row.get("readiness") or {}).get("water_interlock") or {}).get("status") == "blocked"
            for row in robot_summaries
        ),
        "water_interlock_error_count": sum(
            ((row.get("readiness") or {}).get("water_interlock") or {}).get("status") == "error"
            for row in robot_summaries
        ),
        "updated_at": max(overview_updates, default=None),
    }
    robot_table_columns = ["name", "model", "cloud_online", "local_ip", "battery", "last_seen_at", "last_error"]
    job_table_columns = ["begin_at", "end_at", "duration_minutes", "cleaned_area_m2", "complete", "error_code", "finish_reason"]
    status_table_columns = ["timestamp", "robot_duid", "state_name", "battery", "error_code", "clean_area_m2", "rssi"]
    robot_table_rows = []
    for robot in robots:
        latest_status = latest_status_by_robot.get(robot.duid)
        robot_table_rows.append(
            {
                "name": robot.name,
                "model": robot.model,
                "cloud_online": robot.cloud_online,
                "local_ip": robot.local_ip,
                "battery": latest_status.battery if latest_status else None,
                "last_seen_at": robot.last_seen_at,
                "last_error": robot.last_error,
            }
        )
    tables = [
        api_table("Roboter", robot_table_columns, robot_table_rows),
        api_table("Siste vasker", job_table_columns, [api_pick(row, job_table_columns) for row in jobs]),
        api_table("Siste statuser", status_table_columns, [api_pick(row, status_table_columns) for row in statuses]),
    ]
    if view == "roboter":
        robot_rows = []
        for robot in robots:
            status = latest_status_by_robot.get(robot.duid)
            robot_rows.append(
                {
                    "name": robot.name,
                    "model": robot.model,
                    "cloud_online": robot.cloud_online,
                    "local_ip": robot.local_ip,
                    "battery": status.battery if status else None,
                    "state_name": status.state_name if status else None,
                    "last_seen_at": robot.last_seen_at,
                    "last_error": robot.last_error,
                    "path": f"/classic/renhold/robot/{quote(robot.duid or '', safe='')}",
                }
            )
        tables = [
            api_table(
                "Robotdetaljer",
                ["name", "model", "cloud_online", "local_ip", "battery", "state_name", "last_seen_at", "last_error", "path"],
                robot_rows,
            ),
            api_table(
                "Renholdsverktøy",
                ["tool", "path", "description", "count"],
                [
                    api_tool_row("Klassisk oversikt", "/classic/renhold/oversikt", "Eksisterende renholdsflate med roboter, jobber og planer.", len(robots)),
                    api_tool_row("Renhold JSON", "/classic/renhold/json", "Rå JSON for roboter, jobber og statuser.", len(statuses)),
                ],
            ),
        ]
    return {
        "title": v2_module_title("renhold", view),
        "subtitle": "Robotvaskere, status, planer og utført renhold.",
        "cards": [
            api_card("Roboter", len(robot_summaries), "stk", f"{len(robots)} tilkoblet", "status", href="/renhold/roboter"),
            api_card("Siste jobber", len(jobs), "stk", "Hentet fra robotsystemene", "status", href="/renhold/oversikt"),
            api_card("Siste status", statuses[0].state_name if statuses else "-", "", statuses[0].timestamp.strftime("%H:%M") if statuses and statuses[0].timestamp else "", "status", href="/renhold/roboter"),
            api_card("Feil", sum(1 for row in statuses[:20] if row.error_code and row.error_code != 0), "siste", "Siste 20 statuser", "status", href="/renhold/roboter"),
        ],
        "tables": tables,
        "roborock": {
            "summary": overview_summary,
            "robots": robot_summaries,
            "timeline": {
                "day": today_local.isoformat(),
                "generatedAt": api_local_iso(timeline_now),
                "window": {
                    "startAt": api_local_iso(timeline_window["start"]),
                    "endAt": api_local_iso(timeline_window["end"]),
                },
                "summary": timeline_summary,
                "robots": timeline_robots,
            },
        },
    }

