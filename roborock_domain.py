import json
from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo


LOCAL_TZ = ZoneInfo("Europe/Oslo")

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
    101: "Stille",
    102: "Balansert",
    103: "Turbo",
    104: "Maks",
    105: "Maks+",
}

ROBOROCK_MOP_LABELS = {
    300: "Standard",
    301: "Lav",
    302: "Medium",
    303: "Høy",
}

ROBOROCK_WATER_LABELS = {
    200: "Av",
    201: "Lav",
    202: "Medium",
    203: "Høy",
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
    "out_of_water": "Tom",
    "out_of_water_2": "Tom",
    "refill_error": "Påfyllingsfeil",
    "full_not_installed": "Full eller ikke montert",
    "full_not_installed_2": "Full eller ikke montert",
    "drain_error": "Tømmefeil",
    "not_installed": "Ikke montert",
    "full": "Full",
    "empty_not_installed": "Tom eller ikke montert",
}

ROBOROCK_TELEMETRY_EVENT_FIELDS = {
    "state_code": ("robot", "Robotstatus"),
    "is_charging": ("lading", "Lading"),
    "error_code": ("robot", "Robotfeil"),
    "dock_error_status": ("dokk", "Dokkfeil"),
    "clear_water_status": ("vann", "Rentvann"),
    "dirty_water_status": ("vann", "Skittent vann"),
    "dust_bag_status": ("dokk", "Støvpose"),
    "clean_fluid_status": ("vann", "Rengjøringsmiddel"),
    "water_shortage_status": ("vann", "Vannmangel"),
    "water_box_carriage_status": ("vann", "Vanntank montert"),
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


def roborock_telemetry_value_label(field_name: str, value: Any, name: Any = None) -> str:
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
    if field_name in {"clear_water_status", "dirty_water_status", "dust_bag_status", "clean_fluid_status"}:
        return roborock_resource_status_label(value, name)
    if field_name == "rssi":
        return roborock_signal_label(value)
    if field_name in {"is_charging", "in_cleaning", "in_returning", "auto_dust_collection", "wash_ready"}:
        return roborock_bool_label(value)
    if field_name == "battery" and value is not None:
        return f"{int_value(value)} %"
    return str(value) if value is not None else "Ikke støttet"


def roborock_telemetry_changes(previous: Dict[str, Any] | None, current: Dict[str, Any]) -> list[Dict[str, Any]]:
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
        old_label = roborock_telemetry_value_label(field_name, old_value, old_name)
        new_label = roborock_telemetry_value_label(field_name, new_value, new_name)
        severity = "info"
        if field_name in {"error_code", "dock_error_status"} and int_value(new_value) not in {None, 0}:
            severity = "critical"
        elif field_name in {
            "clear_water_status",
            "dirty_water_status",
            "dust_bag_status",
            "clean_fluid_status",
            "water_shortage_status",
        } and new_label not in {"OK", "Ikke støttet", "0"}:
            severity = "warning"
        changes.append(
            {
                "category": category,
                "field_name": field_name,
                "title": title,
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


def roborock_next_schedule_score(schedule: Any) -> int:
    minutes = roborock_schedule_minutes(schedule)
    if minutes > 24 * 60:
        return minutes
    now = datetime.now(LOCAL_TZ)
    now_minutes = now.hour * 60 + now.minute
    return minutes - now_minutes if minutes >= now_minutes else minutes + (24 * 60 - now_minutes)


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
