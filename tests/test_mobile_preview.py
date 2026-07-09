import unittest
import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

import main


def request_with_role(*, can_settings: bool, is_master: bool = False):
    return SimpleNamespace(
        state=SimpleNamespace(
            auth_can_settings=can_settings,
            auth_is_master=is_master,
        )
    )


class MobilePreviewTests(unittest.TestCase):
    def test_viewer_does_not_receive_money_screens(self):
        screens = main.mobile_preview_screens_for_request(request_with_role(can_settings=False))
        keys = {screen["key"] for screen in screens}

        self.assertNotIn("omsetning", keys)
        self.assertNotIn("omsetning-uke", keys)
        self.assertIn("parkering", keys)
        self.assertIn("soling", keys)

    def test_settings_user_receives_money_screens(self):
        screens = main.mobile_preview_screens_for_request(request_with_role(can_settings=True))
        keys = {screen["key"] for screen in screens}

        self.assertIn("omsetning", keys)
        self.assertIn("omsetning-uke", keys)


if __name__ == "__main__":
    unittest.main()
