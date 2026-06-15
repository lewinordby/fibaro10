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
        self.assertEqual(parsed["long_term_parking_ex_vat"], 0)
        self.assertEqual(parsed["long_term_share_percent"], 90)
        self.assertEqual(parsed["long_term_share_ex_vat"], 0)
        self.assertEqual(parsed["control_fee_net_ex_vat"], 25740)
        self.assertEqual(parsed["control_fee_share_percent"], 25)
        self.assertEqual(parsed["control_fee_share_ex_vat"], 6435)
        self.assertEqual(parsed["total_basis_ex_vat"], 192937)
        self.assertEqual(parsed["total_share_ex_vat"], 156912)
        self.assertEqual(parsed["vat_25_percent"], 39228)
        self.assertEqual(parsed["payout_inc_vat"], 196140)
        self.assertGreaterEqual(parsed["_meta"]["confidence"], 0.9)
        self.assertIn("easypark_ex_vat", parsed["_meta"]["field_sources"])

        form_rows = {
            row["field"]: row
            for row in main.settlement_form_rows(
                parsed,
                {
                    "flowbird": {
                        "label": "flowbird-parknordic",
                        "sources": ["flowbird-parknordic"],
                        "count": 213,
                        "paid_ex_vat": 10825.60,
                        "paid_inc_vat": 13532.00,
                    },
                    "easypark": {
                        "label": "EasyPark",
                        "sources": ["EasyPark"],
                        "count": 3157,
                        "paid_ex_vat": 160262.40,
                        "paid_inc_vat": 200328.00,
                    },
                },
            )
        }
        self.assertEqual(form_rows["gross_coin_card_ex_vat"]["expected"], 10825.6)
        self.assertAlmostEqual(form_rows["gross_coin_card_ex_vat"]["difference"], -244.6)
        self.assertEqual(form_rows["gross_coin_card_ex_vat"]["expectedSource"], "source_system = flowbird-parknordic")
        self.assertEqual(form_rows["easypark_ex_vat"]["expected"], 160262.4)
        self.assertAlmostEqual(form_rows["easypark_ex_vat"]["difference"], -2484.4)
        self.assertEqual(form_rows["easypark_ex_vat"]["expectedSource"], "source_system = EasyPark")

    def test_sun_settlement_text_parser_reads_altera_creditnote(self) -> None:
        extraction = {
            "method": "test",
            "line_count": 18,
            "pages_count": 1,
            "warnings": [],
            "lines": [
                "603",
                "31/01/26",
                "Lillehammer VelvÃ¦re AS, SUN2 Lillehammer",
                "Altera AS",
                "1584Faktnr.:",
                "Kreditnota",
                "101 Solomsetning for perioden -1.00128,868.29 -128,868.29",
                "102 Produktsalg for perioden -1.001,742.40 -1,742.40",
                "103 Transaksjonskostnad (6%) 1.007,836.64 7,836.64",
                "104 Serviceavtale 1.001,110.00 1,110.00",
                "105 MarkedsfÃ¸ring - SMS 1.000.00 0.00",
                "106 MarkedsfÃ¸ring - E-post 1.000.00 0.00",
                "Kontantrabatt: Mva grunnlag: -121664.05",
                "Sum mva:",
                "-30416.01",
                "FakturabelÃ¸p: -152,080.06",
                "Sum ordrelinjer: -121664.05",
            ],
        }

        parsed = main.parse_sun_settlement_text(extraction)

        self.assertEqual(parsed["credit_note_number"], 1584)
        self.assertEqual(parsed["credit_note_date"], "2026-01-31")
        self.assertEqual(parsed["delivery_date"], "2026-01-31")
        self.assertEqual(parsed["supplier_name"], "Altera AS")
        self.assertEqual(parsed["sun_revenue_ex_vat"], 128868.29)
        self.assertEqual(parsed["product_sales_ex_vat"], 1742.4)
        self.assertEqual(parsed["transaction_fee_ex_vat"], -7836.64)
        self.assertEqual(parsed["service_fee_ex_vat"], -1110)
        self.assertEqual(parsed["marketing_sms_fee_ex_vat"], 0)
        self.assertEqual(parsed["marketing_email_fee_ex_vat"], 0)
        self.assertEqual(parsed["sum_ex_vat"], 121664.05)
        self.assertEqual(parsed["vat_25_percent"], 30416.01)
        self.assertEqual(parsed["payout_inc_vat"], 152080.06)
        self.assertEqual(main.settlement_period_from_parsed_dates(parsed, "delivery_date", "credit_note_date")[2], "Januar 2026")
        self.assertEqual(parsed["_meta"]["confidence"], 1.0)

        form_rows = {row["field"]: row for row in main.sun_settlement_form_rows(parsed)}
        self.assertEqual(form_rows["sum_ex_vat"]["status"], "ok")
        self.assertEqual(form_rows["vat_25_percent"]["status"], "ok")
        self.assertEqual(form_rows["payout_inc_vat"]["status"], "ok")
        self.assertEqual(form_rows["sum_ex_vat"]["difference"], 0)
        self.assertEqual(form_rows["vat_25_percent"]["difference"], 0)
        self.assertEqual(form_rows["payout_inc_vat"]["difference"], 0)

        product_control_rows = {
            row["field"]: row
            for row in main.sun_settlement_form_rows(
                parsed,
                {
                    "count": 8,
                    "quantity": 8,
                    "amount_ex_vat": 1742.4,
                    "amount_inc_vat": 2178,
                    "last_imported_at": None,
                },
            )
        }
        self.assertEqual(product_control_rows["product_sales_ex_vat"]["expected"], 1742.4)
        self.assertEqual(product_control_rows["product_sales_ex_vat"]["expectedSource"], "sun2_product_sales")
        self.assertEqual(product_control_rows["product_sales_ex_vat"]["status"], "ok")
        self.assertEqual(product_control_rows["product_sales_ex_vat"]["difference"], 0)


if __name__ == "__main__":
    unittest.main()
