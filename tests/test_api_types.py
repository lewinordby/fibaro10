import unittest

from api_types import BuildLogEntryPayload, BuildLogResponsePayload, HealthPayload, ModuleCardPayload, ModulePayload, ModuleTablePayload


class ApiTypeContractTests(unittest.TestCase):
    def test_build_log_entry_contract_has_frontend_fields(self) -> None:
        required = set(BuildLogEntryPayload.__required_keys__)

        self.assertTrue(
            {
                "version",
                "build",
                "date",
                "headline",
                "title",
                "description",
                "applications",
                "changes",
                "request",
                "workDuration",
                "creditsUsed",
                "path",
                "isCurrent",
            }.issubset(required)
        )

    def test_build_log_response_contract_has_rows(self) -> None:
        required = set(BuildLogResponsePayload.__required_keys__)

        self.assertEqual(required, {"currentBuild", "rows"})

    def test_health_contract_has_operational_fields(self) -> None:
        required = set(HealthPayload.__required_keys__)

        self.assertEqual(required, {"status", "app", "checks", "summary", "sources", "storage"})

    def test_module_contract_has_generic_cards_and_tables(self) -> None:
        card_required = set(ModuleCardPayload.__required_keys__)
        table_required = set(ModuleTablePayload.__required_keys__)
        module_optional = set(ModulePayload.__optional_keys__)

        self.assertTrue({"title", "value", "tone"}.issubset(card_required))
        self.assertTrue({"title", "columns", "rows"}.issubset(table_required))
        self.assertIn("meta", set(ModuleTablePayload.__optional_keys__))
        self.assertTrue({"cards", "charts", "tables", "actions", "filters"}.issubset(module_optional))


if __name__ == "__main__":
    unittest.main()
