from datetime import date, datetime, time, timedelta
from io import StringIO
from typing import Any, Dict, Optional
import csv
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
LOCAL_TZ = ZoneInfo("Europe/Oslo")

app = FastAPI(title="Fibaro10")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


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
    "light_lyslist", "light_reklame", "light_spot_inngang", "light_parkering", "extra",
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
    {"id": 275, "name": "Spot foran glassvegg", "extra_key": "light_spot_glass_275"},
    {"id": 299, "name": "Spot foran massasje", "extra_key": "light_spot_glass_299"},
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
    if attr:
        value = getattr(row, attr, None)
    else:
        extra = row.extra or {}
        value = extra.get(device.get("extra_key"))
        if value is None and isinstance(extra.get("values"), dict):
            value = extra["values"].get(device.get("extra_key"))
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


@app.get("/health")
async def health():
    return {"status": "ok", "storage": ["utelys_events", "utelys_samples", "ventilasjon_events", "ventilasjon_samples", "event_data"]}


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
    for group_name, items in [("Ute lys", light_items), ("Ventilasjon", vent_items)]:
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
