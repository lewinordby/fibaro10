"""Compare old/new calculations on one database snapshot; no startup jobs.

The caller supplies CANDIDATE_ENERGY and CANDIDATE_TIME source strings before
this script, then pipes it into an existing web container's Python interpreter.
"""
import asyncio
from datetime import datetime
import json
import statistics
import sys
import time
import types

import main

candidate = types.ModuleType('candidate_energy')
sys.modules[candidate.__name__] = candidate
exec(compile(CANDIDATE_ENERGY, '<candidate-energy>', 'exec'), candidate.__dict__)
time_module = types.ModuleType('candidate_time')
exec(compile(CANDIDATE_TIME, '<candidate-time>', 'exec'), time_module.__dict__)
candidate.normalize_local_naive = time_module.normalize_local_naive
new_builder = candidate.create_service(main.energy_dependencies)['build_sunbed_power_analysis']
original_to_thread = asyncio.to_thread
timings = {'before_ms': [], 'after_ms': []}


async def compare(builder, *args, **kwargs):
    if builder.__name__ != 'build_sunbed_power_analysis':
        return await original_to_thread(builder, *args, **kwargs)
    result = None
    for _ in range(3):
        start = time.perf_counter()
        before = await original_to_thread(builder, *args, **kwargs)
        timings['before_ms'].append(round((time.perf_counter() - start) * 1000))
        start = time.perf_counter()
        result = await original_to_thread(new_builder, *args, **kwargs)
        timings['after_ms'].append(round((time.perf_counter() - start) * 1000))
        assert before == result, 'Changed results on identical real data'
    return result


async def run():
    asyncio.to_thread = compare
    try:
        async with main.async_session() as session:
            await main.load_sunbed_power_analysis(session, None, None, datetime.now(main.LOCAL_TZ).date())
    finally:
        asyncio.to_thread = original_to_thread
        await main.engine.dispose()
    timings['identical_results'] = True
    timings['median_before_ms'] = statistics.median(timings['before_ms'])
    timings['median_after_ms'] = statistics.median(timings['after_ms'])
    print(json.dumps(timings))


asyncio.run(run())
