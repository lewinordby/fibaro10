import unittest
from urllib.parse import urlencode
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from starlette.requests import Request

from alarm_mobile.app.main import (
    INDEX_HTML,
    SESSION_COOKIE_NAME,
    login_view,
    monitor_payload,
    safe_next_path,
)


def request_for(path: str, *, query: dict[str, str] | None = None, cookie: str = "") -> Request:
    headers = [(b"host", b"alarm.lilletorget.net")]
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
            "server": ("alarm.lilletorget.net", 443),
        }
    )


class AlarmMobileTests(unittest.IsolatedAsyncioTestCase):
    def test_safe_next_path_accepts_alarm_deep_link_only_on_same_host(self):
        self.assertEqual(
            safe_next_path("/?section=dorer&alarm=42"),
            "/?section=dorer&alarm=42",
        )
        self.assertEqual(safe_next_path("https://example.com/"), "/")
        self.assertEqual(safe_next_path("//example.com/"), "/")

    async def test_valid_session_preserves_deep_link(self):
        token = "valid-opaque-session"
        cookie = f"{SESSION_COOKIE_NAME}={token}"
        destination = "/?section=pullerter&incident=17"
        with patch(
            "alarm_mobile.app.main.fibaro_request",
            new=AsyncMock(return_value={"username": "test"}),
        ):
            response = await login_view(
                request_for("/auth/login", query={"next": destination}, cookie=cookie)
            )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], destination)

    async def test_stale_session_is_deleted(self):
        token = "stale-opaque-session"
        cookie = f"{SESSION_COOKIE_NAME}={token}"
        with patch(
            "alarm_mobile.app.main.fibaro_request",
            new=AsyncMock(side_effect=HTTPException(status_code=401, detail="Ugyldig")),
        ):
            response = await login_view(request_for("/auth/login", cookie=cookie))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_camera_payload_contains_only_mobile_proxy_urls(self):
        result = monitor_payload(
            {
                "camera_monitors": [
                    {
                        "camera_id": "camera-1",
                        "asset_key": "test-felt",
                        "camera_name": "G6 Butikk Front",
                        "status": "normal",
                        "latest_url": "/private/latest",
                        "baseline_url": "/private/baseline",
                        "display_crop": {"width": 1600, "height": 900},
                        "context": {"plates": ["AB12345"]},
                    }
                ]
            }
        )
        self.assertEqual(len(result), 1)
        self.assertIn("/api/bollards/cameras/camera-1/latest/crop", result[0]["images"]["latest"])
        self.assertEqual(result[0]["assetKey"], "test-felt")
        self.assertNotIn("context", result[0])
        self.assertNotIn("AB12345", str(result))

    def test_shell_has_all_alarm_views(self):
        self.assertIn('id="overviewView"', INDEX_HTML)
        self.assertIn('id="doorsView"', INDEX_HTML)
        self.assertIn('id="bollardsView"', INDEX_HTML)
        self.assertIn('id="bollardDetailView"', INDEX_HTML)
        self.assertIn("alarm-mobile.js?v=7", INDEX_HTML)
        self.assertIn("/appkit-assets/lilletorget-appkit.css?v=3", INDEX_HTML)
        self.assertIn('class="appkit-footer bottom-nav"', INDEX_HTML)


if __name__ == "__main__":
    unittest.main()
