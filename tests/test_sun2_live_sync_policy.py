import sys
import types
from datetime import timedelta

try:
    import playwright.sync_api  # noqa: F401
except ModuleNotFoundError:
    playwright_module = types.ModuleType("playwright")
    sync_api_module = types.ModuleType("playwright.sync_api")

    class PlaywrightTimeoutError(Exception):
        pass

    sync_api_module.TimeoutError = PlaywrightTimeoutError
    sync_api_module.sync_playwright = lambda: None
    playwright_module.sync_api = sync_api_module
    sys.modules["playwright"] = playwright_module
    sys.modules["playwright.sync_api"] = sync_api_module

from sun2_session_scraper.app import main as scraper


def test_today_sync_rate_limit_uses_last_attempt_even_after_failure():
    now = scraper.local_now()
    original = dict(scraper.state)
    try:
        scraper.state["today_sync_last_attempt_at"] = (now - timedelta(seconds=61)).isoformat()
        assert scraper.today_sync_retry_after_seconds(now) == scraper.LIVE_SYNC_MIN_INTERVAL_SECONDS - 61
    finally:
        scraper.state.clear()
        scraper.state.update(original)


def test_today_sync_is_available_after_minimum_interval():
    now = scraper.local_now()
    original = dict(scraper.state)
    try:
        scraper.state["today_sync_last_attempt_at"] = (
            now - timedelta(seconds=scraper.LIVE_SYNC_MIN_INTERVAL_SECONDS)
        ).isoformat()
        assert scraper.today_sync_retry_after_seconds(now) == 0
    finally:
        scraper.state.clear()
        scraper.state.update(original)
