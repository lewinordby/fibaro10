"""Frozen calculation contracts captured from build 1832, before relocation."""
import asyncio
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from fibaro_core.services.forecasts import builders, models, snapshots


class Session:
    def __init__(self, rows=()):
        self.rows = rows
        self.queries = []
        self.added = []

    async def execute(self, statement):
        from sqlalchemy.dialects import postgresql
        self.queries.append(str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True})))
        return SimpleNamespace(all=lambda: self.rows)

    def add(self, row):
        self.added.append(row)


def history_for(today, count):
    rows = []
    for offset in range(count):
        day = today - timedelta(days=offset)
        sessions = (offset * 13) % 91
        paid = sessions * 78.35
        rows.append(dict(period=day.isoformat(), sessions=sessions, paid=paid,
                         minutes=sessions * 24, vehicles=sessions // 2,
                         totalt_antall_solinger=sessions, totalt_inntjent_kr=paid,
                         total_soletid_minutter=sessions * 24))
    rows.append({'period': 'invalid'})
    return {'daily': rows, 'first_date': today - timedelta(days=count), 'last_date': today}


async def forecast_contracts(namespace=None):
    results = {}
    for stamp in ['2024-02-29T06:30', '2025-12-31T12:00', '2026-04-02T17:12', '2026-08-30T23:15']:
        now = datetime.fromisoformat(stamp)
        for count in [0, 30, 400, 1500]:
            for domain in ['sun2', 'parking']:
                session = Session([(now.date() - timedelta(days=2), 13, 50)])
                getter = AsyncMock(return_value=history_for(now.date(), count))
                cache = {}
                name = f'build_{domain}_forecast'
                if namespace is None:
                    result = await getattr(builders, name)(session, now.date(), now, cache=cache, summaries_getter=getter)
                else:
                    namespace['SUMMARY_CACHE'] = cache
                    namespace[f'get_{domain}_summaries'] = getter
                    result = await namespace[name](session, now.date(), now)
                payload = json.dumps([result, session.queries], default=str, sort_keys=True, ensure_ascii=True)
                results[f'{stamp}/{count}/{domain}'] = hashlib.sha256(payload.encode()).hexdigest()
    return results


def test_calculations_and_queries_match_pre_extraction_contract():
    expected = json.loads((Path(__file__).parent / 'fixtures/forecast_contracts.json').read_text())
    assert asyncio.run(forecast_contracts()) == expected


@pytest.mark.parametrize('domain', ['sun2', 'parking'])
def test_forecast_cache_hit_avoids_all_queries(domain):
    async def run():
        now = datetime(2026, 8, 30, 15)
        getter = AsyncMock(return_value=history_for(now.date(), 30))
        cache = {}
        session = Session()
        first = await getattr(builders, f'build_{domain}_forecast')(session, now.date(), now, cache=cache, summaries_getter=getter)
        count = len(session.queries)
        second = await getattr(builders, f'build_{domain}_forecast')(session, now.date(), now, cache=cache, summaries_getter=getter)
        assert second is first
        assert getter.await_count == 1
        assert len(session.queries) == count
    asyncio.run(run())


def test_snapshot_save_adds_three_periods_without_committing():
    async def run():
        now = datetime(2026, 8, 30, 23, 30)
        session = Session()
        forecast = await builders.build_parking_forecast(session, now.date(), now, cache={}, summaries_getter=AsyncMock(return_value=history_for(now.date(), 30)))
        await snapshots.save_forecast_snapshots(session, 'parking', forecast, 'test')
        assert [row.period_type for row in session.added] == ['day', 'month', 'year']
        assert all(row.created_by == 'test' for row in session.added)
        assert session.added[0].forecast_paid == forecast['day']['forecast']['paid']
    asyncio.run(run())


@pytest.mark.parametrize('fraction', [0, 0.1, 0.5, 1])
def test_forecast_never_falls_below_actual(fraction):
    value, _ = models.intraday_forecast_value(100, 10, fraction, 800, 420)
    assert value >= 100
