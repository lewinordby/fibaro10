import unittest

from sun2_helpers import (
    SUN2_ROOM_UNKNOWN_OLD_10,
    normalize_room_id,
    repair_mojibake,
    room_key_from_name,
    sun2_room_identity,
    sun2_room_label,
)


class Sun2HelperTests(unittest.TestCase):
    def test_room_key_from_name_normalizes_display_name(self):
        self.assertEqual(room_key_from_name("Rom 07 Super VIP"), "rom_07")
        self.assertIsNone(room_key_from_name("VIP"))

    def test_normalize_room_id_accepts_common_forms(self):
        self.assertEqual(normalize_room_id("rom_7"), "rom-07")
        self.assertEqual(normalize_room_id("12"), "rom-12")
        self.assertIsNone(normalize_room_id("14"))

    def test_room_identity_maps_display_room_10_to_physical_room_11(self):
        identity = sun2_room_identity("Rom 10")

        self.assertEqual(identity["room_id"], "rom-11")
        self.assertEqual(identity["physical_room_number"], 11)
        self.assertEqual(identity["display_room_number"], 10)
        self.assertEqual(identity["sun2_bed_id"], "679")

    def test_room_identity_keeps_old_unknown_dot_room(self):
        identity = sun2_room_identity(".")

        self.assertEqual(identity, SUN2_ROOM_UNKNOWN_OLD_10)

    def test_room_label_uses_source_name_when_present(self):
        self.assertEqual(sun2_room_label("rom-12", "Deluxe"), "Rom 12 - Deluxe")
        self.assertEqual(sun2_room_label("rom-10", "."), "Rom 10 - tidligere SUN2-navn '.'")

    def test_repair_mojibake_leaves_normal_text_alone(self):
        self.assertEqual(repair_mojibake("Kjøling"), "Kjøling")


if __name__ == "__main__":
    unittest.main()
