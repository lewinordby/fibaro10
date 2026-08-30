from datetime import datetime
import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

from main import build_sunbed_power_analysis
from datetime import timedelta, timezone
from pathlib import Path
import random
import pytest
import main


def test_sunbed_power_analysis_uses_stable_baseline_for_session_samples() -> None:
    tanning_session = SimpleNamespace(
        id=1,
        room_id="1",
        sun2_bed_id="bed-1",
        started_at=datetime(2026, 8, 1, 10, 0),
        ended_at=datetime(2026, 8, 1, 10, 20),
        duration_minutes=20,
    )
    samples = [
        {"bucket_start": datetime(2026, 8, 1, 9, 59, 30), "differanse_beregnet_w": 1000},
        {"bucket_start": datetime(2026, 8, 1, 10, 3, 0), "differanse_beregnet_w": 7000},
        {"bucket_start": datetime(2026, 8, 1, 10, 3, 30), "differanse_beregnet_w": 7000},
        {"bucket_start": datetime(2026, 8, 1, 10, 4, 0), "differanse_beregnet_w": 7000},
        {"bucket_start": datetime(2026, 8, 1, 10, 4, 30), "differanse_beregnet_w": 7000},
        {"bucket_start": datetime(2026, 8, 1, 10, 30, 0), "differanse_beregnet_w": 1000},
    ]

    analysis = build_sunbed_power_analysis([tanning_session], samples, {})

    assert analysis["summary"]["single_samples"] == 4
    assert analysis["summary"]["global_baseline_w"] == 1000
    assert len(analysis["rooms"]) == 1
    assert analysis["rooms"][0]["estimate_w"] == 6000
    assert analysis["rooms"][0]["estimated_kwh"] == 0.2


@pytest.mark.parametrize("seed", range(24))
def test_optimized_analysis_matches_build_1836_for_identical_inputs(seed):
    namespace = {**build_sunbed_power_analysis.__globals__, **vars(main), "dependencies": main.energy_dependencies}
    source = (Path(__file__).parent / "fixtures/sunbed_analysis_1836.py").read_text(encoding="utf-8")
    exec(compile(source, "sunbed_analysis_1836.py", "exec"), namespace)
    original = namespace["build_sunbed_power_analysis"]
    rng = random.Random(seed)
    start = datetime(2026, 8, 1, 9)
    sessions = [SimpleNamespace(id=n, room_id=str(n % 3 + 1), sun2_bed_id=f"bed-{n % 3 + 1}",
                               started_at=start + timedelta(minutes=10 * n), ended_at=None,
                               duration_minutes=rng.choice([10, 15, 20, 25])) for n in range(1, 10)]
    samples = [{"bucket_start": start + timedelta(seconds=30 * n), "differanse_beregnet_w": rng.randrange(250, 22000)} for n in range(260)]
    ventilation = [{"bucket_start": start + timedelta(seconds=300 * n + seed % 3), "fan_tak": bool(n % 2)} for n in range(27)]
    if seed % 2:
        rng.shuffle(samples)
        rng.shuffle(ventilation)
    if seed % 3 == 0:
        # Equivalent timezone-aware observations must give the same values.
        for row in samples:
            row["bucket_start"] = row["bucket_start"].replace(tzinfo=timezone(timedelta(hours=2)))
    if seed == 23:
        ventilation = []
    assert build_sunbed_power_analysis(sessions, samples, {}, ventilation) == original(sessions, samples, {}, ventilation)
