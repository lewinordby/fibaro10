from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional
from urllib.parse import urlencode

import asyncpg

try:
    import aiohttp
except ModuleNotFoundError:  # Lightweight unit-test environments may only load pure helpers.
    aiohttp = None  # type: ignore[assignment]


logger = logging.getLogger("unifi_protect_events.plate_validation")

PERMANENT_NO_MATCH = {204, 400, 404}
TRANSIENT_HTTP_STATUSES = {0, 408, 425, 429, 500, 502, 503, 504}
SWEDISH_PLATE_RE = re.compile(r"^[A-HJ-PR-UW-Z]{3}[0-9]{2}([0-9]|[A-HJ-NPR-UW-Z])$")
DANISH_PLATE_RE = re.compile(r"^[A-Z]{2}[0-9]{5}$")


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_plate_validations (
        console_key VARCHAR NOT NULL,
        plate TEXT NOT NULL,
        status VARCHAR NOT NULL DEFAULT 'pending',
        is_valid BOOLEAN,
        likely_misread BOOLEAN NOT NULL DEFAULT FALSE,
        country_code VARCHAR,
        source VARCHAR,
        vehicle_label TEXT,
        local_match BOOLEAN NOT NULL DEFAULT FALSE,
        sources JSONB NOT NULL DEFAULT '{}'::jsonb,
        error TEXT,
        attempts INTEGER NOT NULL DEFAULT 0,
        first_seen_at TIMESTAMPTZ,
        last_seen_at TIMESTAMPTZ,
        checked_at TIMESTAMPTZ,
        next_check_at TIMESTAMPTZ,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (console_key, plate)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_plate_validations_due
        ON unifi_protect_plate_validations (console_key, next_check_at, status)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_plate_validations_status
        ON unifi_protect_plate_validations (console_key, status, last_seen_at DESC)
    """,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compact_plate(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def is_swedish_plate(value: Any) -> bool:
    return bool(SWEDISH_PLATE_RE.fullmatch(compact_plate(value)))


def is_danish_plate(value: Any) -> bool:
    return bool(DANISH_PLATE_RE.fullmatch(compact_plate(value)))


def json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    return value


def first_vehicle(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {}
    vehicles = raw.get("kjoretoydataListe")
    if isinstance(vehicles, list) and vehicles and isinstance(vehicles[0], Mapping):
        return dict(vehicles[0])
    return dict(raw)


def nested(data: Any, *path: Any) -> Any:
    current = data
    for key in path:
        if isinstance(key, int):
            if not isinstance(current, list) or key >= len(current):
                return None
            current = current[key]
        elif isinstance(current, Mapping):
            current = current.get(key)
        else:
            return None
    return current


def first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def svv_vehicle_label(raw: Any) -> Optional[str]:
    vehicle = first_vehicle(raw)
    general = nested(vehicle, "godkjenning", "tekniskGodkjenning", "tekniskeData", "generelt") or {}
    make = first_present(
        nested(general, "merke", 0, "merke"),
        nested(general, "merke", 0, "merkeNavn"),
        nested(general, "merke", 0),
    )
    model = first_present(nested(general, "handelsbetegnelse", 0), nested(general, "modell"))
    label = " ".join(str(value).strip() for value in (make, model) if str(value or "").strip())
    return label or None


def foreign_vehicle_label(data: Any) -> Optional[str]:
    if not isinstance(data, Mapping):
        return None
    fields = data.get("fields") if isinstance(data.get("fields"), Mapping) else {}
    value = first_present(data.get("vehicle_title"), data.get("title"), fields.get("vehicle_title"))
    return str(value).strip() if value else None


def source_result(
    *,
    status: int,
    checked_at: datetime,
    outcome: str,
    error: Optional[str] = None,
    data: Any = None,
    url: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "status": int(status),
        "outcome": outcome,
        "checked_at": checked_at.isoformat(),
        "error": error,
        "url": url,
        "data": data if isinstance(data, (dict, list)) else None,
    }


def public_validation(row: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    if not row:
        return {
            "status": "pending",
            "is_valid": None,
            "likely_misread": False,
            "country_code": None,
            "country": None,
            "source": None,
            "vehicle_label": None,
            "local_match": False,
            "checked_at": None,
            "next_check_at": None,
            "message": "Venter på validering i Protect Ledger",
            "sources": {},
        }
    status = str(row.get("validation_status") or row.get("status") or "pending")
    country_code = row.get("validation_country_code") or row.get("country_code")
    country = {"NO": "Norge", "SE": "Sverige", "DK": "Danmark"}.get(str(country_code or "").upper())
    messages = {
        "valid_local": "Kjent i lokalt kjøretøy-/parkeringsregister",
        "valid_norway": "Bekreftet hos Statens vegvesen",
        "valid_sweden": "Bekreftet i svensk kjøretøyoppslag",
        "valid_denmark": "Bekreftet i dansk kjøretøyoppslag",
        "not_found": "Ikke funnet lokalt, i Norge eller i relevant svensk/dansk register",
        "pending": "Venter på validering i Protect Ledger",
        "error": "Valideringen er midlertidig utsatt; skiltet er ikke avvist",
    }
    sources = json_value(row.get("validation_sources") if "validation_sources" in row else row.get("sources"))
    return {
        "status": status,
        "is_valid": row.get("validation_is_valid") if "validation_is_valid" in row else row.get("is_valid"),
        "likely_misread": bool(
            row.get("validation_likely_misread")
            if "validation_likely_misread" in row
            else row.get("likely_misread")
        ),
        "country_code": country_code,
        "country": country,
        "source": row.get("validation_source") or row.get("source"),
        "vehicle_label": row.get("validation_vehicle_label") or row.get("vehicle_label"),
        "local_match": bool(row.get("validation_local_match") or row.get("local_match")),
        "checked_at": row.get("validation_checked_at") or row.get("checked_at"),
        "next_check_at": row.get("validation_next_check_at") or row.get("next_check_at"),
        "message": messages.get(status, status),
        "error": row.get("validation_error") or row.get("error"),
        "sources": sources if isinstance(sources, Mapping) else {},
    }


@dataclass(frozen=True)
class ValidationSettings:
    enabled: bool
    svv_api_key: str
    svv_api_url: str
    svv_auth_header: str
    svv_auth_prefix: str
    car_info_url: str
    car_info_token: str
    interval_seconds: int = 30
    batch_size: int = 20
    timeout_seconds: int = 30
    valid_cache_days: int = 30
    negative_cache_days: int = 7
    transient_retry_minutes: int = 30


class PlateValidator:
    def __init__(
        self,
        pool: asyncpg.Pool,
        session: aiohttp.ClientSession,
        console_key: str,
        settings: ValidationSettings,
    ) -> None:
        self.pool = pool
        self.session = session
        self.console_key = console_key
        self.settings = settings
        self.wake_event = asyncio.Event()
        self.last_run_at: Optional[datetime] = None
        self.last_success_at: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.processed_since_start = 0
        self.validated_since_start = 0
        self.not_found_since_start = 0
        self._running = False

    async def initialize(self) -> None:
        for statement in SCHEMA_STATEMENTS:
            await self.pool.execute(statement)
        await self.pool.execute(
            """
            INSERT INTO unifi_protect_plate_validations (
                console_key, plate, first_seen_at, last_seen_at, next_check_at
            )
            SELECT console_key, normalized_value, min(occurred_at), max(occurred_at), CURRENT_TIMESTAMP
            FROM unifi_protect_recognitions
            WHERE console_key = $1
              AND kind = 'license_plate'
              AND normalized_value IS NOT NULL
              AND normalized_value <> ''
              AND COALESCE(source_device, '') <> 'FAKE_MAC'
            GROUP BY console_key, normalized_value
            ON CONFLICT (console_key, plate) DO UPDATE SET
                first_seen_at = LEAST(
                    unifi_protect_plate_validations.first_seen_at,
                    EXCLUDED.first_seen_at
                ),
                last_seen_at = GREATEST(
                    unifi_protect_plate_validations.last_seen_at,
                    EXCLUDED.last_seen_at
                )
            """,
            self.console_key,
        )

    def wake(self) -> None:
        self.wake_event.set()

    async def run_forever(self) -> None:
        if not self.settings.enabled:
            logger.info("Protect Ledger plate validation is disabled")
            return
        while True:
            try:
                await self.run_due()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.last_error = str(error)[:500]
                logger.exception("Protect Ledger plate validation cycle failed")
            self.wake_event.clear()
            try:
                await asyncio.wait_for(
                    self.wake_event.wait(), timeout=self.settings.interval_seconds
                )
            except asyncio.TimeoutError:
                pass

    async def run_due(self, *, force_plate: str = "") -> dict[str, Any]:
        if self._running:
            return {"status": "busy", "processed": 0}
        self._running = True
        self.last_run_at = utc_now()
        processed = valid = not_found = failed = 0
        try:
            if force_plate:
                plate = compact_plate(force_plate)
                await self.pool.execute(
                    """
                    INSERT INTO unifi_protect_plate_validations (
                        console_key, plate, status, next_check_at, updated_at
                    ) VALUES ($1, $2, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (console_key, plate) DO UPDATE SET
                        status = 'pending', next_check_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    self.console_key,
                    plate,
                )
                plates = [plate]
            else:
                rows = await self.pool.fetch(
                    """
                    SELECT plate
                    FROM unifi_protect_plate_validations
                    WHERE console_key = $1
                      AND (next_check_at IS NULL OR next_check_at <= CURRENT_TIMESTAMP)
                    ORDER BY
                        CASE status WHEN 'pending' THEN 0 WHEN 'error' THEN 1 ELSE 2 END,
                        last_seen_at DESC NULLS LAST,
                        updated_at ASC
                    LIMIT $2
                    """,
                    self.console_key,
                    self.settings.batch_size,
                )
                plates = [str(row["plate"]) for row in rows]
            for plate in plates:
                try:
                    result = await self.validate_plate(plate)
                    processed += 1
                    if result["is_valid"] is True:
                        valid += 1
                    elif result["status"] == "not_found":
                        not_found += 1
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    failed += 1
                    await self._store_transient_error(plate, str(error))
                    logger.warning("Plate validation failed for %s: %s", plate, error)
            self.processed_since_start += processed
            self.validated_since_start += valid
            self.not_found_since_start += not_found
            if failed == 0:
                self.last_success_at = utc_now()
                self.last_error = None
            return {
                "status": "ok" if failed == 0 else "partial",
                "processed": processed,
                "valid": valid,
                "not_found": not_found,
                "failed": failed,
            }
        finally:
            self._running = False

    async def _local_evidence(self, plate: str) -> Optional[dict[str, Any]]:
        try:
            row = await self.pool.fetchrow(
                """
                SELECT plate, navn, omrade, sun2_id, notat, first_seen, last_seen,
                       parkering_count, paid_total
                FROM kjoretoy
                WHERE regexp_replace(upper(COALESCE(plate, '')), '[^A-Z0-9]', '', 'g') = $1
                ORDER BY last_seen DESC NULLS LAST
                LIMIT 1
                """,
                plate,
            )
        except asyncpg.UndefinedTableError:
            return None
        if row:
            return {
                "plate": row["plate"],
                "name": row["navn"],
                "area": row["omrade"],
                "sun2_id": row["sun2_id"],
                "first_seen": row["first_seen"].isoformat() if row["first_seen"] else None,
                "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None,
                "parking_count": int(row["parkering_count"] or 0),
                "paid_total": float(row["paid_total"] or 0),
            }
        try:
            parking = await self.pool.fetchrow(
                """
                SELECT car_license_number AS plate, count(*)::integer AS parking_count,
                       min(start_time) AS first_seen, max(start_time) AS last_seen
                FROM parkering
                WHERE regexp_replace(upper(COALESCE(car_license_number, '')), '[^A-Z0-9]', '', 'g') = $1
                GROUP BY car_license_number
                ORDER BY max(start_time) DESC
                LIMIT 1
                """,
                plate,
            )
        except asyncpg.UndefinedTableError:
            return None
        if not parking:
            return None
        return {
            "plate": parking["plate"],
            "first_seen": parking["first_seen"].isoformat() if parking["first_seen"] else None,
            "last_seen": parking["last_seen"].isoformat() if parking["last_seen"] else None,
            "parking_count": int(parking["parking_count"] or 0),
        }

    async def _svv_lookup(self, plate: str) -> dict[str, Any]:
        checked_at = utc_now()
        if not self.settings.svv_api_key:
            return source_result(
                status=0,
                checked_at=checked_at,
                outcome="configuration_error",
                error="SVV_API_KEY mangler i Protect Ledger",
            )
        url = f"{self.settings.svv_api_url}?{urlencode({'kjennemerke': plate})}"
        auth_value = " ".join(
            value for value in (self.settings.svv_auth_prefix, self.settings.svv_api_key) if value
        )
        headers = {
            "Accept": "application/json",
            self.settings.svv_auth_header: auth_value,
            "User-Agent": "protect-ledger/1.0",
        }
        try:
            timeout = aiohttp.ClientTimeout(total=self.settings.timeout_seconds)
            async with self.session.get(url, headers=headers, timeout=timeout) as response:
                text = await response.text()
                status = response.status
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as error:
            return source_result(
                status=0, checked_at=checked_at, outcome="transient_error", error=str(error)[:240]
            )
        if status in PERMANENT_NO_MATCH or not text.strip():
            return source_result(
                status=status or 204,
                checked_at=checked_at,
                outcome="not_found",
                error="Ingen treff hos Statens vegvesen",
            )
        if status >= 400:
            return source_result(
                status=status,
                checked_at=checked_at,
                outcome="transient_error" if status in TRANSIENT_HTTP_STATUSES else "error",
                error=f"HTTP {status} fra Statens vegvesen",
            )
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return source_result(
                status=502,
                checked_at=checked_at,
                outcome="transient_error",
                error="Uleselig JSON fra Statens vegvesen",
            )
        vehicle = first_vehicle(data)
        if not vehicle:
            return source_result(
                status=204, checked_at=checked_at, outcome="not_found", data=data
            )
        return source_result(status=200, checked_at=checked_at, outcome="confirmed", data=data)

    async def _foreign_lookup(self, plate: str, country_code: str) -> dict[str, Any]:
        checked_at = utc_now()
        if not self.settings.car_info_url:
            return source_result(
                status=0,
                checked_at=checked_at,
                outcome="configuration_error",
                error="Nordisk oppslagsadapter er ikke konfigurert",
            )
        headers = {"Accept": "application/json"}
        if self.settings.car_info_token:
            headers["X-Car-Info-Token"] = self.settings.car_info_token
        url = f"{self.settings.car_info_url.rstrip('/')}/api/lookup-plate/{plate}"
        try:
            timeout = aiohttp.ClientTimeout(total=self.settings.timeout_seconds + 5)
            async with self.session.post(url, headers=headers, timeout=timeout) as response:
                payload = await response.json(content_type=None)
                adapter_status = response.status
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ValueError) as error:
            return source_result(
                status=0, checked_at=checked_at, outcome="transient_error", error=str(error)[:240]
            )
        if adapter_status >= 400:
            return source_result(
                status=adapter_status,
                checked_at=checked_at,
                outcome="transient_error",
                error=str(payload.get("detail") or f"Oppslagsadapter HTTP {adapter_status}")[:240],
            )
        status = int(payload.get("http_status") or 0)
        data = payload.get("data") if isinstance(payload.get("data"), Mapping) else {}
        confirmed = bool(payload.get("confirmed"))
        error = str(payload.get("error") or "").strip() or None
        if status == 200 and confirmed:
            outcome = "confirmed"
        elif status in PERMANENT_NO_MATCH:
            outcome = "not_found"
        elif status in TRANSIENT_HTTP_STATUSES or status >= 500:
            outcome = "transient_error"
        else:
            outcome = "error"
        return source_result(
            status=status,
            checked_at=checked_at,
            outcome=outcome,
            error=error,
            data=data,
            url=str(payload.get("url") or "") or None,
        )

    async def validate_plate(self, raw_plate: str) -> dict[str, Any]:
        plate = compact_plate(raw_plate)
        if not plate:
            raise ValueError("Tomt registreringsnummer")
        checked_at = utc_now()
        sources: dict[str, Any] = {}
        local = await self._local_evidence(plate)
        if local:
            sources["local"] = {
                "outcome": "confirmed",
                "checked_at": checked_at.isoformat(),
                "data": local,
            }
            return await self._store_result(
                plate,
                status="valid_local",
                is_valid=True,
                likely_misread=False,
                country_code=None,
                source="Lokalt register",
                vehicle_label=str(local.get("name") or "").strip() or None,
                local_match=True,
                sources=sources,
                error=None,
                checked_at=checked_at,
                next_check_at=checked_at + timedelta(days=self.settings.valid_cache_days),
            )

        sources["local"] = {"outcome": "not_found", "checked_at": checked_at.isoformat()}
        svv = await self._svv_lookup(plate)
        sources["norway"] = svv
        if svv["outcome"] == "confirmed":
            return await self._store_result(
                plate,
                status="valid_norway",
                is_valid=True,
                likely_misread=False,
                country_code="NO",
                source="Statens vegvesen",
                vehicle_label=svv_vehicle_label(svv.get("data")),
                local_match=False,
                sources=sources,
                error=None,
                checked_at=checked_at,
                next_check_at=checked_at + timedelta(days=self.settings.valid_cache_days),
            )
        if svv["outcome"] not in {"not_found"}:
            return await self._store_result(
                plate,
                status="error" if svv["outcome"] != "configuration_error" else "pending",
                is_valid=None,
                likely_misread=False,
                country_code=None,
                source="Statens vegvesen",
                vehicle_label=None,
                local_match=False,
                sources=sources,
                error=svv.get("error"),
                checked_at=checked_at,
                next_check_at=checked_at + timedelta(minutes=self.settings.transient_retry_minutes),
            )

        if is_swedish_plate(plate):
            sweden = await self._foreign_lookup(plate, "SE")
        else:
            sweden = source_result(
                status=422, checked_at=checked_at, outcome="not_applicable", error="Ikke svensk skiltformat"
            )
        sources["sweden"] = sweden
        if sweden["outcome"] == "confirmed":
            return await self._store_result(
                plate,
                status="valid_sweden",
                is_valid=True,
                likely_misread=False,
                country_code="SE",
                source="Biluppgifter.se",
                vehicle_label=foreign_vehicle_label(sweden.get("data")),
                local_match=False,
                sources=sources,
                error=None,
                checked_at=checked_at,
                next_check_at=checked_at + timedelta(days=self.settings.valid_cache_days),
            )
        if sweden["outcome"] not in {"not_found", "not_applicable"}:
            return await self._store_result(
                plate,
                status="error",
                is_valid=None,
                likely_misread=False,
                country_code=None,
                source="Biluppgifter.se",
                vehicle_label=None,
                local_match=False,
                sources=sources,
                error=sweden.get("error"),
                checked_at=checked_at,
                next_check_at=checked_at + timedelta(minutes=self.settings.transient_retry_minutes),
            )

        if is_danish_plate(plate):
            denmark = await self._foreign_lookup(plate, "DK")
        else:
            denmark = source_result(
                status=422, checked_at=checked_at, outcome="not_applicable", error="Ikke dansk skiltformat"
            )
        sources["denmark"] = denmark
        if denmark["outcome"] == "confirmed":
            return await self._store_result(
                plate,
                status="valid_denmark",
                is_valid=True,
                likely_misread=False,
                country_code="DK",
                source="Tjekbil.dk",
                vehicle_label=foreign_vehicle_label(denmark.get("data")),
                local_match=False,
                sources=sources,
                error=None,
                checked_at=checked_at,
                next_check_at=checked_at + timedelta(days=self.settings.valid_cache_days),
            )
        if denmark["outcome"] not in {"not_found", "not_applicable"}:
            return await self._store_result(
                plate,
                status="error",
                is_valid=None,
                likely_misread=False,
                country_code=None,
                source="Tjekbil.dk",
                vehicle_label=None,
                local_match=False,
                sources=sources,
                error=denmark.get("error"),
                checked_at=checked_at,
                next_check_at=checked_at + timedelta(minutes=self.settings.transient_retry_minutes),
            )

        return await self._store_result(
            plate,
            status="not_found",
            is_valid=False,
            likely_misread=True,
            country_code=None,
            source=None,
            vehicle_label=None,
            local_match=False,
            sources=sources,
            error=None,
            checked_at=checked_at,
            next_check_at=checked_at + timedelta(days=self.settings.negative_cache_days),
        )

    async def _store_transient_error(self, plate: str, error: str) -> None:
        checked_at = utc_now()
        await self._store_result(
            compact_plate(plate),
            status="error",
            is_valid=None,
            likely_misread=False,
            country_code=None,
            source=None,
            vehicle_label=None,
            local_match=False,
            sources={},
            error=error[:500],
            checked_at=checked_at,
            next_check_at=checked_at + timedelta(minutes=self.settings.transient_retry_minutes),
        )

    async def _store_result(
        self,
        plate: str,
        *,
        status: str,
        is_valid: Optional[bool],
        likely_misread: bool,
        country_code: Optional[str],
        source: Optional[str],
        vehicle_label: Optional[str],
        local_match: bool,
        sources: Mapping[str, Any],
        error: Optional[str],
        checked_at: datetime,
        next_check_at: datetime,
    ) -> dict[str, Any]:
        row = await self.pool.fetchrow(
            """
            INSERT INTO unifi_protect_plate_validations (
                console_key, plate, status, is_valid, likely_misread, country_code,
                source, vehicle_label, local_match, sources, error, attempts,
                checked_at, next_check_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11, 1,
                $12, $13, CURRENT_TIMESTAMP
            )
            ON CONFLICT (console_key, plate) DO UPDATE SET
                status = EXCLUDED.status,
                is_valid = EXCLUDED.is_valid,
                likely_misread = EXCLUDED.likely_misread,
                country_code = EXCLUDED.country_code,
                source = EXCLUDED.source,
                vehicle_label = EXCLUDED.vehicle_label,
                local_match = EXCLUDED.local_match,
                sources = EXCLUDED.sources,
                error = EXCLUDED.error,
                attempts = unifi_protect_plate_validations.attempts + 1,
                checked_at = EXCLUDED.checked_at,
                next_check_at = EXCLUDED.next_check_at,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            self.console_key,
            plate,
            status,
            is_valid,
            likely_misread,
            country_code,
            source,
            vehicle_label,
            local_match,
            json.dumps(sources, ensure_ascii=False, default=str),
            error,
            checked_at,
            next_check_at,
        )
        return dict(row)

    async def status(self) -> dict[str, Any]:
        totals = await self.pool.fetchrow(
            """
            SELECT count(*)::integer AS total,
                   count(*) FILTER (WHERE is_valid IS TRUE)::integer AS valid,
                   count(*) FILTER (WHERE status = 'not_found')::integer AS not_found,
                   count(*) FILTER (WHERE status = 'pending')::integer AS pending,
                   count(*) FILTER (WHERE status = 'error')::integer AS errors,
                   count(*) FILTER (
                       WHERE next_check_at IS NULL OR next_check_at <= CURRENT_TIMESTAMP
                   )::integer AS due
            FROM unifi_protect_plate_validations
            WHERE console_key = $1
            """,
            self.console_key,
        )
        return {
            "enabled": self.settings.enabled,
            "svv_configured": bool(self.settings.svv_api_key),
            "nordic_adapter_configured": bool(self.settings.car_info_url),
            "running": self._running,
            "last_run_at": self.last_run_at,
            "last_success_at": self.last_success_at,
            "last_error": self.last_error,
            "processed_since_start": self.processed_since_start,
            "validated_since_start": self.validated_since_start,
            "not_found_since_start": self.not_found_since_start,
            "totals": dict(totals) if totals else {},
        }


async def upsert_plate_candidates(
    connection: asyncpg.Connection,
    console_key: str,
    rows: list[Mapping[str, Any]],
) -> int:
    stored = 0
    for row in rows:
        if row.get("kind") != "license_plate":
            continue
        plate = compact_plate(row.get("normalized_value") or row.get("value"))
        if not plate:
            continue
        occurred_at = row.get("occurred_at") or utc_now()
        await connection.execute(
            """
            INSERT INTO unifi_protect_plate_validations (
                console_key, plate, first_seen_at, last_seen_at, next_check_at
            ) VALUES ($1, $2, $3, $3, CURRENT_TIMESTAMP)
            ON CONFLICT (console_key, plate) DO UPDATE SET
                first_seen_at = LEAST(
                    unifi_protect_plate_validations.first_seen_at,
                    EXCLUDED.first_seen_at
                ),
                last_seen_at = GREATEST(
                    unifi_protect_plate_validations.last_seen_at,
                    EXCLUDED.last_seen_at
                )
            """,
            console_key,
            plate,
            occurred_at,
        )
        stored += 1
    return stored
