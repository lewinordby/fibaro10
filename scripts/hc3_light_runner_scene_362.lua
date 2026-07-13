--[[
%% properties
%% events
%% globals
%% autostart
--]]

-- SOLSTUDIO - samlet utelysstyring basert på lux.
--
-- Prinsipp:
--   - Én scene har ansvar for alt ute lys.
--   - Scenen leser lux-sensor og kontrollerer lys én gang.
--   - En separat block/cron-scene starter denne hvert 5. minutt.
--   - Lys med åpningstid kan bare slås på innenfor sitt tidsvindu.
--   - Hvis et lys er utenfor sitt tidsvindu, slås det av.
--   - Hysterese brukes for å unngå flimring:
--       PÅ når lux går under "på under"
--       AV når lux går over "av over"
--       Mellom verdiene beholdes nåværende tilstand.

-- ============================================================
-- INNSTILLINGER - endre kun her ved justering
-- ============================================================

local LOG_TAG = "UTE-LYS-LUX"

-- Hvor ofte trigger-scenen skal starte denne scenen.
local CHECK_INTERVAL_MINUTES = 5

-- Lux-sensor ute.
local SENSOR_ID = 433

-- Logging til ekstern tjeneste.
-- Nytt API bruker strukturerte felt på /events.
local RENDER_LOG_ENABLED = true
local RENDER_URL = "http://192.168.20.218:8110/events"
local CONFIG_URL = "http://192.168.20.218:8110/api/config/lights"

-- Åpning/stenging for lys som følger solsenterets åpningstid.
local OPEN_TIME = "06:45"
local CLOSE_STANDARD = "23:00"
local CLOSE_SPOT_INNGANG = "23:20"

-- Global testvariabel. Dette er den eneste globale variabelen scenen trenger.
local VAR_TEST_LUX = "UTE_LYS_TEST_LUX"

-- Enheter og grenser.
-- useTimeWindow = true betyr at lyset bare kan være på innenfor start/stop.
local LIGHTS = {
  {
    name = "Lyslist fasade",
    configKey = "lyslist",
    eventKey = "lyslist",
    onKey = "lyslist_on_lux",
    offKey = "lyslist_off_lux",
    startKey = "open_from",
    stopKey = "close_at",
    deviceId = 425,
    deviceIds = {425, 298},
    onBelowLux = 1000,
    offAboveLux = 1500,
    useTimeWindow = true,
    startTime = OPEN_TIME,
    stopTime = CLOSE_STANDARD
  },
  {
    name = "Reklameplakater teglfasade",
    configKey = "reklame",
    eventKey = "reklame",
    onKey = "reklame_on_lux",
    offKey = "reklame_off_lux",
    startKey = "open_from",
    stopKey = "close_at",
    deviceId = 427,
    onBelowLux = 500,
    offAboveLux = 700,
    useTimeWindow = true,
    startTime = OPEN_TIME,
    stopTime = CLOSE_STANDARD
  },
  {
    name = "Spot foran glassvegg",
    configKey = "spot_glass",
    eventKey = "spot_glass_275",
    onKey = "spot_glass_on_lux",
    offKey = "spot_glass_off_lux",
    startKey = "open_from",
    stopKey = "close_at",
    deviceId = 275,
    onBelowLux = 1500,
    offAboveLux = 2000,
    useTimeWindow = true,
    startTime = OPEN_TIME,
    stopTime = CLOSE_STANDARD
  },
  {
    name = "Spot foran massasje glassvegg",
    configKey = "spot_glass",
    eventKey = "spot_glass_299",
    onKey = "spot_glass_on_lux",
    offKey = "spot_glass_off_lux",
    startKey = "open_from",
    stopKey = "close_at",
    deviceId = 299,
    onBelowLux = 1500,
    offAboveLux = 2000,
    useTimeWindow = true,
    startTime = OPEN_TIME,
    stopTime = CLOSE_STANDARD
  },
  {
    name = "6xspot over inngang",
    configKey = "spot_inngang",
    eventKey = "spot_inngang",
    onKey = "spot_inngang_on_lux",
    offKey = "spot_inngang_off_lux",
    startKey = "open_from",
    stopKey = "entrance_close_at",
    deviceId = 424,
    onBelowLux = 100,
    offAboveLux = 150,
    useTimeWindow = true,
    startTime = OPEN_TIME,
    stopTime = CLOSE_SPOT_INNGANG
  },
  {
    name = "Gatelys parkering",
    configKey = "parkering",
    eventKey = "parkering",
    onKey = "parkering_on_lux",
    offKey = "parkering_off_lux",
    startKey = nil,
    stopKey = nil,
    deviceId = 440,
    onBelowLux = 50,
    offAboveLux = 80,
    useTimeWindow = false,
    startTime = "",
    stopTime = ""
  }
}

-- ============================================================
-- SLUTT INNSTILLINGER
-- ============================================================

local function log(message)
  fibaro.debug(LOG_TAG, tostring(message))
end

local function warn(message)
  fibaro.warning(LOG_TAG, tostring(message))
end

local function timeToMinutes(hhmm)
  local h, m = tostring(hhmm or ""):match("^(%d+):(%d+)$")
  if not h or not m then return nil end
  return tonumber(h) * 60 + tonumber(m)
end

local function nowMinutes()
  local now = os.date("*t")
  return now.hour * 60 + now.min
end

local function isWithinTimeWindow(light)
  if not light.useTimeWindow then return true end
  local startMin = timeToMinutes(light.startTime)
  local stopMin = timeToMinutes(light.stopTime)
  if not startMin or not stopMin then return false end

  local current = nowMinutes()
  if startMin <= stopMin then
    return current >= startMin and current < stopMin
  end

  -- Støtter tidsvinduer over midnatt hvis vi trenger det senere.
  return current >= startMin or current < stopMin
end

local function setGlobalVariable(name, value)
  local text = tostring(value or "")
  local ok, existing = pcall(api.get, "/globalVariables/" .. name)
  if ok and existing and existing.name then
    api.put("/globalVariables/" .. name, { name = name, value = text })
  else
    api.post("/globalVariables", { name = name, value = text })
  end
end

local function getGlobalVariable(name)
  local ok, variable = pcall(api.get, "/globalVariables/" .. name)
  if ok and variable and variable.value ~= nil then
    return tostring(variable.value)
  end
  return ""
end

local function getLux()
  local testValue = tonumber(getGlobalVariable(VAR_TEST_LUX))
  if testValue then
    return testValue, "TEST"
  end
  return tonumber(fibaro.getValue(SENSOR_ID, "value")), "SENSOR"
end

local function clearTestLuxIfUsed(luxSource)
  if luxSource == "TEST" then
    setGlobalVariable(VAR_TEST_LUX, "")
    log("Tømmer " .. VAR_TEST_LUX .. " etter testkjøring")
  end
end

local function jsonEscape(value)
  local text = tostring(value or "")
  text = text:gsub("\\", "\\\\")
  text = text:gsub('"', '\\"')
  text = text:gsub("\n", " ")
  text = text:gsub("\r", " ")
  return text
end

local function getTimestamp()
  return os.date("%Y-%m-%dT%H:%M:%S")
end

local function sampleBucket()
  local minute = math.floor(tonumber(os.date("%M")) / 5) * 5
  return string.format("%sT%s:%02d:00", os.date("%Y-%m-%d"), os.date("%H"), minute)
end

local function jsonNumber(value)
  return string.format("%.2f", tonumber(value or 0)):gsub(",", ".")
end

local function jsonBool(value)
  return value and "true" or "false"
end

local function lightDeviceIds(light)
  if type(light.deviceIds) == "table" and #light.deviceIds > 0 then
    return light.deviceIds
  end
  return { light.deviceId }
end

local function primaryDeviceId(light)
  return tonumber(lightDeviceIds(light)[1] or 0) or 0
end

local function deviceIdListText(light)
  local ids = {}
  for _, deviceId in ipairs(lightDeviceIds(light)) do
    ids[#ids + 1] = tostring(deviceId)
  end
  return table.concat(ids, ",")
end

local function jsonDeviceIdArray(light)
  return "[" .. deviceIdListText(light) .. "]"
end

local function numberValue(value, fallback)
  local parsed = tonumber(value)
  if parsed == nil then return fallback end
  return parsed
end

local function textValue(value, fallback)
  if value == nil or tostring(value) == "" then return fallback end
  return tostring(value)
end

local function applyConfigValues(config)
  local values = config.values or {}
  local devices = config.devices or {}
  local luxSensor = devices.lux_sensor or {}

  SENSOR_ID = numberValue(luxSensor.id, SENSOR_ID)
  CHECK_INTERVAL_MINUTES = numberValue(values.config_poll_minutes, CHECK_INTERVAL_MINUTES)
  OPEN_TIME = textValue(values.open_from, OPEN_TIME)
  CLOSE_STANDARD = textValue(values.close_at, CLOSE_STANDARD)
  CLOSE_SPOT_INNGANG = textValue(values.entrance_close_at, CLOSE_SPOT_INNGANG)

  for _, light in ipairs(LIGHTS) do
    light.onBelowLux = numberValue(values[light.onKey], light.onBelowLux)
    light.offAboveLux = numberValue(values[light.offKey], light.offAboveLux)
    if light.startKey then light.startTime = textValue(values[light.startKey], light.startTime) end
    if light.stopKey then light.stopTime = textValue(values[light.stopKey], light.stopTime) end
  end

  log("Hentet lysconfig fra app versjon " .. tostring(config.version or "?"))
end

local function applyRemoteConfigThen(callback)
  local http = net.HTTPClient()
  http:request(CONFIG_URL, {
    options = {
      method = "GET",
      headers = { ["Accept"] = "application/json" },
      timeout = 5000
    },
    success = function(response)
      if tonumber(response.status) ~= 200 then
        warn("Bruker lokal fallback-config. App-config svarte HTTP " .. tostring(response.status))
        callback()
        return
      end
      if not json or not json.decode then
        warn("Bruker lokal fallback-config. json.decode mangler")
        callback()
        return
      end
      local ok, decoded = pcall(json.decode, response.data or "")
      if ok and type(decoded) == "table" then
        applyConfigValues(decoded)
      else
        warn("Bruker lokal fallback-config. App-config hadde ugyldig JSON")
      end
      callback()
    end,
    error = function(message)
      warn("Bruker lokal fallback-config. Kunne ikke hente app-config: " .. tostring(message))
      callback()
    end
  })
end

local function logToRender(light, action, lux, reason)
  if not RENDER_LOG_ENABLED then return end
  if not lux then lux = getLux() end
  if not lux then
    warn("Logger ikke til Render fordi lux mangler")
    return
  end

  local actionValue = action == "PAA" and 1 or 0
  local stateValue = action == "PAA" and "true" or "false"
  local deviceKey = light.eventKey or light.configKey or ""
  local source = string.format("UTE LYS | %s | %s | key=%s | ids=%s", light.name, action, tostring(deviceKey), deviceIdListText(light))
  local payload = string.format(
    '{"system": "utelys", "event_type": "device_change", "timestamp": "%s", "action": "%s", "device_key": "%s", "device_id": %d, "device_name": "%s", "mode": "lux", "reason": "%s", "source": "%s", "lux": %s, "value": %s, "state": %s, "extra": {"device_key": "%s", "device_ids": %s}}',
    getTimestamp(),
    jsonEscape(action),
    jsonEscape(deviceKey),
    primaryDeviceId(light),
    jsonEscape(light.name),
    jsonEscape(reason or ""),
    jsonEscape(source),
    jsonNumber(lux),
    jsonNumber(actionValue),
    stateValue,
    jsonEscape(deviceKey),
    jsonDeviceIdArray(light)
  )

  local http = net.HTTPClient()
  http:request(RENDER_URL, {
    options = {
      method = "POST",
      headers = { ["Content-Type"] = "application/json" },
      data = payload,
      timeout = 5000
    },
    success = function(response)
      log("Render logg OK: " .. tostring(response.status) .. " " .. source .. " lux=" .. tostring(lux))
    end,
    error = function(err)
      warn("Render logg FEIL: " .. tostring(err) .. " " .. source)
    end
  })
end

local function isOn(deviceId)
  local value = fibaro.getValue(deviceId, "value")
  return tostring(value) == "true" or tostring(value) == "1" or tonumber(value or 0) == 1
end

local function anyDeviceOn(light)
  for _, deviceId in ipairs(lightDeviceIds(light)) do
    if isOn(deviceId) then return true end
  end
  return false
end

local function allDevicesOn(light)
  for _, deviceId in ipairs(lightDeviceIds(light)) do
    if not isOn(deviceId) then return false end
  end
  return true
end

local function logLuxSampleToRender(lux, luxSource, lightStates)
  if not RENDER_LOG_ENABLED then return end
  if not lux then
    warn("Logger ikke lux-sample fordi lux mangler")
    return
  end

  lightStates = lightStates or {}
  local source = string.format("UTE LYS | 5MIN_SAMPLE | lux_kilde=%s", tostring(luxSource or ""))
  local payload = string.format(
    '{"system": "utelys", "event_type": "sample_5min", "timestamp": "%s", "bucket_start": "%s", "mode": "lux", "source": "%s", "lux": %s, "value": %s, "light_lyslist": %s, "light_reklame": %s, "light_spot_glass_275": %s, "light_spot_glass_299": %s, "light_spot_inngang": %s, "light_parkering": %s, "extra": {"lux_kilde": "%s"}}',
    getTimestamp(),
    sampleBucket(),
    jsonEscape(source),
    jsonNumber(lux),
    jsonNumber(lux),
    jsonBool(lightStates["lyslist"]),
    jsonBool(lightStates["reklame"]),
    jsonBool(lightStates["spot_glass_275"]),
    jsonBool(lightStates["spot_glass_299"]),
    jsonBool(lightStates["spot_inngang"]),
    jsonBool(lightStates["parkering"]),
    jsonEscape(luxSource or "")
  )

  local http = net.HTTPClient()
  http:request(RENDER_URL, {
    options = {
      method = "POST",
      headers = { ["Content-Type"] = "application/json" },
      data = payload,
      timeout = 5000
    },
    success = function(response)
      log("Render lux-sample OK: " .. tostring(response.status) .. " lux=" .. tostring(lux))
    end,
    error = function(err)
      warn("Render lux-sample FEIL: " .. tostring(err))
    end
  })
end

local function turnOn(light, reason, lux)
  if not allDevicesOn(light) then
    for _, deviceId in ipairs(lightDeviceIds(light)) do
      if not isOn(deviceId) then
        fibaro.call(deviceId, "turnOn")
        log("PÅ " .. light.name .. " (" .. deviceId .. "): " .. tostring(reason or ""))
      end
    end
    logToRender(light, "PAA", lux, reason)
  end
  return true
end

local function turnOff(light, reason, lux)
  if anyDeviceOn(light) then
    for _, deviceId in ipairs(lightDeviceIds(light)) do
      if isOn(deviceId) then
        fibaro.call(deviceId, "turnOff")
        log("AV " .. light.name .. " (" .. deviceId .. "): " .. tostring(reason or ""))
      end
    end
    logToRender(light, "AV", lux, reason)
  end
  return false
end

local function describeDecision(light, lux, action, reason)
  local window = "hele døgnet"
  if light.useTimeWindow then
    window = tostring(light.startTime) .. "-" .. tostring(light.stopTime)
  end

  return string.format(
    "lux=%.0f on<%s off>%s vindu=%s handling=%s grunn=%s",
    lux,
    tostring(light.onBelowLux),
    tostring(light.offAboveLux),
    window,
    tostring(action),
    tostring(reason or "")
  )
end

local function applyLight(light, lux)
  local insideWindow = isWithinTimeWindow(light)

  if not insideWindow then
    turnOff(light, "utenfor tidsvindu", lux)
    log(describeDecision(light, lux, "AV", "utenfor tidsvindu"))
    return
  end

  if lux < light.onBelowLux then
    turnOn(light, "lux under på-grense", lux)
    log(describeDecision(light, lux, "PÅ", "lux under på-grense"))
  elseif lux > light.offAboveLux then
    turnOff(light, "lux over av-grense", lux)
    log(describeDecision(light, lux, "AV", "lux over av-grense"))
  else
    log(describeDecision(light, lux, "INGEN ENDRING", "hysterese"))
  end
end

local function desiredStateForSample(light, lux)
  if not isWithinTimeWindow(light) then return false end
  if lux < light.onBelowLux then return true end
  if lux > light.offAboveLux then return false end
  return anyDeviceOn(light)
end

local function applyAllLights()
  setGlobalVariable(VAR_TEST_LUX, getGlobalVariable(VAR_TEST_LUX))

  local lux, luxSource = getLux()
  if not lux then
    warn("Kan ikke lese lux-sensor " .. SENSOR_ID)
    return
  end

  log("Kontrollerer utelys: lux=" .. tostring(lux) .. " kilde=" .. tostring(luxSource))

  local lightStates = {}
  for _, light in ipairs(LIGHTS) do
    applyLight(light, lux)
    lightStates[light.eventKey or light.configKey] = desiredStateForSample(light, lux)
  end

  logLuxSampleToRender(lux, luxSource, lightStates)
  clearTestLuxIfUsed(luxSource)
end

log("Starter samlet luxstyring for utelys")
applyRemoteConfigThen(function()
  applyAllLights()
  log("Ferdig med en kontrollrunde")
end)
