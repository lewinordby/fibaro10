from datetime import date, datetime
import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

import main


class ParkingRowApiTests(unittest.TestCase):
    def test_weekly_average_payload_calculates_amount_and_duration_per_session(self):
        period = main.parking_weekly_average_period({}, date(2026, 1, 14))
        rows = [
            (datetime(2026, 1, 5, 9, 0), datetime(2026, 1, 5, 10, 0), 60, 120),
            (datetime(2026, 1, 7, 10, 0), datetime(2026, 1, 7, 10, 30), 30, 80),
            (datetime(2026, 1, 12, 11, 0), datetime(2026, 1, 12, 11, 45), None, 90),
        ]

        payload = main.parking_weekly_average_payload(rows, period, datetime(2026, 1, 14, 12, 0))
        weeks = [item for item in payload["weeks"] if item["sessions"]]

        self.assertEqual(len(weeks), 2)
        self.assertEqual(weeks[0]["avgPaidPerSession"], 100)
        self.assertEqual(weeks[0]["avgMinutesPerSession"], 45)
        self.assertEqual(weeks[1]["avgPaidPerSession"], 90)
        self.assertEqual(weeks[1]["avgMinutesPerSession"], 45)
        self.assertTrue(weeks[1]["isPartial"])
        self.assertEqual(payload["summary"]["avgPaidPerSession"], 96.67)
        self.assertEqual(payload["summary"]["avgMinutesPerSession"], 45)
        self.assertEqual(payload["summary"]["durationCoveragePct"], 100)

    def test_weekly_average_period_defaults_to_current_year(self):
        period = main.parking_weekly_average_period({}, date(2026, 8, 2))

        self.assertEqual(period["key"], "this_year")
        self.assertEqual(period["dateFrom"], "2026-01-01")
        self.assertEqual(period["dateTo"], "2026-08-02")

    def test_weekly_year_comparison_uses_current_and_previous_year_by_default(self):
        selected = main.parking_weekly_selected_years(None, [2026, 2025, 2023], 2026)
        self.assertEqual(selected, [2026, 2025])

        selected = main.parking_weekly_selected_years("2023,2026,1999", [2026, 2025, 2023], 2026)
        self.assertEqual(selected, [2023, 2026])

    def test_weekly_year_comparison_keeps_boundary_days_in_calendar_year(self):
        self.assertEqual(main.parking_calendar_comparison_week(date(2021, 1, 1)), 1)
        self.assertEqual(main.parking_calendar_comparison_week(date(2018, 12, 31)), 53)
        ranges = main.parking_calendar_comparison_week_ranges(2021)
        self.assertEqual(ranges[1], (date(2021, 1, 1), date(2021, 1, 7)))

    def test_weekly_year_comparison_calculates_weighted_weekly_averages(self):
        rows = [
            (2026, 1, 2, 200, 90, 2),
            (2026, 2, 1, 80, 60, 1),
            (2025, 1, 4, 320, 180, 4),
        ]

        payload = main.parking_weekly_year_comparison_payload(
            rows,
            [2026, 2025],
            [2026, 2025],
            datetime(2026, 1, 8, 12, 0),
        )

        self.assertEqual(payload["selectedYears"], [2026, 2025])
        self.assertEqual(payload["currentWeek"], 2)
        self.assertEqual(payload["series"][0]["points"][0]["avgPaidPerSession"], 100)
        self.assertEqual(payload["series"][0]["points"][0]["avgMinutesPerSession"], 45)
        self.assertTrue(payload["series"][0]["points"][1]["isPartial"])
        self.assertEqual(payload["series"][0]["avgPaidPerSession"], 93.33)
        self.assertEqual(payload["series"][1]["points"][0]["avgPaidPerSession"], 80)

    def test_parking_row_api_includes_vehicle_details(self):
        row = main.ParkingSession(
            id=1,
            start_time=datetime(2026, 6, 26, 12, 0),
            car_license_number="AB12345",
            status="completed",
        )
        vehicle = main.ParkingVehicle(plate="AB12345", navn="Test Eier")
        details = main.ParkingVehicleDetails(
            plate="AB12345",
            merke="Toyota",
            typebetegnelse="Corolla",
            farge="Svart",
        )

        payload = main.parking_row_api(row, vehicle, details)

        self.assertEqual(payload["vehicle_owner"], "Test Eier")
        self.assertEqual(payload["vehicle_make"], "Toyota")
        self.assertEqual(payload["vehicle_type"], "Corolla")
        self.assertEqual(payload["vehicle_color"], "Svart")
        self.assertEqual(payload["path"], "/parkering/kjoretoy/AB12345")

    def test_parking_row_api_links_plate_without_vehicle_record(self):
        row = main.ParkingSession(
            id=11,
            start_time=datetime(2026, 8, 25, 8, 0),
            car_license_number=" ab 12345 ",
            status="Ongoing",
        )

        payload = main.parking_row_api(row)

        self.assertEqual(payload["path"], "/parkering/kjoretoy/AB12345")

    def test_parking_row_api_uses_foreign_lookup_fallback(self):
        row = main.ParkingSession(
            id=2,
            start_time=datetime(2026, 6, 26, 12, 0),
            car_license_number="HWN31L",
            status="completed",
        )
        vehicle = main.ParkingVehicle(
            plate="HWN31L",
            navn="",
            car_info_data={
                "fields": {
                    "brand": "Volvo",
                    "model": "XC60",
                    "color": "Gra",
                }
            },
        )

        payload = main.parking_row_api(row, vehicle)

        self.assertEqual(payload["vehicle_make"], "Volvo")
        self.assertEqual(payload["vehicle_type"], "XC60")
        self.assertEqual(payload["vehicle_color"], "Gra")

    def test_parking_row_api_calculates_departure_against_paid_slot(self):
        row = main.ParkingSession(
            id=3,
            start_time=datetime(2026, 6, 26, 12, 0),
            end_time=datetime(2026, 6, 26, 12, 45),
            car_license_number="AB12345",
            status="Ended",
        )

        payload = main.parking_row_api(row)

        self.assertEqual(payload["end_delta_min"], -15)

    def test_parking_row_api_skips_departure_delta_for_ongoing(self):
        row = main.ParkingSession(
            id=4,
            start_time=datetime(2026, 6, 26, 12, 0),
            end_time=datetime(2026, 6, 26, 12, 45),
            car_license_number="AB12345",
            status="Ongoing",
        )

        payload = main.parking_row_api(row)

        self.assertIsNone(payload["end_delta_min"])

    def test_cars_detection_paid_coverage_includes_boundaries(self):
        start = datetime(2026, 7, 21, 12, 0)
        end = datetime(2026, 7, 21, 13, 0)

        self.assertTrue(main.cars_detection_is_covered(start, start, end))
        self.assertTrue(main.cars_detection_is_covered(end, start, end))
        self.assertFalse(main.cars_detection_is_covered(datetime(2026, 7, 21, 13, 1), start, end))
        self.assertFalse(main.cars_detection_is_covered(None, start, end))

    def test_cars_confidence_levels_are_bounded_and_labeled(self):
        self.assertEqual(main.cars_unifi_score(104), 100.0)
        self.assertEqual(main.cars_unifi_score(-4), 0.0)
        self.assertIsNone(main.cars_unifi_score("not-a-score"))
        self.assertEqual(main.cars_confidence_level(80), "high")
        self.assertEqual(main.cars_confidence_level(79.9), "medium")
        self.assertEqual(main.cars_confidence_level(59.9), "low")
        self.assertEqual(main.cars_confidence_level(None), "unscored")

    def test_cars_ocr_variants_require_similarity_camera_and_time(self):
        at = datetime(2026, 7, 21, 12, 0)
        left = [(at, "camera-1")]

        self.assertEqual(main.cars_plate_edit_distance("EP34885", "EP3488"), 1)
        self.assertTrue(
            main.cars_likely_ocr_variants(
                "EP34885",
                "EP3488",
                left,
                [(datetime(2026, 7, 21, 12, 1), "camera-1")],
            )
        )
        self.assertFalse(
            main.cars_likely_ocr_variants(
                "EP34885",
                "EP3488",
                left,
                [(datetime(2026, 7, 21, 12, 1), "camera-2")],
            )
        )
        self.assertFalse(
            main.cars_likely_ocr_variants(
                "EP34885",
                "EV32408",
                left,
                [(datetime(2026, 7, 21, 12, 1), "camera-1")],
            )
        )

    def test_cars_daily_group_merges_only_invalid_variant_into_valid_plate(self):
        items = [
            {
                "plate": "AB12345",
                "display_value": "AB 12345",
                "detection_count": 1,
                "detections": [{"recognition_id": 1, "occurred_at": "2026-07-21T12:00:00+02:00"}],
                "validation": {"is_valid": True},
                "likely_canonical_plate": "AB12345",
            },
            {
                "plate": "AB1234S",
                "detection_count": 1,
                "detections": [{"recognition_id": 2, "occurred_at": "2026-07-21T12:01:00+02:00"}],
                "validation": {"is_valid": False},
                "is_likely_ocr_variant": True,
                "likely_canonical_plate": "AB12345",
            },
        ]

        grouped = main.cars_group_daily_recognitions(items)

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["plate"], "AB12345")
        self.assertEqual(grouped[0]["detection_count"], 2)
        self.assertEqual(grouped[0]["observed_plate_values"], ["AB12345", "AB1234S"])
        self.assertEqual(grouped[0]["detections"][1]["observed_plate"], "AB1234S")

    def test_cars_daily_group_never_merges_two_valid_plates(self):
        items = [
            {
                "plate": "AB12345",
                "validation": {"is_valid": True},
                "likely_canonical_plate": "AB12345",
            },
            {
                "plate": "AB1234S",
                "validation": {"is_valid": True},
                "is_likely_ocr_variant": True,
                "likely_canonical_plate": "AB12345",
            },
        ]

        grouped = main.cars_group_daily_recognitions(items)

        self.assertEqual({item["plate"] for item in grouped}, {"AB12345", "AB1234S"})

    def test_cars_daily_payment_matches_the_whole_day_and_keeps_precise_timing(self):
        detections = [datetime(2026, 7, 21, 8, 0), datetime(2026, 7, 21, 14, 30)]
        paid_sessions = [
            {
                "_startAt": datetime(2026, 7, 21, 12, 0),
                "_endAt": datetime(2026, 7, 21, 13, 0),
            }
        ]

        metrics = main.cars_daily_payment_metrics(detections, paid_sessions)

        self.assertEqual(metrics["paymentStatus"], "paid_same_day")
        self.assertEqual(metrics["dayMatchedDetectionCount"], 2)
        self.assertEqual(metrics["coveredDetectionCount"], 0)
        self.assertEqual(metrics["minutesBeforeFirstPayment"], 240.0)
        self.assertEqual(metrics["minutesAfterLastPayment"], 90.0)


class CarsDayApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_parking_control_report_maps_month_and_visits(self):
        ledger = AsyncMock(
            return_value={
                "generated_at": "2026-08-25T09:00:00Z",
                "identity": "PARKNORDIC",
                "display_name": "Park Nordic",
                "policy": {"gap_minutes": 60, "label": "Under 60 min", "detail": "Estimert."},
                "summary": {
                    "visit_count": 1,
                    "active_days": 1,
                    "observation_count": 2,
                    "observed_minutes": 12,
                    "average_visit_minutes": 12,
                },
                "days": [
                    {
                        "date": "2026-08-25",
                        "visit_count": 1,
                        "observation_count": 2,
                        "observed_minutes": 12,
                        "visits": [
                            {
                                "id": "visit-1",
                                "start_at": "2026-08-25T07:00:00Z",
                                "end_at": "2026-08-25T07:12:00Z",
                                "duration_minutes": 12,
                                "observation_count": 2,
                                "camera_names": ["Butikk front"],
                                "is_single_observation": False,
                                "observations": [
                                    {
                                        "recognition_id": 123,
                                        "occurred_at": "2026-08-25T07:00:00Z",
                                        "camera_id": "front",
                                        "camera_name": "Butikk front",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        )
        parking_payload = ledger.return_value
        known_stays_payload = {
            "policy": {
                "min_duration_minutes": 10,
                "label": "Mer enn 10 minutter",
                "detail": "Fra første til siste observasjon.",
            },
            "summary": {
                "vehicle_day_count": 1,
                "active_days": 1,
                "unique_vehicle_count": 1,
                "observation_count": 3,
                "observed_minutes": 18,
            },
            "days": [
                {
                    "date": "2026-08-25",
                    "observation_count": 3,
                    "vehicles": [
                        {
                            "id": "firmabil-2026-08-25",
                            "identity": "FIRMABIL",
                            "display_name": "Firmabil",
                            "first_observed_at": "2026-08-25T08:00:00Z",
                            "last_observed_at": "2026-08-25T08:18:00Z",
                            "duration_minutes": 18,
                            "observation_count": 3,
                            "camera_names": ["Butikk front"],
                        }
                    ],
                }
            ],
        }
        registered_stays_payload = {
            "policy": {"min_duration_minutes": 10, "country_codes": ["NO", "SE", "DK"]},
            "summary": {"vehicle_day_count": 1},
            "days": [],
        }
        unpaid_registered_payload = {
            "policy": {"label": "Registerfunnet uten betaling"},
            "summary": {"vehicleDayCount": 1},
            "days": [],
        }
        ledger.side_effect = lambda method, **_kwargs: (
            known_stays_payload
            if method == "known_vehicle_stays_report"
            else registered_stays_payload
            if method == "registered_vehicle_stays_report"
            else parking_payload
        )
        unpaid_builder = AsyncMock(return_value=unpaid_registered_payload)
        with patch.object(main.parking_http.dependencies, "protect_ledger_json", new=ledger), patch.object(
            main.parking_http.dependencies, "unpaid_registered_vehicle_stays_payload", new=unpaid_builder
        ):
            payload = await main.api_parking_control_report(
                response=main.Response(), period="month", month="2026-08", week=None, gap_minutes=60
            )

        self.assertEqual(payload["month"], "2026-08")
        self.assertEqual(payload["periodType"], "month")
        self.assertEqual(payload["periodValue"], "2026-08")
        self.assertEqual(payload["summary"]["visitCount"], 1)
        self.assertEqual(payload["days"][0]["visits"][0]["durationMinutes"], 12.0)
        self.assertEqual(payload["days"][0]["visits"][0]["observations"][0]["recognitionId"], 123)
        self.assertEqual(payload["knownVehicles"]["summary"]["vehicleDayCount"], 1)
        self.assertEqual(payload["knownVehicles"]["days"][0]["vehicles"][0]["displayName"], "Firmabil")
        self.assertEqual(payload["unpaidRegisteredVehicles"]["summary"]["vehicleDayCount"], 1)
        report_call = next(call for call in ledger.await_args_list if call.args[0] == "known_vehicle_report")
        stays_call = next(call for call in ledger.await_args_list if call.args[0] == "known_vehicle_stays_report")
        registered_call = next(call for call in ledger.await_args_list if call.args[0] == "registered_vehicle_stays_report")
        self.assertEqual(report_call.kwargs["identity"], "PARKNORDIC")
        self.assertEqual(stays_call.kwargs["min_duration_minutes"], 10)
        self.assertEqual(registered_call.kwargs["min_duration_minutes"], 10)
        unpaid_builder.assert_awaited_once_with(registered_stays_payload, date(2026, 8, 1), date(2026, 9, 1))

    async def test_unpaid_registered_vehicle_stays_excludes_paid_vehicle_days(self):
        class ScalarRows:
            def __init__(self, rows):
                self.rows = rows

            def scalars(self):
                return self

            def all(self):
                return self.rows

        class PairRows:
            def all(self):
                return []

        class Session:
            def __init__(self):
                self.calls = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def execute(self, _query):
                self.calls += 1
                if self.calls == 1:
                    return ScalarRows(
                        [
                            main.ParkingSession(
                                id=1,
                                parking_area="Lilletorget",
                                source_system="easypark",
                                area_number=1,
                                parking_id=1,
                                start_time=datetime(2026, 8, 25, 9, 0),
                                end_time=datetime(2026, 8, 25, 10, 0),
                                fee_inc_vat=50,
                                car_license_number="AB12345",
                                status="completed",
                            )
                        ]
                    )
                return PairRows()

        source = {
            "policy": {"min_duration_minutes": 10, "country_codes": ["NO", "SE", "DK"]},
            "summary": {"vehicle_day_count": 2},
            "days": [
                {
                    "date": "2026-08-25",
                    "vehicles": [
                        {
                            "plate": "AB12345",
                            "country_code": "NO",
                            "first_observed_at": "2026-08-25T07:00:00Z",
                            "last_observed_at": "2026-08-25T07:20:00Z",
                            "duration_minutes": 20,
                            "observation_count": 3,
                        },
                        {
                            "plate": "CD67890",
                            "country_code": "NO",
                            "first_observed_at": "2026-08-25T08:00:00Z",
                            "last_observed_at": "2026-08-25T08:15:00Z",
                            "duration_minutes": 15,
                            "observation_count": 2,
                        },
                    ],
                }
            ],
        }

        with patch.object(main, "async_session", new=lambda: Session()):
            payload = await main.unpaid_registered_vehicle_stays_payload(source, date(2026, 8, 1), date(2026, 9, 1))

        self.assertEqual(payload["summary"]["vehicleDayCount"], 1)
        self.assertEqual(payload["summary"]["excludedPaidVehicleDays"], 1)
        self.assertEqual(payload["days"][0]["vehicles"][0]["plate"], "CD67890")

    async def test_parking_control_report_can_select_iso_week(self):
        ledger = AsyncMock(
            return_value={
                "policy": {},
                "summary": {},
                "days": [],
            }
        )
        with patch.object(main.parking_http.dependencies, "protect_ledger_json", new=ledger):
            payload = await main.api_parking_control_report(
                response=main.Response(), period="week", month=None, week="2026-W35", gap_minutes=60
            )

        self.assertEqual(payload["periodType"], "week")
        self.assertEqual(payload["periodValue"], "2026-W35")
        self.assertEqual(payload["rangeStart"], "2026-08-24")
        self.assertEqual(payload["rangeEnd"], "2026-08-30")
        self.assertIn("Uke 35", payload["periodLabel"])
        report_call = next(call for call in ledger.await_args_list if call.args[0] == "known_vehicle_report")
        self.assertEqual(report_call.kwargs["gap_minutes"], 60)

    async def test_cars_day_uses_light_ledger_payload_and_server_cache(self):
        main.clear_summary_cache("cars_day")
        ledger = AsyncMock(return_value={"items": []})
        try:
            with patch.object(main.parking_http.dependencies, "protect_ledger_json", new=ledger):
                first_response = main.Response()
                first = await main.api_cars_day(response=first_response, day="2026-07-21")
                second_response = main.Response()
                second = await main.api_cars_day(response=second_response, day="2026-07-21")
        finally:
            main.clear_summary_cache("cars_day")

        self.assertEqual(first_response.headers["Cache-Control"], "no-store, max-age=0")
        self.assertEqual(first_response.headers["X-Data-Cache"], "miss")
        self.assertEqual(second_response.headers["X-Data-Cache"], "hit")
        self.assertEqual(first, second)
        self.assertEqual(first["selectedDay"], "2026-07-21")
        self.assertEqual(first["items"], [])
        self.assertEqual(first["summary"]["uniquePlates"], 0)
        self.assertEqual(ledger.await_count, 1)

    async def test_cars_day_requests_summary_mode_from_ledger(self):
        main.clear_summary_cache("cars_day")
        ledger = AsyncMock(return_value={"items": []})
        try:
            with patch.object(main.parking_http.dependencies, "protect_ledger_json", new=ledger):
                await main.api_cars_day(response=main.Response(), day="2026-07-20")
        finally:
            main.clear_summary_cache("cars_day")

        self.assertFalse(ledger.await_args.kwargs["include_detections"])

    async def test_cars_day_detection_detail_is_loaded_for_one_plate(self):
        main.clear_summary_cache("cars_day_detections")
        ledger = AsyncMock(
            return_value={
                "items": [
                    {
                        "plate": "AB12345",
                        "detection_count": 1,
                        "detections": [
                            {
                                "recognition_id": 42,
                                "occurred_at": "2026-07-21T10:15:30+02:00",
                                "snapshot_url": "/api/v1/recognitions/42/snapshot",
                            }
                        ],
                    }
                ]
            }
        )
        try:
            with patch.object(main.parking_http.dependencies, "protect_ledger_json", new=ledger):
                payload = await main.api_cars_day_detections("AB12345", day="2026-07-21")
        finally:
            main.clear_summary_cache("cars_day_detections")

        self.assertTrue(ledger.await_args.kwargs["include_detections"])
        self.assertEqual(ledger.await_args.kwargs["plate"], "AB12345")
        self.assertEqual(payload["detectionCount"], 1)
        self.assertEqual(payload["detections"][0]["recognitionId"], 42)


if __name__ == "__main__":
    unittest.main()
