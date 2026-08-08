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
        assert "/appkit-assets/lilletorget-appkit.css?v=1" in html
        assert "/appkit-assets/lilletorget-appkit.js?v=1" in html
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
