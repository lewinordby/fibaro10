import argparse
import asyncio
import json
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from sqlalchemy import or_, select


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconstruct stored solroom alarms from door and Sun2 history.")
    parser.add_argument("--since", default="2026-07-13", help="First local date to inspect (YYYY-MM-DD).")
    parser.add_argument("--dry-run", action="store_true", help="Calculate without storing alarm rows.")
    return parser.parse_args()


async def run(since_day: date, dry_run: bool) -> dict:
    import main

    now = main.local_now_naive()
    since_at = datetime.combine(since_day, time.min)
    configs = [config for config in main.DOOR_SENSOR_CONFIG if config.get("group_key") == "solrom"]
    device_ids = [int(config["device_id"]) for config in configs if config.get("device_id") is not None]
    room_ids = [room_id for room_id in (main.sunroom_room_id_for_config(config) for config in configs) if room_id]
    bed_ids = [bed_id for bed_id in (main.sunroom_bed_id_for_config(config) for config in configs) if bed_id]

    async with main.async_session() as session:
        door_rows = (
            await session.execute(
                select(main.DoorEvent)
                .where(main.DoorEvent.device_id.in_(device_ids))
                .where(main.DoorEvent.timestamp >= since_at - timedelta(days=1))
                .order_by(main.DoorEvent.timestamp.asc(), main.DoorEvent.id.asc())
            )
        ).scalars().all()
        session_rows = (
            await session.execute(
                select(main.Sun2TanningSession)
                .where(
                    or_(
                        main.Sun2TanningSession.room_id.in_(room_ids),
                        main.Sun2TanningSession.sun2_bed_id.in_(bed_ids),
                    )
                )
                .where(main.Sun2TanningSession.started_at >= since_at - timedelta(hours=2))
                .order_by(main.Sun2TanningSession.started_at.desc(), main.Sun2TanningSession.id.desc())
            )
        ).scalars().all()

        sessions_by_room: dict[str, list] = {room_id: [] for room_id in room_ids}
        for row in session_rows:
            room_id = main.sunroom_canonical_room_id(row)
            if room_id:
                sessions_by_room.setdefault(room_id, []).append(row)

        periods_by_device: dict[str, list[dict]] = {}
        for period in main.door_closed_periods(main.door_change_rows(door_rows), now):
            periods_by_device.setdefault(main.door_period_device_key(period), []).append(period)

        created = 0
        existing = 0
        reconstructed: list[dict] = []
        for config in configs:
            room_id = main.sunroom_room_id_for_config(config)
            room_sessions = sessions_by_room.get(room_id or "", [])
            for period in periods_by_device.get(main.door_config_device_key(config), []):
                closed_at = period.get("closedAt")
                opened_at = period.get("openedAt")
                if not closed_at or (opened_at or now) < since_at:
                    continue
                matched = main.sunroom_match_session_for_period(room_sessions, closed_at, opened_at, now)
                compare_at = opened_at or now
                alarm_reason = None
                detected_at = None
                expected_exit_at = main.sunroom_expected_exit_at(matched) if matched else None
                if not matched and compare_at >= closed_at + timedelta(minutes=main.SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES):
                    alarm_reason = "closed_without_session"
                    detected_at = closed_at + timedelta(minutes=main.SUNROOM_DOOR_NO_SESSION_ALARM_MINUTES)
                elif matched:
                    session_end = main.sunroom_session_end_at(matched)
                    if session_end and compare_at >= session_end + timedelta(minutes=main.SUNROOM_DOOR_ALERT_AFTER_END_MINUTES):
                        alarm_reason = "overstay"
                        detected_at = session_end + timedelta(minutes=main.SUNROOM_DOOR_ALERT_AFTER_END_MINUTES)
                if not alarm_reason or not detected_at or detected_at < since_at:
                    continue

                session_payload = main.sunroom_session_payload(matched) if matched else None
                item = {
                    "deviceId": config.get("device_id"),
                    "deviceKey": config.get("device_key"),
                    "title": config.get("title"),
                    "displayRoomNumber": main.sunroom_display_number(config),
                    "physicalRoomNumber": main.sunroom_identity_for_config(config).get("physical_room_number"),
                    "sun2BedId": main.sunroom_bed_id_for_config(config),
                    "roomId": room_id,
                    "roomLabel": config.get("title"),
                    "doorChangedAt": closed_at.isoformat(),
                    "expectedExitAt": expected_exit_at.isoformat() if expected_exit_at else None,
                    "expectedExitLabel": main.format_source_datetime(expected_exit_at) if expected_exit_at else "-",
                    "occupiedSinceLabel": main.format_source_datetime(closed_at),
                    "occupiedDurationLabel": main.door_duration_label(int((compare_at - closed_at).total_seconds())),
                    "overstayLabel": main.door_duration_label(int((compare_at - expected_exit_at).total_seconds()))
                    if expected_exit_at and compare_at > expected_exit_at
                    else "",
                    "severity": "alert",
                    "isOccupied": opened_at is None,
                    "alarmReason": alarm_reason,
                    "noSessionAlarmActive": alarm_reason == "closed_without_session",
                    "session": session_payload,
                }
                event_key = main.sunroom_alarm_event_key(item)
                alarm = (
                    await session.execute(select(main.AlarmEvent).where(main.AlarmEvent.event_key == event_key))
                ).scalars().first()
                if alarm is None:
                    alarm = main.AlarmEvent(
                        event_key=event_key,
                        domain="doors",
                        alarm_type=alarm_reason,
                        severity="alert",
                        outcome="unreviewed",
                        title=str(config.get("title") or "Solromalarm"),
                        notification_status="unknown",
                        notification_count=0,
                        source="reconstructed",
                        created_at=now,
                    )
                    session.add(alarm)
                    created += 1
                else:
                    existing += 1
                alarm.status = "active" if opened_at is None else "resolved"
                alarm.detail = main.sunroom_alarm_message(item, detected_at)
                alarm.device_key = config.get("device_key")
                alarm.device_id = config.get("device_id")
                alarm.room_id = room_id
                alarm.display_room_number = main.sunroom_display_number(config)
                alarm.physical_room_number = main.sunroom_identity_for_config(config).get("physical_room_number")
                alarm.sun2_bed_id = main.sunroom_bed_id_for_config(config)
                alarm.source_session_id = session_payload.get("sourceSessionId") if session_payload else None
                alarm.door_changed_at = closed_at
                alarm.expected_exit_at = expected_exit_at
                alarm.detected_at = detected_at
                alarm.last_observed_at = opened_at or now
                alarm.resolved_at = opened_at
                alarm.resolution_reason = "door_opened" if opened_at else None
                alarm.updated_at = now
                alarm.raw = {**item, "openedAt": opened_at.isoformat() if opened_at else None}
                reconstructed.append(
                    {
                        "room": alarm.title,
                        "type": alarm_reason,
                        "detectedAt": detected_at.isoformat(),
                        "resolvedAt": opened_at.isoformat() if opened_at else None,
                    }
                )

        if dry_run:
            await session.rollback()
        else:
            await session.commit()
        return {
            "ok": True,
            "dryRun": dry_run,
            "since": since_day.isoformat(),
            "doorEvents": len(door_rows),
            "sun2Sessions": len(session_rows),
            "created": created,
            "existing": existing,
            "alarms": reconstructed,
        }


async def main_cli() -> int:
    load_dotenv(REPO_ROOT / ".env")
    args = parse_args()
    result = await run(date.fromisoformat(args.since), args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main_cli()))
