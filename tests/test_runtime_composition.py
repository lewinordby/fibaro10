"""Exercise lifecycle, middleware and single-owner resources without external IO."""
import asyncio
from dataclasses import replace
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://test:test@127.0.0.1/test')
import main
from fibaro_core import lifecycle, middleware


class Session:
    def __init__(self, fail_commit=False):
        self.commit = AsyncMock(side_effect=RuntimeError('commit failed') if fail_commit else None)
        self.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])))
        self.flush = AsyncMock()
        self.add = Mock()
        self.closed = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed += 1


class Connection(Session):
    run_sync = AsyncMock()
    exec_driver_sql = AsyncMock()


def startup_fixture(enabled, fail_commit=False):
    session = Session(fail_commit)
    conn = Connection()
    jobs = Mock(stop_all=AsyncMock())
    dependencies = replace(
        main.lifecycle_dependencies, engine=SimpleNamespace(begin=lambda: conn),
        async_session=lambda: session, background_tasks=jobs,
        FIBARO10_BACKGROUND_TASKS_ENABLED=enabled, SVV_SYNC_ENABLED=True, SVV_API_KEY='test',
        SUN2_AXIS_SNAPSHOT_LINK_ENABLED=True, SUNROOM_DOOR_MONITOR_ENABLED=True,
        HC3_DOOR_UNEXPECTED_CHECK_ENABLED=True, OWNTRACKS_VISIT_SYNC_ENABLED=True,
        OPERATIONAL_RETENTION_ENABLED=True, SUNBED_POWER_CACHE_WARM_ENABLED=True,
        ROBOROCK_CONTROL_TOKEN='test', ensure_energy_node_backfill=AsyncMock(return_value={}),
        ensure_default_roborock_cleaning_profiles=AsyncMock(), ensure_default_roborock_door_automation=AsyncMock(),
        ensure_roborock_schedule_snapshot_backfill=AsyncMock(return_value=0),
        get_or_create_config=AsyncMock(), seed_energy_circuits=AsyncMock(),
    )
    return lifecycle.create_handlers(dependencies), dependencies, jobs, session


@pytest.mark.parametrize('enabled', [False, True])
def test_workers_start_once_only_in_background_role(enabled):
    handlers, deps, jobs, session = startup_fixture(enabled)
    asyncio.run(handlers['startup']())
    names = [call.args[0] for call in jobs.start.call_args_list]
    assert names == ([
        'svv-sync', 'sun2-axis-snapshot-link', 'sunroom-door-monitor', 'hc3-door-poll',
        'owntracks-visit-sync', 'ntfy-outbox', 'operational-retention',
        'sunbed-power-cache-warm', 'roborock-door-automation',
    ] if enabled else [])
    assert len(names) == len(set(names))
    assert session.commit.await_count == 2
    assert session.closed == 2
    assert deps.ensure_roborock_schedule_snapshot_backfill.await_count == int(enabled)
    asyncio.run(handlers['shutdown_application']())
    jobs.stop_all.assert_awaited_once()


def test_failed_initialization_does_not_launch_workers():
    handlers, _, jobs, session = startup_fixture(True, fail_commit=True)
    with pytest.raises(RuntimeError, match='commit failed'):
        asyncio.run(handlers['startup']())
    jobs.start.assert_not_called()
    assert session.closed == 1


def test_process_resources_are_shared_not_copied():
    assert main.cache_dependencies.SUMMARY_CACHE is main.SUMMARY_CACHE
    assert main.sun_dependencies.SUMMARY_CACHE is main.SUMMARY_CACHE
    assert main.parking_dependencies.SUMMARY_CACHE is main.SUMMARY_CACHE
    assert main.sun_dependencies.process_locks is main.process_locks
    assert main.sunroom_dependencies.sunroom_door_verifications is main.sunroom_door_verifications
    assert main.weather_dependencies.process_locks is main.process_locks
    assert main.maintenance_dependencies.process_locks is main.process_locks
    assert main.lifecycle_dependencies.background_tasks is main.background_tasks
    assert main.lifecycle_dependencies.async_session is main.async_session


@pytest.mark.parametrize('valid', [False, True])
def test_authenticated_middleware_checks_session_before_protected_handler(valid):
    user = SimpleNamespace(id=1, name='test', role='viewer', is_master=False)
    deps = replace(main.middleware_dependencies, is_public_request=lambda r: False,
                   is_car_info_app_request_path=lambda p: False, is_koble_worker_request_path=lambda p: False,
                   presented_session_token=lambda r: 'test-token', wants_html=lambda r: False,
                   find_auth_session=AsyncMock(return_value=(user, 123) if valid else None),
                   log_access_attempt=AsyncMock())
    handler = middleware.create_handlers(deps)['access_key_middleware']
    request = Request({'type': 'http', 'method': 'GET', 'path': '/api/overview', 'headers': []})
    next_handler = AsyncMock(return_value=JSONResponse({'ok': True}))
    response = asyncio.run(handler(request, next_handler))
    assert response.status_code == (200 if valid else 401)
    assert next_handler.await_count == int(valid)
    if valid:
        assert request.state.auth_session_id == 123
        assert request.state.auth_role == 'viewer'
        assert not request.state.auth_can_settings


def test_main_is_only_composition_not_business_logic():
    import ast
    from pathlib import Path
    tree = ast.parse(Path(main.__file__).read_text(encoding='utf-8'))
    assert not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for n in tree.body)
