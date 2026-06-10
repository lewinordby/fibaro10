import unittest

from api_types import BuildLogEntryPayload, BuildLogResponsePayload, HealthPayload


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

        self.assertEqual(required, {"status", "app", "checks", "sources", "storage"})


if __name__ == "__main__":
    unittest.main()
