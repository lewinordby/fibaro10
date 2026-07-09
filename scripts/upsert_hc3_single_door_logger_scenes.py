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

DOORS = [
    {"device_id": 453, "device_key": "door_453", "name": "96.0 bod/kjokken", "title": "Bod/kjokken"},
    {"device_id": 447, "device_key": "door_447", "name": "94.0 Kjeller luke", "title": "Kjeller luke"},
    {"device_id": 413, "device_key": "door_413", "name": "86.0 Arbeidsrom", "title": "Arbeidsrom"},
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

local function postPayload(payload)
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
      if tonumber(response.status) >= 200 and tonumber(response.status) < 300 then
        log("Sent OK " .. tostring(response.status) .. ": " .. tostring(payload.device_id) .. " " .. tostring(payload.action))
      else
        warn("Fibaro10 svarte " .. tostring(response.status) .. ": " .. tostring(response.data))
      end
    end,
    error = function(err)
      warn("Feil ved sending: " .. tostring(err))
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


def scene_payload(door: dict) -> dict:
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


def main():
    root = pathlib.Path(__file__).resolve().parents[1]
    backup_dir = root / "outputs" / "hc3_inventory" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")

    _, scenes = request("/api/scenes")
    results = []
    for door in DOORS:
        name = scene_name(door)
        existing = next((scene for scene in scenes if scene.get("name") == name), None)
        payload = scene_payload(door)
        if existing:
            scene_id = existing["id"]
            _, current = request(f"/api/scenes/{scene_id}")
            (backup_dir / f"scene_{scene_id}_before_single_door_{door['device_id']}_{stamp}.json").write_text(
                json.dumps(current, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            status, _ = request(f"/api/scenes/{scene_id}", method="PUT", body=payload)
            action = "updated"
        else:
            status, created = request("/api/scenes", method="POST", body=payload)
            scene_id = created.get("id")
            action = "created"

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

    output = {
        "status": "ok",
        "hc3": BASE_URL,
        "room_id": ROOM_ID,
        "scenes": results,
        "next_step": "Create one HC3 block scene per door: when the door sensor value changes, run the listed logger scene.",
    }
    out_path = root / "outputs" / "hc3_inventory" / f"door_single_scene_map_{stamp}.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
