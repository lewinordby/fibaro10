"""Full comparison outputs recorded from build 1831 before extraction."""

import asyncio
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
import main
from comparison_cases import contracts, full_overview_contracts

FIXTURE = Path(__file__).with_name("fixtures") / "comparison_contracts.json"


def test_comparison_outputs_and_requested_periods_are_unchanged():
    actual = asyncio.run(contracts(main))
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert set(actual) == set(expected)
    assert {key: value for key, value in actual.items() if value != expected[key]} == {}


def test_unfiltered_overview_retains_non_business_fields():
    actual = asyncio.run(full_overview_contracts(main))
    expected = json.loads(FIXTURE.with_name("overview_full_contracts.json").read_text(encoding="utf-8"))
    assert actual == expected


if __name__ == "__main__":
    if sys.argv[1:] != ["--record"]:
        raise SystemExit("Only --record is supported; use before changing comparison behavior.")
    FIXTURE.write_text(json.dumps(asyncio.run(contracts(main)), indent=2) + "\n", encoding="utf-8")
