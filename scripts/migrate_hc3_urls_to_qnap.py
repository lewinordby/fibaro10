import base64
import json
import os
import pathlib
import time
import urllib.request


BASE_URL = os.environ.get("HC3_BASE_URL", "http://192.168.1.10").rstrip("/")
USER = os.environ["HC3_USER"]
PASS = os.environ["HC3_PASS"]

OLD_URL = "https://fibaro10.onrender.com"
NEW_URL = os.environ.get("FIBARO10_QNAP_URL", "http://192.168.20.218:8110").rstrip("/")


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


def scene_payload(scene: dict, new_content: str) -> dict:
    keys = [
        "name",
        "description",
        "type",
        "mode",
        "maxRunningInstances",
        "icon",
        "iconExtension",
        "hidden",
        "protectedByPin",
        "stopOnAlarm",
        "restart",
        "enabled",
        "roomId",
        "categories",
    ]
    payload = {key: scene[key] for key in keys if key in scene}
    payload["content"] = new_content
    return payload


def main():
    root = pathlib.Path(__file__).resolve().parents[1]
    backup_dir = root / "outputs" / "hc3_inventory" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")

    _, scenes = request("/api/scenes")
    changed = []
    for scene in scenes:
        content = scene.get("content") or ""
        if OLD_URL not in content:
            continue
        scene_id = scene["id"]
        _, full_scene = request(f"/api/scenes/{scene_id}")
        current_content = full_scene.get("content") or content
        new_content = current_content.replace(OLD_URL, NEW_URL)
        if new_content == current_content:
            continue
        (backup_dir / f"scene_{scene_id}_before_qnap_url_{stamp}.json").write_text(
            json.dumps(full_scene, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        status, _ = request(f"/api/scenes/{scene_id}", method="PUT", body=scene_payload(full_scene, new_content))
        changed.append({"id": scene_id, "name": scene.get("name"), "status": status})

    print(json.dumps({"old": OLD_URL, "new": NEW_URL, "changed": changed}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
