"""Integration boundaries left in the composition root during extraction."""

import asyncio
import ast
from collections import Counter
from datetime import datetime, timedelta
import inspect
import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
import main
from fibaro_core.services.summaries import energy, parking, periods, revenue, sun


def test_composition_root_has_no_shadowed_function_definitions():
    tree = ast.parse(Path(main.__file__).read_text(encoding="utf-8"))
    names = Counter(node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
    assert not {name: count for name, count in names.items() if count > 1}


@pytest.mark.parametrize("module", [energy, parking, periods, revenue, sun])
def test_composition_root_reexports_the_actual_domain_functions(module):
    for name, value in vars(module).items():
        if inspect.isfunction(value) and value.__module__ == module.__name__:
            assert getattr(main, name) is value


@pytest.mark.parametrize("domain,builder_name,getter", [
    ("sun2", "build_sun2_summaries_fast", main.get_sun2_summaries),
    ("parking", "build_parking_summaries_fast", main.get_parking_summaries),
    ("energy", "build_energy_summaries_fast", main.get_energy_summaries),
])
def test_cache_still_has_one_owner_and_force_bypasses_it(monkeypatch, domain, builder_name, getter):
    cache = {}
    monkeypatch.setattr(main, "SUMMARY_CACHE", cache)
    builder = AsyncMock(side_effect=[{"total": 10}, {"total": 20}])
    monkeypatch.setattr(main, builder_name, builder)
    session = object()

    async def run():
        first = await getter(session)
        assert await getter(session) is first
        second = await getter(session, force=True)
        assert second == {"total": 20}
        assert cache[domain]["value"] is second
        assert builder.await_count == 2
        assert all(call.args == (session,) for call in builder.await_args_list)

    asyncio.run(run())


def test_cache_invalidation_includes_variants_without_clearing_other_domains(monkeypatch):
    cache = dict.fromkeys(["sun2", "sun2:year", "sun2:month", "sun20", "parking", "energy"])
    monkeypatch.setattr(main, "SUMMARY_CACHE", cache)
    main.clear_summary_cache("sun2")
    assert set(cache) == {"sun20", "parking", "energy"}


def test_failed_refresh_does_not_replace_cached_data(monkeypatch):
    old = {"expires": datetime.min, "value": {"total": 10}}
    cache = {"parking": old}
    monkeypatch.setattr(main, "SUMMARY_CACHE", cache)
    builder = AsyncMock(side_effect=RuntimeError("database unavailable"))
    with pytest.raises(RuntimeError, match="database unavailable"):
        asyncio.run(main.cached_summaries("parking", builder, object()))
    assert cache["parking"] is old
    assert builder.await_count == 1


def test_comparisons_keep_separate_last_successful_source_times_not_wall_clock():
    now = datetime(2026, 8, 30, 16)
    sun_at = now.replace(hour=14, minute=25)
    parking_at = now.replace(hour=12)
    imports = [
        {"job_name": "sun2_sessions_import", "last_success_at": sun_at},
        {"job_name": "easypark_parking_import", "last_success_at": parking_at, "last_failed_at": now},
    ]
    windows = main.status_comparison_windows(imports, now)
    assert windows == main.status_comparison_windows(imports, now + timedelta(hours=2))
    for period in windows.values():
        assert period["current"]["sunEnd"] == sun_at
        assert period["current"]["parkingEnd"] == parking_at
        for comparison in period["comparisons"]:
            assert comparison["sunEnd"].time() == sun_at.time()
            assert comparison["parkingEnd"].time() == parking_at.time()
    yesterday = windows["today"]["comparisons"][0]
    assert yesterday["parkingEnd"] == datetime(2026, 8, 29, 12)


def test_previous_month_comparison_stops_at_month_end():
    now = datetime(2024, 3, 31, 16)
    imports = [{"job_name": name, "last_success_at": now.replace(hour=12)}
               for name in ("sun2_sessions_import", "easypark_parking_import")]
    comparison = main.status_comparison_windows(imports, now)["month"]["comparisons"][0]
    assert comparison["start"] == datetime(2024, 2, 1)
    assert comparison["sunEnd"] == comparison["parkingEnd"] == datetime(2024, 3, 1)
