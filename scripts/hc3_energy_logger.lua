--[[
  LILLETORGET - ENERGILOGGING TIL FIBARO10

  Logger realtime effekt (W) og akkumulert energi (kWh) hvert minutt.
  Differanse fra Fibaro sendes med som kontrollverdi, men fibaro10 beregner
  egen differanse fra Inntak minus Varmepumper, Belysning, Massasje, Avfukter og Annet.

  Anbefalt bruk:
    - Lua scene som starter automatisk etter reboot via eksisterende reboot-trigger.
    - Kun en instans skal kjore.
--]]

-- ============================================================
-- KONFIGURASJON
-- ============================================================

local API_URL = "http://192.168.20.218:8110/api/energi/fibaro"
local SOURCE = "HC3 ENERGI | 1MIN"
local INTERVAL_SECONDS = 60

local REALTIME_IDS = {
  inntak = 221,
  varmepumper = 237,
  belysning = 305,
  massasje = 333,
  annet = 332,
  avfukter = 450,
  differanse_fibaro = 331
}

local ACCUMULATED_IDS = {
  inntak = 220,
  varmepumper = 335,
  belysning = 336,
  massasje = 337,
  annet = 328,
  avfukter = 451,
  differanse_fibaro = 334
}

-- ============================================================
-- HJELPEFUNKSJONER
-- ============================================================

local function timestamp()
  return os.date("%Y-%m-%dT%H:%M:%S")
end

local function numberValue(deviceId)
  if not deviceId then return nil end
  local raw = fibaro.getValue(deviceId, "value")
  local value = tonumber(raw)
  if value == nil then
    fibaro.warning("Energi", "Kan ikke lese verdi fra device " .. tostring(deviceId) .. " (" .. tostring(raw) .. ")")
  end
  return value
end

local function buildPayload()
  return {
    source = SOURCE,
    timestamp = timestamp(),

    inntak_w = numberValue(REALTIME_IDS.inntak),
    varmepumper_w = numberValue(REALTIME_IDS.varmepumper),
    belysning_w = numberValue(REALTIME_IDS.belysning),
    massasje_w = numberValue(REALTIME_IDS.massasje),
    annet_w = numberValue(REALTIME_IDS.annet),
    avfukter_w = numberValue(REALTIME_IDS.avfukter),
    differanse_fibaro_w = numberValue(REALTIME_IDS.differanse_fibaro),

    inntak_kwh = numberValue(ACCUMULATED_IDS.inntak),
    varmepumper_kwh = numberValue(ACCUMULATED_IDS.varmepumper),
    belysning_kwh = numberValue(ACCUMULATED_IDS.belysning),
    massasje_kwh = numberValue(ACCUMULATED_IDS.massasje),
    annet_kwh = numberValue(ACCUMULATED_IDS.annet),
    avfukter_kwh = numberValue(ACCUMULATED_IDS.avfukter),
    differanse_fibaro_kwh = numberValue(ACCUMULATED_IDS.differanse_fibaro),

    extra = {
      realtime_ids = REALTIME_IDS,
      accumulated_ids = ACCUMULATED_IDS,
      interval_seconds = INTERVAL_SECONDS
    }
  }
end

local function postPayload(payload)
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
      if response.status >= 200 and response.status < 300 then
        fibaro.debug("Energi", "Sendt OK: " .. tostring(response.status))
      else
        fibaro.warning("Energi", "API svarte " .. tostring(response.status) .. ": " .. tostring(response.data))
      end
    end,
    error = function(err)
      fibaro.warning("Energi", "Feil ved sending: " .. tostring(err))
    end
  })
end

-- ============================================================
-- HOVEDLOKKE
-- ============================================================

local function loop()
  local payload = buildPayload()
  fibaro.debug("Energi", "Sender energisample: inntak=" .. tostring(payload.inntak_w) .. " W")
  postPayload(payload)
  fibaro.setTimeout(INTERVAL_SECONDS * 1000, loop)
end

fibaro.debug("Energi", "Starter energilogging hvert " .. INTERVAL_SECONDS .. " sekund")
loop()
