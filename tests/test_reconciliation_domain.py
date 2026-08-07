import unittest

from reconciliation_domain import (
    evaluate_reconciliation,
    reconciliation_difference_percent,
    reconciliation_group,
    reconciliation_summary,
    state_reconciliation,
)


class ReconciliationDomainTests(unittest.TestCase):
    def test_marks_values_inside_absolute_tolerance_as_ok(self):
        row = evaluate_reconciliation(
            check_id="parking-2026-07",
            domain="Parkering",
            title="Parkeringsoppgjor",
            actual_label="Fibaro10",
            actual_value=1000.75,
            reference_label="Oppgjor",
            reference_value=1000,
            unit="kr",
            absolute_tolerance=1,
        )

        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["difference"], 0.75)
        self.assertEqual(row["difference_percent"], 0.07)

    def test_uses_largest_of_absolute_and_percentage_tolerance(self):
        warning = evaluate_reconciliation(
            check_id="energy",
            domain="Energi",
            title="Elvia mot HC3",
            actual_label="HC3",
            actual_value=104,
            reference_label="Elvia",
            reference_value=100,
            unit="kWh",
            absolute_tolerance=1,
            percent_tolerance=2,
            critical_multiplier=3,
        )
        critical = evaluate_reconciliation(
            check_id="energy",
            domain="Energi",
            title="Elvia mot HC3",
            actual_label="HC3",
            actual_value=107,
            reference_label="Elvia",
            reference_value=100,
            unit="kWh",
            absolute_tolerance=1,
            percent_tolerance=2,
            critical_multiplier=3,
        )

        self.assertEqual(warning["allowed_difference"], 2)
        self.assertEqual(warning["status"], "warning")
        self.assertEqual(critical["status"], "critical")

    def test_missing_reference_is_never_reported_as_ok(self):
        row = evaluate_reconciliation(
            check_id="sun-missing",
            domain="Soling",
            title="Soloppgjor",
            actual_label="SUN2",
            actual_value=15000,
            reference_label="Oppgjor",
            reference_value=None,
            unit="kr",
            absolute_tolerance=1,
        )

        self.assertEqual(row["status"], "missing")
        self.assertIsNone(row["difference"])

    def test_zero_reference_has_no_misleading_percentage(self):
        self.assertIsNone(reconciliation_difference_percent(10, 0))

    def test_summary_prioritizes_critical_status(self):
        rows = [
            state_reconciliation(
                check_id="ok",
                domain="System",
                title="OK",
                status="ok",
                value_label="Status",
                value=1,
            ),
            state_reconciliation(
                check_id="critical",
                domain="Dorer",
                title="Alarm",
                status="critical",
                value_label="Aktive",
                value=2,
            ),
            state_reconciliation(
                check_id="missing",
                domain="Soling",
                title="Bilag",
                status="missing",
                value_label="Bilag",
                value=0,
            ),
        ]

        summary = reconciliation_summary(rows)
        group = reconciliation_group("all", "Alle", "", rows)

        self.assertEqual(summary["attention"], 2)
        self.assertEqual(summary["overall_status"], "critical")
        self.assertEqual(group["checks"][0]["id"], "critical")


if __name__ == "__main__":
    unittest.main()
