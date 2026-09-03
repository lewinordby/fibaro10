"""Cleaning models."""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from fibaro_core.database import Base
from time_formatting import local_now_naive


class RoborockRobot(Base):
    __tablename__ = "roborock_robots"

    id = Column(Integer, primary_key=True, index=True)
    duid = Column(String, unique=True, index=True, nullable=False)
    provider = Column(String, index=True, nullable=False, default="roborock")
    external_id = Column(String, index=True, nullable=True)
    integration_status = Column(String, nullable=False, default="active")
    name = Column(String, index=True, nullable=False)
    product = Column(String, nullable=True)
    model = Column(String, nullable=True)
    firmware = Column(String, nullable=True)
    protocol_version = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    local_ip = Column(String, nullable=True)
    cloud_online = Column(Boolean, nullable=True)
    shared = Column(Boolean, nullable=True)
    time_zone_id = Column(String, nullable=True)
    last_seen_at = Column(DateTime, nullable=True, index=True)
    last_cloud_at = Column(DateTime, nullable=True)
    last_local_at = Column(DateTime, nullable=True)
    last_status_at = Column(DateTime, nullable=True)
    last_map_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    capabilities = Column(JSON, nullable=True)
    extra = Column(JSON, nullable=True)


class RoborockStatusSample(Base):
    __tablename__ = "roborock_status_samples"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, nullable=True)
    state_code = Column(Integer, nullable=True)
    state_name = Column(String, nullable=True)
    battery = Column(Integer, nullable=True)
    error_code = Column(Integer, nullable=True)
    in_cleaning = Column(Boolean, nullable=True)
    in_returning = Column(Boolean, nullable=True)
    clean_time_seconds = Column(Integer, nullable=True)
    clean_area_m2 = Column(Float, nullable=True)
    fan_power = Column(Integer, nullable=True)
    water_box_mode = Column(Integer, nullable=True)
    mop_mode = Column(Integer, nullable=True)
    dock_type = Column(Integer, nullable=True)
    charge_status = Column(Integer, nullable=True)
    clean_percent = Column(Integer, nullable=True)
    local_ip = Column(String, nullable=True)
    rssi = Column(Integer, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockTelemetrySample(Base):
    __tablename__ = "roborock_telemetry_samples"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, nullable=True)
    state_code = Column(Integer, nullable=True)
    state_name = Column(String, nullable=True)
    battery = Column(Integer, nullable=True)
    error_code = Column(Integer, nullable=True)
    in_cleaning = Column(Boolean, nullable=True)
    in_returning = Column(Boolean, nullable=True)
    clean_time_seconds = Column(Integer, nullable=True)
    clean_area_m2 = Column(Float, nullable=True)
    clean_percent = Column(Integer, nullable=True)
    fan_power = Column(Integer, nullable=True)
    water_box_mode = Column(Integer, nullable=True)
    mop_mode = Column(Integer, nullable=True)
    charge_status = Column(Integer, nullable=True)
    is_charging = Column(Boolean, nullable=True)
    dock_type = Column(Integer, nullable=True)
    dock_error_status = Column(Integer, nullable=True)
    dust_collection_status = Column(Integer, nullable=True)
    auto_dust_collection = Column(Boolean, nullable=True)
    wash_status = Column(Integer, nullable=True)
    wash_phase = Column(Integer, nullable=True)
    wash_ready = Column(Boolean, nullable=True)
    dry_status = Column(Integer, nullable=True)
    water_shortage_status = Column(Integer, nullable=True)
    water_box_status = Column(Integer, nullable=True)
    water_box_carriage_status = Column(Integer, nullable=True)
    clear_water_status = Column(Integer, nullable=True)
    clear_water_status_name = Column(String, nullable=True)
    dirty_water_status = Column(Integer, nullable=True)
    dirty_water_status_name = Column(String, nullable=True)
    dust_bag_status = Column(Integer, nullable=True)
    dust_bag_status_name = Column(String, nullable=True)
    clean_fluid_status = Column(Integer, nullable=True)
    clean_fluid_status_name = Column(String, nullable=True)
    water_box_filter_status = Column(Integer, nullable=True)
    dock_cool_fan_status = Column(Integer, nullable=True)
    local_ip = Column(String, nullable=True)
    rssi = Column(Integer, nullable=True)
    dss = Column(Integer, nullable=True)
    rss = Column(Integer, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockTelemetryEvent(Base):
    __tablename__ = "roborock_telemetry_events"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    category = Column(String, index=True, nullable=True)
    field_name = Column(String, index=True, nullable=False)
    title = Column(String, nullable=True)
    previous_value = Column(String, nullable=True)
    current_value = Column(String, nullable=True)
    previous_label = Column(String, nullable=True)
    current_label = Column(String, nullable=True)
    severity = Column(String, index=True, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockCleanJob(Base):
    __tablename__ = "roborock_clean_jobs"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    record_id = Column(String, index=True, nullable=False)
    begin_at = Column(DateTime, index=True, nullable=True)
    end_at = Column(DateTime, index=True, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    area_m2 = Column(Float, nullable=True)
    cleaned_area_m2 = Column(Float, nullable=True)
    complete = Column(Boolean, nullable=True)
    error_code = Column(Integer, nullable=True)
    start_type = Column(Integer, nullable=True)
    clean_type = Column(Integer, nullable=True)
    finish_reason = Column(Integer, nullable=True)
    dust_collection_status = Column(Integer, nullable=True)
    avoid_count = Column(Integer, nullable=True)
    wash_count = Column(Integer, nullable=True)
    clean_times = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class RoborockSchedule(Base):
    __tablename__ = "roborock_schedules"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    schedule_id = Column(String, index=True, nullable=False)
    cron = Column(String, nullable=True)
    enabled = Column(Boolean, nullable=True)
    repeated = Column(Boolean, nullable=True)
    segments = Column(String, nullable=True)
    fan_power = Column(Integer, nullable=True)
    mop_mode = Column(Integer, nullable=True)
    water_box_mode = Column(Integer, nullable=True)
    repeat = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    raw = Column(JSON, nullable=True)


class RoborockScheduleSnapshot(Base):
    __tablename__ = "roborock_schedule_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    captured_at = Column(DateTime, index=True, nullable=False)
    source = Column(String, nullable=True)
    fingerprint = Column(String, nullable=False)
    schedules = Column(JSON, nullable=False, default=list)


class CleaningZone(Base):
    __tablename__ = "cleaning_zones"

    id = Column(Integer, primary_key=True, index=True)
    zone_number = Column(Integer, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class RoborockCleaningZoneMapping(Base):
    __tablename__ = "roborock_cleaning_zone_mappings"
    __table_args__ = (
        UniqueConstraint("robot_duid", "zone_id", name="uq_roborock_cleaning_zone_robot_zone"),
        UniqueConstraint("robot_duid", "segment_id", name="uq_roborock_cleaning_zone_robot_segment"),
    )

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, nullable=False, index=True)
    zone_id = Column(Integer, ForeignKey("cleaning_zones.id"), nullable=False, index=True)
    segment_id = Column(String, nullable=False)
    source_schedule_id = Column(String, nullable=True)
    source_cron = Column(String, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    imported_by = Column(String, nullable=True)


class RoborockCleaningProfile(Base):
    __tablename__ = "roborock_cleaning_profiles"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    cleaning_type = Column(String, nullable=False, index=True)
    fan_power = Column(Integer, nullable=False)
    water_box_mode = Column(Integer, nullable=False)
    mop_mode = Column(Integer, nullable=False)
    repeat = Column(Integer, nullable=False, default=1)
    active = Column(Boolean, nullable=False, default=True, index=True)
    builtin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class RoborockDoorAutomation(Base):
    __tablename__ = "roborock_door_automations"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, nullable=False, unique=True, index=True)
    door_device_id = Column(Integer, nullable=False, default=545, index=True)
    enabled = Column(Boolean, nullable=False, default=False, index=True)
    opening_threshold = Column(Integer, nullable=False, default=10)
    minimum_interval_minutes = Column(Integer, nullable=False, default=60)
    zone_numbers = Column(JSON, nullable=False, default=list)
    profile_id = Column(Integer, ForeignKey("roborock_cleaning_profiles.id"), nullable=False, index=True)
    counter_reset_at = Column(DateTime, nullable=True, index=True)
    last_attempt_at = Column(DateTime, nullable=True, index=True)
    last_started_at = Column(DateTime, nullable=True, index=True)
    last_request_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="disabled", index=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=local_now_naive, nullable=False)
    updated_at = Column(DateTime, default=local_now_naive, nullable=False, index=True)


class RoborockConsumableSnapshot(Base):
    __tablename__ = "roborock_consumables"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    main_brush_work_time = Column(Integer, nullable=True)
    side_brush_work_time = Column(Integer, nullable=True)
    filter_work_time = Column(Integer, nullable=True)
    sensor_dirty_time = Column(Integer, nullable=True)
    dust_collection_work_times = Column(Integer, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockMapSnapshot(Base):
    __tablename__ = "roborock_maps"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    image_bytes = Column(Integer, nullable=True)
    raw_bytes = Column(Integer, nullable=True)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    rooms = Column(Integer, nullable=True)
    zones = Column(Integer, nullable=True)
    charger = Column(JSON, nullable=True)
    vacuum_position = Column(JSON, nullable=True)
    image_base64 = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockProbeResult(Base):
    __tablename__ = "roborock_probe_results"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, index=True, nullable=True)
    command = Column(String, index=True, nullable=True)
    ok = Column(Boolean, nullable=True)
    error = Column(Text, nullable=True)
    result_type = Column(String, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockSyncRun(Base):
    __tablename__ = "roborock_sync_runs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    collector_id = Column(String, index=True, nullable=True)
    source = Column(String, nullable=True)
    ok = Column(Boolean, nullable=True)
    robots_count = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockCommandRun(Base):
    __tablename__ = "roborock_command_runs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True, nullable=False)
    robot_duid = Column(String, index=True, nullable=False)
    action = Column(String, index=True, nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow, index=True)
    finished_at = Column(DateTime, nullable=True, index=True)
    requested_by = Column(String, nullable=True)
    status = Column(String, index=True, nullable=False, default="running")
    message = Column(Text, nullable=True)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
