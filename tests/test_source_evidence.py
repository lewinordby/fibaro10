import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fibaro_core.services.source_evidence import measurement_evidence, source_data_evidence, SOURCE_MEASUREMENTS
from import_jobs import IMPORT_JOB_DEFINITIONS


def test_only_periodic_measurements_become_stale():
    now = datetime(2026, 8, 30, 12)
    stamp = now - timedelta(hours=12)
    assert measurement_evidence(stamp, label='door', now=now)['status'] == 'observed'
    assert measurement_evidence(stamp, label='energy', now=now, periodic=True, warning_minutes=5)['status'] == 'warn'
    assert measurement_evidence(None, label='energy', now=now)['status'] == 'unknown'


def test_future_time_and_timezone_are_not_reported_as_fresh():
    now = datetime(2026, 8, 30, 12)
    assert measurement_evidence(now + timedelta(minutes=10), label='energy', now=now)['status'] == 'warn'
    equivalent_utc = datetime(2026, 8, 30, 10, tzinfo=timezone.utc)
    item = measurement_evidence(equivalent_utc, label='energy', now=now, periodic=True, warning_minutes=5)
    assert item['status'] == 'ok'
    assert item['timestamp'] == '2026-08-30T12:00:00+02:00'


def test_sources_use_indexed_single_measurement_and_never_call_collectors():
    assert set(SOURCE_MEASUREMENTS) <= set(IMPORT_JOB_DEFINITIONS)
    for source in SOURCE_MEASUREMENTS:
        session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None)))
        result = asyncio.run(source_data_evidence(session, source))
        query = str(session.execute.call_args.args[0])
        assert 'LIMIT' in query and 'ORDER BY' in query
        assert result['measurements'][0]['status'] == 'unknown'
        assert result['coverageThrough'] is None
        assert result['serviceHealth'] == 'not_checked'


def test_every_robot_is_shown_including_missing_status():
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(all=lambda: [('VIP', None), ('2.etg', datetime(2026, 1, 1))])))
    result = asyncio.run(source_data_evidence(session, 'roborock_sync'))
    assert [row['label'] for row in result['measurements']] == ['VIP', '2.etg']
    assert result['measurements'][0]['status'] == 'unknown'
    assert result['measurements'][1]['status'] == 'warn'


def test_unknown_coverage_is_not_replaced_by_import_time():
    session = SimpleNamespace(execute=AsyncMock())
    result = asyncio.run(source_data_evidence(session, 'sun2_members_import'))
    session.execute.assert_not_called()
    assert result['measurements'] == []
    assert result['coverageThrough'] is None


def test_import_timestamps_keep_their_values_and_explain_their_origin(monkeypatch):
    import main
    from fibaro_core.models import ImportJobStatus
    from fibaro_core.services.runtime import system

    stamp = datetime(2026, 8, 30, 8)
    failure = stamp + timedelta(minutes=5)
    scheduled = stamp + timedelta(hours=2)
    jobs = ['easypark_parking_import', 'hc3_energy_1min']
    definitions = {key: IMPORT_JOB_DEFINITIONS[key] for key in jobs}
    definitions['sun2_members_import'] = IMPORT_JOB_DEFINITIONS['sun2_members_import']
    monkeypatch.setattr(system, 'IMPORT_JOB_DEFINITIONS', definitions)
    rows = [ImportJobStatus(job_name=key, title=key, category='Test', status='failed',
                           last_success_at=stamp, last_failed_at=failure, last_run_at=failure) for key in jobs]
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: rows))))
    monkeypatch.setattr(main.system_dependencies, 'easypark_downloader_status', lambda: {})
    monkeypatch.setattr(main.system_dependencies, 'easypark_next_run_at_from_status', lambda _: scheduled)
    # The metadata fallback is intentionally represented by a stored record.
    async def execute(query):
        if 'import_job_status' in str(query):
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: rows))
        if 'count(' in str(query):
            return SimpleNamespace(scalar_one=lambda: 1)
        return SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: SimpleNamespace(imported_at=stamp)))
    session.execute = execute
    result = {row['job_name']: row for row in asyncio.run(main.import_status_rows(session))}
    for key in jobs:
        assert result[key]['last_success_at'] == stamp
        assert result[key]['last_failed_at'] == failure
        assert result[key]['status'] == 'bad'
        assert result[key]['success_time_basis'] == 'import_log'
    assert result[jobs[0]]['next_expected_at'] == scheduled
    assert result[jobs[0]]['next_expected_kind'] == 'scheduled'
    assert result[jobs[1]]['next_expected_at'] == stamp + timedelta(minutes=2)
    assert result[jobs[1]]['next_expected_kind'] == 'freshness_deadline'
    assert result['sun2_members_import']['success_time_basis'] == 'stored_data'


def test_detail_endpoint_adds_evidence_without_changing_run_history(monkeypatch):
    import main
    from fibaro_core.services import source_evidence
    from fibaro_core.routers.ingestion_routes import create_router
    from contextlib import asynccontextmanager

    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))))
    @asynccontextmanager
    async def sessions():
        yield session
    router = create_router(SimpleNamespace(async_session=sessions,
        import_status_rows=AsyncMock(return_value=[{'job_name': 'hc3_energy_1min'}]),
        api_import_status_row=main.api_import_status_row, api_import_job_run_row=main.api_import_job_run_row))
    expected = {'measurements': [], 'coverageThrough': None}
    monkeypatch.setattr(source_evidence, 'source_data_evidence', AsyncMock(return_value=expected))
    payload = asyncio.run(router.endpoints['import_status_detail']('hc3_energy_1min'))
    assert payload['evidence'] == expected
    assert payload['source']['job_name'] == 'hc3_energy_1min'
    assert payload['runs'] == []
    assert payload['summary'] == {'runs': 0, 'ok': 0, 'failed': 0, 'unknown': 0}
