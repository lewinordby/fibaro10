from __future__ import annotations

import asyncio
import base64
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import cv2
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from .model import ModelRegistry
from .profiles import PROFILES


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("visual_anomaly_service")

SNAPSHOT_ROOT = Path(os.getenv("VISUAL_AI_SNAPSHOT_ROOT", "/snapshots"))
DATA_ROOT = Path(os.getenv("VISUAL_AI_DATA_ROOT", "/data"))
API_TOKEN = os.getenv("VISUAL_AI_TOKEN", "").strip()
AUTO_TRAIN = os.getenv("VISUAL_AI_AUTO_TRAIN", "true").strip().lower() in {"1", "true", "yes", "on"}
SAMPLE_LIMIT = int(os.getenv("VISUAL_AI_SAMPLE_LIMIT", "160"))

registry = ModelRegistry(SNAPSHOT_ROOT, DATA_ROOT, SAMPLE_LIMIT)
bootstrap_task: asyncio.Task[None] | None = None


def require_token(authorization: str | None) -> None:
    if not API_TOKEN:
        return
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid visual AI token")


async def bootstrap_models() -> None:
    await asyncio.sleep(3)
    for profile_id, model in registry.models.items():
        if model.ready:
            continue
        try:
            logger.info("Training missing visual model %s", profile_id)
            await asyncio.to_thread(registry.train_profile, profile_id, False)
        except Exception:
            logger.exception("Visual model training failed for %s", profile_id)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global bootstrap_task
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    if AUTO_TRAIN:
        bootstrap_task = asyncio.create_task(bootstrap_models(), name="visual-ai-bootstrap")
    yield
    if bootstrap_task is not None:
        bootstrap_task.cancel()
        await asyncio.gather(bootstrap_task, return_exceptions=True)
        bootstrap_task = None


app = FastAPI(title="Lilletorget Visual Anomaly Service", version="1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, Any]:
    profiles = registry.status()
    ready = sum(1 for profile in profiles if profile["ready"])
    errors = [profile for profile in profiles if (profile.get("training") or {}).get("state") == "error"]
    return {
        "status": "ok" if not errors else "degraded",
        "service": "visual_anomaly_service",
        "models_ready": ready,
        "models_total": len(profiles),
        "profiles": profiles,
    }


@app.get("/api/v1/profiles")
async def profiles(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_token(authorization)
    return {"profiles": registry.status()}


@app.post("/api/v1/profiles/{profile_id}/infer")
async def infer(
    profile_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    require_token(authorization)
    if profile_id not in PROFILES:
        raise HTTPException(status_code=404, detail="Unknown visual AI profile")
    content = await request.body()
    if not content or len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="JPEG body is empty or too large")
    try:
        result, heatmap = await asyncio.to_thread(registry.infer, profile_id, content)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    ok, encoded = cv2.imencode(".jpg", heatmap, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise HTTPException(status_code=500, detail="Could not encode AI heatmap")
    result["heatmap_base64"] = base64.b64encode(encoded.tobytes()).decode("ascii")
    result["mode"] = "advisory"
    return result


def _train_background(profile_id: str, force: bool) -> None:
    try:
        registry.train_profile(profile_id, force=force)
    except Exception:
        logger.exception("Manual training failed for %s", profile_id)


@app.post("/api/v1/profiles/{profile_id}/train", status_code=202)
async def train_profile(
    profile_id: str,
    background_tasks: BackgroundTasks,
    force: bool = False,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    require_token(authorization)
    if profile_id not in PROFILES:
        raise HTTPException(status_code=404, detail="Unknown visual AI profile")
    current = registry.training.get(profile_id) or {}
    if current.get("state") in {"collecting", "extracting", "training"}:
        return {"status": "already_running", "profile_id": profile_id}
    background_tasks.add_task(_train_background, profile_id, force)
    return {"status": "accepted", "profile_id": profile_id, "force": force}


@app.post("/api/v1/train-all", status_code=202)
async def train_all(
    background_tasks: BackgroundTasks,
    force: bool = False,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    require_token(authorization)
    background_tasks.add_task(registry.train_all, force)
    return {"status": "accepted", "profiles": list(PROFILES), "force": force}

