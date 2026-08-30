"""Building services with explicit process dependencies."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from fibaro_core.models import (
    AlarmEvent,
    ControlConfig,
    ControlConfigHistory,
    GenericEvent,
    OutdoorLightEvent,
    OutdoorLightSample,
    ParkingSession,
    Sun2TanningSession,
    VentilationEvent,
    VentilationSample,
    YrForecastSample,
)
from fibaro_core.schemas import EventDataIn
from fibaro_core.services.comparisons.windows import status_timeline_position
from solar_position import solar_elevation_degrees
from sqlalchemy import select
from sun2_helpers import sun2_room_label
from time import monotonic
from time_formatting import (
    LOCAL_TZ,
    api_local_iso,
    format_source_datetime,
    format_source_datetime_short,
    local_now_naive,
    sample_bucket,
)
from typing import Any, Callable, Dict, Iterable, Optional
from urllib.parse import quote_plus
from value_parsing import float_or_zero
import asyncio
import base64
import json
import math
import urllib.request


@dataclass
class Dependencies:
    CONFIG_DEFINITIONS: Any
    CONTROL_DEVICES: Any
    HC3_BASE_URL: Any
    HC3_DOOR_POLL_TIMEOUT_SECONDS: Any
    HC3_DOOR_UNEXPECTED_RECHECK_MINUTES: Any
    HC3_ENERGY_DEVICE_LIST_CACHE_SECONDS: Any
    HC3_ENERGY_LIVE_TIMEOUT_SECONDS: Any
    HC3_PASS: Any
    HC3_SWITCH_POLL_TIMEOUT_SECONDS: Any
    HC3_SWITCH_STATUS_CACHE_SECONDS: Any
    HC3_USER: Any
    LIGHT_TIMELINE_DEVICES: Any
    MET_LAT: Any
    MET_LON: Any
    NTFY_LIGHTS_TOPIC: Any
    NTFY_VENTILATION_TOPIC: Any
    VENT_TIMELINE_DEVICES: Any
    add_segment: Callable[..., Any]
    api_bool_state: Callable[..., Any]
    async_session: Callable[..., Any]
    clean_display_text: Callable[..., Any]
    display_action: Callable[..., Any]
    display_segments: Callable[..., Any]
    enqueue_ntfy_message: Callable[..., Any]
    hc3_door_unexpected_verified_until: Any
    hc3_energy_device_list_cache: Any
    hc3_switch_status_cache: Any
    logger: Any
    parse_boolish: Callable[..., Any]
    payload_weather_symbol: Callable[..., Any]
    payload_weather_text: Callable[..., Any]
    percent_between: Callable[..., Any]
    row_to_dict: Callable[..., Any]
    status_parking_timeline_event: Callable[..., Any]
    sunbed_session_bounds: Callable[..., Any]
    time_minutes: Callable[..., Any]
    total_from_segments: Callable[..., Any]
    value_from_payload: Callable[..., Any]
    weather_label: Callable[..., Any]


def create_service(dependencies: Dependencies):

    def config_definition(key: str) -> Optional[Dict[str, Any]]:
        CONFIG_DEFINITIONS = dependencies.CONFIG_DEFINITIONS
        return CONFIG_DEFINITIONS.get(key)

    def config_defaults(key: str) -> Dict[str, Any]:
        definition = config_definition(key)
        values: Dict[str, Any] = {}
        if not definition:
            return values
        for group in definition["groups"]:
            for field in group["fields"]:
                values[field["key"]] = deepcopy(field["default"])
        return values

    def parse_config_value(raw: Any, field: Dict[str, Any]):
        field_type = field.get("type")
        if field_type == "bool":
            if isinstance(raw, bool):
                return raw
            return str(raw).strip().lower() in {"on", "true", "1", "yes"}
        if raw in (None, ""):
            return deepcopy(field["default"])
        if field_type == "int":
            try:
                return int(float(raw))
            except ValueError:
                return int(field["default"])
        if field_type == "float":
            try:
                return float(str(raw).replace(",", "."))
            except ValueError:
                return float(field["default"])
        return str(raw).strip()

    def merge_config_values(key: str, values: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        merged = config_defaults(key)
        if values:
            for item_key, value in values.items():
                if item_key in merged:
                    merged[item_key] = value
        return merged

    def config_values_from_form(key: str, form: Dict[str, str]) -> Dict[str, Any]:
        definition = config_definition(key)
        values = config_defaults(key)
        if not definition:
            return values
        for group in definition["groups"]:
            for field in group["fields"]:
                values[field["key"]] = parse_config_value(form.get(field["key"]), field)
        return values

    def config_values_from_payload(key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        definition = config_definition(key)
        values = config_defaults(key)
        if not definition:
            return values
        source = payload.get("values") if isinstance(payload.get("values"), dict) else payload
        for group in definition["groups"]:
            for field in group["fields"]:
                values[field["key"]] = parse_config_value(source.get(field["key"]), field)
        return values

    def validate_config_values(key: str, values: Dict[str, Any]) -> list[str]:
        time_minutes = dependencies.time_minutes
        errors: list[str] = []

        def require_increasing(label: str, low_key: str, high_key: str):
            if float(values[high_key]) <= float(values[low_key]):
                errors.append(f"{label}: av-grensen må være høyere enn på-grensen.")

        def require_lower_stop(label: str, stop_key: str, start_key: str):
            if float(values[stop_key]) >= float(values[start_key]):
                errors.append(f"{label}: stoppgrensen må være lavere enn startgrensen.")

        def require_time_order(label: str, start_key: str, stop_key: str):
            start = time_minutes(str(values[start_key]))
            stop = time_minutes(str(values[stop_key]))
            if start is None or stop is None:
                errors.append(f"{label}: tidspunkt må være på formatet HH:MM.")
            elif stop <= start:
                errors.append(f"{label}: sluttid må være senere enn starttid.")

        if key == "lights":
            require_time_order("Lys åpningstid", "open_from", "close_at")
            require_increasing("Lyslist", "lyslist_on_lux", "lyslist_off_lux")
            require_increasing("Reklameplakater", "reklame_on_lux", "reklame_off_lux")
            require_increasing("Spot foran glassvegg", "spot_glass_on_lux", "spot_glass_off_lux")
            require_increasing("6xspot inngang", "spot_inngang_on_lux", "spot_inngang_off_lux")
            require_increasing("Parkeringslys", "parkering_on_lux", "parkering_off_lux")
            if int(values["decision_delay_seconds"]) < 0 or int(values["decision_delay_seconds"]) > 900:
                errors.append("Bekreftelsestid bør være mellom 0 og 900 sekunder.")
            if int(values["config_poll_minutes"]) < 1 or int(values["config_poll_minutes"]) > 60:
                errors.append("HC3 config-henting bør være mellom 1 og 60 minutter.")
        elif key == "ventilation":
            require_time_order("Ventilasjon åpningstid", "open_from", "close_at")
            require_lower_stop("VIP innluft", "vip_stop_temp", "vip_start_temp")
            require_lower_stop("1./2.etg innluft", "floor_stop_temp", "floor_start_temp")
            require_lower_stop("Takvifte loft", "loft_exhaust_stop_temp", "loft_exhaust_start_temp")
            require_lower_stop("Avfukter kjeller", "basement_humidity_stop", "basement_humidity_start")
            if int(values["afterrun_minutes"]) < 0 or int(values["afterrun_minutes"]) > 180:
                errors.append("Ettergang bør være mellom 0 og 180 minutter.")
            if int(values["exhaust_stop_before_close_minutes"]) < 0 or int(values["exhaust_stop_before_close_minutes"]) > 240:
                errors.append("Stopp avtrekk før stenging bør være mellom 0 og 240 minutter.")

        return errors

    def light_rules(values: Dict[str, Any]) -> list[str]:
        return [
            f"Lyslist slås på når lux er under {values['lyslist_on_lux']} og av når lux er over {values['lyslist_off_lux']}, innen {values['open_from']}-{values['close_at']}.",
            f"Reklameplakater slås på når lux er under {values['reklame_on_lux']} og av når lux er over {values['reklame_off_lux']}, innen {values['open_from']}-{values['close_at']}.",
            f"Spot foran glassvegg slås på under {values['spot_glass_on_lux']} lux og av over {values['spot_glass_off_lux']} lux, innen {values['open_from']}-{values['close_at']}.",
            f"6xspot over inngang slås på under {values['spot_inngang_on_lux']} lux og av over {values['spot_inngang_off_lux']} lux, fra {values['open_from']} til {values['entrance_close_at']}.",
            f"Parkeringslys slås på under {values['parkering_on_lux']} lux og av over {values['parkering_off_lux']} lux uavhengig av åpningstid.",
            f"Alle lysendringer bekreftes etter {values['decision_delay_seconds']} sekunder for å unngå flimring.",
        ]

    def ventilation_rules(values: Dict[str, Any]) -> list[str]:
        return [
            f"Normal ventilasjon vurderes mellom {values['open_from']} og {values['close_at']}; forkjøling kan starte {values['pre_cooling_from']} på varme dager.",
            f"Mekanisk ventilasjon sperres når utetemperaturen er under {values['mechanical_min_outdoor_temp']}°C.",
            f"VIP innluft starter over {values['vip_start_temp']}°C og stopper under {values['vip_stop_temp']}°C når ute er minst {values['outdoor_cooler_delta']}°C kaldere.",
            f"2.etg innluft vurderer 1.etg og 2.etg, starter over {values['floor_start_temp']}°C og stopper under {values['floor_stop_temp']}°C.",
            f"Takvifte starter når loftet er over {values['loft_exhaust_start_temp']}°C og stopper under {values['loft_exhaust_stop_temp']}°C, men ikke hvis inne er under {values['indoor_allow_exhaust_temp']}°C.",
            f"Avtrekk stoppes {values['exhaust_stop_before_close_minutes']} minutter før stenging for å spare varme mot natten.",
            "Hvis avtrekk er aktivt kan innluft tvinges for å unngå undertrykk, men ikke når ute er varmere enn inne med mindre loftet er sikkerhetsvarmt.",
        ]

    def config_rules(key: str, values: Dict[str, Any]) -> list[str]:
        if key == "lights":
            return light_rules(values)
        if key == "ventilation":
            return ventilation_rules(values)
        return []

    def config_summary_rows(key: str, values: Dict[str, Any]) -> list[Dict[str, str]]:
        CONTROL_DEVICES = dependencies.CONTROL_DEVICES
        if key == "lights":
            rows = []
            for group in CONTROL_DEVICES["lights"]["groups"]:
                window = "Hele døgnet"
                if group["follows_opening_hours"]:
                    window = f"{values[group['time_from_key']]}-{values[group['time_to_key']]}"
                rows.append(
                    {
                        "name": group["name"],
                        "device": group["key"],
                        "start": f"PÅ under {values[group['on_lux_key']]} lux",
                        "stop": f"AV over {values[group['off_lux_key']]} lux",
                        "window": window,
                        "note": "Styres av lux og tidsvindu" if group["follows_opening_hours"] else "Styres av lux uavhengig av åpningstid",
                    }
                )
            return rows

        if key == "ventilation":
            return [
                {
                    "name": "Innluft VIP",
                    "device": "vip_intake",
                    "start": f"Start over {values['vip_start_temp']}°C",
                    "stop": f"Stopp under {values['vip_stop_temp']}°C",
                    "window": f"{values['open_from']}-{values['close_at']}",
                    "note": f"VIP vurderes mot ute minst {values['outdoor_cooler_delta']}°C kaldere",
                },
                {
                    "name": "Innluft 1./2.etg",
                    "device": "floor_intake",
                    "start": f"Start over {values['floor_start_temp']}°C",
                    "stop": f"Stopp under {values['floor_stop_temp']}°C",
                    "window": f"{values['open_from']}-{values['close_at']}",
                    "note": "Bruker 1.etg og 2.etg som grunnlag",
                },
                {
                    "name": "Takvifte avtrekk",
                    "device": "roof_exhaust",
                    "start": f"Loft over {values['loft_exhaust_start_temp']}°C",
                    "stop": f"Loft under {values['loft_exhaust_stop_temp']}°C",
                    "window": f"Stopper {values['exhaust_stop_before_close_minutes']} min før stenging",
                    "note": f"Ikke tillatt hvis inne er under {values['indoor_allow_exhaust_temp']}°C",
                },
                {
                    "name": "Avfukter kjeller",
                    "device": "dehumidifier_basement",
                    "start": f"Fukt over {values['basement_humidity_start']}%",
                    "stop": f"Fukt under {values['basement_humidity_stop']}%",
                    "window": f"Sperret under {values['basement_min_temp']}°C",
                    "note": "Bruker kjeller temperatur/fukt fra HC3 444/445",
                },
                {
                    "name": "Mekanisk sperre",
                    "device": "-",
                    "start": f"Tillatt over {values['mechanical_min_outdoor_temp']}°C ute",
                    "stop": f"Sperret under {values['mechanical_min_outdoor_temp']}°C ute",
                    "window": "Gjelder alle vifter",
                    "note": "Hindrer kald trekk og unødvendig varmetap",
                },
            ]

        return []

    def config_stat_cards(key: str, values: Dict[str, Any], version: int) -> list[Dict[str, str]]:
        if key == "lights":
            return [
                {"label": "Aktiv versjon", "value": str(version), "detail": "HC3 leser denne versjonen"},
                {"label": "Runner-scene", "value": "362", "detail": "Kortkjørende Lua-styring"},
                {"label": "Luxsensor", "value": "433", "detail": "Brukes av alle lysregler"},
                {"label": "Sjekkintervall", "value": f"{values['config_poll_minutes']} min", "detail": "Trigger-scenen starter runneren"},
            ]
        if key == "ventilation":
            return [
                {"label": "Aktiv versjon", "value": str(version), "detail": "HC3 leser denne versjonen"},
                {"label": "Runner-scene", "value": "363", "detail": "Kortkjørende Lua-styring"},
                {"label": "Driftstid", "value": f"{values['open_from']}-{values['close_at']}", "detail": "Normal vurderingsperiode"},
                {"label": "Utesperre", "value": f"{values['mechanical_min_outdoor_temp']}°C", "detail": "Stopper mekanisk ventilasjon"},
            ]
        return []

    def config_operational_notes(key: str, values: Dict[str, Any]) -> list[Dict[str, str]]:
        if key == "lights":
            return [
                {
                    "title": "Når tar endringen effekt?",
                    "text": f"Trigger-scenen starter lys-runneren hvert {values['config_poll_minutes']} minutt. Runneren henter alltid siste config-versjon fra appen før den vurderer lux.",
                },
                {
                    "title": "Rask test",
                    "text": "Sett globalvariabelen UTE_LYS_TEST_LUX i HC3 til ønsket lux-verdi og kjør scene 362. Variabelen tømmes automatisk etter testen.",
                },
                {
                    "title": "Hysterese",
                    "text": "Lys slås på under på-grensen og av over av-grensen. Hvis lux ligger mellom disse verdiene beholdes gjeldende status.",
                },
            ]
        if key == "ventilation":
            return [
                {
                    "title": "Når tar endringen effekt?",
                    "text": "Trigger-scenen starter ventilasjons-runneren hvert 5. minutt. Runneren henter alltid siste config-versjon fra appen før den styrer viftene.",
                },
                {
                    "title": "Rask test",
                    "text": "Bruk VENT_TEST_TEMP_INNE, VENT_TEST_TEMP_UTE og VENT_TEST_DIFF_W i HC3 og kjør scene 363. Testvariablene tømmes automatisk etter kjøring.",
                },
                {
                    "title": "Sikkerhet",
                    "text": "Mekanisk ventilasjon sperres ved for lav utetemperatur, og avtrekk skal ikke gå uten at innluft er vurdert samtidig.",
                },
            ]
        return []

    def config_devices(key: str) -> Dict[str, Any]:
        CONTROL_DEVICES = dependencies.CONTROL_DEVICES
        return deepcopy(CONTROL_DEVICES.get(key, {}))

    def config_payload(row: ControlConfig) -> Dict[str, Any]:
        values = merge_config_values(row.key, row.values)
        return {
            "system": row.key,
            "version": row.version,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "updated_by": row.updated_by,
            "values": values,
            "devices": config_devices(row.key),
            "rules": config_rules(row.key, values),
            "fallback_note": "HC3 skal bruke sist kjente verdier hvis API-et ikke kan nås.",
        }

    async def get_or_create_config(session, key: str) -> Optional[ControlConfig]:
        CONFIG_DEFINITIONS = dependencies.CONFIG_DEFINITIONS
        if key not in CONFIG_DEFINITIONS:
            return None
        row = (await session.execute(select(ControlConfig).where(ControlConfig.key == key))).scalars().first()
        if row:
            row.values = merge_config_values(key, row.values)
            return row
        row = ControlConfig(key=key, version=1, values=config_defaults(key), updated_by="system")
        session.add(row)
        session.add(ControlConfigHistory(config_key=key, version=1, values=row.values, changed_by="system", reason="Standardverdier opprettet"))
        await session.commit()
        await session.refresh(row)
        return row

    def light_ntfy_payload(event: OutdoorLightEvent) -> Optional[dict[str, Any]]:
        NTFY_LIGHTS_TOPIC = dependencies.NTFY_LIGHTS_TOPIC
        clean_display_text = dependencies.clean_display_text
        state = state_from_event(event)
        if state is None:
            return None
        action = "P\u00c5" if state else "AV"
        device_name = event.device_name or event.device_key or "Ukjent lys"
        pieces = [f"{device_name} er {action}."]
        if event.lux is not None:
            pieces.append(f"Lux: {event.lux:.0f}.")
        detail = clean_display_text(event.reason or event.source or "")
        if detail:
            pieces.append(f"\u00c5rsak: {detail}.")
        return {
            "topic": NTFY_LIGHTS_TOPIC,
            "title": f"SUN2 lys {action}",
            "message": " ".join(pieces),
            "tags": "bulb",
            "priority": "3",
        }

    async def publish_light_ntfy(event: OutdoorLightEvent) -> bool:
        enqueue_ntfy_message = dependencies.enqueue_ntfy_message
        logger = dependencies.logger
        payload = light_ntfy_payload(event)
        if payload is None:
            return False
        try:
            return await enqueue_ntfy_message(**payload)
        except Exception as exc:
            logger.warning("Kunne ikke legge NTFY-varsel for lys i ko: %s", exc, exc_info=True)
            return False

    def ventilation_ntfy_payload(event: VentilationEvent) -> Optional[dict[str, Any]]:
        NTFY_VENTILATION_TOPIC = dependencies.NTFY_VENTILATION_TOPIC
        clean_display_text = dependencies.clean_display_text
        state = state_from_event(event)
        if state is None:
            return None
        action = "P\u00c5" if state else "AV"
        device_name = event.device_name or event.device_key or "Ukjent vifte"
        pieces = [f"{device_name} er {action}."]
        if event.mode:
            pieces.append(f"Modus: {clean_display_text(event.mode)}.")
        temps = []
        if event.temp_1etg is not None:
            temps.append(f"1.etg {event.temp_1etg:.1f}\u00b0")
        if event.temp_2etg is not None:
            temps.append(f"2.etg {event.temp_2etg:.1f}\u00b0")
        if event.temp_vip is not None:
            temps.append(f"VIP {event.temp_vip:.1f}\u00b0")
        if event.humidity_1etg is not None:
            temps.append(f"fukt 1.etg {event.humidity_1etg:.0f}%")
        if event.humidity_2etg is not None:
            temps.append(f"fukt 2.etg {event.humidity_2etg:.0f}%")
        if event.humidity_vip is not None:
            temps.append(f"fukt VIP {event.humidity_vip:.0f}%")
        if event.temp_kjeller is not None:
            temps.append(f"kjeller {event.temp_kjeller:.1f}\u00b0")
        if event.humidity_kjeller is not None:
            temps.append(f"fukt kjeller {event.humidity_kjeller:.0f}%")
        if event.temp_ute is not None:
            temps.append(f"ute {event.temp_ute:.1f}\u00b0")
        if event.temp_loft is not None:
            temps.append(f"loft {event.temp_loft:.1f}\u00b0")
        if temps:
            pieces.append("Temp: " + ", ".join(temps) + ".")
        if event.diff_w is not None:
            pieces.append(f"Diff: {event.diff_w:.0f} W.")
        detail = clean_display_text(event.reason or event.source or "")
        if detail:
            pieces.append(f"\u00c5rsak: {detail}.")
        return {
            "topic": NTFY_VENTILATION_TOPIC,
            "title": f"SUN2 ventilasjon {action}",
            "message": " ".join(pieces),
            "tags": "dash",
            "priority": "3",
        }

    async def publish_ventilation_ntfy(event: VentilationEvent) -> bool:
        enqueue_ntfy_message = dependencies.enqueue_ntfy_message
        logger = dependencies.logger
        payload = ventilation_ntfy_payload(event)
        if payload is None:
            return False
        try:
            return await enqueue_ntfy_message(**payload)
        except Exception as exc:
            logger.warning("Kunne ikke legge NTFY-varsel for ventilasjon i ko: %s", exc, exc_info=True)
            return False

    def state_from_event(row):
        if row.action == "PAA":
            return True
        if row.action == "AV":
            return False
        if row.state is not None:
            return bool(row.state)
        return None

    def lux_scale(values):
        max_value = max([value for value in values if value is not None] or [100])
        for axis_max, step in [(200, 50), (1000, 250), (2000, 500), (5000, 1000), (10000, 2000), (20000, 5000)]:
            if max_value <= axis_max:
                return {"max": float(axis_max), "step": step}
        return {"max": 20000.0, "step": 5000}

    def lux_y(value: float, max_lux: float) -> float:
        graph_top = 22
        graph_bottom = 278
        graph_mid = (graph_top + graph_bottom) / 2
        scale_break = 2000.0
        usable = graph_bottom - graph_top
        if max_lux <= 0:
            return graph_bottom
        value = max(0, min(value, max_lux))
        if max_lux <= scale_break:
            return round(graph_bottom - (value / max_lux) * usable, 2)
        if value <= scale_break:
            return round(graph_bottom - (value / scale_break) * (graph_bottom - graph_mid), 2)
        return round(graph_mid - ((value - scale_break) / (max_lux - scale_break)) * (graph_mid - graph_top), 2)

    def lux_tick_values(max_lux: float):
        if max_lux <= 200:
            values = [50, 100, 150, 200]
        elif max_lux <= 1000:
            values = [100, 250, 500, 750, 1000]
        elif max_lux <= 2000:
            values = [250, 500, 1000, 1500, 2000]
        else:
            values = [500, 1000, 1500, 2000, 5000, 10000, 15000, 20000]
        return [value for value in values if value <= max_lux]

    def lux_tick_label(value: int) -> str:
        if value >= 1000:
            return f"{value // 1000}K" if value % 1000 == 0 else f"{value / 1000:g}K"
        return str(value)

    def temp_axis(values):
        valid_values = [float(value) for value in values if value is not None]
        if not valid_values:
            return {"min": 0.0, "max": 30.0, "step": 5.0}

        raw_min = min(valid_values)
        raw_max = max(valid_values)
        lower = math.floor(raw_min - 1)
        upper = math.ceil(raw_max + 1)
        if upper - lower < 4:
            center = (upper + lower) / 2
            lower = math.floor(center - 2)
            upper = math.ceil(center + 2)

        span = upper - lower
        if span <= 8:
            step = 1.0
        elif span <= 16:
            step = 2.0
        else:
            step = 5.0

        lower = math.floor(lower / step) * step
        upper = math.ceil(upper / step) * step
        return {"min": float(lower), "max": float(upper), "step": step}

    def temp_y(value: float, axis_min: float, axis_max: float) -> float:
        graph_top = 22
        graph_bottom = 278
        usable = graph_bottom - graph_top
        if axis_max <= axis_min:
            return graph_bottom
        ratio = (value - axis_min) / (axis_max - axis_min)
        return round(graph_bottom - max(0, min(1, ratio)) * usable, 2)

    def temp_label(value) -> str:
        if value is None:
            return "-"
        return f"{float(value):.1f}°"

    def status_sun_timeline_event(row: Sun2TanningSession, period_start: datetime, lane_end: datetime, axis_seconds: float) -> Optional[Dict[str, Any]]:
        sunbed_session_bounds = dependencies.sunbed_session_bounds
        bounds = sunbed_session_bounds(row)
        if not bounds:
            return None
        start_at, end_at = bounds
        position = status_timeline_position(start_at, end_at, period_start, lane_end, axis_seconds)
        if not position:
            return None
        customer_type = (row.customer_type or "").lower()
        kind = "standard"
        if "ikke" in customer_type:
            kind = "no-member"
        elif "medlem" in customer_type:
            kind = "member"
        paid = float_or_zero(row.paid_amount_kr)
        room_label = sun2_room_label(row.room_id, row.room or row.source_room_name)
        title_parts = [f"{room_label} {start_at:%d.%m %H:%M}-{end_at:%H:%M}", f"{float_or_zero(row.duration_minutes):.0f} min"]
        if paid:
            title_parts.append(f"{paid:.0f} kr")
        if row.user_name:
            title_parts.append(str(row.user_name))
        href = f"/soling/enkeltimer?date_from={start_at.date().isoformat()}&date_to={start_at.date().isoformat()}"
        if row.room_id:
            href += f"&room_id={quote_plus(str(row.room_id))}"
        return {
            "id": f"sun-{row.id}",
            "kind": kind,
            "left": position["left"],
            "width": position["width"],
            "label": room_label,
            "title": " | ".join(title_parts),
            "start": api_local_iso(start_at),
            "end": api_local_iso(end_at),
            "amount": paid,
            "href": href,
        }

    async def status_timeline_lane(
        session,
        source: str,
        label: str,
        period_label: str,
        kind: str,
        start: datetime,
        end: datetime,
        axis_seconds: float,
    ) -> Dict[str, Any]:
        status_parking_timeline_event = dependencies.status_parking_timeline_event
        if kind == "sun":
            rows = (
                await session.execute(
                    select(Sun2TanningSession)
                    .where(Sun2TanningSession.started_at >= start)
                    .where(Sun2TanningSession.started_at < end)
                    .order_by(Sun2TanningSession.started_at.asc())
                )
            ).scalars().all()
            events = [item for row in rows if (item := status_sun_timeline_event(row, start, end, axis_seconds))]
            paid = sum(float_or_zero(row.paid_amount_kr) for row in rows)
            count = len(rows)
        else:
            rows = (
                await session.execute(
                    select(ParkingSession)
                    .where(ParkingSession.start_time >= start)
                    .where(ParkingSession.start_time < end)
                    .order_by(ParkingSession.start_time.asc())
                )
            ).scalars().all()
            events = [item for row in rows if (item := status_parking_timeline_event(row, start, end, axis_seconds))]
            paid = sum(float_or_zero(row.fee_inc_vat) for row in rows)
            count = len(rows)
        return {
            "key": f"{source}-{kind}",
            "source": source,
            "label": label,
            "periodLabel": period_label,
            "kind": kind,
            "start": api_local_iso(start),
            "end": api_local_iso(end),
            "endLeft": round(max(0, min(100, ((end - start).total_seconds() / axis_seconds) * 100)), 4) if axis_seconds > 0 else 0,
            "count": count,
            "paid": paid,
            "events": events,
        }

    def light_status_text(row: OutdoorLightSample) -> str:
        LIGHT_TIMELINE_DEVICES = dependencies.LIGHT_TIMELINE_DEVICES
        active = []
        for device in LIGHT_TIMELINE_DEVICES:
            if light_sample_state(row, device):
                active.append(device["name"])
        return ", ".join(active) if active else "Alt av"

    def event_detail(system: str, row) -> str:
        pieces = []
        if system == "lys" and row.lux is not None:
            pieces.append(f"Lux {row.lux:.0f}")
        if system == "ventilasjon":
            if row.temp_1etg is not None:
                pieces.append(f"1.etg {row.temp_1etg:.1f}°")
            if row.temp_2etg is not None:
                pieces.append(f"2.etg {row.temp_2etg:.1f}°")
            if row.temp_vip is not None:
                pieces.append(f"VIP {row.temp_vip:.1f}°")
            if row.humidity_1etg is not None:
                pieces.append(f"fukt 1.etg {row.humidity_1etg:.0f}%")
            if row.humidity_2etg is not None:
                pieces.append(f"fukt 2.etg {row.humidity_2etg:.0f}%")
            if row.humidity_vip is not None:
                pieces.append(f"fukt VIP {row.humidity_vip:.0f}%")
            if row.temp_kjeller is not None:
                pieces.append(f"kjeller {row.temp_kjeller:.1f}°")
            if row.humidity_kjeller is not None:
                pieces.append(f"fukt kjeller {row.humidity_kjeller:.0f}%")
            if row.temp_ute is not None:
                pieces.append(f"ute {row.temp_ute:.1f}°")
            if row.diff_w is not None:
                pieces.append(f"diff {row.diff_w:.0f} W")
        return ", ".join(pieces)

    def light_sample_state(row, device) -> Optional[bool]:
        attr = device.get("sample_attr")
        value = getattr(row, attr, None)
        if value is None:
            return None
        return bool(value)

    def sample_state(row, device) -> Optional[bool]:
        attr = device.get("sample_attr")
        if not row or not attr:
            return None
        value = getattr(row, attr, None)
        if value is None:
            return None
        return bool(value)

    def hc3_control_device_id(device: Dict[str, Any]) -> Optional[int]:
        ids = device.get("legacy_ids") or []
        if not ids:
            return None
        try:
            return int(ids[0])
        except (TypeError, ValueError):
            return None

    def hc3_switch_config_for_timeline_device(device: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        device_id = hc3_control_device_id(device)
        if device_id is None:
            return None
        return {
            "key": device.get("key"),
            "name": device.get("name"),
            "device_id": device_id,
        }

    def ventilation_status_payload(
        device: Dict[str, Any],
        latest_sample: Optional[VentilationSample],
        hc3_status: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        api_bool_state = dependencies.api_bool_state
        sample_value = sample_state(latest_sample, device) if latest_sample else None
        sample_at = latest_sample.bucket_start or latest_sample.timestamp if latest_sample else None
        hc3_value = hc3_status.get("state") if hc3_status else None
        has_hc3_value = hc3_value is not None
        state = hc3_value if has_hc3_value else sample_value
        device_id = (hc3_status or {}).get("deviceId") or hc3_control_device_id(device)
        checked_at = (hc3_status or {}).get("checkedAt")
        error = (hc3_status or {}).get("error")
        if has_hc3_value:
            source = "HC3 styring"
        elif error:
            source = "Siste sample (HC3 styring feilet)"
        elif hc3_status:
            source = "Siste sample (styring ukjent)"
        else:
            source = "Siste sample"
        tooltip_parts = [
            f"{device.get('name') or device.get('key')}",
            f"Styringsgrunnlag: {source}",
            "Merk: dette er antatt drift fra HC3-bryter/rele, ikke separat fysisk viftesensor.",
        ]
        if device_id:
            tooltip_parts.append(f"HC3-id: {device_id}")
        if checked_at:
            tooltip_parts.append(f"Sjekket: {checked_at}")
        if sample_at:
            tooltip_parts.append(f"Siste sample: {format_source_datetime_short(sample_at)}")
        if error:
            tooltip_parts.append(f"Feil: {error}")
        return {
            "key": device.get("key"),
            "label": device.get("name"),
            "state": api_bool_state(state),
            "sampleState": api_bool_state(sample_value),
            "sampleAt": api_local_iso(sample_at),
            "deviceId": device_id,
            "deviceName": (hc3_status or {}).get("deviceName") or device.get("name"),
            "statusSource": source,
            "checkedAt": checked_at,
            "error": error,
            "tooltip": " | ".join(part for part in tooltip_parts if part),
        }

    def event_extra_key(row) -> Optional[str]:
        extra = getattr(row, "extra", None) or {}
        if isinstance(extra, dict):
            key = extra.get("device_key") or extra.get("key")
            if key:
                return str(key)
        return None

    def event_device_key(row, devices) -> Optional[str]:
        key = getattr(row, "device_key", None) or event_extra_key(row)
        if key:
            return str(key)
        device_id = getattr(row, "device_id", None)
        device_name = (getattr(row, "device_name", None) or "").strip().lower()
        for device in devices:
            if device_id is not None and device_id in device.get("legacy_ids", []):
                return device["key"]
            if device_name and device_name == device["name"].strip().lower():
                return device["key"]
        return None

    def event_matches_device(row, device, devices) -> bool:
        return event_device_key(row, devices) == device["key"]

    def dedupe_samples_by_bucket(rows):
        buckets = {}
        for row in rows:
            buckets[row.bucket_start or row.timestamp] = row
        return [buckets[key] for key in sorted(buckets)]

    def point_from_row(row, day_start: datetime, day_end: datetime, system: str):
        clean_display_text = dependencies.clean_display_text
        display_action = dependencies.display_action
        percent_between = dependencies.percent_between
        event_time = max(day_start, min(day_end, row.timestamp))
        reason = clean_display_text(row.reason or row.source or "")
        return {
            "left": percent_between(event_time, day_start, day_end),
            "time": event_time.strftime("%H:%M"),
            "action": display_action(row.action),
            "action_class": "on" if row.action == "PAA" else "off" if row.action == "AV" else "neutral",
            "reason": reason,
            "detail": event_detail(system, row),
        }

    def build_timeline_item(device, rows, previous_row, day_start: datetime, day_end: datetime, timeline_end: datetime, system: str):
        add_segment = dependencies.add_segment
        display_segments = dependencies.display_segments
        total_from_segments = dependencies.total_from_segments
        state = state_from_event(previous_row) if previous_row else False
        if state is None:
            state = False
        cursor = day_start
        raw_segments = []
        points = []

        for row in rows:
            if row.timestamp >= timeline_end:
                break
            event_time = max(day_start, min(timeline_end, row.timestamp))
            if state and event_time > cursor:
                add_segment(raw_segments, cursor, event_time)

            new_state = state_from_event(row)
            points.append(point_from_row(row, day_start, day_end, system))
            if new_state is not None:
                state = new_state
                cursor = event_time

        if state and cursor < timeline_end:
            add_segment(raw_segments, cursor, timeline_end)

        return {
            "id": device["key"],
            "name": device["name"],
            "segments": display_segments(raw_segments, day_start, day_end),
            "points": points,
            "total": total_from_segments(raw_segments),
        }

    async def build_timeline_group(model, devices, system: str, day_start: datetime, day_end: datetime, timeline_end: datetime):
        async_session = dependencies.async_session
        async with async_session() as session:
            day_result = await session.execute(
                select(model)
                .where(model.timestamp >= day_start)
                .where(model.timestamp < timeline_end)
                .order_by(model.timestamp.asc())
            )
            rows = day_result.scalars().all()
            previous = {}
            for device in devices:
                previous_candidates = (await session.execute(
                    select(model)
                    .where(model.timestamp < day_start)
                    .order_by(model.timestamp.desc())
                    .limit(300)
                )).scalars().all()
                previous[device["key"]] = next((row for row in previous_candidates if event_matches_device(row, device, devices)), None)

        rows_by_device = {device["key"]: [] for device in devices}
        for row in rows:
            key = event_device_key(row, devices)
            if key in rows_by_device:
                rows_by_device[key].append(row)

        return [
            build_timeline_item(device, rows_by_device.get(device["key"], []), previous.get(device["key"]), day_start, day_end, timeline_end, system)
            for device in devices
        ]

    async def build_light_timeline_group(day_start: datetime, day_end: datetime, timeline_end: datetime):
        LIGHT_TIMELINE_DEVICES = dependencies.LIGHT_TIMELINE_DEVICES
        add_segment = dependencies.add_segment
        async_session = dependencies.async_session
        display_action = dependencies.display_action
        display_segments = dependencies.display_segments
        percent_between = dependencies.percent_between
        total_from_segments = dependencies.total_from_segments
        async with async_session() as session:
            event_result = await session.execute(
                select(OutdoorLightEvent)
                .where(OutdoorLightEvent.timestamp >= day_start)
                .where(OutdoorLightEvent.timestamp < timeline_end)
                .order_by(OutdoorLightEvent.timestamp.asc())
            )
            event_rows = event_result.scalars().all()
            sample_result = await session.execute(
                select(OutdoorLightSample)
                .where(OutdoorLightSample.timestamp >= day_start)
                .where(OutdoorLightSample.timestamp < timeline_end)
                .order_by(OutdoorLightSample.timestamp.asc())
            )
            sample_rows = sample_result.scalars().all()
            sample_rows = dedupe_samples_by_bucket(sample_rows)
            previous_sample_result = await session.execute(
                select(OutdoorLightSample)
                .where(OutdoorLightSample.timestamp < day_start)
                .order_by(OutdoorLightSample.timestamp.desc())
                .limit(1)
            )
            previous_sample = previous_sample_result.scalars().first()
            previous_events = {}
            for device in LIGHT_TIMELINE_DEVICES:
                previous_candidates = (await session.execute(
                    select(OutdoorLightEvent)
                    .where(OutdoorLightEvent.timestamp < day_start)
                    .order_by(OutdoorLightEvent.timestamp.desc())
                    .limit(300)
                )).scalars().all()
                previous_events[device["key"]] = next(
                    (row for row in previous_candidates if event_matches_device(row, device, LIGHT_TIMELINE_DEVICES)),
                    None,
                )

        events_by_device = {device["key"]: [] for device in LIGHT_TIMELINE_DEVICES}
        for row in event_rows:
            key = event_device_key(row, LIGHT_TIMELINE_DEVICES)
            if key in events_by_device:
                events_by_device[key].append(row)

        items = []
        for device in LIGHT_TIMELINE_DEVICES:
            state = light_sample_state(previous_sample, device) if previous_sample else None
            if state is None and previous_events.get(device["key"]):
                state = state_from_event(previous_events[device["key"]])
            if state is None:
                state = False
            cursor = day_start
            raw_segments = []
            points = [point_from_row(row, day_start, day_end, "lys") for row in events_by_device.get(device["key"], [])]
            sample_points = []
            state_changes = []

            for row in sample_rows:
                sample_time = row.bucket_start or row.timestamp
                if sample_time >= timeline_end:
                    break
                event_time = max(day_start, min(timeline_end, sample_time))
                new_state = light_sample_state(row, device)
                if new_state is None:
                    continue
                state_changes.append({
                    "time": event_time,
                    "state": new_state,
                    "source": "sample",
                    "lux": row.lux,
                })

            for row in events_by_device.get(device["key"], []):
                if row.timestamp >= timeline_end:
                    continue
                event_time = max(day_start, min(timeline_end, row.timestamp))
                new_state = state_from_event(row)
                if new_state is None:
                    continue
                state_changes.append({
                    "time": event_time,
                    "state": new_state,
                    "source": "event",
                    "lux": row.lux,
                })

            state_changes.sort(key=lambda item: (item["time"], 0 if item["source"] == "sample" else 1))

            for change in state_changes:
                event_time = change["time"]
                new_state = change["state"]
                if state and event_time > cursor:
                    add_segment(raw_segments, cursor, event_time)
                if new_state != state and change["source"] == "sample":
                    action = "PAA" if new_state else "AV"
                    has_event_point = any(point["time"] == event_time.strftime("%H:%M") and point["action"] == display_action(action) for point in points)
                    if not has_event_point:
                        sample_points.append({
                            "left": percent_between(event_time, day_start, day_end),
                            "time": event_time.strftime("%H:%M"),
                            "action": display_action(action),
                            "action_class": "on" if new_state else "off",
                            "reason": "Statusendring fra 5-minutters luxlogg",
                            "detail": f"Lux {change['lux']:.0f}" if change["lux"] is not None else "",
                        })
                state = new_state
                cursor = event_time

            if state and cursor < timeline_end:
                add_segment(raw_segments, cursor, timeline_end)

            all_points = sorted(points + sample_points, key=lambda point: point["time"])
            items.append({
                "id": device["key"],
                "name": device["name"],
                "segments": display_segments(raw_segments, day_start, day_end),
                "points": all_points,
                "total": total_from_segments(raw_segments),
            })

        return items

    async def build_light_chart_markers(day_start: datetime, day_end: datetime, timeline_end: datetime):
        LIGHT_TIMELINE_DEVICES = dependencies.LIGHT_TIMELINE_DEVICES
        async_session = dependencies.async_session
        clean_display_text = dependencies.clean_display_text
        percent_between = dependencies.percent_between
        light_colors = {
            "lyslist": "#df705d",
            "reklame": "#f2b84b",
            "spot_glass_275": "#3f7fbd",
            "spot_glass_299": "#2f8fa3",
            "spot_inngang": "#726189",
            "parkering": "#2563eb",
        }
        light_shorts = {
            "lyslist": "Lyslist",
            "reklame": "Reklame",
            "spot_glass_275": "Glass",
            "spot_glass_299": "Massasje",
            "spot_inngang": "Inngang",
            "parkering": "Parkering",
        }
        devices = [
            {
                **device,
                "short": light_shorts.get(device["key"], device["name"]),
                "color": light_colors.get(device["key"], "#df705d"),
                "default": True,
            }
            for device in LIGHT_TIMELINE_DEVICES
        ]

        async with async_session() as session:
            event_rows = (
                await session.execute(
                    select(OutdoorLightEvent)
                    .where(OutdoorLightEvent.timestamp >= day_start)
                    .where(OutdoorLightEvent.timestamp < timeline_end)
                    .order_by(OutdoorLightEvent.timestamp.asc())
                )
            ).scalars().all()
            sample_rows = (
                await session.execute(
                    select(OutdoorLightSample)
                    .where(OutdoorLightSample.timestamp >= day_start)
                    .where(OutdoorLightSample.timestamp < timeline_end)
                    .order_by(OutdoorLightSample.timestamp.asc())
                )
            ).scalars().all()
            sample_rows = dedupe_samples_by_bucket(sample_rows)
            previous_sample = (
                await session.execute(
                    select(OutdoorLightSample)
                    .where(OutdoorLightSample.timestamp < day_start)
                    .order_by(OutdoorLightSample.timestamp.desc())
                    .limit(1)
                )
            ).scalars().first()
            previous_candidates = (
                await session.execute(
                    select(OutdoorLightEvent)
                    .where(OutdoorLightEvent.timestamp < day_start)
                    .order_by(OutdoorLightEvent.timestamp.desc())
                    .limit(300)
                )
            ).scalars().all()

        events_by_device = {device["key"]: [] for device in devices}
        for row in event_rows:
            key = event_device_key(row, LIGHT_TIMELINE_DEVICES)
            if key in events_by_device:
                events_by_device[key].append(row)

        markers = []
        light_lane_y = {device["key"]: 34 + index * 13 for index, device in enumerate(devices)}
        for device in devices:
            state = light_sample_state(previous_sample, device) if previous_sample else None
            if state is None:
                previous_event = next(
                    (row for row in previous_candidates if event_matches_device(row, device, LIGHT_TIMELINE_DEVICES)),
                    None,
                )
                state = state_from_event(previous_event) if previous_event else None
            if state is None:
                state = False

            changes = []
            for row in sample_rows:
                sample_time = row.bucket_start or row.timestamp
                if sample_time is None or sample_time >= timeline_end:
                    continue
                new_state = light_sample_state(row, device)
                if new_state is None:
                    continue
                changes.append(
                    {
                        "time": max(day_start, min(timeline_end, sample_time)),
                        "state": new_state,
                        "source_order": 0,
                        "detail": f"Lux {row.lux:.0f}" if row.lux is not None else "",
                        "reason": "Statusendring fra 5-minutters luxlogg",
                    }
                )

            for row in events_by_device.get(device["key"], []):
                if row.timestamp >= timeline_end:
                    continue
                new_state = state_from_event(row)
                if new_state is None:
                    continue
                detail = event_detail("lys", row)
                reason = clean_display_text(row.reason or row.source or "")
                changes.append(
                    {
                        "time": max(day_start, min(timeline_end, row.timestamp)),
                        "state": new_state,
                        "source_order": 1,
                        "detail": detail,
                        "reason": reason,
                    }
                )

            seen = set()
            for change in sorted(changes, key=lambda item: (item["time"], item["source_order"])):
                if change["state"] == state:
                    continue
                action = "PÅ" if change["state"] else "AV"
                action_class = "on" if change["state"] else "off"
                marker_key = (device["key"], change["time"].replace(second=0, microsecond=0), action_class)
                if marker_key in seen:
                    state = change["state"]
                    continue
                seen.add(marker_key)
                markers.append(
                    {
                        "light_key": device["key"],
                        "light_name": device["name"],
                        "light_short": device["short"],
                        "color": device["color"],
                        "x": percent_between(change["time"], day_start, day_end) * 10,
                        "lane_y": light_lane_y.get(device["key"], 34),
                        "time": change["time"].strftime("%H:%M"),
                        "action": action,
                        "class": action_class,
                        "detail": change["detail"],
                        "reason": change["reason"],
                    }
                )
                state = change["state"]

        return {"lights": devices, "events": markers}

    async def fetch_lux_samples(day_start: datetime, timeline_end: datetime):
        LIGHT_TIMELINE_DEVICES = dependencies.LIGHT_TIMELINE_DEVICES
        async_session = dependencies.async_session
        async with async_session() as session:
            sample_result = await session.execute(
                select(OutdoorLightSample)
                .where(OutdoorLightSample.timestamp >= day_start)
                .where(OutdoorLightSample.timestamp < timeline_end)
                .order_by(OutdoorLightSample.timestamp.asc())
            )
            sample_rows = dedupe_samples_by_bucket(sample_result.scalars().all())

        samples = []
        lux_values = []
        for row in sample_rows:
            sample_time = row.bucket_start or row.timestamp
            lux_value = row.lux if row.lux is not None else row.value
            if sample_time is None or lux_value is None:
                continue
            lux_values.append(lux_value)
            samples.append(
                {
                    "time_dt": sample_time,
                    "time": sample_time.strftime("%H:%M"),
                    "lux": round(lux_value, 1),
                    "lux_label": f"{lux_value:.0f}",
                    "mode": row.mode or "",
                    "source": row.source or "",
                    "lights": light_status_text(row),
                    "light_states": {device["key"]: light_sample_state(row, device) for device in LIGHT_TIMELINE_DEVICES},
                }
            )
        return samples, lux_values

    def build_solar_elevation_samples(day_start: datetime, day_end: datetime, interval_minutes: int = 10):
        MET_LAT = dependencies.MET_LAT
        MET_LON = dependencies.MET_LON
        samples = []
        cursor = day_start
        interval = timedelta(minutes=max(1, interval_minutes))
        while cursor <= day_end:
            elevation = solar_elevation_degrees(cursor, MET_LAT, MET_LON, LOCAL_TZ)
            samples.append(
                {
                    "time_dt": cursor,
                    "time": cursor.strftime("%H:%M"),
                    "solar_elevation": round(max(0.0, elevation), 1),
                }
            )
            cursor += interval
        return samples

    async def build_lux_day(day_start: datetime, day_end: datetime, timeline_end: datetime, scale_values: Optional[list] = None):
        percent_between = dependencies.percent_between
        samples, lux_values = await fetch_lux_samples(day_start, timeline_end)

        scale = lux_scale(scale_values if scale_values is not None else lux_values)
        max_lux = scale["max"]
        points = []
        for sample in samples:
            points.append(
                {
                    **sample,
                    "x": percent_between(sample["time_dt"], day_start, day_end) * 10,
                    "y": lux_y(float(sample["lux"]), max_lux),
                }
            )
        polyline = " ".join(f"{point['x']:.2f},{point['y']:.2f}" for point in points)

        y_ticks = [
            {
                "label": lux_tick_label(value),
                "value": value,
                "y": lux_y(float(value), max_lux),
                "symbol_radius": round(2.2 + math.sqrt(value / max_lux) * 3.8, 2),
                "symbol_opacity": round(0.25 + math.sqrt(value / max_lux) * 0.55, 2),
            }
            for value in lux_tick_values(max_lux)
        ]
        reference_lines = [
            {"label": f"{lux_tick_label(value)} lux", "value": value, "y": lux_y(float(value), max_lux)}
            for value in [100, 1000, 2000]
            if value <= max_lux
        ]

        lux_only = [sample["lux"] for sample in samples]
        summary = {
            "count": len(samples),
            "min": f"{min(lux_only):.0f}" if lux_only else "-",
            "max": f"{max(lux_only):.0f}" if lux_only else "-",
            "latest": f"{lux_only[-1]:.0f}" if lux_only else "-",
            "latest_time": samples[-1]["time"] if samples else "-",
            "scale_max": f"{max_lux:.0f}",
            "scale_step": f"{scale['step']:.0f}",
            "scale_break": "2000",
        }
        return {
            "points": points,
            "polyline": polyline,
            "y_ticks": y_ticks,
            "reference_lines": reference_lines,
            "samples_desc": list(reversed(samples)),
            "summary": summary,
        }

    def build_lux_sparkline(sample_rows, day_start: datetime, day_end: datetime):
        percent_between = dependencies.percent_between
        rows = dedupe_samples_by_bucket(sample_rows)
        values = []
        points = []
        for row in rows:
            sample_time = row.bucket_start or row.timestamp
            lux_value = row.lux if row.lux is not None else row.value
            if sample_time is None or lux_value is None:
                continue
            values.append(float(lux_value))
            points.append((sample_time, float(lux_value)))
        if not points:
            return {"polyline": "", "count": 0}
        max_lux = lux_scale(values)["max"]
        polyline = " ".join(
            f"{percent_between(sample_time, day_start, day_end) * 10:.2f},{lux_y(value, max_lux):.2f}"
            for sample_time, value in points
        )
        return {"polyline": polyline, "count": len(points)}

    async def build_temp_day(day_start: datetime, day_end: datetime, timeline_end: datetime):
        VENT_TIMELINE_DEVICES = dependencies.VENT_TIMELINE_DEVICES
        async_session = dependencies.async_session
        clean_display_text = dependencies.clean_display_text
        percent_between = dependencies.percent_between
        series_config = [
            {"key": "temp_1etg", "label": "1.etg", "kind": "temperature", "unit": "C", "class": "one", "color": "#df705d", "default": False},
            {"key": "temp_2etg", "label": "2.etg", "kind": "temperature", "unit": "C", "class": "two", "color": "#f2b84b", "default": False},
            {"key": "temp_vip", "label": "VIP", "kind": "temperature", "unit": "C", "class": "vip", "color": "#8b5cf6", "default": False},
            {"key": "temp_ute", "label": "Ute styring", "kind": "temperature", "unit": "C", "class": "outdoor", "color": "#2f8fa3", "default": False},
            {"key": "temp_ute_netatmo", "label": "Ute Netatmo", "kind": "temperature", "unit": "C", "class": "outdoor-netatmo", "color": "#14b8a6", "default": False},
            {"key": "temp_yr", "label": "Yr API", "kind": "temperature", "unit": "C", "class": "yr", "color": "#4b7fbb", "default": False},
            {"key": "temp_loft", "label": "Loft", "kind": "temperature", "unit": "C", "class": "loft", "color": "#726189", "default": True},
            {"key": "temp_kjeller", "label": "Kjeller", "kind": "temperature", "unit": "C", "class": "basement", "color": "#2f8fa3", "default": False},
            {"key": "temp_passiv", "label": "Pass innluft", "kind": "temperature", "unit": "C", "class": "passive", "color": "#52a464", "default": False},
            {"key": "temp_luftinntak", "label": "Luftinntak", "kind": "temperature", "unit": "C", "class": "intake", "color": "#9a660f", "default": False},
            {"key": "temp_min_inne", "label": "Min inne", "kind": "temperature", "unit": "C", "class": "indoor-min", "color": "#93c5fd", "default": False},
            {"key": "temp_avg_inne", "label": "Snitt inne", "kind": "temperature", "unit": "C", "class": "indoor-avg", "color": "#3f7fbd", "default": False},
            {"key": "temp_max_inne", "label": "Maks inne", "kind": "temperature", "unit": "C", "class": "indoor-max", "color": "#1d4ed8", "default": False},
            {"key": "humidity_kjeller", "label": "Fukt kjeller", "kind": "humidity", "unit": "%", "class": "humidity-basement", "color": "#0f766e", "default": True},
            {"key": "humidity_1etg", "label": "Fukt 1.etg", "kind": "humidity", "unit": "%", "class": "humidity-one", "color": "#16a34a", "default": False},
            {"key": "humidity_2etg", "label": "Fukt 2.etg", "kind": "humidity", "unit": "%", "class": "humidity-two", "color": "#22c55e", "default": False},
            {"key": "humidity_vip", "label": "Fukt VIP", "kind": "humidity", "unit": "%", "class": "humidity-vip", "color": "#14b8a6", "default": False},
            {"key": "humidity_loft", "label": "Fukt loft", "kind": "humidity", "unit": "%", "class": "humidity-loft", "color": "#0d9488", "default": False},
            {"key": "humidity_ute", "label": "Fukt ute", "kind": "humidity", "unit": "%", "class": "humidity-outdoor", "color": "#38bdf8", "default": False},
            {"key": "humidity_yr", "label": "Fukt Yr", "kind": "humidity", "unit": "%", "class": "humidity-yr", "color": "#60a5fa", "default": False},
            {"key": "humidity_luftinntak", "label": "Fukt innluft", "kind": "humidity", "unit": "%", "class": "humidity-intake", "color": "#06b6d4", "default": False},
            {"key": "humidity_passiv", "label": "Fukt passiv", "kind": "humidity", "unit": "%", "class": "humidity-passive", "color": "#84cc16", "default": False},
        ]
        fan_config = [
            {**VENT_TIMELINE_DEVICES[0], "short": "VIP", "color": "#52a464", "default": True},
            {**VENT_TIMELINE_DEVICES[1], "short": "2.etg", "color": "#3f7fbd", "default": True},
            {**VENT_TIMELINE_DEVICES[2], "short": "Tak", "color": "#726189", "default": True},
            {**VENT_TIMELINE_DEVICES[3], "short": "Avf.", "color": "#2f8fa3", "default": True},
        ]
        fan_by_key = {fan["key"]: fan for fan in fan_config}

        async with async_session() as session:
            sample_result = await session.execute(
                select(VentilationSample)
                .where(VentilationSample.timestamp >= day_start)
                .where(VentilationSample.timestamp < timeline_end)
                .order_by(VentilationSample.timestamp.asc())
            )
            sample_rows = dedupe_samples_by_bucket(sample_result.scalars().all())
            fan_result = await session.execute(
                select(VentilationEvent)
                .where(VentilationEvent.timestamp >= day_start)
                .where(VentilationEvent.timestamp < timeline_end)
                .order_by(VentilationEvent.timestamp.asc())
            )
            fan_rows = fan_result.scalars().all()

        def day_value_label(series: Dict[str, Any], value: Any) -> str:
            if value is None:
                return "-"
            if series.get("kind") == "humidity":
                return f"{float(value):.0f}%"
            return temp_label(value)

        samples = []
        all_values = []
        for row in sample_rows:
            sample_time = row.bucket_start or row.timestamp
            if sample_time is None:
                continue

            sample = {
                "time_dt": sample_time,
                "time": sample_time.strftime("%H:%M"),
                "mode": row.mode or "",
                "source": row.source or "",
            }
            has_value = False
            for series in series_config:
                value = getattr(row, series["key"], None)
                sample[series["key"]] = value
                sample[f"{series['key']}_label"] = day_value_label(series, value)
                if value is not None:
                    has_value = True
                    if series.get("kind") == "temperature":
                        all_values.append(value)
            for fan in fan_config:
                sample_attr = fan.get("sample_attr")
                if not sample_attr:
                    continue
                state = getattr(row, sample_attr, None)
                sample[sample_attr] = state
                if state is not None:
                    has_value = True
            if has_value:
                samples.append(sample)

        axis = temp_axis(all_values)
        series_items = []
        for series in series_config:
            points = []
            values = []
            for sample in samples:
                value = sample[series["key"]]
                if value is None:
                    continue
                values.append(value)
                if series.get("kind") == "temperature":
                    points.append(
                        {
                            "x": percent_between(sample["time_dt"], day_start, day_end) * 10,
                            "y": temp_y(float(value), axis["min"], axis["max"]),
                        }
                    )
            series_items.append(
                {
                    **series,
                    "polyline": " ".join(f"{point['x']:.2f},{point['y']:.2f}" for point in points),
                    "latest": day_value_label(series, values[-1]) if values else "-",
                    "min": day_value_label(series, min(values)) if values else "-",
                    "max": day_value_label(series, max(values)) if values else "-",
                }
            )

        y_ticks = []
        tick = axis["min"]
        while tick <= axis["max"] + 0.001:
            y_ticks.append({"label": temp_label(tick), "y": temp_y(tick, axis["min"], axis["max"])})
            tick += axis["step"]

        fan_events = []
        for row in fan_rows:
            fan_key = event_device_key(row, VENT_TIMELINE_DEVICES)
            if fan_key not in fan_by_key:
                continue
            state = state_from_event(row)
            if state is None:
                continue
            fan = fan_by_key[fan_key]
            event_time = max(day_start, min(timeline_end, row.timestamp))
            fan_events.append(
                {
                    "fan_key": fan_key,
                    "fan_name": fan["name"],
                    "fan_short": fan["short"],
                    "color": fan["color"],
                    "x": percent_between(event_time, day_start, day_end) * 10,
                    "time": event_time.strftime("%H:%M"),
                    "action": "PÅ" if state else "AV",
                    "class": "on" if state else "off",
                    "detail": clean_display_text(row.reason or row.source or ""),
                }
            )

        visible_series_count = sum(1 for series in series_items if series["polyline"])
        summary = {
            "count": len(samples),
            "fan_event_count": len(fan_events),
            "latest_time": samples[-1]["time"] if samples else "-",
            "axis_min": temp_label(axis["min"]),
            "axis_max": temp_label(axis["max"]),
            "series_count": visible_series_count,
        }
        return {
            "series": series_items,
            "fans": fan_config,
            "fan_events": fan_events,
            "y_ticks": y_ticks,
            "samples_desc": list(reversed(samples)),
            "summary": summary,
        }

    def merged_extra(data: EventDataIn):
        extra = dict(data.extra or {})
        if data.device_key:
            extra["device_key"] = data.device_key
        if data.values:
            extra["values"] = data.values
        for key in ("weather_type", "weather_symbol", "weather_text", "yr_weather", "yr_symbol"):
            value = getattr(data, key)
            if value not in (None, ""):
                extra[key] = value
        return extra or None

    def light_from_payload(data: EventDataIn) -> OutdoorLightEvent:
        value_from_payload = dependencies.value_from_payload
        return OutdoorLightEvent(
            timestamp=data.timestamp or datetime.now(timezone.utc).replace(tzinfo=None),
            event_type=data.event_type,
            action=data.action,
            device_key=data.device_key,
            device_id=data.device_id,
            device_name=data.device_name,
            mode=data.mode,
            reason=data.reason,
            source=data.source,
            lux=value_from_payload(data, "lux"),
            value=value_from_payload(data, "value"),
            state=value_from_payload(data, "state"),
            extra=merged_extra(data),
        )

    def light_sample_from_payload(data: EventDataIn, met_weather: Optional[Dict[str, Any]] = None) -> OutdoorLightSample:
        payload_weather_symbol = dependencies.payload_weather_symbol
        payload_weather_text = dependencies.payload_weather_text
        value_from_payload = dependencies.value_from_payload
        weather_label = dependencies.weather_label
        timestamp = data.timestamp or datetime.utcnow()
        weather_symbol = payload_weather_symbol(data) or ((met_weather or {}).get("symbol") or None)
        weather_text = weather_label(payload_weather_text(data)) or ((met_weather or {}).get("text") or None)
        return OutdoorLightSample(
            timestamp=timestamp,
            bucket_start=data.bucket_start or sample_bucket(timestamp),
            mode=data.mode,
            source=data.source,
            lux=value_from_payload(data, "lux"),
            value=value_from_payload(data, "value"),
            light_lyslist=value_from_payload(data, "light_lyslist"),
            light_reklame=value_from_payload(data, "light_reklame"),
            light_spot_glass_275=value_from_payload(data, "light_spot_glass_275"),
            light_spot_glass_299=value_from_payload(data, "light_spot_glass_299"),
            light_spot_inngang=value_from_payload(data, "light_spot_inngang"),
            light_parkering=value_from_payload(data, "light_parkering"),
            weather_symbol=weather_symbol,
            weather_text=weather_text,
            extra=merged_extra(data),
        )

    def vent_from_payload(data: EventDataIn) -> VentilationEvent:
        value_from_payload = dependencies.value_from_payload
        return VentilationEvent(
            timestamp=data.timestamp or datetime.utcnow(),
            event_type=data.event_type,
            action=data.action,
            device_key=data.device_key,
            device_id=data.device_id,
            device_name=data.device_name,
            mode=data.mode,
            reason=data.reason,
            source=data.source,
            value=value_from_payload(data, "value"),
            state=value_from_payload(data, "state"),
            temp_1etg=value_from_payload(data, "temp_1etg"),
            temp_2etg=value_from_payload(data, "temp_2etg"),
            temp_vip=value_from_payload(data, "temp_vip"),
            temp_ute=value_from_payload(data, "temp_ute"),
            temp_loft=value_from_payload(data, "temp_loft"),
            humidity_1etg=value_from_payload(data, "humidity_1etg"),
            humidity_2etg=value_from_payload(data, "humidity_2etg"),
            humidity_vip=value_from_payload(data, "humidity_vip"),
            humidity_ute=value_from_payload(data, "humidity_ute"),
            humidity_yr=value_from_payload(data, "humidity_yr"),
            humidity_loft=value_from_payload(data, "humidity_loft"),
            temp_kjeller=value_from_payload(data, "temp_kjeller"),
            humidity_kjeller=value_from_payload(data, "humidity_kjeller"),
            temp_passiv=value_from_payload(data, "temp_passiv"),
            temp_luftinntak=value_from_payload(data, "temp_luftinntak"),
            humidity_passiv=value_from_payload(data, "humidity_passiv"),
            humidity_luftinntak=value_from_payload(data, "humidity_luftinntak"),
            diff_w=value_from_payload(data, "diff_w"),
            power_w=value_from_payload(data, "power_w"),
            energy_kwh=value_from_payload(data, "energy_kwh"),
            fan_vip=value_from_payload(data, "fan_vip"),
            fan_2etg=value_from_payload(data, "fan_2etg"),
            fan_tak=value_from_payload(data, "fan_tak"),
            fan_avfukter=value_from_payload(data, "fan_avfukter"),
            extra=merged_extra(data),
        )

    def vent_sample_from_payload(data: EventDataIn) -> VentilationSample:
        value_from_payload = dependencies.value_from_payload
        timestamp = data.timestamp or datetime.utcnow()
        return VentilationSample(
            timestamp=timestamp,
            bucket_start=data.bucket_start or sample_bucket(timestamp),
            mode=data.mode,
            source=data.source,
            temp_1etg=value_from_payload(data, "temp_1etg"),
            temp_2etg=value_from_payload(data, "temp_2etg"),
            temp_vip=value_from_payload(data, "temp_vip"),
            temp_ute=value_from_payload(data, "temp_ute"),
            temp_ute_netatmo=value_from_payload(data, "temp_ute_netatmo"),
            temp_yr=value_from_payload(data, "temp_yr"),
            temp_loft=value_from_payload(data, "temp_loft"),
            humidity_1etg=value_from_payload(data, "humidity_1etg"),
            humidity_2etg=value_from_payload(data, "humidity_2etg"),
            humidity_vip=value_from_payload(data, "humidity_vip"),
            humidity_ute=value_from_payload(data, "humidity_ute"),
            humidity_yr=value_from_payload(data, "humidity_yr"),
            humidity_loft=value_from_payload(data, "humidity_loft"),
            temp_kjeller=value_from_payload(data, "temp_kjeller"),
            humidity_kjeller=value_from_payload(data, "humidity_kjeller"),
            temp_passiv=value_from_payload(data, "temp_passiv"),
            temp_luftinntak=value_from_payload(data, "temp_luftinntak"),
            humidity_passiv=value_from_payload(data, "humidity_passiv"),
            humidity_luftinntak=value_from_payload(data, "humidity_luftinntak"),
            temp_min_inne=value_from_payload(data, "temp_min_inne"),
            temp_avg_inne=value_from_payload(data, "temp_avg_inne"),
            temp_max_inne=value_from_payload(data, "temp_max_inne"),
            diff_w=value_from_payload(data, "diff_w"),
            estimated_sunbeds=value_from_payload(data, "estimated_sunbeds"),
            afterrun_active=value_from_payload(data, "afterrun_active"),
            heat_need=value_from_payload(data, "heat_need"),
            cool_need=value_from_payload(data, "cool_need"),
            open_time=value_from_payload(data, "open_time"),
            pre_cooling=value_from_payload(data, "pre_cooling"),
            exhaust_time_allowed=value_from_payload(data, "exhaust_time_allowed"),
            fan_vip=value_from_payload(data, "fan_vip"),
            fan_2etg=value_from_payload(data, "fan_2etg"),
            fan_tak=value_from_payload(data, "fan_tak"),
            fan_avfukter=value_from_payload(data, "fan_avfukter"),
            extra=merged_extra(data),
        )

    async def upsert_kjeller_measurement_sample(session, timestamp: datetime, fibaroid: int, value: float, source: str) -> Optional[int]:
        field_map = {
            408: "humidity_1etg",
            344: "humidity_2etg",
            347: "humidity_vip",
            350: "humidity_ute",
            353: "humidity_loft",
            357: "humidity_luftinntak",
            359: "humidity_2etg",
            362: "humidity_vip",
            444: "temp_kjeller",
            445: "humidity_kjeller",
        }
        field = field_map.get(fibaroid)
        if not field:
            return None
        bucket_start = sample_bucket(timestamp)
        row = (
            await session.execute(
                select(VentilationSample)
                .where(VentilationSample.bucket_start == bucket_start)
                .order_by(VentilationSample.id.desc())
                .limit(1)
            )
        ).scalars().first()
        if not row:
            row = VentilationSample(
                timestamp=timestamp,
                bucket_start=bucket_start,
                source=source,
                extra={"measurement_source": "hc3_meter_readings"},
            )
            session.add(row)
            await session.flush()
        else:
            row.timestamp = max(row.timestamp or timestamp, timestamp)
            row.source = row.source or source
            row.extra = {
                **(row.extra or {}),
                "measurement_source": "hc3_meter_readings",
            }
        setattr(row, field, value)
        return row.id

    def generic_from_payload(data: EventDataIn) -> GenericEvent:
        value_from_payload = dependencies.value_from_payload
        return GenericEvent(
            timestamp=data.timestamp or datetime.utcnow(),
            system=data.system,
            event_type=data.event_type,
            action=data.action,
            device_key=data.device_key,
            device_id=data.device_id,
            device_name=data.device_name,
            mode=data.mode,
            reason=data.reason,
            source=data.source,
            lux=value_from_payload(data, "lux"),
            value=value_from_payload(data, "value"),
            state=value_from_payload(data, "state"),
            extra=merged_extra(data),
        )

    def hc3_first_present(*values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    def hc3_api_is_configured() -> bool:
        HC3_BASE_URL = dependencies.HC3_BASE_URL
        HC3_PASS = dependencies.HC3_PASS
        HC3_USER = dependencies.HC3_USER
        return bool(HC3_BASE_URL and HC3_USER and HC3_PASS)

    def hc3_basic_auth_header() -> str:
        HC3_PASS = dependencies.HC3_PASS
        HC3_USER = dependencies.HC3_USER
        token = base64.b64encode(f"{HC3_USER}:{HC3_PASS}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    def hc3_device_request(device_id: int, timeout_seconds: Optional[int] = None) -> Dict[str, Any]:
        HC3_BASE_URL = dependencies.HC3_BASE_URL
        HC3_DOOR_POLL_TIMEOUT_SECONDS = dependencies.HC3_DOOR_POLL_TIMEOUT_SECONDS
        if not hc3_api_is_configured():
            raise RuntimeError("HC3_BASE_URL/HC3_USER/HC3_PASS er ikke konfigurert for Fibaro10.")
        request = urllib.request.Request(f"{HC3_BASE_URL}/api/devices/{int(device_id)}")
        request.add_header("Accept", "application/json")
        request.add_header("Authorization", hc3_basic_auth_header())
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds or HC3_DOOR_POLL_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"HC3 svarte {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"HC3 kunne ikke nås: {exc.reason}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("HC3 svarte ikke med et JSON-objekt.")
        return payload

    def hc3_cached_device_request(device_id: int, timeout_seconds: Optional[int] = None) -> Dict[str, Any]:
        HC3_SWITCH_STATUS_CACHE_SECONDS = dependencies.HC3_SWITCH_STATUS_CACHE_SECONDS
        hc3_switch_status_cache = dependencies.hc3_switch_status_cache
        device_id_int = int(device_id)
        now_monotonic = monotonic()
        cached = hc3_switch_status_cache.get(device_id_int)
        if cached and HC3_SWITCH_STATUS_CACHE_SECONDS > 0 and now_monotonic - cached[0] <= HC3_SWITCH_STATUS_CACHE_SECONDS:
            return dict(cached[1])
        payload = hc3_device_request(device_id_int, timeout_seconds=timeout_seconds)
        hc3_switch_status_cache[device_id_int] = (now_monotonic, dict(payload))
        return payload

    def hc3_devices_request(timeout_seconds: Optional[int] = None) -> list[Dict[str, Any]]:
        HC3_BASE_URL = dependencies.HC3_BASE_URL
        HC3_ENERGY_DEVICE_LIST_CACHE_SECONDS = dependencies.HC3_ENERGY_DEVICE_LIST_CACHE_SECONDS
        HC3_ENERGY_LIVE_TIMEOUT_SECONDS = dependencies.HC3_ENERGY_LIVE_TIMEOUT_SECONDS
        hc3_energy_device_list_cache = dependencies.hc3_energy_device_list_cache
        if not hc3_api_is_configured():
            raise RuntimeError("HC3_BASE_URL/HC3_USER/HC3_PASS er ikke konfigurert for Fibaro10.")
        now_monotonic = monotonic()
        cached_at = float(hc3_energy_device_list_cache.get("cached_at") or 0)
        cached_rows = hc3_energy_device_list_cache.get("rows")
        if isinstance(cached_rows, list) and now_monotonic - cached_at <= HC3_ENERGY_DEVICE_LIST_CACHE_SECONDS:
            return [dict(row) for row in cached_rows]
        request = urllib.request.Request(f"{HC3_BASE_URL}/api/devices")
        request.add_header("Accept", "application/json")
        request.add_header("Authorization", hc3_basic_auth_header())
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds or HC3_ENERGY_LIVE_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"HC3 svarte {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"HC3 kunne ikke nås: {exc.reason}") from exc
        if not isinstance(payload, list):
            raise RuntimeError("HC3 svarte ikke med en enhetsliste.")
        rows = [dict(row) for row in payload if isinstance(row, dict)]
        hc3_energy_device_list_cache["cached_at"] = now_monotonic
        hc3_energy_device_list_cache["rows"] = rows
        return [dict(row) for row in rows]

    def hc3_switch_status_from_device(config: Dict[str, Any], device: Dict[str, Any]) -> Dict[str, Any]:
        parse_boolish = dependencies.parse_boolish
        properties = device.get("properties") if isinstance(device.get("properties"), dict) else {}
        raw_value = hc3_first_present(properties.get("value"), device.get("value"))
        dead = parse_boolish(hc3_first_present(properties.get("dead"), device.get("dead")))
        enabled = parse_boolish(hc3_first_present(properties.get("enabled"), device.get("enabled")))
        return {
            "key": config.get("key"),
            "label": config.get("name"),
            "deviceId": int(config.get("device_id") or device.get("id") or 0) or None,
            "deviceName": hc3_first_present(device.get("name"), properties.get("name"), config.get("name")),
            "state": parse_boolish(raw_value),
            "rawValue": str(raw_value).lower() if isinstance(raw_value, bool) else str(raw_value) if raw_value is not None else None,
            "dead": dead,
            "enabled": enabled,
            "statusSource": "HC3 styring",
            "checkedAt": api_local_iso(local_now_naive()),
            "error": None,
        }

    async def hc3_fetch_switch_status(config: Dict[str, Any]) -> Dict[str, Any]:
        HC3_SWITCH_POLL_TIMEOUT_SECONDS = dependencies.HC3_SWITCH_POLL_TIMEOUT_SECONDS
        device_id = config.get("device_id")
        if device_id is None:
            raise RuntimeError("Mangler HC3 device-id.")
        device = await asyncio.to_thread(
            hc3_cached_device_request,
            int(device_id),
            HC3_SWITCH_POLL_TIMEOUT_SECONDS,
        )
        return hc3_switch_status_from_device(config, device)

    async def hc3_fetch_switch_statuses(configs: list[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        if not configs or not hc3_api_is_configured():
            return {}
        semaphore = asyncio.Semaphore(4)

        async def fetch_one(config: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
            key = str(config.get("key") or config.get("device_id") or "unknown")
            async with semaphore:
                try:
                    return key, await hc3_fetch_switch_status(config)
                except Exception as exc:
                    return key, {
                        "key": key,
                        "label": config.get("name"),
                        "deviceId": config.get("device_id"),
                        "deviceName": config.get("name"),
                        "state": None,
                        "rawValue": None,
                        "dead": None,
                        "enabled": None,
                        "statusSource": "HC3 styring feilet",
                        "checkedAt": api_local_iso(local_now_naive()),
                        "error": str(exc),
                    }

        rows = await asyncio.gather(*(fetch_one(config) for config in configs))
        return {key: payload for key, payload in rows}

    def hc3_unexpected_poll_cooldown_active(device_id: int, now: datetime) -> bool:
        hc3_door_unexpected_verified_until = dependencies.hc3_door_unexpected_verified_until
        until = hc3_door_unexpected_verified_until.get(int(device_id))
        return bool(until and until > now)

    def mark_hc3_unexpected_poll_verified(device_ids: Iterable[int], now: datetime) -> None:
        HC3_DOOR_UNEXPECTED_RECHECK_MINUTES = dependencies.HC3_DOOR_UNEXPECTED_RECHECK_MINUTES
        hc3_door_unexpected_verified_until = dependencies.hc3_door_unexpected_verified_until
        until = now + timedelta(minutes=HC3_DOOR_UNEXPECTED_RECHECK_MINUTES)
        for device_id in device_ids:
            hc3_door_unexpected_verified_until[int(device_id)] = until

    def attach_hc3_alarm_verification(items: list[Dict[str, Any]], result: Optional[Dict[str, Any]]) -> list[Dict[str, Any]]:
        if result is None:
            return items
        checked_at = local_now_naive().isoformat()
        checked_ok = bool(result.get("ok")) and int(result.get("checked") or 0) > 0
        output: list[Dict[str, Any]] = []
        for source_item in items:
            item = dict(source_item)
            if item.get("severity") == "alert" and item.get("isOccupied") and item.get("alarmReason"):
                item["hc3VerificationAt"] = checked_at
                item["hc3VerificationOk"] = checked_ok
                item["hc3VerificationFailed"] = not checked_ok
                item["hc3VerificationMessage"] = result.get("message")
            output.append(item)
        return output

    def alarm_event_payload(row: AlarmEvent) -> Dict[str, Any]:
        return {
            "id": row.id,
            "eventKey": row.event_key,
            "domain": row.domain,
            "alarmType": row.alarm_type,
            "status": row.status,
            "severity": row.severity,
            "outcome": row.outcome,
            "title": row.title,
            "detail": row.detail,
            "deviceKey": row.device_key,
            "deviceId": row.device_id,
            "roomId": row.room_id,
            "displayRoomNumber": row.display_room_number,
            "physicalRoomNumber": row.physical_room_number,
            "sun2BedId": row.sun2_bed_id,
            "sourceSessionId": row.source_session_id,
            "doorChangedAt": row.door_changed_at.isoformat() if row.door_changed_at else None,
            "expectedExitAt": row.expected_exit_at.isoformat() if row.expected_exit_at else None,
            "detectedAt": row.detected_at.isoformat() if row.detected_at else None,
            "detectedLabel": format_source_datetime(row.detected_at) if row.detected_at else "-",
            "lastObservedAt": row.last_observed_at.isoformat() if row.last_observed_at else None,
            "resolvedAt": row.resolved_at.isoformat() if row.resolved_at else None,
            "resolvedLabel": format_source_datetime(row.resolved_at) if row.resolved_at else "Pågår",
            "resolutionReason": row.resolution_reason,
            "notificationStatus": row.notification_status,
            "notificationCount": int(row.notification_count or 0),
            "firstNotificationAt": row.first_notification_at.isoformat() if row.first_notification_at else None,
            "lastNotificationAt": row.last_notification_at.isoformat() if row.last_notification_at else None,
            "lastNotificationLabel": format_source_datetime(row.last_notification_at) if row.last_notification_at else "-",
            "reviewedAt": row.reviewed_at.isoformat() if row.reviewed_at else None,
            "reviewedBy": row.reviewed_by,
            "reviewNote": row.review_note,
            "source": row.source,
        }

    async def config_context(config_key: str):
        async_session = dependencies.async_session
        definition = config_definition(config_key)
        if not definition:
            return None
        async with async_session() as session:
            row = await get_or_create_config(session, config_key)
            history = (
                await session.execute(
                    select(ControlConfigHistory)
                    .where(ControlConfigHistory.config_key == config_key)
                    .order_by(ControlConfigHistory.changed_at.desc())
                    .limit(20)
                )
            ).scalars().all()
        values = merge_config_values(config_key, row.values)
        return {
            "definition": definition,
            "config_key": config_key,
            "config": row,
            "values": values,
            "rules": config_rules(config_key, values),
            "summary_rows": config_summary_rows(config_key, values),
            "stat_cards": config_stat_cards(config_key, values, row.version),
            "operational_notes": config_operational_notes(config_key, values),
            "devices": config_devices(config_key),
            "history": history,
            "saved": False,
            "errors": [],
        }

    def ventilation_latest_payload(
        latest: Optional[VentilationSample],
        latest_yr: Optional[YrForecastSample],
        fan_statuses: Optional[list[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        VENT_TIMELINE_DEVICES = dependencies.VENT_TIMELINE_DEVICES
        def measurement(key: str, label: str, temp_key: Optional[str] = None, humidity_key: Optional[str] = None, detail: str = "") -> Dict[str, Any]:
            return {
                "key": key,
                "label": label,
                "temperature": getattr(latest, temp_key, None) if latest and temp_key else None,
                "humidity": getattr(latest, humidity_key, None) if latest and humidity_key else None,
                "detail": detail,
            }

        fans = fan_statuses if fan_statuses is not None else [
            {
                **ventilation_status_payload(device, latest, None),
                "detail": "Paa" if sample_state(latest, device) is True else "AV" if sample_state(latest, device) is False else "-",
            }
            for device in VENT_TIMELINE_DEVICES
        ]
        return {
            "bucketStart": api_local_iso(latest.bucket_start if latest else None),
            "timestamp": api_local_iso(latest.timestamp if latest else None),
            "mode": latest.mode if latest else None,
            "source": latest.source if latest else None,
            "groups": [
                {
                    "key": "indoor",
                    "title": "Inne",
                    "fields": [
                        measurement("1etg", "1.etg", "temp_1etg", "humidity_1etg"),
                        measurement("2etg", "2.etg", "temp_2etg", "humidity_2etg"),
                        measurement("vip", "VIP", "temp_vip", "humidity_vip"),
                    ],
                },
                {
                    "key": "outdoor",
                    "title": "Ute og Yr",
                    "fields": [
                        measurement("styring", "Ute styring", "temp_ute", "humidity_ute"),
                        measurement("netatmo", "Netatmo ute", "temp_ute_netatmo", "humidity_ute"),
                        measurement("yr", "Yr", "temp_yr", "humidity_yr", latest_yr.weather_text if latest_yr else ""),
                    ],
                },
                {
                    "key": "ventilation",
                    "title": "Ventilasjon",
                    "fields": [
                        measurement("loft", "Loft", "temp_loft", "humidity_loft"),
                        measurement("luftinntak", "Innluft", "temp_luftinntak", "humidity_luftinntak"),
                        measurement("passiv", "Passiv innluft", "temp_passiv", "humidity_passiv"),
                    ],
                },
                {
                    "key": "basement",
                    "title": "Kjeller",
                    "fields": [
                        measurement("kjeller", "Kjeller", "temp_kjeller", "humidity_kjeller", "Avfukter styres av fukt"),
                    ],
                },
            ],
            "fans": fans,
            "weather": {
                "bucketStart": api_local_iso(latest_yr.bucket_start if latest_yr else None),
                "text": latest_yr.weather_text if latest_yr else None,
                "airTemperature": latest_yr.air_temperature if latest_yr else None,
                "relativeHumidity": latest_yr.relative_humidity if latest_yr else None,
                "windSpeed": latest_yr.wind_speed if latest_yr else None,
                "windGust": latest_yr.wind_speed_of_gust if latest_yr else None,
                "cloudAreaFraction": latest_yr.cloud_area_fraction if latest_yr else None,
                "precipitationNext1h": latest_yr.precipitation_next_1h if latest_yr else None,
            },
        }

    def ventilation_day_payload(temp_day: Dict[str, Any], selected_day: date, is_today: bool, now_marker: Optional[float]) -> Dict[str, Any]:
        samples = []
        for sample in reversed(temp_day["samples_desc"]):
            cleaned = {key: value for key, value in sample.items() if key != "time_dt" and not key.endswith("_label")}
            samples.append(cleaned)
        return {
            "selectedDay": selected_day.isoformat(),
            "selectedDayLabel": selected_day.strftime("%d.%m.%Y"),
            "prevDay": (selected_day - timedelta(days=1)).isoformat(),
            "nextDay": (selected_day + timedelta(days=1)).isoformat(),
            "isToday": is_today,
            "nowMarker": now_marker,
            "summary": temp_day["summary"],
            "series": temp_day["series"],
            "fans": temp_day["fans"],
            "fanEvents": temp_day["fan_events"],
            "samples": samples,
        }

    def empty_ventilation_day_payload(selected_day: date, is_today: bool, now_marker: Optional[float]) -> Dict[str, Any]:
        return {
            "selectedDay": selected_day.isoformat(),
            "selectedDayLabel": selected_day.strftime("%d.%m.%Y"),
            "prevDay": (selected_day - timedelta(days=1)).isoformat(),
            "nextDay": (selected_day + timedelta(days=1)).isoformat(),
            "isToday": is_today,
            "nowMarker": now_marker,
            "summary": {},
            "series": [],
            "fans": [],
            "fanEvents": [],
            "samples": [],
        }

    def control_settings_payload(
        config_key: str,
        config: ControlConfig,
        values: Dict[str, Any],
        history: list[ControlConfigHistory],
    ) -> Dict[str, Any]:
        definition = config_definition(config_key) or {}
        groups = []
        for group in definition.get("groups", []):
            groups.append(
                {
                    "title": group["title"],
                    "description": group.get("description", ""),
                    "fields": [
                        {
                            "key": field["key"],
                            "label": field["label"],
                            "type": field.get("type", "text"),
                            "unit": field.get("unit", ""),
                            "help": field.get("help", ""),
                            "value": values.get(field["key"]),
                        }
                        for field in group.get("fields", [])
                    ],
                }
            )
        return {
            "system": config_key,
            "title": definition.get("title", config_key),
            "subtitle": definition.get("subtitle", ""),
            "version": config.version,
            "updatedAt": api_local_iso(config.updated_at),
            "updatedBy": config.updated_by,
            "groups": groups,
            "rules": config_rules(config_key, values),
            "summaryRows": config_summary_rows(config_key, values),
            "notes": config_operational_notes(config_key, values),
            "history": api_config_history_rows(history),
            "updateEndpoint": f"/api/config/{config_key}",
        }

    def ventilation_settings_payload(
        config: ControlConfig,
        values: Dict[str, Any],
        history: list[ControlConfigHistory],
    ) -> Dict[str, Any]:
        return control_settings_payload("ventilation", config, values, history)

    def api_config_value_rows(values: Dict[str, Any]) -> list[Dict[str, Any]]:
        return [{"key": key, "value": value} for key, value in sorted(values.items())]

    def api_config_field_rows(key: str, values: Dict[str, Any]) -> list[Dict[str, Any]]:
        definition = config_definition(key)
        if not definition:
            return api_config_value_rows(values)
        rows: list[Dict[str, Any]] = []
        for group in definition["groups"]:
            for field in group["fields"]:
                rows.append(
                    {
                        "group": group["title"],
                        "key": field["key"],
                        "label": field["label"],
                        "value": values.get(field["key"]),
                        "unit": field.get("unit") or "",
                        "help": field.get("help") or "",
                    }
                )
        return rows

    def api_config_history_rows(rows: list[ControlConfigHistory]) -> list[Dict[str, Any]]:
        row_to_dict = dependencies.row_to_dict
        return [
            row_to_dict(row, ["config_key", "version", "changed_at", "changed_by", "reason"])
            for row in rows
        ]

    return {
        "alarm_event_payload": alarm_event_payload,
        "api_config_field_rows": api_config_field_rows,
        "api_config_history_rows": api_config_history_rows,
        "api_config_value_rows": api_config_value_rows,
        "attach_hc3_alarm_verification": attach_hc3_alarm_verification,
        "build_light_chart_markers": build_light_chart_markers,
        "build_light_timeline_group": build_light_timeline_group,
        "build_lux_day": build_lux_day,
        "build_lux_sparkline": build_lux_sparkline,
        "build_solar_elevation_samples": build_solar_elevation_samples,
        "build_temp_day": build_temp_day,
        "build_timeline_group": build_timeline_group,
        "build_timeline_item": build_timeline_item,
        "config_context": config_context,
        "config_defaults": config_defaults,
        "config_definition": config_definition,
        "config_devices": config_devices,
        "config_operational_notes": config_operational_notes,
        "config_payload": config_payload,
        "config_rules": config_rules,
        "config_stat_cards": config_stat_cards,
        "config_summary_rows": config_summary_rows,
        "config_values_from_form": config_values_from_form,
        "config_values_from_payload": config_values_from_payload,
        "control_settings_payload": control_settings_payload,
        "dedupe_samples_by_bucket": dedupe_samples_by_bucket,
        "empty_ventilation_day_payload": empty_ventilation_day_payload,
        "event_detail": event_detail,
        "event_device_key": event_device_key,
        "event_extra_key": event_extra_key,
        "event_matches_device": event_matches_device,
        "fetch_lux_samples": fetch_lux_samples,
        "generic_from_payload": generic_from_payload,
        "get_or_create_config": get_or_create_config,
        "hc3_api_is_configured": hc3_api_is_configured,
        "hc3_basic_auth_header": hc3_basic_auth_header,
        "hc3_cached_device_request": hc3_cached_device_request,
        "hc3_control_device_id": hc3_control_device_id,
        "hc3_device_request": hc3_device_request,
        "hc3_devices_request": hc3_devices_request,
        "hc3_fetch_switch_status": hc3_fetch_switch_status,
        "hc3_fetch_switch_statuses": hc3_fetch_switch_statuses,
        "hc3_first_present": hc3_first_present,
        "hc3_switch_config_for_timeline_device": hc3_switch_config_for_timeline_device,
        "hc3_switch_status_from_device": hc3_switch_status_from_device,
        "hc3_unexpected_poll_cooldown_active": hc3_unexpected_poll_cooldown_active,
        "light_from_payload": light_from_payload,
        "light_ntfy_payload": light_ntfy_payload,
        "light_rules": light_rules,
        "light_sample_from_payload": light_sample_from_payload,
        "light_sample_state": light_sample_state,
        "light_status_text": light_status_text,
        "lux_scale": lux_scale,
        "lux_tick_label": lux_tick_label,
        "lux_tick_values": lux_tick_values,
        "lux_y": lux_y,
        "mark_hc3_unexpected_poll_verified": mark_hc3_unexpected_poll_verified,
        "merge_config_values": merge_config_values,
        "merged_extra": merged_extra,
        "parse_config_value": parse_config_value,
        "point_from_row": point_from_row,
        "publish_light_ntfy": publish_light_ntfy,
        "publish_ventilation_ntfy": publish_ventilation_ntfy,
        "sample_state": sample_state,
        "state_from_event": state_from_event,
        "status_sun_timeline_event": status_sun_timeline_event,
        "status_timeline_lane": status_timeline_lane,
        "temp_axis": temp_axis,
        "temp_label": temp_label,
        "temp_y": temp_y,
        "upsert_kjeller_measurement_sample": upsert_kjeller_measurement_sample,
        "validate_config_values": validate_config_values,
        "vent_from_payload": vent_from_payload,
        "vent_sample_from_payload": vent_sample_from_payload,
        "ventilation_day_payload": ventilation_day_payload,
        "ventilation_latest_payload": ventilation_latest_payload,
        "ventilation_ntfy_payload": ventilation_ntfy_payload,
        "ventilation_rules": ventilation_rules,
        "ventilation_settings_payload": ventilation_settings_payload,
        "ventilation_status_payload": ventilation_status_payload,
    }
