from typing import Any, Dict, Optional
import re


def repair_mojibake(value: Any) -> Any:
    if not isinstance(value, str) or ("Ãƒ" not in value and "Ã‚" not in value):
        return value
    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value


def room_key_from_name(value: Any) -> Optional[str]:
    text = repair_mojibake(value)
    if not isinstance(text, str):
        return None
    match = re.search(r"\brom\s*0*(\d+)\b", text, re.IGNORECASE)
    if not match:
        return None
    return f"rom_{int(match.group(1)):02d}"


SUN2_ROOM_MAP_BY_DISPLAY = {
    1: {"room_id": "rom-01", "physical_room_number": 1, "display_room_number": 1, "sun2_bed_id": "640"},
    2: {"room_id": "rom-02", "physical_room_number": 2, "display_room_number": 2, "sun2_bed_id": "641"},
    3: {"room_id": "rom-03", "physical_room_number": 3, "display_room_number": 3, "sun2_bed_id": "642"},
    4: {"room_id": "rom-04", "physical_room_number": 4, "display_room_number": 4, "sun2_bed_id": "643"},
    5: {"room_id": "rom-05", "physical_room_number": 5, "display_room_number": 5, "sun2_bed_id": "644"},
    6: {"room_id": "rom-06", "physical_room_number": 6, "display_room_number": 6, "sun2_bed_id": "645"},
    7: {"room_id": "rom-07", "physical_room_number": 7, "display_room_number": 7, "sun2_bed_id": "646"},
    8: {"room_id": "rom-08", "physical_room_number": 8, "display_room_number": 8, "sun2_bed_id": "647"},
    9: {"room_id": "rom-09", "physical_room_number": 9, "display_room_number": 9, "sun2_bed_id": "648"},
    10: {"room_id": "rom-11", "physical_room_number": 11, "display_room_number": 10, "sun2_bed_id": "679"},
    11: {"room_id": "rom-12", "physical_room_number": 12, "display_room_number": 11, "sun2_bed_id": "680"},
    12: {"room_id": "rom-13", "physical_room_number": 13, "display_room_number": 12, "sun2_bed_id": "681"},
}

SUN2_ROOM_UNKNOWN_OLD_10 = {
    "room_id": "rom-10",
    "physical_room_number": 10,
    "display_room_number": None,
    "sun2_bed_id": "649",
}


def normalize_room_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower().replace("_", "-")
    match = re.search(r"(?:rom[-\s]*)?0*(\d{1,2})$", text)
    if not match:
        return None
    number = int(match.group(1))
    if 1 <= number <= 13:
        return f"rom-{number:02d}"
    return None


def sun2_room_identity(value: Any = None, room_id: Any = None, bed_id: Any = None) -> Dict[str, Any]:
    explicit_room_id = normalize_room_id(room_id)
    bed_id_text = (repair_mojibake(bed_id) or "").strip()
    if explicit_room_id:
        physical_number = int(explicit_room_id.rsplit("-", 1)[-1])
        identity = {
            "room_id": explicit_room_id,
            "physical_room_number": physical_number,
            "display_room_number": None,
            "sun2_bed_id": bed_id_text or None,
        }
        for item in list(SUN2_ROOM_MAP_BY_DISPLAY.values()) + [SUN2_ROOM_UNKNOWN_OLD_10]:
            if item["room_id"] == explicit_room_id:
                identity.update(item)
                if bed_id_text:
                    identity["sun2_bed_id"] = bed_id_text
                break
        return identity

    text_value = repair_mojibake(value)
    text = str(text_value).strip() if text_value is not None else ""
    if text in {".", "-", ""}:
        identity = dict(SUN2_ROOM_UNKNOWN_OLD_10)
        if bed_id_text:
            identity["sun2_bed_id"] = bed_id_text
        return identity

    match = re.search(r"\brom\s*0*(\d{1,2})\b", text, re.IGNORECASE)
    if match:
        display_number = int(match.group(1))
        identity = dict(SUN2_ROOM_MAP_BY_DISPLAY.get(display_number) or {})
        if identity:
            if bed_id_text:
                identity["sun2_bed_id"] = bed_id_text
            return identity

    explicit_from_value = normalize_room_id(text)
    if explicit_from_value:
        return sun2_room_identity(room_id=explicit_from_value, bed_id=bed_id_text)
    return {"room_id": None, "physical_room_number": None, "display_room_number": None, "sun2_bed_id": bed_id_text or None}


def sun2_room_label(room_id: Optional[str], source_name: Optional[str] = None) -> str:
    normalized = normalize_room_id(room_id)
    source = (repair_mojibake(source_name) or "").strip()
    if not normalized:
        return source or "-"
    number = int(normalized.rsplit("-", 1)[-1])
    if source and source not in {".", "-"}:
        return f"Rom {number} - {source}"
    if normalized == "rom-10":
        return "Rom 10 - tidligere SUN2-navn '.'"
    return f"Rom {number}"


SUN2_ROOM_OPTIONS = [
    {"value": f"rom-{number:02d}", "label": f"Rom {number}"}
    for number in range(1, 14)
]
