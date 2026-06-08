--[[
  LILLETORGET - ENERGILOGGING TIL FIBARO10

  Logger realtime effekt (W) og akkumulert energi (kWh) hvert 30. sekund.
  Fibaro10 beregner forbruksdelta fra realtime W. Akkumulert kWh logges som kontroll.
  Differanse fra Fibaro sendes med som kontrollverdi, men fibaro10 beregner
  egen differanse fra Inntak minus Varmepumper, Belysning, Massasje og Annet.
  Avfukter logges fortsatt separat, men inngar ogsa i Annet-oppsamlingen i HC3.

  Anbefalt bruk:
    - Lua scene som starter automatisk etter reboot via eksisterende reboot-trigger.
    - Kun en instans skal kjore.
--]]

-- ============================================================
-- KONFIGURASJON
-- ============================================================

local API_URL = "http://192.168.20.218:8110/api/energi/fibaro"
local SOURCE = "HC3 ENERGI | 30SEC"
local INTERVAL_SECONDS = 30

local REALTIME_IDS = {
  inntak = 221,
  varmepumper = 237,
  belysning = 305,
  massasje = 333,
  annet = 332,
  avfukter = { id = 449, property = "power" },
  differanse_fibaro = 331
}

local ACCUMULATED_IDS = {
  inntak = 220,
  varmepumper = 335,
  belysning = 336,
  massasje = 337,
  annet = 328,
  avfukter = { id = 449, property = "energy" },
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

local function meterValue(source)
  if type(source) == "table" then
    local raw = fibaro.getValue(source.id, source.property or "value")
    local value = tonumber(raw)
    if value == nil then
      fibaro.warning("Energi", "Kan ikke lese " .. tostring(source.property or "value") .. " fra device " .. tostring(source.id) .. " (" .. tostring(raw) .. ")")
    end
    return value
  end
  return numberValue(source)
end

local function buildPayload()
  return {
    source = SOURCE,
    timestamp = timestamp(),

    inntak_w = meterValue(REALTIME_IDS.inntak),
    varmepumper_w = meterValue(REALTIME_IDS.varmepumper),
    belysning_w = meterValue(REALTIME_IDS.belysning),
    massasje_w = meterValue(REALTIME_IDS.massasje),
    annet_w = meterValue(REALTIME_IDS.annet),
    avfukter_w = meterValue(REALTIME_IDS.avfukter),
    differanse_fibaro_w = meterValue(REALTIME_IDS.differanse_fibaro),

    inntak_kwh = meterValue(ACCUMULATED_IDS.inntak),
    varmepumper_kwh = meterValue(ACCUMULATED_IDS.varmepumper),
    belysning_kwh = meterValue(ACCUMULATED_IDS.belysning),
    massasje_kwh = meterValue(ACCUMULATED_IDS.massasje),
    annet_kwh = meterValue(ACCUMULATED_IDS.annet),
    avfukter_kwh = meterValue(ACCUMULATED_IDS.avfukter),
    differanse_fibaro_kwh = meterValue(ACCUMULATED_IDS.differanse_fibaro),

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
