import unittest

from unifi_protect_events.app.build_log import (
    PROTECT_LEDGER_BUILD,
    protect_ledger_build_detail,
    protect_ledger_build_log_payload,
    protect_ledger_build_summary,
)


class ProtectLedgerBuildLogTests(unittest.TestCase):
    def test_current_build_exists_in_log(self):
        summary = protect_ledger_build_summary()
        detail = protect_ledger_build_detail(PROTECT_LEDGER_BUILD)

        self.assertEqual(summary["name"], "Protect Ledger")
        self.assertEqual(summary["build"], PROTECT_LEDGER_BUILD)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["build"], PROTECT_LEDGER_BUILD)

    def test_builds_are_newest_first_and_complete(self):
        payload = protect_ledger_build_log_payload()
        builds = [int(row["build"]) for row in payload["items"]]

        self.assertEqual(builds, sorted(builds, reverse=True))
        self.assertEqual(payload["count"], len(payload["items"]))
        for row in payload["items"]:
            self.assertTrue(row["headline"])
            self.assertTrue(row["description"])
            self.assertTrue(row["changes"])
            self.assertTrue(row["applications"])

    def test_search_matches_changes_and_components(self):
        validation = protect_ledger_build_log_payload(query="Statens vegvesen")
        component = protect_ledger_build_log_payload(query="integration.py")
        missing = protect_ledger_build_log_payload(query="ingen-sl slik-komponent")

        self.assertEqual([row["build"] for row in validation["items"]], ["3"])
        self.assertGreaterEqual(component["count"], 1)
        self.assertEqual(missing["count"], 0)
        self.assertEqual(missing["items"], [])

    def test_detail_returns_none_for_unknown_build(self):
        self.assertIsNone(protect_ledger_build_detail("9999"))


if __name__ == "__main__":
    unittest.main()
