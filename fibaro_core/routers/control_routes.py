"""Control HTTP routes; runtime services are supplied by composition."""

from dataclasses import dataclass
from datetime import datetime
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi.responses import Response
from fibaro_core.export_definitions import DOOR_EVENT_COLUMNS
from fibaro_core.models import DoorEvent
from fibaro_core.routers.bundle import RouterBundle
from sqlalchemy import func
from sqlalchemy import select
from time_formatting import format_source_datetime_short
from time_formatting import local_now_naive
from time_formatting import normalize_local_naive
from typing import Any
from typing import Any, Callable
from typing import Dict
from typing import Optional
from unifi_protect_client import ProtectLedgerError
import asyncio


@dataclass
class Dependencies:
    ALARM_APP_URL: Any
    DOOR_SENSOR_CONFIG: Any
    DOOR_SENSOR_IDS: Any
    NTFY_BOLLARDS_TOPIC: Any
    async_session: Callable[..., Any]
    bollard_image_cache_control: Callable[..., Any]
    bollard_mobile_notification_payload: Callable[..., Any]
    door_age_label: Callable[..., Any]
    door_change_rows: Callable[..., Any]
    door_change_text: Callable[..., Any]
    door_config_device_key: Callable[..., Any]
    door_event_payload: Callable[..., Any]
    door_open_periods: Callable[..., Any]
    door_period_device_key: Callable[..., Any]
    door_status_payload: Callable[..., Any]
    latest_door_event_by_device: Callable[..., Any]
    logger: Any
    parse_day: Callable[..., Any]
    protect_ledger_client: Callable[..., Any]
    protect_ledger_json: Callable[..., Any]
    publish_ntfy_message: Callable[..., Any]
    row_to_dict: Callable[..., Any]
    run_hc3_door_poll_once: Callable[..., Any]
    sunroom_door_alarm_payload: Callable[..., Any]
    sunroom_door_session_payload: Callable[..., Any]
    sunroom_logic_payload: Callable[..., Any]
    sunroom_room_detail_payload: Callable[..., Any]
    sunroom_room_overview_payload: Callable[..., Any]


def create_router(dependencies: Dependencies) -> RouterBundle:
    router = APIRouter()


    @router.get("/api/unifi-protect/status")
    async def api_unifi_protect_status() -> dict[str, Any]:
        protect_ledger_json = dependencies.protect_ledger_json
        return await protect_ledger_json("status")

    @router.get("/api/unifi-protect/cameras")
    async def api_unifi_protect_cameras() -> dict[str, Any]:
        protect_ledger_json = dependencies.protect_ledger_json
        return await protect_ledger_json("cameras")

    @router.get("/api/unifi-protect/capabilities")
    async def api_unifi_protect_capabilities() -> dict[str, Any]:
        protect_ledger_json = dependencies.protect_ledger_json
        return await protect_ledger_json("capabilities")

    @router.get("/api/unifi-protect/stats")
    async def api_unifi_protect_stats() -> dict[str, Any]:
        protect_ledger_json = dependencies.protect_ledger_json
        return await protect_ledger_json("stats")

    @router.get("/api/unifi-protect/events")
    async def api_unifi_protect_events(
        event_type: str = "",
        camera_id: str = "",
        detection_type: str = "",
        from_at: Optional[datetime] = Query(default=None, alias="from"),
        to_at: Optional[datetime] = Query(default=None, alias="to"),
        has_snapshot: Optional[bool] = None,
        limit: int = Query(default=100, ge=1, le=500),
        cursor: str = "",
    ) -> dict[str, Any]:
        protect_ledger_json = dependencies.protect_ledger_json
        return await protect_ledger_json(
            "events",
            event_type=event_type,
            camera_id=camera_id,
            detection_type=detection_type,
            **{
                "from": from_at.isoformat() if from_at else None,
                "to": to_at.isoformat() if to_at else None,
                "has_snapshot": has_snapshot,
                "limit": limit,
                "cursor": cursor,
            },
        )

    @router.get("/api/unifi-protect/recognitions")
    async def api_unifi_protect_recognitions(
        kind: str = "",
        value: str = "",
        camera_id: str = "",
        is_known: Optional[bool] = None,
        from_at: Optional[datetime] = Query(default=None, alias="from"),
        to_at: Optional[datetime] = Query(default=None, alias="to"),
        limit: int = Query(default=100, ge=1, le=500),
        cursor: str = "",
    ) -> dict[str, Any]:
        protect_ledger_json = dependencies.protect_ledger_json
        return await protect_ledger_json(
            "recognitions",
            kind=kind,
            value=value,
            camera_id=camera_id,
            is_known=is_known,
            **{
                "from": from_at.isoformat() if from_at else None,
                "to": to_at.isoformat() if to_at else None,
                "limit": limit,
                "cursor": cursor,
            },
        )

    @router.get("/api/unifi-protect/recognitions/{recognition_id}")
    async def api_unifi_protect_recognition_detail(recognition_id: int) -> dict[str, Any]:
        protect_ledger_json = dependencies.protect_ledger_json
        return await protect_ledger_json("recognition_detail", recognition_id=recognition_id)

    @router.get("/api/unifi-protect/license-plates/daily")
    async def api_unifi_protect_daily_license_plates(
        from_at: datetime = Query(alias="from"),
        to_at: datetime = Query(alias="to"),
    ) -> dict[str, Any]:
        protect_ledger_json = dependencies.protect_ledger_json
        return await protect_ledger_json(
            "daily_license_plates",
            **{"from": from_at.isoformat(), "to": to_at.isoformat()},
        )

    @router.get("/api/unifi-protect/bollards")
    async def api_unifi_protect_bollards() -> dict[str, Any]:
        protect_ledger_json = dependencies.protect_ledger_json
        payload = await protect_ledger_json("bollards")
        for monitor in payload.get("camera_monitors", []):
            for key in (
                "baseline_url", "latest_url", "overlay_url",
                "baseline_crop_url", "latest_crop_url", "overlay_crop_url",
                "ai_heatmap_url",
            ):
                if monitor.get(key):
                    monitor[key] = str(monitor[key]).replace(
                        "/api/v1/bollards/", "/api/unifi-protect/bollards/", 1
                    )
        for monitor in payload.get("asset_monitors", []):
            for key in (
                "baseline_url", "latest_url", "overlay_url",
                "baseline_crop_url", "latest_crop_url", "overlay_crop_url",
                "ai_heatmap_url",
            ):
                if monitor.get(key):
                    monitor[key] = str(monitor[key]).replace(
                        "/api/v1/bollards/", "/api/unifi-protect/bollards/", 1
                    )
        for region in payload.get("regions", []):
            if region.get("baseline_url"):
                region["baseline_url"] = str(region["baseline_url"]).replace(
                    "/api/v1/bollards/", "/api/unifi-protect/bollards/", 1
                )
        for incident in payload.get("incidents", []):
            for evidence in (incident.get("evidence") or {}).values():
                for key in ("before_url", "after_url"):
                    if evidence.get(key):
                        evidence[key] = str(evidence[key]).replace(
                            "/api/v1/bollards/", "/api/unifi-protect/bollards/", 1
                        )
        return payload

    @router.get("/api/unifi-protect/bollards/mobile-notifications")
    async def api_unifi_protect_bollard_mobile_notifications() -> dict[str, Any]:
        bollard_mobile_notification_payload = dependencies.bollard_mobile_notification_payload
        protect_ledger_json = dependencies.protect_ledger_json
        status = await protect_ledger_json("bollards")
        return bollard_mobile_notification_payload(status)

    @router.post("/api/unifi-protect/bollards/mobile-notifications/test")
    async def api_test_unifi_protect_bollard_mobile_notification() -> dict[str, Any]:
        ALARM_APP_URL = dependencies.ALARM_APP_URL
        NTFY_BOLLARDS_TOPIC = dependencies.NTFY_BOLLARDS_TOPIC
        logger = dependencies.logger
        publish_ntfy_message = dependencies.publish_ntfy_message
        if not NTFY_BOLLARDS_TOPIC:
            raise HTTPException(status_code=503, detail="Varselkanalen er ikke konfigurert")
        try:
            await asyncio.to_thread(
                publish_ntfy_message,
                NTFY_BOLLARDS_TOPIC,
                "Testvarsel - pullerter og trapp ved Solstudio",
                "Test fra Fibaro10: mobilvarsling for pullert- og trappekontrollen virker. Ingen hendelse er registrert.",
                "white_check_mark,car",
                "4",
                f"{ALARM_APP_URL}/?section=pullerter",
            )
        except Exception as error:
            logger.warning("Kunne ikke sende testvarsel for pullerter: %s", error, exc_info=True)
            raise HTTPException(status_code=502, detail="Testvarselet kunne ikke sendes") from error
        return {"sent": True}

    @router.get("/api/unifi-protect/events/{source_event_id}/snapshot")
    async def api_unifi_protect_snapshot(source_event_id: str) -> Response:
        protect_ledger_client = dependencies.protect_ledger_client
        client = protect_ledger_client()
        try:
            content, content_type = await asyncio.to_thread(client.snapshot, source_event_id)
        except ProtectLedgerError as error:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        return Response(content=content, media_type=content_type, headers={"Cache-Control": "private, max-age=3600"})

    @router.get("/api/unifi-protect/recognitions/{recognition_id}/snapshot")
    async def api_unifi_protect_recognition_snapshot(recognition_id: int) -> Response:
        protect_ledger_client = dependencies.protect_ledger_client
        client = protect_ledger_client()
        try:
            content, content_type = await asyncio.to_thread(client.recognition_snapshot, recognition_id)
        except ProtectLedgerError as error:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        return Response(content=content, media_type=content_type, headers={"Cache-Control": "private, max-age=3600"})

    @router.get("/api/unifi-protect/bollards/regions/{region_id}/baseline")
    async def api_unifi_protect_bollard_baseline(region_id: int) -> Response:
        bollard_image_cache_control = dependencies.bollard_image_cache_control
        protect_ledger_client = dependencies.protect_ledger_client
        client = protect_ledger_client()
        try:
            content, content_type = await asyncio.to_thread(client.bollard_region_baseline, region_id)
        except ProtectLedgerError as error:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        return Response(content=content, media_type=content_type, headers={"Cache-Control": bollard_image_cache_control("baseline")})

    @router.get("/api/unifi-protect/bollards/cameras/{camera_id}/{kind}")
    async def api_unifi_protect_bollard_camera_image(camera_id: str, kind: str) -> Response:
        bollard_image_cache_control = dependencies.bollard_image_cache_control
        protect_ledger_client = dependencies.protect_ledger_client
        client = protect_ledger_client()
        try:
            content, content_type = await asyncio.to_thread(
                client.bollard_camera_image,
                camera_id,
                kind,
            )
        except ProtectLedgerError as error:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        return Response(content=content, media_type=content_type, headers={"Cache-Control": bollard_image_cache_control(kind)})

    @router.get("/api/unifi-protect/bollards/cameras/{camera_id}/{kind}/crop")
    async def api_unifi_protect_bollard_camera_crop(camera_id: str, kind: str) -> Response:
        bollard_image_cache_control = dependencies.bollard_image_cache_control
        protect_ledger_client = dependencies.protect_ledger_client
        client = protect_ledger_client()
        try:
            content, content_type = await asyncio.to_thread(
                client.bollard_camera_crop,
                camera_id,
                kind,
            )
        except ProtectLedgerError as error:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        return Response(content=content, media_type=content_type, headers={"Cache-Control": bollard_image_cache_control(kind)})

    @router.get("/api/unifi-protect/bollards/assets/{asset_key}/{kind}")
    async def api_unifi_protect_bollard_asset_image(asset_key: str, kind: str) -> Response:
        bollard_image_cache_control = dependencies.bollard_image_cache_control
        protect_ledger_client = dependencies.protect_ledger_client
        client = protect_ledger_client()
        try:
            content, content_type = await asyncio.to_thread(
                client.bollard_asset_image,
                asset_key,
                kind,
            )
        except ProtectLedgerError as error:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        return Response(content=content, media_type=content_type, headers={"Cache-Control": bollard_image_cache_control(kind)})

    @router.get("/api/unifi-protect/bollards/incidents/{incident_id}/images/{camera_id}/{kind}")
    async def api_unifi_protect_bollard_incident_image(
        incident_id: int,
        camera_id: str,
        kind: str,
    ) -> Response:
        bollard_image_cache_control = dependencies.bollard_image_cache_control
        protect_ledger_client = dependencies.protect_ledger_client
        client = protect_ledger_client()
        try:
            content, content_type = await asyncio.to_thread(
                client.bollard_incident_image,
                incident_id,
                camera_id,
                kind,
            )
        except ProtectLedgerError as error:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": bollard_image_cache_control(kind, historical=True)},
        )

    @router.post("/api/hc3/doors/poll-sync")
    async def api_hc3_doors_poll_sync():
        run_hc3_door_poll_once = dependencies.run_hc3_door_poll_once
        result = await run_hc3_door_poll_once("manual_api")
        return {"status": "ok" if result.get("ok") else "error", **result}

    @router.get("/api/hc3/door-events/json")
    async def api_hc3_door_events_json(limit: int = Query(200, ge=1, le=5000)):
        async_session = dependencies.async_session
        row_to_dict = dependencies.row_to_dict
        async with async_session() as session:
            result = await session.execute(select(DoorEvent).order_by(DoorEvent.timestamp.desc()).limit(limit))
            rows = result.scalars().all()
        return {"count": len(rows), "rows": [row_to_dict(row, DOOR_EVENT_COLUMNS) for row in rows]}

    @router.get("/api/hc3/doors/status")
    async def api_hc3_doors_status(
        history_limit: int = Query(50, ge=1, le=500),
        period_limit: int = Query(80, ge=1, le=500),
    ):
        DOOR_SENSOR_CONFIG = dependencies.DOOR_SENSOR_CONFIG
        DOOR_SENSOR_IDS = dependencies.DOOR_SENSOR_IDS
        async_session = dependencies.async_session
        door_age_label = dependencies.door_age_label
        door_change_rows = dependencies.door_change_rows
        door_change_text = dependencies.door_change_text
        door_config_device_key = dependencies.door_config_device_key
        door_event_payload = dependencies.door_event_payload
        door_open_periods = dependencies.door_open_periods
        door_period_device_key = dependencies.door_period_device_key
        door_status_payload = dependencies.door_status_payload
        latest_door_event_by_device = dependencies.latest_door_event_by_device
        now = local_now_naive()
        raw_limit = max(history_limit * 20, period_limit * 20, len(DOOR_SENSOR_IDS) * 150, 1000)
        async with async_session() as session:
            history_result = await session.execute(
                select(DoorEvent)
                .where(DoorEvent.device_id.in_(DOOR_SENSOR_IDS))
                .order_by(DoorEvent.timestamp.desc(), DoorEvent.id.desc())
                .limit(raw_limit)
            )
            raw_rows = history_result.scalars().all()
            total_events = await session.scalar(select(func.count(DoorEvent.id)).where(DoorEvent.device_id.in_(DOOR_SENSOR_IDS)))

        change_rows_ascending = door_change_rows(list(reversed(raw_rows)))
        latest_status_by_device = latest_door_event_by_device(raw_rows)
        latest_change_by_device: Dict[int, DoorEvent] = {}
        for row in reversed(change_rows_ascending):
            if row.device_id is not None:
                latest_change_by_device.setdefault(int(row.device_id), row)
        newest_change_event = max(
            change_rows_ascending,
            key=lambda row: (normalize_local_naive(row.timestamp) or datetime.min, row.id or 0),
            default=None,
        )
        newest_at = normalize_local_naive(newest_change_event.timestamp) if newest_change_event else None
        periods = door_open_periods(change_rows_ascending, now)
        recent_periods_by_device: Dict[str, list[Dict[str, Any]]] = {}
        for period in periods:
            recent_periods_by_device.setdefault(door_period_device_key(period), []).append(period)
        raw_history_rows = raw_rows[:history_limit]
        change_history_rows = list(reversed(change_rows_ascending))[:history_limit]

        doors = []
        for config in DOOR_SENSOR_CONFIG:
            device_id = config.get("device_id")
            latest_row = latest_status_by_device.get(int(device_id)) if device_id is not None else None
            latest_change = latest_change_by_device.get(int(device_id)) if device_id is not None else None
            door = door_status_payload(config, latest_row, now, latest_change)
            door["recentPeriods"] = recent_periods_by_device.get(door_config_device_key(config), [])[:2]
            doors.append(door)
        doors = sorted(doors, key=lambda item: (str(item.get("groupKey") or ""), int(item.get("sortOrder") or 0), str(item.get("title") or "")))
        known = [door for door in doors if door["state"] != "unknown"]
        open_doors = [door for door in doors if door["state"] == "open"]
        closed_doors = [door for door in doors if door["state"] == "closed"]
        configured_doors = [door for door in doors if door["isConfigured"]]
        return {
            "generatedAt": now.isoformat(),
            "datakildePath": "/admin/datakilder/hc3_door_events",
            "summary": {
                "total": len(doors),
                "configured": len(configured_doors),
                "planned": len(doors) - len(configured_doors),
                "known": len(known),
                "open": len(open_doors),
                "closed": len(closed_doors),
                "unknown": len(doors) - len(known),
                "latestAt": newest_at.isoformat() if newest_at else None,
                "latestLabel": format_source_datetime_short(newest_at) if newest_at else "-",
                "latestAgeLabel": door_age_label(newest_at, now),
                "latestChangeText": door_change_text(newest_change_event),
                "events": int(total_events or 0),
                "changes": len(change_rows_ascending),
                "periods": len(periods),
                "activePeriods": len([period for period in periods if period.get("state") == "open"]),
            },
            "doors": doors,
            "changes": [door_event_payload(row, now) for row in change_history_rows],
            "events": [door_event_payload(row, now) for row in raw_history_rows],
            "periods": periods[:period_limit],
        }

    @router.get("/api/hc3/doors/sunroom-sessions")
    async def api_hc3_doors_sunroom_sessions():
        async_session = dependencies.async_session
        sunroom_door_session_payload = dependencies.sunroom_door_session_payload
        async with async_session() as session:
            return await sunroom_door_session_payload(session, notify=False)

    @router.get("/api/hc3/doors/sunroom-logic")
    async def api_hc3_doors_sunroom_logic(
        hours: int = Query(12, ge=1, le=72),
        limit: int = Query(180, ge=20, le=500),
    ):
        async_session = dependencies.async_session
        sunroom_logic_payload = dependencies.sunroom_logic_payload
        async with async_session() as session:
            return await sunroom_logic_payload(session, hours=hours, limit=limit)

    @router.get("/api/hc3/doors/alarm")
    async def api_hc3_doors_alarm(
        history_limit: int = Query(100, ge=10, le=500),
        day: Optional[str] = Query(None),
    ):
        async_session = dependencies.async_session
        parse_day = dependencies.parse_day
        sunroom_door_alarm_payload = dependencies.sunroom_door_alarm_payload
        history_day = parse_day(day) if day else None
        async with async_session() as session:
            return await sunroom_door_alarm_payload(session, history_limit=history_limit, history_day=history_day)

    @router.get("/api/hc3/doors/sunroom-overview")
    async def api_hc3_doors_sunroom_overview(days: int = Query(2, ge=1, le=30), day: Optional[str] = Query(None)):
        async_session = dependencies.async_session
        sunroom_room_overview_payload = dependencies.sunroom_room_overview_payload
        async with async_session() as session:
            return await sunroom_room_overview_payload(session, days=days, day=day)

    @router.get("/api/hc3/doors/sunroom-sessions/{room_id}")
    async def api_hc3_doors_sunroom_room_detail(
        room_id: str,
        days: int = Query(14, ge=1, le=90),
        limit: int = Query(120, ge=10, le=500),
    ):
        async_session = dependencies.async_session
        sunroom_room_detail_payload = dependencies.sunroom_room_detail_payload
        async with async_session() as session:
            return await sunroom_room_detail_payload(session, room_id, days=days, limit=limit)

    return RouterBundle(router, {
        "api_hc3_door_events_json": api_hc3_door_events_json,
        "api_hc3_doors_alarm": api_hc3_doors_alarm,
        "api_hc3_doors_poll_sync": api_hc3_doors_poll_sync,
        "api_hc3_doors_status": api_hc3_doors_status,
        "api_hc3_doors_sunroom_logic": api_hc3_doors_sunroom_logic,
        "api_hc3_doors_sunroom_overview": api_hc3_doors_sunroom_overview,
        "api_hc3_doors_sunroom_room_detail": api_hc3_doors_sunroom_room_detail,
        "api_hc3_doors_sunroom_sessions": api_hc3_doors_sunroom_sessions,
        "api_test_unifi_protect_bollard_mobile_notification": api_test_unifi_protect_bollard_mobile_notification,
        "api_unifi_protect_bollard_asset_image": api_unifi_protect_bollard_asset_image,
        "api_unifi_protect_bollard_baseline": api_unifi_protect_bollard_baseline,
        "api_unifi_protect_bollard_camera_crop": api_unifi_protect_bollard_camera_crop,
        "api_unifi_protect_bollard_camera_image": api_unifi_protect_bollard_camera_image,
        "api_unifi_protect_bollard_incident_image": api_unifi_protect_bollard_incident_image,
        "api_unifi_protect_bollard_mobile_notifications": api_unifi_protect_bollard_mobile_notifications,
        "api_unifi_protect_bollards": api_unifi_protect_bollards,
        "api_unifi_protect_cameras": api_unifi_protect_cameras,
        "api_unifi_protect_capabilities": api_unifi_protect_capabilities,
        "api_unifi_protect_daily_license_plates": api_unifi_protect_daily_license_plates,
        "api_unifi_protect_events": api_unifi_protect_events,
        "api_unifi_protect_recognition_detail": api_unifi_protect_recognition_detail,
        "api_unifi_protect_recognition_snapshot": api_unifi_protect_recognition_snapshot,
        "api_unifi_protect_recognitions": api_unifi_protect_recognitions,
        "api_unifi_protect_snapshot": api_unifi_protect_snapshot,
        "api_unifi_protect_stats": api_unifi_protect_stats,
        "api_unifi_protect_status": api_unifi_protect_status,
    }, dependencies)
