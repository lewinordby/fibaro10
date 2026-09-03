"""Cleaning services with explicit process dependencies."""

from cleaning_robot_domain import cleaning_provider, cleaning_robot_external_id, cleaning_robot_uid
from dataclasses import dataclass
from datetime import datetime
from fastapi import HTTPException
from fibaro_core.export_definitions import ROBOROCK_TELEMETRY_COLUMNS
from fibaro_core.models import (
    CleaningZone,
    ControlConfig,
    DoorEvent,
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
from fibaro_core.schemas import RoborockCleaningProfileIn
from roborock_domain import (
    reconcile_roborock_schedule_snapshot,
    roborock_active_cycle_summary,
    roborock_fan_label,
    roborock_mop_label,
    roborock_rounds_label,
    roborock_state_label,
    roborock_telemetry_changes,
    roborock_water_label,
)
from roborock_door_automation import (
    automation_counter_start,
    automation_decision,
    opening_window,
    profile_command_payload,
    unique_ints,
)
from roborock_profiles import (
    CLEANING_TYPE_LABELS,
    DEFAULT_CLEANING_PROFILES,
    cleaning_profile_summary,
    validate_cleaning_profile,
)
from roborock_zones import RoborockZoneScheduleError, discover_roborock_zone_candidates
from sqlalchemy import func, select
from time_formatting import api_local_iso, local_now_naive, normalize_local_naive, utc_naive_to_local_naive
from typing import Any, Callable, Dict, Iterable, Mapping, Optional
from urllib.parse import quote
from value_parsing import (
    area_m2_from_payload,
    bool_value,
    first_dict,
    float_value,
    int_value,
    timestamp_value,
)
import asyncio
import hashlib
import json
import secrets
import urllib.request


@dataclass
class Dependencies:
    DREAME_CONTROL_TOKEN: Any
    DREAME_LOGGER_URL: Any
    ROBOROCK_CONTROL_TOKEN: Any
    ROBOROCK_DOOR_AUTOMATION_POLL_SECONDS: Any
    ROBOROCK_LOGGER_URL: Any
    _roborock_door_automation_lock: Any
    async_session: Callable[..., Any]
    config_defaults: Callable[..., Any]
    door_change_rows: Callable[..., Any]
    door_event_state_bool: Callable[..., Any]
    logger: Any
    merge_config_values: Callable[..., Any]
    row_to_dict: Callable[..., Any]


def create_service(dependencies: Dependencies):

    def roborock_schedule_params(schedule: Dict[str, Any]) -> Dict[str, Any]:
        params = (((schedule.get("param") or {}).get("params")) or [])
        return params[0] if params and isinstance(params[0], dict) else {}

    def roborock_schedule_snapshot_rows(schedules: Iterable[Any]) -> list[Dict[str, Any]]:
        rows = []
        for schedule in schedules:
            if isinstance(schedule, Mapping):
                params = roborock_schedule_params(dict(schedule))
                schedule_id = str(schedule.get("id") or schedule.get("schedule_id") or "")
                row = {
                    "schedule_id": schedule_id,
                    "cron": schedule.get("cron"),
                    "enabled": bool_value(schedule.get("enabled")),
                    "repeated": bool_value(schedule.get("repeated")),
                    "segments": params.get("segments"),
                    "fan_power": int_value(params.get("fan_power")),
                    "mop_mode": int_value(params.get("mop_mode")),
                    "water_box_mode": int_value(params.get("water_box_mode")),
                    "repeat": int_value(params.get("repeat")),
                }
            else:
                schedule_id = str(getattr(schedule, "schedule_id", "") or "")
                row = {
                    "schedule_id": schedule_id,
                    "cron": getattr(schedule, "cron", None),
                    "enabled": getattr(schedule, "enabled", None),
                    "repeated": getattr(schedule, "repeated", None),
                    "segments": getattr(schedule, "segments", None),
                    "fan_power": getattr(schedule, "fan_power", None),
                    "mop_mode": getattr(schedule, "mop_mode", None),
                    "water_box_mode": getattr(schedule, "water_box_mode", None),
                    "repeat": getattr(schedule, "repeat", None),
                }
            if schedule_id:
                rows.append(row)
        return sorted(rows, key=lambda row: row["schedule_id"])

    def roborock_schedule_snapshot_fingerprint(rows: list[Dict[str, Any]]) -> str:
        encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    async def record_roborock_schedule_snapshot(
        session,
        robot_duid: str,
        schedules: Iterable[Any],
        captured_at: datetime,
        source: str,
    ) -> bool:
        rows = roborock_schedule_snapshot_rows(schedules)
        fingerprint = roborock_schedule_snapshot_fingerprint(rows)
        latest = (
            await session.execute(
                select(RoborockScheduleSnapshot)
                .where(RoborockScheduleSnapshot.robot_duid == robot_duid)
                .order_by(RoborockScheduleSnapshot.captured_at.desc(), RoborockScheduleSnapshot.id.desc())
                .limit(1)
            )
        ).scalars().first()
        if latest and latest.fingerprint == fingerprint:
            return False
        session.add(
            RoborockScheduleSnapshot(
                robot_duid=robot_duid,
                captured_at=captured_at,
                source=source,
                fingerprint=fingerprint,
                schedules=rows,
            )
        )
        return True

    async def ensure_roborock_schedule_snapshot_backfill(session) -> int:
        robots = (await session.execute(select(RoborockRobot.duid))).scalars().all()
        existing_robot_duids = set(
            (await session.execute(select(RoborockScheduleSnapshot.robot_duid).distinct())).scalars().all()
        )
        created = 0
        captured_at = local_now_naive()
        for robot_duid in robots:
            if robot_duid in existing_robot_duids:
                continue
            schedules = (
                await session.execute(
                    select(RoborockSchedule)
                    .where(RoborockSchedule.robot_duid == robot_duid)
                    .where(RoborockSchedule.deleted_at.is_(None))
                    .order_by(RoborockSchedule.schedule_id)
                )
            ).scalars().all()
            if await record_roborock_schedule_snapshot(
                session,
                robot_duid,
                schedules,
                captured_at,
                "startup-backfill",
            ):
                created += 1
        return created

    def roborock_cleaning_profile_payload(profile: RoborockCleaningProfile) -> Dict[str, Any]:
        values = {
            "cleaning_type": profile.cleaning_type,
            "fan_power": profile.fan_power,
            "water_box_mode": profile.water_box_mode,
            "mop_mode": profile.mop_mode,
            "repeat": profile.repeat,
        }
        return {
            "id": profile.id,
            "slug": profile.slug,
            "name": profile.name,
            "description": profile.description or "",
            "cleaningType": profile.cleaning_type,
            "cleaningTypeLabel": CLEANING_TYPE_LABELS.get(profile.cleaning_type, profile.cleaning_type),
            "fanPower": profile.fan_power,
            "fanLabel": roborock_fan_label(profile.fan_power),
            "waterBoxMode": profile.water_box_mode,
            "waterLabel": roborock_water_label(profile.water_box_mode),
            "mopMode": profile.mop_mode,
            "mopLabel": roborock_mop_label(profile.mop_mode),
            "repeat": profile.repeat,
            "roundsLabel": roborock_rounds_label(profile.repeat),
            "summary": cleaning_profile_summary(values),
            "active": bool(profile.active),
            "builtin": bool(profile.builtin),
            "createdAt": api_local_iso(utc_naive_to_local_naive(profile.created_at)),
            "updatedAt": api_local_iso(utc_naive_to_local_naive(profile.updated_at)),
        }

    async def ensure_default_roborock_cleaning_profiles(session) -> None:
        existing = (
            await session.execute(
                select(RoborockCleaningProfile).where(
                    RoborockCleaningProfile.slug.in_([row["slug"] for row in DEFAULT_CLEANING_PROFILES])
                )
            )
        ).scalars().all()
        existing_slugs = {row.slug for row in existing}
        now = datetime.utcnow()
        for values in DEFAULT_CLEANING_PROFILES:
            if values["slug"] in existing_slugs:
                continue
            session.add(
                RoborockCleaningProfile(
                    **values,
                    active=True,
                    builtin=True,
                    created_at=now,
                    updated_at=now,
                )
            )

    async def ensure_default_roborock_door_automation(session) -> Optional[RoborockDoorAutomation]:
        robot = (
            await session.execute(
                select(RoborockRobot).where(func.lower(RoborockRobot.name) == "1.etg b")
            )
        ).scalars().first()
        if not robot:
            return None
        existing = (
            await session.execute(
                select(RoborockDoorAutomation).where(RoborockDoorAutomation.robot_duid == robot.duid)
            )
        ).scalars().first()
        if existing:
            return existing
        await session.flush()
        profile = (
            await session.execute(
                select(RoborockCleaningProfile)
                .where(RoborockCleaningProfile.slug == "vacuum-normal")
                .limit(1)
            )
        ).scalars().first()
        if not profile:
            profile = (
                await session.execute(
                    select(RoborockCleaningProfile)
                    .where(
                        RoborockCleaningProfile.cleaning_type == "vacuum",
                        RoborockCleaningProfile.active == True,
                    )
                    .order_by(RoborockCleaningProfile.id)
                    .limit(1)
                )
            ).scalars().first()
        if not profile:
            return None
        automation = RoborockDoorAutomation(
            robot_duid=robot.duid,
            door_device_id=545,
            enabled=False,
            opening_threshold=10,
            minimum_interval_minutes=60,
            zone_numbers=[1],
            profile_id=profile.id,
            counter_reset_at=local_now_naive(),
            status="disabled",
            created_at=local_now_naive(),
            updated_at=local_now_naive(),
        )
        session.add(automation)
        await session.flush()
        return automation

    async def import_roborock_cleaning_zones(
        session,
        robot_duid: str,
        schedules: Iterable[Any],
        imported_by: str,
    ) -> Dict[str, Any]:
        candidates = discover_roborock_zone_candidates(schedules)
        if not candidates:
            return {"imported": 0, "created": 0, "updated": 0, "zones": []}

        existing_pairs = (
            await session.execute(
                select(RoborockCleaningZoneMapping, CleaningZone)
                .join(CleaningZone, CleaningZone.id == RoborockCleaningZoneMapping.zone_id)
                .where(RoborockCleaningZoneMapping.robot_duid == robot_duid)
            )
        ).all()
        proposed_segments = {zone.zone_number: mapping.segment_id for mapping, zone in existing_pairs}
        proposed_segments.update({candidate.zone_number: candidate.segment_id for candidate in candidates})
        segment_owners: Dict[str, int] = {}
        for zone_number, segment_id in proposed_segments.items():
            previous_zone = segment_owners.get(segment_id)
            if previous_zone is not None and previous_zone != zone_number:
                raise RoborockZoneScheduleError(
                    f"Segment {segment_id} er allerede koblet til Sone {previous_zone} for denne roboten"
                )
            segment_owners[segment_id] = zone_number

        zone_numbers = [candidate.zone_number for candidate in candidates]
        zones = (
            await session.execute(select(CleaningZone).where(CleaningZone.zone_number.in_(zone_numbers)))
        ).scalars().all()
        zones_by_number = {zone.zone_number: zone for zone in zones}
        now = datetime.utcnow()
        created = 0
        for zone_number in zone_numbers:
            if zone_number not in zones_by_number:
                zone = CleaningZone(
                    zone_number=zone_number,
                    name=f"Sone {zone_number}",
                    created_at=now,
                    updated_at=now,
                )
                session.add(zone)
                zones_by_number[zone_number] = zone
        await session.flush()

        mappings_by_zone_id = {mapping.zone_id: mapping for mapping, _zone in existing_pairs}
        rows = []
        for candidate in candidates:
            zone = zones_by_number[candidate.zone_number]
            mapping = mappings_by_zone_id.get(zone.id)
            if not mapping:
                mapping = RoborockCleaningZoneMapping(robot_duid=robot_duid, zone_id=zone.id)
                session.add(mapping)
                created += 1
            mapping.segment_id = candidate.segment_id
            mapping.source_schedule_id = candidate.schedule_id
            mapping.source_cron = candidate.cron
            mapping.imported_at = now
            mapping.imported_by = imported_by
            rows.append(
                {
                    "zoneNumber": zone.zone_number,
                    "name": zone.name,
                    "segmentId": mapping.segment_id,
                    "sourceScheduleId": mapping.source_schedule_id,
                    "sourceCron": mapping.source_cron,
                    "importedAt": api_local_iso(utc_naive_to_local_naive(mapping.imported_at)),
                    "importedBy": mapping.imported_by,
                }
            )
        return {
            "imported": len(rows),
            "created": created,
            "updated": len(rows) - created,
            "zones": sorted(rows, key=lambda row: row["zoneNumber"]),
        }

    async def ingest_roborock_robot(session, robot_data: Dict[str, Any], batch_time: datetime, source: str) -> Dict[str, Any]:
        meta = robot_data.get("metadata") or robot_data
        provider = cleaning_provider(robot_data.get("provider") or meta.get("provider"), source)
        raw_identity = robot_data.get("external_id") or robot_data.get("duid") or robot_data.get("robot_duid")
        external_id = cleaning_robot_external_id(provider, raw_identity)
        duid = cleaning_robot_uid(provider, external_id)
        if not duid:
            return {"ok": False, "error": "Mangler DUID"}

        network = robot_data.get("network") or {}
        capabilities = robot_data.get("capabilities") or robot_data.get("probe_results") or {}
        local_ip = robot_data.get("local_ip") or network.get("ip") or meta.get("local_ip")
        status = first_dict(robot_data.get("status"))
        consumable = first_dict(robot_data.get("consumables") or robot_data.get("consumable"))
        cloud_online = bool_value(meta.get("online") if "online" in meta else meta.get("cloud_online"))

        existing = (
            await session.execute(select(RoborockRobot).where(RoborockRobot.duid == duid))
        ).scalars().first()
        if not existing:
            existing = RoborockRobot(
                duid=duid,
                provider=provider,
                external_id=external_id,
                integration_status="active",
                name=robot_data.get("name") or meta.get("name") or duid,
            )
            session.add(existing)

        existing.provider = provider
        existing.external_id = external_id
        existing.integration_status = "active"
        existing.name = robot_data.get("name") or meta.get("name") or existing.name or duid
        existing.product = robot_data.get("product") or meta.get("product") or meta.get("product_id") or existing.product
        existing.model = robot_data.get("model") or meta.get("model") or existing.model
        existing.firmware = meta.get("firmware") or meta.get("fv") or existing.firmware
        existing.protocol_version = meta.get("protocol_version") or meta.get("pv") or existing.protocol_version
        existing.serial_number = robot_data.get("serial_number") or meta.get("serial_number") or meta.get("sn") or existing.serial_number
        existing.local_ip = local_ip or existing.local_ip
        existing.cloud_online = cloud_online if cloud_online is not None else existing.cloud_online
        existing.shared = bool_value(meta.get("shared") if "shared" in meta else meta.get("share"))
        existing.time_zone_id = meta.get("time_zone_id") or meta.get("timezone") or existing.time_zone_id
        existing.last_seen_at = batch_time
        if robot_data.get("cloud"):
            existing.last_cloud_at = batch_time
        if status or network:
            existing.last_local_at = batch_time
        if status:
            existing.last_status_at = batch_time
        if robot_data.get("map"):
            existing.last_map_at = batch_time
        existing.last_error = robot_data.get("last_error") or robot_data.get("error") or None
        existing.capabilities = capabilities or existing.capabilities
        existing.extra = {
            "source": source,
            "provider": provider,
            "metadata": meta,
            "summary": robot_data.get("clean_summary"),
            "settings": robot_data.get("settings"),
        }

        if status:
            session.add(
                RoborockStatusSample(
                    robot_duid=duid,
                    timestamp=batch_time,
                    source=source,
                    state_code=int_value(status.get("state")),
                    state_name=status.get("state_name") or roborock_state_label(status.get("state")),
                    battery=int_value(status.get("battery")),
                    error_code=int_value(status.get("error_code") if "error_code" in status else status.get("error")),
                    in_cleaning=bool_value(status.get("in_cleaning")),
                    in_returning=bool_value(status.get("in_returning")),
                    clean_time_seconds=int_value(status.get("clean_time")),
                    clean_area_m2=area_m2_from_payload(status.get("clean_area")),
                    fan_power=int_value(status.get("fan_power")),
                    water_box_mode=int_value(status.get("water_box_mode")),
                    mop_mode=int_value(status.get("mop_mode")),
                    dock_type=int_value(status.get("dock_type")),
                    charge_status=int_value(status.get("charge_status")),
                    clean_percent=int_value(status.get("clean_percent")),
                    local_ip=local_ip,
                    rssi=int_value(network.get("rssi")),
                    raw={"status": status, "network": network},
                )
            )

        if consumable:
            session.add(
                RoborockConsumableSnapshot(
                    robot_duid=duid,
                    timestamp=batch_time,
                    main_brush_work_time=int_value(consumable.get("main_brush_work_time")),
                    side_brush_work_time=int_value(consumable.get("side_brush_work_time")),
                    filter_work_time=int_value(consumable.get("filter_work_time")),
                    sensor_dirty_time=int_value(consumable.get("sensor_dirty_time")),
                    dust_collection_work_times=int_value(consumable.get("dust_collection_work_times")),
                    raw=consumable,
                )
            )

        for job in robot_data.get("clean_jobs") or robot_data.get("jobs") or []:
            record_id = str(job.get("id") or job.get("record_id") or "")
            if not record_id:
                continue
            existing_job = (
                await session.execute(
                    select(RoborockCleanJob)
                    .where(RoborockCleanJob.robot_duid == duid)
                    .where(RoborockCleanJob.record_id == record_id)
                )
            ).scalars().first()
            if not existing_job:
                existing_job = RoborockCleanJob(robot_duid=duid, record_id=record_id)
                session.add(existing_job)
            existing_job.begin_at = timestamp_value(job.get("begin") or job.get("begin_at"))
            existing_job.end_at = timestamp_value(job.get("end") or job.get("end_at"))
            existing_job.duration_seconds = int_value(job.get("duration_seconds") or job.get("duration"))
            existing_job.duration_minutes = float_value(job.get("duration_minutes"))
            existing_job.area_m2 = float_value(job.get("area_m2")) or area_m2_from_payload(job.get("area"))
            existing_job.cleaned_area_m2 = float_value(job.get("cleaned_area_m2")) or area_m2_from_payload(job.get("cleaned_area"))
            existing_job.complete = bool_value(job.get("complete"))
            existing_job.error_code = int_value(job.get("error") if "error" in job else job.get("error_code"))
            existing_job.start_type = int_value(job.get("start_type"))
            existing_job.clean_type = int_value(job.get("clean_type"))
            existing_job.finish_reason = int_value(job.get("finish_reason"))
            existing_job.dust_collection_status = int_value(job.get("dust_collection_status"))
            existing_job.avoid_count = int_value(job.get("avoid_count"))
            existing_job.wash_count = int_value(job.get("wash_count"))
            existing_job.clean_times = int_value(job.get("clean_times"))
            existing_job.updated_at = batch_time
            existing_job.raw = job

        raw_schedules = robot_data.get("schedules")
        schedules_received = isinstance(raw_schedules, list) and all(
            isinstance(schedule, dict) and str(schedule.get("id") or schedule.get("schedule_id") or "")
            for schedule in raw_schedules
        )
        schedule_payloads = raw_schedules if schedules_received else []
        existing_schedules = []
        schedules_by_id: Dict[str, RoborockSchedule] = {}
        if schedules_received:
            existing_schedules = (
                await session.execute(
                    select(RoborockSchedule).where(RoborockSchedule.robot_duid == duid)
                )
            ).scalars().all()
            schedules_by_id = {str(row.schedule_id): row for row in existing_schedules}
        seen_schedule_ids: set[str] = set()
        for schedule in schedule_payloads:
            schedule_id = str(schedule.get("id") or schedule.get("schedule_id") or "")
            if not schedule_id:
                continue
            seen_schedule_ids.add(schedule_id)
            params = roborock_schedule_params(schedule)
            existing_schedule = schedules_by_id.get(schedule_id)
            if not existing_schedule:
                existing_schedule = RoborockSchedule(robot_duid=duid, schedule_id=schedule_id)
                session.add(existing_schedule)
                existing_schedules.append(existing_schedule)
                schedules_by_id[schedule_id] = existing_schedule
            existing_schedule.cron = schedule.get("cron")
            existing_schedule.enabled = bool_value(schedule.get("enabled"))
            existing_schedule.repeated = bool_value(schedule.get("repeated"))
            existing_schedule.segments = params.get("segments")
            existing_schedule.fan_power = int_value(params.get("fan_power"))
            existing_schedule.mop_mode = int_value(params.get("mop_mode"))
            existing_schedule.water_box_mode = int_value(params.get("water_box_mode"))
            existing_schedule.repeat = int_value(params.get("repeat"))
            existing_schedule.updated_at = batch_time
            existing_schedule.raw = schedule

        deleted_schedules = (
            reconcile_roborock_schedule_snapshot(existing_schedules, seen_schedule_ids, batch_time)
            if schedules_received
            else 0
        )
        schedule_snapshot_created = False
        if schedules_received:
            schedule_snapshot_created = await record_roborock_schedule_snapshot(
                session,
                duid,
                schedule_payloads,
                batch_time,
                source,
            )

        if provider == "roborock":
            try:
                zone_import = await import_roborock_cleaning_zones(session, duid, schedule_payloads, source)
                zone_import_status = {
                    "status": "ok",
                    "checkedAt": api_local_iso(batch_time),
                    "imported": zone_import["imported"],
                }
            except RoborockZoneScheduleError as exc:
                zone_import_status = {
                    "status": "error",
                    "checkedAt": api_local_iso(batch_time),
                    "message": str(exc),
                }
        else:
            zone_import_status = {
                "status": "not_applicable",
                "checkedAt": api_local_iso(batch_time),
                "message": "Soner administreres av Dreamehome.",
            }
        existing.extra = {**(existing.extra or {}), "cleaning_zone_import": zone_import_status}

        map_data = robot_data.get("map") or {}
        if map_data:
            image_size = map_data.get("image_size") or []
            if not isinstance(image_size, list):
                image_size = []
            session.add(
                RoborockMapSnapshot(
                    robot_duid=duid,
                    timestamp=batch_time,
                    image_bytes=int_value(map_data.get("image_bytes")),
                    raw_bytes=int_value(map_data.get("raw_bytes")),
                    image_width=int_value(image_size[0] if len(image_size) > 0 else map_data.get("image_width")),
                    image_height=int_value(image_size[1] if len(image_size) > 1 else map_data.get("image_height")),
                    rooms=int_value(map_data.get("rooms")),
                    zones=int_value(map_data.get("zones")),
                    charger=map_data.get("charger"),
                    vacuum_position=map_data.get("vacuum_position"),
                    image_base64=map_data.get("image_base64"),
                    raw={key: value for key, value in map_data.items() if key != "image_base64"},
                )
            )

        for probe in robot_data.get("probe_results") or []:
            session.add(
                RoborockProbeResult(
                    robot_duid=duid,
                    timestamp=batch_time,
                    source=probe.get("source") or source,
                    command=probe.get("command") or probe.get("name"),
                    ok=bool_value(probe.get("ok")),
                    error=probe.get("error"),
                    result_type=probe.get("type") or probe.get("result_type"),
                    raw=probe,
                )
            )
        return {
            "ok": True,
            "duid": duid,
            "deleted_schedules": deleted_schedules,
            "schedule_snapshot_created": schedule_snapshot_created,
        }

    def roborock_telemetry_sample_values(telemetry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "state_code": int_value(telemetry.get("state_code")),
            "state_name": telemetry.get("state_name"),
            "battery": int_value(telemetry.get("battery")),
            "error_code": int_value(telemetry.get("error_code")),
            "in_cleaning": bool_value(telemetry.get("in_cleaning")),
            "in_returning": bool_value(telemetry.get("in_returning")),
            "clean_time_seconds": int_value(telemetry.get("clean_time_seconds")),
            "clean_area_m2": area_m2_from_payload(telemetry.get("clean_area_raw")),
            "clean_percent": int_value(telemetry.get("clean_percent")),
            "fan_power": int_value(telemetry.get("fan_power")),
            "water_box_mode": int_value(telemetry.get("water_box_mode")),
            "mop_mode": int_value(telemetry.get("mop_mode")),
            "charge_status": int_value(telemetry.get("charge_status")),
            "is_charging": bool_value(telemetry.get("is_charging")),
            "dock_type": int_value(telemetry.get("dock_type")),
            "dock_error_status": int_value(telemetry.get("dock_error_status")),
            "dust_collection_status": int_value(telemetry.get("dust_collection_status")),
            "auto_dust_collection": bool_value(telemetry.get("auto_dust_collection")),
            "wash_status": int_value(telemetry.get("wash_status")),
            "wash_phase": int_value(telemetry.get("wash_phase")),
            "wash_ready": bool_value(telemetry.get("wash_ready")),
            "dry_status": int_value(telemetry.get("dry_status")),
            "water_shortage_status": int_value(telemetry.get("water_shortage_status")),
            "water_box_status": int_value(telemetry.get("water_box_status")),
            "water_box_carriage_status": int_value(telemetry.get("water_box_carriage_status")),
            "clear_water_status": int_value(telemetry.get("clear_water_status")),
            "clear_water_status_name": telemetry.get("clear_water_status_name"),
            "dirty_water_status": int_value(telemetry.get("dirty_water_status")),
            "dirty_water_status_name": telemetry.get("dirty_water_status_name"),
            "dust_bag_status": int_value(telemetry.get("dust_bag_status")),
            "dust_bag_status_name": telemetry.get("dust_bag_status_name"),
            "clean_fluid_status": int_value(telemetry.get("clean_fluid_status")),
            "clean_fluid_status_name": telemetry.get("clean_fluid_status_name"),
            "water_box_filter_status": int_value(telemetry.get("water_box_filter_status")),
            "dock_cool_fan_status": int_value(telemetry.get("dock_cool_fan_status")),
            "local_ip": telemetry.get("local_ip"),
            "rssi": int_value(telemetry.get("rssi")),
            "dss": int_value(telemetry.get("dss")),
            "rss": int_value(telemetry.get("rss")),
        }

    def roborock_water_interlock_from_sample(sample: Any) -> Dict[str, Any]:
        raw = getattr(sample, "raw", None)
        normalized = raw.get("normalized") if isinstance(raw, dict) else None
        interlock = normalized.get("water_interlock") if isinstance(normalized, dict) else None
        return interlock if isinstance(interlock, dict) else {}

    async def ingest_roborock_telemetry_robot(
        session,
        robot_data: Dict[str, Any],
        batch_time: datetime,
        source: str,
    ) -> Dict[str, Any]:
        row_to_dict = dependencies.row_to_dict
        provider = cleaning_provider(robot_data.get("provider"), source)
        raw_identity = robot_data.get("external_id") or robot_data.get("duid") or robot_data.get("robot_duid")
        external_id = cleaning_robot_external_id(provider, raw_identity)
        duid = cleaning_robot_uid(provider, external_id)
        if not duid:
            return {"ok": False, "error": "Mangler DUID", "events": 0}

        robot = (
            await session.execute(select(RoborockRobot).where(RoborockRobot.duid == duid))
        ).scalars().first()
        if not robot:
            robot = RoborockRobot(
                duid=duid,
                provider=provider,
                external_id=external_id,
                integration_status="active",
                name=robot_data.get("name") or duid,
            )
            session.add(robot)
        robot.provider = provider
        robot.external_id = external_id
        robot.integration_status = "active"
        robot.name = robot_data.get("name") or robot.name
        robot.model = robot_data.get("model") or robot.model
        robot.local_ip = robot_data.get("local_ip") or robot.local_ip
        robot.last_seen_at = batch_time

        telemetry = robot_data.get("telemetry") or {}
        events_created = 0
        if telemetry:
            values = roborock_telemetry_sample_values(telemetry)
            previous = (
                await session.execute(
                    select(RoborockTelemetrySample)
                    .where(RoborockTelemetrySample.robot_duid == duid)
                    .order_by(RoborockTelemetrySample.timestamp.desc(), RoborockTelemetrySample.id.desc())
                    .limit(1)
                )
            ).scalars().first()
            previous_values = (
                row_to_dict(previous, [column for column in ROBOROCK_TELEMETRY_COLUMNS if column not in {"id", "raw"}])
                if previous
                else None
            )
            sample = RoborockTelemetrySample(
                robot_duid=duid,
                timestamp=batch_time,
                source=source,
                raw={
                    "status_raw": telemetry.get("status_raw") or {},
                    "network_raw": telemetry.get("network_raw") or {},
                    "normalized": {
                        key: value
                        for key, value in telemetry.items()
                        if key not in {"status_raw", "network_raw"}
                    },
                },
                **values,
            )
            session.add(sample)
            robot.last_local_at = batch_time
            robot.last_status_at = batch_time
            robot.local_ip = values.get("local_ip") or robot.local_ip

            for change in roborock_telemetry_changes(previous_values, values, robot.provider):
                session.add(
                    RoborockTelemetryEvent(
                        robot_duid=duid,
                        timestamp=batch_time,
                        raw={"source": source},
                        **change,
                    )
                )
                events_created += 1

        for probe in robot_data.get("probes") or []:
            command = probe.get("command") or probe.get("name")
            if command in {"GET_STATUS", "GET_NETWORK_INFO"}:
                continue
            session.add(
                RoborockProbeResult(
                    robot_duid=duid,
                    timestamp=batch_time,
                    source=probe.get("source") or source,
                    command=command,
                    ok=bool_value(probe.get("ok")),
                    error=probe.get("error"),
                    result_type=probe.get("result_type") or probe.get("type"),
                    raw=probe,
                )
            )
        return {"ok": bool(telemetry), "duid": duid, "events": events_created}

    def api_roborock_active_cycle(status_rows: list[Any]) -> Optional[Dict[str, Any]]:
        cycle = roborock_active_cycle_summary(status_rows)
        if not cycle:
            return None
        return {
            **cycle,
            "started_at": api_local_iso(cycle.get("started_at")),
            "last_floor_at": api_local_iso(cycle.get("last_floor_at")),
            "dock_since": api_local_iso(cycle.get("dock_since")),
            "last_observed_at": api_local_iso(cycle.get("last_observed_at")),
        }

    def latest_cleaning_robot_sample(status_sample: Any = None, telemetry_sample: Any = None) -> Any:
        candidates = [sample for sample in (telemetry_sample, status_sample) if sample is not None]
        return max(
            candidates,
            key=lambda sample: normalize_local_naive(getattr(sample, "timestamp", None)) or datetime.min,
            default=None,
        )

    async def roborock_door_automation_payload(
        session,
        automation: RoborockDoorAutomation,
        now: Optional[datetime] = None,
    ) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        ROBOROCK_CONTROL_TOKEN = dependencies.ROBOROCK_CONTROL_TOKEN
        config_defaults = dependencies.config_defaults
        door_change_rows = dependencies.door_change_rows
        door_event_state_bool = dependencies.door_event_state_bool
        merge_config_values = dependencies.merge_config_values
        now = normalize_local_naive(now) or local_now_naive()
        ventilation_config = (
            await session.execute(select(ControlConfig).where(ControlConfig.key == "ventilation"))
        ).scalars().first()
        ventilation_values = merge_config_values(
            "ventilation",
            ventilation_config.values if ventilation_config else config_defaults("ventilation"),
        )
        open_at, close_at = opening_window(
            now.date(),
            ventilation_values.get("open_from"),
            ventilation_values.get("close_at"),
        )
        counter_start = automation_counter_start(
            open_at,
            normalize_local_naive(automation.last_started_at),
            normalize_local_naive(automation.counter_reset_at),
        )
        previous_event = (
            await session.execute(
                select(DoorEvent)
                .where(
                    DoorEvent.device_id == automation.door_device_id,
                    DoorEvent.timestamp < counter_start,
                )
                .order_by(DoorEvent.timestamp.desc(), DoorEvent.id.desc())
                .limit(1)
            )
        ).scalars().first()
        period_events = (
            await session.execute(
                select(DoorEvent)
                .where(
                    DoorEvent.device_id == automation.door_device_id,
                    DoorEvent.timestamp >= counter_start,
                    DoorEvent.timestamp <= now,
                )
                .order_by(DoorEvent.timestamp, DoorEvent.id)
            )
        ).scalars().all()
        current_event = (
            await session.execute(
                select(DoorEvent)
                .where(
                    DoorEvent.device_id == automation.door_device_id,
                    DoorEvent.timestamp <= now,
                )
                .order_by(DoorEvent.timestamp.desc(), DoorEvent.id.desc())
                .limit(1)
            )
        ).scalars().first()
        change_events = door_change_rows(([previous_event] if previous_event else []) + list(period_events))
        opening_events = [
            row
            for row in change_events
            if door_event_state_bool(row) is True
            and (normalize_local_naive(row.timestamp) or datetime.min) >= counter_start
        ]
        last_opening_at = (
            normalize_local_naive(opening_events[-1].timestamp) if opening_events else None
        )

        selected_zone_numbers = unique_ints(automation.zone_numbers or [])
        mapping_pairs = (
            await session.execute(
                select(RoborockCleaningZoneMapping, CleaningZone)
                .join(CleaningZone, CleaningZone.id == RoborockCleaningZoneMapping.zone_id)
                .where(
                    RoborockCleaningZoneMapping.robot_duid == automation.robot_duid,
                    CleaningZone.zone_number.in_(selected_zone_numbers or [-1]),
                )
                .order_by(CleaningZone.zone_number)
            )
        ).all()
        mappings_by_zone = {zone.zone_number: (mapping, zone) for mapping, zone in mapping_pairs}
        configured_zones = []
        segment_ids: list[int] = []
        validation_issues: list[str] = []
        if not selected_zone_numbers:
            validation_issues.append("Velg minst én sone")
        for zone_number in selected_zone_numbers:
            pair = mappings_by_zone.get(zone_number)
            if not pair:
                configured_zones.append(
                    {"zoneNumber": zone_number, "name": f"Sone {zone_number}", "segmentId": None, "mapped": False}
                )
                validation_issues.append(f"Sone {zone_number} er ikke kartlagt for roboten")
                continue
            mapping, zone = pair
            try:
                segment_id = int(mapping.segment_id)
            except (TypeError, ValueError):
                segment_id = 0
            configured_zones.append(
                {
                    "zoneNumber": zone.zone_number,
                    "name": zone.name,
                    "segmentId": segment_id or None,
                    "mapped": segment_id > 0,
                }
            )
            if segment_id > 0:
                segment_ids.append(segment_id)
            else:
                validation_issues.append(f"{zone.name} har ugyldig robotsegment")

        profile = await session.get(RoborockCleaningProfile, automation.profile_id)
        profile_payload = roborock_cleaning_profile_payload(profile) if profile else None
        if not profile or not profile.active:
            validation_issues.append("Valgt rengjøringsprofil finnes ikke eller er deaktivert")
        elif profile.cleaning_type != "vacuum":
            validation_issues.append("Dørstyringen krever en ren støvsugingsprofil")
        if not ROBOROCK_CONTROL_TOKEN:
            validation_issues.append("Robotstyring er ikke konfigurert")

        decision = automation_decision(
            now=now,
            enabled=bool(automation.enabled),
            open_at=open_at,
            close_at=close_at,
            opening_count=len(opening_events),
            opening_threshold=automation.opening_threshold,
            minimum_interval_minutes=automation.minimum_interval_minutes,
            last_started_at=normalize_local_naive(automation.last_started_at),
            door_is_open=door_event_state_bool(current_event),
            validation_issues=validation_issues,
            status=automation.status,
            last_attempt_at=normalize_local_naive(automation.last_attempt_at),
        )
        public_payload = {
            "enabled": bool(automation.enabled),
            "doorDeviceId": automation.door_device_id,
            "openingThreshold": automation.opening_threshold,
            "minimumIntervalMinutes": automation.minimum_interval_minutes,
            "zoneNumbers": selected_zone_numbers,
            "profileId": automation.profile_id,
            "profile": profile_payload,
            "configuredZones": configured_zones,
            "openingCount": len(opening_events),
            "counterStartedAt": api_local_iso(counter_start),
            "lastOpeningAt": api_local_iso(last_opening_at),
            "doorIsOpen": door_event_state_bool(current_event),
            "openingHours": {
                "openAt": api_local_iso(open_at),
                "closeAt": api_local_iso(close_at),
                "openFrom": open_at.strftime("%H:%M"),
                "closeAtLabel": close_at.strftime("%H:%M"),
            },
            "status": decision["key"],
            "statusLabel": decision["label"],
            "statusDetail": decision["detail"],
            "eligible": decision["eligible"],
            "pendingStart": decision["pending"],
            "nextAllowedAt": api_local_iso(decision["next_allowed_at"]),
            "remainingIntervalSeconds": decision["remaining_interval_seconds"],
            "validationIssues": validation_issues,
            "lastAttemptAt": api_local_iso(normalize_local_naive(automation.last_attempt_at)),
            "lastStartedAt": api_local_iso(normalize_local_naive(automation.last_started_at)),
            "lastRequestId": automation.last_request_id,
            "lastError": automation.last_error,
            "updatedAt": api_local_iso(normalize_local_naive(automation.updated_at)),
        }
        command_payload = None
        if (
            not validation_issues
            and selected_zone_numbers
            and len(segment_ids) == len(selected_zone_numbers)
            and profile_payload
        ):
            command_payload = {
                "zone_numbers": selected_zone_numbers,
                "segment_ids": segment_ids,
                "zone_names": [row["name"] for row in configured_zones],
                "profile": profile_command_payload(profile_payload),
            }
        return public_payload, command_payload

    def post_roborock_control(duid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        ROBOROCK_CONTROL_TOKEN = dependencies.ROBOROCK_CONTROL_TOKEN
        ROBOROCK_LOGGER_URL = dependencies.ROBOROCK_LOGGER_URL
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        control_request = urllib.request.Request(
            f"{ROBOROCK_LOGGER_URL}/api/control/{quote(duid, safe='')}",
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-roborock-control-token": ROBOROCK_CONTROL_TOKEN,
            },
        )
        try:
            with urllib.request.urlopen(control_request, timeout=40) as response:
                data = json.loads(response.read().decode("utf-8") or "{}")
                return data if isinstance(data, dict) else {"result": data}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                error_data = json.loads(raw or "{}")
            except json.JSONDecodeError:
                error_data = {}
            detail = error_data.get("detail") if isinstance(error_data, dict) else None
            raise RuntimeError(str(detail or raw or f"Roborock_logger svarte {exc.code}")) from exc

    def post_dreame_control(external_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        DREAME_CONTROL_TOKEN = dependencies.DREAME_CONTROL_TOKEN
        DREAME_LOGGER_URL = dependencies.DREAME_LOGGER_URL
        body = json.dumps(
            {"action": payload.get("action"), "request_id": payload.get("request_id")},
            ensure_ascii=False,
        ).encode("utf-8")
        control_request = urllib.request.Request(
            f"{DREAME_LOGGER_URL}/robots/{quote(external_id, safe='')}/control",
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-dreame-control-token": DREAME_CONTROL_TOKEN,
            },
        )
        try:
            with urllib.request.urlopen(control_request, timeout=40) as response:
                data = json.loads(response.read().decode("utf-8") or "{}")
                return data if isinstance(data, dict) else {"result": data}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                error_data = json.loads(raw or "{}")
            except json.JSONDecodeError:
                error_data = {}
            detail = error_data.get("detail") if isinstance(error_data, dict) else None
            raise RuntimeError(str(detail or raw or f"Dreame_logger svarte {exc.code}")) from exc

    async def run_roborock_door_automation_once(now: Optional[datetime] = None) -> Dict[str, Any]:
        _roborock_door_automation_lock = dependencies._roborock_door_automation_lock
        async_session = dependencies.async_session
        async with _roborock_door_automation_lock:
            now = normalize_local_naive(now) or local_now_naive()
            async with async_session() as session:
                automations = (
                    await session.execute(
                        select(RoborockDoorAutomation).order_by(RoborockDoorAutomation.id)
                    )
                ).scalars().all()
                results: list[Dict[str, Any]] = []
                for automation in automations:
                    public_payload, command_payload = await roborock_door_automation_payload(
                        session, automation, now
                    )
                    current_status = str(public_payload["status"])
                    if automation.status != current_status and current_status != "ready":
                        automation.status = current_status
                        automation.updated_at = now
                    if not public_payload["eligible"] or not command_payload:
                        results.append(
                            {
                                "robotDuid": automation.robot_duid,
                                "status": current_status,
                                "started": False,
                            }
                        )
                        continue

                    request_id = f"door-auto-{secrets.token_hex(12)}"
                    automation.status = "starting"
                    automation.last_attempt_at = now
                    automation.last_request_id = request_id
                    automation.last_error = None
                    automation.updated_at = now
                    command_run = RoborockCommandRun(
                        request_id=request_id,
                        robot_duid=automation.robot_duid,
                        action="clean_zone",
                        requested_at=datetime.utcnow(),
                        requested_by="door_automation",
                        status="running",
                        message=(
                            f"Automatisk støvsuging etter {automation.opening_threshold} inngangsdøråpninger"
                        ),
                    )
                    session.add(command_run)
                    await session.commit()
                    command_id = command_run.id

                    try:
                        result = await asyncio.to_thread(
                            post_roborock_control,
                            automation.robot_duid,
                            {
                                "action": "clean_zone",
                                "request_id": request_id,
                                "actor": "door_automation",
                                "confirmation": f"CONFIRM:{automation.robot_duid}:clean_zone",
                                "zone_numbers": command_payload["zone_numbers"],
                                "segment_ids": command_payload["segment_ids"],
                                "zone_number": command_payload["zone_numbers"][0],
                                "segment_id": command_payload["segment_ids"][0],
                                "profile": command_payload["profile"],
                            },
                        )
                        command_status = str(result.get("status") or "ok")
                        if command_status != "ok":
                            raise RuntimeError(str(result.get("message") or "Robotkommandoen feilet"))
                        message = (
                            f"{command_payload['profile']['name']} startet i "
                            f"{', '.join(command_payload['zone_names'])}"
                        )
                        before_state = result.get("before")
                        after_state = result.get("after")
                        error_message = None
                    except Exception as exc:
                        result = {"error": str(exc), "target": command_payload}
                        command_status = "error"
                        message = str(exc)
                        before_state = None
                        after_state = None
                        error_message = str(exc)

                    automation = await session.get(RoborockDoorAutomation, automation.id)
                    command_run = await session.get(RoborockCommandRun, command_id)
                    finished_at = local_now_naive()
                    if command_run:
                        command_run.finished_at = datetime.utcnow()
                        command_run.status = command_status
                        command_run.message = message
                        command_run.before_state = before_state
                        command_run.after_state = after_state
                        command_run.result = result
                    if automation:
                        automation.updated_at = finished_at
                        if command_status == "ok":
                            automation.status = "counting"
                            automation.last_started_at = finished_at
                            automation.last_error = None
                        else:
                            automation.status = "error"
                            automation.last_error = error_message
                    await session.commit()
                    results.append(
                        {
                            "robotDuid": command_run.robot_duid if command_run else None,
                            "status": command_status,
                            "started": command_status == "ok",
                            "message": message,
                        }
                    )
                await session.commit()
                return {"checkedAt": api_local_iso(now), "automations": results}

    async def roborock_door_automation_worker() -> None:
        ROBOROCK_DOOR_AUTOMATION_POLL_SECONDS = dependencies.ROBOROCK_DOOR_AUTOMATION_POLL_SECONDS
        logger = dependencies.logger
        await asyncio.sleep(10)
        while True:
            try:
                await run_roborock_door_automation_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Feil i inngangsstyrt Roborock-automatikk")
            await asyncio.sleep(ROBOROCK_DOOR_AUTOMATION_POLL_SECONDS)

    def apply_roborock_cleaning_profile_values(
        profile: RoborockCleaningProfile,
        values: RoborockCleaningProfileIn,
    ) -> None:
        try:
            settings = validate_cleaning_profile(values.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        profile.name = values.name.strip()
        profile.description = values.description.strip()
        profile.cleaning_type = settings["cleaning_type"]
        profile.fan_power = settings["fan_power"]
        profile.water_box_mode = settings["water_box_mode"]
        profile.mop_mode = settings["mop_mode"]
        profile.repeat = settings["repeat"]
        profile.active = values.active
        profile.updated_at = datetime.utcnow()

    return {
        "api_roborock_active_cycle": api_roborock_active_cycle,
        "apply_roborock_cleaning_profile_values": apply_roborock_cleaning_profile_values,
        "ensure_default_roborock_cleaning_profiles": ensure_default_roborock_cleaning_profiles,
        "ensure_default_roborock_door_automation": ensure_default_roborock_door_automation,
        "ensure_roborock_schedule_snapshot_backfill": ensure_roborock_schedule_snapshot_backfill,
        "import_roborock_cleaning_zones": import_roborock_cleaning_zones,
        "ingest_roborock_robot": ingest_roborock_robot,
        "ingest_roborock_telemetry_robot": ingest_roborock_telemetry_robot,
        "latest_cleaning_robot_sample": latest_cleaning_robot_sample,
        "post_dreame_control": post_dreame_control,
        "post_roborock_control": post_roborock_control,
        "record_roborock_schedule_snapshot": record_roborock_schedule_snapshot,
        "roborock_cleaning_profile_payload": roborock_cleaning_profile_payload,
        "roborock_door_automation_payload": roborock_door_automation_payload,
        "roborock_door_automation_worker": roborock_door_automation_worker,
        "roborock_schedule_params": roborock_schedule_params,
        "roborock_schedule_snapshot_fingerprint": roborock_schedule_snapshot_fingerprint,
        "roborock_schedule_snapshot_rows": roborock_schedule_snapshot_rows,
        "roborock_telemetry_sample_values": roborock_telemetry_sample_values,
        "roborock_water_interlock_from_sample": roborock_water_interlock_from_sample,
        "run_roborock_door_automation_once": run_roborock_door_automation_once,
    }
