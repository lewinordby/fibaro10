from __future__ import annotations

import os
from pathlib import Path
import json
import re
import unittest

from fastapi import Request

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://example:example@127.0.0.1:5432/example",
)

import main
import system_app.app.main as system_main


ROOT = Path(__file__).resolve().parents[1]
CURRENT_ROOTS = {
    "/omsetning",
    "/parkering",
    "/soling",
    "/koble",
    "/bygg",
    "/renhold",
    "/kontroll",
    "/energi",
    "/vedlikehold",
    "/operasjon",
    "/eiendeler",
    "/rapporter",
    "/system",
}


def iter_paths(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "path" and isinstance(child, str):
                yield child
            else:
                yield from iter_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_paths(child)


class ManualDocumentationTests(unittest.TestCase):
    def test_living_manual_uses_current_mantis_routes(self) -> None:
        payload = main.admin_manual_payload()
        paths = set(iter_paths(payload))

        self.assertEqual(payload["title"], "Lilletorget manual")
        self.assertEqual(len(payload["chapters"]), 10)
        self.assertGreater(len(paths), 20)
        for path in paths:
            root = "/" + path.strip("/").split("/", 1)[0]
            self.assertIn(root, CURRENT_ROOTS, path)

    def test_current_repository_manuals_name_mantis_as_primary(self) -> None:
        for relative_path in ("docs/README.md", "docs/kort-brukermanual.md"):
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("https://app.lilletorget.net", content, relative_path)
            self.assertNotIn("/status/omsetning", content, relative_path)
            self.assertNotIn("/admin/datakilder", content, relative_path)

    def test_documented_current_paths_exist_in_mantis_navigation(self) -> None:
        apps = json.loads(
            (ROOT / "system_app/app/navigation.json").read_text(encoding="utf-8")
        )["apps"]
        valid_paths = {app["basePath"].rstrip("/") for app in apps}
        for app in apps:
            for group in app["groups"]:
                for item in group["items"]:
                    suffix = "" if item["to"] == "/" else item["to"]
                    valid_paths.add(f'{app["basePath"]}{suffix}'.rstrip("/"))

        content = (ROOT / "docs/kort-brukermanual.md").read_text(encoding="utf-8")
        roots = "|".join(re.escape(path.lstrip("/")) for path in CURRENT_ROOTS)
        documented_paths = {
            match.rstrip("/")
            for match in re.findall(rf"/(?:{roots})(?:/[a-z0-9-]+)*", content)
        }
        self.assertTrue(documented_paths)
        self.assertEqual(documented_paths - valid_paths, set())

    def test_static_manual_redirects_to_current_manual(self) -> None:
        content = (ROOT / "static/manualer/sun2_driftsmanual.html").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "https://app.lilletorget.net/system/manual",
            content,
        )
        self.assertNotIn("/konto/manual", content)


class ManualAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_manual_overview_links_to_system_routes(self) -> None:
        payload = main.admin_manual_payload()
        original = system_main.core_json

        async def fake_core_json(*_args, **_kwargs):
            return payload

        system_main.core_json = fake_core_json
        try:
            request = Request(
                {
                    "type": "http",
                    "method": "GET",
                    "path": "/api/modules/manual",
                    "headers": [],
                    "query_string": b"view=oversikt",
                }
            )
            result = await system_main.manual_module(request, None, {})
        finally:
            system_main.core_json = original

        rows = result["tables"][0]["rows"]
        self.assertEqual(len(rows), 10)
        self.assertTrue(
            all(row["path"].startswith("/system/manual/") for row in rows)
        )


if __name__ == "__main__":
    unittest.main()
