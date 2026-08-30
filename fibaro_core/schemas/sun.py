"""Sun schemas."""

from datetime import date, datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class Sun2RoomStatIn(BaseModel):
    stat_date: date
    room: str
    room_id: Optional[str] = None
    room_key: Optional[str] = None
    source_room_name: Optional[str] = None
    sun2_bed_id: Optional[str] = None
    total_soletid_minutter: Optional[float] = None
    totalt_antall_solinger: Optional[int] = None
    solinger_medlemmer: Optional[int] = None
    solinger_ikke_medlemmer: Optional[int] = None
    totalt_inntjent_kr: Optional[float] = None
    inntjent_medlemmer_kr: Optional[float] = None
    inntjent_ikke_medlemmer_kr: Optional[float] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class Sun2RoomStatsIngestIn(BaseModel):
    source: str = "sun2_importer"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    stat_date: Optional[date] = None
    source_file: Optional[str] = None
    message: Optional[str] = None
    rows: list[Sun2RoomStatIn] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class Sun2TanningSessionIn(BaseModel):
    source_session_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    stat_date: Optional[date] = None
    room_id: Optional[str] = None
    room: Optional[str] = None
    room_key: Optional[str] = None
    source_room_name: Optional[str] = None
    sun2_user_id: Optional[str] = None
    sun2_center_id: Optional[str] = None
    sun2_bed_id: Optional[str] = None
    user_name: Optional[str] = None
    user_identifier: Optional[str] = None
    customer_type: Optional[str] = None
    gender: Optional[str] = None
    payment_method: Optional[str] = None
    duration_minutes: Optional[float] = None
    paid_amount_kr: Optional[float] = None
    status: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class Sun2TanningSessionsIngestIn(BaseModel):
    source: str = "sun2_session_scraper"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    source_file: Optional[str] = None
    message: Optional[str] = None
    rows: list[Sun2TanningSessionIn] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class Sun2BedIn(BaseModel):
    room_id: Optional[str] = None
    physical_room_number: Optional[int] = None
    display_room_number: Optional[int] = None
    sun2_center_id: Optional[str] = None
    sun2_bed_id: str
    name: str
    source_room_name: Optional[str] = None
    bed_model: Optional[str] = None
    bed_model_id: Optional[str] = None
    max_minutes: Optional[float] = None
    startup_minutes: Optional[float] = None
    cooldown_minutes: Optional[float] = None
    current_price_per_min: Optional[float] = None
    status: Optional[str] = None
    status_code: Optional[str] = None
    lamp_status: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class Sun2BedsIngestIn(BaseModel):
    source: str = "sun2_session_scraper"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    message: Optional[str] = None
    beds: list[Sun2BedIn] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class Sun2MemberIn(BaseModel):
    sun2_user_id: str
    sun2_center_id: Optional[str] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    initials: Optional[str] = None
    age: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    profile_url: Optional[str] = None
    customer_type: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    member_since: Optional[date] = None
    last_seen_at: Optional[datetime] = None
    status: Optional[str] = None
    balance_kr: Optional[float] = None
    total_spent_kr: Optional[float] = None
    visits_count: Optional[int] = None
    source_file: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class Sun2MembersIngestIn(BaseModel):
    source: str = "sun2_session_scraper"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    message: Optional[str] = None
    members: list[Sun2MemberIn] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class Sun2ProductSaleIn(BaseModel):
    source_sale_id: str
    sold_at: Optional[datetime] = None
    stat_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    quantity: Optional[float] = None
    unit_price_kr: Optional[float] = None
    amount_inc_vat_kr: Optional[float] = None
    amount_ex_vat_kr: Optional[float] = None
    vat_kr: Optional[float] = None
    payment_method: Optional[str] = None
    sun2_user_id: Optional[str] = None
    user_name: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class Sun2ProductSalesIngestIn(BaseModel):
    source: str = "sun2_session_scraper"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    source_file: Optional[str] = None
    message: Optional[str] = None
    rows: list[Sun2ProductSaleIn] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class Sun2FinanceSettlementIn(BaseModel):
    source_payout_id: str
    payout_label: Optional[str] = None
    period_start: date
    period_end: date
    payout_date: Optional[date] = None
    member_tanning_count: Optional[int] = None
    member_tanning_inc_vat_kr: Optional[float] = None
    unregistered_tanning_count: Optional[int] = None
    unregistered_tanning_inc_vat_kr: Optional[float] = None
    tanning_bonus_inc_vat_kr: Optional[float] = None
    tanning_control_inc_vat_kr: Optional[float] = None
    tanning_control_ex_vat_kr: Optional[float] = None
    member_product_count: Optional[int] = None
    member_product_inc_vat_kr: Optional[float] = None
    unregistered_product_count: Optional[int] = None
    unregistered_product_inc_vat_kr: Optional[float] = None
    product_bonus_inc_vat_kr: Optional[float] = None
    product_control_inc_vat_kr: Optional[float] = None
    product_control_ex_vat_kr: Optional[float] = None
    transaction_cost_kr: Optional[float] = None
    service_fee_kr: Optional[float] = None
    payout_inc_vat_kr: Optional[float] = None
    vat_kr: Optional[float] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class Sun2FinanceSettlementsIngestIn(BaseModel):
    source: str = "sun2_session_scraper"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    source_file: Optional[str] = None
    message: Optional[str] = None
    rows: list[Sun2FinanceSettlementIn] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)
