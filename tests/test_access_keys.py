import os
import unittest
from unittest.mock import AsyncMock, patch

from starlette.requests import Request

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

import main


class AccessKeyTests(unittest.TestCase):
    def test_master_password_uses_plain_password_hash(self) -> None:
        password = "secret-master"

        self.assertEqual(
            main.access_password_hash("master", password, is_master=True),
            main.hash_access_key(password),
        )
        self.assertEqual(main.access_key_prefix("master", password, is_master=True), "sun2_master")

    def test_regular_user_password_uses_username_and_password_hash(self) -> None:
        password = "secret-user"

        self.assertEqual(
            main.access_password_hash("user", password, is_master=False),
            main.credential_hash("user", password),
        )
        self.assertEqual(main.access_key_prefix("user", password, is_master=False), main.credential_prefix("user", password))

    def test_master_row_does_not_expose_plaintext_password(self) -> None:
        row = main.AccessKey(name="master", key_hash="hash", key_prefix="sun2_master", is_master=True, role="master")

        payload = main.api_access_key_row(row)

        self.assertNotIn("key_plaintext", payload)
        self.assertNotIn("password", payload)
        self.assertEqual(payload["password_status"], "Kan settes på nytt, kan ikke vises")

    def test_session_tokens_are_hashed_before_storage(self) -> None:
        self.assertEqual(len(main.hash_auth_session_token("opaque-session")), 64)
        self.assertNotEqual(main.hash_auth_session_token("opaque-session"), "opaque-session")


def form_request(
    path: str,
    body: bytes,
    *,
    host: str = "test",
    forwarded_host: str = "",
    forwarded_proto: str = "https",
    public_host: str = "",
    public_proto: str = "https",
) -> Request:
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    headers = [(b"content-type", b"application/x-www-form-urlencoded"), (b"host", host.encode("ascii"))]
    if forwarded_host:
        headers.extend(
            [
                (b"x-forwarded-host", forwarded_host.encode("ascii")),
                (b"x-forwarded-proto", forwarded_proto.encode("ascii")),
            ]
        )
    if public_host:
        headers.extend(
            [
                (b"x-lilletorget-public-host", public_host.encode("ascii")),
                (b"x-lilletorget-public-proto", public_proto.encode("ascii")),
            ]
        )
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 1234),
            "server": (host, 443),
        },
        receive,
    )


class BrowserSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_cookie_contains_only_opaque_session(self) -> None:
        access_key = main.AccessKey(id=7, name="test", key_hash="credential-hash", key_prefix="key_test", active=True)
        request = form_request("/auth/login", b"username=test&password=secret-value")
        with (
            patch("main.find_access_key", new=AsyncMock(return_value=access_key)),
            patch("main.create_auth_session", new=AsyncMock(return_value="opaque-session-token")),
            patch("main.log_access_attempt", new=AsyncMock()),
        ):
            response = await main.login_submit(request)

        cookies = "\n".join(value.decode("latin-1") for name, value in response.raw_headers if name.lower() == b"set-cookie")
        self.assertIn("lilletorget_session=opaque-session-token", cookies)
        self.assertNotIn("secret-value", cookies)
        self.assertNotIn("fibaro10_access_password=secret-value", cookies)
        session_cookie = next(line for line in cookies.splitlines() if "lilletorget_session=opaque-session-token" in line)
        self.assertNotIn("domain=", session_cookie.lower())

    async def test_login_cookie_is_shared_across_lilletorget_apps(self) -> None:
        access_key = main.AccessKey(id=7, name="test", key_hash="credential-hash", key_prefix="key_test", active=True)
        request = form_request(
            "/auth/login",
            b"username=test&password=secret-value",
            host="fibaro10",
            forwarded_host="fibaro10:8110",
            forwarded_proto="http",
            public_host="app.lilletorget.net",
        )
        with (
            patch("main.find_access_key", new=AsyncMock(return_value=access_key)),
            patch("main.create_auth_session", new=AsyncMock(return_value="shared-session-token")),
            patch("main.log_access_attempt", new=AsyncMock()),
        ):
            response = await main.login_submit(request)

        cookies = [value.decode("latin-1") for name, value in response.raw_headers if name.lower() == b"set-cookie"]
        session_cookie = next(value for value in cookies if "lilletorget_session=shared-session-token" in value)
        self.assertIn("domain=.lilletorget.net", session_cookie.lower())
        self.assertIn("httponly", session_cookie.lower())
        self.assertIn("secure", session_cookie.lower())
        self.assertIn("samesite=lax", session_cookie.lower())


if __name__ == "__main__":
    unittest.main()
