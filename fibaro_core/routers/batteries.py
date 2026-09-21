"""Battery inventory across existing collectors; no writes or hardware commands."""

import asyncio
import logging

from fastapi import APIRouter, Response
from sqlalchemy import select
from sqlalchemy.orm import load_only

from fibaro_core.models.cleaning import RoborockRobot, RoborockStatusSample, RoborockTelemetrySample
from fibaro_core.services.batteries import robot_battery
from time_formatting import api_local_iso, local_now_naive

logger = logging.getLogger(__name__)


def create_batteries_router(session_factory, hc3_snapshot):
    router = APIRouter()

    @router.get("/api/system/batteries")
    async def api_system_batteries(response: Response):
        response.headers["Cache-Control"] = "no-store"
        hc3 = await asyncio.to_thread(hc3_snapshot.read)
        now = local_now_naive()
        rows = list(hc3["rows"])
        errors = [error for error in (hc3["error"], hc3["roomsError"]) if error]
        try:
            async with session_factory() as session:
                robots = (await session.execute(select(RoborockRobot))).scalars().all()
                for robot in robots:
                    samples = []
                    for model in (RoborockTelemetrySample, RoborockStatusSample):
                        columns = [model.timestamp, model.battery, model.state_name]
                        if model is RoborockTelemetrySample:
                            columns.append(model.is_charging)
                        sample = (await session.execute(
                            select(model).options(load_only(*columns))
                            .where(model.robot_duid == robot.duid, model.battery.is_not(None))
                            .order_by(model.timestamp.desc(), model.id.desc()).limit(1)
                        )).scalars().first()
                        samples.append(sample)
                    rows.append(robot_battery(robot, samples, now))
        except Exception:
            logger.exception("Could not read robot battery inventory")
            errors.append("Batterier fra robotene kunne ikke leses. Oversikten er ufullstendig.")
        rows.sort(key=lambda row: (
            {"critical": 0, "low": 1, "unknown": 2, "ok": 3}[row["status"]],
            row["level"] if row["level"] is not None else -1, row["name"].casefold(),
        ))
        return {"generatedAt": api_local_iso(now), "hc3CheckedAt": hc3["checkedAt"],
                "hc3Unavailable": bool(hc3["error"]), "errors": errors, "devices": rows}

    return router
