"""Physical room identities, independent of the September 2026 terminal rewiring."""

from datetime import date, datetime, timezone
import hashlib
import json
import re
from zoneinfo import ZoneInfo


CUTOVER_DATE = date(2026, 9, 11)
MAPPING_VERSION = "terminal-2026-09-11-v1"
LOCAL_TZ = ZoneInfo("Europe/Oslo")
LEGACY_BEDS = {**{n: str(639 + n) for n in range(1, 10)}, 10: "679", 11: "680", 12: "681"}
CURRENT_BEDS = {**LEGACY_BEDS, 10: "649", 11: "679", 12: "680"}


def local_date(value, *, utc_naive=False):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(value, datetime):
        if value.tzinfo is None and utc_naive:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(LOCAL_TZ).date() if value.tzinfo else value.date()
    return value if isinstance(value, date) else None


def display_number(name):
    match = re.search(r"\brom\s*0*(\d{1,2})\b", str(name or ""), re.IGNORECASE)
    return int(match[1]) if match else None


def room_identity_for_display(number, event_at=None):
    if number not in CURRENT_BEDS:
        return {"room_id": None, "physical_room_number": None, "display_room_number": None, "sun2_bed_id": None}
    day = local_date(event_at)
    beds = LEGACY_BEDS if day and day < CUTOVER_DATE else CURRENT_BEDS
    # These database IDs are stable references used by images, assets and alarms.
    stable_number = number if number < 10 else number + 1
    return {
        "room_id": f"rom-{stable_number:02d}",
        "physical_room_number": number,
        "display_room_number": number,
        "sun2_bed_id": beds[number],
    }


SUN2_ROOM_MAP_BY_DISPLAY = {n: room_identity_for_display(n) for n in CURRENT_BEDS}
SUN2_ROOM_UNKNOWN_OLD_10 = {
    "room_id": "rom-10", "physical_room_number": None,
    "display_room_number": None, "sun2_bed_id": "649",
}


def session_identity(source_name, event_at, observed_at=None):
    """Decode the label as observed, then map its output to the room at event time.

    A new SUN2 download relabels old transactions. Original daily CSV files keep
    their old labels; callers must supply the label observation epoch explicitly.
    """
    day = local_date(event_at)
    observed_day = local_date(observed_at, utc_naive=True) or day
    number = display_number(source_name)
    unnamed = str(source_name or "").strip() in {".", "...", "-"}
    if day and day < CUTOVER_DATE:
        if observed_day and observed_day >= CUTOVER_DATE:
            if unnamed:
                number = 12
            elif number == 10:
                return dict(SUN2_ROOM_UNKNOWN_OLD_10)
            elif number in (11, 12):
                number -= 1
        elif unnamed:
            return dict(SUN2_ROOM_UNKNOWN_OLD_10)
    return room_identity_for_display(number, day)


def current_bed_identity(name, bed_id):
    bed_id = str(bed_id or "").strip()
    number = next((n for n, value in CURRENT_BEDS.items() if value == bed_id), None)
    identity = room_identity_for_display(number)
    identity["sun2_bed_id"] = bed_id or None
    return identity


def canonical_session_room_id(room_id, bed_id, event_at=None):
    day = local_date(event_at)
    beds = CURRENT_BEDS if day and day >= CUTOVER_DATE else LEGACY_BEDS
    number = next((n for n, value in beds.items() if value == str(bed_id or "")), None)
    if number:
        return room_identity_for_display(number, day)["room_id"]
    return room_id


def canonical_room_name(source_name, identity):
    number = identity.get("display_room_number")
    if number and display_number(source_name) != number:
        return f"Rom {number}"
    return source_name


def stable_session_id(row, identity):
    """Versioned identity must not change when SUN2 renames a terminal output."""
    started = row.started_at
    if started.tzinfo:
        started = started.astimezone(LOCAL_TZ).replace(tzinfo=None)
    payload = {
        "started_at": started.isoformat(timespec="minutes"),
        "room": identity.get("room_id") or str(row.source_room_name or row.room or "").strip(),
        "user": str(row.sun2_user_id or row.user_identifier or row.user_name or "").strip(),
        "duration": float(row.duration_minutes) if row.duration_minutes is not None else None,
        "paid": float(row.paid_amount_kr) if row.paid_amount_kr is not None else None,
    }
    return "stable:v2:" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def mapping_provenance(identity, observed_at, original_source_id=None):
    return {
        "version": MAPPING_VERSION,
        "label_observed_at": str(observed_at) if observed_at else None,
        "display_room_number": identity.get("display_room_number"),
        "terminal_bed_id": identity.get("sun2_bed_id"),
        "input_source_session_id": original_source_id,
    }
