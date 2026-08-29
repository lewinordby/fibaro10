from system_inventory import (
    system_component_rows,
    system_component_summary,
    system_subsystem_rows,
    system_web_interface_rows,
)


def test_system_inventory_contains_core_components():
    rows = system_component_rows()
    names = {row["component"] for row in rows}

    assert "fibaro10" in names
    assert "lilletorget_mantis" in names
    assert "lilletorget_kiosk" in names
    assert "revenue_app" in names
    assert "parking_app" in names
    assert "sun_app" in names
    assert "energy_app" in names
    assert "operations_app" in names
    assert "maintenance_app" in names
    assert "system_app" in names
    assert "link_app" in names
    assert "online_dashboard" in names
    assert "owntracks_service" in names
    assert "maintenance_mobile" in names
    assert "revenue_app" in names
    assert "parking_sun_linker" in names
    assert "unifi_protect_events" in names
    assert "visual_anomaly_service" in names
    assert "fibaro10_proxy" in names
    assert "owntracks_postgres" in names
    assert "desktop_v2" not in names
    assert "shell_app" not in names
    assert "fibaro10ipad" not in names


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
    assert "lilletorget_mantis" in names
    assert "lilletorget_kiosk" in names
    assert "owntracks_service" in names
    assert "maintenance_mobile" in names
    assert "axis_camera_snapshots" in names
    assert "sun2_session_scraper" in names
    assert "unifi_protect_events" in names
    assert "revenue_app" not in names
    assert "operations_app" not in names

    for row in rows:
        assert row["web_url"] or row["local_url"]


def test_system_subsystem_catalog_has_titles_and_typed_links():
    rows = system_subsystem_rows()
    assert len(rows) == len(system_component_rows())
    assert all(row["title"] for row in rows)

    maintenance = next(row for row in rows if row["component"] == "maintenance_mobile")
    assert maintenance["access"] == "external"
    assert {link["kind"] for link in maintenance["links"]} == {"public", "local", "health"}

    internal = next(row for row in rows if row["component"] == "owntracks_postgres")
    assert internal["access"] == "internal"
    assert internal["links"] == []
