"""Building models."""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text
from fibaro_core.database import Base
from time_formatting import local_now_naive


class OutdoorLightEvent(Base):
    __tablename__ = "utelys_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True, default="device_change")
    action = Column(String, index=True, nullable=True)
    device_key = Column(String, index=True, nullable=True)
    device_id = Column(Integer, index=True, nullable=True)
    device_name = Column(String, nullable=True)
    mode = Column(String, index=True, nullable=True)
    reason = Column(Text, nullable=True)
    source = Column(Text, nullable=True)
    lux = Column(Float, nullable=True)
    value = Column(Float, nullable=True)
    state = Column(Boolean, nullable=True)
    extra = Column(JSON, nullable=True)


class OutdoorLightSample(Base):
    __tablename__ = "utelys_samples"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    bucket_start = Column(DateTime, index=True, nullable=False)
    mode = Column(String, index=True, nullable=True)
    source = Column(Text, nullable=True)
    lux = Column(Float, nullable=True)
    value = Column(Float, nullable=True)
    light_lyslist = Column(Boolean, nullable=True)
    light_reklame = Column(Boolean, nullable=True)
    light_spot_glass_275 = Column(Boolean, nullable=True)
    light_spot_glass_299 = Column(Boolean, nullable=True)
    light_spot_inngang = Column(Boolean, nullable=True)
    light_parkering = Column(Boolean, nullable=True)
    weather_symbol = Column(String, nullable=True)
    weather_text = Column(String, nullable=True)
    extra = Column(JSON, nullable=True)


class VentilationEvent(Base):
    __tablename__ = "ventilasjon_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True, default="fan_change")
    action = Column(String, index=True, nullable=True)
    device_key = Column(String, index=True, nullable=True)
    device_id = Column(Integer, index=True, nullable=True)
    device_name = Column(String, nullable=True)
    mode = Column(String, index=True, nullable=True)
    reason = Column(Text, nullable=True)
    source = Column(Text, nullable=True)
    value = Column(Float, nullable=True)
    state = Column(Boolean, nullable=True)

    temp_1etg = Column(Float, nullable=True)
    temp_2etg = Column(Float, nullable=True)
    temp_vip = Column(Float, nullable=True)
    temp_ute = Column(Float, nullable=True)
    temp_loft = Column(Float, nullable=True)
    humidity_1etg = Column(Float, nullable=True)
    humidity_2etg = Column(Float, nullable=True)
    humidity_vip = Column(Float, nullable=True)
    humidity_ute = Column(Float, nullable=True)
    humidity_yr = Column(Float, nullable=True)
    humidity_loft = Column(Float, nullable=True)
    temp_kjeller = Column(Float, nullable=True)
    humidity_kjeller = Column(Float, nullable=True)
    temp_passiv = Column(Float, nullable=True)
    temp_luftinntak = Column(Float, nullable=True)
    humidity_passiv = Column(Float, nullable=True)
    humidity_luftinntak = Column(Float, nullable=True)
    diff_w = Column(Float, nullable=True)
    power_w = Column(Float, nullable=True)
    energy_kwh = Column(Float, nullable=True)

    fan_vip = Column(Boolean, nullable=True)
    fan_2etg = Column(Boolean, nullable=True)
    fan_tak = Column(Boolean, nullable=True)
    fan_avfukter = Column(Boolean, nullable=True)
    extra = Column(JSON, nullable=True)


class VentilationSample(Base):
    __tablename__ = "ventilasjon_samples"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    bucket_start = Column(DateTime, index=True, nullable=False)
    mode = Column(String, index=True, nullable=True)
    source = Column(Text, nullable=True)

    temp_1etg = Column(Float, nullable=True)
    temp_2etg = Column(Float, nullable=True)
    temp_vip = Column(Float, nullable=True)
    temp_ute = Column(Float, nullable=True)
    temp_ute_netatmo = Column(Float, nullable=True)
    temp_yr = Column(Float, nullable=True)
    temp_loft = Column(Float, nullable=True)
    humidity_1etg = Column(Float, nullable=True)
    humidity_2etg = Column(Float, nullable=True)
    humidity_vip = Column(Float, nullable=True)
    humidity_ute = Column(Float, nullable=True)
    humidity_yr = Column(Float, nullable=True)
    humidity_loft = Column(Float, nullable=True)
    temp_kjeller = Column(Float, nullable=True)
    humidity_kjeller = Column(Float, nullable=True)
    temp_passiv = Column(Float, nullable=True)
    temp_luftinntak = Column(Float, nullable=True)
    humidity_passiv = Column(Float, nullable=True)
    humidity_luftinntak = Column(Float, nullable=True)
    temp_min_inne = Column(Float, nullable=True)
    temp_avg_inne = Column(Float, nullable=True)
    temp_max_inne = Column(Float, nullable=True)

    diff_w = Column(Float, nullable=True)
    estimated_sunbeds = Column(Integer, nullable=True)
    afterrun_active = Column(Boolean, nullable=True)
    heat_need = Column(Boolean, nullable=True)
    cool_need = Column(Boolean, nullable=True)
    open_time = Column(Boolean, nullable=True)
    pre_cooling = Column(Boolean, nullable=True)
    exhaust_time_allowed = Column(Boolean, nullable=True)

    fan_vip = Column(Boolean, nullable=True)
    fan_2etg = Column(Boolean, nullable=True)
    fan_tak = Column(Boolean, nullable=True)
    fan_avfukter = Column(Boolean, nullable=True)
    extra = Column(JSON, nullable=True)


class YrForecastSample(Base):
    __tablename__ = "yr_forecast_samples"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    bucket_start = Column(DateTime, index=True, nullable=False)
    source = Column(Text, nullable=True)
    api_updated_at = Column(DateTime, nullable=True)
    last_modified = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, index=True, nullable=True)
    next_fetch_after = Column(DateTime, nullable=True)
    age_seconds = Column(Integer, nullable=True)
    forecast_time = Column(DateTime, nullable=True)
    symbol_code = Column(String, nullable=True)
    weather_text = Column(String, nullable=True)
    air_temperature = Column(Float, nullable=True)
    air_temperature_percentile_10 = Column(Float, nullable=True)
    air_temperature_percentile_90 = Column(Float, nullable=True)
    relative_humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    wind_speed_of_gust = Column(Float, nullable=True)
    wind_speed_percentile_10 = Column(Float, nullable=True)
    wind_speed_percentile_90 = Column(Float, nullable=True)
    wind_from_direction = Column(Float, nullable=True)
    cloud_area_fraction = Column(Float, nullable=True)
    cloud_area_fraction_high = Column(Float, nullable=True)
    cloud_area_fraction_medium = Column(Float, nullable=True)
    cloud_area_fraction_low = Column(Float, nullable=True)
    fog_area_fraction = Column(Float, nullable=True)
    dew_point_temperature = Column(Float, nullable=True)
    air_pressure_at_sea_level = Column(Float, nullable=True)
    ultraviolet_index_clear_sky = Column(Float, nullable=True)
    precipitation_next_1h = Column(Float, nullable=True)
    precipitation_next_1h_min = Column(Float, nullable=True)
    precipitation_next_1h_max = Column(Float, nullable=True)
    precipitation_next_6h = Column(Float, nullable=True)
    precipitation_next_6h_min = Column(Float, nullable=True)
    precipitation_next_6h_max = Column(Float, nullable=True)
    probability_of_precipitation_next_1h = Column(Float, nullable=True)
    probability_of_precipitation_next_6h = Column(Float, nullable=True)
    probability_of_precipitation_next_12h = Column(Float, nullable=True)
    probability_of_thunder_next_1h = Column(Float, nullable=True)
    air_temperature_min_next_6h = Column(Float, nullable=True)
    air_temperature_max_next_6h = Column(Float, nullable=True)
    symbol_confidence_next_12h = Column(String, nullable=True)
    temp_1h = Column(Float, nullable=True)
    temp_3h = Column(Float, nullable=True)
    temp_6h = Column(Float, nullable=True)
    temp_12h = Column(Float, nullable=True)
    temp_24h = Column(Float, nullable=True)
    symbol_1h = Column(String, nullable=True)
    symbol_3h = Column(String, nullable=True)
    symbol_6h = Column(String, nullable=True)
    symbol_12h = Column(String, nullable=True)
    symbol_24h = Column(String, nullable=True)
    temp_min_next_6h = Column(Float, nullable=True)
    temp_max_next_6h = Column(Float, nullable=True)
    extra = Column(JSON, nullable=True)
    raw = Column(JSON, nullable=True)


class GenericEvent(Base):
    __tablename__ = "event_data"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    system = Column(String, index=True, nullable=False)
    event_type = Column(String, index=True, default="status")
    action = Column(String, index=True, nullable=True)
    device_key = Column(String, index=True, nullable=True)
    device_id = Column(Integer, index=True, nullable=True)
    device_name = Column(String, nullable=True)
    mode = Column(String, index=True, nullable=True)
    reason = Column(Text, nullable=True)
    source = Column(Text, nullable=True)
    lux = Column(Float, nullable=True)
    value = Column(Float, nullable=True)
    state = Column(Boolean, nullable=True)
    extra = Column(JSON, nullable=True)


class DoorEvent(Base):
    __tablename__ = "door_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=local_now_naive, index=True)
    event_type = Column(String, index=True, default="door_change")
    action = Column(String, index=True, nullable=False)
    device_key = Column(String, index=True, nullable=True)
    device_id = Column(Integer, index=True, nullable=True)
    device_name = Column(String, nullable=True)
    source = Column(Text, nullable=True)
    raw_value = Column(String, nullable=True)
    state = Column(Boolean, index=True, nullable=True)
    previous_state = Column(Boolean, nullable=True)
    battery_level = Column(Float, nullable=True)
    extra = Column(JSON, nullable=True)


class DoorSensorStatus(Base):
    __tablename__ = "door_sensor_status"

    device_id = Column(Integer, primary_key=True)
    device_key = Column(String, index=True, nullable=True)
    device_name = Column(String, nullable=True)
    state = Column(Boolean, index=True, nullable=True)
    raw_value = Column(String, nullable=True)
    battery_level = Column(Float, nullable=True)
    hc3_dead = Column(Boolean, nullable=True)
    hc3_enabled = Column(Boolean, nullable=True)
    observed_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)
    last_changed_at = Column(DateTime, index=True, nullable=True)
    last_change_event_id = Column(Integer, nullable=True)
    source = Column(String, index=True, nullable=True)
    extra = Column(JSON, nullable=True)
    created_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)
    updated_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)


class AlarmEvent(Base):
    __tablename__ = "alarm_events"

    id = Column(Integer, primary_key=True, index=True)
    event_key = Column(String, unique=True, index=True, nullable=False)
    domain = Column(String, index=True, nullable=False, default="doors")
    alarm_type = Column(String, index=True, nullable=False)
    status = Column(String, index=True, nullable=False, default="active")
    severity = Column(String, index=True, nullable=False, default="alert")
    outcome = Column(String, index=True, nullable=False, default="unreviewed")
    title = Column(String, nullable=False)
    detail = Column(Text, nullable=True)
    device_key = Column(String, index=True, nullable=True)
    device_id = Column(Integer, index=True, nullable=True)
    room_id = Column(String, index=True, nullable=True)
    display_room_number = Column(Integer, index=True, nullable=True)
    physical_room_number = Column(Integer, index=True, nullable=True)
    sun2_bed_id = Column(String, index=True, nullable=True)
    source_session_id = Column(String, index=True, nullable=True)
    door_changed_at = Column(DateTime, index=True, nullable=True)
    expected_exit_at = Column(DateTime, nullable=True)
    detected_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)
    last_observed_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)
    resolved_at = Column(DateTime, index=True, nullable=True)
    resolution_reason = Column(String, nullable=True)
    notification_status = Column(String, index=True, nullable=False, default="pending")
    notification_count = Column(Integer, nullable=False, default=0)
    first_notification_at = Column(DateTime, nullable=True)
    last_notification_at = Column(DateTime, index=True, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)
    review_note = Column(Text, nullable=True)
    source = Column(String, index=True, nullable=False, default="sunroom_door_monitor")
    created_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)
    updated_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)
    raw = Column(JSON, nullable=True)


class ControlConfig(Base):
    __tablename__ = "control_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    values = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_by = Column(String, nullable=True)


class ControlConfigHistory(Base):
    __tablename__ = "control_config_history"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String, index=True, nullable=False)
    version = Column(Integer, nullable=False)
    values = Column(JSON, nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, index=True)
    changed_by = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
