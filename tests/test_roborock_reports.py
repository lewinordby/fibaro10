from datetime import date, datetime
from types import SimpleNamespace

from roborock_reports import build_night_report, report_window


def row(**values):
    return SimpleNamespace(**values)


def test_report_window_covers_evening_to_morning() -> None:
    window = report_window(date(2026, 8, 14))
    assert window["start"] == datetime(2026, 8, 13, 22, 0)
    assert window["ready_by"] == datetime(2026, 8, 14, 6, 45)
    assert window["end"] == datetime(2026, 8, 14, 8, 0)


def test_night_job_exposes_only_actual_dock_intervals() -> None:
    robot = row(duid="robot-dock", name="1.etg B", model="Q5")
    job = row(
        robot_duid="robot-dock",
        record_id="job-dock",
        begin_at=datetime(2026, 8, 13, 23, 0),
        end_at=datetime(2026, 8, 14, 0, 0),
        duration_minutes=37.0,
        duration_seconds=2220,
        cleaned_area_m2=30.0,
        area_m2=30.0,
        complete=True,
        error_code=0,
        wash_count=None,
        clean_times=1,
    )
    samples = [
        row(robot_duid="robot-dock", timestamp=datetime(2026, 8, 14, 1, 0), state_code=23, in_cleaning=True, in_returning=False, is_charging=False, battery=100, fan_power=104, water_box_mode=200, mop_mode=300),
        row(robot_duid="robot-dock", timestamp=datetime(2026, 8, 14, 1, 3), state_code=18, in_cleaning=True, in_returning=False, is_charging=False, battery=99, fan_power=104, water_box_mode=200, mop_mode=300),
        row(robot_duid="robot-dock", timestamp=datetime(2026, 8, 14, 1, 20), state_code=6, in_cleaning=True, in_returning=True, is_charging=False, battery=20, fan_power=104, water_box_mode=200, mop_mode=300),
        row(robot_duid="robot-dock", timestamp=datetime(2026, 8, 14, 1, 22), state_code=8, in_cleaning=True, in_returning=False, is_charging=True, battery=19, fan_power=104, water_box_mode=200, mop_mode=300),
        row(robot_duid="robot-dock", timestamp=datetime(2026, 8, 14, 1, 50), state_code=18, in_cleaning=True, in_returning=False, is_charging=False, battery=80, fan_power=104, water_box_mode=200, mop_mode=300),
        row(robot_duid="robot-dock", timestamp=datetime(2026, 8, 14, 2, 0), state_code=6, in_cleaning=False, in_returning=True, is_charging=False, battery=78, fan_power=104, water_box_mode=200, mop_mode=300),
    ]

    report = build_night_report(date(2026, 8, 14), [robot], [job], samples, [])

    assert report["robots"][0]["jobs"][0]["dockIntervals"] == [
        {
            "startedAt": "2026-08-14T01:00:00+02:00",
            "endedAt": "2026-08-14T01:03:00+02:00",
            "label": "Vasker mopp",
        },
        {
            "startedAt": "2026-08-14T01:22:00+02:00",
            "endedAt": "2026-08-14T01:50:00+02:00",
            "label": "Lader i dokk",
        },
    ]


def test_night_report_summarizes_modes_battery_and_mop_washes() -> None:
    robot = row(duid="robot-a", name="1.etg A", model="Qrevo")
    job = row(
        robot_duid="robot-a",
        record_id="job-1",
        begin_at=datetime(2026, 8, 13, 23, 0),  # UTC: 01:00 in Oslo
        end_at=datetime(2026, 8, 14, 0, 4),
        duration_minutes=64.0,
        duration_seconds=3840,
        cleaned_area_m2=38.5,
        area_m2=38.5,
        complete=True,
        error_code=0,
        wash_count=7,
        clean_times=1,
    )
    samples = [
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 1, 0), in_cleaning=True, battery=100, fan_power=105, water_box_mode=203, mop_mode=301, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=False),
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 2, 4), in_cleaning=True, battery=75, fan_power=105, water_box_mode=203, mop_mode=301, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=False),
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 6, 44), in_cleaning=False, battery=96, fan_power=105, water_box_mode=203, mop_mode=301, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=True),
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 7, 0), in_cleaning=False, battery=100, fan_power=105, water_box_mode=203, mop_mode=301, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=True),
    ]
    probes = [
        row(robot_duid="robot-a", command="GET_SMART_WASH_PARAMS", ok=True, raw={"value": {"smart_wash": 0, "wash_interval": 600}}),
        row(robot_duid="robot-a", command="GET_WASH_TOWEL_MODE", ok=True, raw={"value": {"wash_mode": 1}}),
        row(robot_duid="robot-a", command="GET_CUSTOM_MODE", ok=True, raw={"value": [104]}),
        row(robot_duid="robot-a", command="GET_WATER_BOX_CUSTOM_MODE", ok=True, raw={"value": {"water_box_mode": 207}}),
        row(robot_duid="robot-a", command="APP_GET_DRYER_SETTING", ok=True, raw={"value": {"status": 0, "on": {"dry_time": 7200}}}),
        row(robot_duid="robot-a", command="GET_DUST_COLLECTION_MODE", ok=True, raw={"value": {"mode": 0}}),
        row(robot_duid="robot-a", command="GET_DUST_COLLECTION_SWITCH_STATUS", ok=True, raw={"value": {"status": 1}}),
        row(robot_duid="robot-a", command="GET_CARPET_MODE", ok=True, raw={"value": [{"enable": 1}]}),
        row(robot_duid="robot-a", command="GET_DND_TIMER", ok=True, raw={"value": [{"enabled": 1, "start_hour": 22, "start_minute": 0, "end_hour": 7, "end_minute": 0}]}),
    ]

    report = build_night_report(date(2026, 8, 14), [robot], [job], samples, probes)

    result = report["robots"][0]
    assert report["conclusion"]["status"] == "neutral"
    assert report["summary"]["jobs"] == 1
    assert result["jobs"][0]["cleaningType"] == "mop"
    assert result["jobs"][0]["modeLabel"] == "Dyp · høy vannmengde · 1 runde"
    assert result["jobs"][0]["batteryStart"] == 100
    assert result["jobs"][0]["batteryEnd"] == 75
    assert result["jobs"][0]["expectedWashCount"] == 7
    assert result["jobs"][0]["waterStatus"] == "ok"
    assert result["jobs"][0]["waterStatusLabel"] == "OK"
    assert result["settings"]["modeLabel"] == "Balansert"
    assert result["settings"]["items"] == [
        {"key": "fan", "label": "Standard sugekraft", "value": "Maks"},
        {"key": "water", "label": "Standard vannmengde", "value": "Tilpasset"},
        {"key": "mop-wash", "label": "Moppevask", "value": "Balansert · hvert 10. min"},
        {"key": "dryer", "label": "Tørketid", "value": "2 t"},
        {"key": "dust", "label": "Støvtømming", "value": "På · Smart"},
        {"key": "carpet", "label": "Teppemodus", "value": "På"},
        {"key": "dnd", "label": "Ikke forstyrr", "value": "22:00–07:00"},
    ]
    assert report["summary"]["washCount"] == 7
    assert result["readiness"]["batteryAtOpening"] == 96
    assert result["readiness"]["fullChargeAt"].startswith("2026-08-14T07:00")


def test_water_shortage_is_reported_without_marking_completed_job_as_failed() -> None:
    robot = row(duid="robot-a", name="VIP", model="Qrevo")
    job = row(
        robot_duid="robot-a", record_id="job-2",
        begin_at=datetime(2026, 8, 14, 2, 0), end_at=datetime(2026, 8, 14, 3, 0),
        duration_minutes=60.0, duration_seconds=3600, cleaned_area_m2=30.0, area_m2=30.0,
        complete=True, error_code=0, wash_count=5, clean_times=1,
    )
    samples = [
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 4, 1), in_cleaning=True, battery=90, fan_power=105, water_box_mode=203, mop_mode=303, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=False),
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 5, 0), in_cleaning=True, battery=75, fan_power=105, water_box_mode=203, mop_mode=303, water_shortage_status=1, clear_water_status=1, clear_water_status_name="out_of_water", dock_error_status=0, is_charging=False),
    ]

    report = build_night_report(date(2026, 8, 14), [robot], [job], samples, [])

    result = report["robots"][0]["jobs"][0]
    assert report["conclusion"]["status"] == "warning"
    assert result["complete"] is True
    assert result["status"] == "warning"
    assert result["issues"] == ["Vannvarsel kl. 05:00"]
    assert result["waterStatus"] == "warning"
    assert result["waterStatusLabel"] == "Vannmangel kl. 05:00"
    assert result["waterWarningAt"].startswith("2026-08-14T05:00")


def test_empty_dock_after_completed_wash_does_not_downgrade_the_job() -> None:
    robot = row(duid="robot-a", name="2.etg", model="Qrevo")
    job = row(
        robot_duid="robot-a", record_id="job-dock-empty",
        begin_at=datetime(2026, 8, 14, 2, 0), end_at=datetime(2026, 8, 14, 3, 0),
        duration_minutes=60.0, duration_seconds=3600, cleaned_area_m2=30.0, area_m2=30.0,
        complete=True, error_code=0, wash_count=6, clean_times=1,
    )
    samples = [
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 4, 1), in_cleaning=True, battery=90, fan_power=105, water_box_mode=203, mop_mode=303, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=False),
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 5, 0), in_cleaning=True, battery=75, fan_power=105, water_box_mode=203, mop_mode=303, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=False),
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 5, 5), in_cleaning=False, battery=75, fan_power=105, water_box_mode=203, mop_mode=303, water_shortage_status=0, clear_water_status=1, clear_water_status_name="out_of_water", dock_error_status=39, is_charging=True),
    ]

    report = build_night_report(date(2026, 8, 14), [robot], [job], samples, [])

    result = report["robots"][0]["jobs"][0]
    assert report["conclusion"]["status"] == "neutral"
    assert result["status"] == "ok"
    assert result["statusLabel"] == "Fullført"
    assert result["issues"] == []


def test_robot_water_shortage_after_job_does_not_downgrade_completed_wash() -> None:
    robot = row(duid="robot-a", name="1.etg A", model="Qrevo")
    job = row(
        robot_duid="robot-a", record_id="job-later-shortage",
        begin_at=datetime(2026, 8, 14, 2, 0), end_at=datetime(2026, 8, 14, 3, 0),
        duration_minutes=60.0, duration_seconds=3600, cleaned_area_m2=30.0, area_m2=30.0,
        complete=True, error_code=0, wash_count=6, clean_times=1,
    )
    samples = [
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 4, 1), in_cleaning=True, battery=90, fan_power=105, water_box_mode=203, mop_mode=303, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=False),
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 5, 0), in_cleaning=True, battery=75, fan_power=105, water_box_mode=203, mop_mode=303, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=False),
        row(robot_duid="robot-a", timestamp=datetime(2026, 8, 14, 5, 8), in_cleaning=False, battery=75, fan_power=105, water_box_mode=203, mop_mode=303, water_shortage_status=1, clear_water_status=1, clear_water_status_name="out_of_water", dock_error_status=39, is_charging=True),
    ]

    report = build_night_report(date(2026, 8, 14), [robot], [job], samples, [])

    result = report["robots"][0]["jobs"][0]
    assert result["status"] == "ok"
    assert result["issues"] == []


def test_mop_mode_is_ignored_when_water_is_explicitly_off() -> None:
    robot = row(duid="robot-b", name="1.etg B", model="Q5")
    job = row(
        robot_duid="robot-b", record_id="vacuum-1",
        begin_at=datetime(2026, 8, 13, 21, 30), end_at=datetime(2026, 8, 13, 22, 0),
        duration_minutes=30.0, duration_seconds=1800, cleaned_area_m2=24.0, area_m2=24.0,
        complete=True, error_code=0, wash_count=None, clean_times=2,
    )
    samples = [
        row(robot_duid="robot-b", timestamp=datetime(2026, 8, 13, 23, 30), in_cleaning=True, battery=100, fan_power=104, water_box_mode=200, mop_mode=300, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=False),
        row(robot_duid="robot-b", timestamp=datetime(2026, 8, 14, 0, 0), in_cleaning=True, battery=80, fan_power=104, water_box_mode=200, mop_mode=300, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=False),
    ]

    report = build_night_report(date(2026, 8, 14), [robot], [job], samples, [])

    result = report["robots"][0]["jobs"][0]
    assert result["cleaningType"] == "vacuum"
    assert result["cleaningTypeLabel"] == "Støvsuging"
    assert result["waterStatus"] == "not_applicable"
    assert result["modeLabel"] == "Maks · 2 runder"


def test_night_report_exposes_relevant_water_events_with_timestamps() -> None:
    robot = row(duid="robot-water-events", name="VIP", model="Qrevo")
    events = [
        row(
            robot_duid="robot-water-events", timestamp=datetime(2026, 8, 14, 4, 20),
            field_name="clear_water_status", previous_label="OK", current_label="Tom",
            severity="warning",
        ),
        row(
            robot_duid="robot-water-events", timestamp=datetime(2026, 8, 14, 6, 10),
            field_name="clear_water_status", previous_label="Tom", current_label="OK",
            severity="info",
        ),
        row(
            robot_duid="robot-water-events", timestamp=datetime(2026, 8, 14, 6, 15),
            field_name="water_box_status", previous_label="Montert", current_label="Ikke montert",
            severity="info",
        ),
    ]

    report = build_night_report(
        date(2026, 8, 14), [robot], [], [], [], water_events=events,
    )

    water_events = report["robots"][0]["waterEvents"]
    assert len(water_events) == 2
    assert water_events[0]["timestamp"].startswith("2026-08-14T04:20")
    assert water_events[0]["title"] == "Rentvann i dokk"
    assert water_events[0]["currentLabel"] == "Tom"
    assert water_events[0]["severity"] == "warning"
    assert water_events[1]["currentLabel"] == "OK"
    assert water_events[1]["severity"] == "ok"


def test_night_report_marks_an_enabled_schedule_without_a_job_as_missing() -> None:
    robot = row(duid="robot-2", name="2.etg", model="Qrevo")
    schedules = [
        row(robot_duid="robot-2", schedule_id="vacuum-0100", cron="0 1 * * *", enabled=True, fan_power=104, water_box_mode=200, mop_mode=300, repeat=1),
        row(robot_duid="robot-2", schedule_id="mop-0300", cron="0 3 * * *", enabled=True, fan_power=105, water_box_mode=203, mop_mode=303, repeat=2),
    ]
    completed_job = row(
        robot_duid="robot-2", record_id="job-0300",
        begin_at=datetime(2026, 8, 14, 1, 0), end_at=datetime(2026, 8, 14, 3, 50),
        duration_minutes=127.0, duration_seconds=7620, cleaned_area_m2=74.0, area_m2=74.0,
        complete=True, error_code=0, wash_count=13, clean_times=2,
    )
    samples = [
        row(robot_duid="robot-2", timestamp=datetime(2026, 8, 14, 1, 0), in_cleaning=False, battery=100, fan_power=104, water_box_mode=200, mop_mode=300, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=True),
        row(robot_duid="robot-2", timestamp=datetime(2026, 8, 14, 3, 4), in_cleaning=True, battery=99, fan_power=105, water_box_mode=203, mop_mode=303, water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay", dock_error_status=0, is_charging=False),
    ]

    report = build_night_report(
        date(2026, 8, 14),
        [robot],
        [completed_job],
        samples,
        [],
        generated_at=datetime(2026, 8, 14, 8, 5),
        schedules=schedules,
    )

    result = report["robots"][0]
    assert report["conclusion"]["status"] == "warning"
    assert report["summary"]["plannedJobs"] == 2
    assert report["summary"]["plannedCompleted"] == 1
    assert report["summary"]["plannedMissing"] == 1
    assert result["statusLabel"] == "Planlagt jobb uteble"
    assert [planned["status"] for planned in result["scheduleCheck"]["jobs"]] == ["missing", "completed"]
    assert result["scheduleCheck"]["jobs"][0]["scheduledAt"].startswith("2026-08-14T01:00")
    assert result["scheduleCheck"]["jobs"][1]["actualStartedAt"].startswith("2026-08-14T03:00")
    assert result["findings"][0] == "Planlagt støvsuging kl. 01:00 ble ikke registrert."


def test_night_report_matches_a_completed_job_started_seventy_minutes_late() -> None:
    robot = row(duid="robot-delayed", name="1.etg A", model="Qrevo")
    schedule = row(
        robot_duid="robot-delayed", schedule_id="mop-0005", cron="5 0 * * *", enabled=True,
        fan_power=105, water_box_mode=203, mop_mode=303, repeat=1,
    )
    completed_job = row(
        robot_duid="robot-delayed", record_id="job-0115",
        begin_at=datetime(2026, 8, 13, 23, 15), end_at=datetime(2026, 8, 14, 0, 20),
        duration_minutes=65.0, duration_seconds=3900, cleaned_area_m2=38.0, area_m2=38.0,
        complete=True, error_code=0, wash_count=6, clean_times=1,
    )
    samples = [
        row(
            robot_duid="robot-delayed", timestamp=datetime(2026, 8, 14, 1, 15),
            in_cleaning=True, battery=100, fan_power=105, water_box_mode=203, mop_mode=303,
            water_shortage_status=0, clear_water_status=0, clear_water_status_name="okay",
            dock_error_status=0, is_charging=False,
        ),
    ]

    report = build_night_report(
        date(2026, 8, 14),
        [robot],
        [completed_job],
        samples,
        [],
        generated_at=datetime(2026, 8, 14, 8, 5),
        schedules=[schedule],
    )

    planned = report["robots"][0]["scheduleCheck"]
    assert planned["missing"] == 0
    assert planned["completed"] == 1
    assert planned["delayed"] == 1
    assert planned["jobs"][0]["delayMinutes"] == 70
    assert planned["jobs"][0]["statusLabel"] == "Startet +70 min"
    assert report["conclusion"]["title"] == "Planlagt rengjøring startet forsinket"


def test_schedule_check_keeps_an_active_job_running() -> None:
    robot = row(duid="robot-live", name="Dagrobot", model="Qrevo")
    schedule = row(
        robot_duid="robot-live", schedule_id="night-0300", cron="0 3 * * *", enabled=True,
        fan_power=104, water_box_mode=200, mop_mode=300, repeat=1,
    )
    active_job = row(
        robot_duid="robot-live", record_id="active-1",
        begin_at=datetime(2026, 8, 14, 1, 0), end_at=None,
        duration_minutes=10.0, duration_seconds=600, cleaned_area_m2=5.0, area_m2=5.0,
        complete=False, error_code=0, wash_count=None, clean_times=1,
    )

    report = build_night_report(
        date(2026, 8, 14),
        [robot],
        [active_job],
        [],
        [],
        generated_at=datetime(2026, 8, 14, 3, 10),
        schedules=[schedule],
    )

    planned = report["robots"][0]["scheduleCheck"]
    assert planned["completed"] == 0
    assert planned["running"] == 1
    assert planned["jobs"][0]["status"] == "running"
    assert planned["jobs"][0]["statusLabel"] == "Pågår"


def test_next_night_shows_active_and_paused_plans_without_missing_jobs() -> None:
    robot = row(duid="robot-plan", name="2.etg", model="Qrevo")
    schedules = [
        row(
            robot_duid="robot-plan", schedule_id="active-0100", cron="0 1 * * *", enabled=True,
            fan_power=105, water_box_mode=203, mop_mode=303, repeat=1,
        ),
        row(
            robot_duid="robot-plan", schedule_id="paused-0300", cron="0 3 * * *", enabled=False,
            fan_power=105, water_box_mode=203, mop_mode=303, repeat=2,
        ),
    ]

    report = build_night_report(
        date(2026, 8, 16),
        [robot],
        [],
        [],
        [],
        generated_at=datetime(2026, 8, 15, 12, 0),
        schedules=schedules,
    )

    planned = report["robots"][0]["scheduleCheck"]
    assert report["isForecast"] is True
    assert report["conclusion"]["title"] == "Neste natts renholdsplan"
    assert report["summary"]["plannedJobs"] == 1
    assert report["summary"]["plannedPending"] == 1
    assert report["summary"]["plannedPaused"] == 1
    assert report["summary"]["plannedMissing"] == 0
    assert planned["expected"] == 1
    assert planned["paused"] == 1
    assert [job["status"] for job in planned["jobs"]] == ["pending", "paused"]


def test_historical_report_uses_the_plan_snapshot_that_applied_at_night_start() -> None:
    robot = row(duid="robot-history", name="VIP", model="Qrevo", provider="roborock")
    current_schedule = row(
        robot_duid="robot-history", schedule_id="new-0300", cron="0 3 * * *", enabled=True,
        fan_power=105, water_box_mode=203, mop_mode=303, repeat=1,
    )
    snapshot = row(
        robot_duid="robot-history",
        captured_at=datetime(2026, 8, 13, 20, 0),
        schedules=[{
            "schedule_id": "old-0100", "cron": "0 1 * * *", "enabled": True,
            "fan_power": 105, "water_box_mode": 203, "mop_mode": 303, "repeat": 1,
        }],
    )
    job = row(
        robot_duid="robot-history", record_id="scheduled-job",
        begin_at=datetime(2026, 8, 13, 23, 0), end_at=datetime(2026, 8, 14, 0, 0),
        duration_minutes=60.0, duration_seconds=3600, cleaned_area_m2=25.0, area_m2=25.0,
        complete=True, error_code=0, wash_count=5, clean_times=1, start_type=3,
    )

    report = build_night_report(
        date(2026, 8, 14), [robot], [job], [], [],
        generated_at=datetime(2026, 8, 14, 8, 5),
        schedules=[current_schedule], schedule_snapshots=[snapshot],
    )

    result = report["robots"][0]
    assert result["scheduleCheck"]["historyAvailable"] is True
    assert result["scheduleCheck"]["jobs"][0]["scheduleId"] == "old-0100"
    assert result["scheduleCheck"]["completed"] == 1
    assert result["jobs"][0]["origin"] == "planned"
    assert result["readiness"]["evaluated"] is True
    assert result["readiness"]["readyBeforeOpening"] is True


def test_event_triggered_job_is_marked_but_not_used_for_plan_assessment() -> None:
    robot = row(duid="robot-mixed", name="1.etg B", model="Q5", provider="roborock")
    snapshot = row(
        robot_duid="robot-mixed",
        captured_at=datetime(2026, 8, 13, 20, 0),
        schedules=[{
            "schedule_id": "night-0100", "cron": "0 1 * * *", "enabled": True,
            "fan_power": 104, "water_box_mode": 200, "mop_mode": 300, "repeat": 1,
        }],
    )
    planned_job = row(
        robot_duid="robot-mixed", record_id="planned",
        begin_at=datetime(2026, 8, 13, 23, 0), end_at=datetime(2026, 8, 14, 0, 0),
        duration_minutes=60.0, duration_seconds=3600, cleaned_area_m2=30.0, area_m2=30.0,
        complete=True, error_code=0, wash_count=None, clean_times=1, start_type=3,
    )
    event_job = row(
        robot_duid="robot-mixed", record_id="door-triggered",
        begin_at=datetime(2026, 8, 14, 4, 30), end_at=datetime(2026, 8, 14, 5, 0),
        duration_minutes=30.0, duration_seconds=1800, cleaned_area_m2=12.0, area_m2=12.0,
        complete=True, error_code=0, wash_count=None, clean_times=1, start_type=2,
    )

    report = build_night_report(
        date(2026, 8, 14), [robot], [planned_job, event_job], [], [],
        generated_at=datetime(2026, 8, 14, 8, 5), schedule_snapshots=[snapshot],
    )

    result = report["robots"][0]
    jobs = {job["recordId"]: job for job in result["jobs"]}
    assert jobs["planned"]["origin"] == "planned"
    assert jobs["door-triggered"]["origin"] == "other"
    assert result["totals"]["otherJobs"] == 1
    assert result["readiness"]["readyBeforeOpening"] is True
    assert result["readiness"]["lastJobEndedAt"].startswith("2026-08-14T02:00")
    assert report["summary"]["readyBeforeOpening"] == 1


def test_historical_report_does_not_guess_when_snapshot_history_is_missing() -> None:
    robot = row(duid="robot-no-history", name="2.etg", model="Qrevo", provider="roborock")
    schedule = row(
        robot_duid="robot-no-history", schedule_id="current", cron="0 1 * * *", enabled=True,
        fan_power=105, water_box_mode=203, mop_mode=303, repeat=1,
    )

    report = build_night_report(
        date(2026, 8, 14), [robot], [], [], [],
        generated_at=datetime(2026, 8, 14, 8, 5),
        schedules=[schedule], schedule_snapshots=[],
    )

    result = report["robots"][0]
    assert result["scheduleCheck"]["historyAvailable"] is False
    assert result["scheduleCheck"]["expected"] == 0
    assert result["readiness"]["evaluated"] is False
    assert report["summary"]["activeRobots"] == 0


def test_jobs_without_plan_history_are_reported_as_unclassified() -> None:
    robot = row(duid="robot-no-history-job", name="VIP", model="Qrevo", provider="roborock")
    job = row(
        robot_duid="robot-no-history-job", record_id="historical-job",
        begin_at=datetime(2026, 8, 13, 23, 0), end_at=datetime(2026, 8, 14, 0, 0),
        duration_minutes=60.0, duration_seconds=3600, cleaned_area_m2=25.0, area_m2=25.0,
        complete=True, error_code=0, wash_count=5, clean_times=1, start_type=3,
    )

    report = build_night_report(
        date(2026, 8, 14), [robot], [job], [], [],
        generated_at=datetime(2026, 8, 14, 8, 5), schedule_snapshots=[],
    )

    assert report["robots"][0]["jobs"][0]["origin"] == "unknown"
    assert report["robots"][0]["totals"]["otherJobs"] == 0
    assert report["robots"][0]["totals"]["unclassifiedJobs"] == 1
    assert report["summary"]["unclassifiedJobs"] == 1
    assert report["conclusion"]["title"] == "Nattens rengjøring er registrert"


def test_manual_job_near_schedule_time_does_not_satisfy_the_plan() -> None:
    robot = row(duid="robot-manual", name="1.etg A", model="Qrevo", provider="roborock")
    snapshot = row(
        robot_duid="robot-manual", captured_at=datetime(2026, 8, 13, 20, 0),
        schedules=[{
            "schedule_id": "night-0100", "cron": "0 1 * * *", "enabled": True,
            "fan_power": 105, "water_box_mode": 203, "mop_mode": 303, "repeat": 1,
        }],
    )
    manual_job = row(
        robot_duid="robot-manual", record_id="manual-near-plan",
        begin_at=datetime(2026, 8, 13, 23, 2), end_at=datetime(2026, 8, 14, 0, 0),
        duration_minutes=58.0, duration_seconds=3480, cleaned_area_m2=25.0, area_m2=25.0,
        complete=True, error_code=0, wash_count=5, clean_times=1, start_type=2,
    )

    report = build_night_report(
        date(2026, 8, 14), [robot], [manual_job], [], [],
        generated_at=datetime(2026, 8, 14, 8, 5), schedule_snapshots=[snapshot],
    )

    result = report["robots"][0]
    assert result["scheduleCheck"]["missing"] == 1
    assert result["scheduleCheck"]["matchedRecordIds"] == []
    assert result["jobs"][0]["origin"] == "other"
    assert result["readiness"]["readyBeforeOpening"] is False


def test_schedule_change_during_night_only_affects_later_occurrences() -> None:
    robot = row(duid="robot-plan-change", name="2.etg", model="Qrevo", provider="roborock")
    baseline = row(
        robot_duid="robot-plan-change", captured_at=datetime(2026, 8, 13, 20, 0),
        schedules=[{
            "schedule_id": "night-0100", "cron": "0 1 * * *", "enabled": True,
            "fan_power": 105, "water_box_mode": 203, "mop_mode": 303, "repeat": 1,
        }],
    )
    removed_before_start = row(
        robot_duid="robot-plan-change", captured_at=datetime(2026, 8, 14, 0, 30),
        schedules=[],
    )

    report = build_night_report(
        date(2026, 8, 14), [robot], [], [], [],
        generated_at=datetime(2026, 8, 14, 8, 5),
        schedule_snapshots=[baseline, removed_before_start],
    )

    result = report["robots"][0]
    assert result["scheduleCheck"]["historyAvailable"] is True
    assert result["scheduleCheck"]["expected"] == 0
    assert result["scheduleCheck"]["missing"] == 0
    assert result["readiness"]["evaluated"] is False
    assert report["summary"]["activeRobots"] == 0
