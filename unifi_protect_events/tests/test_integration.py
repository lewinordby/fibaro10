import unittest
from datetime import datetime, timezone
from starlette.requests import Request

from unifi_protect_events.app.integration import (
    add_plate_quality,
    decode_cursor,
    daily_license_plates,
    encode_cursor,
    normalize_recognition_value,
    parse_alarm_recognitions,
    payload_digest,
    list_recognitions,
    require_webhook,
    recognition_kind,
)
from unifi_protect_events.app.plate_validation import public_validation


class _SearchPool:
    def __init__(self):
        self.arguments = ()
        self.query = ""

    async def fetch(self, query, *arguments):
        self.query = query
        self.arguments = arguments
        return []


class RecognitionParserTests(unittest.TestCase):
    def test_parses_known_and_unknown_license_plates(self):
        meta, rows = parse_alarm_recognitions(
            {
                "timestamp": 1_721_234_567_890,
                "cameraId": "camera-1",
                "cameraName": "Parkering",
                "alarm": {
                    "name": "Alle skilt",
                    "triggers": [
                        {"key": "license_plate_known", "value": "AB 12345"},
                        {"key": "license_plate_unknown", "value": "ZZ-99887"},
                    ],
                },
            }
        )

        self.assertEqual(meta["camera_id"], "camera-1")
        self.assertEqual([row["normalized_value"] for row in rows], ["AB12345", "ZZ99887"])
        self.assertEqual([row["is_known"] for row in rows], [True, False])
        self.assertTrue(all(row["kind"] == "license_plate" for row in rows))

    def test_parses_face_mapping_value_and_iso_time(self):
        meta, rows = parse_alarm_recognitions(
            {
                "occurredAt": "2026-07-21T12:30:00Z",
                "eventLocalLink": "https://console/protect/timelapse/abc?event=123e4567-e89b-12d3-a456-426614174000",
                "triggers": [{"type": "face_known", "value": {"name": "Ola Nordmann"}}],
            }
        )

        self.assertEqual(meta["source_event_id"], "123e4567-e89b-12d3-a456-426614174000")
        self.assertEqual(rows[0]["kind"], "face")
        self.assertEqual(rows[0]["value"], "Ola Nordmann")
        self.assertEqual(rows[0]["normalized_value"], "ola nordmann")

    def test_prefers_named_face_group_from_protect_webhook(self):
        _, rows = parse_alarm_recognitions(
            {
                "alarm": {
                    "triggers": [
                        {
                            "key": "face_known",
                            "group": {"id": "face-id-1", "name": "Kari Nordmann"},
                            "value": "face-id-1",
                            "device": "camera-1",
                        }
                    ]
                }
            }
        )

        self.assertEqual(rows[0]["kind"], "face")
        self.assertTrue(rows[0]["is_known"])
        self.assertEqual(rows[0]["value"], "Kari Nordmann")
        self.assertEqual(rows[0]["normalized_value"], "kari nordmann")

    def test_ignores_non_recognition_triggers(self):
        _, rows = parse_alarm_recognitions({"triggers": [{"key": "motion", "value": "active"}]})
        self.assertEqual(rows, [])

    def test_trigger_device_is_preserved_for_camera_correlation(self):
        _, rows = parse_alarm_recognitions(
            {"alarm": {"triggers": [{"key": "license_plate_unknown", "device": "74:AC:B9:9F:4E:24", "value": "EV12345"}]}}
        )

        self.assertEqual(rows[0]["camera_id"], "74:AC:B9:9F:4E:24")

    def test_webhook_accepts_gateway_ip_or_query_token(self):
        gateway_request = Request(
            {"type": "http", "headers": [], "client": ("192.168.1.1", 1234), "query_string": b""}
        )
        token_request = Request(
            {"type": "http", "headers": [], "client": ("192.168.20.50", 1234), "query_string": b"token=secret"}
        )

        require_webhook(gateway_request, "secret", frozenset({"192.168.1.1"}))
        require_webhook(token_request, "secret", frozenset({"192.168.1.1"}))

    def test_recognition_helpers(self):
        self.assertEqual(recognition_kind("License Plate · Unknown"), "license_plate")
        self.assertEqual(recognition_kind("person_of_interest"), "person_of_interest")
        self.assertEqual(normalize_recognition_value("license_plate", " ev 12 345 "), "EV12345")
        self.assertEqual(payload_digest(b"payload"), payload_digest(b"payload"))

    def test_cursor_round_trip_and_invalid_cursor(self):
        timestamp = datetime(2026, 7, 21, 12, 30, tzinfo=timezone.utc)
        cursor = encode_cursor(timestamp, 42)
        decoded_at, identifier = decode_cursor(cursor)
        self.assertEqual(decoded_at, timestamp)
        self.assertEqual(identifier, "42")
        with self.assertRaises(ValueError):
            decode_cursor("not-a-cursor")


class RecognitionQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_plate_search_normalizes_spacing_without_losing_text_search(self):
        pool = _SearchPool()

        result = await list_recognitions(pool, "console", limit=25, value=" AB 12345 ")

        self.assertEqual(result["items"], [])
        self.assertIn("AB12345", pool.arguments)
        self.assertIn("ab 12345", pool.arguments)
        self.assertIn("regexp_replace", pool.query)
        self.assertIn("FAKE_MAC", pool.query)

    async def test_daily_plate_query_is_aggregated_and_bounded(self):
        pool = _SearchPool()
        from_at = datetime(2026, 7, 21, 0, 0, tzinfo=timezone.utc)
        to_at = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc)

        result = await daily_license_plates(pool, "console", from_at=from_at, to_at=to_at)

        self.assertEqual(result["summary"]["unique_plates"], 0)
        self.assertEqual(pool.arguments, ("console", from_at, to_at))
        self.assertIn("r.kind = 'license_plate'", pool.query)
        self.assertIn("AS unifi_score", pool.query)
        self.assertIn("'unifi_score', unifi_score", pool.query)
        self.assertIn("'snapshot_time_offset_ms', snapshot_time_offset_ms", pool.query)
        self.assertIn("/api/v1/recognitions/", pool.query)
        self.assertIn("GROUP BY normalized_value", pool.query)


class PlateQualityTests(unittest.TestCase):
    def test_registry_validation_payload_distinguishes_no_match_from_transient_error(self):
        not_found = public_validation(
            {
                "status": "not_found",
                "is_valid": False,
                "likely_misread": True,
                "sources": {"norway": {"outcome": "not_found"}},
            }
        )
        transient = public_validation(
            {
                "status": "error",
                "is_valid": None,
                "likely_misread": False,
                "error": "HTTP 503",
                "sources": {"norway": {"outcome": "transient_error"}},
            }
        )

        self.assertTrue(not_found["likely_misread"])
        self.assertFalse(transient["likely_misread"])
        self.assertIsNone(transient["is_valid"])

    def test_confirmed_plate_wins_over_nearby_ocr_variant(self):
        observed = datetime(2026, 7, 21, 12, 30, tzinfo=timezone.utc)
        items = [
            {
                "plate": "AB12345",
                "detection_count": 1,
                "known_in_protect": False,
                "average_unifi_score": 70,
                "validation": {"is_valid": True, "likely_misread": False},
                "detections": [{"occurred_at": observed, "camera_id": "camera-1"}],
            },
            {
                "plate": "AB12346",
                "detection_count": 3,
                "known_in_protect": False,
                "average_unifi_score": 95,
                "validation": {"is_valid": False, "likely_misread": True},
                "detections": [{"occurred_at": observed, "camera_id": "camera-1"}],
            },
        ]

        add_plate_quality(items)

        self.assertEqual(items[1]["likely_canonical_plate"], "AB12345")
        self.assertTrue(items[1]["is_likely_ocr_variant"])
        self.assertEqual(items[1]["presentation_status"], "likely_misread")

    def test_two_confirmed_nearby_plates_are_kept_separate(self):
        observed = datetime(2026, 7, 21, 12, 30, tzinfo=timezone.utc)
        items = [
            {
                "plate": plate,
                "detection_count": 1,
                "validation": {"is_valid": True, "likely_misread": False},
                "detections": [{"occurred_at": observed, "camera_id": "camera-1"}],
            }
            for plate in ("AB12345", "AB12346")
        ]

        add_plate_quality(items)

        self.assertFalse(items[0]["ocr_variant_candidates"])
        self.assertFalse(items[1]["ocr_variant_candidates"])
        self.assertEqual([item["presentation_status"] for item in items], ["valid", "valid"])

    def test_transient_registry_error_is_review_not_misread_even_when_variant_exists(self):
        observed = datetime(2026, 7, 21, 12, 30, tzinfo=timezone.utc)
        items = [
            {
                "plate": "AB12345",
                "detection_count": 2,
                "validation": {"is_valid": True, "likely_misread": False},
                "detections": [{"occurred_at": observed, "camera_id": "camera-1"}],
            },
            {
                "plate": "AB12346",
                "detection_count": 1,
                "validation": {"is_valid": None, "likely_misread": False},
                "detections": [{"occurred_at": observed, "camera_id": "camera-1"}],
            },
        ]

        add_plate_quality(items)

        self.assertTrue(items[1]["is_likely_ocr_variant"])
        self.assertFalse(items[1]["likely_misread"])
        self.assertTrue(items[1]["requires_review"])
        self.assertEqual(items[1]["presentation_status"], "pending_review")


if __name__ == "__main__":
    unittest.main()
