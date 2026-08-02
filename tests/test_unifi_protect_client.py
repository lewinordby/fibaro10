import json
import unittest
from unittest.mock import patch

from unifi_protect_client import ProtectLedgerClient


class _Headers:
    def get_content_type(self):
        return "application/json"


class _Response:
    headers = _Headers()

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ProtectLedgerClientTests(unittest.TestCase):
    @patch("unifi_protect_client.urlopen")
    def test_status_uses_local_url_and_bearer_token(self, urlopen):
        urlopen.return_value = _Response({"status": "ok", "local_only": True})
        client = ProtectLedgerClient("http://unifi_protect_events:8130/", "secret")

        payload = client.status()

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://unifi_protect_events:8130/api/v1/status")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        self.assertTrue(payload["local_only"])

    @patch("unifi_protect_client.urlopen")
    def test_event_filters_are_encoded(self, urlopen):
        urlopen.return_value = _Response({"items": []})
        client = ProtectLedgerClient("http://ledger:8130", "secret")

        client.events(camera_id="camera 1", has_snapshot=False, limit=25)

        request = urlopen.call_args.args[0]
        self.assertIn("camera_id=camera+1", request.full_url)
        self.assertIn("has_snapshot=False", request.full_url)
        self.assertIn("limit=25", request.full_url)

    @patch("unifi_protect_client.urlopen")
    def test_stats_capabilities_and_recognition_detail_use_versioned_api(self, urlopen):
        urlopen.return_value = _Response({"items": []})
        client = ProtectLedgerClient("http://ledger:8130", "secret")

        client.capabilities()
        self.assertEqual(urlopen.call_args.args[0].full_url, "http://ledger:8130/api/v1/capabilities")
        client.stats()
        self.assertEqual(urlopen.call_args.args[0].full_url, "http://ledger:8130/api/v1/stats")
        client.recognition_detail(42)
        self.assertEqual(urlopen.call_args.args[0].full_url, "http://ledger:8130/api/v1/recognitions/42")
        client.recognition_snapshot(42)
        self.assertEqual(
            urlopen.call_args.args[0].full_url,
            "http://ledger:8130/api/v1/recognitions/42/snapshot",
        )

    @patch("unifi_protect_client.urlopen")
    def test_daily_license_plates_uses_aggregate_endpoint(self, urlopen):
        urlopen.return_value = _Response({"items": []})
        client = ProtectLedgerClient("http://ledger:8130", "secret")

        client.daily_license_plates(**{"from": "2026-07-21T00:00:00+02:00", "to": "2026-07-22T00:00:00+02:00"})

        request = urlopen.call_args.args[0]
        self.assertIn("/api/v1/license-plates/daily?", request.full_url)
        self.assertIn("from=2026-07-21T00%3A00%3A00%2B02%3A00", request.full_url)

    @patch("unifi_protect_client.urlopen")
    def test_bollards_and_evidence_use_versioned_api(self, urlopen):
        urlopen.return_value = _Response({"regions": [], "incidents": []})
        client = ProtectLedgerClient("http://ledger:8130", "secret")

        client.bollards()
        self.assertEqual(urlopen.call_args.args[0].full_url, "http://ledger:8130/api/v1/bollards")
        client.bollard_region_baseline(9)
        self.assertEqual(
            urlopen.call_args.args[0].full_url,
            "http://ledger:8130/api/v1/bollards/regions/9/baseline",
        )
        client.bollard_camera_image("camera 1", "overlay")
        self.assertEqual(
            urlopen.call_args.args[0].full_url,
            "http://ledger:8130/api/v1/bollards/cameras/camera%201/overlay",
        )
        client.bollard_camera_image("camera 1", "ai")
        self.assertEqual(
            urlopen.call_args.args[0].full_url,
            "http://ledger:8130/api/v1/bollards/cameras/camera%201/ai",
        )
        client.bollard_camera_crop("camera 1", "latest")
        self.assertEqual(
            urlopen.call_args.args[0].full_url,
            "http://ledger:8130/api/v1/bollards/cameras/camera%201/latest/crop",
        )
        client.bollard_asset_image("trapp-solstudio", "ai")
        self.assertEqual(
            urlopen.call_args.args[0].full_url,
            "http://ledger:8130/api/v1/bollards/assets/trapp-solstudio/ai",
        )
        client.bollard_incident_image(12, "camera 1", "after")
        self.assertEqual(
            urlopen.call_args.args[0].full_url,
            "http://ledger:8130/api/v1/bollards/incidents/12/images/camera%201/after",
        )


if __name__ == "__main__":
    unittest.main()
