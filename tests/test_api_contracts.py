import ast
from datetime import datetime
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
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


class ApiPayloadContractTests(unittest.TestCase):
    def test_api_pick_only_includes_extra_when_requested(self) -> None:
        os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")
        import main

        row = SimpleNamespace(value=42, extra={"device": "HC3", "metadata": "repeated"})

        self.assertEqual(main.api_pick(row, ["value"]), {"value": 42})
        self.assertEqual(
            main.api_pick(row, ["value", "extra"]),
            {"value": 42, "extra": {"device": "HC3", "metadata": "repeated"}},
        )


class OverviewApiContractTests(unittest.TestCase):
    def test_overview_year_revenue_totals_are_present(self) -> None:
        from fibaro_core.services.comparisons.overview import (
            OverviewComparisons, build_overview_cards, overview_comparison_plan,
        )
        plan = overview_comparison_plan([], datetime(2026, 8, 30, 16))
        sun, full, parking = {}, {}, {}
        for period in plan.periods:
            for window in (period.current, period.previous, period.extra):
                sun[window.key] = SimpleNamespace(paid=100, sessions=1)
                parking[window.key] = SimpleNamespace(paid=20, sessions=2)
            for window in (period.previous, period.extra):
                full[window.key] = SimpleNamespace(paid=200, sessions=3)
                parking[window.key + "_full"] = SimpleNamespace(paid=40, sessions=4)
        year = build_overview_cards(OverviewComparisons(plan, full, sun, parking), {}, {}, "revenue")[3]
        self.assertEqual(year["total"], 120)
        self.assertEqual(year["previousTotal"], 120)
        self.assertEqual(year["previousFullTotal"], 240)
        self.assertEqual(year["extraComparisons"][0]["total"], 120)
        self.assertEqual(year["extraComparisons"][0]["fullTotal"], 240)

    def test_overview_uses_batched_period_queries(self) -> None:
        tree = ast.parse(Path("fibaro_core/services/comparisons/overview.py").read_text(encoding="utf-8"))
        overview_func = next(
            node
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "load_overview_comparisons"
        )
        called_names = {
            node.func.id
            for node in ast.walk(overview_func)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }

        self.assertIn("sun2_period_snapshots", called_names)
        self.assertIn("sun2_datetime_snapshots", called_names)
        self.assertIn("parking_datetime_snapshots", called_names)
        self.assertNotIn("sun2_period_snapshot", called_names)
        self.assertNotIn("sun2_datetime_snapshot", called_names)
        self.assertNotIn("parking_datetime_snapshot", called_names)


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

        manifest_response = client.get("/manifest.webmanifest")
        self.assertEqual(manifest_response.status_code, 200)
        self.assertEqual(manifest_response.json()["short_name"], "Fibaro10")
        self.assertTrue(manifest_response.headers["content-type"].startswith("application/manifest+json"))
