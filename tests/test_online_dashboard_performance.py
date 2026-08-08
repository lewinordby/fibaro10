import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://example:example@127.0.0.1:5432/example",
)

from online_dashboard.app import main as online_main  # noqa: E402


def test_energy_delta_marks_lower_consumption_as_favorable() -> None:
    assert online_main.kwh_delta(42.8, 38.1) == ("+4,7 kWh", "+12%", "is-negative")
    assert online_main.kwh_delta(35.0, 40.0) == ("-5,0 kWh", "-12%", "is-positive")


def test_generic_performance_panel_supports_operational_status() -> None:
    html = online_main.render_performance_panel(
        modifier="drift",
        label="Drift akkurat n\u00e5",
        main_value="Normal",
        updated_text="Oppdatert kl. 14:25",
        comparisons=[
            ("Klima", "23,1\u00b0", "", "", "Ute 21,4\u00b0", "/temperatur"),
            ("Ventilasjon", "1 av 4 p\u00e5", "", "", "NORMAL", "/ventilasjon"),
        ],
        stats=[
            ("Solrom", "7 ledige", "5 i bruk"),
            ("Andre d\u00f8rer", "4 lukket", "1 \u00e5pen"),
        ],
    )

    assert "detail-performance-drift" in html
    assert "Drift akkurat n\u00e5" in html
    assert "Normal" in html
    assert "Klima" in html
    assert "Ventilasjon" in html
    assert "<em>" not in html
    assert html.count('class="dashboard-performance-stat"') == 2
    assert '<span>Solrom</span><strong>7 ledige</strong><small>5 i bruk</small>' in html


def test_drift_performance_uses_door_climate_and_fan_status() -> None:
    html = online_main.render_drift_performance(
        {
            "door_alarm": {"summary": {"alarms": 0, "watch": 0, "busy": 5, "rooms": 12}},
            "solroom_doors": [{"state": "closed"}] * 5 + [{"state": "open"}] * 7,
            "other_doors": [{"state": "closed"}] * 4 + [{"state": "open"}],
            "fan_items": [("VIP", True), ("2.etg", False), ("Tak", False), ("Avfukter", False)],
            "vent": {"mode": "NORMAL", "timestamp": None},
            "inside_avg": 23.1,
            "outside": 21.4,
        }
    )

    assert "Drift akkurat nå" in html
    assert ">Normal<" in html
    assert "1 av 4 på" in html
    assert "7 ledige" in html
    assert "5 i bruk" in html
    assert "4 lukkede" in html
    assert "1 åpen" in html


def test_energy_performance_panel_has_energy_modifier() -> None:
    html = online_main.render_performance_panel(
        modifier="energy",
        label="Forbruk hittil i dag",
        main_value="42,8 kWh",
        updated_text="Per kl. 14:25",
        comparisons=[
            ("I g\u00e5r samme tidspunkt", "+4,7 kWh", "+12%", "is-negative", "8,6 kWh igjen", "/energi"),
            ("Forrige uke", "-2,4 kWh", "-5%", "is-positive", "13,2 kWh igjen", "/energi"),
        ],
        stats=[("Effekt n\u00e5", "12,6 kW", "fra HC3"), ("Uforklart", "0,8 kW", "beregnet diff")],
    )

    assert "detail-performance-energy" in html
    assert "42,8 kWh" in html
    assert "is-negative" in html
    assert "is-positive" in html
