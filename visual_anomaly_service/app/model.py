from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import cv2
import numpy as np
import torch
import torch.nn.functional as functional
from torch import nn
from torchvision.models import ResNet18_Weights, resnet18
from torchvision.models.feature_extraction import create_feature_extractor

from .profiles import PROFILES, Profile, prepare_profile_image


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ModelMetadata:
    profile_id: str
    display_name: str
    model_version: str
    trained_at: str
    training_samples: int
    calibration_samples: int
    source_candidates: int
    memory_patches: int
    image_threshold: float
    patch_threshold: float
    structure_threshold: float
    calibration_median: float
    calibration_mad: float
    structure_calibration_median: float
    structure_calibration_mad: float
    archive_fingerprint: str


class FeatureExtractor(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        backbone = resnet18(weights=ResNet18_Weights.DEFAULT)
        self.extractor = create_feature_extractor(
            backbone,
            return_nodes={"layer2": "layer2", "layer3": "layer3"},
        )
        self.extractor.eval()

    @torch.inference_mode()
    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        features = self.extractor(tensor)
        layer2 = features["layer2"]
        layer3 = functional.interpolate(
            features["layer3"], size=layer2.shape[-2:], mode="bilinear", align_corners=False
        )
        combined = torch.cat((layer2, layer3), dim=1)
        return functional.adaptive_avg_pool2d(combined, (24, 24))


class PatchCoreModel:
    """CPU PatchCore implementation for fixed-camera, normal-only anomaly detection."""

    image_size = 512
    projected_dimensions = 128
    model_version = "patchcore-resnet18-fixed-position-v5"

    def __init__(self, profile: Profile, model_root: Path) -> None:
        self.profile = profile
        self.model_root = model_root
        self.path = model_root / profile.profile_id / "model.pt"
        self.metadata_path = model_root / profile.profile_id / "metadata.json"
        self.extractor: FeatureExtractor | None = None
        self.projection: torch.Tensor | None = None
        self.memory_bank: torch.Tensor | None = None
        self.structure_bank: torch.Tensor | None = None
        self.metadata: ModelMetadata | None = None
        self.lock = threading.RLock()
        self._load_if_available()

    @property
    def ready(self) -> bool:
        return (
            self.memory_bank is not None
            and self.structure_bank is not None
            and self.projection is not None
            and self.metadata is not None
        )

    def _feature_extractor(self) -> FeatureExtractor:
        if self.extractor is None:
            torch.set_num_threads(max(1, int(os.getenv("PATCHCORE_TORCH_THREADS", "4"))))
            self.extractor = FeatureExtractor()
        return self.extractor

    def _projection(self, dimensions: int) -> torch.Tensor:
        if self.projection is None:
            generator = torch.Generator().manual_seed(20260801)
            projection = torch.randn(
                dimensions,
                self.projected_dimensions,
                generator=generator,
                dtype=torch.float32,
            ) / math.sqrt(self.projected_dimensions)
            self.projection = projection
        return self.projection

    @staticmethod
    def _normalized_gray(atlas: np.ndarray) -> np.ndarray:
        # Local contrast normalization makes the fixed-camera model care far
        # more about physical shape than sunlight, shadows and white balance.
        gray = cv2.cvtColor(atlas, cv2.COLOR_BGR2GRAY)
        return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)

    @classmethod
    def _tensor(cls, atlas: np.ndarray) -> torch.Tensor:
        normalized = cls._normalized_gray(atlas)
        rgb = cv2.cvtColor(normalized, cv2.COLOR_GRAY2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().div_(255.0)
        mean = torch.tensor((0.485, 0.456, 0.406)).view(3, 1, 1)
        std = torch.tensor((0.229, 0.224, 0.225)).view(3, 1, 1)
        return ((tensor - mean) / std).unsqueeze(0)

    def embeddings(self, atlas: np.ndarray) -> torch.Tensor:
        features = self._feature_extractor()(self._tensor(atlas))
        patches = features.permute(0, 2, 3, 1).reshape(-1, features.shape[1])
        projection = self._projection(patches.shape[1])
        projected = patches @ projection
        return functional.normalize(projected, p=2, dim=1).cpu()

    @classmethod
    def structure_map(cls, atlas: np.ndarray) -> torch.Tensor:
        gray = cls._normalized_gray(atlas)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 45, 125)
        reduced = cv2.resize(edges, (96, 96), interpolation=cv2.INTER_AREA)
        return torch.from_numpy(reduced.astype(np.float32) / 255.0)

    @staticmethod
    def _distances(embeddings: torch.Tensor, bank: torch.Tensor) -> torch.Tensor:
        if bank.ndim == 3:
            if bank.shape[1] != embeddings.shape[0] or bank.shape[2] != embeddings.shape[1]:
                raise ValueError("Position-aware memory bank has incompatible dimensions")
            return torch.linalg.vector_norm(bank - embeddings.unsqueeze(0), dim=2).amin(dim=0)
        minima: list[torch.Tensor] = []
        for chunk in embeddings.split(192):
            minima.append(torch.cdist(chunk, bank).amin(dim=1))
        return torch.cat(minima)

    @staticmethod
    def _score(distances: torch.Tensor) -> float:
        return float(torch.quantile(distances, 0.995).item())

    @staticmethod
    def _structure_distance(
        query: torch.Tensor, bank: torch.Tensor
    ) -> tuple[float, torch.Tensor]:
        differences = torch.abs(bank - query.unsqueeze(0))
        scores = differences.mean(dim=(1, 2))
        index = int(torch.argmin(scores).item())
        return float(scores[index].item()), differences[index]

    def _load_if_available(self) -> None:
        if not self.path.is_file() or not self.metadata_path.is_file():
            return
        metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        if metadata.get("model_version") != self.model_version:
            return
        payload = torch.load(self.path, map_location="cpu", weights_only=True)
        self.memory_bank = payload["memory_bank"].float()
        self.structure_bank = payload["structure_bank"].float()
        self.projection = payload["projection"].float()
        self.metadata = ModelMetadata(**metadata)

    def train(self, atlases: Iterable[np.ndarray], source_candidates: int, fingerprint: str) -> ModelMetadata:
        started = time.perf_counter()
        all_atlases = list(atlases)
        if len(all_atlases) < 24:
            raise ValueError(f"At least 24 normal images are required, got {len(all_atlases)}")
        calibration_count = max(8, min(60, len(all_atlases) // 5))
        calibration_indices = set(
            np.linspace(0, len(all_atlases) - 1, num=calibration_count, dtype=int).tolist()
        )
        calibration = [atlas for index, atlas in enumerate(all_atlases) if index in calibration_indices]
        training = [atlas for index, atlas in enumerate(all_atlases) if index not in calibration_indices]
        with self.lock:
            self.projection = None
            # Fixed cameras let us make PatchCore stricter and more useful: each
            # patch is matched only against historical patches at the same
            # atlas coordinate, never against an unrelated part of the scene.
            memory_bank = torch.stack([self.embeddings(atlas) for atlas in training])
            structure_bank = torch.stack([self.structure_map(atlas) for atlas in training])
            calibration_scores: list[float] = []
            structure_scores: list[float] = []
            calibration_patch_distances: list[torch.Tensor] = []
            for atlas in calibration:
                distances = self._distances(self.embeddings(atlas), memory_bank)
                calibration_scores.append(self._score(distances))
                calibration_patch_distances.append(distances)
                structure_score, _structure_difference = self._structure_distance(
                    self.structure_map(atlas), structure_bank
                )
                structure_scores.append(structure_score)
            scores = np.asarray(calibration_scores, dtype=np.float32)
            median = float(np.median(scores))
            mad = float(np.median(np.abs(scores - median)))
            robust_limit = median + max(0.012, 6.0 * 1.4826 * mad)
            image_threshold = max(
                float(np.quantile(scores, 0.995)) * 1.06,
                robust_limit,
                median * 1.15,
            )
            structure_values = np.asarray(structure_scores, dtype=np.float32)
            structure_median = float(np.median(structure_values))
            structure_mad = float(
                np.median(np.abs(structure_values - structure_median))
            )
            structure_threshold = max(
                float(np.quantile(structure_values, 0.995)) * 1.06,
                structure_median + max(0.004, 6.0 * 1.4826 * structure_mad),
                structure_median * 1.15,
            )
            patch_values = torch.cat(calibration_patch_distances)
            patch_threshold = max(
                float(torch.quantile(patch_values, 0.997).item()) * 1.04,
                0.02,
            )
            metadata = ModelMetadata(
                profile_id=self.profile.profile_id,
                display_name=self.profile.display_name,
                model_version=self.model_version,
                trained_at=utc_iso(),
                training_samples=len(training),
                calibration_samples=len(calibration),
                source_candidates=source_candidates,
                memory_patches=int(memory_bank.shape[0] * memory_bank.shape[1]),
                image_threshold=round(image_threshold, 6),
                patch_threshold=round(patch_threshold, 6),
                structure_threshold=round(structure_threshold, 6),
                calibration_median=round(median, 6),
                calibration_mad=round(mad, 6),
                structure_calibration_median=round(structure_median, 6),
                structure_calibration_mad=round(structure_mad, 6),
                archive_fingerprint=fingerprint,
            )
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".part")
            torch.save(
                {
                    "memory_bank": memory_bank,
                    "structure_bank": structure_bank,
                    "projection": self.projection,
                    "training_seconds": round(time.perf_counter() - started, 2),
                },
                temporary,
            )
            os.replace(temporary, self.path)
            self.metadata_path.write_text(
                json.dumps(asdict(metadata), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self.memory_bank = memory_bank
            self.structure_bank = structure_bank
            self.metadata = metadata
            return metadata

    def infer(self, atlas: np.ndarray) -> tuple[dict[str, Any], np.ndarray]:
        if (
            not self.ready
            or self.metadata is None
            or self.memory_bank is None
            or self.structure_bank is None
        ):
            raise RuntimeError("Model is not trained")
        started = time.perf_counter()
        with self.lock:
            distances = self._distances(self.embeddings(atlas), self.memory_bank)
        score = self._score(distances)
        threshold = self.metadata.image_threshold * self.profile.threshold_scale
        structure_score, structure_difference = self._structure_distance(
            self.structure_map(atlas), self.structure_bank
        )
        structure_threshold = self.metadata.structure_threshold * self.profile.threshold_scale
        distance_map = distances.reshape(24, 24).numpy()
        heat = np.clip(distance_map / max(self.metadata.patch_threshold, 1e-6), 0.0, 1.5)
        structure_heat = cv2.resize(
            structure_difference.numpy(),
            (distance_map.shape[1], distance_map.shape[0]),
            interpolation=cv2.INTER_AREA,
        )
        structure_heat = np.clip(
            structure_heat / max(structure_threshold, 1e-6), 0.0, 1.5
        )
        heat = np.maximum(heat, structure_heat)
        heat = cv2.GaussianBlur(heat, (0, 0), 1.2)
        heat_u8 = np.clip(heat / 1.5 * 255.0, 0, 255).astype(np.uint8)
        heat_u8 = cv2.resize(heat_u8, (atlas.shape[1], atlas.shape[0]), interpolation=cv2.INTER_CUBIC)
        color = cv2.applyColorMap(heat_u8, cv2.COLORMAP_TURBO)
        overlay = cv2.addWeighted(atlas, 0.62, color, 0.38, 0)
        columns = 1 if len(self.profile.regions) == 1 else 2
        rows = (len(self.profile.regions) + columns - 1) // columns
        tile_size = overlay.shape[1] // max(columns, rows)
        for index, region in enumerate(self.profile.regions):
            x = (index % columns) * tile_size
            y = (index // columns) * tile_size
            label = str(region.get("label") or f"Område {index + 1}")
            cv2.rectangle(
                overlay,
                (x + 1, y + 1),
                (x + tile_size - 2, y + tile_size - 2),
                (242, 242, 242),
                1,
            )
            cv2.putText(
                overlay,
                label,
                (x + 12, y + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (18, 18, 18),
                3,
                cv2.LINE_AA,
            )
            cv2.putText(
                overlay,
                label,
                (x + 12, y + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
        ratio = score / max(threshold, 1e-6)
        structure_ratio = structure_score / max(structure_threshold, 1e-6)
        combined_ratio = max(ratio, structure_ratio)
        is_anomaly = combined_ratio > 1.0
        return (
            {
                "profile_id": self.profile.profile_id,
                "display_name": self.profile.display_name,
                "object_type": self.profile.object_type,
                "status": "anomaly" if is_anomaly else "normal",
                "is_anomaly": is_anomaly,
                "score": round(score, 6),
                "threshold": round(threshold, 6),
                "score_ratio": round(combined_ratio, 4),
                "patch_score_ratio": round(ratio, 4),
                "structural_score": round(structure_score, 6),
                "structural_threshold": round(structure_threshold, 6),
                "structural_score_ratio": round(structure_ratio, 4),
                "confidence": round(min(1.0, abs(combined_ratio - 1.0)), 4),
                "model_version": self.metadata.model_version,
                "trained_at": self.metadata.trained_at,
                "training_samples": self.metadata.training_samples,
                "inference_ms": round((time.perf_counter() - started) * 1000.0, 1),
            },
            overlay,
        )


def archive_fingerprint(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        stat = path.stat()
        digest.update(str(path).encode())
        digest.update(str(stat.st_size).encode())
        digest.update(str(stat.st_mtime_ns).encode())
    return digest.hexdigest()[:20]


def decode_image(content: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Invalid JPEG image")
    return image


def sampled_archive_images(snapshot_root: Path, profile: Profile, limit: int) -> tuple[list[Path], int]:
    candidates = sorted(
        path
        for path in snapshot_root.glob(f"*/*/*/{profile.camera_hash}/**/*")
        if path.suffix.lower() in {".jpg", ".jpeg"} and "bollards" not in path.parts
    )
    total = len(candidates)
    if total <= limit:
        return candidates, total
    indices = np.linspace(0, total - 1, num=limit, dtype=int)
    return [candidates[int(index)] for index in indices], total


def unique_training_atlases(paths: list[Path], profile: Profile) -> list[np.ndarray]:
    atlases: list[np.ndarray] = []
    hashes: set[str] = set()
    for path in paths:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            continue
        try:
            atlas = prepare_profile_image(profile, image, is_source=True)
        except ValueError:
            continue
        signature_image = cv2.resize(cv2.cvtColor(atlas, cv2.COLOR_BGR2GRAY), (24, 24))
        signature = hashlib.sha1(signature_image.tobytes()).hexdigest()
        if signature in hashes:
            continue
        hashes.add(signature)
        atlases.append(atlas)
    return atlases


class ModelRegistry:
    def __init__(self, snapshot_root: Path, data_root: Path, sample_limit: int = 160) -> None:
        self.snapshot_root = snapshot_root
        self.data_root = data_root
        self.model_root = data_root / "models"
        self.sample_limit = max(40, min(500, sample_limit))
        self.models = {
            profile_id: PatchCoreModel(profile, self.model_root)
            for profile_id, profile in PROFILES.items()
        }
        self.training: dict[str, dict[str, Any]] = {}
        self.training_lock = threading.Lock()

    def status(self) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for profile_id, model in self.models.items():
            metadata = asdict(model.metadata) if model.metadata else None
            output.append(
                {
                    "profile_id": profile_id,
                    "display_name": model.profile.display_name,
                    "object_type": model.profile.object_type,
                    "camera_name": model.profile.camera_name,
                    "ready": model.ready,
                    "training": self.training.get(profile_id),
                    "metadata": metadata,
                }
            )
        return output

    def train_profile(self, profile_id: str, force: bool = False) -> ModelMetadata:
        if profile_id not in self.models:
            raise KeyError(profile_id)
        model = self.models[profile_id]
        with self.training_lock:
            self.training[profile_id] = {"state": "collecting", "started_at": utc_iso()}
            try:
                paths, total = sampled_archive_images(
                    self.snapshot_root, model.profile, self.sample_limit
                )
                fingerprint = archive_fingerprint(paths)
                if (
                    not force
                    and model.metadata is not None
                    and model.metadata.archive_fingerprint == fingerprint
                ):
                    return model.metadata
                self.training[profile_id].update(
                    {"state": "extracting", "source_candidates": total, "selected": len(paths)}
                )
                atlases = unique_training_atlases(paths, model.profile)
                self.training[profile_id].update(
                    {"state": "training", "usable_samples": len(atlases)}
                )
                metadata = model.train(atlases, total, fingerprint)
                self.training[profile_id] = {
                    "state": "ready",
                    "completed_at": utc_iso(),
                    "training_samples": metadata.training_samples,
                }
                return metadata
            except Exception as error:
                self.training[profile_id] = {
                    "state": "error",
                    "completed_at": utc_iso(),
                    "error": str(error)[:500],
                }
                raise

    def train_all(self, force: bool = False) -> list[ModelMetadata]:
        return [self.train_profile(profile_id, force=force) for profile_id in PROFILES]

    def infer(self, profile_id: str, content: bytes) -> tuple[dict[str, Any], np.ndarray]:
        if profile_id not in self.models:
            raise KeyError(profile_id)
        model = self.models[profile_id]
        image = decode_image(content)
        atlas = prepare_profile_image(model.profile, image, is_source=False)
        return model.infer(atlas)
