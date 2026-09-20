import os
from datetime import datetime
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1/example")

from online_dashboard.app import main, revenue
from scripts.mobile_revenue_preview_data import revenue_preview


def test_period_navigation_is_progressive_and_preserves_all_data():
    html = revenue.render_overview(revenue_preview())
    assert html.count('role="tab"') == 4
    assert html.count('class="rev-period"') == 4
    assert html.count('class="rev-breakdown"') == 4
    for key in revenue.PERIOD_KEYS:
        assert f'aria-controls="revenue-{key}"' in html
        assert f'data-state-key="revenue-breakdown-{key}"' in html
    # Without JavaScript the period buttons are hidden, never the data.
    assert 'aria-label="Omsetningsperiode" hidden' in html
    assert '<article hidden' not in html
    assert 'Forskjell per inntektskilde' in html


def test_detail_summary_preserves_sensor_information_and_physical_state():
    html = main.render_door_status_summary({
        "state": "closed", "display_state_label": "Stengt", "battery_level": 0,
        "last_changed": "18.09 kl. 13:27:51", "age_label": "2 døgn",
        "last_updated": "20.09 kl. 10:15:05",
    })
    for value in ("Stengt", "Lukket", "0%", "18.09 kl. 13:27:51", "2 døgn", "20.09 kl. 10:15:05"):
        assert value in html
    assert 'detail-stats' not in html
    assert 'Ukjent' in main.render_door_status_summary({})
    assert '&lt;script&gt;' in main.render_door_status_summary({'last_changed': '<script>'})


def test_room_counts_do_not_count_disabled_room_as_occupied():
    html = main.render_door_counts([
        {'state': 'closed', 'display_state': 'disabled'},
        {'state': 'open'}, {'state': 'unknown'},
    ], datetime(2026, 9, 20, 10, 15), solrooms=True)
    assert '<dt>I bruk</dt><dd>0</dd>' in html
    assert '<dt>Stengt</dt><dd>1</dd>' in html
    assert '<dt>Ledige</dt><dd>1</dd>' in html
    assert '<dt>Ukjent</dt><dd>1</dd>' in html


def test_mobile_layout_script_is_public_and_loaded_on_both_views():
    response = TestClient(main.app).get('/mobile-assets/mobile-layout.js')
    assert response.status_code == 200
    assert 'pagehide' in response.text
    for html in (main.DASHBOARD_HTML, main.DETAIL_HTML):
        assert '/mobile-assets/mobile-layout.js?v=1' in html
        assert '/mobile-assets/revenue-dashboard.css?v=2' in html
