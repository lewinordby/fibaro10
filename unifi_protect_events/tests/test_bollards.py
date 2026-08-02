import unittest

import cv2
import numpy as np

from app.bollards import (
    BOLLARD_CAMERA_DISPLAY_CROPS,
    BOLLARD_CAMERA_ANALYSIS_ZONES,
    FIXED_STRUCTURE_MONITORS,
    TARGET_CAMERA_NAMES,
    bollard_notification_message,
    compare_bollard_region,
    compare_bollard_zones,
    compare_full_scene,
    fixed_pixel_crop,
    normalize_fixed_camera_frame,
    normalized_bollard_key,
    normalized_roi,
)


def _scene(object_x: int = 130) -> np.ndarray:
    image = np.full((240, 360, 3), 205, dtype=np.uint8)
    cv2.line(image, (0, 190), (359, 190), (70, 70, 70), 4)
    cv2.rectangle(image, (object_x, 75), (object_x + 34, 190), (32, 42, 38), -1)
    cv2.rectangle(image, (object_x + 5, 82), (object_x + 29, 176), (215, 185, 45), 4)
    cv2.circle(image, (object_x + 17, 105), 8, (245, 245, 245), 2)
    cv2.line(image, (object_x + 7, 145), (object_x + 27, 145), (245, 245, 245), 3)
    return image


def stabilized_test_scene(object_x: int = 130) -> np.ndarray:
    image = _scene(object_x)
    for y in range(20, 220, 35):
        for x in range(20, 340, 45):
            if not (110 < x < 230 and 55 < y < 205):
                cv2.circle(image, (x, y), 4, (40, 90, 150), -1)
    return image


class BollardHelpersTests(unittest.TestCase):
    def test_hybrid_status_keeps_classical_monitoring_independent(self):
        from app.bollards import BollardService

        self.assertEqual(BollardService._hybrid_status("normal", "normal", False), "normal")
        self.assertEqual(
            BollardService._hybrid_status("changed", "anomaly", True), "corroborated"
        )
        self.assertEqual(
            BollardService._hybrid_status("normal", "anomaly", True), "ai_review"
        )
        self.assertEqual(
            BollardService._hybrid_status("changed", "error", None), "classical_review"
        )

    def test_ready_ai_must_corroborate_an_incident(self):
        from app.bollards import BollardService

        self.assertFalse(
            BollardService._incident_candidate(
                {"state": "changed", "ai_status": "normal", "ai_is_anomaly": False}
            )
        )
        self.assertTrue(
            BollardService._incident_candidate(
                {"state": "changed", "ai_status": "anomaly", "ai_is_anomaly": True}
            )
        )
        self.assertTrue(
            BollardService._incident_candidate(
                {"state": "changed", "ai_status": "error", "ai_is_anomaly": None}
            )
        )
        self.assertTrue(
            BollardService._effectively_normal(
                {"state": "changed", "ai_status": "normal", "ai_is_anomaly": False}
            )
        )

    def test_display_crop_preserves_exact_source_pixels(self):
        image = np.arange(24 * 32 * 3, dtype=np.uint16).reshape((24, 32, 3))
        crop = {"x": 7, "y": 5, "width": 11, "height": 13}

        result = fixed_pixel_crop(image, crop)

        self.assertEqual(result.shape, (13, 11, 3))
        np.testing.assert_array_equal(result, image[5:18, 7:18])

    def test_every_target_camera_has_one_absolute_display_crop(self):
        self.assertEqual(set(BOLLARD_CAMERA_DISPLAY_CROPS), set(TARGET_CAMERA_NAMES))
        for crop in BOLLARD_CAMERA_DISPLAY_CROPS.values():
            self.assertTrue(all(isinstance(value, int) for value in crop.values()))
            self.assertGreater(crop["width"], 0)
            self.assertGreater(crop["height"], 0)

    def test_solstudio_pullerts_and_stairs_have_separate_fixed_crops(self):
        self.assertEqual(
            BOLLARD_CAMERA_DISPLAY_CROPS["G6 Solstudio Front"],
            {"x": 2765, "y": 0, "width": 537, "height": 734},
        )
        self.assertEqual(
            FIXED_STRUCTURE_MONITORS["trapp-solstudio"]["crop"],
            {"x": 2200, "y": 400, "width": 1640, "height": 1760},
        )

    def test_stairs_incident_has_its_own_notification_text(self):
        message = bollard_notification_message(
            {"bollard_key": "trapp-solstudio", "display_name": "Trapp ved Solstudio"}
        )

        self.assertIn("Trappa ved Solstudio", message)
        self.assertIn("skadet", message)
        self.assertNotIn("flyttet", message)

    def test_push_message_never_contains_local_plate_context(self):
        message = bollard_notification_message(
            {
                "display_name": "Pullert foran inngang",
                "context": {"plates": [{"normalized_value": "AB12345"}]},
            }
        )

        self.assertIn("Pullert foran inngang", message)
        self.assertNotIn("AB12345", message)

    def test_normalizes_name_and_roi(self):
        self.assertEqual(normalized_bollard_key("  Pullert Øst 1 "), "pullert-st-1")
        self.assertEqual(
            normalized_roi({"x": 0.2, "y": 0.3, "width": 0.1, "height": 0.4}),
            {"x": 0.2, "y": 0.3, "width": 0.1, "height": 0.4},
        )
        self.assertEqual(
            normalized_roi('{"x": 0.2, "y": 0.3, "width": 0.1, "height": 0.4}'),
            {"x": 0.2, "y": 0.3, "width": 0.1, "height": 0.4},
        )
        with self.assertRaises(ValueError):
            normalized_roi({"x": 0.99, "y": 0.3, "width": 0.2, "height": 0.4})

    def test_same_position_is_normal(self):
        baseline = _scene()
        result = compare_bollard_region(
            baseline,
            baseline.copy(),
            {"x": 0.35, "y": 0.28, "width": 0.12, "height": 0.53},
            match_threshold=0.4,
            movement_tolerance_pixels=8,
        )
        self.assertEqual(result["state"], "normal")
        self.assertGreater(result["expected_score"], 0.85)

    def test_polygon_overlay_is_preserved_and_masks_comparison(self):
        polygon = [
            {"x": 0.36, "y": 0.31},
            {"x": 0.44, "y": 0.31},
            {"x": 0.46, "y": 0.46},
            {"x": 0.46, "y": 0.79},
            {"x": 0.35, "y": 0.79},
            {"x": 0.35, "y": 0.46},
        ]
        roi = normalized_roi({"polygon": polygon})
        self.assertEqual(roi["polygon"], polygon)
        baseline = _scene()
        result = compare_bollard_region(
            baseline,
            baseline.copy(),
            roi,
            match_threshold=0.42,
            movement_tolerance_pixels=8,
        )
        self.assertEqual(result["state"], "normal")
        self.assertEqual(result["selection_type"], "polygon")
        self.assertGreater(result["mask_coverage"], 0.5)

        moved = compare_bollard_region(
            baseline,
            _scene(170),
            roi,
            match_threshold=0.42,
            movement_tolerance_pixels=8,
        )
        self.assertEqual(moved["state"], "moved")

    def test_large_shift_is_reported_as_moved(self):
        baseline = _scene(130)
        current = _scene(170)
        result = compare_bollard_region(
            baseline,
            current,
            {"x": 0.35, "y": 0.28, "width": 0.12, "height": 0.53},
            match_threshold=0.35,
            movement_tolerance_pixels=8,
        )
        self.assertEqual(result["state"], "moved")
        self.assertGreater(result["distance_pixels"], 30)

    def test_full_scene_overlay_compares_without_regions(self):
        baseline = _scene(130)
        unchanged, comparison_frame, overlay = compare_full_scene(
            baseline,
            baseline.copy(),
            analysis_width=360,
        )
        self.assertEqual(unchanged["state"], "normal")
        self.assertEqual(unchanged["comparison_mode"], "fixed_source_pixel_crop")
        self.assertFalse(unchanged["analysis_resized"])
        self.assertEqual(comparison_frame.shape, baseline.shape)
        self.assertEqual(overlay.shape, baseline.shape)

        changed, _aligned, _overlay = compare_full_scene(
            baseline,
            _scene(170),
            analysis_width=360,
        )
        self.assertIn(changed["state"], {"changed", "obscured"})
        self.assertGreater(changed["raw_changed_fraction"], 0)

    def test_full_scene_overlay_marks_changed_pixels_pure_red(self):
        baseline = stabilized_test_scene(130)
        current = baseline.copy()
        cv2.rectangle(current, (255, 95), (275, 125), (0, 0, 0), -1)

        result, _comparison_frame, overlay = compare_full_scene(baseline, current)

        red_pixels = np.all(overlay == np.array([0, 0, 255], dtype=np.uint8), axis=2)
        self.assertGreater(result["changed_fraction"], 0)
        self.assertGreater(int(np.count_nonzero(red_pixels)), 0)

    def test_fixed_crop_analysis_never_uses_requested_working_size(self):
        baseline = stabilized_test_scene(130)

        result, comparison_frame, overlay = compare_full_scene(
            baseline,
            baseline.copy(),
            analysis_width=90,
        )

        self.assertEqual(result["analysis_size"], {"width": 360, "height": 240})
        self.assertFalse(result["analysis_resized"])
        np.testing.assert_array_equal(comparison_frame, baseline)
        self.assertEqual(overlay.shape, baseline.shape)

    def test_full_scene_treats_a_large_foreground_change_as_obscured(self):
        baseline = _scene(130)
        foreground = baseline.copy()
        cv2.rectangle(foreground, (0, 0), (260, 180), (20, 25, 30), -1)

        result, _aligned, _overlay = compare_full_scene(
            baseline,
            foreground,
            analysis_width=360,
        )

        self.assertEqual(result["state"], "obscured")

    def test_fixed_structure_polygon_ignores_changes_outside_the_structure(self):
        baseline = stabilized_test_scene(130)
        current = baseline.copy()
        cv2.rectangle(current, (0, 0), (100, 239), (10, 10, 10), -1)

        result, _comparison, _overlay = compare_full_scene(
            baseline,
            current,
            analysis_width=360,
            analysis_polygon=(
                {"x": 0.35, "y": 0.20},
                {"x": 0.75, "y": 0.20},
                {"x": 0.75, "y": 0.90},
                {"x": 0.35, "y": 0.90},
            ),
            change_fraction_threshold=0.0025,
            obscured_fraction_threshold=0.06,
        )

        self.assertEqual(result["state"], "normal")
        self.assertEqual(result["changed_fraction"], 0.0)

    def test_large_fixed_structure_change_is_actionable(self):
        baseline = stabilized_test_scene(130)
        current = baseline.copy()
        cv2.rectangle(current, (125, 55), (300, 205), (10, 10, 10), -1)

        result, _comparison, _overlay = compare_full_scene(
            baseline,
            current,
            analysis_width=360,
            analysis_polygon=(
                {"x": 0.30, "y": 0.15},
                {"x": 0.90, "y": 0.15},
                {"x": 0.90, "y": 0.90},
                {"x": 0.30, "y": 0.90},
            ),
            change_fraction_threshold=0.015,
            obscured_fraction_threshold=0.06,
            major_change_is_actionable=True,
        )

        self.assertEqual(result["state"], "changed")

    def test_every_target_camera_has_internal_analysis_zones(self):
        self.assertEqual(set(BOLLARD_CAMERA_ANALYSIS_ZONES), set(TARGET_CAMERA_NAMES))
        self.assertTrue(all(BOLLARD_CAMERA_ANALYSIS_ZONES[name] for name in TARGET_CAMERA_NAMES))

    def test_fixed_zones_are_normal_until_the_bollard_moves(self):
        baseline = stabilized_test_scene(130)
        zones = (
            {
                "key": "test-bollard",
                "x": 0.35,
                "y": 0.28,
                "width": 0.12,
                "height": 0.53,
                "match_threshold": 0.5,
                "movement_tolerance_pixels": 8,
            },
        )

        normal, comparison_frame, overlay = compare_bollard_zones(baseline, baseline.copy(), zones)
        moved, _comparison_frame, _overlay = compare_bollard_zones(
            baseline,
            stabilized_test_scene(170),
            zones,
        )

        self.assertEqual(normal["state"], "normal")
        self.assertEqual(normal["comparison_mode"], "fixed_bollard_zones")
        self.assertEqual(normal["analysis_zone_count"], 1)
        self.assertEqual(comparison_frame.shape, baseline.shape)
        self.assertEqual(overlay.shape, baseline.shape)
        self.assertEqual(moved["state"], "changed")
        self.assertEqual(moved["abnormal_zone_count"], 1)
        self.assertIn(moved["change_components"][0]["state"], {"moved", "missing"})

    def test_fixed_camera_frame_is_never_geometrically_shifted(self):
        baseline = stabilized_test_scene(130)
        transform = np.float32([[1, 0, 11], [0, 1, -7]])
        current = cv2.warpAffine(
            baseline,
            transform,
            (baseline.shape[1], baseline.shape[0]),
            borderMode=cv2.BORDER_REFLECT,
        )

        comparison_frame, metadata = normalize_fixed_camera_frame(baseline, current)

        np.testing.assert_array_equal(comparison_frame, current)
        self.assertFalse(metadata["aligned"])
        self.assertFalse(metadata["resized"])
        self.assertEqual(metadata["mode"], "fixed_camera_pixels")

    def test_fixed_camera_frame_rejects_resolution_changes(self):
        baseline = stabilized_test_scene(130)
        current = cv2.resize(baseline, (180, 120), interpolation=cv2.INTER_AREA)

        with self.assertRaisesRegex(ValueError, "blir ikke skalert"):
            normalize_fixed_camera_frame(baseline, current)


if __name__ == "__main__":
    unittest.main()
