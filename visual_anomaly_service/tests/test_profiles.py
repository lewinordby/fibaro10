import unittest

import numpy as np

from app.profiles import PROFILES, build_analysis_atlas, fixed_source_crop, prepare_profile_image


class ProfileImageTests(unittest.TestCase):
    def test_fixed_crop_uses_exact_source_pixels(self):
        image = np.arange(100 * 120 * 3, dtype=np.int64).reshape(100, 120, 3)
        crop = fixed_source_crop(image, {"x": 20, "y": 10, "width": 30, "height": 40})
        np.testing.assert_array_equal(crop, image[10:50, 20:50])

    def test_atlas_has_stable_size_for_multiple_regions(self):
        image = np.full((300, 500, 3), 160, dtype=np.uint8)
        atlas = build_analysis_atlas(
            image,
            (
                {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.4},
                {"x": 0.5, "y": 0.2, "width": 0.3, "height": 0.3},
            ),
        )
        self.assertEqual(atlas.shape, (512, 512, 3))

    def test_every_profile_builds_from_a_4k_source(self):
        source = np.full((2160, 3840, 3), 127, dtype=np.uint8)
        for profile in PROFILES.values():
            with self.subTest(profile=profile.profile_id):
                atlas = prepare_profile_image(profile, source, is_source=True)
                self.assertEqual(atlas.shape, (512, 512, 3))

    def test_every_pullert_has_an_explicit_analysis_region(self):
        self.assertEqual(len(PROFILES["north-bollards"].regions), 3)
        self.assertEqual(len(PROFILES["front-bollards"].regions), 4)
        self.assertEqual(len(PROFILES["solstudio-bollards"].regions), 3)
        for profile_id in ("north-bollards", "front-bollards", "solstudio-bollards"):
            for region in PROFILES[profile_id].regions:
                self.assertTrue(str(region.get("label") or "").startswith("Pullert"))
        self.assertGreater(PROFILES["solstudio-bollards"].threshold_scale, 0.9)
        self.assertLess(PROFILES["solstudio-bollards"].threshold_scale, 1.0)


if __name__ == "__main__":
    unittest.main()
