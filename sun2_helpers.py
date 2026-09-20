from typing import Any, Dict, Optional
import re
from sun2_room_mapping import SUN2_ROOM_MAP_BY_DISPLAY, SUN2_ROOM_UNKNOWN_OLD_10


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
    identity = next((item for item in SUN2_ROOM_MAP_BY_DISPLAY.values() if item["room_id"] == normalized), None)
    number = identity["display_room_number"] if identity else int(normalized.rsplit("-", 1)[-1])
    if identity and room_key_from_name(source) == f"rom_{number:02d}":
        return source
    if source and source not in {".", "-"}:
        return f"Rom {number} - {source}"
    if normalized == "rom-10":
        return "Rom 10 - tidligere SUN2-navn '.'"
    return f"Rom {number}"


SUN2_ROOM_OPTIONS = [
    {"value": identity["room_id"], "label": f"Rom {number}"}
    for number, identity in SUN2_ROOM_MAP_BY_DISPLAY.items()
] + [{"value": "rom-10", "label": "Tidligere ubrukt utgang 10"}]
