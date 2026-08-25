import unittest
from datetime import date, datetime, timezone
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
    known_vehicle_report,
    known_vehicle_stays_report,
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


class _RowsPool:
    def __init__(self, rows):
        self.rows = rows
        self.arguments = ()
        self.query = ""

    async def fetch(self, query, *arguments):
        self.query = query
        self.arguments = arguments
        return self.rows


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

    async def test_daily_plate_summary_keeps_timestamps_but_not_full_rollup(self):
        pool = _SearchPool()
        from_at = datetime(2026, 7, 21, 0, 0, tzinfo=timezone.utc)
        to_at = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc)

        await daily_license_plates(
            pool,
            "console",
            from_at=from_at,
            to_at=to_at,
            include_detections=False,
        )

        self.assertEqual(pool.arguments, ("console", from_at, to_at))
        self.assertIn("AS detection_times", pool.query)
        self.assertIn("first_recognition_id", pool.query)
        self.assertNotIn("detection_rollup AS", pool.query)

    async def test_daily_plate_detail_can_be_bounded_to_one_plate(self):
        pool = _SearchPool()
        from_at = datetime(2026, 7, 21, 0, 0, tzinfo=timezone.utc)
        to_at = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc)

        await daily_license_plates(
            pool,
            "console",
            from_at=from_at,
            to_at=to_at,
            plate=" ab 12345 ",
        )

        self.assertEqual(pool.arguments, ("console", from_at, to_at, "AB12345"))
        self.assertIn("r.normalized_value = $4", pool.query)

    async def test_known_vehicle_report_deduplicates_and_groups_visits(self):
        rows = [
            {
                "recognition_id": 1,
                "value": "Park Nordic",
                "normalized_value": "PARKNORDIC",
                "camera_id": "north",
                "camera_name": "Butikk nord",
                "source_event_id": "event-1",
                "occurred_at": datetime(2026, 8, 4, 7, 0, tzinfo=timezone.utc),
            },
            {
                "recognition_id": 2,
                "value": "Park Nordic",
                "normalized_value": "PARKNORDIC",
                "camera_id": "north",
                "camera_name": "Butikk nord",
                "source_event_id": "event-1",
                "occurred_at": datetime(2026, 8, 4, 7, 0, tzinfo=timezone.utc),
            },
            {
                "recognition_id": 3,
                "value": "Park Nordic",
                "normalized_value": "PARKNORDIC",
                "camera_id": "front",
                "camera_name": "Butikk front",
                "source_event_id": "event-2",
                "occurred_at": datetime(2026, 8, 4, 7, 30, tzinfo=timezone.utc),
            },
            {
                "recognition_id": 4,
                "value": "Park Nordic",
                "normalized_value": "PARKNORDIC",
                "camera_id": "front",
                "camera_name": "Butikk front",
                "source_event_id": "event-3",
                "occurred_at": datetime(2026, 8, 4, 8, 30, tzinfo=timezone.utc),
            },
            {
                "recognition_id": 5,
                "value": "Park Nordic",
                "normalized_value": "PARKNORDIC",
                "camera_id": "front",
                "camera_name": "Butikk front",
                "source_event_id": "event-4",
                "occurred_at": datetime(2026, 8, 5, 8, 0, tzinfo=timezone.utc),
            },
            {
                "recognition_id": 6,
                "value": "Park Nordic",
                "normalized_value": "PARKNORDIC",
                "camera_id": "north",
                "camera_name": "Butikk nord",
                "source_event_id": "event-5",
                "occurred_at": datetime(2026, 8, 5, 8, 0, tzinfo=timezone.utc),
            },
        ]
        pool = _RowsPool(rows)

        report = await known_vehicle_report(
            pool,
            "console",
            identity="Park Nordic",
            from_at=datetime(2026, 7, 31, 22, 0, tzinfo=timezone.utc),
            to_at=datetime(2026, 8, 31, 22, 0, tzinfo=timezone.utc),
            gap_minutes=60,
        )

        self.assertEqual(pool.arguments[1], "PARKNORDIC")
        self.assertEqual(report["summary"]["observation_count"], 5)
        self.assertEqual(report["summary"]["visit_count"], 3)
        self.assertEqual(report["summary"]["active_days"], 2)
        august_fourth = next(day for day in report["days"] if day["date"] == "2026-08-04")
        self.assertEqual(august_fourth["visit_count"], 2)
        self.assertEqual(august_fourth["visits"][0]["duration_minutes"], 30.0)
        self.assertEqual(august_fourth["visits"][0]["observation_count"], 2)
        self.assertIn("Butikk nord", august_fourth["visits"][0]["camera_names"])
        self.assertEqual(len(august_fourth["visits"][0]["observations"]), 2)
        self.assertEqual(august_fourth["visits"][0]["observations"][0]["recognition_id"], 1)
        august_fifth = next(day for day in report["days"] if day["date"] == "2026-08-05")
        self.assertEqual(august_fifth["visits"][0]["observation_count"], 2)
        self.assertTrue(august_fifth["visits"][0]["is_single_observation"])

    async def test_known_vehicle_stays_report_groups_daily_known_vehicles(self):
        pool = _RowsPool(
            [
                {
                    "local_date": date(2026, 8, 25),
                    "identity": "LEWIBIL",
                    "display_name": "Lewi bil",
                    "first_observed_at": datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc),
                    "last_observed_at": datetime(2026, 8, 25, 8, 25, tzinfo=timezone.utc),
                    "duration_minutes": 25.0,
                    "observation_count": 4,
                    "camera_names": ["Butikk front", "Butikk nord"],
                },
                {
                    "local_date": date(2026, 8, 24),
                    "identity": "LEWIBIL",
                    "display_name": "Lewi bil",
                    "first_observed_at": datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc),
                    "last_observed_at": datetime(2026, 8, 24, 10, 15, tzinfo=timezone.utc),
                    "duration_minutes": 15.0,
                    "observation_count": 2,
                    "camera_names": ["Butikk front"],
                },
            ]
        )

        report = await known_vehicle_stays_report(
            pool,
            "console",
            from_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            to_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            min_duration_minutes=10,
        )

        self.assertIn("r.is_known IS TRUE", pool.query)
        self.assertIn("upper(r.normalized_value) <> 'PARKNORDIC'", pool.query)
        self.assertIn("HAVING max(occurred_at) - min(occurred_at) >", pool.query)
        self.assertEqual(pool.arguments[4], 10)
        self.assertEqual(report["summary"]["vehicle_day_count"], 2)
        self.assertEqual(report["summary"]["unique_vehicle_count"], 1)
        self.assertEqual(report["summary"]["observation_count"], 6)
        self.assertEqual(report["days"][0]["date"], "2026-08-25")
        self.assertEqual(report["days"][0]["vehicles"][0]["duration_minutes"], 25.0)


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
