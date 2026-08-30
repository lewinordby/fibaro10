"""Source queries domain services."""

from datetime import datetime
from fibaro_core.models import ParkingSession
from fibaro_core.models import Sun2ProductSale
from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy import select
from typing import Any
from typing import Dict
from typing import Optional
from value_parsing import float_or_zero
from value_parsing import int_or_zero


async def parking_period_source_summaries(session, start_at: datetime, end_at: datetime) -> Dict[str, Dict[str, Any]]:
    rows = (
        await session.execute(
            select(
                ParkingSession.source_system,
                func.count(ParkingSession.id),
                func.coalesce(func.sum(ParkingSession.fee_ex_vat), 0),
                func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0),
            )
            .where(ParkingSession.start_time >= start_at)
            .where(ParkingSession.start_time < end_at)
            .group_by(ParkingSession.source_system)
        )
    ).all()
    summaries: Dict[str, Dict[str, Any]] = {
        "easypark": {"label": "EasyPark", "sources": [], "count": 0, "paid_ex_vat": 0.0, "paid_inc_vat": 0.0},
        "flowbird": {"label": "flowbird-parknordic", "sources": [], "count": 0, "paid_ex_vat": 0.0, "paid_inc_vat": 0.0},
        "other": {"label": "Andre kilder", "sources": [], "count": 0, "paid_ex_vat": 0.0, "paid_inc_vat": 0.0},
    }
    for source_system, count_value, paid_ex_vat, paid_inc_vat in rows:
        key = parking_source_control_key(source_system)
        item = summaries[key]
        source_label = (source_system or "").strip() or "-"
        if source_label not in item["sources"]:
            item["sources"].append(source_label)
        item["count"] += int_or_zero(count_value)
        item["paid_ex_vat"] += float_or_zero(paid_ex_vat)
        item["paid_inc_vat"] += float_or_zero(paid_inc_vat)
    for item in summaries.values():
        item["paid_ex_vat"] = round(float_or_zero(item.get("paid_ex_vat")), 2)
        item["paid_inc_vat"] = round(float_or_zero(item.get("paid_inc_vat")), 2)
    return summaries


def parking_source_control_key(source_system: Optional[str]) -> str:
    source = (source_system or "").strip().lower()
    if source == "easypark":
        return "easypark"
    if source == "flowbird-parknordic" or "flowbird" in source:
        return "flowbird"
    return "other"


def sun2_product_daily_scope_condition():
    return Sun2ProductSale.period_start == Sun2ProductSale.period_end


def sun2_product_monthly_scope_condition():
    return and_(
        Sun2ProductSale.period_start.is_not(None),
        Sun2ProductSale.period_end.is_not(None),
        Sun2ProductSale.period_start != Sun2ProductSale.period_end,
    )


def sun2_product_amount_inc_expr():
    return func.coalesce(Sun2ProductSale.amount_inc_vat_kr, Sun2ProductSale.amount_ex_vat_kr * 1.25)


def sun2_product_amount_ex_expr():
    return func.coalesce(Sun2ProductSale.amount_ex_vat_kr, Sun2ProductSale.amount_inc_vat_kr / 1.25)
