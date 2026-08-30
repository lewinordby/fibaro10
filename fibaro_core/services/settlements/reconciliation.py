"""Reconciliation domain services."""

from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from fibaro_core.models import SettlementImport
from fibaro_core.services.settlements.controls import sun2_finance_settlement_period_summary
from fibaro_core.services.settlements.controls import sun2_tanning_revenue_control_expected
from fibaro_core.services.settlements.controls import sun2_tanning_sessions_period_summary
from fibaro_core.services.settlements.parsing import PARKING_SETTLEMENT_PROVIDER
from fibaro_core.services.settlements.parsing import SUN_SETTLEMENT_PROVIDER
from fibaro_core.services.settlements.parsing import parse_settlement_number
from fibaro_core.services.settlements.parsing import settlement_parsed_float
from fibaro_core.services.settlements.source_queries import parking_period_source_summaries
from fibaro_core.services.summaries.periods import month_label
from reconciliation_domain import evaluate_reconciliation
from reconciliation_domain import reconciliation_difference
from sqlalchemy import select
from typing import Any
from typing import Dict
from typing import Optional
from value_parsing import float_or_zero


def reconciliation_diff(system_value: Optional[float], settlement_value: Optional[float]) -> Optional[float]:
    difference = reconciliation_difference(system_value, settlement_value)
    return round(difference, 2) if difference is not None else None


def reconciliation_status(system_value: Optional[float], settlement_value: Optional[float], diff_value: Optional[float]) -> str:
    if settlement_value is None:
        return "Mangler oppgjør"
    if system_value is None:
        return "Mangler systemgrunnlag"
    result = evaluate_reconciliation(
        check_id="legacy-settlement-control",
        domain="Oppgjør",
        title="Oppgjørskontroll",
        actual_label="System",
        actual_value=system_value,
        reference_label="Oppgjør",
        reference_value=settlement_value,
        unit="kr",
        absolute_tolerance=1,
        critical_multiplier=1,
    )
    return "OK" if result["status"] == "ok" else "Avvik"


def settlement_amount_sum(*values: Optional[float]) -> Optional[float]:
    parsed_values = [parse_settlement_number(value) for value in values]
    if not any(value is not None for value in parsed_values):
        return None
    return round(sum(float_or_zero(value) for value in parsed_values), 2)


async def revenue_settlement_reconciliation_rows(session, limit: int = 36) -> list[Dict[str, Any]]:
    parking_settlements = (
        await session.execute(
            select(SettlementImport)
            .where(SettlementImport.provider == PARKING_SETTLEMENT_PROVIDER)
            .where(SettlementImport.period_start.is_not(None))
            .where(SettlementImport.period_end.is_not(None))
            .order_by(SettlementImport.period_start.desc(), SettlementImport.imported_at.desc())
            .limit(limit * 2)
        )
    ).scalars().all()
    sun_settlements = (
        await session.execute(
            select(SettlementImport)
            .where(SettlementImport.provider == SUN_SETTLEMENT_PROVIDER)
            .where(SettlementImport.period_start.is_not(None))
            .where(SettlementImport.period_end.is_not(None))
            .order_by(SettlementImport.period_start.desc(), SettlementImport.imported_at.desc())
            .limit(limit * 2)
        )
    ).scalars().all()

    periods: dict[tuple[date, date], Dict[str, Any]] = {}
    for row in parking_settlements:
        if not row.period_start or not row.period_end:
            continue
        key = (row.period_start, row.period_end)
        periods.setdefault(key, {"start": row.period_start, "end": row.period_end})
        periods[key].setdefault("parking", row)
    for row in sun_settlements:
        if not row.period_start or not row.period_end:
            continue
        key = (row.period_start, row.period_end)
        periods.setdefault(key, {"start": row.period_start, "end": row.period_end})
        periods[key].setdefault("sun", row)

    rows: list[Dict[str, Any]] = []
    for item in sorted(periods.values(), key=lambda value: value["start"], reverse=True)[:limit]:
        start = item["start"]
        end = item["end"]
        parking_row: Optional[SettlementImport] = item.get("parking")
        sun_row: Optional[SettlementImport] = item.get("sun")
        period_label = (
            (parking_row.period_label if parking_row else None)
            or (sun_row.period_label if sun_row else None)
            or month_label(start)
        )

        parking_source = await parking_period_source_summaries(
            session,
            datetime.combine(start, time.min),
            datetime.combine(end + timedelta(days=1), time.min),
        )
        parking_system_ex = round(
            float_or_zero(parking_source["easypark"].get("paid_ex_vat"))
            + float_or_zero(parking_source["flowbird"].get("paid_ex_vat"))
            + float_or_zero(parking_source["other"].get("paid_ex_vat")),
            2,
        )
        parking_settlement_ex = None
        if parking_row:
            parking_settlement_ex = settlement_amount_sum(
                settlement_parsed_float(parking_row.parsed, "gross_coin_card_ex_vat"),
                settlement_parsed_float(parking_row.parsed, "easypark_ex_vat"),
            )
        parking_diff = reconciliation_diff(parking_system_ex, parking_settlement_ex)
        parking_status = reconciliation_status(parking_system_ex, parking_settlement_ex, parking_diff)

        finance_summary = await sun2_finance_settlement_period_summary(session, start, end)
        sessions_summary = await sun2_tanning_sessions_period_summary(session, start, end)
        sun_system_ex, _detail, _source, _source_label = sun2_tanning_revenue_control_expected(
            finance_summary,
            sessions_summary,
        )
        sun_settlement_ex = settlement_parsed_float(sun_row.parsed, "sun_revenue_ex_vat") if sun_row else None
        sun_diff = reconciliation_diff(sun_system_ex, sun_settlement_ex)
        sun_status = reconciliation_status(sun_system_ex, sun_settlement_ex, sun_diff)

        system_total = settlement_amount_sum(parking_system_ex, sun_system_ex)
        settlement_total = settlement_amount_sum(parking_settlement_ex, sun_settlement_ex)
        total_diff = reconciliation_diff(system_total, settlement_total)
        if parking_status == "OK" and sun_status == "OK":
            status = "OK"
        elif "Avvik" in {parking_status, sun_status}:
            status = "Avvik"
        else:
            status = "Mangler grunnlag"

        rows.append(
            {
                "period_label": period_label,
                "period_start": start,
                "period_end": end,
                "parking_settlement_id": parking_row.id if parking_row else None,
                "parking_settlement_imported_at": parking_row.imported_at if parking_row else None,
                "parking_system_ex_vat": parking_system_ex,
                "parking_settlement_ex_vat": parking_settlement_ex,
                "parking_diff_ex_vat": parking_diff,
                "parking_control_status": parking_status,
                "sun_settlement_id": sun_row.id if sun_row else None,
                "sun_settlement_imported_at": sun_row.imported_at if sun_row else None,
                "sun_system_ex_vat": sun_system_ex,
                "sun_settlement_ex_vat": sun_settlement_ex,
                "sun_diff_ex_vat": sun_diff,
                "sun_control_status": sun_status,
                "system_total_ex_vat": system_total,
                "settlement_total_ex_vat": settlement_total,
                "total_diff_ex_vat": total_diff,
                "status": status,
            }
        )
    return rows
