"""Cache services with explicit process dependencies."""

from dataclasses import dataclass
from datetime import datetime
from fibaro_core.services.summaries.energy import build_energy_summaries_fast
from fibaro_core.services.summaries.parking import build_parking_summaries_fast
from fibaro_core.services.summaries.sun import build_sun2_summaries_fast
from typing import Any, Callable, Dict


@dataclass
class Dependencies:
    SUMMARY_CACHE: Any
    SUMMARY_CACHE_TTL: Any


def create_service(dependencies: Dependencies):

    async def cached_summaries(cache_key: str, builder, session, force: bool = False) -> Dict[str, Any]:
        SUMMARY_CACHE = dependencies.SUMMARY_CACHE
        SUMMARY_CACHE_TTL = dependencies.SUMMARY_CACHE_TTL
        now = datetime.utcnow()
        cached = SUMMARY_CACHE.get(cache_key)
        if not force and cached and cached.get("expires", datetime.min) > now:
            return cached["value"]
        value = await builder(session)
        SUMMARY_CACHE[cache_key] = {"expires": now + SUMMARY_CACHE_TTL, "value": value}
        return value

    async def get_sun2_summaries(session, force: bool = False) -> Dict[str, Any]:
        return await cached_summaries("sun2", build_sun2_summaries_fast, session, force)

    async def get_energy_summaries(session, force: bool = False) -> Dict[str, Any]:
        return await cached_summaries("energy", build_energy_summaries_fast, session, force)

    async def get_parking_summaries(session, force: bool = False) -> Dict[str, Any]:
        return await cached_summaries("parking", build_parking_summaries_fast, session, force)

    def clear_summary_cache(*keys: str) -> None:
        SUMMARY_CACHE = dependencies.SUMMARY_CACHE
        for key in keys:
            SUMMARY_CACHE.pop(key, None)
            prefix = f"{key}:"
            for cached_key in list(SUMMARY_CACHE):
                if cached_key.startswith(prefix):
                    SUMMARY_CACHE.pop(cached_key, None)

    return {
        "cached_summaries": cached_summaries,
        "clear_summary_cache": clear_summary_cache,
        "get_energy_summaries": get_energy_summaries,
        "get_parking_summaries": get_parking_summaries,
        "get_sun2_summaries": get_sun2_summaries,
    }
