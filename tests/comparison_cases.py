"""Deterministic inputs for comparison contracts; no production data."""

from contextlib import ExitStack
from datetime import date, datetime, timedelta, timezone
import hashlib
import importlib
import json
from types import SimpleNamespace
from unittest.mock import patch


NOW_CASES = [
    datetime(2026, 8, 30, 16, 7, 23),
    datetime(2024, 3, 31, 16, 7, 23),
    datetime(2024, 2, 29, 16, 7, 23),
    datetime(2021, 1, 1, 16, 7, 23),
    datetime(2026, 1, 1, 0, 7, 23),
    datetime(2026, 10, 25, 16, 7, 23),
    datetime(2026, 12, 31, 23, 59, 59),
]


def imports_at(now, variant="normal"):
    stamps = [now - timedelta(minutes=17), now - timedelta(hours=4, minutes=3)]
    if variant == "missing":
        stamps = [None, None]
    elif variant == "stale":
        stamps = [now - timedelta(days=2), now - timedelta(days=45)]
    elif variant == "future":
        stamps = [now + timedelta(hours=1), now + timedelta(days=1)]
    elif variant == "utc":
        stamps = [datetime(2026, 8, 30, 10, 5, 17, tzinfo=timezone.utc),
                  datetime(2026, 8, 30, 8, 0, 13, tzinfo=timezone.utc)]
    return [dict(job_name=name, last_success_at=stamp, last_failed_at=now,
                 source_no=index, title=name, status="ok", age="fixed", status_text="OK",
                 next_expected_at=now + timedelta(hours=1))
            for index, (name, stamp) in enumerate(zip(
                ("sun2_sessions_import", "easypark_parking_import"), stamps), 1)]


def summaries(domain):
    records = []
    for year in range(2020, 2027):
        for month, day in [(1, 1), (2, 28), (3, 1), (8, 29), (12, 31)]:
            value = date(year, month, day)
            count = (value.toordinal() % 17) + 1
            paid = count * (177.25 if domain == "sun" else 51.75)
            records.append(dict(period=value.isoformat(), period_label=value.isoformat(),
                                totalt_inntjent_kr=paid, totalt_antall_solinger=count,
                                total_soletid_minutter=count * 20, paid=paid, sessions=count,
                                parking_time_min=count * 47))
    return {"daily": records, "monthly": [], "yearly": [], "weekly_chart": []}


def snapshot(kind, start, end):
    if not isinstance(start, datetime):
        start = datetime.combine(start, datetime.min.time())
        end = datetime.combine(end, datetime.min.time())
    span = max(0, (end - start).total_seconds())
    count = int(span // (613 if kind == "sun" else 997))
    paid = count * (177.25 if kind == "sun" else 51.75) + (start.toordinal() % 31 if span else 0)
    return SimpleNamespace(paid=paid, sessions=count, minutes=count * 20, rooms=min(count, 12))


def normalize(value):
    if isinstance(value, dict):
        return {str(k): normalize(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [normalize(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def digest(value):
    return hashlib.sha256(json.dumps(normalize(value), sort_keys=True, ensure_ascii=True).encode()).hexdigest()


class Scenario:
    def __init__(self, main, now, variant="normal"):
        self.main, self.now = main, now
        self.imports = imports_at(now, variant)
        self.calls = []
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    async def execute(self, statement):
        raise AssertionError("Unexpected database query")

    def batch(self, kind, name):
        async def run(session, periods):
            assert session is self and not self.closed
            self.calls.append((name, normalize(periods)))
            return {key: snapshot(kind, *bounds) for key, bounds in periods.items()}
        return run

    def single(self, kind):
        async def run(session, start, end):
            assert session is self and not self.closed
            self.calls.append((kind, start, end))
            return snapshot(kind, start, end)
        return run

    async def lane(self, session, source, label, period_label, kind, start, end, axis_seconds):
        assert session is self and not self.closed
        self.calls.append(("lane", source, kind, start, end, axis_seconds))
        return dict(key=f"{source}-{kind}", label=label, periodLabel=period_label,
                    start=start.isoformat(), end=end.isoformat(), events=[])

    def patches(self):
        stack = ExitStack()
        main = self.main
        # Shared formatting helpers keep their original module globals when an
        # original endpoint is replayed from the pre-refactor commit.
        stack.enter_context(patch("main.local_now_naive", lambda: self.now))
        async def imports(session):
            assert session is self
            return self.imports
        async def sun(session):
            return summaries("sun")
        async def parking(session):
            return summaries("parking")
        targets = [main]
        for module in ("overview", "chart"):
            try:
                targets.append(importlib.import_module("fibaro_core.services.comparisons." + module))
            except ModuleNotFoundError:
                pass
        for target in targets:
            for name, value in {
                "sun2_period_snapshots": self.batch("sun", "sun-full"),
                "sun2_datetime_snapshots": self.batch("sun", "sun-cutoff"),
                "parking_datetime_snapshots": self.batch("parking", "parking"),
                "sun2_datetime_snapshot": self.single("sun"),
                "parking_datetime_snapshot": self.single("parking"),
            }.items():
                if hasattr(target, name):
                    stack.enter_context(patch.object(target, name, value))
        for name, value in dict(local_now_naive=lambda: self.now, async_session=lambda: self,
                                import_status_rows=imports, get_sun2_summaries=sun,
                                get_parking_summaries=parking, status_timeline_lane=self.lane).items():
            stack.enter_context(patch.object(main, name, value))
        return stack


async def contracts(main):
    result = {}
    for now in NOW_CASES:
        for variant in ("normal", "missing", "stale", "future"):
            key = f"{now.isoformat()}/{variant}"
            for scope in ("revenue", "parking", "sun"):
                case = Scenario(main, now, variant)
                with case.patches():
                    payload = await main.api_v2_overview(scope=scope)
                assert case.closed
                result[f"overview/{key}/{scope}"] = digest((payload, case.calls))
            for anchor in (None, (now.date() - timedelta(days=40)).isoformat(), "2028-01-01"):
                for period, comparison in (("today", "previous"), ("today", "same-weekday-last-week"),
                                           ("week", "previous"), ("week", "same-week-last-year"),
                                           ("month", "previous"), ("month", "same-month-last-year")):
                    for references in ("auto", "none"):
                        case = Scenario(main, now, variant)
                        with case.patches():
                            payload = await main.api_v2_status_comparison(
                                period=period, compare=comparison, anchor=anchor, references=references)
                        result[f"chart/{key}/{anchor}/{period}/{comparison}/{references}"] = digest((payload, case.calls))
        for prefix in ("sun2", "parking", "revenue"):
            for year in (None, "2024", "2025", "2030"):
                case = Scenario(main, now)
                with case.patches():
                    payload = await getattr(main, f"api_v2_{prefix}_year_comparison")(year=year)
                result[f"year/{now.isoformat()}/{prefix}/{year}"] = digest(payload)
    return result


class FullScenario(Scenario):
    """The unfiltered overview retains its non-business data and query path."""

    def __init__(self, main, now):
        super().__init__(main, now)
        self.queries = []
        self.results = [None, None, None, None, 3,
                        SimpleNamespace(start_time=now, car_license_number="TEST"),
                        SimpleNamespace(started_at=now, room="Test room"),
                        SimpleNamespace(bucket_start=now, inntak_w=1000, differanse_beregnet_w=100),
                        SimpleNamespace(kwh=10, samples=12)]

    async def execute(self, statement):
        assert not self.closed
        self.queries.append(str(statement))
        value = self.results.pop(0)
        class Result:
            def scalars(self):
                return self
            def first(self):
                return value
            def one(self):
                return value
            def scalar_one(self):
                return value
        return Result()

    def patches(self):
        stack = super().patches()
        async def switches(configs):
            return {}
        stack.enter_context(patch.object(self.main, "hc3_fetch_switch_statuses", switches))
        stack.enter_context(patch.object(self.main, "build_now_status", lambda *args: dict(
            indoor_avg=21, outdoor_avg=14, timestamp=self.now, weather="test")))
        stack.enter_context(patch.object(self.main, "ventilation_status_payload", lambda device, *args: dict(key=device["key"], state=None)))
        stack.enter_context(patch.object(self.main, "weather_from_rows", lambda *args: "test"))
        return stack


async def full_overview_contracts(main):
    result = {}
    for now in NOW_CASES:
        case = FullScenario(main, now)
        with case.patches():
            payload = await main.api_v2_overview(scope=None)
        assert case.closed and not case.results
        result[now.isoformat()] = digest((payload, case.calls, case.queries))
    return result
