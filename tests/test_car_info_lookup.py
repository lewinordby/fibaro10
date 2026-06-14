import unittest

from car_info_lookup.app.parsing import is_swedish_license_plate, parse_car_info_html


class CarInfoLookupTests(unittest.TestCase):
    def test_swedish_license_plate_filter(self) -> None:
        self.assertTrue(is_swedish_license_plate("HWN31L"))
        self.assertTrue(is_swedish_license_plate("ABC123"))
        self.assertFalse(is_swedish_license_plate("EL12345"))
        self.assertFalse(is_swedish_license_plate("DP12345"))
        self.assertFalse(is_swedish_license_plate("ABC12O"))

    def test_car_info_parser_extracts_relevant_fields(self) -> None:
        html = """
        <html>
          <head>
            <title>HWN31L - Volkswagen Caravelle T32 eHybrid E-CVT, 233hk, 2026</title>
            <meta property="og:title" content="HWN31L - Volkswagen Caravelle T32 eHybrid E-CVT, 233hk, 2026"/>
            <meta property="og:description" content="HWN31L is a grey Volkswagen Caravelle T32 from 2026 with a 233 hp hybrid engine and automatic transmission. In traffic: No."/>
          </head>
          <body>
            <span class="licplate license_code_S"><span class="plate-text">HWN31L</span></span>
            <script>window.marketCode = "se";</script>
            <span class="sptitle">First registered</span><span>2026-01-15</span>
            <span class="sptitle">Body type</span><span>Van</span>
            <span class="sptitle">Mileage</span><span>12 345 km</span>
            <span class="sptitle">Inspection valid to</span><span>2029-01-31</span>
          </body>
        </html>
        """

        parsed = parse_car_info_html("HWN31L", "https://www.car.info/sv-se/license-plate/S/HWN31L", html)

        self.assertTrue(parsed["confirmed_swedish"])
        self.assertEqual(parsed["fields"]["model_year"], "2026")
        self.assertIn("Volkswagen Caravelle", parsed["fields"]["vehicle_title"])
        self.assertEqual(parsed["fields"]["color"], "grey")
        self.assertEqual(parsed["fields"]["fuel"], "Hybrid")
        self.assertEqual(parsed["fields"]["transmission"], "Automat")
        self.assertEqual(parsed["fields"]["first_registered"], "2026-01-15")
        self.assertEqual(parsed["fields"]["vehicle_type"], "Van")
        self.assertEqual(parsed["fields"]["mileage"], "12 345 km")
        self.assertEqual(parsed["fields"]["inspection_valid_to"], "2029-01-31")


if __name__ == "__main__":
    unittest.main()
