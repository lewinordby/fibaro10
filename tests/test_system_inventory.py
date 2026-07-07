from system_inventory import system_component_rows, system_component_summary, system_web_interface_rows


def test_system_inventory_contains_core_components():
    rows = system_component_rows()
    names = {row["component"] for row in rows}

    assert "fibaro10" in names
    assert "desktop_v2" in names
    assert "online_dashboard" in names
    assert "owntracks_service" in names
    assert "maintenance_mobile" in names
    assert "parking_sun_linker" in names
    assert "fibaro10_proxy" in names
    assert "owntracks_postgres" in names


def test_system_inventory_summary_counts_rows():
    rows = system_component_rows()
    summary = system_component_summary()

    assert summary["components"] == len(rows)
    assert summary["active"] >= 1
    assert summary["critical"] >= 1
    assert summary["web_interfaces"] == len(system_web_interface_rows())
    assert sum(row["count"] for row in summary["area_rows"]) == len(rows)
    assert sum(row["count"] for row in summary["status_rows"]) == len(rows)


def test_system_inventory_web_interfaces_are_clickable():
    rows = system_web_interface_rows()
    names = {row["component"] for row in rows}

    assert "online_dashboard" in names
    assert "owntracks_service" in names
    assert "maintenance_mobile" in names
    assert "axis_camera_snapshots" in names
    assert "sun2_session_scraper" in names

    for row in rows:
        assert row["web_url"] or row["local_url"]
