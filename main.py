from datetime import datetime
from io import StringIO
from typing import Any, Dict, Optional
import csv
import os

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

    temp_1etg: Optional[float] = None
    temp_2etg: Optional[float] = None
    temp_vip: Optional[float] = None
    temp_ute: Optional[float] = None
    temp_loft: Optional[float] = None
    temp_passiv: Optional[float] = None
    temp_luftinntak: Optional[float] = None
    lux: Optional[float] = None
    diff_w: Optional[float] = None
    power_w: Optional[float] = None
    energy_kwh: Optional[float] = None
    value: Optional[float] = None

    fan_vip: Optional[bool] = None
    fan_2etg: Optional[bool] = None
    fan_tak: Optional[bool] = None
    state: Optional[bool] = None

    values: Dict[str, Any] = Field(default_factory=dict)
    extra: Dict[str, Any] = Field(default_factory=dict)


LIGHT_COLUMNS = [
    "id", "timestamp", "event_type", "action", "device_id", "device_name",
    "mode", "reason", "source", "lux", "value", "state", "extra",
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


def row_to_dict(row, columns):
    out = {column: getattr(row, column) for column in columns if column != "extra"}
    out["timestamp"] = row.timestamp.isoformat() if row.timestamp else None
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
    return {"status": "ok", "storage": ["utelys_events", "ventilasjon_events", "event_data"]}


@app.get("/", response_class=HTMLResponse)
@app.get("/events", response_class=HTMLResponse)
async def index(request: Request):
    async with async_session() as session:
        lights = (await session.execute(select(OutdoorLightEvent).order_by(OutdoorLightEvent.timestamp.desc()).limit(1))).scalars().all()
        ventilation = (await session.execute(select(VentilationEvent).order_by(VentilationEvent.timestamp.desc()).limit(1))).scalars().all()
    return templates.TemplateResponse(request, "index.html", {"latest_light": lights[0] if lights else None, "latest_vent": ventilation[0] if ventilation else None})


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
        event_id = await save_record(light_from_payload(data))
        return {"status": "ok", "id": event_id, "table": "utelys_events"}
    if system in {"ventilasjon", "ventilation", "vent"}:
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
    rows, limit = await fetch_rows(VentilationEvent, event_type, action, device_id, mode, source_contains, from_text, to_text, limit)
    filters = {"event_type": event_type or "", "action": action or "", "device_id": device_id or "", "mode": mode or "", "source_contains": source_contains or "", "from": from_text or "", "to": to_text or "", "limit": limit}
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
    rows, _ = await fetch_rows(VentilationEvent, event_type, action, device_id, mode, source_contains, from_text, to_text, limit)
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
    return await csv_response(VentilationEvent, VENT_COLUMNS, "ventilasjon_events.csv", event_type, action, device_id, mode, source_contains, from_text, to_text)


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
