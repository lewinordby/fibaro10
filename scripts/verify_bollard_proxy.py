from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main


async def verify() -> None:
    payload = await main.api_unifi_protect_bollards()
    monitors = payload.get("camera_monitors", [])
    if len(monitors) != 3:
        raise RuntimeError(f"Expected three camera monitors, got {len(monitors)}")
    if not all(
        str(item.get("baseline_url", "")).startswith("/api/unifi-protect/bollards/")
        for item in monitors
    ):
        raise RuntimeError("Fibaro10 did not rewrite all camera image URLs")
    baseline_images = []
    for monitor in monitors:
        image = await main.api_unifi_protect_bollard_camera_image(
            str(monitor["camera_id"]),
            "baseline",
        )
        if image.media_type != "image/jpeg" or len(image.body) < 10_000:
            raise RuntimeError("Fibaro10 did not return a Protect Ledger camera image")
        baseline_images.append(
            {
                "camera": monitor.get("camera_name"),
                "bytes": len(image.body),
                "sha256": hashlib.sha256(image.body).hexdigest(),
            }
        )
    print(
        {
            "camera_monitors": len(monitors),
            "comparison_mode": payload.get("comparison_mode"),
            "rewritten_urls": True,
            "baseline_images": baseline_images,
        }
    )


if __name__ == "__main__":
    asyncio.run(verify())
