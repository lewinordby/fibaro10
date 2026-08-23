import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, Optional
from zoneinfo import ZoneInfo


LOCAL_TZ = ZoneInfo("Europe/Oslo")


def reconcile_roborock_schedule_snapshot(
    schedules: Iterable[Any],
    seen_schedule_ids: set[str],
    deleted_at: datetime,
) -> int:
    deleted_count = 0
    for schedule in schedules:
        if str(schedule.schedule_id) in seen_schedule_ids:
            schedule.deleted_at = None
            continue
        if schedule.deleted_at is None:
            schedule.deleted_at = deleted_at
            schedule.enabled = False
            deleted_count += 1
    return deleted_count

ROBOROCK_STATE_LABELS = {
    1: "Starter opp",
    2: "Venter",
    3: "Hviler",
    4: "Klar",
    5: "Fjernstyring",
    6: "Rengjør",
    7: "Returnerer til dock",
    8: "Lader",
    9: "Ladefeil",
    10: "Pause",
    11: "Flekkrengjøring",
    12: "Feil",
    13: "Slår av",
    14: "Oppdaterer",
    15: "Dokker",
    16: "Går til målpunkt",
    17: "Sonerengjøring",
    18: "Romrengjøring",
    22: "Tømmer støvbeholder",
    23: "Vasker mopp",
    26: "Går til moppvask",
    28: "Kartlegger",
}

ROBOROCK_ERROR_LABELS = {
    0: "Ingen feil",
    1: "Laser/sensor-feil",
    2: "Støtfanger sitter fast",
    3: "Hjul henger",
    4: "Kantsensor må rengjøres",
    5: "Hovedbørste sitter fast",
    6: "Sidebørste sitter fast",
    7: "Hjul sitter fast",
    8: "Robot sitter fast",
    9: "Støvbeholder mangler",
    10: "Filter blokkert eller vått",
    11: "Magnetstripe/no-go oppdaget",
    12: "Lavt batteri",
    13: "Ladefeil",
    14: "Batterifeil",
    15: "Vegg-/avstandssensor må rengjøres",
    16: "Robot står skjevt",
    17: "Sidebørstemodul-feil",
    18: "Viftefeil",
    21: "Vertikal støtfanger trykket inn",
    22: "Dock-posisjonsfeil",
    23: "Dock-lokalisering mislyktes",
    24: "No-go-sone eller usynlig vegg",
    26: "Vannfilter må rengjøres",
}

ROBOROCK_FAN_LABELS = {
    105: "Av",
    101: "Stille",
    102: "Balansert",
    103: "Turbo",
    104: "Maks",
    108: "Maks+",
}

ROBOROCK_MOP_LABELS = {
    300: "Standard",
    301: "Dyp",
    302: "Tilpasset",
    303: "Dyp+",
    304: "Hurtig",
    306: "Smart",
}

ROBOROCK_WATER_LABELS = {
    200: "Av",
    201: "Lav",
    202: "Medium",
    203: "Høy",
    204: "Tilpasset",
    207: "Tilpasset",
    208: "Maks",
    209: "Smart",
}

ROBOROCK_CHARGE_LABELS = {
    0: "Ikke på lader",
    1: "På lader",
    2: "Lader",
}

ROBOROCK_DOCK_TYPE_LABELS = {
    0: "Ingen dokk",
    1: "Automatisk tømmestasjon",
    3: "Tøm, vask og fyll",
    5: "Auto-Empty Dock Pure",
    6: "S7 Max Ultra Dock",
    7: "S8 Dock",
    8: "Qrevo P10-dokk",
    9: "P10 Pro-dokk",
    10: "S8 MaxV Ultra Dock",
    14: "Qrevo Master-dokk",
    15: "Qrevo S-dokk",
    17: "Qrevo Curv-dokk",
}

ROBOROCK_DOCK_ERROR_LABELS = {
    0: "Ingen feil",
    32: "Støvbeholder eller filter mangler",
    33: "Feil på tømmestasjonens vifte",
    34: "Luftkanal blokkert eller støvpose full",
    35: "Spenningsfeil i tømmestasjon",
    38: "Rentvann mangler",
    39: "Skittentvannstank full",
    42: "Vedlikeholdsbørste sitter fast",
    44: "Lås på skittentvannstank er åpen",
    46: "Støvbeholder mangler",
    53: "Vaskekar fullt eller blokkert",
}

ROBOROCK_RESOURCE_STATUS_LABELS = {
    "okay": "OK",
    "ok": "OK",
    "normal": "OK",
    "installed": "OK",
    "present": "OK",
    "out_of_water": "Tom",
    "out_of_water_2": "Tom",
    "low_water": "Lite",
    "checking": "Kontrollerer",
    "refill_error": "Påfyllingsfeil",
    "full_not_installed": "Full eller ikke montert",
    "full_not_installed_2": "Full eller ikke montert",
    "not_installed_or_full": "Full eller ikke montert",
    "drain_error": "Tømmefeil",
    "not_installed": "Ikke montert",
    "full": "Full",
    "empty_not_installed": "Tom eller ikke montert",
    "low_detergent": "Lite",
    "disabled": "Deaktivert",
}

DREAME_WATER_WARNING_LABELS = {
    -1: "Ikke støttet",
    0: "OK",
    1: "Tomt - varsel kvittert",
    2: "Tomt",
    3: "Tomt etter rengjøring",
    4: "Ikke nok vann til rengjøring",
    5: "Lite vann",
    6: "Rentvannstank ikke montert",
}

DREAME_BLOCKING_WATER_WARNING_CODES = {1, 2, 3, 4, 6}

DREAME_WATER_MODE_LABELS = {
    0: "Av",
    1: "Lav",
    2: "Medium",
    3: "Høy",
}

ROBOROCK_TELEMETRY_EVENT_FIELDS = {
    "state_code": ("robot", "Robotstatus"),
    "is_charging": ("lading", "Lading"),
    "error_code": ("robot", "Robotfeil"),
    "dock_error_status": ("dokk", "Dokkfeil"),
    "clear_water_status": ("vann", "Rentvann i dokk"),
    "dirty_water_status": ("vann", "Skittentvann i dokk"),
    "dust_bag_status": ("dokk", "Støvpose"),
    "clean_fluid_status": ("vann", "Rengjøringsmiddel"),
    "water_shortage_status": ("vann", "Vannmangel i robot"),
    "water_box_status": ("vann", "Vanntank i robot"),
    "water_box_carriage_status": ("vann", "Mopp montert"),
    "water_box_filter_status": ("vann", "Vannfilter"),
    "dust_collection_status": ("dokk", "Støvtømming"),
    "wash_status": ("dokk", "Moppevask"),
    "wash_phase": ("dokk", "Vaskefase"),
    "dry_status": ("dokk", "Tørking"),
    "auto_dust_collection": ("innstilling", "Automatisk støvtømming"),
}

ROBOROCK_DAYS = {
    "0": "søn",
    "1": "man",
    "2": "tir",
    "3": "ons",
    "4": "tor",
    "5": "fre",
    "6": "lør",
    "7": "søn",
    "SUN": "søn",
    "MON": "man",
    "TUE": "tir",
    "WED": "ons",
    "THU": "tor",
    "FRI": "fre",
    "SAT": "lør",
}


def int_value(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def bool_value(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "ja", "på", "on"}:
        return True
    if text in {"0", "false", "no", "nei", "av", "off"}:
        return False
    return None


def roborock_label(mapping: Dict[int, str], value: Any, fallback_prefix: str = "Kode") -> str:
    number = int_value(value)
    if number is None:
        return "-"
    return mapping.get(number, f"{fallback_prefix} {number}")


def roborock_state_label(value: Any) -> str:
    return roborock_label(ROBOROCK_STATE_LABELS, value, "Statuskode")


def roborock_error_label(value: Any) -> str:
    return roborock_label(ROBOROCK_ERROR_LABELS, value, "Feilkode")


def roborock_fan_label(value: Any) -> str:
    return roborock_label(ROBOROCK_FAN_LABELS, value, "Nivå")


def roborock_mop_label(value: Any) -> str:
    return roborock_label(ROBOROCK_MOP_LABELS, value, "Nivå")


def roborock_water_label(value: Any) -> str:
    return roborock_label(ROBOROCK_WATER_LABELS, value, "Nivå")


def roborock_charge_label(value: Any) -> str:
    return roborock_label(ROBOROCK_CHARGE_LABELS, value, "Ladestatus")


def roborock_dock_type_label(value: Any) -> str:
    return roborock_label(ROBOROCK_DOCK_TYPE_LABELS, value, "Dokktype")


def roborock_dock_error_label(value: Any) -> str:
    return roborock_label(ROBOROCK_DOCK_ERROR_LABELS, value, "Dokkfeil")


def roborock_resource_status_label(value: Any, name: Any = None) -> str:
    if name:
        key = str(name).strip().lower()
        if key in ROBOROCK_RESOURCE_STATUS_LABELS:
            return ROBOROCK_RESOURCE_STATUS_LABELS[key]
        return key.replace("_", " ").capitalize()
    number = int_value(value)
    if number is None:
        return "Ikke støttet"
    return "OK" if number == 0 else f"Statuskode {number}"


def cleaning_water_warning_label(value: Any, provider: Any = None) -> str:
    number = int_value(value)
    if number is None:
        return "Ikke støttet"
    if str(provider or "").strip().lower() == "dreame":
        return DREAME_WATER_WARNING_LABELS.get(number, f"Vannvarsel {number}")
    return "OK" if number == 0 else "Vannmangel"


def cleaning_water_warning_blocks(value: Any, provider: Any = None) -> bool:
    number = int_value(value)
    if number is None or number == 0:
        return False
    if str(provider or "").strip().lower() == "dreame":
        return number in DREAME_BLOCKING_WATER_WARNING_CODES
    return True


def cleaning_water_mode_label(value: Any, provider: Any = None) -> str:
    number = int_value(value)
    if number is None:
        return "Ikke støttet"
    if str(provider or "").strip().lower() == "dreame":
        return DREAME_WATER_MODE_LABELS.get(number, f"Nivå {number}")
    return roborock_water_label(number)


def roborock_telemetry_value_label(
    field_name: str,
    value: Any,
    name: Any = None,
    provider: Any = None,
) -> str:
    if value is None and not name:
        return "Ikke støttet"
    if field_name == "state_code":
        return roborock_state_label(value)
    if field_name == "error_code":
        return roborock_error_label(value)
    if field_name == "dock_type":
        return roborock_dock_type_label(value)
    if field_name == "dock_error_status":
        return roborock_dock_error_label(value)
    if field_name == "charge_status":
        return roborock_charge_label(value)
    if field_name == "water_box_filter_status":
        number = int_value(value)
        if number is None:
            return "Ikke støttet"
        # The Qrevo-family reports the normal installed filter state as DSS value 2.
        return "OK" if number in {0, 2} else f"Statuskode {number}"
    if field_name in {
        "clear_water_status",
        "dirty_water_status",
        "dust_bag_status",
        "clean_fluid_status",
    }:
        return roborock_resource_status_label(value, name)
    if field_name == "water_shortage_status":
        return cleaning_water_warning_label(value, provider)
    if field_name == "water_box_mode":
        return cleaning_water_mode_label(value, provider)
    if field_name in {"water_box_status", "water_box_carriage_status"}:
        number = int_value(value)
        if number is None:
            return "Ikke støttet"
        return "Montert" if number != 0 else "Ikke montert"
    if field_name == "rssi":
        return roborock_signal_label(value)
    if field_name in {"is_charging", "in_cleaning", "in_returning", "auto_dust_collection", "wash_ready"}:
        return roborock_bool_label(value)
    if field_name == "battery" and value is not None:
        return f"{int_value(value)} %"
    return str(value) if value is not None else "Ikke støttet"


def roborock_telemetry_changes(
    previous: Dict[str, Any] | None,
    current: Dict[str, Any],
    provider: Any = None,
) -> list[Dict[str, Any]]:
    if not previous:
        return []
    changes = []
    for field_name, (category, title) in ROBOROCK_TELEMETRY_EVENT_FIELDS.items():
        old_value = previous.get(field_name)
        new_value = current.get(field_name)
        if old_value == new_value:
            continue
        name_key = field_name.replace("_status", "_status_name")
        old_name = previous.get(name_key)
        new_name = current.get(name_key)
        old_label = roborock_telemetry_value_label(field_name, old_value, old_name, provider)
        new_label = roborock_telemetry_value_label(field_name, new_value, new_name, provider)
        severity = "info"
        if field_name in {"error_code", "dock_error_status"} and int_value(new_value) not in {None, 0}:
            severity = "critical"
        elif field_name in {
            "clear_water_status",
            "dirty_water_status",
            "dust_bag_status",
            "clean_fluid_status",
            "water_shortage_status",
            "water_box_filter_status",
        } and new_label not in {"OK", "Ikke støttet", "0"}:
            severity = "warning"
        changes.append(
            {
                "category": category,
                "field_name": field_name,
                "title": (
                    "Vannvarsel"
                    if field_name == "water_shortage_status"
                    and str(provider or "").strip().lower() == "dreame"
                    else title
                ),
                "previous_value": None if old_value is None else str(old_value),
                "current_value": None if new_value is None else str(new_value),
                "previous_label": old_label,
                "current_label": new_label,
                "severity": severity,
            }
        )
    return changes


def roborock_signal_label(value: Any) -> str:
    rssi = int_value(value)
    if rssi is None:
        return "-"
    if rssi >= -55:
        quality = "svært bra"
    elif rssi >= -67:
        quality = "bra"
    elif rssi >= -75:
        quality = "svak"
    else:
        quality = "dårlig"
    return f"{quality} ({rssi} dBm)"


def roborock_bool_label(value: Any) -> str:
    if value is None:
        return "-"
    return "Ja" if bool_value(value) else "Nei"


def roborock_job_status(complete: Any, error_code: Any, end_at: Any) -> tuple[str, str]:
    error = int_value(error_code)
    if error not in {None, 0}:
        return "error", "Feil"
    if end_at is None:
        return "running", "Pågår"
    if bool_value(complete):
        return "complete", "Fullført"
    return "stopped", "Avbrutt"


def _roborock_row_value(row: Any, field_name: str) -> Any:
    if isinstance(row, Mapping):
        return row.get(field_name)
    return getattr(row, field_name, None)


def _roborock_row_timestamp(row: Any) -> Optional[datetime]:
    value = _roborock_row_value(row, "timestamp")
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo is None else value.astimezone(LOCAL_TZ).replace(tzinfo=None)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed.replace(tzinfo=None) if parsed.tzinfo is None else parsed.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return None


def roborock_active_cycle_summary(status_rows: list[Any]) -> Optional[Dict[str, Any]]:
    """Describe a Roborock cycle that is active even while the robot pauses in its dock."""
    ordered = sorted(
        (row for row in status_rows if _roborock_row_timestamp(row) is not None),
        key=lambda row: _roborock_row_timestamp(row) or datetime.min,
        reverse=True,
    )
    if not ordered or bool_value(_roborock_row_value(ordered[0], "in_cleaning")) is not True:
        return None

    active_rows = []
    for row in ordered:
        if bool_value(_roborock_row_value(row, "in_cleaning")) is not True:
            break
        active_rows.append(row)

    oldest_active = active_rows[-1]
    started_at = _roborock_row_timestamp(oldest_active)
    first_clean_seconds = int_value(_roborock_row_value(oldest_active, "clean_time_seconds"))
    if started_at and first_clean_seconds and 0 < first_clean_seconds <= 15 * 60:
        started_at -= timedelta(seconds=first_clean_seconds)

    floor_state_codes = {6, 11, 17, 18}
    last_floor_at = next(
        (
            _roborock_row_timestamp(row)
            for row in active_rows
            if int_value(_roborock_row_value(row, "state_code")) in floor_state_codes
            and bool_value(_roborock_row_value(row, "in_returning")) is not True
        ),
        None,
    )

    dock_state_codes = {8, 22, 23}
    dock_suffix = []
    for row in active_rows:
        if int_value(_roborock_row_value(row, "state_code")) not in dock_state_codes:
            break
        dock_suffix.append(row)
    dock_since = _roborock_row_timestamp(dock_suffix[-1]) if dock_suffix else None

    latest = active_rows[0]
    state_code = int_value(_roborock_row_value(latest, "state_code"))
    returning = bool_value(_roborock_row_value(latest, "in_returning")) is True
    if state_code == 8:
        phase, phase_label = "charging_pause", "Lader i dokk under pågående jobb"
    elif state_code == 22:
        phase, phase_label = "emptying", "Tømmer støvbeholder under pågående jobb"
    elif state_code == 23:
        phase, phase_label = "washing_mop", "Vasker mopp under pågående jobb"
    elif state_code == 26:
        phase, phase_label = "mop_return", "På vei til moppvask"
    elif returning:
        phase, phase_label = "returning", "Returnerer til dokk"
    else:
        phase, phase_label = "cleaning", "Rengjør nå"

    clean_time_seconds = int_value(_roborock_row_value(latest, "clean_time_seconds"))
    return {
        "started_at": started_at,
        "last_floor_at": last_floor_at,
        "dock_since": dock_since,
        "last_observed_at": _roborock_row_timestamp(latest),
        "phase": phase,
        "phase_label": phase_label,
        "active_minutes": round(clean_time_seconds / 60, 1) if clean_time_seconds is not None else None,
        "cleaned_area_m2": _roborock_row_value(latest, "clean_area_m2"),
        "progress_percent": int_value(_roborock_row_value(latest, "clean_percent")),
        "battery": int_value(_roborock_row_value(latest, "battery")),
    }


def roborock_operational_readiness(
    *,
    cloud_online: Any,
    last_error: Any,
    error_code: Any,
    dock_error: str,
    clear_water: str,
    dirty_water: str,
    dust_bag: str,
    active: bool,
    data_age_minutes: Optional[int],
    robot_water: str = "Ikke støttet",
    robot_water_title: str = "Vann i robot",
    stale_after_minutes: int = 10,
) -> Dict[str, Any]:
    issues = []
    if cloud_online is False:
        issues.append("Ikke tilkoblet Roborock")
    if last_error:
        issues.append(str(last_error))
    if int_value(error_code) not in {None, 0}:
        issues.append(roborock_error_label(error_code))
    if data_age_minutes is None:
        issues.append("Ingen telemetri mottatt")
    elif data_age_minutes > stale_after_minutes:
        issues.append(f"Telemetri er {data_age_minutes} min gammel")
    issues.extend(
        roborock_resource_issues(
            dock_error,
            clear_water,
            dirty_water,
            dust_bag,
            robot_water,
            robot_water_title,
        )
    )
    if cloud_online is False:
        status, label = "offline", "Ikke tilkoblet"
    elif issues:
        status, label = "attention", "Krever tilsyn"
    elif active:
        status, label = "active", "Rengjør nå"
    else:
        status, label = "ready", "Klar"
    return {"status": status, "label": label, "issues": list(dict.fromkeys(issues))}


def roborock_resource_issues(
    dock_error: str,
    clear_water: str,
    dirty_water: str,
    dust_bag: str,
    robot_water: str = "Ikke støttet",
    robot_water_title: str = "Vann i robot",
) -> list[str]:
    """Return resource problems without connection or freshness concerns."""
    issues = []
    if dock_error not in {"Ingen feil", "Ikke støttet", "-"}:
        issues.append(dock_error)
    dock_error_lower = dock_error.lower()
    for label, value, dock_marker in (
        ("Rentvann", clear_water, "rentvann"),
        ("Skittent vann", dirty_water, "skittent"),
        ("Støvpose", dust_bag, "støv"),
    ):
        if value not in {"OK", "Ikke støttet", "-"} and dock_marker not in dock_error_lower:
            issues.append(f"{label}: {value}")
    if robot_water not in {"OK", "Ikke støttet", "-"}:
        issues.append(f"{robot_water_title}: {robot_water}")
    return list(dict.fromkeys(issues))


def format_seconds_as_hours(value: Any) -> str:
    seconds = int_value(value)
    if seconds is None:
        return "-"
    hours = seconds / 3600
    if hours < 1:
        return f"{round(seconds / 60)} min"
    return f"{hours:.1f} t"


def roborock_cron_parts(cron: Optional[str]) -> Optional[tuple[int, int, str]]:
    if not cron:
        return None
    parts = cron.split()
    if len(parts) < 5:
        return None
    minute = int_value(parts[0])
    hour = int_value(parts[1])
    if minute is None or hour is None:
        return None
    return minute, hour, parts[4]


def roborock_schedule_minutes(schedule: Any) -> int:
    parts = roborock_cron_parts(getattr(schedule, "cron", None))
    if not parts:
        return 24 * 60 + 1
    minute, hour, _ = parts
    return hour * 60 + minute


def roborock_cron_weekdays(day_field: str) -> Optional[set[int]]:
    """Return Python weekdays (Monday=0), or None for an every-day cron."""
    value = str(day_field or "").strip().upper()
    if value in {"", "*", "?"}:
        return None

    named_days = {
        "MON": 0,
        "TUE": 1,
        "WED": 2,
        "THU": 3,
        "FRI": 4,
        "SAT": 5,
        "SUN": 6,
    }

    def parse_day(token: str) -> Optional[int]:
        token = token.strip().upper()
        if token in named_days:
            return named_days[token]
        number = int_value(token)
        if number in {0, 7}:
            return 6
        if number is not None and 1 <= number <= 6:
            return number - 1
        return None

    weekdays: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" not in part:
            weekday = parse_day(part)
            if weekday is None:
                return set()
            weekdays.add(weekday)
            continue
        start_token, end_token = part.split("-", 1)
        start = parse_day(start_token)
        end = parse_day(end_token)
        if start is None or end is None:
            return set()
        weekday = start
        weekdays.add(weekday)
        while weekday != end:
            weekday = (weekday + 1) % 7
            weekdays.add(weekday)
    return weekdays


def roborock_next_schedule_at(schedule: Any, now: Optional[datetime] = None) -> Optional[datetime]:
    parts = roborock_cron_parts(getattr(schedule, "cron", None))
    if not parts:
        return None
    minute, hour, day_field = parts
    if not 0 <= minute <= 59 or not 0 <= hour <= 23:
        return None
    weekdays = roborock_cron_weekdays(day_field)
    if weekdays == set():
        return None
    current = now or datetime.now(LOCAL_TZ)
    current = current.replace(tzinfo=LOCAL_TZ) if current.tzinfo is None else current.astimezone(LOCAL_TZ)
    allowed_days = weekdays if weekdays is not None else set(range(7))
    for offset in range(8):
        day = current.date() + timedelta(days=offset)
        if day.weekday() not in allowed_days:
            continue
        candidate = datetime(day.year, day.month, day.day, hour, minute, tzinfo=LOCAL_TZ)
        if candidate >= current:
            return candidate
    return None


def roborock_next_schedule_score(schedule: Any, now: Optional[datetime] = None) -> int:
    current = now or datetime.now(LOCAL_TZ)
    current = current.replace(tzinfo=LOCAL_TZ) if current.tzinfo is None else current.astimezone(LOCAL_TZ)
    next_at = roborock_next_schedule_at(schedule, current)
    if next_at is None:
        return 8 * 24 * 60 * 60
    return max(0, int((next_at - current).total_seconds()))


def roborock_next_schedule_text(schedule: Any, now: Optional[datetime] = None) -> Optional[str]:
    current = now or datetime.now(LOCAL_TZ)
    current = current.replace(tzinfo=LOCAL_TZ) if current.tzinfo is None else current.astimezone(LOCAL_TZ)
    next_at = roborock_next_schedule_at(schedule, current)
    if next_at is None:
        return None
    day_offset = (next_at.date() - current.date()).days
    if day_offset == 0:
        day_label = "I dag"
    elif day_offset == 1:
        day_label = "I morgen"
    else:
        day_label = ("mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag")[
            next_at.weekday()
        ]
    return f"{day_label} kl. {next_at:%H:%M}"


def roborock_schedule_text(schedule: Any) -> str:
    cron = getattr(schedule, "cron", None)
    parts = roborock_cron_parts(cron)
    if not parts:
        return cron or "-"
    minute, hour, day_field = parts
    time_text = f"{hour:02d}:{minute:02d}"
    if day_field in {"*", "?", ""}:
        return f"Hver dag kl. {time_text}"
    days = [ROBOROCK_DAYS.get(day.strip().upper(), day.strip()) for day in day_field.split(",") if day.strip()]
    if days:
        return f"{', '.join(days)} kl. {time_text}"
    return f"Kl. {time_text}"


def roborock_rounds_label(value: Any) -> str:
    number = int_value(value)
    if number is None:
        return "-"
    return f"{number} runde" if number == 1 else f"{number} runder"


def roborock_json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, indent=2, default=str)
