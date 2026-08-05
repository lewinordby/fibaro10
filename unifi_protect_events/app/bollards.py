from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping, Optional, Sequence

import aiohttp
import asyncpg
import cv2
import numpy as np


logger = logging.getLogger("unifi_protect_events.bollards")

TARGET_CAMERA_NAMES = (
    "G6 Butikk Nord",
    "G6 Butikk Front",
    "G6 Solstudio Front",
)

# Fixed 4K source-pixel rectangles used only for presentation. Images are never
# geometrically normalized: the same source pixels are cut out every time.
BOLLARD_CAMERA_DISPLAY_CROPS: dict[str, dict[str, int]] = {
    "G6 Butikk Nord": {"x": 614, "y": 324, "width": 1152, "height": 1836},
    "G6 Butikk Front": {"x": 0, "y": 1123, "width": 2803, "height": 1037},
    "G6 Solstudio Front": {"x": 2765, "y": 0, "width": 537, "height": 734},
}

# Fixed structures that need independent comparison, status and notification.
# Crops are absolute source pixels and are never resized or perspective-corrected.
FIXED_STRUCTURE_MONITORS: dict[str, dict[str, Any]] = {
    "trapp-solstudio": {
        "display_name": "Trapp ved Solstudio",
        "asset_type": "stairs",
        "camera_name": "G6 Solstudio Front",
        "crop": {"x": 2200, "y": 400, "width": 1640, "height": 1760},
        "analysis_polygon": (
            {"x": 0.325, "y": 0.15},
            {"x": 0.545, "y": 0.22},
            {"x": 0.565, "y": 0.93},
            {"x": 0.14, "y": 0.85},
        ),
        "change_fraction_threshold": 0.015,
        "obscured_fraction_threshold": 0.06,
    },
}

# Tight, internal comparison zones around the visible metal structures. They are
# not drawn in the UI. The cameras are fixed, so every zone is compared at its
# original pixel position without geometric correction of the camera image.
BOLLARD_CAMERA_ANALYSIS_ZONES: dict[str, tuple[dict[str, Any], ...]] = {
    "G6 Butikk Nord": (
        {"key": "nord-1", "x": 0.205, "y": 0.190, "width": 0.055, "height": 0.250},
        {"key": "nord-2", "x": 0.235, "y": 0.440, "width": 0.065, "height": 0.240},
        {"key": "nord-3", "x": 0.305, "y": 0.840, "width": 0.075, "height": 0.155},
    ),
    "G6 Butikk Front": (
        {"key": "front-1", "x": 0.000, "y": 0.540, "width": 0.055, "height": 0.180},
        {"key": "front-2", "x": 0.370, "y": 0.790, "width": 0.145, "height": 0.105},
        {"key": "front-3", "x": 0.490, "y": 0.810, "width": 0.145, "height": 0.110},
        {"key": "front-4", "x": 0.585, "y": 0.825, "width": 0.130, "height": 0.120},
    ),
    "G6 Solstudio Front": (
        {"key": "solstudio-1-3", "x": 0.740, "y": 0.000, "width": 0.080, "height": 0.340},
    ),
}
BOLLARD_ZONE_MATCH_THRESHOLD = 0.10
BOLLARD_ZONE_MOVEMENT_TOLERANCE_PIXELS = 30

VISUAL_AI_CAMERA_PROFILES: dict[str, str] = {
    "G6 Butikk Nord": "north-bollards",
    "G6 Butikk Front": "front-bollards",
    "G6 Solstudio Front": "solstudio-bollards",
}
VISUAL_AI_ASSET_PROFILES: dict[str, str] = {
    "trapp-solstudio": "solstudio-stairs",
}

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_bollard_settings (
        console_key VARCHAR PRIMARY KEY,
        monitoring_enabled BOOLEAN NOT NULL DEFAULT FALSE,
        analysis_interval_seconds INTEGER NOT NULL DEFAULT 300
            CHECK (analysis_interval_seconds BETWEEN 5 AND 300),
        confirmation_seconds INTEGER NOT NULL DEFAULT 300
            CHECK (confirmation_seconds BETWEEN 10 AND 1800),
        notification_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_bollard_camera_monitors (
        console_key VARCHAR NOT NULL,
        camera_id VARCHAR NOT NULL,
        camera_name VARCHAR NOT NULL,
        baseline_path TEXT,
        baseline_captured_at TIMESTAMPTZ,
        latest_path TEXT,
        latest_captured_at TIMESTAMPTZ,
        overlay_path TEXT,
        status VARCHAR NOT NULL DEFAULT 'uncalibrated',
        change_score DOUBLE PRECISION,
        changed_fraction DOUBLE PRECISION,
        largest_change_fraction DOUBLE PRECISION,
        mean_difference DOUBLE PRECISION,
        change_components JSONB NOT NULL DEFAULT '[]'::jsonb,
        alignment JSONB NOT NULL DEFAULT '{}'::jsonb,
        consecutive_abnormal INTEGER NOT NULL DEFAULT 0,
        abnormal_since TIMESTAMPTZ,
        last_checked_at TIMESTAMPTZ,
        last_error TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (console_key, camera_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_fixed_asset_monitors (
        console_key VARCHAR NOT NULL,
        asset_key VARCHAR NOT NULL,
        display_name VARCHAR NOT NULL,
        asset_type VARCHAR NOT NULL,
        camera_id VARCHAR NOT NULL,
        camera_name VARCHAR NOT NULL,
        crop JSONB NOT NULL,
        baseline_path TEXT,
        baseline_captured_at TIMESTAMPTZ,
        latest_path TEXT,
        latest_captured_at TIMESTAMPTZ,
        overlay_path TEXT,
        status VARCHAR NOT NULL DEFAULT 'uncalibrated',
        change_score DOUBLE PRECISION,
        changed_fraction DOUBLE PRECISION,
        largest_change_fraction DOUBLE PRECISION,
        mean_difference DOUBLE PRECISION,
        change_components JSONB NOT NULL DEFAULT '[]'::jsonb,
        consecutive_abnormal INTEGER NOT NULL DEFAULT 0,
        abnormal_since TIMESTAMPTZ,
        last_checked_at TIMESTAMPTZ,
        last_error TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (console_key, asset_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_bollard_regions (
        region_id BIGSERIAL PRIMARY KEY,
        console_key VARCHAR NOT NULL,
        bollard_key VARCHAR NOT NULL,
        display_name VARCHAR NOT NULL,
        camera_id VARCHAR NOT NULL,
        camera_name VARCHAR,
        roi JSONB NOT NULL,
        enabled BOOLEAN NOT NULL DEFAULT TRUE,
        baseline_path TEXT,
        baseline_captured_at TIMESTAMPTZ,
        match_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.42,
        movement_tolerance_pixels INTEGER NOT NULL DEFAULT 12,
        status VARCHAR NOT NULL DEFAULT 'uncalibrated',
        last_match_score DOUBLE PRECISION,
        last_expected_score DOUBLE PRECISION,
        last_offset_x INTEGER,
        last_offset_y INTEGER,
        consecutive_abnormal INTEGER NOT NULL DEFAULT 0,
        abnormal_since TIMESTAMPTZ,
        last_checked_at TIMESTAMPTZ,
        last_error TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (console_key, bollard_key, camera_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS unifi_protect_bollard_incidents (
        incident_id BIGSERIAL PRIMARY KEY,
        console_key VARCHAR NOT NULL,
        bollard_key VARCHAR NOT NULL,
        display_name VARCHAR NOT NULL,
        status VARCHAR NOT NULL DEFAULT 'active',
        severity VARCHAR NOT NULL DEFAULT 'alarm',
        detected_at TIMESTAMPTZ NOT NULL,
        confirmed_at TIMESTAMPTZ,
        last_observed_at TIMESTAMPTZ NOT NULL,
        acknowledged_at TIMESTAMPTZ,
        acknowledged_by VARCHAR,
        resolved_at TIMESTAMPTZ,
        resolution_reason VARCHAR,
        evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
        context JSONB NOT NULL DEFAULT '{}'::jsonb,
        notification_status VARCHAR NOT NULL DEFAULT 'pending',
        notification_at TIMESTAMPTZ,
        notification_error TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_bollard_regions_camera
        ON unifi_protect_bollard_regions (console_key, camera_id, enabled)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_bollard_incidents_status
        ON unifi_protect_bollard_incidents (console_key, status, detected_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_bollard_camera_monitors_status
        ON unifi_protect_bollard_camera_monitors (console_key, status, last_checked_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_unifi_protect_fixed_asset_monitors_status
        ON unifi_protect_fixed_asset_monitors (console_key, status, last_checked_at DESC)
    """,
    """
    ALTER TABLE unifi_protect_bollard_camera_monitors
        ADD COLUMN IF NOT EXISTS ai_profile_id TEXT,
        ADD COLUMN IF NOT EXISTS ai_status VARCHAR NOT NULL DEFAULT 'not_ready',
        ADD COLUMN IF NOT EXISTS ai_score DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS ai_threshold DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS ai_score_ratio DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS ai_is_anomaly BOOLEAN,
        ADD COLUMN IF NOT EXISTS ai_heatmap_path TEXT,
        ADD COLUMN IF NOT EXISTS ai_model_version TEXT,
        ADD COLUMN IF NOT EXISTS ai_trained_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS ai_training_samples INTEGER,
        ADD COLUMN IF NOT EXISTS ai_inference_ms DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS ai_last_checked_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS ai_last_error TEXT,
        ADD COLUMN IF NOT EXISTS hybrid_status VARCHAR NOT NULL DEFAULT 'classical_only'
    """,
    """
    ALTER TABLE unifi_protect_fixed_asset_monitors
        ADD COLUMN IF NOT EXISTS ai_profile_id TEXT,
        ADD COLUMN IF NOT EXISTS ai_status VARCHAR NOT NULL DEFAULT 'not_ready',
        ADD COLUMN IF NOT EXISTS ai_score DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS ai_threshold DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS ai_score_ratio DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS ai_is_anomaly BOOLEAN,
        ADD COLUMN IF NOT EXISTS ai_heatmap_path TEXT,
        ADD COLUMN IF NOT EXISTS ai_model_version TEXT,
        ADD COLUMN IF NOT EXISTS ai_trained_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS ai_training_samples INTEGER,
        ADD COLUMN IF NOT EXISTS ai_inference_ms DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS ai_last_checked_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS ai_last_error TEXT,
        ADD COLUMN IF NOT EXISTS hybrid_status VARCHAR NOT NULL DEFAULT 'classical_only'
    """,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def bollard_notification_message(incident: Mapping[str, Any]) -> str:
    """Build the external push text without leaking locally stored context."""
    if str(incident.get("bollard_key") or "") == "trapp-solstudio":
        return "Trappa ved Solstudio ser ut til å være endret eller skadet. Kontroller kamera og trapp."
    display_name = str(incident.get("display_name") or "En pullert").strip()
    return f"{display_name} ser ut til å være flyttet. Kontrollér kamera og område."


def bollard_alarm_click_url(base_url: str, incident_id: Any) -> str:
    return f"{str(base_url).rstrip('/')}/?section=pullerter&incident={incident_id}"


def normalized_bollard_key(value: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "-", value.strip().casefold()).strip("-")
    if not key:
        raise ValueError("Pullerten må ha et navn")
    return key[:80]


def normalized_roi(value: Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError("Området har ugyldig JSON") from error
    if not isinstance(value, Mapping):
        raise ValueError("Området må inneholde x, y, width og height")
    polygon_value = value.get("polygon")
    polygon: list[dict[str, float]] | None = None
    if polygon_value is not None:
        if not isinstance(polygon_value, list) or not 3 <= len(polygon_value) <= 80:
            raise ValueError("Overlayen må ha mellom 3 og 80 punkter")
        polygon = []
        try:
            for point in polygon_value:
                point_x = float(point["x"])
                point_y = float(point["y"])
                if not 0 <= point_x <= 1 or not 0 <= point_y <= 1:
                    raise ValueError("Overlaypunktet ligger utenfor bildet")
                polygon.append({"x": round(point_x, 6), "y": round(point_y, 6)})
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Overlayen inneholder et ugyldig punkt") from error
        area = abs(
            sum(
                polygon[index]["x"] * polygon[(index + 1) % len(polygon)]["y"]
                - polygon[(index + 1) % len(polygon)]["x"] * polygon[index]["y"]
                for index in range(len(polygon))
            )
        ) / 2
        if area < 0.00004:
            raise ValueError("Overlayen er for liten")
        minimum_x = min(point["x"] for point in polygon)
        minimum_y = min(point["y"] for point in polygon)
        maximum_x = max(point["x"] for point in polygon)
        maximum_y = max(point["y"] for point in polygon)
        roi = {
            "x": minimum_x,
            "y": minimum_y,
            "width": maximum_x - minimum_x,
            "height": maximum_y - minimum_y,
        }
    else:
        try:
            roi = {key: float(value[key]) for key in ("x", "y", "width", "height")}
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Området må inneholde x, y, width og height") from error
    if roi["width"] < 0.01 or roi["height"] < 0.01:
        raise ValueError("Det markerte området er for lite")
    if roi["x"] < 0 or roi["y"] < 0:
        raise ValueError("Området ligger utenfor bildet")
    if roi["x"] + roi["width"] > 1.00001 or roi["y"] + roi["height"] > 1.00001:
        raise ValueError("Området ligger utenfor bildet")
    result: dict[str, Any] = {
        key: round(max(0.0, min(1.0, number)), 6) for key, number in roi.items()
    }
    if polygon is not None:
        result["polygon"] = polygon
    return result


def roi_pixels(roi: Mapping[str, Any], width: int, height: int) -> tuple[int, int, int, int]:
    value = normalized_roi(roi)
    x = max(0, min(width - 1, round(value["x"] * width)))
    y = max(0, min(height - 1, round(value["y"] * height)))
    right = max(x + 2, min(width, round((value["x"] + value["width"]) * width)))
    bottom = max(y + 2, min(height, round((value["y"] + value["height"]) * height)))
    return x, y, right - x, bottom - y


def roi_polygon_mask(
    roi: Mapping[str, Any] | str,
    image_width: int,
    image_height: int,
    x: int,
    y: int,
    width: int,
    height: int,
) -> np.ndarray | None:
    value = normalized_roi(roi)
    polygon = value.get("polygon")
    if not polygon:
        return None
    points = np.array(
        [
            [
                max(0, min(width - 1, round(point["x"] * image_width) - x)),
                max(0, min(height - 1, round(point["y"] * image_height) - y)),
            ]
            for point in polygon
        ],
        dtype=np.int32,
    )
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [points], 255)
    return mask


def decode_jpeg(content: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None or image.ndim != 3:
        raise ValueError("Kamerabildet kunne ikke dekodes")
    return image


def fixed_pixel_crop(image: np.ndarray, crop: Mapping[str, Any]) -> np.ndarray:
    """Cut an absolute source-pixel rectangle without resizing or warping it."""
    image_height, image_width = image.shape[:2]
    x = int(crop["x"])
    y = int(crop["y"])
    width = int(crop["width"])
    height = int(crop["height"])
    if x < 0 or y < 0 or width < 1 or height < 1:
        raise ValueError("Kamerautslettet har ugyldige pikselkoordinater")
    if x + width > image_width or y + height > image_height:
        raise ValueError(
            f"Kamerabildet er {image_width}x{image_height}, men det faste utsnittet "
            f"krever minst {x + width}x{y + height} piksler"
        )
    return image[y : y + height, x : x + width].copy()


def normalize_fixed_camera_frame(
    baseline: np.ndarray,
    current: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Preserve fixed camera pixels and reject any changed image geometry."""
    source_height, source_width = current.shape[:2]
    target_height, target_width = baseline.shape[:2]
    if (source_height, source_width) != (target_height, target_width):
        raise ValueError(
            f"Kameraoppløsningen er endret fra {target_width}x{target_height} til "
            f"{source_width}x{source_height}; bildet blir ikke skalert"
        )
    return current, {
        "aligned": False,
        "mode": "fixed_camera_pixels",
        "resized": False,
        "source_size": {"width": source_width, "height": source_height},
        "comparison_size": {"width": target_width, "height": target_height},
    }


def _edge_image(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    equalized = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    blurred = cv2.GaussianBlur(equalized, (5, 5), 0)
    return cv2.Canny(blurred, 45, 135)


def compare_bollard_region(
    baseline: np.ndarray,
    current: np.ndarray,
    roi: Mapping[str, Any],
    *,
    match_threshold: float = 0.42,
    movement_tolerance_pixels: int = 12,
) -> dict[str, Any]:
    """Compare a tight bollard ROI and search nearby for physical displacement."""
    height, width = baseline.shape[:2]
    if current.shape[:2] != baseline.shape[:2]:
        raise ValueError("Kamerabildene har ulik oppløsning og blir ikke skalert")
    x, y, roi_width, roi_height = roi_pixels(roi, width, height)
    template = _edge_image(baseline[y : y + roi_height, x : x + roi_width])
    polygon_mask = roi_polygon_mask(roi, width, height, x, y, roi_width, roi_height)
    margin_x = max(movement_tolerance_pixels * 5, round(roi_width * 0.9))
    margin_y = max(movement_tolerance_pixels * 5, round(roi_height * 0.55))
    search_x = max(0, x - margin_x)
    search_y = max(0, y - margin_y)
    search_right = min(width, x + roi_width + margin_x)
    search_bottom = min(height, y + roi_height + margin_y)
    search = _edge_image(current[search_y:search_bottom, search_x:search_right])
    if search.shape[0] < template.shape[0] or search.shape[1] < template.shape[1]:
        raise ValueError("Søkeområdet er mindre enn pullertområdet")
    visible_template = cv2.bitwise_and(template, template, mask=polygon_mask) if polygon_mask is not None else template
    if int(np.count_nonzero(visible_template)) < max(12, round(template.size * 0.002)):
        raise ValueError("Referanseområdet har for få synlige kanter")
    effective_threshold = float(match_threshold)
    if polygon_mask is not None:
        result = cv2.matchTemplate(search, template, cv2.TM_CCORR_NORMED, mask=polygon_mask)
        result = np.nan_to_num(result, nan=-1.0, posinf=-1.0, neginf=-1.0)
        effective_threshold = max(effective_threshold, 0.68)
    else:
        result = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
    _minimum, best_score, _minimum_location, best_location = cv2.minMaxLoc(result)
    expected_x = x - search_x
    expected_y = y - search_y
    expected_x = max(0, min(result.shape[1] - 1, expected_x))
    expected_y = max(0, min(result.shape[0] - 1, expected_y))
    expected_score = float(result[expected_y, expected_x])
    offset_x = int(best_location[0] - expected_x)
    offset_y = int(best_location[1] - expected_y)
    distance = math.hypot(offset_x, offset_y)
    best_score = float(best_score) if math.isfinite(best_score) else -1.0
    expected_score = expected_score if math.isfinite(expected_score) else -1.0
    if expected_score >= effective_threshold or (
        best_score >= effective_threshold and distance <= movement_tolerance_pixels
    ):
        state = "normal"
    elif best_score >= effective_threshold:
        state = "moved"
    else:
        state = "missing"
    return {
        "state": state,
        "best_score": round(best_score, 4),
        "expected_score": round(expected_score, 4),
        "offset_x": offset_x,
        "offset_y": offset_y,
        "distance_pixels": round(distance, 2),
        "match_threshold": round(effective_threshold, 4),
        "movement_tolerance_pixels": movement_tolerance_pixels,
        "selection_type": "polygon" if polygon_mask is not None else "rectangle",
        "mask_coverage": round(float(np.count_nonzero(polygon_mask)) / polygon_mask.size, 4)
        if polygon_mask is not None
        else 1.0,
        "roi_pixels": {"x": x, "y": y, "width": roi_width, "height": roi_height},
    }


def compare_bollard_zones(
    baseline: np.ndarray,
    current: np.ndarray,
    zones: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    """Compare light-tolerant bollard templates at fixed camera coordinates."""
    if not zones:
        raise ValueError("Kameraet mangler faste pullertsoner")
    comparison_frame, alignment = normalize_fixed_camera_frame(baseline, current)
    zone_results: list[dict[str, Any]] = []
    for index, zone in enumerate(zones, start=1):
        roi = normalized_roi(zone)
        result = compare_bollard_region(
            baseline,
            comparison_frame,
            roi,
            match_threshold=float(zone.get("match_threshold") or BOLLARD_ZONE_MATCH_THRESHOLD),
            movement_tolerance_pixels=int(
                zone.get("movement_tolerance_pixels") or BOLLARD_ZONE_MOVEMENT_TOLERANCE_PIXELS
            ),
        )
        zone_results.append(
            {
                "zone_key": str(zone.get("key") or f"zone-{index}"),
                "x": roi["x"],
                "y": roi["y"],
                "width": roi["width"],
                "height": roi["height"],
                **result,
            }
        )

    abnormal = [item for item in zone_results if item["state"] != "normal"]
    missing = [item for item in zone_results if item["state"] == "missing"]
    if len(zone_results) > 1 and len(missing) >= max(2, math.ceil(len(zone_results) * 0.6)):
        state = "obscured"
    elif abnormal:
        state = "changed"
    else:
        state = "normal"

    representative = min(
        abnormal or zone_results,
        key=lambda item: float(item.get("best_score") or -1),
    )
    abnormal_fraction = len(abnormal) / len(zone_results)
    largest_fraction = max(
        (float(item["width"]) * float(item["height"]) for item in abnormal),
        default=0.0,
    )
    overlay = cv2.addWeighted(baseline, 0.5, comparison_frame, 0.5, 0)
    result = {
        "state": state,
        "change_score": round(abnormal_fraction, 4),
        "changed_fraction": round(abnormal_fraction, 6),
        "raw_changed_fraction": round(abnormal_fraction, 6),
        "largest_change_fraction": round(largest_fraction, 6),
        "mean_difference": round(abnormal_fraction, 5),
        "change_components": zone_results,
        "alignment": alignment,
        "analysis_size": {"width": baseline.shape[1], "height": baseline.shape[0]},
        "analysis_zone_count": len(zone_results),
        "abnormal_zone_count": len(abnormal),
        "comparison_mode": "fixed_bollard_zones",
        "best_score": representative["best_score"],
        "expected_score": representative["expected_score"],
        "offset_x": representative["offset_x"],
        "offset_y": representative["offset_y"],
        "distance_pixels": representative["distance_pixels"],
    }
    return result, comparison_frame, overlay


def encode_jpeg(image: np.ndarray, quality: int = 88) -> bytes:
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, max(55, min(95, quality))])
    if not ok:
        raise ValueError("Klarte ikke å kode sammenligningsbildet")
    return encoded.tobytes()


def compare_full_scene(
    baseline: np.ndarray,
    current: np.ndarray,
    *,
    analysis_width: int = 1280,
    analysis_polygon: Sequence[Mapping[str, float]] | None = None,
    change_fraction_threshold: float = 0.00018,
    obscured_fraction_threshold: float = 0.018,
    major_change_is_actionable: bool = False,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    """Compare the exact source-pixel crops without geometric processing."""
    comparison_frame, alignment = normalize_fixed_camera_frame(baseline, current)
    height, width = baseline.shape[:2]
    # Kept in the signature for API compatibility. Analysis deliberately uses
    # every pixel in the already cropped source image.
    _ = analysis_width
    size = (width, height)
    base_small = baseline
    current_small = comparison_frame

    base_lab = cv2.cvtColor(base_small, cv2.COLOR_BGR2LAB)
    current_lab = cv2.cvtColor(current_small, cv2.COLOR_BGR2LAB)
    base_light = cv2.GaussianBlur(base_lab[:, :, 0], (7, 7), 0)
    current_light = cv2.GaussianBlur(current_lab[:, :, 0], (7, 7), 0)
    light_difference = cv2.absdiff(base_light, current_light)
    color_difference = cv2.absdiff(base_lab[:, :, 1:], current_lab[:, :, 1:]).mean(axis=2)

    base_edges = cv2.Canny(base_light, 45, 135)
    current_edges = cv2.Canny(current_light, 45, 135)
    tolerance_kernel = np.ones((5, 5), np.uint8)
    base_near = cv2.dilate(base_edges, tolerance_kernel, iterations=1)
    current_near = cv2.dilate(current_edges, tolerance_kernel, iterations=1)
    removed_edges = cv2.bitwise_and(base_edges, cv2.bitwise_not(current_near))
    added_edges = cv2.bitwise_and(current_edges, cv2.bitwise_not(base_near))
    structural = cv2.bitwise_or(removed_edges, added_edges)
    appearance = np.where((light_difference > 24) & (color_difference > 5), 255, 0).astype(np.uint8)
    raw_mask = cv2.bitwise_or(cv2.dilate(structural, np.ones((3, 3), np.uint8), iterations=1), appearance)

    # UniFi burns a changing timestamp into the upper-left corner. It is not scene content.
    raw_mask[: max(1, round(size[1] * 0.065)), : max(1, round(size[0] * 0.22))] = 0
    raw_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    raw_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))

    analysis_mask: np.ndarray | None = None
    if analysis_polygon:
        points = np.array(
            [
                [
                    max(0, min(size[0] - 1, round(float(point["x"]) * size[0]))),
                    max(0, min(size[1] - 1, round(float(point["y"]) * size[1]))),
                ]
                for point in analysis_polygon
            ],
            dtype=np.int32,
        )
        if len(points) < 3:
            raise ValueError("Analysepolygonet må ha minst tre punkter")
        analysis_mask = np.zeros_like(raw_mask)
        cv2.fillPoly(analysis_mask, [points], 255)
        analysis_mask = cv2.erode(analysis_mask, np.ones((5, 5), np.uint8), iterations=1)
        raw_mask = cv2.bitwise_and(raw_mask, analysis_mask)

    total_pixels = int(np.count_nonzero(analysis_mask)) if analysis_mask is not None else raw_mask.size
    total_pixels = max(1, total_pixels)
    component_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(raw_mask, 8)
    filtered = np.zeros_like(raw_mask)
    components: list[dict[str, Any]] = []
    large_change_fraction = 0.0
    minimum_area = max(36, round(total_pixels * 0.00005))
    for label in range(1, component_count):
        left, top, component_width, component_height, area = (int(value) for value in stats[label])
        fraction = area / total_pixels
        if area < minimum_area:
            continue
        if fraction >= 0.018:
            large_change_fraction = max(large_change_fraction, fraction)
        else:
            filtered[labels == label] = 255
        components.append(
            {
                "x": round(left / size[0], 5),
                "y": round(top / size[1], 5),
                "width": round(component_width / size[0], 5),
                "height": round(component_height / size[1], 5),
                "area_fraction": round(fraction, 6),
            }
        )
    components.sort(key=lambda item: item["area_fraction"], reverse=True)
    components = components[:20]

    raw_fraction = float(np.count_nonzero(raw_mask)) / total_pixels
    changed_fraction = float(np.count_nonzero(filtered)) / total_pixels
    largest_fraction = max((item["area_fraction"] for item in components), default=0.0)
    mean_difference = (
        float(light_difference[analysis_mask > 0].mean()) / 255.0
        if analysis_mask is not None
        else float(light_difference.mean()) / 255.0
    )
    localized = [item for item in components if 0.00005 <= item["area_fraction"] < 0.018]
    if (
        raw_fraction >= 0.12
        or changed_fraction >= obscured_fraction_threshold
        or large_change_fraction >= 0.035
        or mean_difference >= 0.16
    ):
        state = "changed" if major_change_is_actionable else "obscured"
    elif changed_fraction >= change_fraction_threshold and localized:
        state = "changed"
    else:
        state = "normal"
    change_score = min(
        1.0,
        changed_fraction / max(change_fraction_threshold, obscured_fraction_threshold)
        + min(0.45, len(localized) * 0.035)
        + min(0.25, mean_difference * 1.5),
    )

    mask_full = filtered
    overlay = cv2.addWeighted(baseline, 0.5, comparison_frame, 0.5, 0)
    overlay[mask_full > 0] = np.array([0, 0, 255], dtype=np.uint8)
    result = {
        "state": state,
        "change_score": round(change_score, 4),
        "changed_fraction": round(changed_fraction, 6),
        "raw_changed_fraction": round(raw_fraction, 6),
        "largest_change_fraction": round(largest_fraction, 6),
        "mean_difference": round(mean_difference, 5),
        "change_components": components,
        "alignment": alignment,
        "analysis_size": {"width": size[0], "height": size[1]},
        "comparison_mode": "fixed_source_pixel_crop",
        "analysis_resized": False,
        "analysis_polygon": list(analysis_polygon or []),
        "change_fraction_threshold": change_fraction_threshold,
        "obscured_fraction_threshold": obscured_fraction_threshold,
        "major_change_is_actionable": major_change_is_actionable,
    }
    return result, comparison_frame, overlay


def safe_image_path(root: Path, relative_path: str) -> Path:
    resolved_root = root.resolve()
    path = (resolved_root / relative_path).resolve()
    if not path.is_relative_to(resolved_root):
        raise ValueError("Ugyldig bildesti")
    return path


def write_image_atomic(root: Path, relative_path: str, content: bytes) -> Path:
    destination = safe_image_path(root, relative_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.part")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def image_relative_path(
    console_key: str,
    camera_id: str,
    category: str,
    identifier: str,
    captured_at: datetime,
) -> str:
    camera_hash = hashlib.sha256(f"{console_key}:{camera_id}".encode()).hexdigest()[:12]
    item_hash = hashlib.sha256(f"{console_key}:{category}:{identifier}".encode()).hexdigest()
    return Path(
        captured_at.strftime("%Y"),
        captured_at.strftime("%m"),
        captured_at.strftime("%d"),
        camera_hash,
        "bollards",
        category,
        f"{item_hash}.jpg",
    ).as_posix()


@dataclass(frozen=True)
class BollardRuntimeSettings:
    monitoring_enabled: bool
    analysis_interval_seconds: int
    confirmation_seconds: int
    notification_enabled: bool


SnapshotFetcher = Callable[[str, bool], Awaitable[tuple[bytes, datetime]]]


class BollardService:
    def __init__(
        self,
        pool: asyncpg.Pool,
        console_key: str,
        snapshot_root: Path,
        snapshot_fetcher: SnapshotFetcher,
        notification_session: aiohttp.ClientSession,
        *,
        ntfy_base_url: str = "https://ntfy.sh",
        ntfy_topic: str = "",
        alarm_app_url: str = "https://alarm.lilletorget.net",
        visual_ai_url: str = "",
        visual_ai_token: str = "",
        visual_ai_timeout_seconds: int = 30,
    ) -> None:
        self.pool = pool
        self.console_key = console_key
        self.snapshot_root = snapshot_root
        self.snapshot_fetcher = snapshot_fetcher
        self.notification_session = notification_session
        self.ntfy_base_url = ntfy_base_url.rstrip("/")
        self.ntfy_topic = ntfy_topic.strip()
        self.alarm_app_url = alarm_app_url.rstrip("/")
        self.visual_ai_url = visual_ai_url.rstrip("/")
        self.visual_ai_token = visual_ai_token.strip()
        self.visual_ai_timeout_seconds = max(3, min(120, visual_ai_timeout_seconds))
        self.task: Optional[asyncio.Task[None]] = None
        self.lock = asyncio.Lock()
        self.last_run_at: Optional[datetime] = None
        self.last_success_at: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.checks_since_start = 0
        self.incidents_since_start = 0

    async def initialize(self) -> None:
        for statement in SCHEMA_STATEMENTS:
            await self.pool.execute(statement)
        await self.pool.execute(
            """
            INSERT INTO unifi_protect_bollard_settings (console_key)
            VALUES ($1) ON CONFLICT (console_key) DO NOTHING
            """,
            self.console_key,
        )

    def start(self) -> None:
        if self.task is None:
            self.task = asyncio.create_task(self.run_forever(), name="protect-bollard-monitor")

    async def close(self) -> None:
        if self.task is not None:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None

    async def settings(self) -> BollardRuntimeSettings:
        row = await self.pool.fetchrow(
            "SELECT * FROM unifi_protect_bollard_settings WHERE console_key = $1",
            self.console_key,
        )
        return BollardRuntimeSettings(
            monitoring_enabled=bool(row["monitoring_enabled"]),
            analysis_interval_seconds=int(row["analysis_interval_seconds"]),
            confirmation_seconds=int(row["confirmation_seconds"]),
            notification_enabled=bool(row["notification_enabled"]),
        )

    async def target_cameras(self) -> list[dict[str, Any]]:
        rows = await self.pool.fetch(
            """
            SELECT camera_id, name, state, smart_detect_types, last_event_at
            FROM unifi_protect_cameras
            WHERE console_key = $1 AND name = ANY($2::varchar[])
            ORDER BY array_position($2::varchar[], name)
            """,
            self.console_key,
            list(TARGET_CAMERA_NAMES),
        )
        return [dict(row) for row in rows]

    async def ensure_camera_monitors(self, cameras: Sequence[Mapping[str, Any]] | None = None) -> None:
        rows = list(cameras) if cameras is not None else await self.target_cameras()
        for camera in rows:
            await self.pool.execute(
                """
                INSERT INTO unifi_protect_bollard_camera_monitors (
                    console_key, camera_id, camera_name
                ) VALUES ($1, $2, $3)
                ON CONFLICT (console_key, camera_id) DO UPDATE SET
                    camera_name = EXCLUDED.camera_name, updated_at = CURRENT_TIMESTAMP
                """,
                self.console_key,
                str(camera["camera_id"]),
                str(camera["name"]),
            )

    async def _materialize_fixed_asset_baseline(
        self,
        *,
        asset_key: str,
        camera_id: str,
        source_path: str,
        captured_at: datetime,
        crop: Mapping[str, Any],
    ) -> str:
        """Store the fixed source-pixel crop as the asset's actual baseline."""
        source_content = await asyncio.to_thread(
            safe_image_path(self.snapshot_root, source_path).read_bytes
        )
        cropped_content = await asyncio.to_thread(
            lambda: encode_jpeg(fixed_pixel_crop(decode_jpeg(source_content), crop), quality=95)
        )
        relative = image_relative_path(
            self.console_key,
            camera_id,
            "asset-baseline",
            asset_key,
            captured_at,
        )
        await asyncio.to_thread(
            write_image_atomic,
            self.snapshot_root,
            relative,
            cropped_content,
        )
        return relative

    async def ensure_fixed_asset_monitors(
        self,
        cameras: Sequence[Mapping[str, Any]] | None = None,
    ) -> None:
        camera_rows = list(cameras) if cameras is not None else await self.target_cameras()
        cameras_by_name = {str(camera["name"]): camera for camera in camera_rows}
        for asset_key, definition in FIXED_STRUCTURE_MONITORS.items():
            camera_name = str(definition["camera_name"])
            camera = cameras_by_name.get(camera_name)
            if camera is None:
                continue
            camera_id = str(camera["camera_id"])
            baseline = await self.pool.fetchrow(
                """
                SELECT baseline_path, baseline_captured_at
                FROM unifi_protect_bollard_camera_monitors
                WHERE console_key = $1 AND camera_id = $2
                """,
                self.console_key,
                camera_id,
            )
            existing = await self.pool.fetchrow(
                """
                SELECT baseline_path, baseline_captured_at
                FROM unifi_protect_fixed_asset_monitors
                WHERE console_key = $1 AND asset_key = $2
                """,
                self.console_key,
                asset_key,
            )
            asset_baseline_path = (
                str(existing["baseline_path"])
                if existing and existing["baseline_path"]
                else None
            )
            asset_baseline_at = existing["baseline_captured_at"] if existing else None
            has_materialized_crop = bool(
                asset_baseline_path
                and "/asset-baseline/" in f"/{asset_baseline_path}"
                and safe_image_path(self.snapshot_root, asset_baseline_path).is_file()
            )
            if not has_materialized_crop and baseline and baseline["baseline_path"]:
                asset_baseline_at = baseline["baseline_captured_at"]
                asset_baseline_path = await self._materialize_fixed_asset_baseline(
                    asset_key=asset_key,
                    camera_id=camera_id,
                    source_path=str(baseline["baseline_path"]),
                    captured_at=asset_baseline_at,
                    crop=definition["crop"],
                )
            await self.pool.execute(
                """
                INSERT INTO unifi_protect_fixed_asset_monitors (
                    console_key, asset_key, display_name, asset_type,
                    camera_id, camera_name, crop, baseline_path, baseline_captured_at,
                    status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9,
                          CASE WHEN $8::text IS NULL THEN 'uncalibrated' ELSE 'normal' END)
                ON CONFLICT (console_key, asset_key) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    asset_type = EXCLUDED.asset_type,
                    camera_id = EXCLUDED.camera_id,
                    camera_name = EXCLUDED.camera_name,
                    crop = EXCLUDED.crop,
                    baseline_path = EXCLUDED.baseline_path,
                    baseline_captured_at = EXCLUDED.baseline_captured_at,
                    status = CASE
                        WHEN unifi_protect_fixed_asset_monitors.baseline_path IS NULL
                             AND EXCLUDED.baseline_path IS NOT NULL THEN 'normal'
                        ELSE unifi_protect_fixed_asset_monitors.status
                    END,
                    updated_at = CURRENT_TIMESTAMP
                """,
                self.console_key,
                asset_key,
                str(definition["display_name"]),
                str(definition["asset_type"]),
                camera_id,
                camera_name,
                json.dumps(definition["crop"]),
                asset_baseline_path,
                asset_baseline_at,
            )

    @staticmethod
    def public_monitor(row: Mapping[str, Any]) -> dict[str, Any]:
        item = dict(row)
        camera_id = str(item["camera_id"])
        item["monitor_id"] = f"camera:{camera_id}"
        item["item_type"] = "bollards"
        item["display_name"] = str(item.get("camera_name") or camera_id)
        components = item.get("change_components") or []
        alignment = item.get("alignment") or {}
        if isinstance(components, str):
            components = json.loads(components)
        if isinstance(alignment, str):
            alignment = json.loads(alignment)
        item["change_components"] = components
        item["alignment"] = alignment
        item["baseline_url"] = f"/api/bollards/cameras/{camera_id}/baseline" if item.get("baseline_path") else None
        item["latest_url"] = f"/api/bollards/cameras/{camera_id}/latest" if item.get("latest_path") else None
        item["overlay_url"] = f"/api/bollards/cameras/{camera_id}/overlay" if item.get("overlay_path") else None
        item["baseline_crop_url"] = f"/api/bollards/cameras/{camera_id}/baseline/crop" if item.get("baseline_path") else None
        item["latest_crop_url"] = f"/api/bollards/cameras/{camera_id}/latest/crop" if item.get("latest_path") else None
        item["overlay_crop_url"] = f"/api/bollards/cameras/{camera_id}/overlay/crop" if item.get("overlay_path") else None
        item["ai_heatmap_url"] = (
            f"/api/bollards/cameras/{camera_id}/ai" if item.get("ai_heatmap_path") else None
        )
        crop = BOLLARD_CAMERA_DISPLAY_CROPS.get(str(item.get("camera_name") or ""))
        item["display_crop"] = dict(crop) if crop else None
        item["image_geometry"] = "fixed_source_pixel_crop"
        for key in ("baseline_path", "latest_path", "overlay_path", "ai_heatmap_path"):
            item.pop(key, None)
        return item

    @staticmethod
    def public_fixed_asset(row: Mapping[str, Any]) -> dict[str, Any]:
        item = dict(row)
        asset_key = str(item["asset_key"])
        crop = item.get("crop") or {}
        components = item.get("change_components") or []
        if isinstance(crop, str):
            crop = json.loads(crop)
        if isinstance(components, str):
            components = json.loads(components)
        item["monitor_id"] = f"asset:{asset_key}"
        item["item_type"] = str(item.get("asset_type") or "structure")
        item["display_crop"] = dict(crop)
        item["change_components"] = components
        item["image_geometry"] = "fixed_source_pixel_crop"
        item["baseline_crop_url"] = (
            f"/api/bollards/assets/{asset_key}/baseline" if item.get("baseline_path") else None
        )
        item["latest_crop_url"] = (
            f"/api/bollards/assets/{asset_key}/latest" if item.get("latest_path") else None
        )
        item["overlay_crop_url"] = (
            f"/api/bollards/assets/{asset_key}/overlay" if item.get("overlay_path") else None
        )
        item["baseline_url"] = item["baseline_crop_url"]
        item["latest_url"] = item["latest_crop_url"]
        item["overlay_url"] = item["overlay_crop_url"]
        item["ai_heatmap_url"] = (
            f"/api/bollards/assets/{asset_key}/ai" if item.get("ai_heatmap_path") else None
        )
        for key in ("baseline_path", "latest_path", "overlay_path", "ai_heatmap_path", "crop"):
            item.pop(key, None)
        return item

    @staticmethod
    def public_region(row: Mapping[str, Any]) -> dict[str, Any]:
        item = dict(row)
        item["roi"] = normalized_roi(item["roi"])
        item.pop("baseline_path", None)
        item["baseline_url"] = (
            f"/api/bollards/regions/{row['region_id']}/baseline" if row.get("baseline_path") else None
        )
        return item

    @staticmethod
    def public_incident(row: Mapping[str, Any]) -> dict[str, Any]:
        item = dict(row)
        evidence = item.get("evidence") or {}
        if isinstance(evidence, str):
            evidence = json.loads(evidence)
        item["evidence"] = {
            camera_id: {
                key: value
                for key, value in camera_evidence.items()
                if key not in {"before_path", "after_path"}
            }
            | {
                "before_url": f"/api/bollards/incidents/{row['incident_id']}/images/{camera_id}/before"
                if camera_evidence.get("before_path")
                else None,
                "after_url": f"/api/bollards/incidents/{row['incident_id']}/images/{camera_id}/after"
                if camera_evidence.get("after_path")
                else None,
            }
            for camera_id, camera_evidence in evidence.items()
            if isinstance(camera_evidence, Mapping)
        }
        return item

    async def status_payload(self, *, incident_limit: int = 50) -> dict[str, Any]:
        settings = await self.settings()
        cameras = await self.target_cameras()
        await self.ensure_camera_monitors(cameras)
        await self.ensure_fixed_asset_monitors(cameras)
        monitors, fixed_assets, regions, incidents = await asyncio.gather(
            self.pool.fetch(
                """
                SELECT * FROM unifi_protect_bollard_camera_monitors
                WHERE console_key = $1
                ORDER BY array_position($2::varchar[], camera_name)
                """,
                self.console_key,
                list(TARGET_CAMERA_NAMES),
            ),
            self.pool.fetch(
                """
                SELECT * FROM unifi_protect_fixed_asset_monitors
                WHERE console_key = $1 ORDER BY display_name
                """,
                self.console_key,
            ),
            self.pool.fetch(
                """
                SELECT * FROM unifi_protect_bollard_regions
                WHERE console_key = $1 ORDER BY display_name, camera_name
                """,
                self.console_key,
            ),
            self.pool.fetch(
                """
                SELECT * FROM unifi_protect_bollard_incidents
                WHERE console_key = $1 ORDER BY detected_at DESC LIMIT $2
                """,
                self.console_key,
                incident_limit,
            ),
        )
        region_items = [self.public_region(dict(row)) for row in regions]
        monitor_items = [self.public_monitor(dict(row)) for row in monitors]
        fixed_asset_items = [self.public_fixed_asset(dict(row)) for row in fixed_assets]
        active_incidents = sum(1 for row in incidents if row["status"] in {"active", "acknowledged"})
        calibrated = sum(1 for row in monitors if row["baseline_path"])
        calibrated_assets = sum(1 for row in fixed_assets if row["baseline_path"])
        ai_rows = [*monitors, *fixed_assets]
        ai_ready = sum(1 for row in ai_rows if row.get("ai_status") in {"normal", "anomaly"})
        ai_anomalies = sum(1 for row in ai_rows if bool(row.get("ai_is_anomaly")))
        return {
            "settings": settings.__dict__,
            "comparison_mode": "fixed_object_zones",
            "target_camera_names": list(TARGET_CAMERA_NAMES),
            "cameras": cameras,
            "camera_monitors": monitor_items,
            "asset_monitors": fixed_asset_items,
            "regions": region_items,
            "incidents": [self.public_incident(dict(row)) for row in incidents],
            "summary": {
                "target_cameras": len(TARGET_CAMERA_NAMES),
                "connected_cameras": sum(1 for row in cameras if row.get("state") == "CONNECTED"),
                "configured_regions": 0,
                "calibrated_regions": calibrated,
                "baseline_cameras": calibrated,
                "monitored_assets": len(fixed_assets),
                "calibrated_assets": calibrated_assets,
                "inspection_objects": len(monitors) + len(fixed_assets),
                "active_incidents": active_incidents,
                "monitoring_ready": bool(
                    settings.monitoring_enabled
                    and calibrated == len(TARGET_CAMERA_NAMES)
                    and calibrated_assets == len(FIXED_STRUCTURE_MONITORS)
                    and len(cameras) == len(TARGET_CAMERA_NAMES)
                ),
                "ai_profiles_ready": ai_ready,
                "ai_profiles_total": len(ai_rows),
                "ai_anomalies": ai_anomalies,
            },
            "visual_ai": {
                "configured": bool(self.visual_ai_url),
                "mode": "advisory",
                "profiles_ready": ai_ready,
                "profiles_total": len(ai_rows),
                "anomalies": ai_anomalies,
                "failure_isolation": True,
            },
            "runtime": {
                "running": self.task is not None and not self.task.done(),
                "last_run_at": self.last_run_at,
                "last_success_at": self.last_success_at,
                "last_error": self.last_error,
                "checks_since_start": self.checks_since_start,
                "incidents_since_start": self.incidents_since_start,
                "notification_configured": bool(self.ntfy_topic),
            },
        }

    async def capture_camera_baseline(self, camera_id: str) -> dict[str, Any]:
        content, captured_at = await self.snapshot_fetcher(camera_id, True)
        return await self.set_camera_baseline(camera_id, content, captured_at)

    async def set_camera_baseline(
        self,
        camera_id: str,
        content: bytes,
        captured_at: datetime,
    ) -> dict[str, Any]:
        cameras = await self.target_cameras()
        camera = next((row for row in cameras if str(row["camera_id"]) == camera_id), None)
        if camera is None:
            raise LookupError("Kameraet er ikke et av de tre pullertkameraene")
        decode_jpeg(content)
        relative = image_relative_path(
            self.console_key,
            camera_id,
            "scene-baseline",
            camera_id,
            captured_at,
        )
        await asyncio.to_thread(write_image_atomic, self.snapshot_root, relative, content)
        previous = await self.pool.fetchrow(
            """
            SELECT baseline_path, latest_path, overlay_path
            FROM unifi_protect_bollard_camera_monitors
            WHERE console_key = $1 AND camera_id = $2
            """,
            self.console_key,
            camera_id,
        )
        row = await self.pool.fetchrow(
            """
            INSERT INTO unifi_protect_bollard_camera_monitors (
                console_key, camera_id, camera_name, baseline_path,
                baseline_captured_at, status, change_components, alignment
            ) VALUES ($1, $2, $3, $4, $5, 'normal', '[]'::jsonb, '{}'::jsonb)
            ON CONFLICT (console_key, camera_id) DO UPDATE SET
                camera_name = EXCLUDED.camera_name,
                baseline_path = EXCLUDED.baseline_path,
                baseline_captured_at = EXCLUDED.baseline_captured_at,
                latest_path = NULL, latest_captured_at = NULL, overlay_path = NULL,
                status = 'normal', change_score = NULL, changed_fraction = NULL,
                largest_change_fraction = NULL, mean_difference = NULL,
                change_components = '[]'::jsonb, alignment = '{}'::jsonb,
                consecutive_abnormal = 0, abnormal_since = NULL,
                last_checked_at = NULL, last_error = NULL, updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            self.console_key,
            camera_id,
            str(camera["name"]),
            relative,
            captured_at,
        )
        await self.ensure_fixed_asset_monitors(cameras)
        for asset_key, definition in FIXED_STRUCTURE_MONITORS.items():
            if str(definition["camera_name"]) != str(camera["name"]):
                continue
            old_asset_path = await self.pool.fetchval(
                """
                SELECT baseline_path FROM unifi_protect_fixed_asset_monitors
                WHERE console_key = $1 AND asset_key = $2
                """,
                self.console_key,
                asset_key,
            )
            asset_baseline_path = await self._materialize_fixed_asset_baseline(
                asset_key=asset_key,
                camera_id=camera_id,
                source_path=relative,
                captured_at=captured_at,
                crop=definition["crop"],
            )
            await self.pool.execute(
                """
                UPDATE unifi_protect_fixed_asset_monitors
                SET baseline_path = $3, baseline_captured_at = $4,
                    latest_path = NULL, latest_captured_at = NULL, overlay_path = NULL,
                    status = 'normal', change_score = NULL, changed_fraction = NULL,
                    largest_change_fraction = NULL, mean_difference = NULL,
                    change_components = '[]'::jsonb, consecutive_abnormal = 0,
                    abnormal_since = NULL, last_checked_at = NULL, last_error = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE console_key = $1 AND asset_key = $2
                """,
                self.console_key,
                asset_key,
                asset_baseline_path,
                captured_at,
            )
            if old_asset_path and str(old_asset_path) != asset_baseline_path:
                try:
                    await asyncio.to_thread(
                        safe_image_path(self.snapshot_root, str(old_asset_path)).unlink,
                        missing_ok=True,
                    )
                except OSError:
                    logger.warning("Could not remove replaced asset baseline %s", old_asset_path)
        if previous:
            for key in ("baseline_path", "latest_path", "overlay_path"):
                old_path = previous[key]
                if old_path and str(old_path) != relative:
                    try:
                        await asyncio.to_thread(
                            safe_image_path(self.snapshot_root, str(old_path)).unlink,
                            missing_ok=True,
                        )
                    except OSError:
                        logger.warning("Could not remove replaced full-frame image %s", old_path)
        return self.public_monitor(dict(row))

    async def capture_all_baselines(self) -> list[dict[str, Any]]:
        cameras = await self.target_cameras()
        if len(cameras) != len(TARGET_CAMERA_NAMES):
            raise ValueError("Alle tre pullertkameraene må være tilkoblet")
        results: list[dict[str, Any]] = []
        for camera in cameras:
            results.append(await self.capture_camera_baseline(str(camera["camera_id"])))
        return results

    async def camera_comparison_image_path(self, camera_id: str, kind: str) -> Path:
        columns = {
            "baseline": "baseline_path",
            "latest": "latest_path",
            "overlay": "overlay_path",
            "ai": "ai_heatmap_path",
        }
        column = columns.get(kind)
        if not column:
            raise ValueError("Bildetype må være baseline, latest eller overlay")
        value = await self.pool.fetchval(
            f"""
            SELECT {column} FROM unifi_protect_bollard_camera_monitors
            WHERE console_key = $1 AND camera_id = $2
            """,
            self.console_key,
            camera_id,
        )
        if not value:
            raise LookupError("Sammenligningsbildet finnes ikke")
        path = safe_image_path(self.snapshot_root, str(value))
        if not path.is_file():
            raise LookupError("Bildefilen finnes ikke")
        return path

    async def camera_comparison_image(self, camera_id: str, kind: str) -> tuple[bytes, dict[str, int]]:
        path = await self.camera_comparison_image_path(camera_id, kind)
        camera_name = await self.pool.fetchval(
            """
            SELECT camera_name FROM unifi_protect_bollard_camera_monitors
            WHERE console_key = $1 AND camera_id = $2
            """,
            self.console_key,
            camera_id,
        )
        crop = BOLLARD_CAMERA_DISPLAY_CROPS.get(str(camera_name or ""))
        if crop is None:
            raise LookupError("Kameraet mangler et fast pikselutsnitt")
        content = await asyncio.to_thread(path.read_bytes)

        def crop_content() -> bytes:
            return encode_jpeg(fixed_pixel_crop(decode_jpeg(content), crop), quality=95)

        return await asyncio.to_thread(crop_content), dict(crop)

    async def fixed_asset_comparison_image(
        self,
        asset_key: str,
        kind: str,
    ) -> tuple[bytes, dict[str, int]]:
        columns = {
            "baseline": "baseline_path",
            "latest": "latest_path",
            "overlay": "overlay_path",
            "ai": "ai_heatmap_path",
        }
        column = columns.get(kind)
        if column is None:
            raise ValueError("Bildetype må være baseline, latest eller overlay")
        row = await self.pool.fetchrow(
            f"""
            SELECT crop, {column} AS image_path
            FROM unifi_protect_fixed_asset_monitors
            WHERE console_key = $1 AND asset_key = $2
            """,
            self.console_key,
            asset_key,
        )
        if row is None:
            raise LookupError("Det overvåkede objektet finnes ikke")
        if not row["image_path"]:
            raise LookupError("Sammenligningsbildet finnes ikke")
        crop = row["crop"]
        if isinstance(crop, str):
            crop = json.loads(crop)
        crop = {key: int(crop[key]) for key in ("x", "y", "width", "height")}
        content = await asyncio.to_thread(
            safe_image_path(self.snapshot_root, str(row["image_path"])).read_bytes
        )
        image = await asyncio.to_thread(decode_jpeg, content)
        if kind != "ai" and image.shape[:2] != (crop["height"], crop["width"]):
            raise ValueError("Det lagrede kontrollbildet har ikke det faste pikselutsnittet")
        if kind == "ai":
            crop = {"x": 0, "y": 0, "width": image.shape[1], "height": image.shape[0]}
        return content, crop

    async def create_region(
        self,
        *,
        display_name: str,
        bollard_key: str,
        camera_id: str,
        roi: Mapping[str, Any],
        match_threshold: float = 0.42,
        movement_tolerance_pixels: int = 12,
    ) -> dict[str, Any]:
        name = display_name.strip()[:120]
        if not name:
            raise ValueError("Pullerten må ha et navn")
        key = normalized_bollard_key(bollard_key or name)
        normalized = normalized_roi(roi)
        camera = await self.pool.fetchrow(
            """
            SELECT camera_id, name FROM unifi_protect_cameras
            WHERE console_key = $1 AND camera_id = $2 AND name = ANY($3::varchar[])
            """,
            self.console_key,
            camera_id,
            list(TARGET_CAMERA_NAMES),
        )
        if camera is None:
            raise ValueError("Kameraet er ikke blant de tre godkjente pullertkameraene")
        content, captured_at = await self.snapshot_fetcher(camera_id, True)
        baseline_image = decode_jpeg(content)
        x, y, width, height = roi_pixels(normalized, baseline_image.shape[1], baseline_image.shape[0])
        if width < 20 or height < 20:
            raise ValueError("Pullertområdet må være minst 20 piksler i referansebildet")
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                row = await connection.fetchrow(
                    """
                    INSERT INTO unifi_protect_bollard_regions (
                        console_key, bollard_key, display_name, camera_id, camera_name,
                        roi, enabled, match_threshold, movement_tolerance_pixels,
                        status, baseline_captured_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, TRUE, $7, $8,
                              'normal', $9, CURRENT_TIMESTAMP)
                    ON CONFLICT (console_key, bollard_key, camera_id) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        camera_name = EXCLUDED.camera_name,
                        roi = EXCLUDED.roi,
                        enabled = TRUE,
                        match_threshold = EXCLUDED.match_threshold,
                        movement_tolerance_pixels = EXCLUDED.movement_tolerance_pixels,
                        status = 'normal',
                        baseline_captured_at = EXCLUDED.baseline_captured_at,
                        consecutive_abnormal = 0,
                        abnormal_since = NULL,
                        last_error = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING *
                    """,
                    self.console_key,
                    key,
                    name,
                    camera_id,
                    camera["name"],
                    json.dumps(normalized),
                    max(0.1, min(0.95, float(match_threshold))),
                    max(2, min(200, int(movement_tolerance_pixels))),
                    captured_at,
                )
                relative = image_relative_path(
                    self.console_key,
                    camera_id,
                    "baselines",
                    str(row["region_id"]),
                    captured_at,
                )
                await asyncio.to_thread(write_image_atomic, self.snapshot_root, relative, content)
                row = await connection.fetchrow(
                    """
                    UPDATE unifi_protect_bollard_regions
                    SET baseline_path = $3, updated_at = CURRENT_TIMESTAMP
                    WHERE console_key = $1 AND region_id = $2 RETURNING *
                    """,
                    self.console_key,
                    row["region_id"],
                    relative,
                )
        return self.public_region(dict(row))

    async def refresh_baseline(self, region_id: int) -> dict[str, Any]:
        row = await self.pool.fetchrow(
            "SELECT * FROM unifi_protect_bollard_regions WHERE console_key = $1 AND region_id = $2",
            self.console_key,
            region_id,
        )
        if row is None:
            raise LookupError("Pullertområdet finnes ikke")
        content, captured_at = await self.snapshot_fetcher(str(row["camera_id"]), True)
        image = decode_jpeg(content)
        roi_pixels(row["roi"], image.shape[1], image.shape[0])
        relative = image_relative_path(
            self.console_key,
            str(row["camera_id"]),
            "baselines",
            str(region_id),
            captured_at,
        )
        await asyncio.to_thread(write_image_atomic, self.snapshot_root, relative, content)
        updated = await self.pool.fetchrow(
            """
            UPDATE unifi_protect_bollard_regions
            SET baseline_path = $3, baseline_captured_at = $4, status = 'normal',
                consecutive_abnormal = 0, abnormal_since = NULL, last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE console_key = $1 AND region_id = $2 RETURNING *
            """,
            self.console_key,
            region_id,
            relative,
            captured_at,
        )
        old_path = row["baseline_path"]
        if old_path and old_path != relative:
            try:
                await asyncio.to_thread(
                    safe_image_path(self.snapshot_root, str(old_path)).unlink,
                    missing_ok=True,
                )
            except OSError:
                logger.warning("Could not remove replaced bollard baseline %s", old_path)
        return self.public_region(dict(updated))

    async def delete_region(self, region_id: int) -> None:
        row = await self.pool.fetchrow(
            """
            DELETE FROM unifi_protect_bollard_regions
            WHERE console_key = $1 AND region_id = $2
            RETURNING baseline_path
            """,
            self.console_key,
            region_id,
        )
        if row is None:
            raise LookupError("Pullertområdet finnes ikke")
        if row["baseline_path"]:
            try:
                await asyncio.to_thread(
                    safe_image_path(self.snapshot_root, str(row["baseline_path"])).unlink,
                    missing_ok=True,
                )
            except OSError:
                logger.warning("Could not remove deleted bollard baseline %s", row["baseline_path"])

    async def update_settings(
        self,
        *,
        monitoring_enabled: bool,
        analysis_interval_seconds: int,
        confirmation_seconds: int,
        notification_enabled: bool,
    ) -> dict[str, Any]:
        calibrated = await self.pool.fetchval(
            """
            SELECT count(*) FROM unifi_protect_bollard_camera_monitors
            WHERE console_key = $1 AND baseline_path IS NOT NULL
            """,
            self.console_key,
        )
        if monitoring_enabled and int(calibrated or 0) != len(TARGET_CAMERA_NAMES):
            raise ValueError("Alle tre kameraene må ha referansebilde før sammenligningen kan aktiveres")
        await self.pool.execute(
            """
            UPDATE unifi_protect_bollard_settings
            SET monitoring_enabled = $2, analysis_interval_seconds = $3,
                confirmation_seconds = $4, notification_enabled = $5,
                updated_at = CURRENT_TIMESTAMP
            WHERE console_key = $1
            """,
            self.console_key,
            monitoring_enabled,
            max(60, min(300, analysis_interval_seconds)),
            max(10, min(1800, confirmation_seconds)),
            notification_enabled,
        )
        return (await self.status_payload())["settings"]

    async def run_forever(self) -> None:
        while True:
            try:
                settings = await self.settings()
                if settings.monitoring_enabled:
                    await self.run_once()
                self.last_error = None
                interval = settings.analysis_interval_seconds
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.last_error = str(error)[:500]
                logger.warning("Bollard monitor failed: %s", self.last_error)
                interval = 10
            await asyncio.sleep(interval)

    @staticmethod
    def _hybrid_status(classical_state: str, ai_status: str, ai_is_anomaly: bool | None) -> str:
        classical_abnormal = classical_state != "normal"
        if ai_status == "anomaly" and ai_is_anomaly:
            return "corroborated" if classical_abnormal else "ai_review"
        if classical_abnormal:
            return "classical_review"
        if ai_status == "normal":
            return "normal"
        return "classical_only"

    @staticmethod
    def _incident_candidate(result: Mapping[str, Any]) -> bool:
        classical_abnormal = str(result.get("state") or "") in {"moved", "missing", "changed"}
        ai_status = str(result.get("ai_status") or "").lower()
        if ai_status == "normal":
            return False
        if ai_status == "anomaly":
            return classical_abnormal and bool(result.get("ai_is_anomaly"))
        return classical_abnormal

    @staticmethod
    def _effectively_normal(result: Mapping[str, Any]) -> bool:
        ai_status = str(result.get("ai_status") or "").lower()
        if ai_status == "normal":
            return True
        if ai_status == "anomaly":
            return False
        return str(result.get("state") or "") == "normal"

    async def _visual_ai_infer(
        self,
        *,
        profile_id: str,
        content: bytes,
        camera_id: str,
        category: str,
        identifier: str,
        captured_at: datetime,
    ) -> dict[str, Any]:
        checked_at = utc_now()
        base_result: dict[str, Any] = {
            "ai_profile_id": profile_id,
            "ai_status": "disabled" if not self.visual_ai_url else "not_ready",
            "ai_score": None,
            "ai_threshold": None,
            "ai_score_ratio": None,
            "ai_is_anomaly": None,
            "ai_heatmap_path": None,
            "ai_model_version": None,
            "ai_trained_at": None,
            "ai_training_samples": None,
            "ai_inference_ms": None,
            "ai_last_checked_at": checked_at,
            "ai_last_error": None,
        }
        if not self.visual_ai_url:
            return base_result
        headers = {"Content-Type": "image/jpeg", "Accept": "application/json"}
        if self.visual_ai_token:
            headers["Authorization"] = f"Bearer {self.visual_ai_token}"
        try:
            timeout = aiohttp.ClientTimeout(total=self.visual_ai_timeout_seconds)
            async with self.notification_session.post(
                f"{self.visual_ai_url}/api/v1/profiles/{profile_id}/infer",
                data=content,
                headers=headers,
                timeout=timeout,
            ) as response:
                if response.status == 503:
                    detail = (await response.text())[:500]
                    base_result.update({"ai_status": "training", "ai_last_error": detail})
                    return base_result
                if response.status >= 400:
                    detail = (await response.text())[:500]
                    raise RuntimeError(f"Visual AI svarte {response.status}: {detail}")
                payload = await response.json()
            heatmap_content = base64.b64decode(str(payload.pop("heatmap_base64")), validate=True)
            decode_jpeg(heatmap_content)
            heatmap_relative = image_relative_path(
                self.console_key,
                camera_id,
                category,
                identifier,
                captured_at,
            )
            await asyncio.to_thread(
                write_image_atomic,
                self.snapshot_root,
                heatmap_relative,
                heatmap_content,
            )
            trained_at = payload.get("trained_at")
            if isinstance(trained_at, str):
                trained_at = datetime.fromisoformat(trained_at.replace("Z", "+00:00"))
            base_result.update(
                {
                    "ai_status": str(payload.get("status") or "not_ready"),
                    "ai_score": payload.get("score"),
                    "ai_threshold": payload.get("threshold"),
                    "ai_score_ratio": payload.get("score_ratio"),
                    "ai_is_anomaly": bool(payload.get("is_anomaly")),
                    "ai_heatmap_path": heatmap_relative,
                    "ai_model_version": payload.get("model_version"),
                    "ai_trained_at": trained_at,
                    "ai_training_samples": payload.get("training_samples"),
                    "ai_inference_ms": payload.get("inference_ms"),
                    "ai_last_error": None,
                }
            )
        except Exception as error:
            base_result.update({"ai_status": "error", "ai_last_error": str(error)[:500]})
            logger.warning("Visual AI profile %s failed: %s", profile_id, error)
        return base_result

    async def run_once(self) -> dict[str, Any]:
        if self.lock.locked():
            return {"status": "already_running"}
        async with self.lock:
            self.last_run_at = utc_now()
            settings = await self.settings()
            cameras = await self.target_cameras()
            await self.ensure_camera_monitors(cameras)
            await self.ensure_fixed_asset_monitors(cameras)
            monitors = await self.pool.fetch(
                """
                SELECT * FROM unifi_protect_bollard_camera_monitors
                WHERE console_key = $1 AND baseline_path IS NOT NULL
                ORDER BY array_position($2::varchar[], camera_name)
                """,
                self.console_key,
                list(TARGET_CAMERA_NAMES),
            )
            fixed_assets = await self.pool.fetch(
                """
                SELECT * FROM unifi_protect_fixed_asset_monitors
                WHERE console_key = $1 AND baseline_path IS NOT NULL
                ORDER BY display_name
                """,
                self.console_key,
            )
            assets_by_camera: dict[str, list[Mapping[str, Any]]] = {}
            for asset in fixed_assets:
                assets_by_camera.setdefault(str(asset["camera_id"]), []).append(asset)
            if not monitors:
                self.last_success_at = utc_now()
                return {"status": "no_baselines", "checked": 0, "incidents": 0}
            results: list[dict[str, Any]] = []
            current_images: dict[str, tuple[bytes, datetime]] = {}
            for row in monitors:
                camera_id = str(row["camera_id"])
                try:
                    # Reference and current frames must use the same Protect snapshot mode.
                    content, captured_at = await self.snapshot_fetcher(camera_id, True)
                    current_images[camera_id] = (content, captured_at)
                    current = decode_jpeg(content)
                    baseline_path = safe_image_path(self.snapshot_root, str(row["baseline_path"]))
                    baseline = decode_jpeg(await asyncio.to_thread(baseline_path.read_bytes))
                    zones = BOLLARD_CAMERA_ANALYSIS_ZONES.get(str(row["camera_name"]))
                    if not zones:
                        raise ValueError(f"Mangler pullertsoner for {row['camera_name']}")
                    comparison, comparison_frame, overlay = await asyncio.to_thread(
                        compare_bollard_zones,
                        baseline,
                        current,
                        zones,
                    )
                    latest_relative = image_relative_path(
                        self.console_key, camera_id, "scene-latest", camera_id, captured_at
                    )
                    overlay_relative = image_relative_path(
                        self.console_key, camera_id, "scene-overlay", camera_id, captured_at
                    )
                    await asyncio.gather(
                        asyncio.to_thread(
                            write_image_atomic,
                            self.snapshot_root,
                            latest_relative,
                            encode_jpeg(comparison_frame),
                        ),
                        asyncio.to_thread(
                            write_image_atomic,
                            self.snapshot_root,
                            overlay_relative,
                            encode_jpeg(overlay),
                        ),
                    )
                    comparison.update(
                        {
                            "bollard_key": "pullertomrade-solstudio",
                            "display_name": "Pullertområdet ved solstudio",
                            "camera_id": camera_id,
                            "camera_name": row["camera_name"],
                            "captured_at": captured_at,
                            "baseline_path": row["baseline_path"],
                            "latest_path": latest_relative,
                            "overlay_path": overlay_relative,
                            "best_score": comparison["best_score"],
                            "expected_score": comparison["expected_score"],
                            "offset_x": comparison["offset_x"],
                            "offset_y": comparison["offset_y"],
                            "distance_pixels": comparison["distance_pixels"],
                        }
                    )
                    camera_name = str(row["camera_name"])
                    ai_profile_id = VISUAL_AI_CAMERA_PROFILES[camera_name]
                    display_crop = BOLLARD_CAMERA_DISPLAY_CROPS[camera_name]
                    ai_result = await self._visual_ai_infer(
                        profile_id=ai_profile_id,
                        content=encode_jpeg(fixed_pixel_crop(current, display_crop), quality=95),
                        camera_id=camera_id,
                        category="scene-ai",
                        identifier=ai_profile_id,
                        captured_at=captured_at,
                    )
                    comparison.update(ai_result)
                    comparison["hybrid_status"] = self._hybrid_status(
                        str(comparison["state"]),
                        str(ai_result["ai_status"]),
                        ai_result["ai_is_anomaly"],
                    )
                    await self._store_scene_result(row, comparison, settings.confirmation_seconds)
                    results.append(comparison)
                    for asset_row in assets_by_camera.get(camera_id, []):
                        try:
                            crop = asset_row["crop"]
                            if isinstance(crop, str):
                                crop = json.loads(crop)
                            asset_key = str(asset_row["asset_key"])
                            asset_definition = FIXED_STRUCTURE_MONITORS[asset_key]
                            baseline_crop = decode_jpeg(
                                await asyncio.to_thread(
                                    safe_image_path(
                                        self.snapshot_root,
                                        str(asset_row["baseline_path"]),
                                    ).read_bytes
                                )
                            )
                            current_crop_content = encode_jpeg(
                                fixed_pixel_crop(current, crop),
                                quality=95,
                            )
                            current_crop = decode_jpeg(current_crop_content)
                            asset_comparison, _asset_frame, asset_overlay = await asyncio.to_thread(
                                compare_full_scene,
                                baseline_crop,
                                current_crop,
                                analysis_width=1280,
                                analysis_polygon=asset_definition["analysis_polygon"],
                                change_fraction_threshold=float(
                                    asset_definition["change_fraction_threshold"]
                                ),
                                obscured_fraction_threshold=float(
                                    asset_definition["obscured_fraction_threshold"]
                                ),
                                major_change_is_actionable=True,
                            )
                            asset_latest_relative = image_relative_path(
                                self.console_key,
                                camera_id,
                                "asset-latest",
                                asset_key,
                                captured_at,
                            )
                            asset_overlay_relative = image_relative_path(
                                self.console_key,
                                camera_id,
                                "asset-overlay",
                                asset_key,
                                captured_at,
                            )
                            await asyncio.gather(
                                asyncio.to_thread(
                                    write_image_atomic,
                                    self.snapshot_root,
                                    asset_latest_relative,
                                    current_crop_content,
                                ),
                                asyncio.to_thread(
                                    write_image_atomic,
                                    self.snapshot_root,
                                    asset_overlay_relative,
                                    encode_jpeg(asset_overlay, quality=95),
                                ),
                            )
                            asset_comparison.update(
                                {
                                    "bollard_key": asset_key,
                                    "display_name": str(asset_row["display_name"]),
                                    "asset_type": str(asset_row["asset_type"]),
                                    "camera_id": camera_id,
                                    "camera_name": row["camera_name"],
                                    "captured_at": captured_at,
                                    "baseline_path": asset_row["baseline_path"],
                                    "latest_path": asset_latest_relative,
                                    "overlay_path": asset_overlay_relative,
                                }
                            )
                            asset_profile_id = VISUAL_AI_ASSET_PROFILES[asset_key]
                            asset_ai_result = await self._visual_ai_infer(
                                profile_id=asset_profile_id,
                                content=current_crop_content,
                                camera_id=camera_id,
                                category="asset-ai",
                                identifier=asset_profile_id,
                                captured_at=captured_at,
                            )
                            asset_comparison.update(asset_ai_result)
                            asset_comparison["hybrid_status"] = self._hybrid_status(
                                str(asset_comparison["state"]),
                                str(asset_ai_result["ai_status"]),
                                asset_ai_result["ai_is_anomaly"],
                            )
                            await self._store_fixed_asset_result(
                                asset_row,
                                asset_comparison,
                                settings.confirmation_seconds,
                            )
                            results.append(asset_comparison)
                        except Exception as asset_error:
                            safe_asset_error = str(asset_error)[:500]
                            logger.warning(
                                "Fixed asset %s analysis failed: %s",
                                asset_row["asset_key"],
                                safe_asset_error,
                            )
                            await self.pool.execute(
                                """
                                UPDATE unifi_protect_fixed_asset_monitors
                                SET status = 'camera_error', last_error = $3,
                                    last_checked_at = CURRENT_TIMESTAMP,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE console_key = $1 AND asset_key = $2
                                """,
                                self.console_key,
                                asset_row["asset_key"],
                                safe_asset_error,
                            )
                except Exception as error:
                    safe_error = str(error)[:500]
                    logger.warning("Bollard camera %s analysis failed: %s", camera_id, safe_error)
                    await self.pool.execute(
                        """
                        UPDATE unifi_protect_bollard_camera_monitors
                        SET status = 'camera_error', last_error = $3,
                            last_checked_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                        WHERE console_key = $1 AND camera_id = $2
                        """,
                        self.console_key,
                        camera_id,
                        safe_error,
                    )
            new_incidents = await self._update_incidents(
                results, current_images, settings.confirmation_seconds, settings.notification_enabled
            )
            self.checks_since_start += len(results)
            self.incidents_since_start += len(new_incidents)
            self.last_success_at = utc_now()
            self.last_error = None
            return {
                "status": "ok",
                "checked": len(results),
                "new_incidents": len(new_incidents),
                "results": results,
            }

    async def _store_scene_result(
        self,
        row: Mapping[str, Any],
        result: Mapping[str, Any],
        confirmation_seconds: int,
    ) -> None:
        now = utc_now()
        changed = result["state"] == "changed"
        abnormal_since = row["abnormal_since"] if changed else None
        if changed and abnormal_since is None:
            abnormal_since = now
        elapsed = (now - abnormal_since).total_seconds() if abnormal_since else 0
        consecutive = int(row["consecutive_abnormal"] or 0) + 1 if changed else 0
        if result["state"] == "obscured":
            status = "obscured"
        elif changed and elapsed >= confirmation_seconds:
            status = "suspected"
        elif changed:
            status = "changed"
        else:
            status = "normal"
        await self.pool.execute(
            """
            UPDATE unifi_protect_bollard_camera_monitors
            SET latest_path = $3, latest_captured_at = $4, overlay_path = $5,
                status = $6, change_score = $7, changed_fraction = $8,
                largest_change_fraction = $9, mean_difference = $10,
                change_components = $11::jsonb, alignment = $12::jsonb,
                consecutive_abnormal = $13, abnormal_since = $14,
                last_checked_at = $15, last_error = NULL,
                ai_profile_id = $16, ai_status = $17, ai_score = $18,
                ai_threshold = $19, ai_score_ratio = $20, ai_is_anomaly = $21,
                ai_heatmap_path = COALESCE($22, ai_heatmap_path),
                ai_model_version = $23, ai_trained_at = $24,
                ai_training_samples = $25, ai_inference_ms = $26,
                ai_last_checked_at = $27, ai_last_error = $28,
                hybrid_status = $29, updated_at = CURRENT_TIMESTAMP
            WHERE console_key = $1 AND camera_id = $2
            """,
            self.console_key,
            row["camera_id"],
            result["latest_path"],
            result["captured_at"],
            result["overlay_path"],
            status,
            result["change_score"],
            result["changed_fraction"],
            result["largest_change_fraction"],
            result["mean_difference"],
            json.dumps(result["change_components"]),
            json.dumps(result["alignment"]),
            consecutive,
            abnormal_since,
            now,
            result.get("ai_profile_id"),
            result.get("ai_status", "not_ready"),
            result.get("ai_score"),
            result.get("ai_threshold"),
            result.get("ai_score_ratio"),
            result.get("ai_is_anomaly"),
            result.get("ai_heatmap_path"),
            result.get("ai_model_version"),
            result.get("ai_trained_at"),
            result.get("ai_training_samples"),
            result.get("ai_inference_ms"),
            result.get("ai_last_checked_at"),
            result.get("ai_last_error"),
            result.get("hybrid_status", "classical_only"),
        )
        for old_key, new_key in (
            ("latest_path", "latest_path"),
            ("overlay_path", "overlay_path"),
            ("ai_heatmap_path", "ai_heatmap_path"),
        ):
            old_path = row.get(old_key)
            new_path = result.get(new_key)
            if old_path and new_path and str(old_path) != str(new_path):
                try:
                    await asyncio.to_thread(
                        safe_image_path(self.snapshot_root, str(old_path)).unlink,
                        missing_ok=True,
                    )
                except OSError:
                    logger.warning("Could not remove replaced comparison image %s", old_path)
        result["persistent_seconds"] = round(elapsed, 1)
        result["stored_status"] = status

    async def _store_region_result(
        self,
        row: Mapping[str, Any],
        result: Mapping[str, Any],
        confirmation_seconds: int,
    ) -> None:
        now = utc_now()
        abnormal = result["state"] != "normal"
        abnormal_since = row["abnormal_since"] if abnormal else None
        if abnormal and abnormal_since is None:
            abnormal_since = now
        elapsed = (now - abnormal_since).total_seconds() if abnormal_since else 0
        if not abnormal:
            status = "normal"
            consecutive = 0
        elif result["state"] == "missing" and elapsed < confirmation_seconds:
            status = "obscured"
            consecutive = int(row["consecutive_abnormal"] or 0) + 1
        else:
            status = "suspected"
            consecutive = int(row["consecutive_abnormal"] or 0) + 1
        await self.pool.execute(
            """
            UPDATE unifi_protect_bollard_regions
            SET status = $3, last_match_score = $4, last_expected_score = $5,
                last_offset_x = $6, last_offset_y = $7,
                consecutive_abnormal = $8, abnormal_since = $9,
                last_checked_at = $10, last_error = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE console_key = $1 AND region_id = $2
            """,
            self.console_key,
            row["region_id"],
            status,
            result["best_score"],
            result["expected_score"],
            result["offset_x"],
            result["offset_y"],
            consecutive,
            abnormal_since,
            now,
        )
        result["persistent_seconds"] = round(elapsed, 1)
        result["stored_status"] = status

    async def _store_fixed_asset_result(
        self,
        row: Mapping[str, Any],
        result: Mapping[str, Any],
        confirmation_seconds: int,
    ) -> None:
        now = utc_now()
        changed = result["state"] == "changed"
        abnormal_since = row["abnormal_since"] if changed else None
        if changed and abnormal_since is None:
            abnormal_since = now
        elapsed = (now - abnormal_since).total_seconds() if abnormal_since else 0
        consecutive = int(row["consecutive_abnormal"] or 0) + 1 if changed else 0
        if result["state"] == "obscured":
            status = "obscured"
        elif changed and elapsed >= confirmation_seconds:
            status = "suspected"
        elif changed:
            status = "changed"
        else:
            status = "normal"
        await self.pool.execute(
            """
            UPDATE unifi_protect_fixed_asset_monitors
            SET latest_path = $3, latest_captured_at = $4, overlay_path = $5,
                status = $6, change_score = $7, changed_fraction = $8,
                largest_change_fraction = $9, mean_difference = $10,
                change_components = $11::jsonb, consecutive_abnormal = $12,
                abnormal_since = $13, last_checked_at = $14,
                last_error = NULL, ai_profile_id = $15, ai_status = $16,
                ai_score = $17, ai_threshold = $18, ai_score_ratio = $19,
                ai_is_anomaly = $20,
                ai_heatmap_path = COALESCE($21, ai_heatmap_path),
                ai_model_version = $22, ai_trained_at = $23,
                ai_training_samples = $24, ai_inference_ms = $25,
                ai_last_checked_at = $26, ai_last_error = $27,
                hybrid_status = $28, updated_at = CURRENT_TIMESTAMP
            WHERE console_key = $1 AND asset_key = $2
            """,
            self.console_key,
            row["asset_key"],
            result["latest_path"],
            result["captured_at"],
            result["overlay_path"],
            status,
            result["change_score"],
            result["changed_fraction"],
            result["largest_change_fraction"],
            result["mean_difference"],
            json.dumps(result["change_components"]),
            consecutive,
            abnormal_since,
            now,
            result.get("ai_profile_id"),
            result.get("ai_status", "not_ready"),
            result.get("ai_score"),
            result.get("ai_threshold"),
            result.get("ai_score_ratio"),
            result.get("ai_is_anomaly"),
            result.get("ai_heatmap_path"),
            result.get("ai_model_version"),
            result.get("ai_trained_at"),
            result.get("ai_training_samples"),
            result.get("ai_inference_ms"),
            result.get("ai_last_checked_at"),
            result.get("ai_last_error"),
            result.get("hybrid_status", "classical_only"),
        )
        for key in ("latest_path", "overlay_path", "ai_heatmap_path"):
            old_path = row.get(key)
            new_path = result.get(key)
            if old_path and new_path and str(old_path) != str(new_path):
                try:
                    await asyncio.to_thread(
                        safe_image_path(self.snapshot_root, str(old_path)).unlink,
                        missing_ok=True,
                    )
                except OSError:
                    logger.warning("Could not remove replaced asset image %s", old_path)
        result["persistent_seconds"] = round(elapsed, 1)
        result["stored_status"] = status

    async def _context_for(self, camera_ids: Sequence[str], observed_at: datetime) -> dict[str, Any]:
        from_at = observed_at - timedelta(minutes=3)
        to_at = observed_at + timedelta(minutes=1)
        events = await self.pool.fetch(
            """
            SELECT source_event_id, camera_id, camera_name, event_type,
                   smart_detect_types, start_at, score
            FROM unifi_protect_events
            WHERE console_key = $1 AND camera_id = ANY($2::varchar[])
              AND COALESCE(start_at, last_received_at) BETWEEN $3 AND $4
              AND ('vehicle' = ANY(smart_detect_types) OR event_type ILIKE '%vehicle%')
            ORDER BY COALESCE(start_at, last_received_at) DESC LIMIT 20
            """,
            self.console_key,
            list(camera_ids),
            from_at,
            to_at,
        )
        plates = await self.pool.fetch(
            """
            SELECT recognition_id, normalized_value, camera_id, camera_name, occurred_at
            FROM unifi_protect_recognitions
            WHERE console_key = $1 AND kind = 'license_plate'
              AND camera_id = ANY($2::varchar[]) AND occurred_at BETWEEN $3 AND $4
              AND COALESCE(source_device, '') <> 'FAKE_MAC'
            ORDER BY occurred_at DESC LIMIT 20
            """,
            self.console_key,
            list(camera_ids),
            from_at,
            to_at,
        )
        return {
            "vehicle_events": [dict(row) for row in events],
            "plates": [dict(row) for row in plates],
        }

    async def _update_incidents(
        self,
        results: list[dict[str, Any]],
        current_images: Mapping[str, tuple[bytes, datetime]],
        confirmation_seconds: int,
        notification_enabled: bool,
    ) -> list[int]:
        by_bollard: dict[str, list[dict[str, Any]]] = {}
        for result in results:
            by_bollard.setdefault(result["bollard_key"], []).append(result)
        created: list[int] = []
        now = utc_now()
        for bollard_key, rows in by_bollard.items():
            persistent = [
                row
                for row in rows
                if self._incident_candidate(row)
                and float(row.get("persistent_seconds") or 0) >= confirmation_seconds
            ]
            moved = [row for row in persistent if row["state"] in {"moved", "changed"}]
            required = 2 if len(rows) > 1 else 1
            confirmed = len(persistent) >= required and (bool(moved) or len(rows) > 1)
            active = await self.pool.fetchrow(
                """
                SELECT * FROM unifi_protect_bollard_incidents
                WHERE console_key = $1 AND bollard_key = $2
                  AND status IN ('active', 'acknowledged')
                ORDER BY detected_at DESC LIMIT 1
                """,
                self.console_key,
                bollard_key,
            )
            if confirmed:
                if active:
                    await self.pool.execute(
                        """
                        UPDATE unifi_protect_bollard_incidents
                        SET last_observed_at = $3, updated_at = CURRENT_TIMESTAMP
                        WHERE console_key = $1 AND incident_id = $2
                        """,
                        self.console_key,
                        active["incident_id"],
                        now,
                    )
                    continue
                camera_ids = list(dict.fromkeys(row["camera_id"] for row in persistent))
                context = await self._context_for(camera_ids, now)
                evidence: dict[str, Any] = {}
                for row in persistent:
                    camera_id = row["camera_id"]
                    content, captured_at = current_images[camera_id]
                    try:
                        content, captured_at = await self.snapshot_fetcher(camera_id, True)
                    except Exception:
                        pass
                    if row.get("asset_type"):
                        definition = FIXED_STRUCTURE_MONITORS.get(str(row["bollard_key"]))
                        if definition:
                            content = encode_jpeg(
                                fixed_pixel_crop(decode_jpeg(content), definition["crop"]),
                                quality=95,
                            )
                    after_path = image_relative_path(
                        self.console_key,
                        camera_id,
                        "incident-after",
                        f"{bollard_key}:{captured_at.isoformat()}",
                        captured_at,
                    )
                    before_path = image_relative_path(
                        self.console_key,
                        camera_id,
                        "incident-before",
                        f"{bollard_key}:{captured_at.isoformat()}",
                        captured_at,
                    )
                    baseline_content = await asyncio.to_thread(
                        safe_image_path(
                            self.snapshot_root,
                            str(row["baseline_path"]),
                        ).read_bytes
                    )
                    await asyncio.to_thread(
                        write_image_atomic,
                        self.snapshot_root,
                        before_path,
                        baseline_content,
                    )
                    await asyncio.to_thread(write_image_atomic, self.snapshot_root, after_path, content)
                    evidence[camera_id] = {
                        "camera_name": row["camera_name"],
                        "asset_type": row.get("asset_type"),
                        "before_path": before_path,
                        "after_path": after_path,
                        "captured_at": captured_at.isoformat(),
                        "state": row["state"],
                        "score": row.get("best_score"),
                        "expected_score": row.get("expected_score"),
                        "offset_x": row.get("offset_x"),
                        "offset_y": row.get("offset_y"),
                        "distance_pixels": row.get("distance_pixels"),
                        "change_score": row.get("change_score"),
                        "changed_fraction": row.get("changed_fraction"),
                        "largest_change_fraction": row.get("largest_change_fraction"),
                    }
                incident = await self.pool.fetchrow(
                    """
                    INSERT INTO unifi_protect_bollard_incidents (
                        console_key, bollard_key, display_name, status, severity,
                        detected_at, confirmed_at, last_observed_at, evidence, context
                    ) VALUES ($1, $2, $3, 'active', 'alarm', $4, $4, $4, $5::jsonb, $6::jsonb)
                    RETURNING *
                    """,
                    self.console_key,
                    bollard_key,
                    persistent[0]["display_name"],
                    now,
                    json.dumps(evidence, default=str),
                    json.dumps(context, default=str),
                )
                created.append(int(incident["incident_id"]))
                if notification_enabled:
                    await self._notify_incident(dict(incident))
            elif active and rows and all(self._effectively_normal(row) for row in rows):
                await self.pool.execute(
                    """
                    UPDATE unifi_protect_bollard_incidents
                    SET status = 'resolved', resolved_at = $3,
                        resolution_reason = 'hybrid_normal', updated_at = CURRENT_TIMESTAMP
                    WHERE console_key = $1 AND incident_id = $2
                    """,
                    self.console_key,
                    active["incident_id"],
                    now,
                )
        return created

    async def _notify_incident(self, incident: Mapping[str, Any]) -> None:
        if not self.ntfy_topic:
            await self.pool.execute(
                """
                UPDATE unifi_protect_bollard_incidents
                SET notification_status = 'not_configured', updated_at = CURRENT_TIMESTAMP
                WHERE console_key = $1 AND incident_id = $2
                """,
                self.console_key,
                incident["incident_id"],
            )
            return
        message = bollard_notification_message(incident)
        try:
            async with self.notification_session.post(
                f"{self.ntfy_base_url}/{self.ntfy_topic}",
                data=message.encode("utf-8"),
                headers={
                    "Title": "Pullertalarm ved solstudio",
                    "Priority": "5",
                    "Tags": "warning,car",
                    "Click": bollard_alarm_click_url(self.alarm_app_url, incident["incident_id"]),
                },
                timeout=aiohttp.ClientTimeout(total=8),
            ) as response:
                response.raise_for_status()
            await self.pool.execute(
                """
                UPDATE unifi_protect_bollard_incidents
                SET notification_status = 'sent', notification_at = CURRENT_TIMESTAMP,
                    notification_error = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE console_key = $1 AND incident_id = $2
                """,
                self.console_key,
                incident["incident_id"],
            )
        except Exception as error:
            await self.pool.execute(
                """
                UPDATE unifi_protect_bollard_incidents
                SET notification_status = 'failed', notification_error = $3,
                    updated_at = CURRENT_TIMESTAMP
                WHERE console_key = $1 AND incident_id = $2
                """,
                self.console_key,
                incident["incident_id"],
                str(error)[:500],
            )

    async def acknowledge(self, incident_id: int, acknowledged_by: str = "Protect Ledger") -> dict[str, Any]:
        row = await self.pool.fetchrow(
            """
            UPDATE unifi_protect_bollard_incidents
            SET status = CASE WHEN status = 'active' THEN 'acknowledged' ELSE status END,
                acknowledged_at = CASE WHEN status = 'active' THEN CURRENT_TIMESTAMP ELSE acknowledged_at END,
                acknowledged_by = CASE WHEN status = 'active' THEN $3 ELSE acknowledged_by END,
                updated_at = CURRENT_TIMESTAMP
            WHERE console_key = $1 AND incident_id = $2 RETURNING *
            """,
            self.console_key,
            incident_id,
            acknowledged_by[:120],
        )
        if row is None:
            raise LookupError("Hendelsen finnes ikke")
        return self.public_incident(dict(row))

    async def retention_cleanup(self, retention_days: int) -> dict[str, int]:
        rows = await self.pool.fetch(
            """
            DELETE FROM unifi_protect_bollard_incidents
            WHERE console_key = $1 AND status = 'resolved'
              AND COALESCE(resolved_at, detected_at)
                  < CURRENT_TIMESTAMP - make_interval(days => $2)
            RETURNING evidence
            """,
            self.console_key,
            max(1, int(retention_days)),
        )
        paths: set[str] = set()
        for row in rows:
            evidence = row["evidence"] or {}
            if isinstance(evidence, str):
                evidence = json.loads(evidence)
            for camera_evidence in evidence.values():
                if not isinstance(camera_evidence, Mapping):
                    continue
                for key in ("before_path", "after_path"):
                    if camera_evidence.get(key):
                        paths.add(str(camera_evidence[key]))
        removed_files = 0
        for relative_path in paths:
            try:
                path = safe_image_path(self.snapshot_root, relative_path)
                existed = path.is_file()
                await asyncio.to_thread(path.unlink, missing_ok=True)
                removed_files += int(existed)
            except OSError:
                logger.warning("Could not remove expired bollard evidence %s", relative_path)
        return {"deleted_incidents": len(rows), "deleted_files": removed_files}

    async def region_image_path(self, region_id: int) -> Path:
        value = await self.pool.fetchval(
            """
            SELECT baseline_path FROM unifi_protect_bollard_regions
            WHERE console_key = $1 AND region_id = $2
            """,
            self.console_key,
            region_id,
        )
        if not value:
            raise LookupError("Referansebildet finnes ikke")
        path = safe_image_path(self.snapshot_root, str(value))
        if not path.is_file():
            raise LookupError("Referansefilen finnes ikke")
        return path

    async def incident_image_path(self, incident_id: int, camera_id: str, kind: str) -> Path:
        if kind not in {"before", "after"}:
            raise ValueError("Bildetype må være before eller after")
        evidence = await self.pool.fetchval(
            """
            SELECT evidence FROM unifi_protect_bollard_incidents
            WHERE console_key = $1 AND incident_id = $2
            """,
            self.console_key,
            incident_id,
        )
        if evidence is None:
            raise LookupError("Hendelsen finnes ikke")
        if isinstance(evidence, str):
            evidence = json.loads(evidence)
        value = (evidence.get(camera_id) or {}).get(f"{kind}_path")
        if not value:
            raise LookupError("Bildet finnes ikke")
        path = safe_image_path(self.snapshot_root, str(value))
        if not path.is_file():
            raise LookupError("Bildefilen finnes ikke")
        return path
