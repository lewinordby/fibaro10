import unittest
from urllib.parse import urlencode

from starlette.requests import Request

from maintenance_mobile.app.main import (
    INDEX_HTML,
    SESSION_COOKIE_NAME,
    login_view,
    make_session_token,
    mobile_bollard_camera_payload,
    notifications_page,
)


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


class NotificationsPageTests(unittest.IsolatedAsyncioTestCase):
    async def test_direct_link_preserves_destination_through_login(self):
        response = await notifications_page(request_for("/varsler"))

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/auth/login?next=/varsler")

        login = await login_view(request_for("/auth/login", query={"next": "/varsler"}))
        self.assertIn('action="/auth/login?next=/varsler"', login.body.decode("utf-8"))

    async def test_authenticated_user_sees_visible_subscription_entry_and_page(self):
        token = make_session_token("test", "test-password")
        cookie = f"{SESSION_COOKIE_NAME}={token}"

        notification_page = await notifications_page(request_for("/varsler", cookie=cookie))
        html = notification_page.body.decode("utf-8")

        self.assertIn('class="notification-entry" href="/varsler"', INDEX_HTML)
        self.assertEqual(notification_page.status_code, 200)
        self.assertIn('id="notificationsScreen"', html)
        self.assertIn("maintenance-mobile.js?v=1465", html)
        self.assertIn("har opptakstid på hver sin side av skyveren", html)

    def test_camera_payload_exposes_only_authenticated_mobile_proxy_urls(self):
        payload = mobile_bollard_camera_payload(
            {
                "comparison_mode": "full_frame_overlay",
                "camera_monitors": [
                    {
                        "camera_id": "6a35149c002cef03e4018be0",
                        "camera_name": "G6 Butikk Front",
                        "status": "normal",
                        "latest_captured_at": "2026-07-22T06:47:00Z",
                        "baseline_captured_at": "2026-07-21T17:27:59Z",
                        "latest_url": "/api/unifi-protect/bollards/cameras/camera/one/latest",
                        "overlay_url": "/api/unifi-protect/bollards/cameras/camera/one/overlay",
                        "baseline_url": "/api/unifi-protect/bollards/cameras/camera/one/baseline",
                        "display_crop": {"x": 0, "y": 1123, "width": 2803, "height": 1037},
                        "latest_path": "/private/latest.jpg",
                        "context": {"plates": ["AB12345"]},
                    }
                ],
                "asset_monitors": [
                    {
                        "monitor_id": "asset:trapp-solstudio",
                        "asset_key": "trapp-solstudio",
                        "item_type": "stairs",
                        "display_name": "Trapp ved Solstudio",
                        "camera_id": "6a219d5e00513a03e4066cba",
                        "camera_name": "G6 Solstudio Front",
                        "status": "normal",
                        "latest_captured_at": "2026-07-22T06:47:00Z",
                        "baseline_captured_at": "2026-07-21T17:27:59Z",
                        "latest_url": "/api/unifi-protect/bollards/assets/trapp-solstudio/latest",
                        "overlay_url": "/api/unifi-protect/bollards/assets/trapp-solstudio/overlay",
                        "baseline_url": "/api/unifi-protect/bollards/assets/trapp-solstudio/baseline",
                        "display_crop": {"x": 2200, "y": 400, "width": 1640, "height": 1760},
                    }
                ],
            },
            cropped=True,
        )

        self.assertEqual(payload["comparisonMode"], "full_frame_overlay")
        self.assertEqual(len(payload["items"]), 2)
        item = payload["items"][0]
        self.assertEqual(item["cameraName"], "G6 Butikk Front")
        self.assertIn("/api/bollards/cameras/6a35149c002cef03e4018be0/overlay/crop", item["images"]["overlay"])
        self.assertEqual(
            item["crop"],
            {"x": 0, "y": 1123, "width": 2803, "height": 1037, "aspectRatio": 2.703},
        )
        self.assertNotIn("latest_path", item)
        self.assertNotIn("context", item)
        self.assertNotIn("AB12345", str(payload))
        stairs = payload["items"][1]
        self.assertEqual(stairs["cameraName"], "Trapp ved Solstudio")
        self.assertEqual(stairs["itemType"], "stairs")
        self.assertIn(
            "/api/bollards/assets/trapp-solstudio/overlay",
            stairs["images"]["overlay"],
        )


if __name__ == "__main__":
    unittest.main()
