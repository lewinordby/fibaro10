"""Restore evidenced clean-water changes from timestamped Dreame logs, not guesses.

Read-only unless --apply is passed. Run inside a Fibaro10 container with DATABASE_URL.
The input must contain logs for ONE robot only; --external-id identifies that robot.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from fibaro_core.database import create_database
from fibaro_core.models.cleaning import RoborockRobot, RoborockTelemetryEvent
from roborock_domain import roborock_telemetry_changes
from time_formatting import normalize_local_naive


def parse_changes(text: str):
    pattern = re.compile(r"^(\S+) .*Property CLEAN_WATER_TANK_STATUS Changed: ([012]) -> ([012])$")
    for line in text.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        stamp, previous, current = match.groups()
        timestamp = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("Log timestamps must include timezone")
        names = {"0": "installed", "1": "not_installed", "2": "low_water"}
        changes = roborock_telemetry_changes(
            {"clear_water_status": int(previous), "clear_water_status_name": names[previous]},
            {"clear_water_status": int(current), "clear_water_status_name": names[current]}, "dreame")
        for change in changes:
            yield normalize_local_naive(timestamp), change, line


async def main(args):
    engine, sessions = create_database(os.environ["DATABASE_URL"])
    duid = f"dreame:{args.external_id}"
    results = []
    try:
        async with sessions() as session:
            robot = (await session.execute(select(RoborockRobot).where(RoborockRobot.duid == duid))).scalars().one()
            for stamp, change, evidence in parse_changes(args.log_file.read_text(encoding="utf-8")):
                existing = (await session.execute(select(RoborockTelemetryEvent).where(
                    RoborockTelemetryEvent.robot_duid == duid,
                    RoborockTelemetryEvent.field_name == "clear_water_status",
                    RoborockTelemetryEvent.timestamp >= stamp.replace(microsecond=0),
                    RoborockTelemetryEvent.timestamp < stamp.replace(microsecond=0) + timedelta(seconds=1),
                    RoborockTelemetryEvent.previous_value == change["previous_value"],
                    RoborockTelemetryEvent.current_value == change["current_value"],
                ))).scalars().first()
                results.append({"robot": robot.name, "timestamp": stamp.isoformat(),
                                **change, "action": "already_present" if existing else "insert"})
                if not existing:
                    session.add(RoborockTelemetryEvent(robot_duid=duid, timestamp=stamp, **change,
                        raw={"source": "dreame-log-recovery", "evidence": evidence,
                             "recovered_at": datetime.now().isoformat()}))
                    await session.flush()
            if args.apply:
                await session.commit()
            else:
                await session.rollback()
    finally:
        await engine.dispose()
    print(json.dumps({"applied": args.apply, "events": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-file", type=Path, required=True)
    parser.add_argument("--external-id", required=True)
    parser.add_argument("--apply", action="store_true")
    asyncio.run(main(parser.parse_args()))
