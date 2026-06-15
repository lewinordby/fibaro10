import unittest

from car_info_lookup.app.parsing import (
    compact_plate,
    is_danish_license_plate,
    is_supported_foreign_license_plate,
    is_swedish_license_plate,
    parse_biluppgifter_html,
    parse_tjekbil_json,
)


class NordicVehicleLookupTests(unittest.TestCase):
    def test_swedish_license_plate_filter(self) -> None:
        self.assertTrue(is_swedish_license_plate("HWN31L"))
        self.assertTrue(is_swedish_license_plate("ABC123"))
        self.assertFalse(is_swedish_license_plate("EL12345"))
        self.assertFalse(is_swedish_license_plate("DP12345"))
        self.assertFalse(is_swedish_license_plate("ABC12O"))
        self.assertTrue(is_supported_foreign_license_plate("HWN31L"))
        self.assertEqual(compact_plate("LÖBK957"), "LBK957")
        self.assertTrue(is_swedish_license_plate("LÖBK957"))

    def test_danish_license_plate_filter(self) -> None:
        self.assertTrue(is_danish_license_plate("DY71543"))
        self.assertTrue(is_danish_license_plate("DP12345"))
        self.assertFalse(is_danish_license_plate("HWN31L"))
        self.assertTrue(is_supported_foreign_license_plate("DY71543"))

    def test_biluppgifter_parser_extracts_vehicle_fields(self) -> None:
        html = """
        <html>
          <head>
            <title>WDB22E Mercedes-Benz EQE 350 4-matic Silver 2024 - Biluppgifter.se</title>
            <meta name="description" content="WDB22E \u00e4r en Silver Personbil av \u00e5rsmodell 2024 som \u00e4r Itrafik." />
          </head>
          <body>
            <h1>S\u00f6k fordonsuppgifter</h1>
            <h1>Mercedes-Benz EQE 350 4-matic, 292hk, 2024</h1>
            <span class="label">Fabrikat</span><span class="value">Mercedes-Benz</span>
            <span class="label">Variant</span><span class="value">EQE 350 4-matic</span>
            <span class="label">Registreringsnummer</span><span class="value">WDB22E</span>
            <span class="label">Fordons\u00e5r / Modell\u00e5r</span><span class="value">2024 / 2024</span>
            <span class="label">Status</span><span class="value">I Trafik</span>
            <span class="label">F\u00f6rst registrerad</span><span class="value">2025-01-31</span>
            <span class="label">Senaste \u00e4garbyte</span><span class="value">2025-02-28</span>
            <span class="label">N\u00e4sta besiktning senast</span><span class="value">2028-02-29</span>
            <span class="label">Drivmedel</span><span class="value">El</span>
            <span class="label">Motoreffekt</span><span class="value">292 HK / 215 kW</span>
            <span class="label">Fyrhjulsdrift</span><span class="value">Ja</span>
            <span class="label">F\u00e4rg</span><span class="value">Silver</span>
            <span class="label">Kaross</span><span class="value">Stationsvagn Kombivagn</span>
          </body>
        </html>
        """

        parsed = parse_biluppgifter_html("WDB22E", "https://biluppgifter.se/fordon/wdb22e/", html)

        self.assertTrue(parsed["confirmed_swedish"])
        self.assertEqual(parsed["provider"], "biluppgifter")
        self.assertEqual(parsed["fields"]["vehicle_title"], "Mercedes-Benz EQE 350 4-matic")
        self.assertEqual(parsed["fields"]["model_year"], "2024")
        self.assertEqual(parsed["fields"]["color"], "Silver")
        self.assertEqual(parsed["fields"]["vehicle_type"], "Personbil")
        self.assertEqual(parsed["fields"]["first_registered"], "2025-01-31")
        self.assertEqual(parsed["fields"]["latest_owner_change"], "2025-02-28")
        self.assertEqual(parsed["fields"]["inspection_valid_to"], "2028-02-29")
        self.assertEqual(parsed["fields"]["fuel"], "El")
        self.assertEqual(parsed["fields"]["power"], "292 HK / 215 kW")
        self.assertEqual(parsed["fields"]["drivetrain"], "Fyrhjulsdrift")
        self.assertEqual(parsed["fields"]["body_type"], "Stationsvagn Kombivagn")

    def test_tjekbil_parser_extracts_vehicle_fields(self) -> None:
        payload = {
            "basic": {
                "regNr": "DY71543",
                "stelNr": "VG5DM116000008340",
                "status": "Registreret",
                "foersteRegistreringDato": "2024-06-17T00:00:00+02:00",
                "koeretoejArtNavn": "Motorcykel",
                "maerkeTypeNavn": "YAMAHA",
                "modelTypeNavn": "Tenere 700 World Raid (XTZ700)",
                "modelAar": "2022",
                "motorHestekraefter": 73,
                "motorStoersteEffekt": 54.0,
                "drivkraftTypeNavn": "Benzin",
            },
            "extended": {
                "general": {
                    "regNr": "DY71543",
                    "maerke": "YAMAHA",
                    "model": "Tenere 700 World Raid (XTZ700)",
                    "modelAar": "2022",
                    "firstRegDate": "2024-06-17T00:00:00+02:00",
                    "status": "Registreret",
                    "koeretoejArt": "Motorcykel",
                    "stelNummer": "VG5DM116000008340",
                },
                "techical": {
                    "motorStoersteEffekt": 54.0,
                    "totalVaegt": 394,
                    "drivkraftTypeNavn": "Benzin",
                },
                "inspection": {
                    "naesteSyn": "2028-06-17T00:00:00+02:00",
                    "sidsteSynResultat": "Godkendt",
                },
            },
        }

        parsed = parse_tjekbil_json("DY71543", "https://www.tjekbil.dk/api/v3/dmr/regnr/DY71543", payload)

        self.assertTrue(parsed["confirmed_danish"])
        self.assertTrue(parsed["confirmed_vehicle"])
        self.assertEqual(parsed["provider"], "tjekbil")
        self.assertEqual(parsed["country_code"], "DK")
        self.assertEqual(parsed["fields"]["vehicle_title"], "YAMAHA Tenere 700 World Raid (XTZ700)")
        self.assertEqual(parsed["fields"]["model_year"], "2022")
        self.assertEqual(parsed["fields"]["first_registered"], "2024-06-17")
        self.assertEqual(parsed["fields"]["vehicle_type"], "Motorcykel")
        self.assertEqual(parsed["fields"]["fuel"], "Benzin")
        self.assertEqual(parsed["fields"]["power"], "73 HK / 54.0 kW")
        self.assertEqual(parsed["fields"]["vin"], "VG5DM116000008340")
        self.assertEqual(parsed["fields"]["inspection_valid_to"], "2028-06-17")


if __name__ == "__main__":
    unittest.main()
