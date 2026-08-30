"""Deterministic calculation and SQL contracts captured before extraction."""

import asyncio
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fibaro_core.services.summaries import energy, parking, periods, revenue, sun

DOMAINS = {"sun2": sun, "parking": parking, "revenue": revenue}

SNAPSHOT = Path(__file__).with_name("fixtures") / "summary_contracts.json"


def normalize(value):
    if isinstance(value, dict):
        return {str(key): normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    if isinstance(value, set):
        return sorted(normalize(item) for item in value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, SimpleNamespace):
        return normalize(vars(value))
    return value


def digest(value):
    return hashlib.sha256(json.dumps(normalize(value), sort_keys=True).encode()).hexdigest()


class Result:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class Session:
    def __init__(self, *results):
        self.results = list(results)
        self.statements = []

    async def execute(self, statement):
        compiled = statement.compile(dialect=postgresql.dialect())
        self.statements.append({"sql": str(compiled), "params": compiled.params})
        assert self.results, "Unexpected extra query"
        return Result(self.results.pop(0))


def source_rows():
    days = [date(2023, 1, 1) + timedelta(weeks=n * 3) for n in range(60)]
    days += [date(2024, 2, 29), date(2024, 12, 30), date(2025, 1, 1), date(2026, 8, 29)]
    return [
        {
            "stat_date": day,
            "room": str(n % 12 + 1),
            "total_soletid_minutter": 10 + n,
            "totalt_antall_solinger": n % 5 + 1,
            "solinger_medlemmer": n % 5,
            "solinger_ikke_medlemmer": 1,
            "totalt_inntjent_kr": Decimal("-12.50") if n % 11 == 0 else Decimal("123.45") + n,
            "inntjent_medlemmer_kr": None,
            "inntjent_ikke_medlemmer_kr": Decimal("12.50"),
            "rooms_count": n % 12 + 1,
            "rows_count": n % 5 + 1,
        }
        for n, day in reversed(list(enumerate(sorted(days))))
    ]


def parking_rows(rows):
    return [
        {"stat_date": row["stat_date"].isoformat(), "sessions": row["rows_count"],
         "paid": row["totalt_inntjent_kr"], "minutes": row["total_soletid_minutter"],
         "vehicles": row["rooms_count"]}
        for row in rows
    ]


async def capture_contracts():
    contracts = {}
    for case, rows in (("empty", []), ("mixed", source_rows())):
        sun_session = Session(rows, [])
        sun_result = await sun.build_sun2_summaries_fast(sun_session)
        parking_session = Session(parking_rows(rows))
        parking_result = await parking.build_parking_summaries_fast(parking_session)
        energy_rows = [
            {"stat_date": row["stat_date"], "consumption_kwh": Decimal("12.75"),
             "production_kwh": None, "hours_count": 23, "estimated_hours_count": 2}
            for row in rows
        ]
        bounds = [{"first_at": datetime(2023, 1, 1), "last_at": datetime(2026, 8, 29, 23)}] if rows else []
        energy_session = Session(energy_rows, bounds)
        energy_result = await energy.build_energy_summaries_fast(energy_session)
        for name, result, session in (("sun", sun_result, sun_session), ("parking", parking_result, parking_session), ("energy", energy_result, energy_session)):
            contracts[f"{case}/{name}/result"] = digest(result)
            contracts[f"{case}/{name}/queries"] = digest(session.statements)
            assert not session.results
        business = revenue.combine_business_summaries(sun_result, parking_result)
        contracts[f"{case}/revenue"] = digest(business)
        model_rows = [{key: float(value) if isinstance(value, Decimal) else value for key, value in row.items()} for row in rows]
        contracts[f"{case}/sun-legacy"] = digest(sun.build_sun2_summaries([SimpleNamespace(**row) for row in model_rows]))
        model_energy = [{key: float(value) if isinstance(value, Decimal) else value for key, value in row.items()} for row in energy_rows]
        legacy_energy = [SimpleNamespace(**row, measured_at=datetime.combine(row["stat_date"], datetime.min.time()),
                                        year=row["stat_date"].year, month=row["stat_date"].month, is_estimated=True)
                         for row in model_energy]
        contracts[f"{case}/energy-legacy"] = digest(energy.build_energy_summaries(legacy_energy))
        for domain, data in (("sun2", sun_result), ("parking", parking_result), ("revenue", business)):
            daily = getattr(DOMAINS[domain], f"{domain}_daily_by_year")(data)
            for year, day in ((2023, 31), (2024, 60), (2024, 366), (2025, 400), (2026, 241)):
                current = getattr(DOMAINS[domain], f"{domain}_year_series")(daily, year, day, "current", "#123456")
                previous = getattr(DOMAINS[domain], f"{domain}_year_series")(daily, year - 1, day, "comparison", "#654321")
                contracts[f"{case}/{domain}/{year}/{day}"] = digest({
                    "current": current, "previous": previous,
                    "delta": getattr(DOMAINS[domain], f"{domain}_year_comparison_delta")(current, previous),
                })

    periods = {
        "sun-today": (datetime(2026, 8, 30), datetime(2026, 8, 30, 12, 5)),
        "parking-today": (datetime(2026, 8, 30), datetime(2026, 8, 30, 10)),
        "previous": (datetime(2026, 8, 29), datetime(2026, 8, 29, 10)),
    }
    for domain in ("sun2", "parking"):
        session = Session([{"period_key": "previous", "sessions": 2, "paid": Decimal("49.50"), "minutes": 30, "rooms": 1}])
        value = await getattr(DOMAINS[domain], f"{domain}_datetime_snapshots")(session, periods)
        contracts[f"{domain}/cutoffs"] = digest({"result": value, "queries": session.statements})
    return contracts


@pytest.fixture(scope="module")
def captured():
    return asyncio.run(capture_contracts())


def test_calculation_and_sql_contracts_are_unchanged(captured):
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert captured.keys() == expected.keys()
    for key in expected:
        assert captured[key] == expected[key], key


def test_fast_sun_combines_imported_days_and_live_fallback_without_extra_queries():
    rows = source_rows()
    imported, live = rows[1:], rows[:1]
    session = Session(imported, live)
    result = asyncio.run(sun.build_sun2_summaries_fast(session))
    assert len(session.statements) == 2
    assert "NOT IN (SELECT DISTINCT sun2_room_daily_stats.stat_date" in session.statements[1]["sql"]
    assert result["total"]["totalt_antall_solinger"] == sum(row["totalt_antall_solinger"] for row in rows)
    assert result["total"]["totalt_inntjent_kr"] == pytest.approx(sum(float(row["totalt_inntjent_kr"]) for row in rows))
    assert len({item["period"] for item in result["daily"]}) == len(rows)
    assert result["daily"][0]["period"] == "2026-08-29"
    assert len(result["top_days"]) == len(result["top_weeks"]) == len(result["top_months"]) == 20
    assert result["total_rows"] == sum(row["rows_count"] for row in rows)


def test_combined_revenue_keeps_non_overlapping_history_and_does_not_mutate_inputs():
    sun_input = {"daily": [{"period": "2024-12-30", "totalt_inntjent_kr": 100, "totalt_antall_solinger": 2}]}
    parking_input = {"daily": [{"period": "2025-01-01", "paid": 150, "sessions": 3}]}
    before = deepcopy((sun_input, parking_input))
    result = revenue.combine_business_summaries(sun_input, parking_input)
    assert (sun_input, parking_input) == before
    assert [row["period"] for row in result["daily"]] == ["2025-01-01", "2024-12-30"]
    week = result["weekly"][0]
    assert week["period"] == "2025-W01"
    assert week["total_paid"] == 250
    assert week["sun_count"] == 2 and week["parking_count"] == 3


@pytest.mark.parametrize("prefix,year,length", [("sun2", 2024, 366), ("parking", 2025, 365), ("revenue", 2024, 366)])
def test_year_series_fills_missing_days_and_clamps_to_year(prefix, year, length):
    daily = {year: {1: {"amount": 100.50, "count": 2, "minutes": 45}, 3: {"amount": -10, "count": 1, "minutes": 20}}}
    result = getattr(DOMAINS[prefix], f"{prefix}_year_series")(daily, year, 400, "current", "#123456")
    assert len(result["points"]) == length
    assert result["daysWithData"] == 2
    assert result["points"][1]["amount"] == 0
    assert result["points"][1]["cumulativeAmount"] == 100.50
    assert result["totalAmount"] == 90.50
    assert result["totalCount"] == (0 if prefix == "revenue" else 3)
    assert result["points"][-1]["date"] == f"{year}-12-31"


@pytest.mark.parametrize("function,value_key", [("revenue_period_rank_summary", "total_paid"), ("count_period_rank_summary", "total_count")])
def test_rank_ties_and_missing_or_future_history(function, value_key):
    rows = [{"period": f"2026-{month:02d}", value_key: value}
            for month, value in enumerate([0, -5, None, 100, 100, 150, 9000, 99000], start=1)]
    arguments = (rows, 100, "2026-07", "months")
    result = getattr(revenue, function)(*arguments, *(["count"] if value_key == "total_count" else []))
    assert result["rank"] == 2
    assert result["totalPeriods"] == 4
    assert result["bestTotal"] == 150


@pytest.mark.parametrize("domain", ["sun2", "parking"])
def test_empty_periods_do_not_hit_database(domain):
    session = Session()
    assert asyncio.run(getattr(DOMAINS[domain], f"{domain}_datetime_snapshots")(session, {})) == {}
    assert not session.statements


def test_imported_day_even_with_zero_sales_takes_precedence_and_end_date_is_exclusive():
    start, end = date(2026, 8, 29), date(2026, 8, 30)
    session = Session(
        [{"stat_date": start.isoformat(), "totalt_antall_solinger": 0, "totalt_inntjent_kr": 0}],
        [{"stat_date": start, "sessions": 5, "paid": 500}, {"stat_date": end, "sessions": 6, "paid": 600}],
        [(start, 1), (end, 2)],
    )
    result = asyncio.run(sun.sun2_period_snapshot(session, start, end))
    assert result.sessions == result.paid == 0
    assert len(session.statements) == 3
    for query in session.statements:
        assert start in query["params"].values() and end in query["params"].values()
        assert "stat_date >=" in query["sql"] and "stat_date <" in query["sql"]


@pytest.mark.parametrize("domain,column", [("sun2", "started_at"), ("parking", "start_time")])
def test_time_snapshots_use_exact_supplied_cutoff_and_single_batch(domain, column):
    start = datetime(2026, 8, 30)
    cutoff = start.replace(hour=10, minute=5, second=17)
    session = Session([])
    result = asyncio.run(getattr(DOMAINS[domain], f"{domain}_datetime_snapshot")(session, start, cutoff))
    assert result.sessions == result.paid == 0
    assert len(session.statements) == 1
    query = session.statements[0]
    assert start in query["params"].values() and cutoff in query["params"].values()
    assert f"{column} >=" in query["sql"] and f"{column} <" in query["sql"]


@pytest.mark.parametrize("value,expected", [
    (datetime(2026, 1, 1, 23, 59), date(2026, 1, 1)),
    (date(2026, 1, 1), date(2026, 1, 1)),
    ("2024-02-29T12:00:00", date(2024, 2, 29)),
    ("2025-02-29", None), ("invalid", None), (None, None),
])
def test_stat_date_normalization(value, expected):
    assert periods.normalized_stat_date(value) == expected


@pytest.mark.parametrize("day,expected", [(date(2021, 1, 1), "2020-W53"), (date(2024, 12, 30), "2025-W01")])
def test_iso_week_year_is_not_assumed_to_be_calendar_year(day, expected):
    assert periods.iso_week_period(day)[0] == expected


@pytest.mark.parametrize("value,expected", [(None, 2026), ("bad", 2026), ("2030", 2026), ("1990", 2000), ("2024", 2024)])
def test_year_navigation_uses_current_year_limit(value, expected):
    year = periods.parse_anchor_year(value, 2026)
    assert year == expected
    navigation = periods.year_comparison_navigation(year, 2026)
    assert navigation["canNext"] == (year < 2026)
    assert navigation["previousAnchor"] == str(year - 1)


@pytest.mark.parametrize("day,offset,expected", [
    (date(2024, 1, 31), 1, date(2024, 2, 1)),
    (date(2026, 1, 30), -1, date(2025, 12, 1)),
    (date(2026, 12, 15), 2, date(2027, 2, 1)),
])
def test_month_shift_preserves_effective_start_of_month_behavior(day, offset, expected):
    assert periods.add_months(day, offset) == expected


def test_month_label_is_preserved():
    assert periods.month_label(date(2026, 8, 30)) == "August 2026"


if __name__ == "__main__":
    if sys.argv[1:] != ["--record"]:
        raise SystemExit("Use pytest, or --record only for an intentional calculation contract change.")
    SNAPSHOT.write_text(json.dumps(asyncio.run(capture_contracts()), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {SNAPSHOT.name}")
