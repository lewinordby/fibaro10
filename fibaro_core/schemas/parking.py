"""Parking schemas."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ParkingVehicleNameUpdate(BaseModel):
    navn: str = Field("", max_length=500)
    sun2_id: Optional[str] = Field(None, max_length=120)
    notat: Optional[str] = Field(None, max_length=2000)
    source: Optional[str] = Field(None, max_length=120)
    raw: Dict[str, Any] = Field(default_factory=dict)


class ParkingVehicleAreaUpdate(BaseModel):
    omrade: str = Field("", max_length=240)
    source: Optional[str] = Field(None, max_length=120)
    raw: Dict[str, Any] = Field(default_factory=dict)


class ParkingVehicleCarInfoUpdate(BaseModel):
    status: int = Field(0, ge=0, le=999)
    url: Optional[str] = Field(None, max_length=1000)
    error: Optional[str] = Field(None, max_length=1000)
    data: Dict[str, Any] = Field(default_factory=dict)
