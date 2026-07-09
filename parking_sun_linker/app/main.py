from __future__ import annotations

import asyncio
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy import BigInteger, Column, DateTime, Float, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
FIBARO10_BASE_URL = os.getenv("FIBARO10_BASE_URL", "http://fibaro10:8110").rstrip("/")
KOBLE_WORKER_TOKEN = (os.getenv("KOBLE_WORKER_TOKEN") or os.getenv("CAR_INFO_APP_TOKEN") or "").strip()
HTTP_TIMEOUT_SECONDS = max(5, int(os.getenv("KOBLE_HTTP_TIMEOUT_SECONDS", "30")))
RUN_ON_START = os.getenv("KOBLE_RUN_ON_START", "true").strip().lower() in {"1", "true", "yes", "ja"}
LOOP_SLEEP_SECONDS = max(0.05, float(os.getenv("KOBLE_LOOP_SLEEP_SECONDS", "0.2")))
BATCH_SIZE = max(1, min(100, int(os.getenv("KOBLE_BATCH_SIZE", "25"))))

Base = declarative_base()
app = FastAPI(title="Fibaro10 parking sun linker")
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
async_session = async_sessionmaker(engine, expire_on_commit=False) if engine else None
worker_task: asyncio.Task | None = None

state: dict[str, Any] = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "running": False,
    "generation": None,
    "last_action": "init",
    "last_success_at": None,
    "last_error": None,
    "last_parking_id": None,
    "last_plate": None,
    "last_config": None,
    "processed_since_start": 0,
    "matches_since_start": 0,
}


class ParkingSession(Base):
    __tablename__ = "parkering"

    id = Column(BigInteger, primary_key=True)
    source_system = Column(Text)
    parking_id = Column(BigInteger)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    fee_inc_vat = Column(Float)
    car_license_number = Column(Text)
    status = Column(Text)


class Sun2TanningSession(Base):
    __tablename__ = "sun2_tanning_sessions"

    id = Column(Integer, primary_key=True)
    source_session_id = Column(String)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    room_id = Column(String)
    room = Column(String)
    sun2_user_id = Column(String)
    user_name = Column(String)
    duration_minutes = Column(Float)
    paid_amount_kr = Column(Float)


class ParkingSunLinkProcessed(Base):
    __tablename__ = "parking_sun_link_processed"

    id = Column(Integer, primary_key=True)
    generation = Column(Integer)
    parking_record_id = Column(BigInteger)
    plate = Column(Text)
    parking_start_at = Column(DateTime)
    matches_found = Column(Integer)
    checked_at = Column(DateTime)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def set_state(**values: Any) -> None:
    state.update(values)


def compact_plate(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(value or "")).upper()


def iso_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def fibaro_request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{FIBARO10_BASE_URL}{path}"
    headers = {"x-koble-token": KOBLE_WORKER_TOKEN}
    response = requests.request(method, url, json=payload, headers=headers, timeout=HTTP_TIMEOUT_SECONDS)
    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()


async def fibaro_get(path: str) -> dict[str, Any]:
    return await asyncio.to_thread(fibaro_request, "GET", path, None)


async def fibaro_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(fibaro_request, "POST", path, payload)


async def post_status(config: dict[str, Any], status: str, status_text: str, last_error: str | None = None) -> None:
    payload = {
        "generation": int(config.get("generation") or 1),
        "status": status,
        "status_text": status_text,
        "last_error": last_error,
        "last_processed_parking_id": state.get("last_parking_id"),
        "last_processed_plate": state.get("last_plate"),
        "raw": {
            "worker": "parking_sun_linker",
            "last_action": state.get("last_action"),
            "processed_since_start": state.get("processed_since_start"),
            "matches_since_start": state.get("matches_since_start"),
        },
    }
    try:
        await fibaro_post("/api/koble/worker/status", payload)
        if last_error:
            set_state(last_error=last_error)
        else:
            set_state(last_success_at=utcnow_iso(), last_error=None)
    except Exception as exc:
        set_state(last_error=f"Statusrapport feilet: {exc}")


async def next_parkings(session, config: dict[str, Any], limit: int) -> list[tuple[ParkingSession, str]]:
    generation = int(config.get("generation") or 1)
    recent_days = max(0, int(config.get("recent_days") or 0))
    plate_expr = func.upper(func.replace(func.coalesce(ParkingSession.car_license_number, ""), " ", ""))
    processed_ids = (
        select(ParkingSunLinkProcessed.parking_record_id)
        .where(ParkingSunLinkProcessed.generation == generation)
        .subquery()
    )
    stmt = (
        select(ParkingSession, plate_expr.label("plate"))
        .where(ParkingSession.start_time.is_not(None))
        .where(plate_expr != "")
        .where(~ParkingSession.id.in_(select(processed_ids.c.parking_record_id)))
        .order_by(ParkingSession.start_time.desc(), ParkingSession.id.desc())
        .limit(limit)
    )
    if recent_days > 0:
        recent_cutoff = datetime.now() - timedelta(days=recent_days)
        active_plates = (
            select(plate_expr.label("plate"))
            .where(ParkingSession.start_time >= recent_cutoff)
            .where(plate_expr != "")
            .distinct()
            .subquery()
        )
        stmt = stmt.where(plate_expr.in_(select(active_plates.c.plate)))
    rows = (await session.execute(stmt)).all()
    return [(row[0], compact_plate(row.plate)) for row in rows if compact_plate(row.plate)]


async def session_matches(session, parking: ParkingSession, plate: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    max_minutes = max(1, int(config.get("max_minutes") or 3))
    if not parking.start_time:
        return []
    end_at = parking.start_time + timedelta(minutes=max_minutes)
    sun2_id_expr = func.trim(func.coalesce(Sun2TanningSession.sun2_user_id, ""))
    stmt = (
        select(Sun2TanningSession, sun2_id_expr.label("sun2_id"))
        .where(Sun2TanningSession.started_at >= parking.start_time)
        .where(Sun2TanningSession.started_at <= end_at)
        .where(sun2_id_expr != "")
        .order_by(Sun2TanningSession.started_at.asc(), Sun2TanningSession.id.asc())
    )
    rows = (await session.execute(stmt)).all()
    matches: list[dict[str, Any]] = []
    for row in rows:
        sun_session: Sun2TanningSession = row[0]
        delta_minutes = None
        if sun_session.started_at and parking.start_time:
            delta_minutes = round((sun_session.started_at - parking.start_time).total_seconds() / 60.0, 3)
        matches.append(
            {
                "generation": int(config.get("generation") or 1),
                "plate": plate,
                "sun2_id": str(row.sun2_id or "").strip(),
                "parking_record_id": int(parking.id),
                "parking_id": int(parking.parking_id) if parking.parking_id is not None else None,
                "source_system": parking.source_system,
                "parking_start_at": iso_value(parking.start_time),
                "sun_session_id": int(sun_session.id),
                "source_session_id": sun_session.source_session_id,
                "sun_started_at": iso_value(sun_session.started_at),
                "room_id": sun_session.room_id,
                "room": sun_session.room,
                "user_name": sun_session.user_name,
                "duration_minutes": sun_session.duration_minutes,
                "paid_amount_kr": sun_session.paid_amount_kr,
                "fee_inc_vat": parking.fee_inc_vat,
                "delta_minutes": delta_minutes,
            }
        )
    return matches


async def process_batch(config: dict[str, Any]) -> bool:
    if async_session is None:
        raise RuntimeError("DATABASE_URL mangler")
    async with async_session() as session:
        items = await next_parkings(session, config, BATCH_SIZE)
        if not items:
            return False
        processed_rows: list[dict[str, Any]] = []
        match_rows: list[dict[str, Any]] = []
        for parking, plate in items:
            matches = await session_matches(session, parking, plate, config)
            processed_rows.append(
                {
                    "generation": int(config.get("generation") or 1),
                    "parking_record_id": int(parking.id),
                    "plate": plate,
                    "parking_start_at": iso_value(parking.start_time),
                    "matches_found": len(matches),
                }
            )
            match_rows.extend(matches)
    last_processed = processed_rows[-1]
    payload = {
        "generation": int(config.get("generation") or 1),
        "processed": processed_rows,
        "matches": match_rows,
        "status": {
            "generation": int(config.get("generation") or 1),
            "status": "kjorer",
            "status_text": (
                f"Behandlet {len(processed_rows)} parkeringer. "
                f"Siste {last_processed['plate']} {last_processed['parking_start_at']}."
            ),
            "raw": {"worker": "parking_sun_linker", "batch_size": len(processed_rows)},
        },
    }
    await fibaro_post("/api/koble/worker/results", payload)
    set_state(
        last_action="processed",
        last_success_at=utcnow_iso(),
        last_error=None,
        last_parking_id=int(last_processed["parking_record_id"]),
        last_plate=last_processed["plate"],
        processed_since_start=int(state.get("processed_since_start") or 0) + len(processed_rows),
        matches_since_start=int(state.get("matches_since_start") or 0) + len(match_rows),
    )
    return True


async def worker_loop() -> None:
    set_state(running=True, last_action="start")
    while True:
        config: dict[str, Any] = {}
        try:
            config = await fibaro_get("/api/koble/worker/config")
            generation = int(config.get("generation") or 1)
            if state.get("generation") != generation:
                set_state(generation=generation, processed_since_start=0, matches_since_start=0)
            set_state(last_config=config, last_action="config")
            if not config.get("enabled"):
                await post_status(config, "stoppet", "Worker er klar, men jobben er stoppet i Fibaro10.")
                await asyncio.sleep(max(5, int(config.get("idle_sleep_seconds") or 20)))
                continue
            processed = await process_batch(config)
            if processed:
                await asyncio.sleep(LOOP_SLEEP_SECONDS)
                continue
            await post_status(config, "ajour", "Ingen flere ubehandlede parkeringer i gjeldende utvalg.")
            await asyncio.sleep(max(5, int(config.get("idle_sleep_seconds") or 20)))
        except asyncio.CancelledError:
            set_state(running=False, last_action="cancelled")
            raise
        except Exception as exc:
            set_state(last_action="error", last_error=str(exc))
            if config:
                await post_status(config, "feil", f"Koblingsworker feilet: {exc}", str(exc))
            await asyncio.sleep(30)


@app.on_event("startup")
async def startup() -> None:
    global worker_task
    if RUN_ON_START:
        worker_task = asyncio.create_task(worker_loop())


@app.on_event("shutdown")
async def shutdown() -> None:
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": not state.get("last_error"),
        "time": utcnow_iso(),
        "state": state,
        "fibaro10_base_url": FIBARO10_BASE_URL,
        "has_database_url": bool(DATABASE_URL),
        "has_token": bool(KOBLE_WORKER_TOKEN),
        "batch_size": BATCH_SIZE,
    }


@app.get("/")
async def root() -> dict[str, Any]:
    return await health()
