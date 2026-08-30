"""Application lifecycle, bound explicitly by the composition root."""

from dataclasses import dataclass
from fibaro_core.database import Base
from fibaro_core.models import AccessKey, OutdoorLightEvent, VentilationEvent
from fibaro_core.schema_bootstrap import PERFORMANCE_INDEXES, STARTUP_COLUMNS
from sqlalchemy import delete, or_, select, text as sql_text
from typing import Any, Callable


@dataclass
class Dependencies:
    CONFIG_DEFINITIONS: Any
    FIBARO10_BACKGROUND_TASKS_ENABLED: Any
    FIBARO10_PROCESS_ROLE: Any
    HC3_DOOR_UNEXPECTED_CHECK_ENABLED: Any
    MASTER_ACCESS_KEY_HASH: Any
    OPERATIONAL_RETENTION_ENABLED: Any
    OWNTRACKS_VISIT_SYNC_ENABLED: Any
    ROBOROCK_CONTROL_TOKEN: Any
    SUN2_AXIS_SNAPSHOT_LINK_ENABLED: Any
    SUNBED_POWER_CACHE_WARM_ENABLED: Any
    SUNROOM_DOOR_MONITOR_ENABLED: Any
    SVV_API_KEY: Any
    SVV_SYNC_ENABLED: Any
    access_key_prefix: Any
    access_password_hash: Any
    async_session: Any
    background_tasks: Any
    engine: Any
    ensure_default_roborock_cleaning_profiles: Any
    ensure_default_roborock_door_automation: Any
    ensure_energy_node_backfill: Any
    ensure_roborock_schedule_snapshot_backfill: Any
    get_or_create_config: Any
    hc3_door_poll_worker: Any
    logger: Any
    normalize_username: Any
    notification_outbox_worker: Any
    operational_retention_worker: Any
    owntracks_site_visit_sync_worker: Any
    parking_vehicle_svv_worker: Any
    roborock_door_automation_worker: Any
    seed_energy_circuits: Any
    sun2_axis_snapshot_link_worker: Any
    sunbed_power_cache_warm_worker: Any
    sunroom_door_monitor_worker: Any


def create_handlers(dependencies: Dependencies):
    async def startup():
        CONFIG_DEFINITIONS = dependencies.CONFIG_DEFINITIONS
        FIBARO10_BACKGROUND_TASKS_ENABLED = dependencies.FIBARO10_BACKGROUND_TASKS_ENABLED
        FIBARO10_PROCESS_ROLE = dependencies.FIBARO10_PROCESS_ROLE
        HC3_DOOR_UNEXPECTED_CHECK_ENABLED = dependencies.HC3_DOOR_UNEXPECTED_CHECK_ENABLED
        MASTER_ACCESS_KEY_HASH = dependencies.MASTER_ACCESS_KEY_HASH
        OPERATIONAL_RETENTION_ENABLED = dependencies.OPERATIONAL_RETENTION_ENABLED
        OWNTRACKS_VISIT_SYNC_ENABLED = dependencies.OWNTRACKS_VISIT_SYNC_ENABLED
        ROBOROCK_CONTROL_TOKEN = dependencies.ROBOROCK_CONTROL_TOKEN
        SUN2_AXIS_SNAPSHOT_LINK_ENABLED = dependencies.SUN2_AXIS_SNAPSHOT_LINK_ENABLED
        SUNBED_POWER_CACHE_WARM_ENABLED = dependencies.SUNBED_POWER_CACHE_WARM_ENABLED
        SUNROOM_DOOR_MONITOR_ENABLED = dependencies.SUNROOM_DOOR_MONITOR_ENABLED
        SVV_API_KEY = dependencies.SVV_API_KEY
        SVV_SYNC_ENABLED = dependencies.SVV_SYNC_ENABLED
        access_key_prefix = dependencies.access_key_prefix
        access_password_hash = dependencies.access_password_hash
        async_session = dependencies.async_session
        background_tasks = dependencies.background_tasks
        engine = dependencies.engine
        ensure_default_roborock_cleaning_profiles = dependencies.ensure_default_roborock_cleaning_profiles
        ensure_default_roborock_door_automation = dependencies.ensure_default_roborock_door_automation
        ensure_energy_node_backfill = dependencies.ensure_energy_node_backfill
        ensure_roborock_schedule_snapshot_backfill = dependencies.ensure_roborock_schedule_snapshot_backfill
        get_or_create_config = dependencies.get_or_create_config
        hc3_door_poll_worker = dependencies.hc3_door_poll_worker
        logger = dependencies.logger
        normalize_username = dependencies.normalize_username
        notification_outbox_worker = dependencies.notification_outbox_worker
        operational_retention_worker = dependencies.operational_retention_worker
        owntracks_site_visit_sync_worker = dependencies.owntracks_site_visit_sync_worker
        parking_vehicle_svv_worker = dependencies.parking_vehicle_svv_worker
        roborock_door_automation_worker = dependencies.roborock_door_automation_worker
        seed_energy_circuits = dependencies.seed_energy_circuits
        sun2_axis_snapshot_link_worker = dependencies.sun2_axis_snapshot_link_worker
        sunbed_power_cache_warm_worker = dependencies.sunbed_power_cache_warm_worker
        sunroom_door_monitor_worker = dependencies.sunroom_door_monitor_worker
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            for table_name, columns in STARTUP_COLUMNS.items():
                for column_name, column_type in columns:
                    await conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type}")
            for _, statement in PERFORMANCE_INDEXES:
                await conn.execute(sql_text(statement))
            await conn.execute(delete(OutdoorLightEvent).where(OutdoorLightEvent.source == "CODEX TEST"))
            await conn.execute(delete(VentilationEvent).where(VentilationEvent.source == "CODEX TEST"))
        async with async_session() as session:
            node_backfill = await ensure_energy_node_backfill(session)
            if node_backfill.get("created") or node_backfill.get("linked") or node_backfill.get("updated"):
                logger.info("Energy node backfill: %s", node_backfill)
            master_rows = (
                await session.execute(
                    select(AccessKey).where(
                        or_(
                            AccessKey.key_hash == MASTER_ACCESS_KEY_HASH,
                            AccessKey.name == "master",
                            AccessKey.is_master == True,
                        )
                    )
                )
            ).scalars().all()
            master = None
            if master_rows:
                active_masters = [row for row in master_rows if row.active and (row.name == "master" or row.is_master)]
                preferred_rows = active_masters or master_rows
                master = sorted(
                    preferred_rows,
                    key=lambda row: (int(row.uses_count or 0), row.key_hash == MASTER_ACCESS_KEY_HASH, -(row.id or 0)),
                    reverse=True,
                )[0]
                merged_uses_count = sum(int(row.uses_count or 0) for row in master_rows)
                duplicate_ids = [row.id for row in master_rows if row.id and row.id != master.id]
                if duplicate_ids:
                    await session.execute(delete(AccessKey).where(AccessKey.id.in_(duplicate_ids)))
                    await session.flush()
                master.name = "master"
                master.key_hash = master.key_hash or MASTER_ACCESS_KEY_HASH
                master.key_prefix = "sun2_master"
                master.is_master = True
                master.role = "master"
                master.active = True
                master.uses_count = max(int(master.uses_count or 0), merged_uses_count)
            else:
                session.add(
                    AccessKey(
                        name="master",
                        key_hash=MASTER_ACCESS_KEY_HASH,
                        key_prefix="sun2_master",
                        role="master",
                        is_master=True,
                        active=True,
                    )
                )
            legacy_shared = (
                await session.execute(
                    select(AccessKey)
                    .where(AccessKey.is_master == False)
                    .where(AccessKey.key_plaintext.isnot(None))
                )
            ).scalars().all()
            for key in legacy_shared:
                username = normalize_username(key.name)
                password = key.key_plaintext or ""
                if not key.role:
                    key.role = "viewer"
                if username and password:
                    key.name = username
                    key.key_hash = access_password_hash(username, password, is_master=False)
                    key.key_prefix = access_key_prefix(username, password, is_master=False)
            await ensure_default_roborock_cleaning_profiles(session)
            await ensure_default_roborock_door_automation(session)
            snapshot_backfill = (
                await ensure_roborock_schedule_snapshot_backfill(session)
                if FIBARO10_BACKGROUND_TASKS_ENABLED
                else 0
            )
            if snapshot_backfill:
                logger.info("Opprettet %s innledende Roborock-plansnapshots", snapshot_backfill)
            await session.commit()
        async with async_session() as session:
            for config_key in CONFIG_DEFINITIONS:
                await get_or_create_config(session, config_key)
            await seed_energy_circuits(session)
            await session.commit()
        if not FIBARO10_BACKGROUND_TASKS_ENABLED:
            logger.info("Background tasks disabled for Fibaro10 process role %s", FIBARO10_PROCESS_ROLE)
            return
        if SVV_SYNC_ENABLED and SVV_API_KEY:
            background_tasks.start("svv-sync", parking_vehicle_svv_worker)
        if SUN2_AXIS_SNAPSHOT_LINK_ENABLED:
            background_tasks.start("sun2-axis-snapshot-link", sun2_axis_snapshot_link_worker)
        if SUNROOM_DOOR_MONITOR_ENABLED:
            background_tasks.start("sunroom-door-monitor", sunroom_door_monitor_worker)
        if HC3_DOOR_UNEXPECTED_CHECK_ENABLED:
            background_tasks.start("hc3-door-poll", hc3_door_poll_worker)
        if OWNTRACKS_VISIT_SYNC_ENABLED:
            background_tasks.start("owntracks-visit-sync", owntracks_site_visit_sync_worker)
        background_tasks.start("ntfy-outbox", notification_outbox_worker)
        if OPERATIONAL_RETENTION_ENABLED:
            background_tasks.start("operational-retention", operational_retention_worker)
        if SUNBED_POWER_CACHE_WARM_ENABLED:
            background_tasks.start("sunbed-power-cache-warm", sunbed_power_cache_warm_worker)
        if ROBOROCK_CONTROL_TOKEN:
            background_tasks.start("roborock-door-automation", roborock_door_automation_worker)

    async def shutdown_application():
        background_tasks = dependencies.background_tasks
        await background_tasks.stop_all()

    return {
        "startup": startup,
        "shutdown_application": shutdown_application,
    }
