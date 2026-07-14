from __future__ import annotations

import base64
import datetime as dt
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any


BASE_URL = os.environ.get("HC3_BASE_URL", "http://192.168.1.10").rstrip("/")
USER = os.environ.get("HC3_USER")
PASS = os.environ.get("HC3_PASS")

GROUP_IDS = [237, 305, 333, 332, 335, 336, 337, 328, 331, 334]
SUMMARY_GROUP_IDS = {237, 305, 333, 332, 335, 336, 337, 328}
DIFF_GROUP_IDS = {331, 334}


def request_json(path: str) -> Any:
    if not USER or not PASS:
        raise SystemExit("Sett HC3_USER og HC3_PASS før scriptet kjøres.")
    token = base64.b64encode(f"{USER}:{PASS}".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def strip_lua_comments(content: str) -> str:
    content = re.sub(r"--\[\[.*?\]\]", "", content, flags=re.S)
    return re.sub(r"--.*", "", content)


def ids_from_quickapp(content: str) -> list[int]:
    clean = strip_lua_comments(content or "")
    ids: list[int] = []
    for pattern in [
        r"MAIN(?:_METER)?_ID\s*=\s*(\d+)",
        r"METER_IDS\s*=\s*\{([^}]*)\}",
        r"SUB_SUM_QA_IDS\s*=\s*\{([^}]*)\}",
        r"SUB_IDS\s*=\s*\{([^}]*)\}",
        r"METERS\s*=\s*\{(.*?)\n\}",
    ]:
        for match in re.findall(pattern, clean, flags=re.S):
            text = match if isinstance(match, str) else match[0]
            if pattern.startswith("MAIN"):
                ids.append(int(text))
            elif "METERS" in pattern:
                ids.extend(int(value) for value in re.findall(r"id\s*=\s*(\d+)", text))
            else:
                ids.extend(int(value) for value in re.findall(r"\b\d+\b", text))
    seen: list[int] = []
    for item in ids:
        if item not in seen:
            seen.append(item)
    return seen


def meter_value_label(row: dict[str, Any]) -> str:
    for key in ("value", "power", "energy"):
        value = row.get(key)
        if isinstance(value, (int, float)):
            return f"{value:g}"
    return ""


def main() -> None:
    devices = request_json("/api/devices")
    rooms = request_json("/api/rooms")
    room_names = {int(room.get("id")): room.get("name") for room in rooms if room.get("id") is not None}
    by_id = {int(device["id"]): device for device in devices}

    def device_row(device_id: int) -> dict[str, Any]:
        device = by_id.get(int(device_id), {})
        props = device.get("properties") or {}
        parent_id = device.get("parentId")
        parent = by_id.get(int(parent_id), {}) if parent_id is not None else {}
        return {
            "id": int(device_id),
            "name": device.get("name") or "(mangler i HC3)",
            "type": device.get("type"),
            "baseType": device.get("baseType"),
            "roomID": device.get("roomID"),
            "room": room_names.get(int(device.get("roomID") or 0)),
            "parentId": parent_id,
            "parentName": parent.get("name"),
            "value": props.get("value"),
            "power": props.get("power"),
            "energy": props.get("energy"),
            "dead": props.get("dead"),
            "enabled": device.get("enabled"),
            "visible": device.get("visible"),
            "valueLabel": meter_value_label({"value": props.get("value"), "power": props.get("power"), "energy": props.get("energy")}),
        }

    group_data: dict[str, Any] = {}
    for group_id in GROUP_IDS:
        quickapp_file = request_json(f"/api/quickApp/{group_id}/files/main")
        ids = ids_from_quickapp(quickapp_file.get("content") or "")
        device = by_id.get(group_id, {})
        group_data[str(group_id)] = {
            "id": group_id,
            "name": device.get("name"),
            "ids": ids,
            "members": [device_row(item) for item in ids],
        }

    energy_types = ("powerMeter", "energyMeter", "electricMeter")
    energy_devices: list[dict[str, Any]] = []
    for device in devices:
        props = device.get("properties") or {}
        device_type = str(device.get("type") or "")
        base_type = str(device.get("baseType") or "")
        has_meter_type = any(marker in device_type for marker in energy_types) or any(marker in base_type for marker in energy_types)
        has_meter_prop = any(key in props for key in ("power", "energy"))
        if has_meter_type or has_meter_prop:
            energy_devices.append(device_row(int(device["id"])))

    included_ids: set[int] = set()
    for group_id in SUMMARY_GROUP_IDS:
        included_ids.update(group_data[str(group_id)]["ids"])
    diff_ids = set(group_data["331"]["ids"] + group_data["334"]["ids"])
    not_in_groups = [
        item
        for item in energy_devices
        if item["id"] not in included_ids and item["id"] not in diff_ids and item["id"] not in GROUP_IDS
    ]

    all_devices = [device_row(int(device["id"])) for device in devices]
    output = {
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "hc3_base": BASE_URL,
        "groups": group_data,
        "all_devices": all_devices,
        "all_device_count": len(all_devices),
        "energy_device_count": len(energy_devices),
        "included_meter_ids": sorted(included_ids),
        "diff_meter_ids": sorted(diff_ids),
        "not_in_groups": not_in_groups,
        "not_in_groups_visible_alive": [
            item for item in not_in_groups if item.get("enabled") is not False and item.get("dead") is not True
        ],
    }

    docs_path = Path("docs/hc3-energy-inventory-current.json")
    docs_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    output_dir = Path("outputs/hc3_inventory")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"energy_quickapps_current_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(docs_path)
    print(output_path)
    print(f"devices={len(all_devices)} energy_devices={len(energy_devices)} not_in_groups={len(not_in_groups)}")


if __name__ == "__main__":
    main()
