from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import json
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Mapping, Optional, Sequence

import asyncpg
from fastapi import HTTPException, Request

from . import plate_validation


RECOGNITION_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_alarm_webhooks (
        console_key VARCHAR NOT NULL,
        webhook_id VARCHAR NOT NULL,
        received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        occurred_at TIMESTAMPTZ,
        alarm_name VARCHAR,
        source_event_id VARCHAR,
        source_device VARCHAR,
        recognition_count INTEGER NOT NULL DEFAULT 0,
        processing_status VARCHAR NOT NULL DEFAULT 'received',
        raw JSONB NOT NULL,
        PRIMARY KEY (console_key, webhook_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_recognitions (
        recognition_id BIGSERIAL PRIMARY KEY,
        console_key VARCHAR NOT NULL,
        webhook_id VARCHAR NOT NULL,
        trigger_index INTEGER NOT NULL,
        kind VARCHAR NOT NULL,
        value TEXT,
        normalized_value TEXT,
        is_known BOOLEAN,
        trigger_key VARCHAR,
        camera_id VARCHAR,
        camera_name VARCHAR,
        source_device VARCHAR,
        source_event_id VARCHAR,
        occurred_at TIMESTAMPTZ NOT NULL,
        received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        correlation_status VARCHAR NOT NULL DEFAULT 'unmatched',
        raw JSONB NOT NULL,
        UNIQUE (console_key, webhook_id, trigger_index)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_cursor
        ON unifi_protect_events (
            console_key,
            (COALESCE(start_at, last_received_at)) DESC,
            source_event_id DESC
        )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_recognitions_cursor
        ON unifi_protect_recognitions (console_key, occurred_at DESC, recognition_id DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_recognitions_value
        ON unifi_protect_recognitions (console_key, kind, normalized_value, occurred_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_recognitions_camera
        ON unifi_protect_recognitions (console_key, camera_id, occurred_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_recognitions_license_plate_day
        ON unifi_protect_recognitions (console_key, occurred_at DESC, normalized_value)
        WHERE kind = 'license_plate' AND normalized_value IS NOT NULL AND normalized_value <> ''
    """,
    "ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_status VARCHAR NOT NULL DEFAULT 'not_requested'",
    "ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_path TEXT",
    "ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_content_type VARCHAR",
    "ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_size_bytes BIGINT",
    "ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_captured_at TIMESTAMPTZ",
    "ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_target_at TIMESTAMPTZ",
    "ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_time_offset_ms INTEGER",
    "ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_source VARCHAR",
    "ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_camera_id VARCHAR",
    "ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_error TEXT",
    "ALTER TABLE unifi_protect_recognitions ADD COLUMN IF NOT EXISTS snapshot_attempt_count INTEGER NOT NULL DEFAULT 0",
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_recognitions_snapshot_status
        ON unifi_protect_recognitions (console_key, snapshot_status, occurred_at DESC)
    """,
)


REQUIRED_ALARM_RULES = (
    ("license_plate_known", "license_plate", True, "Bilskilt · kjent"),
    ("license_plate_unknown", "license_plate", False, "Bilskilt · ukjent"),
    ("face_known", "face", True, "Ansikt · kjent"),
    ("face_unknown", "face", False, "Ansikt · ukjent"),
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        seconds = float(value) / 1000 if abs(float(value)) > 10_000_000_000 else float(value)
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return parse_timestamp(float(text))
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _scalar(value: Any) -> Optional[str]:
    if value is None or isinstance(value, (dict, list)):
        return None
    result = str(value).strip()
    return result or None


def _mapping_value(value: Any, keys: Sequence[str]) -> Optional[str]:
    if isinstance(value, Mapping):
        for key in keys:
            candidate = _scalar(value.get(key))
            if candidate:
                return candidate
        return None
    return _scalar(value)


def _first_scalar(payloads: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Optional[str]:
    for payload in payloads:
        for key in keys:
            candidate = _mapping_value(payload.get(key), ("id", "value", "name", "text"))
            if candidate:
                return candidate
    return None


def recognition_kind(trigger_key: str) -> Optional[str]:
    normalized = re.sub(r"[^a-z0-9]+", "_", trigger_key.lower()).strip("_")
    if "license" in normalized or "licence" in normalized or "plate" in normalized:
        return "license_plate"
    if "face" in normalized:
        return "face"
    if "person_of_interest" in normalized or "personofinterest" in normalized:
        return "person_of_interest"
    return None


def normalize_recognition_value(kind: str, value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if kind == "license_plate":
        normalized = re.sub(r"[^A-Z0-9]", "", value.upper())
        return normalized or None
    normalized = " ".join(value.casefold().split())
    return normalized or None


def parse_alarm_recognitions(payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    alarm = payload.get("alarm") if isinstance(payload.get("alarm"), Mapping) else {}
    event = payload.get("event") if isinstance(payload.get("event"), Mapping) else {}
    candidates = (payload, alarm, event)
    occurred_at = None
    for source in candidates:
        for key in ("timestamp", "occurredAt", "eventTime", "start", "createdAt", "date"):
            occurred_at = parse_timestamp(source.get(key))
            if occurred_at:
                break
        if occurred_at:
            break
    occurred_at = occurred_at or utc_now()

    alarm_name = _first_scalar(candidates, ("alarmName", "name", "title"))
    source_event_id = _first_scalar(candidates, ("eventId", "eventID", "sourceEventId"))
    event_link = _first_scalar(candidates, ("eventLocalLink", "eventLink", "localLink"))
    if not source_event_id and event_link:
        match = re.search(r"[0-9a-f]{8}-[0-9a-f-]{27,}", event_link, re.IGNORECASE)
        source_event_id = match.group(0) if match else None
    camera_id = _first_scalar(candidates, ("cameraId", "cameraID", "deviceId", "deviceID"))
    camera_name = _first_scalar(candidates, ("cameraName", "deviceName", "camera", "device"))
    source_device = _first_scalar(candidates, ("sourceDevice", "source", "deviceName"))

    trigger_source = alarm.get("triggers") or payload.get("triggers") or event.get("triggers") or []
    if isinstance(trigger_source, Mapping):
        triggers: list[Any] = [trigger_source]
    elif isinstance(trigger_source, list):
        triggers = trigger_source
    else:
        triggers = []

    rows: list[dict[str, Any]] = []
    for index, raw_trigger in enumerate(triggers):
        if not isinstance(raw_trigger, Mapping):
            raw_trigger = {"key": str(raw_trigger)}
        key = _first_scalar((raw_trigger,), ("key", "type", "triggerKey", "event", "name")) or "unknown"
        kind = recognition_kind(key)
        if not kind:
            continue
        key_normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
        is_known = False if "unknown" in key_normalized else True if "known" in key_normalized else None
        group_value = _mapping_value(raw_trigger.get("group"), ("name", "label", "text", "value", "id"))
        value = group_value or _first_scalar(
            (raw_trigger,),
            ("value", "plate", "licensePlate", "licencePlate", "recognizedValue", "identity", "person", "label"),
        )
        if value and value.casefold() in {"known", "unknown", "true", "false"}:
            value = None
        trigger_device = _first_scalar((raw_trigger,), ("cameraId", "cameraID", "deviceId", "deviceID", "device"))
        rows.append(
            {
                "trigger_index": index,
                "kind": kind,
                "value": value,
                "normalized_value": normalize_recognition_value(kind, value),
                "is_known": is_known,
                "trigger_key": key,
                "camera_id": camera_id or trigger_device,
                "camera_name": camera_name,
                "source_device": source_device or trigger_device,
                "source_event_id": source_event_id,
                "occurred_at": occurred_at,
                "raw": dict(raw_trigger),
            }
        )

    meta = {
        "occurred_at": occurred_at,
        "alarm_name": alarm_name,
        "source_event_id": source_event_id,
        "source_device": source_device,
        "camera_id": camera_id,
        "camera_name": camera_name,
    }
    return meta, rows


def payload_digest(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


def encode_cursor(timestamp: datetime, identifier: str | int) -> str:
    value = json.dumps([timestamp.astimezone(timezone.utc).isoformat(), str(identifier)], separators=(",", ":"))
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def decode_cursor(value: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        timestamp, identifier = json.loads(raw.decode("utf-8"))
        parsed = parse_timestamp(timestamp)
        if parsed is None or not str(identifier):
            raise ValueError
        return parsed, str(identifier)
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError, binascii.Error) as error:
        raise ValueError("Invalid cursor") from error


class EventBroker:
    def __init__(self, queue_size: int = 100):
        self.queue_size = queue_size
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self.queue_size)
        async with self._lock:
            self._subscribers.add(queue)
        try:
            yield queue
        finally:
            async with self._lock:
                self._subscribers.discard(queue)

    async def publish(self, event: dict[str, Any]) -> None:
        async with self._lock:
            queues = tuple(self._subscribers)
        for queue in queues:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


def request_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("X-API-Key", "").strip()


def require_token(request: Request, expected: str, *, purpose: str) -> None:
    if not expected:
        raise HTTPException(status_code=503, detail=f"{purpose} token is not configured")
    if not hmac.compare_digest(request_token(request), expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


def require_webhook(request: Request, expected: str, allowed_ips: frozenset[str]) -> None:
    client_ip = request.client.host if request.client else ""
    if client_ip and client_ip in allowed_ips:
        return
    supplied = request_token(request) or request.query_params.get("token", "").strip()
    if expected and hmac.compare_digest(supplied, expected):
        return
    if not expected and not allowed_ips:
        raise HTTPException(status_code=503, detail="Webhook authentication is not configured")
    raise HTTPException(status_code=401, detail="Webhook source or token is not authorized")


async def initialize(pool: asyncpg.Pool) -> None:
    for statement in RECOGNITION_SCHEMA_STATEMENTS:
        await pool.execute(statement)


async def _correlate_event(
    connection: asyncpg.Connection,
    console_key: str,
    row: Mapping[str, Any],
) -> tuple[Optional[str], Optional[str], Optional[str], str]:
    source_event_id = _scalar(row.get("source_event_id"))
    camera_id = _scalar(row.get("camera_id"))
    camera_name = _scalar(row.get("camera_name"))
    if camera_id:
        camera = await connection.fetchrow(
            """
            SELECT camera_id, name
            FROM unifi_protect_cameras
            WHERE console_key = $1
              AND (camera_id = $2 OR regexp_replace(COALESCE(mac, ''), '[^A-Fa-f0-9]', '', 'g') =
                   regexp_replace($2, '[^A-Fa-f0-9]', '', 'g'))
            LIMIT 1
            """,
            console_key,
            camera_id,
        )
        if camera:
            camera_id = camera["camera_id"]
            camera_name = camera["name"] or camera_name
    if source_event_id:
        match = await connection.fetchrow(
            """
            SELECT source_event_id, camera_id, camera_name
            FROM unifi_protect_events
            WHERE console_key = $1 AND source_event_id = $2
            """,
            console_key,
            source_event_id,
        )
        if match:
            return match["source_event_id"], match["camera_id"], match["camera_name"], "event_id"

    kind = str(row["kind"])
    detection = "licensePlate" if kind == "license_plate" else "face" if kind == "face" else "person"
    match = await connection.fetchrow(
        """
        SELECT source_event_id, camera_id, camera_name
        FROM unifi_protect_events
        WHERE console_key = $1
          AND ($2::varchar IS NULL OR camera_id = $2 OR camera_name = $3)
          AND COALESCE(start_at, last_received_at)
              BETWEEN $4::timestamptz - INTERVAL '2 minutes' AND $4::timestamptz + INTERVAL '2 minutes'
          AND ($5 = ANY(smart_detect_types) OR event_type ILIKE '%' || $5 || '%')
        ORDER BY abs(extract(epoch FROM (COALESCE(start_at, last_received_at) - $4::timestamptz)))
        LIMIT 1
        """,
        console_key,
        camera_id,
        camera_name,
        row["occurred_at"],
        detection,
    )
    if match:
        return match["source_event_id"], match["camera_id"], match["camera_name"], "nearest_event"
    return source_event_id, camera_id, camera_name, "unmatched"


async def store_alarm_webhook(
    pool: asyncpg.Pool,
    console_key: str,
    raw_body: bytes,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    webhook_id = payload_digest(raw_body)
    meta, parsed_rows = parse_alarm_recognitions(payload)
    received_at = utc_now()
    stored: list[dict[str, Any]] = []
    duplicate = False
    async with pool.acquire() as connection:
        async with connection.transaction():
            inserted = await connection.fetchval(
                """
                INSERT INTO unifi_protect_alarm_webhooks (
                    console_key, webhook_id, received_at, occurred_at, alarm_name,
                    source_event_id, source_device, recognition_count, processing_status, raw
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb)
                ON CONFLICT (console_key, webhook_id) DO NOTHING
                RETURNING webhook_id
                """,
                console_key,
                webhook_id,
                received_at,
                meta["occurred_at"],
                meta["alarm_name"],
                meta["source_event_id"],
                meta["source_device"],
                len(parsed_rows),
                "parsed" if parsed_rows else "no_recognition_triggers",
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str),
            )
            if inserted is None:
                duplicate = True
            else:
                for row in parsed_rows:
                    source_event_id, camera_id, camera_name, correlation_status = await _correlate_event(
                        connection, console_key, row
                    )
                    record = await connection.fetchrow(
                        """
                        INSERT INTO unifi_protect_recognitions (
                            console_key, webhook_id, trigger_index, kind, value, normalized_value,
                            is_known, trigger_key, camera_id, camera_name, source_device,
                            source_event_id, occurred_at, received_at, correlation_status, raw
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                            $12, $13, $14, $15, $16::jsonb
                        )
                        RETURNING recognition_id, kind, value, normalized_value, is_known,
                                  camera_id, camera_name, source_event_id, occurred_at,
                                  received_at, correlation_status
                        """,
                        console_key,
                        webhook_id,
                        row["trigger_index"],
                        row["kind"],
                        row["value"],
                        row["normalized_value"],
                        row["is_known"],
                        row["trigger_key"],
                        camera_id,
                        camera_name,
                        row["source_device"],
                        source_event_id,
                        row["occurred_at"],
                        received_at,
                        correlation_status,
                        json.dumps(row["raw"], ensure_ascii=False, separators=(",", ":"), default=str),
                    )
                    stored.append(dict(record))
                await plate_validation.upsert_plate_candidates(connection, console_key, stored)
    return {
        "status": "duplicate" if duplicate else "accepted",
        "webhook_id": webhook_id,
        "recognition_count": len(stored),
        "recognitions": stored,
    }


def _add_filter(arguments: list[Any], conditions: list[str], expression: str, value: Any) -> None:
    arguments.append(value)
    conditions.append(expression.replace("?", f"${len(arguments)}"))


async def list_events_v1(
    pool: asyncpg.Pool,
    console_key: str,
    *,
    limit: int,
    cursor: str = "",
    event_type: str = "",
    camera_id: str = "",
    detection_type: str = "",
    from_at: Optional[datetime] = None,
    to_at: Optional[datetime] = None,
    has_snapshot: Optional[bool] = None,
) -> dict[str, Any]:
    arguments: list[Any] = [console_key]
    conditions = ["console_key = $1"]
    if event_type:
        _add_filter(arguments, conditions, "event_type = ?", event_type)
    if camera_id:
        _add_filter(arguments, conditions, "camera_id = ?", camera_id)
    if detection_type:
        _add_filter(arguments, conditions, "? = ANY(smart_detect_types)", detection_type)
    if from_at:
        _add_filter(arguments, conditions, "COALESCE(start_at, last_received_at) >= ?", from_at)
    if to_at:
        _add_filter(arguments, conditions, "COALESCE(start_at, last_received_at) <= ?", to_at)
    if has_snapshot is not None:
        _add_filter(arguments, conditions, "(snapshot_status = 'stored') = ?", has_snapshot)
    if cursor:
        cursor_at, cursor_id = decode_cursor(cursor)
        arguments.extend([cursor_at, cursor_id])
        conditions.append(
            f"(COALESCE(start_at, last_received_at), source_event_id) < "
            f"(${len(arguments) - 1}::timestamptz, ${len(arguments)}::varchar)"
        )
    arguments.append(limit + 1)
    rows = await pool.fetch(
        f"""
        SELECT source_event_id, message_type, event_type, model_key, camera_id, camera_name,
               smart_detect_types, start_at, end_at, duration_ms, score,
               first_received_at, last_received_at, update_count,
               snapshot_status, snapshot_size_bytes, snapshot_captured_at,
               CASE WHEN snapshot_status = 'stored'
                    THEN '/api/v1/events/' || source_event_id || '/snapshot' END AS snapshot_url
        FROM unifi_protect_events
        WHERE {' AND '.join(conditions)}
        ORDER BY COALESCE(start_at, last_received_at) DESC, source_event_id DESC
        LIMIT ${len(arguments)}
        """,
        *arguments,
    )
    has_more = len(rows) > limit
    selected = rows[:limit]
    next_cursor = None
    if has_more and selected:
        last = selected[-1]
        next_cursor = encode_cursor(last["start_at"] or last["last_received_at"], last["source_event_id"])
    return {"items": [dict(row) for row in selected], "next_cursor": next_cursor, "has_more": has_more}


async def list_recognitions(
    pool: asyncpg.Pool,
    console_key: str,
    *,
    limit: int,
    cursor: str = "",
    kind: str = "",
    value: str = "",
    camera_id: str = "",
    is_known: Optional[bool] = None,
    from_at: Optional[datetime] = None,
    to_at: Optional[datetime] = None,
) -> dict[str, Any]:
    arguments: list[Any] = [console_key]
    conditions = ["r.console_key = $1", "COALESCE(r.source_device, '') <> 'FAKE_MAC'"]
    if kind:
        _add_filter(arguments, conditions, "r.kind = ?", kind)
    if value:
        plate_value = normalize_recognition_value("license_plate", value) or value
        text_value = normalize_recognition_value("face", value) or value
        arguments.extend([plate_value, text_value])
        conditions.append(
            f"(regexp_replace(upper(COALESCE(r.normalized_value, '')), '[^A-Z0-9]', '', 'g') "
            f"LIKE '%' || ${len(arguments) - 1} || '%' "
            f"OR COALESCE(r.normalized_value, '') ILIKE '%' || ${len(arguments)} || '%' "
            f"OR COALESCE(r.value, '') ILIKE '%' || ${len(arguments)} || '%')"
        )
    if camera_id:
        _add_filter(arguments, conditions, "r.camera_id = ?", camera_id)
    if is_known is not None:
        _add_filter(arguments, conditions, "r.is_known = ?", is_known)
    if from_at:
        _add_filter(arguments, conditions, "r.occurred_at >= ?", from_at)
    if to_at:
        _add_filter(arguments, conditions, "r.occurred_at <= ?", to_at)
    if cursor:
        cursor_at, cursor_id = decode_cursor(cursor)
        try:
            numeric_id = int(cursor_id)
        except ValueError as error:
            raise ValueError("Invalid cursor") from error
        arguments.extend([cursor_at, numeric_id])
        conditions.append(f"(r.occurred_at, r.recognition_id) < (${len(arguments) - 1}::timestamptz, ${len(arguments)}::bigint)")
    arguments.append(limit + 1)
    rows = await pool.fetch(
        f"""
        SELECT r.recognition_id, r.kind, r.value, r.normalized_value, r.is_known,
               r.trigger_key, r.camera_id, r.camera_name, r.source_event_id,
               r.occurred_at, r.received_at, r.correlation_status,
               r.snapshot_status, r.snapshot_captured_at, r.snapshot_target_at,
               r.snapshot_time_offset_ms, r.snapshot_source, r.snapshot_camera_id,
               CASE WHEN r.snapshot_status = 'stored'
                    THEN '/api/v1/recognitions/' || r.recognition_id || '/snapshot' END AS snapshot_url
        FROM unifi_protect_recognitions r
        WHERE {' AND '.join(conditions)}
        ORDER BY r.occurred_at DESC, r.recognition_id DESC
        LIMIT ${len(arguments)}
        """,
        *arguments,
    )
    has_more = len(rows) > limit
    selected = rows[:limit]
    next_cursor = None
    if has_more and selected:
        last = selected[-1]
        next_cursor = encode_cursor(last["occurred_at"], last["recognition_id"])
    return {"items": [dict(row) for row in selected], "next_cursor": next_cursor, "has_more": has_more}


def plate_edit_distance(left: str, right: str) -> int:
    left_value = plate_validation.compact_plate(left)
    right_value = plate_validation.compact_plate(right)
    if len(left_value) > len(right_value):
        left_value, right_value = right_value, left_value
    previous = list(range(len(left_value) + 1))
    for right_index, right_character in enumerate(right_value, start=1):
        current = [right_index]
        for left_index, left_character in enumerate(left_value, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[left_index] + 1,
                    previous[left_index - 1] + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]


def likely_plate_variants(left: Mapping[str, Any], right: Mapping[str, Any], maximum_seconds: int = 120) -> bool:
    left_plate = plate_validation.compact_plate(left.get("plate"))
    right_plate = plate_validation.compact_plate(right.get("plate"))
    left_validation = left.get("validation") if isinstance(left.get("validation"), Mapping) else {}
    right_validation = right.get("validation") if isinstance(right.get("validation"), Mapping) else {}
    # Two independently confirmed registrations must never be collapsed into one OCR reading.
    if left_validation.get("is_valid") is True and right_validation.get("is_valid") is True:
        return False
    if left_plate == right_plate or min(len(left_plate), len(right_plate)) < 5:
        return False
    if abs(len(left_plate) - len(right_plate)) > 2:
        return False
    distance_limit = 1 if max(len(left_plate), len(right_plate)) <= 6 else 2
    if plate_edit_distance(left_plate, right_plate) > distance_limit:
        return False
    for left_detection in left.get("quality_detections") or left.get("detections") or []:
        left_at = parse_timestamp(left_detection.get("occurred_at"))
        left_camera = left_detection.get("camera_id") or left_detection.get("camera_name")
        if not left_at or not left_camera:
            continue
        for right_detection in right.get("quality_detections") or right.get("detections") or []:
            right_at = parse_timestamp(right_detection.get("occurred_at"))
            right_camera = right_detection.get("camera_id") or right_detection.get("camera_name")
            if right_at and left_camera == right_camera and abs((left_at - right_at).total_seconds()) <= maximum_seconds:
                return True
    return False


def _canonical_priority(item: Mapping[str, Any]) -> tuple[int, int, int, float, int]:
    validation = item.get("validation") if isinstance(item.get("validation"), Mapping) else {}
    score = item.get("average_unifi_score")
    try:
        numeric_score = float(score) if score is not None else -1.0
    except (TypeError, ValueError):
        numeric_score = -1.0
    return (
        1 if validation.get("is_valid") is True else 0,
        1 if item.get("known_in_protect") else 0,
        int(item.get("detection_count") or 0),
        numeric_score,
        len(str(item.get("plate") or "")),
    )


def add_plate_quality(items: list[dict[str, Any]]) -> None:
    """Annotate, but never destructively merge, likely OCR variants."""
    by_plate = {str(item.get("plate") or ""): item for item in items}
    for item in items:
        item["ocr_variant_candidates"] = []
        item["is_likely_ocr_variant"] = False
        item["likely_canonical_plate"] = item.get("plate")
    plates = list(by_plate)
    for left_index, left_plate in enumerate(plates):
        for right_plate in plates[left_index + 1 :]:
            left = by_plate[left_plate]
            right = by_plate[right_plate]
            if not likely_plate_variants(left, right):
                continue
            distance = plate_edit_distance(left_plate, right_plate)
            left["ocr_variant_candidates"].append(
                {"plate": right_plate, "edit_distance": distance, "detection_count": right.get("detection_count", 0)}
            )
            right["ocr_variant_candidates"].append(
                {"plate": left_plate, "edit_distance": distance, "detection_count": left.get("detection_count", 0)}
            )
    for item in items:
        related = [by_plate[row["plate"]] for row in item["ocr_variant_candidates"]]
        if related:
            canonical = max([item, *related], key=_canonical_priority)
            item["likely_canonical_plate"] = canonical.get("plate")
            item["is_likely_ocr_variant"] = canonical is not item
            item["ocr_variant_candidates"].sort(
                key=lambda row: (-int(row.get("detection_count") or 0), str(row.get("plate") or ""))
            )
        validation = item.get("validation") or {}
        validation_resolved = validation.get("is_valid") is not None
        item["likely_misread"] = bool(
            validation.get("likely_misread")
            or (item["is_likely_ocr_variant"] and validation_resolved and validation.get("is_valid") is False)
        )
        item["requires_review"] = bool(
            item["likely_misread"] or item["is_likely_ocr_variant"] or not validation_resolved
        )
        item["presentation_status"] = (
            "likely_misread"
            if item["likely_misread"]
            else "valid"
            if validation.get("is_valid") is True
            else "pending_review"
        )


async def daily_license_plates(
    pool: asyncpg.Pool,
    console_key: str,
    *,
    from_at: datetime,
    to_at: datetime,
    include_detections: bool = True,
    plate: str = "",
) -> dict[str, Any]:
    """Return one complete row per plate while retaining every detection for the day."""
    plate_value = plate_validation.compact_plate(plate)
    plate_filter = "AND r.normalized_value = $4" if plate_value else ""
    query_arguments: tuple[Any, ...] = (
        (console_key, from_at, to_at, plate_value)
        if plate_value
        else (console_key, from_at, to_at)
    )
    detection_rollup = """
        , detection_rollup AS (
            SELECT normalized_value AS plate,
                   jsonb_agg(
                       jsonb_build_object(
                           'recognition_id', recognition_id,
                           'occurred_at', occurred_at,
                           'camera_id', camera_id,
                           'camera_name', camera_name,
                           'source_event_id', source_event_id,
                           'unifi_score', unifi_score,
                           'snapshot_url', snapshot_url,
                           'snapshot_status', snapshot_status,
                           'snapshot_captured_at', snapshot_captured_at,
                           'snapshot_target_at', snapshot_target_at,
                           'snapshot_time_offset_ms', snapshot_time_offset_ms,
                           'snapshot_source', snapshot_source,
                           'snapshot_camera_id', snapshot_camera_id
                       ) ORDER BY occurred_at ASC, recognition_id ASC
                   ) AS detections
            FROM plate_rows
            GROUP BY normalized_value
        )
    """ if include_detections else ""
    detection_select = "d.detections" if include_detections else """
        CASE
            WHEN p.first_recognition_id = p.last_recognition_id THEN jsonb_build_array(
                jsonb_build_object(
                    'recognition_id', first_row.recognition_id,
                    'occurred_at', first_row.occurred_at,
                    'camera_id', first_row.camera_id,
                    'camera_name', first_row.camera_name,
                    'source_event_id', first_row.source_event_id,
                    'unifi_score', first_row.unifi_score,
                    'snapshot_url', first_row.snapshot_url,
                    'snapshot_status', first_row.snapshot_status,
                    'snapshot_captured_at', first_row.snapshot_captured_at,
                    'snapshot_target_at', first_row.snapshot_target_at,
                    'snapshot_time_offset_ms', first_row.snapshot_time_offset_ms,
                    'snapshot_source', first_row.snapshot_source,
                    'snapshot_camera_id', first_row.snapshot_camera_id
                )
            )
            ELSE jsonb_build_array(
                jsonb_build_object(
                    'recognition_id', first_row.recognition_id,
                    'occurred_at', first_row.occurred_at,
                    'camera_id', first_row.camera_id,
                    'camera_name', first_row.camera_name,
                    'source_event_id', first_row.source_event_id,
                    'unifi_score', first_row.unifi_score,
                    'snapshot_url', first_row.snapshot_url,
                    'snapshot_status', first_row.snapshot_status,
                    'snapshot_captured_at', first_row.snapshot_captured_at,
                    'snapshot_target_at', first_row.snapshot_target_at,
                    'snapshot_time_offset_ms', first_row.snapshot_time_offset_ms,
                    'snapshot_source', first_row.snapshot_source,
                    'snapshot_camera_id', first_row.snapshot_camera_id
                ),
                jsonb_build_object(
                    'recognition_id', last_row.recognition_id,
                    'occurred_at', last_row.occurred_at,
                    'camera_id', last_row.camera_id,
                    'camera_name', last_row.camera_name,
                    'source_event_id', last_row.source_event_id,
                    'unifi_score', last_row.unifi_score,
                    'snapshot_url', last_row.snapshot_url,
                    'snapshot_status', last_row.snapshot_status,
                    'snapshot_captured_at', last_row.snapshot_captured_at,
                    'snapshot_target_at', last_row.snapshot_target_at,
                    'snapshot_time_offset_ms', last_row.snapshot_time_offset_ms,
                    'snapshot_source', last_row.snapshot_source,
                    'snapshot_camera_id', last_row.snapshot_camera_id
                )
            )
        END
    """
    detection_join = "LEFT JOIN detection_rollup d ON d.plate = p.plate" if include_detections else """
        LEFT JOIN plate_rows first_row ON first_row.recognition_id = p.first_recognition_id
        LEFT JOIN plate_rows last_row ON last_row.recognition_id = p.last_recognition_id
    """
    rows = await pool.fetch(
        f"""
        WITH plate_rows AS (
            SELECT r.recognition_id, r.value, r.normalized_value, r.is_known,
                   r.camera_id, r.camera_name, r.source_event_id, r.occurred_at,
                   COALESCE(
                       e.score,
                       CASE
                           WHEN jsonb_typeof(r.raw #> '{{sourceEvent,score}}') = 'number'
                           THEN (r.raw #>> '{{sourceEvent,score}}')::double precision
                       END
                   ) AS unifi_score,
                   CASE
                       WHEN r.snapshot_status = 'stored' THEN 'stored'
                       WHEN e.snapshot_status = 'stored' THEN 'stored'
                       ELSE r.snapshot_status
                   END AS snapshot_status,
                   CASE
                       WHEN r.snapshot_status = 'stored' THEN r.snapshot_captured_at
                       WHEN e.snapshot_status = 'stored' THEN e.snapshot_captured_at
                   END AS snapshot_captured_at,
                   r.snapshot_target_at,
                   CASE
                       WHEN r.snapshot_status = 'stored' THEN r.snapshot_time_offset_ms
                       WHEN e.snapshot_status = 'stored' AND e.snapshot_captured_at IS NOT NULL
                       THEN round(extract(epoch FROM (e.snapshot_captured_at - r.occurred_at)) * 1000)::integer
                   END AS snapshot_time_offset_ms,
                   CASE
                       WHEN r.snapshot_status = 'stored' THEN r.snapshot_source
                       WHEN e.snapshot_status = 'stored' THEN 'event_snapshot_fallback'
                   END AS snapshot_source,
                   CASE
                       WHEN r.snapshot_status = 'stored' THEN r.snapshot_camera_id
                       WHEN e.snapshot_status = 'stored' THEN r.camera_id
                   END AS snapshot_camera_id,
                   CASE WHEN r.snapshot_status = 'stored' OR e.snapshot_status = 'stored'
                        THEN '/api/v1/recognitions/' || r.recognition_id || '/snapshot' END AS snapshot_url
            FROM unifi_protect_recognitions r
            LEFT JOIN unifi_protect_events e
              ON e.console_key = r.console_key AND e.source_event_id = r.source_event_id
            WHERE r.console_key = $1
              AND r.kind = 'license_plate'
              AND r.normalized_value IS NOT NULL
              AND r.normalized_value <> ''
              AND COALESCE(r.source_device, '') <> 'FAKE_MAC'
              AND r.occurred_at >= $2
              AND r.occurred_at < $3
              {plate_filter}
        ), plate_totals AS (
            SELECT normalized_value AS plate,
                   (array_agg(value ORDER BY occurred_at DESC, recognition_id DESC))[1] AS display_value,
                   count(*)::integer AS detection_count,
                   min(occurred_at) AS first_detected_at,
                   max(occurred_at) AS last_detected_at,
                   round(avg(unifi_score)::numeric, 1)::double precision AS average_unifi_score,
                   min(unifi_score) AS minimum_unifi_score,
                   max(unifi_score) AS maximum_unifi_score,
                   count(unifi_score)::integer AS scored_detection_count,
                   bool_or(is_known IS TRUE) AS known_in_protect,
                   array_agg(DISTINCT COALESCE(camera_name, camera_id))
                       FILTER (WHERE COALESCE(camera_name, camera_id) IS NOT NULL) AS camera_names,
                   (array_agg(recognition_id ORDER BY occurred_at ASC, recognition_id ASC))[1]
                       AS first_recognition_id,
                   (array_agg(recognition_id ORDER BY occurred_at DESC, recognition_id DESC))[1]
                       AS last_recognition_id,
                   array_agg(occurred_at ORDER BY occurred_at ASC, recognition_id ASC)
                       AS detection_times,
                   array_agg(camera_id ORDER BY occurred_at ASC, recognition_id ASC)
                       AS detection_camera_ids
            FROM plate_rows
            GROUP BY normalized_value
        )
        {detection_rollup}
        SELECT p.*,
               {detection_select} AS detections,
               v.status AS validation_status,
               v.is_valid AS validation_is_valid,
               v.likely_misread AS validation_likely_misread,
               v.country_code AS validation_country_code,
               v.source AS validation_source,
               v.vehicle_label AS validation_vehicle_label,
               v.local_match AS validation_local_match,
               v.sources AS validation_sources,
               v.error AS validation_error,
               v.checked_at AS validation_checked_at,
               v.next_check_at AS validation_next_check_at
        FROM plate_totals p
        {detection_join}
        LEFT JOIN unifi_protect_plate_validations v
          ON v.console_key = $1 AND v.plate = p.plate
        ORDER BY p.last_detected_at DESC, p.plate ASC
        """,
        *query_arguments,
    )
    items = []
    for row in rows:
        item = dict(row)
        if isinstance(item.get("detections"), str):
            item["detections"] = json.loads(item["detections"])
        item["quality_detections"] = [
            {"occurred_at": occurred_at, "camera_id": camera_id}
            for occurred_at, camera_id in zip(
                item.get("detection_times") or [],
                item.get("detection_camera_ids") or [],
            )
        ]
        item["validation"] = plate_validation.public_validation(item)
        for key in list(item):
            if key.startswith("validation_"):
                item.pop(key, None)
        items.append(item)

    add_plate_quality(items)
    for item in items:
        item.pop("quality_detections", None)
        item.pop("detection_camera_ids", None)
    return {
        "from": from_at,
        "to": to_at,
        "summary": {
            "unique_plates": len(items),
            "detections": sum(int(item.get("detection_count") or 0) for item in items),
            "known_plates": sum(1 for item in items if item.get("known_in_protect")),
            "validated_plates": sum(1 for item in items if item["validation"].get("is_valid") is True),
            "pending_validation": sum(1 for item in items if item["validation"].get("is_valid") is None),
            "likely_misreads": sum(1 for item in items if item.get("likely_misread")),
            "review_required": sum(1 for item in items if item.get("requires_review")),
        },
        "items": items,
    }


async def recognition_detail(
    pool: asyncpg.Pool,
    console_key: str,
    recognition_id: int,
) -> Optional[dict[str, Any]]:
    row = await pool.fetchrow(
        """
        SELECT r.recognition_id, r.webhook_id, r.trigger_index, r.kind, r.value,
               r.normalized_value, r.is_known, r.trigger_key, r.camera_id,
               r.camera_name, r.source_device, r.source_event_id, r.occurred_at,
               r.received_at, r.correlation_status, r.raw AS trigger_raw,
               w.alarm_name, w.processing_status AS webhook_status,
               w.raw AS webhook_raw,
               r.snapshot_status, r.snapshot_path, r.snapshot_content_type,
               r.snapshot_size_bytes, r.snapshot_captured_at, r.snapshot_target_at,
               r.snapshot_time_offset_ms, r.snapshot_source, r.snapshot_camera_id,
               r.snapshot_error, r.snapshot_attempt_count,
               CASE WHEN r.snapshot_status = 'stored'
                    THEN '/api/v1/recognitions/' || r.recognition_id || '/snapshot' END AS snapshot_url
        FROM unifi_protect_recognitions r
        JOIN unifi_protect_alarm_webhooks w
          ON w.console_key = r.console_key AND w.webhook_id = r.webhook_id
        WHERE r.console_key = $1 AND r.recognition_id = $2
        """,
        console_key,
        recognition_id,
    )
    return dict(row) if row else None


async def alarm_manager_status(pool: asyncpg.Pool, console_key: str) -> dict[str, Any]:
    webhook_totals = await pool.fetchrow(
        """
        SELECT count(*) AS total,
               count(*) FILTER (WHERE received_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours') AS last_24h,
               max(received_at) AS last_received_at,
               max(occurred_at) AS last_occurred_at
        FROM unifi_protect_alarm_webhooks
        WHERE console_key = $1
        """,
        console_key,
    )
    recognition_totals = await pool.fetchrow(
        """
        SELECT count(*) AS total, max(received_at) AS last_received_at
        FROM unifi_protect_recognitions
        WHERE console_key = $1
        """,
        console_key,
    )
    observed_rows = await pool.fetch(
        """
        SELECT kind, is_known, count(*) AS count, max(received_at) AS last_received_at
        FROM unifi_protect_recognitions
        WHERE console_key = $1
          AND kind IN ('license_plate', 'face')
          AND is_known IS NOT NULL
        GROUP BY kind, is_known
        """,
        console_key,
    )
    observed = {
        (str(row["kind"]), bool(row["is_known"])): row
        for row in observed_rows
    }
    rules = []
    for key, kind, is_known, label in REQUIRED_ALARM_RULES:
        match = observed.get((kind, is_known))
        rules.append(
            {
                "key": key,
                "kind": kind,
                "is_known": is_known,
                "label": label,
                "verified": match is not None,
                "received_count": int(match["count"]) if match else 0,
                "last_received_at": match["last_received_at"] if match else None,
            }
        )
    verified_count = sum(1 for rule in rules if rule["verified"])
    return {
        "webhooks": dict(webhook_totals) if webhook_totals else {},
        "recognitions": dict(recognition_totals) if recognition_totals else {},
        "required_rules": rules,
        "verified_rule_count": verified_count,
        "required_rule_count": len(rules),
        "all_rules_verified": verified_count == len(rules),
    }


async def recognition_summary(pool: asyncpg.Pool, console_key: str) -> dict[str, Any]:
    totals = await pool.fetchrow(
        """
        SELECT count(*) AS total,
               count(*) FILTER (WHERE occurred_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours') AS last_24h,
               count(*) FILTER (WHERE kind = 'license_plate') AS license_plates,
               count(*) FILTER (WHERE kind = 'face') AS faces,
               count(*) FILTER (WHERE is_known IS TRUE) AS known,
               count(*) FILTER (WHERE is_known IS FALSE) AS unknown,
               count(DISTINCT normalized_value) FILTER (WHERE normalized_value IS NOT NULL) AS unique_values,
               max(occurred_at) AS last_recognition_at
        FROM unifi_protect_recognitions
        WHERE console_key = $1 AND COALESCE(source_device, '') <> 'FAKE_MAC'
        """,
        console_key,
    )
    recent = await list_recognitions(pool, console_key, limit=12)
    return {"totals": dict(totals) if totals else {}, "recent": recent["items"]}
