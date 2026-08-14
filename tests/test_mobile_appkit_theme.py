import os
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://example:example@127.0.0.1:5432/example",
)

from alarm_mobile.app.main import INDEX_HTML as ALARM_HTML  # noqa: E402
from maintenance_mobile.app.main import INDEX_HTML as MAINTENANCE_HTML  # noqa: E402
from online_dashboard.app.main import (  # noqa: E402
    DASHBOARD_HTML,
    DETAIL_HTML,
    LOGIN_HTML,
    mobile_nav,
    money_delta,
    target_progress_text,
)


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
        assert "/appkit-assets/lilletorget-appkit.css?v=4" in html
        assert "/appkit-assets/lilletorget-appkit.js?v=5" in html
        assert 'class="appkit-mobile theme-light' in html


def test_mobile_apps_have_stable_bottom_navigation() -> None:
    assert 'class="appkit-footer maintenance-nav"' in MAINTENANCE_HTML
    assert 'class="appkit-footer bottom-nav"' in ALARM_HTML
    assert "{{ mobile_nav }}" in DASHBOARD_HTML
    assert "{{ mobile_nav }}" in DETAIL_HTML


def test_online_bottom_navigation_uses_area_colors_for_active_item() -> None:
    expected = {
        "sun": "nav-sun is-active",
        "parking": "nav-parking is-active",
        "energy": "nav-energy is-active",
        "drift": "nav-drift is-active",
    }
    for active, active_classes in expected.items():
        html = mobile_nav(active)
        assert active_classes in html
        assert 'nav-status is-primary"' in html
        assert "<span>Dashboard</span>" in html
        assert "<span>Status</span>" not in html

    css = (ROOT / "static" / "online-dashboard.css").read_text(encoding="utf-8")
    for selector in (".nav-sun.is-active", ".nav-parking.is-active", ".nav-energy.is-active", ".nav-drift.is-active"):
        assert selector in css
    for selector in (".nav-sun svg", ".nav-parking svg", ".nav-energy svg", ".nav-drift svg"):
        assert selector in css
    assert ".nav-status.is-primary.is-active" in css
    assert ".nav-status.is-primary:not(.is-active) svg" in css


def test_mobile_apps_use_appkit_dashboard_patterns() -> None:
    assert "appkit-glance maintenance-glance" in MAINTENANCE_HTML
    assert "is-active is-primary" in MAINTENANCE_HTML
    assert "{{ dashboard_highlight }}" in DASHBOARD_HTML
    assert '<section class="metric-grid">' in DASHBOARD_HTML
    assert "appkit-content-title" in DASHBOARD_HTML
    assert 'href="/renhold"' in DASHBOARD_HTML
    assert "{{ robot_cards }}" in DASHBOARD_HTML


def test_online_detail_pages_use_the_fixed_header_as_the_only_title() -> None:
    assert '<div class="appkit-header-title">{{ title }}' in DETAIL_HTML
    assert '<span class="appkit-header-subtitle">Lilletorget</span>' in DETAIL_HTML
    assert '<section class="detail-hero">' not in DETAIL_HTML


def test_online_dashboard_uses_the_fixed_header_as_the_only_title() -> None:
    assert '<div class="appkit-header-title">Dashboard' in DASHBOARD_HTML
    assert '<span class="appkit-header-subtitle">{{ open_label }} · {{ open_detail }}</span>' in DASHBOARD_HTML
    assert "dashboard-page-title" not in DASHBOARD_HTML
    assert "dashboard-glance" not in DASHBOARD_HTML
    assert "Driftsoversikt" not in DASHBOARD_HTML


def test_online_pages_offer_a_persistent_light_dark_theme_toggle() -> None:
    for html in (DASHBOARD_HTML, DETAIL_HTML):
        assert 'class="appkit-header-action appkit-theme-button"' in html
        assert "data-toggle-theme" in html
        assert 'class="theme-dark-icon"' in html
        assert 'class="theme-light-icon"' in html

    script = (ROOT / "packages" / "mobile-appkit" / "lilletorget-appkit.js").read_text(encoding="utf-8")
    assert 'const storageKey = "lilletorget-mobile-theme"' in script
    assert 'body.classList.remove("theme-dark", "theme-light")' in script
    assert 'node.setAttribute("aria-label", actionLabel)' in script

    css = (ROOT / "static" / "online-dashboard.css").read_text(encoding="utf-8")
    assert ':root[data-theme="dark"] body.appkit-mobile .dashboard-performance-comparisons > a' in css


def test_online_dark_theme_has_dedicated_surfaces_navigation_and_brand_assets() -> None:
    static_root = ROOT / "static"
    assert (static_root / "lilletorget-mark-dark.svg").is_file()
    assert (static_root / "lilletorget-wordmark-dark.svg").is_file()
    assert "lilletorget-mark-dark.svg?v=1694" in DASHBOARD_HTML
    assert "lilletorget-mark-dark.svg?v=1694" in DETAIL_HTML
    assert "lilletorget-wordmark-dark.svg?v=1694" in LOGIN_HTML

    shared_css = (ROOT / "packages" / "mobile-appkit" / "lilletorget-appkit.css").read_text(encoding="utf-8")
    assert "--appkit-page: #0f151b" in shared_css
    assert "--appkit-surface: #18212a" in shared_css
    assert "--appkit-line: #374552" in shared_css
    assert "--appkit-muted: #b1bdc9" in shared_css

    css = (static_root / "online-dashboard.css").read_text(encoding="utf-8")
    for selector in (
        ':root[data-theme="dark"] body.appkit-mobile .dashboard-performance',
        ':root[data-theme="dark"] body.appkit-mobile .detail-performance-parking',
        ':root[data-theme="dark"] body.appkit-mobile .detail-performance-sun',
        ':root[data-theme="dark"] body.appkit-mobile .detail-performance-energy',
        ':root[data-theme="dark"] body.appkit-mobile .detail-performance-drift',
        ':root[data-theme="dark"] body.appkit-mobile .appkit-footer .nav-status.is-primary:not(.is-active) svg',
    ):
        assert selector in css
    assert "border-top: 3px solid var(--appkit-revenue)" in css
    assert ':root[data-theme="dark"] body.appkit-mobile .notice' in css
    assert ':root[data-theme="dark"] body.appkit-mobile .door-mini-card' in css
    assert ':root[data-theme="dark"] body.appkit-mobile .other-door-card' in css
    assert ':root[data-theme="dark"] body.appkit-mobile .door-control-row' in css
    assert '.door-mini-card.is-solrom.is-open' in css
    assert '.door-mini-card.is-solrom.is-closed' in css
    assert "border-left-color: var(--appkit-energy)" in css
    assert "border-left-color: var(--appkit-revenue)" in css
    assert "background: var(--appkit-surface-soft)" in css


def test_dashboard_performance_helpers_show_direction_and_full_day_target() -> None:
    assert money_delta(11_840, 10_920) == ("+920 kr", "+8%", "is-positive")
    assert money_delta(11_840, 12_480) == ("-640 kr", "-5%", "is-negative")
    assert target_progress_text(11_840, 13_600, "hele gårsdagen") == "1 760 kr igjen til hele gårsdagen"
    assert target_progress_text(14_100, 13_600, "hele gårsdagen") == "500 kr over hele gårsdagen"


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


def test_shared_theme_keeps_small_mobile_text_readable() -> None:
    source = (ROOT / "packages" / "mobile-appkit" / "lilletorget-appkit.css").read_text(encoding="utf-8")
    assert "--appkit-muted: #65717d" in source
    assert "--appkit-muted: #b1bdc9" in source
    assert ".appkit-footer a," in source
    assert "font-size: 0.71rem" in source
    assert "font-size: 0.72rem" in source
