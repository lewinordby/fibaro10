import os
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://example:example@127.0.0.1:5432/example",
)

from alarm_mobile.app.main import INDEX_HTML as ALARM_HTML  # noqa: E402
from maintenance_mobile.app.main import INDEX_HTML as MAINTENANCE_HTML  # noqa: E402
from online_dashboard.app.main import DASHBOARD_HTML, DETAIL_HTML, LOGIN_HTML  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


def test_shared_appkit_assets_are_versioned_in_repo() -> None:
    asset_root = ROOT / "packages" / "mobile-appkit"
    assert (asset_root / "vendor" / "appkit-style.css").is_file()
    assert (asset_root / "vendor" / "highlights" / "highlight-blue.css").is_file()
    assert (asset_root / "lilletorget-appkit.css").is_file()
    assert (asset_root / "lilletorget-appkit.js").is_file()


def test_all_mobile_shells_load_the_shared_theme() -> None:
    for html in (ALARM_HTML, MAINTENANCE_HTML, DASHBOARD_HTML, DETAIL_HTML, LOGIN_HTML):
        assert "/appkit-assets/vendor/appkit-style.css?v=1" in html
        assert "/appkit-assets/lilletorget-appkit.css?v=2" in html
        assert "/appkit-assets/lilletorget-appkit.js?v=2" in html
        assert 'class="appkit-mobile theme-light' in html


def test_mobile_apps_have_stable_bottom_navigation() -> None:
    assert 'class="appkit-footer maintenance-nav"' in MAINTENANCE_HTML
    assert 'class="appkit-footer bottom-nav"' in ALARM_HTML
    assert "{{ mobile_nav }}" in DASHBOARD_HTML
    assert "{{ mobile_nav }}" in DETAIL_HTML


def test_mobile_apps_use_appkit_dashboard_patterns() -> None:
    assert "appkit-glance maintenance-glance" in MAINTENANCE_HTML
    assert "is-active is-primary" in MAINTENANCE_HTML
    assert "dashboard-glance" in DASHBOARD_HTML
    assert "appkit-content-title" in DASHBOARD_HTML


def test_online_detail_pages_use_the_fixed_header_as_the_only_title() -> None:
    assert '<div class="appkit-header-title">{{ title }}' in DETAIL_HTML
    assert '<span class="appkit-header-subtitle">Lilletorget</span>' in DETAIL_HTML
    assert '<section class="detail-hero">' not in DETAIL_HTML


def test_online_dashboard_uses_the_fixed_header_as_the_only_title() -> None:
    assert '<div class="appkit-header-title">Dashboard' in DASHBOARD_HTML
    assert "dashboard-page-title" not in DASHBOARD_HTML
    assert "Driftsoversikt" not in DASHBOARD_HTML
    assert '<small class="dashboard-glance-detail">{{ open_detail }}</small>' in DASHBOARD_HTML


def test_mobile_shells_use_the_vector_brand_mark() -> None:
    for name in ("lilletorget-mark.svg", "lilletorget-mark-mono.svg", "lilletorget-wordmark.svg"):
        source = (ROOT / "static" / name).read_text(encoding="utf-8")
        assert source.startswith("<svg")
        assert 'viewBox="' in source

    for html in (ALARM_HTML, MAINTENANCE_HTML, DASHBOARD_HTML, DETAIL_HTML):
        assert "/static/lilletorget-mark.svg?v=1681" in html
        assert "/static/lilletorget-mark.png" not in html

    assert "/static/lilletorget-wordmark.svg?v=1681" in LOGIN_HTML
    assert "/static/lilletorget-login.png" not in LOGIN_HTML


def test_shared_theme_explicitly_allows_touch_scrolling() -> None:
    source = (ROOT / "packages" / "mobile-appkit" / "lilletorget-appkit.css").read_text(encoding="utf-8")
    assert "overflow-y: auto !important" in source
    assert "touch-action: pan-y" in source
    assert "-webkit-overflow-scrolling: touch" in source
    assert "#page" in source and "overflow: visible !important" in source
