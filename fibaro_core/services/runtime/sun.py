"""Sun services with explicit process dependencies."""

from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fastapi import HTTPException
from fibaro_core.config import SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS
from fibaro_core.export_definitions import (
    SUN2_BED_COLUMNS,
    SUN2_IMPORT_COLUMNS,
    SUN2_MEMBER_COLUMNS,
    SUN2_SESSION_COLUMNS,
)
from fibaro_core.models import (
    EnergyFibaroSample,
    EnergyHourlyConsumption,
    ImportJobStatus,
    Sun2Bed,
    Sun2FinanceSettlement,
    Sun2Member,
    Sun2ProductSale,
    Sun2RoomDailyStat,
    Sun2TanningSession,
    Sun2TanningSessionImage,
)
from fibaro_core.schemas import (
    Sun2BedsIngestIn,
    Sun2FinanceSettlementsIngestIn,
    Sun2MembersIngestIn,
    Sun2ProductSalesIngestIn,
    Sun2RoomStatsIngestIn,
    Sun2TanningSessionIn,
    Sun2TanningSessionsIngestIn,
)
from fibaro_core.services.forecasts import builders as forecast_builders
from fibaro_core.services.forecasts.calendar import iter_dates, month_end
from fibaro_core.services.presentation import (
    api_card,
    api_chart,
    api_table,
    api_table_meta,
    format_short_number,
)
from fibaro_core.services.settlements.controls import sun2_product_sales_period_summary
from fibaro_core.services.settlements.source_queries import (
    sun2_product_amount_ex_expr,
    sun2_product_amount_inc_expr,
    sun2_product_daily_scope_condition,
    sun2_product_monthly_scope_condition,
)
from fibaro_core.services.summaries.periods import add_months
from pathlib import Path
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import load_only
from sun2_helpers import (
    SUN2_ROOM_MAP_BY_DISPLAY,
    SUN2_ROOM_OPTIONS,
    SUN2_ROOM_UNKNOWN_OLD_10,
    normalize_room_id,
    repair_mojibake,
    room_key_from_name,
    sun2_room_identity,
    sun2_room_label,
)
from time import monotonic
from time_formatting import LOCAL_TZ, local_now_naive, normalize_local_naive
from typing import Any, Callable, Dict, Iterable, Optional
from urllib.parse import urlencode
from value_parsing import float_or_zero, int_or_zero
import asyncio
import hashlib
import json
import re
import urllib.request


@dataclass
class Dependencies:
    AXIS_SNAPSHOT_FILENAME_RE: Any
    AXIS_SNAPSHOT_ID_RE: Any
    SUMMARY_CACHE: Any
    SUN2_AXIS_SNAPSHOT_DAY_CACHE_ARCHIVE_SECONDS: Any
    SUN2_AXIS_SNAPSHOT_DAY_CACHE_CURRENT_SECONDS: Any
    SUN2_AXIS_SNAPSHOT_LINK_DAYS: Any
    SUN2_AXIS_SNAPSHOT_LINK_ENABLED: Any
    SUN2_AXIS_SNAPSHOT_LINK_INITIAL_DELAY_SECONDS: Any
    SUN2_AXIS_SNAPSHOT_LINK_INTERVAL_SECONDS: Any
    SUN2_AXIS_SNAPSHOT_LINK_LIMIT: Any
    SUN2_AXIS_SNAPSHOT_MINUTE_ASSUMED_SECOND: Any
    SUN2_AXIS_SNAPSHOT_ROOT: Any
    SUN2_AXIS_SNAPSHOT_SERIES_OFFSETS_SECONDS: Any
    SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS: Any
    SUN2_SESSIONS_QUIET_END_HOUR: Any
    SUN2_SESSION_SCRAPER_URL: Any
    SUNROOM_DOOR_SYNC_TIMEOUT_SECONDS: Any
    api_filter: Callable[..., Any]
    api_filter_int: Callable[..., Any]
    api_filter_options: Callable[..., Any]
    api_filter_value: Callable[..., Any]
    api_pick: Callable[..., Any]
    async_session: Callable[..., Any]
    axis_snapshot_day_cache: Any
    cleanup_sunroom_door_verifications: Callable[..., Any]
    get_sun2_summaries: Callable[..., Any]
    import_job_age: Callable[..., Any]
    logger: Any
    parse_day: Callable[..., Any]
    process_locks: Any
    sunroom_door_period_key: Callable[..., Any]
    sunroom_door_verifications: Any
    sunroom_force_sync_candidates: Callable[..., Any]
    sunroom_sync_candidate_is_due: Callable[..., Any]


def create_service(dependencies: Dependencies):
    SUN2_AXIS_SNAPSHOT_LINK_DAYS = dependencies.SUN2_AXIS_SNAPSHOT_LINK_DAYS
    SUN2_AXIS_SNAPSHOT_LINK_LIMIT = dependencies.SUN2_AXIS_SNAPSHOT_LINK_LIMIT
    SUN2_AXIS_SNAPSHOT_ROOT = dependencies.SUN2_AXIS_SNAPSHOT_ROOT
    SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS = dependencies.SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS

    def parse_axis_snapshot_time(path: Path) -> Optional[datetime]:
        AXIS_SNAPSHOT_FILENAME_RE = dependencies.AXIS_SNAPSHOT_FILENAME_RE
        match = AXIS_SNAPSHOT_FILENAME_RE.match(path.name)
        if not match:
            return None
        try:
            return datetime.strptime(f"{match.group(1)} {match.group(2)}", "%Y-%m-%d %H-%M-%S")
        except ValueError:
            return None

    def axis_snapshot_id(captured_at: datetime) -> str:
        return normalize_local_naive(captured_at).strftime("%Y%m%d%H%M%S")

    def parse_axis_snapshot_id(snapshot_id: str) -> Optional[datetime]:
        AXIS_SNAPSHOT_ID_RE = dependencies.AXIS_SNAPSHOT_ID_RE
        if not AXIS_SNAPSHOT_ID_RE.fullmatch((snapshot_id or "").strip()):
            return None
        try:
            return datetime.strptime(snapshot_id, "%Y%m%d%H%M%S")
        except ValueError:
            return None

    def axis_snapshot_path_for_id(snapshot_id: str, root: Path = SUN2_AXIS_SNAPSHOT_ROOT) -> Optional[tuple[datetime, Path]]:
        captured_at = parse_axis_snapshot_id(snapshot_id)
        if captured_at is None:
            return None
        root_resolved = root.resolve()
        direct = (
            root_resolved
            / captured_at.strftime("%Y-%m-%d")
            / f"axis_{captured_at.strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
        )
        try:
            direct.resolve().relative_to(root_resolved)
        except (OSError, ValueError):
            return None
        if direct.is_file():
            return captured_at, direct
        for candidate_at, path in axis_snapshot_day_candidates(captured_at.date(), root):
            if candidate_at == captured_at:
                return candidate_at, path
        return None

    def axis_snapshot_day_candidates(day: date, root: Path = SUN2_AXIS_SNAPSHOT_ROOT) -> list[tuple[datetime, Path]]:
        SUN2_AXIS_SNAPSHOT_DAY_CACHE_ARCHIVE_SECONDS = dependencies.SUN2_AXIS_SNAPSHOT_DAY_CACHE_ARCHIVE_SECONDS
        SUN2_AXIS_SNAPSHOT_DAY_CACHE_CURRENT_SECONDS = dependencies.SUN2_AXIS_SNAPSHOT_DAY_CACHE_CURRENT_SECONDS
        axis_snapshot_day_cache = dependencies.axis_snapshot_day_cache
        root_resolved = root.resolve()
        day_dir = root_resolved / day.isoformat()
        if not day_dir.is_dir():
            return []
        try:
            day_dir.resolve().relative_to(root_resolved)
        except (OSError, ValueError):
            return []

        cache_key = (str(root_resolved), day.isoformat())
        stat = day_dir.stat()
        ttl = (
            SUN2_AXIS_SNAPSHOT_DAY_CACHE_CURRENT_SECONDS
            if day >= local_now_naive().date()
            else SUN2_AXIS_SNAPSHOT_DAY_CACHE_ARCHIVE_SECONDS
        )
        cached = axis_snapshot_day_cache.get(cache_key)
        if (
            cached
            and cached.get("mtime_ns") == stat.st_mtime_ns
            and float(cached.get("expires_at") or 0) > monotonic()
        ):
            return list(cached.get("candidates") or [])

        candidates: list[tuple[datetime, Path]] = []
        for path in day_dir.glob("*.jpg"):
            captured_at = parse_axis_snapshot_time(path)
            if captured_at is None:
                continue
            try:
                path.resolve().relative_to(root_resolved)
            except (OSError, ValueError):
                continue
            candidates.append((captured_at, path))
        candidates = sorted(candidates, key=lambda item: item[0])
        axis_snapshot_day_cache[cache_key] = {
            "mtime_ns": stat.st_mtime_ns,
            "expires_at": monotonic() + ttl,
            "candidates": candidates,
        }
        return list(candidates)

    def axis_snapshot_archive_days(root: Path = SUN2_AXIS_SNAPSHOT_ROOT) -> list[date]:
        if not root.exists():
            return []
        root_resolved = root.resolve()
        days: list[date] = []
        for path in root_resolved.iterdir():
            if not path.is_dir():
                continue
            try:
                path.resolve().relative_to(root_resolved)
                days.append(date.fromisoformat(path.name))
            except (OSError, ValueError):
                continue
        return sorted(days)

    def axis_snapshot_candidates(
        root: Path = SUN2_AXIS_SNAPSHOT_ROOT,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
    ) -> list[tuple[datetime, Path]]:
        if not root.exists():
            return []
        if start_at or end_at:
            start_bound = normalize_local_naive(start_at) if start_at else normalize_local_naive(end_at)
            end_bound = normalize_local_naive(end_at) if end_at else normalize_local_naive(start_at)
            if start_bound is None or end_bound is None:
                return []
            if end_bound < start_bound:
                start_bound, end_bound = end_bound, start_bound
            candidates: list[tuple[datetime, Path]] = []
            for day in iter_dates(start_bound.date(), end_bound.date()):
                candidates.extend(
                    item
                    for item in axis_snapshot_day_candidates(day, root)
                    if start_bound <= item[0] <= end_bound
                )
            return sorted(candidates, key=lambda item: item[0])

        candidates: list[tuple[datetime, Path]] = []
        for day in axis_snapshot_archive_days(root):
            candidates.extend(axis_snapshot_day_candidates(day, root))
        return sorted(candidates, key=lambda item: item[0])

    def closest_axis_snapshot_index(candidates: list[tuple[datetime, Path]], target_at: datetime) -> int:
        if not candidates:
            return -1
        times = [item[0] for item in candidates]
        index = bisect_left(times, target_at)
        if index <= 0:
            return 0
        if index >= len(candidates):
            return len(candidates) - 1
        before_delta = abs((times[index - 1] - target_at).total_seconds())
        after_delta = abs((times[index] - target_at).total_seconds())
        return index - 1 if before_delta <= after_delta else index

    def nearest_axis_snapshot(
        candidates: list[tuple[datetime, Path]],
        target_at: datetime,
        tolerance_seconds: int = SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS,
        times: Optional[list[datetime]] = None,
        excluded_ids: Optional[set[str]] = None,
    ) -> Optional[tuple[datetime, Path, float]]:
        if not candidates:
            return None
        times = times or [item[0] for item in candidates]
        excluded_ids = excluded_ids or set()
        start = bisect_left(times, target_at - timedelta(seconds=tolerance_seconds))
        end = bisect_right(times, target_at + timedelta(seconds=tolerance_seconds))
        options = [
            item
            for item in candidates[start:end]
            if axis_snapshot_id(item[0]) not in excluded_ids
        ]
        if not options:
            return None
        captured_at, path = min(options, key=lambda item: abs((item[0] - target_at).total_seconds()))
        delta_seconds = abs((captured_at - target_at).total_seconds())
        return captured_at, path, delta_seconds

    def axis_snapshot_series_around(
        primary_captured_at: datetime,
        root: Path = SUN2_AXIS_SNAPSHOT_ROOT,
    ) -> list[tuple[int, datetime, Path, bool]]:
        primary_captured_at = normalize_local_naive(primary_captured_at)
        if primary_captured_at is None:
            return []
        day_start = datetime.combine(primary_captured_at.date(), time.min)
        day_end = datetime.combine(primary_captured_at.date(), time.max.replace(microsecond=0))
        candidates = axis_snapshot_candidates(root=root, start_at=day_start, end_at=day_end)
        if not candidates:
            return []
        selected_index = closest_axis_snapshot_index(candidates, primary_captured_at)
        if selected_index < 0:
            return []
        selected_at = candidates[selected_index][0]
        selected_id = axis_snapshot_id(selected_at)
        window_start = max(0, selected_index - 2)
        window_end = min(len(candidates), selected_index + 3)
        primary_offset = -SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS
        series: list[tuple[int, datetime, Path, bool]] = []
        for captured_at, path in candidates[window_start:window_end]:
            relative_seconds = int(round((captured_at - selected_at).total_seconds()))
            offset_seconds = primary_offset + relative_seconds
            is_primary = axis_snapshot_id(captured_at) == selected_id
            series.append((offset_seconds, captured_at, path, is_primary))
        return series

    def sun2_session_axis_start_at(row: Sun2TanningSession) -> Optional[datetime]:
        SUN2_AXIS_SNAPSHOT_MINUTE_ASSUMED_SECOND = dependencies.SUN2_AXIS_SNAPSHOT_MINUTE_ASSUMED_SECOND
        started_at = normalize_local_naive(row.started_at)
        if not started_at:
            return None
        if started_at.second == 0 and started_at.microsecond == 0:
            raw_time = str((row.raw or {}).get("Tidspunkt") or (row.raw or {}).get("tidspunkt") or "")
            if raw_time and not re.search(r"\d{1,2}:\d{2}:\d{2}", raw_time):
                started_at = started_at + timedelta(seconds=SUN2_AXIS_SNAPSHOT_MINUTE_ASSUMED_SECOND)
        return started_at

    def sun2_session_axis_target_at(row: Sun2TanningSession) -> Optional[datetime]:
        started_at = sun2_session_axis_start_at(row)
        if not started_at:
            return None
        return started_at - timedelta(seconds=SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS)

    def sun2_session_axis_target_series(row: Sun2TanningSession) -> list[tuple[int, datetime, bool]]:
        SUN2_AXIS_SNAPSHOT_SERIES_OFFSETS_SECONDS = dependencies.SUN2_AXIS_SNAPSHOT_SERIES_OFFSETS_SECONDS
        started_at = sun2_session_axis_start_at(row)
        if not started_at:
            return []
        primary_offset = -SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS
        return [
            (offset_seconds, started_at + timedelta(seconds=offset_seconds), offset_seconds == primary_offset)
            for offset_seconds in SUN2_AXIS_SNAPSHOT_SERIES_OFFSETS_SECONDS
        ]

    def primary_sun2_session_image(images: Iterable[Sun2TanningSessionImage]) -> Optional[Sun2TanningSessionImage]:
        rows = list(images)
        if not rows:
            return None
        primary_offset = -SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS
        primary_rows = [image for image in rows if bool(getattr(image, "is_primary", False))]
        if primary_rows:
            return sorted(primary_rows, key=lambda image: image.created_at or datetime.min, reverse=True)[0]
        offset_rows = [image for image in rows if int_or_zero(getattr(image, "offset_seconds", 0)) == primary_offset]
        if offset_rows:
            return sorted(offset_rows, key=lambda image: image.created_at or datetime.min, reverse=True)[0]
        return sorted(rows, key=lambda image: abs(int_or_zero(getattr(image, "offset_seconds", 0)) - primary_offset))[0]

    def sun2_session_image_meta_options():
        return load_only(
            Sun2TanningSessionImage.id,
            Sun2TanningSessionImage.session_id,
            Sun2TanningSessionImage.captured_at,
            Sun2TanningSessionImage.target_at,
            Sun2TanningSessionImage.offset_seconds,
            Sun2TanningSessionImage.is_primary,
            Sun2TanningSessionImage.delta_seconds,
            Sun2TanningSessionImage.source,
            Sun2TanningSessionImage.created_at,
            Sun2TanningSessionImage.byte_size,
            Sun2TanningSessionImage.content_type,
        )

    def sun2_session_image_payload(row: Sun2TanningSession, image: Sun2TanningSessionImage) -> Dict[str, Any]:
        captured_at = normalize_local_naive(image.captured_at)
        image_url = f"/soling/enkeltimer/{row.id}/bilder/{image.id}.jpg" if image.id else f"/soling/enkeltimer/{row.id}/bilde.jpg"
        snapshot_id_value = axis_snapshot_id(captured_at) if captured_at else ""
        offset_seconds = int_or_zero(getattr(image, "offset_seconds", None))
        return {
            "id": image.id,
            "snapshotId": snapshot_id_value,
            "capturedAt": captured_at.isoformat() if captured_at else None,
            "label": captured_at.strftime("%d.%m.%Y %H:%M:%S") if captured_at else "",
            "imageUrl": image_url,
            "offsetSeconds": offset_seconds,
            "offsetLabel": f"{offset_seconds:+d} sek",
            "deltaSeconds": round(float_or_zero(image.delta_seconds), 1),
            "isPrimary": bool(image.is_primary),
            "source": image.source,
        }

    def axis_snapshot_browser_payload(
        row: Sun2TanningSession,
        images: Optional[list[Sun2TanningSessionImage]] = None,
        snapshot_id_value: Optional[str] = None,
    ) -> Dict[str, Any]:
        SUN2_AXIS_SNAPSHOT_ROOT = dependencies.SUN2_AXIS_SNAPSHOT_ROOT
        SUN2_AXIS_SNAPSHOT_SERIES_OFFSETS_SECONDS = dependencies.SUN2_AXIS_SNAPSHOT_SERIES_OFFSETS_SECONDS
        images = sorted(images or [], key=lambda image: (int_or_zero(getattr(image, "offset_seconds", 0)), image.captured_at or datetime.min))
        primary_image = primary_sun2_session_image(images)
        saved_images = [sun2_session_image_payload(row, image) for image in images]
        target_at = sun2_session_axis_target_at(row)
        linked_id = axis_snapshot_id(primary_image.captured_at) if primary_image and primary_image.captured_at else None
        requested_at = parse_axis_snapshot_id(snapshot_id_value or "") if snapshot_id_value else None
        preferred_at = requested_at or (normalize_local_naive(primary_image.captured_at) if primary_image and primary_image.captured_at else None) or target_at
        archive_day = (preferred_at or target_at or normalize_local_naive(row.started_at) or local_now_naive()).date()
        archive_start = datetime.combine(archive_day, time.min)
        archive_end = datetime.combine(archive_day, time.max.replace(microsecond=0))
        candidates = axis_snapshot_candidates(start_at=archive_start, end_at=archive_end)
        selected_index = closest_axis_snapshot_index(candidates, preferred_at) if preferred_at else -1

        current = None
        previous_id = None
        next_id = None
        if selected_index >= 0:
            captured_at, path = candidates[selected_index]
            current_id = axis_snapshot_id(captured_at)
            previous_id = axis_snapshot_id(candidates[selected_index - 1][0]) if selected_index > 0 else None
            next_id = axis_snapshot_id(candidates[selected_index + 1][0]) if selected_index < len(candidates) - 1 else None
            delta_seconds = abs((captured_at - target_at).total_seconds()) if target_at else None
            current = {
                "id": current_id,
                "capturedAt": captured_at.isoformat(),
                "label": captured_at.strftime("%d.%m.%Y %H:%M:%S"),
                "filename": path.name,
                "imageUrl": f"/api/soling/axis-snapshots/{current_id}/image",
                "deltaSeconds": round(delta_seconds, 1) if delta_seconds is not None else None,
                "isLinked": linked_id == current_id,
            }

        linked = None
        if primary_image:
            linked = sun2_session_image_payload(row, primary_image)

        return {
            "sessionId": row.id,
            "startedAt": row.started_at.isoformat() if row.started_at else None,
            "targetAt": target_at.isoformat() if target_at else None,
            "targetLabel": target_at.strftime("%d.%m.%Y %H:%M:%S") if target_at else "",
            "seriesOffsets": SUN2_AXIS_SNAPSHOT_SERIES_OFFSETS_SECONDS,
            "snapshotRoot": str(SUN2_AXIS_SNAPSHOT_ROOT),
            "archiveDay": archive_day.isoformat(),
            "snapshotsFound": len(candidates),
            "linked": linked,
            "savedImages": saved_images,
            "current": current,
            "previousSnapshotId": previous_id,
            "nextSnapshotId": next_id,
            "canPrevious": previous_id is not None,
            "canNext": next_id is not None,
        }

    async def replace_sun2_session_image_with_axis_snapshot(
        session,
        session_id: int,
        snapshot_id_value: str,
    ) -> Dict[str, Any]:
        snapshot = axis_snapshot_path_for_id(snapshot_id_value)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Fant ikke valgt Axis-bilde i arkivet.")
        captured_at, path = snapshot
        row = (
            await session.execute(
                select(Sun2TanningSession).where(Sun2TanningSession.id == session_id)
            )
        ).scalars().first()
        if not row:
            raise HTTPException(status_code=404, detail="Fant ikke soltimen.")

        series = axis_snapshot_series_around(captured_at)
        if not series:
            series = [(-SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS, captured_at, path, True)]
        primary_target_at = sun2_session_axis_target_at(row)
        primary_offset = -SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS
        await session.execute(
            delete(Sun2TanningSessionImage).where(Sun2TanningSessionImage.session_id == row.id)
        )
        added_primary = False
        for offset_seconds, image_captured_at, image_path, is_primary in series:
            content = image_path.read_bytes()
            if not content.startswith(b"\xff\xd8"):
                raise HTTPException(status_code=400, detail=f"Valgt bildefil er ikke et gyldig JPEG-bilde: {image_path.name}")
            relative_seconds = offset_seconds - primary_offset
            target_at = primary_target_at + timedelta(seconds=relative_seconds) if primary_target_at else None
            delta_seconds = abs((image_captured_at - target_at).total_seconds()) if target_at else None
            stat = image_path.stat()
            image = Sun2TanningSessionImage(
                session_id=row.id,
                captured_at=image_captured_at,
                target_at=target_at,
                offset_seconds=offset_seconds,
                is_primary=is_primary,
                delta_seconds=delta_seconds,
                source_path=str(image_path),
                source_mtime=datetime.fromtimestamp(stat.st_mtime, LOCAL_TZ).replace(tzinfo=None),
                content_type="image/jpeg",
                image_bytes=content,
                byte_size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                source="axis_snapshot_manual",
            )
            session.add(image)
            added_primary = added_primary or is_primary
        if not added_primary:
            raise HTTPException(status_code=400, detail="Kunne ikke finne valgt hovedbilde i bildepakken.")
        await session.flush()
        images = (
            await session.execute(
                select(Sun2TanningSessionImage)
                .options(sun2_session_image_meta_options())
                .where(Sun2TanningSessionImage.session_id == row.id)
                .order_by(Sun2TanningSessionImage.offset_seconds.asc(), Sun2TanningSessionImage.captured_at.asc())
            )
        ).scalars().all()
        return axis_snapshot_browser_payload(row, images, snapshot_id_value)

    async def set_sun2_session_primary_image(
        session,
        session_id: int,
        image_id: int,
    ) -> Dict[str, Any]:
        row = (
            await session.execute(
                select(Sun2TanningSession).where(Sun2TanningSession.id == session_id)
            )
        ).scalars().first()
        if not row:
            raise HTTPException(status_code=404, detail="Fant ikke soltimen.")

        image = (
            await session.execute(
                select(Sun2TanningSessionImage)
                .options(sun2_session_image_meta_options())
                .where(Sun2TanningSessionImage.session_id == session_id)
                .where(Sun2TanningSessionImage.id == image_id)
            )
        ).scalars().first()
        if not image:
            raise HTTPException(status_code=404, detail="Fant ikke bildet på denne soltimen.")

        await session.execute(
            update(Sun2TanningSessionImage)
            .where(Sun2TanningSessionImage.session_id == row.id)
            .values(is_primary=False)
        )
        await session.execute(
            update(Sun2TanningSessionImage)
            .where(Sun2TanningSessionImage.id == image.id)
            .values(is_primary=True)
        )
        await session.flush()

        images = (
            await session.execute(
                select(Sun2TanningSessionImage)
                .options(sun2_session_image_meta_options())
                .where(Sun2TanningSessionImage.session_id == row.id)
                .order_by(Sun2TanningSessionImage.offset_seconds.asc(), Sun2TanningSessionImage.captured_at.asc())
            )
        ).scalars().all()
        return axis_snapshot_browser_payload(row, images, axis_snapshot_id(image.captured_at) if image.captured_at else None)

    async def link_axis_snapshots_to_sun2_sessions(
        session,
        days: int = 35,
        limit: int = 5000,
        tolerance_seconds: int = SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS,
        replace: bool = False,
    ) -> Dict[str, Any]:
        SUN2_AXIS_SNAPSHOT_MINUTE_ASSUMED_SECOND = dependencies.SUN2_AXIS_SNAPSHOT_MINUTE_ASSUMED_SECOND
        SUN2_AXIS_SNAPSHOT_ROOT = dependencies.SUN2_AXIS_SNAPSHOT_ROOT
        SUN2_AXIS_SNAPSHOT_SERIES_OFFSETS_SECONDS = dependencies.SUN2_AXIS_SNAPSHOT_SERIES_OFFSETS_SECONDS
        SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS = dependencies.SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS
        logger = dependencies.logger
        days = max(1, min(int(days or 35), 3650))
        limit = max(1, min(int(limit or 5000), 50000))
        tolerance_seconds = max(1, min(int(tolerance_seconds or SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS), 300))
        start_cutoff = local_now_naive() - timedelta(days=days)
        result: Dict[str, Any] = {
            "snapshot_root": str(SUN2_AXIS_SNAPSHOT_ROOT),
            "snapshots_found": 0,
            "sessions_checked": 0,
            "linked": 0,
            "already_linked": 0,
            "no_match": 0,
            "missing_file": 0,
            "invalid_jpeg": 0,
            "errors": 0,
            "days": days,
            "limit": limit,
            "target_offset_seconds": SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS,
            "target_offsets_seconds": SUN2_AXIS_SNAPSHOT_SERIES_OFFSETS_SECONDS,
            "minute_assumed_second": SUN2_AXIS_SNAPSHOT_MINUTE_ASSUMED_SECOND,
            "tolerance_seconds": tolerance_seconds,
        }
        rows = (
            await session.execute(
                select(Sun2TanningSession)
                .where(Sun2TanningSession.started_at >= start_cutoff)
                .order_by(Sun2TanningSession.started_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        result["sessions_checked"] = len(rows)
        if not rows:
            return result

        session_ids = [row.id for row in rows if row.id]
        existing_image_rows = (
                await session.execute(
                select(
                    Sun2TanningSessionImage.session_id,
                    Sun2TanningSessionImage.offset_seconds,
                    Sun2TanningSessionImage.captured_at,
                )
                .where(Sun2TanningSessionImage.session_id.in_(session_ids))
            )
        ).all()
        existing_by_session: dict[int, set[int]] = defaultdict(set)
        used_snapshot_ids_by_session: dict[int, set[str]] = defaultdict(set)
        for session_id, offset_seconds, captured_at in existing_image_rows:
            if session_id is None:
                continue
            existing_by_session[int(session_id)].add(int_or_zero(offset_seconds))
            if captured_at:
                used_snapshot_ids_by_session[int(session_id)].add(axis_snapshot_id(captured_at))

        needed_days: set[date] = set()
        for row in rows:
            if not row.id:
                continue
            existing_offsets = set() if replace else existing_by_session.get(row.id, set())
            for offset_seconds, target_at, _is_primary in sun2_session_axis_target_series(row):
                if offset_seconds in existing_offsets:
                    continue
                needed_days.add((target_at - timedelta(seconds=tolerance_seconds)).date())
                needed_days.add((target_at + timedelta(seconds=tolerance_seconds)).date())

        candidates: list[tuple[datetime, Path]] = []
        for candidate_day in sorted(needed_days):
            candidates.extend(axis_snapshot_day_candidates(candidate_day))
        candidates.sort(key=lambda item: item[0])
        candidate_times = [item[0] for item in candidates]
        result["snapshots_found"] = len(candidates)
        result["snapshot_days_checked"] = len(needed_days)

        for row in rows:
            if not row.id:
                continue
            targets = sun2_session_axis_target_series(row)
            if not targets:
                result["no_match"] += 1
                continue
            existing_offsets = set() if replace else existing_by_session.get(row.id, set())
            used_snapshot_ids = set() if replace else used_snapshot_ids_by_session.get(row.id, set()).copy()
            if replace and existing_by_session.get(row.id):
                await session.execute(delete(Sun2TanningSessionImage).where(Sun2TanningSessionImage.session_id == row.id))
            for offset_seconds, target_at, is_primary in targets:
                if offset_seconds in existing_offsets:
                    result["already_linked"] += 1
                    continue
                match = nearest_axis_snapshot(
                    candidates,
                    target_at,
                    tolerance_seconds,
                    candidate_times,
                    excluded_ids=used_snapshot_ids,
                )
                if match is None:
                    result["no_match"] += 1
                    continue
                captured_at, path, delta_seconds = match
                try:
                    content = path.read_bytes()
                    if not content.startswith(b"\xff\xd8"):
                        result["invalid_jpeg"] += 1
                        continue
                    stat = path.stat()
                    image_values = {
                        "session_id": row.id,
                        "captured_at": captured_at,
                        "target_at": target_at,
                        "offset_seconds": offset_seconds,
                        "is_primary": is_primary,
                        "delta_seconds": delta_seconds,
                        "source_path": str(path),
                        "source_mtime": datetime.fromtimestamp(stat.st_mtime, LOCAL_TZ).replace(tzinfo=None),
                        "content_type": "image/jpeg",
                        "image_bytes": content,
                        "byte_size": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "source": "axis_snapshot_backfill",
                    }
                    insert_result = await session.execute(
                        pg_insert(Sun2TanningSessionImage)
                        .values(**image_values)
                        .on_conflict_do_nothing(index_elements=["session_id", "offset_seconds"])
                        .returning(Sun2TanningSessionImage.id)
                    )
                    existing_offsets.add(offset_seconds)
                    if insert_result.scalar_one_or_none() is None:
                        result["already_linked"] += 1
                        continue
                    used_snapshot_ids.add(axis_snapshot_id(captured_at))
                    result["linked"] += 1
                except FileNotFoundError:
                    result["missing_file"] += 1
                except Exception:
                    logger.exception("Could not link Axis snapshot to SUN2 session %s offset %s", row.id, offset_seconds)
                    result["errors"] += 1
        return result

    def get_sun2_axis_snapshot_link_lock() -> asyncio.Lock:
        process_locks = dependencies.process_locks
        if process_locks.sun2_axis_snapshot_link_lock is None:
            process_locks.sun2_axis_snapshot_link_lock = asyncio.Lock()
        return process_locks.sun2_axis_snapshot_link_lock

    async def run_sun2_axis_snapshot_link_once(
        reason: str,
        days: int = SUN2_AXIS_SNAPSHOT_LINK_DAYS,
        limit: int = SUN2_AXIS_SNAPSHOT_LINK_LIMIT,
        tolerance_seconds: int = SUN2_AXIS_SNAPSHOT_TOLERANCE_SECONDS,
        replace: bool = False,
    ) -> Dict[str, Any]:
        async_session = dependencies.async_session
        logger = dependencies.logger
        lock = get_sun2_axis_snapshot_link_lock()
        if lock.locked():
            logger.info("Axis SUN2 image link skipped, already running: reason=%s", reason)
            return {"skipped": True, "reason": "already_running"}
        async with lock:
            async with async_session() as session:
                result = await link_axis_snapshots_to_sun2_sessions(
                    session,
                    days=days,
                    limit=limit,
                    tolerance_seconds=tolerance_seconds,
                    replace=replace,
                )
                await session.commit()
            if result.get("linked") or result.get("errors"):
                logger.info(
                    "Axis SUN2 image link: reason=%s linked=%s already_linked=%s no_match=%s errors=%s snapshots=%s",
                    reason,
                    result.get("linked"),
                    result.get("already_linked"),
                    result.get("no_match"),
                    result.get("errors"),
                    result.get("snapshots_found"),
                )
            return result

    def schedule_sun2_axis_snapshot_link(reason: str, days: int = SUN2_AXIS_SNAPSHOT_LINK_DAYS) -> None:
        SUN2_AXIS_SNAPSHOT_LINK_ENABLED = dependencies.SUN2_AXIS_SNAPSHOT_LINK_ENABLED
        SUN2_AXIS_SNAPSHOT_LINK_LIMIT = dependencies.SUN2_AXIS_SNAPSHOT_LINK_LIMIT
        if not SUN2_AXIS_SNAPSHOT_LINK_ENABLED:
            return
        asyncio.create_task(run_sun2_axis_snapshot_link_once(reason, days=days, limit=SUN2_AXIS_SNAPSHOT_LINK_LIMIT))

    async def sun2_axis_snapshot_link_worker() -> None:
        SUN2_AXIS_SNAPSHOT_LINK_INITIAL_DELAY_SECONDS = dependencies.SUN2_AXIS_SNAPSHOT_LINK_INITIAL_DELAY_SECONDS
        SUN2_AXIS_SNAPSHOT_LINK_INTERVAL_SECONDS = dependencies.SUN2_AXIS_SNAPSHOT_LINK_INTERVAL_SECONDS
        logger = dependencies.logger
        await asyncio.sleep(SUN2_AXIS_SNAPSHOT_LINK_INITIAL_DELAY_SECONDS)
        while True:
            try:
                await run_sun2_axis_snapshot_link_once("periodic")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Axis SUN2 image auto-link failed")
            await asyncio.sleep(SUN2_AXIS_SNAPSHOT_LINK_INTERVAL_SECONDS)

    def sun2_sessions_active_minutes_since(stamp: Optional[datetime], now_value: Optional[datetime] = None) -> Optional[int]:
        SUN2_SESSIONS_QUIET_END_HOUR = dependencies.SUN2_SESSIONS_QUIET_END_HOUR
        if stamp is None:
            return None
        now_value = now_value or local_now_naive()
        if stamp.tzinfo is not None:
            stamp = stamp.astimezone(LOCAL_TZ).replace(tzinfo=None)
        if now_value.tzinfo is not None:
            now_value = now_value.astimezone(LOCAL_TZ).replace(tzinfo=None)
        if stamp >= now_value:
            return 0

        total = 0.0
        day = stamp.date()
        while day <= now_value.date():
            active_start = datetime.combine(day, time(hour=SUN2_SESSIONS_QUIET_END_HOUR))
            active_end = datetime.combine(day + timedelta(days=1), time.min)
            segment_start = max(stamp, active_start)
            segment_end = min(now_value, active_end)
            if segment_end > segment_start:
                total += (segment_end - segment_start).total_seconds() / 60
            day += timedelta(days=1)
        return int(total)

    async def build_sun2_forecast(session, today: date, now_local: datetime) -> Dict[str, Any]:
        SUMMARY_CACHE = dependencies.SUMMARY_CACHE
        get_sun2_summaries = dependencies.get_sun2_summaries
        return await forecast_builders.build_sun2_forecast(
            session, today, now_local, cache=SUMMARY_CACHE, summaries_getter=get_sun2_summaries,
        )

    def request_sun2_today_sync(reason: str = "door_closed") -> Dict[str, Any]:
        SUN2_SESSION_SCRAPER_URL = dependencies.SUN2_SESSION_SCRAPER_URL
        SUNROOM_DOOR_SYNC_TIMEOUT_SECONDS = dependencies.SUNROOM_DOOR_SYNC_TIMEOUT_SECONDS
        query = urlencode({"reason": reason[:120]})
        request = urllib.request.Request(
            f"{SUN2_SESSION_SCRAPER_URL}/sync-today?{query}",
            data=b"",
            method="POST",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=SUNROOM_DOOR_SYNC_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8", errors="replace")
            payload = json.loads(raw or "{}")
            if not isinstance(payload, dict) or payload.get("status") not in {"ok", "deferred"}:
                raise RuntimeError(str(payload.get("error") if isinstance(payload, dict) else "Ugyldig svar fra Sun2-synk"))
            return payload

    async def force_sun2_sync_for_closed_rooms(items: list[Dict[str, Any]], now: datetime) -> Dict[str, Any]:
        cleanup_sunroom_door_verifications = dependencies.cleanup_sunroom_door_verifications
        logger = dependencies.logger
        process_locks = dependencies.process_locks
        sunroom_door_period_key = dependencies.sunroom_door_period_key
        sunroom_door_verifications = dependencies.sunroom_door_verifications
        sunroom_force_sync_candidates = dependencies.sunroom_force_sync_candidates
        sunroom_sync_candidate_is_due = dependencies.sunroom_sync_candidate_is_due
        cleanup_sunroom_door_verifications(now)
        candidates = sunroom_force_sync_candidates(items)
        if not candidates:
            return {"attempted": False, "ok": None, "rooms": 0}

        due = [item for item in candidates if sunroom_sync_candidate_is_due(item, now)]
        if not due:
            return {"attempted": False, "ok": None, "rooms": len(candidates)}
        if process_locks.sunroom_door_sync_lock is None:
            process_locks.sunroom_door_sync_lock = asyncio.Lock()

        async with process_locks.sunroom_door_sync_lock:
            attempted_at = local_now_naive()
            due = [item for item in candidates if sunroom_sync_candidate_is_due(item, attempted_at)]
            if not due:
                return {"attempted": False, "ok": None, "rooms": len(candidates)}
            error_text = ""
            response_payload: Dict[str, Any] = {}
            room_labels = [str(item.get("displayRoomNumber") or item.get("roomId") or "?") for item in due]
            reason = f"door_closed rooms={','.join(room_labels)}"
            try:
                response_payload = await asyncio.to_thread(request_sun2_today_sync, reason)
                if response_payload.get("status") == "deferred":
                    return {
                        "attempted": False,
                        "deferred": True,
                        "ok": None,
                        "rooms": len(due),
                        "retryAfterSeconds": response_payload.get("retry_after_seconds"),
                        "nextAllowedAt": response_payload.get("next_allowed_at"),
                    }
                ok = True
            except Exception as exc:
                ok = False
                error_text = str(exc)[:1000]
                logger.warning("Tvungen Sun2-synk for doralarm feilet: %s", exc)
            for item in due:
                previous = sunroom_door_verifications.get(sunroom_door_period_key(item)) or {}
                sunroom_door_verifications[sunroom_door_period_key(item)] = {
                    "attemptedAt": attempted_at,
                    "ok": ok,
                    "error": error_text,
                    "attemptCount": int(previous.get("attemptCount") or 0) + 1,
                    "reason": "new_session_check" if item.get("session") else "missing_session",
                }
            return {
                "attempted": True,
                "attemptedAt": attempted_at.isoformat(),
                "ok": ok,
                "rooms": len(due),
                "error": error_text or None,
                "result": response_payload.get("result") if ok else None,
            }

    def fetch_sun2_scraper_runtime() -> Dict[str, Any]:
        SUN2_SESSION_SCRAPER_URL = dependencies.SUN2_SESSION_SCRAPER_URL
        request = urllib.request.Request(
            f"{SUN2_SESSION_SCRAPER_URL}/json",
            method="GET",
            headers={"Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace") or "{}")
            if not isinstance(payload, dict):
                raise ValueError("Ugyldig statusformat")
            return {"available": True, **payload}
        except Exception as exc:
            return {"available": False, "error": str(exc)[:500]}

    async def ingest_sun2_room_stats(session, data: Sun2RoomStatsIngestIn, batch_time: datetime) -> Dict[str, int]:
        inserted = 0
        updated = 0
        batch_date = data.stat_date
        for row in data.rows:
            source_room_name = (repair_mojibake(row.source_room_name or row.room) or "").strip()
            room = (repair_mojibake(row.room) or source_room_name).strip()
            room_key = (repair_mojibake(row.room_key) or room_key_from_name(source_room_name) or room_key_from_name(room) or room).strip()
            identity = sun2_room_identity(source_room_name or room, row.room_id, row.sun2_bed_id)
            if not room:
                continue
            stat_date = row.stat_date or batch_date
            existing = (
                await session.execute(
                    select(Sun2RoomDailyStat)
                    .where(Sun2RoomDailyStat.stat_date == stat_date)
                    .where(Sun2RoomDailyStat.room_key == room_key)
                )
            ).scalars().first()
            if not existing:
                existing = (
                    await session.execute(
                        select(Sun2RoomDailyStat)
                        .where(Sun2RoomDailyStat.stat_date == stat_date)
                        .where(Sun2RoomDailyStat.room == room)
                    )
                ).scalars().first()
            if not existing:
                same_day = (
                    await session.execute(
                        select(Sun2RoomDailyStat).where(Sun2RoomDailyStat.stat_date == stat_date)
                    )
                ).scalars().all()
                existing = next(
                    (
                        candidate for candidate in same_day
                        if repair_mojibake(candidate.room) == room
                        or repair_mojibake(candidate.source_room_name) == source_room_name
                        or (candidate.room_key and repair_mojibake(candidate.room_key) == room_key)
                    ),
                    None,
                )
            if not existing:
                existing = Sun2RoomDailyStat(stat_date=stat_date, room=room)
                session.add(existing)
                inserted += 1
            else:
                updated += 1

            existing.room_key = room_key
            existing.room_id = identity.get("room_id")
            existing.room = room
            existing.source_room_name = source_room_name
            existing.sun2_bed_id = identity.get("sun2_bed_id")
            existing.total_soletid_minutter = row.total_soletid_minutter
            existing.totalt_antall_solinger = row.totalt_antall_solinger
            existing.solinger_medlemmer = row.solinger_medlemmer
            existing.solinger_ikke_medlemmer = row.solinger_ikke_medlemmer
            existing.totalt_inntjent_kr = row.totalt_inntjent_kr
            existing.inntjent_medlemmer_kr = row.inntjent_medlemmer_kr
            existing.inntjent_ikke_medlemmer_kr = row.inntjent_ikke_medlemmer_kr
            existing.source = data.source
            existing.source_file = data.source_file
            existing.imported_at = batch_time
            existing.raw = row.raw or {}

        return {"inserted": inserted, "updated": updated}

    async def ingest_sun2_beds(session, data: Sun2BedsIngestIn, batch_time: datetime) -> Dict[str, int]:
        inserted = 0
        updated = 0
        skipped = 0
        for row in data.beds:
            bed_id = (repair_mojibake(row.sun2_bed_id) or "").strip()
            name = (repair_mojibake(row.name) or "").strip()
            if not bed_id or not name:
                skipped += 1
                continue
            identity = sun2_room_identity(row.source_room_name or name, row.room_id, bed_id)
            existing = (
                await session.execute(
                    select(Sun2Bed).where(Sun2Bed.sun2_bed_id == bed_id)
                )
            ).scalars().first()
            if not existing:
                existing = Sun2Bed(sun2_bed_id=bed_id, name=name)
                session.add(existing)
                inserted += 1
            else:
                updated += 1

            existing.room_id = row.room_id or identity.get("room_id")
            existing.physical_room_number = row.physical_room_number or identity.get("physical_room_number")
            existing.display_room_number = row.display_room_number or identity.get("display_room_number")
            existing.sun2_center_id = (repair_mojibake(row.sun2_center_id) or "").strip() or None
            existing.sun2_bed_id = bed_id
            existing.name = name
            existing.source_room_name = (repair_mojibake(row.source_room_name) or name).strip() or None
            existing.bed_model = (repair_mojibake(row.bed_model) or "").strip() or None
            existing.bed_model_id = (repair_mojibake(row.bed_model_id) or "").strip() or None
            existing.max_minutes = row.max_minutes
            existing.startup_minutes = row.startup_minutes
            existing.cooldown_minutes = row.cooldown_minutes
            existing.current_price_per_min = row.current_price_per_min
            existing.status = (repair_mojibake(row.status) or "").strip() or None
            existing.status_code = (repair_mojibake(row.status_code) or "").strip() or None
            existing.lamp_status = (repair_mojibake(row.lamp_status) or "").strip() or None
            existing.source = data.source
            existing.imported_at = batch_time
            existing.raw = row.raw or {}
        return {"inserted": inserted, "updated": updated, "skipped": skipped}

    async def ingest_sun2_members(session, data: Sun2MembersIngestIn, batch_time: datetime) -> Dict[str, int]:
        inserted = 0
        updated = 0
        skipped = 0
        source = data.source or "sun2_session_scraper"
        for row in data.members:
            sun2_user_id = (repair_mojibake(row.sun2_user_id) or "").strip()
            if not sun2_user_id:
                skipped += 1
                continue
            existing = (
                await session.execute(
                    select(Sun2Member).where(Sun2Member.sun2_user_id == sun2_user_id)
                )
            ).scalars().first()
            if not existing:
                existing = Sun2Member(sun2_user_id=sun2_user_id)
                session.add(existing)
                inserted += 1
            else:
                updated += 1

            existing.sun2_center_id = (repair_mojibake(row.sun2_center_id) or "").strip() or existing.sun2_center_id
            existing.name = (repair_mojibake(row.name) or "").strip() or None
            existing.display_name = (repair_mojibake(row.display_name) or "").strip() or existing.name or None
            existing.initials = (repair_mojibake(row.initials) or "").strip() or None
            existing.age = row.age
            existing.email = (repair_mojibake(row.email) or "").strip() or None
            existing.phone = (repair_mojibake(row.phone) or "").strip() or None
            existing.profile_url = (repair_mojibake(row.profile_url) or "").strip() or None
            existing.customer_type = (repair_mojibake(row.customer_type) or "").strip() or None
            existing.gender = (repair_mojibake(row.gender) or "").strip() or None
            existing.birth_date = row.birth_date
            existing.member_since = row.member_since
            existing.last_seen_at = row.last_seen_at
            existing.status = (repair_mojibake(row.status) or "").strip() or None
            existing.balance_kr = row.balance_kr
            existing.total_spent_kr = row.total_spent_kr
            existing.visits_count = row.visits_count
            existing.source = source
            existing.source_file = (repair_mojibake(row.source_file or "") or "").strip() or None
            existing.imported_at = batch_time
            existing.raw = row.raw or {}
        return {"inserted": inserted, "updated": updated, "skipped": skipped}

    async def ingest_sun2_product_sales(session, data: Sun2ProductSalesIngestIn, batch_time: datetime) -> Dict[str, int]:
        inserted = 0
        updated = 0
        skipped = 0
        source = data.source or "sun2_session_scraper"
        source_file = (repair_mojibake(data.source_file) or "").strip()
        period_summary = data.extra.get("period_summary") if isinstance(data.extra.get("period_summary"), dict) else None
        replaced = 0
        if source_file and data.rows:
            result = await session.execute(
                delete(Sun2ProductSale)
                .where(Sun2ProductSale.source == source)
                .where(Sun2ProductSale.source_file == source_file)
            )
            replaced = int(result.rowcount or 0)
        for row in data.rows:
            source_sale_id = (repair_mojibake(row.source_sale_id) or "").strip()
            stat_date = row.stat_date or (row.sold_at.date() if row.sold_at else None) or data.period_start
            if not source_sale_id or not stat_date:
                skipped += 1
                continue
            existing = (
                await session.execute(
                    select(Sun2ProductSale)
                    .where(Sun2ProductSale.source == source)
                    .where(Sun2ProductSale.source_sale_id == source_sale_id)
                )
            ).scalars().first()
            if not existing:
                existing = Sun2ProductSale(source=source, source_sale_id=source_sale_id, stat_date=stat_date)
                session.add(existing)
                inserted += 1
            else:
                updated += 1

            existing.source = source
            existing.source_sale_id = source_sale_id
            existing.sold_at = row.sold_at
            existing.stat_date = stat_date
            existing.period_start = row.period_start or data.period_start
            existing.period_end = row.period_end or data.period_end
            existing.product_name = (repair_mojibake(row.product_name) or "").strip() or None
            existing.product_category = (repair_mojibake(row.product_category) or "").strip() or None
            existing.quantity = row.quantity
            existing.unit_price_kr = row.unit_price_kr
            existing.amount_inc_vat_kr = row.amount_inc_vat_kr
            existing.amount_ex_vat_kr = row.amount_ex_vat_kr
            existing.vat_kr = row.vat_kr
            existing.payment_method = (repair_mojibake(row.payment_method) or "").strip() or None
            existing.sun2_user_id = (repair_mojibake(row.sun2_user_id) or "").strip() or None
            existing.user_name = (repair_mojibake(row.user_name) or "").strip() or None
            existing.source_file = source_file or data.source_file
            existing.imported_at = batch_time
            raw = dict(row.raw or {})
            if period_summary and not isinstance(raw.get("period_summary"), dict):
                raw["period_summary"] = period_summary
            existing.raw = raw
        return {"inserted": inserted, "updated": updated, "skipped": skipped, "replaced": replaced}

    async def ingest_sun2_finance_settlements(session, data: Sun2FinanceSettlementsIngestIn, batch_time: datetime) -> Dict[str, int]:
        inserted = 0
        updated = 0
        skipped = 0
        source = data.source or "sun2_session_scraper"
        source_file = (repair_mojibake(data.source_file) or "").strip()
        for row in data.rows:
            source_payout_id = (repair_mojibake(row.source_payout_id) or "").strip()
            if not source_payout_id or not row.period_start or not row.period_end:
                skipped += 1
                continue
            existing = (
                await session.execute(
                    select(Sun2FinanceSettlement)
                    .where(Sun2FinanceSettlement.source == source)
                    .where(Sun2FinanceSettlement.source_payout_id == source_payout_id)
                )
            ).scalars().first()
            if not existing:
                existing = Sun2FinanceSettlement(source=source, source_payout_id=source_payout_id)
                session.add(existing)
                inserted += 1
            else:
                updated += 1

            tanning_control_inc = row.tanning_control_inc_vat_kr
            tanning_values_present = any(
                value is not None
                for value in (
                    row.member_tanning_inc_vat_kr,
                    row.unregistered_tanning_inc_vat_kr,
                    row.tanning_bonus_inc_vat_kr,
                )
            )
            if tanning_control_inc is None and tanning_values_present:
                tanning_control_inc = (
                    float_or_zero(row.member_tanning_inc_vat_kr)
                    + float_or_zero(row.unregistered_tanning_inc_vat_kr)
                    - float_or_zero(row.tanning_bonus_inc_vat_kr)
                )
            tanning_control_ex = row.tanning_control_ex_vat_kr
            if tanning_control_ex is None and tanning_control_inc is not None:
                tanning_control_ex = round(tanning_control_inc / 1.25, 2)

            product_control_inc = row.product_control_inc_vat_kr
            product_values_present = any(
                value is not None
                for value in (
                    row.member_product_inc_vat_kr,
                    row.unregistered_product_inc_vat_kr,
                    row.product_bonus_inc_vat_kr,
                )
            )
            if product_control_inc is None and product_values_present:
                product_control_inc = (
                    float_or_zero(row.member_product_inc_vat_kr)
                    + float_or_zero(row.unregistered_product_inc_vat_kr)
                    - float_or_zero(row.product_bonus_inc_vat_kr)
                )
            product_control_ex = row.product_control_ex_vat_kr
            if product_control_ex is None and product_control_inc is not None:
                product_control_ex = round(product_control_inc / 1.25, 2)

            existing.source = source
            existing.source_payout_id = source_payout_id
            existing.payout_label = (repair_mojibake(row.payout_label) or "").strip() or None
            existing.period_start = row.period_start
            existing.period_end = row.period_end
            existing.payout_date = row.payout_date
            existing.member_tanning_count = row.member_tanning_count
            existing.member_tanning_inc_vat_kr = row.member_tanning_inc_vat_kr
            existing.unregistered_tanning_count = row.unregistered_tanning_count
            existing.unregistered_tanning_inc_vat_kr = row.unregistered_tanning_inc_vat_kr
            existing.tanning_bonus_inc_vat_kr = row.tanning_bonus_inc_vat_kr
            existing.tanning_control_inc_vat_kr = round(tanning_control_inc, 2) if tanning_control_inc is not None else None
            existing.tanning_control_ex_vat_kr = round(tanning_control_ex, 2) if tanning_control_ex is not None else None
            existing.member_product_count = row.member_product_count
            existing.member_product_inc_vat_kr = row.member_product_inc_vat_kr
            existing.unregistered_product_count = row.unregistered_product_count
            existing.unregistered_product_inc_vat_kr = row.unregistered_product_inc_vat_kr
            existing.product_bonus_inc_vat_kr = row.product_bonus_inc_vat_kr
            existing.product_control_inc_vat_kr = round(product_control_inc, 2) if product_control_inc is not None else None
            existing.product_control_ex_vat_kr = round(product_control_ex, 2) if product_control_ex is not None else None
            existing.transaction_cost_kr = row.transaction_cost_kr
            existing.service_fee_kr = row.service_fee_kr
            existing.payout_inc_vat_kr = row.payout_inc_vat_kr
            existing.vat_kr = row.vat_kr
            existing.source_file = source_file or data.source_file
            existing.imported_at = batch_time
            existing.raw = row.raw or {}
        return {"inserted": inserted, "updated": updated, "skipped": skipped}

    async def ingest_sun2_tanning_sessions(session, data: Sun2TanningSessionsIngestIn, batch_time: datetime) -> Dict[str, int]:
        inserted = 0
        updated = 0
        skipped = 0
        source = data.source or "sun2_session_scraper"
        source_file = (repair_mojibake(data.source_file) or "").strip()
        replaced = 0

        if source_file and data.rows:
            result = await session.execute(
                delete(Sun2TanningSession)
                .where(Sun2TanningSession.source == source)
                .where(Sun2TanningSession.source_file == source_file)
            )
            replaced = int(result.rowcount or 0)

        for row in data.rows:
            source_session_id = (repair_mojibake(row.source_session_id) or "").strip()
            if not source_session_id or not row.started_at:
                skipped += 1
                continue
            source_room_name = (repair_mojibake(row.source_room_name or row.room) or "").strip()
            room = (repair_mojibake(row.room) or source_room_name).strip()
            room_key = (repair_mojibake(row.room_key) or room_key_from_name(source_room_name) or room_key_from_name(room) or "").strip()
            identity = sun2_room_identity(source_room_name or room, row.room_id, row.sun2_bed_id)
            stat_date = row.stat_date or row.started_at.date()

            existing = (
                await session.execute(
                    select(Sun2TanningSession)
                    .where(Sun2TanningSession.source == source)
                    .where(Sun2TanningSession.source_session_id == source_session_id)
                )
            ).scalars().first()

            if not existing:
                legacy_source_session_id = str((row.raw or {}).get("legacy_source_session_id") or "").strip()
                if legacy_source_session_id:
                    existing = (
                        await session.execute(
                            select(Sun2TanningSession)
                            .where(Sun2TanningSession.source == source)
                            .where(Sun2TanningSession.source_session_id == legacy_source_session_id)
                        )
                    ).scalars().first()

            if not existing:
                natural_query = (
                    select(Sun2TanningSession)
                    .where(Sun2TanningSession.source == source)
                    .where(Sun2TanningSession.started_at == row.started_at)
                    .where(Sun2TanningSession.stat_date == stat_date)
                    .where(Sun2TanningSession.duration_minutes == row.duration_minutes)
                    .where(Sun2TanningSession.paid_amount_kr == row.paid_amount_kr)
                )
                if identity.get("sun2_bed_id"):
                    natural_query = natural_query.where(Sun2TanningSession.sun2_bed_id == identity.get("sun2_bed_id"))
                elif identity.get("room_id"):
                    natural_query = natural_query.where(Sun2TanningSession.room_id == identity.get("room_id"))
                if row.sun2_user_id:
                    natural_query = natural_query.where(Sun2TanningSession.sun2_user_id == row.sun2_user_id)
                elif row.user_identifier:
                    natural_query = natural_query.where(Sun2TanningSession.user_identifier == row.user_identifier)
                existing = (await session.execute(natural_query)).scalars().first()

            if not existing:
                existing = Sun2TanningSession(source=source, source_session_id=source_session_id)
                session.add(existing)
                inserted += 1
            else:
                updated += 1

            existing.source = source
            existing.source_session_id = source_session_id
            existing.started_at = row.started_at
            existing.ended_at = row.ended_at
            existing.stat_date = stat_date
            existing.room_id = identity.get("room_id")
            existing.room_key = room_key or None
            existing.room = room or None
            existing.source_room_name = source_room_name or None
            existing.sun2_user_id = (repair_mojibake(row.sun2_user_id) or "").strip() or None
            existing.sun2_center_id = (repair_mojibake(row.sun2_center_id) or "").strip() or None
            existing.sun2_bed_id = identity.get("sun2_bed_id")
            existing.user_name = (repair_mojibake(row.user_name) or "").strip() or None
            existing.user_identifier = (repair_mojibake(row.user_identifier) or "").strip() or None
            existing.customer_type = (repair_mojibake(row.customer_type) or "").strip() or None
            existing.gender = (repair_mojibake(row.gender) or "").strip() or None
            existing.payment_method = (repair_mojibake(row.payment_method) or "").strip() or None
            existing.duration_minutes = row.duration_minutes
            existing.paid_amount_kr = row.paid_amount_kr
            existing.status = (repair_mojibake(row.status) or "").strip() or None
            existing.source_file = source_file or data.source_file
            existing.imported_at = batch_time
            existing.raw = row.raw or {}

        return {"inserted": inserted, "updated": updated, "skipped": skipped, "replaced": replaced}

    def sun2_duplicate_session_id_payload(rows: list[Sun2TanningSessionIn]) -> list[Dict[str, Any]]:
        grouped: Dict[str, list[Sun2TanningSessionIn]] = defaultdict(list)
        for row in rows:
            source_session_id = (repair_mojibake(row.source_session_id) or "").strip()
            if source_session_id:
                grouped[source_session_id].append(row)

        duplicates: list[Dict[str, Any]] = []
        for source_session_id, items in grouped.items():
            if len(items) < 2:
                continue
            duplicates.append(
                {
                    "source_session_id": source_session_id,
                    "count": len(items),
                    "rows": [
                        {
                            "started_at": item.started_at.isoformat() if item.started_at else None,
                            "room_id": item.room_id,
                            "sun2_bed_id": item.sun2_bed_id,
                            "sun2_user_id": item.sun2_user_id,
                            "duration_minutes": item.duration_minutes,
                            "paid_amount_kr": item.paid_amount_kr,
                        }
                        for item in items
                    ],
                }
            )
        return duplicates

    async def backfill_sun2_room_identity(session) -> Dict[str, int]:
        counts = {"daily": 0, "sessions": 0}
        for model, key in [(Sun2RoomDailyStat, "daily"), (Sun2TanningSession, "sessions")]:
            source_text = func.lower(func.trim(func.coalesce(model.source_room_name, model.room, model.room_key, "")))
            missing_identity = or_(model.room_id.is_(None), model.sun2_bed_id.is_(None))
            old_room = await session.execute(
                update(model)
                .where(missing_identity)
                .where(or_(source_text == ".", source_text == "-"))
                .values(room_id=SUN2_ROOM_UNKNOWN_OLD_10["room_id"], sun2_bed_id=SUN2_ROOM_UNKNOWN_OLD_10["sun2_bed_id"])
            )
            counts[key] += int(old_room.rowcount or 0)

            for display_number, identity in SUN2_ROOM_MAP_BY_DISPLAY.items():
                room_text = f"rom {display_number}"
                result = await session.execute(
                    update(model)
                    .where(missing_identity)
                    .where(or_(source_text == room_text, source_text.like(f"{room_text} %")))
                    .values(room_id=identity["room_id"], sun2_bed_id=identity["sun2_bed_id"])
                )
                counts[key] += int(result.rowcount or 0)
        return counts

    def api_sun2_summary_row(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "period": item.get("period"),
            "period_label": item.get("period_label") or item.get("period"),
            "totalt_inntjent_kr": round(float_or_zero(item.get("totalt_inntjent_kr")), 2),
            "totalt_antall_solinger": int_or_zero(item.get("totalt_antall_solinger")),
            "total_soletid_timer": round(float_or_zero(item.get("total_soletid_timer")), 2),
            "rooms_count": int_or_zero(item.get("rooms_count")),
            "days_count": int_or_zero(item.get("days_count")),
        }

    def api_sun2_overview_tables(summaries: Dict[str, Any], latest_sessions: list[Dict[str, Any]], latest_import_rows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        return [
            api_table(
                "Topp dager omsetning",
                ["period_label", "totalt_inntjent_kr", "totalt_antall_solinger", "total_soletid_timer", "rooms_count"],
                [api_sun2_summary_row(row) for row in summaries.get("top_days", [])],
            ),
            api_table(
                "Topp uker omsetning",
                ["period_label", "totalt_inntjent_kr", "totalt_antall_solinger", "total_soletid_timer", "days_count"],
                [api_sun2_summary_row(row) for row in summaries.get("top_weeks", [])],
            ),
            api_table(
                "Topp m\u00e5neder omsetning",
                ["period", "totalt_inntjent_kr", "totalt_antall_solinger", "total_soletid_timer", "days_count"],
                [api_sun2_summary_row(row) for row in summaries.get("top_months", [])],
            ),
            api_table(
                "Topp dager antall",
                ["period_label", "totalt_antall_solinger", "totalt_inntjent_kr", "total_soletid_timer", "rooms_count"],
                [api_sun2_summary_row(row) for row in summaries.get("top_days_by_count", [])],
            ),
            api_table(
                "Topp uker antall",
                ["period_label", "totalt_antall_solinger", "totalt_inntjent_kr", "total_soletid_timer", "days_count"],
                [api_sun2_summary_row(row) for row in summaries.get("top_weeks_by_count", [])],
            ),
            api_table(
                "Topp m\u00e5neder antall",
                ["period", "totalt_antall_solinger", "totalt_inntjent_kr", "total_soletid_timer", "days_count"],
                [api_sun2_summary_row(row) for row in summaries.get("top_months_by_count", [])],
            ),
            api_table("Siste solinger", ["started_at", "room_label", "duration_minutes", "paid_amount_kr", "user_name", "customer_type", "status"], latest_sessions),
            api_table("Siste import", SUN2_IMPORT_COLUMNS, latest_import_rows),
        ]

    def api_sun2_weekly_chart(summaries: Dict[str, Any], metric: str = "revenue") -> Dict[str, Any]:
        chart_rows = summaries.get("weekly_chart", [])

        def metric_series(metric_key: str) -> list[Dict[str, Any]]:
            return [
                {
                    "name": row["year"],
                    "data": row[metric_key],
                    "color": row.get("color"),
                    "unit": "kr" if metric_key == "revenue" else "stk",
                }
                for row in chart_rows
            ]

        current_year = local_now_naive().year
        default_metric = "count" if metric == "count" else "revenue"
        return api_chart(
            "Ukesutvikling soling",
            [str(week) for week in range(1, 54)],
            metric_series(default_metric),
            "En linje per år, uke 1-53. Samme datagrunnlag som V1 oversikt.",
            "line",
            360,
            metrics=[
                {"key": "revenue", "label": "Omsetning", "unit": "kr", "series": metric_series("revenue")},
                {"key": "count", "label": "Antall", "unit": "stk", "series": metric_series("count")},
            ],
            default_metric=default_metric,
            default_visible_series=[str(current_year), str(current_year - 1)],
        )

    def api_sun2_session_row(
        row: Sun2TanningSession,
        image: Optional[Sun2TanningSessionImage] = None,
        image_count: int = 0,
        images: Optional[list[Sun2TanningSessionImage]] = None,
    ) -> Dict[str, Any]:
        api_pick = dependencies.api_pick
        data = api_pick(row, SUN2_SESSION_COLUMNS)
        if row.room_id:
            data["room_label"] = sun2_room_label(row.room_id, row.room)
        if images is not None:
            ordered_images = sorted(
                images,
                key=lambda item: (
                    int_or_zero(getattr(item, "offset_seconds", 0)),
                    item.captured_at or datetime.min,
                    item.id or 0,
                ),
            )
            image = primary_sun2_session_image(ordered_images)
            image_count = len(ordered_images)
            data["session_images"] = [sun2_session_image_payload(row, item) for item in ordered_images]
        else:
            data["session_images"] = [sun2_session_image_payload(row, image)] if image else []
        if image:
            data.update(
                {
                    "has_image": True,
                    "image_url": f"/soling/enkeltimer/{row.id}/bilde.jpg",
                    "image_captured_at": image.captured_at.isoformat() if image.captured_at else None,
                    "image_target_at": image.target_at.isoformat() if image.target_at else None,
                    "image_delta_seconds": round(float_or_zero(image.delta_seconds), 1),
                    "image_byte_size": image.byte_size,
                    "image_count": max(1, image_count),
                    "image_offset_seconds": image.offset_seconds,
                }
            )
        else:
            data.update(
                {
                    "has_image": False,
                    "image_url": "",
                    "image_captured_at": None,
                    "image_target_at": None,
                    "image_delta_seconds": None,
                    "image_byte_size": None,
                    "image_count": 0,
                    "image_offset_seconds": None,
                }
            )
        return data

    def api_sun2_bed_row(row: Sun2Bed, totals: Dict[str, Any]) -> Dict[str, Any]:
        api_pick = dependencies.api_pick
        data = api_pick(row, SUN2_BED_COLUMNS)
        total = totals.get(row.room_id) or {}
        data.update(
            {
                "room_label": sun2_room_label(row.room_id, row.name),
                "sessions_count": int_or_zero(total.get("sessions_count")),
                "duration_hours": round(float_or_zero(total.get("duration_minutes")) / 60, 2),
                "paid_amount_kr": round(float_or_zero(total.get("paid_amount_kr")), 2),
                "last_session_at": total.get("last_at"),
            }
        )
        return data

    async def api_sun2_day_timeline(session, selected: date) -> Dict[str, Any]:
        day_start = datetime.combine(selected, time.min)
        day_end = day_start + timedelta(days=1)
        visible_room_numbers = list(range(1, 10)) + [11, 12, 13]
        visible_room_ids = [f"rom-{number:02d}" for number in visible_room_numbers]
        room_lookup = {
            room_id: {
                "roomId": room_id,
                "label": f"Rom {int(room_id.rsplit('-', 1)[-1])}",
                "sessions": [],
                "count": 0,
                "minutes": 0.0,
                "paid": 0.0,
            }
            for room_id in visible_room_ids
        }

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
        internal_energy_hour = func.extract("hour", EnergyFibaroSample.bucket_start)
        internal_energy_rows = (
            await session.execute(
                select(
                    internal_energy_hour.label("hour"),
                    func.coalesce(func.sum(EnergyFibaroSample.inntak_delta_kwh), 0).label("internal_kwh"),
                    func.count(EnergyFibaroSample.id).label("samples_count"),
                )
                .where(EnergyFibaroSample.bucket_start >= day_start)
                .where(EnergyFibaroSample.bucket_start < day_end)
                .group_by(internal_energy_hour)
                .order_by(internal_energy_hour.asc())
            )
        ).mappings().all()

        totals = {"sessionsCount": 0, "durationMinutes": 0.0, "durationHours": 0.0, "paidAmountKr": 0.0}
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
                "label": f"{start_at:%H:%M}",
                "title": " | ".join(title_parts),
                "kind": kind,
                "href": f"/soling/enkeltimer?date_from={selected.isoformat()}&date_to={selected.isoformat()}&room_id={room_id}",
            }
            room_lookup[room_id]["sessions"].append(item)
            aggregate_sessions.append({**item, "label": room_lookup[room_id]["label"]})
            room_lookup[room_id]["count"] += 1
            room_lookup[room_id]["minutes"] += duration_minutes
            room_lookup[room_id]["paid"] += paid
            totals["sessionsCount"] += 1
            totals["durationMinutes"] += duration_minutes
            totals["paidAmountKr"] += paid

        totals["durationHours"] = round(totals["durationMinutes"] / 60, 2)
        rooms = [room_lookup[room_id] for room_id in visible_room_ids]
        busiest_room = max(rooms, key=lambda item: item["count"], default=None)
        if busiest_room and not busiest_room["count"]:
            busiest_room = None
        top_revenue_room = max(rooms, key=lambda item: item["paid"], default=None)
        if top_revenue_room and not top_revenue_room["paid"]:
            top_revenue_room = None
        today = datetime.now(LOCAL_TZ).date()
        now_marker = None
        if selected == today:
            now_local = datetime.now(LOCAL_TZ).replace(tzinfo=None)
            now_marker = round(max(0, min(100, ((now_local - day_start).total_seconds() / 86400) * 100)), 3)

        ticks = [{"label": f"{hour:02d}", "left": round(hour / 24 * 100, 4)} for hour in range(0, 25, 2)]
        energy_lookup = {int(item.get("hour") or 0): item for item in energy_rows}
        internal_energy_lookup = {int(item.get("hour") or 0): item for item in internal_energy_rows}
        energy_hours = []
        max_energy_kwh = max([float((item.get("consumption_kwh") or 0)) for item in energy_rows] or [0.0])
        max_internal_energy_kwh = max([float((item.get("internal_kwh") or 0)) for item in internal_energy_rows] or [0.0])
        max_visible_energy_kwh = max(max_energy_kwh, max_internal_energy_kwh)
        total_energy_kwh = sum(float((item.get("consumption_kwh") or 0)) for item in energy_rows)
        total_internal_energy_kwh = sum(float((item.get("internal_kwh") or 0)) for item in internal_energy_rows)
        total_internal_energy_samples = sum(int_or_zero(item.get("samples_count")) for item in internal_energy_rows)
        for hour in range(24):
            item = energy_lookup.get(hour) or {}
            internal_item = internal_energy_lookup.get(hour) or {}
            consumption = float(item.get("consumption_kwh") or 0)
            production = float(item.get("production_kwh") or 0)
            internal_kwh = float(internal_item.get("internal_kwh") or 0)
            internal_samples = int_or_zero(internal_item.get("samples_count"))
            energy_hours.append(
                {
                    "hour": hour,
                    "left": round(hour / 24 * 100, 4),
                    "width": round(100 / 24, 4),
                    "height": round((consumption / max_visible_energy_kwh) * 100, 2) if max_visible_energy_kwh else 0,
                    "internalHeight": round((internal_kwh / max_visible_energy_kwh) * 100, 2) if max_visible_energy_kwh else 0,
                    "consumptionKwh": consumption,
                    "productionKwh": production,
                    "internalKwh": internal_kwh,
                    "internalSamples": internal_samples,
                    "title": f"{hour:02d}:00-{(hour + 1) % 24:02d}:00 | Elvia {consumption:.2f} kWh | Egen {internal_kwh:.2f} kWh",
                }
            )
        peak_energy_hour = max(energy_hours, key=lambda item: item["consumptionKwh"], default=None)
        if peak_energy_hour and not peak_energy_hour["consumptionKwh"]:
            peak_energy_hour = None
        peak_internal_energy_hour = max(energy_hours, key=lambda item: item["internalKwh"], default=None)
        if peak_internal_energy_hour and not peak_internal_energy_hour["internalKwh"]:
            peak_internal_energy_hour = None
        return {
            "selectedDay": selected.isoformat(),
            "selectedDayLabel": selected.strftime("%d.%m.%Y"),
            "prevDay": (selected - timedelta(days=1)).isoformat(),
            "nextDay": (selected + timedelta(days=1)).isoformat(),
            "rooms": rooms,
            "aggregateSessions": aggregate_sessions,
            "totals": totals,
            "busiestRoom": busiest_room,
            "topRevenueRoom": top_revenue_room,
            "ticks": ticks,
            "nowMarker": now_marker,
            "energyHours": energy_hours,
            "energySummary": {
                "hoursCount": len([item for item in energy_hours if item["consumptionKwh"] > 0]),
                "totalKwh": total_energy_kwh,
                "maxKwh": max_energy_kwh,
                "peakHour": peak_energy_hour,
                "internalHoursCount": len([item for item in energy_hours if item["internalKwh"] > 0]),
                "internalTotalKwh": total_internal_energy_kwh,
                "internalMaxKwh": max_internal_energy_kwh,
                "internalSamples": total_internal_energy_samples,
                "internalPeakHour": peak_internal_energy_hour,
            },
        }

    def api_sun2_member_row(row: Sun2Member, stats: Dict[str, Any]) -> Dict[str, Any]:
        api_pick = dependencies.api_pick
        data = api_pick(row, SUN2_MEMBER_COLUMNS)
        stat = stats.get(row.sun2_user_id) or {}
        data.update(
            {
                "sessions_count": int_or_zero(stat.get("sessions_count")),
                "duration_hours": round(float_or_zero(stat.get("duration_minutes")) / 60, 2),
                "paid_amount_kr": round(float_or_zero(stat.get("paid_amount_kr")), 2),
                "last_session_at": stat.get("last_session_at"),
                "session_name": stat.get("session_name"),
            }
        )
        return data

    def api_sun2_forecast_rows(forecast: Dict[str, Any]) -> list[Dict[str, Any]]:
        rows = []
        for key, label in [("day", "I dag"), ("month", "Måned"), ("year", "År")]:
            item = forecast.get(key) or {}
            actual = item.get("actual") or {}
            forecast_values = item.get("forecast") or {}
            rows.append(
                {
                    "period": label,
                    "label": item.get("label") or label,
                    "actual_sessions": round(float_or_zero(actual.get("sessions")), 1),
                    "forecast_sessions": round(float_or_zero(forecast_values.get("sessions")), 1),
                    "actual_paid": round(float_or_zero(actual.get("paid")), 2),
                    "forecast_paid": round(float_or_zero(forecast_values.get("paid")), 2),
                    "actual_hours": round(float_or_zero(actual.get("minutes")) / 60, 2),
                    "forecast_hours": round(float_or_zero(forecast_values.get("minutes")) / 60, 2),
                    "tempo": round(float_or_zero(item.get("tempo")) * 100, 1) if item.get("tempo") is not None else None,
                    "remaining_days": item.get("remaining_days"),
                }
            )
        return rows

    def sun2_product_summary_row(period: str, label: str, summary: Dict[str, Any]) -> Dict[str, Any]:
        amount_inc = float_or_zero(summary.get("amount_inc_vat"))
        amount_ex = float_or_zero(summary.get("amount_ex_vat"))
        count_value = int_or_zero(summary.get("count"))
        quantity = float_or_zero(summary.get("quantity"))
        return {
            "period": period,
            "period_label": label,
            "sales_count": count_value,
            "quantity": round(quantity, 2),
            "amount_inc_vat_kr": round(amount_inc, 2),
            "amount_ex_vat_kr": round(amount_ex, 2),
            "average_sale_inc_vat_kr": round(amount_inc / count_value, 2) if count_value else None,
            "first_date": summary.get("first_date"),
            "last_date": summary.get("last_date"),
            "last_imported_at": summary.get("last_imported_at"),
            "source_scope": summary.get("source_scope"),
            "control_basis": summary.get("control_basis"),
        }

    async def sun2_product_sales_range_summary(session, start: date, end: date) -> Dict[str, Any]:
        rows = []
        cursor = date(start.year, start.month, 1)
        while cursor <= end:
            period_start = cursor
            period_end = min(month_end(cursor), end)
            summary = await sun2_product_sales_period_summary(session, period_start, period_end)
            rows.append(sun2_product_summary_row(period_start.strftime("%Y-%m"), period_start.strftime("%m.%Y"), summary))
            cursor = add_months(cursor, 1)
        amount_inc = sum(float_or_zero(row.get("amount_inc_vat_kr")) for row in rows)
        amount_ex = sum(float_or_zero(row.get("amount_ex_vat_kr")) for row in rows)
        sales_count = sum(int_or_zero(row.get("sales_count")) for row in rows)
        quantity = sum(float_or_zero(row.get("quantity")) for row in rows)
        return {
            "count": sales_count,
            "quantity": round(quantity, 2),
            "amount_inc_vat": round(amount_inc, 2),
            "amount_ex_vat": round(amount_ex, 2),
            "first_date": start,
            "last_date": end,
            "months": rows,
            "source_scope": "month_summary",
        }

    async def sun2_product_sales_month_rows(session, limit: int = 24) -> list[Dict[str, Any]]:
        period_rows = (
            await session.execute(
                select(Sun2ProductSale.stat_date, Sun2ProductSale.period_start, Sun2ProductSale.period_end)
                .order_by(Sun2ProductSale.stat_date.desc(), Sun2ProductSale.period_start.desc().nullslast())
                .limit(6000)
            )
        ).all()
        month_starts: list[date] = []
        seen = set()
        for stat_date, period_start, _period_end in period_rows:
            candidate = period_start or stat_date
            if not candidate:
                continue
            month_start = date(candidate.year, candidate.month, 1)
            key = month_start.isoformat()
            if key in seen:
                continue
            seen.add(key)
            month_starts.append(month_start)
            if len(month_starts) >= limit:
                break
        rows = []
        for month_start_value in month_starts:
            period_end = month_end(month_start_value)
            summary = await sun2_product_sales_period_summary(session, month_start_value, period_end)
            rows.append(sun2_product_summary_row(month_start_value.strftime("%Y-%m"), month_start_value.strftime("%B %Y"), summary))
        return rows

    def api_sun2_product_sale_row(row: Sun2ProductSale) -> Dict[str, Any]:
        api_pick = dependencies.api_pick
        data = api_pick(
            row,
            [
                "sold_at",
                "stat_date",
                "period_start",
                "period_end",
                "product_name",
                "product_category",
                "quantity",
                "unit_price_kr",
                "amount_inc_vat_kr",
                "amount_ex_vat_kr",
                "vat_kr",
                "payment_method",
                "user_name",
                "source_file",
                "imported_at",
            ],
        )
        data["source_scope"] = "maaned" if row.period_start and row.period_end and row.period_start != row.period_end else "dag"
        return data

    async def sun2_product_module_payload(
        session,
        today: date,
        month_start: date,
        params: Any,
    ) -> Dict[str, Any]:
        api_filter = dependencies.api_filter
        api_filter_int = dependencies.api_filter_int
        api_filter_options = dependencies.api_filter_options
        api_filter_value = dependencies.api_filter_value
        import_job_age = dependencies.import_job_age
        parse_day = dependencies.parse_day
        year_start = date(today.year, 1, 1)
        recent_start = today - timedelta(days=119)
        q_value = api_filter_value(params, "q")
        date_from_value = api_filter_value(params, "date_from")
        date_to_value = api_filter_value(params, "date_to")
        category_value = api_filter_value(params, "category")
        payment_method_value = api_filter_value(params, "payment_method")
        scope_value = api_filter_value(params, "scope", "daily") or "daily"
        limit_value = api_filter_int(params, "limit", 250, 25, 1000)

        today_summary = await sun2_product_sales_period_summary(session, today, today)
        month_summary = await sun2_product_sales_period_summary(session, month_start, today)
        year_summary = await sun2_product_sales_range_summary(session, year_start, today)
        month_rows = await sun2_product_sales_month_rows(session)

        product_conditions = []
        if scope_value == "daily":
            product_conditions.append(sun2_product_daily_scope_condition())
        elif scope_value == "monthly":
            product_conditions.append(sun2_product_monthly_scope_condition())
        if q_value:
            like = f"%{q_value.lower()}%"
            product_conditions.append(
                or_(
                    func.lower(func.coalesce(Sun2ProductSale.product_name, "")).like(like),
                    func.lower(func.coalesce(Sun2ProductSale.product_category, "")).like(like),
                    func.lower(func.coalesce(Sun2ProductSale.user_name, "")).like(like),
                    func.lower(func.coalesce(Sun2ProductSale.sun2_user_id, "")).like(like),
                    func.lower(func.coalesce(Sun2ProductSale.payment_method, "")).like(like),
                    func.lower(func.coalesce(Sun2ProductSale.source_file, "")).like(like),
                )
            )
        if date_from_value:
            product_conditions.append(Sun2ProductSale.stat_date >= parse_day(date_from_value))
        if date_to_value:
            product_conditions.append(Sun2ProductSale.stat_date <= parse_day(date_to_value))
        if category_value:
            product_conditions.append(Sun2ProductSale.product_category == category_value)
        if payment_method_value:
            product_conditions.append(Sun2ProductSale.payment_method == payment_method_value)

        product_stmt = select(Sun2ProductSale).order_by(Sun2ProductSale.stat_date.desc(), Sun2ProductSale.sold_at.desc().nullslast()).limit(limit_value)
        product_count_stmt = select(func.count(Sun2ProductSale.id))
        if product_conditions:
            product_stmt = product_stmt.where(*product_conditions)
            product_count_stmt = product_count_stmt.where(*product_conditions)
        product_rows = (await session.execute(product_stmt)).scalars().all()
        filtered_count = (await session.execute(product_count_stmt)).scalar_one()

        amount_inc_expr = sun2_product_amount_inc_expr()
        amount_ex_expr = sun2_product_amount_ex_expr()
        top_product_conditions = list(product_conditions)
        if not date_from_value and not date_to_value:
            top_product_conditions.append(Sun2ProductSale.stat_date >= recent_start)
        product_name_expr = func.coalesce(Sun2ProductSale.product_name, "Ukjent")
        product_category_expr = func.coalesce(Sun2ProductSale.product_category, "")
        top_product_stmt = (
            select(
                product_name_expr.label("product_name"),
                product_category_expr.label("product_category"),
                func.count(Sun2ProductSale.id).label("sales_count"),
                func.coalesce(func.sum(Sun2ProductSale.quantity), 0).label("quantity"),
                func.coalesce(func.sum(amount_inc_expr), 0).label("amount_inc_vat_kr"),
                func.coalesce(func.sum(amount_ex_expr), 0).label("amount_ex_vat_kr"),
                func.max(Sun2ProductSale.stat_date).label("last_date"),
            )
            .group_by(product_name_expr, product_category_expr)
            .order_by(func.coalesce(func.sum(amount_inc_expr), 0).desc())
            .limit(20)
        )
        if top_product_conditions:
            top_product_stmt = top_product_stmt.where(*top_product_conditions)
        top_products = [
            {
                "product_name": item.get("product_name"),
                "product_category": item.get("product_category"),
                "sales_count": int_or_zero(item.get("sales_count")),
                "quantity": round(float_or_zero(item.get("quantity")), 2),
                "amount_inc_vat_kr": round(float_or_zero(item.get("amount_inc_vat_kr")), 2),
                "amount_ex_vat_kr": round(float_or_zero(item.get("amount_ex_vat_kr")), 2),
                "last_date": item.get("last_date"),
            }
            for item in (await session.execute(top_product_stmt)).mappings().all()
        ]

        chart_anchor_day = today
        if date_from_value:
            chart_anchor_day = parse_day(date_from_value)
        elif date_to_value:
            chart_anchor_day = parse_day(date_to_value)
        chart_month_start = date(chart_anchor_day.year, chart_anchor_day.month, 1)
        chart_month_end = month_end(chart_anchor_day)
        daily_chart_rows = (
            await session.execute(
                select(
                    Sun2ProductSale.stat_date.label("stat_date"),
                    func.count(Sun2ProductSale.id).label("sales_count"),
                    func.coalesce(func.sum(Sun2ProductSale.quantity), 0).label("quantity"),
                    func.coalesce(func.sum(amount_inc_expr), 0).label("amount_inc_vat_kr"),
                    func.coalesce(func.sum(amount_ex_expr), 0).label("amount_ex_vat_kr"),
                )
                .where(sun2_product_daily_scope_condition())
                .where(Sun2ProductSale.stat_date >= chart_month_start)
                .where(Sun2ProductSale.stat_date <= chart_month_end)
                .group_by(Sun2ProductSale.stat_date)
                .order_by(Sun2ProductSale.stat_date.asc())
            )
        ).mappings().all()
        daily_by_date = {item.get("stat_date"): item for item in daily_chart_rows if item.get("stat_date")}
        daily_rows = []
        for day in iter_dates(chart_month_start, chart_month_end):
            item = daily_by_date.get(day)
            future_day = day > today
            daily_rows.append(
                {
                    "period": day.isoformat(),
                    "period_label": day.strftime("%d.%m"),
                    "sales_count": None if future_day else int_or_zero(item.get("sales_count") if item else 0),
                    "quantity": None if future_day else round(float_or_zero(item.get("quantity") if item else 0), 2),
                    "amount_inc_vat_kr": None if future_day else round(float_or_zero(item.get("amount_inc_vat_kr") if item else 0), 2),
                    "amount_ex_vat_kr": None if future_day else round(float_or_zero(item.get("amount_ex_vat_kr") if item else 0), 2),
                }
            )

        category_options = api_filter_options(
            (await session.execute(select(Sun2ProductSale.product_category).distinct().order_by(Sun2ProductSale.product_category.asc()))).scalars().all()
        )
        payment_options = api_filter_options(
            (await session.execute(select(Sun2ProductSale.payment_method).distinct().order_by(Sun2ProductSale.payment_method.asc()))).scalars().all()
        )
        daily_status = (
            await session.execute(select(ImportJobStatus).where(ImportJobStatus.job_name == "sun2_product_sales_daily_import").limit(1))
        ).scalars().first()
        monthly_status = (
            await session.execute(select(ImportJobStatus).where(ImportJobStatus.job_name == "sun2_product_sales_monthly_import").limit(1))
        ).scalars().first()

        charts = [
            api_chart(
                "Produktsalg per dag",
                [row["period_label"] for row in daily_rows],
                [
                    {"name": "Omsetning inkl. mva", "data": [row["amount_inc_vat_kr"] for row in daily_rows], "type": "bar", "color": "#f59e0b"},
                    {"name": "Antall", "data": [row["sales_count"] for row in daily_rows], "type": "line", "color": "#64748b"},
                ],
                f"Daglige produktsalg for {chart_month_start.strftime('%m.%Y')}. Månedsimport brukes ikke her for å unngå dobbelttelling.",
                "bar",
                320,
            ),
            api_chart(
                "Produktsalg per måned",
                [row["period_label"] for row in reversed(month_rows[:12])],
                [
                    {"name": "Omsetning inkl. mva", "data": [row["amount_inc_vat_kr"] for row in reversed(month_rows[:12])], "type": "bar", "color": "#d97706"},
                ],
                "Månedsgrunnlag bruker månedsimport der den finnes, ellers daglige linjer.",
                "bar",
                300,
            ),
        ]
        tables = [
            api_table(
                "Produktsalg",
                ["sold_at", "stat_date", "product_name", "product_category", "quantity", "unit_price_kr", "amount_inc_vat_kr", "amount_ex_vat_kr", "payment_method", "user_name", "source_scope", "source_file", "imported_at"],
                [api_sun2_product_sale_row(row) for row in product_rows],
            ),
            api_table(
                "Månedsgrunnlag",
                ["period_label", "sales_count", "quantity", "amount_inc_vat_kr", "amount_ex_vat_kr", "average_sale_inc_vat_kr", "source_scope", "control_basis", "last_imported_at"],
                month_rows,
            ),
            api_table(
                "Topp produkter",
                ["product_name", "product_category", "sales_count", "quantity", "amount_inc_vat_kr", "amount_ex_vat_kr", "last_date"],
                top_products,
            ),
        ]
        return {
            "title": "Soling · Produkter",
            "subtitle": "Produktsalg fra Sun2. Månedsgrunnlag brukes til kontroll, daglige linjer brukes til dagsfordeling.",
            "cards": [
                api_card("I dag", format_short_number(today_summary.get("amount_inc_vat"), 2), "kr", f"{format_short_number(today_summary.get('quantity'), 2)} stk / {today_summary.get('count', 0)} linjer", "sun2", href="/soling/produkter"),
                api_card("Måned", format_short_number(month_summary.get("amount_inc_vat"), 2), "kr", f"{format_short_number(month_summary.get('quantity'), 2)} stk / {month_summary.get('count', 0)} linjer", "revenue", href="/soling/produkter"),
                api_card("I år", format_short_number(year_summary.get("amount_inc_vat"), 2), "kr", f"{format_short_number(year_summary.get('quantity'), 2)} stk", "revenue", href="/soling/produkter"),
                api_card("Treff", filtered_count, "linjer", f"Viser {len(product_rows)} linjer", "status", href="/soling/produkter"),
                api_card("Dagimport", import_job_age(daily_status) if daily_status else "-", "", daily_status.status_text if daily_status else "Ingen status", "status", href="/admin/datakilder"),
                api_card("Månedsimport", import_job_age(monthly_status) if monthly_status else "-", "", monthly_status.status_text if monthly_status else "Ingen status", "status", href="/admin/datakilder"),
            ],
            "charts": charts,
            "tables": tables,
            "filters": [
                api_filter("q", "Søk", "text", q_value, "Produkt, kategori, navn, betaling eller fil"),
                api_filter("date_from", "Fra dato", "date", date_from_value),
                api_filter("date_to", "Til dato", "date", date_to_value),
                api_filter("category", "Kategori", "select", category_value, options=category_options),
                api_filter("payment_method", "Betaling", "select", payment_method_value, options=payment_options),
                api_filter(
                    "scope",
                    "Grunnlag",
                    "select",
                    scope_value,
                    options=[
                        {"label": "Daglige linjer", "value": "daily"},
                        {"label": "Månedsimport", "value": "monthly"},
                        {"label": "Alle linjer", "value": "all"},
                    ],
                ),
                api_filter("limit", "Antall", "number", limit_value),
            ],
        }

    async def sun2_sessions_module_payload(session, params: Optional[Any] = None) -> Dict[str, Any]:
        api_filter = dependencies.api_filter
        api_filter_int = dependencies.api_filter_int
        api_filter_options = dependencies.api_filter_options
        api_filter_value = dependencies.api_filter_value
        parse_day = dependencies.parse_day
        params = params or {}
        q_value = api_filter_value(params, "q")
        date_from_value = api_filter_value(params, "date_from")
        date_to_value = api_filter_value(params, "date_to")
        room_id_value = api_filter_value(params, "room_id")
        payment_method_value = api_filter_value(params, "payment_method")
        status_value = api_filter_value(params, "status")
        customer_type_value = api_filter_value(params, "customer_type")
        limit_value = api_filter_int(params, "limit", 100, 25, 1000)
        page_value = api_filter_int(params, "page", 1, 1, 100000)
        offset_value = (page_value - 1) * limit_value
        session_conditions = []
        if q_value:
            like = f"%{q_value.lower()}%"
            session_conditions.append(
                or_(
                    func.lower(func.coalesce(Sun2TanningSession.user_name, "")).like(like),
                    func.lower(func.coalesce(Sun2TanningSession.sun2_user_id, "")).like(like),
                    func.lower(func.coalesce(Sun2TanningSession.user_identifier, "")).like(like),
                    func.lower(func.coalesce(Sun2TanningSession.room, "")).like(like),
                    func.lower(func.coalesce(Sun2TanningSession.room_id, "")).like(like),
                    func.lower(func.coalesce(Sun2TanningSession.source_file, "")).like(like),
                )
            )
        if date_from_value:
            session_conditions.append(Sun2TanningSession.stat_date >= parse_day(date_from_value))
        if date_to_value:
            session_conditions.append(Sun2TanningSession.stat_date <= parse_day(date_to_value))
        if room_id_value:
            session_conditions.append(Sun2TanningSession.room_id == room_id_value)
        if payment_method_value:
            session_conditions.append(Sun2TanningSession.payment_method == payment_method_value)
        if status_value:
            session_conditions.append(Sun2TanningSession.status == status_value)
        if customer_type_value:
            session_conditions.append(Sun2TanningSession.customer_type == customer_type_value)

        session_stmt = select(Sun2TanningSession).order_by(Sun2TanningSession.started_at.desc()).offset(offset_value).limit(limit_value)
        session_count_stmt = select(func.count(Sun2TanningSession.id))
        if session_conditions:
            session_stmt = session_stmt.where(*session_conditions)
            session_count_stmt = session_count_stmt.where(*session_conditions)
        filtered_sessions = (await session.execute(session_stmt)).scalars().all()
        filtered_count = (await session.execute(session_count_stmt)).scalar_one()

        filtered_session_ids = [row.id for row in filtered_sessions if row.id]
        filtered_image_lookup: Dict[int, Sun2TanningSessionImage] = {}
        filtered_image_counts: Dict[int, int] = {}
        images_by_session: Dict[int, list[Sun2TanningSessionImage]] = {}
        if filtered_session_ids:
            filtered_image_rows = (
                await session.execute(
                    select(Sun2TanningSessionImage)
                    .options(sun2_session_image_meta_options())
                    .where(Sun2TanningSessionImage.session_id.in_(filtered_session_ids))
                    .order_by(
                        Sun2TanningSessionImage.session_id.asc(),
                        Sun2TanningSessionImage.is_primary.desc(),
                        Sun2TanningSessionImage.offset_seconds.desc(),
                        Sun2TanningSessionImage.created_at.desc(),
                    )
                )
            ).scalars().all()
            images_by_session = defaultdict(list)
            for image in filtered_image_rows:
                images_by_session[image.session_id].append(image)
            filtered_image_lookup = {
                session_id: primary_sun2_session_image(images)
                for session_id, images in images_by_session.items()
            }
            filtered_image_counts = {session_id: len(images) for session_id, images in images_by_session.items()}

        room_option_rows = (
            await session.execute(
                select(Sun2TanningSession.room_id, func.max(Sun2TanningSession.room))
                .where(Sun2TanningSession.room_id.is_not(None))
                .group_by(Sun2TanningSession.room_id)
                .order_by(Sun2TanningSession.room_id.asc())
            )
        ).all()
        payment_options = api_filter_options(
            (await session.execute(select(Sun2TanningSession.payment_method).distinct().order_by(Sun2TanningSession.payment_method.asc()))).scalars().all()
        )
        status_options = api_filter_options(
            (await session.execute(select(Sun2TanningSession.status).distinct().order_by(Sun2TanningSession.status.asc()))).scalars().all()
        )
        customer_options = api_filter_options(
            (await session.execute(select(Sun2TanningSession.customer_type).distinct().order_by(Sun2TanningSession.customer_type.asc()))).scalars().all()
        )
        room_options = [
            {"label": sun2_room_label(room_id, room_name), "value": room_id}
            for room_id, room_name in room_option_rows
            if room_id
        ]

        return {
            "title": "Soling · enkeltimer",
            "subtitle": "Enkeltimer fra Sun2 med lagrede Axis-bilder og bildearkiv.",
            "cards": [
                api_card("Treff", filtered_count, "stk", f"Viser {offset_value + 1 if filtered_sessions else 0}-{min(offset_value + len(filtered_sessions), filtered_count)}", "sun2", href="/soling/enkeltimer"),
                api_card(
                    "Med bilde",
                    sum(1 for row in filtered_sessions if filtered_image_counts.get(row.id, 0)),
                    "stk",
                    "I viste rader",
                    "status",
                    href="/soling/enkeltimer",
                ),
            ],
            "charts": [],
            "tables": [
                api_table(
                    "Enkeltimer",
                    ["started_at", "ended_at", "room_label", "duration_minutes", "paid_amount_kr", "user_name", "payment_method", "customer_type", "status"],
                    [
                        api_sun2_session_row(
                            row,
                            filtered_image_lookup.get(row.id),
                            filtered_image_counts.get(row.id, 0),
                            images_by_session.get(row.id, []),
                        )
                        for row in filtered_sessions
                    ],
                    meta=api_table_meta(filtered_count, page_value, limit_value, len(filtered_sessions)),
                ),
            ],
            "filters": [
                api_filter("q", "Søk", "text", q_value, "Navn, SUN2-id, rom, fil"),
                api_filter("date_from", "Fra dato", "date", date_from_value),
                api_filter("date_to", "Til dato", "date", date_to_value),
                api_filter("room_id", "Rom", "select", room_id_value, options=room_options),
                api_filter("payment_method", "Betaling", "select", payment_method_value, options=payment_options),
                api_filter("status", "Status", "select", status_value, options=status_options),
                api_filter("customer_type", "Kundetype", "select", customer_type_value, options=customer_options),
                api_filter("page", "Side", "number", page_value),
                api_filter("limit", "Antall", "number", limit_value),
            ],
        }

    async def get_sun2_session_options(session) -> Dict[str, list[str]]:
        SUMMARY_CACHE = dependencies.SUMMARY_CACHE
        cache_key = "sun2_session_options"
        now_value = datetime.utcnow()
        cached = SUMMARY_CACHE.get(cache_key)
        if cached and cached.get("expires", datetime.min) > now_value:
            return cached["value"]

        def distinct_text(column):
            return (
                select(column)
                .where(column.is_not(None))
                .where(column != "")
                .distinct()
                .order_by(column)
            )

        bed_rows = (
            await session.execute(
                select(Sun2Bed)
                .where(Sun2Bed.room_id.is_not(None))
                .order_by(Sun2Bed.physical_room_number, Sun2Bed.room_id)
            )
        ).scalars().all()
        room_ids = [
            {
                "value": bed.room_id,
                "label": sun2_room_label(bed.room_id, bed.name),
            }
            for bed in bed_rows
            if bed.room_id
        ] or list(SUN2_ROOM_OPTIONS)
        seen_room_ids = set()
        deduped_room_ids = []
        for item in room_ids:
            if item["value"] in seen_room_ids:
                continue
            seen_room_ids.add(item["value"])
            deduped_room_ids.append(item)

        value = {
            "room_ids": deduped_room_ids,
            "rooms": (await session.execute(distinct_text(Sun2TanningSession.room))).scalars().all(),
            "payments": (await session.execute(distinct_text(Sun2TanningSession.payment_method))).scalars().all(),
            "statuses": (await session.execute(distinct_text(Sun2TanningSession.status))).scalars().all(),
            "customers": (await session.execute(distinct_text(Sun2TanningSession.customer_type))).scalars().all(),
        }
        SUMMARY_CACHE[cache_key] = {"expires": now_value + timedelta(minutes=30), "value": value}
        return value

    async def get_sun2_session_database_total(session) -> Dict[str, Any]:
        SUMMARY_CACHE = dependencies.SUMMARY_CACHE
        cache_key = "sun2_session_database_total"
        now_value = datetime.utcnow()
        cached = SUMMARY_CACHE.get(cache_key)
        if cached and cached.get("expires", datetime.min) > now_value:
            return cached["value"]
        value = (
            await session.execute(
                select(
                    func.count(Sun2TanningSession.id).label("sessions_count"),
                    func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                    func.count(func.distinct(Sun2TanningSession.sun2_user_id)).label("unique_users_count"),
                )
            )
        ).mappings().first() or {}
        value = dict(value)
        SUMMARY_CACHE[cache_key] = {"expires": now_value + timedelta(minutes=5), "value": value}
        return value

    return {
        "api_sun2_bed_row": api_sun2_bed_row,
        "api_sun2_day_timeline": api_sun2_day_timeline,
        "api_sun2_forecast_rows": api_sun2_forecast_rows,
        "api_sun2_member_row": api_sun2_member_row,
        "api_sun2_overview_tables": api_sun2_overview_tables,
        "api_sun2_product_sale_row": api_sun2_product_sale_row,
        "api_sun2_session_row": api_sun2_session_row,
        "api_sun2_summary_row": api_sun2_summary_row,
        "api_sun2_weekly_chart": api_sun2_weekly_chart,
        "axis_snapshot_archive_days": axis_snapshot_archive_days,
        "axis_snapshot_browser_payload": axis_snapshot_browser_payload,
        "axis_snapshot_candidates": axis_snapshot_candidates,
        "axis_snapshot_day_candidates": axis_snapshot_day_candidates,
        "axis_snapshot_id": axis_snapshot_id,
        "axis_snapshot_path_for_id": axis_snapshot_path_for_id,
        "axis_snapshot_series_around": axis_snapshot_series_around,
        "backfill_sun2_room_identity": backfill_sun2_room_identity,
        "build_sun2_forecast": build_sun2_forecast,
        "closest_axis_snapshot_index": closest_axis_snapshot_index,
        "fetch_sun2_scraper_runtime": fetch_sun2_scraper_runtime,
        "force_sun2_sync_for_closed_rooms": force_sun2_sync_for_closed_rooms,
        "get_sun2_axis_snapshot_link_lock": get_sun2_axis_snapshot_link_lock,
        "get_sun2_session_database_total": get_sun2_session_database_total,
        "get_sun2_session_options": get_sun2_session_options,
        "ingest_sun2_beds": ingest_sun2_beds,
        "ingest_sun2_finance_settlements": ingest_sun2_finance_settlements,
        "ingest_sun2_members": ingest_sun2_members,
        "ingest_sun2_product_sales": ingest_sun2_product_sales,
        "ingest_sun2_room_stats": ingest_sun2_room_stats,
        "ingest_sun2_tanning_sessions": ingest_sun2_tanning_sessions,
        "link_axis_snapshots_to_sun2_sessions": link_axis_snapshots_to_sun2_sessions,
        "nearest_axis_snapshot": nearest_axis_snapshot,
        "parse_axis_snapshot_id": parse_axis_snapshot_id,
        "parse_axis_snapshot_time": parse_axis_snapshot_time,
        "primary_sun2_session_image": primary_sun2_session_image,
        "replace_sun2_session_image_with_axis_snapshot": replace_sun2_session_image_with_axis_snapshot,
        "request_sun2_today_sync": request_sun2_today_sync,
        "run_sun2_axis_snapshot_link_once": run_sun2_axis_snapshot_link_once,
        "schedule_sun2_axis_snapshot_link": schedule_sun2_axis_snapshot_link,
        "set_sun2_session_primary_image": set_sun2_session_primary_image,
        "sun2_axis_snapshot_link_worker": sun2_axis_snapshot_link_worker,
        "sun2_duplicate_session_id_payload": sun2_duplicate_session_id_payload,
        "sun2_product_module_payload": sun2_product_module_payload,
        "sun2_product_sales_month_rows": sun2_product_sales_month_rows,
        "sun2_product_sales_range_summary": sun2_product_sales_range_summary,
        "sun2_product_summary_row": sun2_product_summary_row,
        "sun2_session_axis_start_at": sun2_session_axis_start_at,
        "sun2_session_axis_target_at": sun2_session_axis_target_at,
        "sun2_session_axis_target_series": sun2_session_axis_target_series,
        "sun2_session_image_meta_options": sun2_session_image_meta_options,
        "sun2_session_image_payload": sun2_session_image_payload,
        "sun2_sessions_active_minutes_since": sun2_sessions_active_minutes_since,
        "sun2_sessions_module_payload": sun2_sessions_module_payload,
    }
