"""System models."""

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Float, Integer, JSON, String, Text
from fibaro_core.database import Base
from time_formatting import local_now_naive


class OperationalIncidentReview(Base):
    __tablename__ = "operational_incident_reviews"

    id = Column(Integer, primary_key=True, index=True)
    incident_key = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, index=True, nullable=False, default="acknowledged")
    note = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)
    reviewed_by = Column(String, nullable=True)
    created_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)
    updated_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)


class AssetRegistryItem(Base):
    __tablename__ = "asset_registry_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False, default="Annet")
    location = Column(String, index=True, nullable=True)
    manufacturer = Column(String, nullable=True)
    model = Column(String, nullable=True)
    serial_no = Column(String, index=True, nullable=True)
    hc3_device_id = Column(Integer, index=True, nullable=True)
    owner_app = Column(String, index=True, nullable=True)
    status = Column(String, index=True, nullable=False, default="I drift")
    installed_at = Column(Date, nullable=True)
    warranty_until = Column(Date, index=True, nullable=True)
    service_interval_days = Column(Integer, nullable=True)
    last_service_at = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    extra = Column(JSON, nullable=True)
    created_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)
    updated_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)


class AutomationWorkbenchRule(Base):
    __tablename__ = "automation_workbench_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    domain = Column(String, index=True, nullable=False, default="Drift")
    description = Column(Text, nullable=True)
    trigger_type = Column(String, index=True, nullable=False, default="Hendelse")
    trigger_config = Column(JSON, nullable=True)
    conditions = Column(JSON, nullable=True)
    actions = Column(JSON, nullable=True)
    mode = Column(String, index=True, nullable=False, default="Utkast")
    enabled = Column(Boolean, index=True, nullable=False, default=False)
    cooldown_minutes = Column(Integer, nullable=False, default=0)
    last_evaluated_at = Column(DateTime, nullable=True)
    last_triggered_at = Column(DateTime, nullable=True)
    last_result = Column(Text, nullable=True)
    created_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)
    updated_at = Column(DateTime, index=True, nullable=False, default=local_now_naive)


class ImportJobStatus(Base):
    __tablename__ = "import_job_status"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    category = Column(String, index=True, nullable=False)
    source = Column(String, index=True, nullable=True)
    status = Column(String, index=True, nullable=False, default="unknown")
    status_text = Column(String, nullable=True)
    last_started_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True, index=True)
    last_failed_at = Column(DateTime, nullable=True, index=True)
    last_run_at = Column(DateTime, nullable=True, index=True)
    next_expected_at = Column(DateTime, nullable=True, index=True)
    expected_interval_minutes = Column(Integer, nullable=True)
    warning_after_minutes = Column(Integer, nullable=True)
    records_imported = Column(Integer, nullable=True)
    records_total = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class ImportJobRun(Base):
    __tablename__ = "import_job_runs"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String, index=True, nullable=False)
    title = Column(String, nullable=True)
    category = Column(String, index=True, nullable=True)
    source = Column(String, index=True, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, default=datetime.utcnow, index=True)
    ok = Column(Boolean, index=True, nullable=True)
    status = Column(String, index=True, nullable=True)
    records_imported = Column(Integer, nullable=True)
    records_total = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class AiQueryLog(Base):
    __tablename__ = "ai_query_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    username = Column(String, index=True, nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    ok = Column(Boolean, index=True, nullable=True)
    error = Column(Text, nullable=True)
    tool_calls_count = Column(Integer, nullable=True)
    raw = Column(JSON, nullable=True)


class AccessKey(Base):
    __tablename__ = "access_keys"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    key_hash = Column(String, unique=True, index=True, nullable=False)
    key_prefix = Column(String, index=True, nullable=False)
    key_plaintext = Column(String, nullable=True)
    role = Column(String, default="viewer", index=True)
    is_master = Column(Boolean, default=False, index=True)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_seen_at = Column(DateTime, nullable=True)
    last_notified_at = Column(DateTime, nullable=True)
    last_ip = Column(String, nullable=True)
    last_user_agent = Column(Text, nullable=True)
    uses_count = Column(Integer, default=0)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    access_key_id = Column(Integer, index=True, nullable=False)
    credential_hash_at_issue = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    expires_at = Column(DateTime, index=True, nullable=False)
    last_seen_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, index=True, nullable=True)
    created_ip = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"

    id = Column(BigInteger, primary_key=True, index=True)
    topic = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    tags = Column(Text, nullable=True)
    priority = Column(String, nullable=False, default="3")
    click_url = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    locked_at = Column(DateTime, nullable=True, index=True)
    sent_at = Column(DateTime, nullable=True, index=True)
    last_error = Column(Text, nullable=True)
    related_type = Column(String, nullable=True, index=True)
    related_id = Column(BigInteger, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    access_key_id = Column(Integer, nullable=True, index=True)
    key_name = Column(String, nullable=True)
    key_prefix = Column(String, nullable=True, index=True)
    path = Column(Text, nullable=False)
    method = Column(String, nullable=False)
    ip = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, default=True, index=True)
    reason = Column(String, nullable=True)
