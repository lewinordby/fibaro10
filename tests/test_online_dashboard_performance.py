import asyncio
import os
from datetime import datetime, timedelta

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


def test_drift_robot_entry_links_to_full_robot_overview() -> None:
    html = online_main.render_robot_drift_entry(
        [
            {"name": "1.etg A", "status": "ok", "status_at": datetime(2026, 8, 14, 16, 37)},
            {"name": "1.etg B", "status": "active", "status_at": datetime(2026, 8, 14, 16, 38)},
            {"name": "Aqua10", "status": "pending", "status_at": None},
        ]
    )

    assert 'href="/renhold"' in html
    assert "1 rengjør nå" in html
    assert "1 må følges opp" in html
    assert "Klare" in html
    assert "Oppfølging" in html
    assert "Rengjør nå" in html
    assert "Sist lest kl. 16:38" in html


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


def test_mobile_robot_overview_shows_status_battery_and_latest_job() -> None:
    robots = [
        {
            "name": "1.etg A",
            "provider": "roborock",
            "status": "ok",
            "state_label": "Lader",
            "battery": 96,
            "status_at": online_main.datetime(2026, 8, 14, 14, 20),
            "job_started_at": online_main.datetime(2026, 8, 14, 5, 0),
            "job_duration_minutes": 61,
            "job_area_m2": 39.4,
            "job_status": "Fullført",
        },
        {
            "name": "Aqua10",
            "provider": "dreame",
            "status": "pending",
            "state_label": "Venter på konto",
            "battery": None,
            "status_at": None,
            "job_started_at": None,
            "job_status": "Ingen jobb registrert",
        },
    ]

    html = online_main.render_robot_overview_cards(robots)

    assert "1.etg A" in html
    assert "Lader" in html
    assert "96%" in html
    assert "61 min" in html
    assert "39,4 m²" in html
    assert "Aqua10" in html
    assert "Venter på konto" in html
    assert online_main.robot_overview_summary(robots) == "1 klare · 1 må følges opp"


def test_mobile_robot_state_prioritizes_active_and_error_states() -> None:
    now = datetime(2026, 8, 14, 16, 0)
    assert online_main.mobile_robot_state(
        {"state_code": 6, "in_cleaning": True}, status_at=now, now=now
    ) == ("Rengjør", "active")
    assert online_main.mobile_robot_state(
        {"state_code": 7, "in_cleaning": False}, status_at=now, now=now
    ) == ("Returnerer", "active")
    assert online_main.mobile_robot_state(
        {"provider": "dreame", "state_code": 6, "state_name": "charging", "in_cleaning": False},
        status_at=now,
        now=now,
    ) == ("Lader", "ok")
    assert online_main.mobile_robot_state({"state_code": 8, "error_code": 12}) == ("Feil", "error")
    assert online_main.mobile_robot_state({"integration_status": "pending"}) == ("Venter på konto", "pending")


def test_mobile_robot_state_never_reports_stale_or_offline_activity_as_active() -> None:
    now = datetime(2026, 8, 14, 16, 0)
    stale = now - timedelta(minutes=21)

    assert online_main.mobile_robot_state(
        {"state_code": 6, "in_cleaning": True, "cloud_online": False},
        status_at=now,
        now=now,
    ) == ("Frakoblet", "error")
    assert online_main.mobile_robot_state(
        {"state_code": 6, "in_cleaning": True, "cloud_online": True},
        status_at=stale,
        now=now,
    ) == ("Utdatert status", "warning")
    assert online_main.mobile_robot_state(
        {"state_code": 4, "cloud_online": True},
        now=now,
    ) == ("Utdatert status", "warning")


def test_mobile_robot_overview_uses_freshest_sample_and_keeps_status_in_local_time(monkeypatch) -> None:
    captured = {}

    async def fake_many_mappings(query, params=None):
        captured["query"] = query
        return [
            {
                "duid": "robot-a",
                "name": "1.etg A",
                "provider": "roborock",
                "integration_status": "active",
                "cloud_online": True,
                "status_at": datetime(2026, 8, 14, 14, 20),
                "state_code": 8,
                "state_name": "charging",
                "battery": 96,
                "error_code": 0,
                "in_cleaning": False,
                "job_started_at": datetime(2026, 8, 14, 12, 20),
                "job_ended_at": datetime(2026, 8, 14, 13, 20),
                "job_duration_minutes": 60,
                "job_area_m2": 39.4,
                "job_complete": True,
                "job_error_code": 0,
            }
        ]

    monkeypatch.setattr(online_main, "many_mappings", fake_many_mappings)
    monkeypatch.setattr(online_main, "local_now", lambda: datetime(2026, 8, 14, 14, 25))

    robots = asyncio.run(online_main.mobile_robot_overview())

    assert "roborock_telemetry_samples" in captured["query"]
    assert "telemetry.timestamp >= status.timestamp" in captured["query"]
    assert robots[0]["status_at"] == datetime(2026, 8, 14, 14, 20)
    assert robots[0]["job_started_at"] == datetime(2026, 8, 14, 14, 20)
    assert robots[0]["state_label"] == "Lader"
    assert robots[0]["status"] == "ok"
