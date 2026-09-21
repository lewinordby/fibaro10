"""HC3 sensor battery inventory; no database queries or hardware commands."""

import asyncio

from fastapi import APIRouter, Response
from time_formatting import api_local_iso, local_now_naive

def create_batteries_router(hc3_snapshot):
    router = APIRouter()

    @router.get("/api/system/batteries")
    async def api_system_batteries(response: Response):
        response.headers["Cache-Control"] = "no-store"
        hc3 = await asyncio.to_thread(hc3_snapshot.read)
        now = local_now_naive()
        rows = list(hc3["rows"])
        errors = [error for error in (hc3["error"], hc3["roomsError"]) if error]
        rows.sort(key=lambda row: (
            bool(row.get("retired")),
            {"critical": 0, "low": 1, "unknown": 2, "ok": 3}[row["status"]],
            row["level"] if row["level"] is not None else -1, row["name"].casefold(),
        ))
        return {"generatedAt": api_local_iso(now), "hc3CheckedAt": hc3["checkedAt"],
                "hc3Unavailable": bool(hc3["error"]), "errors": errors, "devices": rows}

    return router
