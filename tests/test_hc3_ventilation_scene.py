import unittest
from pathlib import Path


SCENE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hc3_ventilation_runner_scene_363.lua"


class Hc3VentilationSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCENE_PATH.read_text(encoding="utf-8")

    def test_normal_exhaust_requires_cooler_replacement_air(self):
        guard = self.source.index("elseif not replacementAirAcceptable then")
        normal_exhaust = self.source.index("elseif maxInne > AVTREKK_MAX_INNE_ON")
        safety_exhaust = self.source.index("elseif tempLoft > AVTREKK_LOFT_SAFETY_ON")

        self.assertLess(safety_exhaust, guard)
        self.assertLess(guard, normal_exhaust)

    def test_hot_loft_intake_is_checked_per_zone(self):
        self.assertIn("and not vipOutdoorWarmer", self.source)
        self.assertIn("and not floorsOutdoorWarmer", self.source)
        self.assertIn("openTime and vipLoftHotAllowed", self.source)
        self.assertIn("openTime and floorsLoftHotAllowed", self.source)


if __name__ == "__main__":
    unittest.main()
