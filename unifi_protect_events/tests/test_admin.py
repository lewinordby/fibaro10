import unittest

from unifi_protect_events.app.admin import (
    PolicyCache,
    camera_capabilities,
    detection_reference,
    evaluate_policy,
    extract_detection_types,
)


def policy(**overrides):
    values = {
        "default_store_new_event_types": True,
        "retention_days": 365,
        "catalog_sample_limit_bytes": 65536,
        "snapshots_enabled": True,
        "snapshot_high_quality": False,
        "snapshot_max_bytes": 12582912,
        "cameras": {},
        "event_types": {},
        "detection_types": {},
    }
    values.update(overrides)
    return PolicyCache(**values)


class AdminPolicyTests(unittest.TestCase):
    def test_extract_detection_types_deduplicates_top_level_and_metadata(self):
        self.assertEqual(
            extract_detection_types(
                {
                    "smartDetectTypes": ["person", "face"],
                    "metadata": {"smartDetectType": "person"},
                }
            ),
            ("person", "face"),
        )

    def test_camera_capabilities_combines_supported_and_enabled_types(self):
        objects, audio = camera_capabilities(
            {
                "featureFlags": {
                    "smartDetectTypes": ["person", "vehicle"],
                    "smartDetectAudioTypes": ["alrmSmoke"],
                },
                "smartDetectSettings": {
                    "objectTypes": ["person"],
                    "audioTypes": ["alrmSpeak"],
                },
            }
        )
        self.assertEqual(objects, ("person", "vehicle"))
        self.assertEqual(audio, ("alrmSmoke", "alrmSpeak"))

    def test_policy_filters_camera_event_and_all_disabled_detection_types(self):
        event = {
            "camera_id": "camera-1",
            "event_type": "smartDetectZone",
            "smart_detect_types": ("person", "face"),
        }
        self.assertEqual(evaluate_policy(policy(cameras={"camera-1": False}), event)[1], "camera_disabled")
        self.assertEqual(evaluate_policy(policy(event_types={"smartDetectZone": False}), event)[1], "event_type_disabled")
        self.assertEqual(
            evaluate_policy(policy(detection_types={"person": False, "face": False}), event)[1],
            "detection_types_disabled",
        )
        self.assertTrue(evaluate_policy(policy(detection_types={"person": False, "face": True}), event)[0])

    def test_unknown_audio_detection_gets_a_readable_catalog_entry(self):
        display, category, description = detection_reference("alrmFuture")
        self.assertEqual(display, "Future")
        self.assertEqual(category, "Lyd")
        self.assertTrue(description)


if __name__ == "__main__":
    unittest.main()
