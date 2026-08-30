"""Linking schemas."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ParkingSunLinkSettingsUpdate(BaseModel):
    min_matches: Optional[int] = Field(None, ge=1, le=20)
    max_minutes: Optional[int] = Field(None, ge=1, le=30)
    recent_days: Optional[int] = Field(None, ge=0, le=3650)
    idle_sleep_seconds: Optional[int] = Field(None, ge=5, le=3600)


class ParkingSunLinkCandidateUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=40)
    note: Optional[str] = Field(None, max_length=2000)


class ParkingSunLinkWorkerStatusIn(BaseModel):
    generation: int = Field(1, ge=1)
    status: str = Field("kjorer", max_length=40)
    status_text: Optional[str] = Field(None, max_length=1000)
    processed_count: Optional[int] = Field(None, ge=0)
    matched_count: Optional[int] = Field(None, ge=0)
    candidate_count: Optional[int] = Field(None, ge=0)
    strong_candidate_count: Optional[int] = Field(None, ge=0)
    checked_plate_count: Optional[int] = Field(None, ge=0)
    last_processed_parking_id: Optional[int] = None
    last_processed_plate: Optional[str] = Field(None, max_length=40)
    last_processed_at: Optional[datetime] = None
    last_error: Optional[str] = Field(None, max_length=4000)
    raw: Dict[str, Any] = Field(default_factory=dict)


class ParkingSunLinkProcessedIn(BaseModel):
    generation: int = Field(1, ge=1)
    parking_record_id: int
    plate: str = Field(..., max_length=40)
    parking_start_at: Optional[datetime] = None
    matches_found: int = Field(0, ge=0)


class ParkingSunLinkMatchIn(BaseModel):
    generation: int = Field(1, ge=1)
    plate: str = Field(..., max_length=40)
    sun2_id: str = Field(..., max_length=120)
    parking_record_id: int
    parking_id: Optional[int] = None
    source_system: Optional[str] = Field(None, max_length=240)
    parking_start_at: Optional[datetime] = None
    sun_session_id: int
    source_session_id: Optional[str] = Field(None, max_length=240)
    sun_started_at: Optional[datetime] = None
    room_id: Optional[str] = Field(None, max_length=120)
    room: Optional[str] = Field(None, max_length=240)
    user_name: Optional[str] = Field(None, max_length=500)
    duration_minutes: Optional[float] = None
    paid_amount_kr: Optional[float] = None
    fee_inc_vat: Optional[float] = None
    delta_minutes: Optional[float] = None


class ParkingSunLinkWorkerResultsIn(BaseModel):
    generation: int = Field(1, ge=1)
    processed: list[ParkingSunLinkProcessedIn] = Field(default_factory=list)
    matches: list[ParkingSunLinkMatchIn] = Field(default_factory=list)
    status: Optional[ParkingSunLinkWorkerStatusIn] = None
