from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import urllib.error
import urllib.request
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .upstream import DreameCredentials, DreameUpstream
from .water_interlock import ACTIVE_SCHEDULE_STATES, active_schedule_rows, clear_water_state, interlock_label


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
LOGGER = logging.getLogger("dreame_logger")

DATA_DIR = Path(os.getenv("DREAME_DATA_DIR", "/data"))
BUILD_FILE = Path(__file__).resolve().parents[1] / "BUILD"
STATE_FILE = DATA_DIR / "state.json"
QUEUE_FILE = DATA_DIR / "pending_batches.jsonl"
LOCAL_TIMEZONE = os.getenv("LOCAL_TIMEZONE", "Europe/Oslo")
LOCAL_TZ = ZoneInfo(LOCAL_TIMEZONE)
SYNC_INTERVAL_SECONDS = max(60, int(os.getenv("DREAME_SYNC_INTERVAL_SECONDS", "300")))
FIBARO10_API_BASE_URL = os.getenv("FIBARO10_API_BASE_URL", "http://fibaro10:8110").rstrip("/")
FIBARO10_API_USERNAME = os.getenv("FIBARO10_API_USERNAME", "")
FIBARO10_API_PASSWORD = os.getenv("FIBARO10_API_PASSWORD", "")
DREAME_USERNAME = os.getenv("DREAME_USERNAME", "").strip()
DREAME_PASSWORD = os.getenv("DREAME_PASSWORD", "")
DREAME_COUNTRY = os.getenv("DREAME_COUNTRY", "eu").strip().lower()
DREAME_ACCOUNT_TYPE = os.getenv("DREAME_ACCOUNT_TYPE", "dreame").strip().lower()
DREAME_CONTROL_TOKEN = os.getenv("DREAME_CONTROL_TOKEN", "").strip()
DREAME_WATER_INTERLOCK_ENABLED = os.getenv("DREAME_WATER_INTERLOCK_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
EXPECTED_ROBOT_NAME = os.getenv("DREAME_EXPECTED_ROBOT_NAME", "Aqua10").strip() or "Aqua10"
COLLECTOR_ID = os.getenv("COLLECTOR_ID", "dreame_logger")
APP_BUILD = BUILD_FILE.read_text(encoding="utf-8").strip() if BUILD_FILE.exists() else "dev"


def local_now() -> datetime:
    return datetime.now(LOCAL_TZ).replace(microsecond=0)


def load_state() -> dict[str, Any]:
    defaults = {
        "configured": bool(DREAME_USERNAME and DREAME_PASSWORD),
        "last_sync": None,
        "last_success": None,
        "last_error": None,
        "robots": [],
        "pending_batches": 0,
        "water_interlocks": {},
    }
    if not STATE_FILE.exists():
        return defaults
    try:
        stored = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    return {**defaults, **stored, "configured": bool(DREAME_USERNAME and DREAME_PASSWORD)}


def save_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATE_FILE)


def api_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "User-Agent": "dreame_logger/1"}
    if FIBARO10_API_USERNAME:
        headers["x-access-username"] = FIBARO10_API_USERNAME
    if FIBARO10_API_PASSWORD:
        headers["x-access-password"] = FIBARO10_API_PASSWORD
    return headers


def post_json(path: str, payload: dict[str, Any], timeout: int = 45) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{FIBARO10_API_BASE_URL}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=api_headers(),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8") or "{}")


def queue_batch(payload: dict[str, Any], path: str = "/api/renhold/ingest") -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with QUEUE_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps({"path": path, "payload": payload}, ensure_ascii=False, separators=(",", ":")) + "\n")


def pending_count() -> int:
    if not QUEUE_FILE.exists():
        return 0
    with QUEUE_FILE.open("r", encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())


def flush_queue() -> int:
    if not QUEUE_FILE.exists():
        return 0
    lines = [line for line in QUEUE_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    remaining: list[str] = []
    sent = 0
    for index, line in enumerate(lines):
        try:
            queued = json.loads(line)
            if isinstance(queued, dict) and isinstance(queued.get("payload"), dict):
                post_json(str(queued.get("path") or "/api/renhold/ingest"), queued["payload"])
            else:
                post_json("/api/renhold/ingest", queued)
            sent += 1
        except Exception:
            remaining = lines[index:]
            break
    temp = QUEUE_FILE.with_suffix(".tmp")
    temp.write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")
    temp.replace(QUEUE_FILE)
    return sent


def summarized_robot(snapshot: dict[str, Any]) -> dict[str, Any]:
    status = snapshot.get("status") or {}
    return {
        "external_id": snapshot.get("external_id"),
        "name": snapshot.get("name"),
        "model": snapshot.get("model"),
        "state": status.get("state_name") or "Ingen status",
        "battery": status.get("battery"),
        "online": (snapshot.get("metadata") or {}).get("online"),
        "error": snapshot.get("last_error"),
        "water_interlock": (snapshot.get("telemetry") or {}).get("water_interlock"),
    }


def public_water_interlock(entry: dict[str, Any]) -> dict[str, Any]:
    paused = entry.get("paused_schedules") if isinstance(entry.get("paused_schedules"), list) else []
    status = str(entry.get("status") or "ready")
    return {
        "enabled": DREAME_WATER_INTERLOCK_ENABLED,
        "status": status,
        "label": interlock_label(status, len(paused)),
        "water_status": entry.get("water_status"),
        "checked_at": entry.get("checked_at"),
        "blocked_at": entry.get("blocked_at"),
        "restored_at": entry.get("restored_at"),
        "paused_count": len(paused),
        "paused_schedules": paused,
        "last_action": entry.get("last_action"),
        "last_error": entry.get("last_error"),
    }


async def reconcile_water_interlock(snapshot: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    external_id = str(snapshot.get("external_id") or "")
    now = local_now().isoformat()
    interlocks = state.setdefault("water_interlocks", {})
    entry = interlocks.setdefault(external_id, {"paused_schedules": []})
    telemetry = snapshot.get("telemetry") if isinstance(snapshot.get("telemetry"), dict) else {}
    water_status = clear_water_state(telemetry)
    entry.update({"checked_at": now, "water_status": water_status})

    if not DREAME_WATER_INTERLOCK_ENABLED:
        entry.update({"status": "disabled", "last_error": None})
        return public_water_interlock(entry)
    if water_status == "unknown":
        entry.update({"status": "blocked" if entry.get("paused_schedules") else "unsupported", "last_error": None})
        return public_water_interlock(entry)

    schedules = snapshot.get("schedules") if isinstance(snapshot.get("schedules"), list) else []
    schedules_by_id = {
        str(row.get("id") or row.get("schedule_id")): row
        for row in schedules
        if isinstance(row, dict) and (row.get("id") or row.get("schedule_id"))
    }
    paused = {
        str(row.get("schedule_id")): row
        for row in (entry.get("paused_schedules") or [])
        if isinstance(row, dict) and row.get("schedule_id")
    }

    if water_status == "empty":
        candidates = {row["schedule_id"]: row for row in active_schedule_rows(schedules)}
        if candidates:
            result = await asyncio.to_thread(
                get_upstream().set_schedule_states,
                external_id,
                {schedule_id: "0" for schedule_id in candidates},
            )
            verified = result.get("verified") or {}
            before = result.get("before") or {}
            for schedule_id, row in candidates.items():
                if verified.get(schedule_id) == "0":
                    previous_state = str(before.get(schedule_id) or paused.get(schedule_id, {}).get("previous_state") or "1")
                    paused[schedule_id] = {
                        **row,
                        "previous_state": previous_state if previous_state in ACTIVE_SCHEDULE_STATES else "1",
                        "paused_at": paused.get(schedule_id, {}).get("paused_at") or now,
                    }
                    schedules_by_id[schedule_id]["enabled"] = False
            entry["last_action"] = {
                "action": "pause",
                "at": now,
                "count": sum(verified.get(schedule_id) == "0" for schedule_id in candidates),
                "requested": len(candidates),
            }
            entry["last_error"] = None if result.get("ok") else json.dumps(result.get("failed"), ensure_ascii=False)
        else:
            entry["last_error"] = None
        entry["paused_schedules"] = list(paused.values())
        entry["blocked_at"] = entry.get("blocked_at") or now
        entry["status"] = "error" if entry.get("last_error") else "blocked"
        return public_water_interlock(entry)

    restorable = {
        schedule_id: row
        for schedule_id, row in paused.items()
        if schedule_id in schedules_by_id
    }
    if restorable:
        requested = {
            schedule_id: str(row.get("previous_state") or "1")
            for schedule_id, row in restorable.items()
        }
        result = await asyncio.to_thread(get_upstream().set_schedule_states, external_id, requested)
        verified = result.get("verified") or {}
        restored_ids = {schedule_id for schedule_id, target in requested.items() if verified.get(schedule_id) == target}
        for schedule_id in restored_ids:
            schedules_by_id[schedule_id]["enabled"] = True
        paused = {
            schedule_id: row
            for schedule_id, row in paused.items()
            if schedule_id not in restored_ids and schedule_id in schedules_by_id
        }
        entry["last_action"] = {
            "action": "restore",
            "at": now,
            "count": len(restored_ids),
            "requested": len(restorable),
        }
        entry["last_error"] = None if result.get("ok") else json.dumps(result.get("failed"), ensure_ascii=False)
    else:
        paused = {schedule_id: row for schedule_id, row in paused.items() if schedule_id in schedules_by_id}
        entry["last_error"] = None
    entry["paused_schedules"] = list(paused.values())
    if not paused:
        entry["restored_at"] = now if entry.get("blocked_at") else entry.get("restored_at")
        entry["blocked_at"] = None
    entry["status"] = "error" if entry.get("last_error") else ("blocked" if paused else "ready")
    return public_water_interlock(entry)


upstream: DreameUpstream | None = None
sync_lock = asyncio.Lock()


def get_upstream() -> DreameUpstream:
    global upstream
    if not DREAME_USERNAME or not DREAME_PASSWORD:
        raise RuntimeError("Dreamehome-konto er ikke konfigurert")
    if upstream is None:
        upstream = DreameUpstream(
            DreameCredentials(
                username=DREAME_USERNAME,
                password=DREAME_PASSWORD,
                country=DREAME_COUNTRY,
                account_type=DREAME_ACCOUNT_TYPE,
            ),
            LOCAL_TIMEZONE,
        )
    return upstream


async def sync_once() -> dict[str, Any]:
    async with sync_lock:
        started = local_now()
        state = load_state()
        state["last_sync"] = started.isoformat()
        if not state["configured"]:
            waiting_payload = {
                "collector_id": COLLECTOR_ID,
                "source": COLLECTOR_ID,
                "timestamp": started.isoformat(),
                "ok": True,
                "message": f"{EXPECTED_ROBOT_NAME} er klargjort; venter på Dreamehome-konto",
                "robots": [],
                "extra": {"configured": False, "expected_robot": EXPECTED_ROBOT_NAME},
            }
            try:
                await asyncio.to_thread(post_json, "/api/renhold/ingest", waiting_payload)
            except Exception:
                LOGGER.warning("Could not report unconfigured Dreame state to Fibaro10", exc_info=True)
            state.update({"last_error": None, "pending_batches": pending_count()})
            save_state(state)
            return {"status": "waiting", "message": "Dreamehome-konto er ikke konfigurert", "robots": 0}
        try:
            await asyncio.to_thread(flush_queue)
            snapshots = await asyncio.to_thread(get_upstream().refresh)
            for snapshot in snapshots:
                telemetry = snapshot.get("telemetry") if isinstance(snapshot.get("telemetry"), dict) else None
                if not telemetry or not snapshot.get("external_id"):
                    continue
                try:
                    telemetry["water_interlock"] = await reconcile_water_interlock(snapshot, state)
                except Exception as exc:
                    external_id = str(snapshot.get("external_id"))
                    entry = state.setdefault("water_interlocks", {}).setdefault(external_id, {"paused_schedules": []})
                    entry.update(
                        {
                            "checked_at": local_now().isoformat(),
                            "water_status": clear_water_state(telemetry),
                            "status": "error",
                            "last_error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                    telemetry["water_interlock"] = public_water_interlock(entry)
                    LOGGER.exception("Aqua10 water interlock failed for %s", external_id)
            payload = {
                "collector_id": COLLECTOR_ID,
                "source": COLLECTOR_ID,
                "timestamp": started.isoformat(),
                "robots": snapshots,
            }
            try:
                result = await asyncio.to_thread(post_json, "/api/renhold/ingest", payload)
            except Exception:
                await asyncio.to_thread(queue_batch, payload, "/api/renhold/ingest")
                raise
            telemetry_robots = [
                {
                    "provider": "dreame",
                    "external_id": item.get("external_id"),
                    "duid": item.get("duid"),
                    "name": item.get("name"),
                    "model": item.get("model"),
                    "telemetry": item.get("telemetry"),
                }
                for item in snapshots
                if item.get("telemetry")
            ]
            if telemetry_robots:
                telemetry_payload = {
                    "collector_id": COLLECTOR_ID,
                    "source": COLLECTOR_ID,
                    "timestamp": started.isoformat(),
                    "robots": telemetry_robots,
                }
                try:
                    await asyncio.to_thread(post_json, "/api/renhold/telemetry/ingest", telemetry_payload)
                except Exception:
                    LOGGER.warning("Fibaro10 telemetry ingest failed; request queued", exc_info=True)
                    await asyncio.to_thread(queue_batch, telemetry_payload, "/api/renhold/telemetry/ingest")
            state.update(
                {
                    "last_success": local_now().isoformat(),
                    "last_error": None,
                    "robots": [summarized_robot(item) for item in snapshots],
                    "pending_batches": pending_count(),
                }
            )
            save_state(state)
            return {"status": "ok", "robots": len(snapshots), "fibaro10": result}
        except Exception as exc:
            LOGGER.exception("Dreame synchronization failed")
            state.update({"last_error": str(exc), "pending_batches": pending_count()})
            save_state(state)
            return {"status": "error", "message": str(exc), "robots": len(state.get("robots") or [])}


async def sync_loop() -> None:
    await asyncio.sleep(8)
    while True:
        await sync_once()
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    save_state(load_state())
    task = asyncio.create_task(sync_loop(), name="dreame-sync")
    try:
        yield
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        if upstream:
            await asyncio.to_thread(upstream.close)


app = FastAPI(title="Dreame_logger", lifespan=lifespan)


class ControlRequest(BaseModel):
    action: Literal["start", "resume", "pause", "stop", "dock"]
    request_id: str = Field(min_length=8, max_length=100)


def require_control_token(token: str | None) -> None:
    if not DREAME_CONTROL_TOKEN or token != DREAME_CONTROL_TOKEN:
        raise HTTPException(status_code=401, detail="Ugyldig kontrolltoken")


@app.get("/health")
async def health() -> dict[str, Any]:
    state = load_state()
    return {
        "status": "ok",
        "service": "dreame_logger",
        "build": APP_BUILD,
        "configured": state["configured"],
        "last_success": state["last_success"],
        "last_error": state["last_error"],
        "robots": len(state["robots"]),
        "pending_batches": state["pending_batches"],
    }


@app.get("/state")
async def state() -> dict[str, Any]:
    return load_state()


@app.post("/sync-now")
@app.get("/sync-now")
async def sync_now() -> dict[str, Any]:
    return await sync_once()


@app.post("/robots/{external_id}/control")
async def control_robot(
    external_id: str,
    data: ControlRequest,
    x_dreame_control_token: str | None = Header(default=None),
) -> dict[str, Any]:
    require_control_token(x_dreame_control_token)
    try:
        result = await asyncio.to_thread(get_upstream().control, external_id, data.action)
    except KeyError:
        raise HTTPException(status_code=404, detail="Dreame-roboten ble ikke funnet")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await sync_once()
    return {"status": "ok", "request_id": data.request_id, **result}


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    state = load_state()
    configured = state["configured"]
    robots = state.get("robots") or []
    expected_name = html.escape(EXPECTED_ROBOT_NAME)
    last_success = html.escape(str(state.get("last_success") or "Ikke kjørt"))
    pending_batches = int(state.get("pending_batches", 0) or 0)
    rows = "".join(
        f"<tr><td><strong>{html.escape(str(item.get('name') or '-'))}</strong><small>{html.escape(str(item.get('model') or '-'))}</small></td>"
        f"<td>{html.escape(str(item.get('state') or '-'))}</td><td>{str(item.get('battery')) + ' %' if item.get('battery') is not None else '-'}</td>"
        f"<td>{'Tilkoblet' if item.get('online') else 'Frakoblet'}</td></tr>"
        for item in robots
    ) or '<tr><td colspan="4" class="empty">Aqua10 venter på at Dreamehome-kontoen konfigureres.</td></tr>'
    status_text = "Klar for synkronisering" if configured else "Konto mangler"
    status_tone = "ok" if configured and not state.get("last_error") else "warn"
    html_document = f"""<!doctype html><html lang="no"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dreame-logger</title><style>
:root{{color-scheme:light dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif;background:#f5f7fa;color:#182230}}*{{box-sizing:border-box}}body{{margin:0}}main{{max-width:1120px;margin:auto;padding:32px 24px}}header{{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:22px}}h1{{font-size:25px;margin:0}}p{{color:#667085;margin:5px 0 0}}.badge{{border-radius:999px;padding:8px 13px;font-weight:700;font-size:13px}}.ok{{background:#dcfae6;color:#067647}}.warn{{background:#fef0c7;color:#93370d}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:18px}}.card,.panel{{background:#fff;border:1px solid #e4e7ec;border-radius:8px;box-shadow:0 1px 2px #1018280d}}.card{{padding:16px}}.card small,td small{{display:block;color:#98a2b3;margin-top:4px}}.card strong{{display:block;font-size:18px;margin-top:5px}}.panel header{{padding:15px 18px;margin:0;border-bottom:1px solid #eaecf0}}.panel h2{{font-size:16px;margin:0}}table{{border-collapse:collapse;width:100%}}th,td{{padding:13px 18px;text-align:left;border-bottom:1px solid #f0f1f3;font-size:14px}}th{{font-size:11px;text-transform:uppercase;color:#667085}}.empty{{padding:34px;text-align:center;color:#98a2b3}}.actions{{display:flex;gap:10px;margin-top:18px}}a{{color:#475467}}button{{background:#6941c6;border:0;border-radius:7px;color:#fff;font-weight:700;padding:10px 14px;cursor:pointer}}code{{font-size:12px}}@media(max-width:700px){{.grid{{grid-template-columns:1fr}}header{{align-items:flex-start;flex-direction:column}}}}
@media(prefers-color-scheme:dark){{:root{{background:#101828;color:#f2f4f7}}p{{color:#98a2b3}}.card,.panel{{background:#182230;border-color:#344054}}.panel header,th,td{{border-color:#344054}}}}
</style></head><body><main><header><div><h1>Dreame-logger</h1><p>Separat innlesing og kontroll for Dreame-robotene</p></div><span class="badge {status_tone}">{status_text}</span></header>
<section class="grid"><div class="card"><small>Forventet robot</small><strong>{expected_name}</strong><small>Dreame Aqua10</small></div><div class="card"><small>Siste vellykkede synk</small><strong>{last_success}</strong><small>Hvert {SYNC_INTERVAL_SECONDS // 60}. minutt</small></div><div class="card"><small>Lokal kø</small><strong>{pending_batches}</strong><small>Venter på Fibaro10</small></div></section>
<section class="panel"><header><h2>Oppdagede roboter</h2></header><table><thead><tr><th>Robot</th><th>Tilstand</th><th>Batteri</th><th>Cloud</th></tr></thead><tbody>{rows}</tbody></table></section>
<section class="panel" style="margin-top:18px"><header><h2>Oppsett</h2></header><div style="padding:18px"><p>Legg roboten til i Dreamehome, gi den navnet <strong>{expected_name}</strong> og sett følgende verdier i <code>dreame_logger/.env</code>: <code>DREAME_USERNAME</code>, <code>DREAME_PASSWORD</code> og <code>DREAME_COUNTRY=eu</code>.</p><p>Ingen kart behandles i denne tjenesten. Status, jobbhistorikk, planer og driftsdata sendes til Fibaro10.</p><div class="actions"><form action="/sync-now" method="post"><button>Synkroniser nå</button></form><a href="/state">Vis råstatus</a></div></div></section>
</main></body></html>"""
    return HTMLResponse(html_document)
