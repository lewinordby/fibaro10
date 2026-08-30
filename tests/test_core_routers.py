"""Exercise extracted routers over HTTP without a database or app startup."""

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from fibaro_core.models.system import AssetRegistryItem, AutomationWorkbenchRule
from fibaro_core.routers.assets import create_assets_router
from fibaro_core.routers.automations import create_automations_router


def result(rows):
    value = Mock()
    value.all.return_value = rows
    value.scalars.return_value.all.return_value = rows
    return value


@pytest.fixture
def runtime():
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.add = Mock()
    session.execute.return_value = result([])
    session.get.return_value = None
    factory = Mock(return_value=session)
    authorize = Mock(return_value=None)
    app = FastAPI()
    app.include_router(create_assets_router(factory, authorize))
    app.include_router(create_automations_router(factory, authorize))
    return SimpleNamespace(client=TestClient(app), session=session, factory=factory, authorize=authorize)


def test_asset_listing_keeps_filters_and_order(runtime):
    response = runtime.client.get("/api/system/assets", params={"q": "  Robot  ", "category": "Robotvasker", "status": "I drift"})
    assert response.status_code == 200
    assert response.json()["assets"] == []
    query = runtime.session.execute.call_args.args[0]
    compiled = query.compile(dialect=postgresql.dialect())
    assert "%Robot%" in compiled.params.values()
    assert "Robotvasker" in compiled.params.values()
    assert "I drift" in compiled.params.values()
    assert "ORDER BY asset_registry_items.category, asset_registry_items.location, asset_registry_items.name" in str(compiled)
    runtime.session.commit.assert_not_called()


def test_asset_create_preserves_fields_and_dates(runtime):
    response = runtime.client.post("/api/system/assets", json={
        "name": "  Aqua10  ", "category": "Robotvasker", "manufacturer": " Dreame ",
        "last_service_at": "2026-08-01", "service_interval_days": 30,
    })
    assert response.status_code == 200
    payload = response.json()["asset"]
    assert payload["navn"] == "Aqua10"
    assert payload["produsent"] == "Dreame"
    assert payload["neste vedlikehold"] == "2026-08-31"
    assert payload["oppdatert"].endswith(("+02:00", "+01:00"))
    row = runtime.session.add.call_args.args[0]
    assert isinstance(row, AssetRegistryItem)
    assert row.last_service_at == date(2026, 8, 1)
    runtime.session.commit.assert_awaited_once()
    runtime.session.refresh.assert_awaited_once_with(row)


def test_asset_update_preserves_route_identity(runtime):
    row = AssetRegistryItem(id=7, name="Old", category="Annet")
    runtime.session.get.return_value = row
    response = runtime.client.patch("/api/system/assets/7", json={"name": "New", "hc3_device_id": 511})
    assert response.status_code == 200
    assert response.json()["asset"]["id"] == 7
    assert row.name == "New"
    assert row.hc3_device_id == 511
    runtime.session.get.assert_awaited_once_with(AssetRegistryItem, 7)
    runtime.session.commit.assert_awaited_once()


@pytest.mark.parametrize("path", ["/api/system/assets/999", "/api/system/automations/999"])
def test_update_missing_object_stays_404(runtime, path):
    response = runtime.client.patch(path, json={"name": "Missing"})
    assert response.status_code == 404
    assert response.json()["detail"]
    runtime.session.commit.assert_not_called()


@pytest.mark.parametrize("method,path,payload", [
    ("post", "/api/system/assets", {"name": "Robot"}),
    ("patch", "/api/system/assets/1", {"name": "Robot"}),
    ("post", "/api/system/assets/discover", None),
    ("post", "/api/system/automations", {"name": "Rule"}),
    ("patch", "/api/system/automations/1", {"name": "Rule"}),
])
def test_writes_require_settings_access_before_database(runtime, method, path, payload):
    runtime.authorize.return_value = JSONResponse({"detail": "Forbidden"}, status_code=403)
    response = getattr(runtime.client, method)(path, json=payload)
    assert response.status_code == 403
    runtime.authorize.assert_called_once()
    runtime.factory.assert_not_called()


@pytest.mark.parametrize("path,payload", [
    ("/api/system/assets", {"name": "x"}),
    ("/api/system/assets", {"name": "Robot", "hc3_device_id": 0}),
    ("/api/system/assets", {"name": "Robot", "service_interval_days": 0}),
    ("/api/system/automations", {"name": "Rule", "cooldown_minutes": -1}),
])
def test_invalid_payload_remains_422_without_database_work(runtime, path, payload):
    response = runtime.client.post(path, json=payload)
    assert response.status_code == 422
    runtime.factory.assert_not_called()


def test_discovery_uses_canonical_robot_identity_and_deduplicates(runtime):
    bed = SimpleNamespace(name="Solrom 1", display_room_number=1, physical_room_number=1,
                          room_id="1", bed_model="Q14", sun2_bed_id="bed-1")
    robot = SimpleNamespace(name="Aqua10", provider="dreame", model="Aqua10", product=None,
                            serial_number="serial", integration_status="active", duid="dreame:robot-1")
    node = SimpleNamespace(id=3, name="Kurs 6", area="VIP", manufacturer="Qubino", model="Meter",
                           hc3_device_id=527, hc3_power_device_id=None, node_type="meter")
    runtime.session.execute.side_effect = [
        result([("Solseng", "SOLROM 1")]),
        result([bed, SimpleNamespace(name="."), SimpleNamespace(name="")]),
        result([robot, robot]), result([node]),
    ]
    response = runtime.client.post("/api/system/assets/discover")
    assert response.status_code == 200
    assert response.json()["created"] == 2
    added = [call.args[0] for call in runtime.session.add.call_args_list]
    assert added[0].extra == {"robotUid": "dreame:robot-1"}
    assert added[0].manufacturer == "Dreame"
    assert added[0].status == "I drift"
    assert added[1].extra == {"energyNodeId": 3, "nodeType": "meter"}
    runtime.session.commit.assert_awaited_once()


def test_automation_listing_preserves_order(runtime):
    response = runtime.client.get("/api/system/automations")
    assert response.status_code == 200
    assert response.json()["automations"] == []
    query = str(runtime.session.execute.call_args.args[0])
    assert "ORDER BY automation_workbench_rules.enabled DESC, automation_workbench_rules.domain, automation_workbench_rules.name" in query


def test_automation_create_stores_configuration_without_executing_it(runtime):
    response = runtime.client.post("/api/system/automations", json={
        "name": "  Test rule ", "trigger": "Plain text", "conditions": '{"minutes": 15}',
        "actions": '["notify"]', "mode": "Observer", "enabled": True,
    })
    assert response.status_code == 200
    row = runtime.session.add.call_args.args[0]
    assert isinstance(row, AutomationWorkbenchRule)
    assert row.name == "Test rule"
    assert row.trigger_config == {"beskrivelse": "Plain text"}
    assert row.conditions == {"minutes": 15}
    assert row.actions == {"verdi": ["notify"]}
    assert response.json()["automation"]["modus"] == "Observer"
    runtime.session.commit.assert_awaited_once()


def test_automation_update_keeps_evaluation_history(runtime):
    row = AutomationWorkbenchRule(id=9, name="Old", last_evaluated_at=datetime(2026, 8, 1, 12), last_result="Observed")
    runtime.session.get.return_value = row
    response = runtime.client.patch("/api/system/automations/9", json={"name": "Updated", "cooldown_minutes": 20})
    assert response.status_code == 200
    assert row.name == "Updated"
    assert row.last_result == "Observed"
    assert row.last_evaluated_at == datetime(2026, 8, 1, 12)
    assert response.json()["automation"]["ventetid min"] == 20


def test_commit_error_is_not_reported_as_success(runtime):
    runtime.session.commit.side_effect = RuntimeError("database unavailable")
    with pytest.raises(RuntimeError, match="database unavailable"):
        runtime.client.post("/api/system/assets", json={"name": "Robot"})
    runtime.session.__aexit__.assert_awaited_once()
