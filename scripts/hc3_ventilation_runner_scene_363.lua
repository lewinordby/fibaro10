--[[
%% properties
%% events
%% globals
--]]

-- SOLSTUDIO - ventilasjonsstyring
--
-- Kortkjørende Lua-scene som startes hvert 5. minutt av en egen trigger-scene.
-- Scenen vurderer temperaturer, estimert solsengaktivitet og varmebehov før den
-- styrer innblåsing og avtrekk.

-- ============================================================
-- INNSTILLINGER - endre kun her ved justering
-- ============================================================

local LOG_TAG = "VENT-STYRING"
local CHECK_INTERVAL_MINUTES = 5

-- Temperaturfølere
local TEMP_1ETG_ID = 407
local TEMP_2ETG_ID = 346
local TEMP_VIP_MAIN_ID = 341
local TEMP_VIP_SUB_ID = 349
local TEMP_INNE_FALLBACK_ID = TEMP_VIP_MAIN_ID
local TEMP_UTE_ID = 351
local TEMP_YR_ID = 3
local TEMP_PASSIV_INNLUFT_ID = 358
local TEMP_LOFT_ID = 354
local HUMIDITY_1ETG_ID = 408
local HUMIDITY_2ETG_ID = 344
local HUMIDITY_VIP_ID = 347
local HUMIDITY_UTE_ID = 350
local HUMIDITY_LOFT_ID = 353
local HUMIDITY_LUFTINNTAK_ID = 357
local TEMP_KJELLER_ID = 444
local HUMIDITY_KJELLER_ID = 445

-- Vifter
local FAN_INNLUFT_VIP_ID = 130
local FAN_INNLUFT_2ETG_ID = 160
local FAN_AVTREKK_TAK_ID = 134
local FAN_AVFUKTER_ID = 449
local FAN_INNLUFT_VIP_KEY = "vip_intake"
local FAN_INNLUFT_2ETG_KEY = "floor_intake"
local FAN_AVTREKK_TAK_KEY = "roof_exhaust"
local FAN_AVFUKTER_KEY = "dehumidifier_basement"

-- Effekt / solsengestimat
-- Differanse R er allerede beregnet i HC3 og brukes som estimat for ukjent forbruk.
local POWER_DIFFERANSE_R_ID = 331
local SOLSENG_1_ON_W = 4000
local SOLSENG_1_OFF_W = 2500
local SOLSENG_2_ON_W = 12000
local SOLSENG_2_OFF_W = 9000
local SOLSENG_ETTERLOP_MINUTES = 30
local VAR_SOLSENG_SIST_AKTIV = "VENT_SOLSENG_SIST_AKTIV"

-- Testverdier. Hvis en verdi settes her, brukes den i neste kjoring og tommes etterpa.
-- VENT_TEST_TEMP_INNE brukes for alle innvendige temperaturer, loft og passiv innluft.
local VAR_TEST_TEMP_INNE = "VENT_TEST_TEMP_INNE"
local VAR_TEST_TEMP_UTE = "VENT_TEST_TEMP_UTE"
local VAR_TEST_DIFF_W = "VENT_TEST_DIFF_W"

-- Temperaturgrenser
local VARMEBEHOV_MIN_UNDER = 22.0
local VARMEBEHOV_AVG_UNDER = 22.5

local KJOLEBEHOV_MAX_OVER = 24.0
local KJOLEBEHOV_AVG_OVER = 23.5

local AVTREKK_LOFT_ON = 29.0
local AVTREKK_LOFT_SAFETY_ON = 34.0
local AVTREKK_LOFT_OFF = 27.0
local AVTREKK_MAX_INNE_ON = 24.5
local AVTREKK_MAX_INNE_OFF = 25.0
local AVTREKK_LOFT_HOT_INSIDE_ON = 27.0

local INNLUFT_UTE_MIN_ON = 10.0
local INNLUFT_UTE_HARD_MIN_ON = 8.0
local INNLUFT_UTE_OFF_UNDER = 7.0
local MEKANISK_VENT_MIN_UTE = 7.0
local INNLUFT_COOL_DELTA = 1.5
local INNLUFT_ZONE_ON_OVER = 23.8
local INNLUFT_ZONE_AVG_ON_OVER = 23.5
local INNLUFT_ZONE_OFF_UNDER = 23.2
local VIP_INNLUFT_ON_OVER = INNLUFT_ZONE_ON_OVER
local VIP_INNLUFT_OFF_UNDER = INNLUFT_ZONE_OFF_UNDER
local FLOOR_INNLUFT_ON_OVER = INNLUFT_ZONE_ON_OVER
local FLOOR_INNLUFT_OFF_UNDER = INNLUFT_ZONE_OFF_UNDER
local INNLUFT_KALD_SPERRE_UNDER = 15.0
local BASEMENT_HUMIDITY_ON = 60.0
local BASEMENT_HUMIDITY_OFF = 55.0
local BASEMENT_MIN_TEMP = 5.0

-- Driftstid
local APNING_START_HOUR = 7.0
local STENGING_HOUR = 23.0
local AVTREKK_STOP_HOUR = 22.0
local FORKJOLING_START_HOUR = 5.0
local FORKJOLING_MIN_INNE = 23.0
local FORKJOLING_COOL_DELTA = 1.0

-- Logging til Render
local RENDER_LOG_ENABLED = true
local RENDER_URL = "http://192.168.20.218:8110/events"
local CONFIG_URL = "http://192.168.20.218:8110/api/config/ventilation"
local LOG_CONTEXT = {}

-- ============================================================
-- SLUTT INNSTILLINGER
-- ============================================================

local function log(message)
  fibaro.debug(LOG_TAG, tostring(message))
end

local function warn(message)
  fibaro.warning(LOG_TAG, tostring(message))
end

local function getNumber(deviceId, property)
  return tonumber(fibaro.getValue(deviceId, property or "value"))
end

local function isDead(deviceId)
  local ok, device = pcall(api.get, "/devices/" .. tostring(deviceId))
  if ok and device and device.properties then
    return device.properties.dead == true
  end
  return false
end

local function getRoomTempWithFallback(primaryId, fallbackId, label)
  local value = getNumber(primaryId, "value")
  if value and not isDead(primaryId) then
    return value, "SENSOR"
  end

  local fallback = getNumber(fallbackId, "value")
  if fallback then
    warn(label .. " bruker fallback fra hovedenhet inne fordi sensor mangler eller er dead")
    return fallback, "FALLBACK_HOVED_INNE"
  end

  return value, "MANGLER"
end

local function getOutdoorTemp()
  local netatmo = getNumber(TEMP_UTE_ID, "value")
  local yr = getNumber(TEMP_YR_ID, "Temperature")
  if netatmo then return netatmo, "NETATMO", netatmo, yr end
  if yr then return yr, "YR", netatmo, yr end
  return nil, "MANGLER", netatmo, yr
end

local function getGlobalVariable(name)
  local ok, variable = pcall(api.get, "/globalVariables/" .. name)
  if ok and variable and variable.value ~= nil then
    return tostring(variable.value)
  end
  return ""
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

local function getTestNumber(name)
  local raw = getGlobalVariable(name)
  raw = tostring(raw or ""):match("^%s*(.-)%s*$")
  if raw == "" then return nil, false end

  local value = tonumber((raw:gsub(",", ".")))
  if not value then
    warn("Testvariabel " .. name .. " har ugyldig verdi: " .. raw)
    return nil, true
  end
  return value, true
end

local function clearTestVariables()
  setGlobalVariable(VAR_TEST_TEMP_INNE, "")
  setGlobalVariable(VAR_TEST_TEMP_UTE, "")
  setGlobalVariable(VAR_TEST_DIFF_W, "")
end

local function isOn(deviceId)
  local value = fibaro.getValue(deviceId, "value")
  return tostring(value) == "true" or tostring(value) == "1" or tonumber(value or 0) == 1
end

local function avg(values)
  local sum = 0
  local count = 0
  for _, value in ipairs(values) do
    if value then
      sum = sum + value
      count = count + 1
    end
  end
  if count == 0 then return nil end
  return sum / count
end

local function minValue(values)
  local out = nil
  for _, value in ipairs(values) do
    if value and (not out or value < out) then out = value end
  end
  return out
end

local function maxValue(values)
  local out = nil
  for _, value in ipairs(values) do
    if value and (not out or value > out) then out = value end
  end
  return out
end

local function hourNow()
  return tonumber(os.date("%H")) + (tonumber(os.date("%M")) / 60)
end

local function inTimeWindow(nowHour, startHour, stopHour)
  return nowHour >= startHour and nowHour < stopHour
end

local function jsonEscape(value)
  local text = tostring(value or "")
  text = text:gsub("\\", "\\\\")
  text = text:gsub('"', '\\"')
  text = text:gsub("\n", " ")
  text = text:gsub("\r", " ")
  return text
end

local function jsonNumber(value)
  return string.format("%.2f", tonumber(value or 0)):gsub(",", ".")
end

local function jsonOptionalNumber(value)
  if value == nil then return "null" end
  return jsonNumber(value)
end

local function jsonBool(value)
  return value and "true" or "false"
end

local function jsonContextBoolOrDevice(value, deviceId)
  if value ~= nil then return jsonBool(value) end
  return jsonBool(isOn(deviceId))
end

local function numberValue(value, fallback)
  local parsed = tonumber(value)
  if parsed == nil then return fallback end
  return parsed
end

local function timeToHour(value, fallback)
  local h, m = tostring(value or ""):match("^(%d+):(%d+)$")
  if not h or not m then return fallback end
  return tonumber(h) + (tonumber(m) / 60)
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

      local ok, config = pcall(json.decode, response.data or "")
      if ok and type(config) == "table" then
        local values = config.values or {}
        local stopBeforeClose = numberValue(values.exhaust_stop_before_close_minutes, 60)
        APNING_START_HOUR = timeToHour(values.open_from, APNING_START_HOUR)
        STENGING_HOUR = timeToHour(values.close_at, STENGING_HOUR)
        FORKJOLING_START_HOUR = timeToHour(values.pre_cooling_from, FORKJOLING_START_HOUR)
        AVTREKK_STOP_HOUR = STENGING_HOUR - (stopBeforeClose / 60)

        MEKANISK_VENT_MIN_UTE = numberValue(values.mechanical_min_outdoor_temp, MEKANISK_VENT_MIN_UTE)
        INNLUFT_UTE_MIN_ON = numberValue(values.intake_min_outdoor_temp, INNLUFT_UTE_MIN_ON)
        INNLUFT_COOL_DELTA = numberValue(values.outdoor_cooler_delta, INNLUFT_COOL_DELTA)
        VARMEBEHOV_MIN_UNDER = numberValue(values.max_indoor_heat_need_temp, VARMEBEHOV_MIN_UNDER)
        VARMEBEHOV_AVG_UNDER = numberValue(values.max_indoor_heat_need_temp, VARMEBEHOV_AVG_UNDER)

        VIP_INNLUFT_ON_OVER = numberValue(values.vip_start_temp, VIP_INNLUFT_ON_OVER)
        VIP_INNLUFT_OFF_UNDER = numberValue(values.vip_stop_temp, VIP_INNLUFT_OFF_UNDER)
        FLOOR_INNLUFT_ON_OVER = numberValue(values.floor_start_temp, FLOOR_INNLUFT_ON_OVER)
        FLOOR_INNLUFT_OFF_UNDER = numberValue(values.floor_stop_temp, FLOOR_INNLUFT_OFF_UNDER)
        INNLUFT_ZONE_ON_OVER = FLOOR_INNLUFT_ON_OVER
        INNLUFT_ZONE_OFF_UNDER = FLOOR_INNLUFT_OFF_UNDER

        AVTREKK_LOFT_ON = numberValue(values.loft_exhaust_start_temp, AVTREKK_LOFT_ON)
        AVTREKK_LOFT_OFF = numberValue(values.loft_exhaust_stop_temp, AVTREKK_LOFT_OFF)
        AVTREKK_MAX_INNE_ON = numberValue(values.indoor_allow_exhaust_temp, AVTREKK_MAX_INNE_ON)
        AVTREKK_MAX_INNE_OFF = AVTREKK_MAX_INNE_ON
        BASEMENT_HUMIDITY_ON = numberValue(values.basement_humidity_start, BASEMENT_HUMIDITY_ON)
        BASEMENT_HUMIDITY_OFF = numberValue(values.basement_humidity_stop, BASEMENT_HUMIDITY_OFF)
        BASEMENT_MIN_TEMP = numberValue(values.basement_min_temp, BASEMENT_MIN_TEMP)
        SOLSENG_1_ON_W = numberValue(values.sunbed_power_1_threshold_w, SOLSENG_1_ON_W)
        SOLSENG_2_ON_W = numberValue(values.sunbed_power_2_threshold_w, SOLSENG_2_ON_W)
        SOLSENG_ETTERLOP_MINUTES = numberValue(values.afterrun_minutes, SOLSENG_ETTERLOP_MINUTES)

        log("Hentet ventilasjonsconfig fra app versjon " .. tostring(config.version or "?"))
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

local function sampleBucket()
  local minute = math.floor(tonumber(os.date("%M")) / 5) * 5
  return string.format("%sT%s:%02d:00", os.date("%Y-%m-%d"), os.date("%H"), minute)
end

local function logToRender(label, deviceKey, deviceId, action, tempValue, reason, mode)
  if not RENDER_LOG_ENABLED then return end
  local actionValue = action == "PAA" and 1 or 0
  local stateValue = action == "PAA" and "true" or "false"
  local source = string.format("VENTILASJON | %s | %s | key=%s | id=%s | modus=%s | %s", label, action, tostring(deviceKey or ""), tostring(deviceId), tostring(mode or ""), tostring(reason or ""))
  local payload = string.format(
    '{"system": "ventilasjon", "event_type": "fan_change", "timestamp": "%s", "action": "%s", "device_key": "%s", "device_id": %d, "device_name": "%s", "mode": "%s", "reason": "%s", "source": "%s", "value": %s, "state": %s, "temp_1etg": %s, "temp_2etg": %s, "temp_vip": %s, "temp_ute": %s, "temp_loft": %s, "humidity_1etg": %s, "humidity_2etg": %s, "humidity_vip": %s, "humidity_ute": %s, "humidity_yr": %s, "humidity_loft": %s, "temp_kjeller": %s, "humidity_kjeller": %s, "temp_passiv": %s, "temp_luftinntak": %s, "humidity_passiv": %s, "humidity_luftinntak": %s, "diff_w": %s, "fan_avfukter": %s, "extra": {"device_key": "%s", "trigger": "%s", "avg_inne": %s, "min_inne": %s, "max_inne": %s, "solsenger": %s}}',
    os.date("%Y-%m-%dT%H:%M:%S"),
    jsonEscape(action),
    jsonEscape(deviceKey or ""),
    tonumber(deviceId or 0),
    jsonEscape(label),
    jsonEscape(mode or ""),
    jsonEscape(reason or ""),
    jsonEscape(source),
    jsonNumber(tempValue),
    stateValue,
    jsonNumber(LOG_CONTEXT.temp1),
    jsonNumber(LOG_CONTEXT.temp2),
    jsonNumber(LOG_CONTEXT.tempVip),
    jsonNumber(LOG_CONTEXT.tempUte),
    jsonNumber(LOG_CONTEXT.tempLoft),
    jsonNumber(LOG_CONTEXT.humidity1),
    jsonNumber(LOG_CONTEXT.humidity2),
    jsonNumber(LOG_CONTEXT.humidityVip),
    jsonNumber(LOG_CONTEXT.humidityUte),
    jsonNumber(LOG_CONTEXT.humidityYr),
    jsonNumber(LOG_CONTEXT.humidityLoft),
    jsonNumber(LOG_CONTEXT.tempKjeller),
    jsonNumber(LOG_CONTEXT.humidityKjeller),
    jsonNumber(LOG_CONTEXT.tempPassiv),
    jsonNumber(LOG_CONTEXT.tempPassiv),
    jsonNumber(LOG_CONTEXT.humidityLuftinntak),
    jsonNumber(LOG_CONTEXT.humidityLuftinntak),
    jsonNumber(LOG_CONTEXT.diffW),
    jsonBool((deviceKey == FAN_AVFUKTER_KEY and action == "PAA") or LOG_CONTEXT.fanAvfukterOn),
    jsonEscape(deviceKey or ""),
    jsonEscape(reason or ""),
    jsonNumber(LOG_CONTEXT.avgInne),
    jsonNumber(LOG_CONTEXT.minInne),
    jsonNumber(LOG_CONTEXT.maxInne),
    tostring(LOG_CONTEXT.sunbeds or 0)
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
      log("Render OK: " .. tostring(response.status) .. " " .. source)
    end,
    error = function(err)
      warn("Render FEIL: " .. tostring(err) .. " " .. source)
    end
  })
end

local function logSampleToRender(mode, force)
  if not RENDER_LOG_ENABLED then return end

  local bucket = sampleBucket()

  local source = string.format(
    "VENTILASJON | 5MIN_SAMPLE | modus=%s | ute_kilde=%s",
    tostring(mode or LOG_CONTEXT.mode or ""),
    tostring(LOG_CONTEXT.uteSource or "")
  )

  local payload = string.format(
    '{"system": "ventilasjon", "event_type": "sample_5min", "timestamp": "%s", "bucket_start": "%s", "mode": "%s", "source": "%s", "temp_1etg": %s, "temp_2etg": %s, "temp_vip": %s, "temp_ute": %s, "temp_ute_netatmo": %s, "temp_yr": %s, "temp_loft": %s, "humidity_1etg": %s, "humidity_2etg": %s, "humidity_vip": %s, "humidity_ute": %s, "humidity_yr": %s, "humidity_loft": %s, "temp_kjeller": %s, "humidity_kjeller": %s, "temp_passiv": %s, "temp_luftinntak": %s, "humidity_passiv": %s, "humidity_luftinntak": %s, "temp_min_inne": %s, "temp_avg_inne": %s, "temp_max_inne": %s, "diff_w": %s, "estimated_sunbeds": %s, "afterrun_active": %s, "heat_need": %s, "cool_need": %s, "open_time": %s, "pre_cooling": %s, "exhaust_time_allowed": %s, "fan_vip": %s, "fan_2etg": %s, "fan_tak": %s, "fan_avfukter": %s, "extra": {"ute_kilde": "%s", "force": %s}}',
    os.date("%Y-%m-%dT%H:%M:%S"),
    bucket,
    jsonEscape(mode or LOG_CONTEXT.mode or ""),
    jsonEscape(source),
    jsonOptionalNumber(LOG_CONTEXT.temp1),
    jsonOptionalNumber(LOG_CONTEXT.temp2),
    jsonOptionalNumber(LOG_CONTEXT.tempVip),
    jsonOptionalNumber(LOG_CONTEXT.tempUte),
    jsonOptionalNumber(LOG_CONTEXT.tempUteNetatmo),
    jsonOptionalNumber(LOG_CONTEXT.tempYr),
    jsonOptionalNumber(LOG_CONTEXT.tempLoft),
    jsonOptionalNumber(LOG_CONTEXT.humidity1),
    jsonOptionalNumber(LOG_CONTEXT.humidity2),
    jsonOptionalNumber(LOG_CONTEXT.humidityVip),
    jsonOptionalNumber(LOG_CONTEXT.humidityUte),
    jsonOptionalNumber(LOG_CONTEXT.humidityYr),
    jsonOptionalNumber(LOG_CONTEXT.humidityLoft),
    jsonOptionalNumber(LOG_CONTEXT.tempKjeller),
    jsonOptionalNumber(LOG_CONTEXT.humidityKjeller),
    jsonOptionalNumber(LOG_CONTEXT.tempPassiv),
    jsonOptionalNumber(LOG_CONTEXT.tempPassiv),
    jsonOptionalNumber(LOG_CONTEXT.humidityLuftinntak),
    jsonOptionalNumber(LOG_CONTEXT.humidityLuftinntak),
    jsonOptionalNumber(LOG_CONTEXT.minInne),
    jsonOptionalNumber(LOG_CONTEXT.avgInne),
    jsonOptionalNumber(LOG_CONTEXT.maxInne),
    jsonOptionalNumber(LOG_CONTEXT.diffW),
    tostring(LOG_CONTEXT.sunbeds or 0),
    jsonBool(LOG_CONTEXT.afterrunActive),
    jsonBool(LOG_CONTEXT.heatNeed),
    jsonBool(LOG_CONTEXT.coolNeed),
    jsonBool(LOG_CONTEXT.openTime),
    jsonBool(LOG_CONTEXT.preCoolingAllowed),
    jsonBool(LOG_CONTEXT.exhaustTimeAllowed),
    jsonContextBoolOrDevice(LOG_CONTEXT.fanVipOn, FAN_INNLUFT_VIP_ID),
    jsonContextBoolOrDevice(LOG_CONTEXT.fan2etgOn, FAN_INNLUFT_2ETG_ID),
    jsonContextBoolOrDevice(LOG_CONTEXT.fanTakOn, FAN_AVTREKK_TAK_ID),
    jsonContextBoolOrDevice(LOG_CONTEXT.fanAvfukterOn, FAN_AVFUKTER_ID),
    jsonEscape(LOG_CONTEXT.uteSource or ""),
    jsonBool(force)
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
      log("Render sample OK: " .. tostring(response.status) .. " " .. bucket)
    end,
    error = function(err)
      warn("Render sample FEIL: " .. tostring(err) .. " " .. bucket)
    end
  })
end

local function setFan(deviceId, deviceKey, label, desiredOn, tempForLog, reason, mode)
  local currentOn = isOn(deviceId)
  if desiredOn and not currentOn then
    fibaro.call(deviceId, "turnOn")
    log("PÅ " .. label .. ": " .. tostring(reason))
    logToRender(label, deviceKey, deviceId, "PAA", tempForLog, reason, mode)
  elseif not desiredOn and currentOn then
    fibaro.call(deviceId, "turnOff")
    log("AV " .. label .. ": " .. tostring(reason))
    logToRender(label, deviceKey, deviceId, "AV", tempForLog, reason, mode)
  else
    log(label .. " ingen endring: " .. tostring(reason))
  end
end

local function estimateSunbeds(diffW)
  if not diffW then return 0 end
  if diffW > SOLSENG_2_ON_W then return 2 end
  if diffW > SOLSENG_1_ON_W then return 1 end
  return 0
end

local function updateSunbedActivity(sunbeds)
  local now = os.time()
  if sunbeds > 0 then
    setGlobalVariable(VAR_SOLSENG_SIST_AKTIV, tostring(now))
    return true, now
  end

  local last = tonumber(getGlobalVariable(VAR_SOLSENG_SIST_AKTIV))
  if last and (now - last) < (SOLSENG_ETTERLOP_MINUTES * 60) then
    return true, last
  end
  return false, last
end

local function decideDehumidifier(tempKjeller, humidityKjeller)
  local currentlyOn = isOn(FAN_AVFUKTER_ID)
  if not tempKjeller or not humidityKjeller then
    return currentlyOn, "mangler kjeller temp/fukt"
  end
  if tempKjeller < BASEMENT_MIN_TEMP then
    return false, "kjeller under minimumstemperatur"
  end
  if humidityKjeller >= BASEMENT_HUMIDITY_ON then
    return true, "fukt over startgrense"
  end
  if humidityKjeller <= BASEMENT_HUMIDITY_OFF then
    return false, "fukt under stoppgrense"
  end
  return currentlyOn, "holder avfukter pga hysterese"
end

local function main()
  local tempVipMain = getNumber(TEMP_VIP_MAIN_ID, "value")
  local temp1, temp1Source = getRoomTempWithFallback(TEMP_1ETG_ID, TEMP_INNE_FALLBACK_ID, "1.etg temperatur")
  local temp2, temp2Source = getRoomTempWithFallback(TEMP_2ETG_ID, TEMP_INNE_FALLBACK_ID, "2.etg temperatur")
  local tempVipSub, tempVipSubSource = getRoomTempWithFallback(TEMP_VIP_SUB_ID, TEMP_INNE_FALLBACK_ID, "VIP undertemperatur")
  local tempVip = avg({ tempVipMain, tempVipSub })
  local tempUte, uteSource, tempUteNetatmo, tempYr = getOutdoorTemp()
  local tempPassiv = getNumber(TEMP_PASSIV_INNLUFT_ID, "value")
  local tempLoft = getNumber(TEMP_LOFT_ID, "value")
  local humidity1 = getNumber(HUMIDITY_1ETG_ID, "value")
  local humidity2 = getNumber(HUMIDITY_2ETG_ID, "value")
  local humidityVip = getNumber(HUMIDITY_VIP_ID, "value")
  local humidityUte = getNumber(HUMIDITY_UTE_ID, "value")
  local humidityYr = getNumber(TEMP_YR_ID, "Humidity")
  local humidityLoft = getNumber(HUMIDITY_LOFT_ID, "value")
  local humidityLuftinntak = getNumber(HUMIDITY_LUFTINNTAK_ID, "value")
  local tempKjeller = getNumber(TEMP_KJELLER_ID, "value")
  local humidityKjeller = getNumber(HUMIDITY_KJELLER_ID, "value")
  local diffW = getNumber(POWER_DIFFERANSE_R_ID, "value")

  local testInne, testInneActive = getTestNumber(VAR_TEST_TEMP_INNE)
  local testUte, testUteActive = getTestNumber(VAR_TEST_TEMP_UTE)
  local testDiffW, testDiffActive = getTestNumber(VAR_TEST_DIFF_W)
  local testActive = testInneActive or testUteActive or testDiffActive

  if testInne then
    temp1 = testInne
    temp1Source = "TEST"
    temp2 = testInne
    temp2Source = "TEST"
    tempVipMain = testInne
    tempVipSub = testInne
    tempVipSubSource = "TEST"
    tempVip = testInne
    tempPassiv = testInne
    tempLoft = testInne
    tempKjeller = testInne
  end
  if testUte then
    tempUte = testUte
    uteSource = "TEST"
    tempUteNetatmo = testUte
    tempYr = testUte
  end
  if testDiffW then
    diffW = testDiffW
  end
  if testActive then
    log(string.format(
      "TESTMODUS brukt: inne=%s ute=%s diffW=%s. Testvariabler tommes.",
      tostring(testInne or "-"), tostring(testUte or "-"), tostring(testDiffW or "-")
    ))
    clearTestVariables()
  end

  if not temp1 or not temp2 or not tempVip or not tempUte or not tempLoft then
    warn("Mangler temperaturdata. Stopper uten å endre vifter.")
    return
  end

  local minInne = minValue({ temp1, temp2, tempVip })
  local maxInne = maxValue({ temp1, temp2, tempVip })
  local avgInne = avg({ temp1, temp2, tempVip })
  local sunbeds = estimateSunbeds(diffW)
  local afterrunActive = updateSunbedActivity(sunbeds)

  LOG_CONTEXT = {
    temp1 = temp1,
    temp2 = temp2,
    tempVip = tempVip,
    tempUte = tempUte,
    tempUteNetatmo = tempUteNetatmo,
    tempYr = tempYr,
    uteSource = uteSource,
    tempLoft = tempLoft,
    humidity1 = humidity1,
    humidity2 = humidity2,
    humidityVip = humidityVip,
    humidityUte = humidityUte,
    humidityYr = humidityYr,
    humidityLoft = humidityLoft,
    tempKjeller = tempKjeller,
    humidityKjeller = humidityKjeller,
    tempPassiv = tempPassiv,
    humidityLuftinntak = humidityLuftinntak,
    diffW = diffW,
    minInne = minInne,
    avgInne = avgInne,
    maxInne = maxInne,
    sunbeds = sunbeds
  }

  local heatNeed = minInne < VARMEBEHOV_MIN_UNDER or avgInne < VARMEBEHOV_AVG_UNDER
  local coolNeed = maxInne > KJOLEBEHOV_MAX_OVER or avgInne > KJOLEBEHOV_AVG_OVER
  local nowHour = hourNow()
  local openTime = inTimeWindow(nowHour, APNING_START_HOUR, STENGING_HOUR)
  local exhaustTimeAllowed = inTimeWindow(nowHour, APNING_START_HOUR, AVTREKK_STOP_HOUR)
  local preCoolingAllowed =
    inTimeWindow(nowHour, FORKJOLING_START_HOUR, APNING_START_HOUR)
    and maxInne > FORKJOLING_MIN_INNE
    and tempUte < (maxInne - FORKJOLING_COOL_DELTA)
    and tempUte > MEKANISK_VENT_MIN_UTE
  local mode = "NORMAL"
  if heatNeed then mode = "VARMEBEVARING" end
  if coolNeed then mode = "KJOLING" end
  if preCoolingAllowed then mode = "FORKJOLING" end

  LOG_CONTEXT.mode = mode
  LOG_CONTEXT.afterrunActive = afterrunActive
  LOG_CONTEXT.heatNeed = heatNeed
  LOG_CONTEXT.coolNeed = coolNeed
  LOG_CONTEXT.openTime = openTime
  LOG_CONTEXT.preCoolingAllowed = preCoolingAllowed
  LOG_CONTEXT.exhaustTimeAllowed = exhaustTimeAllowed

  local avfukterOn, avfukterReason = decideDehumidifier(tempKjeller, humidityKjeller)
  setFan(FAN_AVFUKTER_ID, FAN_AVFUKTER_KEY, "Avfukter kjeller", avfukterOn, humidityKjeller, avfukterReason, "KJELLER_AVFUKTING")
  LOG_CONTEXT.fanAvfukterOn = avfukterOn

  if tempUte < MEKANISK_VENT_MIN_UTE then
    local reason = "utetemperatur under sperregrense"
    log(string.format(
      "mekanisk ventilasjon sperret: ute=%.1f grense=%.1f 1etg=%.1f 2etg=%.1f vip=%.1f loft=%.1f diff=%.0fW",
      tempUte, MEKANISK_VENT_MIN_UTE, temp1, temp2, tempVip, tempLoft, tonumber(diffW or 0)
    ))
    setFan(FAN_AVTREKK_TAK_ID, FAN_AVTREKK_TAK_KEY, "Avtrekk tak/loft", false, tempUte, reason, "SPERRET_KALD_UTE")
    setFan(FAN_INNLUFT_VIP_ID, FAN_INNLUFT_VIP_KEY, "Innluft VIP", false, tempUte, reason, "SPERRET_KALD_UTE")
    setFan(FAN_INNLUFT_2ETG_ID, FAN_INNLUFT_2ETG_KEY, "Innluft 2.etg", false, tempUte, reason, "SPERRET_KALD_UTE")
    LOG_CONTEXT.fanTakOn = false
    LOG_CONTEXT.fanVipOn = false
    LOG_CONTEXT.fan2etgOn = false
    logSampleToRender("SPERRET_KALD_UTE", testActive)
    return
  end

  if not openTime and not preCoolingAllowed then
    local reason = "utenfor driftstid"
    setFan(FAN_AVTREKK_TAK_ID, FAN_AVTREKK_TAK_KEY, "Avtrekk tak/loft", false, tempUte, reason, "UTENFOR_DRIFTSTID")
    setFan(FAN_INNLUFT_VIP_ID, FAN_INNLUFT_VIP_KEY, "Innluft VIP", false, tempUte, reason, "UTENFOR_DRIFTSTID")
    setFan(FAN_INNLUFT_2ETG_ID, FAN_INNLUFT_2ETG_KEY, "Innluft 2.etg", false, tempUte, reason, "UTENFOR_DRIFTSTID")
    LOG_CONTEXT.fanTakOn = false
    LOG_CONTEXT.fanVipOn = false
    LOG_CONTEXT.fan2etgOn = false
    logSampleToRender("UTENFOR_DRIFTSTID", testActive)
    return
  end

  local exhaustCurrentlyOn = isOn(FAN_AVTREKK_TAK_ID)
  local exhaustOn = false
  local exhaustReason = "passivt avtrekk er nok"
  if not exhaustTimeAllowed then
    exhaustOn = false
    exhaustReason = "avtrekk stoppet for a spare varme til natten"
  elseif tempLoft > AVTREKK_LOFT_SAFETY_ON then
    exhaustOn = true
    exhaustReason = "sikkerhet: loft veldig varmt"
  elseif heatNeed then
    exhaustOn = false
    exhaustReason = "varmebehov inne"
  elseif maxInne > AVTREKK_MAX_INNE_ON and tempLoft > AVTREKK_LOFT_HOT_INSIDE_ON then
    exhaustOn = true
    exhaustReason = "inne varmt og loft varmt"
  elseif tempLoft > AVTREKK_LOFT_ON then
    exhaustOn = true
    exhaustReason = "loft varmt"
  elseif exhaustCurrentlyOn and not (tempLoft < AVTREKK_LOFT_OFF and maxInne < AVTREKK_MAX_INNE_OFF) then
    exhaustOn = true
    exhaustReason = "holder avtrekk pga hysterese"
  end

  local vipInletCurrentlyOn = isOn(FAN_INNLUFT_VIP_ID)
  local floorsInletCurrentlyOn = isOn(FAN_INNLUFT_2ETG_ID)
  local vipInletOn = false
  local floorsInletOn = false
  local vipInletReason = "VIP har ikke behov for innblasing"
  local floorsInletReason = "1.etg/2.etg har ikke behov for innblasing"
  local floorsMax = maxValue({ temp1, temp2 })
  local floorsAvg = avg({ temp1, temp2 })
  local vipCoolNeed = tempVip > VIP_INNLUFT_ON_OVER
  local floorsCoolNeed = floorsMax > FLOOR_INNLUFT_ON_OVER or floorsAvg > INNLUFT_ZONE_AVG_ON_OVER
  local vipOutdoorHelpful = tempUte < (tempVip - INNLUFT_COOL_DELTA) and tempUte > INNLUFT_UTE_MIN_ON
  local floorsOutdoorHelpful = tempUte < (floorsMax - INNLUFT_COOL_DELTA) and tempUte > INNLUFT_UTE_MIN_ON
  local loftHotAllowed = tempLoft > AVTREKK_LOFT_ON and tempUte > INNLUFT_UTE_HARD_MIN_ON and not heatNeed
  local vipInletStop = tempVip < VIP_INNLUFT_OFF_UNDER or (tempUte < INNLUFT_UTE_OFF_UNDER and tempVip < KJOLEBEHOV_MAX_OVER) or (heatNeed and tempUte < INNLUFT_KALD_SPERRE_UNDER)
  local floorsInletStop = floorsMax < FLOOR_INNLUFT_OFF_UNDER or (tempUte < INNLUFT_UTE_OFF_UNDER and floorsMax < KJOLEBEHOV_MAX_OVER) or (heatNeed and tempUte < INNLUFT_KALD_SPERRE_UNDER)

  if preCoolingAllowed then
    vipInletOn = true
    floorsInletOn = true
    vipInletReason = "forkjoling for apning"
    floorsInletReason = "forkjoling for apning"
  else
    if openTime and vipCoolNeed and vipOutdoorHelpful then
      vipInletOn = true
      vipInletReason = "VIP trenger kjoling og ute luft hjelper"
    elseif openTime and loftHotAllowed and tempVip > VIP_INNLUFT_OFF_UNDER then
      vipInletOn = true
      vipInletReason = "loft varmt og VIP aksepterer innblasing"
    elseif openTime and vipInletCurrentlyOn and not vipInletStop then
      vipInletOn = true
      vipInletReason = "holder VIP innblasing pga hysterese"
    end

    if openTime and floorsCoolNeed and floorsOutdoorHelpful then
      floorsInletOn = true
      floorsInletReason = "1.etg/2.etg trenger kjoling og ute luft hjelper"
    elseif openTime and loftHotAllowed and floorsMax > FLOOR_INNLUFT_OFF_UNDER then
      floorsInletOn = true
      floorsInletReason = "loft varmt og 1.etg/2.etg aksepterer innblasing"
    elseif openTime and floorsInletCurrentlyOn and not floorsInletStop then
      floorsInletOn = true
      floorsInletReason = "holder 1.etg/2.etg innblasing pga hysterese"
    end
  end

  if exhaustOn and not vipInletOn and not floorsInletOn then
    vipInletOn = true
    floorsInletOn = true
    vipInletReason = "innblasing tvunget fordi avtrekk gar"
    floorsInletReason = "innblasing tvunget fordi avtrekk gar"
  end

  log(string.format(
    "temp 1etg=%.1f(%s) 2etg=%.1f(%s) vip=%.1f(sub=%s) ute=%.1f(%s) passiv=%.1f loft=%.1f kjeller=%s fukt=%s min=%.1f avg=%.1f max=%.1f diff=%.0fW solsenger=%s etterlop=%s time=%.2f apent=%s forkjoling=%s modus=%s vipVifte=%s etgVifte=%s",
    temp1, temp1Source, temp2, temp2Source, tempVip, tempVipSubSource, tempUte, uteSource, tonumber(tempPassiv or -999), tempLoft, tostring(tempKjeller or "-"), tostring(humidityKjeller or "-"), minInne, avgInne, maxInne, tonumber(diffW or 0), tostring(sunbeds), tostring(afterrunActive), nowHour, tostring(openTime), tostring(preCoolingAllowed), mode, tostring(vipInletOn), tostring(floorsInletOn)
  ))

  setFan(FAN_AVTREKK_TAK_ID, FAN_AVTREKK_TAK_KEY, "Avtrekk tak/loft", exhaustOn, tempLoft, exhaustReason, mode)
  setFan(FAN_INNLUFT_VIP_ID, FAN_INNLUFT_VIP_KEY, "Innluft VIP", vipInletOn, tempVip, vipInletReason, mode)
  setFan(FAN_INNLUFT_2ETG_ID, FAN_INNLUFT_2ETG_KEY, "Innluft 2.etg", floorsInletOn, floorsMax, floorsInletReason, mode)
  LOG_CONTEXT.fanTakOn = exhaustOn
  LOG_CONTEXT.fanVipOn = vipInletOn
  LOG_CONTEXT.fan2etgOn = floorsInletOn
  logSampleToRender(mode, testActive)
end

applyRemoteConfigThen(function()
  main()
end)

