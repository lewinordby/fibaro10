"""HTTP validation and runtime ownership for comparison services."""

import asyncio
from datetime import datetime
import os
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
import main
from comparison_cases import Scenario
from fibaro_core.services.comparisons import windows, chart


@pytest.mark.parametrize("period,compare,expected", [("other", "previous", "Ukjent statusperiode"),
                                                    ("today", "other", "Ukjent sammenligning")])
def test_unknown_comparison_is_404_and_closes_session(period, compare, expected):
    case = Scenario(main, datetime(2026, 8, 30, 16))
    app = FastAPI()
    app.add_api_route("/comparison", main.api_v2_status_comparison)
    with case.patches():
        response = TestClient(app).get("/comparison", params={"period": period, "compare": compare})
    assert response.status_code == 404 and response.json()["detail"] == expected
    assert case.closed and case.calls == []


def test_invalid_anchor_fails_before_opening_session(monkeypatch):
    def no_session():
        raise AssertionError("session should not open")
    monkeypatch.setattr(main.revenue_http.dependencies, "async_session", no_session)
    app = FastAPI()
    app.add_api_route("/comparison", main.api_v2_status_comparison)
    response = TestClient(app).get("/comparison?anchor=not-a-date")
    assert response.status_code == 400


@pytest.mark.parametrize("period,hours", [("today", 18), ("week", 168)])
def test_complete_reference_chart_does_not_expand_comparison_totals(period, hours):
    now = datetime(2026, 8, 30, 16)
    case = Scenario(main, now)
    with case.patches():
        payload = asyncio.run(main.api_v2_status_comparison(period=period, compare="previous", anchor=None, references="none"))
    assert payload["axis"]["seconds"] == hours * 3600
    assert payload["referenceComparisons"] == []
    assert payload["comparison"]["parkingEnd"][11:19] == "11:57:00"
    assert payload["lanes"][3]["end"][11:19] == "00:00:00"
    assert len([call for call in case.calls if call[0] == "lane"]) == 4


def test_reference_is_not_duplicated_when_selected():
    case = Scenario(main, datetime(2026, 8, 30, 16))
    with case.patches():
        result = asyncio.run(main.api_v2_status_comparison(period="today", compare="same-weekday-last-week", anchor=None, references="auto"))
    assert result["referenceComparisons"] == []
    assert len(result["lanes"]) == 4


def test_failed_snapshot_propagates_and_closes_session(monkeypatch):
    case = Scenario(main, datetime(2026, 8, 30, 16))
    with case.patches():
        monkeypatch.setattr(chart, "sun2_datetime_snapshot", AsyncMock(side_effect=RuntimeError("database unavailable")))
        with pytest.raises(RuntimeError, match="database unavailable"):
            asyncio.run(main.api_v2_status_comparison(period="today", compare="previous", anchor=None, references="none"))
    assert case.closed


def test_main_reexports_existing_period_helpers():
    for name in ("status_comparison_windows", "source_as_of", "import_row_stamp", "period_cutoff",
                 "shifted_period_cutoff", "same_iso_week_previous_year", "status_timeline_position"):
        assert getattr(main, name) is getattr(windows, name)
