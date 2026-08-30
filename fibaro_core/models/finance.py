"""Finance models."""

from datetime import datetime
from sqlalchemy import Column, Date, DateTime, Float, Integer, JSON, LargeBinary, String, Text, UniqueConstraint
from fibaro_core.database import Base


class SettlementImport(Base):
    __tablename__ = "settlement_imports"
    __table_args__ = (
        UniqueConstraint("provider", "gmail_message_id", "attachment_sha256", name="uq_settlement_provider_message_attachment"),
    )

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, index=True, nullable=False)
    source = Column(String, index=True, nullable=False, default="gmail")
    sender = Column(String, index=True, nullable=True)
    gmail_message_id = Column(Text, nullable=True)
    gmail_uid = Column(String, nullable=True)
    email_subject = Column(Text, nullable=True)
    email_date = Column(DateTime, index=True, nullable=True)
    mailbox = Column(String, nullable=True)
    period_start = Column(Date, index=True, nullable=True)
    period_end = Column(Date, index=True, nullable=True)
    period_label = Column(String, index=True, nullable=True)
    attachment_filename = Column(Text, nullable=True)
    attachment_content_type = Column(String, nullable=True)
    attachment_sha256 = Column(String, index=True, nullable=False)
    attachment_size = Column(Integer, nullable=True)
    attachment_bytes = Column(LargeBinary, nullable=False)
    status = Column(String, index=True, nullable=False, default="imported")
    parsed = Column(JSON, nullable=True)
    raw = Column(JSON, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class ForecastSnapshot(Base):
    __tablename__ = "forecast_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    domain = Column(String, nullable=False, index=True)
    period_type = Column(String, nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    generated_at = Column(DateTime, nullable=True)
    created_by = Column(String, nullable=True)

    forecast_sessions = Column(Float, nullable=True)
    forecast_paid = Column(Float, nullable=True)
    forecast_minutes = Column(Float, nullable=True)
    forecast_vehicles = Column(Float, nullable=True)

    actual_sessions_at_save = Column(Float, nullable=True)
    actual_paid_at_save = Column(Float, nullable=True)
    actual_minutes_at_save = Column(Float, nullable=True)
    actual_vehicles_at_save = Column(Float, nullable=True)

    model_sessions = Column(Float, nullable=True)
    day_fraction = Column(Float, nullable=True)
    tempo = Column(Float, nullable=True)
    raw = Column(JSON, nullable=True)
