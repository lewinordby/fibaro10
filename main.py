from datetime import date, datetime, time, timedelta
from io import StringIO
from typing import Any, Dict, Optional
import csv
import hashlib
import math
import os
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text, select, update
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
PUBLIC_PATHS = {"/health", "/auth/login"}

app = FastAPI(title="Fibaro10")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
        await log_access_attempt(request, False, "missing_or_invalid_key")
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
    request.state.auth_is_master = bool(access_key.is_master)
    await log_access_attempt(request, True, "ok", access_key)
    return await call_next(request)


class OutdoorLightEvent(Base):
    __tablename__ = "utelys_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True, default="device_change")
    action = Column(String, index=True, nullable=True)
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
    extra = Column(JSON, nullable=True)


class VentilationEvent(Base):
    __tablename__ = "ventilasjon_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True, default="fan_change")
    action = Column(String, index=True, nullable=True)
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


class GenericEvent(Base):
    __tablename__ = "event_data"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    system = Column(String, index=True, nullable=False)
    event_type = Column(String, index=True, default="status")
    action = Column(String, index=True, nullable=True)
    device_id = Column(Integer, index=True, nullable=True)
    device_name = Column(String, nullable=True)
    mode = Column(String, index=True, nullable=True)
    reason = Column(Text, nullable=True)
    source = Column(Text, nullable=True)
    lux = Column(Float, nullable=True)
    value = Column(Float, nullable=True)
    state = Column(Boolean, nullable=True)
    extra = Column(JSON, nullable=True)


class AccessKey(Base):
    __tablename__ = "access_keys"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    key_hash = Column(String, unique=True, index=True, nullable=False)
    key_prefix = Column(String, index=True, nullable=False)
    key_plaintext = Column(String, nullable=True)
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


LIGHT_COLUMNS = [
    "id", "timestamp", "event_type", "action", "device_id", "device_name",
    "mode", "reason", "source", "lux", "value", "state", "extra",
]

LIGHT_SAMPLE_COLUMNS = [
    "id", "timestamp", "bucket_start", "mode", "source", "lux", "value",
    "light_lyslist", "light_reklame", "light_spot_glass_275", "light_spot_glass_299",
    "light_spot_inngang", "light_parkering", "extra",
]

VENT_COLUMNS = [
    "id", "timestamp", "event_type", "action", "device_id", "device_name",
    "mode", "reason", "source", "value", "state", "temp_1etg", "temp_2etg",
    "temp_vip", "temp_ute", "temp_loft", "temp_passiv", "temp_luftinntak",
    "diff_w", "power_w", "energy_kwh", "fan_vip", "fan_2etg", "fan_tak", "extra",
]

GENERIC_COLUMNS = [
    "id", "timestamp", "system", "event_type", "action", "device_id",
    "device_name", "mode", "reason", "source", "lux", "value", "state", "extra",
]

VENT_SAMPLE_COLUMNS = [
    "id", "timestamp", "bucket_start", "mode", "source", "temp_1etg", "temp_2etg",
    "temp_vip", "temp_ute", "temp_ute_netatmo", "temp_yr", "temp_loft", "temp_passiv",
    "temp_luftinntak", "temp_min_inne", "temp_avg_inne", "temp_max_inne", "diff_w",
    "estimated_sunbeds", "afterrun_active", "heat_need", "cool_need", "open_time",
    "pre_cooling", "exhaust_time_allowed", "fan_vip", "fan_2etg", "fan_tak", "extra",
]

LIGHT_TIMELINE_DEVICES = [
    {"id": 425, "name": "Lyslist dekor", "sample_attr": "light_lyslist"},
    {"id": 427, "name": "Reklameplakater", "sample_attr": "light_reklame"},
    {"id": 275, "name": "Spot foran glassvegg", "sample_attr": "light_spot_glass_275"},
    {"id": 299, "name": "Spot foran massasje", "sample_attr": "light_spot_glass_299"},
    {"id": 424, "name": "6xspot over inngang", "sample_attr": "light_spot_inngang"},
    {"id": 440, "name": "Parkeringslys/gatelys", "sample_attr": "light_parkering"},
]

VENT_TIMELINE_DEVICES = [
    {"id": 130, "name": "Innluft VIP"},
    {"id": 160, "name": "Innluft 2.etg"},
    {"id": 134, "name": "Avtrekk tak/loft"},
]


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


def hash_access_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_username(value: str) -> str:
    return value.strip().casefold()


def credential_hash(username: str, password: str) -> str:
    return hash_access_key(normalize_username(username) + "\0" + password)


def key_prefix(value: str) -> str:
    return "key_" + hash_access_key(value)[:8]


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
):
    async with async_session() as session:
        session.add(
            AccessLog(
                access_key_id=access_key.id if access_key else None,
                key_name=access_key.name if access_key else None,
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
    for axis_max, step in [(50, 5), (200, 20), (1000, 100), (2000, 200), (10000, 1000), (20000, 2000)]:
        if max_value <= axis_max:
            return {"max": float(axis_max), "step": step}
    return {"max": 20000.0, "step": 2000}


def lux_y(value: float, max_lux: float) -> float:
    graph_top = 22
    graph_bottom = 278
    usable = graph_bottom - graph_top
    if max_lux <= 0:
        return graph_bottom
    scaled_value = math.sqrt(max(0, value))
    scaled_max = math.sqrt(max_lux)
    return round(graph_bottom - max(0, min(1, scaled_value / scaled_max)) * usable, 2)


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
        "id": device["id"],
        "name": device["name"],
        "segments": display_segments(raw_segments, day_start, day_end),
        "points": points,
        "total": total_from_segments(raw_segments),
    }


async def build_timeline_group(model, devices, system: str, day_start: datetime, day_end: datetime, timeline_end: datetime):
    device_ids = [device["id"] for device in devices]
    async with async_session() as session:
        day_result = await session.execute(
            select(model)
            .where(model.device_id.in_(device_ids))
            .where(model.timestamp >= day_start)
            .where(model.timestamp < timeline_end)
            .order_by(model.timestamp.asc())
        )
        rows = day_result.scalars().all()
        previous = {}
        for device_id in device_ids:
            previous_result = await session.execute(
                select(model)
                .where(model.device_id == device_id)
                .where(model.timestamp < day_start)
                .order_by(model.timestamp.desc())
                .limit(1)
            )
            previous[device_id] = previous_result.scalars().first()

    rows_by_device = {device_id: [] for device_id in device_ids}
    for row in rows:
        rows_by_device.setdefault(row.device_id, []).append(row)

    return [
        build_timeline_item(device, rows_by_device.get(device["id"], []), previous.get(device["id"]), day_start, day_end, timeline_end, system)
        for device in devices
    ]


async def build_light_timeline_group(day_start: datetime, day_end: datetime, timeline_end: datetime):
    device_ids = [device["id"] for device in LIGHT_TIMELINE_DEVICES]
    async with async_session() as session:
        event_result = await session.execute(
            select(OutdoorLightEvent)
            .where(OutdoorLightEvent.device_id.in_(device_ids))
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
        for device_id in device_ids:
            previous_event_result = await session.execute(
                select(OutdoorLightEvent)
                .where(OutdoorLightEvent.device_id == device_id)
                .where(OutdoorLightEvent.timestamp < day_start)
                .order_by(OutdoorLightEvent.timestamp.desc())
                .limit(1)
            )
            previous_events[device_id] = previous_event_result.scalars().first()

    events_by_device = {device_id: [] for device_id in device_ids}
    for row in event_rows:
        events_by_device.setdefault(row.device_id, []).append(row)

    items = []
    for device in LIGHT_TIMELINE_DEVICES:
        state = light_sample_state(previous_sample, device) if previous_sample else None
        if state is None and previous_events.get(device["id"]):
            state = state_from_event(previous_events[device["id"]])
        if state is None:
            state = False
        cursor = day_start
        raw_segments = []
        points = [point_from_row(row, day_start, day_end, "lys") for row in events_by_device.get(device["id"], [])]
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

        for row in events_by_device.get(device["id"], []):
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
            "id": device["id"],
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
            "label": f"{value:g}",
            "value": value,
            "y": lux_y(float(value), max_lux),
        }
        for value in range(scale["step"], int(max_lux) + 1, scale["step"])
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
    }
    return {
        "points": points,
        "polyline": polyline,
        "y_ticks": y_ticks,
        "samples_desc": list(reversed(samples)),
        "summary": summary,
    }


def row_to_dict(row, columns):
    out = {column: getattr(row, column) for column in columns if column != "extra"}
    out["timestamp"] = row.timestamp.isoformat() if row.timestamp else None
    if "bucket_start" in out and out["bucket_start"]:
        out["bucket_start"] = out["bucket_start"].isoformat()
    out["extra"] = row.extra or {}
    return out


def merged_extra(data: EventDataIn):
    extra = dict(data.extra or {})
    if data.values:
        extra["values"] = data.values
    return extra or None


def light_from_payload(data: EventDataIn) -> OutdoorLightEvent:
    return OutdoorLightEvent(
        timestamp=data.timestamp or datetime.utcnow(),
        event_type=data.event_type,
        action=data.action,
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


def light_sample_from_payload(data: EventDataIn) -> OutdoorLightSample:
    timestamp = data.timestamp or datetime.utcnow()
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
        extra=merged_extra(data),
    )


def vent_from_payload(data: EventDataIn) -> VentilationEvent:
    return VentilationEvent(
        timestamp=data.timestamp or datetime.utcnow(),
        event_type=data.event_type,
        action=data.action,
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


def apply_common_filters(stmt, model, event_type, action, device_id, mode, source_contains, from_ts, to_ts):
    if event_type:
        stmt = stmt.where(model.event_type == event_type)
    if action:
        stmt = stmt.where(model.action == action)
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


async def fetch_rows(model, event_type, action, device_id, mode, source_contains, from_text, to_text, limit):
    from_ts = parse_datetime(from_text)
    to_ts = parse_datetime(to_text)
    limit = max(1, min(limit, 10000))
    stmt = select(model).order_by(model.timestamp.desc()).limit(limit)
    stmt = apply_common_filters(stmt, model, event_type, action, device_id, mode, source_contains, from_ts, to_ts)
    async with async_session() as session:
        result = await session.execute(stmt)
        return result.scalars().all(), limit


async def csv_response(model, columns, filename, event_type, action, device_id, mode, source_contains, from_text, to_text):
    rows, _ = await fetch_rows(model, event_type, action, device_id, mode, source_contains, from_text, to_text, 10000)
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
        await conn.exec_driver_sql("ALTER TABLE utelys_samples ADD COLUMN IF NOT EXISTS light_spot_glass_275 BOOLEAN")
        await conn.exec_driver_sql("ALTER TABLE utelys_samples ADD COLUMN IF NOT EXISTS light_spot_glass_299 BOOLEAN")
        await conn.exec_driver_sql("ALTER TABLE access_keys ADD COLUMN IF NOT EXISTS key_plaintext VARCHAR")
    async with async_session() as session:
        result = await session.execute(select(AccessKey).where(AccessKey.key_hash == MASTER_ACCESS_KEY_HASH))
        master = result.scalars().first()
        if master:
            master.name = "master"
            master.key_prefix = "sun2_master"
            master.is_master = True
            master.active = True
        else:
            session.add(
                AccessKey(
                    name="master",
                    key_hash=MASTER_ACCESS_KEY_HASH,
                    key_prefix="sun2_master",
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
            if username and password:
                key.name = username
                key.key_hash = credential_hash(username, password)
                key.key_prefix = credential_prefix(username, password)
        await session.commit()


@app.get("/health")
async def health():
    return {"status": "ok", "storage": ["utelys_events", "utelys_samples", "ventilasjon_events", "ventilasjon_samples", "event_data"]}


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
        await log_access_attempt(request, False, "failed_login")
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Ugyldig brukernavn eller passord"},
            status_code=401,
        )
    response = RedirectResponse("/", status_code=303)
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


@app.post("/auth/logout")
async def logout():
    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie(AUTH_USER_COOKIE_NAME)
    response.delete_cookie(AUTH_COOKIE_NAME)
    return response


@app.get("/admin/keys", response_class=HTMLResponse)
async def keys_view(request: Request):
    forbidden = require_master(request)
    if forbidden:
        return forbidden
    async with async_session() as session:
        key_rows = (await session.execute(select(AccessKey).order_by(AccessKey.created_at.desc()))).scalars().all()
        log_rows = (await session.execute(select(AccessLog).order_by(AccessLog.timestamp.desc()).limit(200))).scalars().all()
    return templates.TemplateResponse(
        request,
        "keys.html",
        {"keys": key_rows, "logs": log_rows, "created_username": "", "created_key": "", "error": ""},
    )


@app.post("/admin/keys")
async def keys_create(request: Request):
    forbidden = require_master(request)
    if forbidden:
        return forbidden
    form = await parse_form_body(request)
    username = normalize_username(form.get("username") or form.get("name") or "")[:80]
    password = (form.get("password") or form.get("access_key") or "").strip()
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


@app.post("/admin/keys/disable")
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
    return RedirectResponse("/admin/keys", status_code=303)


@app.get("/", response_class=HTMLResponse)
@app.get("/events", response_class=HTMLResponse)
async def index(request: Request):
    async with async_session() as session:
        lights = (await session.execute(select(OutdoorLightEvent).order_by(OutdoorLightEvent.timestamp.desc()).limit(200))).scalars().all()
        light_samples = (await session.execute(select(OutdoorLightSample).order_by(OutdoorLightSample.timestamp.desc()).limit(1))).scalars().all()
        ventilation = (await session.execute(select(VentilationEvent).order_by(VentilationEvent.timestamp.desc()).limit(100))).scalars().all()
        samples = (await session.execute(select(VentilationSample).order_by(VentilationSample.timestamp.desc()).limit(1))).scalars().all()

    latest_light_by_device = {}
    for row in lights:
        if row.device_id is not None and row.device_id not in latest_light_by_device:
            latest_light_by_device[row.device_id] = row

    latest_vent_by_device = {}
    for row in ventilation:
        if row.device_id is not None and row.device_id not in latest_vent_by_device:
            latest_vent_by_device[row.device_id] = row

    latest_sample = samples[0] if samples else None
    latest_light_sample = light_samples[0] if light_samples else None
    fan_state_from_sample = {
        130: latest_sample.fan_vip if latest_sample else None,
        160: latest_sample.fan_2etg if latest_sample else None,
        134: latest_sample.fan_tak if latest_sample else None,
    }

    light_status = [
        {"id": device["id"], "name": device["name"], "row": latest_light_by_device.get(device["id"])}
        for device in LIGHT_TIMELINE_DEVICES
    ]
    vent_status = [
        {
            "id": device["id"],
            "name": device["name"],
            "row": latest_vent_by_device.get(device["id"]),
            "state": fan_state_from_sample.get(device["id"]),
        }
        for device in VENT_TIMELINE_DEVICES
    ]

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "latest_light": lights[0] if lights else None,
            "latest_light_sample": latest_light_sample,
            "latest_vent": ventilation[0] if ventilation else None,
            "latest_sample": latest_sample,
            "light_status": light_status,
            "vent_status": vent_status,
        },
    )


@app.get("/day", response_class=HTMLResponse)
async def day_view(request: Request, day: Optional[str] = None):
    selected_day = parse_day(day)
    day_start = datetime.combine(selected_day, time.min)
    day_end = day_start + timedelta(days=1)
    now_local = local_now_naive()
    is_today = selected_day == now_local.date()
    timeline_end = min(now_local, day_end) if is_today else day_end
    now_marker = percent_between(now_local, day_start, day_end) if is_today else None
    light_items = await build_light_timeline_group(day_start, day_end, timeline_end)
    vent_items = await build_timeline_group(VentilationEvent, VENT_TIMELINE_DEVICES, "ventilasjon", day_start, day_end, timeline_end)
    events = []
    for group_name, items in [("Lys", light_items), ("Ventilasjon", vent_items)]:
        for item in items:
            for point in item["points"]:
                events.append({**point, "group": group_name, "device": item["name"]})
    events.sort(key=lambda event: event["time"])
    return templates.TemplateResponse(
        request,
        "day.html",
        {
            "selected_day": selected_day.isoformat(),
            "prev_day": (selected_day - timedelta(days=1)).isoformat(),
            "next_day": (selected_day + timedelta(days=1)).isoformat(),
            "is_today": is_today,
            "now_marker": now_marker,
            "now_label": now_local.strftime("%H:%M") if is_today else "",
            "light_items": light_items,
            "vent_items": vent_items,
            "events": events,
            "ticks": [
                {"label": "00", "left": 0},
                {"label": "06", "left": 25},
                {"label": "12", "left": 50},
                {"label": "18", "left": 75},
                {"label": "24", "left": 100},
            ],
        },
    )


@app.get("/day/lux", response_class=HTMLResponse)
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
            event_id = await save_record(light_sample_from_payload(data))
            return {"status": "ok", "id": event_id, "table": "utelys_samples"}
        event_id = await save_record(light_from_payload(data))
        return {"status": "ok", "id": event_id, "table": "utelys_events"}
    if system in {"ventilasjon", "ventilation", "vent"}:
        if data.event_type in {"sample", "sample_5min", "sample_15min", "learning_sample"}:
            event_id = await save_record(vent_sample_from_payload(data))
            return {"status": "ok", "id": event_id, "table": "ventilasjon_samples"}
        event_id = await save_record(vent_from_payload(data))
        return {"status": "ok", "id": event_id, "table": "ventilasjon_events"}
    event_id = await save_record(generic_from_payload(data))
    return {"status": "ok", "id": event_id, "table": "event_data"}


@app.get("/lights", response_class=HTMLResponse)
async def lights_view(
    request: Request,
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 300,
):
    rows, limit = await fetch_rows(OutdoorLightEvent, event_type, action, device_id, mode, source_contains, from_text, to_text, limit)
    filters = {"event_type": event_type or "", "action": action or "", "device_id": device_id or "", "mode": mode or "", "source_contains": source_contains or "", "from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "lights.html", {"rows": rows, "filters": filters})


@app.get("/lights/json")
async def lights_json(
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(OutdoorLightEvent, event_type, action, device_id, mode, source_contains, from_text, to_text, limit)
    return {"count": len(rows), "rows": [row_to_dict(row, LIGHT_COLUMNS) for row in rows]}


@app.get("/lights/download")
async def lights_download(
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(OutdoorLightEvent, LIGHT_COLUMNS, "utelys_events.csv", event_type, action, device_id, mode, source_contains, from_text, to_text)


@app.get("/lights/samples/json")
async def light_samples_json(
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(OutdoorLightSample, None, None, None, mode, None, from_text, to_text, limit)
    return {"count": len(rows), "rows": [row_to_dict(row, LIGHT_SAMPLE_COLUMNS) for row in rows]}


@app.get("/lights/samples", response_class=HTMLResponse)
async def light_samples_view(
    request: Request,
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 500,
):
    rows, limit = await fetch_rows(OutdoorLightSample, None, None, None, mode, None, from_text, to_text, limit)
    filters = {"mode": mode or "", "from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "light_samples.html", {"rows": rows, "filters": filters})


@app.get("/lights/samples/download")
async def light_samples_download(
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(OutdoorLightSample, LIGHT_SAMPLE_COLUMNS, "utelys_samples.csv", None, None, None, mode, None, from_text, to_text)


@app.get("/ventilation", response_class=HTMLResponse)
async def ventilation_view(
    request: Request,
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 300,
):
    rows, limit = await fetch_rows(VentilationEvent, "fan_change", action, device_id, mode, source_contains, from_text, to_text, limit)
    filters = {"event_type": "fan_change", "action": action or "", "device_id": device_id or "", "mode": mode or "", "source_contains": source_contains or "", "from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "ventilation.html", {"rows": rows, "filters": filters})


@app.get("/ventilation/json")
async def ventilation_json(
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(VentilationEvent, "fan_change", action, device_id, mode, source_contains, from_text, to_text, limit)
    return {"count": len(rows), "rows": [row_to_dict(row, VENT_COLUMNS) for row in rows]}


@app.get("/ventilation/download")
async def ventilation_download(
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(VentilationEvent, VENT_COLUMNS, "ventilasjon_events.csv", "fan_change", action, device_id, mode, source_contains, from_text, to_text)


@app.get("/ventilation/samples", response_class=HTMLResponse)
async def ventilation_samples_view(
    request: Request,
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 500,
):
    rows, limit = await fetch_rows(VentilationSample, None, None, None, mode, None, from_text, to_text, limit)
    filters = {"mode": mode or "", "from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "ventilation_samples.html", {"rows": rows, "filters": filters})


@app.get("/ventilation/samples/json")
async def ventilation_samples_json(
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(VentilationSample, None, None, None, mode, None, from_text, to_text, limit)
    return {"count": len(rows), "rows": [row_to_dict(row, VENT_SAMPLE_COLUMNS) for row in rows]}


@app.get("/ventilation/samples/download")
async def ventilation_samples_download(
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(VentilationSample, VENT_SAMPLE_COLUMNS, "ventilasjon_samples.csv", None, None, None, mode, None, from_text, to_text)


@app.get("/download")
@app.get("/events/download")
async def generic_download():
    return await csv_response(GenericEvent, GENERIC_COLUMNS, "event_data.csv", None, None, None, None, None, None, None)


@app.get("/events/json")
async def events_json(limit: int = 1000):
    limit = max(1, min(limit, 10000))
    async with async_session() as session:
        result = await session.execute(select(GenericEvent).order_by(GenericEvent.timestamp.desc()).limit(limit))
        rows = result.scalars().all()
    return {"count": len(rows), "rows": [row_to_dict(row, GENERIC_COLUMNS) for row in rows]}
