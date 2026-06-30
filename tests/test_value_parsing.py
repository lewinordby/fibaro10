from datetime import datetime
import unittest

from value_parsing import area_m2_from_payload, bool_value, first_dict, float_value, int_value, timestamp_value


class ValueParsingTests(unittest.TestCase):
    def test_bool_value_accepts_norwegian_and_numeric_values(self):
        self.assertEqual(bool_value("ja"), True)
        self.assertEqual(bool_value("nei"), False)
        self.assertEqual(bool_value(1), True)
        self.assertEqual(bool_value(0), False)
        self.assertIsNone(bool_value("kanskje"))

    def test_number_parsers_handle_common_local_formats(self):
        self.assertEqual(int_value("42"), 42)
        self.assertIsNone(int_value("42,1"))
        self.assertEqual(float_value("1 234,50"), 1234.5)
        self.assertEqual(float_value("1.234,50"), 1234.5)

    def test_timestamp_value_accepts_iso_and_epoch(self):
        self.assertEqual(timestamp_value("2026-06-30T12:15:00"), datetime(2026, 6, 30, 12, 15))
        self.assertEqual(timestamp_value(0), datetime(1970, 1, 1, 0, 0))
        self.assertIsNone(timestamp_value("ikke-tid"))

    def test_area_from_roborock_payload_converts_square_millimeters(self):
        self.assertEqual(area_m2_from_payload(25500000), 25.5)
        self.assertEqual(area_m2_from_payload(55), 55.0)

    def test_first_dict_extracts_first_dict_from_list(self):
        self.assertEqual(first_dict([{"a": 1}, {"a": 2}]), {"a": 1})
        self.assertEqual(first_dict({"b": 2}), {"b": 2})
        self.assertEqual(first_dict([]), {})


if __name__ == "__main__":
    unittest.main()
