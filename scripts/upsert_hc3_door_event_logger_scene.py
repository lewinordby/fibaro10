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
SCENE_NAME = os.environ.get("HC3_DOOR_SCENE_NAME", "Dør - Magnetfølere - Logger")
ROOM_ID = int(os.environ.get("HC3_DOOR_SCENE_ROOM_ID", os.environ.get("HC3_SCENE_ROOM_ID", "224")))
EXECUTE_AFTER_UPSERT = os.environ.get("HC3_DOOR_SCENE_EXECUTE", "true").strip().lower() in {"1", "true", "yes", "ja"}


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
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
        if not raw:
            return response.status, None
        return response.status, json.loads(raw.decode("utf-8"))


def main():
    root = pathlib.Path(__file__).resolve().parents[1]
    lua = (root / "scripts" / "hc3_door_event_logger.lua").read_text(encoding="utf-8")
    backup_dir = root / "outputs" / "hc3_inventory" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")

    _, scenes = request("/api/scenes")
    existing = next((scene for scene in scenes if scene.get("name") == SCENE_NAME), None)
    payload = {
        "name": SCENE_NAME,
        "description": "Logger åpne/lukke-hendelser fra HC3 magnetfølere 453, 447 og 413 til Fibaro10.",
        "type": "lua",
        "mode": "automatic",
        "enabled": True,
        "hidden": False,
        "roomId": ROOM_ID,
        "categories": [1],
        "icon": "scene_lua",
        "iconExtension": "",
        "protectedByPin": False,
        "maxRunningInstances": 2,
        "restart": False,
        "content": json.dumps({"actions": lua, "conditions": "nil"}, ensure_ascii=False),
    }

    if existing:
        scene_id = existing["id"]
        _, current = request(f"/api/scenes/{scene_id}")
        (backup_dir / f"scene_{scene_id}_before_door_logger_{stamp}.json").write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        status, _ = request(f"/api/scenes/{scene_id}", method="PUT", body=payload)
        action = "updated"
    else:
        status, created = request("/api/scenes", method="POST", body=payload)
        scene_id = created.get("id")
        action = "created"

    print(json.dumps({"action": action, "scene_id": scene_id, "status": status, "execute_after_upsert": EXECUTE_AFTER_UPSERT}, ensure_ascii=False))

    if EXECUTE_AFTER_UPSERT:
        try:
            status, _ = request(f"/api/scenes/{scene_id}/execute", method="POST", body={})
            print(json.dumps({"action": "execute", "scene_id": scene_id, "status": status}, ensure_ascii=False))
        except urllib.error.HTTPError as exc:
            print(json.dumps({"action": "execute", "scene_id": scene_id, "status": exc.code, "error": exc.read().decode("utf-8", errors="replace")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
