import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import Request

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1/example")

from online_dashboard.app import main, revenue
from scripts.mobile_revenue_preview_data import revenue_preview


def test_same_payload_renders_all_periods_and_source_cutoffs():
    payload = revenue_preview()
    html = revenue.render_overview(payload)
    assert [html.index(f'data-period="{key}"') for key in revenue.PERIOD_KEYS] == sorted(
        html.index(f'data-period="{key}"') for key in revenue.PERIOD_KEYS
    )
    for period in payload["statusPeriods"]:
        assert revenue.money(period["total"]) in html
        assert revenue.money(period["previousFullTotal"]) in html
        assert revenue.money(period["extraComparisons"][0]["fullTotal"]) in html
    assert html.count('Soling kl 14:27') == 4
    assert html.count('Parkering kl 14:00') == 4
    assert html.count('5. beste') == 4
    assert '20 stk' in html and '206 kr i snitt' in html
    assert '19.09 kl. 16:00' in html
    assert 'Samme uke 2025' in html and 'Samme måned 2025' in html
    assert 'Hele 2024' in html
    assert '+920 kr' in html and '−640 kr' in html


@pytest.mark.parametrize('value', [None, 'bad', float('nan'), float('inf')])
def test_missing_values_are_not_zero(value):
    assert revenue.money(value) == '–'
    assert 'Ukjent grunnlag' in revenue.delta(value, 100)


def test_zero_reference_and_remaining():
    assert 'Ingen prosentbasis' in revenue.delta(10, 0)
    assert '+10 kr' in revenue.delta(10, 0)
    assert '0 kr' == revenue.money(0)
    assert '10 kr gjenstår' in revenue.full_reference(90, {'fullTotal': 100})
    assert '10 kr over referansen' in revenue.full_reference(110, {'fullTotal': 100})


def test_rounding_matches_desktop_currency_and_percent():
    assert revenue.money(100.50) == '101 kr'
    assert revenue.money(-100.50) == '-101 kr'
    assert '+3%' in revenue.delta(102.5, 100)
    assert '-2%' in revenue.delta(97.5, 100)


def test_mobile_styles_are_public_without_disclosing_revenue():
    from fastapi.testclient import TestClient
    response = TestClient(main.app).get('/mobile-assets/revenue-dashboard.css')
    assert response.status_code == 200
    assert '--appkit-surface' in response.text


def test_api_text_is_escaped():
    payload = revenue_preview()
    payload['statusPeriods'][0]['title'] = '<script>alert(1)</script>'
    payload['statusPeriods'][0]['rank']['basis'] = '\" onclick=\"bad'
    html = revenue.render_overview(payload)
    assert '<script>' not in html
    assert '&lt;script&gt;' in html
    assert 'title="&quot; onclick=&quot;bad"' in html


def test_fetch_uses_existing_session_and_does_not_follow_redirects(monkeypatch):
    captured = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit):
            assert limit == 1_000_000
            return json.dumps(revenue_preview()).encode()
    class Opener:
        def open(self, request, timeout):
            captured.update(url=request.full_url, headers=dict(request.header_items()), timeout=timeout)
            return Response()
    def opener(handler):
        assert handler is revenue.NoRedirect
        return Opener()
    monkeypatch.setenv('FIBARO10_BASE_URL', 'http://core:8110/')
    monkeypatch.setattr(revenue.urllib.request, 'build_opener', opener)
    assert revenue.read_overview('sample-session')['statusPeriods']
    assert captured == {'url': 'http://core:8110/api/overview?scope=revenue',
                        'headers': {'X-session-token': 'sample-session', 'Accept': 'application/json'}, 'timeout': 8}
    assert revenue.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere/') is None


@pytest.mark.parametrize('payload', [None, [], {}, {'statusPeriods': [None] * 4}, {'statusPeriods': [{'key': 'today'}] * 4}])
def test_invalid_payload_fails_closed(monkeypatch, payload):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit): return json.dumps(payload).encode()
    monkeypatch.setattr(revenue.urllib.request, 'build_opener', lambda *a: SimpleNamespace(open=lambda *a, **kw: Response()))
    assert asyncio.run(revenue.load_overview('test-session')) is None


@pytest.mark.parametrize('token', [None, '', 'bad\r\nheader', 'bad;cookie'])
def test_invalid_session_does_not_request_data(monkeypatch, token):
    def fail(*args): raise AssertionError('Must not call API')
    monkeypatch.setattr(revenue, 'read_overview', fail)
    assert asyncio.run(revenue.load_overview(token)) is None


def test_timeout_shows_unavailable_not_zero(monkeypatch):
    def timeout(*args): raise TimeoutError()
    monkeypatch.setattr(revenue, 'read_overview', timeout)
    result = asyncio.run(revenue.load_overview('session'))
    html = revenue.render_overview(result)
    assert 'ikke tilgjengelig' in html
    assert '0 kr' not in html and 'data-period' not in html


@pytest.mark.parametrize('role,expected_calls', [('viewer', 0), ('settings', 1), ('master', 1)])
def test_revenue_route_preserves_access_control(monkeypatch, role, expected_calls):
    request = Request({'type': 'http', 'headers': [(b'cookie', b'fibaro10_session=sample-session')]})
    request.state.access_key = {'name': 'Test', 'role': role}
    load = AsyncMock(return_value=revenue_preview())
    monkeypatch.setattr(main, 'SOURCE_MODE', True)
    monkeypatch.setattr(revenue, 'load_overview', load)
    response = asyncio.run(main.revenue_detail(request))
    assert load.await_count == expected_calls
    if expected_calls:
        load.assert_awaited_once_with('sample-session')
        assert response.body.count(b'data-period=') == 4
    else:
        assert response.status_code == 303


def test_dashboard_uses_same_revenue_renderer():
    import inspect
    source = inspect.getsource(main.dashboard)
    assert 'show_revenue and SOURCE_MODE' in source
    assert 'mobile_revenue.render_overview(overview)' in source
    assert 'mobile_revenue.load_overview' in source
    assert 'show_revenue and SNAPSHOT_MODE' in source
