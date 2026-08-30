"""Mail domain services."""

from datetime import datetime
from datetime import timedelta
from email.utils import parsedate_to_datetime
from fibaro_core.models import SettlementImport
from fibaro_core.services.settlements.parsing import PARKING_SETTLEMENT_PROVIDER
from fibaro_core.services.settlements.parsing import decoded_mime_header
from fibaro_core.services.settlements.parsing import iter_message_attachments
from fibaro_core.services.settlements.parsing import parse_parking_settlement_attachment
from fibaro_core.services.settlements.parsing import parse_settlement_period
from fibaro_core.services.settlements.parsing import settlement_parsed_meta
from sqlalchemy import select
from time_formatting import LOCAL_TZ
from typing import Any
from typing import Dict
from typing import Optional
from value_parsing import float_or_zero
import email as email_lib
import imaplib
import os


def message_email_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except Exception:
        return None
    if parsed.tzinfo:
        return parsed.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return parsed


def settlement_gmail_credentials() -> tuple[str, str]:
    gmail_email = os.getenv("SETTLEMENT_GMAIL_EMAIL") or os.getenv("EASYPARK_GMAIL_EMAIL")
    app_password = os.getenv("SETTLEMENT_GMAIL_APP_PASSWORD") or os.getenv("EASYPARK_GMAIL_APP_PASSWORD")
    if not gmail_email:
        raise RuntimeError("Mangler SETTLEMENT_GMAIL_EMAIL eller EASYPARK_GMAIL_EMAIL.")
    if not app_password:
        raise RuntimeError("Mangler SETTLEMENT_GMAIL_APP_PASSWORD eller EASYPARK_GMAIL_APP_PASSWORD.")
    return gmail_email, app_password.replace(" ", "")


def settlement_mailboxes() -> list[str]:
    configured = os.getenv("SETTLEMENT_GMAIL_MAILBOXES")
    if not configured:
        return ["INBOX", "__GMAIL_ALL__"]
    return [item.strip() for item in configured.split(",") if item.strip()]


def settlement_gmail_configured() -> bool:
    return bool(
        (os.getenv("SETTLEMENT_GMAIL_EMAIL") or os.getenv("EASYPARK_GMAIL_EMAIL"))
        and (os.getenv("SETTLEMENT_GMAIL_APP_PASSWORD") or os.getenv("EASYPARK_GMAIL_APP_PASSWORD"))
    )


def select_gmail_mailbox(mailbox: imaplib.IMAP4_SSL, mailbox_name: str) -> str:
    candidates = [mailbox_name, f'"{mailbox_name}"']
    if " " in mailbox_name or "/" in mailbox_name:
        candidates = [f'"{mailbox_name}"', mailbox_name]
    for candidate in candidates:
        try:
            status, _ = mailbox.select(candidate, readonly=True)
        except imaplib.IMAP4.error:
            continue
        if status == "OK":
            return status
    return "NO"


def parse_imap_mailbox_name(line: str) -> str:
    if ' "/" ' in line:
        name = line.rsplit(' "/" ', 1)[-1]
    elif ' "." ' in line:
        name = line.rsplit(' "." ', 1)[-1]
    else:
        name = line.split(" ", 1)[-1]
    return name.strip().strip('"')


def discover_gmail_all_mailbox(mailbox: imaplib.IMAP4_SSL) -> Optional[str]:
    try:
        status, data = mailbox.list()
    except imaplib.IMAP4.error:
        return None
    if status != "OK":
        return None
    for item in data or []:
        text_value = item.decode(errors="replace") if isinstance(item, bytes) else str(item)
        if "\\All" in text_value:
            return parse_imap_mailbox_name(text_value)
    return None


async def fetch_parking_settlements_from_gmail(session, since_days: int = 370, limit: int = 80) -> Dict[str, Any]:
    gmail_email, app_password = settlement_gmail_credentials()
    sender = os.getenv("PARKING_SETTLEMENT_SENDER", PARKING_SETTLEMENT_SENDER)
    imap_host = os.getenv("SETTLEMENT_GMAIL_IMAP_HOST", "imap.gmail.com")
    since = (datetime.now() - timedelta(days=max(1, since_days))).strftime("%d-%b-%Y")
    imported = 0
    skipped = 0
    scanned_messages = 0
    scanned_attachments = 0
    mailbox_errors: list[str] = []
    seen_message_keys: set[str] = set()
    seen_hashes: set[str] = set()

    with imaplib.IMAP4_SSL(imap_host) as mailbox:
        mailbox.login(gmail_email, app_password)
        mailbox_names = []
        for configured_mailbox in settlement_mailboxes():
            mailbox_name = discover_gmail_all_mailbox(mailbox) if configured_mailbox == "__GMAIL_ALL__" else configured_mailbox
            if mailbox_name and mailbox_name not in mailbox_names:
                mailbox_names.append(mailbox_name)
        for mailbox_name in mailbox_names:
            status = select_gmail_mailbox(mailbox, mailbox_name)
            if status != "OK":
                mailbox_errors.append(f"Kunne ikke åpne {mailbox_name}")
                continue
            status, data = mailbox.uid("search", None, f'(FROM "{sender}" SINCE "{since}")')
            if status != "OK" or not data or not data[0]:
                continue
            message_uids = data[0].split()[-limit:]
            for uid in message_uids:
                status, raw_data = mailbox.uid("fetch", uid, "(RFC822)")
                if status != "OK" or not raw_data:
                    continue
                raw_part = raw_data[0]
                if not isinstance(raw_part, tuple) or len(raw_part) < 2:
                    continue
                raw_message = raw_part[1]
                message = email_lib.message_from_bytes(raw_message)
                message_id = (message.get("Message-ID") or f"{mailbox_name}:{uid.decode(errors='ignore')}").strip()
                message_key = f"{mailbox_name}:{message_id}"
                if message_key in seen_message_keys:
                    continue
                seen_message_keys.add(message_key)
                scanned_messages += 1
                subject = decoded_mime_header(message.get("Subject"))
                sender_value = decoded_mime_header(message.get("From"))
                email_date = message_email_date(message.get("Date"))
                for attachment in iter_message_attachments(message):
                    scanned_attachments += 1
                    sha = attachment["sha256"]
                    if sha in seen_hashes:
                        skipped += 1
                        continue
                    seen_hashes.add(sha)
                    existing = (
                        await session.execute(
                            select(SettlementImport.id)
                            .where(SettlementImport.provider == PARKING_SETTLEMENT_PROVIDER)
                            .where(SettlementImport.attachment_sha256 == sha)
                            .limit(1)
                        )
                    ).scalars().first()
                    if existing:
                        skipped += 1
                        continue
                    parsed_settlement = parse_parking_settlement_attachment(
                        attachment["filename"],
                        attachment["content_type"],
                        attachment["bytes"],
                    )
                    period_start, period_end, period_label = parse_settlement_period(
                        f"{subject} {attachment['filename']}",
                        email_date,
                    )
                    if not period_start and parsed_settlement.get("reported_period_label"):
                        period_start, period_end, period_label = parse_settlement_period(
                            str(parsed_settlement.get("reported_period_label")),
                            email_date,
                        )
                    parser_meta = settlement_parsed_meta(parsed_settlement)
                    session.add(
                        SettlementImport(
                            provider=PARKING_SETTLEMENT_PROVIDER,
                            source="gmail",
                            sender=sender_value,
                            gmail_message_id=message_id,
                            gmail_uid=uid.decode(errors="ignore"),
                            email_subject=subject,
                            email_date=email_date,
                            mailbox=mailbox_name,
                            period_start=period_start,
                            period_end=period_end,
                            period_label=period_label,
                            attachment_filename=attachment["filename"],
                            attachment_content_type=attachment["content_type"],
                            attachment_sha256=sha,
                            attachment_size=len(attachment["bytes"]),
                            attachment_bytes=attachment["bytes"],
                            status="tolket" if float_or_zero(parser_meta.get("confidence")) >= 0.6 else "krever kontroll",
                            parsed=parsed_settlement,
                            raw={
                                "mailbox": mailbox_name,
                                "sender_filter": sender,
                                "gmail_account": gmail_email,
                                "settlement_parser": parser_meta,
                            },
                        )
                    )
                    imported += 1
    return {
        "imported": imported,
        "skipped": skipped,
        "scanned_messages": scanned_messages,
        "scanned_attachments": scanned_attachments,
        "sender": sender,
        "since_days": since_days,
        "mailbox_errors": mailbox_errors,
    }


PARKING_SETTLEMENT_SENDER = os.getenv("PARKING_SETTLEMENT_SENDER", "fredrik@parknordic.no")
