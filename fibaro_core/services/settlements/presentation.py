from fibaro_core.services.settlements.fields import settlement_field, settlement_form_field
"""Presentation domain services."""

from datetime import datetime
from datetime import time
from datetime import timedelta
from fibaro_core.models import SettlementImport
from fibaro_core.services.presentation import api_card
from fibaro_core.services.presentation import api_iso_value
from fibaro_core.services.presentation import api_table
from fibaro_core.services.presentation import format_file_size
from fibaro_core.services.presentation import format_short_number
from fibaro_core.services.settlements.controls import settlement_form_rows
from fibaro_core.services.settlements.controls import sun2_finance_settlement_period_summary
from fibaro_core.services.settlements.controls import sun2_product_sales_expected
from fibaro_core.services.settlements.controls import sun2_product_sales_period_summary
from fibaro_core.services.settlements.controls import sun2_tanning_revenue_control_expected
from fibaro_core.services.settlements.controls import sun2_tanning_sessions_period_summary
from fibaro_core.services.settlements.controls import sun_settlement_form_rows
from fibaro_core.services.settlements.mail import PARKING_SETTLEMENT_SENDER
from fibaro_core.services.settlements.mail import settlement_gmail_configured
from fibaro_core.services.settlements.parsing import PARKING_SETTLEMENT_PROVIDER
from fibaro_core.services.settlements.parsing import SUN_SETTLEMENT_PROVIDER
from fibaro_core.services.settlements.parsing import ensure_settlement_parsed
from fibaro_core.services.settlements.parsing import parse_settlement_number
from fibaro_core.services.settlements.parsing import settlement_field_confidence
from fibaro_core.services.settlements.parsing import settlement_field_source
from fibaro_core.services.settlements.parsing import settlement_number_value
from fibaro_core.services.settlements.parsing import settlement_parsed_float
from fibaro_core.services.settlements.parsing import settlement_parsed_meta
from fibaro_core.services.settlements.parsing import settlement_parsed_value
from fibaro_core.services.settlements.parsing import settlement_public_parsed
from fibaro_core.services.settlements.source_queries import parking_period_source_summaries
from pathlib import Path
from sqlalchemy import func
from sqlalchemy import select
from time_formatting import api_local_iso
from time_formatting import format_local_datetime
from typing import Any
from typing import Dict
from typing import Optional
from value_parsing import float_or_zero
from value_parsing import int_or_zero
import mimetypes


def settlement_row_api(row: SettlementImport) -> Dict[str, Any]:
    parsed = row.parsed if isinstance(row.parsed, dict) else {}
    meta = settlement_parsed_meta(parsed)
    path_prefix = "/soling/oppgjor" if row.provider == SUN_SETTLEMENT_PROVIDER else "/parkering/oppgjor"
    return {
        "id": row.id,
        "provider": row.provider,
        "source": row.source,
        "period_label": row.period_label,
        "period_start": row.period_start.isoformat() if row.period_start else None,
        "period_end": row.period_end.isoformat() if row.period_end else None,
        "status": row.status,
        "sender": row.sender,
        "email_date": api_local_iso(row.email_date),
        "email_subject": row.email_subject,
        "attachment_filename": row.attachment_filename,
        "attachment_content_type": row.attachment_content_type,
        "attachment_size": row.attachment_size,
        "attachment_sha256": row.attachment_sha256[:12] if row.attachment_sha256 else None,
        "easypark_ex_vat": settlement_parsed_value(parsed, "easypark_ex_vat"),
        "easypark_inc_vat_estimate": settlement_parsed_value(parsed, "easypark_inc_vat_estimate"),
        "sun_revenue_ex_vat": settlement_parsed_value(parsed, "sun_revenue_ex_vat"),
        "product_sales_ex_vat": settlement_parsed_value(parsed, "product_sales_ex_vat"),
        "transaction_fee_ex_vat": settlement_parsed_value(parsed, "transaction_fee_ex_vat"),
        "service_fee_ex_vat": settlement_parsed_value(parsed, "service_fee_ex_vat"),
        "marketing_sms_fee_ex_vat": settlement_parsed_value(parsed, "marketing_sms_fee_ex_vat"),
        "marketing_email_fee_ex_vat": settlement_parsed_value(parsed, "marketing_email_fee_ex_vat"),
        "sum_ex_vat": settlement_parsed_value(parsed, "sum_ex_vat"),
        "vat_25_percent": settlement_parsed_value(parsed, "vat_25_percent"),
        "payout_inc_vat": settlement_parsed_value(parsed, "payout_inc_vat"),
        "parser_confidence": meta.get("confidence"),
        "imported_at": api_local_iso(row.imported_at),
        "path": f"{path_prefix}/{row.id}",
    }






def settlement_original_payload(row: SettlementImport, api_prefix: Optional[str] = None) -> Dict[str, Any]:
    filename = row.attachment_filename or f"oppgjor-{row.id}"
    content_type = row.attachment_content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    extension = Path(filename).suffix.lower()
    preview_kind = "unsupported"
    if content_type == "application/pdf" or extension == ".pdf":
        preview_kind = "pdf"
    elif content_type.startswith("image/"):
        preview_kind = "image"
    elif content_type.startswith("text/") or extension in {".csv", ".txt", ".xml"}:
        preview_kind = "text"
    if not api_prefix:
        api_prefix = "/api/soling/settlements" if row.provider == SUN_SETTLEMENT_PROVIDER else "/api/settlements"
    return {
        "filename": filename,
        "contentType": content_type,
        "size": row.attachment_size,
        "sizeLabel": format_file_size(row.attachment_size),
        "sha256": row.attachment_sha256,
        "previewKind": preview_kind,
        "previewUrl": f"{api_prefix}/{row.id}/attachment",
        "downloadUrl": f"{api_prefix}/{row.id}/attachment?download=1",
    }


def parsed_field_rows_for_labels(parsed: Dict[str, Any], labels: list[tuple[str, str, str]]) -> list[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []
    known_fields = {field for _, field, _ in labels}
    for label, field, note in labels:
        if field not in parsed:
            continue
        rows.append(
            settlement_field(
                label,
                field,
                parsed.get(field),
                settlement_field_source(parsed, field),
                note,
                settlement_field_confidence(parsed, field),
            )
        )
    for field in sorted(key for key in parsed.keys() if not key.startswith("_") and key not in known_fields):
        rows.append(
            settlement_field(
                field.replace("_", " ").title(),
                field,
                parsed.get(field),
                settlement_field_source(parsed, field),
                "Ekstra felt fra parseren.",
                settlement_field_confidence(parsed, field),
            )
        )
    return rows


def settlement_parsed_field_rows(parsed: Dict[str, Any]) -> list[Dict[str, Any]]:
    return parsed_field_rows_for_labels(parsed, SETTLEMENT_PARSED_FIELD_LABELS)


def sun_settlement_parsed_field_rows(parsed: Dict[str, Any]) -> list[Dict[str, Any]]:
    return parsed_field_rows_for_labels(parsed, SUN_SETTLEMENT_PARSED_FIELD_LABELS)


async def settlement_detail_payload(session, row: SettlementImport) -> Dict[str, Any]:
    changed = ensure_settlement_parsed(row)
    if changed:
        await session.commit()

    parsed = row.parsed if isinstance(row.parsed, dict) else {}
    public_parsed = settlement_public_parsed(parsed)
    meta = settlement_parsed_meta(parsed)
    control_rows = []
    control_cards = []
    source_summaries: Optional[Dict[str, Dict[str, Any]]] = None
    if row.period_start and row.period_end:
        start_dt = datetime.combine(row.period_start, time.min)
        end_dt = datetime.combine(row.period_end + timedelta(days=1), time.min)
        source_summaries = await parking_period_source_summaries(session, start_dt, end_dt)
        easypark_summary = source_summaries["easypark"]
        flowbird_summary = source_summaries["flowbird"]
        other_summary = source_summaries["other"]
        count_value = int_or_zero(easypark_summary.get("count")) + int_or_zero(flowbird_summary.get("count")) + int_or_zero(other_summary.get("count"))
        paid_value = (
            float_or_zero(easypark_summary.get("paid_inc_vat"))
            + float_or_zero(flowbird_summary.get("paid_inc_vat"))
            + float_or_zero(other_summary.get("paid_inc_vat"))
        )
        average_value = round(paid_value / count_value, 2) if count_value else None
        flowbird_ex_vat = round(float_or_zero(flowbird_summary.get("paid_ex_vat")), 2)
        easypark_source_ex_vat = round(float_or_zero(easypark_summary.get("paid_ex_vat")), 2)
        gross_coin_card = settlement_parsed_float(parsed, "gross_coin_card_ex_vat")
        easypark_ex_vat = settlement_parsed_float(parsed, "easypark_ex_vat")
        payout_inc_vat = settlement_parsed_float(parsed, "payout_inc_vat")
        diff_flowbird = round(gross_coin_card - flowbird_ex_vat, 2) if gross_coin_card is not None else None
        diff_easypark = round(easypark_ex_vat - easypark_source_ex_vat, 2) if easypark_ex_vat is not None else None
        control_rows = [
            settlement_field("Kontrollperiode fra", "period_start", row.period_start, "Tolket fra emne/filnavn"),
            settlement_field("Kontrollperiode til", "period_end", row.period_end, "Beregnet siste dag i tolket måned"),
            settlement_field("Flowbird parkeringer", "flowbird_source_count", int_or_zero(flowbird_summary.get("count")), "source_system = flowbird-parknordic"),
            settlement_field("Flowbird i Fibaro10 eks. mva", "flowbird_source_paid_ex_vat", flowbird_ex_vat, "source_system = flowbird-parknordic", "Summeres fra fee_ex_vat for hele oppgjørsmåneden."),
            settlement_field("Brutto mynt/kort i skjema eks. mva", "gross_coin_card_ex_vat", gross_coin_card, settlement_field_source(parsed, "gross_coin_card_ex_vat"), "Beløp hentet fra oppgjørsskjemaet.", settlement_field_confidence(parsed, "gross_coin_card_ex_vat")),
            settlement_field("Avvik skjema - Flowbird eks. mva", "flowbird_source_diff_ex_vat", diff_flowbird, "Beregnet kontroll", "Positivt tall betyr at skjemaet har høyere brutto mynt/kort enn Fibaro10-kilden."),
            settlement_field("EasyPark parkeringer", "easypark_source_count", int_or_zero(easypark_summary.get("count")), "source_system = EasyPark"),
            settlement_field("EasyPark i Fibaro10 eks. mva", "easypark_source_paid_ex_vat", easypark_source_ex_vat, "source_system = EasyPark", "Summeres fra fee_ex_vat for hele oppgjørsmåneden."),
            settlement_field("EasyPark i skjema eks. mva", "easypark_ex_vat", easypark_ex_vat, settlement_field_source(parsed, "easypark_ex_vat"), "Beløp hentet fra oppgjørsskjemaet.", settlement_field_confidence(parsed, "easypark_ex_vat")),
            settlement_field("Avvik skjema - EasyPark eks. mva", "easypark_source_diff_ex_vat", diff_easypark, "Beregnet kontroll", "Positivt tall betyr at skjemaet har høyere EasyPark-beløp enn Fibaro10-kilden."),
            settlement_field("Andre kildeparkeringer", "other_source_count", int_or_zero(other_summary.get("count")), "Alle andre source_system-verdier"),
            settlement_field("Total parkering i Fibaro10 inkl. mva", "parking_paid", round(paid_value, 2), "Alle parkeringskilder", "Totalverdi for orientering, ikke brukt som EasyPark-kontroll."),
            settlement_field("Snitt per parkering", "average_paid", average_value, "Beregnet fra intern parkeringstelling"),
            settlement_field("Til utbetaling i skjema", "payout_inc_vat", payout_inc_vat, settlement_field_source(parsed, "payout_inc_vat"), "Oppgjørets sluttsum. Dette er ikke direkte det samme som kundebetaling i Fibaro10.", settlement_field_confidence(parsed, "payout_inc_vat")),
        ]
        control_cards = [
            api_card("Flowbird Fibaro10", format_short_number(flowbird_ex_vat, 2), "kr", f"{int_or_zero(flowbird_summary.get('count'))} parkeringer", "parking"),
            api_card("EasyPark Fibaro10", format_short_number(easypark_source_ex_vat, 2), "kr", f"{int_or_zero(easypark_summary.get('count'))} parkeringer", "parking"),
        ]
        if diff_flowbird is not None:
            control_cards.append(api_card("Avvik Flowbird", format_short_number(diff_flowbird, 2), "kr", "Skjema minus Fibaro10 eks. mva", "revenue"))
        if diff_easypark is not None:
            control_cards.append(api_card("Avvik EasyPark", format_short_number(diff_easypark, 2), "kr", "Skjema minus Fibaro10 eks. mva", "revenue"))
    else:
        control_rows = [
            settlement_field("Kontrollstatus", "status", "Mangler periode", "Perioden kunne ikke tolkes fra emne, filnavn eller e-postdato"),
        ]

    parsed_rows = settlement_parsed_field_rows(parsed)
    if not parsed_rows:
        parsed_rows = [
            settlement_field(
                "Skjemafelter",
                "parsed",
                "Ikke maskinlest ennå",
                "Originalskjemaet er lagret, men tall/felter fra selve skjemaet er ikke trukket ut til strukturerte felter ennå.",
            )
        ]
    parser_rows = [
        settlement_field("Parser", "parser", meta.get("parser"), "Teknisk parsermetadata"),
        settlement_field("Parser-versjon", "parser_version", meta.get("parser_version"), "Teknisk parsermetadata"),
        settlement_field("Sikkerhet", "confidence", meta.get("confidence"), "Andel nøkkelfelter som ble funnet"),
        settlement_field("Tekstmetode", "method", meta.get("method"), "Hvordan vedlegget ble lest"),
        settlement_field("Tekstlinjer", "line_count", meta.get("line_count"), "Antall tekstlinjer hentet fra originalfil"),
        settlement_field("Sider", "pages_count", meta.get("pages_count"), "Antall PDF-sider hvis kjent"),
    ]
    warnings = meta.get("warnings") if isinstance(meta.get("warnings"), list) else []
    notes = meta.get("notes") if isinstance(meta.get("notes"), list) else []
    for index, warning in enumerate([*warnings, *notes], start=1):
        parser_rows.append(settlement_field(f"Merknad {index}", f"parser_note_{index}", warning, "Parser"))

    cards = [
        api_card("Periode", row.period_label or "Ikke tolket", "", "Fra emne/filnavn eller e-postdato", "revenue"),
        api_card("Original", settlement_original_payload(row)["sizeLabel"], "", row.attachment_filename or "-", "status"),
        api_card("Skjemafelter", len(public_parsed), "stk", f"Sikkerhet {format_short_number(float_or_zero(meta.get('confidence')) * 100, 0)} %", "status"),
        api_card("Til utbetaling", format_short_number(settlement_parsed_float(parsed, "payout_inc_vat") or 0, 2), "kr", "Fra skjema", "revenue"),
        *control_cards,
    ]
    return {
        "id": row.id,
        "title": row.period_label or f"Oppgjør {row.id}",
        "subtitle": row.attachment_filename or row.email_subject or "",
        "cards": cards,
        "original": settlement_original_payload(row),
        "sections": [
            {"title": "Oppgjørsformular", "rows": settlement_form_rows(parsed, source_summaries)},
            {"title": "Nøkkeltall fra skjema", "rows": parsed_rows},
            {"title": "Kontroll mot Fibaro10", "rows": control_rows},
            {
                "title": "Tolket periode",
                "rows": [
                    settlement_field("Periodeetikett", "period_label", row.period_label, "Tolket fra emne/filnavn, eventuelt antatt fra e-postdato"),
                    settlement_field("Periodestart", "period_start", row.period_start, "Første dag i tolket måned"),
                    settlement_field("Periodeslutt", "period_end", row.period_end, "Siste dag i tolket måned"),
                    settlement_field("Status", "status", row.status, "Importstatus i Fibaro10"),
                ],
            },
            {
                "title": "E-post og vedlegg",
                "rows": [
                    settlement_field("Avsender", "sender", row.sender, "E-postheader From"),
                    settlement_field("E-postdato", "email_date", row.email_date, "E-postheader Date"),
                    settlement_field("Emne", "email_subject", row.email_subject, "E-postheader Subject"),
                    settlement_field("Gmail UID", "gmail_uid", row.gmail_uid, "Gmail IMAP UID"),
                    settlement_field("Postboks", "mailbox", row.mailbox, "Gmail IMAP mappe"),
                    settlement_field("Filnavn", "attachment_filename", row.attachment_filename, "Vedlegg"),
                    settlement_field("Filtype", "attachment_content_type", row.attachment_content_type, "Vedlegg MIME-type"),
                    settlement_field("Filstørrelse", "attachment_size", format_file_size(row.attachment_size), "Vedlegg byte-størrelse"),
                    settlement_field("SHA-256", "attachment_sha256", row.attachment_sha256, "Hash av originalvedlegg"),
                    settlement_field("Importert", "imported_at", row.imported_at, "Tidspunkt Fibaro10 lagret oppgjøret"),
                ],
            },
            {"title": "Parserkontroll", "rows": parser_rows},
        ],
        "raw": row.raw or {},
    }


async def sun_settlement_detail_payload(session, row: SettlementImport) -> Dict[str, Any]:
    changed = ensure_settlement_parsed(row)
    if changed:
        await session.commit()

    parsed = row.parsed if isinstance(row.parsed, dict) else {}
    public_parsed = settlement_public_parsed(parsed)
    meta = settlement_parsed_meta(parsed)
    product_sales_summary = (
        await sun2_product_sales_period_summary(session, row.period_start, row.period_end)
        if row.period_start and row.period_end
        else None
    )
    finance_summary = (
        await sun2_finance_settlement_period_summary(session, row.period_start, row.period_end)
        if row.period_start and row.period_end
        else None
    )
    sessions_summary = (
        await sun2_tanning_sessions_period_summary(session, row.period_start, row.period_end)
        if row.period_start and row.period_end
        else None
    )
    expected_sun_revenue, sun_revenue_detail, sun_revenue_source, sun_revenue_source_label = sun2_tanning_revenue_control_expected(
        finance_summary,
        sessions_summary,
    )
    expected_product_sales, product_sales_detail = sun2_product_sales_expected(product_sales_summary)
    sun_revenue_value = settlement_parsed_float(parsed, "sun_revenue_ex_vat")
    sun_revenue_diff = (
        round(expected_sun_revenue - sun_revenue_value, 2)
        if sun_revenue_value is not None and expected_sun_revenue is not None
        else None
    )
    raw_sessions_ex = parse_settlement_number((sessions_summary or {}).get("amount_ex_vat"))
    raw_sessions_diff = (
        round(raw_sessions_ex - expected_sun_revenue, 2)
        if raw_sessions_ex is not None and expected_sun_revenue is not None
        else None
    )
    finance_gross_ex = parse_settlement_number((finance_summary or {}).get("tanning_gross_ex_vat"))
    raw_sessions_gross_diff = (
        round(raw_sessions_ex - finance_gross_ex, 2)
        if raw_sessions_ex is not None and finance_gross_ex is not None
        else None
    )
    product_sales_value = settlement_parsed_float(parsed, "product_sales_ex_vat")
    product_sales_diff = (
        round(expected_product_sales - product_sales_value, 2)
        if product_sales_value is not None and expected_product_sales is not None
        else None
    )
    parsed_rows = sun_settlement_parsed_field_rows(parsed)
    if not parsed_rows:
        parsed_rows = [
            settlement_field(
                "Skjemafelter",
                "parsed",
                "Ikke maskinlest ennå",
                "Originalskjemaet er lagret, men dokumentet har ikke tekstlag eller lesbare felter i parseren.",
            )
        ]
    parser_rows = [
        settlement_field("Parser", "parser", meta.get("parser"), "Teknisk parsermetadata"),
        settlement_field("Parser-versjon", "parser_version", meta.get("parser_version"), "Teknisk parsermetadata"),
        settlement_field("Sikkerhet", "confidence", meta.get("confidence"), "Andel nokkelfelter som ble funnet"),
        settlement_field("Tekstmetode", "method", meta.get("method"), "Hvordan vedlegget ble lest"),
        settlement_field("Tekstlinjer", "line_count", meta.get("line_count"), "Antall tekstlinjer hentet fra originalfil"),
        settlement_field("Sider", "pages_count", meta.get("pages_count"), "Antall PDF-sider hvis kjent"),
    ]
    warnings = meta.get("warnings") if isinstance(meta.get("warnings"), list) else []
    notes = meta.get("notes") if isinstance(meta.get("notes"), list) else []
    for index, warning in enumerate([*warnings, *notes], start=1):
        parser_rows.append(settlement_field(f"Merknad {index}", f"parser_note_{index}", warning, "Parser"))

    original = settlement_original_payload(row, "/api/soling/settlements")
    cards = [
        api_card("Periode", row.period_label or "Ikke tolket", "", "Fra skjema, filnavn eller dato", "sun2"),
        api_card("Original", original["sizeLabel"], "", row.attachment_filename or "-", "status"),
        api_card("Skjemafelter", len(public_parsed), "stk", f"Sikkerhet {format_short_number(float_or_zero(meta.get('confidence')) * 100, 0)} %", "status"),
        api_card("Beløp NOK", format_short_number(settlement_parsed_float(parsed, "payout_inc_vat") or 0, 2), "kr", "Fra skjema", "revenue"),
    ]
    if expected_sun_revenue is not None:
        cards.append(api_card("Sun2 soling", format_short_number(expected_sun_revenue, 2), "kr", sun_revenue_detail, "sun2"))
    if sun_revenue_diff is not None:
        tone = "status" if abs(sun_revenue_diff) <= 1 else "revenue"
        cards.append(api_card("Avvik soling", format_short_number(sun_revenue_diff, 2), "kr", "Intern månedsomsetning minus skjema eks. mva", tone))
    if raw_sessions_ex is not None:
        cards.append(
            api_card(
                "Rå enkelttimer",
                format_short_number(raw_sessions_ex, 2),
                "kr",
                f"{int_or_zero((sessions_summary or {}).get('count'))} timer eks. mva",
                "sun2",
            )
        )
    if raw_sessions_diff is not None:
        tone = "status" if abs(raw_sessions_diff) <= 1 else "revenue"
        cards.append(api_card("Råtimer kontroll", format_short_number(raw_sessions_gross_diff or 0, 2), "kr", "Rå enkelttimer minus Sun2 månedsomsetning", tone))
    if expected_product_sales is not None:
        cards.append(api_card("Sun2 produktsalg", format_short_number(expected_product_sales, 2), "kr", product_sales_detail, "sun2"))
    if product_sales_diff is not None:
        tone = "status" if abs(product_sales_diff) <= 1 else "revenue"
        cards.append(api_card("Avvik produktsalg", format_short_number(product_sales_diff, 2), "kr", "Sun2 månedsomsetning minus skjema eks. mva", tone))
    return {
        "id": row.id,
        "title": row.period_label or f"Solingsoppgjør {row.id}",
        "subtitle": row.attachment_filename or row.email_subject or "",
        "cards": cards,
        "original": original,
        "sections": [
            {"title": "Oppgjørsskjema", "rows": sun_settlement_form_rows(parsed, product_sales_summary, finance_summary, sessions_summary)},
            {
                "title": "Kontroll mot intern månedsomsetning",
                "rows": [
                    settlement_field("System soling eks. mva", "sun_revenue_source_ex_vat", expected_sun_revenue, sun_revenue_source_label, "Intern månedsomsetning for soling."),
                    settlement_field("Skjema soling eks. mva", "sun_revenue_ex_vat", sun_revenue_value, "Oppgjørsskjema", "Solomsetning for perioden."),
                    settlement_field("Avvik soling eks. mva", "sun_revenue_diff_ex_vat", sun_revenue_diff, "Beregnet kontroll", "System soling minus skjema soling."),
                    settlement_field("System produktsalg eks. mva", "product_sales_source_ex_vat", expected_product_sales, "Sun2 produktsalg", "Intern månedsomsetning for produktsalg."),
                    settlement_field("Skjema produktsalg eks. mva", "product_sales_ex_vat", product_sales_value, "Oppgjørsskjema", "Produktsalg for perioden."),
                    settlement_field("Avvik produktsalg eks. mva", "product_sales_diff_ex_vat", product_sales_diff, "Beregnet kontroll", "System produktsalg minus skjema produktsalg."),
                    settlement_field("Sun2 soling brutto inkl. mva", "sun_finance_gross_inc_vat", (finance_summary or {}).get("tanning_gross_inc_vat"), "Sun2 finanshistorikk", "Medlemssolinger + uregistrerte solinger for perioden."),
                    settlement_field("Kontrollkilde soling", "sun_revenue_source", sun_revenue_source, "Beregnet kontroll", "Kilden som brukes for system soling i denne perioden."),
                    settlement_field("Rå enkelttimer eks. mva", "sun_sessions_raw_ex_vat", raw_sessions_ex, "sun2_tanning_sessions", f"{int_or_zero((sessions_summary or {}).get('count'))} enkelttimer i perioden."),
                    settlement_field("Råtimer mot system soling eks. mva", "sun_sessions_diff_vs_finance_gross_ex_vat", raw_sessions_gross_diff, "Teknisk kontroll", "Rå enkelttimer minus intern månedsomsetning."),
                ],
            },
            {"title": "Nøkkeltall fra skjema", "rows": parsed_rows},
            {
                "title": "Tolket periode",
                "rows": [
                    settlement_field("Periodeetikett", "period_label", row.period_label, "Tolket fra skjema, filnavn eller dato"),
                    settlement_field("Periodestart", "period_start", row.period_start, "Første dag i tolket måned"),
                    settlement_field("Periodeslutt", "period_end", row.period_end, "Siste dag i tolket måned"),
                    settlement_field("Status", "status", row.status, "Importstatus i Fibaro10"),
                ],
            },
            {
                "title": "E-post og vedlegg",
                "rows": [
                    settlement_field("Avsender", "sender", row.sender, "E-postheader From eller manuell import"),
                    settlement_field("E-postdato", "email_date", row.email_date, "E-postheader Date"),
                    settlement_field("Emne", "email_subject", row.email_subject, "E-postheader Subject"),
                    settlement_field("Gmail UID", "gmail_uid", row.gmail_uid, "Gmail IMAP UID"),
                    settlement_field("Postboks", "mailbox", row.mailbox, "Gmail IMAP mappe"),
                    settlement_field("Filnavn", "attachment_filename", row.attachment_filename, "Vedlegg"),
                    settlement_field("Filtype", "attachment_content_type", row.attachment_content_type, "Vedlegg MIME-type"),
                    settlement_field("Filstørrelse", "attachment_size", format_file_size(row.attachment_size), "Vedlegg byte-størrelse"),
                    settlement_field("SHA-256", "attachment_sha256", row.attachment_sha256, "Hash av originalvedlegg"),
                    settlement_field("Importert", "imported_at", row.imported_at, "Tidspunkt Fibaro10 lagret oppgjøret"),
                ],
            },
            {"title": "Parserkontroll", "rows": parser_rows},
        ],
        "raw": row.raw or {},
    }


def sun_settlement_summary_row(
    row: SettlementImport,
    product_sales_summary: Optional[Dict[str, Any]] = None,
    finance_summary: Optional[Dict[str, Any]] = None,
    sessions_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    parsed = row.parsed if isinstance(row.parsed, dict) else {}
    form_rows = sun_settlement_form_rows(parsed, product_sales_summary, finance_summary, sessions_summary)
    control_rows = [item for item in form_rows if item.get("group") == "control"]
    warn_count = len([item for item in form_rows if item.get("status") == "warn"])
    missing_count = len([item for item in form_rows if item.get("status") == "missing"])
    status_label = "OK" if not warn_count and not missing_count else "Krever kontroll"
    expected_sun_revenue, sun_revenue_detail, sun_revenue_source, _ = sun2_tanning_revenue_control_expected(
        finance_summary,
        sessions_summary,
    )
    sun_revenue_value = settlement_parsed_float(parsed, "sun_revenue_ex_vat")
    sun_revenue_diff = (
        round(expected_sun_revenue - sun_revenue_value, 2)
        if sun_revenue_value is not None and expected_sun_revenue is not None
        else None
    )
    if expected_sun_revenue is None:
        sun_revenue_control_status = "Mangler Sun2-grunnlag"
    elif sun_revenue_diff is not None and abs(sun_revenue_diff) <= 1:
        sun_revenue_control_status = "OK"
    else:
        sun_revenue_control_status = "Avvik"
    raw_sessions_ex = parse_settlement_number((sessions_summary or {}).get("amount_ex_vat"))
    raw_sessions_diff = (
        round(raw_sessions_ex - expected_sun_revenue, 2)
        if raw_sessions_ex is not None and expected_sun_revenue is not None
        else None
    )
    finance_gross_ex = parse_settlement_number((finance_summary or {}).get("tanning_gross_ex_vat"))
    raw_sessions_gross_diff = (
        round(raw_sessions_ex - finance_gross_ex, 2)
        if raw_sessions_ex is not None and finance_gross_ex is not None
        else None
    )
    raw_sessions_status = "Mangler råtimer"
    if raw_sessions_ex is not None and finance_gross_ex is not None:
        raw_sessions_status = "OK" if abs(raw_sessions_gross_diff or 0) <= 1 else "Avvik"
    expected_product_sales, product_sales_detail = sun2_product_sales_expected(product_sales_summary)
    product_sales_value = settlement_parsed_float(parsed, "product_sales_ex_vat")
    product_sales_diff = (
        round(expected_product_sales - product_sales_value, 2)
        if product_sales_value is not None and expected_product_sales is not None
        else None
    )
    if expected_product_sales is None:
        product_control_status = "Mangler Sun2-grunnlag"
    elif product_sales_diff is not None and abs(product_sales_diff) <= 1:
        product_control_status = "OK"
    else:
        product_control_status = "Avvik"
    return {
        **settlement_row_api(row),
        "sum_check_status": status_label,
        "sum_check_warnings": warn_count,
        "missing_fields": missing_count,
        "sun_revenue_source_ex_vat": expected_sun_revenue,
        "sun_revenue_source": sun_revenue_source,
        "sun_revenue_source_detail": sun_revenue_detail,
        "sun_revenue_diff_ex_vat": sun_revenue_diff,
        "sun_revenue_control_status": sun_revenue_control_status,
        "sun_sessions_count": int_or_zero((sessions_summary or {}).get("count")),
        "sun_sessions_source_ex_vat": raw_sessions_ex,
        "sun_sessions_diff_vs_finance_ex_vat": raw_sessions_diff,
        "sun_sessions_diff_vs_finance_gross_ex_vat": raw_sessions_gross_diff,
        "sun_sessions_control_status": raw_sessions_status,
        "sun_finance_gross_ex_vat": finance_gross_ex,
        "product_sales_source_ex_vat": expected_product_sales,
        "product_sales_source_detail": product_sales_detail,
        "product_sales_diff_ex_vat": product_sales_diff,
        "product_sales_control_status": product_control_status,
    }


async def sun_settlement_module_payload(session) -> Dict[str, Any]:
    settlement_rows = (
        await session.execute(
            select(SettlementImport)
            .where(SettlementImport.provider == SUN_SETTLEMENT_PROVIDER)
            .order_by(SettlementImport.period_start.desc().nullslast(), SettlementImport.imported_at.desc())
            .limit(200)
        )
    ).scalars().all()
    latest_import_settlement = (
        await session.execute(
            select(SettlementImport)
            .where(SettlementImport.provider == SUN_SETTLEMENT_PROVIDER)
            .order_by(SettlementImport.imported_at.desc())
            .limit(1)
        )
    ).scalars().first()
    changed_any = False
    for row in settlement_rows:
        changed_any = ensure_settlement_parsed(row) or changed_any
    if changed_any:
        await session.commit()

    total_settlements = (
        await session.execute(
            select(func.count(SettlementImport.id)).where(SettlementImport.provider == SUN_SETTLEMENT_PROVIDER)
        )
    ).scalar_one()
    unknown_period_count = (
        await session.execute(
            select(func.count(SettlementImport.id))
            .where(SettlementImport.provider == SUN_SETTLEMENT_PROVIDER)
            .where(SettlementImport.period_start.is_(None))
        )
    ).scalar_one()
    parsed_period_count = max(0, int_or_zero(total_settlements) - int_or_zero(unknown_period_count))
    product_sales_summaries: Dict[int, Dict[str, Any]] = {}
    finance_summaries: Dict[int, Dict[str, Any]] = {}
    sessions_summaries: Dict[int, Dict[str, Any]] = {}
    for row in settlement_rows:
        if row.id and row.period_start and row.period_end:
            product_sales_summaries[row.id] = await sun2_product_sales_period_summary(session, row.period_start, row.period_end)
            finance_summaries[row.id] = await sun2_finance_settlement_period_summary(session, row.period_start, row.period_end)
            sessions_summaries[row.id] = await sun2_tanning_sessions_period_summary(session, row.period_start, row.period_end)
    product_control_rows = [
        sun_settlement_summary_row(
            row,
            product_sales_summaries.get(row.id or 0),
            finance_summaries.get(row.id or 0),
            sessions_summaries.get(row.id or 0),
        )
        for row in settlement_rows
    ]
    sun_revenue_control_ok = len([row for row in product_control_rows if row.get("sun_revenue_control_status") == "OK"])
    sun_revenue_control_missing = len([row for row in product_control_rows if row.get("sun_revenue_control_status") == "Mangler Sun2-grunnlag"])
    raw_sessions_control_avvik = len([row for row in product_control_rows if row.get("sun_sessions_control_status") == "Avvik"])
    product_control_ok = len([row for row in product_control_rows if row.get("product_sales_control_status") == "OK"])
    product_control_missing = len([row for row in product_control_rows if row.get("product_sales_control_status") == "Mangler Sun2-grunnlag"])
    return {
        "title": "Soling · Oppgjør",
        "subtitle": "Manuell innlasting av Altera-kreditnotaer og kontroll av skjemaets egne summer.",
        "cards": [
            api_card("Oppgjør importert", total_settlements, "stk", f"{parsed_period_count} perioder tolket", "sun2", href="/soling/oppgjor"),
            api_card(
                "Siste import",
                format_local_datetime(latest_import_settlement.imported_at) if latest_import_settlement else "-",
                "",
                latest_import_settlement.period_label if latest_import_settlement else "Ingen importerte oppgjør",
                "status",
                href="/soling/oppgjor",
            ),
            api_card("Mangler periode", unknown_period_count, "stk", "Krever manuell kontroll eller OCR", "status", href="/soling/oppgjor"),
            api_card("Kontroll soling", sun_revenue_control_ok, "OK", f"{sun_revenue_control_missing} mangler Sun2-grunnlag", "sun2", href="/soling/oppgjor"),
            api_card("Råtimeavvik", raw_sessions_control_avvik, "stk", "Rå enkelttimer mot Sun2 månedsomsetning", "revenue" if raw_sessions_control_avvik else "status", href="/soling/oppgjor"),
            api_card("Kontroll produktsalg", product_control_ok, "OK", f"{product_control_missing} mangler Sun2-grunnlag", "sun2", href="/soling/oppgjor"),
        ],
        "charts": [],
        "tables": [
            api_table(
                "Solingsoppgjør",
                [
                    "period_label",
                    "period_start",
                    "period_end",
                    "status",
                    "sum_check_status",
                    "sun_revenue_ex_vat",
                    "sun_revenue_source_ex_vat",
                    "sun_revenue_diff_ex_vat",
                    "sun_revenue_control_status",
                    "sun_sessions_count",
                    "sun_sessions_source_ex_vat",
                    "sun_sessions_diff_vs_finance_ex_vat",
                    "sun_sessions_diff_vs_finance_gross_ex_vat",
                    "sun_sessions_control_status",
                    "sun_finance_gross_ex_vat",
                    "product_sales_ex_vat",
                    "product_sales_source_ex_vat",
                    "product_sales_diff_ex_vat",
                    "product_sales_control_status",
                    "transaction_fee_ex_vat",
                    "service_fee_ex_vat",
                    "marketing_sms_fee_ex_vat",
                    "marketing_email_fee_ex_vat",
                    "sum_ex_vat",
                    "vat_25_percent",
                    "payout_inc_vat",
                    "parser_confidence",
                    "attachment_filename",
                    "imported_at",
                ],
                product_control_rows,
            ),
        ],
        "actions": [],
        "uploadEndpoint": "/api/actions/soling/upload-settlement",
    }


async def parking_settlement_module_payload(session) -> Dict[str, Any]:
    settlement_rows = (
        await session.execute(
            select(SettlementImport)
            .where(SettlementImport.provider == PARKING_SETTLEMENT_PROVIDER)
            .order_by(SettlementImport.period_start.desc().nullslast(), SettlementImport.imported_at.desc())
            .limit(200)
        )
    ).scalars().all()
    latest_import_settlement = (
        await session.execute(
            select(SettlementImport)
            .where(SettlementImport.provider == PARKING_SETTLEMENT_PROVIDER)
            .order_by(SettlementImport.imported_at.desc())
            .limit(1)
        )
    ).scalars().first()
    changed_any = False
    for row in settlement_rows:
        changed_any = ensure_settlement_parsed(row) or changed_any
    if changed_any:
        await session.commit()

    total_settlements = (
        await session.execute(
            select(func.count(SettlementImport.id)).where(SettlementImport.provider == PARKING_SETTLEMENT_PROVIDER)
        )
    ).scalar_one()
    unknown_period_count = (
        await session.execute(
            select(func.count(SettlementImport.id))
            .where(SettlementImport.provider == PARKING_SETTLEMENT_PROVIDER)
            .where(SettlementImport.period_start.is_(None))
        )
    ).scalar_one()
    parsed_period_count = max(0, int_or_zero(total_settlements) - int_or_zero(unknown_period_count))
    control_rows = []
    for row in settlement_rows[:36]:
        if not row.period_start or not row.period_end:
            continue
        start_dt = datetime.combine(row.period_start, time.min)
        end_dt = datetime.combine(row.period_end + timedelta(days=1), time.min)
        source_summaries = await parking_period_source_summaries(session, start_dt, end_dt)
        easypark_summary = source_summaries["easypark"]
        flowbird_summary = source_summaries["flowbird"]
        other_summary = source_summaries["other"]
        count_value = int_or_zero(easypark_summary.get("count")) + int_or_zero(flowbird_summary.get("count")) + int_or_zero(other_summary.get("count"))
        paid_value = (
            float_or_zero(easypark_summary.get("paid_inc_vat"))
            + float_or_zero(flowbird_summary.get("paid_inc_vat"))
            + float_or_zero(other_summary.get("paid_inc_vat"))
        )
        flowbird_ex_vat = round(float_or_zero(flowbird_summary.get("paid_ex_vat")), 2)
        easypark_source_ex_vat = round(float_or_zero(easypark_summary.get("paid_ex_vat")), 2)
        gross_coin_card = settlement_parsed_float(row.parsed, "gross_coin_card_ex_vat")
        easypark_ex_vat = settlement_parsed_float(row.parsed, "easypark_ex_vat")
        flowbird_source_diff = round(gross_coin_card - flowbird_ex_vat, 2) if gross_coin_card is not None else None
        easypark_source_diff = round(easypark_ex_vat - easypark_source_ex_vat, 2) if easypark_ex_vat is not None else None
        control_rows.append(
            {
                "period_label": row.period_label,
                "period_start": row.period_start.isoformat(),
                "period_end": row.period_end.isoformat(),
                "parking_count": count_value,
                "parking_paid": round(paid_value, 2),
                "flowbird_source_count": int_or_zero(flowbird_summary.get("count")),
                "flowbird_source_paid_ex_vat": flowbird_ex_vat,
                "gross_coin_card_ex_vat": settlement_parsed_value(row.parsed, "gross_coin_card_ex_vat"),
                "flowbird_source_diff_ex_vat": flowbird_source_diff,
                "easypark_source_count": int_or_zero(easypark_summary.get("count")),
                "easypark_source_paid_ex_vat": easypark_source_ex_vat,
                "easypark_source_diff_ex_vat": easypark_source_diff,
                "other_source_count": int_or_zero(other_summary.get("count")),
                "easypark_ex_vat": settlement_parsed_value(row.parsed, "easypark_ex_vat"),
                "payout_inc_vat": settlement_parsed_value(row.parsed, "payout_inc_vat"),
                "average_paid": round(paid_value / count_value, 2) if count_value else None,
                "attachment_filename": row.attachment_filename,
                "status": row.status,
            }
        )
    actions = [
        {
            "key": "fetch-parking-settlements",
            "label": "Hent Park Nordic fra Gmail",
            "method": "POST",
            "path": "/api/actions/parkering/fetch-settlements",
            "confirm": f"Hente nye parkeringsoppgjør fra Gmail fra {PARKING_SETTLEMENT_SENDER}?",
            "tone": "primary",
        }
    ]
    return {
        "title": "Parkering · Oppgjør",
        "subtitle": "Importer månedlige parkeringsoppgjør fra Gmail og kontroller EasyPark og Flowbird/Park Nordic mot interne kildetall.",
        "cards": [
            api_card(
                "Oppgjør importert",
                total_settlements,
                "stk",
                f"{parsed_period_count} perioder tolket",
                "parking",
                href="/parkering/oppgjor",
            ),
            api_card(
                "Siste import",
                format_local_datetime(latest_import_settlement.imported_at) if latest_import_settlement else "-",
                "",
                latest_import_settlement.period_label if latest_import_settlement else "Ingen importerte oppgjør",
                "status",
                href="/parkering/oppgjor",
            ),
            api_card(
                "Ikke periodetolket",
                unknown_period_count,
                "stk",
                "Krever manuell kontroll av filnavn/emne",
                "status",
                href="/parkering/oppgjor",
            ),
            api_card(
                "Gmail",
                "Klar" if settlement_gmail_configured() else "Mangler",
                "",
                "Bruker egne SETTLEMENT-vars eller EasyPark-vars som fallback",
                "status",
                href="/admin/teknisk",
            ),
        ],
        "charts": [],
        "tables": [
            api_table(
                "Parkeringsoppgjør",
                [
                    "period_label",
                    "period_start",
                    "period_end",
                    "status",
                    "easypark_ex_vat",
                    "easypark_inc_vat_estimate",
                    "payout_inc_vat",
                    "parser_confidence",
                    "attachment_filename",
                    "email_date",
                    "imported_at",
                ],
                [settlement_row_api(row) for row in settlement_rows],
            ),
            api_table(
                "Kontroll mot interne parkeringstall",
                [
                    "period_label",
                    "period_start",
                    "period_end",
                    "parking_count",
                    "parking_paid",
                    "flowbird_source_count",
                    "flowbird_source_paid_ex_vat",
                    "gross_coin_card_ex_vat",
                    "flowbird_source_diff_ex_vat",
                    "easypark_source_count",
                    "easypark_source_paid_ex_vat",
                    "easypark_source_diff_ex_vat",
                    "other_source_count",
                    "easypark_ex_vat",
                    "payout_inc_vat",
                    "average_paid",
                    "attachment_filename",
                    "status",
                ],
                control_rows,
            ),
        ],
        "actions": actions,
    }


SETTLEMENT_PARSED_FIELD_LABELS: list[tuple[str, str, str]] = [
    ("Rapportdato", "report_date", "Dato i selve oppgjørsrapporten."),
    ("Rapportperiode", "reported_period_label", "Periode slik den står i skjemaet."),
    ("Driftssted nr.", "site_number", "Park Nordic sitt driftsstednummer."),
    ("Driftssted", "site_name", "Navn på driftssted i skjemaet."),
    ("Oppdragsgiver nr.", "customer_number", "Park Nordic sitt kundenummer."),
    ("Oppdragsgiver", "customer_name", "Kundenavn i skjemaet."),
    ("Antall automater", "machine_count", "Antall automater oppgitt i skjemaet."),
    ("Brutto mynt/kort eks. mva", "gross_coin_card_ex_vat", "Beløp i kolonnen Oms. eks. mva."),
    ("EasyPark eks. mva", "easypark_ex_vat", "Beløp i kolonnen Oms. eks. mva."),
    ("EasyPark estimert inkl. mva", "easypark_inc_vat_estimate", "Beregnet som EasyPark eks. mva * 1,25."),
    ("Fratrekk eks. mva", "settlement_fee_ex_vat", "Fratrekk for tømming, telling og kortavregning."),
    ("Nettoinntekter mynt/kort eks. mva", "revenue_basis_ex_vat", "Første summeringsrad etter fratrekk."),
    ("Andel mynt/kort", "revenue_share_percent", "Andel i prosent fra samme summeringsrad."),
    ("Sum mynt/kort eks. mva", "revenue_share_ex_vat", "Sum-kolonnen for hovedomsetning."),
    ("Langtidsparkering eks. mva", "long_term_parking_ex_vat", "Andre uetiketterte tallrad etter fratrekk."),
    ("Andel langtidsparkering", "long_term_share_percent", "Andel i prosent for langtidsparkering."),
    ("Sum langtidsparkering eks. mva", "long_term_share_ex_vat", "Sum-kolonnen for langtidsparkering."),
    ("Netto kontrollavgifter eks. mva", "control_fee_net_ex_vat", "Tredje uetiketterte tallrad etter fratrekk."),
    ("Andel kontrollavgifter", "control_fee_share_percent", "Andel i prosent for kontrollavgifter."),
    ("Sum kontrollavgifter eks. mva", "control_fee_share_ex_vat", "Sum-kolonnen for kontrollavgifter."),
    ("Grunnlag omsetning eks. mva", "total_basis_ex_vat", "Totalsum før mva."),
    ("Totalt oppgjør eks. mva", "total_share_ex_vat", "Sum til grunnlag for mva."),
    ("25% mva", "vat_25_percent", "Mva-linje i skjemaet."),
    ("Til utbetaling inkl. mva", "payout_inc_vat", "Sluttsum oppgitt i skjemaet."),
    ("Kontakt e-post", "contact_email", "E-postadresse funnet i skjemaet."),
]


SUN_SETTLEMENT_PARSED_FIELD_LABELS: list[tuple[str, str, str]] = [
    ("Kreditnotanr.", "credit_note_number", "Kreditnotanummer fra Altera."),
    ("Kreditnotadato", "credit_note_date", "Dato på kreditnotaen."),
    ("Leveransedato", "delivery_date", "Dato/periodegrunnlag fra skjemaet."),
    ("Leverandør", "supplier_name", "Leverandør funnet i skjemaet."),
    ("Leverandør org.nr.", "supplier_org_no", "Organisasjonsnummer funnet i skjemaet."),
    ("Kunde", "customer_name", "Kundenavn funnet i skjemaet."),
    ("Solomsetning eks. mva", "sun_revenue_ex_vat", "Beløp fra linjen Solomsetning for perioden."),
    ("Produktsalg eks. mva", "product_sales_ex_vat", "Beløp fra linjen Produktsalg for perioden."),
    ("Transaksjonskostnad eks. mva", "transaction_fee_ex_vat", "Fratrekk fra linjen Transaksjonskostnad."),
    ("Serviceavtale eks. mva", "service_fee_ex_vat", "Fratrekk fra linjen Serviceavtale."),
    ("Markedsføring SMS eks. mva", "marketing_sms_fee_ex_vat", "Eventuelt fratrekk for markedsføring på SMS."),
    ("Markedsføring e-post eks. mva", "marketing_email_fee_ex_vat", "Eventuelt fratrekk for markedsføring på e-post."),
    ("Sum eks. mva", "sum_ex_vat", "Sum eks. mva fra skjemaet."),
    ("25% mva", "vat_25_percent", "Mva-linje fra skjemaet."),
    ("Beløp NOK", "payout_inc_vat", "Sluttsum fra skjemaet."),
]
