"""Linking HTTP routes; runtime services are supplied by composition."""

from dataclasses import dataclass
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request
from fibaro_core.models import ParkingSunLinkCandidate
from fibaro_core.models import ParkingSunLinkMatch
from fibaro_core.models import ParkingSunLinkProcessed
from fibaro_core.models import ParkingVehicle
from fibaro_core.routers.bundle import RouterBundle
from fibaro_core.schemas import ParkingSunLinkCandidateUpdate
from fibaro_core.schemas import ParkingSunLinkSettingsUpdate
from fibaro_core.schemas import ParkingSunLinkWorkerResultsIn
from fibaro_core.schemas import ParkingSunLinkWorkerStatusIn
from parking_vehicle_helpers import normalize_plate
from sqlalchemy.dialects.postgresql import insert as pg_insert
from time_formatting import local_now_naive
from time_formatting import normalize_local_naive
from typing import Any, Callable
from value_parsing import int_or_zero


@dataclass
class Dependencies:
    PARKING_SUN_LINK_CONFIRMED: Any
    PARKING_SUN_LINK_REJECTED: Any
    SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS: Any
    async_session: Callable[..., Any]
    clear_summary_cache: Callable[..., Any]
    get_parking_sun_link_state: Callable[..., Any]
    has_koble_worker_access: Callable[..., Any]
    logger: Any
    parking_sun_link_assessment: Callable[..., Any]
    parking_sun_link_probability: Callable[..., Any]
    parking_sun_link_status_value: Callable[..., Any]
    redirect_with_query_params: Callable[..., Any]
    refresh_parking_sun_link_candidate_pairs: Callable[..., Any]
    refresh_parking_sun_link_state_counts: Callable[..., Any]
    require_settings_access: Callable[..., Any]
    reset_parking_sun_link_data: Callable[..., Any]
    run_sun2_axis_snapshot_link_once: Callable[..., Any]
    update_parking_sun_link_import_status: Callable[..., Any]


def create_router(dependencies: Dependencies) -> RouterBundle:
    router = APIRouter()


    @router.post("/api/actions/koble/start")
    async def api_v2_koble_start(request: Request):
        async_session = dependencies.async_session
        get_parking_sun_link_state = dependencies.get_parking_sun_link_state
        require_settings_access = dependencies.require_settings_access
        update_parking_sun_link_import_status = dependencies.update_parking_sun_link_import_status
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        async with async_session() as session:
            state = await get_parking_sun_link_state(session)
            state.enabled = True
            state.status = "venter"
            state.status_text = "Koblingsjobben er aktiv og venter på worker."
            state.last_started_at = local_now_naive()
            state.last_finished_at = None
            state.last_error = None
            state.updated_at = local_now_naive()
            await update_parking_sun_link_import_status(session, state)
            await session.commit()
        return {"status": "ok", "message": "Koblingsjobben er startet."}

    @router.post("/api/actions/koble/stop")
    async def api_v2_koble_stop(request: Request):
        async_session = dependencies.async_session
        get_parking_sun_link_state = dependencies.get_parking_sun_link_state
        require_settings_access = dependencies.require_settings_access
        update_parking_sun_link_import_status = dependencies.update_parking_sun_link_import_status
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        async with async_session() as session:
            state = await get_parking_sun_link_state(session)
            state.enabled = False
            state.status = "stoppet"
            state.status_text = "Koblingsjobben er stoppet fra Fibaro10."
            state.last_finished_at = local_now_naive()
            state.updated_at = local_now_naive()
            await update_parking_sun_link_import_status(session, state)
            await session.commit()
        return {"status": "ok", "message": "Koblingsjobben er stoppet."}

    @router.post("/api/actions/koble/restart")
    async def api_v2_koble_restart(request: Request):
        async_session = dependencies.async_session
        get_parking_sun_link_state = dependencies.get_parking_sun_link_state
        require_settings_access = dependencies.require_settings_access
        reset_parking_sun_link_data = dependencies.reset_parking_sun_link_data
        update_parking_sun_link_import_status = dependencies.update_parking_sun_link_import_status
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        async with async_session() as session:
            state = await get_parking_sun_link_state(session)
            await reset_parking_sun_link_data(session, state, enabled=True)
            await update_parking_sun_link_import_status(session, state)
            await session.commit()
        return {"status": "ok", "message": "Koblingsjobben starter fra nyeste parkering."}

    @router.patch("/api/koble/settings/{state_id}")
    async def api_v2_koble_settings_update(request: Request, state_id: int, data: ParkingSunLinkSettingsUpdate):
        async_session = dependencies.async_session
        get_parking_sun_link_state = dependencies.get_parking_sun_link_state
        require_settings_access = dependencies.require_settings_access
        reset_parking_sun_link_data = dependencies.reset_parking_sun_link_data
        update_parking_sun_link_import_status = dependencies.update_parking_sun_link_import_status
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        if state_id != 1:
            raise HTTPException(status_code=404, detail="Koble-innstillinger ikke funnet")
        values = data.dict(exclude_unset=True)
        if not values:
            raise HTTPException(status_code=400, detail="Ingen endringer")
        async with async_session() as session:
            state = await get_parking_sun_link_state(session)
            changed = False
            for key, value in values.items():
                if value is None:
                    continue
                if getattr(state, key) != value:
                    setattr(state, key, value)
                    changed = True
            if changed:
                await reset_parking_sun_link_data(session, state, enabled=True)
                state.status_text = "Parametere er endret. Jobben starter fra nyeste parkering."
            await update_parking_sun_link_import_status(session, state)
            await session.commit()
        return {"status": "ok", "message": "Koble-parametere er lagret."}

    @router.patch("/api/koble/candidates/{candidate_id}")
    async def api_v2_koble_candidate_update(request: Request, candidate_id: int, data: ParkingSunLinkCandidateUpdate):
        PARKING_SUN_LINK_CONFIRMED = dependencies.PARKING_SUN_LINK_CONFIRMED
        PARKING_SUN_LINK_REJECTED = dependencies.PARKING_SUN_LINK_REJECTED
        async_session = dependencies.async_session
        clear_summary_cache = dependencies.clear_summary_cache
        get_parking_sun_link_state = dependencies.get_parking_sun_link_state
        parking_sun_link_assessment = dependencies.parking_sun_link_assessment
        parking_sun_link_probability = dependencies.parking_sun_link_probability
        parking_sun_link_status_value = dependencies.parking_sun_link_status_value
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        values = data.dict(exclude_unset=True)
        async with async_session() as session:
            candidate = await session.get(ParkingSunLinkCandidate, candidate_id)
            if not candidate:
                raise HTTPException(status_code=404, detail="Koblingskandidat ikke funnet")
            actor = getattr(request.state, "access_key_name", None) or getattr(request.state, "auth_username", None) or "Fibaro10"
            now_value = local_now_naive()
            if "note" in values:
                candidate.note = (values.get("note") or "").strip() or None
            if "status" in values:
                new_status = parking_sun_link_status_value(values.get("status"))
                candidate.status = new_status
                if new_status == PARKING_SUN_LINK_CONFIRMED:
                    candidate.confirmed_at = now_value
                    candidate.confirmed_by = actor
                    candidate.rejected_at = None
                    candidate.rejected_by = None
                    candidate.confidence = 100.0
                    vehicle = await session.get(ParkingVehicle, candidate.plate)
                    if vehicle:
                        vehicle.sun2_id = candidate.sun2_id
                        vehicle.updated_at = now_value
                elif new_status == PARKING_SUN_LINK_REJECTED:
                    candidate.rejected_at = now_value
                    candidate.rejected_by = actor
                    candidate.confirmed_at = None
                    candidate.confirmed_by = None
                else:
                    candidate.confirmed_at = None
                    candidate.confirmed_by = None
                    candidate.rejected_at = None
                    candidate.rejected_by = None
                    state = await get_parking_sun_link_state(session)
                    candidate.confidence = parking_sun_link_probability(
                        candidate.matches_count,
                        candidate.avg_delta_minutes,
                        min_matches=state.min_matches,
                        parking_match_count=candidate.parking_match_count,
                        match_days_count=candidate.match_days_count,
                        plate_candidate_count=candidate.plate_candidate_count,
                        sun2_candidate_count=candidate.sun2_candidate_count,
                        competitor_matches_count=candidate.competitor_matches_count,
                    )
                state = await get_parking_sun_link_state(session)
                candidate.assessment = parking_sun_link_assessment(
                    candidate.status,
                    candidate.confidence,
                    min_matches=state.min_matches,
                    parking_match_count=candidate.parking_match_count,
                    plate_candidate_count=candidate.plate_candidate_count,
                    sun2_candidate_count=candidate.sun2_candidate_count,
                    competitor_matches_count=candidate.competitor_matches_count,
                )
            candidate.updated_at = now_value
            await session.commit()
        clear_summary_cache("parking")
        return {"status": "ok", "message": f"Kobling {candidate.plate} / {candidate.sun2_id} er oppdatert."}

    @router.get("/api/koble/worker/config")
    async def api_v2_koble_worker_config(request: Request):
        async_session = dependencies.async_session
        get_parking_sun_link_state = dependencies.get_parking_sun_link_state
        has_koble_worker_access = dependencies.has_koble_worker_access
        refresh_parking_sun_link_state_counts = dependencies.refresh_parking_sun_link_state_counts
        update_parking_sun_link_import_status = dependencies.update_parking_sun_link_import_status
        if not has_koble_worker_access(request):
            raise HTTPException(status_code=401, detail="Mangler gyldig koble-token")
        async with async_session() as session:
            state = await get_parking_sun_link_state(session)
            await refresh_parking_sun_link_state_counts(session, state)
            state.last_worker_seen_at = local_now_naive()
            await update_parking_sun_link_import_status(session, state)
            await session.commit()
        return {
            "enabled": bool(state.enabled),
            "generation": int_or_zero(state.generation),
            "min_matches": int_or_zero(state.min_matches),
            "max_minutes": int_or_zero(state.max_minutes),
            "recent_days": int_or_zero(state.recent_days),
            "idle_sleep_seconds": int_or_zero(state.idle_sleep_seconds),
        }

    @router.post("/api/koble/worker/status")
    async def api_v2_koble_worker_status(request: Request, data: ParkingSunLinkWorkerStatusIn):
        async_session = dependencies.async_session
        get_parking_sun_link_state = dependencies.get_parking_sun_link_state
        has_koble_worker_access = dependencies.has_koble_worker_access
        update_parking_sun_link_import_status = dependencies.update_parking_sun_link_import_status
        if not has_koble_worker_access(request):
            raise HTTPException(status_code=401, detail="Mangler gyldig koble-token")
        now_value = local_now_naive()
        async with async_session() as session:
            state = await get_parking_sun_link_state(session)
            if data.generation != state.generation:
                return {"status": "stale", "generation": int_or_zero(state.generation)}
            state.last_worker_seen_at = now_value
            state.status = (data.status or state.status or "kjorer").strip()[:40]
            state.status_text = data.status_text or state.status_text
            state.last_error = data.last_error
            if data.last_error:
                state.status = "feil"
            for key in [
                "processed_count",
                "matched_count",
                "candidate_count",
                "strong_candidate_count",
                "checked_plate_count",
                "last_processed_parking_id",
                "last_processed_plate",
            ]:
                value = getattr(data, key)
                if value is not None:
                    setattr(state, key, value)
            if data.last_processed_at:
                state.last_processed_at = normalize_local_naive(data.last_processed_at)
            state.raw = data.raw or {}
            state.updated_at = now_value
            await update_parking_sun_link_import_status(session, state)
            await session.commit()
        return {"status": "ok", "generation": int_or_zero(state.generation)}

    @router.post("/api/koble/worker/results")
    async def api_v2_koble_worker_results(request: Request, data: ParkingSunLinkWorkerResultsIn):
        async_session = dependencies.async_session
        get_parking_sun_link_state = dependencies.get_parking_sun_link_state
        has_koble_worker_access = dependencies.has_koble_worker_access
        refresh_parking_sun_link_candidate_pairs = dependencies.refresh_parking_sun_link_candidate_pairs
        refresh_parking_sun_link_state_counts = dependencies.refresh_parking_sun_link_state_counts
        update_parking_sun_link_import_status = dependencies.update_parking_sun_link_import_status
        if not has_koble_worker_access(request):
            raise HTTPException(status_code=401, detail="Mangler gyldig koble-token")
        now_value = local_now_naive()
        async with async_session() as session:
            state = await get_parking_sun_link_state(session)
            if data.generation != state.generation:
                return {"status": "stale", "generation": int_or_zero(state.generation)}
            processed_values = []
            for row in data.processed:
                plate_value = normalize_plate(row.plate)
                if not plate_value or int_or_zero(row.parking_record_id) <= 0:
                    continue
                processed_values.append(
                    {
                        "generation": data.generation,
                        "parking_record_id": int(row.parking_record_id),
                        "plate": plate_value,
                        "parking_start_at": normalize_local_naive(row.parking_start_at) if row.parking_start_at else None,
                        "matches_found": int_or_zero(row.matches_found),
                        "checked_at": now_value,
                    }
                )
            if processed_values:
                stmt = pg_insert(ParkingSunLinkProcessed).values(processed_values)
                await session.execute(
                    stmt.on_conflict_do_update(
                        index_elements=["generation", "parking_record_id"],
                        set_={
                            "plate": stmt.excluded.plate,
                            "parking_start_at": stmt.excluded.parking_start_at,
                            "matches_found": stmt.excluded.matches_found,
                            "checked_at": stmt.excluded.checked_at,
                        },
                    )
                )

            touched_pairs: set[tuple[str, str]] = set()
            match_values = []
            for row in data.matches:
                plate_value = normalize_plate(row.plate)
                sun2_id = str(row.sun2_id or "").strip()
                if not plate_value or not sun2_id or int_or_zero(row.sun_session_id) <= 0:
                    continue
                touched_pairs.add((plate_value, sun2_id))
                match_values.append(
                    {
                        "generation": data.generation,
                        "plate": plate_value,
                        "sun2_id": sun2_id,
                        "parking_record_id": int(row.parking_record_id),
                        "parking_id": row.parking_id,
                        "source_system": row.source_system,
                        "parking_start_at": normalize_local_naive(row.parking_start_at) if row.parking_start_at else None,
                        "sun_session_id": int(row.sun_session_id),
                        "source_session_id": row.source_session_id,
                        "sun_started_at": normalize_local_naive(row.sun_started_at) if row.sun_started_at else None,
                        "room_id": row.room_id,
                        "room": row.room,
                        "user_name": row.user_name,
                        "duration_minutes": row.duration_minutes,
                        "paid_amount_kr": row.paid_amount_kr,
                        "fee_inc_vat": row.fee_inc_vat,
                        "delta_minutes": row.delta_minutes,
                        "created_at": now_value,
                    }
                )
            if match_values:
                stmt = pg_insert(ParkingSunLinkMatch).values(match_values)
                await session.execute(
                    stmt.on_conflict_do_update(
                        index_elements=["generation", "parking_record_id", "sun_session_id"],
                        set_={
                            "plate": stmt.excluded.plate,
                            "sun2_id": stmt.excluded.sun2_id,
                            "parking_id": stmt.excluded.parking_id,
                            "source_system": stmt.excluded.source_system,
                            "parking_start_at": stmt.excluded.parking_start_at,
                            "source_session_id": stmt.excluded.source_session_id,
                            "sun_started_at": stmt.excluded.sun_started_at,
                            "room_id": stmt.excluded.room_id,
                            "room": stmt.excluded.room,
                            "user_name": stmt.excluded.user_name,
                            "duration_minutes": stmt.excluded.duration_minutes,
                            "paid_amount_kr": stmt.excluded.paid_amount_kr,
                            "fee_inc_vat": stmt.excluded.fee_inc_vat,
                            "delta_minutes": stmt.excluded.delta_minutes,
                        },
                    )
                )
                await refresh_parking_sun_link_candidate_pairs(session, data.generation, touched_pairs, min_matches=state.min_matches)
            if data.status:
                state.status = (data.status.status or "kjorer").strip()[:40]
                state.status_text = data.status.status_text or state.status_text
                state.last_error = data.status.last_error
            elif state.enabled:
                state.status = "kjorer"
                state.status_text = "Koblingsjobben behandler parkeringer."
            state.last_worker_seen_at = now_value
            state.last_processed_at = now_value if processed_values else state.last_processed_at
            if processed_values:
                state.last_processed_parking_id = processed_values[-1]["parking_record_id"]
                state.last_processed_plate = processed_values[-1]["plate"]
            await refresh_parking_sun_link_state_counts(session, state)
            await update_parking_sun_link_import_status(session, state)
            await session.commit()
        return {"status": "ok", "generation": int_or_zero(state.generation), "matches": len(match_values), "processed": len(processed_values)}

    @router.post("/soling/enkeltimer/koble-bilder")
    async def sun2_sessions_link_images(request: Request):
        SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS = dependencies.SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS
        logger = dependencies.logger
        redirect_with_query_params = dependencies.redirect_with_query_params
        require_settings_access = dependencies.require_settings_access
        run_sun2_axis_snapshot_link_once = dependencies.run_sun2_axis_snapshot_link_once
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        form = await request.form()
        try:
            days = int(form.get("days") or 7)
        except (TypeError, ValueError):
            days = 7
        try:
            limit = int(form.get("limit") or 5000)
        except (TypeError, ValueError):
            limit = 5000
        try:
            tolerance_seconds = int(form.get("tolerance_seconds") or SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS)
        except (TypeError, ValueError):
            tolerance_seconds = SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS
        replace = str(form.get("replace") or "").strip().lower() in {"1", "true", "yes", "ja", "on"}
        try:
            result = await run_sun2_axis_snapshot_link_once(
                "manual_jinja",
                days=days,
                limit=limit,
                tolerance_seconds=tolerance_seconds,
                replace=replace,
            )
            message = (
                f"Koblet {result.get('linked', 0)} bilder. "
                f"{result.get('already_linked', 0)} hadde bilde fra før, {result.get('no_match', 0)} manglet treff."
            )
            return redirect_with_query_params(request, "/soling/enkeltimer", message=message)
        except Exception as exc:
            logger.exception("Axis-bildekobling for soltimer feilet")
            return redirect_with_query_params(request, "/soling/enkeltimer", error=str(exc))

    return RouterBundle(router, {
        "api_v2_koble_candidate_update": api_v2_koble_candidate_update,
        "api_v2_koble_restart": api_v2_koble_restart,
        "api_v2_koble_settings_update": api_v2_koble_settings_update,
        "api_v2_koble_start": api_v2_koble_start,
        "api_v2_koble_stop": api_v2_koble_stop,
        "api_v2_koble_worker_config": api_v2_koble_worker_config,
        "api_v2_koble_worker_results": api_v2_koble_worker_results,
        "api_v2_koble_worker_status": api_v2_koble_worker_status,
        "sun2_sessions_link_images": sun2_sessions_link_images,
    }, dependencies)
