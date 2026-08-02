from datetime import datetime
import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")

from main import build_sunbed_power_analysis


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
