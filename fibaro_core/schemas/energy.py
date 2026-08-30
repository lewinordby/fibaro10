"""Energy schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class Hc3MeterReadingIn(BaseModel):
    kilde: str
    status: str
    fibaroid: int
    verdi1: float
    verdi2: Optional[float] = None
    forklaring: Optional[str] = None
    ts: Optional[datetime] = None
    source: Optional[str] = "HC3"


class EnergyFibaroIn(BaseModel):
    source: str = "HC3 ENERGI"
    timestamp: Optional[datetime] = None
    bucket_start: Optional[datetime] = None

    inntak_w: Optional[float] = None
    varmepumper_w: Optional[float] = None
    belysning_w: Optional[float] = None
    massasje_w: Optional[float] = None
    annet_w: Optional[float] = None
    avfukter_w: Optional[float] = None
    differanse_fibaro_w: Optional[float] = None

    inntak_kwh: Optional[float] = None
    varmepumper_kwh: Optional[float] = None
    belysning_kwh: Optional[float] = None
    massasje_kwh: Optional[float] = None
    annet_kwh: Optional[float] = None
    avfukter_kwh: Optional[float] = None
    differanse_fibaro_kwh: Optional[float] = None

    extra: Dict[str, Any] = Field(default_factory=dict)


class V2EnergyCircuitUpdate(BaseModel):
    description: Optional[str] = None
    breaker_type: Optional[str] = None
    breaker_rating_a: Optional[float] = None
    breaker_characteristic: Optional[str] = None
    cable_spec: Optional[str] = None
    cable_length_m: Optional[float] = None
    install_method: Optional[str] = None
    terminal_ref: Optional[str] = None
    rcd_ma: Optional[float] = None
    is_sunbed: Optional[bool] = None
    status: Optional[str] = None
    note: Optional[str] = None


class V2EnergyNodeIn(BaseModel):
    name: Optional[str] = None
    circuit_no: Optional[int] = None
    parent_node_id: Optional[int] = None
    node_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    device_type: Optional[str] = None
    hc3_device_id: Optional[int] = None
    hc3_power_device_id: Optional[int] = None
    hc3_energy_device_id: Optional[int] = None
    hc3_switch_device_id: Optional[int] = None
    aggregate_group_key: Optional[str] = None
    endpoint_key: Optional[str] = None
    has_meter: Optional[bool] = None
    has_switch: Optional[bool] = None
    area: Optional[str] = None
    active: Optional[bool] = None
    note: Optional[str] = None


class V2EnergyLoadIn(BaseModel):
    name: Optional[str] = None
    load_type: Optional[str] = None
    area: Optional[str] = None
    circuit_no: Optional[int] = None
    power_profile: Optional[str] = None
    expected_power_w: Optional[float] = None
    min_power_w: Optional[float] = None
    max_power_w: Optional[float] = None
    measured_direct: Optional[bool] = None
    energy_node_id: Optional[int] = None
    fibaro_device_id: Optional[int] = None
    fibaro_meter_id: Optional[int] = None
    zwave_switch_id: Optional[int] = None
    controllable: Optional[bool] = None
    critical: Optional[bool] = None
    active: Optional[bool] = None
    note: Optional[str] = None
