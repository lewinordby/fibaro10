"""Sun models."""

from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, LargeBinary, String, Text, UniqueConstraint
from fibaro_core.database import Base
from fibaro_core.config import SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS


class Sun2RoomDailyStat(Base):
    __tablename__ = "sun2_room_daily_stats"
    __table_args__ = (UniqueConstraint("stat_date", "room", name="uq_sun2_room_daily_stats_date_room"),)

    id = Column(Integer, primary_key=True, index=True)
    stat_date = Column(Date, index=True, nullable=False)
    room_id = Column(String, index=True, nullable=True)
    room_key = Column(String, index=True, nullable=True)
    room = Column(String, index=True, nullable=False)
    source_room_name = Column(String, nullable=True)
    sun2_bed_id = Column(String, index=True, nullable=True)
    total_soletid_minutter = Column(Float, nullable=True)
    totalt_antall_solinger = Column(Integer, nullable=True)
    solinger_medlemmer = Column(Integer, nullable=True)
    solinger_ikke_medlemmer = Column(Integer, nullable=True)
    totalt_inntjent_kr = Column(Float, nullable=True)
    inntjent_medlemmer_kr = Column(Float, nullable=True)
    inntjent_ikke_medlemmer_kr = Column(Float, nullable=True)
    source = Column(String, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class Sun2ImportRun(Base):
    __tablename__ = "sun2_import_runs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    collector_id = Column(String, index=True, nullable=True)
    source = Column(String, nullable=True)
    ok = Column(Boolean, nullable=True)
    stat_date = Column(Date, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    rows_count = Column(Integer, nullable=True)
    inserted_count = Column(Integer, nullable=True)
    updated_count = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class Sun2TanningSession(Base):
    __tablename__ = "sun2_tanning_sessions"
    __table_args__ = (
        UniqueConstraint("source", "source_session_id", name="uq_sun2_session_source_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_session_id = Column(String, index=True, nullable=False)
    started_at = Column(DateTime, index=True, nullable=False)
    ended_at = Column(DateTime, index=True, nullable=True)
    stat_date = Column(Date, index=True, nullable=False)
    room_id = Column(String, index=True, nullable=True)
    room_key = Column(String, index=True, nullable=True)
    room = Column(String, index=True, nullable=True)
    source_room_name = Column(String, nullable=True)
    sun2_user_id = Column(String, index=True, nullable=True)
    sun2_center_id = Column(String, index=True, nullable=True)
    sun2_bed_id = Column(String, index=True, nullable=True)
    user_name = Column(String, index=True, nullable=True)
    user_identifier = Column(String, index=True, nullable=True)
    customer_type = Column(String, index=True, nullable=True)
    gender = Column(String, index=True, nullable=True)
    payment_method = Column(String, index=True, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    paid_amount_kr = Column(Float, nullable=True)
    status = Column(String, index=True, nullable=True)
    source = Column(String, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class Sun2TanningSessionImage(Base):
    __tablename__ = "sun2_tanning_session_images"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sun2_tanning_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    captured_at = Column(DateTime, index=True, nullable=False)
    target_at = Column(DateTime, index=True, nullable=False)
    offset_seconds = Column(Integer, nullable=False, default=-SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS)
    is_primary = Column(Boolean, nullable=False, default=False)
    delta_seconds = Column(Float, nullable=True)
    source_path = Column(Text, nullable=True)
    source_mtime = Column(DateTime, nullable=True)
    content_type = Column(String, default="image/jpeg", nullable=False)
    image_bytes = Column(LargeBinary, nullable=False)
    byte_size = Column(Integer, nullable=True)
    sha256 = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, index=True, default="axis_snapshot_backfill")


class Sun2Bed(Base):
    __tablename__ = "sun2_beds"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, index=True, nullable=True)
    physical_room_number = Column(Integer, index=True, nullable=True)
    display_room_number = Column(Integer, index=True, nullable=True)
    sun2_center_id = Column(String, index=True, nullable=True)
    sun2_bed_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    source_room_name = Column(String, nullable=True)
    bed_model = Column(String, index=True, nullable=True)
    bed_model_id = Column(String, index=True, nullable=True)
    max_minutes = Column(Float, nullable=True)
    startup_minutes = Column(Float, nullable=True)
    cooldown_minutes = Column(Float, nullable=True)
    current_price_per_min = Column(Float, nullable=True)
    status = Column(String, index=True, nullable=True)
    status_code = Column(String, index=True, nullable=True)
    lamp_status = Column(Text, nullable=True)
    source = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class Sun2Member(Base):
    __tablename__ = "sun2_members"

    id = Column(Integer, primary_key=True, index=True)
    sun2_user_id = Column(String, unique=True, index=True, nullable=False)
    sun2_center_id = Column(String, index=True, nullable=True)
    name = Column(String, index=True, nullable=True)
    display_name = Column(String, index=True, nullable=True)
    initials = Column(String, index=True, nullable=True)
    age = Column(Integer, index=True, nullable=True)
    email = Column(String, index=True, nullable=True)
    phone = Column(String, index=True, nullable=True)
    profile_url = Column(Text, nullable=True)
    customer_type = Column(String, index=True, nullable=True)
    gender = Column(String, index=True, nullable=True)
    birth_date = Column(Date, index=True, nullable=True)
    member_since = Column(Date, index=True, nullable=True)
    last_seen_at = Column(DateTime, index=True, nullable=True)
    status = Column(String, index=True, nullable=True)
    balance_kr = Column(Float, nullable=True)
    total_spent_kr = Column(Float, nullable=True)
    visits_count = Column(Integer, nullable=True)
    source = Column(String, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class Sun2ProductSale(Base):
    __tablename__ = "sun2_product_sales"
    __table_args__ = (
        UniqueConstraint("source", "source_sale_id", name="uq_sun2_product_sale_source_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_sale_id = Column(String, index=True, nullable=False)
    sold_at = Column(DateTime, index=True, nullable=True)
    stat_date = Column(Date, index=True, nullable=False)
    period_start = Column(Date, index=True, nullable=True)
    period_end = Column(Date, index=True, nullable=True)
    product_name = Column(String, index=True, nullable=True)
    product_category = Column(String, index=True, nullable=True)
    quantity = Column(Float, nullable=True)
    unit_price_kr = Column(Float, nullable=True)
    amount_inc_vat_kr = Column(Float, nullable=True)
    amount_ex_vat_kr = Column(Float, nullable=True)
    vat_kr = Column(Float, nullable=True)
    payment_method = Column(String, index=True, nullable=True)
    sun2_user_id = Column(String, index=True, nullable=True)
    user_name = Column(String, index=True, nullable=True)
    source = Column(String, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class Sun2FinanceSettlement(Base):
    __tablename__ = "sun2_finance_settlements"
    __table_args__ = (
        UniqueConstraint("source", "source_payout_id", name="uq_sun2_finance_settlement_source_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_payout_id = Column(String, index=True, nullable=False)
    payout_label = Column(String, index=True, nullable=True)
    period_start = Column(Date, index=True, nullable=False)
    period_end = Column(Date, index=True, nullable=False)
    payout_date = Column(Date, index=True, nullable=True)
    member_tanning_count = Column(Integer, nullable=True)
    member_tanning_inc_vat_kr = Column(Float, nullable=True)
    unregistered_tanning_count = Column(Integer, nullable=True)
    unregistered_tanning_inc_vat_kr = Column(Float, nullable=True)
    tanning_bonus_inc_vat_kr = Column(Float, nullable=True)
    tanning_control_inc_vat_kr = Column(Float, nullable=True)
    tanning_control_ex_vat_kr = Column(Float, nullable=True)
    member_product_count = Column(Integer, nullable=True)
    member_product_inc_vat_kr = Column(Float, nullable=True)
    unregistered_product_count = Column(Integer, nullable=True)
    unregistered_product_inc_vat_kr = Column(Float, nullable=True)
    product_bonus_inc_vat_kr = Column(Float, nullable=True)
    product_control_inc_vat_kr = Column(Float, nullable=True)
    product_control_ex_vat_kr = Column(Float, nullable=True)
    transaction_cost_kr = Column(Float, nullable=True)
    service_fee_kr = Column(Float, nullable=True)
    payout_inc_vat_kr = Column(Float, nullable=True)
    vat_kr = Column(Float, nullable=True)
    source = Column(String, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class Sun2SessionImportRun(Base):
    __tablename__ = "sun2_session_import_runs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    collector_id = Column(String, index=True, nullable=True)
    source = Column(String, nullable=True)
    ok = Column(Boolean, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    period_first = Column(DateTime, index=True, nullable=True)
    period_last = Column(DateTime, index=True, nullable=True)
    rows_count = Column(Integer, nullable=True)
    inserted_count = Column(Integer, nullable=True)
    updated_count = Column(Integer, nullable=True)
    skipped_count = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)
