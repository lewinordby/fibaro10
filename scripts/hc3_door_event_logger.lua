--[[
%% properties
453 value
447 value
413 value
%% events
%% globals
--]]

-- LILLETORGET - DOOR / MAGNET SENSOR LOGGER TO FIBARO10
--
-- Logs open/closed changes from HC3 contact sensors to Fibaro10.
-- Automatic trigger logs only the changed device.
-- Manual execution logs current status for all configured devices.

local LOG_TAG = "DOOR-LOGGER"
local API_URL = "http://192.168.20.218:8110/api/hc3/door-events"
local SOURCE = "HC3 DOOR LOGGER"

local DEVICES = {
  [453] = { key = "door_453", name = "96.0 bod/kjokken" },
  [447] = { key = "door_447", name = "94.0 Kjeller luke" },
  [413] = { key = "door_413", name = "86.0 Arbeidsrom" }
}

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

local function globalName(deviceId)
  return "F10_DOOR_" .. tostring(deviceId) .. "_LAST"
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
    api.put("/globalVariables/" .. name, { name = name, value = text })
  else
    api.post("/globalVariables", { name = name, value = text })
  end
end

local function getDeviceName(deviceId, fallback)
  local ok, device = pcall(api.get, "/devices/" .. tostring(deviceId))
  if ok and device and device.name and tostring(device.name) ~= "" then
    return tostring(device.name)
  end
  return fallback
end

local function getBatteryLevel(deviceId)
  local ok, device = pcall(api.get, "/devices/" .. tostring(deviceId))
  if ok and device and device.properties then
    return tonumber(device.properties.batteryLevel)
  end
  return nil
end

local function postPayload(payload, done)
  local http = net.HTTPClient()
  http:request(API_URL, {
    options = {
      method = "POST",
      headers = {
        ["Content-Type"] = "application/json"
      },
      data = json.encode(payload),
      timeout = 8000
    },
    success = function(response)
      if tonumber(response.status) >= 200 and tonumber(response.status) < 300 then
        log("Sent OK " .. tostring(response.status) .. ": " .. tostring(payload.device_id) .. " " .. tostring(payload.action))
      else
        warn("Fibaro10 svarte " .. tostring(response.status) .. ": " .. tostring(response.data))
      end
      if done then done() end
    end,
    error = function(err)
      warn("Feil ved sending: " .. tostring(err))
      if done then done() end
    end
  })
end

local function triggerDeviceId()
  local trigger = sourceTrigger or {}
  local id = trigger.deviceID or trigger.deviceId or trigger.id
  local numeric = tonumber(id)
  if numeric and DEVICES[numeric] then return numeric, trigger end
  return nil, trigger
end

local function orderedDeviceIds()
  local ids = {}
  for deviceId, _ in pairs(DEVICES) do
    ids[#ids + 1] = deviceId
  end
  table.sort(ids)
  return ids
end

local function sendDevice(deviceId, trigger, done)
  local config = DEVICES[deviceId]
  if not config then
    if done then done() end
    return
  end

  local raw = fibaro.getValue(deviceId, "value")
  local state = boolFromRaw(raw)
  local action = actionFromState(state)
  local previousText = getGlobalVariable(globalName(deviceId))
  local previousState = boolFromRaw(previousText)

  local payload = {
    timestamp = timestamp(),
    event_type = "door_change",
    action = action,
    device_key = config.key,
    device_id = deviceId,
    device_name = getDeviceName(deviceId, config.name),
    source = SOURCE,
    raw_value = valueToText(raw),
    state = state,
    previous_state = previousState,
    battery_level = getBatteryLevel(deviceId),
    extra = {
      trigger_type = tostring((trigger or {}).type or "manual"),
      trigger_property = tostring((trigger or {}).propertyName or (trigger or {}).property or "value")
    }
  }

  setGlobalVariable(globalName(deviceId), valueToText(raw))
  log("Sender " .. tostring(payload.device_name) .. " " .. action .. " raw=" .. tostring(raw))
  postPayload(payload, done)
end

local function sendAllDevices(deviceIds, index, trigger)
  if index > #deviceIds then
    log("Manuell statussending ferdig.")
    return
  end
  sendDevice(deviceIds[index], trigger, function()
    fibaro.setTimeout(250, function()
      sendAllDevices(deviceIds, index + 1, trigger)
    end)
  end)
end

local triggeredId, trigger = triggerDeviceId()
if triggeredId then
  sendDevice(triggeredId, trigger)
else
  log("Ingen spesifikk trigger. Sender status for alle dorer.")
  sendAllDevices(orderedDeviceIds(), 1, trigger)
end
