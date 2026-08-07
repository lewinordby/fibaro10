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


def form_request(path: str, body: bytes) -> Request:
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": [(b"content-type", b"application/x-www-form-urlencoded"), (b"host", b"test")],
            "client": ("127.0.0.1", 1234),
            "server": ("test", 443),
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
        self.assertIn("fibaro10_session=opaque-session-token", cookies)
        self.assertNotIn("secret-value", cookies)
        self.assertNotIn("fibaro10_access_password=secret-value", cookies)


if __name__ == "__main__":
    unittest.main()
