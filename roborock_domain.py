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
