from datetime import datetime
from urllib.parse import parse_qs, urlparse
import unittest

import main


class UnifiProtectLinkTests(unittest.TestCase):
    def test_parking_timelapse_url_uses_expected_window(self):
        target = datetime(2026, 6, 22, 16, 15, 12, 520000)

        url = main.unifi_protect_parking_timelapse_url(target)

        self.assertIsNotNone(url)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        target_ms = int(target.replace(tzinfo=main.LOCAL_TZ).timestamp() * 1000)
        self.assertIn(main.UNIFI_PROTECT_PARKING_CAMERA_ID, parsed.path)
        self.assertEqual(int(params["start"][0]), target_ms - 120_000)
        self.assertEqual(int(params["time"][0]), target_ms - 120_000)
        self.assertEqual(int(params["end"][0]), target_ms + 300_000)

    def test_parking_timelapse_url_can_use_one_minute_before(self):
        target = datetime(2026, 6, 22, 16, 15, 12, 520000)

        url = main.unifi_protect_parking_timelapse_url(target, before_seconds=60)

        self.assertIsNotNone(url)
        params = parse_qs(urlparse(url).query)
        target_ms = int(target.replace(tzinfo=main.LOCAL_TZ).timestamp() * 1000)
        self.assertEqual(int(params["start"][0]), target_ms - 60_000)
        self.assertEqual(int(params["time"][0]), target_ms - 60_000)
        self.assertEqual(int(params["end"][0]), target_ms + 300_000)

    def test_parking_timelapse_url_can_use_fifteen_seconds_before(self):
        target = datetime(2026, 6, 22, 16, 15, 12, 520000)

        url = main.unifi_protect_parking_timelapse_url(target, before_seconds=15)

        self.assertIsNotNone(url)
        params = parse_qs(urlparse(url).query)
        target_ms = int(target.replace(tzinfo=main.LOCAL_TZ).timestamp() * 1000)
        self.assertEqual(int(params["start"][0]), target_ms - 15_000)
        self.assertEqual(int(params["time"][0]), target_ms - 15_000)
        self.assertEqual(int(params["end"][0]), target_ms + 300_000)


if __name__ == "__main__":
    unittest.main()
