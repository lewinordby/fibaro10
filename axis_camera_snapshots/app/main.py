from __future__ import annotations

import asyncio
import html
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response

load_dotenv()

logger = logging.getLogger("axis_camera_snapshots")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

LOCAL_TZ = ZoneInfo("Europe/Oslo")
DATA_DIR = Path(os.getenv("AXIS_DATA_DIR", "/data"))
SNAPSHOT_ROOT = Path(os.getenv("AXIS_SNAPSHOT_DIR", str(DATA_DIR / "snapshots")))
CONFIG_FILE = Path(os.getenv("AXIS_CONFIG_FILE", str(DATA_DIR / "config.json")))
STATE_FILE = Path(os.getenv("AXIS_STATE_FILE", str(DATA_DIR / "state.json")))

app = FastAPI(title="Axis camera snapshots")
capture_task: asyncio.Task | None = None
capture_lock = asyncio.Lock()


@dataclass
class AxisConfig:
    enabled: bool
    camera_ip: str
    username: str
    password: str
    snapshot_url: str
    interval_seconds: int
    retention_days: int
    auth_mode: str
    timeout_seconds: float


def env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "ja", "on"}


def default_config() -> AxisConfig:
    camera_ip = os.getenv("AXIS_CAMERA_IP", "").strip()
    snapshot_url = os.getenv("AXIS_SNAPSHOT_URL", "").strip()
    if not snapshot_url and camera_ip:
        snapshot_url = f"http://{camera_ip}/axis-cgi/jpg/image.cgi"
    return AxisConfig(
        enabled=env_bool("AXIS_SNAPSHOT_ENABLED", "false"),
        camera_ip=camera_ip,
        username=os.getenv("AXIS_USERNAME", "").strip(),
        password=os.getenv("AXIS_PASSWORD", ""),
        snapshot_url=snapshot_url,
        interval_seconds=max(1, int(os.getenv("AXIS_INTERVAL_SECONDS", "10"))),
        retention_days=max(1, int(os.getenv("AXIS_RETENTION_DAYS", "7"))),
        auth_mode=os.getenv("AXIS_AUTH_MODE", "auto").strip().lower(),
        timeout_seconds=max(1.0, float(os.getenv("AXIS_TIMEOUT_SECONDS", "8"))),
    )


def load_config() -> AxisConfig:
    config = default_config()
    if CONFIG_FILE.exists():
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        merged = {**asdict(config), **data}
        config = AxisConfig(**merged)
    if config.camera_ip and not config.snapshot_url:
        config.snapshot_url = f"http://{config.camera_ip}/axis-cgi/jpg/image.cgi"
    return config


def save_config(config: AxisConfig) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Could not read state file")
    return {
        "started_at": datetime.now(LOCAL_TZ).isoformat(),
        "last_success_at": None,
        "last_error_at": None,
        "last_error": None,
        "last_file": None,
        "captures_total": 0,
        "errors_total": 0,
    }


def save_state(**updates: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    state.update(updates)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def snapshot_path(ts: datetime) -> Path:
    day_dir = SNAPSHOT_ROOT / ts.strftime("%Y-%m-%d")
    return day_dir / f"axis_{ts.strftime('%Y-%m-%d_%H-%M-%S')}.jpg"


def latest_snapshot_file() -> Path | None:
    state_file = load_state().get("last_file")
    candidates: list[Path] = []
    if state_file:
        candidates.append(Path(str(state_file)))
    if SNAPSHOT_ROOT.exists():
        candidates.extend(SNAPSHOT_ROOT.rglob("*.jpg"))

    root = SNAPSHOT_ROOT.resolve()
    existing: list[Path] = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            resolved.relative_to(root)
            if resolved.is_file():
                existing.append(resolved)
        except (OSError, ValueError):
            continue
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


async def fetch_snapshot(config: AxisConfig) -> bytes:
    if not config.snapshot_url:
        raise RuntimeError("Snapshot URL mangler.")
    if not config.username or not config.password:
        raise RuntimeError("Axis brukernavn/passord mangler.")

    if config.auth_mode == "digest":
        auth: httpx.Auth | tuple[str, str] = httpx.DigestAuth(config.username, config.password)
    else:
        auth = (config.username, config.password)

    async with httpx.AsyncClient(timeout=config.timeout_seconds, follow_redirects=True) as client:
        response = await client.get(config.snapshot_url, auth=auth)
        if response.status_code == 401 and config.auth_mode == "auto":
            response = await client.get(
                config.snapshot_url,
                auth=httpx.DigestAuth(config.username, config.password),
            )
        response.raise_for_status()
        content = response.content

    if not content.startswith(b"\xff\xd8"):
        raise RuntimeError(f"Kamerasvaret var ikke JPEG. Content-Type: {response.headers.get('content-type', '-')}")
    return content


async def capture_once() -> Path:
    async with capture_lock:
        config = load_config()
        if not config.enabled:
            raise RuntimeError("Snapshot-jobben er deaktivert.")
        image = await fetch_snapshot(config)
        ts = now_local()
        target = snapshot_path(ts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(image)
        state = load_state()
        save_state(
            last_success_at=ts.isoformat(),
            last_error=None,
            last_file=str(target),
            captures_total=int(state.get("captures_total") or 0) + 1,
        )
        logger.info("Saved Axis snapshot: %s (%s bytes)", target, len(image))
        delete_old_snapshots(config.retention_days)
        return target


def delete_old_snapshots(retention_days: int) -> int:
    cutoff = now_local() - timedelta(days=max(1, retention_days))
    deleted = 0
    if not SNAPSHOT_ROOT.exists():
        return 0
    for path in SNAPSHOT_ROOT.rglob("*.jpg"):
        try:
            if datetime.fromtimestamp(path.stat().st_mtime, LOCAL_TZ) < cutoff:
                path.unlink()
                deleted += 1
        except Exception:
            logger.exception("Could not delete old snapshot: %s", path)
    if deleted:
        logger.info("Deleted %s old Axis snapshots", deleted)
    return deleted


async def capture_loop() -> None:
    while True:
        config = load_config()
        if config.enabled:
            try:
                await capture_once()
            except Exception as exc:
                state = load_state()
                save_state(
                    last_error_at=now_local().isoformat(),
                    last_error=str(exc),
                    errors_total=int(state.get("errors_total") or 0) + 1,
                )
                logger.warning("Axis snapshot failed: %s", exc)
        await asyncio.sleep(max(1, config.interval_seconds))


def page(content: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="no"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Axis snapshots</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#f5f7fb;color:#26323f}}
main{{width:min(100% - 1.4rem,920px);margin:0 auto;padding:1rem 0 2rem}}
.panel{{background:white;border:1px solid #dbe3ec;border-radius:10px;padding:1rem;margin:.8rem 0;box-shadow:0 1px 3px #0001}}
.grid{{display:grid;gap:.65rem}}@media(min-width:760px){{.grid{{grid-template-columns:repeat(3,1fr)}}}}
.metric{{background:#f9fbfe;border:1px solid #edf1f6;border-radius:8px;padding:.7rem}}.metric span{{display:block;color:#64748b;font-size:.82rem}}
label{{display:grid;gap:.25rem;font-weight:700}}input,select{{padding:.55rem;border:1px solid #dbe3ec;border-radius:7px}}
button,.button{{display:inline-flex;border:1px solid #acd8e1;background:#e7f5f8;color:#176579;border-radius:7px;padding:.55rem .8rem;text-decoration:none;font-weight:700;cursor:pointer}}
.preview{{display:grid;gap:.65rem}}.preview img{{width:100%;max-height:70vh;object-fit:contain;background:#111827;border-radius:8px}}
.muted{{color:#64748b}}
code{{overflow-wrap:anywhere}}
</style></head><body><main><h1>Axis snapshots</h1>{content}</main></body></html>"""
    )


@app.on_event("startup")
async def startup() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        save_config(default_config())
    global capture_task
    capture_task = asyncio.create_task(capture_loop())


@app.get("/health")
async def health() -> dict[str, Any]:
    config = load_config()
    state = load_state()
    return {
        "ok": True,
        "enabled": config.enabled,
        "last_success_at": state.get("last_success_at"),
        "last_error": state.get("last_error"),
    }


@app.get("/api/status")
async def status() -> dict[str, Any]:
    config = asdict(load_config())
    config["password"] = "********" if config.get("password") else ""
    latest = latest_snapshot_file()
    return {
        "config": config,
        "state": load_state(),
        "snapshot_root": str(SNAPSHOT_ROOT),
        "latest_snapshot": str(latest) if latest else None,
    }


@app.get("/latest.jpg")
async def latest_jpg() -> FileResponse:
    latest = latest_snapshot_file()
    if latest is None:
        raise HTTPException(status_code=404, detail="Ingen snapshots funnet.")
    return FileResponse(
        latest,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store, max-age=0"},
        filename=latest.name,
    )


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    config = load_config()
    state = load_state()
    latest = latest_snapshot_file()
    latest_image = ""
    if latest:
        latest_mtime = int(latest.stat().st_mtime)
        latest_image = (
            f"""<section class="panel preview"><h2>Siste bilde</h2>
<img src="/latest.jpg?v={latest_mtime}" alt="Siste Axis snapshot">
<p class="muted">{html.escape(latest.name)}</p></section>"""
        )
    else:
        latest_image = """<section class="panel"><h2>Siste bilde</h2><p class="muted">Ingen bilder lagret ennå.</p></section>"""
    return page(
        f"""
<section class="panel"><div class="grid">
<div class="metric"><span>Aktiv</span><strong>{"Ja" if config.enabled else "Nei"}</strong></div>
<div class="metric"><span>Sist lagret</span><strong>{html.escape(str(state.get("last_success_at") or "-"))}</strong></div>
<div class="metric"><span>Antall bilder</span><strong>{state.get("captures_total", 0)}</strong></div>
</div><p>Siste feil: <code>{html.escape(str(state.get("last_error") or "-"))}</code></p>
<p>Siste fil: <code>{html.escape(str(state.get("last_file") or "-"))}</code></p></section>
{latest_image}
<section class="panel"><h2>Innstillinger</h2>
<form action="/settings" method="post" class="grid">
<label>Aktiv<select name="enabled"><option value="true" {"selected" if config.enabled else ""}>Ja</option><option value="false" {"" if config.enabled else "selected"}>Nei</option></select></label>
<label>Kamera-IP<input name="camera_ip" value="{html.escape(config.camera_ip)}"></label>
<label>Snapshot URL<input name="snapshot_url" value="{html.escape(config.snapshot_url)}"></label>
<label>Brukernavn<input name="username" value="{html.escape(config.username)}"></label>
<label>Passord<input name="password" type="password" placeholder="Uendret hvis tomt"></label>
<label>Intervall sekunder<input name="interval_seconds" type="number" min="1" value="{config.interval_seconds}"></label>
<label>Retention dager<input name="retention_days" type="number" min="1" value="{config.retention_days}"></label>
<label>Auth<select name="auth_mode">
<option value="auto" {"selected" if config.auth_mode == "auto" else ""}>Auto</option>
<option value="basic" {"selected" if config.auth_mode == "basic" else ""}>Basic</option>
<option value="digest" {"selected" if config.auth_mode == "digest" else ""}>Digest</option>
</select></label>
<label>Timeout sekunder<input name="timeout_seconds" type="number" min="1" step="0.5" value="{config.timeout_seconds}"></label>
<div><button>Lagre</button></div>
</form></section>
<section class="panel"><p><a class="button" href="/capture-now">Hent bilde nå</a> <a class="button" href="/api/status">JSON status</a></p></section>
"""
    )


@app.post("/settings")
async def save_settings(
    enabled: str = Form(...),
    camera_ip: str = Form(""),
    snapshot_url: str = Form(""),
    username: str = Form(""),
    password: str = Form(""),
    interval_seconds: int = Form(10),
    retention_days: int = Form(7),
    auth_mode: str = Form("auto"),
    timeout_seconds: float = Form(8.0),
) -> RedirectResponse:
    current = load_config()
    camera_ip = camera_ip.strip()
    snapshot_url = snapshot_url.strip() or (f"http://{camera_ip}/axis-cgi/jpg/image.cgi" if camera_ip else "")
    save_config(
        AxisConfig(
            enabled=enabled.lower() in {"1", "true", "yes", "ja", "on"},
            camera_ip=camera_ip,
            username=username.strip(),
            password=password if password else current.password,
            snapshot_url=snapshot_url,
            interval_seconds=max(1, interval_seconds),
            retention_days=max(1, retention_days),
            auth_mode=auth_mode if auth_mode in {"auto", "basic", "digest"} else "auto",
            timeout_seconds=max(1.0, timeout_seconds),
        )
    )
    return RedirectResponse("/", status_code=303)


@app.get("/capture-now")
async def capture_now() -> RedirectResponse:
    try:
        await capture_once()
    except Exception as exc:
        state = load_state()
        save_state(
            last_error_at=now_local().isoformat(),
            last_error=str(exc),
            errors_total=int(state.get("errors_total") or 0) + 1,
        )
    return RedirectResponse("/", status_code=303)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)
