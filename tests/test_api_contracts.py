import ast
import importlib.util
import os
from pathlib import Path
import unittest

import api_contracts
import build_log


class AdminBuildApiContractTests(unittest.TestCase):
    def test_admin_builds_payload_contains_current_build_first(self) -> None:
        payload = api_contracts.admin_builds_payload()

        self.assertEqual(payload["currentBuild"], build_log.APP_BUILD)
        self.assertGreaterEqual(len(payload["rows"]), 1)
        self.assertEqual(payload["rows"][0]["build"], build_log.APP_BUILD)
        self.assertTrue(payload["rows"][0]["isCurrent"])

    def test_admin_build_payload_returns_none_for_unknown_build(self) -> None:
        self.assertIsNone(api_contracts.admin_build_payload("__missing__"))

    def test_admin_build_payload_matches_route_shape(self) -> None:
        payload = api_contracts.admin_build_payload(build_log.APP_BUILD)

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["path"], f"/admin/build/{build_log.APP_BUILD}")
        self.assertIn("headline", payload)
        self.assertIn("changes", payload)
        self.assertIsInstance(payload["changes"], list)


class OverviewApiContractTests(unittest.TestCase):
    def test_overview_year_revenue_totals_are_assigned(self) -> None:
        tree = ast.parse(Path("main.py").read_text(encoding="utf-8"))
        overview_func = next(
            node
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "api_v2_overview"
        )
        assigned_names: set[str] = set()
        for node in ast.walk(overview_func):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assigned_names.add(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                assigned_names.add(node.target.id)

        for name in ("revenue_year", "revenue_previous_year", "revenue_two_years"):
            self.assertIn(name, assigned_names)


@unittest.skipUnless(
    importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx"),
    "FastAPI/httpx dev dependencies are not installed in this Python environment.",
)
class AdminBuildApiIntegrationTests(unittest.TestCase):
    def test_admin_builds_endpoint_with_test_client(self) -> None:
        os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")
        from fastapi.testclient import TestClient
        import main

        main.PUBLIC_PATHS.add("/api/admin/builds")
        client = TestClient(main.app)

        response = client.get("/api/admin/builds")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["currentBuild"], build_log.APP_BUILD)
        self.assertRegex(response.headers["x-response-time"], r"^\d+\.\dms$")
        self.assertRegex(response.headers["server-timing"], r"^app;dur=\d+\.\d$")

        static_response = client.get("/static/lilletorget-favicon.png")
        self.assertEqual(static_response.status_code, 200)
        self.assertIn("must-revalidate", static_response.headers["cache-control"])
