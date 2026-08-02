from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import cv2
import numpy as np


@dataclass(frozen=True)
class Profile:
    profile_id: str
    display_name: str
    object_type: str
    camera_name: str
    camera_hash: str
    source_crop: Mapping[str, int]
    regions: tuple[Mapping[str, Any], ...]
    threshold_scale: float = 1.0


PROFILES: dict[str, Profile] = {
    "north-bollards": Profile(
        profile_id="north-bollards",
        display_name="Pullerter Butikk Nord",
        object_type="bollards",
        camera_name="G6 Butikk Nord",
        camera_hash="52e69b43c036",
        source_crop={"x": 614, "y": 324, "width": 1152, "height": 1836},
        regions=(
            {"label": "Pullert 1", "x": 0.13, "y": 0.02, "width": 0.22, "height": 0.30, "padding": 0.02},
            {"label": "Pullert 2", "x": 0.24, "y": 0.28, "width": 0.29, "height": 0.39, "padding": 0.02},
            {"label": "Pullert 3", "x": 0.48, "y": 0.66, "width": 0.38, "height": 0.34, "padding": 0.01},
        ),
    ),
    "front-bollards": Profile(
        profile_id="front-bollards",
        display_name="Pullerter Butikk Front",
        object_type="bollards",
        camera_name="G6 Butikk Front",
        camera_hash="2889a734a2fd",
        source_crop={"x": 0, "y": 1123, "width": 2803, "height": 1037},
        regions=(
            {"label": "Pullert 1", "x": 0.00, "y": 0.02, "width": 0.08, "height": 0.36, "padding": 0.02},
            {"label": "Pullert 2", "x": 0.37, "y": 0.35, "width": 0.15, "height": 0.22, "padding": 0.02},
            {"label": "Pullert 3", "x": 0.49, "y": 0.38, "width": 0.15, "height": 0.22, "padding": 0.02},
            {"label": "Pullert 4", "x": 0.58, "y": 0.40, "width": 0.14, "height": 0.22, "padding": 0.02},
        ),
    ),
    "solstudio-bollards": Profile(
        profile_id="solstudio-bollards",
        display_name="Pullerter Solstudio Front",
        object_type="bollards",
        camera_name="G6 Solstudio Front",
        camera_hash="290e6de5f12a",
        source_crop={"x": 2765, "y": 0, "width": 537, "height": 734},
        regions=(
            {"label": "Pullert 1", "x": 0.32, "y": 0.00, "width": 0.13, "height": 0.31, "padding": 0.02},
            {"label": "Pullert 2", "x": 0.35, "y": 0.07, "width": 0.17, "height": 0.37, "padding": 0.02},
            {"label": "Pullert 3", "x": 0.31, "y": 0.20, "width": 0.24, "height": 0.44, "padding": 0.02},
        ),
        threshold_scale=0.94,
    ),
    "solstudio-stairs": Profile(
        profile_id="solstudio-stairs",
        display_name="Trapp ved Solstudio",
        object_type="stairs",
        camera_name="G6 Solstudio Front",
        camera_hash="290e6de5f12a",
        source_crop={"x": 2200, "y": 400, "width": 1640, "height": 1760},
        regions=(
            {
                "label": "Trapp",
                "polygon": (
                    {"x": 0.325, "y": 0.15},
                    {"x": 0.545, "y": 0.22},
                    {"x": 0.565, "y": 0.93},
                    {"x": 0.14, "y": 0.85},
                ),
                "padding": 0.02,
            },
        ),
    ),
}


def fixed_source_crop(image: np.ndarray, crop: Mapping[str, int]) -> np.ndarray:
    height, width = image.shape[:2]
    x = int(crop["x"])
    y = int(crop["y"])
    right = x + int(crop["width"])
    bottom = y + int(crop["height"])
    if x < 0 or y < 0 or right > width or bottom > height:
        raise ValueError(
            f"Fixed crop {x},{y},{right},{bottom} is outside source image {width}x{height}"
        )
    return image[y:bottom, x:right].copy()


def _region_bounds(
    region: Mapping[str, Any], width: int, height: int, padding: float = 0.22
) -> tuple[int, int, int, int, np.ndarray | None]:
    padding = float(region.get("padding", padding))
    polygon = region.get("polygon")
    mask: np.ndarray | None = None
    if polygon:
        points = np.array(
            [
                [round(float(point["x"]) * width), round(float(point["y"]) * height)]
                for point in polygon
            ],
            dtype=np.int32,
        )
        x, y, region_width, region_height = cv2.boundingRect(points)
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask, [points], 255)
    else:
        x = round(float(region["x"]) * width)
        y = round(float(region["y"]) * height)
        region_width = round(float(region["width"]) * width)
        region_height = round(float(region["height"]) * height)
    pad_x = round(region_width * padding)
    pad_y = round(region_height * padding)
    left = max(0, x - pad_x)
    top = max(0, y - pad_y)
    right = min(width, x + region_width + pad_x)
    bottom = min(height, y + region_height + pad_y)
    return left, top, right, bottom, mask


def _fit_tile(image: np.ndarray, tile_size: int, fill: int = 114) -> np.ndarray:
    height, width = image.shape[:2]
    if height < 2 or width < 2:
        raise ValueError("Analysis region is empty")
    scale = min(tile_size / width, tile_size / height)
    resized_width = max(1, round(width * scale))
    resized_height = max(1, round(height * scale))
    resized = cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_AREA)
    tile = np.full((tile_size, tile_size, 3), fill, dtype=np.uint8)
    x = (tile_size - resized_width) // 2
    y = (tile_size - resized_height) // 2
    tile[y : y + resized_height, x : x + resized_width] = resized
    return tile


def build_analysis_atlas(
    image: np.ndarray,
    regions: Sequence[Mapping[str, Any]],
    *,
    atlas_size: int = 512,
) -> np.ndarray:
    """Create a deterministic detail atlas without altering the source camera image."""
    if not regions:
        raise ValueError("Profile has no analysis regions")
    height, width = image.shape[:2]
    columns = 1 if len(regions) == 1 else 2
    rows = (len(regions) + columns - 1) // columns
    tile_size = atlas_size // max(columns, rows)
    atlas = np.full((atlas_size, atlas_size, 3), 114, dtype=np.uint8)
    for index, region in enumerate(regions):
        left, top, right, bottom, polygon_mask = _region_bounds(region, width, height)
        crop = image[top:bottom, left:right].copy()
        if polygon_mask is not None:
            local_mask = polygon_mask[top:bottom, left:right]
            crop[local_mask == 0] = 114
        tile = _fit_tile(crop, tile_size)
        tile_x = (index % columns) * tile_size
        tile_y = (index // columns) * tile_size
        atlas[tile_y : tile_y + tile_size, tile_x : tile_x + tile_size] = tile
    return atlas


def prepare_profile_image(profile: Profile, source_or_crop: np.ndarray, *, is_source: bool) -> np.ndarray:
    fixed_crop = fixed_source_crop(source_or_crop, profile.source_crop) if is_source else source_or_crop
    return build_analysis_atlas(fixed_crop, profile.regions)
