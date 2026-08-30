"""Linking module response assembly, independent of HTTP registration."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fibaro_core.models import ParkingSunLinkCandidate, ParkingSunLinkMatch, ParkingSunLinkProcessed
from fibaro_core.services.presentation import api_card, api_table, format_short_number
from fibaro_core.services.summaries.periods import add_months
from sqlalchemy import case, func, select, tuple_
from sun2_helpers import sun2_room_label
from time_formatting import api_local_iso, format_source_datetime_short
from typing import Any, Dict
from v2_navigation import v2_module_title
from value_parsing import float_or_zero, int_or_zero


@dataclass
class Dependencies:
    PARKING_SUN_LINK_CONFIRMED: Any
    PARKING_SUN_LINK_PENDING: Any
    api_filter: Any
    api_filter_int: Any
    api_parking_sun_link_candidate_row: Any
    api_parking_sun_link_match_row: Any
    api_parking_sun_link_state_row: Any
    get_parking_sun_link_state: Any
    parking_sun_link_candidate_edit: Any
    parking_sun_link_matched_paid_totals: Any
    parking_sun_link_qualified_distinct_matched_paid_total: Any
    parking_sun_link_settings_edit: Any
    refresh_parking_sun_link_state_counts: Any


async def render(session, request, module, view, q, day, now_dt, dependencies):
    PARKING_SUN_LINK_CONFIRMED = dependencies.PARKING_SUN_LINK_CONFIRMED
    PARKING_SUN_LINK_PENDING = dependencies.PARKING_SUN_LINK_PENDING
    api_filter = dependencies.api_filter
    api_filter_int = dependencies.api_filter_int
    api_parking_sun_link_candidate_row = dependencies.api_parking_sun_link_candidate_row
    api_parking_sun_link_match_row = dependencies.api_parking_sun_link_match_row
    api_parking_sun_link_state_row = dependencies.api_parking_sun_link_state_row
    get_parking_sun_link_state = dependencies.get_parking_sun_link_state
    parking_sun_link_candidate_edit = dependencies.parking_sun_link_candidate_edit
    parking_sun_link_matched_paid_totals = dependencies.parking_sun_link_matched_paid_totals
    parking_sun_link_qualified_distinct_matched_paid_total = dependencies.parking_sun_link_qualified_distinct_matched_paid_total
    parking_sun_link_settings_edit = dependencies.parking_sun_link_settings_edit
    refresh_parking_sun_link_state_counts = dependencies.refresh_parking_sun_link_state_counts
    params = request.query_params
    today = now_dt.date()
    tomorrow = today + timedelta(days=1)
    today_start = datetime.combine(today, time.min)
    tomorrow_start = datetime.combine(tomorrow, time.min)
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, time.min)
    previous_month_start = add_months(month_start, -1)
    previous_month_start_dt = datetime.combine(previous_month_start, time.min)
    year_start_dt = datetime.combine(date(today.year, 1, 1), time.min)
    limit_value = api_filter_int(params, "limit", 250, 25, 1000)
    koble_view = view or "oversikt"
    needs_review_candidates = koble_view == "kandidater"
    needs_match_table = koble_view == "treffgrunnlag"
    needs_processed_rows = koble_view == "jobb"
    needs_qualified_rows = koble_view in {"biltreff", "sun2"}
    needs_qualified_totals = koble_view in {"oversikt", "biltreff", "sun2"}
    state = await get_parking_sun_link_state(session)
    generation = int_or_zero(state.generation)
    min_required_matches = max(1, int_or_zero(state.min_matches) or 2)
    await refresh_parking_sun_link_state_counts(session, state)
    candidates: list[ParkingSunLinkCandidate] = []
    if needs_review_candidates:
        candidates = (
            await session.execute(
                select(ParkingSunLinkCandidate)
                .where(ParkingSunLinkCandidate.generation == generation)
                .where(ParkingSunLinkCandidate.parking_match_count >= min_required_matches)
                .order_by(
                    case(
                        (ParkingSunLinkCandidate.status == PARKING_SUN_LINK_PENDING, 0),
                        (ParkingSunLinkCandidate.status == PARKING_SUN_LINK_CONFIRMED, 1),
                        else_=2,
                    ),
                    ParkingSunLinkCandidate.confidence.desc(),
                    ParkingSunLinkCandidate.matches_count.desc(),
                    ParkingSunLinkCandidate.last_match_at.desc(),
                )
                .limit(limit_value)
            )
        ).scalars().all()
    matches: list[ParkingSunLinkMatch] = []
    if needs_match_table:
        matches = (
            await session.execute(
                select(ParkingSunLinkMatch)
                .where(ParkingSunLinkMatch.generation == generation)
                .order_by(ParkingSunLinkMatch.parking_start_at.desc(), ParkingSunLinkMatch.sun_started_at.desc())
                .limit(limit_value)
            )
        ).scalars().all()
    review_pairs = [(row.plate, row.sun2_id) for row in candidates if row.plate and row.sun2_id]
    review_matches_by_pair: Dict[tuple[str, str], list[ParkingSunLinkMatch]] = defaultdict(list)
    if review_pairs:
        review_matches = (
            await session.execute(
                select(ParkingSunLinkMatch)
                .where(ParkingSunLinkMatch.generation == generation)
                .where(tuple_(ParkingSunLinkMatch.plate, ParkingSunLinkMatch.sun2_id).in_(review_pairs))
                .order_by(ParkingSunLinkMatch.parking_start_at.desc(), ParkingSunLinkMatch.sun_started_at.desc())
                .limit(max(300, min(2000, len(review_pairs) * 10)))
            )
        ).scalars().all()
        for match in review_matches:
            pair_key = (str(match.plate or "").strip(), str(match.sun2_id or "").strip())
            if len(review_matches_by_pair[pair_key]) < 6:
                review_matches_by_pair[pair_key].append(match)
    review_matched_paid_by_pair = await parking_sun_link_matched_paid_totals(session, generation, review_pairs) if review_pairs else {}
    processed_rows: list[ParkingSunLinkProcessed] = []
    if needs_processed_rows:
        processed_rows = (
            await session.execute(
                select(ParkingSunLinkProcessed)
                .where(ParkingSunLinkProcessed.generation == generation)
                .order_by(ParkingSunLinkProcessed.checked_at.desc())
                .limit(20)
            )
        ).scalars().all()
    qualified_filter = [
        ParkingSunLinkCandidate.generation == generation,
        ParkingSunLinkCandidate.parking_match_count >= min_required_matches,
    ]
    raw_pair_count = int_or_zero(
        (
            await session.execute(
                select(func.count(ParkingSunLinkCandidate.id)).where(ParkingSunLinkCandidate.generation == generation)
            )
        ).scalar_one_or_none()
    )
    raw_one_off_pair_count = int_or_zero(
        (
            await session.execute(
                select(func.count(ParkingSunLinkCandidate.id))
                .where(ParkingSunLinkCandidate.generation == generation)
                .where(ParkingSunLinkCandidate.parking_match_count < min_required_matches)
            )
        ).scalar_one_or_none()
    )
    qualified_plate_count = int_or_zero(
        (
            await session.execute(
                select(func.count(func.distinct(func.upper(func.trim(ParkingSunLinkCandidate.plate))))).where(
                    *qualified_filter
                )
            )
        ).scalar_one_or_none()
    )
    qualified_pair_count = int_or_zero(
        (
            await session.execute(
                select(func.count(ParkingSunLinkCandidate.id)).where(*qualified_filter)
            )
        ).scalar_one_or_none()
    )
    qualified_paid_subquery = (
        select(
            func.upper(func.trim(ParkingSunLinkCandidate.plate)).label("plate"),
            func.max(ParkingSunLinkCandidate.paid_total).label("paid_total"),
        )
        .where(*qualified_filter)
        .group_by(func.upper(func.trim(ParkingSunLinkCandidate.plate)))
        .subquery()
    )
    qualified_paid_total = float_or_zero(
        (
            await session.execute(
                select(func.coalesce(func.sum(qualified_paid_subquery.c.paid_total), 0))
            )
        ).scalar_one_or_none()
    )
    qualified_candidate_rows: list[Dict[str, Any]] = []
    qualified_visible_pairs: list[tuple[str, str]] = []
    if needs_qualified_rows:
        qualified_candidates = (
            await session.execute(
                select(ParkingSunLinkCandidate)
                .where(*qualified_filter)
                .order_by(
                    ParkingSunLinkCandidate.matches_count.desc(),
                    ParkingSunLinkCandidate.parking_match_count.desc(),
                    ParkingSunLinkCandidate.last_match_at.desc(),
                )
                .limit(limit_value)
            )
        ).scalars().all()
        qualified_candidate_rows = [api_parking_sun_link_candidate_row(row) for row in qualified_candidates]
        qualified_visible_pairs = [(row["plate"], row["sun2_id"]) for row in qualified_candidate_rows if row.get("plate") and row.get("sun2_id")]
    qualified_matched_paid_by_pair = (
        await parking_sun_link_matched_paid_totals(session, generation, qualified_visible_pairs)
        if qualified_candidate_rows and qualified_visible_pairs
        else {}
    )
    for row in qualified_candidate_rows:
        pair_key = (str(row.get("plate") or "").strip(), str(row.get("sun2_id") or "").strip())
        row["matched_paid_total"] = round(qualified_matched_paid_by_pair.get(pair_key, float_or_zero(row.get("matched_paid_total"))), 2)
    qualified_matched_paid_total = (
        await parking_sun_link_qualified_distinct_matched_paid_total(session, generation, min_required_matches)
        if needs_qualified_totals
        else 0.0
    )
    qualified_sun2_group_counts: Dict[str, int] = {}
    qualified_sun2_rows = []
    if koble_view == "sun2":
        qualified_sun2_group_counts = {
            str(row.sun2_id or "").strip(): int_or_zero(row.vehicle_count)
            for row in (
                await session.execute(
                    select(
                        ParkingSunLinkCandidate.sun2_id.label("sun2_id"),
                        func.count(ParkingSunLinkCandidate.id).label("vehicle_count"),
                    )
                    .where(*qualified_filter)
                    .group_by(ParkingSunLinkCandidate.sun2_id)
                )
            ).all()
            if row.sun2_id
        }
        for row in qualified_candidate_rows:
            parking_count = int_or_zero(row.get("parking_count"))
            parking_match_count = int_or_zero(row.get("parking_match_count"))
            parking_without_sun = max(0, parking_count - parking_match_count)
            parking_match_share = (parking_match_count / parking_count * 100.0) if parking_count > 0 else 0.0
            sun2_id = str(row.get("sun2_id") or "").strip()
            qualified_sun2_rows.append(
                {
                    "id": row["id"],
                    "sun2Id": sun2_id,
                    "sun2VehicleCount": qualified_sun2_group_counts.get(sun2_id, 1),
                    "userName": row["user_name"],
                    "plate": row["plate"],
                    "vehicleName": row["navn"],
                    "vehicleArea": row["omrade"],
                    "status": row["status"],
                    "confidence": row["confidence"],
                    "matchesCount": row["matches_count"],
                    "parkingMatchCount": parking_match_count,
                    "parkingCount": parking_count,
                    "parkingWithoutSunCount": parking_without_sun,
                    "parkingMatchShare": round(parking_match_share, 1),
                    "matchDaysCount": row["match_days_count"],
                    "lastMatchAt": row["last_match_at"],
                    "avgDeltaMinutes": row["avg_delta_minutes"],
                    "paidTotal": row["paid_total"],
                    "matchedPaidTotal": row["matched_paid_total"],
                    "path": row["path"],
                }
            )
        qualified_sun2_rows.sort(
            key=lambda item: (
                -int_or_zero(item.get("sun2VehicleCount")),
                str(item.get("sun2Id") or ""),
                -int_or_zero(item.get("matchesCount")),
                -int_or_zero(item.get("parkingMatchCount")),
                str(item.get("plate") or ""),
            )
        )
    state_row = api_parking_sun_link_state_row(state)
    worker_seen = format_source_datetime_short(state.last_worker_seen_at) if state.last_worker_seen_at else "-"
    worker_detail = state.status_text or ("Jobben er aktiv." if state.enabled else "Jobben er stoppet.")
    review_candidates = []
    for candidate in candidates:
        pair_key = (str(candidate.plate or "").strip(), str(candidate.sun2_id or "").strip())
        row = api_parking_sun_link_candidate_row(candidate)
        review_candidates.append(
            {
                "id": row["id"],
                "status": row["status"],
                "confidence": row["confidence"],
                "assessment": row["assessment"],
                "plate": row["plate"],
                "sun2Id": row["sun2_id"],
                "vehicleName": row["navn"],
                "vehicleArea": row["omrade"],
                "userName": row["user_name"],
                "matchesCount": row["matches_count"],
                "parkingMatchCount": row["parking_match_count"],
                "matchDaysCount": row["match_days_count"],
                "plateCandidateCount": row["plate_candidate_count"],
                "sun2CandidateCount": row["sun2_candidate_count"],
                "competitorMatchesCount": row["competitor_matches_count"],
                "firstMatchAt": row["first_match_at"],
                "lastMatchAt": row["last_match_at"],
                "avgDeltaMinutes": row["avg_delta_minutes"],
                "parkingCount": row["parking_count"],
                "paidTotal": row["paid_total"],
                "matchedPaidTotal": round(review_matched_paid_by_pair.get(pair_key, float_or_zero(row.get("matched_paid_total"))), 2),
                "note": row["note"],
                "path": row["path"],
                "matches": [
                    {
                        "id": match.id,
                        "parkingStartAt": api_local_iso(match.parking_start_at),
                        "sunStartedAt": api_local_iso(match.sun_started_at),
                        "deltaMinutes": round(float_or_zero(match.delta_minutes), 2),
                        "roomLabel": sun2_room_label(match.room_id, match.room),
                        "userName": match.user_name,
                        "durationMinutes": round(float_or_zero(match.duration_minutes), 1),
                        "paidAmountKr": round(float_or_zero(match.paid_amount_kr), 2),
                        "feeIncVat": round(float_or_zero(match.fee_inc_vat), 2),
                        "sourceSystem": match.source_system,
                        "parkingId": match.parking_id,
                        "parkingRecordId": match.parking_record_id,
                        "sunSessionId": match.sun_session_id,
                    }
                    for match in review_matches_by_pair.get(pair_key, [])
                ],
            }
        )
    processed_table_rows = [
        {
            "id": row.id,
            "checked_at": api_local_iso(row.checked_at),
            "plate": row.plate,
            "parking_record_id": row.parking_record_id,
            "parking_start_at": api_local_iso(row.parking_start_at),
            "matches_found": int_or_zero(row.matches_found),
        }
        for row in processed_rows
    ]
    return {
        "title": v2_module_title("koble", view),
        "subtitle": (
            "Egen bakgrunnsapp går gjennom parkeringer fra nyeste. Kandidat krever samme bil og samme SUN2-ID "
            f"på minst {min_required_matches} ulike parkeringer, med solstart innen {int_or_zero(state.max_minutes)} min etter ankomst."
        ),
        "kobleReview": {
            "generatedAt": api_local_iso(now_dt),
            "workerStatus": state.status or "-",
            "workerDetail": worker_detail,
            "workerSeenAt": api_local_iso(state.last_worker_seen_at),
            "generation": generation,
            "minMatches": min_required_matches,
            "maxMinutes": int_or_zero(state.max_minutes),
            "visibleCandidateCount": len(review_candidates),
            "candidateCount": int_or_zero(state.candidate_count),
            "strongCandidateCount": int_or_zero(state.strong_candidate_count),
            "rawPairCount": raw_pair_count,
            "rawOneOffPairCount": raw_one_off_pair_count,
            "processedCount": int_or_zero(state.processed_count),
            "matchedCount": int_or_zero(state.matched_count),
            "qualifiedPlateCount": qualified_plate_count,
            "qualifiedPairCount": qualified_pair_count,
            "qualifiedPaidTotal": round(qualified_paid_total, 2),
            "qualifiedMatchedPaidTotal": round(qualified_matched_paid_total, 2),
            "qualifiedSun2Rows": qualified_sun2_rows if koble_view == "sun2" else [],
            "qualifiedRows": [
                {
                    "id": row["id"],
                    "status": row["status"],
                    "confidence": row["confidence"],
                    "assessment": row["assessment"],
                    "plate": row["plate"],
                    "sun2Id": row["sun2_id"],
                    "vehicleName": row["navn"],
                    "vehicleArea": row["omrade"],
                    "userName": row["user_name"],
                    "matchesCount": row["matches_count"],
                    "parkingMatchCount": row["parking_match_count"],
                    "matchDaysCount": row["match_days_count"],
                    "firstMatchAt": row["first_match_at"],
                    "lastMatchAt": row["last_match_at"],
                    "avgDeltaMinutes": row["avg_delta_minutes"],
                    "parkingCount": row["parking_count"],
                    "paidTotal": row["paid_total"],
                    "matchedPaidTotal": row["matched_paid_total"],
                    "path": row["path"],
                }
                for row in qualified_candidate_rows
            ] if koble_view == "biltreff" else [],
            "candidates": review_candidates,
        },
        "cards": [
            api_card(
                "Jobb",
                state.status or "-",
                "",
                worker_detail,
                "status" if state.status != "feil" else "warning",
                href="/koble/jobb",
            ),
            api_card(
                "Sterke kandidater",
                format_short_number(state.strong_candidate_count),
                "",
                f"Avventer, minst {min_required_matches} parkeringer og 70 % sannsynlighet",
                "parking",
                href="/koble/kandidater",
            ),
            api_card(
                "Kvalifiserte kandidater",
                format_short_number(state.candidate_count),
                "",
                f"Samme bil og SUN2-ID på minst {min_required_matches} parkeringer",
                "sun2",
                href="/koble/kandidater",
            ),
            api_card(
                f"Bilnr {min_required_matches}+ parkeringer",
                format_short_number(qualified_plate_count),
                "",
                f"{format_short_number(qualified_pair_count)} SUN2-koblinger med soltreff innen {int_or_zero(state.max_minutes)} min",
                "sun2",
                href="/koble/biltreff",
            ),
            api_card(
                "Parkert ved soltreff",
                format_short_number(qualified_matched_paid_total),
                "kr",
                "Unike parkeringer som har soltreff i kvalifisert grunnlag",
                "parking",
                href="/koble/biltreff",
            ),
            api_card(
                "Parkert totalt",
                format_short_number(qualified_paid_total),
                "kr",
                "Samlet parkering for disse unike bilene",
                "parking",
                href="/koble/biltreff",
            ),
            api_card(
                "Behandlet",
                format_short_number(state.processed_count),
                "parkeringer",
                f"{format_short_number(state.checked_plate_count)} biler, {format_short_number(state.matched_count)} treff",
                "parking",
                href="/koble/jobb",
            ),
            api_card(
                "Worker sist sett",
                worker_seen,
                "",
                f"Generasjon {generation}",
                "status",
                href="/admin/datakilder",
            ),
        ],
        "charts": [],
        "actions": [
            {
                "label": "Start",
                "path": "/api/actions/koble/start",
                "method": "POST",
                "variant": "primary",
                "confirm": "Starte koblingsjobben?",
            },
            {
                "label": "Stopp",
                "path": "/api/actions/koble/stop",
                "method": "POST",
                "confirm": "Stoppe koblingsjobben?",
            },
            {
                "label": "Start fra nyeste",
                "path": "/api/actions/koble/restart",
                "method": "POST",
                "confirm": "Tomme koblingsgrunnlag og starte fra nyeste parkering?",
            },
        ],
        "tables": [
            api_table(
                "Jobbparametere",
                [
                    "id",
                    "enabled",
                    "generation",
                    "min_matches",
                    "max_minutes",
                    "recent_days",
                    "idle_sleep_seconds",
                    "status",
                    "status_text",
                    "last_worker_seen_at",
                ],
                [state_row],
                edit=parking_sun_link_settings_edit(),
            ),
            api_table(
                "Kvalifiserte koblinger",
                [
                    "status",
                    "confidence",
                    "assessment",
                    "plate",
                    "sun2_id",
                    "parking_match_count",
                    "matches_count",
                    "match_days_count",
                    "plate_candidate_count",
                    "sun2_candidate_count",
                    "competitor_matches_count",
                    "first_match_at",
                    "last_match_at",
                    "avg_delta_minutes",
                    "navn",
                    "omrade",
                    "user_name",
                    "parking_count",
                    "matched_paid_total",
                    "paid_total",
                    "note",
                ],
                [],
                edit=parking_sun_link_candidate_edit(),
            ),
            api_table(
                "SUN2 med biltreff",
                [
                    "sun2Id",
                    "sun2VehicleCount",
                    "userName",
                    "plate",
                    "vehicleName",
                    "matchesCount",
                    "parkingMatchCount",
                    "parkingCount",
                    "parkingWithoutSunCount",
                    "parkingMatchShare",
                    "lastMatchAt",
                    "confidence",
                    "status",
                    "matchedPaidTotal",
                    "paidTotal",
                ],
                [],
            ),
            api_table(
                f"Bilnr med {min_required_matches}+ parkeringer",
                [
                    "status",
                    "plate",
                    "sun2_id",
                    "user_name",
                    "matches_count",
                    "parking_match_count",
                    "match_days_count",
                    "confidence",
                    "last_match_at",
                    "avg_delta_minutes",
                    "navn",
                    "omrade",
                    "parking_count",
                    "matched_paid_total",
                    "paid_total",
                ],
                [],
            ),
            api_table(
                "Treffgrunnlag",
                [
                    "parking_start_at",
                    "sun_started_at",
                    "delta_minutes",
                    "plate",
                    "sun2_id",
                    "room_label",
                    "user_name",
                    "duration_minutes",
                    "paid_amount_kr",
                    "fee_inc_vat",
                    "source_system",
                    "parking_id",
                    "sun_session_id",
                ],
                [api_parking_sun_link_match_row(row) for row in matches],
            ),
            api_table(
                "Sist behandlet",
                ["checked_at", "plate", "parking_record_id", "parking_start_at", "matches_found"],
                processed_table_rows,
            ),
        ],
        "filters": [
            api_filter("limit", "Antall", "number", limit_value),
        ],
    }

