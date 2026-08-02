import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from unifi_protect_events.app.main import (
    ProtectEventCollector,
    Settings,
    asyncpg_dsn,
    csv_set,
    epoch_ms_to_datetime,
    normalize_event_message,
    normalize_nvr_url,
    recognition_capture_delay,
    recognition_snapshot_relative_path,
    snapshot_relative_path,
    versioned_bollard_payload,
    websocket_url,
    write_snapshot_atomic,
)


class ProtectEventCollectorTests(unittest.TestCase):
    def test_versioned_bollard_payload_rewrites_ai_heatmaps(self):
        payload = {
            "camera_monitors": [
                {"ai_heatmap_url": "/api/bollards/cameras/camera-1/ai"}
            ],
            "asset_monitors": [
                {"ai_heatmap_url": "/api/bollards/assets/trapp-solstudio/ai"}
            ],
        }

        result = versioned_bollard_payload(payload)

        self.assertEqual(
            result["camera_monitors"][0]["ai_heatmap_url"],
            "/api/v1/bollards/cameras/camera-1/ai",
        )
        self.assertEqual(
            result["asset_monitors"][0]["ai_heatmap_url"],
            "/api/v1/bollards/assets/trapp-solstudio/ai",
        )

    def test_normalize_nvr_url_and_websocket_url(self):
        base = normalize_nvr_url("192.168.1.1/")

        self.assertEqual(base, "https://192.168.1.1")
        self.assertEqual(
            websocket_url(base),
            "wss://192.168.1.1/proxy/protect/integration/v1/subscribe/events",
        )

    def test_normalize_nvr_url_rejects_path(self):
        with self.assertRaises(ValueError):
            normalize_nvr_url("https://192.168.1.1/proxy/protect")

    def test_asyncpg_dsn_accepts_existing_application_url(self):
        self.assertEqual(
            asyncpg_dsn("postgresql+asyncpg://app:secret@db:5432/fibaro10"),
            "postgresql://app:secret@db:5432/fibaro10",
        )

    def test_normalize_event_message_extracts_official_fields(self):
        event = normalize_event_message(
            {
                "type": "add",
                "item": {
                    "id": "event-123",
                    "modelKey": "event",
                    "type": "smartDetectZone",
                    "start": 1_721_234_567_890,
                    "end": None,
                    "device": "camera-1",
                    "smartDetectTypes": ["person", "face"],
                    "score": 87,
                },
            }
        )

        self.assertEqual(event["source_event_id"], "event-123")
        self.assertEqual(event["message_type"], "add")
        self.assertEqual(event["event_type"], "smartDetectZone")
        self.assertEqual(event["camera_id"], "camera-1")
        self.assertEqual(event["score"], 87.0)
        self.assertEqual(event["start_at"].tzinfo, timezone.utc)
        self.assertIsNone(event["end_at"])
        self.assertEqual(event["smart_detect_types"], ("person", "face"))

    def test_synthetic_id_is_stable(self):
        payload = {"type": "update", "item": {"type": "motion", "device": "camera-1"}}

        first = normalize_event_message(payload)
        second = normalize_event_message(payload)

        self.assertTrue(first["source_event_id"].startswith("synthetic:"))
        self.assertEqual(first["source_event_id"], second["source_event_id"])

    def test_filters(self):
        settings = Settings(
            nvr_url="https://192.168.1.1",
            api_key="secret",
            database_url="postgresql://app:secret@db/fibaro10",
            console_key="test",
            verify_ssl=False,
            camera_ids=frozenset({"camera-1"}),
            event_types=frozenset({"motion"}),
            reconnect_min_seconds=2,
            reconnect_max_seconds=60,
        )
        collector = ProtectEventCollector(settings)

        self.assertTrue(collector.should_store({"camera_id": "camera-1", "event_type": "Motion"}))
        self.assertFalse(collector.should_store({"camera_id": "camera-2", "event_type": "motion"}))
        self.assertFalse(collector.should_store({"camera_id": "camera-1", "event_type": "ring"}))

    def test_helpers_handle_invalid_values(self):
        self.assertEqual(
            csv_set(" motion, smartDetectZone, ", lower=True),
            frozenset({"motion", "smartdetectzone"}),
        )
        self.assertIsNone(epoch_ms_to_datetime("not-a-time"))

    def test_snapshot_path_is_stable_and_atomic_writer_stays_under_root(self):
        captured_at = epoch_ms_to_datetime(1_721_234_567_890)
        self.assertIsNotNone(captured_at)
        relative = snapshot_relative_path("console", "camera/1", "event:1", captured_at)
        self.assertEqual(relative.suffix, ".jpg")
        self.assertNotIn("camera/1", relative.as_posix())
        self.assertEqual(relative, snapshot_relative_path("console", "camera/1", "event:1", captured_at))
        with TemporaryDirectory() as directory:
            result = write_snapshot_atomic(Path(directory), relative, b"\xff\xd8test")
            self.assertEqual(result.read_bytes(), b"\xff\xd8test")
            self.assertFalse(any(path.suffix == ".part" for path in Path(directory).rglob("*")))

    def test_recognition_snapshot_path_is_scoped_to_recognition_and_camera(self):
        captured_at = datetime(2026, 7, 21, 18, 30, tzinfo=timezone.utc)
        first = recognition_snapshot_relative_path("console", "camera-1", 42, captured_at)
        second = recognition_snapshot_relative_path("console", "camera-1", 43, captured_at)

        self.assertNotEqual(first, second)
        self.assertIn("recognitions", first.parts)
        self.assertNotIn("camera-1", first.as_posix())

    def test_recognition_capture_delay_aligns_small_clock_skew_only(self):
        now = datetime(2026, 7, 21, 18, 30, tzinfo=timezone.utc)

        self.assertAlmostEqual(
            recognition_capture_delay(now + timedelta(seconds=1), now),
            0.8,
        )
        self.assertEqual(recognition_capture_delay(now - timedelta(seconds=1), now), 0.0)
        self.assertEqual(recognition_capture_delay(now + timedelta(seconds=10), now), 0.0)


if __name__ == "__main__":
    unittest.main()
