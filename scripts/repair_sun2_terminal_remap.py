"""Audited, idempotent SUN2 correction. Default is a fully checked rollback.

Run with the core image, its database environment, and a read-only archive mount.
Never delete session/image rows. See docs/sun2-terminal-remap-audit-20260920.md.
"""

import argparse
import asyncio
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text
import main
from sun2_room_mapping import (
    CUTOVER_DATE, MAPPING_VERSION, canonical_room_name, current_bed_identity,
    mapping_provenance, session_identity,
)


def comparison_key(row, identity):
    def get(key):
        return row.get(key) if isinstance(row, dict) else getattr(row, key)
    stamp = get("started_at")
    if isinstance(stamp, str):
        stamp = datetime.fromisoformat(stamp)
    return (stamp, identity.get("room_id"), str(get("sun2_user_id") or get("user_identifier") or get("user_name") or ""),
            Decimal(str(get("duration_minutes") or 0)), Decimal(str(get("paid_amount_kr") or 0)))


def observed(row):
    return (row.raw or {}).get("room_mapping", {}).get("label_observed_at") or row.imported_at


async def image_fingerprint(session):
    return dict((await session.execute(text("""
        SELECT count(*) AS count,
               md5(coalesce(string_agg(concat_ws(':',id,session_id,captured_at,target_at,
                   offset_seconds,is_primary,sha256,byte_size), '|' ORDER BY id),'')) AS fingerprint
        FROM sun2_tanning_session_images
    """))).mappings().one())


async def repair(archive_dir, apply=False):
    original = []
    fingerprints = {}
    for day in range(1, 11):
        path = archive_dir / f"Sun2_sessions_2026-09-{day:02d}.json"
        content = path.read_bytes()
        payload = json.loads(content)
        assert payload["ok"] and payload["timestamp"][:10] == f"2026-09-{day:02d}", "Not an original daily archive"
        fingerprints[path.name] = hashlib.sha256(content).hexdigest()
        original.extend((row, payload["timestamp"]) for row in payload["rows"])
    assert len(original) == 262, "Daily evidence changed; stop and review"
    assert sum(Decimal(str(r["paid_amount_kr"])) for r, _ in original) == Decimal("50365.16")
    expected = Counter(comparison_key(row, session_identity(row["room"], row["started_at"], stamp)) for row, stamp in original)
    assert all(count == 1 for count in expected.values()), "Ambiguous original sessions"

    report = {"mode": "apply" if apply else "rollback", "mapping_version": MAPPING_VERSION, "archives": fingerprints}
    async with main.async_session() as session:
        async with session.begin():
            await session.execute(text("SET LOCAL lock_timeout = '15s'"))
            await session.execute(text("SELECT pg_advisory_xact_lock(hashtext('sun2_session_ingest'))"))
            await session.execute(text("LOCK TABLE sun2_tanning_sessions, sun2_tanning_session_images, sun2_room_daily_stats, sun2_beds IN SHARE ROW EXCLUSIVE MODE"))
            before_images = await image_fingerprint(session)
            before_count = (await session.execute(text("SELECT count(*) FROM sun2_tanning_sessions"))).scalar_one()
            old = (await session.execute(select(main.Sun2TanningSession).where(
                main.Sun2TanningSession.stat_date >= date(2026,9,1),
                main.Sun2TanningSession.stat_date < CUTOVER_DATE,
            ))).scalars().all()
            indexed = defaultdict(list)
            for row in old:
                identity = session_identity(row.source_room_name or row.room, row.started_at, observed(row))
                indexed[comparison_key(row, identity)].append(row)
            assert not (Counter({k:len(v) for k,v in indexed.items()}) - expected), "Unexpected existing records; do not guess"
            updated = 0
            inserted = []
            for source, stamp in original:
                identity = session_identity(source["room"], source["started_at"], stamp)
                matches = indexed[comparison_key(source, identity)]
                assert len(matches) <= 1, "Ambiguous destination records"
                if not matches:
                    assert source["started_at"] in {"2026-09-01T13:35:00", "2026-09-02T22:57:00"}, "Unexpected missing session"
                    assert identity["display_room_number"] == 11
                    payload = main.Sun2TanningSessionsIngestIn(
                        timestamp=stamp, source_file=f"Sun2_sessions_{source['stat_date']}.json", rows=[source],
                    )
                    result = await main.ingest_sun2_tanning_sessions(session, payload, datetime.utcnow())
                    assert result["inserted"] == 1
                    inserted.append({"started_at":source["started_at"], "room":11, "amount":source["paid_amount_kr"]})
                    continue
                row = matches[0]
                if identity.get("display_room_number") not in (10,11,12):
                    continue
                desired = {"room_id": identity["room_id"], "sun2_bed_id": identity["sun2_bed_id"],
                           "room": source["room"], "source_room_name": source["room"],
                           "room_key": f"rom_{identity['display_room_number']:02d}"}
                if any(getattr(row,key) != value for key,value in desired.items()):
                    for key, value in desired.items():
                        setattr(row,key,value)
                    row.raw = {**(row.raw or {}), **(source.get("raw") or {}),
                               "room_mapping": mapping_provenance(identity, stamp, source["source_session_id"]),
                               "remap_repair": "original-daily-archive-20260920"}
                    updated += 1
            await session.flush()
            corrected = (await session.execute(select(main.Sun2TanningSession).where(
                main.Sun2TanningSession.stat_date >= date(2026,9,1), main.Sun2TanningSession.stat_date < CUTOVER_DATE,
            ))).scalars().all()
            actual = Counter(comparison_key(r, {"room_id":r.room_id}) for r in corrected)
            assert actual == expected, "Historical multiset validation failed"
            assert len(corrected) == 262

            current_updates = 0
            current = (await session.execute(select(main.Sun2TanningSession).where(
                main.Sun2TanningSession.stat_date >= CUTOVER_DATE,
            ))).scalars().all()
            for row in current:
                identity = session_identity(row.source_room_name or row.room, row.started_at, observed(row))
                if identity.get("display_room_number") not in (10,11,12):
                    continue
                if row.room_id != identity["room_id"] or row.sun2_bed_id != identity["sun2_bed_id"]:
                    row.room_id = identity["room_id"]
                    row.sun2_bed_id = identity["sun2_bed_id"]
                    row.raw = {**(row.raw or {}), "room_mapping": mapping_provenance(identity, observed(row), row.source_session_id)}
                    current_updates += 1

            stats_updates = 0
            stats = (await session.execute(select(main.Sun2RoomDailyStat).where(
                main.Sun2RoomDailyStat.stat_date >= CUTOVER_DATE,
            ))).scalars().all()
            for row in stats:
                identity = session_identity(row.source_room_name or row.room, row.stat_date)
                if identity.get("display_room_number") in (10,11,12) and row.sun2_bed_id != identity["sun2_bed_id"]:
                    row.room_id = identity["room_id"]
                    row.sun2_bed_id = identity["sun2_bed_id"]
                    stats_updates += 1

            beds = (await session.execute(select(main.Sun2Bed))).scalars().all()
            beds_updates = 0
            for bed in beds:
                identity = current_bed_identity(bed.name, bed.sun2_bed_id)
                if any(getattr(bed,key) != identity[key] for key in ("room_id","physical_room_number","display_room_number")):
                    for key in ("room_id","physical_room_number","display_room_number"):
                        setattr(bed,key,identity[key])
                    beds_updates += 1
            await session.flush()
            assert await image_fingerprint(session) == before_images, "Image associations changed"
            after_count = (await session.execute(text("SELECT count(*) FROM sun2_tanning_sessions"))).scalar_one()
            assert after_count == before_count + len(inserted)
            report.update(historical_updated=updated, restored=inserted, current_updated=current_updates,
                          daily_stats_updated=stats_updates, beds_updated=beds_updates, historical_sessions=len(corrected),
                          historical_amount="50365.16", images=before_images, session_count_before=before_count,
                          session_count_after=after_count)
            if not apply:
                await session.rollback()
    await main.engine.dispose()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = asyncio.run(repair(args.archive_dir, args.apply))
    output = json.dumps(result, indent=2, default=str)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    print(output)
