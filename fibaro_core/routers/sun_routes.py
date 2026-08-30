"""Sun HTTP routes; runtime services are supplied by composition."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import Response
from fibaro_core.export_definitions import SUN2_BED_COLUMNS
from fibaro_core.export_definitions import SUN2_IMPORT_COLUMNS
from fibaro_core.export_definitions import SUN2_MEMBER_COLUMNS
from fibaro_core.export_definitions import SUN2_ROOM_COLUMNS
from fibaro_core.export_definitions import SUN2_SESSION_COLUMNS
from fibaro_core.export_definitions import SUN2_SESSION_IMPORT_COLUMNS
from fibaro_core.models import EnergyHourlyConsumption
from fibaro_core.models import SettlementImport
from fibaro_core.models import Sun2Bed
from fibaro_core.models import Sun2ImportRun
from fibaro_core.models import Sun2Member
from fibaro_core.models import Sun2RoomDailyStat
from fibaro_core.models import Sun2SessionImportRun
from fibaro_core.models import Sun2TanningSession
from fibaro_core.models import Sun2TanningSessionImage
from fibaro_core.routers.bundle import RouterBundle
from fibaro_core.services.comparisons.years import build_sun2_year_comparison
from fibaro_core.services.forecasts.snapshots import save_forecast_snapshots
from fibaro_core.services.forecasts.snapshots import saved_forecast_table
from fibaro_core.services.settlements.parsing import SUN_SETTLEMENT_PROVIDER
from fibaro_core.services.settlements.parsing import is_settlement_attachment
from fibaro_core.services.settlements.parsing import parse_settlement_period
from fibaro_core.services.settlements.parsing import parse_sun_settlement_attachment
from fibaro_core.services.settlements.parsing import settlement_parsed_meta
from fibaro_core.services.settlements.parsing import settlement_period_from_parsed_dates
from fibaro_core.services.settlements.presentation import sun_settlement_detail_payload
from fibaro_core.services.summaries.periods import parse_anchor_year
from pathlib import Path
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sun2_helpers import normalize_room_id
from sun2_helpers import sun2_room_label
from time_formatting import LOCAL_TZ
from time_formatting import local_now_naive
from typing import Any, Callable
from typing import Dict
from typing import Optional
from urllib.parse import quote
from urllib.parse import urlencode
from value_parsing import float_or_zero
import hashlib
import json
import math
import mimetypes
import re


@dataclass
class Dependencies:
    SUMMARY_CACHE: Any
    SUMMARY_CACHE_TTL: Any
    SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS: Any
    async_session: Callable[..., Any]
    axis_snapshot_browser_payload: Callable[..., Any]
    axis_snapshot_path_for_id: Callable[..., Any]
    backfill_sun2_room_identity: Callable[..., Any]
    build_sun2_forecast: Callable[..., Any]
    clear_summary_cache: Callable[..., Any]
    get_sun2_session_database_total: Callable[..., Any]
    get_sun2_session_options: Callable[..., Any]
    get_sun2_summaries: Callable[..., Any]
    parse_axis_snapshot_id: Callable[..., Any]
    primary_sun2_session_image: Callable[..., Any]
    redirect_keep_query: Callable[..., Any]
    replace_sun2_session_image_with_axis_snapshot: Callable[..., Any]
    require_settings_access: Callable[..., Any]
    row_to_dict: Callable[..., Any]
    run_sun2_axis_snapshot_link_once: Callable[..., Any]
    set_sun2_session_primary_image: Callable[..., Any]
    sun2_session_image_meta_options: Callable[..., Any]
    templates: Any


def create_router(dependencies: Dependencies) -> RouterBundle:
    router = APIRouter()

    SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS = dependencies.SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS

    @router.get("/soling/enkeltimer/{session_id:int}/bilde.jpg")
    async def sun2_session_image(session_id: int):
        async_session = dependencies.async_session
        primary_sun2_session_image = dependencies.primary_sun2_session_image
        async with async_session() as session:
            images = (
                await session.execute(
                    select(Sun2TanningSessionImage)
                    .where(Sun2TanningSessionImage.session_id == session_id)
                    .order_by(
                        Sun2TanningSessionImage.is_primary.desc(),
                        Sun2TanningSessionImage.offset_seconds.desc(),
                        Sun2TanningSessionImage.created_at.desc(),
                    )
                )
            ).scalars().all()
            image = primary_sun2_session_image(images)
        if not image:
            raise HTTPException(status_code=404, detail="Ingen bilde koblet til denne soltimen.")
        return Response(
            content=image.image_bytes,
            media_type=image.content_type or "image/jpeg",
            headers={"Cache-Control": "private, max-age=3600"},
        )

    @router.get("/soling/enkeltimer/{session_id:int}/bilder/{image_id:int}.jpg")
    async def sun2_session_image_item(session_id: int, image_id: int):
        async_session = dependencies.async_session
        async with async_session() as session:
            image = (
                await session.execute(
                    select(Sun2TanningSessionImage)
                    .where(Sun2TanningSessionImage.session_id == session_id)
                    .where(Sun2TanningSessionImage.id == image_id)
                )
            ).scalars().first()
        if not image:
            raise HTTPException(status_code=404, detail="Fant ikke bildet.")
        return Response(
            content=image.image_bytes,
            media_type=image.content_type or "image/jpeg",
            headers={"Cache-Control": "private, max-age=86400, immutable"},
        )

    @router.get("/api/soling/axis-snapshots/{snapshot_id}/image")
    async def api_sun2_axis_snapshot_image(snapshot_id: str):
        axis_snapshot_path_for_id = dependencies.axis_snapshot_path_for_id
        snapshot = axis_snapshot_path_for_id(snapshot_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Fant ikke Axis-bildet.")
        _captured_at, path = snapshot
        return FileResponse(
            path,
            media_type="image/jpeg",
            headers={"Cache-Control": "private, max-age=86400, immutable"},
        )

    @router.get("/api/soling/enkeltimer/{session_id:int}/image-browser")
    async def api_sun2_session_image_browser(session_id: int, snapshot_id: Optional[str] = None):
        async_session = dependencies.async_session
        axis_snapshot_browser_payload = dependencies.axis_snapshot_browser_payload
        parse_axis_snapshot_id = dependencies.parse_axis_snapshot_id
        sun2_session_image_meta_options = dependencies.sun2_session_image_meta_options
        if snapshot_id and parse_axis_snapshot_id(snapshot_id) is None:
            raise HTTPException(status_code=400, detail="Ugyldig bilde-ID.")
        async with async_session() as session:
            row = (
                await session.execute(
                    select(Sun2TanningSession).where(Sun2TanningSession.id == session_id)
                )
            ).scalars().first()
            if not row:
                raise HTTPException(status_code=404, detail="Fant ikke soltimen.")
            images = (
                await session.execute(
                    select(Sun2TanningSessionImage)
                    .options(sun2_session_image_meta_options())
                    .where(Sun2TanningSessionImage.session_id == session_id)
                    .order_by(Sun2TanningSessionImage.offset_seconds.asc(), Sun2TanningSessionImage.captured_at.asc())
                )
            ).scalars().all()
        return axis_snapshot_browser_payload(row, images, snapshot_id)

    @router.post("/api/soling/enkeltimer/{session_id:int}/image")
    async def api_sun2_session_select_image(
        request: Request,
        session_id: int,
        snapshot_id: str = Query(...),
    ):
        async_session = dependencies.async_session
        parse_axis_snapshot_id = dependencies.parse_axis_snapshot_id
        replace_sun2_session_image_with_axis_snapshot = dependencies.replace_sun2_session_image_with_axis_snapshot
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        if parse_axis_snapshot_id(snapshot_id) is None:
            raise HTTPException(status_code=400, detail="Ugyldig bilde-ID.")
        async with async_session() as session:
            payload = await replace_sun2_session_image_with_axis_snapshot(session, session_id, snapshot_id)
            await session.commit()
        return {
            "status": "ok",
            "message": "Bildet er byttet.",
            "browser": payload,
        }

    @router.post("/api/soling/enkeltimer/{session_id:int}/bilder/{image_id:int}/primary")
    async def api_sun2_session_set_primary_image(
        request: Request,
        session_id: int,
        image_id: int,
    ):
        async_session = dependencies.async_session
        require_settings_access = dependencies.require_settings_access
        set_sun2_session_primary_image = dependencies.set_sun2_session_primary_image
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        async with async_session() as session:
            payload = await set_sun2_session_primary_image(session, session_id, image_id)
            await session.commit()
        return {
            "status": "ok",
            "message": "Hovedbildet er oppdatert.",
            "browser": payload,
        }

    @router.get("/api/soling/year-comparison")
    async def api_v2_sun2_year_comparison(year: Optional[str] = Query(None)):
        async_session = dependencies.async_session
        get_sun2_summaries = dependencies.get_sun2_summaries
        now_dt = local_now_naive()
        anchor_year = parse_anchor_year(year, now_dt.year)
        async with async_session() as session:
            summaries = await get_sun2_summaries(session)
        return build_sun2_year_comparison(summaries, now_dt, anchor_year)

    @router.get("/api/soling/settlements/{settlement_id}")
    async def api_v2_sun_settlement_detail(settlement_id: int):
        async_session = dependencies.async_session
        async with async_session() as session:
            row = await session.get(SettlementImport, settlement_id)
            if not row or row.provider != SUN_SETTLEMENT_PROVIDER:
                raise HTTPException(status_code=404, detail="Oppgjør ikke funnet")
            return await sun_settlement_detail_payload(session, row)

    @router.get("/api/soling/settlements/{settlement_id}/attachment")
    async def api_v2_sun_settlement_attachment(settlement_id: int, download: bool = False):
        async_session = dependencies.async_session
        async with async_session() as session:
            row = await session.get(SettlementImport, settlement_id)
            if not row or row.provider != SUN_SETTLEMENT_PROVIDER:
                raise HTTPException(status_code=404, detail="Oppgjør ikke funnet")
            filename = row.attachment_filename or f"soling-oppgjor-{row.id}"
            content_type = row.attachment_content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
            disposition_type = "attachment" if download else "inline"
            quoted_filename = quote(filename)
            return Response(
                content=row.attachment_bytes,
                media_type=content_type,
                headers={
                    "Content-Disposition": f"{disposition_type}; filename*=UTF-8''{quoted_filename}",
                    "Cache-Control": "private, max-age=300",
                },
            )

    @router.post("/api/actions/soling/save-forecast")
    async def api_v2_sun2_save_forecast(request: Request):
        async_session = dependencies.async_session
        build_sun2_forecast = dependencies.build_sun2_forecast
        clear_summary_cache = dependencies.clear_summary_cache
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        now_local = datetime.now(LOCAL_TZ)
        today_value = now_local.date()
        async with async_session() as session:
            forecast = await build_sun2_forecast(session, today_value, now_local)
            await save_forecast_snapshots(session, "sun2", forecast, getattr(request.state, "access_key_name", None))
            await session.commit()
        clear_summary_cache("sun2")
        return {"status": "ok", "message": "Solingprognose lagret."}

    @router.post("/api/actions/soling/upload-settlement")
    async def api_v2_upload_sun_settlement(request: Request):
        async_session = dependencies.async_session
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=400, detail="Mangler fil")
        filename = Path(getattr(upload, "filename", "") or "").name
        if not filename:
            raise HTTPException(status_code=400, detail="Mangler filnavn")
        content = await upload.read()
        if not content:
            raise HTTPException(status_code=400, detail="Tom fil")
        content_type = getattr(upload, "content_type", None) or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        if not is_settlement_attachment(filename, content_type):
            raise HTTPException(status_code=400, detail="Filtypen støttes ikke for oppgjør")

        sha = hashlib.sha256(content).hexdigest()
        parsed = parse_sun_settlement_attachment(filename, content_type, content)
        period_start, period_end, period_label = settlement_period_from_parsed_dates(parsed, "delivery_date", "credit_note_date")
        if not period_start:
            period_start, period_end, period_label = parse_settlement_period(filename, None)
        meta = settlement_parsed_meta(parsed)
        status = "tolket" if float_or_zero(meta.get("confidence")) >= 0.6 else "krever kontroll"

        async with async_session() as session:
            existing = (
                await session.execute(
                    select(SettlementImport)
                    .where(SettlementImport.provider == SUN_SETTLEMENT_PROVIDER)
                    .where(SettlementImport.attachment_sha256 == sha)
                    .limit(1)
                )
            ).scalars().first()
            if existing:
                return {
                    "status": "ok",
                    "message": "Solingsoppgjøret finnes allerede.",
                    "id": existing.id,
                    "path": f"/soling/oppgjor/{existing.id}",
                }
            row = SettlementImport(
                provider=SUN_SETTLEMENT_PROVIDER,
                source="manual_upload",
                sender="manual",
                gmail_message_id=None,
                gmail_uid=None,
                email_subject=filename,
                email_date=None,
                mailbox=None,
                period_start=period_start,
                period_end=period_end,
                period_label=period_label,
                attachment_filename=filename,
                attachment_content_type=content_type,
                attachment_sha256=sha,
                attachment_size=len(content),
                attachment_bytes=content,
                status=status,
                parsed=parsed,
                raw={"settlement_parser": meta, "source": "manual_upload"},
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return {
            "status": "ok",
            "message": f"Solingsoppgjør importert: {period_label}.",
            "id": row.id,
            "path": f"/soling/oppgjor/{row.id}",
        }

    @router.post("/api/sun2/backfill-room-identity")
    async def sun2_backfill_room_identity():
        async_session = dependencies.async_session
        backfill_sun2_room_identity = dependencies.backfill_sun2_room_identity
        clear_summary_cache = dependencies.clear_summary_cache
        async with async_session() as session:
            counts = await backfill_sun2_room_identity(session)
            await session.commit()
        clear_summary_cache("sun2", "sun2_sessions", "sun2_session_options", "sun2_session_database_total")
        return {"status": "ok", **counts}

    @router.get("/sun2/room-stats")
    async def sun2_room_stats_legacy_redirect(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/soling/detaljer", status_code=307)

    @router.get("/sun2/room-stats/json")
    async def sun2_room_stats_json_legacy_redirect(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/api/sun2/room-stats/json", status_code=307)

    @router.get("/energi/soling", response_class=HTMLResponse)
    async def energy_soling_legacy_redirect(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/soling/detaljer", status_code=307)

    @router.get("/soling")
    async def sun2_redirect(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/soling/dagslinje", status_code=307)

    @router.get("/soling/oversikt", response_class=HTMLResponse)
    async def sun2_overview_view(request: Request):
        async_session = dependencies.async_session
        get_sun2_summaries = dependencies.get_sun2_summaries
        templates = dependencies.templates
        async with async_session() as session:
            summaries = await get_sun2_summaries(session)
            latest_import = (
                await session.execute(
                    select(Sun2ImportRun)
                    .order_by(Sun2ImportRun.timestamp.desc())
                    .limit(1)
                )
            ).scalars().first()
        return templates.TemplateResponse(
            request,
            "sun2_overview.html",
            {
                "top_days": summaries["top_days"],
                "top_months": summaries["top_months"],
                "top_days_by_count": summaries["top_days_by_count"],
                "top_months_by_count": summaries["top_months_by_count"],
                "grand_total": summaries["total"],
                "weekly_chart": summaries["weekly_chart"],
                "first_date": summaries["first_date"],
                "last_date": summaries["last_date"],
                "total_rows": summaries["total_rows"],
                "latest_import": latest_import,
            },
        )

    @router.get("/soling/prognose", response_class=HTMLResponse)
    async def sun2_forecast_view(request: Request):
        async_session = dependencies.async_session
        build_sun2_forecast = dependencies.build_sun2_forecast
        templates = dependencies.templates
        now_local = datetime.now(LOCAL_TZ)
        today = now_local.date()
        async with async_session() as session:
            forecast = await build_sun2_forecast(session, today, now_local)
            saved_forecasts = await saved_forecast_table(session, "sun2")
        response = templates.TemplateResponse(
            request,
            "sun2_forecast.html",
            {
                "forecast": forecast,
                "day": forecast["day"],
                "month": forecast["month"],
                "year": forecast["year"],
                "saved_forecasts": saved_forecasts,
                "saved": request.query_params.get("saved") == "1",
            },
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @router.post("/soling/prognose/lagre")
    async def sun2_forecast_save(request: Request):
        async_session = dependencies.async_session
        build_sun2_forecast = dependencies.build_sun2_forecast
        now_local = datetime.now(LOCAL_TZ)
        today = now_local.date()
        async with async_session() as session:
            forecast = await build_sun2_forecast(session, today, now_local)
            await save_forecast_snapshots(session, "sun2", forecast, getattr(request.state, "access_key_name", None))
            await session.commit()
        return RedirectResponse("/soling/prognose?saved=1", status_code=303)

    @router.get("/soling/detaljer", response_class=HTMLResponse)
    async def sun2_room_stats_view(request: Request, limit: int = 150):
        async_session = dependencies.async_session
        get_sun2_summaries = dependencies.get_sun2_summaries
        templates = dependencies.templates
        limit = max(1, min(limit, 1000))
        async with async_session() as session:
            summaries = await get_sun2_summaries(session)
            rows = (
                await session.execute(
                    select(Sun2RoomDailyStat)
                    .order_by(Sun2RoomDailyStat.stat_date.desc(), Sun2RoomDailyStat.room)
                    .limit(limit)
                )
            ).scalars().all()
            imports = (
                await session.execute(
                    select(Sun2ImportRun)
                    .order_by(Sun2ImportRun.timestamp.desc())
                    .limit(25)
                )
            ).scalars().all()
        return templates.TemplateResponse(
            request,
            "sun2_room_stats.html",
            {
                "rows": rows,
                "imports": imports,
                "limit": limit,
                "monthly_totals": summaries["monthly"],
                "yearly_totals": summaries["yearly"],
                "grand_total": summaries["total"],
                "first_date": summaries["first_date"],
                "last_date": summaries["last_date"],
                "total_rows": summaries["total_rows"],
            },
        )

    @router.get("/soling/enkeltimer", response_class=HTMLResponse)
    async def sun2_sessions_view(
        request: Request,
        limit: int = 50,
        page: int = 1,
        scope: Optional[str] = None,
        sun2_user_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        room_id: Optional[str] = None,
        room: Optional[str] = None,
        payment_method: Optional[str] = None,
        status: Optional[str] = None,
        customer_type: Optional[str] = None,
        q: Optional[str] = None,
    ):
        SUMMARY_CACHE = dependencies.SUMMARY_CACHE
        SUMMARY_CACHE_TTL = dependencies.SUMMARY_CACHE_TTL
        async_session = dependencies.async_session
        get_sun2_session_database_total = dependencies.get_sun2_session_database_total
        get_sun2_session_options = dependencies.get_sun2_session_options
        primary_sun2_session_image = dependencies.primary_sun2_session_image
        sun2_session_image_meta_options = dependencies.sun2_session_image_meta_options
        templates = dependencies.templates
        message = request.query_params.get("message", "")
        error = request.query_params.get("error", "")
        limit = max(25, min(limit, 1000))
        page = max(1, page)
        active_sun2_user_id = (sun2_user_id or "").strip()
        active_room_id = normalize_room_id(room_id)
        active_room = (room or "").strip()
        active_payment_method = (payment_method or "").strip()
        active_status = (status or "").strip()
        active_customer_type = (customer_type or "").strip()
        active_q = (q or "").strip()
        active_scope = (scope or "recent").strip().lower()
        if active_scope not in {"recent", "all"}:
            active_scope = "recent"
        active_date_from = None
        active_date_to = None
        try:
            active_date_from = date.fromisoformat(date_from) if date_from else None
        except ValueError:
            active_date_from = None
        try:
            active_date_to = date.fromisoformat(date_to) if date_to else None
        except ValueError:
            active_date_to = None
        user_has_filters = any([
            active_sun2_user_id,
            active_date_from,
            active_date_to,
            active_room_id,
            active_room,
            active_payment_method,
            active_status,
            active_customer_type,
            active_q,
        ])
        auto_recent_window = active_scope != "all" and not user_has_filters
        if auto_recent_window:
            active_date_to = datetime.now(LOCAL_TZ).date()
            active_date_from = active_date_to - timedelta(days=119)

        session_filters = []
        if active_sun2_user_id:
            session_filters.append(Sun2TanningSession.sun2_user_id == active_sun2_user_id)
        if active_date_from:
            session_filters.append(Sun2TanningSession.stat_date >= active_date_from)
        if active_date_to:
            session_filters.append(Sun2TanningSession.stat_date <= active_date_to)
        if active_room_id:
            session_filters.append(Sun2TanningSession.room_id == active_room_id)
        if active_room:
            session_filters.append(Sun2TanningSession.room == active_room)
        if active_payment_method:
            session_filters.append(Sun2TanningSession.payment_method == active_payment_method)
        if active_status:
            session_filters.append(Sun2TanningSession.status == active_status)
        if active_customer_type:
            session_filters.append(Sun2TanningSession.customer_type == active_customer_type)
        if active_q:
            like = f"%{active_q.lower()}%"
            q_room_id = normalize_room_id(active_q)
            numeric_match = re.fullmatch(r"\d{1,2}", active_q)
            if numeric_match:
                q_room_id = normalize_room_id(f"rom-{int(active_q):02d}")
            search_terms = [
                func.lower(func.coalesce(Sun2TanningSession.user_name, "")).like(like),
                func.lower(func.coalesce(Sun2TanningSession.user_identifier, "")).like(like),
                func.lower(func.coalesce(Sun2TanningSession.sun2_user_id, "")).like(like),
                func.lower(func.coalesce(Sun2TanningSession.room_id, "")).like(like),
                func.lower(func.coalesce(Sun2TanningSession.room, "")).like(like),
                func.lower(func.coalesce(Sun2TanningSession.source_room_name, "")).like(like),
                func.lower(func.coalesce(Sun2TanningSession.sun2_bed_id, "")).like(like),
                func.lower(func.coalesce(Sun2TanningSession.payment_method, "")).like(like),
                func.lower(func.coalesce(Sun2TanningSession.status, "")).like(like),
                func.lower(func.coalesce(Sun2TanningSession.source_file, "")).like(like),
            ]
            if q_room_id:
                search_terms.append(Sun2TanningSession.room_id == q_room_id)
            session_filters.append(or_(
                *search_terms,
            ))

        async with async_session() as session:
            options = await get_sun2_session_options(session)
            room_id_options = options["room_ids"]
            room_options = options["rooms"]
            payment_options = options["payments"]
            status_options = options["statuses"]
            customer_options = options["customers"]

            rows_query = select(Sun2TanningSession)
            if session_filters:
                rows_query = rows_query.where(*session_filters)
            offset = (page - 1) * limit
            rows = (
                await session.execute(
                    rows_query
                    .order_by(Sun2TanningSession.started_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
            ).scalars().all()
            image_lookup: Dict[int, Sun2TanningSessionImage] = {}
            row_ids = [row.id for row in rows if row.id]
            if row_ids:
                image_rows = (
                    await session.execute(
                        select(Sun2TanningSessionImage)
                        .options(sun2_session_image_meta_options())
                        .where(Sun2TanningSessionImage.session_id.in_(row_ids))
                        .order_by(Sun2TanningSessionImage.offset_seconds.asc(), Sun2TanningSessionImage.captured_at.asc())
                    )
                ).scalars().all()
                images_by_session: Dict[int, list[Sun2TanningSessionImage]] = defaultdict(list)
                for image in image_rows:
                    images_by_session[image.session_id].append(image)
                image_lookup = {
                    session_id: primary_sun2_session_image(images)
                    for session_id, images in images_by_session.items()
                    if primary_sun2_session_image(images)
                }
            imports = (
                await session.execute(
                    select(Sun2SessionImportRun)
                    .order_by(Sun2SessionImportRun.timestamp.desc())
                    .limit(10)
                )
            ).scalars().all()
            analytics_cache_parts = {
                "scope": active_scope,
                "sun2_user_id": active_sun2_user_id,
                "date_from": active_date_from.isoformat() if active_date_from else "",
                "date_to": active_date_to.isoformat() if active_date_to else "",
                "room_id": active_room_id or "",
                "room": active_room,
                "payment_method": active_payment_method,
                "status": active_status,
                "customer_type": active_customer_type,
                "q": active_q,
            }
            analytics_cache_key = "sun2_sessions:" + hashlib.sha1(
                json.dumps(analytics_cache_parts, sort_keys=True).encode("utf-8")
            ).hexdigest()
            now_value = datetime.utcnow()
            cached_analytics = SUMMARY_CACHE.get(analytics_cache_key)
            if cached_analytics and cached_analytics.get("expires", datetime.min) > now_value:
                analytics = cached_analytics["value"]
                total = analytics["total"]
                database_total = analytics["database_total"]
                total_count = int((total or {}).get("sessions_count") or 0)
                monthly = analytics.get("monthly", [])
                chart_granularity = analytics["chart_granularity"]
                daily = analytics["daily"]
                hourly_rows = analytics["hourly_rows"]
                top_rooms = analytics["top_rooms"]
                top_users = analytics["top_users"]
                payment_breakdown = analytics["payment_breakdown"]
                status_breakdown = analytics["status_breakdown"]
            else:
                total_query = select(
                    func.count(Sun2TanningSession.id).label("sessions_count"),
                    func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                    func.coalesce(func.avg(Sun2TanningSession.duration_minutes), 0).label("avg_duration_minutes"),
                    func.coalesce(func.avg(Sun2TanningSession.paid_amount_kr), 0).label("avg_paid_amount_kr"),
                    func.count(func.distinct(Sun2TanningSession.sun2_user_id)).label("unique_users_count"),
                    func.min(Sun2TanningSession.started_at).label("first_at"),
                    func.max(Sun2TanningSession.started_at).label("last_at"),
                )
                if session_filters:
                    total_query = total_query.where(*session_filters)
                total = dict((await session.execute(total_query)).mappings().first() or {})
                database_total = total
                if session_filters:
                    database_total = await get_sun2_session_database_total(session)
                total_count = int((total or {}).get("sessions_count") or 0)
                monthly = []

                chart_span_days = None
                if active_date_from and active_date_to:
                    chart_span_days = (active_date_to - active_date_from).days + 1
                chart_granularity = "month" if (active_scope == "all" or (chart_span_days and chart_span_days > 370)) else "day"
                if chart_granularity == "month":
                    chart_year_part = func.extract("year", Sun2TanningSession.stat_date)
                    chart_month_part = func.extract("month", Sun2TanningSession.stat_date)
                    day_query = (
                        select(
                            chart_year_part.label("year"),
                            chart_month_part.label("month"),
                            func.count(Sun2TanningSession.id).label("sessions_count"),
                            func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                            func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                        )
                        .group_by(chart_year_part, chart_month_part)
                        .order_by(chart_year_part.asc(), chart_month_part.asc())
                    )
                else:
                    day_query = (
                        select(
                            Sun2TanningSession.stat_date.label("day"),
                            func.count(Sun2TanningSession.id).label("sessions_count"),
                            func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                            func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                        )
                        .group_by(Sun2TanningSession.stat_date)
                        .order_by(Sun2TanningSession.stat_date.asc())
                    )
                if session_filters:
                    day_query = day_query.where(*session_filters)
                daily = [dict(item) for item in (await session.execute(day_query)).mappings().all()]

                hour_part = func.extract("hour", Sun2TanningSession.started_at)
                hourly_query = (
                    select(
                        hour_part.label("hour"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                    )
                    .group_by(hour_part)
                    .order_by(hour_part.asc())
                )
                if session_filters:
                    hourly_query = hourly_query.where(*session_filters)
                hourly_rows = [dict(item) for item in (await session.execute(hourly_query)).mappings().all()]

                top_rooms_query = (
                    select(
                        Sun2TanningSession.room_id.label("room_id"),
                        func.max(Sun2TanningSession.room).label("source_room_name"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                    )
                    .group_by(Sun2TanningSession.room_id)
                    .order_by(func.count(Sun2TanningSession.id).desc())
                    .limit(10)
                )
                if session_filters:
                    top_rooms_query = top_rooms_query.where(*session_filters)
                top_rooms = [
                    {
                        **dict(item),
                        "label": sun2_room_label(item.get("room_id"), item.get("source_room_name")),
                    }
                    for item in (await session.execute(top_rooms_query)).mappings().all()
                ]

                top_users_query = (
                    select(
                        Sun2TanningSession.sun2_user_id.label("sun2_user_id"),
                        func.max(Sun2TanningSession.user_name).label("user_name"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                        func.max(Sun2TanningSession.started_at).label("last_at"),
                    )
                    .where(Sun2TanningSession.sun2_user_id.is_not(None))
                    .where(Sun2TanningSession.sun2_user_id != "")
                    .group_by(Sun2TanningSession.sun2_user_id)
                    .order_by(func.count(Sun2TanningSession.id).desc())
                    .limit(10)
                )
                if session_filters:
                    top_users_query = top_users_query.where(*session_filters)
                top_users = [dict(item) for item in (await session.execute(top_users_query)).mappings().all()]

                payment_query = (
                    select(
                        Sun2TanningSession.payment_method.label("label"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                    )
                    .group_by(Sun2TanningSession.payment_method)
                    .order_by(func.count(Sun2TanningSession.id).desc())
                    .limit(8)
                )
                if session_filters:
                    payment_query = payment_query.where(*session_filters)
                payment_breakdown = [dict(item) for item in (await session.execute(payment_query)).mappings().all()]

                status_query = (
                    select(
                        Sun2TanningSession.status.label("label"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                    )
                    .group_by(Sun2TanningSession.status)
                    .order_by(func.count(Sun2TanningSession.id).desc())
                    .limit(8)
                )
                if session_filters:
                    status_query = status_query.where(*session_filters)
                status_breakdown = [dict(item) for item in (await session.execute(status_query)).mappings().all()]

                SUMMARY_CACHE[analytics_cache_key] = {
                    "expires": now_value + SUMMARY_CACHE_TTL,
                    "value": {
                        "total": total,
                        "database_total": database_total,
                        "monthly": monthly,
                        "chart_granularity": chart_granularity,
                        "daily": daily,
                        "hourly_rows": hourly_rows,
                        "top_rooms": top_rooms,
                        "top_users": top_users,
                        "payment_breakdown": payment_breakdown,
                        "status_breakdown": status_breakdown,
                    },
                }
            page_count = max(1, math.ceil(total_count / limit))
            if page > page_count:
                page = page_count
                offset = (page - 1) * limit
                rows = (
                    await session.execute(
                        rows_query
                        .order_by(Sun2TanningSession.started_at.desc())
                        .offset(offset)
                        .limit(limit)
                    )
                ).scalars().all()
                row_ids = [row.id for row in rows if row.id]
                if row_ids:
                    image_rows = (
                        await session.execute(
                            select(Sun2TanningSessionImage)
                            .options(sun2_session_image_meta_options())
                            .where(Sun2TanningSessionImage.session_id.in_(row_ids))
                            .order_by(Sun2TanningSessionImage.offset_seconds.asc(), Sun2TanningSessionImage.captured_at.asc())
                        )
                    ).scalars().all()
                    images_by_session = defaultdict(list)
                    for image in image_rows:
                        images_by_session[image.session_id].append(image)
                    image_lookup = {
                        session_id: primary_sun2_session_image(images)
                        for session_id, images in images_by_session.items()
                        if primary_sun2_session_image(images)
                    }
                else:
                    image_lookup = {}

        filter_values = {
            "limit": limit,
            "page": page,
            "scope": active_scope,
            "sun2_user_id": active_sun2_user_id,
            "date_from": active_date_from.isoformat() if active_date_from else "",
            "date_to": active_date_to.isoformat() if active_date_to else "",
            "room_id": active_room_id or "",
            "room": active_room,
            "payment_method": active_payment_method,
            "status": active_status,
            "customer_type": active_customer_type,
            "q": active_q,
        }
        def query_url(**updates):
            params = dict(filter_values)
            params.update(updates)
            if params.get("scope") == "recent" and not params.get("date_from") and not params.get("date_to"):
                params.pop("scope", None)
            params = {key: value for key, value in params.items() if value not in (None, "", 0)}
            return f"/soling/enkeltimer?{urlencode(params)}"

        hourly_lookup = {int(item.get("hour") or 0): item for item in hourly_rows}
        hourly = [
            {
                "hour": hour,
                "label": f"{hour:02d}",
                "sessions_count": int((hourly_lookup.get(hour) or {}).get("sessions_count") or 0),
                "paid_amount_kr": float((hourly_lookup.get(hour) or {}).get("paid_amount_kr") or 0),
            }
            for hour in range(24)
        ]
        peak_hour = max(hourly, key=lambda item: item["sessions_count"], default=None)
        best_day = max(daily, key=lambda item: item.get("sessions_count") or 0, default=None)
        daily_chart = [
            {
                "date": (
                    item.get("day").isoformat()
                    if chart_granularity == "day" and item.get("day")
                    else f"{int(item.get('year')):04d}-{int(item.get('month')):02d}-01"
                ),
                "label": (
                    item.get("day").strftime("%d.%m.%Y")
                    if chart_granularity == "day" and item.get("day")
                    else f"{int(item.get('month')):02d}.{int(item.get('year')):04d}"
                ),
                "sessions_count": int(item.get("sessions_count") or 0),
                "duration_hours": round(float(item.get("duration_minutes") or 0) / 60, 2),
                "paid_amount_kr": round(float(item.get("paid_amount_kr") or 0), 2),
            }
            for item in daily
        ]
        active_filter_count = sum(1 for key in ["sun2_user_id", "room_id", "room", "payment_method", "status", "customer_type", "q"] if filter_values.get(key))
        if user_has_filters and (filter_values.get("date_from") or filter_values.get("date_to")):
            active_filter_count += 1
        pagination = {
            "page": page,
            "page_count": page_count,
            "limit": limit,
            "total_count": total_count,
            "from_row": min(total_count, offset + 1) if total_count else 0,
            "to_row": min(total_count, offset + len(rows)),
            "prev_url": query_url(page=max(1, page - 1)) if page > 1 else "",
            "next_url": query_url(page=min(page_count, page + 1)) if page < page_count else "",
            "pages": [
                {"number": number, "url": query_url(page=number), "active": number == page}
                for number in range(max(1, page - 2), min(page_count, page + 2) + 1)
            ],
        }
        return templates.TemplateResponse(
            request,
            "sun2_sessions.html",
            {
                "rows": rows,
                "imports": imports,
                "limit": limit,
                "total": total or {},
                "database_total": database_total or {},
                "monthly": monthly,
                "daily_chart": daily_chart,
                "chart_granularity": chart_granularity,
                "auto_recent_window": auto_recent_window,
                "hourly": hourly,
                "peak_hour": peak_hour,
                "best_day": best_day,
                "top_rooms": top_rooms,
                "top_users": top_users,
                "payment_breakdown": payment_breakdown,
                "status_breakdown": status_breakdown,
                "room_id_options": room_id_options,
                "room_options": room_options,
                "payment_options": payment_options,
                "status_options": status_options,
                "customer_options": customer_options,
                "filters": filter_values,
                "active_filter_count": active_filter_count,
                "pagination": pagination,
                "query_url": query_url,
                "active_sun2_user_id": active_sun2_user_id,
                "image_lookup": image_lookup,
                "message": message,
                "error": error,
            },
        )

    @router.post("/api/actions/soling/link-snapshot-images")
    async def api_v2_sun2_link_snapshot_images(
        request: Request,
        days: int = 7,
        limit: int = 5000,
        tolerance_seconds: int = SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS,
        replace: bool = False,
    ):
        require_settings_access = dependencies.require_settings_access
        run_sun2_axis_snapshot_link_once = dependencies.run_sun2_axis_snapshot_link_once
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        result = await run_sun2_axis_snapshot_link_once(
            "manual_api",
            days=days,
            limit=limit,
            tolerance_seconds=tolerance_seconds,
            replace=replace,
        )
        return {"status": "ok", "result": result}

    @router.get("/soling/dagslinje", response_class=HTMLResponse)
    async def sun2_day_timeline_view(request: Request, day: Optional[str] = None):
        async_session = dependencies.async_session
        templates = dependencies.templates
        try:
            selected = date.fromisoformat(day) if day else datetime.now(LOCAL_TZ).date()
        except ValueError:
            selected = datetime.now(LOCAL_TZ).date()

        day_start = datetime.combine(selected, time.min)
        day_end = day_start + timedelta(days=1)
        visible_room_numbers = list(range(1, 10)) + [11, 12, 13]
        visible_room_ids = [f"rom-{number:02d}" for number in visible_room_numbers]
        room_lookup = {
            room_id: {
                "room_id": room_id,
                "label": f"Rom {int(room_id.rsplit('-', 1)[-1])}",
                "sessions": [],
                "count": 0,
                "minutes": 0.0,
                "paid": 0.0,
            }
            for room_id in visible_room_ids
        }

        async with async_session() as session:
            rows = (
                await session.execute(
                    select(Sun2TanningSession)
                    .where(Sun2TanningSession.stat_date == selected)
                    .where(Sun2TanningSession.room_id.in_(visible_room_ids))
                    .order_by(Sun2TanningSession.room_id.asc(), Sun2TanningSession.started_at.asc())
                )
            ).scalars().all()
            energy_rows = (
                await session.execute(
                    select(
                        EnergyHourlyConsumption.hour.label("hour"),
                        func.coalesce(func.sum(EnergyHourlyConsumption.consumption_kwh), 0).label("consumption_kwh"),
                        func.coalesce(func.sum(EnergyHourlyConsumption.production_kwh), 0).label("production_kwh"),
                        func.count(EnergyHourlyConsumption.id).label("rows_count"),
                    )
                    .where(EnergyHourlyConsumption.stat_date == selected)
                    .group_by(EnergyHourlyConsumption.hour)
                    .order_by(EnergyHourlyConsumption.hour.asc())
                )
            ).mappings().all()

        totals = {"sessions_count": 0, "duration_minutes": 0.0, "duration_hours": 0.0, "paid_amount_kr": 0.0}
        aggregate_sessions = []
        for row in rows:
            room_id = normalize_room_id(row.room_id)
            if room_id not in room_lookup or not row.started_at:
                continue
            start_at = row.started_at
            end_at = row.ended_at
            if getattr(start_at, "tzinfo", None):
                start_at = start_at.astimezone(LOCAL_TZ).replace(tzinfo=None)
            if end_at and getattr(end_at, "tzinfo", None):
                end_at = end_at.astimezone(LOCAL_TZ).replace(tzinfo=None)
            if not end_at:
                end_at = start_at + timedelta(minutes=float(row.duration_minutes or 15))
            if end_at <= start_at:
                end_at = start_at + timedelta(minutes=max(1.0, float(row.duration_minutes or 1)))

            clamped_start = max(day_start, min(day_end, start_at))
            clamped_end = max(clamped_start, min(day_end, end_at))
            duration_minutes = max(0.0, (clamped_end - clamped_start).total_seconds() / 60)
            if duration_minutes <= 0:
                continue

            left = round(((clamped_start - day_start).total_seconds() / 86400) * 100, 4)
            width = max(0.18, round(((clamped_end - clamped_start).total_seconds() / 86400) * 100, 4))
            customer_type = (row.customer_type or "").lower()
            kind = "standard"
            if "ikke" in customer_type:
                kind = "no-member"
            elif "medlem" in customer_type:
                kind = "member"
            paid = float(row.paid_amount_kr or 0)
            label = f"{start_at:%H:%M}"
            title_parts = [
                f"{room_lookup[room_id]['label']} {start_at:%H:%M}-{end_at:%H:%M}",
                f"{duration_minutes:.0f} min",
            ]
            if row.user_name:
                title_parts.append(str(row.user_name))
            if paid:
                title_parts.append(f"{paid:.0f} kr")
            item = {
                "left": left,
                "width": width,
                "label": label,
                "title": " | ".join(title_parts),
                "kind": kind,
                "href": f"/soling/enkeltimer?date_from={selected.isoformat()}&date_to={selected.isoformat()}&room_id={room_id}",
            }
            room_lookup[room_id]["sessions"].append(item)
            aggregate_sessions.append({**item, "label": room_lookup[room_id]["label"]})
            room_lookup[room_id]["count"] += 1
            room_lookup[room_id]["minutes"] += duration_minutes
            room_lookup[room_id]["paid"] += paid
            totals["sessions_count"] += 1
            totals["duration_minutes"] += duration_minutes
            totals["paid_amount_kr"] += paid

        totals["duration_hours"] = round(totals["duration_minutes"] / 60, 2)
        rooms = [room_lookup[room_id] for room_id in visible_room_ids]
        busiest_room = max(rooms, key=lambda item: item["count"], default=None)
        if busiest_room and not busiest_room["count"]:
            busiest_room = None
        today = datetime.now(LOCAL_TZ).date()
        now_marker = None
        if selected == today:
            now_local = datetime.now(LOCAL_TZ).replace(tzinfo=None)
            now_marker = round(max(0, min(100, ((now_local - day_start).total_seconds() / 86400) * 100)), 3)
        ticks = [{"label": f"{hour:02d}", "left": round(hour / 24 * 100, 4)} for hour in range(0, 25, 2)]
        energy_lookup = {int(item.get("hour") or 0): item for item in energy_rows}
        energy_hours = []
        max_energy_kwh = max([float((item.get("consumption_kwh") or 0)) for item in energy_rows] or [0.0])
        total_energy_kwh = sum(float((item.get("consumption_kwh") or 0)) for item in energy_rows)
        for hour in range(24):
            item = energy_lookup.get(hour) or {}
            consumption = float(item.get("consumption_kwh") or 0)
            production = float(item.get("production_kwh") or 0)
            energy_hours.append(
                {
                    "hour": hour,
                    "left": round(hour / 24 * 100, 4),
                    "width": round(100 / 24, 4),
                    "height": round((consumption / max_energy_kwh) * 100, 2) if max_energy_kwh else 0,
                    "consumption_kwh": consumption,
                    "production_kwh": production,
                    "title": f"{hour:02d}:00-{(hour + 1) % 24:02d}:00 | {consumption:.2f} kWh",
                }
            )
        peak_energy_hour = max(energy_hours, key=lambda item: item["consumption_kwh"], default=None)
        if peak_energy_hour and not peak_energy_hour["consumption_kwh"]:
            peak_energy_hour = None
        energy_summary = {
            "hours_count": len([item for item in energy_hours if item["consumption_kwh"] > 0]),
            "total_kwh": total_energy_kwh,
            "max_kwh": max_energy_kwh,
            "peak_hour": peak_energy_hour,
        }

        return templates.TemplateResponse(
            request,
            "sun2_day_timeline.html",
            {
                "selected_day": selected.isoformat(),
                "selected_day_label": selected.strftime("%d.%m.%Y"),
                "prev_day": (selected - timedelta(days=1)).isoformat(),
                "next_day": (selected + timedelta(days=1)).isoformat(),
                "rooms": rooms,
                "aggregate_sessions": aggregate_sessions,
                "totals": totals,
                "busiest_room": busiest_room,
                "ticks": ticks,
                "now_marker": now_marker,
                "energy_hours": energy_hours,
                "energy_summary": energy_summary,
            },
        )

    @router.get("/soling/senger", response_class=HTMLResponse)
    async def sun2_beds_view(request: Request):
        async_session = dependencies.async_session
        templates = dependencies.templates
        async with async_session() as session:
            beds = (
                await session.execute(
                    select(Sun2Bed).order_by(Sun2Bed.physical_room_number, Sun2Bed.room_id, Sun2Bed.name)
                )
            ).scalars().all()
            totals_rows = (
                await session.execute(
                    select(
                        Sun2TanningSession.room_id.label("room_id"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                        func.max(Sun2TanningSession.started_at).label("last_at"),
                    )
                    .group_by(Sun2TanningSession.room_id)
                )
            ).mappings().all()
        totals = {item["room_id"]: item for item in totals_rows}
        return templates.TemplateResponse(
            request,
            "sun2_beds.html",
            {
                "beds": beds,
                "totals": totals,
                "room_label": sun2_room_label,
            },
        )

    @router.get("/soling/medlemmer", response_class=HTMLResponse)
    async def sun2_members_view(
        request: Request,
        q: str = "",
        customer_type: str = "",
        status: str = "",
        limit: int = 250,
    ):
        async_session = dependencies.async_session
        templates = dependencies.templates
        search = (q or "").strip()
        active_customer_type = (customer_type or "").strip()
        active_status = (status or "").strip()
        limit = max(25, min(limit, 1000))
        filters = []
        if search:
            like = f"%{search.lower()}%"
            filters.append(
                or_(
                    func.lower(func.coalesce(Sun2Member.sun2_user_id, "")).like(like),
                    func.lower(func.coalesce(Sun2Member.name, "")).like(like),
                    func.lower(func.coalesce(Sun2Member.display_name, "")).like(like),
                    func.lower(func.coalesce(Sun2Member.initials, "")).like(like),
                    func.lower(func.coalesce(Sun2Member.email, "")).like(like),
                    func.lower(func.coalesce(Sun2Member.phone, "")).like(like),
                )
            )
        if active_customer_type:
            filters.append(Sun2Member.customer_type == active_customer_type)
        if active_status:
            filters.append(Sun2Member.status == active_status)

        async with async_session() as session:
            rows_query = select(Sun2Member)
            for condition in filters:
                rows_query = rows_query.where(condition)
            members = (
                await session.execute(
                    rows_query
                    .order_by(Sun2Member.imported_at.desc(), Sun2Member.name, Sun2Member.display_name, Sun2Member.sun2_user_id)
                    .limit(limit)
                )
            ).scalars().all()
            member_ids = [member.sun2_user_id for member in members if member.sun2_user_id]
            stats = {}
            if member_ids:
                stats_rows = (
                    await session.execute(
                        select(
                            Sun2TanningSession.sun2_user_id.label("sun2_user_id"),
                            func.count(Sun2TanningSession.id).label("sessions_count"),
                            func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                            func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                            func.max(Sun2TanningSession.started_at).label("last_session_at"),
                            func.max(Sun2TanningSession.user_name).label("session_name"),
                        )
                        .where(Sun2TanningSession.sun2_user_id.in_(member_ids))
                        .group_by(Sun2TanningSession.sun2_user_id)
                    )
                ).mappings().all()
                stats = {item["sun2_user_id"]: item for item in stats_rows}
            totals = (
                await session.execute(
                    select(
                        func.count(Sun2Member.id).label("members_count"),
                        func.count(Sun2Member.name).label("named_count"),
                        func.count(Sun2Member.email).label("email_count"),
                        func.count(Sun2Member.phone).label("phone_count"),
                        func.max(Sun2Member.imported_at).label("last_imported_at"),
                    )
                )
            ).mappings().first() or {}
            customer_options = (
                await session.execute(
                    select(Sun2Member.customer_type).where(Sun2Member.customer_type.is_not(None)).distinct().order_by(Sun2Member.customer_type)
                )
            ).scalars().all()
            status_options = (
                await session.execute(
                    select(Sun2Member.status).where(Sun2Member.status.is_not(None)).distinct().order_by(Sun2Member.status)
                )
            ).scalars().all()
            known_from_sessions = (
                await session.execute(
                    select(func.count(func.distinct(Sun2TanningSession.sun2_user_id)))
                    .where(Sun2TanningSession.sun2_user_id.is_not(None))
                    .where(Sun2TanningSession.sun2_user_id != "")
                )
            ).scalar_one()
        return templates.TemplateResponse(
            request,
            "sun2_members.html",
            {
                "members": members,
                "stats": stats,
                "totals": totals,
                "known_from_sessions": known_from_sessions,
                "filters": {
                    "q": search,
                    "customer_type": active_customer_type,
                    "status": active_status,
                    "limit": limit,
                },
                "customer_options": customer_options,
                "status_options": status_options,
            },
        )

    @router.get("/api/sun2/room-stats/json")
    async def sun2_room_stats_json(limit: int = 300):
        async_session = dependencies.async_session
        get_sun2_summaries = dependencies.get_sun2_summaries
        row_to_dict = dependencies.row_to_dict
        limit = max(1, min(limit, 5000))
        async with async_session() as session:
            summaries = await get_sun2_summaries(session)
            rows = (
                await session.execute(
                    select(Sun2RoomDailyStat)
                    .order_by(Sun2RoomDailyStat.stat_date.desc(), Sun2RoomDailyStat.room)
                    .limit(limit)
                )
            ).scalars().all()
            imports = (
                await session.execute(
                    select(Sun2ImportRun)
                    .order_by(Sun2ImportRun.timestamp.desc())
                    .limit(min(limit, 500))
                )
            ).scalars().all()
        return {
            "rows": [row_to_dict(row, SUN2_ROOM_COLUMNS) for row in rows],
            "imports": [row_to_dict(row, SUN2_IMPORT_COLUMNS) for row in imports],
            "daily_totals": summaries["daily"],
            "monthly_totals": summaries["monthly"],
            "yearly_totals": summaries["yearly"],
            "top_days": summaries["top_days"],
            "top_months": summaries["top_months"],
            "top_days_by_count": summaries["top_days_by_count"],
            "top_months_by_count": summaries["top_months_by_count"],
            "grand_total": summaries["total"],
            "first_date": summaries["first_date"],
            "last_date": summaries["last_date"],
            "total_rows": summaries["total_rows"],
        }

    @router.get("/api/sun2/beds/json")
    async def sun2_beds_json():
        async_session = dependencies.async_session
        row_to_dict = dependencies.row_to_dict
        async with async_session() as session:
            rows = (
                await session.execute(
                    select(Sun2Bed).order_by(Sun2Bed.physical_room_number, Sun2Bed.room_id, Sun2Bed.name)
                )
            ).scalars().all()
        return {"rows": [row_to_dict(row, SUN2_BED_COLUMNS) for row in rows]}

    @router.get("/api/sun2/members/json")
    async def sun2_members_json(limit: int = 300, q: Optional[str] = None):
        async_session = dependencies.async_session
        row_to_dict = dependencies.row_to_dict
        limit = max(1, min(limit, 5000))
        search = (q or "").strip()
        async with async_session() as session:
            rows_query = select(Sun2Member)
            if search:
                like = f"%{search.lower()}%"
                rows_query = rows_query.where(
                    or_(
                        func.lower(func.coalesce(Sun2Member.sun2_user_id, "")).like(like),
                        func.lower(func.coalesce(Sun2Member.name, "")).like(like),
                        func.lower(func.coalesce(Sun2Member.display_name, "")).like(like),
                        func.lower(func.coalesce(Sun2Member.initials, "")).like(like),
                        func.lower(func.coalesce(Sun2Member.email, "")).like(like),
                        func.lower(func.coalesce(Sun2Member.phone, "")).like(like),
                    )
                )
            rows = (
                await session.execute(
                    rows_query
                    .order_by(Sun2Member.imported_at.desc(), Sun2Member.sun2_user_id)
                    .limit(limit)
                )
            ).scalars().all()
        return {"rows": [row_to_dict(row, SUN2_MEMBER_COLUMNS) for row in rows], "q": search or None}

    @router.get("/api/sun2/sessions/json")
    async def sun2_sessions_json(limit: int = 300, sun2_user_id: Optional[str] = None):
        async_session = dependencies.async_session
        row_to_dict = dependencies.row_to_dict
        limit = max(1, min(limit, 5000))
        active_sun2_user_id = (sun2_user_id or "").strip()
        async with async_session() as session:
            rows_query = select(Sun2TanningSession)
            if active_sun2_user_id:
                rows_query = rows_query.where(Sun2TanningSession.sun2_user_id == active_sun2_user_id)
            rows = (
                await session.execute(
                    rows_query
                    .order_by(Sun2TanningSession.started_at.desc())
                    .limit(limit)
                )
            ).scalars().all()
            imports = (
                await session.execute(
                    select(Sun2SessionImportRun)
                    .order_by(Sun2SessionImportRun.timestamp.desc())
                    .limit(min(limit, 500))
                )
            ).scalars().all()
        return {
            "rows": [row_to_dict(row, SUN2_SESSION_COLUMNS) for row in rows],
            "imports": [row_to_dict(row, SUN2_SESSION_IMPORT_COLUMNS) for row in imports],
            "sun2_user_id": active_sun2_user_id or None,
        }

    return RouterBundle(router, {
        "api_sun2_axis_snapshot_image": api_sun2_axis_snapshot_image,
        "api_sun2_session_image_browser": api_sun2_session_image_browser,
        "api_sun2_session_select_image": api_sun2_session_select_image,
        "api_sun2_session_set_primary_image": api_sun2_session_set_primary_image,
        "api_v2_sun2_link_snapshot_images": api_v2_sun2_link_snapshot_images,
        "api_v2_sun2_save_forecast": api_v2_sun2_save_forecast,
        "api_v2_sun2_year_comparison": api_v2_sun2_year_comparison,
        "api_v2_sun_settlement_attachment": api_v2_sun_settlement_attachment,
        "api_v2_sun_settlement_detail": api_v2_sun_settlement_detail,
        "api_v2_upload_sun_settlement": api_v2_upload_sun_settlement,
        "energy_soling_legacy_redirect": energy_soling_legacy_redirect,
        "sun2_backfill_room_identity": sun2_backfill_room_identity,
        "sun2_beds_json": sun2_beds_json,
        "sun2_beds_view": sun2_beds_view,
        "sun2_day_timeline_view": sun2_day_timeline_view,
        "sun2_forecast_save": sun2_forecast_save,
        "sun2_forecast_view": sun2_forecast_view,
        "sun2_members_json": sun2_members_json,
        "sun2_members_view": sun2_members_view,
        "sun2_overview_view": sun2_overview_view,
        "sun2_redirect": sun2_redirect,
        "sun2_room_stats_json": sun2_room_stats_json,
        "sun2_room_stats_json_legacy_redirect": sun2_room_stats_json_legacy_redirect,
        "sun2_room_stats_legacy_redirect": sun2_room_stats_legacy_redirect,
        "sun2_room_stats_view": sun2_room_stats_view,
        "sun2_session_image": sun2_session_image,
        "sun2_session_image_item": sun2_session_image_item,
        "sun2_sessions_json": sun2_sessions_json,
        "sun2_sessions_view": sun2_sessions_view,
    }, dependencies)
