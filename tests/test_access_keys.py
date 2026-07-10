import os
import unittest

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


if __name__ == "__main__":
    unittest.main()
