from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request

from .parsing import compact_plate, is_swedish_license_plate, looks_rate_limited, parse_car_info_html

load_dotenv()

DATA_DIR = Path(os.getenv("CAR_INFO_DATA_DIR", "/data"))
STATE_PATH = DATA_DIR / "state.json"

FIBARO10_BASE_URL = os.getenv("FIBARO10_BASE_URL", "http://fibaro10:8110").rstrip("/")
FIBARO10_USERNAME = os.getenv("FIBARO10_USERNAME", "")
FIBARO10_PASSWORD = os.getenv("FIBARO10_PASSWORD", "")
APP_TOKEN = os.getenv("CAR_INFO_APP_TOKEN", "").strip()

URL_TEMPLATE = os.getenv("CAR_INFO_URL_TEMPLATE", "https://www.car.info/sv-se/license-plate/S/{plate}")
USER_AGENT = os.getenv(
    "CAR_INFO_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
)
RUN_INTERVAL_MINUTES = max(15, int(os.getenv("CAR_INFO_RUN_INTERVAL_MINUTES", "45")))
RUN_ON_START = os.getenv("CAR_INFO_RUN_ON_START", "true").strip().lower() in {"1", "true", "yes", "ja"}
BATCH_SIZE = max(1, min(5, int(os.getenv("CAR_INFO_BATCH_SIZE", "1"))))
REQUEST_TIMEOUT_SECONDS = max(5, int(os.getenv("CAR_INFO_REQUEST_TIMEOUT_SECONDS", "30")))
REQUEST_DELAY_SECONDS = max(0, int(os.getenv("CAR_INFO_REQUEST_DELAY_SECONDS", "30")))
RATE_LIMIT_BACKOFF_MINUTES = max(30, int(os.getenv("CAR_INFO_RATE_LIMIT_BACKOFF_MINUTES", "240")))
TEXT_LIMIT = max(1000, int(os.getenv("CAR_INFO_TEXT_LIMIT", "12000")))
BACKLOG_ENABLED = os.getenv("CAR_INFO_BACKLOG_ENABLED", "true").strip().lower() in {"1", "true", "yes", "ja"}
BACKLOG_MAX_PER_CYCLE = max(1, min(100, int(os.getenv("CAR_INFO_BACKLOG_MAX_PER_CYCLE", "25"))))
BACKLOG_DELAY_SECONDS = max(0, int(os.getenv("CAR_INFO_BACKLOG_DELAY_SECONDS", str(max(REQUEST_DELAY_SECONDS, 60)))))

app = FastAPI(title="Fibaro10 car.info lookup")
lock = asyncio.Lock()
worker_task: asyncio.Task | None = None
state: dict[str, Any] = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "running": False,
    "last_success_at": None,
    "last_error": None,
    "last_action": "init",
    "last_plate": None,
    "last_url": None,
    "last_result": None,
    "backoff_until": None,
    "last_candidate_count": None,
    "backlog_enabled": BACKLOG_ENABLED,
    "backlog_last_cycle_at": None,
    "backlog_last_status": None,
    "processed": 0,
    "confirmed_swedish": 0,
    "skipped": 0,
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utcnow_iso() -> str:
    return utcnow().isoformat()


def parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def load_state() -> None:
    if not STATE_PATH.exists():
        return
    try:
        stored = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return
    if isinstance(stored, dict):
        state.update(stored)


def save_state() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def set_state(**values: Any) -> None:
    state.update(values)
    save_state()


def require_token(token: str | None) -> None:
    if APP_TOKEN and token != APP_TOKEN:
        raise HTTPException(status_code=401, detail="Ugyldig car.info-token")


def fibaro_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if FIBARO10_USERNAME and FIBARO10_PASSWORD:
        headers["x-access-username"] = FIBARO10_USERNAME
        headers["x-access-password"] = FIBARO10_PASSWORD
    elif APP_TOKEN:
        headers["x-car-info-token"] = APP_TOKEN
    else:
        raise RuntimeError("Mangler FIBARO10_USERNAME/FIBARO10_PASSWORD eller CAR_INFO_APP_TOKEN")
    return headers


def fibaro_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(
        f"{FIBARO10_BASE_URL}{path}",
        params=params or {},
        headers=fibaro_headers(),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def fibaro_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"{FIBARO10_BASE_URL}{path}",
        data=json.dumps(payload),
        headers=fibaro_headers(),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def car_info_url(plate: str) -> str:
    return URL_TEMPLATE.replace("{plate}", compact_plate(plate))


def fetch_car_info(plate: str) -> tuple[int, str, dict[str, Any], str | None]:
    compact = compact_plate(plate)
    if not is_swedish_license_plate(compact):
        return 400, "", {}, "Registreringsnummer matcher ikke svensk standardformat"
    url = car_info_url(compact)
    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "sv-SE,sv;q=0.9,en-SE;q=0.8,en;q=0.7,nb;q=0.6",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
        allow_redirects=True,
    )
    html_text = response.text or ""
    if looks_rate_limited(response.status_code, html_text):
        return 429, response.url, {"rate_limit": True, "headers": dict(response.headers)}, "car.info rate-limit/coffee break"
    if response.status_code == 404:
        return 404, response.url, {}, "Ikke funnet hos car.info"
    if response.status_code >= 400:
        return response.status_code, response.url, {}, f"HTTP {response.status_code}"
    parsed = parse_car_info_html(compact, response.url, html_text, text_limit=TEXT_LIMIT)
    if not parsed.get("confirmed_swedish"):
        return 204, response.url, parsed, "Fant side, men kunne ikke bekrefte svensk bil"
    return 200, response.url, parsed, None


def backoff_active() -> str | None:
    until = parse_iso(state.get("backoff_until"))
    if until and until > utcnow():
        return until.isoformat()
    return None


async def run_once(limit: int = BATCH_SIZE, force: bool = False) -> dict[str, Any]:
    if lock.locked():
        return {"status": "busy", "message": "Car.info-oppslag kjører allerede"}
    async with lock:
        if not force:
            until = backoff_active()
            if until:
                return {"status": "backoff", "message": f"Venter på car.info-rate-limit til {until}", "backoff_until": until}

        started = time.monotonic()
        set_state(running=True, last_action="fetch_candidates", last_error=None)
        processed = confirmed = skipped = failed = 0
        results: list[dict[str, Any]] = []
        try:
            candidates = await asyncio.to_thread(
                fibaro_get,
                "/api/parkering/kjoretoy/car-info-kandidater",
                {"limit": max(1, min(10, limit))},
            )
            rows = candidates.get("rows") or []
            set_state(last_candidate_count=candidates.get("count"))
            for index, row in enumerate(rows):
                plate = compact_plate(row.get("plate"))
                if not is_swedish_license_plate(plate):
                    skipped += 1
                    results.append({"plate": plate, "status": "skipped", "message": "Ikke svensk format"})
                    continue
                set_state(last_action="fetch_car_info", last_plate=plate, last_url=car_info_url(plate))
                status_code, url, data, error = await asyncio.to_thread(fetch_car_info, plate)
                payload = {"status": status_code, "url": url, "error": error, "data": data}
                post_result = await asyncio.to_thread(fibaro_post, f"/api/parkering/kjoretoy/{plate}/car-info", payload)
                processed += 1
                if status_code == 200 and data.get("confirmed_swedish"):
                    confirmed += 1
                elif status_code >= 400:
                    failed += 1
                result = {
                    "plate": plate,
                    "status": status_code,
                    "url": url,
                    "confirmed_swedish": bool(data.get("confirmed_swedish")),
                    "error": error,
                    "fibaro10": post_result,
                }
                results.append(result)
                set_state(last_result=result)
                if status_code == 429:
                    until = utcnow() + timedelta(minutes=RATE_LIMIT_BACKOFF_MINUTES)
                    set_state(backoff_until=until.isoformat(), last_error=error)
                    break
                if REQUEST_DELAY_SECONDS and index < len(rows) - 1:
                    await asyncio.sleep(REQUEST_DELAY_SECONDS)

            set_state(
                running=False,
                last_action="idle",
                last_success_at=utcnow_iso() if failed == 0 else state.get("last_success_at"),
                processed=int(state.get("processed") or 0) + processed,
                confirmed_swedish=int(state.get("confirmed_swedish") or 0) + confirmed,
                skipped=int(state.get("skipped") or 0) + skipped,
            )
            return {
                "status": "ok",
                "candidate_count": candidates.get("count"),
                "processed": processed,
                "confirmed_swedish": confirmed,
                "skipped": skipped,
                "failed": failed,
                "rate_limited": any(item.get("status") == 429 for item in results),
                "duration_seconds": round(time.monotonic() - started, 2),
                "results": results,
            }
        except Exception as exc:
            set_state(running=False, last_action="error", last_error=str(exc))
            return {"status": "error", "message": str(exc), "results": results}


async def run_backlog_cycle(max_items: int = BACKLOG_MAX_PER_CYCLE, force: bool = False) -> dict[str, Any]:
    started = time.monotonic()
    max_items = max(1, min(100, max_items))
    total_processed = 0
    total_confirmed = 0
    total_skipped = 0
    total_failed = 0
    results: list[dict[str, Any]] = []
    status = "ok"
    message = None
    candidate_count = None

    set_state(backlog_last_cycle_at=utcnow_iso(), backlog_last_status="running")
    while total_processed < max_items:
        if not force:
            until = backoff_active()
            if until:
                status = "backoff"
                message = f"Venter paa car.info-rate-limit til {until}"
                break

        result = await run_once(1, force=force)
        status = result.get("status") or status
        candidate_count = result.get("candidate_count", candidate_count)
        results.extend(result.get("results") or [])
        total_processed += int(result.get("processed") or 0)
        total_confirmed += int(result.get("confirmed_swedish") or 0)
        total_skipped += int(result.get("skipped") or 0)
        total_failed += int(result.get("failed") or 0)

        if result.get("status") in {"busy", "error", "backoff"}:
            message = result.get("message")
            break
        if result.get("rate_limited"):
            status = "backoff"
            message = result.get("message") or "car.info rate-limit/coffee break"
            break
        if int(result.get("processed") or 0) == 0:
            status = "complete" if not candidate_count else "idle"
            message = "Ingen flere kandidater akkurat naa." if candidate_count else "Koeen er tom."
            break
        if BACKLOG_DELAY_SECONDS and total_processed < max_items:
            await asyncio.sleep(BACKLOG_DELAY_SECONDS)

    payload = {
        "status": status,
        "message": message,
        "candidate_count": candidate_count,
        "processed": total_processed,
        "confirmed_swedish": total_confirmed,
        "skipped": total_skipped,
        "failed": total_failed,
        "duration_seconds": round(time.monotonic() - started, 2),
        "backoff_until": backoff_active(),
        "results": results,
    }
    set_state(
        backlog_last_cycle_at=utcnow_iso(),
        backlog_last_status=status,
        last_candidate_count=candidate_count,
        last_error=message if status in {"backoff", "error"} else None,
    )
    return payload


async def scheduler_loop() -> None:
    await asyncio.sleep(5 if RUN_ON_START else RUN_INTERVAL_MINUTES * 60)
    while True:
        try:
            if BACKLOG_ENABLED:
                await run_backlog_cycle(BACKLOG_MAX_PER_CYCLE)
            else:
                await run_once(BATCH_SIZE)
        except Exception as exc:
            set_state(running=False, last_action="scheduler_error", last_error=str(exc))
        until = parse_iso(backoff_active())
        if until:
            sleep_seconds = max(60, min(RUN_INTERVAL_MINUTES * 60, int((until - utcnow()).total_seconds())))
        else:
            sleep_seconds = RUN_INTERVAL_MINUTES * 60
        await asyncio.sleep(sleep_seconds)


@app.on_event("startup")
async def startup() -> None:
    global worker_task
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    load_state()
    if worker_task is None:
        worker_task = asyncio.create_task(scheduler_loop())


@app.get("/")
async def index() -> dict[str, Any]:
    return await health()


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "car_info_lookup",
        "state": state,
        "config": {
            "fibaro10_base_url": FIBARO10_BASE_URL,
            "url_template": URL_TEMPLATE,
            "run_interval_minutes": RUN_INTERVAL_MINUTES,
            "batch_size": BATCH_SIZE,
            "rate_limit_backoff_minutes": RATE_LIMIT_BACKOFF_MINUTES,
            "backlog_enabled": BACKLOG_ENABLED,
            "backlog_max_per_cycle": BACKLOG_MAX_PER_CYCLE,
            "backlog_delay_seconds": BACKLOG_DELAY_SECONDS,
        },
    }


@app.post("/api/run-once")
async def api_run_once(
    request: Request,
    limit: int = Query(BATCH_SIZE, ge=1, le=5),
    force: bool = Query(False),
    x_car_info_token: str | None = Header(None),
) -> dict[str, Any]:
    require_token(x_car_info_token)
    return await run_once(limit, force)


@app.post("/api/run-backlog")
async def api_run_backlog(
    request: Request,
    max_items: int = Query(BACKLOG_MAX_PER_CYCLE, ge=1, le=100),
    force: bool = Query(False),
    x_car_info_token: str | None = Header(None),
) -> dict[str, Any]:
    require_token(x_car_info_token)
    return await run_backlog_cycle(max_items, force)


@app.get("/api/svensk-skilt/{plate}")
async def api_swedish_plate_check(plate: str) -> dict[str, Any]:
    compact = compact_plate(plate)
    return {"plate": compact, "is_swedish_standard": is_swedish_license_plate(compact)}
