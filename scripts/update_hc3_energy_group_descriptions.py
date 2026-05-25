import base64
import json
import os
import re
import urllib.request


BASE_URL = os.environ.get("HC3_BASE_URL", "http://192.168.1.10").rstrip("/")
USER = os.environ["HC3_USER"]
PASS = os.environ["HC3_PASS"]

GROUP_IDS = [237, 305, 333, 332, 331, 335, 336, 337, 328, 334]


def auth_header() -> str:
    return "Basic " + base64.b64encode(f"{USER}:{PASS}".encode("utf-8")).decode("ascii")


def request(path: str, method: str = "GET", body=None):
    data = None
    headers = {"Authorization": auth_header(), "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE_URL + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read()
        if not raw:
            return response.status, None
        return response.status, json.loads(raw.decode("utf-8"))


def strip_lua_comments(content: str) -> str:
    content = re.sub(r"--\[\[.*?\]\]", "", content, flags=re.S)
    content = re.sub(r"--.*", "", content)
    return content


def ids_from_quickapp(content: str) -> list[int]:
    clean = strip_lua_comments(content)
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
    for device_id in ids:
        if device_id not in seen:
            seen.append(device_id)
    return seen


def device_label(device: dict) -> str:
    props = device.get("properties") or {}
    value = props.get("value")
    power = props.get("power")
    energy = props.get("energy")
    suffix = []
    if power is not None:
        suffix.append(f"power={power} W")
    if energy is not None:
        suffix.append(f"energy={energy} kWh")
    if power is None and energy is None and value is not None:
        suffix.append(f"value={value}")
    suffix_text = f" ({', '.join(suffix)})" if suffix else ""
    return f"{device.get('id')} - {device.get('name')}{suffix_text}"


def group_description(group: dict, members: list[dict]) -> str:
    lines = [
        "Energi-gruppe dokumentert automatisk.",
        "",
        "Undermålere/grunnlag:",
    ]
    lines.extend(f"- {device_label(member)}" for member in members)
    lines.extend(
        [
            "",
            "Merk: Listen er hentet fra QuickApp-koden og brukes som dokumentasjon i HC3.",
        ]
    )
    return "\n".join(lines)


def main():
    _, all_devices = request("/api/devices")
    devices = {device["id"]: device for device in all_devices}

    for group_id in GROUP_IDS:
        _, file_data = request(f"/api/quickApp/{group_id}/files/main")
        member_ids = ids_from_quickapp(file_data.get("content") or "")
        members = [devices[device_id] for device_id in member_ids if device_id in devices]
        description = group_description(devices[group_id], members)
        payload = {
            "properties": {
                "userDescription": description,
            }
        }
        status, _ = request(f"/api/devices/{group_id}", method="PUT", body=payload)
        print(f"{group_id} {devices[group_id].get('name')}: {status}, {len(members)} undermålere")


if __name__ == "__main__":
    main()
