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

app = FastAPI()

# Statisk og templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Databaseoppsett
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String, default="unknown")


class EventData(Base):
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

    temp_1etg = Column(Float, nullable=True)
    temp_2etg = Column(Float, nullable=True)
    temp_vip = Column(Float, nullable=True)
    temp_ute = Column(Float, nullable=True)
    temp_loft = Column(Float, nullable=True)
    temp_passiv = Column(Float, nullable=True)
    temp_luftinntak = Column(Float, nullable=True)
    lux = Column(Float, nullable=True)
    diff_w = Column(Float, nullable=True)
    power_w = Column(Float, nullable=True)
    energy_kwh = Column(Float, nullable=True)
    value = Column(Float, nullable=True)

    fan_vip = Column(Boolean, nullable=True)
    fan_2etg = Column(Boolean, nullable=True)
    fan_tak = Column(Boolean, nullable=True)
    state = Column(Boolean, nullable=True)

    extra = Column(JSON, nullable=True)


class SensorDataIn(BaseModel):
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


EVENT_COLUMNS = [
    "id",
    "timestamp",
    "system",
    "event_type",
    "action",
    "device_id",
    "device_name",
    "mode",
    "reason",
    "source",
    "temp_1etg",
    "temp_2etg",
    "temp_vip",
    "temp_ute",
    "temp_loft",
    "temp_passiv",
    "temp_luftinntak",
    "lux",
    "diff_w",
    "power_w",
    "energy_kwh",
    "value",
    "fan_vip",
    "fan_2etg",
    "fan_tak",
    "state",
    "extra",
]


def value_from_payload(data: EventDataIn, key: str):
    explicit = getattr(data, key)
    if explicit is not None:
        return explicit
    return data.values.get(key)


def event_to_dict(row: EventData) -> Dict[str, Any]:
    out = {column: getattr(row, column) for column in EVENT_COLUMNS if column != "extra"}
    out["timestamp"] = row.timestamp.isoformat() if row.timestamp else None
    out["extra"] = row.extra or {}
    return out


def apply_event_filters(
    stmt,
    system: Optional[str],
    event_type: Optional[str],
    action: Optional[str],
    device_id: Optional[int],
    mode: Optional[str],
    source: Optional[str],
    source_contains: Optional[str],
    from_ts: Optional[datetime],
    to_ts: Optional[datetime],
):
    if system:
        stmt = stmt.where(EventData.system == system)
    if event_type:
        stmt = stmt.where(EventData.event_type == event_type)
    if action:
        stmt = stmt.where(EventData.action == action)
    if device_id is not None:
        stmt = stmt.where(EventData.device_id == device_id)
    if mode:
        stmt = stmt.where(EventData.mode == mode)
    if source:
        stmt = stmt.where(EventData.source == source)
    if source_contains:
        stmt = stmt.where(EventData.source.ilike(f"%{source_contains}%"))
    if from_ts:
        stmt = stmt.where(EventData.timestamp >= from_ts)
    if to_ts:
        stmt = stmt.where(EventData.timestamp <= to_ts)
    return stmt


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/log")
async def log_data(data: SensorDataIn):
    async with async_session() as session:
        record = SensorData(
            temperature=data.temperature,
            humidity=data.humidity,
            timestamp=data.timestamp,
            source=data.source,
        )
        session.add(record)
        await session.commit()
    return {"status": "ok"}


@app.post("/events")
async def log_event(data: EventDataIn):
    merged_extra = dict(data.extra or {})
    if data.values:
        merged_extra["values"] = data.values

    async with async_session() as session:
        record = EventData(
            timestamp=data.timestamp or datetime.utcnow(),
            system=data.system,
            event_type=data.event_type,
            action=data.action,
            device_id=data.device_id,
            device_name=data.device_name,
            mode=data.mode,
            reason=data.reason,
            source=data.source,
            temp_1etg=value_from_payload(data, "temp_1etg"),
            temp_2etg=value_from_payload(data, "temp_2etg"),
            temp_vip=value_from_payload(data, "temp_vip"),
            temp_ute=value_from_payload(data, "temp_ute"),
            temp_loft=value_from_payload(data, "temp_loft"),
            temp_passiv=value_from_payload(data, "temp_passiv"),
            temp_luftinntak=value_from_payload(data, "temp_luftinntak"),
            lux=value_from_payload(data, "lux"),
            diff_w=value_from_payload(data, "diff_w"),
            power_w=value_from_payload(data, "power_w"),
            energy_kwh=value_from_payload(data, "energy_kwh"),
            value=value_from_payload(data, "value"),
            fan_vip=value_from_payload(data, "fan_vip"),
            fan_2etg=value_from_payload(data, "fan_2etg"),
            fan_tak=value_from_payload(data, "fan_tak"),
            state=value_from_payload(data, "state"),
            extra=merged_extra or None,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
    return {"status": "ok", "id": record.id}


@app.get("/", response_class=HTMLResponse)
async def read_data(request: Request, source: str = None, source_contains: str = None, limit: int = 100):
    limit = max(1, min(limit, 1000))
    stmt = select(SensorData).order_by(SensorData.timestamp.desc()).limit(limit)
    if source:
        stmt = stmt.where(SensorData.source == source)
    if source_contains:
        stmt = stmt.where(SensorData.source.ilike(f"%{source_contains}%"))

    async with async_session() as session:
        result = await session.execute(stmt)
        rows = result.scalars().all()

    return templates.TemplateResponse(
        "table.html",
        {
            "request": request,
            "rows": rows,
            "source": source or "",
            "source_contains": source_contains or "",
            "limit": limit,
        },
    )


@app.get("/download")
async def download_csv(source: str = None, source_contains: str = None):
    stmt = select(SensorData).order_by(SensorData.timestamp.desc())
    if source:
        stmt = stmt.where(SensorData.source == source)
    if source_contains:
        stmt = stmt.where(SensorData.source.ilike(f"%{source_contains}%"))

    async with async_session() as session:
        result = await session.execute(stmt)
        rows = result.scalars().all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "temperature", "humidity", "timestamp", "source"])
    for row in rows:
        writer.writerow([row.id, row.temperature, row.humidity, row.timestamp, row.source])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )


@app.get("/events", response_class=HTMLResponse)
async def read_events(
    request: Request,
    system: Optional[str] = None,
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_ts: Optional[datetime] = Query(default=None, alias="from"),
    to_ts: Optional[datetime] = Query(default=None, alias="to"),
    limit: int = 200,
):
    limit = max(1, min(limit, 5000))
    stmt = select(EventData).order_by(EventData.timestamp.desc()).limit(limit)
    stmt = apply_event_filters(stmt, system, event_type, action, device_id, mode, source, source_contains, from_ts, to_ts)

    async with async_session() as session:
        result = await session.execute(stmt)
        rows = result.scalars().all()

    return templates.TemplateResponse(
        "events.html",
        {
            "request": request,
            "rows": rows,
            "filters": {
                "system": system or "",
                "event_type": event_type or "",
                "action": action or "",
                "device_id": device_id or "",
                "mode": mode or "",
                "source": source or "",
                "source_contains": source_contains or "",
                "from": from_ts.isoformat() if from_ts else "",
                "to": to_ts.isoformat() if to_ts else "",
                "limit": limit,
            },
        },
    )


@app.get("/events/download")
async def download_events_csv(
    system: Optional[str] = None,
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_ts: Optional[datetime] = Query(default=None, alias="from"),
    to_ts: Optional[datetime] = Query(default=None, alias="to"),
):
    stmt = select(EventData).order_by(EventData.timestamp.desc())
    stmt = apply_event_filters(stmt, system, event_type, action, device_id, mode, source, source_contains, from_ts, to_ts)

    async with async_session() as session:
        result = await session.execute(stmt)
        rows = result.scalars().all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(EVENT_COLUMNS)
    for row in rows:
        row_dict = event_to_dict(row)
        writer.writerow([json_value(row_dict.get(column)) for column in EVENT_COLUMNS])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=events.csv"},
    )


@app.get("/events/json")
async def events_json(
    system: Optional[str] = None,
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_ts: Optional[datetime] = Query(default=None, alias="from"),
    to_ts: Optional[datetime] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    limit = max(1, min(limit, 10000))
    stmt = select(EventData).order_by(EventData.timestamp.desc()).limit(limit)
    stmt = apply_event_filters(stmt, system, event_type, action, device_id, mode, source, source_contains, from_ts, to_ts)

    async with async_session() as session:
        result = await session.execute(stmt)
        rows = result.scalars().all()

    return {"count": len(rows), "rows": [event_to_dict(row) for row in rows]}


def json_value(value):
    if isinstance(value, (dict, list)):
        import json

        return json.dumps(value, ensure_ascii=False)
    return value
