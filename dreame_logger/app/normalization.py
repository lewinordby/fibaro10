from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    if hasattr(value, "__dict__"):
        return jsonable({key: item for key, item in vars(value).items() if not key.startswith("_")})
    return str(value)


def enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def enum_name(value: Any) -> str | None:
    name = getattr(value, "name", None)
    return str(name).replace("_", " ").title() if name else None


def safe_attr(value: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(value, name, default)
    except Exception:
        return default


def number_from_text(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value or ""))
    return float(match.group(0).replace(",", ".")) if match else None


def stable_history_id(external_id: str, record_identity: Any, timestamp: Any) -> str:
    raw = f"{external_id}|{record_identity}|{timestamp}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def normalize_history(external_id: str, history: Any, timezone_name: str) -> list[dict[str, Any]]:
    if not isinstance(history, dict):
        return []
    ZoneInfo(timezone_name)
    rows: list[dict[str, Any]] = []
    for record_identity, item in history.items():
        if not isinstance(item, dict):
            continue
        timestamp = item.get("timestamp")
        try:
            # Fibaro10 stores cleaning-job instants as UTC-naive values.
            started = datetime.fromtimestamp(float(timestamp), timezone.utc).replace(tzinfo=None)
        except (TypeError, ValueError, OSError):
            continue
        duration_minutes = number_from_text(item.get("cleaning_time"))
        area_m2 = number_from_text(item.get("cleaned_area"))
        status = str(item.get("status") or "").strip().lower()
        completed = item.get("completed")
        rows.append(
            {
                "id": stable_history_id(
                    external_id,
                    item.get("id") or item.get("record_id") or record_identity,
                    timestamp,
                ),
                "begin_at": started.isoformat(),
                "end_at": (
                    started.replace(microsecond=0)
                    if not duration_minutes
                    else (started + timedelta(minutes=duration_minutes)).replace(microsecond=0)
                ).isoformat(),
                "duration_minutes": duration_minutes,
                "duration_seconds": round(duration_minutes * 60) if duration_minutes is not None else None,
                "area_m2": area_m2,
                "cleaned_area_m2": area_m2,
                "complete": bool(completed) if completed is not None else status not in {"", "unknown", "error"},
                "error_code": 1 if status == "error" else 0,
                "raw": jsonable(item),
            }
        )
    return rows


def normalize_schedule_cron(raw: dict[str, Any]) -> str | None:
    value = raw.get("cron") or raw.get("time") or raw.get("start_time")
    if value is None:
        return None
    schedule_time = str(value).strip()
    if len(schedule_time.split()) >= 5:
        return schedule_time

    match = re.fullmatch(r"(\d{1,2}):(\d{2})", schedule_time)
    if not match:
        return schedule_time
    hour, minute = (int(part) for part in match.groups())
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return schedule_time

    # Dreame encodes weekdays from Sunday through Saturday as a seven-bit string.
    repeats = str(raw.get("repeats") or "").zfill(7)
    if re.fullmatch(r"[01]{7}", repeats) and "1" in repeats:
        day_field = ",".join(str(index) for index, enabled in enumerate(repeats) if enabled == "1")
    else:
        day_field = "*"
    return f"{minute} {hour} * * {day_field}"


def normalize_schedule(item: Any, index: int) -> dict[str, Any] | None:
    raw = jsonable(item)
    if not isinstance(raw, dict):
        return None
    schedule_id = raw.get("id") or raw.get("schedule_id") or raw.get("did")
    if not schedule_id:
        schedule_id = hashlib.sha256(repr(sorted(raw.items())).encode("utf-8")).hexdigest()[:24]
    cron = normalize_schedule_cron(raw)
    invalid = bool(raw.get("invalid", False))
    once = bool(raw.get("once", False))
    return {
        "id": str(schedule_id),
        "cron": cron,
        "enabled": bool(raw.get("enabled", raw.get("active", True))) and not invalid,
        "repeated": bool(raw.get("repeated", not once)),
        "segments": raw.get("segments") or raw.get("rooms"),
        "raw": raw,
    }


def normalize_device_snapshot(device: Any, descriptor: dict[str, Any], timezone_name: str) -> dict[str, Any]:
    status = device.status
    external_id = str(descriptor.get("did") or "")
    state = safe_attr(status, "state")
    error = safe_attr(status, "error")
    charging_status = safe_attr(status, "charging_status")
    suction = safe_attr(status, "suction_level")
    water = safe_attr(status, "water_volume")
    cleaning_mode = safe_attr(status, "cleaning_mode")
    clean_water_status = safe_attr(status, "clean_water_tank_status")
    dirty_water_status = safe_attr(status, "dirty_water_tank_status")
    dust_bag_status = safe_attr(status, "dust_bag_status")
    detergent_status = safe_attr(status, "detergent_status")
    water_warning_status = safe_attr(status, "low_water_warning")
    if water_warning_status is None:
        low_water = safe_attr(status, "low_water")
        water_warning_status = 5 if low_water is True else 0 if low_water is False else None
    water_tank_status = safe_attr(status, "water_tank")
    if water_tank_status is None:
        water_tank_status = safe_attr(status, "water_tank_status")
    dock_error_status = safe_attr(status, "dock_error")
    if dock_error_status is None:
        dock_error_status = safe_attr(status, "base_error")
    raw_properties = {
        str(getattr(key, "name", key)): jsonable(value)
        for key, value in (getattr(device, "data", {}) or {}).items()
    }
    in_cleaning = bool(safe_attr(status, "started", False))
    in_returning = bool(safe_attr(status, "returning", False))
    battery = safe_attr(status, "battery_level")
    clean_minutes = number_from_text(safe_attr(status, "cleaning_time"))
    clean_area = number_from_text(safe_attr(status, "cleaned_area"))
    state_name = safe_attr(status, "state_name") or enum_name(state) or "Ukjent"
    status_payload = {
        "state": enum_value(state),
        "state_name": str(state_name),
        "battery": int(battery) if battery is not None else None,
        "error_code": enum_value(error),
        "in_cleaning": in_cleaning,
        "in_returning": in_returning,
        "clean_time": round(clean_minutes * 60) if clean_minutes is not None else None,
        "clean_area": clean_area,
        "fan_power": enum_value(suction),
        "water_box_mode": enum_value(water),
        "mop_mode": enum_value(cleaning_mode),
        "charge_status": enum_value(charging_status),
        "dock_type": 1 if bool(safe_attr(status, "docked", False)) else 0,
        "raw": raw_properties,
    }
    telemetry = {
        "state_code": enum_value(state),
        "state_name": str(state_name),
        "battery": int(battery) if battery is not None else None,
        "error_code": enum_value(error),
        "in_cleaning": in_cleaning,
        "in_returning": in_returning,
        "clean_time_seconds": status_payload["clean_time"],
        "clean_area_raw": clean_area,
        "fan_power": enum_value(suction),
        "water_box_mode": enum_value(water),
        "mop_mode": enum_value(cleaning_mode),
        "charge_status": enum_value(charging_status),
        "is_charging": bool(safe_attr(status, "charging", False)),
        "dock_type": status_payload["dock_type"],
        "dock_error_status": enum_value(dock_error_status),
        "dust_collection_status": enum_value(safe_attr(status, "dust_collection")),
        "wash_status": enum_value(safe_attr(status, "self_wash_base_status")),
        "wash_ready": bool(safe_attr(status, "washing_available", False)),
        "dry_status": 1 if bool(safe_attr(status, "drying", False)) else 0,
        # Preserve Dreame's complete warning code. It distinguishes low water,
        # empty water, missing tank and insufficient water for cleaning.
        "water_shortage_status": enum_value(water_warning_status),
        "water_box_status": enum_value(water_tank_status),
        "clear_water_status": enum_value(clean_water_status),
        "clear_water_status_name": safe_attr(status, "clean_water_tank_status_name") or enum_name(clean_water_status),
        "dirty_water_status": enum_value(dirty_water_status),
        "dirty_water_status_name": safe_attr(status, "dirty_water_tank_status_name") or enum_name(dirty_water_status),
        "dust_bag_status": enum_value(dust_bag_status),
        "dust_bag_status_name": safe_attr(status, "dust_bag_status_name") or enum_name(dust_bag_status),
        "clean_fluid_status": enum_value(detergent_status),
        "clean_fluid_status_name": safe_attr(status, "detergent_status_name") or enum_name(detergent_status),
        "status_raw": raw_properties,
    }
    raw_schedule_values = safe_attr(status, "schedule", []) or []
    schedule_values = raw_schedule_values.values() if isinstance(raw_schedule_values, dict) else raw_schedule_values
    schedules = [row for index, item in enumerate(schedule_values) if (row := normalize_schedule(item, index))]
    history = normalize_history(external_id, safe_attr(status, "cleaning_history"), timezone_name)
    return {
        "provider": "dreame",
        "external_id": external_id,
        "duid": f"dreame:{external_id}",
        "name": descriptor.get("name") or descriptor.get("customName") or "Aqua10",
        "model": descriptor.get("model"),
        "serial_number": safe_attr(status, "serial_number"),
        "metadata": {
            **jsonable(descriptor),
            "provider": "dreame",
            "online": bool(getattr(device, "available", False)),
            "time_zone_id": timezone_name,
        },
        "cloud": True,
        "status": status_payload,
        "telemetry": telemetry,
        "consumables": {
            "unit": "percent_remaining",
            "main_brush_percent": safe_attr(status, "main_brush_life"),
            "side_brush_percent": safe_attr(status, "side_brush_life"),
            "filter_percent": safe_attr(status, "filter_life"),
            "sensor_percent": safe_attr(status, "sensor_dirty_life"),
            "mop_percent": safe_attr(status, "mop_life"),
            "detergent_percent": safe_attr(status, "detergent_life"),
        },
        "clean_jobs": history,
        "schedules": schedules,
        "settings": {
            "cleaning_mode": enum_name(cleaning_mode),
            "suction_level": enum_name(suction),
            "water_volume": enum_name(water),
            "mop_wash_level": safe_attr(status, "mop_wash_level_name") or enum_name(safe_attr(status, "mop_wash_level")),
            "mop_clean_frequency": safe_attr(status, "mop_clean_frequency_name") or enum_name(safe_attr(status, "mop_clean_frequency")),
            "auto_empty_mode": safe_attr(status, "auto_empty_mode_name") or enum_name(safe_attr(status, "auto_empty_mode")),
        },
    }
