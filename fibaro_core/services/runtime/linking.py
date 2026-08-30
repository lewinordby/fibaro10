"""Linking services with explicit process dependencies."""

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from fastapi import Request
from fibaro_core.models import ImportJobStatus
from fibaro_core.models import ParkingSession
from fibaro_core.models import ParkingSunLinkCandidate
from fibaro_core.models import ParkingSunLinkJobState
from fibaro_core.models import ParkingSunLinkMatch
from fibaro_core.models import ParkingSunLinkProcessed
from fibaro_core.models import ParkingVehicle
from fibaro_core.models import Sun2TanningSession
from sqlalchemy import Date
from sqlalchemy import and_
from sqlalchemy import cast
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import tuple_
from sun2_helpers import sun2_room_label
from time_formatting import api_local_iso
from time_formatting import local_now_naive
from time_formatting import normalize_local_naive
from typing import Any
from typing import Any, Callable
from typing import Dict
from typing import Iterable
from typing import Optional
from urllib.parse import quote
from value_parsing import float_or_zero
from value_parsing import int_or_zero


@dataclass
class Dependencies:
    CAR_INFO_APP_TOKEN: Any
    KOBLE_WORKER_TOKEN: Any
    PARKING_SUN_LINK_CONFIRMED: Any
    PARKING_SUN_LINK_PENDING: Any
    PARKING_SUN_LINK_REJECTED: Any
    PARKING_SUN_LINK_STATUSES: Any
    import_job_definition: Callable[..., Any]


def create_service(dependencies: Dependencies):

    def has_koble_worker_access(request: Request) -> bool:
        CAR_INFO_APP_TOKEN = dependencies.CAR_INFO_APP_TOKEN
        KOBLE_WORKER_TOKEN = dependencies.KOBLE_WORKER_TOKEN
        token = (request.headers.get("x-koble-token") or request.query_params.get("koble_token") or "").strip()
        allowed_tokens = {value for value in [KOBLE_WORKER_TOKEN, CAR_INFO_APP_TOKEN] if value}
        return bool(token and token in allowed_tokens)

    def is_koble_worker_request_path(path: str) -> bool:
        return bool((path or "").startswith("/api/koble/worker/"))

    async def parking_sun_link_candidates(
        session: Any,
        reference_time: datetime,
        min_matches: int = 2,
        max_minutes: int = 3,
        recent_days: int = 0,
        limit: int = 250,
    ) -> Dict[str, Any]:
        parking_plate = func.upper(func.replace(func.coalesce(ParkingSession.car_license_number, ""), " ", ""))
        session_sun2_id = func.trim(func.coalesce(Sun2TanningSession.sun2_user_id, ""))
        delta_seconds = func.extract("epoch", Sun2TanningSession.started_at - ParkingSession.start_time)
        recent_cutoff = reference_time - timedelta(days=recent_days) if recent_days > 0 else None
        recent_plates_query = (
            select(parking_plate.label("plate"))
            .where(ParkingSession.car_license_number.is_not(None))
            .where(parking_plate != "")
        )
        if recent_cutoff:
            recent_plates_query = recent_plates_query.where(ParkingSession.start_time >= recent_cutoff)
        recent_plates = recent_plates_query.distinct().subquery()
        match_conditions = [
            ParkingSession.start_time.is_not(None),
            ParkingSession.car_license_number.is_not(None),
            Sun2TanningSession.started_at.is_not(None),
            session_sun2_id != "",
            parking_plate.in_(select(recent_plates.c.plate)),
            delta_seconds >= 0,
            delta_seconds <= max_minutes * 60,
        ]

        base_from = (
            select()
            .select_from(ParkingSession)
            .outerjoin(ParkingVehicle, ParkingVehicle.plate == parking_plate)
            .join(Sun2TanningSession, and_(Sun2TanningSession.started_at >= ParkingSession.start_time, session_sun2_id != ""))
            .where(*match_conditions)
        )
        count_expr = func.count(func.distinct(Sun2TanningSession.id)).label("matches_count")
        parking_match_count_expr = func.count(func.distinct(ParkingSession.id)).label("parking_match_count")
        latest_parking_expr = func.max(ParkingSession.start_time)
        candidate_stmt = (
            base_from.with_only_columns(
                parking_plate.label("plate"),
                session_sun2_id.label("sun2_id"),
                count_expr,
                parking_match_count_expr,
                func.min(ParkingSession.start_time).label("first_match_at"),
                latest_parking_expr.label("last_match_at"),
                func.avg(delta_seconds / 60.0).label("avg_delta_minutes"),
                func.max(ParkingVehicle.navn).label("vehicle_name"),
                func.max(ParkingVehicle.omrade).label("vehicle_area"),
                func.max(Sun2TanningSession.user_name).label("sun2_user_name"),
                func.max(ParkingVehicle.parkering_count).label("parking_count"),
                func.max(ParkingVehicle.paid_total).label("paid_total"),
            )
            .group_by(parking_plate, session_sun2_id)
            .having(func.count(func.distinct(ParkingSession.id)) >= min_matches)
            .order_by(count_expr.desc(), latest_parking_expr.desc())
            .limit(limit)
        )
        recent_plate_count = int_or_zero((await session.execute(select(func.count()).select_from(recent_plates))).scalar_one_or_none())
        candidate_rows_raw = (await session.execute(candidate_stmt)).all()
        candidate_pairs = [(row.plate, row.sun2_id) for row in candidate_rows_raw if row.plate and row.sun2_id]

        match_rows: list[Dict[str, Any]] = []
        if candidate_pairs:
            match_stmt = (
                base_from.with_only_columns(
                    ParkingSession.id.label("parking_record_id"),
                    ParkingSession.parking_id.label("parking_id"),
                    ParkingSession.source_system.label("source_system"),
                    ParkingSession.start_time.label("parking_start_at"),
                    ParkingSession.end_time.label("parking_end_at"),
                    ParkingSession.status.label("parking_status"),
                    ParkingSession.fee_inc_vat.label("fee_inc_vat"),
                    parking_plate.label("plate"),
                    session_sun2_id.label("sun2_id"),
                    ParkingVehicle.navn.label("vehicle_name"),
                    ParkingVehicle.omrade.label("vehicle_area"),
                    Sun2TanningSession.id.label("sun_session_id"),
                    Sun2TanningSession.source_session_id.label("source_session_id"),
                    Sun2TanningSession.started_at.label("sun_started_at"),
                    Sun2TanningSession.ended_at.label("sun_ended_at"),
                    Sun2TanningSession.room_id.label("room_id"),
                    Sun2TanningSession.room.label("room"),
                    Sun2TanningSession.user_name.label("sun2_user_name"),
                    Sun2TanningSession.duration_minutes.label("duration_minutes"),
                    Sun2TanningSession.paid_amount_kr.label("paid_amount_kr"),
                    delta_seconds.label("delta_seconds"),
                )
                .where(tuple_(parking_plate, session_sun2_id).in_(candidate_pairs))
                .order_by(ParkingSession.start_time.desc(), Sun2TanningSession.started_at.desc())
                .limit(max(250, min(1000, limit * 6)))
            )
            for row in (await session.execute(match_stmt)).all():
                plate = str(row.plate or "").strip()
                match_rows.append(
                    {
                        "id": f"{row.parking_record_id}-{row.sun_session_id}",
                        "parking_start_at": api_local_iso(row.parking_start_at),
                        "sun_started_at": api_local_iso(row.sun_started_at),
                        "delta_minutes": round(float_or_zero(row.delta_seconds) / 60.0, 2),
                        "plate": plate,
                        "sun2_id": row.sun2_id,
                        "navn": row.vehicle_name,
                        "omrade": row.vehicle_area,
                        "room_label": sun2_room_label(row.room_id, row.room),
                        "user_name": row.sun2_user_name,
                        "duration_minutes": round(float_or_zero(row.duration_minutes), 1),
                        "paid_amount_kr": round(float_or_zero(row.paid_amount_kr), 2),
                        "fee_inc_vat": round(float_or_zero(row.fee_inc_vat), 2),
                        "source_system": row.source_system,
                        "parking_id": row.parking_id,
                        "parking_record_id": int_or_zero(row.parking_record_id),
                        "sun_session_id": int_or_zero(row.sun_session_id),
                        "source_session_id": row.source_session_id,
                        "path": f"/parkering/kjoretoy/{quote(plate)}" if plate else "",
                    }
                )

        candidate_rows: list[Dict[str, Any]] = []
        for row in candidate_rows_raw:
            plate = str(row.plate or "").strip()
            candidate_rows.append(
                {
                    "id": f"{plate}-{row.sun2_id}",
                    "plate": plate,
                    "sun2_id": row.sun2_id,
                    "matches_count": int_or_zero(row.matches_count),
                    "parking_match_count": int_or_zero(row.parking_match_count),
                    "first_match_at": api_local_iso(row.first_match_at),
                    "last_match_at": api_local_iso(row.last_match_at),
                    "avg_delta_minutes": round(float_or_zero(row.avg_delta_minutes), 2),
                    "navn": row.vehicle_name,
                    "omrade": row.vehicle_area,
                    "user_name": row.sun2_user_name,
                    "parking_count": int_or_zero(row.parking_count),
                    "paid_total": round(float_or_zero(row.paid_total), 2),
                    "path": f"/parkering/kjoretoy/{quote(plate)}" if plate else "",
                }
            )

        return {
            "candidate_rows": candidate_rows,
            "match_rows": match_rows,
            "candidate_count": len(candidate_rows),
            "match_count": sum(row["matches_count"] for row in candidate_rows),
            "recent_plate_count": recent_plate_count,
            "recent_cutoff": recent_cutoff,
        }

    def parking_sun_link_status_value(value: Optional[str]) -> str:
        PARKING_SUN_LINK_CONFIRMED = dependencies.PARKING_SUN_LINK_CONFIRMED
        PARKING_SUN_LINK_PENDING = dependencies.PARKING_SUN_LINK_PENDING
        PARKING_SUN_LINK_REJECTED = dependencies.PARKING_SUN_LINK_REJECTED
        normalized = (value or "").strip().lower()
        if normalized in {"bekreftet", "confirmed", "ok", "ja"}:
            return PARKING_SUN_LINK_CONFIRMED
        if normalized in {"avvist", "rejected", "nei"}:
            return PARKING_SUN_LINK_REJECTED
        return PARKING_SUN_LINK_PENDING

    def parking_sun_link_probability(
        matches_count: int,
        avg_delta_minutes: Optional[float],
        *,
        min_matches: int = 2,
        parking_match_count: Optional[int] = None,
        match_days_count: Optional[int] = None,
        plate_candidate_count: Optional[int] = None,
        sun2_candidate_count: Optional[int] = None,
        competitor_matches_count: Optional[int] = None,
    ) -> float:
        matches = int_or_zero(matches_count)
        observations = int_or_zero(parking_match_count) or matches
        days = int_or_zero(match_days_count)
        plate_options = max(1, int_or_zero(plate_candidate_count) or 1)
        sun2_options = max(1, int_or_zero(sun2_candidate_count) or 1)
        competitor = int_or_zero(competitor_matches_count)
        required = max(1, int_or_zero(min_matches) or 2)
        avg_delta = float_or_zero(avg_delta_minutes)

        if observations >= required:
            probability = 58.0 + min(24.0, (observations - required) * 8.0)
        else:
            probability = min(54.0, 18.0 + observations * 22.0)

        if days >= 3:
            probability += 10.0
        elif days >= 2:
            probability += 6.0

        if avg_delta <= 0.5:
            probability += 12.0
        elif avg_delta <= 1:
            probability += 9.0
        elif avg_delta <= 2:
            probability += 6.0
        elif avg_delta <= 3:
            probability += 3.0

        probability -= min(20.0, (plate_options - 1) * 8.0)
        probability -= min(20.0, (sun2_options - 1) * 8.0)
        if competitor >= observations and competitor > 0:
            probability -= 18.0
        elif competitor >= max(1, observations - 1):
            probability -= 8.0

        if observations < required:
            probability = min(probability, 55.0)
        return round(max(5.0, min(98.0, probability)), 1)

    def parking_sun_link_assessment(
        status: str,
        confidence: float,
        *,
        min_matches: int,
        parking_match_count: int,
        plate_candidate_count: int,
        sun2_candidate_count: int,
        competitor_matches_count: int,
    ) -> str:
        PARKING_SUN_LINK_CONFIRMED = dependencies.PARKING_SUN_LINK_CONFIRMED
        PARKING_SUN_LINK_REJECTED = dependencies.PARKING_SUN_LINK_REJECTED
        if status == PARKING_SUN_LINK_CONFIRMED:
            return "Bekreftet manuelt"
        if status == PARKING_SUN_LINK_REJECTED:
            return "Avvist manuelt"
        required = max(1, int_or_zero(min_matches) or 2)
        observations = int_or_zero(parking_match_count)
        if observations < required:
            return f"Venter på flere treff ({observations}/{required})"
        if competitor_matches_count >= observations and competitor_matches_count > 0:
            return "Usikker: konkurrerende kobling er like sterk"
        if plate_candidate_count > 1 or sun2_candidate_count > 1:
            return "Mulig kobling, men har alternativer"
        if confidence >= 85:
            return "Svært sannsynlig"
        if confidence >= 70:
            return "Sannsynlig"
        return "Krever manuell vurdering"

    def parking_sun_link_settings_edit() -> Dict[str, Any]:
        return {
            "kind": "koble-settings",
            "title": "parameter",
            "idField": "id",
            "endpoint": "/api/koble/settings/{id}",
            "method": "PATCH",
            "fields": [
                {"key": "min_matches", "label": "Sterk kandidat fra treff", "type": "number"},
                {"key": "max_minutes", "label": "Maks minutter etter parkering", "type": "number"},
                {"key": "recent_days", "label": "Bilutvalg dager (0 = alle)", "type": "number"},
                {"key": "idle_sleep_seconds", "label": "Pause naar ajour sek", "type": "number"},
            ],
        }

    def parking_sun_link_candidate_edit() -> Dict[str, Any]:
        PARKING_SUN_LINK_STATUSES = dependencies.PARKING_SUN_LINK_STATUSES
        return {
            "kind": "koble-candidate",
            "title": "kobling",
            "idField": "id",
            "endpoint": "/api/koble/candidates/{id}",
            "method": "PATCH",
            "fields": [
                {
                    "key": "status",
                    "label": "Status",
                    "type": "select",
                    "options": [{"label": value, "value": value} for value in PARKING_SUN_LINK_STATUSES],
                    "required": True,
                },
                {"key": "note", "label": "Notat", "type": "textarea"},
            ],
        }

    async def get_parking_sun_link_state(session: Any) -> ParkingSunLinkJobState:
        state = (
            await session.execute(select(ParkingSunLinkJobState).where(ParkingSunLinkJobState.id == 1))
        ).scalars().first()
        if not state:
            state = ParkingSunLinkJobState(id=1)
            session.add(state)
            await session.flush()
        changed = False
        defaults = {
            "enabled": False,
            "generation": 1,
            "min_matches": 2,
            "max_minutes": 3,
            "recent_days": 0,
            "idle_sleep_seconds": 20,
            "status": "stoppet",
            "status_text": "Koblingsjobben er stoppet.",
            "processed_count": 0,
            "matched_count": 0,
            "candidate_count": 0,
            "strong_candidate_count": 0,
            "checked_plate_count": 0,
            "updated_at": local_now_naive(),
            "raw": {},
        }
        for key, value in defaults.items():
            if getattr(state, key, None) is None:
                setattr(state, key, value)
                changed = True
        if changed:
            await session.flush()
        return state

    async def reset_parking_sun_link_data(session: Any, state: ParkingSunLinkJobState, *, enabled: bool = True) -> ParkingSunLinkJobState:
        await session.execute(delete(ParkingSunLinkMatch))
        await session.execute(delete(ParkingSunLinkCandidate))
        await session.execute(delete(ParkingSunLinkProcessed))
        state.enabled = enabled
        state.generation = int_or_zero(state.generation) + 1
        state.status = "venter" if enabled else "stoppet"
        state.status_text = "Starter fra nyeste parkering." if enabled else "Stoppet."
        state.processed_count = 0
        state.matched_count = 0
        state.candidate_count = 0
        state.strong_candidate_count = 0
        state.checked_plate_count = 0
        state.last_processed_parking_id = None
        state.last_processed_plate = None
        state.last_processed_at = None
        state.last_started_at = local_now_naive() if enabled else state.last_started_at
        state.last_finished_at = None
        state.last_error = None
        state.updated_at = local_now_naive()
        state.raw = {}
        return state

    def api_parking_sun_link_state_row(state: ParkingSunLinkJobState) -> Dict[str, Any]:
        return {
            "id": state.id,
            "enabled": bool(state.enabled),
            "generation": int_or_zero(state.generation),
            "min_matches": int_or_zero(state.min_matches),
            "max_minutes": int_or_zero(state.max_minutes),
            "recent_days": int_or_zero(state.recent_days),
            "idle_sleep_seconds": int_or_zero(state.idle_sleep_seconds),
            "status": state.status,
            "status_text": state.status_text,
            "processed_count": int_or_zero(state.processed_count),
            "matched_count": int_or_zero(state.matched_count),
            "candidate_count": int_or_zero(state.candidate_count),
            "strong_candidate_count": int_or_zero(state.strong_candidate_count),
            "checked_plate_count": int_or_zero(state.checked_plate_count),
            "last_processed_parking_id": state.last_processed_parking_id,
            "last_processed_plate": state.last_processed_plate,
            "last_processed_at": api_local_iso(state.last_processed_at),
            "last_worker_seen_at": api_local_iso(state.last_worker_seen_at),
            "updated_at": api_local_iso(state.updated_at),
        }

    def api_parking_sun_link_candidate_row(row: ParkingSunLinkCandidate) -> Dict[str, Any]:
        plate = str(row.plate or "").strip()
        return {
            "id": row.id,
            "status": row.status,
            "confidence": round(float_or_zero(row.confidence), 1),
            "assessment": row.assessment,
            "plate": plate,
            "sun2_id": row.sun2_id,
            "matches_count": int_or_zero(row.matches_count),
            "parking_match_count": int_or_zero(row.parking_match_count),
            "match_days_count": int_or_zero(row.match_days_count),
            "plate_candidate_count": int_or_zero(row.plate_candidate_count),
            "sun2_candidate_count": int_or_zero(row.sun2_candidate_count),
            "competitor_matches_count": int_or_zero(row.competitor_matches_count),
            "first_match_at": api_local_iso(row.first_match_at),
            "last_match_at": api_local_iso(row.last_match_at),
            "avg_delta_minutes": round(float_or_zero(row.avg_delta_minutes), 2),
            "navn": row.navn,
            "omrade": row.omrade,
            "user_name": row.user_name,
            "parking_count": int_or_zero(row.parking_count),
            "paid_total": round(float_or_zero(row.paid_total), 2),
            "matched_paid_total": round(float_or_zero(row.matched_paid_total), 2),
            "note": row.note,
            "confirmed_at": api_local_iso(row.confirmed_at),
            "confirmed_by": row.confirmed_by,
            "rejected_at": api_local_iso(row.rejected_at),
            "rejected_by": row.rejected_by,
            "path": f"/parkering/kjoretoy/{quote(plate)}" if plate else "",
        }

    def api_parking_sun_link_match_row(row: ParkingSunLinkMatch) -> Dict[str, Any]:
        plate = str(row.plate or "").strip()
        return {
            "id": row.id,
            "parking_start_at": api_local_iso(row.parking_start_at),
            "sun_started_at": api_local_iso(row.sun_started_at),
            "delta_minutes": round(float_or_zero(row.delta_minutes), 2),
            "plate": plate,
            "sun2_id": row.sun2_id,
            "room_label": sun2_room_label(row.room_id, row.room),
            "user_name": row.user_name,
            "duration_minutes": round(float_or_zero(row.duration_minutes), 1),
            "paid_amount_kr": round(float_or_zero(row.paid_amount_kr), 2),
            "fee_inc_vat": round(float_or_zero(row.fee_inc_vat), 2),
            "source_system": row.source_system,
            "parking_id": row.parking_id,
            "parking_record_id": row.parking_record_id,
            "sun_session_id": row.sun_session_id,
            "source_session_id": row.source_session_id,
            "path": f"/parkering/kjoretoy/{quote(plate)}" if plate else "",
        }

    async def parking_sun_link_matched_paid_totals(
        session: Any,
        generation: int,
        pairs: Optional[Iterable[tuple[str, str]]] = None,
    ) -> Dict[tuple[str, str], float]:
        clean_pairs = sorted({(str(plate or "").strip(), str(sun2_id or "").strip()) for plate, sun2_id in (pairs or []) if plate and sun2_id})
        stmt = (
            select(
                ParkingSunLinkMatch.plate.label("plate"),
                ParkingSunLinkMatch.sun2_id.label("sun2_id"),
                ParkingSunLinkMatch.parking_record_id.label("parking_record_id"),
                func.max(ParkingSunLinkMatch.fee_inc_vat).label("fee_inc_vat"),
            )
            .where(ParkingSunLinkMatch.generation == generation)
            .group_by(ParkingSunLinkMatch.plate, ParkingSunLinkMatch.sun2_id, ParkingSunLinkMatch.parking_record_id)
        )
        if clean_pairs:
            stmt = stmt.where(tuple_(ParkingSunLinkMatch.plate, ParkingSunLinkMatch.sun2_id).in_(clean_pairs))
        matched_parking_amounts = stmt.subquery()
        rows = (
            await session.execute(
                select(
                    matched_parking_amounts.c.plate,
                    matched_parking_amounts.c.sun2_id,
                    func.coalesce(func.sum(matched_parking_amounts.c.fee_inc_vat), 0).label("matched_paid_total"),
                ).group_by(matched_parking_amounts.c.plate, matched_parking_amounts.c.sun2_id)
            )
        ).all()
        return {
            (str(row.plate or "").strip(), str(row.sun2_id or "").strip()): float_or_zero(row.matched_paid_total)
            for row in rows
        }

    async def parking_sun_link_qualified_distinct_matched_paid_total(
        session: Any,
        generation: int,
        min_parking_match_count: int = 2,
    ) -> float:
        matched_parking_amounts = (
            select(
                ParkingSunLinkMatch.parking_record_id.label("parking_record_id"),
                func.max(ParkingSunLinkMatch.fee_inc_vat).label("fee_inc_vat"),
            )
            .join(
                ParkingSunLinkCandidate,
                and_(
                    ParkingSunLinkCandidate.generation == ParkingSunLinkMatch.generation,
                    ParkingSunLinkCandidate.plate == ParkingSunLinkMatch.plate,
                    ParkingSunLinkCandidate.sun2_id == ParkingSunLinkMatch.sun2_id,
                ),
            )
            .where(ParkingSunLinkMatch.generation == generation)
            .where(ParkingSunLinkCandidate.generation == generation)
            .where(ParkingSunLinkCandidate.parking_match_count >= min_parking_match_count)
            .group_by(ParkingSunLinkMatch.parking_record_id)
            .subquery()
        )
        return float_or_zero(
            (
                await session.execute(
                    select(func.coalesce(func.sum(matched_parking_amounts.c.fee_inc_vat), 0))
                )
            ).scalar_one_or_none()
        )

    async def refresh_parking_sun_link_candidate_pairs(
        session: Any,
        generation: int,
        pairs: Optional[Iterable[tuple[str, str]]] = None,
        min_matches: int = 2,
    ) -> None:
        PARKING_SUN_LINK_CONFIRMED = dependencies.PARKING_SUN_LINK_CONFIRMED
        PARKING_SUN_LINK_PENDING = dependencies.PARKING_SUN_LINK_PENDING
        required_matches = max(1, int_or_zero(min_matches) or 2)
        clean_pairs = sorted({(str(plate or "").strip(), str(sun2_id or "").strip()) for plate, sun2_id in (pairs or []) if plate and sun2_id})
        pair_count_rows = (
            await session.execute(
                select(
                    ParkingSunLinkMatch.plate,
                    ParkingSunLinkMatch.sun2_id,
                    func.count(func.distinct(ParkingSunLinkMatch.parking_record_id)).label("parking_match_count"),
                )
                .where(ParkingSunLinkMatch.generation == generation)
                .group_by(ParkingSunLinkMatch.plate, ParkingSunLinkMatch.sun2_id)
            )
        ).all()
        pair_counts: Dict[tuple[str, str], int] = {}
        qualified_plate_options: Dict[str, set[str]] = {}
        qualified_sun2_options: Dict[str, set[str]] = {}
        for pair_row in pair_count_rows:
            plate_key = str(pair_row.plate or "").strip()
            sun2_key = str(pair_row.sun2_id or "").strip()
            if not plate_key or not sun2_key:
                continue
            pair_key = (plate_key, sun2_key)
            pair_count = int_or_zero(pair_row.parking_match_count)
            pair_counts[pair_key] = pair_count
            if pair_count >= required_matches:
                qualified_plate_options.setdefault(plate_key, set()).add(sun2_key)
                qualified_sun2_options.setdefault(sun2_key, set()).add(plate_key)

        matched_parking_amounts = (
            select(
                ParkingSunLinkMatch.plate.label("plate"),
                ParkingSunLinkMatch.sun2_id.label("sun2_id"),
                ParkingSunLinkMatch.parking_record_id.label("parking_record_id"),
                func.max(ParkingSunLinkMatch.fee_inc_vat).label("fee_inc_vat"),
            )
            .where(ParkingSunLinkMatch.generation == generation)
            .group_by(ParkingSunLinkMatch.plate, ParkingSunLinkMatch.sun2_id, ParkingSunLinkMatch.parking_record_id)
            .subquery()
        )
        matched_paid_by_pair = (
            select(
                matched_parking_amounts.c.plate.label("plate"),
                matched_parking_amounts.c.sun2_id.label("sun2_id"),
                func.coalesce(func.sum(matched_parking_amounts.c.fee_inc_vat), 0).label("matched_paid_total"),
            )
            .group_by(matched_parking_amounts.c.plate, matched_parking_amounts.c.sun2_id)
            .subquery()
        )

        stmt = (
            select(
                ParkingSunLinkMatch.plate,
                ParkingSunLinkMatch.sun2_id,
                func.count(ParkingSunLinkMatch.id).label("matches_count"),
                func.count(func.distinct(ParkingSunLinkMatch.parking_record_id)).label("parking_match_count"),
                func.count(func.distinct(cast(ParkingSunLinkMatch.parking_start_at, Date))).label("match_days_count"),
                func.min(ParkingSunLinkMatch.parking_start_at).label("first_match_at"),
                func.max(ParkingSunLinkMatch.parking_start_at).label("last_match_at"),
                func.avg(ParkingSunLinkMatch.delta_minutes).label("avg_delta_minutes"),
                func.max(ParkingVehicle.navn).label("navn"),
                func.max(ParkingVehicle.omrade).label("omrade"),
                func.max(ParkingSunLinkMatch.user_name).label("user_name"),
                func.max(ParkingVehicle.parkering_count).label("parking_count"),
                func.max(ParkingVehicle.paid_total).label("paid_total"),
                func.max(matched_paid_by_pair.c.matched_paid_total).label("matched_paid_total"),
            )
            .select_from(ParkingSunLinkMatch)
            .outerjoin(ParkingVehicle, ParkingVehicle.plate == ParkingSunLinkMatch.plate)
            .outerjoin(
                matched_paid_by_pair,
                and_(
                    matched_paid_by_pair.c.plate == ParkingSunLinkMatch.plate,
                    matched_paid_by_pair.c.sun2_id == ParkingSunLinkMatch.sun2_id,
                ),
            )
            .where(ParkingSunLinkMatch.generation == generation)
            .group_by(ParkingSunLinkMatch.plate, ParkingSunLinkMatch.sun2_id)
        )
        if clean_pairs:
            stmt = stmt.where(tuple_(ParkingSunLinkMatch.plate, ParkingSunLinkMatch.sun2_id).in_(clean_pairs))
        rows = (await session.execute(stmt)).all()
        now_value = local_now_naive()
        for row in rows:
            plate_key = str(row.plate or "").strip()
            sun2_key = str(row.sun2_id or "").strip()
            pair_key = (plate_key, sun2_key)
            parking_match_count = int_or_zero(row.parking_match_count)
            match_days_count = int_or_zero(row.match_days_count)
            is_qualified_pair = parking_match_count >= required_matches
            plate_candidate_count = len(qualified_plate_options.get(plate_key, set())) if is_qualified_pair else 1
            sun2_candidate_count = len(qualified_sun2_options.get(sun2_key, set())) if is_qualified_pair else 1
            plate_candidate_count = max(1, plate_candidate_count)
            sun2_candidate_count = max(1, sun2_candidate_count)
            competitor_matches_count = 0
            for other_key, other_count in pair_counts.items():
                other_plate, other_sun2 = other_key
                if other_key == pair_key:
                    continue
                if int_or_zero(other_count) < required_matches:
                    continue
                if other_plate == plate_key or other_sun2 == sun2_key:
                    competitor_matches_count = max(competitor_matches_count, int_or_zero(other_count))
            candidate = (
                await session.execute(
                    select(ParkingSunLinkCandidate)
                    .where(ParkingSunLinkCandidate.generation == generation)
                    .where(ParkingSunLinkCandidate.plate == row.plate)
                    .where(ParkingSunLinkCandidate.sun2_id == row.sun2_id)
                )
            ).scalars().first()
            if not candidate:
                candidate = ParkingSunLinkCandidate(
                    generation=generation,
                    plate=row.plate,
                    sun2_id=row.sun2_id,
                    status=PARKING_SUN_LINK_PENDING,
                    created_at=now_value,
                )
                session.add(candidate)
            candidate.matches_count = int_or_zero(row.matches_count)
            candidate.parking_match_count = parking_match_count
            candidate.match_days_count = match_days_count
            candidate.plate_candidate_count = plate_candidate_count
            candidate.sun2_candidate_count = sun2_candidate_count
            candidate.competitor_matches_count = competitor_matches_count
            candidate.first_match_at = normalize_local_naive(row.first_match_at) if row.first_match_at else None
            candidate.last_match_at = normalize_local_naive(row.last_match_at) if row.last_match_at else None
            candidate.avg_delta_minutes = float_or_zero(row.avg_delta_minutes)
            candidate.navn = row.navn
            candidate.omrade = row.omrade
            candidate.user_name = row.user_name
            candidate.parking_count = int_or_zero(row.parking_count)
            candidate.paid_total = float_or_zero(row.paid_total)
            candidate.matched_paid_total = float_or_zero(row.matched_paid_total)
            candidate.confidence = 100.0 if candidate.status == PARKING_SUN_LINK_CONFIRMED else parking_sun_link_probability(
                candidate.matches_count,
                candidate.avg_delta_minutes,
                min_matches=required_matches,
                parking_match_count=parking_match_count,
                match_days_count=match_days_count,
                plate_candidate_count=plate_candidate_count,
                sun2_candidate_count=sun2_candidate_count,
                competitor_matches_count=competitor_matches_count,
            )
            candidate.assessment = parking_sun_link_assessment(
                candidate.status,
                candidate.confidence,
                min_matches=required_matches,
                parking_match_count=parking_match_count,
                plate_candidate_count=plate_candidate_count,
                sun2_candidate_count=sun2_candidate_count,
                competitor_matches_count=competitor_matches_count,
            )
            candidate.updated_at = now_value

    async def refresh_parking_sun_link_state_counts(session: Any, state: ParkingSunLinkJobState) -> None:
        PARKING_SUN_LINK_PENDING = dependencies.PARKING_SUN_LINK_PENDING
        generation = int_or_zero(state.generation)
        required_matches = max(1, int_or_zero(state.min_matches) or 2)
        state.processed_count = int_or_zero(
            (await session.execute(select(func.count(ParkingSunLinkProcessed.id)).where(ParkingSunLinkProcessed.generation == generation))).scalar_one_or_none()
        )
        state.matched_count = int_or_zero(
            (await session.execute(select(func.count(ParkingSunLinkMatch.id)).where(ParkingSunLinkMatch.generation == generation))).scalar_one_or_none()
        )
        state.candidate_count = int_or_zero(
            (
                await session.execute(
                    select(func.count(ParkingSunLinkCandidate.id))
                    .where(ParkingSunLinkCandidate.generation == generation)
                    .where(ParkingSunLinkCandidate.parking_match_count >= required_matches)
                )
            ).scalar_one_or_none()
        )
        state.strong_candidate_count = int_or_zero(
            (
                await session.execute(
                    select(func.count(ParkingSunLinkCandidate.id))
                    .where(ParkingSunLinkCandidate.generation == generation)
                    .where(ParkingSunLinkCandidate.parking_match_count >= required_matches)
                    .where(ParkingSunLinkCandidate.status == PARKING_SUN_LINK_PENDING)
                    .where(ParkingSunLinkCandidate.confidence >= 70)
                )
            ).scalar_one_or_none()
        )
        state.checked_plate_count = int_or_zero(
            (
                await session.execute(
                    select(func.count(func.distinct(ParkingSunLinkProcessed.plate))).where(ParkingSunLinkProcessed.generation == generation)
                )
            ).scalar_one_or_none()
        )
        state.updated_at = local_now_naive()

    async def update_parking_sun_link_import_status(session: Any, state: ParkingSunLinkJobState) -> None:
        import_job_definition = dependencies.import_job_definition
        definition = import_job_definition("parking_sun_link_worker")
        now_value = local_now_naive()
        row = (
            await session.execute(select(ImportJobStatus).where(ImportJobStatus.job_name == "parking_sun_link_worker"))
        ).scalars().first()
        if not row:
            row = ImportJobStatus(job_name="parking_sun_link_worker", title=definition["title"], category=definition["category"])
            session.add(row)
        row.title = definition["title"]
        row.category = definition["category"]
        row.source = definition.get("source")
        row.status = "bad" if state.status == "feil" else ("running" if state.enabled and state.status not in {"ajour", "stoppet"} else "ok")
        row.status_text = state.status_text or state.status
        row.last_run_at = state.last_worker_seen_at or now_value
        if row.status == "bad":
            row.last_failed_at = state.last_worker_seen_at or now_value
        else:
            row.last_success_at = state.last_worker_seen_at or now_value
        row.expected_interval_minutes = definition.get("expected_interval_minutes")
        row.warning_after_minutes = definition.get("warning_after_minutes")
        row.records_imported = int_or_zero(state.processed_count)
        # Candidate count is an outcome, not the total number of parking rows.
        row.records_total = None
        row.next_expected_at = (state.last_worker_seen_at or now_value) + timedelta(minutes=definition.get("expected_interval_minutes") or 10)
        row.message = state.status_text
        row.raw = api_parking_sun_link_state_row(state)

    return {
        "api_parking_sun_link_candidate_row": api_parking_sun_link_candidate_row,
        "api_parking_sun_link_match_row": api_parking_sun_link_match_row,
        "api_parking_sun_link_state_row": api_parking_sun_link_state_row,
        "get_parking_sun_link_state": get_parking_sun_link_state,
        "has_koble_worker_access": has_koble_worker_access,
        "is_koble_worker_request_path": is_koble_worker_request_path,
        "parking_sun_link_assessment": parking_sun_link_assessment,
        "parking_sun_link_candidate_edit": parking_sun_link_candidate_edit,
        "parking_sun_link_candidates": parking_sun_link_candidates,
        "parking_sun_link_matched_paid_totals": parking_sun_link_matched_paid_totals,
        "parking_sun_link_probability": parking_sun_link_probability,
        "parking_sun_link_qualified_distinct_matched_paid_total": parking_sun_link_qualified_distinct_matched_paid_total,
        "parking_sun_link_settings_edit": parking_sun_link_settings_edit,
        "parking_sun_link_status_value": parking_sun_link_status_value,
        "refresh_parking_sun_link_candidate_pairs": refresh_parking_sun_link_candidate_pairs,
        "refresh_parking_sun_link_state_counts": refresh_parking_sun_link_state_counts,
        "reset_parking_sun_link_data": reset_parking_sun_link_data,
        "update_parking_sun_link_import_status": update_parking_sun_link_import_status,
    }
