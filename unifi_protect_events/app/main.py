from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import random
import ssl
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Optional
from urllib.parse import quote, urlparse, urlunparse
from zoneinfo import ZoneInfo

import aiohttp
import asyncpg
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import admin, bollards, integration, plate_validation
from .build_log import (
    protect_ledger_build_detail,
    protect_ledger_build_log_payload,
    protect_ledger_build_summary,
)


logger = logging.getLogger("unifi_protect_events")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

CAMERAS_PATH = "/proxy/protect/integration/v1/cameras"
EVENTS_PATH = "/proxy/protect/integration/v1/subscribe/events"
SNAPSHOT_PATH = "/proxy/protect/integration/v1/cameras/{camera_id}/snapshot"

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_cameras (
        console_key VARCHAR NOT NULL,
        camera_id VARCHAR NOT NULL,
        name VARCHAR,
        model_key VARCHAR,
        mac VARCHAR,
        state VARCHAR,
        synced_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        raw JSONB NOT NULL,
        PRIMARY KEY (console_key, camera_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_events (
        console_key VARCHAR NOT NULL,
        source_event_id VARCHAR NOT NULL,
        message_type VARCHAR NOT NULL,
        event_type VARCHAR,
        model_key VARCHAR,
        camera_id VARCHAR,
        camera_name VARCHAR,
        start_at TIMESTAMPTZ,
        end_at TIMESTAMPTZ,
        score DOUBLE PRECISION,
        first_received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        update_count INTEGER NOT NULL DEFAULT 1,
        raw JSONB NOT NULL,
        PRIMARY KEY (console_key, source_event_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_start
        ON unifi_protect_events (start_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_camera_start
        ON unifi_protect_events (console_key, camera_id, start_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_type_start
        ON unifi_protect_events (event_type, start_at DESC)
    """,
)


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def csv_set(raw: str, *, lower: bool = False) -> frozenset[str]:
    values = [value.strip() for value in raw.split(",") if value.strip()]
    if lower:
        values = [value.lower() for value in values]
    return frozenset(values)


def normalize_nvr_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError("UNIFI_PROTECT_NVR_URL is required")
    if "://" not in value:
        value = f"https://{value}"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("UNIFI_PROTECT_NVR_URL must be an http(s) URL or host name")
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise ValueError("UNIFI_PROTECT_NVR_URL must not include a path, query or fragment")
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", "")).rstrip("/")


def websocket_url(nvr_url: str) -> str:
    parsed = urlparse(nvr_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, EVENTS_PATH, "", "", ""))


def asyncpg_dsn(raw: str) -> str:
    value = raw.strip()
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://"):
        if value.startswith(prefix):
            return "postgresql://" + value.removeprefix(prefix)
    if value.startswith("postgres://"):
        return "postgresql://" + value.removeprefix("postgres://")
    return value


def epoch_ms_to_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    try:
        milliseconds = float(value)
        return datetime.fromtimestamp(milliseconds / 1000.0, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def optional_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def scalar_text(value: Any) -> Optional[str]:
    if value is None or isinstance(value, (dict, list)):
        return None
    text = str(value).strip()
    return text or None


def snapshot_relative_path(
    console_key: str,
    camera_id: str,
    source_event_id: str,
    captured_at: datetime,
) -> Path:
    camera_hash = hashlib.sha256(f"{console_key}:{camera_id}".encode("utf-8")).hexdigest()[:12]
    event_hash = hashlib.sha256(f"{console_key}:{source_event_id}".encode("utf-8")).hexdigest()
    return Path(
        captured_at.strftime("%Y"),
        captured_at.strftime("%m"),
        captured_at.strftime("%d"),
        camera_hash,
        f"{event_hash}.jpg",
    )


def recognition_snapshot_relative_path(
    console_key: str,
    camera_id: str,
    recognition_id: int,
    captured_at: datetime,
) -> Path:
    camera_hash = hashlib.sha256(f"{console_key}:{camera_id}".encode("utf-8")).hexdigest()[:12]
    recognition_hash = hashlib.sha256(
        f"{console_key}:recognition:{recognition_id}".encode("utf-8")
    ).hexdigest()
    return Path(
        captured_at.strftime("%Y"),
        captured_at.strftime("%m"),
        captured_at.strftime("%d"),
        camera_hash,
        "recognitions",
        f"{recognition_hash}.jpg",
    )


def recognition_capture_delay(
    target_at: Optional[datetime],
    now: Optional[datetime] = None,
    *,
    request_lead_seconds: float = 0.2,
    maximum_wait_seconds: float = 3.0,
) -> float:
    """Return a short delay that aligns a live snapshot with the OCR timestamp.

    Protect timestamps have been observed up to roughly one second ahead of the
    webhook receipt time.  We wait for that timestamp, but never let a bad clock
    hold the recognition queue for more than a few seconds.
    """
    if target_at is None:
        return 0.0
    current = now or datetime.now(timezone.utc)
    if target_at.tzinfo is None:
        target_at = target_at.replace(tzinfo=timezone.utc)
    delay = (target_at.astimezone(timezone.utc) - current.astimezone(timezone.utc)).total_seconds()
    delay -= max(0.0, request_lead_seconds)
    if delay <= 0 or delay > maximum_wait_seconds:
        return 0.0
    return delay


def write_snapshot_atomic(root: Path, relative_path: Path, content: bytes) -> Path:
    root = root.resolve()
    destination = (root / relative_path).resolve()
    if not destination.is_relative_to(root):
        raise ValueError("Snapshot path is outside the configured directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.part")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def normalize_event_message(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("Protect message must be a JSON object")
    item = payload.get("item")
    if not isinstance(item, Mapping):
        raise ValueError("Protect message is missing an item object")

    raw_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    source_event_id = scalar_text(item.get("id"))
    if not source_event_id:
        digest = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
        source_event_id = f"synthetic:{digest}"

    camera = item.get("device") or item.get("camera") or item.get("cameraId")
    if isinstance(camera, Mapping):
        camera = camera.get("id")

    start_at = epoch_ms_to_datetime(item.get("start"))
    end_at = epoch_ms_to_datetime(item.get("end"))
    duration_ms = None
    if start_at is not None and end_at is not None:
        duration_ms = max(0, int((end_at - start_at).total_seconds() * 1000))

    return {
        "source_event_id": source_event_id,
        "message_type": scalar_text(payload.get("type")) or "unknown",
        "event_type": scalar_text(item.get("type")),
        "model_key": scalar_text(item.get("modelKey")),
        "camera_id": scalar_text(camera),
        "start_at": start_at,
        "end_at": end_at,
        "duration_ms": duration_ms,
        "smart_detect_types": admin.extract_detection_types(item),
        "score": optional_float(item.get("score")),
        "raw_json": raw_json,
    }


@dataclass(frozen=True)
class Settings:
    nvr_url: str
    api_key: str
    database_url: str
    console_key: str
    verify_ssl: bool
    camera_ids: frozenset[str]
    event_types: frozenset[str]
    reconnect_min_seconds: float
    reconnect_max_seconds: float
    snapshot_dir: Path = Path("/data/snapshots")
    read_api_token: str = ""
    webhook_token: str = ""
    webhook_allowed_ips: frozenset[str] = frozenset({"192.168.1.1", "192.168.20.1"})
    snapshot_workers: int = 2
    snapshot_queue_size: int = 1000
    recognition_snapshot_workers: int = 2

    @classmethod
    def from_env(cls) -> "Settings":
        nvr_url = normalize_nvr_url(os.getenv("UNIFI_PROTECT_NVR_URL", ""))
        api_key = os.getenv("UNIFI_PROTECT_API_KEY", "").strip()
        database_url = asyncpg_dsn(os.getenv("DATABASE_URL", ""))
        if not api_key:
            raise ValueError("UNIFI_PROTECT_API_KEY is required")
        if not database_url:
            raise ValueError("DATABASE_URL is required")
        parsed = urlparse(nvr_url)
        console_key = os.getenv("UNIFI_PROTECT_CONSOLE_KEY", "").strip() or parsed.netloc
        reconnect_min = max(0.5, float(os.getenv("UNIFI_PROTECT_RECONNECT_MIN_SECONDS", "2")))
        reconnect_max = max(reconnect_min, float(os.getenv("UNIFI_PROTECT_RECONNECT_MAX_SECONDS", "60")))
        return cls(
            nvr_url=nvr_url,
            api_key=api_key,
            database_url=database_url,
            console_key=console_key,
            verify_ssl=env_bool("UNIFI_PROTECT_VERIFY_SSL", False),
            camera_ids=csv_set(os.getenv("UNIFI_PROTECT_CAMERA_IDS", "")),
            event_types=csv_set(os.getenv("UNIFI_PROTECT_EVENT_TYPES", ""), lower=True),
            reconnect_min_seconds=reconnect_min,
            reconnect_max_seconds=reconnect_max,
            snapshot_dir=Path(os.getenv("UNIFI_PROTECT_SNAPSHOT_DIR", "/data/snapshots")),
            read_api_token=os.getenv("UNIFI_PROTECT_READ_API_TOKEN", "").strip(),
            webhook_token=os.getenv("UNIFI_PROTECT_WEBHOOK_TOKEN", "").strip(),
            webhook_allowed_ips=csv_set(
                os.getenv("UNIFI_PROTECT_WEBHOOK_ALLOWED_IPS", "192.168.1.1,192.168.20.1")
            ),
            snapshot_workers=max(1, min(8, int(os.getenv("UNIFI_PROTECT_SNAPSHOT_WORKERS", "2")))),
            snapshot_queue_size=max(10, min(10000, int(os.getenv("UNIFI_PROTECT_SNAPSHOT_QUEUE_SIZE", "1000")))),
            recognition_snapshot_workers=max(
                1,
                min(8, int(os.getenv("UNIFI_PROTECT_RECOGNITION_SNAPSHOT_WORKERS", "2"))),
            ),
        )


class ProtectEventCollector:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pool: Optional[asyncpg.Pool] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.validation_session: Optional[aiohttp.ClientSession] = None
        self.policy: Optional[admin.PolicyCache] = None
        self.camera_names: dict[str, str] = {}
        self.database_ready = False
        self.websocket_connected = False
        self.last_connected_at: Optional[datetime] = None
        self.last_event_at: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.events_stored = 0
        self.events_ignored = 0
        self.snapshots_stored = 0
        self.snapshots_failed = 0
        self.last_retention_at: Optional[datetime] = None
        self.last_retention_deleted = 0
        self.last_retention_recognitions = 0
        self.last_retention_webhooks = 0
        self.last_retention_bollard_incidents = 0
        self.started_at = datetime.now(timezone.utc)
        self._ssl_context = self._make_ssl_context()
        self.broker = integration.EventBroker()
        self.snapshot_queue: asyncio.Queue[Mapping[str, Any]] = asyncio.Queue(
            maxsize=settings.snapshot_queue_size
        )
        self.snapshot_tasks: list[asyncio.Task[None]] = []
        self.recognition_snapshot_queue: asyncio.Queue[Mapping[str, Any]] = asyncio.Queue(
            maxsize=settings.snapshot_queue_size
        )
        self.recognition_snapshot_tasks: list[asyncio.Task[None]] = []
        self.recognition_snapshots_stored = 0
        self.recognition_snapshots_failed = 0
        self.plate_validator: Optional[plate_validation.PlateValidator] = None
        self.bollard_service: Optional[bollards.BollardService] = None

    def _make_ssl_context(self) -> Optional[ssl.SSLContext]:
        if urlparse(self.settings.nvr_url).scheme != "https":
            return None
        context = ssl.create_default_context()
        if not self.settings.verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    def _safe_error(self, error: BaseException) -> str:
        return str(error).replace(self.settings.api_key, "***")[:500]

    async def start(self) -> None:
        self.settings.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.pool = await asyncpg.create_pool(
            dsn=self.settings.database_url,
            min_size=1,
            max_size=5,
            command_timeout=30,
        )
        for statement in SCHEMA_STATEMENTS:
            await self.pool.execute(statement)
        await admin.initialize(self.pool, self.settings.console_key)
        await integration.initialize(self.pool)
        await self.recover_interrupted_snapshots()
        self.policy = await admin.load_policy(self.pool, self.settings.console_key)
        timeout = aiohttp.ClientTimeout(total=None, connect=15, sock_connect=15)
        self.session = aiohttp.ClientSession(
            headers={"Accept": "application/json", "X-API-Key": self.settings.api_key},
            timeout=timeout,
        )
        # Registry requests must never inherit the UniFi API key.
        self.validation_session = aiohttp.ClientSession(
            headers={"Accept": "application/json"},
            timeout=aiohttp.ClientTimeout(total=None, connect=15, sock_connect=15),
        )
        validation_settings = plate_validation.ValidationSettings(
            enabled=env_bool("PROTECT_PLATE_VALIDATION_ENABLED", True),
            svv_api_key=os.getenv("SVV_API_KEY", "").strip(),
            svv_api_url=os.getenv(
                "SVV_API_URL",
                "https://www.vegvesen.no/ws/no/vegvesen/kjoretoy/felles/datautlevering/enkeltoppslag/kjoretoydata",
            ).strip(),
            svv_auth_header=os.getenv("SVV_API_AUTH_HEADER", "SVV-Authorization").strip(),
            svv_auth_prefix=os.getenv("SVV_API_AUTH_PREFIX", "Apikey").strip(),
            car_info_url=os.getenv("CAR_INFO_LOOKUP_URL", "http://car_info_lookup:8126").strip(),
            car_info_token=os.getenv("CAR_INFO_APP_TOKEN", "").strip(),
            interval_seconds=max(5, int(os.getenv("PROTECT_PLATE_VALIDATION_INTERVAL_SECONDS", "30"))),
            batch_size=max(1, min(100, int(os.getenv("PROTECT_PLATE_VALIDATION_BATCH_SIZE", "20")))),
            timeout_seconds=max(5, int(os.getenv("PROTECT_PLATE_VALIDATION_TIMEOUT_SECONDS", "30"))),
            valid_cache_days=max(1, int(os.getenv("PROTECT_PLATE_VALIDATION_CACHE_DAYS", "30"))),
            negative_cache_days=max(1, int(os.getenv("PROTECT_PLATE_NEGATIVE_CACHE_DAYS", "7"))),
            transient_retry_minutes=max(5, int(os.getenv("PROTECT_PLATE_RETRY_MINUTES", "30"))),
        )
        self.plate_validator = plate_validation.PlateValidator(
            self.pool,
            self.validation_session,
            self.settings.console_key,
            validation_settings,
        )
        await self.plate_validator.initialize()
        master_hash = os.getenv("MASTER_ACCESS_KEY_HASH", "").strip()
        bollard_topic = os.getenv("PROTECT_BOLLARD_NTFY_TOPIC", "").strip()
        if not bollard_topic and master_hash:
            topic_hash = hashlib.sha256(f"protect-bollards:{master_hash}".encode()).hexdigest()[:24]
            bollard_topic = f"protect-pullerter-{topic_hash}"
        self.bollard_service = bollards.BollardService(
            self.pool,
            self.settings.console_key,
            self.settings.snapshot_dir,
            self.fetch_camera_jpeg,
            self.validation_session,
            ntfy_base_url=os.getenv("NTFY_BASE_URL", "https://ntfy.sh").strip(),
            ntfy_topic=bollard_topic,
            alarm_app_url=os.getenv("ALARM_APP_URL", "https://alarm.lilletorget.net").strip(),
            visual_ai_url=os.getenv("VISUAL_AI_URL", "").strip(),
            visual_ai_token=os.getenv("VISUAL_AI_TOKEN", "").strip(),
            visual_ai_timeout_seconds=max(
                3, int(os.getenv("VISUAL_AI_TIMEOUT_SECONDS", "30"))
            ),
        )
        await self.bollard_service.initialize()
        self.bollard_service.start()
        self.database_ready = True
        self.snapshot_tasks = [
            asyncio.create_task(self.snapshot_worker(index + 1), name=f"protect-snapshot-{index + 1}")
            for index in range(self.settings.snapshot_workers)
        ]
        self.recognition_snapshot_tasks = [
            asyncio.create_task(
                self.recognition_snapshot_worker(index + 1),
                name=f"protect-recognition-snapshot-{index + 1}",
            )
            for index in range(self.settings.recognition_snapshot_workers)
        ]

    async def recover_interrupted_snapshots(self) -> None:
        if self.pool is None:
            return
        error = "Snapshot capture was interrupted by service restart"
        await self.pool.execute(
            """
            UPDATE unifi_protect_events
            SET snapshot_status = 'failed', snapshot_error = $2
            WHERE console_key = $1 AND snapshot_status = 'capturing'
            """,
            self.settings.console_key,
            error,
        )
        await self.pool.execute(
            """
            UPDATE unifi_protect_recognitions
            SET snapshot_status = 'failed', snapshot_error = $2
            WHERE console_key = $1 AND snapshot_status = 'capturing'
            """,
            self.settings.console_key,
            error,
        )

    async def reload_policy(self) -> None:
        if self.pool is None:
            raise RuntimeError("collector is not started")
        self.policy = await admin.load_policy(self.pool, self.settings.console_key)

    async def close(self) -> None:
        self.websocket_connected = False
        if self.bollard_service is not None:
            await self.bollard_service.close()
            self.bollard_service = None
        for task in self.snapshot_tasks:
            task.cancel()
        for task in self.recognition_snapshot_tasks:
            task.cancel()
        if self.snapshot_tasks:
            await asyncio.gather(*self.snapshot_tasks, return_exceptions=True)
        if self.recognition_snapshot_tasks:
            await asyncio.gather(*self.recognition_snapshot_tasks, return_exceptions=True)
        self.snapshot_tasks = []
        self.recognition_snapshot_tasks = []
        if self.session is not None:
            await self.session.close()
            self.session = None
        if self.validation_session is not None:
            await self.validation_session.close()
            self.validation_session = None
        self.plate_validator = None
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def fetch_camera_jpeg(
        self,
        camera_id: str,
        high_quality: bool,
    ) -> tuple[bytes, datetime]:
        """Fetch one bounded local snapshot for calibration or image analysis."""
        if self.session is None or self.policy is None:
            raise RuntimeError("Collector is not started")
        encoded_camera_id = quote(camera_id, safe="")
        url = f"{self.settings.nvr_url}{SNAPSHOT_PATH.format(camera_id=encoded_camera_id)}"
        request_started_at = datetime.now(timezone.utc)
        async with self.session.get(
            url,
            params={"highQuality": str(bool(high_quality)).lower()},
            headers={"Accept": "image/jpeg"},
            ssl=self._ssl_context,
        ) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "image/jpeg":
                raise ValueError(
                    f"Protect snapshot returned unsupported content type {content_type or 'unknown'}"
                )
            declared_size = response.content_length
            if declared_size is not None and declared_size > self.policy.snapshot_max_bytes:
                raise ValueError(f"Snapshot exceeds {self.policy.snapshot_max_bytes} byte limit")
            chunks: list[bytes] = []
            received = 0
            async for chunk in response.content.iter_chunked(256 * 1024):
                received += len(chunk)
                if received > self.policy.snapshot_max_bytes:
                    raise ValueError(f"Snapshot exceeds {self.policy.snapshot_max_bytes} byte limit")
                chunks.append(chunk)
        request_finished_at = datetime.now(timezone.utc)
        content = b"".join(chunks)
        if not content.startswith(b"\xff\xd8"):
            raise ValueError("Protect snapshot is not a valid JPEG")
        captured_at = request_started_at + (request_finished_at - request_started_at) / 2
        return content, captured_at
        self.database_ready = False

    async def sync_cameras(self) -> int:
        if self.session is None or self.pool is None:
            raise RuntimeError("collector is not started")
        url = f"{self.settings.nvr_url}{CAMERAS_PATH}"
        async with self.session.get(url, ssl=self._ssl_context) as response:
            response.raise_for_status()
            cameras = await response.json()
        if not isinstance(cameras, list):
            raise ValueError("Protect cameras endpoint did not return a JSON array")

        names: dict[str, str] = {}
        capabilities: dict[str, set[str]] = {}
        for camera in cameras:
            if not isinstance(camera, Mapping):
                continue
            camera_id = scalar_text(camera.get("id"))
            if not camera_id:
                continue
            name = scalar_text(camera.get("name"))
            if name:
                names[camera_id] = name
            smart_types, smart_audio_types = admin.camera_capabilities(camera)
            for detection_type in (*smart_types, *smart_audio_types):
                capabilities.setdefault(detection_type, set()).add(camera_id)
            await self.pool.execute(
                """
                INSERT INTO unifi_protect_cameras (
                    console_key, camera_id, name, model_key, mac, state, synced_at, raw,
                    smart_detect_types, smart_detect_audio_types
                ) VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP, $7::jsonb, $8, $9)
                ON CONFLICT (console_key, camera_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    model_key = EXCLUDED.model_key,
                    mac = EXCLUDED.mac,
                    state = EXCLUDED.state,
                    synced_at = EXCLUDED.synced_at,
                    raw = EXCLUDED.raw,
                    smart_detect_types = EXCLUDED.smart_detect_types,
                    smart_detect_audio_types = EXCLUDED.smart_detect_audio_types
                """,
                self.settings.console_key,
                camera_id,
                name,
                scalar_text(camera.get("modelKey")),
                scalar_text(camera.get("mac")),
                scalar_text(camera.get("state")),
                json.dumps(camera, ensure_ascii=False, separators=(",", ":"), default=str),
                list(smart_types),
                list(smart_audio_types),
            )
        self.camera_names = names
        await admin.sync_detection_capabilities(self.pool, self.settings.console_key, capabilities)
        await self.reload_policy()
        return len(names)

    def storage_decision(self, event: Mapping[str, Any]) -> tuple[bool, str]:
        camera_id = event.get("camera_id")
        event_type = str(event.get("event_type") or "").lower()
        if self.settings.camera_ids and camera_id not in self.settings.camera_ids:
            return False, "environment_camera_filter"
        if self.settings.event_types and event_type not in self.settings.event_types:
            return False, "environment_event_filter"
        if self.policy is not None:
            return admin.evaluate_policy(self.policy, event)
        return True, "stored"

    def should_store(self, event: Mapping[str, Any]) -> bool:
        return self.storage_decision(event)[0]

    async def store_event(self, event: Mapping[str, Any]) -> None:
        if self.pool is None:
            raise RuntimeError("collector is not started")
        now = datetime.now(timezone.utc)
        camera_id = event.get("camera_id")
        snapshot_status = (
            "pending"
            if camera_id and self.policy is not None and self.policy.snapshots_enabled
            else "not_requested"
        )
        await self.pool.execute(
            """
            INSERT INTO unifi_protect_events (
                console_key, source_event_id, message_type, event_type, model_key,
                camera_id, camera_name, start_at, end_at, score, smart_detect_types,
                duration_ms, snapshot_status, first_received_at, last_received_at,
                update_count, raw
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                $12, $13, $14, $14, 1, $15::jsonb
            )
            ON CONFLICT (console_key, source_event_id) DO UPDATE SET
                message_type = EXCLUDED.message_type,
                event_type = COALESCE(EXCLUDED.event_type, unifi_protect_events.event_type),
                model_key = COALESCE(EXCLUDED.model_key, unifi_protect_events.model_key),
                camera_id = COALESCE(EXCLUDED.camera_id, unifi_protect_events.camera_id),
                camera_name = COALESCE(EXCLUDED.camera_name, unifi_protect_events.camera_name),
                start_at = COALESCE(EXCLUDED.start_at, unifi_protect_events.start_at),
                end_at = COALESCE(EXCLUDED.end_at, unifi_protect_events.end_at),
                score = COALESCE(EXCLUDED.score, unifi_protect_events.score),
                smart_detect_types = CASE
                    WHEN cardinality(EXCLUDED.smart_detect_types) > 0 THEN EXCLUDED.smart_detect_types
                    ELSE unifi_protect_events.smart_detect_types
                END,
                duration_ms = COALESCE(EXCLUDED.duration_ms, unifi_protect_events.duration_ms),
                snapshot_status = CASE
                    WHEN unifi_protect_events.snapshot_status = 'not_requested'
                         AND EXCLUDED.snapshot_status = 'pending' THEN 'pending'
                    ELSE unifi_protect_events.snapshot_status
                END,
                last_received_at = EXCLUDED.last_received_at,
                update_count = unifi_protect_events.update_count + 1,
                raw = EXCLUDED.raw
            """,
            self.settings.console_key,
            event["source_event_id"],
            event["message_type"],
            event.get("event_type"),
            event.get("model_key"),
            camera_id,
            self.camera_names.get(str(camera_id)) if camera_id else None,
            event.get("start_at"),
            event.get("end_at"),
            event.get("score"),
            list(event.get("smart_detect_types") or ()),
            event.get("duration_ms"),
            snapshot_status,
            now,
            event["raw_json"],
        )
        self.events_stored += 1
        self.last_event_at = now
        await self.broker.publish(
            {
                "type": "event",
                "data": {
                    "source_event_id": event["source_event_id"],
                    "event_type": event.get("event_type"),
                    "camera_id": camera_id,
                    "camera_name": self.camera_names.get(str(camera_id)) if camera_id else None,
                    "smart_detect_types": list(event.get("smart_detect_types") or ()),
                    "occurred_at": (event.get("start_at") or now).isoformat(),
                    "snapshot_status": snapshot_status,
                },
            }
        )

    async def enqueue_snapshot(self, event: Mapping[str, Any]) -> None:
        if not event.get("camera_id") or self.policy is None or not self.policy.snapshots_enabled:
            return
        try:
            self.snapshot_queue.put_nowait(dict(event))
        except asyncio.QueueFull:
            self.snapshots_failed += 1
            if self.pool is not None:
                await self.pool.execute(
                    """
                    UPDATE unifi_protect_events
                    SET snapshot_status = 'failed', snapshot_error = 'Snapshot queue is full'
                    WHERE console_key = $1 AND source_event_id = $2
                      AND snapshot_status = 'pending'
                    """,
                    self.settings.console_key,
                    event["source_event_id"],
                )

    async def snapshot_worker(self, worker_number: int) -> None:
        while True:
            try:
                event = await self.snapshot_queue.get()
                try:
                    await self.capture_snapshot(event)
                finally:
                    self.snapshot_queue.task_done()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.warning("Snapshot worker %s failed: %s", worker_number, self._safe_error(error))

    async def capture_snapshot(self, event: Mapping[str, Any]) -> None:
        if self.pool is None or self.session is None or self.policy is None:
            return
        camera_id = scalar_text(event.get("camera_id"))
        source_event_id = scalar_text(event.get("source_event_id"))
        if not camera_id or not source_event_id or not self.policy.snapshots_enabled:
            return

        claimed = await self.pool.fetchrow(
            """
            UPDATE unifi_protect_events
            SET snapshot_status = 'capturing',
                snapshot_attempt_count = snapshot_attempt_count + 1,
                snapshot_error = NULL
            WHERE console_key = $1 AND source_event_id = $2
              AND snapshot_status IN ('pending', 'failed')
              AND snapshot_attempt_count < 3
            RETURNING snapshot_attempt_count
            """,
            self.settings.console_key,
            source_event_id,
        )
        if claimed is None:
            return

        captured_at = datetime.now(timezone.utc)
        relative_path = snapshot_relative_path(
            self.settings.console_key,
            camera_id,
            source_event_id,
            captured_at,
        )
        encoded_camera_id = quote(camera_id, safe="")
        url = f"{self.settings.nvr_url}{SNAPSHOT_PATH.format(camera_id=encoded_camera_id)}"
        try:
            async with self.session.get(
                url,
                params={"highQuality": str(self.policy.snapshot_high_quality).lower()},
                headers={"Accept": "image/jpeg"},
                ssl=self._ssl_context,
            ) as response:
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                if content_type != "image/jpeg":
                    raise ValueError(f"Protect snapshot returned unsupported content type {content_type or 'unknown'}")
                declared_size = response.content_length
                if declared_size is not None and declared_size > self.policy.snapshot_max_bytes:
                    raise ValueError(f"Snapshot exceeds {self.policy.snapshot_max_bytes} byte limit")
                chunks: list[bytes] = []
                received = 0
                async for chunk in response.content.iter_chunked(256 * 1024):
                    received += len(chunk)
                    if received > self.policy.snapshot_max_bytes:
                        raise ValueError(f"Snapshot exceeds {self.policy.snapshot_max_bytes} byte limit")
                    chunks.append(chunk)
            image = b"".join(chunks)
            if not image.startswith(b"\xff\xd8"):
                raise ValueError("Protect snapshot is not a valid JPEG")
            await asyncio.to_thread(write_snapshot_atomic, self.settings.snapshot_dir, relative_path, image)
            await self.pool.execute(
                """
                UPDATE unifi_protect_events
                SET snapshot_status = 'stored', snapshot_path = $3,
                    snapshot_content_type = 'image/jpeg', snapshot_size_bytes = $4,
                    snapshot_captured_at = $5, snapshot_error = NULL
                WHERE console_key = $1 AND source_event_id = $2
                """,
                self.settings.console_key,
                source_event_id,
                relative_path.as_posix(),
                len(image),
                captured_at,
            )
            self.snapshots_stored += 1
        except Exception as error:
            safe_error = self._safe_error(error)
            await self.pool.execute(
                """
                UPDATE unifi_protect_events
                SET snapshot_status = 'failed', snapshot_error = $3
                WHERE console_key = $1 AND source_event_id = $2
                """,
                self.settings.console_key,
                source_event_id,
                safe_error,
            )
            self.snapshots_failed += 1
            logger.warning("Could not store snapshot for Protect event %s: %s", source_event_id, safe_error)

    async def enqueue_recognition_snapshots(
        self, recognitions: list[Mapping[str, Any]]
    ) -> None:
        """Queue one camera image for recognitions sharing camera and OCR time."""
        if self.pool is None or self.policy is None or not self.policy.snapshots_enabled:
            return
        grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
        for recognition in recognitions:
            camera_id = scalar_text(recognition.get("camera_id"))
            recognition_id = recognition.get("recognition_id")
            occurred_at = recognition.get("occurred_at")
            if not camera_id or not isinstance(recognition_id, int):
                continue
            target_key = occurred_at.isoformat() if isinstance(occurred_at, datetime) else str(occurred_at or "")
            grouped.setdefault((camera_id, target_key), []).append(recognition)

        for (camera_id, _), rows in grouped.items():
            recognition_ids = [int(row["recognition_id"]) for row in rows]
            target_at = rows[0].get("occurred_at")
            if not isinstance(target_at, datetime):
                target_at = datetime.now(timezone.utc)
            await self.pool.execute(
                """
                UPDATE unifi_protect_recognitions
                SET snapshot_status = 'pending', snapshot_target_at = $3,
                    snapshot_source = 'alarm_webhook_live', snapshot_error = NULL
                WHERE console_key = $1 AND recognition_id = ANY($2::bigint[])
                  AND snapshot_status IN ('not_requested', 'failed')
                """,
                self.settings.console_key,
                recognition_ids,
                target_at,
            )
            item = {
                "recognition_ids": recognition_ids,
                "camera_id": camera_id,
                "target_at": target_at,
            }
            try:
                self.recognition_snapshot_queue.put_nowait(item)
            except asyncio.QueueFull:
                self.recognition_snapshots_failed += len(recognition_ids)
                await self.pool.execute(
                    """
                    UPDATE unifi_protect_recognitions
                    SET snapshot_status = 'failed', snapshot_error = 'Recognition snapshot queue is full'
                    WHERE console_key = $1 AND recognition_id = ANY($2::bigint[])
                    """,
                    self.settings.console_key,
                    recognition_ids,
                )

    async def recognition_snapshot_worker(self, worker_number: int) -> None:
        while True:
            try:
                item = await self.recognition_snapshot_queue.get()
                try:
                    await self.capture_recognition_snapshot(item)
                finally:
                    self.recognition_snapshot_queue.task_done()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.warning(
                    "Recognition snapshot worker %s failed: %s",
                    worker_number,
                    self._safe_error(error),
                )

    async def capture_recognition_snapshot(self, item: Mapping[str, Any]) -> None:
        if self.pool is None or self.session is None or self.policy is None:
            return
        camera_id = scalar_text(item.get("camera_id"))
        recognition_ids = [
            int(value) for value in item.get("recognition_ids", []) if isinstance(value, int)
        ]
        target_at = item.get("target_at")
        if not isinstance(target_at, datetime):
            target_at = datetime.now(timezone.utc)
        if not camera_id or not recognition_ids or not self.policy.snapshots_enabled:
            return

        claimed = await self.pool.fetch(
            """
            UPDATE unifi_protect_recognitions
            SET snapshot_status = 'capturing',
                snapshot_attempt_count = snapshot_attempt_count + 1,
                snapshot_error = NULL
            WHERE console_key = $1 AND recognition_id = ANY($2::bigint[])
              AND snapshot_status IN ('pending', 'failed')
              AND snapshot_attempt_count < 3
            RETURNING recognition_id
            """,
            self.settings.console_key,
            recognition_ids,
        )
        claimed_ids = [int(row["recognition_id"]) for row in claimed]
        if not claimed_ids:
            return

        delay = recognition_capture_delay(target_at)
        if delay:
            await asyncio.sleep(delay)

        encoded_camera_id = quote(camera_id, safe="")
        url = f"{self.settings.nvr_url}{SNAPSHOT_PATH.format(camera_id=encoded_camera_id)}"
        request_started_at = datetime.now(timezone.utc)
        try:
            async with self.session.get(
                url,
                params={"highQuality": "true"},
                headers={"Accept": "image/jpeg"},
                ssl=self._ssl_context,
            ) as response:
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                if content_type != "image/jpeg":
                    raise ValueError(
                        f"Protect recognition snapshot returned unsupported content type {content_type or 'unknown'}"
                    )
                declared_size = response.content_length
                if declared_size is not None and declared_size > self.policy.snapshot_max_bytes:
                    raise ValueError(
                        f"Recognition snapshot exceeds {self.policy.snapshot_max_bytes} byte limit"
                    )
                chunks: list[bytes] = []
                received = 0
                async for chunk in response.content.iter_chunked(256 * 1024):
                    received += len(chunk)
                    if received > self.policy.snapshot_max_bytes:
                        raise ValueError(
                            f"Recognition snapshot exceeds {self.policy.snapshot_max_bytes} byte limit"
                        )
                    chunks.append(chunk)
            request_finished_at = datetime.now(timezone.utc)
            captured_at = request_started_at + (request_finished_at - request_started_at) / 2
            image = b"".join(chunks)
            if not image.startswith(b"\xff\xd8"):
                raise ValueError("Protect recognition snapshot is not a valid JPEG")
            relative_path = recognition_snapshot_relative_path(
                self.settings.console_key,
                camera_id,
                claimed_ids[0],
                captured_at,
            )
            await asyncio.to_thread(
                write_snapshot_atomic,
                self.settings.snapshot_dir,
                relative_path,
                image,
            )
            offset_ms = round((captured_at - target_at).total_seconds() * 1000)
            await self.pool.execute(
                """
                UPDATE unifi_protect_recognitions
                SET snapshot_status = 'stored', snapshot_path = $3,
                    snapshot_content_type = 'image/jpeg', snapshot_size_bytes = $4,
                    snapshot_captured_at = $5, snapshot_target_at = $6,
                    snapshot_time_offset_ms = $7, snapshot_source = 'alarm_webhook_live',
                    snapshot_camera_id = $8, snapshot_error = NULL
                WHERE console_key = $1 AND recognition_id = ANY($2::bigint[])
                """,
                self.settings.console_key,
                claimed_ids,
                relative_path.as_posix(),
                len(image),
                captured_at,
                target_at,
                offset_ms,
                camera_id,
            )
            self.recognition_snapshots_stored += len(claimed_ids)
        except Exception as error:
            safe_error = self._safe_error(error)
            await self.pool.execute(
                """
                UPDATE unifi_protect_recognitions
                SET snapshot_status = 'failed', snapshot_error = $3
                WHERE console_key = $1 AND recognition_id = ANY($2::bigint[])
                """,
                self.settings.console_key,
                claimed_ids,
                safe_error,
            )
            self.recognition_snapshots_failed += len(claimed_ids)
            logger.warning(
                "Could not store recognition snapshot for camera %s: %s",
                camera_id,
                safe_error,
            )

    async def remove_snapshot_files(self, paths: tuple[str, ...]) -> int:
        root = self.settings.snapshot_dir.resolve()

        def remove() -> int:
            deleted = 0
            for value in paths:
                candidate = (root / value).resolve()
                if not candidate.is_relative_to(root):
                    logger.warning("Skipping unsafe snapshot path during retention: %s", value)
                    continue
                if candidate.is_file():
                    candidate.unlink()
                    deleted += 1
            return deleted

        return await asyncio.to_thread(remove)

    async def consume_events(self) -> None:
        if self.session is None:
            raise RuntimeError("collector is not started")
        async with self.session.ws_connect(
            websocket_url(self.settings.nvr_url),
            ssl=self._ssl_context,
            heartbeat=30,
            autoping=True,
        ) as websocket:
            self.websocket_connected = True
            self.last_connected_at = datetime.now(timezone.utc)
            self.last_error = None
            logger.info("Connected to UniFi Protect event WebSocket at %s", self.settings.nvr_url)
            try:
                async for message in websocket:
                    try:
                        if message.type == aiohttp.WSMsgType.TEXT:
                            payload = json.loads(message.data)
                        elif message.type == aiohttp.WSMsgType.BINARY:
                            payload = json.loads(message.data.decode("utf-8"))
                        elif message.type in {
                            aiohttp.WSMsgType.CLOSE,
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.CLOSING,
                        }:
                            break
                        elif message.type == aiohttp.WSMsgType.ERROR:
                            raise websocket.exception() or RuntimeError("Protect WebSocket failed")
                        else:
                            continue
                        event = normalize_event_message(payload)
                    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
                        logger.warning("Ignoring unsupported Protect message: %s", error)
                        continue
                    should_store, _ = self.storage_decision(event)
                    if should_store:
                        await self.store_event(event)
                    else:
                        self.events_ignored += 1
                    if self.pool is not None and self.policy is not None:
                        await admin.register_observation(
                            self.pool,
                            self.settings.console_key,
                            event,
                            stored=should_store,
                            policy=self.policy,
                        )
                    if should_store:
                        await self.enqueue_snapshot(event)
            finally:
                self.websocket_connected = False

    async def run_forever(self) -> None:
        delay = self.settings.reconnect_min_seconds
        while True:
            connected_before = self.last_connected_at
            try:
                camera_count = await self.sync_cameras()
                logger.info("Synced %s UniFi Protect cameras", camera_count)
                await self.consume_events()
                raise ConnectionError("Protect WebSocket closed")
            except asyncio.CancelledError:
                raise
            except Exception as error:
                if self.last_connected_at != connected_before:
                    delay = self.settings.reconnect_min_seconds
                self.websocket_connected = False
                self.last_error = self._safe_error(error)
                logger.warning("UniFi Protect connection failed; retrying: %s", self.last_error)
                await asyncio.sleep(delay + random.uniform(0, min(1.0, delay / 4)))
                delay = min(delay * 2, self.settings.reconnect_max_seconds)

    async def cleanup_forever(self) -> None:
        while True:
            try:
                if self.pool is not None:
                    await self.reload_policy()
                    retention_days = self.policy.retention_days if self.policy else 365
                    retention = await admin.retention_cleanup(
                        self.pool,
                        self.settings.console_key,
                        retention_days,
                    )
                    await self.remove_snapshot_files(retention.snapshot_paths)
                    bollard_retention = (
                        await self.bollard_service.retention_cleanup(retention_days)
                        if self.bollard_service
                        else {"deleted_incidents": 0}
                    )
                    self.last_retention_deleted = retention.deleted_events
                    self.last_retention_recognitions = retention.deleted_recognitions
                    self.last_retention_webhooks = retention.deleted_webhooks
                    self.last_retention_bollard_incidents = int(
                        bollard_retention.get("deleted_incidents", 0)
                    )
                    self.last_retention_at = datetime.now(timezone.utc)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.warning("UniFi Protect retention cleanup failed: %s", self._safe_error(error))
            await asyncio.sleep(6 * 60 * 60)

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.database_ready else "starting",
            "app": protect_ledger_build_summary(),
            "version": protect_ledger_build_summary()["version"],
            "build": protect_ledger_build_summary()["build"],
            "database_ready": self.database_ready,
            "websocket_connected": self.websocket_connected,
            "console_key": self.settings.console_key,
            "camera_count": len(self.camera_names),
            "events_stored_since_start": self.events_stored,
            "events_ignored_since_start": self.events_ignored,
            "snapshots_stored_since_start": self.snapshots_stored,
            "snapshots_failed_since_start": self.snapshots_failed,
            "snapshot_queue_depth": self.snapshot_queue.qsize(),
            "snapshot_queue_capacity": self.snapshot_queue.maxsize,
            "snapshot_workers": len(self.snapshot_tasks),
            "recognition_snapshots_stored_since_start": self.recognition_snapshots_stored,
            "recognition_snapshots_failed_since_start": self.recognition_snapshots_failed,
            "recognition_snapshot_queue_depth": self.recognition_snapshot_queue.qsize(),
            "recognition_snapshot_workers": len(self.recognition_snapshot_tasks),
            "stream_subscribers": self.broker.subscriber_count,
            "started_at": self.started_at.isoformat(),
            "last_connected_at": self.last_connected_at.isoformat() if self.last_connected_at else None,
            "last_event_at": self.last_event_at.isoformat() if self.last_event_at else None,
            "retention_days": self.policy.retention_days if self.policy else None,
            "last_retention_at": self.last_retention_at.isoformat() if self.last_retention_at else None,
            "last_retention_deleted": self.last_retention_deleted,
            "last_retention_recognitions": self.last_retention_recognitions,
            "last_retention_webhooks": self.last_retention_webhooks,
            "last_retention_bollard_incidents": self.last_retention_bollard_incidents,
            "plate_validation_enabled": bool(
                self.plate_validator and self.plate_validator.settings.enabled
            ),
            "plate_validation_running": bool(
                self.plate_validator and self.plate_validator._running
            ),
            "plate_validation_processed_since_start": (
                self.plate_validator.processed_since_start if self.plate_validator else 0
            ),
            "plate_validation_last_success_at": (
                self.plate_validator.last_success_at.isoformat()
                if self.plate_validator and self.plate_validator.last_success_at
                else None
            ),
            "bollard_monitor_running": bool(
                self.bollard_service
                and self.bollard_service.task
                and not self.bollard_service.task.done()
            ),
            "bollard_monitor_last_run_at": (
                self.bollard_service.last_run_at.isoformat()
                if self.bollard_service and self.bollard_service.last_run_at
                else None
            ),
            "bollard_monitor_last_error": (
                self.bollard_service.last_error if self.bollard_service else None
            ),
            "last_error": self.last_error,
        }


collector: Optional[ProtectEventCollector] = None
collector_task: Optional[asyncio.Task[None]] = None
cleanup_task: Optional[asyncio.Task[None]] = None
plate_validation_task: Optional[asyncio.Task[None]] = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global collector, collector_task, cleanup_task, plate_validation_task
    collector = ProtectEventCollector(Settings.from_env())
    await collector.start()
    collector_task = asyncio.create_task(collector.run_forever(), name="unifi-protect-events")
    cleanup_task = asyncio.create_task(collector.cleanup_forever(), name="unifi-protect-retention")
    if collector.plate_validator is not None:
        plate_validation_task = asyncio.create_task(
            collector.plate_validator.run_forever(), name="protect-plate-validation"
        )
    try:
        yield
    finally:
        if collector_task is not None:
            collector_task.cancel()
        if cleanup_task is not None:
            cleanup_task.cancel()
        if plate_validation_task is not None:
            plate_validation_task.cancel()
        await asyncio.gather(
            *(task for task in (collector_task, cleanup_task, plate_validation_task) if task is not None),
            return_exceptions=True,
        )
        await collector.close()


class RuleUpdate(BaseModel):
    store_enabled: bool


class SettingsUpdate(BaseModel):
    default_store_new_event_types: bool
    retention_days: int = Field(ge=1, le=3650)
    catalog_sample_limit_bytes: int = Field(ge=1024, le=1048576)
    snapshots_enabled: bool
    snapshot_high_quality: bool
    snapshot_max_bytes: int = Field(ge=65536, le=52428800)


class BollardRegionCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    bollard_key: str = Field(default="", max_length=120)
    camera_id: str = Field(min_length=1, max_length=160)
    roi: dict[str, float]
    match_threshold: float = Field(default=0.42, ge=0.1, le=0.95)
    movement_tolerance_pixels: int = Field(default=12, ge=2, le=200)


class BollardSettingsUpdate(BaseModel):
    monitoring_enabled: bool
    analysis_interval_seconds: int = Field(ge=5, le=300)
    confirmation_seconds: int = Field(ge=10, le=1800)
    notification_enabled: bool


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
INDEX_FILE = APP_DIR / "templates" / "index.html"

app = FastAPI(title="Protect Ledger", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def active_collector() -> ProtectEventCollector:
    if collector is None or collector.pool is None:
        raise HTTPException(status_code=503, detail="Collector is starting")
    return collector


def active_bollard_service() -> bollards.BollardService:
    current = active_collector()
    if current.bollard_service is None:
        raise HTTPException(status_code=503, detail="Pullertovervåkingen starter")
    return current.bollard_service


@app.get("/", response_class=FileResponse)
@app.get("/events", response_class=FileResponse)
@app.get("/configuration", response_class=FileResponse)
@app.get("/storage", response_class=FileResponse)
@app.get("/recognitions", response_class=FileResponse)
@app.get("/plates", response_class=FileResponse)
@app.get("/bollards", response_class=FileResponse)
@app.get("/integrations", response_class=FileResponse)
@app.get("/builds", response_class=FileResponse)
async def web_app() -> FileResponse:
    return FileResponse(INDEX_FILE)


@app.get("/health")
async def health() -> JSONResponse:
    if collector is None:
        return JSONResponse({"status": "starting"}, status_code=503)
    payload = collector.health()
    return JSONResponse(payload, status_code=200 if collector.database_ready else 503)


@app.get("/ready")
async def ready() -> JSONResponse:
    if collector is None:
        return JSONResponse({"status": "not_ready"}, status_code=503)
    payload = collector.health()
    status_code = 200 if collector.database_ready and collector.websocket_connected else 503
    return JSONResponse(payload, status_code=status_code)


@app.get("/api/overview")
async def api_overview() -> dict[str, Any]:
    current = active_collector()
    payload = await admin.overview(current.pool, current.settings.console_key)
    payload["health"] = current.health()
    return payload


@app.get("/api/builds")
async def api_builds(
    q: str = "",
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    return protect_ledger_build_log_payload(query=q, limit=limit)


@app.get("/api/builds/{build}")
async def api_build_detail(build: str) -> dict[str, Any]:
    row = protect_ledger_build_detail(build)
    if row is None:
        raise HTTPException(status_code=404, detail="Build not found")
    return row


@app.get("/api/bollards")
async def api_bollards() -> dict[str, Any]:
    return await active_bollard_service().status_payload()


@app.get("/api/bollards/cameras/{camera_id}/snapshot")
async def api_bollard_camera_snapshot(
    camera_id: str,
    high_quality: bool = False,
) -> Response:
    current = active_collector()
    service = active_bollard_service()
    cameras = await service.target_cameras()
    if camera_id not in {str(row["camera_id"]) for row in cameras}:
        raise HTTPException(status_code=404, detail="Kameraet er ikke et pullertkamera")
    try:
        content, captured_at = await current.fetch_camera_jpeg(camera_id, high_quality)
    except Exception as error:
        raise HTTPException(status_code=502, detail=current._safe_error(error)) from error
    return Response(
        content=content,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store",
            "X-Captured-At": captured_at.isoformat(),
        },
    )


@app.post("/api/bollards/baselines")
async def api_bollard_capture_all_baselines() -> dict[str, Any]:
    try:
        monitors = await active_bollard_service().capture_all_baselines()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "ok", "camera_monitors": monitors}


@app.post("/api/bollards/cameras/{camera_id}/baseline")
async def api_bollard_capture_camera_baseline(camera_id: str) -> dict[str, Any]:
    try:
        return await active_bollard_service().capture_camera_baseline(camera_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.put("/api/bollards/cameras/{camera_id}/baseline")
async def api_bollard_import_camera_baseline(camera_id: str, request: Request) -> dict[str, Any]:
    content = await request.body()
    if not content or len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Referansebildet mangler eller er for stort")
    captured_text = request.headers.get("x-captured-at", "")
    try:
        captured_at = datetime.fromisoformat(captured_text.replace("Z", "+00:00")) if captured_text else datetime.now(timezone.utc)
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="X-Captured-At har ugyldig tidspunkt") from error
    try:
        return await active_bollard_service().set_camera_baseline(camera_id, content, captured_at)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/bollards/cameras/{camera_id}/{kind}", response_class=FileResponse)
async def api_bollard_comparison_image(camera_id: str, kind: str) -> FileResponse:
    try:
        path = await active_bollard_service().camera_comparison_image_path(camera_id, kind)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.get("/api/bollards/cameras/{camera_id}/{kind}/crop")
async def api_bollard_cropped_comparison_image(camera_id: str, kind: str) -> Response:
    try:
        content, crop = await active_bollard_service().camera_comparison_image(camera_id, kind)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return Response(
        content=content,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store",
            "X-Image-Geometry": "fixed-source-pixel-crop",
            "X-Crop-Rect": f"{crop['x']},{crop['y']},{crop['width']},{crop['height']}",
        },
    )


@app.get("/api/bollards/assets/{asset_key}/{kind}")
async def api_bollard_fixed_asset_image(asset_key: str, kind: str) -> Response:
    try:
        content, crop = await active_bollard_service().fixed_asset_comparison_image(asset_key, kind)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return Response(
        content=content,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store",
            "X-Image-Geometry": "fixed-source-pixel-crop",
            "X-Crop-Rect": f"{crop['x']},{crop['y']},{crop['width']},{crop['height']}",
        },
    )


@app.post("/api/bollards/regions")
async def api_bollard_region_create(body: BollardRegionCreate) -> dict[str, Any]:
    try:
        return await active_bollard_service().create_region(
            display_name=body.display_name,
            bollard_key=body.bollard_key,
            camera_id=body.camera_id,
            roi=body.roi,
            match_threshold=body.match_threshold,
            movement_tolerance_pixels=body.movement_tolerance_pixels,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/bollards/regions/{region_id}/baseline")
async def api_bollard_region_baseline(region_id: int) -> dict[str, Any]:
    try:
        return await active_bollard_service().refresh_baseline(region_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/bollards/regions/{region_id}/baseline", response_class=FileResponse)
async def api_bollard_region_baseline_image(region_id: int) -> FileResponse:
    try:
        path = await active_bollard_service().region_image_path(region_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.delete("/api/bollards/regions/{region_id}", status_code=204)
async def api_bollard_region_delete(region_id: int) -> Response:
    try:
        await active_bollard_service().delete_region(region_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=204)


@app.post("/api/bollards/settings")
async def api_bollard_settings(body: BollardSettingsUpdate) -> dict[str, Any]:
    try:
        return await active_bollard_service().update_settings(
            monitoring_enabled=body.monitoring_enabled,
            analysis_interval_seconds=body.analysis_interval_seconds,
            confirmation_seconds=body.confirmation_seconds,
            notification_enabled=body.notification_enabled,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/bollards/analyze-now")
async def api_bollard_analyze_now() -> dict[str, Any]:
    return await active_bollard_service().run_once()


@app.post("/api/bollards/incidents/{incident_id}/acknowledge")
async def api_bollard_incident_acknowledge(incident_id: int) -> dict[str, Any]:
    try:
        return await active_bollard_service().acknowledge(incident_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get(
    "/api/bollards/incidents/{incident_id}/images/{camera_id}/{kind}",
    response_class=FileResponse,
)
async def api_bollard_incident_image(
    incident_id: int,
    camera_id: str,
    kind: str,
) -> FileResponse:
    try:
        path = await active_bollard_service().incident_image_path(incident_id, camera_id, kind)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.get("/api/catalog")
async def api_catalog() -> dict[str, Any]:
    current = active_collector()
    return await admin.catalog(current.pool, current.settings.console_key)


@app.get("/api/events")
async def api_events(
    event_type: str = "",
    camera_id: str = "",
    detection_type: str = "",
    q: str = "",
    hours: int = Query(default=168, ge=0, le=87600),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    current = active_collector()
    return await admin.events(
        current.pool,
        current.settings.console_key,
        event_type=event_type.strip(),
        camera_id=camera_id.strip(),
        detection_type=detection_type.strip(),
        query=q.strip(),
        hours=hours,
        limit=limit,
        offset=offset,
    )


@app.get("/api/events/{source_event_id}")
async def api_event_detail(source_event_id: str) -> dict[str, Any]:
    current = active_collector()
    row = await admin.event_detail(current.pool, current.settings.console_key, source_event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return row


@app.get("/api/events/{source_event_id}/snapshot", response_class=FileResponse)
async def api_event_snapshot(source_event_id: str) -> FileResponse:
    current = active_collector()
    row = await current.pool.fetchrow(
        """
        SELECT snapshot_status, snapshot_path, snapshot_content_type
        FROM unifi_protect_events
        WHERE console_key = $1 AND source_event_id = $2
        """,
        current.settings.console_key,
        source_event_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if row["snapshot_status"] != "stored" or not row["snapshot_path"]:
        raise HTTPException(status_code=404, detail=f"Snapshot is {row['snapshot_status']}")
    root = current.settings.snapshot_dir.resolve()
    path = (root / str(row["snapshot_path"])).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(status_code=404, detail="Snapshot file not found")
    return FileResponse(
        path,
        media_type=str(row["snapshot_content_type"] or "image/jpeg"),
        headers={"Cache-Control": "private, max-age=86400"},
    )


@app.get("/api/storage")
async def api_storage() -> dict[str, Any]:
    current = active_collector()
    return await admin.storage(current.pool, current.settings.console_key)


@app.get("/api/recognitions")
async def api_recognitions(
    kind: str = "",
    value: str = "",
    camera_id: str = "",
    is_known: Optional[bool] = None,
    limit: int = Query(default=100, ge=1, le=200),
    cursor: str = "",
) -> dict[str, Any]:
    current = active_collector()
    try:
        return await integration.list_recognitions(
            current.pool,
            current.settings.console_key,
            limit=limit,
            cursor=cursor,
            kind=kind.strip(),
            value=value.strip(),
            camera_id=camera_id.strip(),
            is_known=is_known,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/recognition-summary")
async def api_recognition_summary() -> dict[str, Any]:
    current = active_collector()
    return await integration.recognition_summary(current.pool, current.settings.console_key)


def plate_day_window(day_value: str = "") -> tuple[date, datetime, datetime]:
    local_tz = ZoneInfo("Europe/Oslo")
    if day_value:
        try:
            selected = date.fromisoformat(day_value)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="day must be YYYY-MM-DD") from error
    else:
        selected = datetime.now(local_tz).date()
    start = datetime.combine(selected, time.min, tzinfo=local_tz)
    return selected, start, start + timedelta(days=1)


@app.get("/api/license-plates/daily")
async def api_daily_license_plates(day: str = "") -> dict[str, Any]:
    current = active_collector()
    selected, from_at, to_at = plate_day_window(day)
    payload = await integration.daily_license_plates(
        current.pool,
        current.settings.console_key,
        from_at=from_at,
        to_at=to_at,
    )
    payload.update(
        {
            "selected_day": selected.isoformat(),
            "previous_day": (selected - timedelta(days=1)).isoformat(),
            "next_day": (selected + timedelta(days=1)).isoformat(),
            "is_today": selected == datetime.now(ZoneInfo("Europe/Oslo")).date(),
        }
    )
    return payload


async def plate_validation_payload(current: ProtectEventCollector, plate: str) -> dict[str, Any]:
    plate_value = plate_validation.compact_plate(plate)
    row = await current.pool.fetchrow(
        """
        SELECT * FROM unifi_protect_plate_validations
        WHERE console_key = $1 AND plate = $2
        """,
        current.settings.console_key,
        plate_value,
    )
    return {"plate": plate_value, "validation": plate_validation.public_validation(row)}


@app.get("/api/license-plates/validation/status")
async def api_plate_validation_status() -> dict[str, Any]:
    current = active_collector()
    if current.plate_validator is None:
        return {"enabled": False, "totals": {}}
    return await current.plate_validator.status()


@app.get("/api/license-plates/{plate}")
async def api_plate_validation(plate: str) -> dict[str, Any]:
    return await plate_validation_payload(active_collector(), plate)


@app.post("/api/license-plates/{plate}/validate")
async def api_validate_plate(plate: str) -> dict[str, Any]:
    current = active_collector()
    if current.plate_validator is None or not current.plate_validator.settings.enabled:
        raise HTTPException(status_code=503, detail="Plate validation is disabled")
    result = await current.plate_validator.run_due(force_plate=plate)
    return {**result, **await plate_validation_payload(current, plate)}


@app.get("/api/recognitions/{recognition_id}")
async def api_recognition_detail(recognition_id: int) -> dict[str, Any]:
    current = active_collector()
    row = await integration.recognition_detail(
        current.pool, current.settings.console_key, recognition_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Recognition not found")
    return row


@app.get("/api/recognitions/{recognition_id}/snapshot", response_class=FileResponse)
async def api_recognition_snapshot(recognition_id: int) -> FileResponse:
    current = active_collector()
    row = await current.pool.fetchrow(
        """
        SELECT r.snapshot_status AS recognition_status,
               r.snapshot_path AS recognition_path,
               r.snapshot_content_type AS recognition_content_type,
               e.snapshot_status AS event_status,
               e.snapshot_path AS event_path,
               e.snapshot_content_type AS event_content_type
        FROM unifi_protect_recognitions r
        LEFT JOIN unifi_protect_events e
          ON e.console_key = r.console_key AND e.source_event_id = r.source_event_id
        WHERE r.console_key = $1 AND r.recognition_id = $2
        """,
        current.settings.console_key,
        recognition_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Recognition not found")
    if row["recognition_status"] == "stored" and row["recognition_path"]:
        snapshot_path = row["recognition_path"]
        content_type = row["recognition_content_type"]
    elif row["event_status"] == "stored" and row["event_path"]:
        snapshot_path = row["event_path"]
        content_type = row["event_content_type"]
    else:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Recognition snapshot is {row['recognition_status']}; "
                f"event snapshot is {row['event_status'] or 'missing'}"
            ),
        )
    root = current.settings.snapshot_dir.resolve()
    path = (root / str(snapshot_path)).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(status_code=404, detail="Recognition snapshot file not found")
    return FileResponse(
        path,
        media_type=str(content_type or "image/jpeg"),
        headers={"Cache-Control": "private, max-age=86400"},
    )


@app.get("/api/integration-status")
async def api_integration_status() -> dict[str, Any]:
    current = active_collector()
    alarm_manager = await integration.alarm_manager_status(
        current.pool, current.settings.console_key
    )
    validation_status = (
        await current.plate_validator.status() if current.plate_validator else {"enabled": False}
    )
    return {
        "local_only": True,
        "nvr_host": urlparse(current.settings.nvr_url).hostname,
        "read_api_token_configured": bool(current.settings.read_api_token),
        "webhook_token_configured": bool(current.settings.webhook_token),
        "webhook_allowed_ips": sorted(current.settings.webhook_allowed_ips),
        "api_version": "v1",
        "endpoints": {
            "status": "/api/v1/status",
            "build": "/api/v1/build",
            "build_log": "/api/v1/builds",
            "cameras": "/api/v1/cameras",
            "capabilities": "/api/v1/capabilities",
            "stats": "/api/v1/stats",
            "events": "/api/v1/events",
            "recognitions": "/api/v1/recognitions",
            "daily_license_plates": "/api/v1/license-plates/daily",
            "plate_validation": "/api/v1/license-plates/{plate}",
            "bollards": "/api/v1/bollards",
            "stream": "/api/v1/stream",
            "alarm_webhook": "/api/v1/webhooks/unifi-alarm",
        },
        "alarm_manager": alarm_manager,
        "plate_validation": validation_status,
    }


def require_read_api(request: Request, current: ProtectEventCollector) -> None:
    integration.require_token(request, current.settings.read_api_token, purpose="Read API")


@app.get("/api/v1/status")
async def api_v1_status(request: Request) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    return {"api_version": "v1", "local_only": True, **current.health()}


def versioned_bollard_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep image links inside the authenticated API namespace."""
    for monitor in payload.get("camera_monitors", []):
        for key in (
            "baseline_url", "latest_url", "overlay_url",
            "baseline_crop_url", "latest_crop_url", "overlay_crop_url",
            "ai_heatmap_url",
        ):
            if monitor.get(key):
                monitor[key] = str(monitor[key]).replace(
                    "/api/bollards/", "/api/v1/bollards/", 1
                )
    for monitor in payload.get("asset_monitors", []):
        for key in (
            "baseline_url", "latest_url", "overlay_url",
            "baseline_crop_url", "latest_crop_url", "overlay_crop_url",
            "ai_heatmap_url",
        ):
            if monitor.get(key):
                monitor[key] = str(monitor[key]).replace(
                    "/api/bollards/", "/api/v1/bollards/", 1
                )
    for region in payload.get("regions", []):
        if region.get("baseline_url"):
            region["baseline_url"] = str(region["baseline_url"]).replace(
                "/api/bollards/", "/api/v1/bollards/", 1
            )
    for incident in payload.get("incidents", []):
        for evidence in (incident.get("evidence") or {}).values():
            for key in ("before_url", "after_url"):
                if evidence.get(key):
                    evidence[key] = str(evidence[key]).replace(
                        "/api/bollards/", "/api/v1/bollards/", 1
                    )
    return payload


@app.get("/api/v1/bollards")
async def api_v1_bollards(request: Request) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    payload = await active_bollard_service().status_payload()
    return {"api_version": "v1", "local_only": True, **versioned_bollard_payload(payload)}


@app.get("/api/v1/bollards/regions/{region_id}/baseline", response_class=FileResponse)
async def api_v1_bollard_region_baseline_image(
    request: Request,
    region_id: int,
) -> FileResponse:
    current = active_collector()
    require_read_api(request, current)
    return await api_bollard_region_baseline_image(region_id)


@app.get("/api/v1/bollards/cameras/{camera_id}/{kind}", response_class=FileResponse)
async def api_v1_bollard_comparison_image(
    request: Request,
    camera_id: str,
    kind: str,
) -> FileResponse:
    current = active_collector()
    require_read_api(request, current)
    return await api_bollard_comparison_image(camera_id, kind)


@app.get("/api/v1/bollards/cameras/{camera_id}/{kind}/crop")
async def api_v1_bollard_cropped_comparison_image(
    request: Request,
    camera_id: str,
    kind: str,
) -> Response:
    current = active_collector()
    require_read_api(request, current)
    return await api_bollard_cropped_comparison_image(camera_id, kind)


@app.get("/api/v1/bollards/assets/{asset_key}/{kind}")
async def api_v1_bollard_fixed_asset_image(
    request: Request,
    asset_key: str,
    kind: str,
) -> Response:
    current = active_collector()
    require_read_api(request, current)
    return await api_bollard_fixed_asset_image(asset_key, kind)


@app.get(
    "/api/v1/bollards/incidents/{incident_id}/images/{camera_id}/{kind}",
    response_class=FileResponse,
)
async def api_v1_bollard_incident_image(
    request: Request,
    incident_id: int,
    camera_id: str,
    kind: str,
) -> FileResponse:
    current = active_collector()
    require_read_api(request, current)
    return await api_bollard_incident_image(incident_id, camera_id, kind)


@app.get("/api/v1/build")
async def api_v1_build(request: Request) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    return {"api_version": "v1", "local_only": True, **protect_ledger_build_summary()}


@app.get("/api/v1/builds")
async def api_v1_builds(
    request: Request,
    q: str = "",
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    return {
        "api_version": "v1",
        "local_only": True,
        **protect_ledger_build_log_payload(query=q, limit=limit),
    }


@app.get("/api/v1/builds/{build}")
async def api_v1_build_detail(request: Request, build: str) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    row = protect_ledger_build_detail(build)
    if row is None:
        raise HTTPException(status_code=404, detail="Build not found")
    return {"api_version": "v1", "local_only": True, **row}


@app.get("/api/v1/cameras")
async def api_v1_cameras(request: Request) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    rows = await current.pool.fetch(
        """
        SELECT camera_id, name, model_key, mac, state, store_enabled,
               smart_detect_types, smart_detect_audio_types, last_event_at, synced_at
        FROM unifi_protect_cameras WHERE console_key = $1 ORDER BY name, camera_id
        """,
        current.settings.console_key,
    )
    return {"items": [dict(row) for row in rows]}


@app.get("/api/v1/capabilities")
async def api_v1_capabilities(request: Request) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    catalog = await admin.catalog(current.pool, current.settings.console_key)
    return {
        "event_types": catalog["event_types"],
        "detection_types": catalog["detection_types"],
    }


@app.get("/api/v1/stats")
async def api_v1_stats(request: Request) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    overview, recognitions, alarm_manager, validation_status = await asyncio.gather(
        admin.overview(current.pool, current.settings.console_key),
        integration.recognition_summary(current.pool, current.settings.console_key),
        integration.alarm_manager_status(current.pool, current.settings.console_key),
        current.plate_validator.status() if current.plate_validator else asyncio.sleep(0, result={"enabled": False}),
    )
    return {
        "api_version": "v1",
        "local_only": True,
        "health": current.health(),
        "events": overview.get("totals", {}),
        "cameras": overview.get("cameras", {}),
        "catalog": overview.get("catalog", {}),
        "daily": overview.get("daily", []),
        "recognitions": recognitions.get("totals", {}),
        "alarm_manager": alarm_manager,
        "plate_validation": validation_status,
    }


@app.get("/api/v1/events")
async def api_v1_events(
    request: Request,
    event_type: str = "",
    camera_id: str = "",
    detection_type: str = "",
    from_at: Optional[datetime] = Query(default=None, alias="from"),
    to_at: Optional[datetime] = Query(default=None, alias="to"),
    has_snapshot: Optional[bool] = None,
    limit: int = Query(default=100, ge=1, le=500),
    cursor: str = "",
) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    try:
        return await integration.list_events_v1(
            current.pool,
            current.settings.console_key,
            limit=limit,
            cursor=cursor,
            event_type=event_type.strip(),
            camera_id=camera_id.strip(),
            detection_type=detection_type.strip(),
            from_at=from_at,
            to_at=to_at,
            has_snapshot=has_snapshot,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/v1/events/{source_event_id}")
async def api_v1_event_detail(request: Request, source_event_id: str) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    row = await admin.event_detail(current.pool, current.settings.console_key, source_event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    row["snapshot_url"] = (
        f"/api/v1/events/{source_event_id}/snapshot" if row.get("snapshot_status") == "stored" else None
    )
    return row


@app.get("/api/v1/events/{source_event_id}/snapshot", response_class=FileResponse)
async def api_v1_event_snapshot(request: Request, source_event_id: str) -> FileResponse:
    current = active_collector()
    require_read_api(request, current)
    return await api_event_snapshot(source_event_id)


@app.get("/api/v1/recognitions")
async def api_v1_recognitions(
    request: Request,
    kind: str = "",
    value: str = "",
    camera_id: str = "",
    is_known: Optional[bool] = None,
    from_at: Optional[datetime] = Query(default=None, alias="from"),
    to_at: Optional[datetime] = Query(default=None, alias="to"),
    limit: int = Query(default=100, ge=1, le=500),
    cursor: str = "",
) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    try:
        return await integration.list_recognitions(
            current.pool,
            current.settings.console_key,
            limit=limit,
            cursor=cursor,
            kind=kind.strip(),
            value=value.strip(),
            camera_id=camera_id.strip(),
            is_known=is_known,
            from_at=from_at,
            to_at=to_at,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/v1/recognitions/{recognition_id}")
async def api_v1_recognition_detail(request: Request, recognition_id: int) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    row = await integration.recognition_detail(
        current.pool, current.settings.console_key, recognition_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Recognition not found")
    return row


@app.get("/api/v1/recognitions/{recognition_id}/snapshot", response_class=FileResponse)
async def api_v1_recognition_snapshot(request: Request, recognition_id: int) -> FileResponse:
    current = active_collector()
    require_read_api(request, current)
    return await api_recognition_snapshot(recognition_id)


@app.get("/api/v1/license-plates/daily")
async def api_v1_daily_license_plates(
    request: Request,
    from_at: datetime = Query(alias="from"),
    to_at: datetime = Query(alias="to"),
    include_detections: bool = Query(default=True),
    plate: str = Query(default=""),
) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    if to_at <= from_at:
        raise HTTPException(status_code=400, detail="to must be after from")
    if to_at - from_at > timedelta(days=2):
        raise HTTPException(status_code=400, detail="Daily plate window cannot exceed two days")
    return await integration.daily_license_plates(
        current.pool,
        current.settings.console_key,
        from_at=from_at,
        to_at=to_at,
        include_detections=include_detections,
        plate=plate,
    )


@app.get("/api/v1/known-vehicles/report")
async def api_v1_known_vehicle_report(
    request: Request,
    identity: str,
    from_at: datetime = Query(alias="from"),
    to_at: datetime = Query(alias="to"),
    gap_minutes: int = Query(default=60, ge=5, le=180),
    timezone_name: str = Query(default="Europe/Oslo", alias="timezone"),
) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    try:
        return await integration.known_vehicle_report(
            current.pool,
            current.settings.console_key,
            identity=identity,
            from_at=from_at,
            to_at=to_at,
            gap_minutes=gap_minutes,
            timezone_name=timezone_name,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/v1/known-vehicles/stays")
async def api_v1_known_vehicle_stays_report(
    request: Request,
    from_at: datetime = Query(alias="from"),
    to_at: datetime = Query(alias="to"),
    min_duration_minutes: int = Query(default=10, ge=1, le=240),
    timezone_name: str = Query(default="Europe/Oslo", alias="timezone"),
) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    try:
        return await integration.known_vehicle_stays_report(
            current.pool,
            current.settings.console_key,
            from_at=from_at,
            to_at=to_at,
            min_duration_minutes=min_duration_minutes,
            timezone_name=timezone_name,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/v1/registered-vehicles/stays")
async def api_v1_registered_vehicle_stays_report(
    request: Request,
    from_at: datetime = Query(alias="from"),
    to_at: datetime = Query(alias="to"),
    min_duration_minutes: int = Query(default=10, ge=1, le=240),
    timezone_name: str = Query(default="Europe/Oslo", alias="timezone"),
) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    try:
        return await integration.registered_vehicle_stays_report(
            current.pool,
            current.settings.console_key,
            from_at=from_at,
            to_at=to_at,
            min_duration_minutes=min_duration_minutes,
            timezone_name=timezone_name,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/v1/license-plates/validation/status")
async def api_v1_plate_validation_status(request: Request) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    if current.plate_validator is None:
        return {"enabled": False, "totals": {}}
    return await current.plate_validator.status()


@app.get("/api/v1/license-plates/{plate}")
async def api_v1_plate_validation(request: Request, plate: str) -> dict[str, Any]:
    current = active_collector()
    require_read_api(request, current)
    return await plate_validation_payload(current, plate)


@app.post("/api/v1/webhooks/unifi-alarm")
async def api_v1_alarm_webhook(request: Request) -> dict[str, Any]:
    current = active_collector()
    integration.require_webhook(
        request,
        current.settings.webhook_token,
        current.settings.webhook_allowed_ips,
    )
    raw_body = await request.body()
    if len(raw_body) > 1024 * 1024:
        raise HTTPException(status_code=413, detail="Webhook payload exceeds 1 MB")
    try:
        payload = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="Webhook body must be valid JSON") from error
    if not isinstance(payload, Mapping):
        raise HTTPException(status_code=400, detail="Webhook body must be a JSON object")
    result = await integration.store_alarm_webhook(
        current.pool, current.settings.console_key, raw_body, payload
    )
    await current.enqueue_recognition_snapshots(result["recognitions"])
    if current.plate_validator and any(
        recognition.get("kind") == "license_plate" for recognition in result["recognitions"]
    ):
        current.plate_validator.wake()
    for recognition in result["recognitions"]:
        await current.broker.publish({"type": "recognition", "data": recognition})
    return result


@app.get("/api/v1/stream")
async def api_v1_stream(request: Request) -> StreamingResponse:
    current = active_collector()
    require_read_api(request, current)

    async def stream() -> Any:
        yield "retry: 3000\n\n"
        async with current.broker.subscribe() as queue:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20)
                    payload = json.dumps(event["data"], ensure_ascii=False, default=str)
                    yield f"event: {event['type']}\ndata: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.patch("/api/config/{kind}/{key}")
async def api_update_rule(kind: str, key: str, body: RuleUpdate) -> dict[str, Any]:
    current = active_collector()
    try:
        await admin.update_rule(
            current.pool,
            current.settings.console_key,
            kind,
            key,
            body.store_enabled,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Configuration target not found") from error
    await current.reload_policy()
    return {"status": "ok", "kind": kind, "key": key, "store_enabled": body.store_enabled}


@app.patch("/api/config/settings")
async def api_update_settings(body: SettingsUpdate) -> dict[str, Any]:
    current = active_collector()
    try:
        await admin.update_settings(
            current.pool,
            current.settings.console_key,
            default_store_new_event_types=body.default_store_new_event_types,
            retention_days=body.retention_days,
            catalog_sample_limit_bytes=body.catalog_sample_limit_bytes,
            snapshots_enabled=body.snapshots_enabled,
            snapshot_high_quality=body.snapshot_high_quality,
            snapshot_max_bytes=body.snapshot_max_bytes,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    await current.reload_policy()
    return {"status": "ok", **body.model_dump()}


@app.post("/api/maintenance/retention")
async def api_run_retention() -> dict[str, Any]:
    current = active_collector()
    await current.reload_policy()
    retention_days = current.policy.retention_days if current.policy else 365
    retention = await admin.retention_cleanup(current.pool, current.settings.console_key, retention_days)
    deleted_snapshots = await current.remove_snapshot_files(retention.snapshot_paths)
    bollard_retention = (
        await current.bollard_service.retention_cleanup(retention_days)
        if current.bollard_service
        else {"deleted_incidents": 0, "deleted_files": 0}
    )
    current.last_retention_at = datetime.now(timezone.utc)
    current.last_retention_deleted = retention.deleted_events
    current.last_retention_recognitions = retention.deleted_recognitions
    current.last_retention_webhooks = retention.deleted_webhooks
    current.last_retention_bollard_incidents = int(bollard_retention["deleted_incidents"])
    return {
        "status": "ok",
        "deleted": retention.deleted_events,
        "deleted_recognitions": retention.deleted_recognitions,
        "deleted_webhooks": retention.deleted_webhooks,
        "deleted_snapshots": deleted_snapshots,
        "deleted_bollard_incidents": bollard_retention["deleted_incidents"],
        "deleted_bollard_snapshots": bollard_retention["deleted_files"],
        "snapshot_bytes": retention.snapshot_bytes,
        "retention_days": retention_days,
    }
