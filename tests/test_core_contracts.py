"""Freeze public contracts before splitting the composition root into modules."""

import hashlib
import inspect
import json
import os
from pathlib import Path
import sys

import pytest
from fastapi.routing import APIRoute
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@127.0.0.1/test")

import main

SNAPSHOT = Path(__file__).with_name("fixtures") / "core_contracts.json"


def fingerprint(value):
    def json_default(item):
        return sorted(item) if isinstance(item, (set, frozenset)) else str(item)

    encoded = json.dumps(value, sort_keys=True, ensure_ascii=True, default=json_default)
    return hashlib.sha256(encoded.encode()).hexdigest()


def column_default(column, default):
    if default is None:
        return None
    if column.table.name == "sun2_tanning_session_images" and column.name == "offset_seconds":
        return "-SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS"
    arg = default.arg
    if callable(arg):
        return inspect.unwrap(arg).__qualname__
    return str(arg)


def api_routes(routes):
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif getattr(route, "original_router", None) is not None:
            # FastAPI 0.139 retains included routers instead of flattening them.
            assert not route.include_context.prefix
            yield from api_routes(route.original_router.routes)


def current_contracts():
    dialect = postgresql.dialect()
    tables = {}
    for name, table in main.Base.metadata.tables.items():
        tables[name] = fingerprint({
            "ddl": str(CreateTable(table).compile(dialect=dialect)),
            "indexes": sorted(str(CreateIndex(index).compile(dialect=dialect)) for index in table.indexes),
            "defaults": {
                column.name: [column_default(column, column.default), column_default(column, column.onupdate)]
                for column in table.columns
            },
        })
    schema = main.app.openapi()
    return {
        "definitions": {
            name: fingerprint(value)
            for name, value in vars(main).items()
            if name.endswith("_COLUMNS") or name in {"AI_DATASETS", "PERFORMANCE_INDEXES", "ROBOROCK_TELEMETRY_DISPLAY_FIELDS"}
        },
        "tables": tables,
        "schemas": {
            name: fingerprint(value)
            for name, value in schema.get("components", {}).get("schemas", {}).items()
        },
        "operations": {
            f"{method.upper()} {path}": fingerprint(operation)
            for path, methods in schema["paths"].items()
            for method, operation in methods.items()
        },
        "route_order": [
            [route.path, sorted(route.methods), route.name]
            for route in api_routes(main.app.routes)
        ],
    }


@pytest.fixture(scope="module")
def contracts():
    return current_contracts()


@pytest.mark.parametrize("section", ["definitions", "tables", "schemas", "operations", "route_order"])
def test_core_contracts_unchanged(contracts, section):
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert contracts[section] == expected[section]


def test_configured_image_offset_default_is_preserved():
    default = main.Sun2TanningSessionImage.__table__.c.offset_seconds.default.arg
    assert default == -main.SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS


if __name__ == "__main__":
    if sys.argv[1:] != ["--record"]:
        raise SystemExit("Use pytest, or --record when intentionally changing public contracts.")
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(current_contracts(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Recorded {SNAPSHOT.name}")
