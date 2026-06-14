import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

import main


class ParkingSettlementParserTests(unittest.TestCase):
    def test_parking_settlement_text_parser_reads_parknordic_pdf_text(self) -> None:
        extraction = {
            "method": "test",
            "line_count": 28,
            "pages_count": 1,
            "warnings": [],
            "lines": [
                "Oslo 11.05.2026",
                "OPPGJØRSRAPPORT FOR april 2026",
                "Driftssted 11613 Lilletorget",
                "Oppdragsgiver 50797 Lillehammer Velvære AS",
                "Antall automater 1",
                "Oms. eks. mva Andel i % Sum",
                "Bruttoinntekter over mynt/kortautomat 10 581",
                "EasyPark 157 778",
                "Fratrekk tømming, telling av mynt, avregning kredittkort -1 162",
                "167 197 90,0 % 150 477",
                "0 90,0 % 0",
                "25 740 25,0 % 6 435",
                "192 937 156 912",
                "39 228",
                "196 140",
                "Betaling vil skje etter at vi har mottatt faktura fra dere!",
                "lewi.nordby@gmail.com",
            ],
        }

        parsed = main.parse_parking_settlement_text(extraction)

        self.assertEqual(parsed["report_date"], "2026-05-11")
        self.assertEqual(parsed["reported_period_label"], "April 2026")
        self.assertEqual(parsed["site_number"], "11613")
        self.assertEqual(parsed["site_name"], "Lilletorget")
        self.assertEqual(parsed["customer_number"], "50797")
        self.assertEqual(parsed["customer_name"], "Lillehammer Velvære AS")
        self.assertEqual(parsed["machine_count"], 1)
        self.assertEqual(parsed["gross_coin_card_ex_vat"], 10581)
        self.assertEqual(parsed["easypark_ex_vat"], 157778)
        self.assertEqual(parsed["easypark_inc_vat_estimate"], 197222.5)
        self.assertEqual(parsed["settlement_fee_ex_vat"], -1162)
        self.assertEqual(parsed["revenue_basis_ex_vat"], 167197)
        self.assertEqual(parsed["revenue_share_percent"], 90)
        self.assertEqual(parsed["revenue_share_ex_vat"], 150477)
        self.assertEqual(parsed["long_term_parking_ex_vat"], 25740)
        self.assertEqual(parsed["long_term_share_percent"], 25)
        self.assertEqual(parsed["long_term_share_ex_vat"], 6435)
        self.assertEqual(parsed["total_basis_ex_vat"], 192937)
        self.assertEqual(parsed["total_share_ex_vat"], 156912)
        self.assertEqual(parsed["vat_25_percent"], 39228)
        self.assertEqual(parsed["payout_inc_vat"], 196140)
        self.assertGreaterEqual(parsed["_meta"]["confidence"], 0.9)
        self.assertIn("easypark_ex_vat", parsed["_meta"]["field_sources"])


if __name__ == "__main__":
    unittest.main()
