import unittest

import build_log


class BuildLogTests(unittest.TestCase):
    def test_current_build_is_first_and_marked_current(self) -> None:
        entry = build_log.normalized_build_log_entry(build_log.BUILD_LOG[0])

        self.assertEqual(entry["build"], build_log.APP_BUILD)
        self.assertTrue(entry["isCurrent"])
        self.assertEqual(entry["path"], f"/admin/build/{build_log.APP_BUILD}")

    def test_minimal_entry_gets_safe_defaults(self) -> None:
        entry = build_log.normalized_build_log_entry({"build": "42", "changes": ["Endring"]})

        self.assertEqual(entry["headline"], "Build 42")
        self.assertEqual(entry["title"], "Build 42")
        self.assertEqual(entry["description"], "Endring")
        self.assertEqual(entry["workDuration"], "Ikke registrert")
        self.assertEqual(entry["creditsUsed"], "Ikke registrert")

    def test_api_row_uses_table_safe_applications_text(self) -> None:
        row = build_log.api_build_log_row(
            {
                "build": "43",
                "date": "10.06.2026",
                "headline": "Kort overskrift",
                "applications": ["Frontend", "Backend"],
            }
        )

        self.assertEqual(row["applications"], "Frontend; Backend")
        self.assertEqual(row["headline"], "Kort overskrift")
        self.assertEqual(row["path"], "/admin/build/43")


if __name__ == "__main__":
    unittest.main()
