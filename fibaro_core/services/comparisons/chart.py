"""Comparison response assembly with an explicit session and timeline reader."""

from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException
from fibaro_core.services.summaries.sun import sun2_datetime_snapshot
from fibaro_core.services.summaries.parking import parking_datetime_snapshot
from fibaro_core.services.comparisons.windows import (
    status_comparison_windows, status_period_summary, status_timeline_ticks,
)
from time_formatting import api_local_iso


async def build_status_comparison(
    session,
    import_rows: list[Dict[str, Any]],
    now_dt: datetime,
    period: str,
    compare: str,
    anchor_day: Optional[date],
    references: str,
    *,
    timeline_lane: Callable[..., Awaitable[Dict[str, Any]]],
) -> Dict[str, Any]:
    today = now_dt.date()
    windows = status_comparison_windows(import_rows, now_dt, anchor_day)
    period_config = windows.get(period)
    if not period_config:
        raise HTTPException(status_code=404, detail="Ukjent statusperiode")
    comparison_config = next(
        (item for item in period_config["comparisons"] if item["key"] == compare),
        None,
    )
    if not comparison_config:
        raise HTTPException(status_code=404, detail="Ukjent sammenligning")
    include_reference_comparisons = references != "none"
    reference_configs = (
        [
            item
            for item in period_config["comparisons"]
            if item["key"] == "same-weekday-last-week" and item["key"] != comparison_config["key"]
        ]
        if include_reference_comparisons
        else []
    )

    current_config = period_config["current"]
    fixed_chart_period = period in {"today", "week"}

    def chart_start(config: Dict[str, Any]) -> datetime:
        if period == "today":
            return config["start"] + timedelta(hours=6)
        return config["start"]

    def chart_window_end(config: Dict[str, Any]) -> datetime:
        if period == "today":
            return config["start"] + timedelta(days=1)
        if period == "week":
            return config["start"] + timedelta(days=7)
        return max(config["sunEnd"], config["parkingEnd"])

    def chart_end(config: Dict[str, Any], source_key: str) -> datetime:
        if not fixed_chart_period:
            return config[source_key]
        window_start = chart_start(config)
        window_end = chart_window_end(config)
        if config is not current_config:
            return window_end
        return max(window_start, min(config[source_key], window_end))

    current_chart_start = chart_start(current_config)
    comparison_chart_start = chart_start(comparison_config)
    current_sun_chart_end = chart_end(current_config, "sunEnd")
    current_parking_chart_end = chart_end(current_config, "parkingEnd")
    comparison_sun_chart_end = chart_end(comparison_config, "sunEnd")
    comparison_parking_chart_end = chart_end(comparison_config, "parkingEnd")
    axis_candidates = [
        3600.0,
        (current_sun_chart_end - current_chart_start).total_seconds(),
        (current_parking_chart_end - current_chart_start).total_seconds(),
        (comparison_sun_chart_end - comparison_chart_start).total_seconds(),
        (comparison_parking_chart_end - comparison_chart_start).total_seconds(),
    ]
    for reference_config in reference_configs:
        reference_chart_start = chart_start(reference_config)
        reference_sun_chart_end = chart_end(reference_config, "sunEnd")
        reference_parking_chart_end = chart_end(reference_config, "parkingEnd")
        axis_candidates.extend(
            [
                (reference_sun_chart_end - reference_chart_start).total_seconds(),
                (reference_parking_chart_end - reference_chart_start).total_seconds(),
            ]
        )
    axis_seconds = max(axis_candidates)

    current_sun = await sun2_datetime_snapshot(session, current_config["start"], current_config["sunEnd"])
    current_parking = await parking_datetime_snapshot(session, current_config["start"], current_config["parkingEnd"])
    comparison_sun = await sun2_datetime_snapshot(session, comparison_config["start"], comparison_config["sunEnd"])
    comparison_parking = await parking_datetime_snapshot(
        session,
        comparison_config["start"],
        comparison_config["parkingEnd"],
    )

    lanes = [
        await timeline_lane(
            session,
            "current",
            "Soling",
            current_config["label"],
            "sun",
            current_chart_start,
            current_sun_chart_end,
            axis_seconds,
        ),
        await timeline_lane(
            session,
            "current",
            "Parkering",
            current_config["label"],
            "parking",
            current_chart_start,
            current_parking_chart_end,
            axis_seconds,
        ),
        await timeline_lane(
            session,
            "comparison",
            "Soling",
            comparison_config["label"],
            "sun",
            comparison_chart_start,
            comparison_sun_chart_end,
            axis_seconds,
        ),
        await timeline_lane(
            session,
            "comparison",
            "Parkering",
            comparison_config["label"],
            "parking",
            comparison_chart_start,
            comparison_parking_chart_end,
            axis_seconds,
        ),
    ]
    reference_results = []
    for reference_config in reference_configs:
        reference_chart_start = chart_start(reference_config)
        reference_sun_chart_end = chart_end(reference_config, "sunEnd")
        reference_parking_chart_end = chart_end(reference_config, "parkingEnd")
        reference_sun = await sun2_datetime_snapshot(session, reference_config["start"], reference_config["sunEnd"])
        reference_parking = await parking_datetime_snapshot(
            session,
            reference_config["start"],
            reference_config["parkingEnd"],
        )
        reference_lanes = [
            await timeline_lane(
                session,
                "reference",
                "Soling",
                reference_config["label"],
                "sun",
                reference_chart_start,
                reference_sun_chart_end,
                axis_seconds,
            ),
            await timeline_lane(
                session,
                "reference",
                "Parkering",
                reference_config["label"],
                "parking",
                reference_chart_start,
                reference_parking_chart_end,
                axis_seconds,
            ),
        ]
        reference_results.append(
            {
                "config": reference_config,
                "sun": reference_sun,
                "parking": reference_parking,
                "lanes": reference_lanes,
            }
        )

    current_summary = status_period_summary(
        current_config["label"],
        current_config["start"],
        current_config["sunEnd"],
        current_config["parkingEnd"],
        current_sun,
        current_parking,
        today,
    )
    comparison_summary = status_period_summary(
        comparison_config["label"],
        comparison_config["start"],
        comparison_config["sunEnd"],
        comparison_config["parkingEnd"],
        comparison_sun,
        comparison_parking,
        today,
    )
    reference_payloads = []
    for reference_result in reference_results:
        reference_config = reference_result["config"]
        reference_summary = status_period_summary(
            reference_config["label"],
            reference_config["start"],
            reference_config["sunEnd"],
            reference_config["parkingEnd"],
            reference_result["sun"],
            reference_result["parking"],
            today,
        )
        reference_payloads.append(
            {
                "key": reference_config["key"],
                "label": reference_config["label"],
                "summary": reference_summary,
                "delta": {
                    "sol": current_summary["sol"] - reference_summary["sol"],
                    "solCount": current_summary["solCount"] - reference_summary["solCount"],
                    "parking": current_summary["parking"] - reference_summary["parking"],
                    "parkingCount": current_summary["parkingCount"] - reference_summary["parkingCount"],
                    "total": current_summary["total"] - reference_summary["total"],
                },
                "lanes": reference_result["lanes"],
            }
        )
    axis_end = current_chart_start + timedelta(seconds=axis_seconds)
    return {
        "generatedAt": api_local_iso(now_dt),
        "periodKey": period,
        "comparisonKey": compare,
        "anchor": period_config["anchor"],
        "title": period_config["title"],
        "comparisonLabel": comparison_config["label"],
        "navigation": period_config["navigation"],
        "axis": {
            "start": api_local_iso(current_chart_start),
            "end": api_local_iso(axis_end),
            "seconds": axis_seconds,
            "ticks": status_timeline_ticks(current_chart_start, axis_seconds),
        },
        "current": current_summary,
        "comparison": comparison_summary,
        "delta": {
            "sol": current_summary["sol"] - comparison_summary["sol"],
            "solCount": current_summary["solCount"] - comparison_summary["solCount"],
            "parking": current_summary["parking"] - comparison_summary["parking"],
            "parkingCount": current_summary["parkingCount"] - comparison_summary["parkingCount"],
            "total": current_summary["total"] - comparison_summary["total"],
        },
        "lanes": lanes,
        "referenceComparisons": reference_payloads,
    }
