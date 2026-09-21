import json
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fibaro_core.routers.batteries import create_batteries_router
from fibaro_core.services.batteries import HC3BatterySnapshot, battery_value, hc3_batteries


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
    assert rows[0]["name"] == "Klimaføler – VIP"
    assert rows[0]["source"] == "Netatmo"
    assert "DO-NOT-EXPOSE" not in json.dumps(rows)


def test_replaced_entrance_sensors_are_not_presented_as_current_door():
    rows = hc3_batteries([device(i, type="com.fibaro.doorSensor") for i in (499, 541, 545)], [], [
        {"device_id": 545, "title": "Inngang", "device_key": "door_inngang", "group_key": "andre"},
    ])
    assert [row["retired"] for row in rows] == [True, True, False]
    assert rows[0]["name"] == rows[1]["name"] == "Tidligere inngangsføler"
    assert "HC3-ID 545" in rows[1]["identificationNote"]
    assert rows[2]["name"] == "Dørføler – Inngang"
    assert rows[2]["location"] == "1.etg"


def test_catalog_override_wins_if_old_sensor_is_repurposed():
    row = hc3_batteries([device(541, type="com.fibaro.doorSensor")], [], [
        {"device_id": 541, "title": "Ny dør", "device_key": "other"},
    ])[0]
    assert row["name"] == "Dørføler – Ny dør" and not row["retired"]


def test_solroom_uses_physical_room_and_department_not_generic_hc3_name():
    row = hc3_batteries([device(543, name="148.0 Door Sensor", roomID=219)], [{"id": 219, "name": "Default"}], [
        {"device_id": 543, "title": "Solrom 3", "group_key": "solrom", "section_title": "1.etg"},
    ])[0]
    assert row["name"] == "Dørføler – Solrom 3" and row["location"] == "1.etg"
    assert row["primaryDeviceId"] == 543
    assert row["channels"][0]["name"] == "148.0 Door Sensor"


def test_unmapped_sensor_is_honest_about_unknown_location():
    row = hc3_batteries([
        {"id": 215, "name": "Z-Wave Node 54", "type": "com.fibaro.zwaveDevice"},
        device(216, 255, parentId=215, name="54.0 Temperature Sensor", type="com.fibaro.temperatureSensor", roomID=219),
        device(217, 255, parentId=215, type="com.fibaro.humiditySensor", roomID=219),
    ], [{"id": 219, "name": "Default"}])[0]
    assert row["name"] == "Temperatur- og fuktføler"
    assert row["location"] == "Plassering må avklares"
    assert row["hc3Node"] == 54 and row["primaryDeviceId"] == 216
    assert row["identificationNote"] and row["status"] == "critical"


def test_location_uses_named_sibling_instead_of_default_room():
    row = hc3_batteries([
        {"id": 430, "name": "Z-Wave Node 91", "type": "com.fibaro.zwaveDevice"},
        device(431, parentId=430, name="91.0 Motion Sensor", type="com.fibaro.motionSensor", roomID=219),
        device(433, parentId=430, name="91.0 Lys ute", type="com.fibaro.lightSensor", roomID=224),
    ], [{"id": 219, "name": "Default"}, {"id": 224, "name": "Ute"}])[0]
    assert row["name"] == "Multisensor – Ute" and row["location"] == "Ute"


def test_netatmo_station_is_not_mistaken_for_module_location():
    row = device(362, 18, name="Humidity SUN2 (Loft Sør) innluft vip", parentId=338, roomID=225)
    row["properties"]["quickAppVariables"] = [{"name": "module_id", "value": "a"}, {"name": "device_id", "value": "b"}]
    result = hc3_batteries([{"id": 338, "name": "Netatmo 2.6.1"}, row], [{"id": 225, "name": "Loft sør"}])[0]
    assert result["name"] == "Klimaføler – Innluft VIP" and result["location"] == "Loft sør"


def test_unknown_battery_and_unavailable_devices_remain_visible():
    rows = hc3_batteries([
        device(1, properties={"batteryLevel": None, "dead": True}, enabled=False),
        {"id": 2, "interfaces": ["battery"]}, {"id": 3, "properties": {"power": 100}},
    ], [])
    assert len(rows) == 2
    assert rows[0]["unavailable"] and rows[0]["disabled"]
    assert rows[0]["status"] == "unknown"


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


def test_api_is_hc3_only_and_preserves_rooms_failure_warning():
    snapshot = Mock()
    snapshot.read.return_value = {"rows": hc3_batteries([device(1)], []), "checkedAt": None,
                                  "error": None, "roomsError": "Romnavn kunne ikke oppdateres fra HC3."}
    app = FastAPI()
    app.include_router(create_batteries_router(snapshot))
    with TestClient(app) as client:
        response = client.get("/api/system/batteries")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert len(response.json()["devices"]) == 1
    assert response.json()["errors"]


def test_retired_devices_sort_after_active_sensors():
    snapshot = Mock()
    rows = hc3_batteries([device(541, 0, type="com.fibaro.doorSensor"), device(545, 100)], [])
    snapshot.read.return_value = {"rows": rows, "checkedAt": None, "error": None, "roomsError": None}
    app = FastAPI()
    app.include_router(create_batteries_router(snapshot))
    with TestClient(app) as client:
        devices = client.get("/api/system/batteries").json()["devices"]
    assert [row["primaryDeviceId"] for row in devices] == [545, 541]
