import base64
import json
import os
import pathlib
import time
import urllib.error
import urllib.request


BASE_URL = os.environ.get("HC3_BASE_URL", "http://192.168.1.10").rstrip("/")
USER = os.environ.get("HC3_USER", "")
PASS = os.environ.get("HC3_PASS", "")
ROOM_ID = int(os.environ.get("HC3_DOOR_SCENE_ROOM_ID", os.environ.get("HC3_SCENE_ROOM_ID", "224")))
SCENE_PREFIX = os.environ.get("HC3_DOOR_SINGLE_SCENE_PREFIX", "Dorlogger")
EXECUTE_AFTER_UPSERT = os.environ.get("HC3_DOOR_SINGLE_EXECUTE", "false").strip().lower() in {"1", "true", "yes", "ja"}
DISABLE_LEGACY_TRIGGERS = os.environ.get("HC3_DOOR_DISABLE_LEGACY", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "ja",
}
LEGACY_TRIGGER_NAMES = {"registrere dor aapnes", "registrere dor lukkes"}

DOORS = [
    {"device_id": 459, "device_key": "door_solrom_01", "name": "98.0 Rom 1", "title": "Solrom 1"},
    {"device_id": 465, "device_key": "door_solrom_04", "name": "101.0 Rom 4", "title": "Solrom 4"},
    {"device_id": 463, "device_key": "door_solrom_05", "name": "100.0 Rom 5", "title": "Solrom 5"},
    {"device_id": 469, "device_key": "door_solrom_06", "name": "104.0 Rom 6", "title": "Solrom 6"},
    {"device_id": 471, "device_key": "door_solrom_07", "name": "105.0 Rom 7", "title": "Solrom 7"},
    {"device_id": 473, "device_key": "door_solrom_08", "name": "106.0 Rom 8", "title": "Solrom 8"},
    {"device_id": 475, "device_key": "door_solrom_09", "name": "107.0 Rom 9", "title": "Solrom 9"},
    {"device_id": 477, "device_key": "door_solrom_10", "name": "108.0 Rom 10", "title": "Solrom 10"},
    {"device_id": 479, "device_key": "door_solrom_11", "name": "109.0 Rom 11", "title": "Solrom 11"},
    {"device_id": 491, "device_key": "door_solrom_12", "name": "116.0 Rom 12", "title": "Solrom 12"},
    {"device_id": 453, "device_key": "door_453", "name": "96.0 bod/kjokken", "title": "Bod/kjokken"},
    {"device_id": 447, "device_key": "door_447", "name": "94.0 Kjeller luke", "title": "Kjeller luke"},
    {"device_id": 413, "device_key": "door_413", "name": "86.0 Arbeidsrom", "title": "Arbeidsrom"},
    {"device_id": 499, "device_key": "door_inngang", "name": "120.0 Inngang", "title": "Inngang"},
    {"device_id": 483, "device_key": "door_massasjestudio", "name": "112.0 Massasje", "title": "Massasjestudio"},
    {"device_id": 535, "device_key": "door_loftluke_massasje", "name": "128.0 Loftluke massasje", "title": "Loftluke massasje"},
    {"device_id": 489, "device_key": "door_vaskerom", "name": "115.0 Vaskerom", "title": "Vaskerom"},
    {"device_id": 487, "device_key": "door_papirlager", "name": "114.0 Papirlager", "title": "Papirlager"},
    {"device_id": 493, "device_key": "door_vaktmesterlager", "name": "117.0 Vaktmesterlager", "title": "Vaktmesterlager"},
    {"device_id": 495, "device_key": "door_toalett", "name": "118.0 Toalett", "title": "Toalett"},
]


def request(path: str, method: str = "GET", body=None):
    if not USER or not PASS:
        raise RuntimeError("HC3_USER and HC3_PASS must be set before updating HC3 scenes")
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


def lua_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def render_lua(door: dict) -> str:
    device_id = int(door["device_id"])
    return f"""--[[
%% properties
%% events
%% globals
--]]

-- LILLETORGET - SINGLE DOOR LOGGER
-- This scene is started by one HC3 block scene for one door only.

local LOG_TAG = "DOOR-{device_id}"
local API_URL = "http://192.168.20.218:8110/api/hc3/door-events"
local SOURCE = "HC3 DOOR LOGGER SINGLE"
local DEVICE_ID = {device_id}
local DEVICE_KEY = {lua_string(door["device_key"])}
local DEVICE_NAME = {lua_string(door["name"])}
local MAX_POST_ATTEMPTS = 5
local RETRY_BASE_DELAY_MS = 5000

local function log(message)
  fibaro.debug(LOG_TAG, tostring(message))
end

local function warn(message)
  fibaro.warning(LOG_TAG, tostring(message))
end

local function timestamp()
  return os.date("%Y-%m-%dT%H:%M:%S")
end

local function valueToText(value)
  if value == nil then return "" end
  return tostring(value)
end

local function boolFromRaw(raw)
  local text = valueToText(raw):lower()
  if text == "true" or text == "1" or text == "open" or text == "opened" then return true end
  if text == "false" or text == "0" or text == "closed" or text == "close" then return false end
  local numeric = tonumber(raw)
  if numeric == 1 then return true end
  if numeric == 0 then return false end
  return nil
end

local function actionFromState(state)
  if state == true then return "OPEN" end
  if state == false then return "CLOSED" end
  return "UNKNOWN"
end

local function globalName()
  return "F10_DOOR_" .. tostring(DEVICE_ID) .. "_LAST"
end

local function getGlobalVariable(name)
  local ok, variable = pcall(api.get, "/globalVariables/" .. name)
  if ok and variable and variable.value ~= nil then
    return tostring(variable.value)
  end
  return ""
end

local function setGlobalVariable(name, value)
  local text = valueToText(value)
  local ok, existing = pcall(api.get, "/globalVariables/" .. name)
  if ok and existing and existing.name then
    api.put("/globalVariables/" .. name, {{ name = name, value = text }})
  else
    api.post("/globalVariables", {{ name = name, value = text }})
  end
end

local function getDeviceName()
  local ok, device = pcall(api.get, "/devices/" .. tostring(DEVICE_ID))
  if ok and device and device.name and tostring(device.name) ~= "" then
    return tostring(device.name)
  end
  return DEVICE_NAME
end

local function getBatteryLevel()
  local ok, device = pcall(api.get, "/devices/" .. tostring(DEVICE_ID))
  if ok and device and device.properties then
    return tonumber(device.properties.batteryLevel)
  end
  return nil
end

local function retryPost(payload, attempt, reason)
  if attempt >= MAX_POST_ATTEMPTS then
    warn("Gir opp sending etter " .. tostring(attempt) .. " forsok: " .. tostring(reason))
    return
  end
  local nextAttempt = attempt + 1
  local delayMs = RETRY_BASE_DELAY_MS * attempt
  warn("Sender pa nytt om " .. tostring(delayMs) .. " ms etter feil: " .. tostring(reason))
  fibaro.setTimeout(delayMs, function()
    postPayload(payload, nextAttempt)
  end)
end

function postPayload(payload, attempt)
  attempt = tonumber(attempt) or 1
  local http = net.HTTPClient()
  http:request(API_URL, {{
    options = {{
      method = "POST",
      headers = {{
        ["Content-Type"] = "application/json"
      }},
      data = json.encode(payload),
      timeout = 8000
    }},
    success = function(response)
      local status = tonumber(response.status) or 0
      if status >= 200 and status < 300 then
        log("Sent OK " .. tostring(response.status) .. ": " .. tostring(payload.device_id) .. " " .. tostring(payload.action))
      else
        retryPost(payload, attempt, "Fibaro10 svarte " .. tostring(response.status) .. ": " .. tostring(response.data))
      end
    end,
    error = function(err)
      retryPost(payload, attempt, "Feil ved sending: " .. tostring(err))
    end
  }})
end

local raw = fibaro.getValue(DEVICE_ID, "value")
local state = boolFromRaw(raw)
local previousText = getGlobalVariable(globalName())
local previousState = boolFromRaw(previousText)

local payload = {{
  timestamp = timestamp(),
  event_type = "door_change",
  action = actionFromState(state),
  device_key = DEVICE_KEY,
  device_id = DEVICE_ID,
  device_name = getDeviceName(),
  source = SOURCE,
  raw_value = valueToText(raw),
  state = state,
  previous_state = previousState,
  battery_level = getBatteryLevel(),
  extra = {{
    trigger_model = "block_scene_per_door",
    logger_scene = LOG_TAG
  }}
}}

setGlobalVariable(globalName(), valueToText(raw))
log("Sender " .. tostring(payload.device_name) .. " " .. tostring(payload.action) .. " raw=" .. tostring(raw))
postPayload(payload)
"""


def scene_name(door: dict) -> str:
    return f"{SCENE_PREFIX} {int(door['device_id'])} - {door['title']}"


def block_scene_name(door: dict) -> str:
    return f"Dortrigger {int(door['device_id'])} - {door['title']}"


def lua_scene_payload(door: dict) -> dict:
    name = scene_name(door)
    return {
        "name": name,
        "description": (
            f"Tynn logger for HC3 dor {door['device_id']}. Startes av egen block scene og sender kun denne doren til Fibaro10."
        ),
        "type": "lua",
        "mode": "manual",
        "enabled": True,
        "hidden": False,
        "roomId": ROOM_ID,
        "categories": [1],
        "icon": "scene_lua",
        "iconExtension": "",
        "protectedByPin": False,
        "maxRunningInstances": 3,
        "restart": False,
        "content": json.dumps({"actions": render_lua(door), "conditions": ""}, ensure_ascii=False),
    }


def block_scene_payload(door: dict, logger_scene_id: int) -> dict:
    device_id = int(door["device_id"])
    content = [
        {
            "conditions": {
                "operator": "any",
                "conditions": [
                    {
                        "group": "device",
                        "type": "single",
                        "isTrigger": True,
                        "id": device_id,
                        "property": "value",
                        "operator": "==",
                        "value": True,
                    },
                    {
                        "group": "device",
                        "type": "single",
                        "isTrigger": True,
                        "id": device_id,
                        "property": "value",
                        "operator": "==",
                        "value": False,
                    },
                ],
            },
            "actions": [
                {
                    "group": "scene",
                    "type": "scene",
                    "action": "execute",
                    "args": [[int(logger_scene_id)]],
                }
            ],
        }
    ]
    return {
        "name": block_scene_name(door),
        "description": (
            f"Trigger for HC3 dor {device_id}. Starter Lua-scene {logger_scene_id} ved apning og lukking."
        ),
        "type": "json",
        "mode": "automatic",
        "enabled": True,
        "hidden": False,
        "roomId": ROOM_ID,
        "categories": [1],
        "icon": "scene_block",
        "iconExtension": "png",
        "protectedByPin": False,
        "maxRunningInstances": 3,
        "restart": True,
        "content": json.dumps(content, ensure_ascii=False),
    }


def upsert_scene(scenes: list[dict], name: str, payload: dict, backup_dir: pathlib.Path, stamp: str, backup_suffix: str):
    existing = next((scene for scene in scenes if scene.get("name") == name), None)
    if existing:
        scene_id = existing["id"]
        _, current = request(f"/api/scenes/{scene_id}")
        (backup_dir / f"scene_{scene_id}_before_{backup_suffix}_{stamp}.json").write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        status, _ = request(f"/api/scenes/{scene_id}", method="PUT", body=payload)
        return "updated", status, scene_id

    status, created = request("/api/scenes", method="POST", body=payload)
    return "created", status, created.get("id")


def disable_legacy_triggers(scenes: list[dict], backup_dir: pathlib.Path, stamp: str) -> list[dict]:
    results = []
    if not DISABLE_LEGACY_TRIGGERS:
        return results
    for scene in scenes:
        name = str(scene.get("name") or "")
        if name not in LEGACY_TRIGGER_NAMES or not scene.get("enabled"):
            continue
        scene_id = int(scene["id"])
        _, current = request(f"/api/scenes/{scene_id}")
        (backup_dir / f"scene_{scene_id}_before_disable_legacy_door_{stamp}.json").write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        current["enabled"] = False
        status, _ = request(f"/api/scenes/{scene_id}", method="PUT", body=current)
        results.append({"scene_id": scene_id, "scene_name": name, "action": "disabled", "status": status})
    return results


def main():
    root = pathlib.Path(__file__).resolve().parents[1]
    backup_dir = root / "outputs" / "hc3_inventory" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")

    _, scenes = request("/api/scenes")
    results = []
    block_results = []
    for door in DOORS:
        name = scene_name(door)
        payload = lua_scene_payload(door)
        action, status, scene_id = upsert_scene(
            scenes,
            name,
            payload,
            backup_dir,
            stamp,
            f"single_door_{door['device_id']}",
        )

        result = {
            "action": action,
            "status": status,
            "scene_id": scene_id,
            "scene_name": name,
            "device_id": int(door["device_id"]),
            "device_key": door["device_key"],
            "block_scene_instruction": f"IF device {door['device_id']} value changes THEN run scene {scene_id}",
        }
        results.append(result)

        if EXECUTE_AFTER_UPSERT:
            try:
                execute_status, _ = request(f"/api/scenes/{scene_id}/execute", method="POST", body={})
                result["execute_status"] = execute_status
            except urllib.error.HTTPError as exc:
                result["execute_status"] = exc.code
                result["execute_error"] = exc.read().decode("utf-8", errors="replace")

        block_payload = block_scene_payload(door, int(scene_id))
        _, latest_scenes = request("/api/scenes")
        block_action, block_status, block_scene_id = upsert_scene(
            latest_scenes,
            block_payload["name"],
            block_payload,
            backup_dir,
            stamp,
            f"door_trigger_{door['device_id']}",
        )
        block_results.append(
            {
                "action": block_action,
                "status": block_status,
                "scene_id": block_scene_id,
                "scene_name": block_payload["name"],
                "device_id": int(door["device_id"]),
                "logger_scene_id": int(scene_id),
                "trigger": "value == true OR value == false",
            }
        )

    _, latest_scenes = request("/api/scenes")
    legacy_results = disable_legacy_triggers(latest_scenes, backup_dir, stamp)

    output = {
        "status": "ok",
        "hc3": BASE_URL,
        "room_id": ROOM_ID,
        "lua_scenes": results,
        "block_scenes": block_results,
        "legacy_triggers": legacy_results,
        "next_step": "Test each door once open/closed and verify that only one Fibaro10 event is written per state change.",
    }
    out_path = root / "outputs" / "hc3_inventory" / f"door_single_scene_map_{stamp}.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
