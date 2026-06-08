--[[
  LILLETORGET - KJELLER AVFUKTER TIL FIBARO10

  Styrer avfukter i kjeller fra HC3:
    - temperatur: device 444
    - fukt: device 445
    - avfukter rele/bryter: device 449

  Scenen leser terskler fra fibaro10 /api/config/ventilation:
    - basement_humidity_start
    - basement_humidity_stop
    - basement_min_temp

  Anbefalt bruk:
    - Kjor hvert 5. minutt, eller trigges naar temp/fukt endres.
    - Kan ogsaa kjore kontinuerlig med INTERVAL_SECONDS hvis onskelig.
--]]

-- ============================================================
-- KONFIGURASJON
-- ============================================================

local API_BASE = "http://192.168.20.218:8110"
local CONFIG_URL = API_BASE .. "/api/config/ventilation"
local EVENTS_URL = API_BASE .. "/events"
local SOURCE = "HC3 KJELLER AVFUKTER"
local INTERVAL_SECONDS = 300
local RUN_FOREVER = false

local DEVICE_IDS = {
  temp_kjeller = 444,
  humidity_kjeller = 445,
  fan_avfukter = 449
}

local DEFAULTS = {
  basement_humidity_start = 60.0,
  basement_humidity_stop = 55.0,
  basement_min_temp = 5.0
}

-- ============================================================
-- HJELPEFUNKSJONER
-- ============================================================

local function timestamp()
  return os.date("%Y-%m-%dT%H:%M:%S")
end

local function numberValue(deviceId)
  local raw = fibaro.getValue(deviceId, "value")
  local value = tonumber(raw)
  if value == nil then
    fibaro.warning("Avfukter", "Kan ikke lese verdi fra device " .. tostring(deviceId) .. " (" .. tostring(raw) .. ")")
  end
  return value
end

local function boolValue(deviceId)
  local raw = fibaro.getValue(deviceId, "value")
  return raw == true or raw == "true" or raw == "1" or raw == 1
end

local function requestJson(method, url, payload, callback)
  local http = net.HTTPClient()
  http:request(url, {
    options = {
      method = method,
      headers = { ["Content-Type"] = "application/json" },
      data = payload and json.encode(payload) or nil,
      timeout = 8000
    },
    success = function(response)
      if response.status >= 200 and response.status < 300 then
        local data = nil
        if response.data and response.data ~= "" then
          data = json.decode(response.data)
        end
        callback(true, data, response)
      else
        fibaro.warning("Avfukter", url .. " svarte " .. tostring(response.status) .. ": " .. tostring(response.data))
        callback(false, nil, response)
      end
    end,
    error = function(err)
      fibaro.warning("Avfukter", "Feil mot " .. url .. ": " .. tostring(err))
      callback(false, nil, nil)
    end
  })
end

local function postEvent(payload)
  requestJson("POST", EVENTS_URL, payload, function(ok)
    if ok then
      fibaro.debug("Avfukter", "Logget " .. tostring(payload.event_type) .. " til fibaro10")
    end
  end)
end

local function setDehumidifier(target)
  local current = boolValue(DEVICE_IDS.fan_avfukter)
  if current == target then
    return false
  end
  fibaro.call(DEVICE_IDS.fan_avfukter, target and "turnOn" or "turnOff")
  return true
end

local function decide(temp, humidity, isOn, values)
  if temp == nil or humidity == nil then
    return isOn, "Mangler temp/fukt fra kjeller"
  end
  if temp < values.basement_min_temp then
    return false, "Kjeller under minimumstemperatur"
  end
  if humidity >= values.basement_humidity_start then
    return true, "Fukt over startgrense"
  end
  if humidity <= values.basement_humidity_stop then
    return false, "Fukt under stoppgrense"
  end
  return isOn, "Innenfor hysterese"
end

local function mergedValues(config)
  local values = {}
  for key, value in pairs(DEFAULTS) do
    values[key] = value
  end
  if config and config.values then
    for key, value in pairs(config.values) do
      if DEFAULTS[key] ~= nil and tonumber(value) ~= nil then
        values[key] = tonumber(value)
      end
    end
  end
  return values
end

local function runOnce()
  requestJson("GET", CONFIG_URL, nil, function(_, config)
    local values = mergedValues(config)
    local temp = numberValue(DEVICE_IDS.temp_kjeller)
    local humidity = numberValue(DEVICE_IDS.humidity_kjeller)
    local current = boolValue(DEVICE_IDS.fan_avfukter)
    local target, reason = decide(temp, humidity, current, values)
    local changed = setDehumidifier(target)
    local now = timestamp()

    local basePayload = {
      system = "ventilasjon",
      source = SOURCE,
      timestamp = now,
      device_key = "dehumidifier_basement",
      device_id = DEVICE_IDS.fan_avfukter,
      device_name = "Avfukter kjeller",
      mode = "KJELLER_AVFUKTING",
      reason = reason,
      temp_kjeller = temp,
      humidity_kjeller = humidity,
      fan_avfukter = target,
      state = target,
      extra = {
        config_values = values,
        device_ids = DEVICE_IDS
      }
    }

    local samplePayload = basePayload
    samplePayload.event_type = "sample_5min"
    postEvent(samplePayload)

    if changed then
      local eventPayload = {}
      for key, value in pairs(basePayload) do
        eventPayload[key] = value
      end
      eventPayload.event_type = "fan_change"
      eventPayload.action = target and "PAA" or "AV"
      postEvent(eventPayload)
      fibaro.debug("Avfukter", "Endret til " .. tostring(eventPayload.action) .. ": " .. reason)
    else
      fibaro.debug("Avfukter", "Ingen endring: " .. reason)
    end
  end)
end

local function loop()
  runOnce()
  if RUN_FOREVER then
    fibaro.setTimeout(INTERVAL_SECONDS * 1000, loop)
  end
end

loop()
