import asyncio
from datetime import timedelta

import pytest

from fibaro_core.services.runtime.cache import Dependencies, create_service


def service():
    cache = {}
    return create_service(Dependencies(cache, timedelta(minutes=5))), cache


def test_eight_simultaneous_misses_execute_one_builder():
    async def scenario():
        api, cache = service()
        calls = 0

        async def builder(session):
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.01)
            return {"value": 42}

        results = await asyncio.gather(*(api["cached_summaries"]("parking", builder, None) for _ in range(8)))
        assert calls == 1
        assert results == [{"value": 42}] * 8

    asyncio.run(scenario())


def test_invalidation_during_query_cannot_repopulate_stale_cache():
    async def scenario():
        api, cache = service()
        started, release = asyncio.Event(), asyncio.Event()

        async def builder(session):
            started.set()
            await release.wait()
            return {"old": True}

        request = asyncio.create_task(api["cached_summaries"]("sun2:month", builder, None))
        await started.wait()
        api["clear_summary_cache"]("sun2")
        release.set()
        await request
        assert "sun2:month" not in cache
        await api["cached_summaries"]("sun2:month", builder, None)
        assert "sun2:month" in cache

    asyncio.run(scenario())


def test_failed_builder_does_not_lock_out_following_requests():
    async def scenario():
        api, cache = service()

        async def fail(session):
            raise RuntimeError("database unavailable")

        with pytest.raises(RuntimeError):
            await api["cached_summaries"]("sun2", fail, None)

        async def succeed(session):
            return 7

        assert await api["cached_summaries"]("sun2", succeed, None) == 7

    asyncio.run(scenario())


def test_different_keys_do_not_block_each_other():
    async def scenario():
        api, _ = service()
        both_started = asyncio.Event()
        calls = 0

        async def builder(session):
            nonlocal calls
            calls += 1
            if calls == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), 1)
            return 1

        await asyncio.gather(api["cached_summaries"]("sun2", builder, None), api["cached_summaries"]("parking", builder, None))

    asyncio.run(scenario())
