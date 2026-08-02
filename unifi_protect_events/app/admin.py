from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

import asyncpg


EVENT_REFERENCE: dict[str, tuple[str, str]] = {
    "smartDetectZone": ("AI-detektering", "Objekt registrert i en konfigurert kamerasone."),
    "smartAudioDetect": ("AI-lyd", "Kameraets lydanalyse registrerte en valgt lydtype."),
    "motion": ("Bevegelse", "Vanlig bevegelsesdeteksjon fra kameraet."),
    "ring": ("Ringeklokke", "Trykk på en UniFi-dørklokke."),
}

DETECTION_REFERENCE: dict[str, tuple[str, str, str]] = {
    "person": ("Person", "Objekt", "Kameraet gjenkjenner en person."),
    "vehicle": ("Kjøretøy", "Objekt", "Kameraet gjenkjenner et kjøretøy."),
    "animal": ("Dyr", "Objekt", "Kameraet gjenkjenner et dyr."),
    "face": ("Ansikt", "Objekt", "Kameraet registrerer et ansikt."),
    "licensePlate": ("Registreringsskilt", "Objekt", "Kameraet registrerer et bilskilt."),
    "package": ("Pakke", "Objekt", "Kameraet registrerer en pakke."),
    "alrmSpeak": ("Tale", "Lyd", "Kameraet registrerer menneskelig tale."),
    "alrmBabyCry": ("Babygråt", "Lyd", "Kameraet registrerer babygråt."),
    "alrmBark": ("Hundebjeff", "Lyd", "Kameraet registrerer hundebjeff."),
    "alrmBurglar": ("Innbruddsalarm", "Lyd", "Kameraet registrerer en innbruddsalarm."),
    "alrmCarHorn": ("Bilhorn", "Lyd", "Kameraet registrerer et bilhorn."),
    "alrmCmonx": ("CO-alarm", "Lyd", "Kameraet registrerer en karbonmonoksidalarm."),
    "alrmGlassBreak": ("Glassknusing", "Lyd", "Kameraet registrerer lyden av glass som knuses."),
    "alrmSiren": ("Sirene", "Lyd", "Kameraet registrerer en sirene."),
    "alrmSmoke": ("Røykvarsler", "Lyd", "Kameraet registrerer en røykvarsler."),
}


ADMIN_SCHEMA_STATEMENTS = (
    "ALTER TABLE unifi_protect_cameras ADD COLUMN IF NOT EXISTS store_enabled BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE unifi_protect_cameras ADD COLUMN IF NOT EXISTS smart_detect_types TEXT[] NOT NULL DEFAULT '{}'",
    "ALTER TABLE unifi_protect_cameras ADD COLUMN IF NOT EXISTS smart_detect_audio_types TEXT[] NOT NULL DEFAULT '{}'",
    "ALTER TABLE unifi_protect_cameras ADD COLUMN IF NOT EXISTS observed_event_count BIGINT NOT NULL DEFAULT 0",
    "ALTER TABLE unifi_protect_cameras ADD COLUMN IF NOT EXISTS last_event_at TIMESTAMPTZ",
    "ALTER TABLE unifi_protect_cameras ADD COLUMN IF NOT EXISTS config_updated_at TIMESTAMPTZ",
    "ALTER TABLE unifi_protect_events ADD COLUMN IF NOT EXISTS smart_detect_types TEXT[] NOT NULL DEFAULT '{}'",
    "ALTER TABLE unifi_protect_events ADD COLUMN IF NOT EXISTS duration_ms BIGINT",
    "ALTER TABLE unifi_protect_events ADD COLUMN IF NOT EXISTS snapshot_status VARCHAR NOT NULL DEFAULT 'not_requested'",
    "ALTER TABLE unifi_protect_events ADD COLUMN IF NOT EXISTS snapshot_path TEXT",
    "ALTER TABLE unifi_protect_events ADD COLUMN IF NOT EXISTS snapshot_content_type VARCHAR",
    "ALTER TABLE unifi_protect_events ADD COLUMN IF NOT EXISTS snapshot_size_bytes BIGINT",
    "ALTER TABLE unifi_protect_events ADD COLUMN IF NOT EXISTS snapshot_captured_at TIMESTAMPTZ",
    "ALTER TABLE unifi_protect_events ADD COLUMN IF NOT EXISTS snapshot_error TEXT",
    "ALTER TABLE unifi_protect_events ADD COLUMN IF NOT EXISTS snapshot_attempt_count INTEGER NOT NULL DEFAULT 0",
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_settings (
        console_key VARCHAR PRIMARY KEY,
        default_store_new_event_types BOOLEAN NOT NULL DEFAULT TRUE,
        retention_days INTEGER NOT NULL DEFAULT 365 CHECK (retention_days BETWEEN 1 AND 3650),
        catalog_sample_limit_bytes INTEGER NOT NULL DEFAULT 65536
            CHECK (catalog_sample_limit_bytes BETWEEN 1024 AND 1048576),
        snapshots_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        snapshot_high_quality BOOLEAN NOT NULL DEFAULT FALSE,
        snapshot_max_bytes INTEGER NOT NULL DEFAULT 12582912
            CHECK (snapshot_max_bytes BETWEEN 65536 AND 52428800),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "ALTER TABLE unifi_protect_settings ADD COLUMN IF NOT EXISTS snapshots_enabled BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE unifi_protect_settings ADD COLUMN IF NOT EXISTS snapshot_high_quality BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE unifi_protect_settings ADD COLUMN IF NOT EXISTS snapshot_max_bytes INTEGER NOT NULL DEFAULT 12582912",
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_event_type_config (
        console_key VARCHAR NOT NULL,
        event_type VARCHAR NOT NULL,
        category VARCHAR NOT NULL DEFAULT 'Annet',
        description TEXT,
        store_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        is_observed BOOLEAN NOT NULL DEFAULT FALSE,
        observed_count BIGINT NOT NULL DEFAULT 0,
        stored_count BIGINT NOT NULL DEFAULT 0,
        ignored_count BIGINT NOT NULL DEFAULT 0,
        first_seen_at TIMESTAMPTZ,
        last_seen_at TIMESTAMPTZ,
        last_sample JSONB,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (console_key, event_type)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_detection_type_config (
        console_key VARCHAR NOT NULL,
        detection_type VARCHAR NOT NULL,
        display_name VARCHAR NOT NULL,
        category VARCHAR NOT NULL DEFAULT 'Annet',
        description TEXT,
        store_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        supported_camera_count INTEGER NOT NULL DEFAULT 0,
        is_observed BOOLEAN NOT NULL DEFAULT FALSE,
        observed_count BIGINT NOT NULL DEFAULT 0,
        first_seen_at TIMESTAMPTZ,
        last_seen_at TIMESTAMPTZ,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (console_key, detection_type)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_config_history (
        id BIGSERIAL PRIMARY KEY,
        console_key VARCHAR NOT NULL,
        target_kind VARCHAR NOT NULL,
        target_key VARCHAR NOT NULL,
        old_value JSONB,
        new_value JSONB NOT NULL,
        changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_detection_types ON unifi_protect_events USING GIN (smart_detect_types)",
    "CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_received ON unifi_protect_events (last_received_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_unifi_protect_events_snapshot_status ON unifi_protect_events (console_key, snapshot_status)",
    "CREATE INDEX IF NOT EXISTS ix_unifi_protect_config_history_changed ON unifi_protect_config_history (console_key, changed_at DESC)",
)


def _scalar_list(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return [str(item).strip() for item in values if item is not None and str(item).strip()]


def extract_detection_types(item: Mapping[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    values.extend(_scalar_list(item.get("smartDetectTypes")))
    values.extend(_scalar_list(item.get("smartDetectType")))
    metadata = item.get("metadata")
    if isinstance(metadata, Mapping):
        values.extend(_scalar_list(metadata.get("smartDetectTypes")))
        values.extend(_scalar_list(metadata.get("smartDetectType")))
    return tuple(dict.fromkeys(values))


def camera_capabilities(camera: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    feature_flags = camera.get("featureFlags") if isinstance(camera.get("featureFlags"), Mapping) else {}
    settings = camera.get("smartDetectSettings") if isinstance(camera.get("smartDetectSettings"), Mapping) else {}
    object_types = _scalar_list(feature_flags.get("smartDetectTypes")) + _scalar_list(settings.get("objectTypes"))
    audio_types = _scalar_list(feature_flags.get("smartDetectAudioTypes")) + _scalar_list(settings.get("audioTypes"))
    return tuple(dict.fromkeys(object_types)), tuple(dict.fromkeys(audio_types))


def event_reference(event_type: str) -> tuple[str, str]:
    return EVENT_REFERENCE.get(event_type, ("Oppdaget av UniFi", "Hendelsestype oppdaget automatisk fra Protect-strømmen."))


def detection_reference(detection_type: str) -> tuple[str, str, str]:
    if detection_type in DETECTION_REFERENCE:
        return DETECTION_REFERENCE[detection_type]
    display = detection_type.removeprefix("alrm") or detection_type
    category = "Lyd" if detection_type.startswith("alrm") else "Objekt"
    return display, category, "Mulighet rapportert av et av kameraene eller observert i hendelsesstrømmen."


@dataclass(frozen=True)
class PolicyCache:
    default_store_new_event_types: bool
    retention_days: int
    catalog_sample_limit_bytes: int
    snapshots_enabled: bool
    snapshot_high_quality: bool
    snapshot_max_bytes: int
    cameras: dict[str, bool]
    event_types: dict[str, bool]
    detection_types: dict[str, bool]


async def initialize(pool: asyncpg.Pool, console_key: str) -> None:
    for statement in ADMIN_SCHEMA_STATEMENTS:
        await pool.execute(statement)
    await pool.execute(
        """
        INSERT INTO unifi_protect_settings (console_key)
        VALUES ($1)
        ON CONFLICT (console_key) DO NOTHING
        """,
        console_key,
    )
    for event_type, (category, description) in EVENT_REFERENCE.items():
        await pool.execute(
            """
            INSERT INTO unifi_protect_event_type_config (
                console_key, event_type, category, description, store_enabled
            ) VALUES ($1, $2, $3, $4, TRUE)
            ON CONFLICT (console_key, event_type) DO UPDATE SET
                category = EXCLUDED.category,
                description = EXCLUDED.description
            """,
            console_key,
            event_type,
            category,
            description,
        )


async def load_policy(pool: asyncpg.Pool, console_key: str) -> PolicyCache:
    settings = await pool.fetchrow(
        "SELECT * FROM unifi_protect_settings WHERE console_key = $1",
        console_key,
    )
    cameras = await pool.fetch(
        "SELECT camera_id, store_enabled FROM unifi_protect_cameras WHERE console_key = $1",
        console_key,
    )
    event_types = await pool.fetch(
        "SELECT event_type, store_enabled FROM unifi_protect_event_type_config WHERE console_key = $1",
        console_key,
    )
    detection_types = await pool.fetch(
        "SELECT detection_type, store_enabled FROM unifi_protect_detection_type_config WHERE console_key = $1",
        console_key,
    )
    return PolicyCache(
        default_store_new_event_types=bool(settings["default_store_new_event_types"]) if settings else True,
        retention_days=int(settings["retention_days"]) if settings else 365,
        catalog_sample_limit_bytes=int(settings["catalog_sample_limit_bytes"]) if settings else 65536,
        snapshots_enabled=bool(settings["snapshots_enabled"]) if settings else True,
        snapshot_high_quality=bool(settings["snapshot_high_quality"]) if settings else False,
        snapshot_max_bytes=int(settings["snapshot_max_bytes"]) if settings else 12582912,
        cameras={str(row["camera_id"]): bool(row["store_enabled"]) for row in cameras},
        event_types={str(row["event_type"]): bool(row["store_enabled"]) for row in event_types},
        detection_types={str(row["detection_type"]): bool(row["store_enabled"]) for row in detection_types},
    )


def evaluate_policy(policy: PolicyCache, event: Mapping[str, Any]) -> tuple[bool, str]:
    camera_id = str(event.get("camera_id") or "")
    event_type = str(event.get("event_type") or "unknown")
    detection_types = tuple(str(value) for value in event.get("smart_detect_types") or ())
    if camera_id and not policy.cameras.get(camera_id, True):
        return False, "camera_disabled"
    if not policy.event_types.get(event_type, policy.default_store_new_event_types):
        return False, "event_type_disabled"
    if detection_types and not any(policy.detection_types.get(value, True) for value in detection_types):
        return False, "detection_types_disabled"
    return True, "stored"


async def sync_detection_capabilities(
    pool: asyncpg.Pool,
    console_key: str,
    capabilities: Mapping[str, set[str]],
) -> None:
    await pool.execute(
        "UPDATE unifi_protect_detection_type_config SET supported_camera_count = 0 WHERE console_key = $1",
        console_key,
    )
    for detection_type, camera_ids in capabilities.items():
        display_name, category, description = detection_reference(detection_type)
        await pool.execute(
            """
            INSERT INTO unifi_protect_detection_type_config (
                console_key, detection_type, display_name, category, description,
                store_enabled, supported_camera_count
            ) VALUES ($1, $2, $3, $4, $5, TRUE, $6)
            ON CONFLICT (console_key, detection_type) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                category = EXCLUDED.category,
                description = EXCLUDED.description,
                supported_camera_count = EXCLUDED.supported_camera_count,
                updated_at = CURRENT_TIMESTAMP
            """,
            console_key,
            detection_type,
            display_name,
            category,
            description,
            len(camera_ids),
        )


def _catalog_sample(event: Mapping[str, Any], byte_limit: int) -> str:
    raw_json = str(event.get("raw_json") or "{}")
    size = len(raw_json.encode("utf-8"))
    if size <= byte_limit:
        return raw_json
    return json.dumps(
        {
            "truncated": True,
            "originalBytes": size,
            "eventType": event.get("event_type"),
            "smartDetectTypes": list(event.get("smart_detect_types") or ()),
        },
        separators=(",", ":"),
    )


async def register_observation(
    pool: asyncpg.Pool,
    console_key: str,
    event: Mapping[str, Any],
    *,
    stored: bool,
    policy: PolicyCache,
) -> None:
    now = datetime.now(timezone.utc)
    event_type = str(event.get("event_type") or "unknown")
    category, description = event_reference(event_type)
    sample = _catalog_sample(event, policy.catalog_sample_limit_bytes)
    await pool.execute(
        """
        INSERT INTO unifi_protect_event_type_config (
            console_key, event_type, category, description, store_enabled,
            is_observed, observed_count, stored_count, ignored_count,
            first_seen_at, last_seen_at, last_sample, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, TRUE, 1, $6, $7, $8, $8, $9::jsonb, $8
        )
        ON CONFLICT (console_key, event_type) DO UPDATE SET
            is_observed = TRUE,
            observed_count = unifi_protect_event_type_config.observed_count + 1,
            stored_count = unifi_protect_event_type_config.stored_count + $6,
            ignored_count = unifi_protect_event_type_config.ignored_count + $7,
            first_seen_at = COALESCE(unifi_protect_event_type_config.first_seen_at, EXCLUDED.first_seen_at),
            last_seen_at = EXCLUDED.last_seen_at,
            last_sample = EXCLUDED.last_sample,
            updated_at = EXCLUDED.updated_at
        """,
        console_key,
        event_type,
        category,
        description,
        policy.event_types.get(event_type, policy.default_store_new_event_types),
        1 if stored else 0,
        0 if stored else 1,
        now,
        sample,
    )
    for detection_type in event.get("smart_detect_types") or ():
        display_name, detection_category, detection_description = detection_reference(str(detection_type))
        await pool.execute(
            """
            INSERT INTO unifi_protect_detection_type_config (
                console_key, detection_type, display_name, category, description,
                store_enabled, is_observed, observed_count, first_seen_at, last_seen_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, TRUE, TRUE, 1, $6, $6, $6)
            ON CONFLICT (console_key, detection_type) DO UPDATE SET
                is_observed = TRUE,
                observed_count = unifi_protect_detection_type_config.observed_count + 1,
                first_seen_at = COALESCE(unifi_protect_detection_type_config.first_seen_at, EXCLUDED.first_seen_at),
                last_seen_at = EXCLUDED.last_seen_at,
                updated_at = EXCLUDED.updated_at
            """,
            console_key,
            str(detection_type),
            display_name,
            detection_category,
            detection_description,
            now,
        )
    camera_id = event.get("camera_id")
    if camera_id:
        await pool.execute(
            """
            UPDATE unifi_protect_cameras
            SET observed_event_count = observed_event_count + 1,
                last_event_at = $3
            WHERE console_key = $1 AND camera_id = $2
            """,
            console_key,
            str(camera_id),
            now,
        )


@dataclass(frozen=True)
class RetentionResult:
    deleted_events: int
    deleted_recognitions: int
    deleted_webhooks: int
    snapshot_paths: tuple[str, ...]
    snapshot_bytes: int


async def retention_cleanup(pool: asyncpg.Pool, console_key: str, retention_days: int) -> RetentionResult:
    async with pool.acquire() as connection:
        async with connection.transaction():
            recognition_rows = await connection.fetch(
                """
                DELETE FROM unifi_protect_recognitions
                WHERE console_key = $1
                  AND occurred_at < CURRENT_TIMESTAMP - make_interval(days => $2)
                RETURNING snapshot_path, snapshot_size_bytes
                """,
                console_key,
                retention_days,
            )
            deleted_webhooks = await connection.fetchval(
                """
                WITH deleted AS (
                    DELETE FROM unifi_protect_alarm_webhooks
                    WHERE console_key = $1
                      AND COALESCE(occurred_at, received_at)
                          < CURRENT_TIMESTAMP - make_interval(days => $2)
                    RETURNING 1
                )
                SELECT count(*) FROM deleted
                """,
                console_key,
                retention_days,
            )
            rows = await connection.fetch(
                """
                DELETE FROM unifi_protect_events
                WHERE console_key = $1
                  AND COALESCE(end_at, start_at, last_received_at)
                      < CURRENT_TIMESTAMP - make_interval(days => $2)
                RETURNING snapshot_path, snapshot_size_bytes
                """,
                console_key,
                retention_days,
            )
    snapshot_rows = [*recognition_rows, *rows]
    snapshot_sizes: dict[str, int] = {}
    for row in snapshot_rows:
        if row["snapshot_path"]:
            path = str(row["snapshot_path"])
            snapshot_sizes[path] = max(snapshot_sizes.get(path, 0), int(row["snapshot_size_bytes"] or 0))
    return RetentionResult(
        deleted_events=len(rows),
        deleted_recognitions=len(recognition_rows),
        deleted_webhooks=int(deleted_webhooks or 0),
        snapshot_paths=tuple(snapshot_sizes),
        snapshot_bytes=sum(snapshot_sizes.values()),
    )


def _records(rows: list[asyncpg.Record]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


async def overview(pool: asyncpg.Pool, console_key: str) -> dict[str, Any]:
    totals = await pool.fetchrow(
        """
        SELECT
            count(*) AS event_count,
            count(*) FILTER (WHERE last_received_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours') AS events_24h,
            count(*) FILTER (WHERE last_received_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour') AS events_1h,
            count(*) FILTER (WHERE snapshot_status = 'stored') AS snapshot_count,
            count(*) FILTER (WHERE snapshot_status = 'failed') AS snapshot_failures,
            COALESCE(sum(snapshot_size_bytes), 0) AS snapshot_bytes,
            max(last_received_at) AS last_event_at
        FROM unifi_protect_events
        WHERE console_key = $1
        """,
        console_key,
    )
    camera_totals = await pool.fetchrow(
        """
        SELECT
            count(*) AS camera_count,
            count(*) FILTER (WHERE state = 'CONNECTED') AS connected_cameras,
            count(*) FILTER (WHERE store_enabled) AS enabled_cameras
        FROM unifi_protect_cameras
        WHERE console_key = $1
        """,
        console_key,
    )
    type_totals = await pool.fetchrow(
        """
        SELECT
            COALESCE(sum(observed_count), 0) AS observed_messages,
            COALESCE(sum(ignored_count), 0) AS ignored_messages,
            count(*) FILTER (WHERE is_observed) AS observed_types,
            count(*) AS catalog_types
        FROM unifi_protect_event_type_config
        WHERE console_key = $1
        """,
        console_key,
    )
    recent = await pool.fetch(
        """
        SELECT source_event_id, event_type, camera_id, camera_name, smart_detect_types,
               start_at, end_at, duration_ms, last_received_at, update_count,
               snapshot_status, snapshot_size_bytes
        FROM unifi_protect_events
        WHERE console_key = $1
        ORDER BY COALESCE(start_at, last_received_at) DESC
        LIMIT 12
        """,
        console_key,
    )
    type_rows = await pool.fetch(
        """
        SELECT event_type, category, store_enabled, is_observed,
               observed_count, stored_count, ignored_count, last_seen_at
        FROM unifi_protect_event_type_config
        WHERE console_key = $1
        ORDER BY observed_count DESC, event_type
        """,
        console_key,
    )
    daily = await pool.fetch(
        """
        SELECT date_trunc('day', COALESCE(start_at, last_received_at))::date AS day, count(*) AS count
        FROM unifi_protect_events
        WHERE console_key = $1
          AND COALESCE(start_at, last_received_at) >= CURRENT_DATE - INTERVAL '13 days'
        GROUP BY 1
        ORDER BY 1
        """,
        console_key,
    )
    return {
        "totals": dict(totals) if totals else {},
        "cameras": dict(camera_totals) if camera_totals else {},
        "catalog": dict(type_totals) if type_totals else {},
        "recent": _records(recent),
        "event_types": _records(type_rows),
        "daily": _records(daily),
    }


async def catalog(pool: asyncpg.Pool, console_key: str) -> dict[str, Any]:
    settings = await pool.fetchrow(
        "SELECT * FROM unifi_protect_settings WHERE console_key = $1",
        console_key,
    )
    event_types = await pool.fetch(
        """
        SELECT * FROM unifi_protect_event_type_config
        WHERE console_key = $1
        ORDER BY is_observed DESC, category, event_type
        """,
        console_key,
    )
    detection_types = await pool.fetch(
        """
        SELECT * FROM unifi_protect_detection_type_config
        WHERE console_key = $1
        ORDER BY is_observed DESC, category, display_name
        """,
        console_key,
    )
    cameras = await pool.fetch(
        """
        SELECT console_key, camera_id, name, model_key, mac, state, store_enabled,
               smart_detect_types, smart_detect_audio_types, observed_event_count,
               last_event_at, synced_at, config_updated_at
        FROM unifi_protect_cameras
        WHERE console_key = $1
        ORDER BY name, camera_id
        """,
        console_key,
    )
    return {
        "settings": dict(settings) if settings else {},
        "event_types": _records(event_types),
        "detection_types": _records(detection_types),
        "cameras": _records(cameras),
    }


async def events(
    pool: asyncpg.Pool,
    console_key: str,
    *,
    event_type: str = "",
    camera_id: str = "",
    detection_type: str = "",
    query: str = "",
    hours: int = 168,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    arguments: list[Any] = [console_key]
    conditions = ["console_key = $1"]

    def add_condition(sql: str, value: Any) -> None:
        arguments.append(value)
        conditions.append(sql.replace("?", f"${len(arguments)}"))

    if event_type:
        add_condition("event_type = ?", event_type)
    if camera_id:
        add_condition("camera_id = ?", camera_id)
    if detection_type:
        add_condition("? = ANY(smart_detect_types)", detection_type)
    if query:
        add_condition("(event_type ILIKE '%' || ? || '%' OR COALESCE(camera_name, '') ILIKE '%' || ? || '%')", query)
    if hours > 0:
        add_condition("COALESCE(start_at, last_received_at) >= CURRENT_TIMESTAMP - make_interval(hours => ?)", hours)

    where = " AND ".join(conditions)
    count = await pool.fetchval(f"SELECT count(*) FROM unifi_protect_events WHERE {where}", *arguments)
    arguments.extend([limit, offset])
    rows = await pool.fetch(
        f"""
        SELECT source_event_id, message_type, event_type, model_key, camera_id, camera_name,
               smart_detect_types, start_at, end_at, duration_ms, score,
               first_received_at, last_received_at, update_count,
               snapshot_status, snapshot_size_bytes, snapshot_captured_at
        FROM unifi_protect_events
        WHERE {where}
        ORDER BY COALESCE(start_at, last_received_at) DESC
        LIMIT ${len(arguments) - 1} OFFSET ${len(arguments)}
        """,
        *arguments,
    )
    return {"total": int(count or 0), "limit": limit, "offset": offset, "rows": _records(rows)}


async def event_detail(pool: asyncpg.Pool, console_key: str, source_event_id: str) -> Optional[dict[str, Any]]:
    row = await pool.fetchrow(
        "SELECT * FROM unifi_protect_events WHERE console_key = $1 AND source_event_id = $2",
        console_key,
        source_event_id,
    )
    return dict(row) if row else None


async def storage(pool: asyncpg.Pool, console_key: str) -> dict[str, Any]:
    sizes = await pool.fetchrow(
        """
        SELECT
            pg_total_relation_size('unifi_protect_events') AS events_total_bytes,
            pg_relation_size('unifi_protect_events') AS events_table_bytes,
            pg_indexes_size('unifi_protect_events') AS events_index_bytes,
            pg_total_relation_size('unifi_protect_recognitions') AS recognitions_total_bytes,
            pg_indexes_size('unifi_protect_recognitions') AS recognitions_index_bytes,
            pg_total_relation_size('unifi_protect_alarm_webhooks') AS webhooks_total_bytes,
            pg_indexes_size('unifi_protect_alarm_webhooks') AS webhooks_index_bytes,
            (pg_total_relation_size('unifi_protect_events')
             + pg_total_relation_size('unifi_protect_recognitions')
             + pg_total_relation_size('unifi_protect_alarm_webhooks')) AS ledger_total_bytes,
            (pg_indexes_size('unifi_protect_events')
             + pg_indexes_size('unifi_protect_recognitions')
             + pg_indexes_size('unifi_protect_alarm_webhooks')) AS ledger_index_bytes,
            pg_total_relation_size('unifi_protect_cameras') AS cameras_total_bytes,
            (SELECT count(*) FROM unifi_protect_events
             WHERE console_key = $1) AS event_count,
            (SELECT count(*) FROM unifi_protect_recognitions
             WHERE console_key = $1) AS recognition_count,
            (SELECT count(*) FROM unifi_protect_alarm_webhooks
             WHERE console_key = $1) AS webhook_count,
            (SELECT count(*) FROM unifi_protect_events
             WHERE console_key = $1 AND snapshot_status = 'stored')
             + (SELECT count(DISTINCT snapshot_path) FROM unifi_protect_recognitions
                WHERE console_key = $1 AND snapshot_status = 'stored') AS snapshot_count,
            (SELECT count(*) FROM unifi_protect_events
             WHERE console_key = $1 AND snapshot_status = 'failed')
             + (SELECT count(*) FROM unifi_protect_recognitions
                WHERE console_key = $1 AND snapshot_status = 'failed') AS snapshot_failures,
            (SELECT COALESCE(sum(snapshot_size_bytes), 0) FROM unifi_protect_events
             WHERE console_key = $1)
             + (SELECT COALESCE(sum(snapshot_size_bytes), 0)
                FROM (
                    SELECT snapshot_path, max(snapshot_size_bytes) AS snapshot_size_bytes
                    FROM unifi_protect_recognitions
                    WHERE console_key = $1 AND snapshot_path IS NOT NULL
                    GROUP BY snapshot_path
                ) recognition_snapshot_files) AS snapshot_bytes
        """
        ,
        console_key,
    )
    distribution = await pool.fetch(
        """
        SELECT event_type, count(*) AS event_count,
               COALESCE(sum(pg_column_size(raw)), 0) AS raw_bytes,
               min(COALESCE(start_at, last_received_at)) AS oldest_at,
               max(COALESCE(end_at, start_at, last_received_at)) AS newest_at
        FROM unifi_protect_events
        WHERE console_key = $1
        GROUP BY event_type
        ORDER BY event_count DESC
        """,
        console_key,
    )
    cameras = await pool.fetch(
        """
        SELECT COALESCE(camera_name, camera_id, 'Ukjent') AS camera_name,
               count(*) AS event_count,
               COALESCE(sum(pg_column_size(raw)), 0) AS raw_bytes
        FROM unifi_protect_events
        WHERE console_key = $1
        GROUP BY 1
        ORDER BY event_count DESC
        """,
        console_key,
    )
    history = await pool.fetch(
        """
        SELECT target_kind, target_key, old_value, new_value, changed_at
        FROM unifi_protect_config_history
        WHERE console_key = $1
        ORDER BY changed_at DESC
        LIMIT 20
        """,
        console_key,
    )
    settings = await pool.fetchrow(
        "SELECT * FROM unifi_protect_settings WHERE console_key = $1",
        console_key,
    )
    return {
        "sizes": dict(sizes) if sizes else {},
        "distribution": _records(distribution),
        "cameras": _records(cameras),
        "history": _records(history),
        "settings": dict(settings) if settings else {},
    }


async def update_rule(
    pool: asyncpg.Pool,
    console_key: str,
    kind: str,
    key: str,
    store_enabled: bool,
) -> None:
    targets = {
        "event_type": ("unifi_protect_event_type_config", "event_type", "updated_at"),
        "detection_type": ("unifi_protect_detection_type_config", "detection_type", "updated_at"),
        "camera": ("unifi_protect_cameras", "camera_id", "config_updated_at"),
    }
    if kind not in targets:
        raise ValueError("Unsupported rule kind")
    table, key_column, timestamp_column = targets[kind]
    async with pool.acquire() as connection:
        async with connection.transaction():
            old_value = await connection.fetchval(
                f"SELECT store_enabled FROM {table} WHERE console_key = $1 AND {key_column} = $2",
                console_key,
                key,
            )
            result = await connection.execute(
                f"UPDATE {table} SET store_enabled = $3, {timestamp_column} = CURRENT_TIMESTAMP WHERE console_key = $1 AND {key_column} = $2",
                console_key,
                key,
                store_enabled,
            )
            if result.endswith(" 0"):
                raise KeyError(key)
            await connection.execute(
                """
                INSERT INTO unifi_protect_config_history (
                    console_key, target_kind, target_key, old_value, new_value
                ) VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
                """,
                console_key,
                kind,
                key,
                json.dumps({"store_enabled": old_value}),
                json.dumps({"store_enabled": store_enabled}),
            )


async def update_settings(
    pool: asyncpg.Pool,
    console_key: str,
    *,
    default_store_new_event_types: bool,
    retention_days: int,
    catalog_sample_limit_bytes: int,
    snapshots_enabled: bool,
    snapshot_high_quality: bool,
    snapshot_max_bytes: int,
) -> None:
    if not 1 <= retention_days <= 3650:
        raise ValueError("retention_days must be between 1 and 3650")
    if not 1024 <= catalog_sample_limit_bytes <= 1048576:
        raise ValueError("catalog_sample_limit_bytes is outside the allowed range")
    if not 65536 <= snapshot_max_bytes <= 52428800:
        raise ValueError("snapshot_max_bytes is outside the allowed range")
    async with pool.acquire() as connection:
        async with connection.transaction():
            old = await connection.fetchrow(
                "SELECT * FROM unifi_protect_settings WHERE console_key = $1",
                console_key,
            )
            new_value = {
                "default_store_new_event_types": default_store_new_event_types,
                "retention_days": retention_days,
                "catalog_sample_limit_bytes": catalog_sample_limit_bytes,
                "snapshots_enabled": snapshots_enabled,
                "snapshot_high_quality": snapshot_high_quality,
                "snapshot_max_bytes": snapshot_max_bytes,
            }
            await connection.execute(
                """
                UPDATE unifi_protect_settings
                SET default_store_new_event_types = $2,
                    retention_days = $3,
                    catalog_sample_limit_bytes = $4,
                    snapshots_enabled = $5,
                    snapshot_high_quality = $6,
                    snapshot_max_bytes = $7,
                    updated_at = CURRENT_TIMESTAMP
                WHERE console_key = $1
                """,
                console_key,
                default_store_new_event_types,
                retention_days,
                catalog_sample_limit_bytes,
                snapshots_enabled,
                snapshot_high_quality,
                snapshot_max_bytes,
            )
            await connection.execute(
                """
                INSERT INTO unifi_protect_config_history (
                    console_key, target_kind, target_key, old_value, new_value
                ) VALUES ($1, 'settings', 'global', $2::jsonb, $3::jsonb)
                """,
                console_key,
                json.dumps(dict(old) if old else {} , default=str),
                json.dumps(new_value),
            )
