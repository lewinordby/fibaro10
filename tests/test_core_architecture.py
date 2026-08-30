"""Keep domain imports independent of the application runtime."""

import ast
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

from fibaro_core import database, models, schemas
from time_formatting import api_local_iso

ROOT = Path(__file__).resolve().parents[1]


def isolated_python(source, **settings):
    env = dict(os.environ, **settings)
    env.pop("DATABASE_URL", None)
    result = subprocess.run(
        [sys.executable, "-c", source], cwd=ROOT, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_core_imports_do_not_create_runtime_or_load_dotenv():
    isolated_python("""
import importlib
import pkgutil
import sys
from unittest.mock import patch
import fibaro_core

with patch('sqlalchemy.ext.asyncio.create_async_engine', side_effect=AssertionError('engine on import')), \
     patch('dotenv.load_dotenv', side_effect=AssertionError('dotenv on import')):
    for module in pkgutil.walk_packages(fibaro_core.__path__, fibaro_core.__name__ + '.'):
        importlib.import_module(module.name)
assert 'main' not in sys.modules
""")


def test_all_models_use_one_metadata_registry_and_keep_public_identity():
    import main

    tables = set()
    for name in models.__all__:
        model = getattr(models, name)
        assert getattr(main, name) is model
        assert issubclass(model, database.Base)
        assert model.__table__.metadata is database.Base.metadata
        tables.add(model.__tablename__)
    assert tables == set(database.Base.metadata.tables)
    for name in schemas.__all__:
        assert getattr(main, name) is getattr(schemas, name)


def test_domain_layers_never_import_composition_root():
    for path in (ROOT / "fibaro_core").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                assert all(alias.name != "main" for alias in node.names), path
            elif isinstance(node, ast.ImportFrom):
                assert node.module != "main", path


def test_composition_root_no_longer_declares_models_or_schemas():
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            assert not any(
                isinstance(base, ast.Name) and base.id in {"Base", "BaseModel"}
                for base in node.bases
            ), node.name


@pytest.mark.parametrize("offset,expected", [("25", -25), ("0", 0), ("-5", 0)])
def test_image_offset_config_is_available_without_main(offset, expected):
    isolated_python(
        "from fibaro_core.models.sun import Sun2TanningSessionImage\n"
        f"assert Sun2TanningSessionImage.__table__.c.offset_seconds.default.arg == {expected}",
        SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS=offset,
    )


def test_database_runtime_is_created_explicitly_with_existing_options():
    with patch.object(database, "create_async_engine") as create_engine, \
         patch.object(database, "async_sessionmaker") as create_session:
        engine, factory = database.create_database("postgresql+asyncpg://example/db")
    create_engine.assert_called_once_with("postgresql+asyncpg://example/db", echo=False)
    create_session.assert_called_once_with(create_engine.return_value, expire_on_commit=False)
    assert engine is create_engine.return_value
    assert factory is create_session.return_value


@pytest.mark.parametrize("value,expected", [
    (None, None),
    (datetime(2026, 8, 30, 12), "2026-08-30T12:00:00+02:00"),
    (datetime(2026, 1, 30, 12), "2026-01-30T12:00:00+01:00"),
    (datetime(2026, 8, 30, 10, tzinfo=timezone.utc), "2026-08-30T12:00:00+02:00"),
    (datetime(2026, 1, 30, 11, tzinfo=timezone.utc), "2026-01-30T12:00:00+01:00"),
])
def test_api_local_iso_preserves_summer_and_winter_offsets(value, expected):
    assert api_local_iso(value) == expected
