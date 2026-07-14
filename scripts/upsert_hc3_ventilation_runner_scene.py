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
SCENE_ID = int(os.environ.get("HC3_VENTILATION_RUNNER_SCENE_ID", "363"))
EXECUTE_AFTER_UPSERT = os.environ.get("HC3_VENTILATION_RUNNER_EXECUTE", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "ja",
}


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
    lua = (root / "scripts" / "hc3_ventilation_runner_scene_363.lua").read_text(encoding="utf-8")
    backup_dir = root / "outputs" / "hc3_inventory" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")

    _, current = request(f"/api/scenes/{SCENE_ID}")
    (backup_dir / f"scene_{SCENE_ID}_before_ventilation_runner_{stamp}.json").write_text(
        json.dumps(current, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    payload = dict(current)
    payload["content"] = json.dumps({"actions": lua, "conditions": "nil"}, ensure_ascii=False)
    status, _ = request(f"/api/scenes/{SCENE_ID}", method="PUT", body=payload)

    result = {
        "action": "updated",
        "scene_id": SCENE_ID,
        "scene_name": current.get("name"),
        "status": status,
        "execute_after_upsert": EXECUTE_AFTER_UPSERT,
    }
    print(json.dumps(result, ensure_ascii=False))

    if EXECUTE_AFTER_UPSERT:
        try:
            execute_status, _ = request(f"/api/scenes/{SCENE_ID}/execute", method="POST", body={})
            print(json.dumps({"action": "execute", "scene_id": SCENE_ID, "status": execute_status}, ensure_ascii=False))
        except urllib.error.HTTPError as exc:
            print(
                json.dumps(
                    {
                        "action": "execute",
                        "scene_id": SCENE_ID,
                        "status": exc.code,
                        "error": exc.read().decode("utf-8", errors="replace"),
                    },
                    ensure_ascii=False,
                )
            )


if __name__ == "__main__":
    main()
