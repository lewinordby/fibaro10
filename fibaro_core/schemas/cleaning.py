"""Cleaning schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RoborockIngestIn(BaseModel):
    source: str = "Roborock_logger"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    message: Optional[str] = None
    robots: list[Dict[str, Any]] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class RoborockTelemetryIn(BaseModel):
    source: str = "Roborock_logger telemetry"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    robots: list[Dict[str, Any]] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class RoborockControlIn(BaseModel):
    action: str
    test_duration_seconds: int = Field(default=5, ge=3, le=12)
    zone_number: Optional[int] = Field(default=None, ge=1, le=59)
    profile_id: Optional[int] = Field(default=None, ge=1)
    wash_mode: Optional[int] = None
    wash_interval_minutes: Optional[int] = None


class RoborockCleaningProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=300)
    cleaning_type: str
    fan_power: int
    water_box_mode: int
    mop_mode: int
    repeat: int = Field(default=1, ge=1, le=3)
    active: bool = True


class RoborockDoorAutomationIn(BaseModel):
    enabled: bool = False
    opening_threshold: int = Field(default=10, ge=1, le=100)
    minimum_interval_minutes: int = Field(default=60, ge=1, le=1440)
    zone_numbers: list[int] = Field(min_length=1, max_length=12)
    profile_id: int = Field(ge=1)
