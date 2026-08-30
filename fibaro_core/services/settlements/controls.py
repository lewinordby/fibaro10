"""Controls domain services."""

from datetime import date
from fibaro_core.models import Sun2FinanceSettlement
from fibaro_core.models import Sun2ProductSale
from fibaro_core.models import Sun2RoomDailyStat
from fibaro_core.models import Sun2TanningSession
from fibaro_core.services.presentation import format_short_number
from fibaro_core.services.settlements.parsing import parse_settlement_number
from fibaro_core.services.settlements.parsing import settlement_number_value
from fibaro_core.services.settlements.parsing import settlement_parsed_float
from fibaro_core.services.settlements.parsing import settlement_parsed_value
from fibaro_core.services.settlements.fields import settlement_form_field
from sqlalchemy import func
from sqlalchemy import select
from time_formatting import format_local_datetime
from typing import Any
from typing import Dict
from typing import Optional
from value_parsing import float_or_zero
from value_parsing import int_or_zero


def settlement_source_expected(
    source_summaries: Optional[Dict[str, Dict[str, Any]]],
    key: str,
) -> tuple[Optional[float], str]:
    if not source_summaries:
        return None, ""
    summary = source_summaries.get(key) or {}
    value = summary.get("paid_ex_vat")
    if value is None:
        return None, ""
    sources = summary.get("sources")
    if isinstance(sources, list) and sources:
        source_text = ", ".join(str(item) for item in sources)
    else:
        source_text = str(summary.get("label") or key)
    count_value = int_or_zero(summary.get("count"))
    return round(float_or_zero(value), 2), f"{count_value} parkeringer fra {source_text}"


async def sun2_product_sales_period_summary(session, start: date, end: date) -> Dict[str, Any]:
    amount_ex_expr = func.coalesce(Sun2ProductSale.amount_ex_vat_kr, Sun2ProductSale.amount_inc_vat_kr / 1.25)
    base_query = select(
        func.count(Sun2ProductSale.id),
        func.coalesce(func.sum(amount_ex_expr), 0),
        func.coalesce(func.sum(Sun2ProductSale.amount_inc_vat_kr), 0),
        func.coalesce(func.sum(Sun2ProductSale.quantity), 0),
        func.min(Sun2ProductSale.stat_date),
        func.max(Sun2ProductSale.stat_date),
        func.max(Sun2ProductSale.imported_at),
    )
    active_filters = [
        Sun2ProductSale.period_start == start,
        Sun2ProductSale.period_end == end,
    ]
    result = (
        await session.execute(
            base_query.where(*active_filters)
        )
    ).one()
    source_scope = "monthly" if int_or_zero(result[0]) else "daily"
    if not int_or_zero(result[0]):
        active_filters = [
            Sun2ProductSale.stat_date >= start,
            Sun2ProductSale.stat_date <= end,
            Sun2ProductSale.period_start == Sun2ProductSale.period_end,
        ]
        result = (
            await session.execute(
                base_query.where(*active_filters)
            )
        ).one()
    count_value, amount_ex, amount_inc, quantity, first_date, last_date, last_imported = result
    period_summary_raw = (
        await session.execute(
            select(Sun2ProductSale.raw)
            .where(*active_filters)
            .where(Sun2ProductSale.raw.isnot(None))
            .order_by(Sun2ProductSale.imported_at.desc())
            .limit(1)
        )
    ).scalars().first()
    period_summary = {}
    if isinstance(period_summary_raw, dict) and isinstance(period_summary_raw.get("period_summary"), dict):
        period_summary = period_summary_raw["period_summary"]
    real_money_inc = parse_settlement_number(period_summary.get("real_money_inc_vat_kr")) if period_summary else None
    total_summary_inc = parse_settlement_number(period_summary.get("total_inc_vat_kr")) if period_summary else None
    control_amount_inc = real_money_inc if real_money_inc is not None else float_or_zero(amount_inc)
    control_amount_ex = round(control_amount_inc / 1.25, 2) if real_money_inc is not None else float_or_zero(amount_ex)
    return {
        "count": int_or_zero(count_value),
        "quantity": float_or_zero(quantity),
        "amount_ex_vat": round(float_or_zero(control_amount_ex), 2),
        "amount_inc_vat": round(float_or_zero(control_amount_inc), 2),
        "gross_amount_ex_vat": round(float_or_zero(amount_ex), 2),
        "gross_amount_inc_vat": round(float_or_zero(amount_inc), 2),
        "real_money_inc_vat": real_money_inc,
        "summary_total_inc_vat": total_summary_inc,
        "control_basis": "ekte_penger" if real_money_inc is not None else "produktlinjer_total",
        "first_date": first_date,
        "last_date": last_date,
        "last_imported_at": last_imported,
        "period_start": start,
        "period_end": end,
        "source_scope": source_scope,
    }


def sun2_product_sales_expected(summary: Optional[Dict[str, Any]]) -> tuple[Optional[float], str]:
    if not summary or int_or_zero(summary.get("count")) <= 0:
        return None, ""
    count_value = int_or_zero(summary.get("count"))
    quantity = float_or_zero(summary.get("quantity"))
    detail = f"{count_value} salgslinjer"
    if quantity:
        detail += f", {format_short_number(quantity, 2)} stk"
    gross_inc = parse_settlement_number(summary.get("gross_amount_inc_vat") or summary.get("summary_total_inc_vat"))
    if gross_inc is not None:
        detail += f", månedsomsetning {format_short_number(gross_inc, 2)} kr inkl. mva"
    last_imported = summary.get("last_imported_at")
    if last_imported:
        detail += f", sist importert {format_local_datetime(last_imported)}"
    return round(float_or_zero(summary.get("gross_amount_ex_vat", summary.get("amount_ex_vat"))), 2), detail


async def sun2_finance_settlement_period_summary(session, start: date, end: date) -> Dict[str, Any]:
    row = (
        await session.execute(
            select(Sun2FinanceSettlement)
            .where(Sun2FinanceSettlement.period_start == start)
            .where(Sun2FinanceSettlement.period_end == end)
            .order_by(Sun2FinanceSettlement.imported_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if not row:
        row = (
            await session.execute(
                select(Sun2FinanceSettlement)
                .where(Sun2FinanceSettlement.period_start <= start)
                .where(Sun2FinanceSettlement.period_end >= end)
                .order_by(Sun2FinanceSettlement.imported_at.desc())
                .limit(1)
            )
        ).scalars().first()
    if not row:
        return {"period_start": start, "period_end": end, "count": 0}
    return {
        "id": row.id,
        "source_payout_id": row.source_payout_id,
        "payout_label": row.payout_label,
        "period_start": row.period_start,
        "period_end": row.period_end,
        "payout_date": row.payout_date,
        "member_tanning_count": row.member_tanning_count,
        "member_tanning_inc_vat": row.member_tanning_inc_vat_kr,
        "unregistered_tanning_count": row.unregistered_tanning_count,
        "unregistered_tanning_inc_vat": row.unregistered_tanning_inc_vat_kr,
        "tanning_gross_inc_vat": round(float_or_zero(row.member_tanning_inc_vat_kr) + float_or_zero(row.unregistered_tanning_inc_vat_kr), 2),
        "tanning_gross_ex_vat": round((float_or_zero(row.member_tanning_inc_vat_kr) + float_or_zero(row.unregistered_tanning_inc_vat_kr)) / 1.25, 2),
        "tanning_control_inc_vat": row.tanning_control_inc_vat_kr,
        "tanning_control_ex_vat": row.tanning_control_ex_vat_kr,
        "last_imported_at": row.imported_at,
        "source_file": row.source_file,
        "count": 1,
    }


def sun2_tanning_revenue_expected(summary: Optional[Dict[str, Any]]) -> tuple[Optional[float], str]:
    if not summary or int_or_zero(summary.get("count")) <= 0:
        return None, ""
    value = parse_settlement_number(summary.get("tanning_gross_ex_vat"))
    if value is None:
        return None, ""
    member_count = int_or_zero(summary.get("member_tanning_count"))
    unregistered_count = int_or_zero(summary.get("unregistered_tanning_count"))
    member_inc = parse_settlement_number(summary.get("member_tanning_inc_vat"))
    unregistered_inc = parse_settlement_number(summary.get("unregistered_tanning_inc_vat"))
    detail_parts = [
        f"{member_count} medlemssolinger",
        f"{unregistered_count} uregistrerte solinger",
    ]
    if member_inc is not None or unregistered_inc is not None:
        detail_parts.append(
            f"månedsomsetning {format_short_number(float_or_zero(member_inc) + float_or_zero(unregistered_inc), 2)} kr inkl. mva"
        )
    payout_label = summary.get("payout_label") or summary.get("source_payout_id")
    if payout_label:
        detail_parts.append(str(payout_label))
    last_imported = summary.get("last_imported_at")
    if last_imported:
        detail_parts.append(f"sist importert {format_local_datetime(last_imported)}")
    return round(float_or_zero(value), 2), ", ".join(detail_parts)


def sun2_tanning_sessions_revenue_expected(summary: Optional[Dict[str, Any]]) -> tuple[Optional[float], str, str, str]:
    if not summary:
        return None, "", "sun2_tanning_sessions", "Sun2 enkelttimer"

    daily_count = int_or_zero(summary.get("daily_count"))
    daily_amount_ex = parse_settlement_number(summary.get("daily_amount_ex_vat"))
    if daily_count > 0 and daily_amount_ex is not None:
        detail_parts = [f"{daily_count} solinger fra dagsstatistikk"]
        daily_amount_inc = parse_settlement_number(summary.get("daily_amount_inc_vat"))
        if daily_amount_inc is not None:
            detail_parts.append(f"månedsomsetning {format_short_number(daily_amount_inc, 2)} kr inkl. mva")
        last_imported = summary.get("daily_last_imported_at")
        if last_imported:
            detail_parts.append(f"sist importert {format_local_datetime(last_imported)}")
        return round(float_or_zero(daily_amount_ex), 2), ", ".join(detail_parts), "sun2_room_daily_stats", "Sun2 dagsstatistikk"

    count_value = int_or_zero(summary.get("count"))
    amount_ex = parse_settlement_number(summary.get("amount_ex_vat"))
    if count_value > 0 and amount_ex is not None:
        detail_parts = [f"{count_value} rå enkelttimer"]
        amount_inc = parse_settlement_number(summary.get("amount_inc_vat"))
        if amount_inc is not None:
            detail_parts.append(f"månedsomsetning {format_short_number(amount_inc, 2)} kr inkl. mva")
        last_imported = summary.get("last_imported_at")
        if last_imported:
            detail_parts.append(f"sist importert {format_local_datetime(last_imported)}")
        return round(float_or_zero(amount_ex), 2), ", ".join(detail_parts), "sun2_tanning_sessions", "Sun2 enkelttimer"

    return None, "", "sun2_tanning_sessions", "Sun2 enkelttimer"


def sun2_tanning_revenue_control_expected(
    finance_summary: Optional[Dict[str, Any]],
    sessions_summary: Optional[Dict[str, Any]] = None,
) -> tuple[Optional[float], str, str, str]:
    value, detail = sun2_tanning_revenue_expected(finance_summary)
    if value is not None:
        return value, detail, "sun2_finance_settlements", "Sun2 finanshistorikk"
    return sun2_tanning_sessions_revenue_expected(sessions_summary)


async def sun2_tanning_sessions_period_summary(session, start: date, end: date) -> Dict[str, Any]:
    result = (
        await session.execute(
            select(
                func.count(Sun2TanningSession.id),
                func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0),
                func.min(Sun2TanningSession.started_at),
                func.max(Sun2TanningSession.started_at),
                func.max(Sun2TanningSession.imported_at),
            )
            .where(Sun2TanningSession.stat_date >= start)
            .where(Sun2TanningSession.stat_date <= end)
        )
    ).one()
    daily_result = (
        await session.execute(
            select(
                func.coalesce(func.sum(Sun2RoomDailyStat.totalt_antall_solinger), 0),
                func.coalesce(func.sum(Sun2RoomDailyStat.totalt_inntjent_kr), 0),
                func.max(Sun2RoomDailyStat.imported_at),
            )
            .where(Sun2RoomDailyStat.stat_date >= start)
            .where(Sun2RoomDailyStat.stat_date <= end)
        )
    ).one()
    count_value, amount_inc, first_started, last_started, last_imported = result
    daily_count, daily_amount_inc, daily_imported = daily_result
    return {
        "period_start": start,
        "period_end": end,
        "count": int_or_zero(count_value),
        "amount_inc_vat": round(float_or_zero(amount_inc), 2),
        "amount_ex_vat": round(float_or_zero(amount_inc) / 1.25, 2),
        "first_started_at": first_started,
        "last_started_at": last_started,
        "last_imported_at": last_imported,
        "daily_count": int_or_zero(daily_count),
        "daily_amount_inc_vat": round(float_or_zero(daily_amount_inc), 2),
        "daily_amount_ex_vat": round(float_or_zero(daily_amount_inc) / 1.25, 2),
        "daily_last_imported_at": daily_imported,
    }


def settlement_form_rows(parsed: Any, source_summaries: Optional[Dict[str, Dict[str, Any]]] = None) -> list[Dict[str, Any]]:
    gross_coin_card = settlement_parsed_float(parsed, "gross_coin_card_ex_vat")
    easypark = settlement_parsed_float(parsed, "easypark_ex_vat")
    fee = settlement_parsed_float(parsed, "settlement_fee_ex_vat")
    net_coin_card = settlement_parsed_float(parsed, "revenue_basis_ex_vat")
    long_term = settlement_parsed_float(parsed, "long_term_parking_ex_vat")
    control_fee = settlement_parsed_float(parsed, "control_fee_net_ex_vat")
    total_basis = settlement_parsed_float(parsed, "total_basis_ex_vat")
    total_share = settlement_parsed_float(parsed, "total_share_ex_vat")
    vat = settlement_parsed_float(parsed, "vat_25_percent")
    payout = settlement_parsed_float(parsed, "payout_inc_vat")

    expected_net_coin_card = settlement_sum_or_none(gross_coin_card, easypark, fee)
    expected_total_basis = settlement_sum_or_none(net_coin_card, long_term, control_fee)
    expected_payout = settlement_sum_or_none(total_share, vat)
    expected_flowbird, expected_flowbird_detail = settlement_source_expected(source_summaries, "flowbird")
    expected_easypark, expected_easypark_detail = settlement_source_expected(source_summaries, "easypark")

    rows = [
        settlement_form_field(
            "Brutto mynt/kortautomat",
            "gross_coin_card_ex_vat",
            settlement_parsed_value(parsed, "gross_coin_card_ex_vat"),
            parsed,
            "amount",
            "Operativt beløp fra linjen Bruttoinntekter over mynt/kortautomat.",
        ),
        settlement_form_field(
            "EasyPark",
            "easypark_ex_vat",
            settlement_parsed_value(parsed, "easypark_ex_vat"),
            parsed,
            "amount",
            "Operativt beløp fra EasyPark-linjen. Dette kontrolleres mot source_system = EasyPark.",
        ),
        settlement_form_field(
            "Fratrekk tømming/telling/kort",
            "settlement_fee_ex_vat",
            settlement_parsed_value(parsed, "settlement_fee_ex_vat"),
            parsed,
            "amount",
            "Operativt fratrekk for tømming, telling og kortavregning.",
        ),
        settlement_form_field(
            "Netto innbetalte kontrollavgifter",
            "control_fee_net_ex_vat",
            settlement_parsed_value(parsed, "control_fee_net_ex_vat"),
            parsed,
            "amount",
            "Operativt beløp fra linjen Netto innbetalte kontrollavgifter.",
        ),
        settlement_form_field(
            "Nettoinntekter mynt/kortautomat",
            "revenue_basis_ex_vat",
            settlement_parsed_value(parsed, "revenue_basis_ex_vat"),
            parsed,
            "control",
            "Kontrollsum: brutto mynt/kort + EasyPark + fratrekk.",
            expected_net_coin_card,
        ),
        settlement_form_field(
            "Grunnlag omsetning eks. mva",
            "total_basis_ex_vat",
            settlement_parsed_value(parsed, "total_basis_ex_vat"),
            parsed,
            "control",
            "Kontrollsum: netto mynt/kort + langtidsparkering + netto kontrollavgifter.",
            expected_total_basis,
        ),
        settlement_form_field(
            "Til utbetaling",
            "payout_inc_vat",
            settlement_parsed_value(parsed, "payout_inc_vat"),
            parsed,
            "control",
            "Kontrollsum: sum eks. mva + 25% mva.",
            expected_payout,
        ),
    ]
    source_controls = {
        "gross_coin_card_ex_vat": (
            expected_flowbird,
            "Fibaro10 flowbird eks. mva",
            "source_system = flowbird-parknordic",
            expected_flowbird_detail,
        ),
        "easypark_ex_vat": (
            expected_easypark,
            "Fibaro10 EasyPark eks. mva",
            "source_system = EasyPark",
            expected_easypark_detail,
        ),
    }
    for item in rows:
        expected, expected_label, expected_source, expected_detail = source_controls.get(item.get("field"), (None, "", "", ""))
        if expected is None:
            continue
        numeric_value = parse_settlement_number(item.get("value"))
        item["expected"] = settlement_number_value(expected)
        item["expectedLabel"] = expected_label
        item["expectedSource"] = expected_source
        item["expectedDetail"] = expected_detail
        if numeric_value is not None:
            difference = round(float(numeric_value) - expected, 2)
            item["difference"] = settlement_number_value(difference)
            item["status"] = "ok" if abs(difference) <= 1 else "warn"
        else:
            item["status"] = "missing"
    return rows


def sun_settlement_form_rows(
    parsed: Any,
    product_sales_summary: Optional[Dict[str, Any]] = None,
    finance_summary: Optional[Dict[str, Any]] = None,
    sessions_summary: Optional[Dict[str, Any]] = None,
) -> list[Dict[str, Any]]:
    sun_revenue = settlement_parsed_float(parsed, "sun_revenue_ex_vat")
    product_sales = settlement_parsed_float(parsed, "product_sales_ex_vat")
    transaction_fee = settlement_parsed_float(parsed, "transaction_fee_ex_vat")
    service_fee = settlement_parsed_float(parsed, "service_fee_ex_vat")
    marketing_sms = settlement_parsed_float(parsed, "marketing_sms_fee_ex_vat")
    marketing_email = settlement_parsed_float(parsed, "marketing_email_fee_ex_vat")
    sum_ex_vat = settlement_parsed_float(parsed, "sum_ex_vat")
    vat = settlement_parsed_float(parsed, "vat_25_percent")
    payout = settlement_parsed_float(parsed, "payout_inc_vat")

    line_sum = settlement_sum_or_none(
        sun_revenue,
        product_sales,
        transaction_fee,
        service_fee,
        marketing_sms,
        marketing_email,
    )
    expected_vat = round(sum_ex_vat * 0.25, 2) if sum_ex_vat is not None else None
    expected_payout = settlement_sum_or_none(sum_ex_vat, vat)
    transaction_base = settlement_sum_or_none(sun_revenue, product_sales)
    expected_transaction_fee = round(-transaction_base * 0.06, 2) if transaction_base is not None else None
    expected_product_sales, expected_product_sales_detail = sun2_product_sales_expected(product_sales_summary)
    expected_sun_revenue, expected_sun_revenue_detail, expected_sun_revenue_source, _ = sun2_tanning_revenue_control_expected(
        finance_summary,
        sessions_summary,
    )

    return [
        settlement_form_field(
            "Solomsetning for perioden",
            "sun_revenue_ex_vat",
            settlement_parsed_value(parsed, "sun_revenue_ex_vat"),
            parsed,
            "amount",
            "Operativt beløp fra linjen Solomsetning for perioden.",
            expected_sun_revenue,
            expected_label="Sun2 månedsomsetning eks. mva",
            expected_source=expected_sun_revenue_source,
            expected_detail=expected_sun_revenue_detail,
            difference_direction="expected_minus_value",
        ),
        settlement_form_field(
            "Produktsalg for perioden",
            "product_sales_ex_vat",
            settlement_parsed_value(parsed, "product_sales_ex_vat"),
            parsed,
            "amount",
            "Operativt beløp fra linjen Produktsalg for perioden.",
            expected_product_sales,
            expected_label="Sun2 månedsomsetning eks. mva",
            expected_source="sun2_product_sales",
            expected_detail=expected_product_sales_detail,
            difference_direction="expected_minus_value",
        ),
        settlement_form_field(
            "Transaksjonskostnad",
            "transaction_fee_ex_vat",
            settlement_parsed_value(parsed, "transaction_fee_ex_vat"),
            parsed,
            "amount",
            "Fratrekk fra linjen Transaksjonskostnad.",
            expected_transaction_fee,
            expected_label="6% av solomsetning + produktsalg",
        ),
        settlement_form_field(
            "Serviceavtale",
            "service_fee_ex_vat",
            settlement_parsed_value(parsed, "service_fee_ex_vat"),
            parsed,
            "amount",
            "Fratrekk fra linjen Serviceavtale.",
        ),
        settlement_form_field(
            "Markedsforing SMS",
            "marketing_sms_fee_ex_vat",
            settlement_parsed_value(parsed, "marketing_sms_fee_ex_vat"),
            parsed,
            "amount",
            "Eventuelt fratrekk for markedsføring på SMS.",
        ),
        settlement_form_field(
            "Markedsforing e-post",
            "marketing_email_fee_ex_vat",
            settlement_parsed_value(parsed, "marketing_email_fee_ex_vat"),
            parsed,
            "amount",
            "Eventuelt fratrekk for markedsføring på e-post.",
        ),
        settlement_form_field(
            "Sum eks. MVA",
            "sum_ex_vat",
            settlement_parsed_value(parsed, "sum_ex_vat"),
            parsed,
            "control",
            "Kontrollsum: solomsetning + produktsalg + fratrekk.",
            line_sum,
        ),
        settlement_form_field(
            "25% mva",
            "vat_25_percent",
            settlement_parsed_value(parsed, "vat_25_percent"),
            parsed,
            "control",
            "Kontrollsum: Sum eks. MVA * 25%.",
            expected_vat,
        ),
        settlement_form_field(
            "Beløp NOK",
            "payout_inc_vat",
            settlement_parsed_value(parsed, "payout_inc_vat"),
            parsed,
            "control",
            "Kontrollsum: Sum eks. MVA + 25% mva.",
            expected_payout,
        ),
    ]


def settlement_sum_or_none(*values: Optional[float]) -> Optional[float]:
    if any(value is None for value in values):
        return None
    return round(sum(float(value or 0) for value in values), 2)
