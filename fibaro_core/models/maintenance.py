"""Maintenance models."""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from fibaro_core.database import Base
from time_formatting import local_now_naive


class SiteVisit(Base):
    __tablename__ = "site_visits"
    __table_args__ = (UniqueConstraint("source", "source_visit_id", name="uq_site_visits_source_visit"),)

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False, default="owntracks", index=True)
    source_visit_id = Column(String, nullable=False, index=True)
    location_key = Column(String, nullable=False, index=True)
    location_name = Column(String, nullable=False, index=True)
    topic = Column(String, nullable=True, index=True)
    username = Column(String, nullable=True, index=True)
    device = Column(String, nullable=True, index=True)
    started_at = Column(DateTime, nullable=False, index=True)
    ended_at = Column(DateTime, nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="open", index=True)
    confidence = Column(Float, nullable=True)
    enter_source = Column(String, nullable=True)
    leave_source = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)
    last_synced_at = Column(DateTime, default=local_now_naive, nullable=False, index=True)
    created_at = Column(DateTime, default=local_now_naive, nullable=False, index=True)
    updated_at = Column(DateTime, default=local_now_naive, nullable=False)


class MaintenanceLogEntry(Base):
    __tablename__ = "maintenance_log_entries"

    id = Column(Integer, primary_key=True, index=True)
    site_visit_id = Column(Integer, ForeignKey("site_visits.id", ondelete="SET NULL"), nullable=True, index=True)
    performed_at = Column(DateTime, default=local_now_naive, nullable=False, index=True)
    performed_by = Column(String, nullable=True, index=True)
    presence_type = Column(String, nullable=True, index=True)
    target_type = Column(String, nullable=True, index=True)
    room_id = Column(String, nullable=True, index=True)
    target_name = Column(String, nullable=True, index=True)
    action_type = Column(String, nullable=True, index=True)
    priority = Column(String, nullable=True, index=True)
    summary = Column(Text, nullable=False)
    tags = Column(JSON, nullable=True)
    status = Column(String, default="Utført", nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=True)
    follow_up_needed = Column(Boolean, default=False, index=True)
    follow_up_text = Column(Text, nullable=True)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=local_now_naive, nullable=False, index=True)
    updated_at = Column(DateTime, default=local_now_naive, nullable=False)
