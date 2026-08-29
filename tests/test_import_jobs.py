from pathlib import Path

from import_jobs import IMPORT_JOB_DEFINITIONS, IMPORT_JOB_NUMBER_BY_NAME


def test_import_job_numbers_are_stable_and_complete():
    assert set(IMPORT_JOB_NUMBER_BY_NAME) == set(IMPORT_JOB_DEFINITIONS)
    assert list(IMPORT_JOB_NUMBER_BY_NAME.values()) == list(range(1, len(IMPORT_JOB_DEFINITIONS) + 1))


def test_core_import_jobs_are_defined():
    for job_name in (
        "hc3_energy_1min",
        "easypark_parking_import",
        "sun2_sessions_import",
        "parking_vehicle_svv_sync",
    ):
        definition = IMPORT_JOB_DEFINITIONS[job_name]
        assert definition["title"]
        assert definition["category"]
        assert "description" in definition


def test_hc3_energy_watchdog_runs_in_the_python_worker():
    script = (Path(__file__).parents[1] / "scripts" / "hc3-energy-watchdog.sh").read_text(encoding="utf-8")

    assert 'CONTAINER="${FIBARO10_CONTAINER:-fibaro10_worker}"' in script
    assert 'CONTAINER="${FIBARO10_CONTAINER:-fibaro10}"' not in script
