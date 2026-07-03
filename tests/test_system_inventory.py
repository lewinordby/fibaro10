from system_inventory import system_component_rows, system_component_summary


def test_system_inventory_contains_core_components():
    rows = system_component_rows()
    names = {row["component"] for row in rows}

    assert "fibaro10" in names
    assert "desktop_v2" in names
    assert "online_dashboard" in names
    assert "owntracks_service" in names


def test_system_inventory_summary_counts_rows():
    rows = system_component_rows()
    summary = system_component_summary()

    assert summary["components"] == len(rows)
    assert summary["active"] >= 1
    assert summary["critical"] >= 1
    assert sum(row["count"] for row in summary["area_rows"]) == len(rows)
    assert sum(row["count"] for row in summary["status_rows"]) == len(rows)
