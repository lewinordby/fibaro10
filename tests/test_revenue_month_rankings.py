from datetime import date

from fibaro_core.services.runtime.dashboard import Dependencies, _revenue_day_rankings, create_service


def test_revenue_day_rankings_cover_year_and_matching_weekday():
    monday_best = date(2026, 1, 5)
    tuesday = date(2026, 1, 6)
    monday_second = date(2026, 1, 12)

    rankings = _revenue_day_rankings(
        {monday_best: 700, tuesday: 300, monday_second: 400},
        {monday_best: 300, tuesday: 200, monday_second: 400},
    )

    assert rankings[monday_best] == {
        "year_rank": 1,
        "year_day_count": 3,
        "weekday_rank": 1,
        "weekday_day_count": 2,
    }
    assert rankings[monday_second]["year_rank"] == 2
    assert rankings[monday_second]["weekday_rank"] == 2
    assert rankings[tuesday]["weekday_rank"] == 1
    assert rankings[tuesday]["weekday_day_count"] == 1


def test_revenue_day_rankings_ignore_days_without_revenue_and_share_tied_rank():
    first = date(2026, 2, 2)
    second = date(2026, 2, 3)
    empty = date(2026, 2, 4)

    rankings = _revenue_day_rankings({first: 500, second: 500, empty: 0}, {})

    assert rankings[first]["year_rank"] == 1
    assert rankings[second]["year_rank"] == 1
    assert rankings[first]["year_day_count"] == 2
    assert empty not in rankings


def test_revenue_day_api_includes_rankings():
    dependencies = Dependencies(
        age_label=lambda *_: "",
        async_session=lambda: None,
        average_value=lambda *_: None,
        latest_timestamp_from=lambda *_: None,
        normalize_month=lambda *_: None,
        weather_from_rows=lambda *_: "",
    )
    api_revenue_day = create_service(dependencies)["api_revenue_day"]

    payload = api_revenue_day(
        {
            "day": date(2026, 9, 4),
            "day_label": "04.09",
            "weekday": "Fre",
            "sol": 1200,
            "sol_count": 6,
            "parking": 800,
            "parking_count": 9,
            "total": 2000,
            "is_today": True,
            "is_weekend": False,
            "year_rank": 12,
            "year_day_count": 247,
            "weekday_rank": 3,
            "weekday_day_count": 35,
        }
    )

    assert payload["yearRank"] == 12
    assert payload["yearDayCount"] == 247
    assert payload["weekdayRank"] == 3
    assert payload["weekdayDayCount"] == 35
