from datetime import datetime
import json
import unittest

from energy_helpers import meter_id_from_filename, parse_elvia_json_payload


class EnergyHelperTests(unittest.TestCase):
    def test_meter_id_from_filename_uses_leading_digits(self):
        self.assertEqual(meter_id_from_filename("707057500012345678-juni.json"), "707057500012345678")
        self.assertEqual(meter_id_from_filename("elvia-export.json"), "elvia")

    def test_parse_elvia_json_payload_extracts_hour_rows(self):
        payload = {
            "Years": [
                {
                    "Months": [
                        {
                            "Days": [
                                {
                                    "Year": 2026,
                                    "Month": 6,
                                    "Day": 10,
                                    "Hours": [
                                        {
                                            "Year": 2026,
                                            "Month": 6,
                                            "Day": 10,
                                            "Hour": 8,
                                            "Consumption": {"Value": "1,25", "Status": "OK", "IsVerified": "true"},
                                            "Production": {"Value": 0},
                                            "IsPublicHoliday": False,
                                            "UseWeekendPrices": "nei",
                                        },
                                        {
                                            "Year": 2026,
                                            "Month": 6,
                                            "Day": 10,
                                            "Hour": 9,
                                            "Consumption": {"Value": "2.50", "Status": "Estimated", "IsVerified": 0},
                                            "Production": {"Value": "0,10"},
                                            "IsPublicHoliday": "0",
                                            "UseWeekendPrices": "ja",
                                        },
                                    ],
                                }
                            ],
                        }
                    ]
                }
            ]
        }

        parsed = parse_elvia_json_payload(json.dumps(payload).encode("utf-8"), "123456-elvia.json")

        self.assertEqual(parsed["meter_id"], "123456")
        self.assertEqual(parsed["first_at"], datetime(2026, 6, 10, 8))
        self.assertEqual(parsed["last_at"], datetime(2026, 6, 10, 9))
        self.assertEqual(parsed["days_count"], 1)
        self.assertEqual(parsed["hours_count"], 2)
        self.assertAlmostEqual(parsed["total_kwh"], 3.75)
        self.assertEqual(parsed["estimated_hours_count"], 1)
        self.assertEqual(parsed["partial_months"][0]["month"], "2026-06")
        self.assertEqual(parsed["rows"][0]["consumption_kwh"], 1.25)
        self.assertEqual(parsed["rows"][0]["is_verified"], True)
        self.assertEqual(parsed["rows"][1]["production_kwh"], 0.1)
        self.assertEqual(parsed["rows"][1]["use_weekend_prices"], True)


if __name__ == "__main__":
    unittest.main()
