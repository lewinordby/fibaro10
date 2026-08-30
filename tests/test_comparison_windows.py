"""Explicit boundary checks in addition to pre-refactor payload fingerprints."""

import asyncio
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from fibaro_core.services.comparisons import overview, windows
from comparison_cases import imports_at, snapshot, summaries


def test_last_success_is_independent_per_source_and_new_failures_do_not_advance_it():
    now = datetime(2026, 8, 30, 16)
    rows = imports_at(now)
    actual = windows.status_comparison_windows(rows, now)
    assert actual == windows.status_comparison_windows(rows, now + timedelta(hours=2))
    for period in actual.values():
        assert period["current"]["sunEnd"] == rows[0]["last_success_at"]
        assert period["current"]["parkingEnd"] == rows[1]["last_success_at"]
        for reference in period["comparisons"]:
            assert reference["sunEnd"].time() == rows[0]["last_success_at"].time()
            assert reference["parkingEnd"].time() == rows[1]["last_success_at"].time()


@pytest.mark.parametrize("month,expected", [(1, 11), (8, 12)])
def test_utc_success_is_converted_to_oslo_before_comparison(month, expected):
    stamp = datetime(2026, month, 30, 10, 5, 17, tzinfo=timezone.utc)
    now = datetime(2026, month, 30, 16)
    rows = [{"job_name": "sun2_sessions_import", "last_success_at": stamp}]
    assert windows.source_as_of(rows, "sun2_sessions_import", now) == now.replace(hour=expected, minute=5, second=17)


def test_missing_and_future_source_times_retain_existing_fallback_policy():
    now = datetime(2026, 8, 30, 16)
    fallback = now - timedelta(hours=1)
    assert windows.source_as_of([], "missing", now) == now
    assert windows.source_as_of([], "missing", now, fallback) == fallback
    assert windows.source_as_of(imports_at(now, "future"), "sun2_sessions_import", now) == now


def test_cutoffs_do_not_cross_period_limits():
    start, end = datetime(2026, 8, 30), datetime(2026, 8, 31)
    assert windows.period_cutoff(start, end, start - timedelta(days=1)) == start
    assert windows.period_cutoff(start, end, end + timedelta(days=1)) == end
    assert windows.shifted_period_cutoff(start, start - timedelta(hours=1), start, end) == start
    assert windows.selected_period_cutoff(start, end, start, False) == end


def test_previous_month_clamps_shorter_reference_and_year_keeps_ordinal_alignment():
    now = datetime(2024, 3, 31, 16)
    rows = [{"job_name": name, "last_success_at": now} for name in ("sun2_sessions_import", "easypark_parking_import")]
    plan = overview.overview_comparison_plan(rows, now)
    month, year = plan.periods[2:]
    assert month.previous.sun_end == month.previous.parking_end == datetime(2024, 3, 1)
    assert year.previous.sun_end == datetime(2023, 4, 1, 16)
    assert year.extra.sun_end == datetime(2022, 4, 1, 16)


def test_iso_week_53_uses_last_available_week_in_previous_iso_year():
    assert windows.same_iso_week_previous_year(date(2021, 1, 1)) == (date(2019, 12, 23), 2019)
    assert windows.week_label(date(2021, 1, 1)) == "Uke 53, 2020"


def test_past_periods_are_complete_and_future_anchor_is_clamped():
    now = datetime(2026, 8, 30, 16)
    rows = imports_at(now, "stale")
    past = windows.status_comparison_windows(rows, now, date(2026, 7, 15))
    assert past["today"]["current"]["sunEnd"] == datetime(2026, 7, 16)
    assert past["week"]["current"]["parkingEnd"] == datetime(2026, 7, 20)
    assert past["month"]["current"]["sunEnd"] == datetime(2026, 8, 1)
    assert windows.status_comparison_windows(rows, now, date(2030, 1, 1)) == windows.status_comparison_windows(rows, now)
    assert not windows.status_comparison_windows(rows, now)["week"]["navigation"]["canNext"]


@pytest.mark.parametrize("anchor", [None, "", " ", 123])
def test_empty_anchor_retains_today(anchor):
    assert windows.parse_anchor_day(anchor, date(2026, 8, 30)) == date(2026, 8, 30)


def test_stale_sources_have_empty_current_day_and_stable_labels():
    now = datetime(2026, 8, 30, 16)
    plan = overview.overview_comparison_plan(imports_at(now, "stale"), now)
    current = plan.periods[0].current
    assert current.start == current.sun_end == current.parking_end
    assert windows.cutoff_label(datetime(2026, 8, 29, 12), now.date()) == "29.08 kl 12:00"


@pytest.mark.parametrize("hours", [0, 18, 24 * 7, 24 * 31])
def test_axis_tick_positions_are_ordered_and_bounded(hours):
    ticks = windows.status_timeline_ticks(datetime(2026, 8, 30, 6), hours * 3600)
    positions = [item["left"] for item in ticks]
    assert positions == sorted(positions)
    assert positions[0] == 0
    assert all(0 <= position <= 100 for position in positions)


def test_period_summary_keeps_source_labels_seconds_and_zero_amounts():
    start = datetime(2026, 8, 30)
    sun_end, parking_end = start.replace(hour=14, second=17), start.replace(hour=12, second=13)
    payload = windows.status_period_summary("I dag", start, sun_end, parking_end,
                                            SimpleNamespace(paid=None, sessions=None),
                                            SimpleNamespace(paid=-50, sessions=2), start.date())
    assert payload["total"] == -50
    assert payload["solCount"] == 0 and payload["parkingCount"] == 2
    assert payload["sunEnd"] == "2026-08-30T14:00:17+02:00"
    assert payload["parkingEnd"] == "2026-08-30T12:00:13+02:00"


def make_data(plan):
    sun, full, parking = {}, {}, {}
    for period in plan.periods:
        for window in (period.current, period.previous, period.extra):
            sun[window.key] = snapshot("sun", window.start, window.sun_end)
            parking[window.key] = snapshot("parking", window.start, window.parking_end)
        for window in (period.previous, period.extra):
            full[window.key] = snapshot("sun", window.start.date(), window.end.date())
            parking[window.key + "_full"] = snapshot("parking", window.start, window.end)
    return overview.OverviewComparisons(plan, full, sun, parking)


@pytest.mark.parametrize("scope,basis", [("revenue", "omsetning"), ("parking", "antall parkeringer"), ("sun", "antall solinger")])
def test_card_totals_labels_and_rank_basis(scope, basis):
    now = datetime(2026, 8, 30, 16)
    data = make_data(overview.overview_comparison_plan(imports_at(now), now))
    cards = overview.build_overview_cards(data, summaries("sun"), summaries("parking"), scope)
    assert [card["key"] for card in cards] == ["today", "week", "month", "year"]
    for card in cards:
        assert card["total"] == card["sol"] + card["parking"]
        assert card["previousTotal"] == card["previousSol"] + card["previousParking"]
        assert card["previousFullTotal"] >= card["previousTotal"]
        assert card["rank"] is None or card["rank"]["basis"].endswith("etter " + basis)
    assert cards[1]["extraComparisons"][0]["label"].endswith("samme uke 2025")
    assert cards[2]["extraComparisons"][0]["label"].endswith("samme måned 2025")
    assert cards[3]["previousFullLabel"] == "Hele 2025"
    assert cards[3]["extraComparisons"][0]["fullLabel"] == "Hele 2024"


def test_loader_uses_existing_batch_functions_once_each(monkeypatch):
    now = datetime(2026, 8, 30, 16)
    plan = overview.overview_comparison_plan(imports_at(now), now)
    session, calls = object(), []
    def reader(kind):
        async def read(actual, periods):
            assert actual is session
            calls.append((kind, periods))
            return {key: snapshot("sun" if kind.startswith("sun") else "parking", *span) for key, span in periods.items()}
        return read
    monkeypatch.setattr(overview, "sun2_period_snapshots", reader("sun-full"))
    monkeypatch.setattr(overview, "sun2_datetime_snapshots", reader("sun-cutoff"))
    monkeypatch.setattr(overview, "parking_datetime_snapshots", reader("parking"))
    data = asyncio.run(overview.load_overview_comparisons(session, plan))
    assert [(kind, len(periods)) for kind, periods in calls] == [("sun-full", 8), ("sun-cutoff", 12), ("parking", 20)]
    assert len(data.plan.periods) == 4
