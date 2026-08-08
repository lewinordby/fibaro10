import unittest
from urllib.parse import urlencode
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from starlette.requests import Request

from maintenance_mobile.app.main import INDEX_HTML, SESSION_COOKIE_NAME, login_view


def request_for(path: str, *, query: dict[str, str] | None = None, cookie: str = "") -> Request:
    headers = [(b"host", b"vedl.lilletorget.net")]
    if cookie:
        headers.append((b"cookie", cookie.encode("ascii")))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": urlencode(query or {}).encode("ascii"),
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("vedl.lilletorget.net", 443),
        }
    )


class MaintenanceMobileTests(unittest.IsolatedAsyncioTestCase):
    async def test_stale_session_is_cleared_instead_of_redirecting_forever(self):
        token = "stale-opaque-session"
        cookie = f"{SESSION_COOKIE_NAME}={token}"

        with patch(
            "maintenance_mobile.app.main.fibaro_request",
            new=AsyncMock(side_effect=HTTPException(status_code=401, detail="Ugyldig bruker")),
        ):
            response = await login_view(request_for("/auth/login", cookie=cookie))

        self.assertEqual(response.status_code, 200)
        self.assertIn("Logg inn på nytt", response.body.decode("utf-8"))
        self.assertIn(SESSION_COOKIE_NAME, response.headers["set-cookie"])
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    async def test_valid_session_redirects_to_maintenance_home(self):
        token = "valid-opaque-session"
        cookie = f"{SESSION_COOKIE_NAME}={token}"

        with patch(
            "maintenance_mobile.app.main.fibaro_request",
            new=AsyncMock(return_value={"username": "test"}),
        ):
            response = await login_view(request_for("/auth/login", cookie=cookie))

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/")

    def test_alarm_features_are_not_embedded_in_maintenance_app(self):
        self.assertIn("Ny registrering", INDEX_HTML)
        self.assertIn("maintenance-mobile.js?v=1474", INDEX_HTML)
        self.assertIn("/appkit-assets/lilletorget-appkit.css?v=3", INDEX_HTML)
        self.assertIn('class="appkit-footer maintenance-nav"', INDEX_HTML)
        self.assertNotIn("notificationsScreen", INDEX_HTML)
        self.assertNotIn("Pullert- og trappevarsler", INDEX_HTML)

    def test_subviews_reuse_the_single_app_header(self):
        self.assertEqual(INDEX_HTML.count('class="appkit-header app-topbar"'), 1)
        self.assertNotIn('class="entry-head sub-topbar"', INDEX_HTML)
        self.assertIn('id="appHeaderTitle"', INDEX_HTML)
        self.assertIn('class="entry-context"', INDEX_HTML)

    def test_history_and_detail_tools_are_available(self):
        self.assertIn('id="detailScreen"', INDEX_HTML)
        self.assertIn('id="historySearch"', INDEX_HTML)
        self.assertIn('data-history-filter="follow-up"', INDEX_HTML)
        self.assertIn('id="historyMoreButton"', INDEX_HTML)
        self.assertIn('id="submitNextButton"', INDEX_HTML)


if __name__ == "__main__":
    unittest.main()
