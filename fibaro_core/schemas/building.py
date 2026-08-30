"""Building schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class LegacyLogIn(BaseModel):
    temperature: float
    humidity: float
    timestamp: datetime
    source: str


class EventDataIn(BaseModel):
    system: str
    event_type: str = "status"
    timestamp: Optional[datetime] = None
    action: Optional[str] = None
    device_key: Optional[str] = None
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    mode: Optional[str] = None
    reason: Optional[str] = None
    source: Optional[str] = None
    bucket_start: Optional[datetime] = None

    temp_1etg: Optional[float] = None
    temp_2etg: Optional[float] = None
    temp_vip: Optional[float] = None
    temp_ute: Optional[float] = None
    temp_ute_netatmo: Optional[float] = None
    temp_yr: Optional[float] = None
    temp_loft: Optional[float] = None
    humidity_1etg: Optional[float] = None
    humidity_2etg: Optional[float] = None
    humidity_vip: Optional[float] = None
    humidity_ute: Optional[float] = None
    humidity_yr: Optional[float] = None
    humidity_loft: Optional[float] = None
    temp_kjeller: Optional[float] = None
    humidity_kjeller: Optional[float] = None
    temp_passiv: Optional[float] = None
    temp_luftinntak: Optional[float] = None
    humidity_passiv: Optional[float] = None
    humidity_luftinntak: Optional[float] = None
    temp_min_inne: Optional[float] = None
    temp_avg_inne: Optional[float] = None
    temp_max_inne: Optional[float] = None
    lux: Optional[float] = None
    weather_type: Optional[str] = None
    weather_symbol: Optional[str] = None
    weather_text: Optional[str] = None
    yr_weather: Optional[str] = None
    yr_symbol: Optional[str] = None
    diff_w: Optional[float] = None
    power_w: Optional[float] = None
    energy_kwh: Optional[float] = None
    value: Optional[float] = None
    estimated_sunbeds: Optional[int] = None

    fan_vip: Optional[bool] = None
    fan_2etg: Optional[bool] = None
    fan_tak: Optional[bool] = None
    fan_avfukter: Optional[bool] = None
    light_lyslist: Optional[bool] = None
    light_reklame: Optional[bool] = None
    light_spot_glass_275: Optional[bool] = None
    light_spot_glass_299: Optional[bool] = None
    light_spot_inngang: Optional[bool] = None
    light_parkering: Optional[bool] = None
    afterrun_active: Optional[bool] = None
    heat_need: Optional[bool] = None
    cool_need: Optional[bool] = None
    open_time: Optional[bool] = None
    pre_cooling: Optional[bool] = None
    exhaust_time_allowed: Optional[bool] = None
    state: Optional[bool] = None

    values: Dict[str, Any] = Field(default_factory=dict)
    extra: Dict[str, Any] = Field(default_factory=dict)


class DoorEventIn(BaseModel):
    timestamp: Optional[datetime] = None
    event_type: str = "door_change"
    action: Optional[str] = None
    device_key: Optional[str] = None
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    source: Optional[str] = "HC3"
    raw_value: Optional[str] = None
    state: Optional[bool] = None
    previous_state: Optional[bool] = None
    battery_level: Optional[float] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
