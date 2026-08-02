from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import median
from typing import Any

import cv2
import numpy as np

from .model import ModelRegistry, sampled_archive_images
from .profiles import PROFILES, prepare_profile_image


def percentile(values: list[float], quantile: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=np.float32), quantile)) if values else 0.0


def evaluate_profile(
    registry: ModelRegistry,
    profile_id: str,
    sample_count: int,
    seed: int,
) -> dict[str, Any]:
    profile = PROFILES[profile_id]
    model = registry.models[profile_id]
    if not model.ready:
        raise RuntimeError(f"Model {profile_id} is not ready")
    candidates, total = sampled_archive_images(registry.snapshot_root, profile, 1_000_000)
    selected = random.Random(f"{seed}:{profile_id}").sample(
        candidates, min(sample_count, len(candidates))
    )
    ratios: list[float] = []
    anomalies = 0
    synthetic_ratios: list[float] = []
    for path in selected:
        source = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if source is None:
            continue
        atlas = prepare_profile_image(profile, source, is_source=True)
        result, _heatmap = model.infer(atlas)
        ratio = float(result["score_ratio"])
        ratios.append(ratio)
        anomalies += int(bool(result["is_anomaly"]))

        changed = atlas.copy()
        columns = 1 if len(profile.regions) == 1 else 2
        rows = (len(profile.regions) + columns - 1) // columns
        tile_size = changed.shape[1] // max(columns, rows)
        for index in range(len(profile.regions)):
            x = (index % columns) * tile_size
            y = (index // columns) * tile_size
            changed[
                y + tile_size // 4 : y + tile_size * 3 // 4,
                x + tile_size // 4 : x + tile_size * 3 // 4,
            ] = 20
        synthetic, _synthetic_heatmap = model.infer(changed)
        synthetic_ratios.append(float(synthetic["score_ratio"]))

    return {
        "profile_id": profile_id,
        "archive_candidates": total,
        "evaluated": len(ratios),
        "archive_anomalies": anomalies,
        "archive_anomaly_rate": round(anomalies / max(1, len(ratios)), 4),
        "ratio_median": round(median(ratios), 4) if ratios else 0.0,
        "ratio_p90": round(percentile(ratios, 0.90), 4),
        "ratio_max": round(max(ratios), 4) if ratios else 0.0,
        "synthetic_ratio_median": round(median(synthetic_ratios), 4)
        if synthetic_ratios
        else 0.0,
        "synthetic_detection_rate": round(
            sum(ratio > 1.0 for ratio in synthetic_ratios) / max(1, len(synthetic_ratios)),
            4,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate visual AI profiles against the archive")
    parser.add_argument("--snapshots", type=Path, default=Path("/snapshots"))
    parser.add_argument("--data", type=Path, default=Path("/data"))
    parser.add_argument("--samples", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20260801)
    parser.add_argument("--profile", choices=tuple(PROFILES))
    args = parser.parse_args()
    registry = ModelRegistry(args.snapshots, args.data, sample_limit=240)
    profile_ids = (args.profile,) if args.profile else tuple(PROFILES)
    results = [
        evaluate_profile(registry, profile_id, max(1, args.samples), args.seed)
        for profile_id in profile_ids
    ]
    print(json.dumps({"profiles": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
