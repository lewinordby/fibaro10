from datetime import date, datetime
import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")

from fibaro_core.schemas.system import AssetRegistryInput, AutomationWorkbenchInput
from fibaro_core.services.assets import (
    apply_asset_registry_input,
    asset_registry_payload,
)
from fibaro_core.services.automations import (
    apply_automation_workbench_input,
    automation_workbench_payload,
)
from observability import STORAGE_TABLES
from system_app.app.main import MODULES


def test_asset_registry_round_trip_payload() -> None:
    now = datetime(2026, 8, 17, 12, 0)
    row = SimpleNamespace(created_at=now, updated_at=now, extra=None)
    apply_asset_registry_input(
        row,
        AssetRegistryInput(
            name="Robot 1.etg A",
            category="Robotvasker",
            location="1.etg",
            manufacturer="Roborock",
            model="S8",
            serial_no="TEST-1",
            owner_app="Bygg og drift",
            status="I drift",
            service_interval_days=30,
            last_service_at=date(2026, 8, 1),
        ),
        now,
    )
    row.id = 1
    row.hc3_device_id = None
    row.installed_at = None
    row.warranty_until = None
    payload = asset_registry_payload(row)
    assert payload["navn"] == "Robot 1.etg A"
    assert payload["neste vedlikehold"] == date(2026, 8, 31)


def test_automation_workbench_preserves_readable_rule_text() -> None:
    now = datetime(2026, 8, 17, 12, 0)
    row = SimpleNamespace(
        id=2,
        created_at=now,
        updated_at=now,
        last_evaluated_at=None,
        last_triggered_at=None,
        last_result=None,
    )
    apply_automation_workbench_input(
        row,
        AutomationWorkbenchInput(
            name="Varsle ved gammel EasyPark-import",
            domain="System",
            trigger_type="Datakilde",
            trigger="EasyPark er eldre enn planlagt",
            conditions='{"minutter": 150}',
            actions="Opprett hendelse og send ntfy",
            mode="Observer",
        ),
        now,
    )
    payload = automation_workbench_payload(row)
    assert payload["modus"] == "Observer"
    assert "EasyPark" in payload["trigger"]
    assert '"minutter": 150' in payload["betingelser"]


def test_workspaces_are_migrated_and_exposed() -> None:
    migration = Path("migrations/versions/20260817_1200_add_assets_and_automation_workbench.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS asset_registry_items" in migration
    assert "CREATE TABLE IF NOT EXISTS automation_workbench_rules" in migration
    assert "asset_registry_items" in STORAGE_TABLES
    assert "automation_workbench_rules" in STORAGE_TABLES
    for module in ("modules/operasjon", "modules/eiendeler", "modules/automatisering", "modules/rapporter", "modules/sok"):
        assert module in MODULES
