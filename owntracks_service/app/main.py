from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
import base64
import hashlib
import json
import logging
import math
import os
import threading
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    func,
    or_,
    select,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .build_log import owntracks_build_log_payload, owntracks_build_summary


load_dotenv()

logger = logging.getLogger("owntracks_service")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

DATA_DIR = Path(os.getenv("OWNTRACKS_DATA_DIR", "/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("OWNTRACKS_DATABASE_URL", f"sqlite:///{DATA_DIR / 'owntracks.db'}")

HTTP_TOKEN = (os.getenv("OWNTRACKS_HTTP_TOKEN") or os.getenv("CAR_INFO_APP_TOKEN") or "").strip()
DEFAULT_TOPIC_USERNAME = os.getenv("OWNTRACKS_HTTP_DEFAULT_USER", "http").strip() or "http"
DEFAULT_TOPIC_DEVICE = os.getenv("OWNTRACKS_HTTP_DEFAULT_DEVICE", "phone").strip() or "phone"
OWNTRACKS_PUBLIC_BASE_URL = os.getenv("OWNTRACKS_PUBLIC_BASE_URL", "https://owntracks.lilletorget.net").rstrip("/")

ZONE_VISIT_BUFFER_M = max(0.0, float(os.getenv("OWNTRACKS_ZONE_VISIT_BUFFER_M", "25")))
ZONE_VISIT_ACCURACY_CAP_M = max(0.0, float(os.getenv("OWNTRACKS_ZONE_VISIT_ACCURACY_CAP_M", "100")))

Base = declarative_base()
engine = create_engine(
    DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def iso_dt(value: Optional[datetime]) -> Optional[str]:
    if not value:
        return None
    if value.tzinfo is None:
        return value.isoformat() + "Z"
    return value.astimezone(timezone.utc).replace(tzinfo=None).isoformat() + "Z"


def float_value(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def int_value(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def json_string(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class OwnTracksDevice(Base):
    __tablename__ = "owntracks_devices"

    id = Column(Integer, primary_key=True)
    topic = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(120), nullable=True, index=True)
    device = Column(String(120), nullable=True, index=True)
    tracker_id = Column(String(80), nullable=True)
    last_seen_at = Column(DateTime, nullable=True, index=True)
    last_received_at = Column(DateTime, nullable=True, index=True)
    last_lat = Column(Float, nullable=True)
    last_lon = Column(Float, nullable=True)
    last_accuracy_m = Column(Float, nullable=True)
    last_battery_percent = Column(Float, nullable=True)
    last_connection = Column(String(40), nullable=True)
    last_event = Column(String(80), nullable=True)
    message_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=utc_now)


class OwnTracksLocation(Base):
    __tablename__ = "owntracks_locations"
    __table_args__ = (UniqueConstraint("message_hash", name="uq_owntracks_locations_message_hash"),)

    id = Column(Integer, primary_key=True)
    topic = Column(String(255), nullable=False, index=True)
    username = Column(String(120), nullable=True, index=True)
    device = Column(String(120), nullable=True, index=True)
    message_hash = Column(String(64), nullable=False)
    received_at = Column(DateTime, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=True, index=True)
    message_type = Column(String(80), nullable=True, index=True)
    event = Column(String(80), nullable=True, index=True)
    tracker_id = Column(String(80), nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    accuracy_m = Column(Float, nullable=True)
    velocity_kmh = Column(Float, nullable=True)
    battery_percent = Column(Float, nullable=True)
    connection = Column(String(40), nullable=True)
    regions = Column(JSON, nullable=True)
    payload = Column(JSON, nullable=False)


class OwnTracksWaypointState(Base):
    __tablename__ = "owntracks_waypoints"
    __table_args__ = (UniqueConstraint("topic", "waypoint_name", name="uq_owntracks_waypoints_topic_name"),)

    id = Column(Integer, primary_key=True)
    topic = Column(String(255), nullable=False, index=True)
    username = Column(String(120), nullable=True, index=True)
    device = Column(String(120), nullable=True, index=True)
    waypoint_name = Column(String(255), nullable=False, index=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    radius_m = Column(Float, nullable=True)
    accuracy_m = Column(Float, nullable=True)
    source_message_type = Column(String(80), nullable=True)
    last_state = Column(String(40), nullable=True, index=True)
    is_inside = Column(Boolean, nullable=True, index=True)
    last_event = Column(String(80), nullable=True)
    last_seen_at = Column(DateTime, nullable=True, index=True)
    last_event_at = Column(DateTime, nullable=True)
    last_location_id = Column(Integer, ForeignKey("owntracks_locations.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utc_now)


class OwnTracksWaypointEvent(Base):
    __tablename__ = "owntracks_waypoint_events"

    id = Column(Integer, primary_key=True)
    topic = Column(String(255), nullable=False, index=True)
    username = Column(String(120), nullable=True, index=True)
    device = Column(String(120), nullable=True, index=True)
    waypoint_name = Column(String(255), nullable=False, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    source_message_type = Column(String(80), nullable=True)
    timestamp = Column(DateTime, nullable=True, index=True)
    received_at = Column(DateTime, nullable=False, index=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    radius_m = Column(Float, nullable=True)
    accuracy_m = Column(Float, nullable=True)
    location_id = Column(Integer, ForeignKey("owntracks_locations.id", ondelete="CASCADE"), nullable=True)
    is_synthetic = Column(Boolean, nullable=False, default=False)
    payload = Column(JSON, nullable=True)


class OwnTracksZoneVisit(Base):
    __tablename__ = "owntracks_zone_visits"

    id = Column(Integer, primary_key=True)
    topic = Column(String(255), nullable=False, index=True)
    username = Column(String(120), nullable=True, index=True)
    device = Column(String(120), nullable=True, index=True)
    waypoint_name = Column(String(255), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False, index=True)
    ended_at = Column(DateTime, nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(String(40), nullable=False, default="open", index=True)
    start_lat = Column(Float, nullable=True)
    start_lon = Column(Float, nullable=True)
    end_lat = Column(Float, nullable=True)
    end_lon = Column(Float, nullable=True)
    last_lat = Column(Float, nullable=True)
    last_lon = Column(Float, nullable=True)
    radius_m = Column(Float, nullable=True)
    enter_source = Column(String(80), nullable=True)
    leave_source = Column(String(80), nullable=True)
    confidence = Column(Float, nullable=True)
    start_location_id = Column(Integer, ForeignKey("owntracks_locations.id", ondelete="SET NULL"), nullable=True)
    end_location_id = Column(Integer, ForeignKey("owntracks_locations.id", ondelete="SET NULL"), nullable=True)
    last_location_id = Column(Integer, ForeignKey("owntracks_locations.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utc_now)


class ServiceState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.last_message_at: Optional[datetime] = None
        self.last_store_error: Optional[str] = None
        self.messages_received = 0
        self.messages_stored = 0
        self.messages_duplicate = 0

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "lastMessageAt": iso_dt(self.last_message_at),
                "lastStoreError": self.last_store_error,
                "messagesReceived": self.messages_received,
                "messagesStored": self.messages_stored,
                "messagesDuplicate": self.messages_duplicate,
            }


STATE = ServiceState()


def topic_identity(topic: str) -> tuple[Optional[str], Optional[str]]:
    parts = [part for part in (topic or "").strip("/").split("/") if part]
    if len(parts) >= 3 and parts[0] == "owntracks":
        return parts[1], parts[2]
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return None, None


def topic_part(value: Optional[str], fallback: str) -> str:
    cleaned = re_topic_part(value)
    return cleaned or fallback


def re_topic_part(value: Optional[str]) -> str:
    raw = (value or "").strip().lower()
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in raw)
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    return cleaned[:80]


OWNTRACKS_TOPIC_SUFFIXES = {
    "beacon",
    "cmd",
    "dump",
    "event",
    "info",
    "step",
    "status",
    "waypoint",
    "waypoints",
}


def canonical_owntracks_topic(topic: str) -> str:
    cleaned = str(topic or "").strip().strip("/")
    parts = [part for part in cleaned.split("/") if part]
    if len(parts) >= 4 and parts[0] == "owntracks" and parts[3].lower() in OWNTRACKS_TOPIC_SUFFIXES:
        return "/".join(parts[:3])
    return cleaned


def http_topic(request: Request, payload: dict[str, Any]) -> str:
    topic = str(payload.get("topic") or payload.get("_topic") or "").strip()
    if topic.startswith("owntracks/"):
        return canonical_owntracks_topic(topic)
    username = str(payload.get("username") or payload.get("user") or request.query_params.get("user") or DEFAULT_TOPIC_USERNAME)
    device = str(
        payload.get("device")
        or payload.get("tid")
        or payload.get("t")
        or request.query_params.get("device")
        or DEFAULT_TOPIC_DEVICE
    )
    return canonical_owntracks_topic(f"owntracks/{topic_part(username, DEFAULT_TOPIC_USERNAME)}/{topic_part(device, DEFAULT_TOPIC_DEVICE)}")


def payload_timestamp(payload: dict[str, Any], fallback: datetime) -> datetime:
    for key in ("tst", "_tst", "created_at", "created", "time"):
        raw = payload.get(key)
        if raw in (None, ""):
            continue
        try:
            if isinstance(raw, (int, float)) or str(raw).strip().isdigit():
                return datetime.fromtimestamp(float(raw), tz=timezone.utc).replace(tzinfo=None, microsecond=0)
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed.replace(microsecond=0)
        except (TypeError, ValueError, OSError):
            continue
    return fallback


def waypoint_name_from_payload(payload: dict[str, Any]) -> Optional[str]:
    for key in ("desc", "description", "name", "rid"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return None


def looks_like_waypoint_item(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    has_name = waypoint_name_from_payload(value) is not None
    has_position = float_value(value.get("lat")) is not None and float_value(value.get("lon") or value.get("lng")) is not None
    return has_name and has_position


def normalize_http_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        return {"_type": "waypoints", "waypoints": payload}
    if not isinstance(payload, dict):
        raise ValueError("Body must be a JSON object or a waypoint list")

    normalized = dict(payload)
    message_type = str(normalized.get("_type") or normalized.get("type") or "").strip().lower()
    if message_type:
        return normalized

    if any(key in normalized for key in ("waypoints", "wps", "data")):
        normalized["_type"] = "waypoints"
        return normalized

    if looks_like_waypoint_item(normalized):
        normalized["_type"] = "waypoint"
        return normalized

    if normalized and all(looks_like_waypoint_item(item) for item in normalized.values()):
        return {"_type": "waypoints", "waypoints": normalized}

    return normalized


def waypoint_names(regions: Any) -> list[str]:
    if regions in (None, ""):
        return []
    if isinstance(regions, str):
        raw_values: Iterable[Any] = [regions]
    elif isinstance(regions, dict):
        raw_values = regions.values()
    elif isinstance(regions, Iterable):
        raw_values = regions
    else:
        raw_values = [regions]
    names: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        if value in (None, ""):
            continue
        name = str(value).strip()
        key = name.lower()
        if name and key not in seen:
            names.append(name)
            seen.add(key)
    return names


def normalized_event_type(event_type: Optional[str]) -> str:
    value = (event_type or "").strip().lower()
    aliases = {
        "entry": "enter",
        "entered": "enter",
        "arrival": "enter",
        "arrive": "enter",
        "departure": "leave",
        "depart": "leave",
        "exit": "leave",
        "left": "leave",
    }
    return aliases.get(value, value or "unknown")


def waypoint_state_for_event(event_type: Optional[str]) -> tuple[Optional[str], Optional[bool]]:
    event = normalized_event_type(event_type)
    if event == "enter":
        return "inside", True
    if event == "leave":
        return "outside", False
    if event == "defined":
        return "defined", None
    return None, None


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def confidence_for_distance(distance_m: float, threshold_m: float) -> float:
    if threshold_m <= 0:
        return 0.0
    ratio = min(1.0, max(0.0, distance_m / threshold_m))
    return round(max(0.1, 1.0 - ratio * 0.7), 3)


def waypoint_items_from_plural(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("waypoints") or payload.get("wps") or payload.get("data") or []
    if isinstance(raw, dict):
        values = raw.values()
    elif isinstance(raw, list):
        values = raw
    else:
        values = []
    return [item for item in values if isinstance(item, dict)]


def message_hash(topic: str, payload_text: str) -> str:
    return hashlib.sha256(f"{topic}\0{payload_text}".encode("utf-8")).hexdigest()


def event_already_exists(
    session: Session,
    topic: str,
    waypoint_name: str,
    event_type: str,
    timestamp: datetime,
    window_seconds: int = 120,
) -> bool:
    start = timestamp - timedelta(seconds=window_seconds)
    end = timestamp + timedelta(seconds=window_seconds)
    existing = session.execute(
        select(OwnTracksWaypointEvent.id)
        .where(OwnTracksWaypointEvent.topic == topic)
        .where(OwnTracksWaypointEvent.waypoint_name == waypoint_name)
        .where(OwnTracksWaypointEvent.event_type == event_type)
        .where(OwnTracksWaypointEvent.timestamp >= start)
        .where(OwnTracksWaypointEvent.timestamp <= end)
        .limit(1)
    ).scalar_one_or_none()
    return existing is not None


def find_waypoint(session: Session, topic: str, waypoint_name: str) -> Optional[OwnTracksWaypointState]:
    waypoint_cache = session.info.setdefault("owntracks_waypoint_cache", {})
    cache_key = (topic, waypoint_name)
    row = waypoint_cache.get(cache_key)
    if row is not None:
        return row
    row = session.execute(
        select(OwnTracksWaypointState)
        .where(OwnTracksWaypointState.topic == topic)
        .where(OwnTracksWaypointState.waypoint_name == waypoint_name)
    ).scalar_one_or_none()
    if row is not None:
        waypoint_cache[cache_key] = row
    return row


def record_waypoint_event(
    session: Session,
    location: OwnTracksLocation,
    waypoint_name: str,
    event_type: str,
    *,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_m: Optional[float] = None,
    accuracy_m: Optional[float] = None,
    synthetic: bool = False,
    event_payload: Optional[dict[str, Any]] = None,
) -> None:
    event_type = normalized_event_type(event_type)
    event_time = location.timestamp or location.received_at
    if event_type not in {"enter", "leave", "defined"}:
        return
    if event_already_exists(session, location.topic, waypoint_name, event_type, event_time):
        return
    session.add(
        OwnTracksWaypointEvent(
            topic=location.topic,
            username=location.username,
            device=location.device,
            waypoint_name=waypoint_name,
            event_type=event_type,
            source_message_type=location.message_type,
            timestamp=event_time,
            received_at=location.received_at,
            lat=lat if lat is not None else location.lat,
            lon=lon if lon is not None else location.lon,
            radius_m=radius_m,
            accuracy_m=accuracy_m if accuracy_m is not None else location.accuracy_m,
            location_id=location.id,
            is_synthetic=synthetic,
            payload=event_payload or location.payload,
        )
    )


def upsert_waypoint(
    session: Session,
    location: OwnTracksLocation,
    waypoint_name: str,
    event_type: str,
    *,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_m: Optional[float] = None,
    accuracy_m: Optional[float] = None,
    synthetic: bool = False,
    event_payload: Optional[dict[str, Any]] = None,
) -> OwnTracksWaypointState:
    event_type = normalized_event_type(event_type)
    state_value, is_inside = waypoint_state_for_event(event_type)
    row = find_waypoint(session, location.topic, waypoint_name)
    if row is None:
        row = OwnTracksWaypointState(topic=location.topic, waypoint_name=waypoint_name)
        session.add(row)
    session.info.setdefault("owntracks_waypoint_cache", {})[(location.topic, waypoint_name)] = row
    row.username = location.username
    row.device = location.device
    row.source_message_type = location.message_type
    row.last_seen_at = location.timestamp or location.received_at
    row.updated_at = utc_now()
    row.last_location_id = location.id
    if lat is not None:
        row.lat = lat
    if lon is not None:
        row.lon = lon
    if radius_m is not None:
        row.radius_m = radius_m
    if accuracy_m is not None:
        row.accuracy_m = accuracy_m
    if state_value is not None:
        row.last_state = state_value
        row.is_inside = is_inside
        row.last_event = event_type
        row.last_event_at = location.timestamp or location.received_at

    record_waypoint_event(
        session,
        location,
        waypoint_name,
        event_type,
        lat=lat,
        lon=lon,
        radius_m=radius_m,
        accuracy_m=accuracy_m,
        synthetic=synthetic,
        event_payload=event_payload,
    )
    return row


def update_zone_visit_position(visit: OwnTracksZoneVisit, location: OwnTracksLocation, confidence: float) -> None:
    visit.last_lat = location.lat
    visit.last_lon = location.lon
    visit.last_location_id = location.id
    visit.confidence = max(float(visit.confidence or 0), confidence)
    visit.updated_at = utc_now()


def open_zone_visit(
    session: Session,
    location: OwnTracksLocation,
    waypoint: OwnTracksWaypointState,
    *,
    source: str,
    confidence: float,
) -> OwnTracksZoneVisit:
    event_at = location.timestamp or location.received_at
    visit_cache = session.info.setdefault("owntracks_open_zone_visit_cache", {})
    cache_key = (location.topic, waypoint.waypoint_name)
    existing = visit_cache.get(cache_key)
    if existing is None:
        existing = session.execute(
            select(OwnTracksZoneVisit)
            .where(OwnTracksZoneVisit.topic == location.topic)
            .where(OwnTracksZoneVisit.waypoint_name == waypoint.waypoint_name)
            .where(OwnTracksZoneVisit.status == "open")
            .limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            visit_cache[cache_key] = existing
    if existing:
        update_zone_visit_position(existing, location, confidence)
        return existing
    visit = OwnTracksZoneVisit(
        topic=location.topic,
        username=location.username,
        device=location.device,
        waypoint_name=waypoint.waypoint_name,
        started_at=event_at,
        status="open",
        start_lat=location.lat,
        start_lon=location.lon,
        last_lat=location.lat,
        last_lon=location.lon,
        radius_m=waypoint.radius_m,
        enter_source=source,
        confidence=confidence,
        start_location_id=location.id,
        last_location_id=location.id,
    )
    session.add(visit)
    visit_cache[cache_key] = visit
    return visit


def close_zone_visit(
    session: Session,
    location: OwnTracksLocation,
    waypoint_name: str,
    *,
    source: str,
) -> Optional[OwnTracksZoneVisit]:
    event_at = location.timestamp or location.received_at
    visit_cache = session.info.setdefault("owntracks_open_zone_visit_cache", {})
    cache_key = (location.topic, waypoint_name)
    visit = visit_cache.get(cache_key)
    if visit is None:
        visit = session.execute(
            select(OwnTracksZoneVisit)
            .where(OwnTracksZoneVisit.topic == location.topic)
            .where(OwnTracksZoneVisit.waypoint_name == waypoint_name)
            .where(OwnTracksZoneVisit.status == "open")
            .limit(1)
        ).scalar_one_or_none()
    if not visit:
        return None
    visit.ended_at = event_at
    visit.duration_seconds = max(0, int((event_at - visit.started_at).total_seconds()))
    visit.status = "closed"
    visit.end_lat = location.lat
    visit.end_lon = location.lon
    visit.last_lat = location.lat
    visit.last_lon = location.lon
    visit.end_location_id = location.id
    visit.last_location_id = location.id
    visit.leave_source = source
    visit.updated_at = utc_now()
    visit_cache.pop(cache_key, None)
    return visit


def materialize_zone_visits_for_location(session: Session, location: OwnTracksLocation) -> None:
    if location.lat is None or location.lon is None:
        return
    if location.message_type in {"waypoint", "waypoints", "status", "transition"}:
        return
    waypoints = session.execute(
        select(OwnTracksWaypointState)
        .where(OwnTracksWaypointState.topic == location.topic)
        .where(OwnTracksWaypointState.lat.isnot(None))
        .where(OwnTracksWaypointState.lon.isnot(None))
    ).scalars()
    for waypoint in waypoints:
        radius_m = float(waypoint.radius_m or 100.0)
        accuracy_extra = min(float(location.accuracy_m or 0.0), ZONE_VISIT_ACCURACY_CAP_M)
        threshold_m = radius_m + ZONE_VISIT_BUFFER_M + accuracy_extra
        distance_m = distance_meters(float(location.lat), float(location.lon), float(waypoint.lat), float(waypoint.lon))
        inside = distance_m <= threshold_m
        confidence = confidence_for_distance(distance_m, threshold_m)
        if inside:
            open_zone_visit(session, location, waypoint, source="computed-position", confidence=confidence)
        else:
            close_zone_visit(session, location, waypoint.waypoint_name, source="computed-position")


def materialize_waypoints(session: Session, location: OwnTracksLocation, payload: dict[str, Any]) -> None:
    message_type = (location.message_type or "").lower()
    if message_type == "waypoints":
        for item in waypoint_items_from_plural(payload):
            name = waypoint_name_from_payload(item)
            if not name:
                continue
            upsert_waypoint(
                session,
                location,
                name,
                "defined",
                lat=float_value(item.get("lat")),
                lon=float_value(item.get("lon") or item.get("lng")),
                radius_m=float_value(item.get("rad") or item.get("radius")),
                accuracy_m=float_value(item.get("acc")),
                event_payload=item,
            )
        return

    if message_type == "waypoint":
        name = waypoint_name_from_payload(payload)
        if name:
            upsert_waypoint(
                session,
                location,
                name,
                "defined",
                lat=location.lat,
                lon=location.lon,
                radius_m=float_value(payload.get("rad") or payload.get("radius")),
                accuracy_m=location.accuracy_m,
            )
        return

    if message_type == "transition":
        name = waypoint_name_from_payload(payload)
        event_type = normalized_event_type(str(payload.get("event") or payload.get("transition") or ""))
        if name:
            waypoint = find_waypoint(session, location.topic, name)
            radius_m = float_value(payload.get("rad") or payload.get("radius"))
            if waypoint:
                waypoint = upsert_waypoint(
                    session,
                    location,
                    name,
                    event_type,
                    accuracy_m=location.accuracy_m,
                )
                if event_type == "enter":
                    open_zone_visit(session, location, waypoint, source="transition", confidence=1.0)
                elif event_type == "leave":
                    close_zone_visit(session, location, name, source="transition")
            else:
                record_waypoint_event(
                    session,
                    location,
                    name,
                    event_type,
                    lat=location.lat,
                    lon=location.lon,
                    radius_m=radius_m,
                    accuracy_m=location.accuracy_m,
                )
        return

    current_names = waypoint_names(payload.get("inregions") or payload.get("regions"))
    if current_names:
        for name in current_names:
            waypoint = find_waypoint(session, location.topic, name)
            if waypoint:
                open_zone_visit(session, location, waypoint, source="inregions", confidence=0.9)


def store_message(topic: str, payload_text: str) -> dict[str, Any]:
    topic = canonical_owntracks_topic(topic)
    received_at = utc_now()
    with STATE.lock:
        STATE.messages_received += 1
        STATE.last_message_at = received_at
    try:
        payload = json.loads(payload_text)
        if not isinstance(payload, dict):
            raise ValueError("Payload is not a JSON object")
    except Exception as exc:
        with STATE.lock:
            STATE.last_store_error = f"Invalid JSON: {exc}"
        raise HTTPException(status_code=400, detail="Payload must be a JSON object") from exc

    username, device = topic_identity(topic)
    message_type = str(payload.get("_type") or payload.get("type") or "").strip().lower() or None
    event_type = str(payload.get("event") or payload.get("transition") or "").strip().lower() or None
    timestamp = payload_timestamp(payload, received_at)
    lat = float_value(payload.get("lat"))
    lon = float_value(payload.get("lon") or payload.get("lng"))
    accuracy_m = float_value(payload.get("acc") or payload.get("accuracy"))
    digest = message_hash(topic, payload_text)

    with SessionLocal() as session:
        duplicate = session.execute(select(OwnTracksLocation.id).where(OwnTracksLocation.message_hash == digest)).scalar_one_or_none()
        if duplicate is not None:
            with STATE.lock:
                STATE.messages_duplicate += 1
            return {"stored": False, "duplicate": True, "id": duplicate}

        location = OwnTracksLocation(
            topic=topic,
            username=username,
            device=device,
            message_hash=digest,
            received_at=received_at,
            timestamp=timestamp,
            message_type=message_type,
            event=event_type,
            tracker_id=str(payload.get("tid") or payload.get("t") or "")[:80] or None,
            lat=lat,
            lon=lon,
            accuracy_m=accuracy_m,
            velocity_kmh=float_value(payload.get("vel") or payload.get("velocity")),
            battery_percent=float_value(payload.get("batt") or payload.get("battery")),
            connection=str(payload.get("conn") or "")[:40] or None,
            regions=payload.get("inregions") or payload.get("regions"),
            payload=payload,
        )
        session.add(location)
        session.flush()
        materialize_waypoints(session, location, payload)
        materialize_zone_visits_for_location(session, location)

        update_device_from_location(session, location)
        session.commit()

    with STATE.lock:
        STATE.messages_stored += 1
        STATE.last_store_error = None
    return {"stored": True, "duplicate": False, "topic": topic, "messageType": message_type}


def update_device_from_location(session: Session, location: OwnTracksLocation) -> OwnTracksDevice:
    device_cache = session.info.setdefault("owntracks_device_cache", {})
    device_row = device_cache.get(location.topic)
    if device_row is None:
        device_row = session.execute(select(OwnTracksDevice).where(OwnTracksDevice.topic == location.topic)).scalar_one_or_none()
    if device_row is None:
        device_row = OwnTracksDevice(topic=location.topic, username=location.username, device=location.device)
        session.add(device_row)
    device_cache[location.topic] = device_row
    device_row.username = location.username
    device_row.device = location.device
    device_row.tracker_id = location.tracker_id or device_row.tracker_id
    device_row.last_seen_at = location.timestamp or device_row.last_seen_at
    device_row.last_received_at = location.received_at
    if location.lat is not None:
        device_row.last_lat = location.lat
    if location.lon is not None:
        device_row.last_lon = location.lon
    if location.accuracy_m is not None:
        device_row.last_accuracy_m = location.accuracy_m
    if location.battery_percent is not None:
        device_row.last_battery_percent = location.battery_percent
    device_row.last_connection = location.connection or device_row.last_connection
    device_row.last_event = location.event or location.message_type or device_row.last_event
    device_row.message_count = int(device_row.message_count or 0) + 1
    device_row.updated_at = utc_now()
    return device_row


def rebuild_zone_visits() -> int:
    with SessionLocal() as session:
        session.execute(delete(OwnTracksZoneVisit))
        locations = session.execute(
            select(OwnTracksLocation)
            .where(OwnTracksLocation.lat.isnot(None))
            .where(OwnTracksLocation.lon.isnot(None))
            .order_by(OwnTracksLocation.timestamp.asc().nullslast(), OwnTracksLocation.received_at.asc())
        ).scalars()
        count = 0
        for location in locations:
            materialize_waypoints(session, location, location.payload or {})
            materialize_zone_visits_for_location(session, location)
            count += 1
        session.commit()
        return count


def normalize_existing_owntracks_data() -> None:
    with SessionLocal() as session:
        tables_to_check = (OwnTracksLocation, OwnTracksDevice, OwnTracksWaypointState, OwnTracksWaypointEvent, OwnTracksZoneVisit)
        needs_rebuild = False
        for table in tables_to_check:
            rows = session.execute(select(table.topic).limit(10000)).scalars()
            if any(topic != canonical_owntracks_topic(topic) for topic in rows):
                needs_rebuild = True
                break
        if not needs_rebuild:
            return

        session.execute(delete(OwnTracksZoneVisit))
        session.execute(delete(OwnTracksWaypointEvent))
        session.execute(delete(OwnTracksWaypointState))
        session.execute(delete(OwnTracksDevice))
        session.flush()

        kept_locations: list[OwnTracksLocation] = []
        seen_hashes: set[str] = set()
        locations = list(
            session.execute(
                select(OwnTracksLocation).order_by(OwnTracksLocation.received_at.asc(), OwnTracksLocation.id.asc())
            ).scalars()
        )
        for location in locations:
            canonical_topic = canonical_owntracks_topic(location.topic)
            location.topic = canonical_topic
            location.username, location.device = topic_identity(canonical_topic)
            location.message_hash = message_hash(canonical_topic, json_string(location.payload or {}))
            if location.message_hash in seen_hashes:
                session.delete(location)
                continue
            seen_hashes.add(location.message_hash)
            kept_locations.append(location)
        session.flush()

        for location in kept_locations:
            materialize_waypoints(session, location, location.payload or {})
            materialize_zone_visits_for_location(session, location)
            update_device_from_location(session, location)
        session.commit()


def db_count(session: Session, model: Any) -> int:
    return int(session.execute(select(func.count(model.id))).scalar_one() or 0)


def duration_label(start_at: Optional[datetime], end_at: Optional[datetime]) -> str:
    if not start_at:
        return "-"
    seconds = max(0, int(((end_at or utc_now()) - start_at).total_seconds()))
    minutes = int(round(seconds / 60))
    if minutes < 60:
        return f"{minutes} min"
    hours, remainder = divmod(minutes, 60)
    if remainder:
        return f"{hours} t {remainder} min"
    return f"{hours} t"


def row_location(row: OwnTracksLocation) -> dict[str, Any]:
    return {
        "id": row.id,
        "topic": row.topic,
        "username": row.username,
        "device": row.device,
        "timestamp": iso_dt(row.timestamp),
        "receivedAt": iso_dt(row.received_at),
        "messageType": row.message_type,
        "event": row.event,
        "lat": row.lat,
        "lon": row.lon,
        "accuracyM": row.accuracy_m,
        "batteryPercent": row.battery_percent,
        "connection": row.connection,
        "regions": row.regions,
    }


def row_device(row: OwnTracksDevice) -> dict[str, Any]:
    return {
        "topic": row.topic,
        "username": row.username,
        "device": row.device,
        "trackerId": row.tracker_id,
        "lastSeenAt": iso_dt(row.last_seen_at),
        "lastReceivedAt": iso_dt(row.last_received_at),
        "lastLat": row.last_lat,
        "lastLon": row.last_lon,
        "lastAccuracyM": row.last_accuracy_m,
        "lastBatteryPercent": row.last_battery_percent,
        "lastConnection": row.last_connection,
        "lastEvent": row.last_event,
        "messageCount": row.message_count,
    }


def row_waypoint(row: OwnTracksWaypointState) -> dict[str, Any]:
    return {
        "id": row.id,
        "topic": row.topic,
        "username": row.username,
        "device": row.device,
        "waypointName": row.waypoint_name,
        "lat": row.lat,
        "lon": row.lon,
        "radiusM": row.radius_m,
        "accuracyM": row.accuracy_m,
        "lastState": row.last_state,
        "isInside": row.is_inside,
        "lastEvent": row.last_event,
        "lastSeenAt": iso_dt(row.last_seen_at),
        "lastEventAt": iso_dt(row.last_event_at),
        "sourceMessageType": row.source_message_type,
    }


def row_event(row: OwnTracksWaypointEvent) -> dict[str, Any]:
    return {
        "id": row.id,
        "topic": row.topic,
        "username": row.username,
        "device": row.device,
        "waypointName": row.waypoint_name,
        "eventType": row.event_type,
        "sourceMessageType": row.source_message_type,
        "timestamp": iso_dt(row.timestamp),
        "receivedAt": iso_dt(row.received_at),
        "lat": row.lat,
        "lon": row.lon,
        "radiusM": row.radius_m,
        "accuracyM": row.accuracy_m,
        "isSynthetic": row.is_synthetic,
    }


def row_visit(row: OwnTracksZoneVisit) -> dict[str, Any]:
    return {
        "id": row.id,
        "topic": row.topic,
        "username": row.username,
        "device": row.device,
        "waypointName": row.waypoint_name,
        "startedAt": iso_dt(row.started_at),
        "endedAt": iso_dt(row.ended_at),
        "durationSeconds": row.duration_seconds,
        "duration": duration_label(row.started_at, row.ended_at),
        "status": row.status,
        "startLat": row.start_lat,
        "startLon": row.start_lon,
        "endLat": row.end_lat,
        "endLon": row.end_lon,
        "lastLat": row.last_lat,
        "lastLon": row.last_lon,
        "radiusM": row.radius_m,
        "enterSource": row.enter_source,
        "leaveSource": row.leave_source,
        "confidence": row.confidence,
    }


def module_table(title: str, columns: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"title": title, "columns": columns, "rows": rows}


def module_card(title: str, value: Any, unit: str = "", subtitle: str = "") -> dict[str, Any]:
    return {"title": title, "value": value, "unit": unit, "subtitle": subtitle}


def require_http_token(request: Request) -> None:
    if not HTTP_TOKEN:
        return
    candidates = []
    auth = request.headers.get("authorization", "")
    header_token = request.headers.get("x-owntracks-token")
    query_token = request.query_params.get("token")
    if header_token:
        candidates.append(header_token.strip())
    if query_token:
        candidates.append(query_token.strip())
    if auth.lower().startswith("bearer "):
        candidates.append(auth[7:].strip())
    elif auth.lower().startswith("basic "):
        try:
            decoded = base64.b64decode(auth[6:].strip()).decode("utf-8", errors="replace")
            _username, _separator, password = decoded.partition(":")
            candidates.append(password.strip())
        except Exception:
            pass
    if HTTP_TOKEN not in candidates:
        raise HTTPException(status_code=401, detail="Invalid OwnTracks token")


def require_owntracks_admin(request: Request) -> None:
    if not HTTP_TOKEN:
        raise HTTPException(status_code=503, detail="OwnTracks token is not configured")
    try:
        require_http_token(request)
    except HTTPException as exc:
        if exc.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="OwnTracks token required",
                headers={"WWW-Authenticate": 'Basic realm="OwnTracks"'},
            ) from exc
        raise


OWNTRACKS_ADMIN_HTML = """
<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OwnTracks | Lilletorget</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <style>
    :root {
      --bg: #f4f7fb;
      --panel: #ffffff;
      --panel-soft: #f8fafc;
      --line: #dfe7f1;
      --text: #111827;
      --muted: #64748b;
      --blue: #2563eb;
      --green: #16a34a;
      --orange: #f59e0b;
      --red: #dc2626;
      --shadow: 0 14px 38px rgba(15, 23, 42, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
    }
    .shell {
      width: min(1680px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 24px 0 40px;
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 18px;
    }
    .brand h1 {
      margin: 0;
      font-size: 26px;
      line-height: 1.1;
      letter-spacing: 0;
    }
    .brand-title {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .build-pill {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 0 9px;
      border-radius: 999px;
      border: 1px solid #bfdbfe;
      background: #eff6ff;
      color: #1d4ed8;
      font-size: 12px;
      font-weight: 750;
    }
    .brand p {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 14px;
    }
    .actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    button, select {
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      min-height: 36px;
      border-radius: 8px;
      padding: 0 12px;
      font: inherit;
    }
    button {
      cursor: pointer;
      font-weight: 650;
    }
    button.primary {
      background: var(--blue);
      border-color: var(--blue);
      color: #fff;
    }
    button:disabled {
      cursor: wait;
      opacity: 0.65;
    }
    .status-line {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      min-height: 20px;
    }
    .dot {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: var(--green);
      display: inline-block;
    }
    .dot.warn { background: var(--orange); }
    .dot.err { background: var(--red); }
    .grid {
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      box-shadow: var(--shadow);
    }
    .metric {
      padding: 14px 16px;
      min-height: 88px;
    }
    .metric .label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 750;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .metric .value {
      margin-top: 8px;
      font-size: 24px;
      line-height: 1;
      font-weight: 760;
    }
    .metric .sub {
      margin-top: 8px;
      color: var(--muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .main-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(420px, 0.85fr);
      gap: 14px;
      align-items: start;
    }
    .panel-head {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .panel-head h2 {
      margin: 0;
      font-size: 16px;
    }
    .panel-head span {
      color: var(--muted);
      font-size: 13px;
    }
    #map {
      height: 560px;
      border-radius: 0 0 12px 12px;
      background: #e8eef6;
    }
    .stack {
      display: grid;
      gap: 14px;
    }
    .table-wrap {
      overflow: auto;
      max-height: 360px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      padding: 9px 10px;
      border-bottom: 1px solid #edf2f7;
      text-align: left;
      vertical-align: top;
      white-space: nowrap;
    }
    th {
      position: sticky;
      top: 0;
      background: var(--panel-soft);
      color: #475569;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      z-index: 1;
    }
    td.muted { color: var(--muted); }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 0 8px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: var(--panel-soft);
      font-size: 12px;
      font-weight: 700;
    }
    .pill.ok { color: #166534; border-color: #bbf7d0; background: #f0fdf4; }
    .pill.warn { color: #92400e; border-color: #fde68a; background: #fffbeb; }
    .pill.err { color: #991b1b; border-color: #fecaca; background: #fef2f2; }
    .empty {
      padding: 22px 16px;
      color: var(--muted);
    }
    a { color: var(--blue); text-decoration: none; font-weight: 650; }
    @media (max-width: 1200px) {
      .grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .main-grid { grid-template-columns: 1fr; }
      #map { height: 460px; }
    }
    @media (max-width: 720px) {
      .shell { width: min(100vw - 20px, 1680px); padding-top: 14px; }
      .topbar { align-items: flex-start; flex-direction: column; }
      .actions { justify-content: flex-start; }
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .metric .value { font-size: 20px; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="topbar">
      <div class="brand">
        <div class="brand-title">
          <h1>OwnTracks</h1>
          <span class="build-pill" id="buildLabel">Build -</span>
        </div>
        <p id="publicUrl">HTTP-mottak for posisjoner, waypoints og beregnede sonebesok.</p>
      </div>
      <div class="actions">
        <select id="hours">
          <option value="24">Siste 24 timer</option>
          <option value="168">Siste 7 dager</option>
          <option value="720">Siste 30 dager</option>
          <option value="0">Alt</option>
        </select>
        <button id="rebuild">Bygg sonebesok</button>
        <button id="refresh" class="primary">Oppdater</button>
      </div>
    </section>
    <div class="status-line" id="status"><span class="dot warn"></span><span>Laster...</span></div>
    <section class="grid" id="metrics"></section>
    <section class="main-grid">
      <article class="card">
        <div class="panel-head">
          <h2>Kart og spor</h2>
          <span id="mapMeta">-</span>
        </div>
        <div id="map"></div>
      </article>
      <div class="stack">
        <article class="card" id="devicesPanel"></article>
        <article class="card" id="visitsPanel"></article>
      </div>
    </section>
    <section class="stack" style="margin-top:14px">
      <article class="card" id="locationsPanel"></article>
      <article class="card" id="waypointsPanel"></article>
      <article class="card" id="eventsPanel"></article>
      <article class="card" id="buildPanel"></article>
    </section>
  </main>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token") || "";
    const state = { map: null, layers: [] };

    function api(path, extra = {}) {
      const url = new URL(path, window.location.origin);
      Object.entries(extra).forEach(([key, value]) => url.searchParams.set(key, value));
      if (token) url.searchParams.set("token", token);
      return url.toString();
    }

    function esc(value) {
      return String(value ?? "").replace(/[&<>"']/g, ch => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
      }[ch]));
    }

    function fmtTime(value) {
      if (!value) return "-";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return String(value);
      return date.toLocaleString("no-NO", { dateStyle: "short", timeStyle: "medium" });
    }

    function fmtNum(value, decimals = 0) {
      if (value === null || value === undefined || value === "") return "-";
      const number = Number(value);
      if (!Number.isFinite(number)) return String(value);
      return number.toLocaleString("no-NO", { maximumFractionDigits: decimals, minimumFractionDigits: decimals });
    }

    function status(text, tone = "ok") {
      const dot = tone === "err" ? "err" : tone === "warn" ? "warn" : "";
      document.getElementById("status").innerHTML = `<span class="dot ${dot}"></span><span>${esc(text)}</span>`;
    }

    async function fetchJson(path, extra = {}, options = {}) {
      const res = await fetch(api(path, extra), { credentials: "same-origin", ...options });
      if (res.status === 401) throw new Error("Mangler gyldig token. Bruk Basic Auth eller ?token=...");
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      return res.json();
    }

    function metric(label, value, sub = "") {
      return `<article class="card metric"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div><div class="sub">${esc(sub)}</div></article>`;
    }

    function renderMetrics(health, moduleData) {
      const counts = health.counts || {};
      const stateData = health.state || {};
      const build = moduleData.metadata?.build || health.app || {};
      const publicInfo = health.public || {};
      const lastCard = (moduleData.cards || []).find(card => card.title === "Siste melding");
      document.getElementById("buildLabel").textContent = `Build ${build.build || "-"}`;
      document.getElementById("publicUrl").textContent = publicInfo.publishUrl
        ? `Publisering: ${publicInfo.publishUrl}`
        : "HTTP-mottak for posisjoner, waypoints og beregnede sonebesok.";
      document.getElementById("metrics").innerHTML = [
        metric("Status", health.status || "-", health.ingest?.authTokenEnabled ? "Token aktivt" : "Token mangler"),
        metric("Build", build.build || "-", build.commit && build.commit !== "unknown" ? build.commit : "Egen OwnTracks-build"),
        metric("Meldinger", counts.locations ?? 0, `Lagret: ${stateData.messagesStored ?? 0}, dublett: ${stateData.messagesDuplicate ?? 0}`),
        metric("Enheter", counts.devices ?? 0, "Telefoner/enheter"),
        metric("Waypoints", counts.waypoints ?? 0, "Definerte soner"),
        metric("Siste melding", lastCard?.value || "-", lastCard?.subtitle || "")
      ].join("");
    }

    function tablePanel(id, title, rows, columns) {
      const panel = document.getElementById(id);
      if (!rows || rows.length === 0) {
        panel.innerHTML = `<div class="panel-head"><h2>${esc(title)}</h2><span>0 rader</span></div><div class="empty">Ingen data enna.</div>`;
        return;
      }
      const head = columns.map(col => `<th>${esc(col.label)}</th>`).join("");
      const body = rows.map(row => `<tr>${columns.map(col => `<td>${col.render ? col.render(row) : esc(row[col.key])}</td>`).join("")}</tr>`).join("");
      panel.innerHTML = `<div class="panel-head"><h2>${esc(title)}</h2><span>${rows.length} rader</span></div><div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
    }

    function mapsLink(lat, lon) {
      if (lat === null || lon === null || lat === undefined || lon === undefined) return "-";
      const href = `https://www.google.com/maps?q=${encodeURIComponent(`${lat},${lon}`)}`;
      return `<a href="${href}" target="_blank" rel="noreferrer">${fmtNum(lat, 5)}, ${fmtNum(lon, 5)}</a>`;
    }

    function pill(value, truthyLabel = "Inne") {
      if (value === true) return `<span class="pill ok">${truthyLabel}</span>`;
      if (value === false) return `<span class="pill">Ute</span>`;
      return `<span class="pill warn">Ukjent</span>`;
    }

    function renderTables(moduleData, mapData) {
      tablePanel("devicesPanel", "Enheter", mapData.devices || [], [
        { label: "Enhet", render: row => esc(row.topic || `${row.username || ""}/${row.device || ""}`) },
        { label: "Sist sett", render: row => fmtTime(row.lastSeenAt) },
        { label: "Posisjon", render: row => mapsLink(row.lastLat, row.lastLon) },
        { label: "Noyaktighet", render: row => `${fmtNum(row.lastAccuracyM)} m` },
        { label: "Batteri", render: row => row.lastBatteryPercent == null ? "-" : `${fmtNum(row.lastBatteryPercent)} %` },
      ]);
      tablePanel("visitsPanel", "Sonebesok", mapData.zoneVisits || [], [
        { label: "Sone", key: "waypointName" },
        { label: "Start", render: row => fmtTime(row.startedAt) },
        { label: "Slutt", render: row => fmtTime(row.endedAt) },
        { label: "Varighet", key: "duration" },
        { label: "Status", render: row => `<span class="pill ${row.status === "open" ? "ok" : ""}">${esc(row.status)}</span>` },
      ]);
      tablePanel("locationsPanel", "Siste posisjoner", [...(mapData.locations || [])].reverse().slice(0, 200), [
        { label: "Tid", render: row => fmtTime(row.timestamp || row.receivedAt) },
        { label: "Enhet", key: "topic" },
        { label: "Type", key: "messageType" },
        { label: "Event", key: "event" },
        { label: "Posisjon", render: row => mapsLink(row.lat, row.lon) },
        { label: "Noyaktighet", render: row => `${fmtNum(row.accuracyM)} m` },
        { label: "Batteri", render: row => row.batteryPercent == null ? "-" : `${fmtNum(row.batteryPercent)} %` },
      ]);
      tablePanel("waypointsPanel", "Waypoints", mapData.waypoints || [], [
        { label: "Navn", key: "waypointName" },
        { label: "Status", render: row => pill(row.isInside) },
        { label: "Sist sett", render: row => fmtTime(row.lastSeenAt) },
        { label: "Radius", render: row => `${fmtNum(row.radiusM)} m` },
        { label: "Senter", render: row => mapsLink(row.lat, row.lon) },
      ]);
      const eventTable = (moduleData.tables || []).find(table => table.title === "Waypoint-hendelser");
      tablePanel("eventsPanel", "Waypoint-hendelser", eventTable?.rows || [], [
        { label: "Tid", render: row => fmtTime(row.timestamp || row.receivedAt) },
        { label: "Sone", key: "waypointName" },
        { label: "Hendelse", render: row => `<span class="pill ${row.eventType === "enter" ? "ok" : ""}">${esc(row.eventType)}</span>` },
        { label: "Kilde", key: "sourceMessageType" },
        { label: "Posisjon", render: row => mapsLink(row.lat, row.lon) },
        { label: "Noyaktighet", render: row => `${fmtNum(row.accuracyM)} m` },
      ]);
      tablePanel("buildPanel", "Buildlogg", moduleData.metadata?.buildLog?.rows || [], [
        { label: "Build", key: "build" },
        { label: "Dato", key: "date" },
        { label: "Overskrift", key: "headline" },
        { label: "Endringer", render: row => (row.changes || []).map(esc).join("<br>") },
      ]);
    }

    function ensureMap() {
      if (state.map || !window.L) return state.map;
      state.map = L.map("map", { scrollWheelZoom: true });
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap"
      }).addTo(state.map);
      state.map.setView([61.115, 10.466], 13);
      return state.map;
    }

    function clearMap() {
      if (!state.map) return;
      state.layers.forEach(layer => state.map.removeLayer(layer));
      state.layers = [];
    }

    function addLayer(layer) {
      layer.addTo(state.map);
      state.layers.push(layer);
      return layer;
    }

    function renderMap(data) {
      const map = ensureMap();
      if (!map) {
        document.getElementById("mapMeta").textContent = "Kartbibliotek kunne ikke lastes";
        return;
      }
      clearMap();
      const bounds = [];
      const locations = data.locations || [];
      const points = locations.filter(row => Number.isFinite(Number(row.lat)) && Number.isFinite(Number(row.lon)));
      if (points.length > 1) {
        addLayer(L.polyline(points.map(row => [row.lat, row.lon]), { color: "#2563eb", weight: 3, opacity: 0.65 }));
      }
      points.forEach((row, index) => {
        bounds.push([row.lat, row.lon]);
        if (index === points.length - 1) {
          addLayer(L.circleMarker([row.lat, row.lon], { radius: 7, color: "#2563eb", fillColor: "#2563eb", fillOpacity: 0.9 })
            .bindPopup(`<b>${esc(row.topic)}</b><br>${fmtTime(row.timestamp || row.receivedAt)}<br>${fmtNum(row.accuracyM)} m`));
        }
      });
      (data.devices || []).forEach(row => {
        if (!Number.isFinite(Number(row.lastLat)) || !Number.isFinite(Number(row.lastLon))) return;
        bounds.push([row.lastLat, row.lastLon]);
        addLayer(L.marker([row.lastLat, row.lastLon]).bindPopup(`<b>${esc(row.topic)}</b><br>Sist sett: ${fmtTime(row.lastSeenAt)}<br>${fmtNum(row.lastAccuracyM)} m`));
      });
      (data.waypoints || []).forEach(row => {
        if (!Number.isFinite(Number(row.lat)) || !Number.isFinite(Number(row.lon))) return;
        bounds.push([row.lat, row.lon]);
        addLayer(L.circle([row.lat, row.lon], {
          radius: Number(row.radiusM || 50),
          color: row.isInside ? "#16a34a" : "#f59e0b",
          fillColor: row.isInside ? "#bbf7d0" : "#fde68a",
          fillOpacity: 0.22,
          weight: 2
        }).bindPopup(`<b>${esc(row.waypointName)}</b><br>${row.isInside ? "Inne" : "Ute"}<br>Radius ${fmtNum(row.radiusM)} m`));
      });
      if (bounds.length) map.fitBounds(bounds, { padding: [28, 28], maxZoom: 16 });
      document.getElementById("mapMeta").textContent = `${points.length} posisjoner, ${(data.waypoints || []).length} waypoints`;
    }

    async function refresh() {
      const button = document.getElementById("refresh");
      button.disabled = true;
      try {
        const hours = document.getElementById("hours").value;
        const [health, moduleData, mapData] = await Promise.all([
          fetchJson("/owntracks/health"),
          fetchJson("/owntracks/api/module"),
          fetchJson("/owntracks/api/map", { hours, limit: 5000 })
        ]);
        renderMetrics(health, moduleData);
        renderTables(moduleData, mapData);
        renderMap(mapData);
        status(`Oppdatert ${new Date().toLocaleTimeString("no-NO")}`);
      } catch (error) {
        console.error(error);
        status(error.message || "Feil ved lasting", "err");
      } finally {
        button.disabled = false;
      }
    }

    async function rebuild() {
      const button = document.getElementById("rebuild");
      button.disabled = true;
      try {
        const res = await fetch(api("/owntracks/api/rebuild"), { method: "POST", credentials: "same-origin" });
        if (res.status === 401) throw new Error("Mangler gyldig token.");
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const data = await res.json();
        status(`Sonebesok bygget: ${data.locationsProcessed} posisjoner`);
        await refresh();
      } catch (error) {
        status(error.message || "Feil ved rebuild", "err");
      } finally {
        button.disabled = false;
      }
    }

    document.getElementById("refresh").addEventListener("click", refresh);
    document.getElementById("hours").addEventListener("change", refresh);
    document.getElementById("rebuild").addEventListener("click", rebuild);
    refresh();
    setInterval(refresh, 30000);
  </script>
</body>
</html>
"""


app = FastAPI(title="OwnTracks service")
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(engine)
    normalize_existing_owntracks_data()


@app.get("/", response_class=HTMLResponse)
def root_admin(request: Request) -> HTMLResponse:
    require_owntracks_admin(request)
    return HTMLResponse(OWNTRACKS_ADMIN_HTML)


@app.get("/service")
def service_root() -> dict[str, Any]:
    return {
        "service": "owntracks_service",
        "app": owntracks_build_summary(),
        "health": "/health",
        "admin": "/",
        "publish": "/pub",
        "map": "/owntracks/api/map",
    }


@app.get("/owntracks", response_class=HTMLResponse)
@app.get("/owntracks/", response_class=HTMLResponse)
def owntracks_admin(request: Request) -> HTMLResponse:
    require_owntracks_admin(request)
    return HTMLResponse(OWNTRACKS_ADMIN_HTML)


def health_payload() -> dict[str, Any]:
    with SessionLocal() as session:
        counts = {
            "devices": db_count(session, OwnTracksDevice),
            "locations": db_count(session, OwnTracksLocation),
            "waypoints": db_count(session, OwnTracksWaypointState),
            "events": db_count(session, OwnTracksWaypointEvent),
            "zoneVisits": db_count(session, OwnTracksZoneVisit),
        }
    return {
        "status": "ok",
        "service": "owntracks_service",
        "app": owntracks_build_summary(),
        "database": "ok",
        "ingest": {"mode": "http", "path": "/pub", "authTokenEnabled": bool(HTTP_TOKEN)},
        "public": {
            "baseUrl": OWNTRACKS_PUBLIC_BASE_URL,
            "publishUrl": f"{OWNTRACKS_PUBLIC_BASE_URL}/pub",
            "adminUrl": OWNTRACKS_PUBLIC_BASE_URL,
        },
        "state": STATE.snapshot(),
        "counts": counts,
        "time": iso_dt(utc_now()),
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return health_payload()


@app.get("/owntracks/health")
def owntracks_external_health(request: Request) -> dict[str, Any]:
    require_owntracks_admin(request)
    return health_payload()


@app.post("/pub")
async def owntracks_http_publish(request: Request) -> list[Any]:
    require_http_token(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Body must be JSON") from exc
    try:
        normalized_payload = normalize_http_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    topic = http_topic(request, normalized_payload)
    store_message(topic, json_string(normalized_payload))
    return []


@app.post("/api/owntracks/rebuild")
def api_rebuild() -> dict[str, Any]:
    started = time.monotonic()
    count = rebuild_zone_visits()
    return {"ok": True, "locationsProcessed": count, "seconds": round(time.monotonic() - started, 3)}


@app.post("/owntracks/api/rebuild")
def owntracks_external_rebuild(request: Request) -> dict[str, Any]:
    require_owntracks_admin(request)
    return api_rebuild()


@app.get("/owntracks/api/build-log")
def owntracks_external_build_log(request: Request) -> dict[str, Any]:
    require_owntracks_admin(request)
    return owntracks_build_log_payload()


@app.get("/api/owntracks/devices")
def api_devices(limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    with SessionLocal() as session:
        rows = session.execute(
            select(OwnTracksDevice)
            .order_by(OwnTracksDevice.last_seen_at.desc().nullslast(), OwnTracksDevice.updated_at.desc())
            .limit(limit)
        ).scalars()
        return {"enabled": True, "ingest": "http", "devices": [row_device(row) for row in rows]}


@app.get("/owntracks/api/devices")
def owntracks_external_devices(request: Request, limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    require_owntracks_admin(request)
    return api_devices(limit=limit)


@app.get("/api/owntracks/waypoints")
def api_waypoints(limit: int = Query(100, ge=1, le=1000), events: int = Query(100, ge=0, le=1000)) -> dict[str, Any]:
    with SessionLocal() as session:
        waypoint_rows = session.execute(
            select(OwnTracksWaypointState)
            .order_by(OwnTracksWaypointState.last_seen_at.desc().nullslast(), OwnTracksWaypointState.updated_at.desc())
            .limit(limit)
        ).scalars()
        event_rows = session.execute(
            select(OwnTracksWaypointEvent)
            .order_by(OwnTracksWaypointEvent.timestamp.desc().nullslast(), OwnTracksWaypointEvent.received_at.desc())
            .limit(events)
        ).scalars()
        return {
            "waypoints": [row_waypoint(row) for row in waypoint_rows],
            "events": [row_event(row) for row in event_rows],
        }


@app.get("/owntracks/api/waypoints")
def owntracks_external_waypoints(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    events: int = Query(100, ge=0, le=1000),
) -> dict[str, Any]:
    require_owntracks_admin(request)
    return api_waypoints(limit=limit, events=events)


@app.get("/api/owntracks/map")
def api_map(hours: int = Query(24, ge=0, le=24 * 365), limit: int = Query(2000, ge=0, le=20000)) -> dict[str, Any]:
    since = utc_now() - timedelta(hours=hours) if hours else None
    with SessionLocal() as session:
        location_stmt = (
            select(OwnTracksLocation)
            .where(OwnTracksLocation.lat.isnot(None))
            .where(OwnTracksLocation.lon.isnot(None))
            .order_by(OwnTracksLocation.timestamp.desc().nullslast(), OwnTracksLocation.received_at.desc())
        )
        if since is not None:
            location_stmt = location_stmt.where(or_(OwnTracksLocation.timestamp >= since, OwnTracksLocation.received_at >= since))
        if limit:
            location_stmt = location_stmt.limit(limit)
        locations = list(session.execute(location_stmt).scalars())
        locations.reverse()

        devices = session.execute(
            select(OwnTracksDevice)
            .where(OwnTracksDevice.last_lat.isnot(None))
            .where(OwnTracksDevice.last_lon.isnot(None))
            .order_by(OwnTracksDevice.last_seen_at.desc().nullslast(), OwnTracksDevice.updated_at.desc())
        ).scalars()
        waypoints = session.execute(
            select(OwnTracksWaypointState)
            .where(OwnTracksWaypointState.lat.isnot(None))
            .where(OwnTracksWaypointState.lon.isnot(None))
            .order_by(OwnTracksWaypointState.last_seen_at.desc().nullslast(), OwnTracksWaypointState.updated_at.desc())
        ).scalars()
        visit_stmt = select(OwnTracksZoneVisit).order_by(OwnTracksZoneVisit.started_at.desc()).limit(1000)
        if since is not None:
            visit_stmt = visit_stmt.where(
                or_(
                    OwnTracksZoneVisit.started_at >= since,
                    OwnTracksZoneVisit.ended_at >= since,
                    OwnTracksZoneVisit.status == "open",
                )
            )
        visits = session.execute(visit_stmt).scalars()
        waypoint_list = [row_waypoint(row) for row in waypoints]
        return {
            "hours": hours,
            "limit": limit,
            "locations": [row_location(row) for row in locations],
            "devices": [row_device(row) for row in devices],
            "waypoints": waypoint_list,
            "waypointDefinitions": waypoint_list,
            "zoneVisits": [row_visit(row) for row in visits],
        }


@app.get("/owntracks/api/map")
def owntracks_external_map(
    request: Request,
    hours: int = Query(24, ge=0, le=24 * 365),
    limit: int = Query(2000, ge=0, le=20000),
) -> dict[str, Any]:
    require_owntracks_admin(request)
    return api_map(hours=hours, limit=limit)


@app.get("/api/owntracks/module")
def api_module() -> dict[str, Any]:
    with SessionLocal() as session:
        devices = list(
            session.execute(
                select(OwnTracksDevice)
                .order_by(OwnTracksDevice.last_seen_at.desc().nullslast(), OwnTracksDevice.updated_at.desc())
                .limit(50)
            ).scalars()
        )
        locations = list(
            session.execute(
                select(OwnTracksLocation)
                .order_by(OwnTracksLocation.received_at.desc())
                .limit(100)
            ).scalars()
        )
        waypoints = list(
            session.execute(
                select(OwnTracksWaypointState)
                .order_by(OwnTracksWaypointState.last_seen_at.desc().nullslast(), OwnTracksWaypointState.updated_at.desc())
                .limit(100)
            ).scalars()
        )
        events = list(
            session.execute(
                select(OwnTracksWaypointEvent)
                .order_by(OwnTracksWaypointEvent.timestamp.desc().nullslast(), OwnTracksWaypointEvent.received_at.desc())
                .limit(100)
            ).scalars()
        )
        visits = list(session.execute(select(OwnTracksZoneVisit).order_by(OwnTracksZoneVisit.started_at.desc()).limit(100)).scalars())

    latest = devices[0] if devices else None
    state = STATE.snapshot()
    return {
        "title": "OwnTracks",
        "subtitle": "Standalone posisjonstjeneste. Fibaro10 skal hente relevante data via API.",
        "cards": [
            module_card("HTTP", "Aktiv", "", f"{OWNTRACKS_PUBLIC_BASE_URL}/pub"),
            module_card("Enheter", len(devices), "stk", "Siste kjente enheter"),
            module_card("Waypoints", len(waypoints), "stk", "Definerte soner"),
            module_card("Beregnet besok", len(visits), "stk", "Fra posisjoner og waypoint-radius"),
            module_card("Siste melding", iso_dt(latest.last_seen_at) if latest else "-", "", latest.topic if latest else "Ingen meldinger"),
        ],
        "charts": [],
        "tables": [
            module_table("Sonebesok", ["startedAt", "endedAt", "duration", "waypointName", "topic", "status", "confidence"], [row_visit(row) for row in visits]),
            module_table("Waypoints", ["waypointName", "topic", "lastState", "isInside", "lastSeenAt", "lat", "lon", "radiusM"], [row_waypoint(row) for row in waypoints]),
            module_table("Waypoint-hendelser", ["timestamp", "waypointName", "topic", "eventType", "sourceMessageType", "lat", "lon", "accuracyM"], [row_event(row) for row in events]),
            module_table("Enheter", ["topic", "username", "device", "lastSeenAt", "lastLat", "lastLon", "lastAccuracyM", "lastBatteryPercent"], [row_device(row) for row in devices]),
            module_table("Siste meldinger", ["receivedAt", "timestamp", "topic", "messageType", "event", "lat", "lon", "accuracyM", "batteryPercent"], [row_location(row) for row in locations]),
        ],
        "actions": [],
        "metadata": {"state": state, "build": owntracks_build_summary(), "buildLog": owntracks_build_log_payload()},
    }


@app.get("/owntracks/api/module")
def owntracks_external_module(request: Request) -> dict[str, Any]:
    require_owntracks_admin(request)
    return api_module()


class DebugMessage(BaseModel):
    topic: str
    payload: dict[str, Any]


@app.post("/api/owntracks/debug/store")
def api_debug_store(message: DebugMessage) -> dict[str, Any]:
    if os.getenv("OWNTRACKS_DEBUG_STORE_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "ja"}:
        raise HTTPException(status_code=404, detail="Debug store disabled")
    return store_message(message.topic, json_string(message.payload))
