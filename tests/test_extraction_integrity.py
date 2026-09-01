"""Every relocated calculation/handler body is checked against build 1832."""
import ast
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCKS = {'sun2_axis_snapshot_link_lock', 'sunroom_door_sync_lock', 'met_weather_fetch_lock', 'owntracks_visit_sync_lock'}


class OriginalNames(ast.NodeTransformer):
    def visit_Attribute(self, node):
        self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id == 'process_locks' and node.attr in LOCKS:
            return ast.Name(id=node.attr, ctx=node.ctx)
        if isinstance(node.value, ast.Name) and node.value.id == 'incident_state' and node.attr == 'bollard_failure_started_at':
            return ast.Name(id='bollard_incident_failure_started_at', ctx=node.ctx)
        return node


def body_digest(node):
    node = deepcopy(node)
    body = [n for n in node.body if not (
        isinstance(n, ast.Assign) and isinstance(n.value, ast.Attribute)
        and isinstance(n.value.value, ast.Name) and n.value.value.id == 'dependencies'
    )]
    restored = OriginalNames().visit(ast.Module(body=body, type_ignores=[]))
    writes = {n.id for n in ast.walk(restored) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    global_names = writes & (LOCKS | {'bollard_incident_failure_started_at'})
    if global_names and not any(isinstance(n, ast.Global) for n in restored.body):
        restored.body.insert(0, ast.Global(names=sorted(global_names)))
    return hashlib.sha256(ast.dump(restored, include_attributes=False).encode()).hexdigest()


def test_all_relocated_function_bodies_preserve_original_behavior():
    expected = json.loads((ROOT / 'tests/fixtures/extraction_body_contracts.json').read_text())
    candidates = defaultdict(set)
    paths = [ROOT / 'main.py', *(ROOT / 'fibaro_core').rglob('*.py')]
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                candidates[node.name].add(body_digest(node))
    # Builders now accept the same cache/reader explicitly (64 payload/SQL tests).
    # Dispatcher branches and the intentionally repaired classic redirect have
    # their own contracts below instead of exempting the rest of the code.
    special = {'build_sun2_forecast', 'build_parking_forecast', 'api_v2_module', 'classic_light_settings_view'}
    # Post-extraction changes: concurrency/invalidation tests and differential
    # energy analysis tests compare actual behavior with the frozen old body.
    special.update({'cached_summaries', 'clear_summary_cache', 'build_sunbed_power_analysis'})
    # Additive measurement evidence is covered by the data-source endpoint tests.
    special.add('import_status_detail')
    special.add('import_status_rows')  # Additive provenance; times/thresholds preserved.
    # Bed-state-aware door alarms intentionally extend the extracted runtime.
    # Their current behavior is covered by test_hc3_door_events.py.
    special.update(
        {
            'apply_sunroom_alarm_verification',
            'api_hc3_doors_status',
            'sunroom_door_alarm_payload',
            'sunroom_door_session_payload',
            'sunroom_force_sync_candidates',
            'sunroom_room_detail_payload',
            'sunroom_room_overview_payload',
            'sunroom_status_item',
            'sync_sunroom_alarm_history',
        }
    )
    differences = [name for name, digest in expected.items() if name not in special and digest not in candidates[name]]
    assert not differences, differences


def test_all_ten_module_response_branches_are_unchanged():
    expected = json.loads((ROOT / 'tests/fixtures/module_body_contracts.json').read_text())
    for module, digest in expected.items():
        tree = ast.parse((ROOT / f'fibaro_core/services/modules/{module}.py').read_text(encoding='utf-8'))
        render = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'render')
        end = next(i for i, n in enumerate(render.body) if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'year_start_dt' for t in n.targets))
        body = ast.Module(body=render.body[end + 1:], type_ignores=[])
        assert hashlib.sha256(ast.dump(body, include_attributes=False).encode()).hexdigest() == digest, module


def test_classic_light_settings_redirect_retains_query_parameters():
    import asyncio
    import os
    from starlette.requests import Request
    os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://test:test@127.0.0.1/test')
    import main

    request = Request({'type': 'http', 'method': 'GET', 'path': '/classic/lys/innstillinger',
                       'query_string': b'tab=rules&device=298', 'headers': []})
    response = asyncio.run(main.classic_light_settings_view(request))
    assert response.status_code in (302, 307)
    assert response.headers['location'] == 'https://app.lilletorget.net/bygg/lys/innstillinger?tab=rules&device=298'
