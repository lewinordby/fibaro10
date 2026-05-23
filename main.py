from datetime import date, datetime, time, timedelta
from email.utils import parsedate_to_datetime
from io import StringIO
from copy import deepcopy
from typing import Any, Dict, Optional
import asyncio
import csv
import hashlib
import json
import math
import os
import re
from urllib.parse import parse_qs
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, JSON, String, Text, UniqueConstraint, delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
LOCAL_TZ = ZoneInfo("Europe/Oslo")
MASTER_ACCESS_KEY_HASH = os.getenv(
    "MASTER_ACCESS_KEY_HASH",
    "752ede847bd180ef3d2700d117d297ced1b25664b946a3639fb7a3b2be93d5d1",
)
AUTH_USER_COOKIE_NAME = "fibaro10_access_username"
AUTH_COOKIE_NAME = "fibaro10_access_password"
PUBLIC_PREFIXES = ("/static/",)
PUBLIC_PATHS = {"/health", "/favicon.ico", "/auth/login"}


def env_float(name: str, default: str) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return float(default)


MET_LAT = env_float("MET_LAT", "61.1153")
MET_LON = env_float("MET_LON", "10.4662")
MET_USER_AGENT = os.getenv("MET_USER_AGENT", "fibaro10/1.0 https://fibaro10.onrender.com")
MET_WEATHER_CACHE = {"expires": datetime.min, "value": None}

app = FastAPI(title="Fibaro10")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def format_local_datetime(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    if isinstance(value, (int, float)):
        value = datetime.utcfromtimestamp(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(LOCAL_TZ).strftime("%d.%m.%Y %H:%M:%S")


def format_local_time(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    if isinstance(value, (int, float)):
        value = datetime.utcfromtimestamp(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(LOCAL_TZ).strftime("%H:%M")


templates.env.filters["localtime"] = format_local_datetime
templates.env.filters["localtime_short"] = format_local_time


ROBOROCK_STATE_LABELS = {
    1: "Starter opp",
    2: "Venter",
    3: "Hviler",
    4: "Klar",
    5: "Fjernstyring",
    6: "Rengjør",
    7: "Returnerer til dock",
    8: "Lader",
    9: "Ladefeil",
    10: "Pause",
    11: "Flekkrengjøring",
    12: "Feil",
    13: "Slår av",
    14: "Oppdaterer",
    15: "Dokker",
    16: "Går til målpunkt",
    17: "Sonerengjøring",
    18: "Romrengjøring",
    22: "Tømmer støvbeholder",
    23: "Vasker mopp",
    26: "Går til moppvask",
    28: "Kartlegger",
}

ROBOROCK_ERROR_LABELS = {
    0: "Ingen feil",
    1: "Laser/sensor-feil",
    2: "Støtfanger sitter fast",
    3: "Hjul henger",
    4: "Kantsensor må rengjøres",
    5: "Hovedbørste sitter fast",
    6: "Sidebørste sitter fast",
    7: "Hjul sitter fast",
    8: "Robot sitter fast",
    9: "Støvbeholder mangler",
    10: "Filter blokkert eller vått",
    11: "Magnetstripe/no-go oppdaget",
    12: "Lavt batteri",
    13: "Ladefeil",
    14: "Batterifeil",
    15: "Vegg-/avstandssensor må rengjøres",
    16: "Robot står skjevt",
    17: "Sidebørstemodul-feil",
    18: "Viftefeil",
    21: "Vertikal støtfanger trykket inn",
    22: "Dock-posisjonsfeil",
    23: "Dock-lokalisering mislyktes",
    24: "No-go-sone eller usynlig vegg",
    26: "Vannfilter må rengjøres",
}

ROBOROCK_FAN_LABELS = {
    101: "Stille",
    102: "Balansert",
    103: "Turbo",
    104: "Maks",
    105: "Maks+",
}

ROBOROCK_MOP_LABELS = {
    300: "Standard",
    301: "Lav",
    302: "Medium",
    303: "Høy",
}

ROBOROCK_WATER_LABELS = {
    200: "Av",
    201: "Lav",
    202: "Medium",
    203: "Høy",
}

ROBOROCK_CHARGE_LABELS = {
    0: "Ikke på lader",
    1: "På lader",
    2: "Lader",
}

ROBOROCK_DAYS = {
    "0": "søn",
    "1": "man",
    "2": "tir",
    "3": "ons",
    "4": "tor",
    "5": "fre",
    "6": "lør",
    "7": "søn",
    "SUN": "søn",
    "MON": "man",
    "TUE": "tir",
    "WED": "ons",
    "THU": "tor",
    "FRI": "fre",
    "SAT": "lør",
}


def roborock_label(mapping: Dict[int, str], value: Any, fallback_prefix: str = "Kode") -> str:
    number = int_value(value)
    if number is None:
        return "-"
    return mapping.get(number, f"{fallback_prefix} {number}")


def roborock_state_label(value: Any) -> str:
    return roborock_label(ROBOROCK_STATE_LABELS, value, "Statuskode")


def roborock_error_label(value: Any) -> str:
    return roborock_label(ROBOROCK_ERROR_LABELS, value, "Feilkode")


def roborock_fan_label(value: Any) -> str:
    return roborock_label(ROBOROCK_FAN_LABELS, value, "Nivå")


def roborock_mop_label(value: Any) -> str:
    return roborock_label(ROBOROCK_MOP_LABELS, value, "Nivå")


def roborock_water_label(value: Any) -> str:
    return roborock_label(ROBOROCK_WATER_LABELS, value, "Nivå")


def roborock_charge_label(value: Any) -> str:
    return roborock_label(ROBOROCK_CHARGE_LABELS, value, "Ladestatus")


def roborock_signal_label(value: Any) -> str:
    rssi = int_value(value)
    if rssi is None:
        return "-"
    if rssi >= -55:
        quality = "svært bra"
    elif rssi >= -67:
        quality = "bra"
    elif rssi >= -75:
        quality = "svak"
    else:
        quality = "dårlig"
    return f"{quality} ({rssi} dBm)"


def roborock_bool_label(value: Any) -> str:
    if value is None:
        return "-"
    return "Ja" if bool_value(value) else "Nei"


def format_seconds_as_hours(value: Any) -> str:
    seconds = int_value(value)
    if seconds is None:
        return "-"
    hours = seconds / 3600
    if hours < 1:
        return f"{round(seconds / 60)} min"
    return f"{hours:.1f} t"


def roborock_cron_parts(cron: Optional[str]) -> Optional[tuple[int, int, str]]:
    if not cron:
        return None
    parts = cron.split()
    if len(parts) < 5:
        return None
    minute = int_value(parts[0])
    hour = int_value(parts[1])
    if minute is None or hour is None:
        return None
    return minute, hour, parts[4]


def roborock_schedule_minutes(schedule: Any) -> int:
    parts = roborock_cron_parts(getattr(schedule, "cron", None))
    if not parts:
        return 24 * 60 + 1
    minute, hour, _ = parts
    return hour * 60 + minute


def roborock_next_schedule_score(schedule: Any) -> int:
    minutes = roborock_schedule_minutes(schedule)
    if minutes > 24 * 60:
        return minutes
    now = datetime.now(LOCAL_TZ)
    now_minutes = now.hour * 60 + now.minute
    return minutes - now_minutes if minutes >= now_minutes else minutes + (24 * 60 - now_minutes)


def roborock_schedule_text(schedule: Any) -> str:
    cron = getattr(schedule, "cron", None)
    parts = roborock_cron_parts(cron)
    if not parts:
        return cron or "-"
    minute, hour, day_field = parts
    time_text = f"{hour:02d}:{minute:02d}"
    if day_field in {"*", "?", ""}:
        return f"Hver dag kl. {time_text}"
    days = [ROBOROCK_DAYS.get(day.strip().upper(), day.strip()) for day in day_field.split(",") if day.strip()]
    if days:
        return f"{', '.join(days)} kl. {time_text}"
    return f"Kl. {time_text}"


def roborock_rounds_label(value: Any) -> str:
    number = int_value(value)
    if number is None:
        return "-"
    return f"{number} runde" if number == 1 else f"{number} runder"


def roborock_json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, indent=2, default=str)


templates.env.filters["roborock_state"] = roborock_state_label
templates.env.filters["roborock_error"] = roborock_error_label
templates.env.filters["roborock_fan"] = roborock_fan_label
templates.env.filters["roborock_mop"] = roborock_mop_label
templates.env.filters["roborock_water"] = roborock_water_label
templates.env.filters["roborock_charge"] = roborock_charge_label
templates.env.filters["roborock_signal"] = roborock_signal_label
templates.env.filters["yesno"] = roborock_bool_label
templates.env.filters["hours"] = format_seconds_as_hours
templates.env.filters["schedule_text"] = roborock_schedule_text
templates.env.filters["rounds"] = roborock_rounds_label
templates.env.filters["pretty_json"] = roborock_json

Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


@app.middleware("http")
async def access_key_middleware(request: Request, call_next):
    if is_public_request(request):
        return await call_next(request)

    username, password = presented_credentials(request)
    access_key = await find_access_key(username, password)
    if not access_key:
        await log_access_attempt(request, False, "missing_or_invalid_key", attempted_username=username)
        if wants_html(request):
            return templates.TemplateResponse(
                request,
                "login.html",
                {"error": "Mangler eller ugyldig brukernavn/passord"},
                status_code=401,
            )
        return JSONResponse({"detail": "Ugyldig eller manglende brukernavn/passord"}, status_code=401)

    request.state.access_key_id = access_key.id
    request.state.access_key_name = access_key.name
    request.state.auth_role = access_role(access_key)
    request.state.auth_is_master = request.state.auth_role == "master"
    request.state.auth_can_settings = request.state.auth_role in ["master", "settings"]
    await log_access_attempt(request, True, "ok", access_key)
    return await call_next(request)


class OutdoorLightEvent(Base):
    __tablename__ = "utelys_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True, default="device_change")
    action = Column(String, index=True, nullable=True)
    device_key = Column(String, index=True, nullable=True)
    device_id = Column(Integer, index=True, nullable=True)
    device_name = Column(String, nullable=True)
    mode = Column(String, index=True, nullable=True)
    reason = Column(Text, nullable=True)
    source = Column(Text, nullable=True)
    lux = Column(Float, nullable=True)
    value = Column(Float, nullable=True)
    state = Column(Boolean, nullable=True)
    extra = Column(JSON, nullable=True)


class OutdoorLightSample(Base):
    __tablename__ = "utelys_samples"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    bucket_start = Column(DateTime, index=True, nullable=False)
    mode = Column(String, index=True, nullable=True)
    source = Column(Text, nullable=True)
    lux = Column(Float, nullable=True)
    value = Column(Float, nullable=True)
    light_lyslist = Column(Boolean, nullable=True)
    light_reklame = Column(Boolean, nullable=True)
    light_spot_glass_275 = Column(Boolean, nullable=True)
    light_spot_glass_299 = Column(Boolean, nullable=True)
    light_spot_inngang = Column(Boolean, nullable=True)
    light_parkering = Column(Boolean, nullable=True)
    weather_symbol = Column(String, nullable=True)
    weather_text = Column(String, nullable=True)
    extra = Column(JSON, nullable=True)


class VentilationEvent(Base):
    __tablename__ = "ventilasjon_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True, default="fan_change")
    action = Column(String, index=True, nullable=True)
    device_key = Column(String, index=True, nullable=True)
    device_id = Column(Integer, index=True, nullable=True)
    device_name = Column(String, nullable=True)
    mode = Column(String, index=True, nullable=True)
    reason = Column(Text, nullable=True)
    source = Column(Text, nullable=True)
    value = Column(Float, nullable=True)
    state = Column(Boolean, nullable=True)

    temp_1etg = Column(Float, nullable=True)
    temp_2etg = Column(Float, nullable=True)
    temp_vip = Column(Float, nullable=True)
    temp_ute = Column(Float, nullable=True)
    temp_loft = Column(Float, nullable=True)
    temp_passiv = Column(Float, nullable=True)
    temp_luftinntak = Column(Float, nullable=True)
    diff_w = Column(Float, nullable=True)
    power_w = Column(Float, nullable=True)
    energy_kwh = Column(Float, nullable=True)

    fan_vip = Column(Boolean, nullable=True)
    fan_2etg = Column(Boolean, nullable=True)
    fan_tak = Column(Boolean, nullable=True)
    extra = Column(JSON, nullable=True)


class VentilationSample(Base):
    __tablename__ = "ventilasjon_samples"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    bucket_start = Column(DateTime, index=True, nullable=False)
    mode = Column(String, index=True, nullable=True)
    source = Column(Text, nullable=True)

    temp_1etg = Column(Float, nullable=True)
    temp_2etg = Column(Float, nullable=True)
    temp_vip = Column(Float, nullable=True)
    temp_ute = Column(Float, nullable=True)
    temp_ute_netatmo = Column(Float, nullable=True)
    temp_yr = Column(Float, nullable=True)
    temp_loft = Column(Float, nullable=True)
    temp_passiv = Column(Float, nullable=True)
    temp_luftinntak = Column(Float, nullable=True)
    temp_min_inne = Column(Float, nullable=True)
    temp_avg_inne = Column(Float, nullable=True)
    temp_max_inne = Column(Float, nullable=True)

    diff_w = Column(Float, nullable=True)
    estimated_sunbeds = Column(Integer, nullable=True)
    afterrun_active = Column(Boolean, nullable=True)
    heat_need = Column(Boolean, nullable=True)
    cool_need = Column(Boolean, nullable=True)
    open_time = Column(Boolean, nullable=True)
    pre_cooling = Column(Boolean, nullable=True)
    exhaust_time_allowed = Column(Boolean, nullable=True)

    fan_vip = Column(Boolean, nullable=True)
    fan_2etg = Column(Boolean, nullable=True)
    fan_tak = Column(Boolean, nullable=True)
    extra = Column(JSON, nullable=True)


class YrForecastSample(Base):
    __tablename__ = "yr_forecast_samples"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    bucket_start = Column(DateTime, index=True, nullable=False)
    source = Column(Text, nullable=True)
    api_updated_at = Column(DateTime, nullable=True)
    last_modified = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, index=True, nullable=True)
    next_fetch_after = Column(DateTime, nullable=True)
    age_seconds = Column(Integer, nullable=True)
    forecast_time = Column(DateTime, nullable=True)
    symbol_code = Column(String, nullable=True)
    weather_text = Column(String, nullable=True)
    air_temperature = Column(Float, nullable=True)
    relative_humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    wind_from_direction = Column(Float, nullable=True)
    cloud_area_fraction = Column(Float, nullable=True)
    fog_area_fraction = Column(Float, nullable=True)
    dew_point_temperature = Column(Float, nullable=True)
    air_pressure_at_sea_level = Column(Float, nullable=True)
    precipitation_next_1h = Column(Float, nullable=True)
    precipitation_next_6h = Column(Float, nullable=True)
    temp_1h = Column(Float, nullable=True)
    temp_3h = Column(Float, nullable=True)
    temp_6h = Column(Float, nullable=True)
    temp_12h = Column(Float, nullable=True)
    temp_24h = Column(Float, nullable=True)
    symbol_1h = Column(String, nullable=True)
    symbol_3h = Column(String, nullable=True)
    symbol_6h = Column(String, nullable=True)
    symbol_12h = Column(String, nullable=True)
    symbol_24h = Column(String, nullable=True)
    temp_min_next_6h = Column(Float, nullable=True)
    temp_max_next_6h = Column(Float, nullable=True)
    extra = Column(JSON, nullable=True)


class GenericEvent(Base):
    __tablename__ = "event_data"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    system = Column(String, index=True, nullable=False)
    event_type = Column(String, index=True, default="status")
    action = Column(String, index=True, nullable=True)
    device_key = Column(String, index=True, nullable=True)
    device_id = Column(Integer, index=True, nullable=True)
    device_name = Column(String, nullable=True)
    mode = Column(String, index=True, nullable=True)
    reason = Column(Text, nullable=True)
    source = Column(Text, nullable=True)
    lux = Column(Float, nullable=True)
    value = Column(Float, nullable=True)
    state = Column(Boolean, nullable=True)
    extra = Column(JSON, nullable=True)


class RoborockRobot(Base):
    __tablename__ = "roborock_robots"

    id = Column(Integer, primary_key=True, index=True)
    duid = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    product = Column(String, nullable=True)
    model = Column(String, nullable=True)
    firmware = Column(String, nullable=True)
    protocol_version = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    local_ip = Column(String, nullable=True)
    cloud_online = Column(Boolean, nullable=True)
    shared = Column(Boolean, nullable=True)
    time_zone_id = Column(String, nullable=True)
    last_seen_at = Column(DateTime, nullable=True, index=True)
    last_cloud_at = Column(DateTime, nullable=True)
    last_local_at = Column(DateTime, nullable=True)
    last_status_at = Column(DateTime, nullable=True)
    last_map_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    capabilities = Column(JSON, nullable=True)
    extra = Column(JSON, nullable=True)


class RoborockStatusSample(Base):
    __tablename__ = "roborock_status_samples"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, nullable=True)
    state_code = Column(Integer, nullable=True)
    state_name = Column(String, nullable=True)
    battery = Column(Integer, nullable=True)
    error_code = Column(Integer, nullable=True)
    in_cleaning = Column(Boolean, nullable=True)
    in_returning = Column(Boolean, nullable=True)
    clean_time_seconds = Column(Integer, nullable=True)
    clean_area_m2 = Column(Float, nullable=True)
    fan_power = Column(Integer, nullable=True)
    water_box_mode = Column(Integer, nullable=True)
    mop_mode = Column(Integer, nullable=True)
    dock_type = Column(Integer, nullable=True)
    charge_status = Column(Integer, nullable=True)
    clean_percent = Column(Integer, nullable=True)
    local_ip = Column(String, nullable=True)
    rssi = Column(Integer, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockCleanJob(Base):
    __tablename__ = "roborock_clean_jobs"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    record_id = Column(String, index=True, nullable=False)
    begin_at = Column(DateTime, index=True, nullable=True)
    end_at = Column(DateTime, index=True, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    area_m2 = Column(Float, nullable=True)
    cleaned_area_m2 = Column(Float, nullable=True)
    complete = Column(Boolean, nullable=True)
    error_code = Column(Integer, nullable=True)
    start_type = Column(Integer, nullable=True)
    clean_type = Column(Integer, nullable=True)
    finish_reason = Column(Integer, nullable=True)
    dust_collection_status = Column(Integer, nullable=True)
    avoid_count = Column(Integer, nullable=True)
    wash_count = Column(Integer, nullable=True)
    clean_times = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class RoborockSchedule(Base):
    __tablename__ = "roborock_schedules"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    schedule_id = Column(String, index=True, nullable=False)
    cron = Column(String, nullable=True)
    enabled = Column(Boolean, nullable=True)
    repeated = Column(Boolean, nullable=True)
    segments = Column(String, nullable=True)
    fan_power = Column(Integer, nullable=True)
    mop_mode = Column(Integer, nullable=True)
    water_box_mode = Column(Integer, nullable=True)
    repeat = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class RoborockConsumableSnapshot(Base):
    __tablename__ = "roborock_consumables"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    main_brush_work_time = Column(Integer, nullable=True)
    side_brush_work_time = Column(Integer, nullable=True)
    filter_work_time = Column(Integer, nullable=True)
    sensor_dirty_time = Column(Integer, nullable=True)
    dust_collection_work_times = Column(Integer, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockMapSnapshot(Base):
    __tablename__ = "roborock_maps"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    image_bytes = Column(Integer, nullable=True)
    raw_bytes = Column(Integer, nullable=True)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    rooms = Column(Integer, nullable=True)
    zones = Column(Integer, nullable=True)
    charger = Column(JSON, nullable=True)
    vacuum_position = Column(JSON, nullable=True)
    image_base64 = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockProbeResult(Base):
    __tablename__ = "roborock_probe_results"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, index=True, nullable=True)
    command = Column(String, index=True, nullable=True)
    ok = Column(Boolean, nullable=True)
    error = Column(Text, nullable=True)
    result_type = Column(String, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockSyncRun(Base):
    __tablename__ = "roborock_sync_runs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    collector_id = Column(String, index=True, nullable=True)
    source = Column(String, nullable=True)
    ok = Column(Boolean, nullable=True)
    robots_count = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class Sun2RoomDailyStat(Base):
    __tablename__ = "sun2_room_daily_stats"
    __table_args__ = (UniqueConstraint("stat_date", "room", name="uq_sun2_room_daily_stats_date_room"),)

    id = Column(Integer, primary_key=True, index=True)
    stat_date = Column(Date, index=True, nullable=False)
    room_key = Column(String, index=True, nullable=True)
    room = Column(String, index=True, nullable=False)
    source_room_name = Column(String, nullable=True)
    total_soletid_minutter = Column(Float, nullable=True)
    totalt_antall_solinger = Column(Integer, nullable=True)
    solinger_medlemmer = Column(Integer, nullable=True)
    solinger_ikke_medlemmer = Column(Integer, nullable=True)
    totalt_inntjent_kr = Column(Float, nullable=True)
    inntjent_medlemmer_kr = Column(Float, nullable=True)
    inntjent_ikke_medlemmer_kr = Column(Float, nullable=True)
    source = Column(String, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class Sun2ImportRun(Base):
    __tablename__ = "sun2_import_runs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    collector_id = Column(String, index=True, nullable=True)
    source = Column(String, nullable=True)
    ok = Column(Boolean, nullable=True)
    stat_date = Column(Date, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    rows_count = Column(Integer, nullable=True)
    inserted_count = Column(Integer, nullable=True)
    updated_count = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class AccessKey(Base):
    __tablename__ = "access_keys"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    key_hash = Column(String, unique=True, index=True, nullable=False)
    key_prefix = Column(String, index=True, nullable=False)
    key_plaintext = Column(String, nullable=True)
    role = Column(String, default="viewer", index=True)
    is_master = Column(Boolean, default=False, index=True)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_seen_at = Column(DateTime, nullable=True)
    last_ip = Column(String, nullable=True)
    last_user_agent = Column(Text, nullable=True)
    uses_count = Column(Integer, default=0)


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    access_key_id = Column(Integer, nullable=True, index=True)
    key_name = Column(String, nullable=True)
    key_prefix = Column(String, nullable=True, index=True)
    path = Column(Text, nullable=False)
    method = Column(String, nullable=False)
    ip = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, default=True, index=True)
    reason = Column(String, nullable=True)


class ControlConfig(Base):
    __tablename__ = "control_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    values = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_by = Column(String, nullable=True)


class ControlConfigHistory(Base):
    __tablename__ = "control_config_history"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String, index=True, nullable=False)
    version = Column(Integer, nullable=False)
    values = Column(JSON, nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, index=True)
    changed_by = Column(String, nullable=True)
    reason = Column(Text, nullable=True)


class LegacyLogIn(BaseModel):
    temperature: float
    humidity: float
    timestamp: datetime
    source: str


class EventDataIn(BaseModel):
    system: str
    event_type: str = "status"
    timestamp: Optional[datetime] = None
    action: Optional[str] = None
    device_key: Optional[str] = None
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    mode: Optional[str] = None
    reason: Optional[str] = None
    source: Optional[str] = None
    bucket_start: Optional[datetime] = None

    temp_1etg: Optional[float] = None
    temp_2etg: Optional[float] = None
    temp_vip: Optional[float] = None
    temp_ute: Optional[float] = None
    temp_ute_netatmo: Optional[float] = None
    temp_yr: Optional[float] = None
    temp_loft: Optional[float] = None
    temp_passiv: Optional[float] = None
    temp_luftinntak: Optional[float] = None
    temp_min_inne: Optional[float] = None
    temp_avg_inne: Optional[float] = None
    temp_max_inne: Optional[float] = None
    lux: Optional[float] = None
    weather_type: Optional[str] = None
    weather_symbol: Optional[str] = None
    weather_text: Optional[str] = None
    yr_weather: Optional[str] = None
    yr_symbol: Optional[str] = None
    diff_w: Optional[float] = None
    power_w: Optional[float] = None
    energy_kwh: Optional[float] = None
    value: Optional[float] = None
    estimated_sunbeds: Optional[int] = None

    fan_vip: Optional[bool] = None
    fan_2etg: Optional[bool] = None
    fan_tak: Optional[bool] = None
    light_lyslist: Optional[bool] = None
    light_reklame: Optional[bool] = None
    light_spot_glass_275: Optional[bool] = None
    light_spot_glass_299: Optional[bool] = None
    light_spot_inngang: Optional[bool] = None
    light_parkering: Optional[bool] = None
    afterrun_active: Optional[bool] = None
    heat_need: Optional[bool] = None
    cool_need: Optional[bool] = None
    open_time: Optional[bool] = None
    pre_cooling: Optional[bool] = None
    exhaust_time_allowed: Optional[bool] = None
    state: Optional[bool] = None

    values: Dict[str, Any] = Field(default_factory=dict)
    extra: Dict[str, Any] = Field(default_factory=dict)


class RoborockIngestIn(BaseModel):
    source: str = "Roborock_logger"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    message: Optional[str] = None
    robots: list[Dict[str, Any]] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class Sun2RoomStatIn(BaseModel):
    stat_date: date
    room: str
    room_key: Optional[str] = None
    source_room_name: Optional[str] = None
    total_soletid_minutter: Optional[float] = None
    totalt_antall_solinger: Optional[int] = None
    solinger_medlemmer: Optional[int] = None
    solinger_ikke_medlemmer: Optional[int] = None
    totalt_inntjent_kr: Optional[float] = None
    inntjent_medlemmer_kr: Optional[float] = None
    inntjent_ikke_medlemmer_kr: Optional[float] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class Sun2RoomStatsIngestIn(BaseModel):
    source: str = "sun2_importer"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    stat_date: Optional[date] = None
    source_file: Optional[str] = None
    message: Optional[str] = None
    rows: list[Sun2RoomStatIn] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


LIGHT_COLUMNS = [
    "id", "timestamp", "event_type", "action", "device_key", "device_id", "device_name",
    "mode", "reason", "source", "lux", "value", "state", "extra",
]

LIGHT_SAMPLE_COLUMNS = [
    "id", "timestamp", "bucket_start", "mode", "source", "lux", "value",
    "light_lyslist", "light_reklame", "light_spot_glass_275", "light_spot_glass_299",
    "light_spot_inngang", "light_parkering", "weather_symbol", "weather_text", "extra",
]

VENT_COLUMNS = [
    "id", "timestamp", "event_type", "action", "device_key", "device_id", "device_name",
    "mode", "reason", "source", "value", "state", "temp_1etg", "temp_2etg",
    "temp_vip", "temp_ute", "temp_loft", "temp_passiv", "temp_luftinntak",
    "diff_w", "power_w", "energy_kwh", "fan_vip", "fan_2etg", "fan_tak", "extra",
]

GENERIC_COLUMNS = [
    "id", "timestamp", "system", "event_type", "action", "device_key", "device_id",
    "device_name", "mode", "reason", "source", "lux", "value", "state", "extra",
]

VENT_SAMPLE_COLUMNS = [
    "id", "timestamp", "bucket_start", "mode", "source", "temp_1etg", "temp_2etg",
    "temp_vip", "temp_ute", "temp_ute_netatmo", "temp_yr", "temp_loft", "temp_passiv",
    "temp_luftinntak", "temp_min_inne", "temp_avg_inne", "temp_max_inne", "diff_w",
    "estimated_sunbeds", "afterrun_active", "heat_need", "cool_need", "open_time",
    "pre_cooling", "exhaust_time_allowed", "fan_vip", "fan_2etg", "fan_tak", "extra",
]

YR_SAMPLE_COLUMNS = [
    "id", "timestamp", "bucket_start", "source", "api_updated_at", "last_modified",
    "expires_at", "next_fetch_after", "age_seconds", "forecast_time", "symbol_code",
    "weather_text", "air_temperature", "relative_humidity", "wind_speed",
    "wind_from_direction", "cloud_area_fraction", "fog_area_fraction",
    "dew_point_temperature", "air_pressure_at_sea_level", "precipitation_next_1h",
    "precipitation_next_6h", "temp_1h", "temp_3h", "temp_6h", "temp_12h",
    "temp_24h", "symbol_1h", "symbol_3h", "symbol_6h", "symbol_12h",
    "symbol_24h", "temp_min_next_6h", "temp_max_next_6h", "extra",
]

ROBOROCK_ROBOT_COLUMNS = [
    "id", "duid", "name", "product", "model", "firmware", "protocol_version",
    "serial_number", "local_ip", "cloud_online", "shared", "time_zone_id",
    "last_seen_at", "last_cloud_at", "last_local_at", "last_status_at",
    "last_map_at", "last_error", "capabilities", "extra",
]

ROBOROCK_STATUS_COLUMNS = [
    "id", "robot_duid", "timestamp", "source", "state_code", "state_name",
    "battery", "error_code", "in_cleaning", "in_returning", "clean_time_seconds",
    "clean_area_m2", "fan_power", "water_box_mode", "mop_mode", "dock_type",
    "charge_status", "clean_percent", "local_ip", "rssi", "raw",
]

ROBOROCK_JOB_COLUMNS = [
    "id", "robot_duid", "record_id", "begin_at", "end_at", "duration_seconds",
    "duration_minutes", "area_m2", "cleaned_area_m2", "complete", "error_code",
    "start_type", "clean_type", "finish_reason", "dust_collection_status",
    "avoid_count", "wash_count", "clean_times", "updated_at", "raw",
]

ROBOROCK_SCHEDULE_COLUMNS = [
    "id", "robot_duid", "schedule_id", "cron", "enabled", "repeated", "segments",
    "fan_power", "mop_mode", "water_box_mode", "repeat", "updated_at", "raw",
]

ROBOROCK_MAP_COLUMNS = [
    "id", "robot_duid", "timestamp", "image_bytes", "raw_bytes", "image_width",
    "image_height", "rooms", "zones", "charger", "vacuum_position", "raw",
]

SUN2_ROOM_COLUMNS = [
    "id", "stat_date", "room_key", "room", "source_room_name", "total_soletid_minutter",
    "totalt_antall_solinger", "solinger_medlemmer", "solinger_ikke_medlemmer",
    "totalt_inntjent_kr", "inntjent_medlemmer_kr", "inntjent_ikke_medlemmer_kr",
    "source", "source_file", "imported_at", "raw",
]

SUN2_IMPORT_COLUMNS = [
    "id", "timestamp", "collector_id", "source", "ok", "stat_date", "source_file",
    "rows_count", "inserted_count", "updated_count", "message", "raw",
]


SUN2_SUM_FIELDS = [
    "total_soletid_minutter",
    "totalt_antall_solinger",
    "solinger_medlemmer",
    "solinger_ikke_medlemmer",
    "totalt_inntjent_kr",
    "inntjent_medlemmer_kr",
    "inntjent_ikke_medlemmer_kr",
]


def empty_sun2_summary(period: str) -> Dict[str, Any]:
    return {
        "period": period,
        "period_label": period,
        "total_soletid_minutter": 0.0,
        "total_soletid_timer": 0.0,
        "totalt_antall_solinger": 0,
        "solinger_medlemmer": 0,
        "solinger_ikke_medlemmer": 0,
        "totalt_inntjent_kr": 0.0,
        "inntjent_medlemmer_kr": 0.0,
        "inntjent_ikke_medlemmer_kr": 0.0,
        "days": set(),
        "rooms": set(),
    }


def add_sun2_row_to_summary(summary: Dict[str, Any], row: Any) -> None:
    for field in SUN2_SUM_FIELDS:
        summary[field] += getattr(row, field) or 0
    if row.stat_date:
        summary["days"].add(row.stat_date)
    if row.room:
        summary["rooms"].add(row.room)


def finalize_sun2_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(summary)
    summary["total_soletid_timer"] = summary["total_soletid_minutter"] / 60
    summary["days_count"] = len(summary.pop("days", []))
    summary["rooms_count"] = len(summary.pop("rooms", []))
    return summary


def build_sun2_summaries(rows: list[Any]) -> Dict[str, Any]:
    daily: Dict[str, Dict[str, Any]] = {}
    monthly: Dict[str, Dict[str, Any]] = {}
    yearly: Dict[str, Dict[str, Any]] = {}
    total = empty_sun2_summary("Totalt")
    first_date = None
    last_date = None

    for row in rows:
        if not row.stat_date:
            continue
        first_date = row.stat_date if first_date is None else min(first_date, row.stat_date)
        last_date = row.stat_date if last_date is None else max(last_date, row.stat_date)
        day_key = row.stat_date.isoformat()
        month_key = row.stat_date.strftime("%Y-%m")
        year_key = str(row.stat_date.year)
        daily.setdefault(day_key, empty_sun2_summary(day_key))
        monthly.setdefault(month_key, empty_sun2_summary(month_key))
        yearly.setdefault(year_key, empty_sun2_summary(year_key))
        daily[day_key]["period_label"] = row.stat_date.strftime("%d.%m.%Y")
        add_sun2_row_to_summary(daily[day_key], row)
        add_sun2_row_to_summary(monthly[month_key], row)
        add_sun2_row_to_summary(yearly[year_key], row)
        add_sun2_row_to_summary(total, row)

    daily_items = [finalize_sun2_summary(daily[key]) for key in sorted(daily, reverse=True)]
    monthly_items = [finalize_sun2_summary(monthly[key]) for key in sorted(monthly, reverse=True)]
    yearly_items = [finalize_sun2_summary(yearly[key]) for key in sorted(yearly, reverse=True)]
    top_sort = lambda item: (
        item["totalt_inntjent_kr"],
        item["totalt_antall_solinger"],
        item["total_soletid_minutter"],
    )

    return {
        "daily": daily_items,
        "monthly": monthly_items,
        "yearly": yearly_items,
        "top_days": sorted(daily_items, key=top_sort, reverse=True)[:10],
        "top_months": sorted(monthly_items, key=top_sort, reverse=True)[:10],
        "total": finalize_sun2_summary(total),
        "first_date": first_date,
        "last_date": last_date,
    }


LIGHT_TIMELINE_DEVICES = [
    {"key": "lyslist", "name": "Lyslist dekor", "sample_attr": "light_lyslist", "legacy_ids": [425]},
    {"key": "reklame", "name": "Reklameplakater", "sample_attr": "light_reklame", "legacy_ids": [427]},
    {"key": "spot_glass_275", "name": "Spot foran glassvegg", "sample_attr": "light_spot_glass_275", "legacy_ids": [275]},
    {"key": "spot_glass_299", "name": "Spot foran massasje", "sample_attr": "light_spot_glass_299", "legacy_ids": [299]},
    {"key": "spot_inngang", "name": "6xspot over inngang", "sample_attr": "light_spot_inngang", "legacy_ids": [424]},
    {"key": "parkering", "name": "Parkeringslys/gatelys", "sample_attr": "light_parkering", "legacy_ids": [440]},
]

VENT_TIMELINE_DEVICES = [
    {"key": "vip_intake", "name": "Innluft VIP", "sample_attr": "fan_vip", "legacy_ids": [130]},
    {"key": "floor_intake", "name": "Innluft 2.etg", "sample_attr": "fan_2etg", "legacy_ids": [160]},
    {"key": "roof_exhaust", "name": "Avtrekk tak/loft", "sample_attr": "fan_tak", "legacy_ids": [134]},
]

DAY_ZOOM_OPTIONS = [
    {"key": "all", "label": "Hele døgnet", "start_hour": 0, "end_hour": 24, "ticks": [0, 6, 12, 18, 24]},
    {"key": "night", "label": "Natt 00-06", "start_hour": 0, "end_hour": 6, "ticks": [0, 2, 4, 6]},
    {"key": "day", "label": "Dag 06-24", "start_hour": 6, "end_hour": 24, "ticks": [6, 12, 18, 24]},
]

WEATHER_LABELS = {
    "clearsky": "Klarvær",
    "clearsky_day": "Klarvær",
    "clearsky_night": "Klarvær",
    "clearsky_polartwilight": "Klarvær",
    "fair": "Lettskyet",
    "fair_day": "Lettskyet",
    "fair_night": "Lettskyet",
    "fair_polartwilight": "Lettskyet",
    "partlycloudy": "Delvis skyet",
    "partlycloudy_day": "Delvis skyet",
    "partlycloudy_night": "Delvis skyet",
    "partlycloudy_polartwilight": "Delvis skyet",
    "cloudy": "Skyet",
    "fog": "Tåke",
    "lightrain": "Lett regn",
    "rain": "Regn",
    "heavyrain": "Kraftig regn",
    "lightsnow": "Lett snø",
    "snow": "Snø",
    "heavysnow": "Kraftig snø",
    "sleet": "Sludd",
    "lightsleet": "Lett sludd",
    "thunderstorm": "Torden",
    "rainshowers": "Regnbyger",
    "lightrainshowers": "Lette regnbyger",
    "heavyrainshowers": "Kraftige regnbyger",
    "snowshowers": "Snøbyger",
    "lightsnowshowers": "Lette snøbyger",
    "heavysnowshowers": "Kraftige snøbyger",
}

STARTUP_COLUMNS = {
    "utelys_events": [
        ("device_key", "VARCHAR"),
    ],
    "ventilasjon_events": [
        ("device_key", "VARCHAR"),
    ],
    "event_data": [
        ("device_key", "VARCHAR"),
    ],
    "utelys_samples": [
        ("light_spot_glass_275", "BOOLEAN"),
        ("light_spot_glass_299", "BOOLEAN"),
        ("weather_symbol", "VARCHAR"),
        ("weather_text", "VARCHAR"),
    ],
    "ventilasjon_samples": [
        ("temp_ute_netatmo", "DOUBLE PRECISION"),
        ("temp_yr", "DOUBLE PRECISION"),
        ("temp_min_inne", "DOUBLE PRECISION"),
        ("temp_avg_inne", "DOUBLE PRECISION"),
        ("temp_max_inne", "DOUBLE PRECISION"),
        ("estimated_sunbeds", "INTEGER"),
        ("afterrun_active", "BOOLEAN"),
        ("heat_need", "BOOLEAN"),
        ("cool_need", "BOOLEAN"),
        ("open_time", "BOOLEAN"),
        ("pre_cooling", "BOOLEAN"),
        ("exhaust_time_allowed", "BOOLEAN"),
    ],
    "access_keys": [
        ("key_plaintext", "VARCHAR"),
        ("role", "VARCHAR"),
    ],
    "yr_forecast_samples": [
        ("api_updated_at", "TIMESTAMP"),
        ("last_modified", "TIMESTAMP"),
        ("expires_at", "TIMESTAMP"),
        ("next_fetch_after", "TIMESTAMP"),
        ("age_seconds", "INTEGER"),
    ],
    "roborock_robots": [
        ("serial_number", "VARCHAR"),
        ("last_map_at", "TIMESTAMP"),
    ],
    "sun2_room_daily_stats": [
        ("room_key", "VARCHAR"),
        ("source_room_name", "VARCHAR"),
    ],
}


CONFIG_DEFINITIONS = {
    "lights": {
        "title": "Lysstyring",
        "subtitle": "Terskler, driftstid og forklaring for utelys",
        "theme": "theme-light",
        "settings_path": "/lys/innstillinger",
        "api_path": "/api/config/lights",
        "groups": [
            {
                "title": "Felles drift",
                "description": "Gjelder alle lys unntatt parkeringslys der feltet sier at åpningstid ignoreres.",
                "fields": [
                    {"key": "open_from", "label": "Start før åpning", "type": "time", "default": "06:45", "unit": "", "help": "Tidligste tidspunkt lys som følger åpningstid kan være på."},
                    {"key": "close_at", "label": "Normal av-tid", "type": "time", "default": "23:00", "unit": "", "help": "Standard av-tid for lys som følger åpningstid."},
                    {"key": "entrance_close_at", "label": "Inngang av-tid", "type": "time", "default": "23:20", "unit": "", "help": "6xspot over inngang kan stå litt lenger enn øvrige fasadelys."},
                    {"key": "decision_delay_seconds", "label": "Bekreftelsestid", "type": "int", "default": 120, "unit": "sek", "help": "Lux må bekreftes etter denne forsinkelsen før lys endres."},
                    {"key": "config_poll_minutes", "label": "HC3 henter config", "type": "int", "default": 5, "unit": "min", "help": "Hvor ofte HC3 bør kontrollere om versjon er endret."},
                ],
            },
            {
                "title": "Luxgrenser",
                "description": "På-grense er lav lux. Av-grense er høyere lux for å gi hysterese og unngå flimring.",
                "fields": [
                    {"key": "lyslist_on_lux", "label": "Lyslist på under", "type": "float", "default": 1000, "unit": "lux", "help": "Dekorlys på fasade."},
                    {"key": "lyslist_off_lux", "label": "Lyslist av over", "type": "float", "default": 1500, "unit": "lux", "help": "Må være høyere enn på-grensen."},
                    {"key": "reklame_on_lux", "label": "Reklame på under", "type": "float", "default": 500, "unit": "lux", "help": "Reklameplakater på tegelfasade."},
                    {"key": "reklame_off_lux", "label": "Reklame av over", "type": "float", "default": 700, "unit": "lux", "help": "Må være høyere enn på-grensen."},
                    {"key": "spot_glass_on_lux", "label": "Spot foran på under", "type": "float", "default": 1500, "unit": "lux", "help": "Spot 275 og 299 foran glassveggen."},
                    {"key": "spot_glass_off_lux", "label": "Spot foran av over", "type": "float", "default": 2000, "unit": "lux", "help": "Må være høyere enn på-grensen."},
                    {"key": "spot_inngang_on_lux", "label": "6xspot inngang på under", "type": "float", "default": 100, "unit": "lux", "help": "Behovsstyrt inngangslys."},
                    {"key": "spot_inngang_off_lux", "label": "6xspot inngang av over", "type": "float", "default": 150, "unit": "lux", "help": "Må være høyere enn på-grensen."},
                    {"key": "parkering_on_lux", "label": "Parkering på under", "type": "float", "default": 50, "unit": "lux", "help": "Parkeringslys/gatelys."},
                    {"key": "parkering_off_lux", "label": "Parkering av over", "type": "float", "default": 80, "unit": "lux", "help": "Parkeringslys følger ikke åpningstid."},
                ],
            },
        ],
    },
    "ventilation": {
        "title": "Ventilasjonsstyring",
        "subtitle": "Temperaturgrenser, driftstid og forklaring for vifter",
        "theme": "theme-vent",
        "settings_path": "/ventilasjon/innstillinger",
        "api_path": "/api/config/ventilation",
        "groups": [
            {
                "title": "Drift og sikkerhet",
                "description": "Disse grensene hindrer trekk, undertrykk og unødvendig varmetap.",
                "fields": [
                    {"key": "open_from", "label": "Åpningstid fra", "type": "time", "default": "07:00", "unit": "", "help": "Normal start for ventilasjonslogikk."},
                    {"key": "close_at", "label": "Stenging", "type": "time", "default": "23:00", "unit": "", "help": "Normal stengetid."},
                    {"key": "pre_cooling_from", "label": "Forkjøling fra", "type": "time", "default": "05:30", "unit": "", "help": "Kan brukes på varme dager når ute fortsatt er kaldt."},
                    {"key": "exhaust_stop_before_close_minutes", "label": "Stopp avtrekk før stenging", "type": "int", "default": 60, "unit": "min", "help": "Sparer varme mot natten."},
                    {"key": "mechanical_min_outdoor_temp", "label": "Sperr mekanisk under", "type": "float", "default": 7.0, "unit": "°C", "help": "Avtrekk og innluft stoppes når ute er kaldere enn dette."},
                    {"key": "intake_min_outdoor_temp", "label": "Innluft minimum ute", "type": "float", "default": 10.0, "unit": "°C", "help": "Hindrer kald innblåsing."},
                ],
            },
            {
                "title": "Innluft",
                "description": "Innluft skal bare gå når ute faktisk hjelper, og alltid gi luft inn dersom avtrekk er aktivt.",
                "fields": [
                    {"key": "vip_start_temp", "label": "VIP innluft start", "type": "float", "default": 23.8, "unit": "°C", "help": "VIP-viften vurderer primært VIP-temperatur."},
                    {"key": "vip_stop_temp", "label": "VIP innluft stopp", "type": "float", "default": 23.2, "unit": "°C", "help": "Lavere enn start for hysterese."},
                    {"key": "floor_start_temp", "label": "1./2.etg innluft start", "type": "float", "default": 23.8, "unit": "°C", "help": "2.etg-viften vurderer 1.etg og 2.etg."},
                    {"key": "floor_stop_temp", "label": "1./2.etg innluft stopp", "type": "float", "default": 23.2, "unit": "°C", "help": "Lavere enn start for hysterese."},
                    {"key": "outdoor_cooler_delta", "label": "Ute må være kaldere", "type": "float", "default": 1.5, "unit": "°C", "help": "Ute må være minst så mye kaldere enn sonen."},
                    {"key": "max_indoor_heat_need_temp", "label": "Varmebehov under", "type": "float", "default": 21.5, "unit": "°C", "help": "Under denne temperaturen unngår vi kjølende ventilasjon."},
                ],
            },
            {
                "title": "Avtrekk tak/loft",
                "description": "Avtrekk skal ikke gå bare fordi solsenger er i bruk hvis lokalet trenger varme.",
                "fields": [
                    {"key": "loft_exhaust_start_temp", "label": "Takvifte start loft", "type": "float", "default": 30.0, "unit": "°C", "help": "Starter når loftet er varmt nok og ute ikke er for kaldt."},
                    {"key": "loft_exhaust_stop_temp", "label": "Takvifte stopp loft", "type": "float", "default": 28.0, "unit": "°C", "help": "Stopper lavere enn start for hysterese."},
                    {"key": "indoor_allow_exhaust_temp", "label": "Avtrekk tillatt når inne over", "type": "float", "default": 25.0, "unit": "°C", "help": "Hindrer at varme blåses ut når lokalet er kaldt."},
                    {"key": "sunbed_power_1_threshold_w", "label": "Antatt 1 solseng over", "type": "int", "default": 4000, "unit": "W", "help": "Differanse mellom total og målt øvrig forbruk."},
                    {"key": "sunbed_power_2_threshold_w", "label": "Antatt 2 solsenger over", "type": "int", "default": 12000, "unit": "W", "help": "Brukes for vurdering og logging."},
                    {"key": "afterrun_minutes", "label": "Ettergang", "type": "int", "default": 20, "unit": "min", "help": "Hvor lenge vifter kan gå etter siste tydelige varmebelastning."},
                ],
            },
        ],
    },
}


CONTROL_DEVICES = {
    "lights": {
        "lux_sensor": {"key": "lux_ute", "name": "Luxsensor ute", "role": "sensor"},
        "groups": [
            {
                "key": "lyslist",
                "name": "Lyslist fasade",
                "on_lux_key": "lyslist_on_lux",
                "off_lux_key": "lyslist_off_lux",
                "time_from_key": "open_from",
                "time_to_key": "close_at",
                "follows_opening_hours": True,
            },
            {
                "key": "reklame",
                "name": "Reklameplakater tegelfasade",
                "on_lux_key": "reklame_on_lux",
                "off_lux_key": "reklame_off_lux",
                "time_from_key": "open_from",
                "time_to_key": "close_at",
                "follows_opening_hours": True,
            },
            {
                "key": "spot_glass",
                "name": "Spot foran glassvegg",
                "on_lux_key": "spot_glass_on_lux",
                "off_lux_key": "spot_glass_off_lux",
                "time_from_key": "open_from",
                "time_to_key": "close_at",
                "follows_opening_hours": True,
            },
            {
                "key": "spot_inngang",
                "name": "6xspot over inngang",
                "on_lux_key": "spot_inngang_on_lux",
                "off_lux_key": "spot_inngang_off_lux",
                "time_from_key": "open_from",
                "time_to_key": "entrance_close_at",
                "follows_opening_hours": True,
            },
            {
                "key": "parkering",
                "name": "Parkeringslys",
                "on_lux_key": "parkering_on_lux",
                "off_lux_key": "parkering_off_lux",
                "time_from_key": None,
                "time_to_key": None,
                "follows_opening_hours": False,
            },
        ],
    },
    "ventilation": {
        "sensors": {
            "outdoor_temp": {"key": "outdoor_temp", "name": "Utetemperatur"},
            "netatmo_main": {"key": "netatmo_main", "name": "Netatmo hovedenhet"},
            "passive_intake": {"name": "Pass innluft"},
        },
        "fans": [
            {"key": "vip_intake", "name": "Innluft VIP", "zone": "VIP"},
            {"key": "floor_intake", "name": "Innluft 1./2.etg", "zone": "1.etg/2.etg"},
            {"key": "roof_exhaust", "name": "Takvifte avtrekk", "zone": "Loft"},
        ],
    },
}


def config_definition(key: str) -> Optional[Dict[str, Any]]:
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


def value_from_payload(data: EventDataIn, key: str):
    explicit = getattr(data, key)
    if explicit is not None:
        return explicit
    return data.values.get(key)


def json_value(value):
    if isinstance(value, (dict, list)):
        import json

        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def repair_mojibake(value: Any) -> Any:
    if not isinstance(value, str) or ("Ã" not in value and "Â" not in value):
        return value
    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value


def room_key_from_name(value: Any) -> Optional[str]:
    text = repair_mojibake(value)
    if not isinstance(text, str):
        return None
    match = re.search(r"\brom\s*0*(\d+)\b", text, re.IGNORECASE)
    if not match:
        return None
    return f"rom_{int(match.group(1)):02d}"


def bool_value(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "ja"}:
            return True
        if normalized in {"0", "false", "no", "off", "nei"}:
            return False
    return None


def int_value(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def float_value(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def timestamp_value(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(value)
    if isinstance(value, str):
        parsed = parse_datetime(value)
        if parsed:
            return parsed
        try:
            return datetime.utcfromtimestamp(int(value))
        except (TypeError, ValueError):
            return None
    return None


def area_m2_from_payload(value: Any) -> Optional[float]:
    number = float_value(value)
    if number is None:
        return None
    if number > 100000:
        return round(number / 1_000_000, 2)
    return number


def first_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    if isinstance(value, dict):
        return value
    return {}


def roborock_schedule_params(schedule: Dict[str, Any]) -> Dict[str, Any]:
    params = (((schedule.get("param") or {}).get("params")) or [])
    return params[0] if params and isinstance(params[0], dict) else {}


def hash_access_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_username(value: str) -> str:
    return value.strip().casefold()


def credential_hash(username: str, password: str) -> str:
    return hash_access_key(normalize_username(username) + "\0" + password)


def credential_prefix(username: str, password: str) -> str:
    return "key_" + credential_hash(username, password)[:8]


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def presented_credentials(request: Request) -> tuple[Optional[str], Optional[str]]:
    username = (
        request.query_params.get("username")
        or request.headers.get("x-access-username")
        or request.cookies.get(AUTH_USER_COOKIE_NAME)
    )
    password = (
        request.query_params.get("password")
        or request.headers.get("x-access-password")
        or request.cookies.get(AUTH_COOKIE_NAME)
    )
    return username, password


def wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept or "*/*" in accept


def is_public_request(request: Request) -> bool:
    path = request.url.path
    if path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
        return True
    if request.method == "GET" and (path == "/api/config" or path.startswith("/api/config/")):
        return True
    return request.method == "POST" and path in {"/events", "/log"}


async def parse_form_body(request: Request) -> Dict[str, str]:
    raw = (await request.body()).decode("utf-8")
    parsed = parse_qs(raw, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


async def log_access_attempt(
    request: Request,
    success: bool,
    reason: str,
    access_key: Optional[AccessKey] = None,
    attempted_username: Optional[str] = None,
):
    async with async_session() as session:
        session.add(
            AccessLog(
                access_key_id=access_key.id if access_key else None,
                key_name=access_key.name if access_key else normalize_username(attempted_username or "") or None,
                key_prefix=access_key.key_prefix if access_key else None,
                path=request.url.path,
                method=request.method,
                ip=client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
                success=success,
                reason=reason,
            )
        )
        if access_key and success:
            await session.execute(
                update(AccessKey)
                .where(AccessKey.id == access_key.id)
                .values(
                    last_seen_at=datetime.utcnow(),
                    last_ip=client_ip(request),
                    last_user_agent=request.headers.get("user-agent", ""),
                    uses_count=AccessKey.uses_count + 1,
                )
            )
        await session.commit()


async def find_access_key(username: Optional[str], password: Optional[str]) -> Optional[AccessKey]:
    if not username or not password:
        return None
    normalized_username = normalize_username(username)
    if normalized_username == "master":
        hashed = hash_access_key(password)
    else:
        hashed = credential_hash(normalized_username, password)
    async with async_session() as session:
        result = await session.execute(
            select(AccessKey)
            .where(AccessKey.name == normalized_username)
            .where(AccessKey.key_hash == hashed)
            .where(AccessKey.active == True)
        )
        return result.scalars().first()


def require_master(request: Request):
    if not getattr(request.state, "auth_is_master", False):
        return JSONResponse({"detail": "Masterbruker kreves"}, status_code=403)
    return None


def access_role(access_key: Optional[AccessKey]) -> str:
    if not access_key:
        return "viewer"
    if access_key.is_master:
        return "master"
    role = (access_key.role or "viewer").strip().lower()
    if role not in ["viewer", "settings"]:
        return "viewer"
    return role


def access_role_label(role: Optional[str], is_master: bool = False) -> str:
    if is_master or role == "master":
        return "Master"
    if role == "settings":
        return "Innstillinger"
    return "Vanlig"


def require_settings_access(request: Request):
    if not getattr(request.state, "auth_can_settings", False):
        return JSONResponse({"detail": "Tilgang til innstillinger kreves"}, status_code=403)
    return None


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def sample_bucket(value: Optional[datetime]) -> datetime:
    stamp = value or datetime.utcnow()
    minute = (stamp.minute // 5) * 5
    return stamp.replace(minute=minute, second=0, microsecond=0)


def parse_day(value: Optional[str]) -> date:
    if value:
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return datetime.now(LOCAL_TZ).date()


def parse_config_value(raw: Optional[str], field: Dict[str, Any]):
    field_type = field.get("type")
    if field_type == "bool":
        return raw in {"on", "true", "1", "yes"}
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


def time_minutes(value: str) -> Optional[int]:
    try:
        hour, minute = str(value).split(":", 1)
        return int(hour) * 60 + int(minute)
    except (TypeError, ValueError):
        return None


def validate_config_values(key: str, values: Dict[str, Any]) -> list[str]:
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
        "Hvis avtrekk er aktivt skal minst én innluftsvifte være tilgjengelig, så vi unngår unødvendig undertrykk.",
    ]


def config_rules(key: str, values: Dict[str, Any]) -> list[str]:
    if key == "lights":
        return light_rules(values)
    if key == "ventilation":
        return ventilation_rules(values)
    return []


def config_summary_rows(key: str, values: Dict[str, Any]) -> list[Dict[str, str]]:
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


def day_zoom_config(value: Optional[str]):
    for option in DAY_ZOOM_OPTIONS:
        if option["key"] == value:
            return option
    return DAY_ZOOM_OPTIONS[0]


def day_zoom_window(selected_day: date, zoom_key: Optional[str]):
    config = day_zoom_config(zoom_key)
    day_start = datetime.combine(selected_day, time.min)
    window_start = day_start + timedelta(hours=config["start_hour"])
    window_end = day_start + timedelta(hours=config["end_hour"])
    ticks = [
        {
            "label": f"{hour:02d}" if hour < 24 else "24",
            "left": percent_between(day_start + timedelta(hours=hour), window_start, window_end),
        }
        for hour in config["ticks"]
    ]
    return config, window_start, window_end, ticks


def local_now_naive() -> datetime:
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)


def display_action(action: Optional[str]) -> str:
    if action == "PAA":
        return "PÅ"
    return action or ""


def clean_display_text(value: Optional[str]) -> str:
    return (value or "").replace("innbl?sing", "innblåsing").replace("innblasing", "innblåsing").replace("KJ?LING", "KJØLING").replace("KJOLING", "KJØLING").replace("kj?lebehov", "kjølebehov").replace("kjolebehov", "kjølebehov")


def state_from_event(row):
    if row.action == "PAA":
        return True
    if row.action == "AV":
        return False
    if row.state is not None:
        return bool(row.state)
    return None


def percent_between(value: datetime, start: datetime, end: datetime) -> float:
    total = (end - start).total_seconds()
    if total <= 0:
        return 0
    seconds = (value - start).total_seconds()
    return round(max(0, min(100, seconds / total * 100)), 3)


def span_width(start_value: datetime, end_value: datetime, day_start: datetime, day_end: datetime) -> float:
    return round(max(0, percent_between(end_value, day_start, day_end) - percent_between(start_value, day_start, day_end)), 3)


def add_segment(segments, start_value: datetime, end_value: datetime):
    if end_value <= start_value:
        return
    if segments and segments[-1]["end_dt"] == start_value:
        segments[-1]["end_dt"] = end_value
    else:
        segments.append({"start_dt": start_value, "end_dt": end_value})


def display_segments(raw_segments, day_start: datetime, day_end: datetime):
    return [
        {
            "left": percent_between(segment["start_dt"], day_start, day_end),
            "width": span_width(segment["start_dt"], segment["end_dt"], day_start, day_end),
            "start": segment["start_dt"].strftime("%H:%M"),
            "end": segment["end_dt"].strftime("%H:%M"),
        }
        for segment in raw_segments
    ]


def total_from_segments(segments) -> str:
    total_minutes = int(round(sum((segment["end_dt"] - segment["start_dt"]).total_seconds() / 60 for segment in segments)))
    return f"{total_minutes // 60}t {total_minutes % 60}m"


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


def minutes_since(value: Optional[datetime], now_value: Optional[datetime] = None) -> Optional[int]:
    if not value:
        return None
    now_value = now_value or local_now_naive()
    delta = now_value - value
    return max(0, int(delta.total_seconds() // 60))


def age_label(minutes: Optional[int]) -> str:
    if minutes is None:
        return "Ingen data"
    if minutes < 1:
        return "Akkurat nå"
    if minutes < 60:
        return f"{minutes} min siden"
    hours = minutes // 60
    rest = minutes % 60
    if hours < 24:
        return f"{hours}t {rest}m siden"
    days = hours // 24
    return f"{days}d siden"


def average_value(values):
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def latest_timestamp_from(*rows):
    timestamps = [row.timestamp for row in rows if row is not None and row.timestamp is not None]
    if not timestamps:
        return None
    return max(timestamps)


def nested_extra_value(value, keys):
    if value is None:
        return None
    if isinstance(value, dict):
        for key in keys:
            found = value.get(key)
            if found not in (None, ""):
                if isinstance(found, (dict, list)):
                    nested = nested_extra_value(found, keys)
                    if nested not in (None, ""):
                        return nested
                    continue
                return found
        for child in value.values():
            found = nested_extra_value(child, keys)
            if found not in (None, ""):
                return found
    elif isinstance(value, list):
        for child in value:
            found = nested_extra_value(child, keys)
            if found not in (None, ""):
                return found
    return None


def weather_label(value) -> Optional[str]:
    if value in (None, ""):
        return None
    raw = str(value).strip()
    key = raw.lower().replace("-", "_")
    if key in WEATHER_LABELS:
        return WEATHER_LABELS[key]
    for suffix in ("_day", "_night", "_polartwilight"):
        if key.endswith(suffix) and key[: -len(suffix)] in WEATHER_LABELS:
            return WEATHER_LABELS[key[: -len(suffix)]]
    cleaned = raw.replace("_", " ").replace("-", " ")
    return cleaned[:1].upper() + cleaned[1:] if cleaned else None


def weather_from_rows(*rows) -> Optional[str]:
    keys = [
        "weather_text",
        "weather_type",
        "yr_weather",
        "weather",
        "condition_text",
        "condition",
        "summary",
        "symbol_code",
        "weather_symbol",
        "yr_symbol",
        "next_1_hours_symbol_code",
    ]
    for row in rows:
        if row is None:
            continue
        for attr in ("weather_text", "weather_type", "yr_weather", "weather_symbol", "yr_symbol"):
            label = weather_label(getattr(row, attr, None))
            if label:
                return label
        extra = getattr(row, "extra", None)
        found = nested_extra_value(extra, keys)
        label = weather_label(found)
        if label:
            return label
    return None


def met_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo:
        stamp = stamp.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return stamp


def http_header_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        stamp = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if stamp.tzinfo:
        stamp = stamp.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return stamp


def met_age_seconds(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def met_next_fetch_after(forecast: Optional[Dict[str, Any]], now_value: Optional[datetime] = None) -> datetime:
    now_value = now_value or datetime.utcnow()
    expires_at = (forecast or {}).get("expires_at")
    if isinstance(expires_at, datetime) and expires_at > now_value:
        return expires_at + timedelta(minutes=1)
    return now_value + timedelta(minutes=1)


def met_details(entry: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not entry:
        return {}
    return entry.get("data", {}).get("instant", {}).get("details", {}) or {}


def met_period_details(entry: Optional[Dict[str, Any]], period: str) -> Dict[str, Any]:
    if not entry:
        return {}
    return entry.get("data", {}).get(period, {}).get("details", {}) or {}


def met_period_symbol(entry: Optional[Dict[str, Any]]) -> Optional[str]:
    if not entry:
        return None
    data = entry.get("data", {})
    for period in ("next_1_hours", "next_6_hours", "next_12_hours"):
        symbol = data.get(period, {}).get("summary", {}).get("symbol_code")
        if symbol:
            return symbol
    return None


def met_value(details: Dict[str, Any], key: str) -> Optional[float]:
    value = details.get(key)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def met_entry_at(timeseries: list[Dict[str, Any]], base_time: Optional[datetime], hours: int) -> Optional[Dict[str, Any]]:
    if not timeseries or not base_time:
        return None
    target = base_time + timedelta(hours=hours)
    entries = [(met_time(entry.get("time")), entry) for entry in timeseries]
    entries = [(stamp, entry) for stamp, entry in entries if stamp is not None]
    if not entries:
        return None
    future_entries = [(stamp, entry) for stamp, entry in entries if stamp >= target]
    source = future_entries or entries
    return min(source, key=lambda item: abs((item[0] - target).total_seconds()))[1]


def met_forecast_from_payload(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    timeseries = payload.get("properties", {}).get("timeseries", [])
    if not timeseries:
        return None
    meta = payload.get("properties", {}).get("meta", {}) or {}
    current = timeseries[0]
    forecast_time = met_time(current.get("time"))
    details = met_details(current)
    symbol = met_period_symbol(current)
    next_1h = met_period_details(current, "next_1_hours")
    next_6h = met_period_details(current, "next_6_hours")
    forecast: Dict[str, Any] = {
        "symbol": symbol or "",
        "text": weather_label(symbol),
        "api_updated_at": met_time(meta.get("updated_at")),
        "forecast_time": forecast_time,
        "air_temperature": met_value(details, "air_temperature"),
        "relative_humidity": met_value(details, "relative_humidity"),
        "wind_speed": met_value(details, "wind_speed"),
        "wind_from_direction": met_value(details, "wind_from_direction"),
        "cloud_area_fraction": met_value(details, "cloud_area_fraction"),
        "fog_area_fraction": met_value(details, "fog_area_fraction"),
        "dew_point_temperature": met_value(details, "dew_point_temperature"),
        "air_pressure_at_sea_level": met_value(details, "air_pressure_at_sea_level"),
        "precipitation_next_1h": met_value(next_1h, "precipitation_amount"),
        "precipitation_next_6h": met_value(next_6h, "precipitation_amount"),
    }
    for hours in (1, 3, 6, 12, 24):
        entry = met_entry_at(timeseries, forecast_time, hours)
        forecast[f"temp_{hours}h"] = met_value(met_details(entry), "air_temperature")
        forecast[f"symbol_{hours}h"] = met_period_symbol(entry)
    next_6h_values = []
    if forecast_time:
        for entry in timeseries:
            stamp = met_time(entry.get("time"))
            temp = met_value(met_details(entry), "air_temperature")
            if stamp and temp is not None and forecast_time <= stamp <= forecast_time + timedelta(hours=6):
                next_6h_values.append(temp)
    forecast["temp_min_next_6h"] = min(next_6h_values) if next_6h_values else None
    forecast["temp_max_next_6h"] = max(next_6h_values) if next_6h_values else None
    forecast["raw_meta"] = meta
    return forecast if forecast["text"] or forecast["air_temperature"] is not None else None


def fetch_met_weather() -> Optional[Dict[str, Any]]:
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={MET_LAT:.4f}&lon={MET_LON:.4f}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": MET_USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            headers = response.headers
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None
    forecast = met_forecast_from_payload(payload)
    if forecast:
        forecast["last_modified"] = http_header_time(headers.get("Last-Modified"))
        forecast["expires_at"] = http_header_time(headers.get("Expires"))
        forecast["age_seconds"] = met_age_seconds(headers.get("Age"))
        forecast["next_fetch_after"] = met_next_fetch_after(forecast)
    return forecast


async def met_weather_cached() -> Optional[Dict[str, Any]]:
    now_value = datetime.utcnow()
    if MET_WEATHER_CACHE["expires"] > now_value:
        return MET_WEATHER_CACHE["value"]
    value = await asyncio.to_thread(fetch_met_weather)
    MET_WEATHER_CACHE["value"] = value
    MET_WEATHER_CACHE["expires"] = met_next_fetch_after(value, now_value) if value else now_value + timedelta(minutes=5)
    return value


def build_now_status(latest_sample, latest_light_sample, latest_light, latest_yr_sample=None):
    indoor_values = [
        {"label": "1.etg", "value": latest_sample.temp_1etg if latest_sample else None},
        {"label": "2.etg", "value": latest_sample.temp_2etg if latest_sample else None},
        {"label": "VIP", "value": latest_sample.temp_vip if latest_sample else None},
    ]
    outdoor_ute = None
    outdoor_yr = None
    if latest_sample:
        outdoor_ute = latest_sample.temp_ute if latest_sample.temp_ute is not None else latest_sample.temp_ute_netatmo
        outdoor_yr = latest_sample.temp_yr
    outdoor_yr_api = latest_yr_sample.air_temperature if latest_yr_sample else None
    outdoor_values = [
        {"label": "Ute", "value": outdoor_ute},
        {"label": "Yr HC3", "value": outdoor_yr},
        {"label": "Yr API", "value": outdoor_yr_api},
    ]
    lux = None
    if latest_light_sample and latest_light_sample.lux is not None:
        lux = latest_light_sample.lux
    elif latest_light and latest_light.lux is not None:
        lux = latest_light.lux
    timestamp = latest_timestamp_from(latest_sample, latest_light_sample, latest_light, latest_yr_sample)
    weather = weather_from_rows(latest_yr_sample, latest_light_sample, latest_sample, latest_light)
    outdoor_avg_values = [outdoor_ute, outdoor_yr_api if outdoor_yr_api is not None else outdoor_yr]
    weather_card = {
        "text": weather,
        "temperature": latest_yr_sample.air_temperature if latest_yr_sample else None,
        "temp_6h": latest_yr_sample.temp_6h if latest_yr_sample else None,
        "humidity": latest_yr_sample.relative_humidity if latest_yr_sample else None,
        "wind": latest_yr_sample.wind_speed if latest_yr_sample else None,
        "precipitation": latest_yr_sample.precipitation_next_1h if latest_yr_sample else None,
        "clouds": latest_yr_sample.cloud_area_fraction if latest_yr_sample else None,
        "timestamp": latest_yr_sample.timestamp if latest_yr_sample else None,
        "api_updated_at": latest_yr_sample.api_updated_at if latest_yr_sample else None,
        "expires_at": latest_yr_sample.expires_at if latest_yr_sample else None,
        "next_fetch_after": latest_yr_sample.next_fetch_after if latest_yr_sample else None,
    }
    return {
        "timestamp": timestamp,
        "mode": latest_sample.mode if latest_sample else None,
        "indoor_avg": average_value([item["value"] for item in indoor_values]),
        "indoor_values": indoor_values,
        "outdoor_avg": average_value(outdoor_avg_values),
        "outdoor_values": outdoor_values,
        "lux": lux,
        "weather": weather,
        "weather_card": weather_card,
        "has_data": any(
            value is not None
            for value in [
                lux,
                weather,
                *[item["value"] for item in indoor_values],
                *[item["value"] for item in outdoor_values],
            ]
        ),
    }


def freshness_item(name: str, row, expected_minutes: int, warning_minutes: Optional[int] = None):
    warning_minutes = warning_minutes or expected_minutes * 2
    stamp = row.timestamp if row else None
    age_minutes = minutes_since(stamp)
    if age_minutes is None:
        status = "bad"
        status_text = "Mangler"
    elif age_minutes <= expected_minutes:
        status = "ok"
        status_text = "OK"
    elif age_minutes <= warning_minutes:
        status = "warn"
        status_text = "Treg"
    else:
        status = "bad"
        status_text = "Gammel"
    return {
        "name": name,
        "age": age_label(age_minutes),
        "status": status,
        "status_text": status_text,
        "timestamp": stamp,
    }


def light_status_text(row: OutdoorLightSample) -> str:
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


async def build_lux_day(day_start: datetime, day_end: datetime, timeline_end: datetime):
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
            }
        )

    scale = lux_scale(lux_values)
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


async def build_temp_day(day_start: datetime, day_end: datetime, timeline_end: datetime):
    series_config = [
        {"key": "temp_yr", "label": "Yr", "class": "yr"},
        {"key": "temp_1etg", "label": "1.etg", "class": "one"},
        {"key": "temp_loft", "label": "Loft", "class": "loft"},
    ]

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
        fan_rows = [
            row for row in fan_result.scalars().all()
            if event_matches_device(row, VENT_TIMELINE_DEVICES[2], VENT_TIMELINE_DEVICES)
        ]

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
            sample[f"{series['key']}_label"] = temp_label(value)
            if value is not None:
                has_value = True
                all_values.append(value)
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
                "latest": temp_label(values[-1]) if values else "-",
                "min": temp_label(min(values)) if values else "-",
                "max": temp_label(max(values)) if values else "-",
            }
        )

    y_ticks = []
    tick = axis["min"]
    while tick <= axis["max"] + 0.001:
        y_ticks.append({"label": temp_label(tick), "y": temp_y(tick, axis["min"], axis["max"])})
        tick += axis["step"]

    fan_events = []
    for row in fan_rows:
        state = state_from_event(row)
        if state is None:
            continue
        event_time = max(day_start, min(timeline_end, row.timestamp))
        fan_events.append(
            {
                "x": percent_between(event_time, day_start, day_end) * 10,
                "time": event_time.strftime("%H:%M"),
                "action": "PÅ" if state else "AV",
                "class": "on" if state else "off",
                "detail": clean_display_text(row.reason or row.source or ""),
            }
        )

    summary = {
        "count": len(samples),
        "fan_event_count": len(fan_events),
        "latest_time": samples[-1]["time"] if samples else "-",
        "axis_min": temp_label(axis["min"]),
        "axis_max": temp_label(axis["max"]),
    }
    return {
        "series": series_items,
        "fan_events": fan_events,
        "y_ticks": y_ticks,
        "samples_desc": list(reversed(samples)),
        "summary": summary,
    }


def row_to_dict(row, columns):
    out = {}
    for column in columns:
        if column == "extra":
            continue
        value = getattr(row, column)
        out[column] = value.isoformat() if isinstance(value, datetime) else value
    if hasattr(row, "extra"):
        out["extra"] = row.extra or {}
    return out


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
    return OutdoorLightEvent(
        timestamp=data.timestamp or datetime.utcnow(),
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


def payload_weather_symbol(data: EventDataIn) -> Optional[str]:
    return (
        data.weather_symbol
        or data.yr_symbol
        or nested_extra_value(data.extra, ["weather_symbol", "yr_symbol", "symbol_code", "next_1_hours_symbol_code"])
        or nested_extra_value(data.values, ["weather_symbol", "yr_symbol", "symbol_code", "next_1_hours_symbol_code"])
    )


def payload_weather_text(data: EventDataIn) -> Optional[str]:
    return (
        data.weather_text
        or data.weather_type
        or data.yr_weather
        or nested_extra_value(data.extra, ["weather_text", "weather_type", "yr_weather", "weather", "condition_text", "condition"])
        or nested_extra_value(data.values, ["weather_text", "weather_type", "yr_weather", "weather", "condition_text", "condition"])
    )


def light_sample_from_payload(data: EventDataIn, met_weather: Optional[Dict[str, Any]] = None) -> OutdoorLightSample:
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


def yr_sample_from_forecast(
    timestamp: datetime,
    bucket_start: datetime,
    source: Optional[str],
    forecast: Dict[str, Any],
) -> YrForecastSample:
    return YrForecastSample(
        timestamp=timestamp,
        bucket_start=bucket_start,
        source=source or "MET/Yr Locationforecast",
        api_updated_at=forecast.get("api_updated_at"),
        last_modified=forecast.get("last_modified"),
        expires_at=forecast.get("expires_at"),
        next_fetch_after=forecast.get("next_fetch_after"),
        age_seconds=forecast.get("age_seconds"),
        forecast_time=forecast.get("forecast_time"),
        symbol_code=forecast.get("symbol") or None,
        weather_text=forecast.get("text") or None,
        air_temperature=forecast.get("air_temperature"),
        relative_humidity=forecast.get("relative_humidity"),
        wind_speed=forecast.get("wind_speed"),
        wind_from_direction=forecast.get("wind_from_direction"),
        cloud_area_fraction=forecast.get("cloud_area_fraction"),
        fog_area_fraction=forecast.get("fog_area_fraction"),
        dew_point_temperature=forecast.get("dew_point_temperature"),
        air_pressure_at_sea_level=forecast.get("air_pressure_at_sea_level"),
        precipitation_next_1h=forecast.get("precipitation_next_1h"),
        precipitation_next_6h=forecast.get("precipitation_next_6h"),
        temp_1h=forecast.get("temp_1h"),
        temp_3h=forecast.get("temp_3h"),
        temp_6h=forecast.get("temp_6h"),
        temp_12h=forecast.get("temp_12h"),
        temp_24h=forecast.get("temp_24h"),
        symbol_1h=forecast.get("symbol_1h"),
        symbol_3h=forecast.get("symbol_3h"),
        symbol_6h=forecast.get("symbol_6h"),
        symbol_12h=forecast.get("symbol_12h"),
        symbol_24h=forecast.get("symbol_24h"),
        temp_min_next_6h=forecast.get("temp_min_next_6h"),
        temp_max_next_6h=forecast.get("temp_max_next_6h"),
        extra={"raw_meta": forecast.get("raw_meta") or {}},
    )


async def save_yr_sample_for_payload(data: EventDataIn, forecast: Optional[Dict[str, Any]] = None) -> Optional[int]:
    forecast = forecast or await met_weather_cached()
    if not forecast:
        return None
    timestamp = data.timestamp or datetime.utcnow()
    bucket_start = data.bucket_start or sample_bucket(timestamp)
    expires_at = forecast.get("expires_at")
    api_updated_at = forecast.get("api_updated_at")
    async with async_session() as session:
        stmt = select(YrForecastSample).limit(1)
        if expires_at:
            stmt = stmt.where(YrForecastSample.expires_at == expires_at)
        elif api_updated_at:
            stmt = stmt.where(YrForecastSample.api_updated_at == api_updated_at)
        else:
            stmt = stmt.where(YrForecastSample.bucket_start == bucket_start)
        existing = (await session.execute(stmt)).scalars().first()
        if existing:
            return existing.id
        record = yr_sample_from_forecast(timestamp, bucket_start, data.source, forecast)
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record.id


def vent_from_payload(data: EventDataIn) -> VentilationEvent:
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
        temp_passiv=value_from_payload(data, "temp_passiv"),
        temp_luftinntak=value_from_payload(data, "temp_luftinntak"),
        diff_w=value_from_payload(data, "diff_w"),
        power_w=value_from_payload(data, "power_w"),
        energy_kwh=value_from_payload(data, "energy_kwh"),
        fan_vip=value_from_payload(data, "fan_vip"),
        fan_2etg=value_from_payload(data, "fan_2etg"),
        fan_tak=value_from_payload(data, "fan_tak"),
        extra=merged_extra(data),
    )


def vent_sample_from_payload(data: EventDataIn) -> VentilationSample:
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
        temp_passiv=value_from_payload(data, "temp_passiv"),
        temp_luftinntak=value_from_payload(data, "temp_luftinntak"),
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
        extra=merged_extra(data),
    )


def generic_from_payload(data: EventDataIn) -> GenericEvent:
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


def apply_common_filters(stmt, model, event_type, action, device_key, device_id, mode, source_contains, from_ts, to_ts):
    if event_type:
        stmt = stmt.where(model.event_type == event_type)
    if action:
        stmt = stmt.where(model.action == action)
    if device_key:
        stmt = stmt.where(model.device_key == device_key)
    if device_id is not None:
        stmt = stmt.where(model.device_id == device_id)
    if mode:
        stmt = stmt.where(model.mode == mode)
    if source_contains:
        stmt = stmt.where(model.source.ilike(f"%{source_contains}%"))
    if from_ts:
        stmt = stmt.where(model.timestamp >= from_ts)
    if to_ts:
        stmt = stmt.where(model.timestamp <= to_ts)
    return stmt


async def save_record(record) -> int:
    async with async_session() as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record.id


async def ingest_roborock_robot(session, robot_data: Dict[str, Any], batch_time: datetime, source: str) -> Dict[str, Any]:
    duid = robot_data.get("duid") or robot_data.get("robot_duid")
    if not duid:
        return {"ok": False, "error": "Mangler DUID"}

    meta = robot_data.get("metadata") or robot_data
    network = robot_data.get("network") or {}
    capabilities = robot_data.get("capabilities") or robot_data.get("probe_results") or {}
    local_ip = robot_data.get("local_ip") or network.get("ip") or meta.get("local_ip")
    status = first_dict(robot_data.get("status"))
    consumable = first_dict(robot_data.get("consumables") or robot_data.get("consumable"))
    cloud_online = bool_value(meta.get("online") if "online" in meta else meta.get("cloud_online"))

    existing = (
        await session.execute(select(RoborockRobot).where(RoborockRobot.duid == duid))
    ).scalars().first()
    if not existing:
        existing = RoborockRobot(duid=duid, name=meta.get("name") or duid)
        session.add(existing)

    existing.name = meta.get("name") or existing.name or duid
    existing.product = robot_data.get("product") or meta.get("product") or meta.get("product_id") or existing.product
    existing.model = robot_data.get("model") or meta.get("model") or existing.model
    existing.firmware = meta.get("firmware") or meta.get("fv") or existing.firmware
    existing.protocol_version = meta.get("protocol_version") or meta.get("pv") or existing.protocol_version
    existing.serial_number = robot_data.get("serial_number") or meta.get("serial_number") or meta.get("sn") or existing.serial_number
    existing.local_ip = local_ip or existing.local_ip
    existing.cloud_online = cloud_online if cloud_online is not None else existing.cloud_online
    existing.shared = bool_value(meta.get("shared") if "shared" in meta else meta.get("share"))
    existing.time_zone_id = meta.get("time_zone_id") or meta.get("timezone") or existing.time_zone_id
    existing.last_seen_at = batch_time
    if robot_data.get("cloud"):
        existing.last_cloud_at = batch_time
    if status or network:
        existing.last_local_at = batch_time
    if status:
        existing.last_status_at = batch_time
    if robot_data.get("map"):
        existing.last_map_at = batch_time
    existing.last_error = robot_data.get("last_error") or robot_data.get("error") or None
    existing.capabilities = capabilities or existing.capabilities
    existing.extra = {
        "source": source,
        "metadata": meta,
        "summary": robot_data.get("clean_summary"),
    }

    if status:
        session.add(
            RoborockStatusSample(
                robot_duid=duid,
                timestamp=batch_time,
                source=source,
                state_code=int_value(status.get("state")),
                state_name=status.get("state_name") or roborock_state_label(status.get("state")),
                battery=int_value(status.get("battery")),
                error_code=int_value(status.get("error_code") if "error_code" in status else status.get("error")),
                in_cleaning=bool_value(status.get("in_cleaning")),
                in_returning=bool_value(status.get("in_returning")),
                clean_time_seconds=int_value(status.get("clean_time")),
                clean_area_m2=area_m2_from_payload(status.get("clean_area")),
                fan_power=int_value(status.get("fan_power")),
                water_box_mode=int_value(status.get("water_box_mode")),
                mop_mode=int_value(status.get("mop_mode")),
                dock_type=int_value(status.get("dock_type")),
                charge_status=int_value(status.get("charge_status")),
                clean_percent=int_value(status.get("clean_percent")),
                local_ip=local_ip,
                rssi=int_value(network.get("rssi")),
                raw={"status": status, "network": network},
            )
        )

    if consumable:
        session.add(
            RoborockConsumableSnapshot(
                robot_duid=duid,
                timestamp=batch_time,
                main_brush_work_time=int_value(consumable.get("main_brush_work_time")),
                side_brush_work_time=int_value(consumable.get("side_brush_work_time")),
                filter_work_time=int_value(consumable.get("filter_work_time")),
                sensor_dirty_time=int_value(consumable.get("sensor_dirty_time")),
                dust_collection_work_times=int_value(consumable.get("dust_collection_work_times")),
                raw=consumable,
            )
        )

    for job in robot_data.get("clean_jobs") or robot_data.get("jobs") or []:
        record_id = str(job.get("id") or job.get("record_id") or "")
        if not record_id:
            continue
        existing_job = (
            await session.execute(
                select(RoborockCleanJob)
                .where(RoborockCleanJob.robot_duid == duid)
                .where(RoborockCleanJob.record_id == record_id)
            )
        ).scalars().first()
        if not existing_job:
            existing_job = RoborockCleanJob(robot_duid=duid, record_id=record_id)
            session.add(existing_job)
        existing_job.begin_at = timestamp_value(job.get("begin") or job.get("begin_at"))
        existing_job.end_at = timestamp_value(job.get("end") or job.get("end_at"))
        existing_job.duration_seconds = int_value(job.get("duration_seconds") or job.get("duration"))
        existing_job.duration_minutes = float_value(job.get("duration_minutes"))
        existing_job.area_m2 = float_value(job.get("area_m2")) or area_m2_from_payload(job.get("area"))
        existing_job.cleaned_area_m2 = float_value(job.get("cleaned_area_m2")) or area_m2_from_payload(job.get("cleaned_area"))
        existing_job.complete = bool_value(job.get("complete"))
        existing_job.error_code = int_value(job.get("error") if "error" in job else job.get("error_code"))
        existing_job.start_type = int_value(job.get("start_type"))
        existing_job.clean_type = int_value(job.get("clean_type"))
        existing_job.finish_reason = int_value(job.get("finish_reason"))
        existing_job.dust_collection_status = int_value(job.get("dust_collection_status"))
        existing_job.avoid_count = int_value(job.get("avoid_count"))
        existing_job.wash_count = int_value(job.get("wash_count"))
        existing_job.clean_times = int_value(job.get("clean_times"))
        existing_job.updated_at = batch_time
        existing_job.raw = job

    for schedule in robot_data.get("schedules") or []:
        schedule_id = str(schedule.get("id") or schedule.get("schedule_id") or "")
        if not schedule_id:
            continue
        params = roborock_schedule_params(schedule)
        existing_schedule = (
            await session.execute(
                select(RoborockSchedule)
                .where(RoborockSchedule.robot_duid == duid)
                .where(RoborockSchedule.schedule_id == schedule_id)
            )
        ).scalars().first()
        if not existing_schedule:
            existing_schedule = RoborockSchedule(robot_duid=duid, schedule_id=schedule_id)
            session.add(existing_schedule)
        existing_schedule.cron = schedule.get("cron")
        existing_schedule.enabled = bool_value(schedule.get("enabled"))
        existing_schedule.repeated = bool_value(schedule.get("repeated"))
        existing_schedule.segments = params.get("segments")
        existing_schedule.fan_power = int_value(params.get("fan_power"))
        existing_schedule.mop_mode = int_value(params.get("mop_mode"))
        existing_schedule.water_box_mode = int_value(params.get("water_box_mode"))
        existing_schedule.repeat = int_value(params.get("repeat"))
        existing_schedule.updated_at = batch_time
        existing_schedule.raw = schedule

    map_data = robot_data.get("map") or {}
    if map_data:
        image_size = map_data.get("image_size") or []
        if not isinstance(image_size, list):
            image_size = []
        session.add(
            RoborockMapSnapshot(
                robot_duid=duid,
                timestamp=batch_time,
                image_bytes=int_value(map_data.get("image_bytes")),
                raw_bytes=int_value(map_data.get("raw_bytes")),
                image_width=int_value(image_size[0] if len(image_size) > 0 else map_data.get("image_width")),
                image_height=int_value(image_size[1] if len(image_size) > 1 else map_data.get("image_height")),
                rooms=int_value(map_data.get("rooms")),
                zones=int_value(map_data.get("zones")),
                charger=map_data.get("charger"),
                vacuum_position=map_data.get("vacuum_position"),
                image_base64=map_data.get("image_base64"),
                raw={key: value for key, value in map_data.items() if key != "image_base64"},
            )
        )

    for probe in robot_data.get("probe_results") or []:
        session.add(
            RoborockProbeResult(
                robot_duid=duid,
                timestamp=batch_time,
                source=probe.get("source") or source,
                command=probe.get("command") or probe.get("name"),
                ok=bool_value(probe.get("ok")),
                error=probe.get("error"),
                result_type=probe.get("type") or probe.get("result_type"),
                raw=probe,
            )
        )
    return {"ok": True, "duid": duid}


async def ingest_sun2_room_stats(session, data: Sun2RoomStatsIngestIn, batch_time: datetime) -> Dict[str, int]:
    inserted = 0
    updated = 0
    batch_date = data.stat_date
    for row in data.rows:
        source_room_name = (repair_mojibake(row.source_room_name or row.room) or "").strip()
        room = (repair_mojibake(row.room) or source_room_name).strip()
        room_key = (repair_mojibake(row.room_key) or room_key_from_name(source_room_name) or room_key_from_name(room) or room).strip()
        if not room:
            continue
        stat_date = row.stat_date or batch_date
        existing = (
            await session.execute(
                select(Sun2RoomDailyStat)
                .where(Sun2RoomDailyStat.stat_date == stat_date)
                .where(Sun2RoomDailyStat.room_key == room_key)
            )
        ).scalars().first()
        if not existing:
            existing = (
                await session.execute(
                    select(Sun2RoomDailyStat)
                    .where(Sun2RoomDailyStat.stat_date == stat_date)
                    .where(Sun2RoomDailyStat.room == room)
                )
            ).scalars().first()
        if not existing:
            same_day = (
                await session.execute(
                    select(Sun2RoomDailyStat).where(Sun2RoomDailyStat.stat_date == stat_date)
                )
            ).scalars().all()
            existing = next(
                (
                    candidate for candidate in same_day
                    if repair_mojibake(candidate.room) == room
                    or repair_mojibake(candidate.source_room_name) == source_room_name
                    or (candidate.room_key and repair_mojibake(candidate.room_key) == room_key)
                ),
                None,
            )
        if not existing:
            existing = Sun2RoomDailyStat(stat_date=stat_date, room=room)
            session.add(existing)
            inserted += 1
        else:
            updated += 1

        existing.room_key = room_key
        existing.room = room
        existing.source_room_name = source_room_name
        existing.total_soletid_minutter = row.total_soletid_minutter
        existing.totalt_antall_solinger = row.totalt_antall_solinger
        existing.solinger_medlemmer = row.solinger_medlemmer
        existing.solinger_ikke_medlemmer = row.solinger_ikke_medlemmer
        existing.totalt_inntjent_kr = row.totalt_inntjent_kr
        existing.inntjent_medlemmer_kr = row.inntjent_medlemmer_kr
        existing.inntjent_ikke_medlemmer_kr = row.inntjent_ikke_medlemmer_kr
        existing.source = data.source
        existing.source_file = data.source_file
        existing.imported_at = batch_time
        existing.raw = row.raw or {}

    return {"inserted": inserted, "updated": updated}


async def fetch_rows(model, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, limit):
    from_ts = parse_datetime(from_text)
    to_ts = parse_datetime(to_text)
    limit = max(1, min(limit, 10000))
    stmt = select(model).order_by(model.timestamp.desc()).limit(limit)
    stmt = apply_common_filters(stmt, model, event_type, action, device_key, device_id, mode, source_contains, from_ts, to_ts)
    async with async_session() as session:
        result = await session.execute(stmt)
        return result.scalars().all(), limit


async def csv_response(model, columns, filename, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text):
    rows, _ = await fetch_rows(model, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, 10000)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        row_dict = row_to_dict(row, columns)
        writer.writerow([json_value(row_dict.get(column)) for column in columns])
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for table_name, columns in STARTUP_COLUMNS.items():
            for column_name, column_type in columns:
                await conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type}")
        await conn.execute(delete(OutdoorLightEvent).where(OutdoorLightEvent.source == "CODEX TEST"))
        await conn.execute(delete(VentilationEvent).where(VentilationEvent.source == "CODEX TEST"))
    async with async_session() as session:
        result = await session.execute(select(AccessKey).where(AccessKey.key_hash == MASTER_ACCESS_KEY_HASH))
        master = result.scalars().first()
        if master:
            master.name = "master"
            master.key_prefix = "sun2_master"
            master.is_master = True
            master.role = "master"
            master.active = True
        else:
            session.add(
                AccessKey(
                    name="master",
                    key_hash=MASTER_ACCESS_KEY_HASH,
                    key_prefix="sun2_master",
                    role="master",
                    is_master=True,
                    active=True,
                )
            )
        legacy_shared = (
            await session.execute(
                select(AccessKey)
                .where(AccessKey.is_master == False)
                .where(AccessKey.key_plaintext.isnot(None))
            )
        ).scalars().all()
        for key in legacy_shared:
            username = normalize_username(key.name)
            password = key.key_plaintext or ""
            if not key.role:
                key.role = "viewer"
            if username and password:
                key.name = username
                key.key_hash = credential_hash(username, password)
                key.key_prefix = credential_prefix(username, password)
        await session.commit()
    async with async_session() as session:
        for config_key in CONFIG_DEFINITIONS:
            await get_or_create_config(session, config_key)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "storage": [
            "utelys_events", "utelys_samples", "ventilasjon_events", "ventilasjon_samples",
            "yr_forecast_samples", "control_configs", "control_config_history", "event_data",
            "roborock_robots", "roborock_status_samples", "roborock_clean_jobs",
            "roborock_schedules", "roborock_consumables", "roborock_maps",
            "sun2_room_daily_stats", "sun2_import_runs",
        ],
    }


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(
        "static/sun2-blue-transparent.png",
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=604800, immutable"},
    )


@app.get("/auth/login", response_class=HTMLResponse)
async def login_view(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": ""})


@app.post("/auth/login")
async def login_submit(request: Request):
    form = await parse_form_body(request)
    username = normalize_username(form.get("username") or "")
    password = (form.get("password") or "").strip()
    access_key = await find_access_key(username, password)
    if not access_key:
        await log_access_attempt(request, False, "failed_login", attempted_username=username)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Ugyldig brukernavn eller passord"},
            status_code=401,
        )
    response = RedirectResponse("/status/dashboard", status_code=303)
    response.set_cookie(
        AUTH_USER_COOKIE_NAME,
        username,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    response.set_cookie(
        AUTH_COOKIE_NAME,
        password,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    await log_access_attempt(request, True, "login", access_key)
    return response


@app.post("/konto/logg-ut")
async def logout():
    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie(AUTH_USER_COOKIE_NAME)
    response.delete_cookie(AUTH_COOKIE_NAME)
    return response


@app.get("/konto/oversikt", response_class=HTMLResponse)
async def account_view(request: Request):
    return templates.TemplateResponse(request, "account.html", {})


@app.get("/energi/testside", response_class=HTMLResponse)
async def energy_view(request: Request):
    return templates.TemplateResponse(request, "energy.html", {})


async def admin_keys_context(
    request: Request,
    session,
    created_username: str = "",
    created_key: str = "",
    error: str = "",
) -> Dict[str, Any]:
    key_rows = (await session.execute(select(AccessKey).order_by(AccessKey.created_at.desc()))).scalars().all()
    selected_key = None
    try:
        selected_key_id = int(request.query_params.get("key_id") or "0")
    except ValueError:
        selected_key_id = 0
    if selected_key_id:
        selected_key = next((key for key in key_rows if key.id == selected_key_id), None)

    log_query = select(AccessLog).order_by(AccessLog.timestamp.desc()).limit(200)
    if selected_key:
        log_query = (
            select(AccessLog)
            .where((AccessLog.access_key_id == selected_key.id) | (AccessLog.key_name == selected_key.name))
            .order_by(AccessLog.timestamp.desc())
            .limit(200)
        )
    log_rows = (await session.execute(log_query)).scalars().all()
    return {
        "keys": key_rows,
        "logs": log_rows,
        "selected_key": selected_key,
        "created_username": created_username,
        "created_key": created_key,
        "error": error,
    }


@app.get("/konto/brukere-og-tilgang", response_class=HTMLResponse)
async def keys_view(request: Request):
    forbidden = require_master(request)
    if forbidden:
        return forbidden
    async with async_session() as session:
        context = await admin_keys_context(request, session)
    return templates.TemplateResponse(request, "keys.html", context)


@app.post("/konto/brukere-og-tilgang")
async def keys_create(request: Request):
    forbidden = require_master(request)
    if forbidden:
        return forbidden
    form = await parse_form_body(request)
    username = normalize_username(form.get("username") or form.get("name") or "")[:80]
    password = (form.get("password") or form.get("access_key") or "").strip()
    role = (form.get("role") or "viewer").strip().lower()
    if role not in ["viewer", "settings"]:
        role = "viewer"
    if not username:
        async with async_session() as session:
            key_rows = (await session.execute(select(AccessKey).order_by(AccessKey.created_at.desc()))).scalars().all()
            log_rows = (await session.execute(select(AccessLog).order_by(AccessLog.timestamp.desc()).limit(200))).scalars().all()
        return templates.TemplateResponse(
            request,
            "keys.html",
            {
                "keys": key_rows,
                "logs": log_rows,
                "created_username": "",
                "created_key": "",
                "error": "Brukernavn må fylles ut.",
            },
            status_code=400,
        )
    if len(password) < 5:
        async with async_session() as session:
            key_rows = (await session.execute(select(AccessKey).order_by(AccessKey.created_at.desc()))).scalars().all()
            log_rows = (await session.execute(select(AccessLog).order_by(AccessLog.timestamp.desc()).limit(200))).scalars().all()
        return templates.TemplateResponse(
            request,
            "keys.html",
            {
                "keys": key_rows,
                "logs": log_rows,
                "created_username": "",
                "created_key": "",
                "error": "Passordet må være minst 5 tegn.",
            },
            status_code=400,
        )
    existing_hash = credential_hash(username, password)
    async with async_session() as session:
        existing = (
            await session.execute(select(AccessKey).where(AccessKey.key_hash == existing_hash))
        ).scalars().first()
        if existing:
            key_rows = (await session.execute(select(AccessKey).order_by(AccessKey.created_at.desc()))).scalars().all()
            log_rows = (await session.execute(select(AccessLog).order_by(AccessLog.timestamp.desc()).limit(200))).scalars().all()
            return templates.TemplateResponse(
                request,
                "keys.html",
                {
                    "keys": key_rows,
                    "logs": log_rows,
                    "created_username": "",
                    "created_key": "",
                    "error": "Denne kombinasjonen av brukernavn og passord finnes allerede.",
                },
                status_code=400,
            )
        record = AccessKey(
            name=username,
            key_hash=existing_hash,
            key_prefix=credential_prefix(username, password),
            key_plaintext=password,
            role=role,
            is_master=False,
            active=True,
        )
        session.add(record)
        await session.commit()
        key_rows = (await session.execute(select(AccessKey).order_by(AccessKey.created_at.desc()))).scalars().all()
        log_rows = (await session.execute(select(AccessLog).order_by(AccessLog.timestamp.desc()).limit(200))).scalars().all()
    return templates.TemplateResponse(
        request,
        "keys.html",
        {"keys": key_rows, "logs": log_rows, "created_username": username, "created_key": password, "error": ""},
    )


@app.post("/konto/brukere-og-tilgang/deaktiver")
async def keys_disable(request: Request):
    forbidden = require_master(request)
    if forbidden:
        return forbidden
    form = await parse_form_body(request)
    try:
        key_id = int(form.get("key_id") or "0")
    except ValueError:
        key_id = 0
    async with async_session() as session:
        await session.execute(
            update(AccessKey)
            .where(AccessKey.id == key_id)
            .where(AccessKey.is_master == False)
            .values(active=False)
        )
        await session.commit()
    return RedirectResponse("/konto/brukere-og-tilgang", status_code=303)


@app.post("/konto/brukere-og-tilgang/rolle")
async def keys_role_update(request: Request):
    forbidden = require_master(request)
    if forbidden:
        return forbidden
    form = await parse_form_body(request)
    try:
        key_id = int(form.get("key_id") or "0")
    except ValueError:
        key_id = 0
    role = (form.get("role") or "viewer").strip().lower()
    if role not in ["viewer", "settings"]:
        role = "viewer"
    async with async_session() as session:
        await session.execute(
            update(AccessKey)
            .where(AccessKey.id == key_id)
            .where(AccessKey.is_master == False)
            .values(role=role)
        )
        await session.commit()
    return RedirectResponse("/konto/brukere-og-tilgang", status_code=303)


async def config_context(config_key: str):
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


@app.get("/api/config")
async def api_control_configs():
    async with async_session() as session:
        rows = [await get_or_create_config(session, config_key) for config_key in CONFIG_DEFINITIONS]
    return {"configs": [config_payload(row) for row in rows if row]}


@app.get("/api/config/{config_key}")
async def api_control_config(config_key: str):
    if config_key not in CONFIG_DEFINITIONS:
        return JSONResponse({"detail": "Ukjent konfigurasjon"}, status_code=404)
    async with async_session() as session:
        row = await get_or_create_config(session, config_key)
    return config_payload(row)


@app.get("/lys/innstillinger", response_class=HTMLResponse)
async def light_settings_view(request: Request):
    context = await config_context("lights")
    return templates.TemplateResponse(request, "control_settings.html", context)


@app.post("/lys/innstillinger", response_class=HTMLResponse)
async def light_settings_update(request: Request):
    return await update_settings(request, "lights")


@app.get("/ventilasjon/innstillinger", response_class=HTMLResponse)
async def ventilation_settings_view(request: Request):
    context = await config_context("ventilation")
    return templates.TemplateResponse(request, "control_settings.html", context)


@app.post("/ventilasjon/innstillinger", response_class=HTMLResponse)
async def ventilation_settings_update(request: Request):
    return await update_settings(request, "ventilation")


async def update_settings(request: Request, config_key: str):
    forbidden = require_settings_access(request)
    if forbidden:
        return forbidden
    form = await parse_form_body(request)
    values = config_values_from_form(config_key, form)
    errors = validate_config_values(config_key, values)
    if errors:
        context = await config_context(config_key)
        context["values"] = values
        context["rules"] = config_rules(config_key, values)
        context["summary_rows"] = config_summary_rows(config_key, values)
        context["stat_cards"] = config_stat_cards(config_key, values, context["config"].version)
        context["operational_notes"] = config_operational_notes(config_key, values)
        context["errors"] = errors
        return templates.TemplateResponse(request, "control_settings.html", context, status_code=400)
    reason = (form.get("reason") or "Endret i grensesnittet").strip()
    changed_by = getattr(request.state, "access_key_name", "") or "master"
    async with async_session() as session:
        row = await get_or_create_config(session, config_key)
        row.values = values
        row.version = (row.version or 1) + 1
        row.updated_at = datetime.utcnow()
        row.updated_by = changed_by
        session.add(
            ControlConfigHistory(
                config_key=config_key,
                version=row.version,
                values=deepcopy(values),
                changed_by=changed_by,
                reason=reason,
            )
        )
        await session.commit()
    context = await config_context(config_key)
    context["saved"] = True
    return templates.TemplateResponse(request, "control_settings.html", context)


@app.get("/")
async def root_redirect():
    return RedirectResponse("/status/dashboard", status_code=303)


@app.get("/status/dashboard", response_class=HTMLResponse)
async def index(request: Request):
    async with async_session() as session:
        lights = (await session.execute(select(OutdoorLightEvent).order_by(OutdoorLightEvent.timestamp.desc()).limit(200))).scalars().all()
        light_samples = (await session.execute(select(OutdoorLightSample).order_by(OutdoorLightSample.timestamp.desc()).limit(1))).scalars().all()
        ventilation = (await session.execute(select(VentilationEvent).order_by(VentilationEvent.timestamp.desc()).limit(100))).scalars().all()
        samples = (await session.execute(select(VentilationSample).order_by(VentilationSample.timestamp.desc()).limit(1))).scalars().all()
        yr_samples = (await session.execute(select(YrForecastSample).order_by(YrForecastSample.timestamp.desc()).limit(1))).scalars().all()

    latest_light_by_key = {}
    for row in lights:
        key = event_device_key(row, LIGHT_TIMELINE_DEVICES)
        if key and key not in latest_light_by_key:
            latest_light_by_key[key] = row

    latest_vent_by_key = {}
    for row in ventilation:
        key = event_device_key(row, VENT_TIMELINE_DEVICES)
        if key and key not in latest_vent_by_key:
            latest_vent_by_key[key] = row

    latest_sample = samples[0] if samples else None
    latest_light_sample = light_samples[0] if light_samples else None
    latest_yr_sample = yr_samples[0] if yr_samples else None
    latest_light = lights[0] if lights else None
    now_status = build_now_status(latest_sample, latest_light_sample, latest_light, latest_yr_sample)

    light_status = []
    for device in LIGHT_TIMELINE_DEVICES:
        row = latest_light_by_key.get(device["key"])
        light_sample_value = light_sample_state(latest_light_sample, device) if latest_light_sample else None
        event_state = state_from_event(row) if row else None
        light_status.append(
            {
                "id": device["key"],
                "name": device["name"],
                "row": row,
                "state": light_sample_value if light_sample_value is not None else event_state,
                "sample_time": latest_light_sample.timestamp if light_sample_value is not None else None,
                "lux": row.lux if row and row.lux is not None else (
                    latest_light_sample.lux
                    if latest_light_sample and latest_light_sample.lux is not None
                    else None
                ),
            }
        )
    vent_status = [
        {
            "id": device["key"],
            "name": device["name"],
            "row": latest_vent_by_key.get(device["key"]),
            "state": sample_state(latest_sample, device),
        }
        for device in VENT_TIMELINE_DEVICES
    ]
    vent_status.append(
        {
            "id": "loft_recovery",
            "name": "Loft > 1.etg gjenvinning",
            "row": None,
            "state": False,
            "dummy_reason": "Planlagt varmegjenvinning fra loft til 1.etg. Ikke koblet til styring ennå.",
        }
    )
    freshness_items = [
        freshness_item("Temp logg", latest_sample, 7, 15),
        freshness_item("Lux logging", latest_light_sample, 7, 15),
        freshness_item("Yr API", latest_yr_sample, 70, 130),
        freshness_item("Lys-hendelser", lights[0] if lights else None, 120, 360),
        freshness_item("Ventilasjonshendelser", ventilation[0] if ventilation else None, 120, 360),
    ]

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "latest_light": latest_light,
            "latest_light_sample": latest_light_sample,
            "latest_vent": ventilation[0] if ventilation else None,
            "latest_sample": latest_sample,
            "latest_yr_sample": latest_yr_sample,
            "now_status": now_status,
            "light_status": light_status,
            "vent_status": vent_status,
            "freshness_items": freshness_items,
        },
    )


@app.get("/status/dagslinje", response_class=HTMLResponse)
async def day_view(request: Request, day: Optional[str] = None, zoom: Optional[str] = "all"):
    selected_day = parse_day(day)
    zoom_config, window_start, window_end, ticks = day_zoom_window(selected_day, zoom)
    now_local = local_now_naive()
    is_today = selected_day == now_local.date()
    if is_today:
        if now_local < window_start:
            timeline_end = window_start
        elif now_local > window_end:
            timeline_end = window_end
        else:
            timeline_end = now_local
    else:
        timeline_end = window_end
    now_marker = percent_between(now_local, window_start, window_end) if is_today and window_start <= now_local <= window_end else None
    light_items = await build_light_timeline_group(window_start, window_end, timeline_end)
    vent_items = await build_timeline_group(VentilationEvent, VENT_TIMELINE_DEVICES, "ventilasjon", window_start, window_end, timeline_end)
    return templates.TemplateResponse(
        request,
        "day.html",
        {
            "selected_day": selected_day.isoformat(),
            "prev_day": (selected_day - timedelta(days=1)).isoformat(),
            "next_day": (selected_day + timedelta(days=1)).isoformat(),
            "zoom": zoom_config["key"],
            "zoom_label": zoom_config["label"],
            "zoom_options": DAY_ZOOM_OPTIONS,
            "is_today": is_today,
            "now_marker": now_marker,
            "now_label": now_local.strftime("%H:%M") if is_today else "",
            "light_items": light_items,
            "vent_items": vent_items,
            "ticks": ticks,
        },
    )


@app.get("/lys/dagslogg-lux", response_class=HTMLResponse)
async def day_lux_view(request: Request, day: Optional[str] = None):
    selected_day = parse_day(day)
    day_start = datetime.combine(selected_day, time.min)
    day_end = day_start + timedelta(days=1)
    now_local = local_now_naive()
    is_today = selected_day == now_local.date()
    timeline_end = min(now_local, day_end) if is_today else day_end
    now_marker = percent_between(now_local, day_start, day_end) if is_today else None
    lux_day = await build_lux_day(day_start, day_end, timeline_end)
    return templates.TemplateResponse(
        request,
        "day_lux.html",
        {
            "selected_day": selected_day.isoformat(),
            "prev_day": (selected_day - timedelta(days=1)).isoformat(),
            "next_day": (selected_day + timedelta(days=1)).isoformat(),
            "is_today": is_today,
            "now_marker": now_marker,
            "now_label": now_local.strftime("%H:%M") if is_today else "",
            "lux_day": lux_day,
            "ticks": [
                {"label": "00", "x": 0},
                {"label": "06", "x": 250},
                {"label": "12", "x": 500},
                {"label": "18", "x": 750},
                {"label": "24", "x": 1000},
            ],
        },
    )


@app.get("/ventilasjon/dagslogg-temp", response_class=HTMLResponse)
async def day_temp_view(request: Request, day: Optional[str] = None):
    selected_day = parse_day(day)
    day_start = datetime.combine(selected_day, time.min)
    day_end = day_start + timedelta(days=1)
    now_local = local_now_naive()
    is_today = selected_day == now_local.date()
    timeline_end = min(now_local, day_end) if is_today else day_end
    now_marker = percent_between(now_local, day_start, day_end) if is_today else None
    temp_day = await build_temp_day(day_start, day_end, timeline_end)
    return templates.TemplateResponse(
        request,
        "day_temp.html",
        {
            "selected_day": selected_day.isoformat(),
            "prev_day": (selected_day - timedelta(days=1)).isoformat(),
            "next_day": (selected_day + timedelta(days=1)).isoformat(),
            "is_today": is_today,
            "now_marker": now_marker,
            "now_label": now_local.strftime("%H:%M") if is_today else "",
            "temp_day": temp_day,
            "ticks": [
                {"label": "00", "x": 0},
                {"label": "06", "x": 250},
                {"label": "12", "x": 500},
                {"label": "18", "x": 750},
                {"label": "24", "x": 1000},
            ],
        },
    )


@app.post("/log")
async def legacy_log_data(data: LegacyLogIn):
    record = GenericEvent(
        timestamp=data.timestamp,
        system="legacy",
        event_type="legacy_log",
        source=data.source,
        value=data.temperature,
        extra={"temperature": data.temperature, "humidity": data.humidity},
    )
    event_id = await save_record(record)
    return {"status": "ok", "id": event_id, "table": "event_data"}


@app.post("/events")
async def log_event(data: EventDataIn):
    system = (data.system or "").lower()
    if system in {"utelys", "ute_lys", "lys"}:
        if data.event_type in {"sample", "sample_5min", "learning_sample"}:
            met_weather = None
            if not payload_weather_symbol(data) and not payload_weather_text(data):
                met_weather = await met_weather_cached()
            yr_sample_id = await save_yr_sample_for_payload(data, met_weather)
            event_id = await save_record(light_sample_from_payload(data, met_weather))
            return {"status": "ok", "id": event_id, "table": "utelys_samples", "yr_sample_id": yr_sample_id}
        event_id = await save_record(light_from_payload(data))
        return {"status": "ok", "id": event_id, "table": "utelys_events"}
    if system in {"ventilasjon", "ventilation", "vent"}:
        if data.event_type in {"sample", "sample_5min", "sample_15min", "learning_sample"}:
            yr_sample_id = await save_yr_sample_for_payload(data)
            event_id = await save_record(vent_sample_from_payload(data))
            return {"status": "ok", "id": event_id, "table": "ventilasjon_samples", "yr_sample_id": yr_sample_id}
        event_id = await save_record(vent_from_payload(data))
        return {"status": "ok", "id": event_id, "table": "ventilasjon_events"}
    event_id = await save_record(generic_from_payload(data))
    return {"status": "ok", "id": event_id, "table": "event_data"}


@app.post("/api/renhold/ingest")
async def roborock_ingest(data: RoborockIngestIn):
    batch_time = data.timestamp or datetime.utcnow()
    results = []
    async with async_session() as session:
        session.add(
            RoborockSyncRun(
                timestamp=batch_time,
                collector_id=data.collector_id,
                source=data.source,
                ok=data.ok,
                robots_count=len(data.robots),
                message=data.message,
                raw={"extra": data.extra},
            )
        )
        for robot in data.robots:
            results.append(await ingest_roborock_robot(session, robot, batch_time, data.source))
        await session.commit()
    return {"status": "ok", "robots": results}


@app.post("/api/sun2/room-stats/ingest")
async def sun2_room_stats_ingest(data: Sun2RoomStatsIngestIn):
    batch_time = data.timestamp or datetime.utcnow()
    async with async_session() as session:
        counts = await ingest_sun2_room_stats(session, data, batch_time)
        session.add(
            Sun2ImportRun(
                timestamp=batch_time,
                collector_id=data.collector_id,
                source=data.source,
                ok=data.ok,
                stat_date=data.stat_date,
                source_file=data.source_file,
                rows_count=len(data.rows),
                inserted_count=counts["inserted"],
                updated_count=counts["updated"],
                message=data.message,
                raw={"extra": data.extra},
            )
        )
        await session.commit()
    return {"status": "ok", **counts, "rows": len(data.rows)}


@app.get("/sun2/room-stats")
async def sun2_room_stats_legacy_redirect():
    return RedirectResponse("/energi/soling", status_code=307)


@app.get("/sun2/room-stats/json")
async def sun2_room_stats_json_legacy_redirect():
    return RedirectResponse("/api/sun2/room-stats/json", status_code=307)


@app.get("/energi")
async def energy_redirect():
    return RedirectResponse("/energi/oversikt", status_code=307)


@app.get("/energi/oversikt", response_class=HTMLResponse)
async def sun2_overview_view(request: Request):
    async with async_session() as session:
        rows = (
            await session.execute(
                select(Sun2RoomDailyStat)
                .order_by(Sun2RoomDailyStat.stat_date.asc(), Sun2RoomDailyStat.room)
            )
        ).scalars().all()
        latest_import = (
            await session.execute(
                select(Sun2ImportRun)
                .order_by(Sun2ImportRun.timestamp.desc())
                .limit(1)
            )
        ).scalars().first()
    summaries = build_sun2_summaries(rows)
    return templates.TemplateResponse(
        request,
        "sun2_overview.html",
        {
            "top_days": summaries["top_days"],
            "top_months": summaries["top_months"],
            "grand_total": summaries["total"],
            "first_date": summaries["first_date"],
            "last_date": summaries["last_date"],
            "total_rows": len(rows),
            "latest_import": latest_import,
        },
    )


@app.get("/energi/soling", response_class=HTMLResponse)
async def sun2_room_stats_view(request: Request, limit: int = 300):
    limit = max(1, min(limit, 1000))
    async with async_session() as session:
        summary_rows = (
            await session.execute(
                select(Sun2RoomDailyStat)
                .order_by(Sun2RoomDailyStat.stat_date.asc(), Sun2RoomDailyStat.room)
            )
        ).scalars().all()
        rows = (
            await session.execute(
                select(Sun2RoomDailyStat)
                .order_by(Sun2RoomDailyStat.stat_date.desc(), Sun2RoomDailyStat.room)
                .limit(limit)
            )
        ).scalars().all()
        imports = (
            await session.execute(
                select(Sun2ImportRun)
                .order_by(Sun2ImportRun.timestamp.desc())
                .limit(25)
            )
        ).scalars().all()
    summaries = build_sun2_summaries(summary_rows)
    return templates.TemplateResponse(
        request,
        "sun2_room_stats.html",
        {
            "rows": rows,
            "imports": imports,
            "limit": limit,
            "monthly_totals": summaries["monthly"],
            "yearly_totals": summaries["yearly"],
            "grand_total": summaries["total"],
            "first_date": summaries["first_date"],
            "last_date": summaries["last_date"],
            "total_rows": len(summary_rows),
        },
    )


@app.get("/api/sun2/room-stats/json")
async def sun2_room_stats_json(limit: int = 300):
    limit = max(1, min(limit, 5000))
    async with async_session() as session:
        summary_rows = (
            await session.execute(
                select(Sun2RoomDailyStat)
                .order_by(Sun2RoomDailyStat.stat_date.asc(), Sun2RoomDailyStat.room)
            )
        ).scalars().all()
        rows = (
            await session.execute(
                select(Sun2RoomDailyStat)
                .order_by(Sun2RoomDailyStat.stat_date.desc(), Sun2RoomDailyStat.room)
                .limit(limit)
            )
        ).scalars().all()
        imports = (
            await session.execute(
                select(Sun2ImportRun)
                .order_by(Sun2ImportRun.timestamp.desc())
                .limit(min(limit, 500))
            )
        ).scalars().all()
    summaries = build_sun2_summaries(summary_rows)
    return {
        "rows": [row_to_dict(row, SUN2_ROOM_COLUMNS) for row in rows],
        "imports": [row_to_dict(row, SUN2_IMPORT_COLUMNS) for row in imports],
        "daily_totals": summaries["daily"],
        "monthly_totals": summaries["monthly"],
        "yearly_totals": summaries["yearly"],
        "top_days": summaries["top_days"],
        "top_months": summaries["top_months"],
        "grand_total": summaries["total"],
        "first_date": summaries["first_date"],
        "last_date": summaries["last_date"],
        "total_rows": len(summary_rows),
    }


@app.get("/renhold/oversikt", response_class=HTMLResponse)
async def cleaning_overview(request: Request):
    async with async_session() as session:
        robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
        latest_status = {}
        latest_jobs = {}
        next_schedules = {}
        for robot in robots:
            latest_status[robot.duid] = (
                await session.execute(
                    select(RoborockStatusSample)
                    .where(RoborockStatusSample.robot_duid == robot.duid)
                    .order_by(RoborockStatusSample.timestamp.desc())
                    .limit(1)
                )
            ).scalars().first()
            latest_jobs[robot.duid] = (
                await session.execute(
                    select(RoborockCleanJob)
                    .where(RoborockCleanJob.robot_duid == robot.duid)
                    .order_by(RoborockCleanJob.begin_at.desc())
                    .limit(1)
                )
            ).scalars().first()
            schedules = (
                await session.execute(
                    select(RoborockSchedule)
                    .where(RoborockSchedule.robot_duid == robot.duid)
                    .where(RoborockSchedule.enabled == True)
                )
            ).scalars().all()
            next_schedules[robot.duid] = min(schedules, key=roborock_next_schedule_score) if schedules else None
    return templates.TemplateResponse(
        request,
        "cleaning_overview.html",
        {
            "robots": robots,
            "latest_status": latest_status,
            "latest_jobs": latest_jobs,
            "next_schedules": next_schedules,
        },
    )


@app.get("/renhold/robot/{duid}", response_class=HTMLResponse)
async def cleaning_robot_detail(request: Request, duid: str):
    async with async_session() as session:
        robot = (await session.execute(select(RoborockRobot).where(RoborockRobot.duid == duid))).scalars().first()
        if not robot:
            return JSONResponse({"detail": "Ukjent robot"}, status_code=404)
        statuses = (
            await session.execute(
                select(RoborockStatusSample)
                .where(RoborockStatusSample.robot_duid == duid)
                .order_by(RoborockStatusSample.timestamp.desc())
                .limit(100)
            )
        ).scalars().all()
        jobs = (
            await session.execute(
                select(RoborockCleanJob)
                .where(RoborockCleanJob.robot_duid == duid)
                .order_by(RoborockCleanJob.begin_at.desc())
                .limit(50)
            )
        ).scalars().all()
        schedules = (
            await session.execute(
                select(RoborockSchedule)
                .where(RoborockSchedule.robot_duid == duid)
                .order_by(RoborockSchedule.cron)
            )
        ).scalars().all()
        consumables = (
            await session.execute(
                select(RoborockConsumableSnapshot)
                .where(RoborockConsumableSnapshot.robot_duid == duid)
                .order_by(RoborockConsumableSnapshot.timestamp.desc())
                .limit(1)
            )
        ).scalars().first()
        latest_map = (
            await session.execute(
                select(RoborockMapSnapshot)
                .where(RoborockMapSnapshot.robot_duid == duid)
                .order_by(RoborockMapSnapshot.timestamp.desc())
                .limit(1)
            )
        ).scalars().first()
    return templates.TemplateResponse(
        request,
        "cleaning_robot.html",
        {
            "robot": robot,
            "latest_status": statuses[0] if statuses else None,
            "statuses": statuses,
            "jobs": jobs,
            "schedules": schedules,
            "consumables": consumables,
            "latest_map": latest_map,
        },
    )


@app.get("/renhold/json")
async def cleaning_json(limit: int = 100):
    limit = max(1, min(limit, 1000))
    async with async_session() as session:
        robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
        jobs = (await session.execute(select(RoborockCleanJob).order_by(RoborockCleanJob.begin_at.desc()).limit(limit))).scalars().all()
        statuses = (await session.execute(select(RoborockStatusSample).order_by(RoborockStatusSample.timestamp.desc()).limit(limit))).scalars().all()
    return {
        "robots": [row_to_dict(row, ROBOROCK_ROBOT_COLUMNS) for row in robots],
        "jobs": [row_to_dict(row, ROBOROCK_JOB_COLUMNS) for row in jobs],
        "statuses": [row_to_dict(row, ROBOROCK_STATUS_COLUMNS) for row in statuses],
    }


@app.get("/lys/hendelser", response_class=HTMLResponse)
async def lights_view(
    request: Request,
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_key: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 300,
):
    rows, limit = await fetch_rows(OutdoorLightEvent, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, limit)
    filters = {"event_type": event_type or "", "action": action or "", "device_key": device_key or "", "device_id": device_id or "", "mode": mode or "", "source_contains": source_contains or "", "from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "lights.html", {"rows": rows, "filters": filters})


@app.get("/lights/json")
async def lights_json(
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_key: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(OutdoorLightEvent, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, limit)
    return {"count": len(rows), "rows": [row_to_dict(row, LIGHT_COLUMNS) for row in rows]}


@app.get("/lights/download")
async def lights_download(
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_key: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(OutdoorLightEvent, LIGHT_COLUMNS, "utelys_events.csv", event_type, action, device_key, device_id, mode, source_contains, from_text, to_text)


@app.get("/lights/samples/json")
async def light_samples_json(
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(OutdoorLightSample, None, None, None, None, mode, None, from_text, to_text, limit)
    return {"count": len(rows), "rows": [row_to_dict(row, LIGHT_SAMPLE_COLUMNS) for row in rows]}


@app.get("/lys/lux-logging", response_class=HTMLResponse)
async def light_samples_view(
    request: Request,
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 500,
):
    rows, limit = await fetch_rows(OutdoorLightSample, None, None, None, None, mode, None, from_text, to_text, limit)
    filters = {"mode": mode or "", "from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "light_samples.html", {"rows": rows, "filters": filters})


@app.get("/lights/samples/download")
async def light_samples_download(
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(OutdoorLightSample, LIGHT_SAMPLE_COLUMNS, "utelys_samples.csv", None, None, None, None, mode, None, from_text, to_text)


@app.get("/ventilasjon/hendelser", response_class=HTMLResponse)
async def ventilation_view(
    request: Request,
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_key: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 300,
):
    rows, limit = await fetch_rows(VentilationEvent, "fan_change", action, device_key, device_id, mode, source_contains, from_text, to_text, limit)
    filters = {"event_type": "fan_change", "action": action or "", "device_key": device_key or "", "device_id": device_id or "", "mode": mode or "", "source_contains": source_contains or "", "from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "ventilation.html", {"rows": rows, "filters": filters})


@app.get("/ventilation/json")
async def ventilation_json(
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_key: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(VentilationEvent, "fan_change", action, device_key, device_id, mode, source_contains, from_text, to_text, limit)
    return {"count": len(rows), "rows": [row_to_dict(row, VENT_COLUMNS) for row in rows]}


@app.get("/ventilation/download")
async def ventilation_download(
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_key: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(VentilationEvent, VENT_COLUMNS, "ventilasjon_events.csv", "fan_change", action, device_key, device_id, mode, source_contains, from_text, to_text)


@app.get("/ventilasjon/temp-logg", response_class=HTMLResponse)
async def ventilation_samples_view(
    request: Request,
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 500,
):
    rows, limit = await fetch_rows(VentilationSample, None, None, None, None, mode, None, from_text, to_text, limit)
    filters = {"mode": mode or "", "from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "ventilation_samples.html", {"rows": rows, "filters": filters})


@app.get("/ventilation/samples/json")
async def ventilation_samples_json(
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(VentilationSample, None, None, None, None, mode, None, from_text, to_text, limit)
    return {"count": len(rows), "rows": [row_to_dict(row, VENT_SAMPLE_COLUMNS) for row in rows]}


@app.get("/ventilation/samples/download")
async def ventilation_samples_download(
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(VentilationSample, VENT_SAMPLE_COLUMNS, "ventilasjon_samples.csv", None, None, None, None, mode, None, from_text, to_text)


@app.get("/ventilasjon/yr-logg", response_class=HTMLResponse)
async def yr_samples_view(
    request: Request,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 500,
):
    rows, limit = await fetch_rows(YrForecastSample, None, None, None, None, None, None, from_text, to_text, limit)
    filters = {"from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "yr_samples.html", {"rows": rows, "filters": filters})


@app.get("/yr/samples/json")
async def yr_samples_json(
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(YrForecastSample, None, None, None, None, None, None, from_text, to_text, limit)
    return {"count": len(rows), "rows": [row_to_dict(row, YR_SAMPLE_COLUMNS) for row in rows]}


@app.get("/yr/samples/download")
async def yr_samples_download(
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(YrForecastSample, YR_SAMPLE_COLUMNS, "yr_forecast_samples.csv", None, None, None, None, None, None, from_text, to_text)


@app.get("/download")
@app.get("/events/download")
async def generic_download():
    return await csv_response(GenericEvent, GENERIC_COLUMNS, "event_data.csv", None, None, None, None, None, None, None, None)


@app.get("/events/json")
async def events_json(limit: int = 1000):
    limit = max(1, min(limit, 10000))
    async with async_session() as session:
        result = await session.execute(select(GenericEvent).order_by(GenericEvent.timestamp.desc()).limit(limit))
        rows = result.scalars().all()
    return {"count": len(rows), "rows": [row_to_dict(row, GENERIC_COLUMNS) for row in rows]}
