"""Linking models."""

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, Integer, JSON, String, Text, UniqueConstraint
from fibaro_core.database import Base


class ParkingSunLinkJobState(Base):
    __tablename__ = "parking_sun_link_job_state"

    id = Column(Integer, primary_key=True, default=1)
    enabled = Column(Boolean, nullable=False, default=False)
    generation = Column(Integer, nullable=False, default=1)
    min_matches = Column(Integer, nullable=False, default=2)
    max_minutes = Column(Integer, nullable=False, default=3)
    recent_days = Column(Integer, nullable=False, default=0)
    idle_sleep_seconds = Column(Integer, nullable=False, default=20)
    status = Column(String, index=True, nullable=False, default="stoppet")
    status_text = Column(Text, nullable=True)
    processed_count = Column(Integer, nullable=False, default=0)
    matched_count = Column(Integer, nullable=False, default=0)
    candidate_count = Column(Integer, nullable=False, default=0)
    strong_candidate_count = Column(Integer, nullable=False, default=0)
    checked_plate_count = Column(Integer, nullable=False, default=0)
    last_processed_parking_id = Column(BigInteger, nullable=True)
    last_processed_plate = Column(Text, nullable=True)
    last_processed_at = Column(DateTime, nullable=True, index=True)
    last_worker_seen_at = Column(DateTime, nullable=True, index=True)
    last_started_at = Column(DateTime, nullable=True, index=True)
    last_finished_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    raw = Column(JSON, nullable=True)


class ParkingSunLinkProcessed(Base):
    __tablename__ = "parking_sun_link_processed"
    __table_args__ = (
        UniqueConstraint("generation", "parking_record_id", name="uq_parking_sun_link_processed_generation_parking"),
    )

    id = Column(Integer, primary_key=True, index=True)
    generation = Column(Integer, index=True, nullable=False)
    parking_record_id = Column(BigInteger, index=True, nullable=False)
    plate = Column(Text, index=True, nullable=False)
    parking_start_at = Column(DateTime, nullable=True, index=True)
    matches_found = Column(Integer, nullable=False, default=0)
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class ParkingSunLinkMatch(Base):
    __tablename__ = "parking_sun_link_matches"
    __table_args__ = (
        UniqueConstraint("generation", "parking_record_id", "sun_session_id", name="uq_parking_sun_link_match_pair"),
    )

    id = Column(Integer, primary_key=True, index=True)
    generation = Column(Integer, index=True, nullable=False)
    plate = Column(Text, index=True, nullable=False)
    sun2_id = Column(Text, index=True, nullable=False)
    parking_record_id = Column(BigInteger, index=True, nullable=False)
    parking_id = Column(BigInteger, nullable=True)
    source_system = Column(Text, nullable=True)
    parking_start_at = Column(DateTime, nullable=True, index=True)
    sun_session_id = Column(Integer, index=True, nullable=False)
    source_session_id = Column(String, nullable=True)
    sun_started_at = Column(DateTime, nullable=True, index=True)
    room_id = Column(String, nullable=True)
    room = Column(String, nullable=True)
    user_name = Column(String, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    paid_amount_kr = Column(Float, nullable=True)
    fee_inc_vat = Column(Float, nullable=True)
    delta_minutes = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class ParkingSunLinkCandidate(Base):
    __tablename__ = "parking_sun_link_candidates"
    __table_args__ = (
        UniqueConstraint("generation", "plate", "sun2_id", name="uq_parking_sun_link_candidate_pair"),
    )

    id = Column(Integer, primary_key=True, index=True)
    generation = Column(Integer, index=True, nullable=False)
    plate = Column(Text, index=True, nullable=False)
    sun2_id = Column(Text, index=True, nullable=False)
    status = Column(String, index=True, nullable=False, default="Avventer")
    confidence = Column(Float, nullable=False, default=0.0)
    matches_count = Column(Integer, nullable=False, default=0)
    parking_match_count = Column(Integer, nullable=False, default=0)
    match_days_count = Column(Integer, nullable=False, default=0)
    plate_candidate_count = Column(Integer, nullable=False, default=1)
    sun2_candidate_count = Column(Integer, nullable=False, default=1)
    competitor_matches_count = Column(Integer, nullable=False, default=0)
    assessment = Column(Text, nullable=True)
    first_match_at = Column(DateTime, nullable=True, index=True)
    last_match_at = Column(DateTime, nullable=True, index=True)
    avg_delta_minutes = Column(Float, nullable=True)
    navn = Column(Text, nullable=True)
    omrade = Column(Text, nullable=True)
    user_name = Column(String, nullable=True)
    parking_count = Column(BigInteger, nullable=True)
    paid_total = Column(Float, nullable=True)
    matched_paid_total = Column(Float, nullable=True)
    note = Column(Text, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by = Column(String, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejected_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
