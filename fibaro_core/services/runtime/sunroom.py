"""Sunroom services with explicit process dependencies."""

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fastapi import HTTPException
from fibaro_core.models import (
    AlarmEvent,
    DoorEvent,
    DoorSensorStatus,
    EnergyFibaroSample,
    Sun2Bed,
    Sun2SessionImportRun,
    Sun2TanningSession,
)
from fibaro_core.schemas import DoorEventIn
from sqlalchemy import and_, or_, select
from statistics import median
from sun2_helpers import SUN2_ROOM_MAP_BY_DISPLAY, normalize_room_id, sun2_room_label
from time_formatting import (
    api_local_iso,
    format_source_datetime,
    format_source_time,
    local_naive_to_utc_naive,
    local_now_naive,
    normalize_local_naive,
    parse_datetime,
    utc_naive_to_local_naive,
)
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlencode
from value_parsing import float_value
import asyncio
import hashlib


@dataclass
class Dependencies:
    ALARM_APP_URL: Any
    DOOR_SENSOR_CONFIG: Any
    DOOR_SENSOR_IDS: Any
    HC3_DOOR_DEBOUNCE_SECONDS: Any
    HC3_DOOR_OTHER_OPEN_VERIFY_MINUTES: Any
    HC3_DOOR_SOLROOM_CLOSED_VERIFY_MINUTES: Any
    HC3_DOOR_STATUS_POLL_INTERVAL_SECONDS: Any
    HC3_DOOR_UNEXPECTED_CHECK_INITIAL_DELAY_SECONDS: Any
    HC3_DOOR_UNEXPECTED_CHECK_INTERVAL_SECONDS: Any
    NTFY_DOORS_TOPIC: Any
    SUNROOM_DOOR_ALERT_AFTER_END_MINUTES: Any
    SUNROOM_DOOR_CRITICAL_MINUTES: Any
    SUNROOM_DOOR_EXIT_GRACE_MINUTES: Any
    SUNROOM_DOOR_FAN_AFTER_RUN_MINUTES: Any
    SUNROOM_DOOR_FORCED_SYNC_MINUTES: Any
    SUNROOM_DOOR_MONITOR_INITIAL_DELAY_SECONDS: Any
    SUNROOM_DOOR_MONITOR_INTERVAL_SECONDS: Any
    SUNROOM_DOOR_NEW_SESSION_GRACE_MINUTES: Any
    SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES: Any
    SUNROOM_DOOR_PAYMENT_DELAY_MINUTES: Any
    SUNROOM_DOOR_SESSION_GRACE_MINUTES: Any
    SUNROOM_DOOR_SESSION_LOOKBACK_HOURS: Any
    SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES: Any
    SUNROOM_DOOR_SYNC_MAX_ATTEMPTS: Any
    SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS: Any
    SUNROOM_DOOR_WARN_AFTER_END_MINUTES: Any
    SUNROOM_BED_STATUS_MAX_AGE_MINUTES: Any
    alarm_event_payload: Callable[..., Any]
    async_session: Callable[..., Any]
    attach_hc3_alarm_verification: Callable[..., Any]
    enqueue_ntfy_message: Callable[..., Any]
    fetch_sun2_scraper_runtime: Callable[..., Any]
    force_sun2_sync_for_closed_rooms: Callable[..., Any]
    hc3_api_is_configured: Callable[..., Any]
    hc3_device_request: Callable[..., Any]
    hc3_first_present: Callable[..., Any]
    hc3_unexpected_poll_cooldown_active: Callable[..., Any]
    logger: Any
    mark_hc3_unexpected_poll_verified: Callable[..., Any]
    ntfy_subscribe_url: Callable[..., Any]
    ntfy_topic_url: Callable[..., Any]
    parse_boolish: Callable[..., Any]
    parse_day: Callable[..., Any]
    record_import_job: Callable[..., Any]
    sunroom_door_verifications: Any


def create_service(dependencies: Dependencies):

    async def publish_door_ntfy(
        title: str,
        message: str,
        priority: str = "4",
        tags: str = "door,warning",
        click_url: str = "",
        related_type: str = "",
        related_id: Optional[int] = None,
        session=None,
    ) -> bool:
        NTFY_DOORS_TOPIC = dependencies.NTFY_DOORS_TOPIC
        enqueue_ntfy_message = dependencies.enqueue_ntfy_message
        logger = dependencies.logger
        try:
            return await enqueue_ntfy_message(
                NTFY_DOORS_TOPIC,
                title,
                message,
                tags,
                priority,
                click_url,
                related_type,
                related_id,
                session,
            )
        except Exception as exc:
            logger.warning("Kunne ikke legge NTFY-varsel for dorer i ko: %s", exc, exc_info=True)
            return False

    def door_action_from_state(state: Optional[bool], action: Optional[str], raw_value: Optional[str]) -> str:
        parse_boolish = dependencies.parse_boolish
        action_text = (action or "").strip().upper()
        if action_text in {"OPEN", "OPENED", "APEN", "ÅPEN", "AOPEN", "PAA", "PÅ"}:
            return "OPEN"
        if action_text in {"CLOSED", "CLOSE", "LUKKET", "STENGT", "AV"}:
            return "CLOSED"
        resolved_state = state if state is not None else parse_boolish(raw_value)
        if resolved_state is True:
            return "OPEN"
        if resolved_state is False:
            return "CLOSED"
        return action_text or "UNKNOWN"

    def door_event_from_payload(data: DoorEventIn) -> DoorEvent:
        parse_boolish = dependencies.parse_boolish
        state = data.state if data.state is not None else parse_boolish(data.raw_value)
        return DoorEvent(
            timestamp=normalize_local_naive(data.timestamp) or local_now_naive(),
            event_type=data.event_type or "door_change",
            action=door_action_from_state(state, data.action, data.raw_value),
            device_key=data.device_key,
            device_id=data.device_id,
            device_name=data.device_name,
            source=data.source or "HC3",
            raw_value=str(data.raw_value) if data.raw_value is not None else None,
            state=state,
            previous_state=data.previous_state,
            battery_level=data.battery_level,
            extra=data.extra or {},
        )

    def door_age_label(value: Optional[datetime], now: Optional[datetime] = None) -> str:
        if not value:
            return "Aldri"
        now = now or local_now_naive()
        seconds = max(0, int((now - value).total_seconds()))
        if seconds < 60:
            return "Akkurat nå"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} min siden"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} t siden"
        days = hours // 24
        return "1 dag siden" if days == 1 else f"{days} dager siden"

    def door_state_from_event(row: Optional[Any]) -> Dict[str, str]:
        if not row:
            return {"state": "unknown", "label": "Ukjent", "tone": "unknown"}
        action = (getattr(row, "action", None) or "").upper()
        if row.state is True or action == "OPEN":
            return {"state": "open", "label": "Åpen", "tone": "warn"}
        if row.state is False or action == "CLOSED":
            return {"state": "closed", "label": "Lukket", "tone": "ok"}
        return {"state": "unknown", "label": "Ukjent", "tone": "unknown"}

    def door_event_payload(row: DoorEvent, now: Optional[datetime] = None) -> Dict[str, Any]:
        state = door_state_from_event(row)
        timestamp = normalize_local_naive(row.timestamp)
        return {
            "id": row.id,
            "timestamp": timestamp.isoformat() if timestamp else None,
            "timeLabel": format_source_datetime(timestamp) if timestamp else "-",
            "ageLabel": door_age_label(timestamp, now),
            "eventType": row.event_type,
            "action": row.action,
            "state": state["state"],
            "stateLabel": state["label"],
            "tone": state["tone"],
            "deviceKey": row.device_key,
            "deviceId": row.device_id,
            "deviceName": row.device_name,
            "source": row.source,
            "rawValue": row.raw_value,
            "batteryLevel": row.battery_level,
            "previousState": row.previous_state,
            "extra": row.extra or {},
        }

    def door_status_payload(
        config: Dict[str, Any],
        row: Optional[DoorEvent],
        now: datetime,
        changed_row: Optional[DoorEvent] = None,
        sensor_status: Optional[DoorSensorStatus] = None,
    ) -> Dict[str, Any]:
        current_row = sensor_status or row
        state = door_state_from_event(current_row)
        change_event = changed_row or row
        changed_at = (
            normalize_local_naive(sensor_status.last_changed_at)
            if sensor_status and sensor_status.last_changed_at
            else normalize_local_naive(change_event.timestamp) if change_event else None
        )
        updated_at = (
            normalize_local_naive(sensor_status.observed_at)
            if sensor_status and sensor_status.observed_at
            else normalize_local_naive(row.timestamp) if row else None
        )
        device_id = config.get("device_id")
        normal_state = str(config.get("normal_state") or "closed")
        return {
            "deviceId": device_id,
            "deviceKey": config["device_key"],
            "title": config["title"],
            "hc3Name": current_row.device_name if current_row and current_row.device_name else config.get("hc3_name", ""),
            "groupKey": config.get("group_key", "andre"),
            "groupTitle": config.get("group_title", "Andre dører"),
            "sectionKey": config.get("section_key", config.get("group_key", "andre")),
            "sectionTitle": config.get("section_title", config.get("group_title", "Andre dører")),
            "sortOrder": int(config.get("sort_order") or 0),
            "normalState": normal_state,
            "normalStateLabel": "Normalt åpen" if normal_state == "open" else "Normalt lukket",
            "isConfigured": device_id is not None,
            "state": state["state"],
            "stateLabel": state["label"] if device_id is not None else "Klargjort",
            "tone": state["tone"],
            "lastChangedAt": changed_at.isoformat() if changed_at else None,
            "lastChangedLabel": format_source_datetime(changed_at) if changed_at else "-",
            "ageLabel": door_age_label(changed_at, now),
            "lastUpdatedAt": updated_at.isoformat() if updated_at else None,
            "lastUpdatedLabel": format_source_datetime(updated_at) if updated_at else "-",
            "lastUpdatedAgeLabel": door_age_label(updated_at, now),
            "rawValue": current_row.raw_value if current_row else None,
            "batteryLevel": current_row.battery_level if current_row else None,
            "batteryLabel": f"{current_row.battery_level:.0f}%" if current_row and current_row.battery_level is not None else "-",
            "hc3Dead": sensor_status.hc3_dead if sensor_status else None,
            "hc3Enabled": sensor_status.hc3_enabled if sensor_status else None,
            "eventId": row.id if row else None,
            "lastChangedEventId": sensor_status.last_change_event_id if sensor_status else change_event.id if change_event else None,
        }

    async def upsert_door_sensor_status(
        session,
        config: Dict[str, Any],
        status: Dict[str, Any],
        observed_at: Optional[datetime] = None,
        change_event: Optional[DoorEvent] = None,
    ) -> DoorSensorStatus:
        device_id = int(status.get("device_id") or config.get("device_id"))
        observed_at = normalize_local_naive(observed_at) or local_now_naive()
        row = await session.get(DoorSensorStatus, device_id)
        current_state = status.get("state")
        if row is None:
            row = DoorSensorStatus(device_id=device_id, created_at=observed_at)
            session.add(row)
            state_changed = current_state is not None
        else:
            state_changed = current_state is not None and row.state != current_state

        row.device_key = status.get("device_key") or config.get("device_key")
        row.device_name = status.get("device_name") or config.get("hc3_name") or config.get("title")
        row.state = current_state
        row.raw_value = status.get("raw_value")
        if status.get("battery_level") is not None:
            row.battery_level = status.get("battery_level")
        if "dead" in status:
            row.hc3_dead = status.get("dead")
        if "hc3_enabled" in status:
            row.hc3_enabled = status.get("hc3_enabled")
        row.observed_at = observed_at
        row.updated_at = local_now_naive()
        row.source = str(status.get("source") or "HC3")
        row.extra = status.get("extra") or {}

        if change_event is not None and (state_changed or row.last_changed_at is None):
            row.last_changed_at = normalize_local_naive(change_event.timestamp) or observed_at
            row.last_change_event_id = change_event.id
        elif state_changed:
            row.last_changed_at = observed_at
            row.last_change_event_id = None
        return row

    async def upsert_door_event_status(session, event: DoorEvent) -> Optional[DoorSensorStatus]:
        if event.device_id is None:
            return None
        config = next(
            (
                item
                for item in dependencies.DOOR_SENSOR_CONFIG
                if item.get("device_id") is not None and int(item["device_id"]) == int(event.device_id)
            ),
            {
                "device_id": event.device_id,
                "device_key": event.device_key,
                "hc3_name": event.device_name,
                "title": event.device_name or event.device_key or str(event.device_id),
            },
        )
        return await upsert_door_sensor_status(
            session,
            config,
            {
                "device_id": event.device_id,
                "device_key": event.device_key,
                "device_name": event.device_name,
                "state": event.state,
                "raw_value": event.raw_value,
                "battery_level": event.battery_level,
                "source": event.source or "HC3",
                "extra": event.extra or {},
            },
            observed_at=event.timestamp,
            change_event=event,
        )

    def door_event_state_bool(row: Optional[DoorEvent]) -> Optional[bool]:
        if not row:
            return None
        state = door_state_from_event(row)
        if state["state"] == "open":
            return True
        if state["state"] == "closed":
            return False
        return None

    def door_event_device_key(row: DoorEvent) -> str:
        if row.device_id is not None:
            return f"id:{int(row.device_id)}"
        return f"key:{row.device_key or 'unknown'}"

    def door_config_device_key(config: Dict[str, Any]) -> str:
        if config.get("device_id") is None:
            return f"key:{config.get('device_key') or 'unknown'}"
        return f"id:{int(config['device_id'])}"

    def hc3_door_poll_is_configured() -> bool:
        hc3_api_is_configured = dependencies.hc3_api_is_configured
        return hc3_api_is_configured()

    def hc3_door_status_from_device(config: Dict[str, Any], device: Dict[str, Any]) -> Dict[str, Any]:
        hc3_first_present = dependencies.hc3_first_present
        parse_boolish = dependencies.parse_boolish
        properties = device.get("properties") if isinstance(device.get("properties"), dict) else {}
        raw_value = hc3_first_present(properties.get("value"), device.get("value"))
        battery_raw = hc3_first_present(properties.get("batteryLevel"), properties.get("battery"), device.get("batteryLevel"))
        battery_level = float_value(battery_raw) if battery_raw is not None else None
        dead = parse_boolish(hc3_first_present(properties.get("dead"), device.get("dead")))
        raw_text = str(raw_value).lower() if isinstance(raw_value, bool) else str(raw_value) if raw_value is not None else None
        return {
            "device_id": int(config["device_id"]),
            "device_key": config.get("device_key"),
            "device_name": hc3_first_present(device.get("name"), properties.get("name"), config.get("hc3_name"), config.get("title")),
            "state": parse_boolish(raw_value),
            "raw_value": raw_text,
            "battery_level": battery_level,
            "dead": dead,
            "hc3_enabled": parse_boolish(hc3_first_present(properties.get("enabled"), device.get("enabled"))),
        }

    async def hc3_fetch_door_status(config: Dict[str, Any]) -> Dict[str, Any]:
        hc3_device_request = dependencies.hc3_device_request
        device = await asyncio.to_thread(hc3_device_request, int(config["device_id"]))
        return hc3_door_status_from_device(config, device)

    async def hc3_fetch_door_statuses(configs: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        semaphore = asyncio.Semaphore(4)

        async def fetch_one(config: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                try:
                    payload = await hc3_fetch_door_status(config)
                    return {"config": config, "payload": payload, "error": None}
                except Exception as exc:
                    return {
                        "config": config,
                        "payload": None,
                        "error": str(exc),
                    }

        return await asyncio.gather(*(fetch_one(config) for config in configs))

    async def hc3_fetch_all_door_statuses() -> list[Dict[str, Any]]:
        DOOR_SENSOR_CONFIG = dependencies.DOOR_SENSOR_CONFIG
        configured = [config for config in DOOR_SENSOR_CONFIG if config.get("device_id") is not None]
        return await hc3_fetch_door_statuses(configured)

    async def latest_door_changes_by_device(session) -> Dict[int, DoorEvent]:
        DOOR_SENSOR_IDS = dependencies.DOOR_SENSOR_IDS
        if not DOOR_SENSOR_IDS:
            return {}
        raw_limit = max(len(DOOR_SENSOR_IDS) * 150, 1000)
        result = await session.execute(
            select(DoorEvent)
            .where(DoorEvent.device_id.in_(DOOR_SENSOR_IDS))
            .order_by(DoorEvent.timestamp.desc(), DoorEvent.id.desc())
            .limit(raw_limit)
        )
        change_rows = door_change_rows(list(reversed(result.scalars().all())))
        latest: Dict[int, DoorEvent] = {}
        for row in reversed(change_rows):
            if row.device_id is not None:
                latest.setdefault(int(row.device_id), row)
        return latest

    def door_state_age_minutes(row: Optional[DoorEvent], now: datetime) -> Optional[float]:
        if not row or not row.timestamp:
            return None
        timestamp = normalize_local_naive(row.timestamp)
        if not timestamp:
            return None
        return max(0.0, (now - timestamp).total_seconds() / 60)

    def door_unexpected_reason(config: Dict[str, Any], latest_row: Optional[DoorEvent], now: datetime) -> Optional[str]:
        HC3_DOOR_OTHER_OPEN_VERIFY_MINUTES = dependencies.HC3_DOOR_OTHER_OPEN_VERIFY_MINUTES
        HC3_DOOR_SOLROOM_CLOSED_VERIFY_MINUTES = dependencies.HC3_DOOR_SOLROOM_CLOSED_VERIFY_MINUTES
        device_id = config.get("device_id")
        if device_id is None:
            return None
        if latest_row is None:
            return "mangler kjent dørstatus"
        state = door_event_state_bool(latest_row)
        if state is None:
            return "ukjent dørstatus"
        age_minutes = door_state_age_minutes(latest_row, now)
        if age_minutes is None:
            return "mangler gyldig tidspunkt for siste dørstatus"
        title = str(config.get("title") or config.get("device_key") or device_id)
        if config.get("group_key") == "solrom":
            if state is False and age_minutes >= HC3_DOOR_SOLROOM_CLOSED_VERIFY_MINUTES:
                return f"{title} har vært lukket i {door_duration_label(int(age_minutes * 60))}"
            return None
        normal_state = str(config.get("normal_state") or "closed").lower()
        expected_state = True if normal_state == "open" else False
        if state != expected_state and age_minutes >= HC3_DOOR_OTHER_OPEN_VERIFY_MINUTES:
            status_text = "åpen" if state else "lukket"
            return f"{title} er {status_text} i {door_duration_label(int(age_minutes * 60))}"
        return None

    def hc3_door_unexpected_targets(
        latest_by_device: Dict[int, DoorEvent],
        now: datetime,
    ) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
        DOOR_SENSOR_CONFIG = dependencies.DOOR_SENSOR_CONFIG
        hc3_unexpected_poll_cooldown_active = dependencies.hc3_unexpected_poll_cooldown_active
        targets: list[Dict[str, Any]] = []
        cooldown: list[Dict[str, Any]] = []
        for config in DOOR_SENSOR_CONFIG:
            device_id = config.get("device_id")
            if device_id is None:
                continue
            device_id_int = int(device_id)
            reason = door_unexpected_reason(config, latest_by_device.get(device_id_int), now)
            if not reason:
                continue
            item = {
                "device_id": device_id_int,
                "title": config.get("title"),
                "reason": reason,
            }
            if hc3_unexpected_poll_cooldown_active(device_id_int, now):
                cooldown.append(item)
                continue
            targets.append({"config": config, **item})
        return targets, cooldown

    def door_poll_sync_payload(config: Dict[str, Any], status: Dict[str, Any], latest_row: Optional[DoorEvent]) -> DoorEventIn:
        latest_state = door_event_state_bool(latest_row)
        current_state = status.get("state")
        return DoorEventIn(
            timestamp=local_now_naive(),
            event_type="door_sync",
            action=door_action_from_state(current_state, None, status.get("raw_value")),
            device_key=status.get("device_key") or config.get("device_key"),
            device_id=status.get("device_id") or config.get("device_id"),
            device_name=status.get("device_name") or config.get("hc3_name") or config.get("title"),
            source="HC3 POLL SYNC",
            raw_value=status.get("raw_value"),
            state=current_state,
            previous_state=latest_state,
            battery_level=status.get("battery_level"),
            extra={
                "reason": "hc3_poll_reconciliation",
                "hc3_dead": status.get("dead"),
                "hc3_enabled": status.get("hc3_enabled"),
                "previous_event_id": latest_row.id if latest_row else None,
                "previous_timestamp": normalize_local_naive(latest_row.timestamp).isoformat() if latest_row and latest_row.timestamp else None,
            },
        )

    async def run_hc3_door_poll_once(
        reason: str = "manual",
        configs: Optional[list[Dict[str, Any]]] = None,
        target_reasons: Optional[Dict[int, str]] = None,
    ) -> Dict[str, Any]:
        DOOR_SENSOR_CONFIG = dependencies.DOOR_SENSOR_CONFIG
        DOOR_SENSOR_IDS = dependencies.DOOR_SENSOR_IDS
        async_session = dependencies.async_session
        record_import_job = dependencies.record_import_job
        started_at = local_now_naive()
        target_configs = configs if configs is not None else [config for config in DOOR_SENSOR_CONFIG if config.get("device_id") is not None]
        if not hc3_door_poll_is_configured():
            async with async_session() as session:
                row = await record_import_job(
                    session,
                    "hc3_door_poll_sync",
                    ok=False,
                    source="HC3 API",
                    started_at=started_at,
                    finished_at=local_now_naive(),
                    records_imported=0,
                    records_total=len(target_configs),
                    message="HC3 API-konfigurasjon mangler i Fibaro10-containeren.",
                    raw={"reason": reason, "configured": False},
                )
                await session.commit()
            return {"ok": False, "message": row.message, "checked": 0, "changed": 0, "errors": 1}

        fetch_results = await hc3_fetch_door_statuses(target_configs)
        checked = 0
        changes: list[Dict[str, Any]] = []
        errors: list[Dict[str, Any]] = []

        async with async_session() as session:
            latest_by_device = await latest_door_changes_by_device(session)
            for item in fetch_results:
                config = item["config"]
                device_id = int(config["device_id"])
                title = str(config.get("title") or config.get("device_key") or device_id)
                if item.get("error"):
                    errors.append({"device_id": device_id, "title": title, "error": item["error"]})
                    continue
                checked += 1
                status = item.get("payload") or {}
                current_state = status.get("state")
                if current_state is None:
                    errors.append({"device_id": device_id, "title": title, "error": f"Ukjent HC3-verdi: {status.get('raw_value')}"})
                    continue
                latest_row = latest_by_device.get(device_id)
                latest_state = door_event_state_bool(latest_row)
                if latest_state == current_state:
                    await upsert_door_sensor_status(
                        session,
                        config,
                        {**status, "source": "HC3 API"},
                        observed_at=local_now_naive(),
                        change_event=latest_row,
                    )
                    continue
                row = door_event_from_payload(door_poll_sync_payload(config, status, latest_row))
                session.add(row)
                await session.flush()
                await upsert_door_sensor_status(
                    session,
                    config,
                    {**status, "source": "HC3 API", "extra": row.extra or {}},
                    observed_at=row.timestamp,
                    change_event=row,
                )
                changes.append(
                    {
                        "event_id": row.id,
                        "device_id": device_id,
                        "title": title,
                        "previous_state": latest_state,
                        "state": current_state,
                        "action": row.action,
                        "reason": (target_reasons or {}).get(device_id),
                    }
                )

            ok = not errors
            if changes and errors:
                message = f"Korrigerte {len(changes)} dørstatus(er), men {len(errors)} HC3-oppslag feilet."
            elif changes:
                message = f"Korrigerte {len(changes)} dørstatus(er) etter kontroll mot HC3."
            elif errors:
                message = f"{len(errors)} HC3-oppslag feilet under dørstatuskontroll."
            else:
                message = f"Alle {checked} konfigurerte dører stemmer med HC3."
            await record_import_job(
                session,
                "hc3_door_poll_sync",
                ok=ok,
                source="HC3 API",
                started_at=started_at,
                finished_at=local_now_naive(),
                records_imported=len(changes),
                records_total=len(target_configs),
                duration_seconds=(local_now_naive() - started_at).total_seconds(),
                message=message,
                raw={
                    "reason": reason,
                    "checked": checked,
                    "polled": len(target_configs),
                    "configured_total": len(DOOR_SENSOR_IDS),
                    "target_reasons": target_reasons or {},
                    "changed": len(changes),
                    "errors": errors[:20],
                    "changes": changes[:20],
                },
            )
            await session.commit()

        return {
            "ok": ok,
            "message": message,
            "checked": checked,
            "polled": len(target_configs),
            "changed": len(changes),
            "errors": len(errors),
            "changes": changes,
        }

    async def run_hc3_door_unexpected_check_once(reason: str = "interval") -> Dict[str, Any]:
        DOOR_SENSOR_IDS = dependencies.DOOR_SENSOR_IDS
        async_session = dependencies.async_session
        mark_hc3_unexpected_poll_verified = dependencies.mark_hc3_unexpected_poll_verified
        record_import_job = dependencies.record_import_job
        started_at = local_now_naive()
        now = local_now_naive()
        async with async_session() as session:
            latest_by_device = await latest_door_changes_by_device(session)
            targets, cooldown = hc3_door_unexpected_targets(latest_by_device, now)
            if not targets:
                message = (
                    "Uventet dørstatus er nylig kontrollert - HC3 ble ikke spurt igjen."
                    if cooldown
                    else "Ingen uventede dørstatuser - HC3 ble ikke spurt."
                )
                await record_import_job(
                    session,
                    "hc3_door_poll_sync",
                    ok=True,
                    source="Fibaro10 lokal kontroll",
                    started_at=started_at,
                    finished_at=local_now_naive(),
                    records_imported=0,
                    records_total=len(DOOR_SENSOR_IDS),
                    duration_seconds=(local_now_naive() - started_at).total_seconds(),
                    message=message,
                    raw={
                        "reason": reason,
                        "unexpected": len(cooldown),
                        "polled": 0,
                        "configured_total": len(DOOR_SENSOR_IDS),
                        "cooldown": cooldown[:20],
                    },
                )
                await session.commit()
                return {"ok": True, "message": message, "unexpected": len(cooldown), "polled": 0, "changed": 0, "errors": 0}

        target_configs = [item["config"] for item in targets]
        target_reasons = {int(item["device_id"]): str(item["reason"]) for item in targets}
        result = await run_hc3_door_poll_once(reason, target_configs, target_reasons)
        mark_hc3_unexpected_poll_verified((int(item["device_id"]) for item in targets), local_now_naive())
        result["unexpected"] = len(targets)
        result["cooldownSkipped"] = len(cooldown)
        return result

    async def hc3_door_poll_worker():
        DOOR_SENSOR_IDS = dependencies.DOOR_SENSOR_IDS
        HC3_DOOR_UNEXPECTED_CHECK_INITIAL_DELAY_SECONDS = dependencies.HC3_DOOR_UNEXPECTED_CHECK_INITIAL_DELAY_SECONDS
        HC3_DOOR_STATUS_POLL_INTERVAL_SECONDS = dependencies.HC3_DOOR_STATUS_POLL_INTERVAL_SECONDS
        async_session = dependencies.async_session
        logger = dependencies.logger
        record_import_job = dependencies.record_import_job
        await asyncio.sleep(HC3_DOOR_UNEXPECTED_CHECK_INITIAL_DELAY_SECONDS)
        while True:
            try:
                await run_hc3_door_poll_once("status_interval")
            except Exception as exc:
                logger.warning("HC3 dørstatuskontroll feilet: %s", exc, exc_info=True)
                try:
                    async with async_session() as session:
                        await record_import_job(
                            session,
                            "hc3_door_poll_sync",
                            ok=False,
                            source="HC3 API",
                            started_at=local_now_naive(),
                            finished_at=local_now_naive(),
                            records_imported=0,
                            records_total=len(DOOR_SENSOR_IDS),
                            message=f"HC3 dørstatuskontroll feilet: {exc}",
                            raw={"reason": "worker_exception"},
                        )
                        await session.commit()
                except Exception:
                    logger.warning("Kunne ikke logge feil fra HC3 dørstatuskontroll.", exc_info=True)
            await asyncio.sleep(HC3_DOOR_STATUS_POLL_INTERVAL_SECONDS)

    def door_period_device_key(period: Dict[str, Any]) -> str:
        device_id = period.get("deviceId")
        if device_id is not None:
            try:
                return f"id:{int(device_id)}"
            except (TypeError, ValueError):
                pass
        return f"key:{period.get('deviceKey') or 'unknown'}"

    def door_change_rows(rows_ascending: list[DoorEvent]) -> list[DoorEvent]:
        HC3_DOOR_DEBOUNCE_SECONDS = dependencies.HC3_DOOR_DEBOUNCE_SECONDS
        changes_by_device: Dict[str, list[DoorEvent]] = {}
        last_state_by_device: Dict[str, bool] = {}
        for row in rows_ascending:
            state = door_event_state_bool(row)
            if state is None:
                continue
            key = door_event_device_key(row)
            if key not in last_state_by_device or last_state_by_device[key] != state:
                changes_by_device.setdefault(key, []).append(row)
                last_state_by_device[key] = state

        stabilized: list[DoorEvent] = []
        for device_rows in changes_by_device.values():
            cluster: list[DoorEvent] = []

            def flush_cluster() -> None:
                if not cluster:
                    return
                if len(cluster) <= 2:
                    stabilized.extend(cluster)
                    return
                final_state = door_event_state_bool(cluster[-1])
                representative = next(
                    (item for item in cluster if door_event_state_bool(item) == final_state),
                    cluster[-1],
                )
                stabilized.append(representative)

            for row in device_rows:
                if cluster:
                    previous_at = normalize_local_naive(cluster[-1].timestamp)
                    current_at = normalize_local_naive(row.timestamp)
                    gap_seconds = (current_at - previous_at).total_seconds() if previous_at and current_at else None
                    if gap_seconds is None or gap_seconds > HC3_DOOR_DEBOUNCE_SECONDS:
                        flush_cluster()
                        cluster = []
                cluster.append(row)
            flush_cluster()

        stabilized.sort(
            key=lambda row: (
                normalize_local_naive(row.timestamp) or datetime.min,
                int(row.id or 0),
            )
        )
        changes: list[DoorEvent] = []
        last_stable_state_by_device: Dict[str, bool] = {}
        for row in stabilized:
            state = door_event_state_bool(row)
            key = door_event_device_key(row)
            if state is not None and last_stable_state_by_device.get(key) != state:
                changes.append(row)
                last_stable_state_by_device[key] = state
        return changes

    def latest_door_event_by_device(rows_descending: list[DoorEvent]) -> Dict[int, DoorEvent]:
        latest_by_device: Dict[int, DoorEvent] = {}
        for row in rows_descending:
            if row.device_id is None:
                continue
            latest_by_device.setdefault(int(row.device_id), row)
        return latest_by_device

    def door_duration_label(seconds: Optional[int]) -> str:
        if seconds is None:
            return "-"
        seconds = max(0, int(seconds))
        if seconds < 60:
            return f"{seconds} sek"
        minutes = seconds // 60
        if minutes < 60:
            return "1 min" if minutes == 1 else f"{minutes} min"
        hours = minutes // 60
        rest_minutes = minutes % 60
        if hours < 24:
            if rest_minutes:
                return f"{hours} t {rest_minutes} min"
            return "1 t" if hours == 1 else f"{hours} t"
        days = hours // 24
        rest_hours = hours % 24
        if rest_hours:
            return f"{days} d {rest_hours} t"
        return "1 dag" if days == 1 else f"{days} dager"

    def door_title_for_row(row: DoorEvent) -> str:
        DOOR_SENSOR_CONFIG = dependencies.DOOR_SENSOR_CONFIG
        if row.device_id is not None:
            for config in DOOR_SENSOR_CONFIG:
                if config.get("device_id") is not None and int(config["device_id"]) == int(row.device_id):
                    return str(config["title"])
        return row.device_name or row.device_key or "Ukjent dør"

    def door_period_payload(open_row: DoorEvent, close_row: Optional[DoorEvent], now: datetime) -> Dict[str, Any]:
        opened_at = normalize_local_naive(open_row.timestamp)
        closed_at = normalize_local_naive(close_row.timestamp) if close_row else None
        duration_end = closed_at or now
        duration_seconds = int((duration_end - opened_at).total_seconds()) if opened_at else None
        state = "open" if close_row is None else "closed"
        return {
            "id": f"{open_row.device_id or open_row.device_key or 'door'}-{open_row.id}",
            "deviceId": open_row.device_id,
            "deviceKey": open_row.device_key,
            "deviceName": open_row.device_name,
            "title": door_title_for_row(open_row),
            "state": state,
            "stateLabel": "Åpen nå" if state == "open" else "Lukket",
            "tone": "warn" if state == "open" else "ok",
            "openedAt": opened_at.isoformat() if opened_at else None,
            "openedLabel": format_source_datetime(opened_at) if opened_at else "-",
            "openedAgeLabel": door_age_label(opened_at, now),
            "closedAt": closed_at.isoformat() if closed_at else None,
            "closedLabel": format_source_datetime(closed_at) if closed_at else "Åpen nå",
            "closedAgeLabel": door_age_label(closed_at, now) if closed_at else "",
            "durationSeconds": duration_seconds,
            "durationLabel": door_duration_label(duration_seconds),
            "openedEventId": open_row.id,
            "closedEventId": close_row.id if close_row else None,
        }

    def door_open_periods(change_rows_ascending: list[DoorEvent], now: datetime) -> list[Dict[str, Any]]:
        open_by_device: Dict[str, DoorEvent] = {}
        periods: list[Dict[str, Any]] = []
        for row in change_rows_ascending:
            state = door_event_state_bool(row)
            key = door_event_device_key(row)
            if state is True:
                open_by_device[key] = row
            elif state is False:
                open_row = open_by_device.pop(key, None)
                if open_row:
                    periods.append(door_period_payload(open_row, row, now))
        for open_row in open_by_device.values():
            periods.append(door_period_payload(open_row, None, now))
        return sorted(periods, key=lambda item: item.get("openedAt") or "", reverse=True)

    def door_closed_period_payload(close_row: DoorEvent, open_row: Optional[DoorEvent], now: datetime) -> Dict[str, Any]:
        closed_at = normalize_local_naive(close_row.timestamp)
        opened_at = normalize_local_naive(open_row.timestamp) if open_row else None
        duration_end = opened_at or now
        duration_seconds = int((duration_end - closed_at).total_seconds()) if closed_at else None
        state = "active" if open_row is None else "closed"
        return {
            "id": f"{close_row.device_id or close_row.device_key or 'door'}-{close_row.id}",
            "deviceId": close_row.device_id,
            "deviceKey": close_row.device_key,
            "title": door_title_for_row(close_row),
            "state": state,
            "closedAt": closed_at,
            "openedAt": opened_at,
            "closedEventId": close_row.id,
            "openedEventId": open_row.id if open_row else None,
            "durationSeconds": duration_seconds,
        }

    def door_closed_periods(change_rows_ascending: list[DoorEvent], now: datetime) -> list[Dict[str, Any]]:
        closed_by_device: Dict[str, DoorEvent] = {}
        periods: list[Dict[str, Any]] = []
        for row in change_rows_ascending:
            state = door_event_state_bool(row)
            key = door_event_device_key(row)
            if state is False:
                closed_by_device[key] = row
            elif state is True:
                close_row = closed_by_device.pop(key, None)
                if close_row:
                    periods.append(door_closed_period_payload(close_row, row, now))
        for close_row in closed_by_device.values():
            periods.append(door_closed_period_payload(close_row, None, now))
        return sorted(periods, key=lambda item: item.get("closedAt") or datetime.min, reverse=True)

    def sunroom_display_number(config: Dict[str, Any]) -> Optional[int]:
        try:
            return int(config.get("sort_order") or 0)
        except (TypeError, ValueError):
            return None

    def sunroom_identity_for_config(config: Dict[str, Any]) -> Dict[str, Any]:
        display_number = sunroom_display_number(config)
        if display_number is None:
            return {}
        return dict(SUN2_ROOM_MAP_BY_DISPLAY.get(display_number) or {})

    def sunroom_room_id_for_config(config: Dict[str, Any]) -> Optional[str]:
        display_number = sunroom_display_number(config)
        if display_number is None:
            return None
        mapped = sunroom_identity_for_config(config)
        return mapped.get("room_id") or normalize_room_id(f"rom-{display_number:02d}")

    def sunroom_bed_id_for_config(config: Dict[str, Any]) -> Optional[str]:
        bed_id = sunroom_identity_for_config(config).get("sun2_bed_id")
        return str(bed_id).strip() if bed_id is not None and str(bed_id).strip() else None

    def sunroom_canonical_room_id(row: Sun2TanningSession) -> Optional[str]:
        bed_id = str(row.sun2_bed_id or "").strip()
        if bed_id:
            for identity in SUN2_ROOM_MAP_BY_DISPLAY.values():
                if str(identity.get("sun2_bed_id") or "").strip() == bed_id:
                    return normalize_room_id(identity.get("room_id"))
        return normalize_room_id(row.room_id)

    def sunroom_config_for_room_id(room_id: str) -> Optional[Dict[str, Any]]:
        DOOR_SENSOR_CONFIG = dependencies.DOOR_SENSOR_CONFIG
        normalized = normalize_room_id(room_id)
        if not normalized:
            return None
        for config in DOOR_SENSOR_CONFIG:
            if config.get("group_key") == "solrom" and sunroom_room_id_for_config(config) == normalized:
                return config
        return None

    def sunroom_session_sun_start_at(row: Sun2TanningSession) -> Optional[datetime]:
        SUNROOM_DOOR_PAYMENT_DELAY_MINUTES = dependencies.SUNROOM_DOOR_PAYMENT_DELAY_MINUTES
        start_at = normalize_local_naive(row.started_at)
        if not start_at:
            return None
        return start_at + timedelta(minutes=SUNROOM_DOOR_PAYMENT_DELAY_MINUTES)

    def sunroom_session_end_at(row: Sun2TanningSession) -> Optional[datetime]:
        sun_start_at = sunroom_session_sun_start_at(row)
        if sun_start_at and row.duration_minutes is not None:
            try:
                return sun_start_at + timedelta(minutes=float(row.duration_minutes))
            except (TypeError, ValueError):
                return None
        return normalize_local_naive(row.ended_at)

    def sunroom_expected_exit_at(row: Sun2TanningSession) -> Optional[datetime]:
        SUNROOM_DOOR_EXIT_GRACE_MINUTES = dependencies.SUNROOM_DOOR_EXIT_GRACE_MINUTES
        end_at = sunroom_session_end_at(row)
        if not end_at:
            return None
        return end_at + timedelta(minutes=SUNROOM_DOOR_EXIT_GRACE_MINUTES)

    def sunroom_session_payload(row: Sun2TanningSession) -> Dict[str, Any]:
        start_at = normalize_local_naive(row.started_at)
        end_at = sunroom_session_end_at(row)
        expected_exit_at = sunroom_expected_exit_at(row)
        sun_start_at = sunroom_session_sun_start_at(row)
        href_params = {}
        if start_at:
            href_params["date_from"] = start_at.date().isoformat()
            href_params["date_to"] = start_at.date().isoformat()
        if row.room_id:
            href_params["room_id"] = row.room_id
        return {
            "id": row.id,
            "sourceSessionId": row.source_session_id,
            "roomId": row.room_id,
            "roomLabel": sun2_room_label(row.room_id, row.room or row.source_room_name),
            "startedAt": start_at.isoformat() if start_at else None,
            "startedLabel": format_source_datetime(start_at) if start_at else "-",
            "sunStartAt": sun_start_at.isoformat() if sun_start_at else None,
            "sunStartLabel": format_source_datetime(sun_start_at) if sun_start_at else "-",
            "endedAt": end_at.isoformat() if end_at else None,
            "endedLabel": format_source_datetime(end_at) if end_at else "-",
            "expectedExitAt": expected_exit_at.isoformat() if expected_exit_at else None,
            "expectedExitLabel": format_source_datetime(expected_exit_at) if expected_exit_at else "-",
            "sun2UserId": row.sun2_user_id,
            "sun2BedId": row.sun2_bed_id,
            "userName": row.user_name,
            "sourceRoomName": row.source_room_name,
            "durationMinutes": row.duration_minutes,
            "paidAmountKr": row.paid_amount_kr,
            "status": row.status,
            "href": f"/soling/enkeltimer?{urlencode(href_params)}" if href_params else "/soling/enkeltimer",
        }

    def sunroom_session_energy_window(row: Sun2TanningSession) -> Optional[tuple[datetime, datetime]]:
        sun_start_at = sunroom_session_sun_start_at(row)
        end_at = sunroom_session_end_at(row)
        if not sun_start_at or not end_at or end_at <= sun_start_at:
            return None
        return sun_start_at, end_at

    def sunroom_median_float(values: list[float]) -> Optional[float]:
        return float(median(values)) if values else None

    def sunroom_watt_label(value: Optional[float]) -> str:
        if value is None:
            return "-"
        return f"{round(float(value)):,}".replace(",", " ") + " W"

    def sunroom_energy_sample_items(samples: list[Any]) -> list[Dict[str, Any]]:
        items: list[Dict[str, Any]] = []
        for sample in samples:
            sample_time = sample.get("bucket_start") if isinstance(sample, dict) else getattr(sample, "bucket_start", None)
            sample_time = normalize_local_naive(sample_time)
            value = sample.get("differanse_beregnet_w") if isinstance(sample, dict) else getattr(sample, "differanse_beregnet_w", None)
            try:
                diff_w = float(value)
            except (TypeError, ValueError):
                continue
            if sample_time:
                items.append({"time": sample_time, "diff_w": diff_w})
        return sorted(items, key=lambda item: item["time"])

    def sunroom_energy_sample_window(
        samples: list[Dict[str, Any]],
        start_at: datetime,
        end_at: datetime,
        sample_times: Optional[list[datetime]] = None,
        *,
        include_end: bool = False,
    ) -> list[Dict[str, Any]]:
        if not samples or end_at < start_at:
            return []
        times = sample_times if sample_times is not None else [item["time"] for item in samples]
        start_index = bisect_left(times, start_at)
        end_index = bisect_right(times, end_at) if include_end else bisect_left(times, end_at)
        return samples[start_index:end_index]

    def sunroom_session_energy_evidence(
        row: Sun2TanningSession,
        samples: list[Dict[str, Any]],
        all_sessions: list[Sun2TanningSession],
        sample_times: Optional[list[datetime]] = None,
    ) -> Dict[str, Any]:
        SUNROOM_DOOR_FAN_AFTER_RUN_MINUTES = dependencies.SUNROOM_DOOR_FAN_AFTER_RUN_MINUTES
        payment_at = normalize_local_naive(row.started_at)
        window = sunroom_session_energy_window(row)
        if not payment_at or not window:
            return {
                "quality": "missing",
                "qualityLabel": "Mangler tid",
                "status": "unknown",
                "statusLabel": "Ikke vurdert",
                "detail": "Sun2-timen mangler start, varighet eller sluttid.",
                "samplesCount": 0,
            }

        sun_start_at, end_at = window
        measure_start = sun_start_at + timedelta(minutes=2)
        measure_end = end_at - timedelta(minutes=1)
        baseline_start = payment_at - timedelta(minutes=10)
        baseline_end = payment_at
        start_check_end = sun_start_at + timedelta(minutes=6)
        expected_delay_seconds = int((sun_start_at - payment_at).total_seconds())

        baseline_values = [
            item["diff_w"]
            for item in sunroom_energy_sample_window(samples, baseline_start, baseline_end, sample_times)
        ]
        active_values = [
            item["diff_w"]
            for item in sunroom_energy_sample_window(samples, measure_start, measure_end, sample_times)
        ]
        start_values = sunroom_energy_sample_window(
            samples,
            payment_at - timedelta(minutes=1),
            start_check_end,
            sample_times,
            include_end=True,
        )
        baseline_w = sunroom_median_float(baseline_values)
        active_w = sunroom_median_float(active_values)
        net_w = active_w - baseline_w if active_w is not None and baseline_w is not None else None

        overlap_count = 0
        edge_conflict = False
        own_id = row.id
        for other in all_sessions:
            if other.id == own_id:
                continue
            other_window = sunroom_session_energy_window(other)
            if not other_window:
                continue
            other_start, other_end = other_window
            other_occupied_end = other_end + timedelta(minutes=SUNROOM_DOOR_FAN_AFTER_RUN_MINUTES)
            if other_start < measure_end and other_occupied_end > measure_start:
                overlap_count += 1
                for other_edge in (other_start, other_end):
                    if abs((other_edge - sun_start_at).total_seconds()) <= 180 or abs((other_edge - end_at).total_seconds()) <= 180:
                        edge_conflict = True

        first_rise_at: Optional[datetime] = None
        start_delta_w: Optional[float] = None
        if baseline_w is not None:
            threshold = baseline_w + 1000
            for item in start_values:
                if item["time"] < sun_start_at - timedelta(minutes=1):
                    continue
                if item["diff_w"] >= threshold:
                    first_rise_at = item["time"]
                    start_delta_w = item["diff_w"] - baseline_w
                    break
        start_delay_seconds = int((first_rise_at - payment_at).total_seconds()) if first_rise_at else None
        delay_deviation_seconds = start_delay_seconds - expected_delay_seconds if start_delay_seconds is not None else None

        if not samples:
            quality = "missing"
            quality_label = "Mangler energidata"
        elif overlap_count == 0:
            quality = "clean"
            quality_label = "Ren måling"
        elif not edge_conflict:
            quality = "separable"
            quality_label = "Kan vurderes"
        else:
            quality = "overlap"
            quality_label = "Overlapp"

        if first_rise_at and delay_deviation_seconds is not None and abs(delay_deviation_seconds) <= 90:
            status = "confirmed"
            status_label = "Starter som forventet"
        elif first_rise_at:
            status = "deviation"
            status_label = "Startavvik"
        elif baseline_w is not None and active_w is not None and (net_w or 0) > 1500:
            status = "power_seen"
            status_label = "Effekt sett"
        elif quality == "overlap":
            status = "overlap"
            status_label = "Overlapp"
        else:
            status = "unknown"
            status_label = "Ikke nok grunnlag"

        if status == "confirmed":
            detail = f"Første tydelige effektøkning kom {door_duration_label(start_delay_seconds)} etter betaling."
        elif status == "deviation":
            direction = "sent" if (delay_deviation_seconds or 0) > 0 else "tidlig"
            detail = f"Effektøkningen kom {door_duration_label(abs(delay_deviation_seconds or 0))} {direction} mot forventet 3 min."
        elif status == "power_seen":
            detail = "Målt effekt i solperioden, men startøyeblikket er ikke tydelig nok."
        elif status == "overlap":
            detail = "Andre senger overlapper start eller slutt, så energien kan ikke fordeles sikkert."
        else:
            detail = "Ikke nok ren energidata til å kontrollere start."

        return {
            "quality": quality,
            "qualityLabel": quality_label,
            "status": status,
            "statusLabel": status_label,
            "detail": detail,
            "samplesCount": len(active_values),
            "baselineSamples": len(baseline_values),
            "overlapCount": overlap_count,
            "edgeConflict": edge_conflict,
            "baselineW": round(baseline_w, 1) if baseline_w is not None else None,
            "baselineLabel": sunroom_watt_label(baseline_w),
            "activeMedianW": round(active_w, 1) if active_w is not None else None,
            "activeMedianLabel": sunroom_watt_label(active_w),
            "estimatedNetW": round(net_w, 1) if net_w is not None else None,
            "estimatedNetLabel": sunroom_watt_label(net_w),
            "startDeltaW": round(start_delta_w, 1) if start_delta_w is not None else None,
            "startDeltaLabel": sunroom_watt_label(start_delta_w),
            "expectedDelaySeconds": expected_delay_seconds,
            "expectedDelayLabel": door_duration_label(expected_delay_seconds),
            "firstRiseAt": first_rise_at.isoformat() if first_rise_at else None,
            "firstRiseLabel": format_source_datetime(first_rise_at) if first_rise_at else "-",
            "startDelaySeconds": start_delay_seconds,
            "startDelayLabel": door_duration_label(start_delay_seconds) if start_delay_seconds is not None else "-",
            "delayDeviationSeconds": delay_deviation_seconds,
            "delayDeviationLabel": door_duration_label(abs(delay_deviation_seconds)) if delay_deviation_seconds is not None else "-",
        }

    def sunroom_power_marker(
        kind: str,
        label: str,
        anchor_at: datetime,
        value_w: Optional[float],
        reference_w: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        if value_w is None or reference_w is None:
            return None
        delta_w = float(value_w) - float(reference_w)
        if delta_w < 5000:
            return None
        return {
            "kind": kind,
            "label": label,
            "time": anchor_at.isoformat(),
            "timeLabel": format_source_datetime(anchor_at),
            "valueW": round(float(value_w), 1),
            "valueLabel": sunroom_watt_label(value_w),
            "deltaW": round(delta_w, 1),
            "deltaLabel": sunroom_watt_label(delta_w),
            "detail": f"Endring minst {sunroom_watt_label(delta_w)} mot referanse.",
        }

    def sunroom_power_markers(
        row: Sun2TanningSession,
        samples: list[Dict[str, Any]],
        sample_times: Optional[list[datetime]] = None,
    ) -> list[Dict[str, Any]]:
        window = sunroom_session_energy_window(row)
        if not window:
            return []
        sun_start_at, end_at = window
        start_anchor = sun_start_at + timedelta(minutes=5)
        stop_anchor = end_at - timedelta(minutes=5)
        baseline_w = sunroom_median_float(
            [
                item["diff_w"]
                for item in sunroom_energy_sample_window(
                    samples,
                    sun_start_at - timedelta(minutes=5),
                    sun_start_at,
                    sample_times,
                )
            ]
        )
        start_w = sunroom_median_float(
            [
                item["diff_w"]
                for item in sunroom_energy_sample_window(
                    samples,
                    start_anchor - timedelta(minutes=1),
                    start_anchor + timedelta(minutes=1),
                    sample_times,
                    include_end=True,
                )
            ]
        )
        stop_w = sunroom_median_float(
            [
                item["diff_w"]
                for item in sunroom_energy_sample_window(
                    samples,
                    stop_anchor - timedelta(minutes=1),
                    stop_anchor + timedelta(minutes=1),
                    sample_times,
                    include_end=True,
                )
            ]
        )
        after_w = sunroom_median_float(
            [
                item["diff_w"]
                for item in sunroom_energy_sample_window(
                    samples,
                    end_at,
                    end_at + timedelta(minutes=5),
                    sample_times,
                    include_end=True,
                )
            ]
        )
        markers = [
            sunroom_power_marker("power_start", "Effekt +5 min", start_anchor, start_w, baseline_w),
            sunroom_power_marker("power_stop", "Effekt -5 min", stop_anchor, stop_w, after_w),
        ]
        return [marker for marker in markers if marker]

    def sunroom_day_event(
        kind: str,
        label: str,
        event_at: Optional[datetime],
        detail: Optional[str] = None,
        source: Optional[str] = None,
        tone: str = "neutral",
        event_id: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        event_at = sunroom_parse_time_value(event_at)
        if not event_at:
            return None
        return {
            "id": f"{kind}-{event_id or event_at.isoformat()}",
            "kind": kind,
            "label": label,
            "time": event_at.isoformat(),
            "timeLabel": format_source_datetime(event_at),
            "detail": detail,
            "source": source,
            "tone": tone,
        }

    def sunroom_parse_time_value(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return normalize_local_naive(value)
        if isinstance(value, str):
            return normalize_local_naive(parse_datetime(value))
        return None

    def sunroom_marker_day_event(marker: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event_at = sunroom_parse_time_value(marker.get("time"))
        kind = str(marker.get("kind") or "marker")
        label = str(marker.get("label") or "Markør")
        tone = "neutral"
        if kind.startswith("entrance_"):
            tone = "entrance"
        elif kind.startswith("power_"):
            tone = "power"
            if kind == "power_start":
                label = "Effektøkning"
            elif kind == "power_stop":
                label = "Effektfall"
        detail = marker.get("detail") or marker.get("deltaLabel") or marker.get("valueLabel")
        return sunroom_day_event(
            kind=kind,
            label=label,
            event_at=event_at,
            detail=detail,
            source="Inngang" if kind.startswith("entrance_") else "HC3 effekt",
            tone=tone,
            event_id=marker.get("eventId") or marker.get("time"),
        )

    def sunroom_session_day_events(
        row: Sun2TanningSession,
        entrance_change_rows: list[DoorEvent],
        energy_samples: list[Dict[str, Any]],
        day_start: datetime,
        day_end: datetime,
        energy_sample_times: Optional[list[datetime]] = None,
    ) -> list[Dict[str, Any]]:
        payload = sunroom_session_payload(row)
        events: list[Dict[str, Any]] = []
        sun_start_at = sunroom_parse_time_value(payload.get("sunStartAt"))
        ended_at = sunroom_parse_time_value(payload.get("endedAt"))
        room_detail = f"{payload.get('durationMinutes') or '-'} min · {sunroom_money_label(payload.get('paidAmountKr'))}"
        for event in [
            sunroom_day_event("sun_start", "Soltime start", sun_start_at, room_detail, "Sun2", "sun", row.id),
            sunroom_day_event("sun_end", "Soltime slutt", ended_at, payload.get("roomLabel"), "Sun2", "sun", f"{row.id}-end"),
        ]:
            if event:
                events.append(event)
        for marker in sunroom_entrance_markers(row, entrance_change_rows) + sunroom_power_markers(
            row,
            energy_samples,
            energy_sample_times,
        ):
            event = sunroom_marker_day_event(marker)
            if event:
                events.append(event)
        return [
            event
            for event in events
            if (event_at := sunroom_parse_time_value(event.get("time"))) and day_start <= event_at < day_end
        ]

    def sunroom_period_day_events(period: Dict[str, Any], day_start: datetime, day_end: datetime) -> list[Dict[str, Any]]:
        events: list[Dict[str, Any]] = []
        closed_at = sunroom_parse_time_value(period.get("closedAt"))
        opened_at = sunroom_parse_time_value(period.get("openedAt"))
        duration_label = door_duration_label(period.get("durationSeconds")) if period.get("durationSeconds") is not None else None
        for event in [
            sunroom_day_event("door_closed", "Dør lukket", closed_at, duration_label, "HC3 dør", "door", period.get("closedEventId")),
            sunroom_day_event("door_open", "Dør åpnet", opened_at, duration_label, "HC3 dør", "door", period.get("openedEventId")),
        ]:
            if event and (event_at := sunroom_parse_time_value(event.get("time"))) and day_start <= event_at < day_end:
                events.append(event)
        return events

    def sunroom_money_label(value: Any) -> str:
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return "-"
        return f"{amount:,.0f} kr".replace(",", " ")

    def sunroom_entrance_config() -> Optional[Dict[str, Any]]:
        DOOR_SENSOR_CONFIG = dependencies.DOOR_SENSOR_CONFIG
        return next((config for config in DOOR_SENSOR_CONFIG if config.get("device_key") == "door_inngang"), None)

    def sunroom_door_event_marker(row: DoorEvent, kind: str, label: str) -> Optional[Dict[str, Any]]:
        event_at = normalize_local_naive(row.timestamp)
        state = door_state_from_event(row)
        if not event_at:
            return None
        return {
            "kind": kind,
            "label": label,
            "time": event_at.isoformat(),
            "timeLabel": format_source_datetime(event_at),
            "state": state["state"],
            "stateLabel": state["label"],
            "eventId": row.id,
            "deviceId": row.device_id,
            "deviceKey": row.device_key,
        }

    def sunroom_entrance_markers(row: Sun2TanningSession, entrance_rows: list[DoorEvent]) -> list[Dict[str, Any]]:
        sun_start_at = sunroom_session_sun_start_at(row) or normalize_local_naive(row.started_at)
        end_at = sunroom_session_end_at(row)
        if not sun_start_at or not end_at:
            return []
        window_start = sun_start_at - timedelta(minutes=90)
        window_end = end_at + timedelta(minutes=90)
        items: list[tuple[datetime, DoorEvent, Optional[bool]]] = []
        for event in entrance_rows:
            event_at = normalize_local_naive(event.timestamp)
            state = door_event_state_bool(event)
            if event_at and state is not None and window_start <= event_at <= window_end:
                items.append((event_at, event, state))
        before_open = next((item for item in reversed(items) if item[0] <= sun_start_at and item[2] is True), None)
        before_closed = next((item for item in reversed(items) if item[0] <= sun_start_at and item[2] is False), None)
        after_open = next((item for item in items if item[0] >= end_at and item[2] is True), None)
        after_closed = next((item for item in items if item[0] >= end_at and item[2] is False), None)
        marker_specs = [
            (before_open, "entrance_open_before", "Inngang åpnet før"),
            (before_closed, "entrance_closed_before", "Inngang lukket før"),
            (after_open, "entrance_open_after", "Inngang åpnet etter"),
            (after_closed, "entrance_closed_after", "Inngang lukket etter"),
        ]
        markers: list[Dict[str, Any]] = []
        for item, kind, label in marker_specs:
            if not item:
                continue
            marker = sunroom_door_event_marker(item[1], kind, label)
            if marker:
                markers.append(marker)
        return sorted(markers, key=lambda marker: marker.get("time") or "")

    def sunroom_session_matches_closed_period(row: Sun2TanningSession, closed_since: Optional[datetime], now: datetime) -> bool:
        SUNROOM_DOOR_PAYMENT_DELAY_MINUTES = dependencies.SUNROOM_DOOR_PAYMENT_DELAY_MINUTES
        SUNROOM_DOOR_SESSION_GRACE_MINUTES = dependencies.SUNROOM_DOOR_SESSION_GRACE_MINUTES
        SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES = dependencies.SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES
        start_at = normalize_local_naive(row.started_at)
        if not start_at or not closed_since:
            return False
        if start_at > now + timedelta(minutes=SUNROOM_DOOR_SESSION_GRACE_MINUTES):
            return False
        sun_start_at = sunroom_session_sun_start_at(row)
        session_end_at = sunroom_session_end_at(row)
        payment_window_start = closed_since - timedelta(minutes=SUNROOM_DOOR_PAYMENT_DELAY_MINUTES + 2)
        payment_window_end = closed_since + timedelta(minutes=SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES)
        paid_near_close = payment_window_start <= start_at <= min(
            payment_window_end,
            now + timedelta(minutes=SUNROOM_DOOR_SESSION_GRACE_MINUTES),
        )
        active_when_closed = bool(
            sun_start_at
            and session_end_at
            and sun_start_at <= closed_since <= session_end_at
        )
        return paid_near_close or active_when_closed

    def sunroom_session_matches_period(row: Sun2TanningSession, closed_at: Optional[datetime], opened_at: Optional[datetime], now: datetime) -> bool:
        SUNROOM_DOOR_PAYMENT_DELAY_MINUTES = dependencies.SUNROOM_DOOR_PAYMENT_DELAY_MINUTES
        SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES = dependencies.SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES
        start_at = normalize_local_naive(row.started_at)
        if not start_at or not closed_at:
            return False
        period_end = opened_at or now
        sun_start_at = sunroom_session_sun_start_at(row)
        session_end_at = sunroom_session_end_at(row)
        paid_near_close = (
            closed_at - timedelta(minutes=SUNROOM_DOOR_PAYMENT_DELAY_MINUTES + 2)
            <= start_at
            <= closed_at + timedelta(minutes=SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES)
        )
        physical_session_overlaps = bool(
            sun_start_at
            and session_end_at
            and sun_start_at <= period_end
            and session_end_at >= closed_at
        )
        return paid_near_close or physical_session_overlaps

    def sunroom_session_period_score(row: Sun2TanningSession, closed_at: datetime, opened_at: Optional[datetime], now: datetime) -> float:
        start_at = normalize_local_naive(row.started_at) or datetime.max
        expected_exit_at = sunroom_expected_exit_at(row)
        period_end = opened_at or now
        start_score = abs((start_at - closed_at).total_seconds())
        if expected_exit_at:
            exit_score = abs((expected_exit_at - period_end).total_seconds())
            return min(start_score, exit_score + 60)
        return start_score

    def sunroom_match_session_for_period(
        sessions: list[Sun2TanningSession],
        closed_at: Optional[datetime],
        opened_at: Optional[datetime],
        now: datetime,
    ) -> Optional[Sun2TanningSession]:
        if not closed_at:
            return None
        candidates = [
            row
            for row in sessions
            if sunroom_session_matches_period(row, closed_at, opened_at, now)
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda row: sunroom_session_period_score(row, closed_at, opened_at, now))[0]

    def sunroom_best_session_for_door(
        sessions: list[Sun2TanningSession],
        is_occupied: bool,
        changed_at: Optional[datetime],
        now: datetime,
    ) -> Optional[Sun2TanningSession]:
        if not sessions:
            return None
        if not is_occupied:
            return sessions[0]
        for row in sessions:
            if sunroom_session_matches_closed_period(row, changed_at, now):
                return row
        return None

    def sunroom_duration_label(seconds: Optional[int]) -> str:
        if seconds is None:
            return "-"
        if seconds > 0:
            return f"om {door_duration_label(seconds)}"
        return door_duration_label(abs(seconds))

    def sunroom_period_status(
        matched_session: Optional[Sun2TanningSession],
        closed_at: Optional[datetime],
        opened_at: Optional[datetime],
        now: datetime,
    ) -> Dict[str, Any]:
        SUNROOM_DOOR_ALERT_AFTER_END_MINUTES = dependencies.SUNROOM_DOOR_ALERT_AFTER_END_MINUTES
        SUNROOM_DOOR_SESSION_GRACE_MINUTES = dependencies.SUNROOM_DOOR_SESSION_GRACE_MINUTES
        SUNROOM_DOOR_WARN_AFTER_END_MINUTES = dependencies.SUNROOM_DOOR_WARN_AFTER_END_MINUTES
        duration_seconds = int(((opened_at or now) - closed_at).total_seconds()) if closed_at else None
        expected_exit_at = sunroom_expected_exit_at(matched_session) if matched_session else None
        is_active = opened_at is None
        severity = "ok"
        status = "Ferdig"
        detail = "Dørperiode ferdig."
        overstay_seconds: Optional[int] = None
        remaining_seconds: Optional[int] = None
        missing_session = False

        if not matched_session:
            missing_session = bool(duration_seconds is not None and duration_seconds >= int(SUNROOM_DOOR_SESSION_GRACE_MINUTES * 60))
            severity = "warning" if missing_session else "waiting"
            status = "Mangler soltime" if missing_session else "Avventer Sun2"
            detail = "Ingen Sun2-time er funnet for denne dørperioden." if missing_session else "Kort dørperiode uten sikker Sun2-kobling."
        elif expected_exit_at:
            session_end_at = sunroom_session_end_at(matched_session)
            compare_at = opened_at or now
            remaining_seconds = int((expected_exit_at - compare_at).total_seconds())
            overstay_seconds = max(0, -remaining_seconds)
            alert_seconds = int((compare_at - session_end_at).total_seconds()) if session_end_at else overstay_seconds
            if alert_seconds >= int(SUNROOM_DOOR_ALERT_AFTER_END_MINUTES * 60):
                severity = "alert"
                status = "Overtid"
                detail = "Døren ble ikke åpnet før rød grense etter solslutt."
            elif alert_seconds >= int(SUNROOM_DOOR_WARN_AFTER_END_MINUTES * 60):
                severity = "warning"
                status = "Overtid"
                detail = "Døren ble ikke åpnet før oransje grense etter solslutt."
            elif is_active:
                severity = "active"
                status = "Pågår"
                detail = "Soltime pågår eller kunden er innenfor normal utgangstid."
            else:
                severity = "ok"
                status = "OK"
                detail = "Døren ble åpnet innenfor forventet tid."
        elif matched_session and is_active:
            severity = "active"
            status = "Pågår"
            detail = "Soltime funnet, men sluttid mangler."

        return {
            "severity": severity,
            "status": status,
            "detail": detail,
            "missingSession": missing_session,
            "expectedExitAt": expected_exit_at,
            "remainingSeconds": remaining_seconds,
            "overstaySeconds": overstay_seconds,
        }

    def sunroom_period_payload(
        period: Dict[str, Any],
        matched_session: Optional[Sun2TanningSession],
        now: datetime,
    ) -> Dict[str, Any]:
        closed_at = period.get("closedAt")
        opened_at = period.get("openedAt")
        status = sunroom_period_status(matched_session, closed_at, opened_at, now)
        expected_exit_at = status.get("expectedExitAt")
        remaining_seconds = status.get("remainingSeconds")
        overstay_seconds = status.get("overstaySeconds")
        return {
            "id": period.get("id"),
            "state": period.get("state"),
            "isActive": opened_at is None,
            "closedAt": closed_at.isoformat() if closed_at else None,
            "closedLabel": format_source_datetime(closed_at) if closed_at else "-",
            "closedAgeLabel": door_age_label(closed_at, now),
            "openedAt": opened_at.isoformat() if opened_at else None,
            "openedLabel": format_source_datetime(opened_at) if opened_at else "Pågår",
            "openedAgeLabel": door_age_label(opened_at, now) if opened_at else "",
            "durationSeconds": period.get("durationSeconds"),
            "durationLabel": door_duration_label(period.get("durationSeconds")),
            "closedEventId": period.get("closedEventId"),
            "openedEventId": period.get("openedEventId"),
            "session": sunroom_session_payload(matched_session) if matched_session else None,
            "severity": status.get("severity"),
            "status": status.get("status"),
            "detail": status.get("detail"),
            "missingSession": status.get("missingSession"),
            "expectedExitAt": expected_exit_at.isoformat() if expected_exit_at else None,
            "expectedExitLabel": format_source_datetime(expected_exit_at) if expected_exit_at else "-",
            "remainingSeconds": remaining_seconds,
            "remainingLabel": sunroom_duration_label(remaining_seconds) if remaining_seconds is not None else "-",
            "overstaySeconds": overstay_seconds,
            "overstayLabel": door_duration_label(overstay_seconds) if overstay_seconds else "",
        }

    def sunroom_bed_status_payload(row: Optional[Sun2Bed], now: datetime) -> Dict[str, Any]:
        max_age_minutes = dependencies.SUNROOM_BED_STATUS_MAX_AGE_MINUTES
        if row is None:
            return {
                "enabled": None,
                "fresh": False,
                "status": None,
                "statusCode": None,
                "importedAt": None,
                "importedLabel": "-",
                "ageMinutes": None,
            }

        status = str(row.status or "").strip()
        status_code = str(row.status_code or "").strip().lower()
        normalized_status = status.casefold()
        if status_code in {"0", "false", "off", "disabled", "inactive"} or normalized_status in {
            "av",
            "slått av",
            "deaktivert",
            "stengt",
            "ute av drift",
        }:
            enabled: Optional[bool] = False
        elif status_code in {"1", "true", "on", "enabled", "active"} or normalized_status in {
            "på",
            "aktiv",
            "i drift",
        }:
            enabled = True
        else:
            enabled = None

        imported_at = utc_naive_to_local_naive(row.imported_at)
        age_minutes = max(0, int((now - imported_at).total_seconds() // 60)) if imported_at else None
        return {
            "enabled": enabled,
            "fresh": bool(age_minutes is not None and age_minutes <= max_age_minutes),
            "status": status or None,
            "statusCode": str(row.status_code or "").strip() or None,
            "importedAt": imported_at.isoformat() if imported_at else None,
            "importedLabel": format_source_datetime(imported_at) if imported_at else "-",
            "ageMinutes": age_minutes,
        }

    async def sunroom_bed_statuses_by_id(
        session,
        bed_ids: list[str],
        now: datetime,
    ) -> Dict[str, Dict[str, Any]]:
        normalized_ids = sorted({str(bed_id) for bed_id in bed_ids if bed_id})
        if not normalized_ids:
            return {}
        rows = (
            await session.execute(select(Sun2Bed).where(Sun2Bed.sun2_bed_id.in_(normalized_ids)))
        ).scalars().all()
        return {
            str(row.sun2_bed_id): sunroom_bed_status_payload(row, now)
            for row in rows
        }

    def apply_sunroom_bed_status_to_active_periods(
        periods: list[Dict[str, Any]],
        bed_status: Optional[Dict[str, Any]],
    ) -> list[Dict[str, Any]]:
        if not bed_status or bed_status.get("enabled") is not False:
            return periods
        for period in periods:
            if not period.get("isActive"):
                continue
            period.update(
                {
                    "severity": "disabled",
                    "status": "Stengt",
                    "detail": "Sengen er slått av i Sun2. Den lukkede døren er ikke et avvik.",
                    "missingSession": False,
                    "remainingSeconds": None,
                    "remainingLabel": "-",
                    "overstaySeconds": None,
                    "overstayLabel": "",
                }
            )
        return periods

    def sunroom_status_item(
        config: Dict[str, Any],
        latest_row: Optional[DoorEvent],
        sessions_by_room: Dict[str, list[Sun2TanningSession]],
        now: datetime,
        bed_status: Optional[Dict[str, Any]] = None,
        sensor_status: Optional[DoorSensorStatus] = None,
    ) -> Dict[str, Any]:
        SUNROOM_DOOR_ALERT_AFTER_END_MINUTES = dependencies.SUNROOM_DOOR_ALERT_AFTER_END_MINUTES
        SUNROOM_DOOR_CRITICAL_MINUTES = dependencies.SUNROOM_DOOR_CRITICAL_MINUTES
        SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES = dependencies.SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES
        SUNROOM_DOOR_SESSION_GRACE_MINUTES = dependencies.SUNROOM_DOOR_SESSION_GRACE_MINUTES
        SUNROOM_DOOR_WARN_AFTER_END_MINUTES = dependencies.SUNROOM_DOOR_WARN_AFTER_END_MINUTES
        door = door_status_payload(config, latest_row, now, sensor_status=sensor_status)
        identity = sunroom_identity_for_config(config)
        display_number = identity.get("display_room_number") or sunroom_display_number(config)
        room_id = sunroom_room_id_for_config(config)
        bed_id = sunroom_bed_id_for_config(config)
        sessions = sessions_by_room.get(room_id or "", [])
        door_state = door.get("state")
        is_occupied = door_state == "closed"
        changed_at = (
            normalize_local_naive(sensor_status.last_changed_at)
            if sensor_status and sensor_status.last_changed_at
            else normalize_local_naive(latest_row.timestamp) if latest_row else None
        )
        closed_since = changed_at if is_occupied else None
        occupied_seconds = int((now - closed_since).total_seconds()) if closed_since else None
        matched_session = sunroom_best_session_for_door(sessions, is_occupied, changed_at, now)
        expected_exit_at = sunroom_expected_exit_at(matched_session) if matched_session else None

        severity = "free"
        status = "Ledig"
        detail = "Døren er åpen."
        overstay_seconds: Optional[int] = None
        remaining_seconds: Optional[int] = None
        missing_session = False
        no_session_alarm_active = False
        no_session_alarm_threshold_seconds = int(SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES * 60)
        no_session_critical_active = False
        alarm_stage: Optional[str] = None
        bed_enabled = bed_status.get("enabled") if bed_status is not None else None
        bed_status_fresh = bool(bed_status.get("fresh")) if bed_status is not None else True
        alarm_eligible = bed_enabled is not False and bed_status_fresh

        if not door.get("isConfigured"):
            severity = "unknown"
            status = "Ikke koblet"
            detail = "Sensor mangler HC3-id."
        elif door_state == "unknown":
            severity = "unknown"
            status = "Ukjent"
            detail = "Ingen sikker dørstatus."
        elif is_occupied:
            if not matched_session:
                missing_session = bool(occupied_seconds is not None and occupied_seconds >= int(SUNROOM_DOOR_SESSION_GRACE_MINUTES * 60))
                no_session_alarm_active = bool(
                    missing_session and occupied_seconds is not None and occupied_seconds >= no_session_alarm_threshold_seconds
                )
                no_session_critical_active = bool(
                    no_session_alarm_active
                    and occupied_seconds is not None
                    and occupied_seconds >= int(SUNROOM_DOOR_CRITICAL_MINUTES * 60)
                )
                if missing_session:
                    severity = "alert" if no_session_alarm_active else "warning"
                    status = "Kritisk alarm" if no_session_critical_active else "Alarm" if no_session_alarm_active else "Mangler soltime"
                    if no_session_critical_active:
                        detail = f"Dør lukket i mer enn {SUNROOM_DOOR_CRITICAL_MINUTES:g} min uten funnet Sun2-time."
                    elif no_session_alarm_active:
                        detail = f"Dør lukket i mer enn {SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES:g} min uten funnet Sun2-time."
                    else:
                        detail = f"Dør lukket i mer enn {SUNROOM_DOOR_SESSION_GRACE_MINUTES:g} min uten funnet Sun2-time."
                else:
                    severity = "waiting"
                    status = "Venter på soltime"
                    detail = f"Avventer Sun2-data inntil {SUNROOM_DOOR_SESSION_GRACE_MINUTES:g} min etter at døren ble lukket."
            elif expected_exit_at:
                remaining_seconds = int((expected_exit_at - now).total_seconds())
                overstay_seconds = max(0, -remaining_seconds)
                session_end_at = sunroom_session_end_at(matched_session)
                alert_seconds = int((now - session_end_at).total_seconds()) if session_end_at else overstay_seconds
                if alert_seconds >= int(SUNROOM_DOOR_ALERT_AFTER_END_MINUTES * 60):
                    severity = "alert"
                    status = "Overtid"
                    detail = f"Kunden er fortsatt inne mer enn {SUNROOM_DOOR_ALERT_AFTER_END_MINUTES:g} min etter solslutt."
                elif alert_seconds >= int(SUNROOM_DOOR_WARN_AFTER_END_MINUTES * 60):
                    severity = "warning"
                    status = "Overtid"
                    detail = f"Kunden er fortsatt inne mer enn {SUNROOM_DOOR_WARN_AFTER_END_MINUTES:g} min etter solslutt."
                else:
                    severity = "active"
                    status = "I bruk"
                    detail = "Soltime funnet. Forventet ut-tid er beregnet fra betaling + oppstart + soltid + normal utgangstid."
            else:
                severity = "active"
                status = "I bruk"
                detail = "Soltime funnet, men sluttid mangler."

        if bed_status is not None and bed_enabled is False:
            severity = "disabled"
            status = "Stengt"
            detail = "Sengen er slått av i Sun2. Døralarm er deaktivert."
            missing_session = False
            no_session_alarm_active = False
            no_session_critical_active = False
            overstay_seconds = None
            remaining_seconds = None
        elif bed_status is not None and not bed_status_fresh and is_occupied and (
            missing_session or severity == "alert"
        ):
            severity = "waiting"
            status = "Kontrollerer sengestatus"
            detail = "Sengestatusen fra Sun2 er utdatert. Døralarm holdes tilbake til statusen er oppdatert."
            missing_session = False
            no_session_alarm_active = False
            no_session_critical_active = False

        alarm_reason = None
        alarm_title = ""
        if no_session_alarm_active:
            alarm_reason = "closed_without_session"
            alarm_title = "Lukket uten soltime"
            alarm_stage = "critical" if no_session_critical_active else "standard"
        elif severity == "alert" and is_occupied and matched_session:
            alarm_reason = "overstay"
            alarm_title = "Overtid etter solslutt"
            alarm_stage = "standard"

        return {
            "deviceId": door.get("deviceId"),
            "deviceKey": door.get("deviceKey"),
            "title": door.get("title"),
            "sectionKey": door.get("sectionKey"),
            "sectionTitle": door.get("sectionTitle"),
            "sortOrder": door.get("sortOrder"),
            "displayRoomNumber": display_number,
            "physicalRoomNumber": identity.get("physical_room_number"),
            "sun2BedId": bed_id,
            "roomId": room_id,
            "roomLabel": door.get("title") or sun2_room_label(room_id, None),
            "doorState": door_state,
            "doorStateLabel": door.get("stateLabel"),
            "doorChangedAt": changed_at.isoformat() if changed_at else None,
            "doorChangedLabel": format_source_datetime(changed_at) if changed_at else "-",
            "doorAgeLabel": door.get("ageLabel"),
            "doorUpdatedAt": door.get("lastUpdatedAt"),
            "doorUpdatedLabel": door.get("lastUpdatedLabel"),
            "doorUpdatedAgeLabel": door.get("lastUpdatedAgeLabel"),
            "batteryLevel": door.get("batteryLevel"),
            "batteryLabel": door.get("batteryLabel"),
            "isOccupied": is_occupied,
            "alarmEligible": alarm_eligible,
            "bedEnabled": bed_enabled,
            "bedStatusFresh": bed_status_fresh,
            "bedStatus": bed_status.get("status") if bed_status is not None else None,
            "bedStatusCode": bed_status.get("statusCode") if bed_status is not None else None,
            "bedStatusImportedAt": bed_status.get("importedAt") if bed_status is not None else None,
            "bedStatusImportedLabel": bed_status.get("importedLabel") if bed_status is not None else "-",
            "bedStatusAgeMinutes": bed_status.get("ageMinutes") if bed_status is not None else None,
            "occupiedSince": closed_since.isoformat() if closed_since else None,
            "occupiedSinceLabel": format_source_datetime(closed_since) if closed_since else "-",
            "occupiedDurationSeconds": occupied_seconds,
            "occupiedDurationLabel": door_duration_label(occupied_seconds),
            "severity": severity,
            "status": status,
            "detail": detail,
            "missingSession": missing_session,
            "noSessionAlarmActive": no_session_alarm_active,
            "noSessionCriticalActive": no_session_critical_active,
            "noSessionAlarmMinutes": SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES,
            "noSessionCriticalMinutes": SUNROOM_DOOR_CRITICAL_MINUTES,
            "alarmReason": alarm_reason,
            "alarmTitle": alarm_title,
            "alarmStage": alarm_stage,
            "session": sunroom_session_payload(matched_session) if matched_session else None,
            "expectedExitAt": expected_exit_at.isoformat() if expected_exit_at else None,
            "expectedExitLabel": format_source_datetime(expected_exit_at) if expected_exit_at else "-",
            "remainingSeconds": remaining_seconds,
            "remainingLabel": sunroom_duration_label(remaining_seconds) if remaining_seconds is not None else "-",
            "overstaySeconds": overstay_seconds,
            "overstayLabel": door_duration_label(overstay_seconds) if overstay_seconds else "",
        }

    def sunroom_alarm_event_key(item: Dict[str, Any]) -> str:
        session_item = item.get("session") or {}
        identity = "|".join(
            (
                str(item.get("deviceKey") or item.get("roomId") or "unknown"),
                str(item.get("alarmReason") or "overstay"),
                str(item.get("doorChangedAt") or ""),
                str(session_item.get("sourceSessionId") or session_item.get("id") or "missing"),
            )
        )
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    def sunroom_alert_key(item: Dict[str, Any]) -> str:
        return sunroom_alarm_event_key(item)

    def sunroom_alarm_detected_at(item: Dict[str, Any], now: datetime) -> datetime:
        SUNROOM_DOOR_ALERT_AFTER_END_MINUTES = dependencies.SUNROOM_DOOR_ALERT_AFTER_END_MINUTES
        SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES = dependencies.SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES
        reason = item.get("alarmReason") or "overstay"
        if reason == "closed_without_session":
            changed_at = sunroom_parse_time_value(item.get("doorChangedAt"))
            if changed_at:
                return changed_at + timedelta(
                    minutes=float(item.get("alarmThresholdMinutes") or SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES)
                )
        session_item = item.get("session") or {}
        ended_at = sunroom_parse_time_value(session_item.get("endedAt"))
        if ended_at:
            return ended_at + timedelta(minutes=SUNROOM_DOOR_ALERT_AFTER_END_MINUTES)
        return now

    def sunroom_alarm_message(item: Dict[str, Any], checked_at: Optional[datetime] = None) -> str:
        if item.get("noSessionAlarmActive"):
            suffix = f" Kontrollert {checked_at.strftime('%H:%M:%S')}." if checked_at else ""
            verification_suffix = ""
            if item.get("sun2VerificationFailed"):
                verification_suffix = " Sun2 kunne ikke bekrefte dagens data."
            if item.get("hc3VerificationFailed"):
                verification_suffix += " HC3-status kunne ikke bekreftes."
            return (
                f"{item.get('title') or item.get('roomLabel')}: dør lukket i "
                f"{item.get('occupiedDurationLabel') or '-'} uten funnet Sun2-time. "
                f"Lukket siden {item.get('occupiedSinceLabel') or '-'}.{verification_suffix}{suffix}"
            )
        return (
            f"{item.get('title') or item.get('roomLabel')}: dør fortsatt lukket. "
            f"Forventet ut {item.get('expectedExitLabel') or '-'}. "
            f"Overtid {item.get('overstayLabel') or '-'}."
        )

    def sunroom_door_period_key(item: Dict[str, Any]) -> str:
        return "|".join(
            (
                str(item.get("deviceKey") or item.get("roomId") or "unknown"),
                str(item.get("doorChangedAt") or "unknown"),
            )
        )

    def sunroom_item_may_have_new_session(item: Dict[str, Any]) -> bool:
        SUNROOM_DOOR_PAYMENT_DELAY_MINUTES = dependencies.SUNROOM_DOOR_PAYMENT_DELAY_MINUTES
        session_item = item.get("session") or {}
        door_changed_at = sunroom_parse_time_value(item.get("doorChangedAt"))
        payment_at = sunroom_parse_time_value(session_item.get("startedAt"))
        if not door_changed_at or not payment_at:
            return False
        return payment_at < door_changed_at - timedelta(minutes=SUNROOM_DOOR_PAYMENT_DELAY_MINUTES + 2)

    def sunroom_force_sync_candidates(items: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        SUNROOM_DOOR_FORCED_SYNC_MINUTES = dependencies.SUNROOM_DOOR_FORCED_SYNC_MINUTES
        threshold_seconds = int(SUNROOM_DOOR_FORCED_SYNC_MINUTES * 60)
        return [
            item
            for item in items
            if item.get("isOccupied")
            and item.get("bedEnabled") is not False
            and (
                not item.get("session")
                or item.get("alarmReason") == "overstay"
                or sunroom_item_may_have_new_session(item)
            )
            and int(item.get("occupiedDurationSeconds") or 0) >= threshold_seconds
            and item.get("doorChangedAt")
        ]

    def cleanup_sunroom_door_verifications(now: datetime) -> None:
        SUNROOM_DOOR_SESSION_LOOKBACK_HOURS = dependencies.SUNROOM_DOOR_SESSION_LOOKBACK_HOURS
        sunroom_door_verifications = dependencies.sunroom_door_verifications
        cutoff = now - timedelta(hours=max(24, SUNROOM_DOOR_SESSION_LOOKBACK_HOURS * 2))
        for key, state in list(sunroom_door_verifications.items()):
            attempted_at = state.get("attemptedAt")
            if not isinstance(attempted_at, datetime) or attempted_at < cutoff:
                sunroom_door_verifications.pop(key, None)

    def sunroom_sync_candidate_is_due(item: Dict[str, Any], now: datetime) -> bool:
        SUNROOM_DOOR_SYNC_MAX_ATTEMPTS = dependencies.SUNROOM_DOOR_SYNC_MAX_ATTEMPTS
        SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS = dependencies.SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS
        sunroom_door_verifications = dependencies.sunroom_door_verifications
        state = sunroom_door_verifications.get(sunroom_door_period_key(item)) or {}
        attempted_at = state.get("attemptedAt")
        attempt_count = int(state.get("attemptCount") or 0)
        retry_before = now - timedelta(seconds=SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS)
        return attempt_count < SUNROOM_DOOR_SYNC_MAX_ATTEMPTS and (
            not isinstance(attempted_at, datetime) or attempted_at <= retry_before
        )

    def apply_sunroom_alarm_verification(
        items: list[Dict[str, Any]],
        now: datetime,
        persisted_alarm_keys: Optional[set[str]] = None,
    ) -> list[Dict[str, Any]]:
        SUNROOM_DOOR_CRITICAL_MINUTES = dependencies.SUNROOM_DOOR_CRITICAL_MINUTES
        SUNROOM_DOOR_NEW_SESSION_GRACE_MINUTES = dependencies.SUNROOM_DOOR_NEW_SESSION_GRACE_MINUTES
        SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES = dependencies.SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES
        SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES = dependencies.SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES
        sunroom_door_verifications = dependencies.sunroom_door_verifications
        verified_items: list[Dict[str, Any]] = []
        persisted_alarm_keys = persisted_alarm_keys or set()
        failure_threshold_seconds = int(SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES * 60)
        new_session_grace_seconds = int(SUNROOM_DOOR_NEW_SESSION_GRACE_MINUTES * 60)
        for source_item in items:
            item = dict(source_item)
            if not item.get("isOccupied") or item.get("alarmEligible") is False:
                verified_items.append(item)
                continue
            state = sunroom_door_verifications.get(sunroom_door_period_key(item)) or {}
            attempted_at = state.get("attemptedAt")
            if isinstance(attempted_at, datetime):
                item["sun2VerificationAt"] = attempted_at.isoformat()
                item["sun2VerificationOk"] = bool(state.get("ok"))
                item["sun2VerificationError"] = state.get("error") or None
                item["sun2VerificationAttemptCount"] = int(state.get("attemptCount") or 0)
                item["sun2VerificationReason"] = state.get("reason") or None

            if item.get("session"):
                if item.get("alarmReason") != "overstay":
                    verified_items.append(item)
                    continue

                occupied_seconds = int(item.get("occupiedDurationSeconds") or 0)
                changed_at = sunroom_parse_time_value(item.get("doorChangedAt"))
                verification_ready_at = (
                    changed_at + timedelta(minutes=SUNROOM_DOOR_NEW_SESSION_GRACE_MINUTES)
                    if changed_at
                    else None
                )
                persisted_alarm = sunroom_alarm_event_key(item) in persisted_alarm_keys
                sync_succeeded_after_grace = bool(
                    state.get("ok")
                    and isinstance(attempted_at, datetime)
                    and verification_ready_at
                    and attempted_at >= verification_ready_at
                )
                sync_failed_long_enough = bool(
                    state
                    and not state.get("ok")
                    and occupied_seconds >= failure_threshold_seconds
                )
                is_critical = occupied_seconds >= int(SUNROOM_DOOR_CRITICAL_MINUTES * 60)
                if persisted_alarm or sync_succeeded_after_grace:
                    item["newSessionCheckActive"] = False
                elif sync_failed_long_enough or is_critical:
                    item["sun2VerificationFailed"] = True
                    item["newSessionCheckActive"] = False
                    item["detail"] = (
                        "Forrige soltime er avsluttet, døren er fortsatt lukket og en mulig ny time "
                        "kunne ikke bekreftes mot oppdaterte Sun2-data."
                    )
                else:
                    item.update(
                        {
                            "severity": "waiting" if occupied_seconds < new_session_grace_seconds else "warning",
                            "status": "Kontrollerer ny time",
                            "detail": (
                                "Forrige soltime er avsluttet. Avventer en ny Sun2-kontroll etter "
                                f"{SUNROOM_DOOR_NEW_SESSION_GRACE_MINUTES:g} min før overtid kan varsles."
                            ),
                            "alarmReason": None,
                            "alarmTitle": "",
                            "alarmStage": None,
                            "newSessionCheckActive": True,
                        }
                    )
                verified_items.append(item)
                continue

            if not item.get("noSessionAlarmActive"):
                verified_items.append(item)
                continue

            occupied_seconds = int(item.get("occupiedDurationSeconds") or 0)
            is_critical = bool(item.get("noSessionCriticalActive"))
            persisted_alarm = sunroom_alarm_event_key(item) in persisted_alarm_keys
            sync_succeeded = bool(state.get("ok")) or persisted_alarm
            sync_failed_long_enough = bool(state and not state.get("ok") and occupied_seconds >= failure_threshold_seconds)
            if sync_succeeded:
                item["alarmThresholdMinutes"] = SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES
            elif sync_failed_long_enough or is_critical:
                item["sun2VerificationFailed"] = True
                item["alarmThresholdMinutes"] = (
                    SUNROOM_DOOR_CRITICAL_MINUTES if is_critical and not state else SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES
                )
                item["detail"] = (
                    f"Dør lukket i {item.get('occupiedDurationLabel') or '-'} uten funnet soltime. "
                    "Tvungen Sun2-kontroll feilet."
                )
            else:
                item.update(
                    {
                        "severity": "warning",
                        "status": "Kontrollerer Sun2",
                        "detail": "Avventer tvungen kontroll av dagens Sun2-data før varsel sendes.",
                        "noSessionAlarmActive": False,
                        "alarmReason": None,
                        "alarmTitle": "",
                        "alarmStage": None,
                    }
                )
            verified_items.append(item)
        return verified_items

    async def verify_sunroom_alert_doors_with_hc3(items: list[Dict[str, Any]]) -> Dict[str, Any]:
        DOOR_SENSOR_CONFIG = dependencies.DOOR_SENSOR_CONFIG
        candidate_ids = {
            int(item["deviceId"])
            for item in items
            if item.get("severity") == "alert" and item.get("isOccupied") and item.get("deviceId") is not None
        }
        configs = [
            config
            for config in DOOR_SENSOR_CONFIG
            if config.get("device_id") is not None and int(config["device_id"]) in candidate_ids
        ]
        if not configs:
            return {"ok": False, "checked": 0, "errors": 1, "message": "Ingen HC3-sensorer kunne kontrolleres."}
        reasons = {int(config["device_id"]): "sunroom_alarm_confirmation" for config in configs}
        return await run_hc3_door_poll_once(
            reason="sunroom_alarm_confirmation",
            configs=configs,
            target_reasons=reasons,
        )

    async def sync_sunroom_alarm_history(session, items: list[Dict[str, Any]], now: datetime) -> Dict[str, AlarmEvent]:
        active_items = [
            item
            for item in items
            if item.get("severity") == "alert" and item.get("isOccupied") and item.get("alarmReason")
        ]
        active_by_key = {sunroom_alarm_event_key(item): item for item in active_items}
        where_clause = and_(AlarmEvent.domain == "doors", AlarmEvent.status == "active")
        if active_by_key:
            where_clause = and_(
                AlarmEvent.domain == "doors",
                or_(AlarmEvent.status == "active", AlarmEvent.event_key.in_(list(active_by_key))),
            )
        existing_rows = (await session.execute(select(AlarmEvent).where(where_clause))).scalars().all()
        existing_by_key = {row.event_key: row for row in existing_rows}
        current_by_device = {str(item.get("deviceKey") or ""): item for item in items}

        for event_key, item in active_by_key.items():
            alarm = existing_by_key.get(event_key)
            session_item = item.get("session") or {}
            notification_stages: list[str] = []
            if alarm is not None and isinstance(alarm.raw, dict):
                notification_stages = [
                    str(stage)
                    for stage in alarm.raw.get("_notificationStages") or []
                    if str(stage) in {"standard", "critical"}
                ]
            if alarm is None:
                alarm = AlarmEvent(
                    event_key=event_key,
                    domain="doors",
                    alarm_type=str(item.get("alarmReason") or "overstay"),
                    status="active",
                    severity="alert",
                    outcome="unreviewed",
                    title=str(item.get("title") or item.get("roomLabel") or "Solromalarm"),
                    detected_at=sunroom_alarm_detected_at(item, now),
                    created_at=now,
                    source="sunroom_door_monitor",
                )
                session.add(alarm)
                existing_by_key[event_key] = alarm
            alarm.status = "active"
            alarm.severity = str(item.get("severity") or "alert")
            alarm.detail = str(item.get("detail") or sunroom_alarm_message(item))
            alarm.device_key = item.get("deviceKey")
            alarm.device_id = item.get("deviceId")
            alarm.room_id = item.get("roomId")
            alarm.display_room_number = item.get("displayRoomNumber")
            alarm.physical_room_number = item.get("physicalRoomNumber")
            alarm.sun2_bed_id = item.get("sun2BedId")
            alarm.source_session_id = session_item.get("sourceSessionId")
            alarm.door_changed_at = sunroom_parse_time_value(item.get("doorChangedAt"))
            alarm.expected_exit_at = sunroom_parse_time_value(item.get("expectedExitAt"))
            alarm.last_observed_at = now
            alarm.resolved_at = None
            alarm.resolution_reason = None
            alarm.updated_at = now
            alarm.raw = {**item, "_notificationStages": notification_stages}

        for alarm in existing_rows:
            if alarm.status != "active" or alarm.event_key in active_by_key:
                continue
            current = current_by_device.get(str(alarm.device_key or "")) or {}
            alarm.status = "resolved"
            alarm.resolved_at = now
            if current.get("doorState") == "open":
                alarm.resolution_reason = "door_opened"
            elif current.get("bedEnabled") is False:
                alarm.resolution_reason = "bed_disabled"
            elif current.get("session"):
                alarm.resolution_reason = "session_found"
            else:
                alarm.resolution_reason = "condition_cleared"
            if alarm.notification_status == "pending":
                alarm.notification_status = "not_sent"
            alarm.last_observed_at = now
            alarm.updated_at = now

        await session.flush()
        return existing_by_key

    async def publish_sunroom_door_alerts(items: list[Dict[str, Any]], now: datetime, session=None) -> int:
        ALARM_APP_URL = dependencies.ALARM_APP_URL
        logger = dependencies.logger
        sent_count = 0
        candidates = [
            item
            for item in items
            if item.get("severity") == "alert" and item.get("isOccupied") and item.get("alarmReason")
        ]
        persisted_by_key: Dict[str, AlarmEvent] = {}
        if session is not None and candidates:
            keys = [sunroom_alarm_event_key(item) for item in candidates]
            rows = (await session.execute(select(AlarmEvent).where(AlarmEvent.event_key.in_(keys)))).scalars().all()
            persisted_by_key = {row.event_key: row for row in rows}

        for item in candidates:
            key = sunroom_alert_key(item)
            persisted = persisted_by_key.get(key)
            alarm_stage = str(item.get("alarmStage") or "standard")
            queued_stages: list[str] = []
            if persisted is not None and isinstance(persisted.raw, dict):
                queued_stages = [str(stage) for stage in persisted.raw.get("_notificationStages") or []]
            notification_count = int(persisted.notification_count or 0) if persisted is not None else 0
            if alarm_stage in queued_stages:
                continue
            if alarm_stage == "standard" and notification_count >= 1:
                continue
            if alarm_stage == "critical" and notification_count >= 2:
                continue
            if persisted is not None and persisted.notification_status == "queued":
                continue
            if item.get("noSessionAlarmActive"):
                message = sunroom_alarm_message(item, now)
                if alarm_stage == "critical":
                    title = "SUN2 kritisk alarm: lukket uten soltime"
                    tags = "door,rotating_light"
                    priority = "5"
                else:
                    title = "SUN2 alarm: lukket uten soltime"
                    tags = "door,warning"
                    priority = "4"
            else:
                message = sunroom_alarm_message(item, now)
                title = "SUN2 dørvarsel"
                tags = "door,rotating_light"
                priority = "4"
            click_url = f"{ALARM_APP_URL}/?section=dorer"
            if persisted is not None and persisted.id:
                click_url = f"{click_url}&alarm={persisted.id}"
            sent = await publish_door_ntfy(
                title,
                message,
                priority=priority,
                tags=tags,
                click_url=click_url,
                related_type="alarm_event" if persisted is not None else "",
                related_id=persisted.id if persisted is not None else None,
                session=session,
            )
            if sent:
                sent_count += 1
                logger.warning(
                    "Sunroom door alert lagt i ko: room=%s bed=%s reason=%s door_changed=%s checked=%s",
                    item.get("roomId"),
                    item.get("sun2BedId"),
                    item.get("alarmReason") or "overstay",
                    item.get("doorChangedAt"),
                    now.isoformat(),
                )
            if persisted is not None:
                persisted.notification_status = "queued" if sent else "failed"
                if sent:
                    persisted.raw = {
                        **(persisted.raw if isinstance(persisted.raw, dict) else item),
                        "_notificationStages": [*queued_stages, alarm_stage],
                    }
                persisted.updated_at = now
        if session is not None:
            await session.flush()
        return sent_count

    async def sunroom_door_session_payload(session, notify: bool = False) -> Dict[str, Any]:
        DOOR_SENSOR_CONFIG = dependencies.DOOR_SENSOR_CONFIG
        NTFY_DOORS_TOPIC = dependencies.NTFY_DOORS_TOPIC
        SUNROOM_DOOR_ALERT_AFTER_END_MINUTES = dependencies.SUNROOM_DOOR_ALERT_AFTER_END_MINUTES
        SUNROOM_DOOR_CRITICAL_MINUTES = dependencies.SUNROOM_DOOR_CRITICAL_MINUTES
        SUNROOM_DOOR_EXIT_GRACE_MINUTES = dependencies.SUNROOM_DOOR_EXIT_GRACE_MINUTES
        SUNROOM_DOOR_FAN_AFTER_RUN_MINUTES = dependencies.SUNROOM_DOOR_FAN_AFTER_RUN_MINUTES
        SUNROOM_DOOR_FORCED_SYNC_MINUTES = dependencies.SUNROOM_DOOR_FORCED_SYNC_MINUTES
        SUNROOM_DOOR_MONITOR_INTERVAL_SECONDS = dependencies.SUNROOM_DOOR_MONITOR_INTERVAL_SECONDS
        SUNROOM_DOOR_NEW_SESSION_GRACE_MINUTES = dependencies.SUNROOM_DOOR_NEW_SESSION_GRACE_MINUTES
        SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES = dependencies.SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES
        SUNROOM_DOOR_PAYMENT_DELAY_MINUTES = dependencies.SUNROOM_DOOR_PAYMENT_DELAY_MINUTES
        SUNROOM_DOOR_SESSION_GRACE_MINUTES = dependencies.SUNROOM_DOOR_SESSION_GRACE_MINUTES
        SUNROOM_DOOR_SESSION_LOOKBACK_HOURS = dependencies.SUNROOM_DOOR_SESSION_LOOKBACK_HOURS
        SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES = dependencies.SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES
        SUNROOM_DOOR_SYNC_MAX_ATTEMPTS = dependencies.SUNROOM_DOOR_SYNC_MAX_ATTEMPTS
        SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS = dependencies.SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS
        SUNROOM_DOOR_WARN_AFTER_END_MINUTES = dependencies.SUNROOM_DOOR_WARN_AFTER_END_MINUTES
        ntfy_subscribe_url = dependencies.ntfy_subscribe_url
        ntfy_topic_url = dependencies.ntfy_topic_url
        now = local_now_naive()
        solroom_configs = [config for config in DOOR_SENSOR_CONFIG if config.get("group_key") == "solrom"]
        solroom_device_ids = [int(config["device_id"]) for config in solroom_configs if config.get("device_id") is not None]
        raw_limit = max(len(solroom_device_ids) * 180, 1000)
        raw_rows: list[DoorEvent] = []
        if solroom_device_ids:
            result = await session.execute(
                select(DoorEvent)
                .where(DoorEvent.device_id.in_(solroom_device_ids))
                .order_by(DoorEvent.timestamp.desc(), DoorEvent.id.desc())
                .limit(raw_limit)
            )
            raw_rows = result.scalars().all()
        sensor_status_rows = (
            await session.execute(
                select(DoorSensorStatus).where(DoorSensorStatus.device_id.in_(solroom_device_ids))
            )
        ).scalars().all() if solroom_device_ids else []
        sensor_status_by_device = {int(row.device_id): row for row in sensor_status_rows}
        change_rows_ascending = door_change_rows(list(reversed(raw_rows)))
        latest_change_by_device: Dict[int, DoorEvent] = {}
        for row in reversed(change_rows_ascending):
            if row.device_id is None:
                continue
            latest_change_by_device.setdefault(int(row.device_id), row)

        room_ids = sorted({room_id for room_id in (sunroom_room_id_for_config(config) for config in solroom_configs) if room_id})
        bed_ids = sorted({bed_id for bed_id in (sunroom_bed_id_for_config(config) for config in solroom_configs) if bed_id})
        bed_statuses_by_id = await sunroom_bed_statuses_by_id(session, bed_ids, now)
        sessions_by_room: Dict[str, list[Sun2TanningSession]] = {room_id: [] for room_id in room_ids}
        if room_ids or bed_ids:
            start_cutoff = now - timedelta(hours=SUNROOM_DOOR_SESSION_LOOKBACK_HOURS)
            identity_conditions = []
            if room_ids:
                identity_conditions.append(Sun2TanningSession.room_id.in_(room_ids))
            if bed_ids:
                identity_conditions.append(Sun2TanningSession.sun2_bed_id.in_(bed_ids))
            session_rows = (
                await session.execute(
                    select(Sun2TanningSession)
                    .where(or_(*identity_conditions))
                    .where(Sun2TanningSession.started_at >= start_cutoff)
                    .order_by(Sun2TanningSession.started_at.desc(), Sun2TanningSession.id.desc())
                )
            ).scalars().all()
            for row in session_rows:
                room_id = sunroom_canonical_room_id(row)
                if room_id:
                    sessions_by_room.setdefault(room_id, []).append(row)

        rooms = []
        for config in solroom_configs:
            device_id = config.get("device_id")
            latest_row = latest_change_by_device.get(int(device_id)) if device_id is not None else None
            sensor_status = sensor_status_by_device.get(int(device_id)) if device_id is not None else None
            bed_id = sunroom_bed_id_for_config(config)
            bed_status = bed_statuses_by_id.get(str(bed_id or ""))
            rooms.append(sunroom_status_item(config, latest_row, sessions_by_room, now, bed_status, sensor_status))
        rooms.sort(key=lambda item: (str(item.get("sectionKey") or ""), int(item.get("sortOrder") or 0)))
        candidate_alarm_keys = {
            sunroom_alarm_event_key(item)
            for item in rooms
            if item.get("isOccupied") and item.get("alarmReason")
        }
        persisted_alarm_keys: set[str] = set()
        if candidate_alarm_keys:
            persisted_alarm_keys = set(
                (
                    await session.execute(
                        select(AlarmEvent.event_key)
                        .where(AlarmEvent.event_key.in_(candidate_alarm_keys))
                        .where(AlarmEvent.status == "active")
                    )
                ).scalars().all()
            )
        rooms = apply_sunroom_alarm_verification(rooms, now, persisted_alarm_keys)
        if notify:
            await sync_sunroom_alarm_history(session, rooms, now)
            await publish_sunroom_door_alerts(rooms, now, session=session)
            await session.commit()
        active_rooms = [item for item in rooms if item.get("isOccupied") and item.get("bedEnabled") is not False]
        disabled_rooms = [item for item in rooms if item.get("bedEnabled") is False]
        warning_rooms = [item for item in rooms if item.get("severity") == "warning"]
        alert_rooms = [item for item in rooms if item.get("severity") == "alert"]
        missing_session_rooms = [item for item in rooms if item.get("missingSession")]
        no_session_alarm_rooms = [item for item in rooms if item.get("noSessionAlarmActive")]
        return {
            "generatedAt": now.isoformat(),
            "ntfyDoorsSubscribeUrl": ntfy_subscribe_url(NTFY_DOORS_TOPIC, "SUN2 dørvarsler"),
            "ntfyDoorsWebUrl": ntfy_topic_url(NTFY_DOORS_TOPIC),
            "rules": {
                "paymentDelayMinutes": SUNROOM_DOOR_PAYMENT_DELAY_MINUTES,
                "fanAfterRunMinutes": SUNROOM_DOOR_FAN_AFTER_RUN_MINUTES,
                "exitGraceMinutes": SUNROOM_DOOR_EXIT_GRACE_MINUTES,
                "sessionGraceMinutes": SUNROOM_DOOR_SESSION_GRACE_MINUTES,
                "forcedSyncMinutes": SUNROOM_DOOR_FORCED_SYNC_MINUTES,
                "syncMinIntervalSeconds": SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS,
                "syncMaxAttempts": SUNROOM_DOOR_SYNC_MAX_ATTEMPTS,
                "newSessionGraceMinutes": SUNROOM_DOOR_NEW_SESSION_GRACE_MINUTES,
                "syncStrategy": "door_event_with_fallback",
                "noSessionAlarmMinutes": SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES,
                "syncFailureAlarmMinutes": SUNROOM_DOOR_SYNC_FAILURE_ALARM_MINUTES,
                "criticalMinutes": SUNROOM_DOOR_CRITICAL_MINUTES,
                "warnAfterEndMinutes": SUNROOM_DOOR_WARN_AFTER_END_MINUTES,
                "alertAfterEndMinutes": SUNROOM_DOOR_ALERT_AFTER_END_MINUTES,
                "monitorIntervalSeconds": SUNROOM_DOOR_MONITOR_INTERVAL_SECONDS,
                "bedStatusMaxAgeMinutes": dependencies.SUNROOM_BED_STATUS_MAX_AGE_MINUTES,
            },
            "summary": {
                "rooms": len(rooms),
                "active": len(active_rooms),
                "disabled": len(disabled_rooms),
                "waiting": len([item for item in rooms if item.get("severity") == "waiting"]),
                "warning": len(warning_rooms),
                "alert": len(alert_rooms),
                "missingSession": len(missing_session_rooms),
                "noSessionAlarm": len(no_session_alarm_rooms),
                "ok": len([item for item in rooms if item.get("severity") in {"free", "active", "disabled"}]),
            },
            "rooms": rooms,
        }

    async def sunroom_door_alarm_payload(
        session,
        history_limit: int = 100,
        history_day: Optional[date] = None,
    ) -> Dict[str, Any]:
        alarm_event_payload = dependencies.alarm_event_payload
        payload = await sunroom_door_session_payload(session, notify=False)
        rooms = list(payload.get("rooms") or [])
        alarms = [item for item in rooms if item.get("severity") == "alert" and item.get("isOccupied")]
        watch = [
            item
            for item in rooms
            if item.get("alarmEligible") is not False
            and item.get("missingSession")
            and not item.get("noSessionAlarmActive")
        ]
        occupied_without_session = [
            item
            for item in rooms
            if item.get("alarmEligible") is not False and item.get("isOccupied") and not item.get("session")
        ]
        history_limit = max(10, min(int(history_limit or 100), 500))
        history_stmt = select(AlarmEvent).where(AlarmEvent.domain == "doors")
        if history_day:
            history_start = datetime.combine(history_day, time.min)
            history_end = history_start + timedelta(days=1)
            history_stmt = history_stmt.where(
                or_(
                    and_(AlarmEvent.detected_at >= history_start, AlarmEvent.detected_at < history_end),
                    and_(AlarmEvent.door_changed_at >= history_start, AlarmEvent.door_changed_at < history_end),
                )
            )
        history_rows = (
            await session.execute(
                history_stmt.order_by(AlarmEvent.detected_at.desc(), AlarmEvent.id.desc()).limit(history_limit)
            )
        ).scalars().all()
        payload["alarms"] = alarms
        payload["watch"] = watch
        payload["occupiedWithoutSession"] = occupied_without_session
        payload["history"] = [alarm_event_payload(row) for row in history_rows]
        payload["summary"] = {
            **dict(payload.get("summary") or {}),
            "alarm": len(alarms),
            "watch": len(watch),
            "occupiedWithoutSession": len(occupied_without_session),
            "history": len(history_rows),
            "historyActive": len([row for row in history_rows if row.status == "active"]),
            "historyNotified": len([row for row in history_rows if int(row.notification_count or 0) > 0]),
        }
        return payload

    def sunroom_sync_reason_label(reason: Any) -> str:
        value = str(reason or "").strip()
        if not value:
            return "Planlagt eller manuell kontroll"
        if value == "fallback":
            return "30-minutters sikkerhetsnett"
        if value.startswith("door_closed"):
            rooms = value.partition("rooms=")[2].strip()
            return f"Lukket dør, rom {rooms}" if rooms else "Lukket solromdør"
        labels = {
            "external": "Ekstern eller manuell kontroll",
            "manual": "Manuell kontroll",
            "production_rate_check": "Produksjonskontroll",
            "nightly_current_month": "Nattlig kontroll av måneden",
        }
        return labels.get(value, value.replace("_", " ").strip().capitalize())

    def sunroom_logic_for_room(item: Dict[str, Any], now: datetime) -> Dict[str, Any]:
        SUNROOM_DOOR_FORCED_SYNC_MINUTES = dependencies.SUNROOM_DOOR_FORCED_SYNC_MINUTES
        SUNROOM_DOOR_SYNC_MAX_ATTEMPTS = dependencies.SUNROOM_DOOR_SYNC_MAX_ATTEMPTS
        SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS = dependencies.SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS
        door_changed_at = sunroom_parse_time_value(item.get("doorChangedAt"))
        verification_at = sunroom_parse_time_value(item.get("sun2VerificationAt"))
        attempt_count = int(item.get("sun2VerificationAttemptCount") or 0)
        max_attempts = SUNROOM_DOOR_SYNC_MAX_ATTEMPTS
        next_at: Optional[datetime] = None
        phase = str(item.get("status") or "Ukjent")
        decision = str(item.get("detail") or "Ingen vurdering tilgjengelig.")
        trigger = "Venter på gyldig sensorstatus"
        next_action = "Kontroller sensortilkoblingen."

        if item.get("doorState") == "open":
            phase = "Ledig"
            decision = "Døren er åpen, og det finnes ingen aktiv dørperiode."
            trigger = "Neste lukking av døren"
            next_action = "Starter et nytt kontrollvindu når døren lukkes."
        elif item.get("doorState") == "unknown":
            phase = "Ukjent status"
            decision = "Systemet mangler en sikker dørstatus."
            trigger = "Ny dørhendelse eller HC3-kontroll"
            next_action = "Avventer status fra HC3."
        elif item.get("severity") == "alert":
            phase = "Alarm"
            trigger = "Bekreftet alarmregel"
            next_action = "Varsling er aktiv; alarmen avsluttes når situasjonen normaliseres."
        elif item.get("newSessionCheckActive"):
            phase = "Kontrollerer ny time"
            trigger = "Forrige soltime er avsluttet, men døren er fortsatt lukket"
            next_action = "Henter SUN2 på nytt før overtid kan varsles."
        elif item.get("session"):
            phase = "Soltime verifisert"
            trigger = "Soltime matchet mot rom og dørperiode"
            next_action = (
                f"Følger forventet ut-tid {item.get('expectedExitLabel') or '-'}; "
                "varsler først ved reell overtid."
            )
            next_at = sunroom_parse_time_value(item.get("expectedExitAt"))
        elif item.get("isOccupied"):
            elapsed_seconds = int(item.get("occupiedDurationSeconds") or 0)
            forced_after_seconds = int(SUNROOM_DOOR_FORCED_SYNC_MINUTES * 60)
            phase = "Klargjøring" if elapsed_seconds < forced_after_seconds else "Kontrollerer betaling"
            decision = (
                "Døren er lukket uten en matchet soltime. Betalingen kan fortsatt mangle i siste "
                "nedlasting."
            )
            trigger = f"Dør lukket i minst {SUNROOM_DOOR_FORCED_SYNC_MINUTES:g} min"
            if attempt_count >= max_attempts:
                next_action = "Maksimalt antall automatiske SUN2-kontroller er brukt for denne dørperioden."
            else:
                next_at = (
                    verification_at + timedelta(seconds=SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS)
                    if verification_at
                    else door_changed_at + timedelta(seconds=forced_after_seconds)
                    if door_changed_at
                    else now
                )
                if next_at < now:
                    next_at = now
                next_action = (
                    f"SUN2-kontroll {attempt_count + 1} av {max_attempts} kan kjøres "
                    f"{format_source_time(next_at)}."
                )

        verification_ok = item.get("sun2VerificationOk") if verification_at else None
        return {
            "roomId": item.get("roomId"),
            "title": item.get("title") or item.get("roomLabel"),
            "sectionTitle": item.get("sectionTitle"),
            "sortOrder": item.get("sortOrder"),
            "doorState": item.get("doorState"),
            "doorStateLabel": item.get("doorStateLabel"),
            "doorAgeLabel": item.get("doorAgeLabel"),
            "doorChangedAt": api_local_iso(door_changed_at),
            "doorUpdatedAt": item.get("doorUpdatedAt"),
            "doorUpdatedLabel": item.get("doorUpdatedLabel"),
            "doorUpdatedAgeLabel": item.get("doorUpdatedAgeLabel"),
            "batteryLevel": item.get("batteryLevel"),
            "batteryLabel": item.get("batteryLabel"),
            "severity": item.get("severity"),
            "phase": phase,
            "decision": decision,
            "trigger": trigger,
            "nextAction": next_action,
            "nextAt": api_local_iso(next_at),
            "attemptCount": attempt_count,
            "maxAttempts": max_attempts,
            "lastVerificationAt": api_local_iso(verification_at),
            "lastVerificationOk": verification_ok,
            "lastVerificationError": item.get("sun2VerificationError"),
            "verificationReason": sunroom_sync_reason_label(item.get("sun2VerificationReason")),
            "session": item.get("session"),
            "expectedExitAt": item.get("expectedExitAt"),
            "expectedExitLabel": item.get("expectedExitLabel"),
        }

    def sunroom_logic_event(
        event_id: str,
        timestamp: Optional[datetime],
        *,
        kind: str,
        kind_label: str,
        room_id: Optional[str],
        room_label: str,
        event: str,
        logic: str,
        action: str,
        result: str,
        tone: str,
    ) -> Dict[str, Any]:
        normalized = normalize_local_naive(timestamp)
        return {
            "id": event_id,
            "timestamp": api_local_iso(normalized),
            "timeLabel": format_source_datetime(normalized),
            "kind": kind,
            "kindLabel": kind_label,
            "roomId": room_id,
            "roomLabel": room_label,
            "event": event,
            "logic": logic,
            "action": action,
            "result": result,
            "tone": tone,
            "_sortAt": normalized or datetime.min,
        }

    async def sunroom_logic_payload(session, hours: int = 12, limit: int = 180) -> Dict[str, Any]:
        DOOR_SENSOR_CONFIG = dependencies.DOOR_SENSOR_CONFIG
        SUNROOM_DOOR_FORCED_SYNC_MINUTES = dependencies.SUNROOM_DOOR_FORCED_SYNC_MINUTES
        SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS = dependencies.SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS
        fetch_sun2_scraper_runtime = dependencies.fetch_sun2_scraper_runtime
        now = local_now_naive()
        hours = max(1, min(int(hours or 12), 72))
        limit = max(20, min(int(limit or 180), 500))
        start_at = now - timedelta(hours=hours)
        status = await sunroom_door_session_payload(session, notify=False)
        rooms = list(status.get("rooms") or [])
        room_logic = [sunroom_logic_for_room(item, now) for item in rooms]
        config_by_device = {
            int(config["device_id"]): config
            for config in DOOR_SENSOR_CONFIG
            if config.get("group_key") == "solrom" and config.get("device_id") is not None
        }
        device_ids = list(config_by_device)
        timeline: list[Dict[str, Any]] = []

        door_rows: list[DoorEvent] = []
        if device_ids:
            raw_door_rows = (
                await session.execute(
                    select(DoorEvent)
                    .where(DoorEvent.device_id.in_(device_ids))
                    .where(DoorEvent.timestamp >= start_at)
                    .order_by(DoorEvent.timestamp.desc(), DoorEvent.id.desc())
                    .limit(max(limit * 4, 800))
                )
            ).scalars().all()
            door_rows = list(reversed(door_change_rows(list(reversed(raw_door_rows)))))

        current_by_device = {int(item["deviceId"]): item for item in rooms if item.get("deviceId") is not None}
        for row in door_rows:
            config = config_by_device.get(int(row.device_id or 0))
            if not config:
                continue
            room_id = sunroom_room_id_for_config(config)
            room_label = str(config.get("title") or row.device_name or room_id or "Solrom")
            is_open = door_event_state_bool(row) is True
            current = current_by_device.get(int(row.device_id or 0))
            row_at = normalize_local_naive(row.timestamp)
            is_current_period = bool(
                current
                and row_at
                and (current_at := sunroom_parse_time_value(current.get("doorChangedAt")))
                and abs((current_at - row_at).total_seconds()) <= 2
            )
            timeline.append(
                sunroom_logic_event(
                    f"door-{row.id}",
                    row_at,
                    kind="door",
                    kind_label="Dør",
                    room_id=room_id,
                    room_label=room_label,
                    event="Dør åpnet" if is_open else "Dør lukket",
                    logic=(
                        "Aktiv dørperiode avsluttes."
                        if is_open
                        else "Ny dørperiode opprettes; normal klargjøringstid starter."
                    ),
                    action=(
                        "Stopper videre betalingskontroll for denne dørperioden."
                        if is_open
                        else f"SUN2 kan kontrolleres etter {SUNROOM_DOOR_FORCED_SYNC_MINUTES:g} min."
                    ),
                    result=(
                        str(current.get("status"))
                        if is_current_period and current
                        else "Dørperioden avsluttet" if is_open else "Kontrollvindu opprettet"
                    ),
                    tone="green" if is_open else "sky",
                )
            )

        room_ids = [item.get("roomId") for item in rooms if item.get("roomId")]
        bed_ids = [item.get("sun2BedId") for item in rooms if item.get("sun2BedId")]
        session_conditions = []
        if room_ids:
            session_conditions.append(Sun2TanningSession.room_id.in_(room_ids))
        if bed_ids:
            session_conditions.append(Sun2TanningSession.sun2_bed_id.in_(bed_ids))
        if session_conditions:
            session_rows = (
                await session.execute(
                    select(Sun2TanningSession)
                    .where(or_(*session_conditions))
                    .where(Sun2TanningSession.started_at >= start_at)
                    .order_by(Sun2TanningSession.started_at.desc(), Sun2TanningSession.id.desc())
                    .limit(limit)
                )
            ).scalars().all()
            for row in session_rows:
                room_id = sunroom_canonical_room_id(row)
                config = sunroom_config_for_room_id(room_id or "")
                payload = sunroom_session_payload(row)
                duration = f"{float(row.duration_minutes):g} min" if row.duration_minutes is not None else "ukjent tid"
                amount = sunroom_money_label(row.paid_amount_kr)
                timeline.append(
                    sunroom_logic_event(
                        f"session-{row.id}",
                        normalize_local_naive(row.started_at),
                        kind="session",
                        kind_label="SUN2",
                        room_id=room_id,
                        room_label=str(config.get("title") if config else payload.get("roomLabel") or room_id or "Solrom"),
                        event="Soltime registrert",
                        logic="Betaling matches mot nærmeste dørperiode for samme rom.",
                        action="Beregner forventet solstart, slutt og tidspunkt ut av rommet.",
                        result=f"{duration} · {amount} · forventet ut {format_source_time(sunroom_parse_time_value(payload.get('expectedExitAt')))}",
                        tone="green",
                    )
                )

        import_start_utc = local_naive_to_utc_naive(start_at)
        import_rows = (
            await session.execute(
                select(Sun2SessionImportRun)
                .where(Sun2SessionImportRun.timestamp >= import_start_utc)
                .order_by(Sun2SessionImportRun.timestamp.desc(), Sun2SessionImportRun.id.desc())
                .limit(min(limit, 120))
            )
        ).scalars().all()
        for row in import_rows:
            raw = row.raw if isinstance(row.raw, dict) else {}
            extra = raw.get("extra") if isinstance(raw.get("extra"), dict) else {}
            reason = extra.get("trigger_reason")
            result_parts = [f"{int(row.rows_count or 0)} timer lest"]
            changed = int(row.inserted_count or 0) + int(row.updated_count or 0)
            if changed:
                result_parts.append(f"{changed} nye eller oppdaterte")
            timeline.append(
                sunroom_logic_event(
                    f"sync-{row.id}",
                    utc_naive_to_local_naive(row.timestamp),
                    kind="sync",
                    kind_label="Kontroll",
                    room_id=None,
                    room_label="Alle rom",
                    event="SUN2-data oppdatert" if row.ok is not False else "SUN2-kontroll feilet",
                    logic=sunroom_sync_reason_label(reason),
                    action="Vurderer alle aktive dørperioder på nytt mot ferske enkelttimer.",
                    result=" · ".join(result_parts) if row.ok is not False else str(row.message or "Ukjent feil"),
                    tone="sky" if row.ok is not False else "red",
                )
            )

        alarm_rows = (
            await session.execute(
                select(AlarmEvent)
                .where(AlarmEvent.domain == "doors")
                .where(or_(AlarmEvent.detected_at >= start_at, AlarmEvent.resolved_at >= start_at))
                .order_by(AlarmEvent.detected_at.desc(), AlarmEvent.id.desc())
                .limit(min(limit, 120))
            )
        ).scalars().all()
        for row in alarm_rows:
            alarm_logic = (
                "Døren er fortsatt lukket etter kontroll uten en passende soltime."
                if row.alarm_type == "closed_without_session"
                else "Døren er fortsatt lukket etter beregnet ut-tid."
            )
            timeline.append(
                sunroom_logic_event(
                    f"alarm-{row.id}",
                    normalize_local_naive(row.detected_at),
                    kind="alarm",
                    kind_label="Alarm",
                    room_id=row.room_id,
                    room_label=row.title or f"Solrom {row.display_room_number or '-'}",
                    event="Alarm utløst",
                    logic=alarm_logic,
                    action="Varsling sendes og hendelsen lagres for etterkontroll.",
                    result=f"{row.status} · {row.notification_status}",
                    tone="red",
                )
            )
            if row.resolved_at and normalize_local_naive(row.resolved_at) >= start_at:
                timeline.append(
                    sunroom_logic_event(
                        f"alarm-resolved-{row.id}",
                        normalize_local_naive(row.resolved_at),
                        kind="alarm",
                        kind_label="Alarm",
                        room_id=row.room_id,
                        room_label=row.title or f"Solrom {row.display_room_number or '-'}",
                        event="Alarm avsluttet",
                        logic="Dør- eller soltimedata viser at alarmsituasjonen ikke lenger er aktiv.",
                        action="Stopper videre varsling for hendelsen.",
                        result=row.resolution_reason or "Normalisert",
                        tone="green",
                    )
                )

        timeline.sort(key=lambda item: item["_sortAt"], reverse=True)
        for item in timeline:
            item.pop("_sortAt", None)
        timeline = timeline[:limit]
        scraper = await asyncio.to_thread(fetch_sun2_scraper_runtime)
        latest_import = import_rows[0] if import_rows else None
        latest_import_at = utc_naive_to_local_naive(latest_import.timestamp) if latest_import else None
        return {
            "generatedAt": api_local_iso(now),
            "windowHours": hours,
            "summary": {
                **dict(status.get("summary") or {}),
                "events": len(timeline),
                "latestSun2At": api_local_iso(latest_import_at),
                "latestSun2Label": format_source_datetime(latest_import_at),
                "scraperAvailable": bool(scraper.get("available")),
            },
            "rules": status.get("rules") or {},
            "scraper": {
                "available": bool(scraper.get("available")),
                "error": scraper.get("error"),
                "lastAttemptAt": scraper.get("today_sync_last_attempt_at"),
                "lastReason": scraper.get("today_sync_last_reason"),
                "lastReasonLabel": sunroom_sync_reason_label(scraper.get("today_sync_last_reason")),
                "lastAction": scraper.get("live_last_action"),
                "lastDeferredAt": scraper.get("today_sync_last_deferred_at"),
                "minIntervalSeconds": scraper.get("live_sync_min_interval_seconds", SUNROOM_DOOR_SYNC_MIN_INTERVAL_SECONDS),
                "fallbackIntervalSeconds": scraper.get("live_sync_fallback_interval_seconds", 1800),
            },
            "rooms": room_logic,
            "events": timeline,
        }

    async def sunroom_room_detail_payload(session, room_id: str, days: int = 14, limit: int = 120) -> Dict[str, Any]:
        now = local_now_naive()
        normalized_room_id = normalize_room_id(room_id)
        config = sunroom_config_for_room_id(room_id)
        if not normalized_room_id or not config:
            raise HTTPException(status_code=404, detail="Ukjent solrom")

        days = max(1, min(days, 90))
        limit = max(10, min(limit, 500))
        start_cutoff = now - timedelta(days=days)
        bed_id = sunroom_bed_id_for_config(config)
        bed_statuses_by_id = await sunroom_bed_statuses_by_id(session, [bed_id] if bed_id else [], now)
        bed_status = bed_statuses_by_id.get(str(bed_id or ""))
        device_id = config.get("device_id")
        latest_row: Optional[DoorEvent] = None
        raw_rows: list[DoorEvent] = []
        sensor_status = await session.get(DoorSensorStatus, int(device_id)) if device_id is not None else None

        if device_id is not None:
            latest_row = (
                await session.execute(
                    select(DoorEvent)
                    .where(DoorEvent.device_id == int(device_id))
                    .order_by(DoorEvent.timestamp.desc(), DoorEvent.id.desc())
                    .limit(1)
                )
            ).scalars().first()
            raw_rows = (
                await session.execute(
                    select(DoorEvent)
                    .where(DoorEvent.device_id == int(device_id))
                    .where(DoorEvent.timestamp >= start_cutoff - timedelta(hours=12))
                    .order_by(DoorEvent.timestamp.desc(), DoorEvent.id.desc())
                    .limit(max(limit * 25, 1500))
                )
            ).scalars().all()

        session_identity = Sun2TanningSession.room_id == normalized_room_id
        if bed_id:
            session_identity = or_(session_identity, Sun2TanningSession.sun2_bed_id == bed_id)
        session_rows = (
            await session.execute(
                select(Sun2TanningSession)
                .where(session_identity)
                .where(Sun2TanningSession.started_at >= start_cutoff - timedelta(hours=2))
                .order_by(Sun2TanningSession.started_at.desc(), Sun2TanningSession.id.desc())
                .limit(max(limit * 3, 300))
            )
        ).scalars().all()

        change_rows_ascending = door_change_rows(list(reversed(raw_rows)))
        closed_period_rows = [
            period
            for period in door_closed_periods(change_rows_ascending, now)
            if (period.get("openedAt") is None)
            or (period.get("openedAt") and period["openedAt"] >= start_cutoff)
            or (period.get("closedAt") and period["closedAt"] >= start_cutoff)
        ][:limit]

        periods = []
        matched_session_ids: set[int] = set()
        for period in closed_period_rows:
            matched_session = sunroom_match_session_for_period(session_rows, period.get("closedAt"), period.get("openedAt"), now)
            if matched_session and matched_session.id is not None:
                matched_session_ids.add(int(matched_session.id))
            periods.append(sunroom_period_payload(period, matched_session, now))
        apply_sunroom_bed_status_to_active_periods(periods, bed_status)

        current_period = next((period for period in periods if period.get("isActive")), None)
        sessions_without_door = [
            sunroom_session_payload(row)
            for row in session_rows
            if row.id is not None and int(row.id) not in matched_session_ids and normalize_local_naive(row.started_at) >= start_cutoff
        ][:25]
        current = sunroom_status_item(
            config,
            latest_row,
            {normalized_room_id: session_rows},
            now,
            bed_status,
            sensor_status,
        )
        alerts = [period for period in periods if period.get("severity") == "alert"]
        warnings = [period for period in periods if period.get("severity") == "warning"]
        missing = [period for period in periods if period.get("missingSession")]

        return {
            "generatedAt": now.isoformat(),
            "days": days,
            "room": current,
            "summary": {
                "periods": len(periods),
                "active": 1 if current_period else 0,
                "warnings": len(warnings),
                "alerts": len(alerts),
                "missingSession": len(missing),
                "sessions": len([row for row in session_rows if normalize_local_naive(row.started_at) >= start_cutoff]),
                "sessionsWithoutDoor": len(sessions_without_door),
            },
            "currentPeriod": current_period,
            "periods": periods,
            "sessionsWithoutDoor": sessions_without_door,
        }

    async def sunroom_room_overview_payload(session, days: int = 2, day: Optional[str] = None) -> Dict[str, Any]:
        DOOR_SENSOR_CONFIG = dependencies.DOOR_SENSOR_CONFIG
        SUNROOM_DOOR_ALERT_AFTER_END_MINUTES = dependencies.SUNROOM_DOOR_ALERT_AFTER_END_MINUTES
        SUNROOM_DOOR_EXIT_GRACE_MINUTES = dependencies.SUNROOM_DOOR_EXIT_GRACE_MINUTES
        SUNROOM_DOOR_FAN_AFTER_RUN_MINUTES = dependencies.SUNROOM_DOOR_FAN_AFTER_RUN_MINUTES
        SUNROOM_DOOR_PAYMENT_DELAY_MINUTES = dependencies.SUNROOM_DOOR_PAYMENT_DELAY_MINUTES
        SUNROOM_DOOR_WARN_AFTER_END_MINUTES = dependencies.SUNROOM_DOOR_WARN_AFTER_END_MINUTES
        parse_day = dependencies.parse_day
        now = local_now_naive()
        days = max(1, min(days, 30))
        selected_day = parse_day(day) if day else now.date()
        has_day_filter = bool(day)
        day_start = datetime.combine(selected_day, time.min)
        day_end = day_start + timedelta(days=1)
        start_cutoff = now - timedelta(days=days)
        raw_start_cutoff = day_start - timedelta(hours=12) if has_day_filter else min(start_cutoff, day_start - timedelta(hours=12))
        raw_end = day_end + timedelta(hours=12) if has_day_filter else now + timedelta(hours=2)
        session_start = day_start - timedelta(hours=2) if has_day_filter else start_cutoff - timedelta(hours=2)
        session_end = day_end + timedelta(hours=2) if has_day_filter else now + timedelta(hours=2)
        energy_start = day_start - timedelta(minutes=30) if has_day_filter else start_cutoff - timedelta(minutes=30)
        energy_end = day_end + timedelta(hours=2) if has_day_filter else now + timedelta(hours=2)
        configs = [config for config in DOOR_SENSOR_CONFIG if config.get("group_key") == "solrom"]
        configs.sort(key=lambda config: int(config.get("sort_order") or 0))
        device_ids = [int(config["device_id"]) for config in configs if config.get("device_id") is not None]
        room_ids = [room_id for room_id in (sunroom_room_id_for_config(config) for config in configs) if room_id]
        bed_ids = [bed_id for bed_id in (sunroom_bed_id_for_config(config) for config in configs) if bed_id]
        bed_statuses_by_id = await sunroom_bed_statuses_by_id(session, bed_ids, now)
        entrance_config = sunroom_entrance_config()
        entrance_device_id = int(entrance_config["device_id"]) if entrance_config and entrance_config.get("device_id") is not None else None

        raw_rows: list[DoorEvent] = []
        if device_ids:
            raw_rows = (
                await session.execute(
                    select(DoorEvent)
                    .where(DoorEvent.device_id.in_(device_ids))
                    .where(DoorEvent.timestamp >= raw_start_cutoff)
                    .where(DoorEvent.timestamp <= raw_end)
                    .order_by(DoorEvent.timestamp.desc(), DoorEvent.id.desc())
                    .limit(max(len(device_ids) * 500, 4000))
                )
            ).scalars().all()
        sensor_status_rows = (
            await session.execute(
                select(DoorSensorStatus).where(DoorSensorStatus.device_id.in_(device_ids))
            )
        ).scalars().all() if device_ids else []
        sensor_status_by_device = {int(row.device_id): row for row in sensor_status_rows}
        entrance_rows: list[DoorEvent] = []
        if entrance_device_id is not None:
            entrance_rows = (
                await session.execute(
                    select(DoorEvent)
                    .where(DoorEvent.device_id == entrance_device_id)
                    .where(DoorEvent.timestamp >= raw_start_cutoff)
                    .where(DoorEvent.timestamp <= raw_end)
                    .order_by(DoorEvent.timestamp.asc(), DoorEvent.id.asc())
                    .limit(2000)
                )
            ).scalars().all()
        entrance_change_rows = door_change_rows(entrance_rows)

        session_identity_conditions = []
        if room_ids:
            session_identity_conditions.append(Sun2TanningSession.room_id.in_(room_ids))
        if bed_ids:
            session_identity_conditions.append(Sun2TanningSession.sun2_bed_id.in_(bed_ids))
        session_rows = (
            await session.execute(
                select(Sun2TanningSession)
                .where(or_(*session_identity_conditions))
                .where(Sun2TanningSession.started_at >= session_start)
                .where(Sun2TanningSession.started_at <= session_end)
                .order_by(Sun2TanningSession.started_at.desc(), Sun2TanningSession.id.desc())
            )
        ).scalars().all()

        energy_rows = (
            await session.execute(
                select(
                    EnergyFibaroSample.bucket_start.label("bucket_start"),
                    EnergyFibaroSample.differanse_beregnet_w.label("differanse_beregnet_w"),
                )
                .where(EnergyFibaroSample.bucket_start >= energy_start)
                .where(EnergyFibaroSample.bucket_start <= energy_end)
                .order_by(EnergyFibaroSample.bucket_start.asc())
            )
        ).mappings().all()
        energy_samples = sunroom_energy_sample_items([dict(row) for row in energy_rows])
        energy_sample_times = [item["time"] for item in energy_samples]
        energy_by_session_id = {
            int(row.id): sunroom_session_energy_evidence(
                row,
                energy_samples,
                session_rows,
                energy_sample_times,
            )
            for row in session_rows
            if row.id is not None
        }

        change_rows_ascending = door_change_rows(list(reversed(raw_rows)))
        latest_change_by_device: Dict[int, DoorEvent] = {}
        for row in reversed(change_rows_ascending):
            if row.device_id is None:
                continue
            latest_change_by_device.setdefault(int(row.device_id), row)

        all_closed_periods = door_closed_periods(change_rows_ascending, now)
        periods_by_device: Dict[str, list[Dict[str, Any]]] = {}
        for period in all_closed_periods:
            closed_at = period.get("closedAt")
            opened_at = period.get("openedAt")
            if has_day_filter:
                if closed_at and closed_at >= day_end:
                    continue
                if opened_at and opened_at < day_start and (not closed_at or closed_at < day_start):
                    continue
            elif opened_at and opened_at < start_cutoff and (not closed_at or closed_at < start_cutoff):
                continue
            periods_by_device.setdefault(door_period_device_key(period), []).append(period)

        sessions_by_room: Dict[str, list[Sun2TanningSession]] = {room_id: [] for room_id in room_ids}
        for row in session_rows:
            normalized = sunroom_canonical_room_id(row)
            if normalized:
                sessions_by_room.setdefault(normalized, []).append(row)

        rooms = []
        all_matched_ids: set[int] = set()
        for config in configs:
            display_number = sunroom_display_number(config)
            room_id = sunroom_room_id_for_config(config)
            device_id = config.get("device_id")
            latest_row = latest_change_by_device.get(int(device_id)) if device_id is not None else None
            room_sessions = sessions_by_room.get(room_id or "", [])
            bed_status = bed_statuses_by_id.get(str(sunroom_bed_id_for_config(config) or ""))
            status_item = sunroom_status_item(
                config,
                latest_row,
                {room_id or "": room_sessions},
                now,
                bed_status,
                sensor_status_by_device.get(int(device_id)) if device_id is not None else None,
            )
            device_periods = periods_by_device.get(door_config_device_key(config), [])

            periods = []
            matched_ids: set[int] = set()
            visible_device_periods = device_periods if has_day_filter else device_periods[:12]
            for period in visible_device_periods:
                matched_session = sunroom_match_session_for_period(room_sessions, period.get("closedAt"), period.get("openedAt"), now)
                if matched_session and matched_session.id is not None:
                    matched_ids.add(int(matched_session.id))
                    all_matched_ids.add(int(matched_session.id))
                payload = sunroom_period_payload(period, matched_session, now)
                if matched_session and matched_session.id is not None:
                    payload["energy"] = energy_by_session_id.get(int(matched_session.id))
                    payload["entranceMarkers"] = sunroom_entrance_markers(matched_session, entrance_change_rows)
                    payload["powerMarkers"] = sunroom_power_markers(
                        matched_session,
                        energy_samples,
                        energy_sample_times,
                    )
                else:
                    payload["energy"] = None
                    payload["entranceMarkers"] = []
                    payload["powerMarkers"] = []
                periods.append(payload)
            apply_sunroom_bed_status_to_active_periods(periods, bed_status)

            day_events: list[Dict[str, Any]] = []
            for period in device_periods:
                day_events.extend(sunroom_period_day_events(period, day_start, day_end))

            for row in room_sessions:
                start_at = normalize_local_naive(row.started_at)
                if start_at and day_start - timedelta(hours=2) <= start_at < day_end:
                    day_events.extend(
                        sunroom_session_day_events(
                            row,
                            entrance_change_rows,
                            energy_samples,
                            day_start,
                            day_end,
                            energy_sample_times,
                        )
                    )

            day_events = sorted(
                day_events,
                key=lambda item: (sunroom_parse_time_value(item.get("time")) or datetime.min, str(item.get("kind") or ""), str(item.get("id") or "")),
            )

            recent_sessions = [
                {
                    **sunroom_session_payload(row),
                    "energy": energy_by_session_id.get(int(row.id)) if row.id is not None else None,
                    "entranceMarkers": sunroom_entrance_markers(row, entrance_change_rows),
                    "powerMarkers": sunroom_power_markers(row, energy_samples, energy_sample_times),
                    "hasDoorMatch": row.id is not None and int(row.id) in matched_ids,
                }
                for row in room_sessions
                if (start_at := normalize_local_naive(row.started_at))
                and ((day_start <= start_at < day_end) if has_day_filter else start_at >= start_cutoff)
            ]
            if not has_day_filter:
                recent_sessions = recent_sessions[:8]

            sessions_without_door = [item for item in recent_sessions if not item.get("hasDoorMatch")]
            alerts = [period for period in periods if period.get("severity") == "alert"]
            warnings = [period for period in periods if period.get("severity") == "warning"]
            energy_confirmed = [
                item
                for item in recent_sessions
                if (item.get("energy") or {}).get("status") == "confirmed"
            ]
            energy_overlap = [
                item
                for item in recent_sessions
                if (item.get("energy") or {}).get("quality") == "overlap"
            ]

            rooms.append(
                {
                    "displayRoomNumber": display_number,
                    "title": config.get("title") or f"Solrom {display_number}",
                    "sectionKey": config.get("section_key"),
                    "sectionTitle": config.get("section_title"),
                    "deviceId": device_id,
                    "deviceKey": config.get("device_key"),
                    "roomId": room_id,
                    "roomLabel": sun2_room_label(room_id, None),
                    "status": status_item,
                    "latestPeriod": periods[0] if periods else None,
                    "periods": periods,
                    "recentSessions": recent_sessions,
                    "sessionsWithoutDoor": sessions_without_door,
                    "dayEvents": day_events,
                    "summary": {
                        "periods": len(periods),
                        "sessions": len(recent_sessions),
                        "matched": len([item for item in recent_sessions if item.get("hasDoorMatch")]),
                        "withoutDoor": len(sessions_without_door),
                        "warnings": len(warnings),
                        "alerts": len(alerts),
                        "energyConfirmed": len(energy_confirmed),
                        "energyOverlap": len(energy_overlap),
                    },
                }
            )

        active_rooms = [
            room
            for room in rooms
            if (room.get("status") or {}).get("isOccupied")
            and (room.get("status") or {}).get("bedEnabled") is not False
        ]
        warning_rooms = [room for room in rooms if (room.get("status") or {}).get("severity") == "warning"]
        alert_rooms = [room for room in rooms if (room.get("status") or {}).get("severity") == "alert"]
        sessions_without_door_count = sum(int((room.get("summary") or {}).get("withoutDoor") or 0) for room in rooms)
        energy_confirmed_count = sum(int((room.get("summary") or {}).get("energyConfirmed") or 0) for room in rooms)
        return {
            "generatedAt": now.isoformat(),
            "dayDate": day_start.date().isoformat(),
            "dayStart": day_start.isoformat(),
            "dayEnd": day_end.isoformat(),
            "days": days,
            "rules": {
                "paymentDelayMinutes": SUNROOM_DOOR_PAYMENT_DELAY_MINUTES,
                "exitGraceMinutes": SUNROOM_DOOR_EXIT_GRACE_MINUTES,
                "fanAfterRunMinutes": SUNROOM_DOOR_FAN_AFTER_RUN_MINUTES,
                "warnAfterEndMinutes": SUNROOM_DOOR_WARN_AFTER_END_MINUTES,
                "alertAfterEndMinutes": SUNROOM_DOOR_ALERT_AFTER_END_MINUTES,
            },
            "summary": {
                "rooms": len(rooms),
                "active": len(active_rooms),
                "warnings": len(warning_rooms),
                "alerts": len(alert_rooms),
                "sessions": len([row for row in session_rows if normalize_local_naive(row.started_at) >= start_cutoff]),
                "dayActivityRooms": len([room for room in rooms if room.get("dayEvents")]),
                "dayEvents": sum(len(room.get("dayEvents") or []) for room in rooms),
                "daySessions": sum(
                    len([event for event in room.get("dayEvents") or [] if event.get("kind") == "sun_start"])
                    for room in rooms
                ),
                "dayPowerEvents": sum(
                    len([event for event in room.get("dayEvents") or [] if str(event.get("kind") or "").startswith("power_")])
                    for room in rooms
                ),
                "doorMatches": len(all_matched_ids),
                "sessionsWithoutDoor": sessions_without_door_count,
                "energyConfirmed": energy_confirmed_count,
                "energySamples": len(energy_samples),
            },
            "rooms": rooms,
        }

    async def sunroom_door_monitor_worker():
        SUNROOM_DOOR_MONITOR_INITIAL_DELAY_SECONDS = dependencies.SUNROOM_DOOR_MONITOR_INITIAL_DELAY_SECONDS
        SUNROOM_DOOR_MONITOR_INTERVAL_SECONDS = dependencies.SUNROOM_DOOR_MONITOR_INTERVAL_SECONDS
        async_session = dependencies.async_session
        attach_hc3_alarm_verification = dependencies.attach_hc3_alarm_verification
        force_sun2_sync_for_closed_rooms = dependencies.force_sun2_sync_for_closed_rooms
        logger = dependencies.logger
        await asyncio.sleep(SUNROOM_DOOR_MONITOR_INITIAL_DELAY_SECONDS)
        while True:
            try:
                async with async_session() as session:
                    payload = await sunroom_door_session_payload(session, notify=False)
                sync_result = await force_sun2_sync_for_closed_rooms(
                    list(payload.get("rooms") or []),
                    local_now_naive(),
                )
                if sync_result.get("attempted"):
                    logger.info(
                        "Tvungen Sun2-kontroll for doralarm: ok=%s rooms=%s error=%s",
                        sync_result.get("ok"),
                        sync_result.get("rooms"),
                        sync_result.get("error"),
                    )

                async with async_session() as checked_session:
                    checked_payload = await sunroom_door_session_payload(checked_session, notify=False)
                    checked_rooms = list(checked_payload.get("rooms") or [])
                    has_alert = any(
                        item.get("severity") == "alert" and item.get("isOccupied") and item.get("alarmReason")
                        for item in checked_rooms
                    )
                    if not has_alert:
                        await sync_sunroom_alarm_history(checked_session, checked_rooms, local_now_naive())
                        await checked_session.commit()
                if has_alert:
                    hc3_result = await verify_sunroom_alert_doors_with_hc3(checked_rooms)
                    async with async_session() as confirmation_session:
                        confirmed = await sunroom_door_session_payload(confirmation_session, notify=False)
                        confirmed_at = local_now_naive()
                        confirmed_rooms = attach_hc3_alarm_verification(
                            list(confirmed.get("rooms") or []),
                            hc3_result,
                        )
                        await sync_sunroom_alarm_history(confirmation_session, confirmed_rooms, confirmed_at)
                        await publish_sunroom_door_alerts(
                            confirmed_rooms,
                            confirmed_at,
                            session=confirmation_session,
                        )
                        await confirmation_session.commit()
            except Exception as exc:
                logger.warning("Sunroom door monitor feilet: %s", exc, exc_info=True)
            await asyncio.sleep(SUNROOM_DOOR_MONITOR_INTERVAL_SECONDS)

    def door_change_text(row: Optional[DoorEvent]) -> str:
        if not row:
            return "Ingen endringer registrert"
        state = door_state_from_event(row)
        action_text = "Åpnet" if state["state"] == "open" else "Lukket" if state["state"] == "closed" else "Ukjent status"
        return f"{door_title_for_row(row)} {action_text.lower()}"

    def operations_recent_door_items(door_result: Dict[str, Any], limit: int = 4) -> list[Dict[str, Any]]:
        doors = door_result.get("doors") or []
        titles_by_key = {
            str(door.get("deviceKey")): door.get("title")
            for door in doors
            if door.get("deviceKey") is not None and door.get("title")
        }
        titles_by_id = {
            str(door.get("deviceId")): door.get("title")
            for door in doors
            if door.get("deviceId") is not None and door.get("title")
        }
        items = []
        for change in (door_result.get("changes") or [])[:limit]:
            device_key = change.get("deviceKey")
            device_id = change.get("deviceId")
            label = (
                titles_by_key.get(str(device_key))
                or titles_by_id.get(str(device_id))
                or change.get("deviceName")
                or device_key
                or device_id
                or "Ukjent dør"
            )
            items.append({
                "label": label,
                "value": change.get("stateLabel"),
                "detail": change.get("ageLabel"),
                "state": change.get("state"),
            })
        return items

    return {
        "apply_sunroom_bed_status_to_active_periods": apply_sunroom_bed_status_to_active_periods,
        "apply_sunroom_alarm_verification": apply_sunroom_alarm_verification,
        "cleanup_sunroom_door_verifications": cleanup_sunroom_door_verifications,
        "door_action_from_state": door_action_from_state,
        "door_age_label": door_age_label,
        "door_change_rows": door_change_rows,
        "door_change_text": door_change_text,
        "door_closed_period_payload": door_closed_period_payload,
        "door_closed_periods": door_closed_periods,
        "door_config_device_key": door_config_device_key,
        "door_duration_label": door_duration_label,
        "door_event_device_key": door_event_device_key,
        "door_event_from_payload": door_event_from_payload,
        "door_event_payload": door_event_payload,
        "door_event_state_bool": door_event_state_bool,
        "door_open_periods": door_open_periods,
        "door_period_device_key": door_period_device_key,
        "door_period_payload": door_period_payload,
        "door_poll_sync_payload": door_poll_sync_payload,
        "door_state_age_minutes": door_state_age_minutes,
        "door_state_from_event": door_state_from_event,
        "door_status_payload": door_status_payload,
        "door_title_for_row": door_title_for_row,
        "door_unexpected_reason": door_unexpected_reason,
        "hc3_door_poll_is_configured": hc3_door_poll_is_configured,
        "hc3_door_poll_worker": hc3_door_poll_worker,
        "hc3_door_status_from_device": hc3_door_status_from_device,
        "hc3_door_unexpected_targets": hc3_door_unexpected_targets,
        "hc3_fetch_all_door_statuses": hc3_fetch_all_door_statuses,
        "hc3_fetch_door_status": hc3_fetch_door_status,
        "hc3_fetch_door_statuses": hc3_fetch_door_statuses,
        "latest_door_changes_by_device": latest_door_changes_by_device,
        "latest_door_event_by_device": latest_door_event_by_device,
        "operations_recent_door_items": operations_recent_door_items,
        "publish_door_ntfy": publish_door_ntfy,
        "publish_sunroom_door_alerts": publish_sunroom_door_alerts,
        "run_hc3_door_poll_once": run_hc3_door_poll_once,
        "run_hc3_door_unexpected_check_once": run_hc3_door_unexpected_check_once,
        "upsert_door_event_status": upsert_door_event_status,
        "upsert_door_sensor_status": upsert_door_sensor_status,
        "sunroom_alarm_detected_at": sunroom_alarm_detected_at,
        "sunroom_alarm_event_key": sunroom_alarm_event_key,
        "sunroom_alarm_message": sunroom_alarm_message,
        "sunroom_alert_key": sunroom_alert_key,
        "sunroom_bed_id_for_config": sunroom_bed_id_for_config,
        "sunroom_best_session_for_door": sunroom_best_session_for_door,
        "sunroom_canonical_room_id": sunroom_canonical_room_id,
        "sunroom_config_for_room_id": sunroom_config_for_room_id,
        "sunroom_day_event": sunroom_day_event,
        "sunroom_display_number": sunroom_display_number,
        "sunroom_door_alarm_payload": sunroom_door_alarm_payload,
        "sunroom_door_event_marker": sunroom_door_event_marker,
        "sunroom_door_monitor_worker": sunroom_door_monitor_worker,
        "sunroom_door_period_key": sunroom_door_period_key,
        "sunroom_door_session_payload": sunroom_door_session_payload,
        "sunroom_duration_label": sunroom_duration_label,
        "sunroom_energy_sample_items": sunroom_energy_sample_items,
        "sunroom_energy_sample_window": sunroom_energy_sample_window,
        "sunroom_entrance_config": sunroom_entrance_config,
        "sunroom_entrance_markers": sunroom_entrance_markers,
        "sunroom_expected_exit_at": sunroom_expected_exit_at,
        "sunroom_force_sync_candidates": sunroom_force_sync_candidates,
        "sunroom_identity_for_config": sunroom_identity_for_config,
        "sunroom_item_may_have_new_session": sunroom_item_may_have_new_session,
        "sunroom_logic_event": sunroom_logic_event,
        "sunroom_logic_for_room": sunroom_logic_for_room,
        "sunroom_logic_payload": sunroom_logic_payload,
        "sunroom_marker_day_event": sunroom_marker_day_event,
        "sunroom_match_session_for_period": sunroom_match_session_for_period,
        "sunroom_median_float": sunroom_median_float,
        "sunroom_money_label": sunroom_money_label,
        "sunroom_parse_time_value": sunroom_parse_time_value,
        "sunroom_period_day_events": sunroom_period_day_events,
        "sunroom_period_payload": sunroom_period_payload,
        "sunroom_period_status": sunroom_period_status,
        "sunroom_power_marker": sunroom_power_marker,
        "sunroom_power_markers": sunroom_power_markers,
        "sunroom_room_detail_payload": sunroom_room_detail_payload,
        "sunroom_room_id_for_config": sunroom_room_id_for_config,
        "sunroom_room_overview_payload": sunroom_room_overview_payload,
        "sunroom_session_day_events": sunroom_session_day_events,
        "sunroom_session_end_at": sunroom_session_end_at,
        "sunroom_session_energy_evidence": sunroom_session_energy_evidence,
        "sunroom_session_energy_window": sunroom_session_energy_window,
        "sunroom_session_matches_closed_period": sunroom_session_matches_closed_period,
        "sunroom_session_matches_period": sunroom_session_matches_period,
        "sunroom_session_payload": sunroom_session_payload,
        "sunroom_session_period_score": sunroom_session_period_score,
        "sunroom_session_sun_start_at": sunroom_session_sun_start_at,
        "sunroom_status_item": sunroom_status_item,
        "sunroom_bed_status_payload": sunroom_bed_status_payload,
        "sunroom_sync_candidate_is_due": sunroom_sync_candidate_is_due,
        "sunroom_sync_reason_label": sunroom_sync_reason_label,
        "sunroom_watt_label": sunroom_watt_label,
        "sync_sunroom_alarm_history": sync_sunroom_alarm_history,
        "verify_sunroom_alert_doors_with_hc3": verify_sunroom_alert_doors_with_hc3,
    }
