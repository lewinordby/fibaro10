import unittest

from observability import STORAGE_TABLES, health_payload


class ObservabilityTests(unittest.TestCase):
    def test_health_payload_contains_app_and_checks(self) -> None:
        payload = health_payload(
            app_version="1",
            app_build="1100",
            app_commit="abc123",
            started_at="2026-06-10T10:00:00Z",
            database={"status": "ok", "detail": "SELECT 1 OK"},
        )

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["app"]["build"], "1100")
        self.assertEqual(payload["app"]["commit"], "abc123")
        self.assertEqual(payload["checks"]["database"]["status"], "ok")
        self.assertEqual(payload["summary"]["sources"]["total"], 0)
        self.assertIn("schema_migrations", payload["storage"])

    def test_health_payload_warns_when_source_is_bad(self) -> None:
        payload = health_payload(
            app_version="1",
            app_build="1100",
            app_commit="abc123",
            started_at="2026-06-10T10:00:00Z",
            database={"status": "ok"},
            sources=[{"title": "EasyPark", "status": "bad"}],
        )

        self.assertEqual(payload["status"], "warn")
        self.assertEqual(payload["summary"]["sources"]["bad"], 1)

    def test_health_payload_warns_when_source_is_slow(self) -> None:
        payload = health_payload(
            app_version="1",
            app_build="1100",
            app_commit="abc123",
            started_at="2026-06-10T10:00:00Z",
            database={"status": "ok"},
            sources=[{"title": "EasyPark", "status": "warn"}],
        )

        self.assertEqual(payload["status"], "warn")
        self.assertEqual(payload["summary"]["sources"]["warn"], 1)

    def test_storage_tables_are_unique(self) -> None:
        self.assertEqual(len(STORAGE_TABLES), len(set(STORAGE_TABLES)))
