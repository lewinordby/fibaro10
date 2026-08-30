"""Read-only cold/warm timing of the default energy analysis, without startup jobs."""
import asyncio
from datetime import datetime
import json
import time

from sqlalchemy import event
import main


async def measure():
    results = []
    query_seconds = []
    query_started = []

    def before(*args):
        query_started.append(time.perf_counter())

    def after(*args):
        query_seconds.append(time.perf_counter() - query_started.pop())

    event.listen(main.engine.sync_engine, "before_cursor_execute", before)
    event.listen(main.engine.sync_engine, "after_cursor_execute", after)
    for kind in ("cold", "warm"):
        query_seconds.clear()
        start = time.perf_counter()
        async with main.async_session() as session:
            payload = await main.load_sunbed_power_analysis(session, None, None, datetime.now(main.LOCAL_TZ).date())
        results.append({"kind": kind, "elapsed_ms": round((time.perf_counter() - start) * 1000),
                        "sql_ms": round(sum(query_seconds) * 1000), "queries": len(query_seconds),
                        "summary": payload["summary"]})
    await main.engine.dispose()
    print(json.dumps(results, default=str))


asyncio.run(measure())
