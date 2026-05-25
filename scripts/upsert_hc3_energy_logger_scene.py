import base64
import json
import os
import pathlib
import time
import urllib.error
import urllib.request


BASE_URL = os.environ.get("HC3_BASE_URL", "http://192.168.1.10").rstrip("/")
USER = os.environ["HC3_USER"]
PASS = os.environ["HC3_PASS"]
SCENE_NAME = "Energi - Logging - 1min"
ROOM_ID = int(os.environ.get("HC3_SCENE_ROOM_ID", "224"))


def request(path: str, method: str = "GET", body=None):
    data = None
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{USER}:{PASS}".encode("utf-8")).decode("ascii"),
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE_URL + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read()
        if not raw:
            return response.status, None
        return response.status, json.loads(raw.decode("utf-8"))


def main():
    root = pathlib.Path(__file__).resolve().parents[1]
    lua = (root / "scripts" / "hc3_energy_logger.lua").read_text(encoding="utf-8")
    backup_dir = root / "outputs" / "hc3_inventory" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")

    _, scenes = request("/api/scenes")
    existing = next((scene for scene in scenes if scene.get("name") == SCENE_NAME), None)
    payload = {
        "name": SCENE_NAME,
        "description": "Logger energi fra Fibaro quickapps til fibaro10 hvert minutt.",
        "type": "lua",
        "mode": "manual",
        "enabled": True,
        "hidden": False,
        "roomId": ROOM_ID,
        "categories": [1],
        "icon": "scene_lua",
        "iconExtension": "",
        "protectedByPin": False,
        "maxRunningInstances": 1,
        "restart": True,
        "content": json.dumps({"actions": lua, "conditions": ""}, ensure_ascii=False),
    }

    if existing:
        scene_id = existing["id"]
        _, current = request(f"/api/scenes/{scene_id}")
        (backup_dir / f"scene_{scene_id}_before_energy_logger_{stamp}.json").write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        status, _ = request(f"/api/scenes/{scene_id}", method="PUT", body=payload)
        action = "updated"
    else:
        status, created = request("/api/scenes", method="POST", body=payload)
        scene_id = created.get("id")
        action = "created"

    print(action, scene_id, status)

    try:
        status, _ = request(f"/api/scenes/{scene_id}/kill", method="POST", body={})
        print("kill", scene_id, status)
    except urllib.error.HTTPError as exc:
        print("kill", scene_id, exc.code)

    status, _ = request(f"/api/scenes/{scene_id}/execute", method="POST", body={})
    print("execute", scene_id, status)


if __name__ == "__main__":
    main()
