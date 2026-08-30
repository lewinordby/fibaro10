"""Maintenance schemas."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class MaintenanceLogInput(BaseModel):
    site_visit_id: Optional[int] = None
    performed_at: Optional[str] = None
    performed_by: Optional[str] = None
    presence_type: Optional[str] = None
    target_type: Optional[str] = None
    room_id: Optional[str] = None
    target_name: Optional[str] = None
    action_type: Optional[str] = None
    priority: Optional[str] = None
    summary: str = Field(..., min_length=1, max_length=4000)
    tags: Optional[Any] = None
    status: Optional[str] = None
    duration_minutes: Optional[int] = None
    follow_up_needed: Optional[bool] = None
    follow_up_text: Optional[str] = None


class MaintenanceSiteVisitInput(BaseModel):
    notes: Optional[str] = None
