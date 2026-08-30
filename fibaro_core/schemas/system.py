"""System schemas."""

from datetime import date, datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AssetRegistryInput(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    category: str = Field(default="Annet", min_length=2, max_length=80)
    location: Optional[str] = Field(default=None, max_length=160)
    manufacturer: Optional[str] = Field(default=None, max_length=120)
    model: Optional[str] = Field(default=None, max_length=160)
    serial_no: Optional[str] = Field(default=None, max_length=160)
    hc3_device_id: Optional[int] = Field(default=None, ge=1)
    owner_app: Optional[str] = Field(default=None, max_length=80)
    status: str = Field(default="I drift", min_length=2, max_length=60)
    installed_at: Optional[date] = None
    warranty_until: Optional[date] = None
    service_interval_days: Optional[int] = Field(default=None, ge=1, le=3650)
    last_service_at: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=4000)


class AutomationWorkbenchInput(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    domain: str = Field(default="Drift", min_length=2, max_length=80)
    description: Optional[str] = Field(default=None, max_length=4000)
    trigger_type: str = Field(default="Hendelse", min_length=2, max_length=80)
    trigger: Optional[str] = Field(default=None, max_length=2000)
    conditions: Optional[str] = Field(default=None, max_length=4000)
    actions: Optional[str] = Field(default=None, max_length=4000)
    mode: str = Field(default="Utkast", min_length=2, max_length=40)
    enabled: bool = False
    cooldown_minutes: int = Field(default=0, ge=0, le=10080)


class ImportStatusReportIn(BaseModel):
    job_name: str
    title: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    ok: Optional[bool] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    next_expected_at: Optional[datetime] = None
    expected_interval_minutes: Optional[int] = None
    warning_after_minutes: Optional[int] = None
    records_imported: Optional[int] = None
    records_total: Optional[int] = None
    duration_seconds: Optional[float] = None
    message: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class V2AccessUserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=5, max_length=240)
    role: str = "viewer"


class V2AccessUserUpdate(BaseModel):
    role: Optional[str] = None
    active: Optional[bool] = None
    password: Optional[str] = Field(None, max_length=240)
