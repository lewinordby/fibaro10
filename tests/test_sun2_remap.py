from datetime import datetime
import unittest

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from sun2_room_mapping import (
    CURRENT_BEDS, LEGACY_BEDS, canonical_session_room_id, current_bed_identity,
    room_identity_for_display, session_identity,
)


class RoomMappingTests(unittest.TestCase):
    def test_all_rooms_before_and_after_cutover(self):
        for number in range(1, 13):
            for day, beds in [("2026-09-10", LEGACY_BEDS), ("2026-09-11", CURRENT_BEDS)]:
                with self.subTest(number=number, day=day):
                    identity = session_identity(f"Rom {number}", day, day)
                    self.assertEqual(identity["display_room_number"], number)
                    self.assertEqual(identity["sun2_bed_id"], beds[number])
                    self.assertEqual(identity["room_id"], room_identity_for_display(number)["room_id"])

    def test_relabelled_historical_transactions(self):
        for old, current in [(10, "Rom 11 MegaSun+"), (11, "Rom 12 Super VIP"), (12, "...")]:
            identity = session_identity(current, "2026-09-01", "2026-09-20")
            self.assertEqual(identity, room_identity_for_display(old, "2026-09-01"))

    def test_unnamed_does_not_mean_active_room_after_cutover(self):
        for name in ("...", ".", "", "unknown"):
            self.assertIsNone(session_identity(name, "2026-09-12", "2026-09-12")["room_id"])
        self.assertEqual(session_identity(".", "2026-09-10", "2026-09-10")["room_id"], "rom-10")

    def test_current_inactive_terminal_has_no_room(self):
        self.assertIsNone(current_bed_identity("...", "681")["room_id"])
        self.assertEqual(current_bed_identity("Rom 12", "680")["room_id"], "rom-13")

    def test_old_and_new_bed_id_map_to_same_room(self):
        self.assertEqual(canonical_session_room_id(None, "681", "2026-09-10"), "rom-13")
        self.assertEqual(canonical_session_room_id(None, "680", "2026-09-11"), "rom-13")
        self.assertEqual(canonical_session_room_id(None, "680", "2026-09-10"), "rom-12")

    def test_label_observation_uses_oslo_date_for_utc_export_stamp(self):
        identity = session_identity("Rom 12", "2026-09-10", "2026-09-10T22:05:00Z")
        self.assertEqual(identity["display_room_number"], 11)

    def test_mobile_and_core_share_current_mapping(self):
        from online_dashboard.app.main import SOLROOM_DOOR_CONFIG, solroom_session_room_id
        for config in SOLROOM_DOOR_CONFIG:
            self.assertEqual(config["sun2_bed_id"], CURRENT_BEDS[config["sort_order"]])
        self.assertEqual(solroom_session_room_id({"sun2_bed_id": "681", "started_at": "2026-09-10"}), "rom-13")
        self.assertEqual(solroom_session_room_id({"sun2_bed_id": "680", "started_at": "2026-09-11"}), "rom-13")


class SessionIngestTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import main
        self.main = main
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        @event.listens_for(self.engine.sync_engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            for model in (main.Sun2TanningSession, main.Sun2TanningSessionImage, main.Sun2Bed, main.Sun2RoomDailyStat):
                await conn.run_sync(model.__table__.create)

    async def asyncTearDown(self):
        await self.engine.dispose()

    def payload(self, names, *, observed="2026-09-20T05:00:00", source_file="month.json", amount=275):
        from fibaro_core.schemas.sun import Sun2TanningSessionsIngestIn
        return Sun2TanningSessionsIngestIn(
            timestamp=observed, source_file=source_file,
            rows=[dict(source_session_id=f"stable:input-{name}", started_at="2026-09-01T13:35:00",
                       room=name, source_room_name=name, sun2_user_id="test-member",
                       duration_minutes=25, paid_amount_kr=amount) for name in names],
        )

    async def ingest(self, db, payload):
        result = await self.main.ingest_sun2_tanning_sessions(db, payload, datetime(2026, 9, 20, 6))
        await db.commit()
        return result

    async def rows(self, db):
        return (await db.execute(select(self.main.Sun2TanningSession).order_by(self.main.Sun2TanningSession.id))).scalars().all()

    async def test_simultaneous_payments_survive_monthly_and_daily_reimports_with_images(self):
        async with self.factory() as db:
            result = await self.ingest(db, self.payload(["Rom 12 Super VIP", "..."]))
            self.assertEqual(result["inserted"], 2)
            before = await self.rows(db)
            self.assertEqual({r.room_id for r in before}, {"rom-12", "rom-13"})
            ids = [(r.id, r.source_session_id) for r in before]
            db.add(self.main.Sun2TanningSessionImage(session_id=before[0].id, captured_at=datetime(2026,9,1,13,34),
                   target_at=datetime(2026,9,1,13,34), offset_seconds=-15, image_bytes=b"original-image", sha256="test"))
            await db.commit()
            for payload in [self.payload(["...", "Rom 12 Super VIP"]),
                            self.payload(["Rom 11 megaSun +", "Rom 12 Super VIP"], observed="2026-09-01T21:30:00", source_file="daily.json"),
                            self.payload(["Rom 12 Super VIP", "..."])]:
                result = await self.ingest(db, payload)
                self.assertEqual(result["inserted"], 0)
                rows = await self.rows(db)
                self.assertEqual([(r.id, r.source_session_id) for r in rows], ids)
                self.assertEqual(sum(r.paid_amount_kr for r in rows), 550)
                images = (await db.execute(select(self.main.Sun2TanningSessionImage))).scalars().all()
                self.assertEqual(len(images), 1)
                self.assertEqual(images[0].image_bytes, b"original-image")

    async def test_unknown_room_does_not_overwrite_known_room(self):
        async with self.factory() as db:
            await self.ingest(db, self.payload(["Rom 5", "unidentified"]))
            rows = await self.rows(db)
            self.assertEqual(len(rows), 2)
            self.assertEqual({r.room_id for r in rows}, {"rom-05", None})
            await self.ingest(db, self.payload(["unidentified", "Rom 5"]))
            self.assertEqual(len(await self.rows(db)), 2)

    async def test_existing_legacy_source_ids_and_primary_keys_are_preserved(self):
        async with self.factory() as db:
            row = self.main.Sun2TanningSession(source="sun2_session_scraper", source_session_id="stable:old-id",
                  started_at=datetime(2026,9,1,13,35), stat_date=datetime(2026,9,1).date(),
                  room_id="rom-12", room="Rom 11 megaSun +", sun2_bed_id="680", sun2_user_id="test-member",
                  duration_minutes=25, paid_amount_kr=275, source_file="month.json")
            db.add(row)
            await db.commit()
            old_id = row.id
            await self.ingest(db, self.payload(["Rom 12 Super VIP", "..."]))
            self.assertEqual((await db.get(self.main.Sun2TanningSession, old_id)).source_session_id, "stable:old-id")
            self.assertEqual(len(await self.rows(db)), 2)

    async def test_source_id_cannot_reassign_a_known_room(self):
        async with self.factory() as db:
            payload = self.payload(["Rom 5"])
            payload.rows[0].source_session_id = "sun2:real-transaction"
            await self.ingest(db, payload)
            payload.rows[0].room = payload.rows[0].source_room_name = "Rom 6"
            with self.assertRaisesRegex(ValueError, "different room"):
                await self.main.ingest_sun2_tanning_sessions(db, payload, datetime(2026,9,20))

    async def test_current_beds_ignore_stale_producer_room_numbers(self):
        from fibaro_core.schemas.sun import Sun2BedsIngestIn
        payload = Sun2BedsIngestIn(beds=[
            dict(name=f"Rom {number}", sun2_bed_id=bed, room_id=f"rom-{number+1}",
                 physical_room_number=number+1, display_room_number=number, status="Av" if number==10 else "Paa")
            for number,bed in [(10,"649"),(11,"679"),(12,"680")]
        ] + [dict(name="...", sun2_bed_id="681", room_id="rom-13", physical_room_number=13)])
        async with self.factory() as db:
            await self.main.ingest_sun2_beds(db, payload, datetime(2026,9,20))
            await db.commit()
            beds = (await db.execute(select(self.main.Sun2Bed))).scalars().all()
            self.assertEqual([(b.sun2_bed_id,b.physical_room_number,b.room_id) for b in beds],
                             [("649",10,"rom-11"),("679",11,"rom-12"),("680",12,"rom-13"),("681",None,None)])
            self.assertEqual(beds[0].status, "Av")

    async def test_daily_csv_identity_uses_report_day_not_import_day(self):
        from fibaro_core.schemas.sun import Sun2RoomStatsIngestIn
        async with self.factory() as db:
            for day, bed in [("2026-09-10","681"),("2026-09-11","680")]:
                payload = Sun2RoomStatsIngestIn(stat_date=day, rows=[dict(
                    stat_date=day, room="Rom 12", sun2_bed_id="681", room_id="rom-13", totalt_inntjent_kr=220)])
                await self.main.ingest_sun2_room_stats(db, payload, datetime(2026,9,20))
                await db.commit()
                row = (await db.execute(select(self.main.Sun2RoomDailyStat).where(
                    self.main.Sun2RoomDailyStat.stat_date==datetime.fromisoformat(day).date()))).scalar_one()
                self.assertEqual(row.sun2_bed_id,bed)
                self.assertEqual(row.room_id,"rom-13")
            await self.main.ingest_sun2_room_stats(db, payload, datetime(2026,9,20))
            await db.commit()
            self.assertEqual(len((await db.execute(select(self.main.Sun2RoomDailyStat))).scalars().all()),2)

    async def test_missing_identity_backfill_respects_both_epochs(self):
        async with self.factory() as db:
            for index, (name, day, imported) in enumerate([
                ("...","2026-09-10","2026-09-20"),
                ("Rom 12","2026-09-10","2026-09-10"),
                ("Rom 12","2026-09-11","2026-09-20"),
            ]):
                db.add(self.main.Sun2TanningSession(source_session_id=str(index),room=name,source_room_name=name,
                    started_at=datetime.fromisoformat(day),stat_date=datetime.fromisoformat(day).date(),
                    imported_at=datetime.fromisoformat(imported)))
            await db.commit()
            result=await self.main.backfill_sun2_room_identity(db)
            await db.commit()
            self.assertEqual(result["sessions"],3)
            self.assertEqual([(r.room_id,r.sun2_bed_id) for r in await self.rows(db)],
                             [("rom-13","681"),("rom-13","681"),("rom-13","680")])
