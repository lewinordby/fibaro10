"""Read-only battery inventory. Never infer a battery timestamp from device.modified."""

import json
import math
import re
import threading
import urllib.request
from collections import defaultdict
from time import monotonic

from time_formatting import api_local_iso, local_now_naive, normalize_local_naive


def battery_value(raw, *, zwave=False):
    if isinstance(raw, bool) or raw is None or raw == "":
        return None, "unknown"
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None, "unknown"
    if zwave and value == 255:
        return None, "critical"
    if not math.isfinite(value) or not 0 <= value <= 100:
        return None, "unknown"
    return value, "critical" if value <= 10 else "low" if value <= 20 else "ok"


def _properties(device):
    return device.get("properties") or {}


def hc3_batteries(devices, rooms, door_config=()):
    by_id = {row["id"]: row for row in devices if isinstance(row.get("id"), int)}
    room_names = {row["id"]: row.get("name", "") for row in rooms}
    doors = {row["device_id"]: row for row in door_config if row.get("device_id")}
    groups = defaultdict(list)
    roots = {}
    for device in by_id.values():
        props = _properties(device)
        if "batteryLevel" not in props and "battery" not in (device.get("interfaces") or []):
            continue
        root = device
        visited = set()
        while root.get("parentId") in by_id and root["id"] not in visited:
            if root.get("type") == "com.fibaro.zwaveDevice":
                break
            visited.add(root["id"])
            root = by_id[root["parentId"]]
        if root.get("type") == "com.fibaro.zwaveDevice":
            key = f"hc3:zwave:{root['id']}"
            source = "HC3"
        else:
            # Only module identity may join QuickApp channels; a shared parent is not enough.
            variables = {v.get("name"): v.get("value") for v in props.get("quickAppVariables", []) if isinstance(v, dict)}
            if variables.get("module_id") and variables.get("device_id"):
                key = f"hc3:module:{device.get('parentId')}:{variables['device_id']}:{variables['module_id']}"
                parent = by_id.get(device.get("parentId"), {})
                source = "Netatmo" if "netatmo" in str(parent.get("name", "")).casefold() else "HC3"
            else:
                key = f"hc3:device:{device['id']}"
                source = "HC3"
            root = device
        groups[key].append(device)
        roots[key] = (root, source)

    result = []
    for key, channels in groups.items():
        channels.sort(key=lambda row: row["id"])
        root, source = roots[key]
        config = next((doors[row["id"]] for row in channels if row["id"] in doors), {})
        name = config.get("title") or channels[0].get("name") or f"HC3 {root['id']}"
        if ":module:" in key:
            name = re.sub(r"^(Humidity|Temperature|CO2)\s+", "", name)
        values = [battery_value(_properties(row).get("batteryLevel"), zwave=":zwave:" in key) for row in channels]
        levels = [level for level, _ in values if level is not None]
        level = min(levels, default=None)
        status = min((status for _, status in values), key=lambda value: {"critical": 0, "low": 1, "ok": 2, "unknown": 3}[value])
        warning = any(_properties(row).get("batteryLevel") in (255, "255") for row in channels) and ":zwave:" in key
        room = config.get("section_title") if config.get("group_key") == "solrom" else room_names.get(channels[0].get("roomID"), "")
        result.append({
            "id": key, "name": name, "source": source, "location": room or "Ikke angitt",
            "model": root.get("model") or _properties(root).get("model") or "",
            "manufacturer": root.get("manufacturer") or _properties(root).get("manufacturer") or "",
            "level": None if warning else level, "status": status, "lowBatteryWarning": warning,
            "rechargeable": False, "charging": None, "state": None,
            "unavailable": any(_properties(row).get("dead") is True for row in [root, *channels]),
            "disabled": root.get("enabled") is False or all(row.get("enabled") is False for row in channels),
            "reportedAt": None, "stale": False,
            "inconsistent": len(set(values)) > 1,
            "channels": [{"id": row["id"], "name": row.get("name", ""),
                          "level": battery_value(_properties(row).get("batteryLevel"), zwave=":zwave:" in key)[0]} for row in channels],
        })
    return result


def robot_battery(robot, samples, now):
    available = [sample for sample in samples if sample is not None and sample.timestamp is not None]
    sample = max(available, key=lambda row: normalize_local_naive(row.timestamp), default=None)
    reported = normalize_local_naive(sample.timestamp) if sample else None
    level, status = battery_value(sample.battery if sample else None)
    return {
        "id": f"robot:{robot.duid}", "name": robot.name, "location": "Renhold",
        "source": "Dreame" if robot.provider == "dreame" else "Roborock",
        "model": robot.model or robot.product or "", "manufacturer": robot.provider,
        "level": level, "status": status, "lowBatteryWarning": False,
        "rechargeable": True, "charging": getattr(sample, "is_charging", None),
        "state": sample.state_name if sample else None, "unavailable": robot.cloud_online is False,
        "disabled": robot.integration_status not in (None, "active"),
        "reportedAt": api_local_iso(reported),
        "stale": reported is None or (now - reported).total_seconds() > 1800,
        "inconsistent": False, "channels": [],
    }


class HC3BatterySnapshot:
    """Bounded, single-flight cache; failures preserve the last successful inventory."""

    def __init__(self, devices_reader, base_url, auth_header, door_config=(), ttl=60):
        self.devices_reader = devices_reader
        self.base_url = base_url
        self.auth_header = auth_header
        self.door_config = door_config
        self.ttl = ttl
        self.lock = threading.Lock()
        self.expires_at = 0
        self.rows = []
        self.rooms = []
        self.checked_at = None
        self.error = None
        self.rooms_error = None

    def read(self):
        with self.lock:
            if monotonic() >= self.expires_at:
                try:
                    devices = self.devices_reader(10)
                    try:
                        request = urllib.request.Request(f"{self.base_url.rstrip('/')}/api/rooms", headers={
                            "Accept": "application/json", "Authorization": self.auth_header(),
                        })
                        with urllib.request.urlopen(request, timeout=5) as response:
                            rooms = json.loads(response.read().decode("utf-8"))
                        if not isinstance(rooms, list):
                            raise ValueError("Invalid room list")
                        self.rooms = rooms
                        self.rooms_error = None
                    except Exception:
                        self.rooms_error = "Romnavn kunne ikke oppdateres fra HC3."
                    self.rows = hc3_batteries(devices, self.rooms, self.door_config)
                    self.checked_at = api_local_iso(local_now_naive())
                    self.error = None
                except Exception:
                    self.error = "HC3 kunne ikke leses. Eventuelle viste verdier er fra siste vellykkede kontroll."
                self.expires_at = monotonic() + self.ttl
            return {"rows": self.rows, "checkedAt": self.checked_at, "error": self.error, "roomsError": self.rooms_error}
