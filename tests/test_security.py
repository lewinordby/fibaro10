import unittest

from security import apply_security_headers, security_headers


class SecurityHeaderTests(unittest.TestCase):
    def test_default_headers_include_browser_hardening(self) -> None:
        headers = security_headers()

        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("camera=()", headers["Permissions-Policy"])
        self.assertNotIn("Strict-Transport-Security", headers)

    def test_hsts_is_explicitly_opt_in(self) -> None:
        headers = security_headers(hsts_enabled=True, hsts_max_age_seconds=60)

        self.assertEqual(headers["Strict-Transport-Security"], "max-age=60; includeSubDomains")

    def test_apply_security_headers_preserves_existing_values(self) -> None:
        headers = {"X-Frame-Options": "DENY"}

        apply_security_headers(headers)

        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")


if __name__ == "__main__":
    unittest.main()
