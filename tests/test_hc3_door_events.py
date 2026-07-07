import ast
from pathlib import Path

from import_jobs import IMPORT_JOB_DEFINITIONS
from observability import STORAGE_TABLES


def test_door_event_api_route_is_registered():
    tree = ast.parse(Path("main.py").read_text(encoding="utf-8"))
    routes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.args
                    and isinstance(decorator.args[0], ast.Constant)
                ):
                    routes.append(decorator.args[0].value)

    assert "/api/hc3/door-events" in routes
    assert "/api/hc3/door-events/json" in routes
    assert "/api/hc3/doors/status" in routes


def test_door_event_datakilde_and_storage_are_registered():
    definition = IMPORT_JOB_DEFINITIONS["hc3_door_events"]

    assert definition["title"] == "Dørhendelser fra HC3"
    assert definition["source"] == "HC3"
    assert "door_events" in STORAGE_TABLES


def test_hc3_door_lua_contains_expected_devices_and_endpoint():
    lua = Path("scripts/hc3_door_event_logger.lua").read_text(encoding="utf-8")

    for device_id in ("453", "447", "413"):
        assert f"{device_id} value" in lua
        assert f"[{device_id}]" in lua

    assert "/api/hc3/door-events" in lua
