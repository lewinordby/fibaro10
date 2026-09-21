import json
from datetime import datetime, timedelta
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fibaro_core.routers.batteries import create_batteries_router
from fibaro_core.services.batteries import HC3BatterySnapshot, battery_value, hc3_batteries, robot_battery


def device(identifier, battery=100, **kwargs):
    return {"id": identifier, "name": f"Sensor {identifier}", "parentId": 0,
            "properties": {"batteryLevel": battery, "batteryLowNotification": True}, **kwargs}


@pytest.mark.parametrize("raw,expected", [(0, (0, "critical")), (10, (10, "critical")),
    (20, (20, "low")), (21, (21, "ok")), (100, (100, "ok")), ("18", (18, "low")),
    (None, (None, "unknown")), (True, (None, "unknown")), ("", (None, "unknown")),
    (101, (None, "unknown")), (-1, (None, "unknown")), (float("nan"), (None, "unknown")),
    (255, (None, "critical"))])
def test_battery_protocol(raw, expected):
    assert battery_value(raw, zwave=True) == expected


def test_reserved_warning_is_zwave_only():
    assert battery_value(255) == (None, "unknown")


def test_physical_zwave_dedup_and_lowest_value():
    parent = {"id": 40, "parentId": 1, "type": "com.fibaro.zwaveDevice", "name": "Parent"}
    rows = hc3_batteries([parent, device(41, 30, parentId=40), device(42, 20, parentId=40)], [])
    assert len(rows) == 1
    assert rows[0]["level"] == 20
    assert rows[0]["status"] == "low"
    assert rows[0]["inconsistent"]
    assert len(rows[0]["channels"]) == 2


def test_critical_warning_never_becomes_255_percent_or_unknown():
    rows = hc3_batteries([
        {"id": 1, "type": "com.fibaro.zwaveDevice"}, device(2, 255, parentId=1), device(3, 60, parentId=1),
    ], [])
    assert rows[0]["level"] is None
    assert rows[0]["status"] == "critical"
    assert rows[0]["lowBatteryWarning"]


def test_notification_setting_and_modified_are_not_current_alarm_or_report_time():
    row = hc3_batteries([device(2, 100, modified=1787810000)], [])[0]
    assert row["status"] == "ok"
    assert row["reportedAt"] is None


def test_quickapp_groups_by_module_not_parent_and_never_exposes_variables():
    def module(identifier, module_id):
        row = device(identifier, 50, parentId=99, name="Humidity VIP")
        row["properties"]["quickAppVariables"] = [
            {"name": "module_id", "value": module_id}, {"name": "device_id", "value": "station"},
            {"name": "access_token", "value": "DO-NOT-EXPOSE"},
        ]
        return row
    rows = hc3_batteries([
        {"id": 99, "name": "Netatmo 2.6.1"}, module(1, "a"), module(2, "a"), module(3, "b"),
        device(4, parentId=99), device(5, parentId=99),
    ], [])
    assert len(rows) == 4
    assert rows[0]["name"] == "VIP"
    assert rows[0]["source"] == "Netatmo"
    assert "DO-NOT-EXPOSE" not in json.dumps(rows)


def test_catalog_names_but_not_invented_mapping_for_old_door():
    rows = hc3_batteries([device(499), device(545)], [], [
        {"device_id": 545, "title": "Inngang", "group_key": "andre"},
    ])
    assert [row["name"] for row in rows] == ["Sensor 499", "Inngang"]


def test_unknown_battery_and_unavailable_devices_remain_visible():
    rows = hc3_batteries([
        device(1, properties={"batteryLevel": None, "dead": True}, enabled=False),
        {"id": 2, "interfaces": ["battery"]}, {"id": 3, "properties": {"power": 100}},
    ], [])
    assert len(rows) == 2
    assert rows[0]["unavailable"] and rows[0]["disabled"]
    assert rows[0]["status"] == "unknown"


def test_robot_latest_time_is_local_and_low_charging_not_replacement_alarm():
    now = datetime(2026, 9, 21, 12, 30)
    robot = SimpleNamespace(duid="aqua", name="Aqua10", provider="dreame", model="Aqua10", product=None,
                            cloud_online=True, integration_status="active")
    sample = SimpleNamespace(timestamp=now, battery=15, is_charging=True, state_name="Lader")
    old = SimpleNamespace(timestamp=now - timedelta(hours=1), battery=0, state_name="Tom")
    row = robot_battery(robot, [old, sample], now)
    assert row["level"] == 15 and row["charging"] and row["rechargeable"]
    assert row["reportedAt"] == "2026-09-21T12:30:00+02:00"
    assert not row["stale"]
    assert robot_battery(robot, [old], now)["stale"]
    assert robot_battery(robot, [], now)["status"] == "unknown"


def test_cache_failure_preserves_last_success_without_claiming_fresh_data():
    reader = Mock(side_effect=[[device(1)], RuntimeError("private hostname")])
    snapshot = HC3BatterySnapshot(reader, "http://hc3", lambda: "secret", ttl=60)
    with patch("urllib.request.urlopen", return_value=BytesIO(b"[]")):
        first = snapshot.read()
    snapshot.read()
    assert reader.call_count == 1
    snapshot.expires_at = 0
    failed = snapshot.read()
    assert failed["rows"] == first["rows"]
    assert failed["checkedAt"] == first["checkedAt"]
    assert failed["error"] and "private hostname" not in failed["error"]


def test_rooms_failure_does_not_hide_battery_devices():
    snapshot = HC3BatterySnapshot(lambda _: [device(1)], "http://hc3", lambda: "secret")
    with patch("urllib.request.urlopen", side_effect=RuntimeError("offline")):
        result = snapshot.read()
    assert len(result["rows"]) == 1 and result["roomsError"] and not result["error"]


def test_api_reports_partial_failure_and_never_hides_hc3_rows():
    snapshot = Mock()
    snapshot.read.return_value = {"rows": hc3_batteries([device(1)], []), "checkedAt": None,
                                  "error": None, "roomsError": None}
    def broken_session():
        raise RuntimeError("DB unavailable")
    app = FastAPI()
    app.include_router(create_batteries_router(broken_session, snapshot))
    with TestClient(app) as client:
        response = client.get("/api/system/batteries")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert len(response.json()["devices"]) == 1
    assert response.json()["errors"]
