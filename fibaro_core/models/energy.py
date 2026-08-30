"""Energy models."""

from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from fibaro_core.database import Base


class EnergyHourlyConsumption(Base):
    __tablename__ = "energy_hourly_consumption"
    __table_args__ = (UniqueConstraint("meter_id", "measured_at", name="uq_energy_hourly_meter_time"),)

    id = Column(Integer, primary_key=True, index=True)
    meter_id = Column(String, index=True, nullable=False)
    measured_at = Column(DateTime, index=True, nullable=False)
    stat_date = Column(Date, index=True, nullable=False)
    year = Column(Integer, index=True, nullable=False)
    month = Column(Integer, index=True, nullable=False)
    day = Column(Integer, index=True, nullable=False)
    hour = Column(Integer, index=True, nullable=False)
    consumption_kwh = Column(Float, nullable=False)
    production_kwh = Column(Float, nullable=True)
    status = Column(String, index=True, nullable=True)
    is_verified = Column(Boolean, nullable=True)
    is_estimated = Column(Boolean, index=True, nullable=True)
    is_public_holiday = Column(Boolean, nullable=True)
    use_weekend_prices = Column(Boolean, nullable=True)
    source = Column(String, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class EnergyImportRun(Base):
    __tablename__ = "energy_import_runs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    meter_id = Column(String, index=True, nullable=True)
    source = Column(String, nullable=True)
    ok = Column(Boolean, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    period_first = Column(DateTime, index=True, nullable=True)
    period_last = Column(DateTime, index=True, nullable=True)
    days_count = Column(Integer, nullable=True)
    hours_count = Column(Integer, nullable=True)
    inserted_count = Column(Integer, nullable=True)
    updated_count = Column(Integer, nullable=True)
    skipped_count = Column(Integer, nullable=True)
    total_kwh = Column(Float, nullable=True)
    estimated_hours_count = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class EnergyFibaroSample(Base):
    __tablename__ = "energy_fibaro_samples"
    __table_args__ = (UniqueConstraint("bucket_start", name="uq_energy_fibaro_bucket"),)

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    bucket_start = Column(DateTime, index=True, nullable=False)
    source = Column(String, index=True, nullable=True)

    inntak_w = Column(Float, nullable=True)
    varmepumper_w = Column(Float, nullable=True)
    belysning_w = Column(Float, nullable=True)
    massasje_w = Column(Float, nullable=True)
    annet_w = Column(Float, nullable=True)
    avfukter_w = Column(Float, nullable=True)
    differanse_fibaro_w = Column(Float, nullable=True)
    differanse_beregnet_w = Column(Float, nullable=True)

    inntak_kwh = Column(Float, nullable=True)
    varmepumper_kwh = Column(Float, nullable=True)
    belysning_kwh = Column(Float, nullable=True)
    massasje_kwh = Column(Float, nullable=True)
    annet_kwh = Column(Float, nullable=True)
    avfukter_kwh = Column(Float, nullable=True)
    differanse_fibaro_kwh = Column(Float, nullable=True)
    differanse_beregnet_kwh = Column(Float, nullable=True)

    inntak_delta_kwh = Column(Float, nullable=True)
    varmepumper_delta_kwh = Column(Float, nullable=True)
    belysning_delta_kwh = Column(Float, nullable=True)
    massasje_delta_kwh = Column(Float, nullable=True)
    annet_delta_kwh = Column(Float, nullable=True)
    avfukter_delta_kwh = Column(Float, nullable=True)
    differanse_fibaro_delta_kwh = Column(Float, nullable=True)
    differanse_beregnet_delta_kwh = Column(Float, nullable=True)

    inntak_reset = Column(Boolean, nullable=True)
    varmepumper_reset = Column(Boolean, nullable=True)
    belysning_reset = Column(Boolean, nullable=True)
    massasje_reset = Column(Boolean, nullable=True)
    annet_reset = Column(Boolean, nullable=True)
    avfukter_reset = Column(Boolean, nullable=True)
    differanse_fibaro_reset = Column(Boolean, nullable=True)

    extra = Column(JSON, nullable=True)


class EnergyCircuit(Base):
    __tablename__ = "energy_circuits"

    id = Column(Integer, primary_key=True, index=True)
    circuit_no = Column(Integer, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    breaker_type = Column(String, nullable=True)
    breaker_rating_a = Column(Float, nullable=True)
    breaker_characteristic = Column(String, nullable=True)
    cable_spec = Column(String, nullable=True)
    cable_length_m = Column(Float, nullable=True)
    install_method = Column(String, nullable=True)
    terminal_ref = Column(String, nullable=True)
    rcd_ma = Column(Float, nullable=True)
    is_sunbed = Column(Boolean, index=True, nullable=True)
    note = Column(Text, nullable=True)
    status = Column(String, index=True, nullable=True)
    source = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)


class EnergyNode(Base):
    __tablename__ = "energy_nodes"
    __table_args__ = (
        UniqueConstraint(
            "circuit_no",
            "hc3_power_device_id",
            "endpoint_key",
            name="uq_energy_node_circuit_power_endpoint",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    circuit_no = Column(Integer, index=True, nullable=True)
    parent_node_id = Column(Integer, ForeignKey("energy_nodes.id", ondelete="SET NULL"), index=True, nullable=True)
    node_type = Column(String, index=True, nullable=True)
    manufacturer = Column(String, index=True, nullable=True)
    model = Column(String, index=True, nullable=True)
    device_type = Column(String, index=True, nullable=True)
    hc3_device_id = Column(Integer, index=True, nullable=True)
    hc3_power_device_id = Column(Integer, index=True, nullable=True)
    hc3_energy_device_id = Column(Integer, index=True, nullable=True)
    hc3_switch_device_id = Column(Integer, index=True, nullable=True)
    aggregate_group_key = Column(String, index=True, nullable=True)
    endpoint_key = Column(String, index=True, nullable=True)
    has_meter = Column(Boolean, nullable=True)
    has_switch = Column(Boolean, nullable=True)
    area = Column(String, index=True, nullable=True)
    active = Column(Boolean, index=True, default=True)
    note = Column(Text, nullable=True)
    source = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)


class EnergyLoad(Base):
    __tablename__ = "energy_loads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    load_type = Column(String, index=True, nullable=True)
    area = Column(String, index=True, nullable=True)
    circuit_no = Column(Integer, index=True, nullable=True)
    power_profile = Column(String, index=True, nullable=True)
    expected_power_w = Column(Float, nullable=True)
    min_power_w = Column(Float, nullable=True)
    max_power_w = Column(Float, nullable=True)
    measured_direct = Column(Boolean, nullable=True)
    energy_node_id = Column(Integer, ForeignKey("energy_nodes.id", ondelete="SET NULL"), index=True, nullable=True)
    fibaro_device_id = Column(Integer, index=True, nullable=True)
    fibaro_meter_id = Column(Integer, index=True, nullable=True)
    zwave_switch_id = Column(Integer, index=True, nullable=True)
    controllable = Column(Boolean, nullable=True)
    critical = Column(Boolean, nullable=True)
    active = Column(Boolean, index=True, default=True)
    note = Column(Text, nullable=True)
    source = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)


class Hc3MeterReading(Base):
    __tablename__ = "hc3_meter_readings"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    kilde = Column(String, index=True, nullable=False)
    status = Column(String, index=True, nullable=False)
    fibaroid = Column(Integer, index=True, nullable=False)
    verdi1 = Column(Float, nullable=False)
    verdi2 = Column(Float, nullable=True)
    forklaring = Column(Text, nullable=True)
    source = Column(String, index=True, nullable=True)
    raw = Column(JSON, nullable=True)
