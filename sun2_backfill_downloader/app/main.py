from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from playwright.sync_api import TimeoutError as PwTimeoutError
from playwright.sync_api import sync_playwright

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


load_dotenv()


def env_value(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or os.getenv(name.lower()) or default


def timezone_name() -> str:
    value = env_value("TZ", "Europe/Oslo") or "Europe/Oslo"
    if value.lower() == "europe/oslo":
        return "Europe/Oslo"
    return value


FILENAME_PREFIX = "Statistics_room"
EXPORT_URL = env_value("EXPORT_URL", "https://sun2owner.repayal.com/php/export/statistics_beds.php")
OUT_DIR = Path(env_value("OUT_DIR", "/data/backfill_raw") or "/data/backfill_raw")
ERROR_DIR = Path(env_value("ERROR_DIR", "/data/backfill_errors") or "/data/backfill_errors")
STATUS_FILE = Path(env_value("STATUS_FILE", "/data/backfill_status.json") or "/data/backfill_status.json")
PAUSE_SECONDS = float(env_value("PAUSE_SECONDS", "2") or "2")
SKIP_EXISTING = (env_value("SKIP_EXISTING", "1") or "1") == "1"
AUTO_START = (env_value("AUTO_START", "0") or "0") == "1"

app = FastAPI(title="Sun2_backfill_downloader")
task: asyncio.Task | None = None
stop_requested = False

state: dict[str, Any] = {
    "started_at": datetime.utcnow().isoformat(),
    "running": False,
    "stop_requested": False,
    "last_error": None,
    "last_date": None,
    "last_success_date": None,
    "last_success_at": None,
    "downloaded": 0,
    "skipped": 0,
    "failed": 0,
    "current_file": None,
    "range": {},
}


def local_today() -> date:
    if ZoneInfo is None:
        return datetime.now().date()
    try:
        return datetime.now(ZoneInfo(timezone_name())).date()
    except Exception:
        return datetime.now().date()


def env_required(name: str) -> str:
    value = (env_value(name, "") or "").strip()
    if not value:
        raise RuntimeError(f"Mangler env var: {name}")
    return value


def parse_date(value: str | None, default: date) -> date:
    if not value:
        return default
    return date.fromisoformat(value.strip())


def iter_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def filename_for(day: date) -> str:
    d = day.isoformat()
    return f"{FILENAME_PREFIX}_{d}_{d}.csv"


def export_url_for(day: date) -> str:
    d = day.isoformat()
    return f"{EXPORT_URL}?startdate={d}&enddate={d}"


def looks_like_login_html(html: str) -> bool:
    h = (html or "").lower()
    return (
        "vennligst logg inn" in h
        or 'id="login-action"' in h
        or 'id="login-form"' in h
        or ("name=\"username\"" in h and "name=\"password\"" in h)
    )


def is_html_bytes(data: bytes) -> bool:
    head = data[:900].lower()
    return b"<!doctype" in head or b"<html" in head or b"<head" in head


def load_progress() -> dict[str, Any]:
    if not STATUS_FILE.exists():
        return {}
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_progress(extra: dict[str, Any]) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {**state, **extra, "saved_at": datetime.utcnow().isoformat()}
    STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def login_if_needed(page, username: str, password: str) -> None:
    if page.locator("#password").count() == 0 and page.locator("input[type='password']").count() == 0:
        return
    state["last_error"] = None
    print("SUN2 login-side funnet, logger inn ...", flush=True)
    if page.locator("#username").count() > 0:
        page.locator("#username").fill(username)
    else:
        page.locator("input[name='username'], input[type='text'], input[type='email']").first.fill(username)

    if page.locator("#password").count() > 0:
        page.locator("#password").fill(password)
    else:
        page.locator("input[name='password'], input[type='password']").first.fill(password)

    if page.locator("#login-action").count() > 0:
        page.locator("#login-action").click()
    elif page.locator("text=Logg inn").count() > 0:
        page.locator("text=Logg inn").first.click()
    else:
        page.locator("button[type='submit'], input[type='submit']").first.click()

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PwTimeoutError:
        pass


def start_date_from_progress(config_start: date) -> date:
    progress = load_progress()
    last_success = progress.get("last_success_date")
    if not last_success:
        return config_start
    try:
        next_date = date.fromisoformat(last_success) + timedelta(days=1)
        return max(config_start, next_date)
    except ValueError:
        return config_start


def run_backfill_sync() -> None:
    global stop_requested
    try:
        username = env_required("SUN2_USERNAME")
        password = env_required("SUN2_PASSWORD")
        configured_start = parse_date(env_value("START_DATE"), date(2017, 3, 1))
        end = parse_date(env_value("END_DATE"), local_today() - timedelta(days=1))
        start = start_date_from_progress(configured_start)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        ERROR_DIR.mkdir(parents=True, exist_ok=True)
        state.update(
            {
                "running": True,
                "stop_requested": False,
                "last_error": None,
                "range": {"start": start.isoformat(), "end": end.isoformat(), "configured_start": configured_start.isoformat()},
            }
        )
        save_progress({})

        if start > end:
            state.update({"running": False, "last_error": None})
            save_progress({"message": "Ferdig, ingen datoer igjen"})
            return

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(locale="nb-NO", accept_downloads=True)
            page = context.new_page()

            page.goto(export_url_for(start), wait_until="domcontentloaded")
            login_if_needed(page, username, password)
            if looks_like_login_html(page.content()):
                raise RuntimeError("Etter login havnet vi fortsatt på login-side")

            for day in iter_dates(start, end):
                if stop_requested:
                    state["stop_requested"] = True
                    break
                filename = filename_for(day)
                out_path = OUT_DIR / filename
                state["last_date"] = day.isoformat()
                state["current_file"] = filename
                if SKIP_EXISTING and out_path.exists():
                    state["skipped"] += 1
                    state["last_success_date"] = day.isoformat()
                    save_progress({"last_action": "skipped_existing"})
                    continue

                try:
                    response = context.request.get(export_url_for(day), max_redirects=10, timeout=30000)
                    data = response.body()
                    if response.status != 200:
                        (ERROR_DIR / f"HTTP_{response.status}_{filename}.html").write_bytes(data)
                        raise RuntimeError(f"HTTP {response.status}")
                    if is_html_bytes(data):
                        (ERROR_DIR / f"HTML_{filename}.html").write_bytes(data)
                        raise RuntimeError("Fikk HTML i stedet for CSV")
                    tmp_path = out_path.with_suffix(".csv.tmp")
                    tmp_path.write_bytes(data)
                    tmp_path.replace(out_path)
                    state["downloaded"] += 1
                    state["last_success_date"] = day.isoformat()
                    state["last_success_at"] = datetime.utcnow().isoformat()
                    state["last_error"] = None
                    save_progress({"last_action": "downloaded"})
                except Exception as exc:
                    state["failed"] += 1
                    state["last_error"] = f"{day.isoformat()}: {exc}"
                    save_progress({"last_action": "failed"})

                if PAUSE_SECONDS > 0:
                    time.sleep(PAUSE_SECONDS)

            context.close()
            browser.close()
    except Exception as exc:
        state["last_error"] = str(exc)
        save_progress({"last_action": "fatal_error"})
    finally:
        state["running"] = False
        state["current_file"] = None
        save_progress({"last_action": "stopped" if stop_requested else "finished"})
        stop_requested = False


async def ensure_task_started() -> bool:
    global task, stop_requested
    if task and not task.done():
        return False
    stop_requested = False
    task = asyncio.create_task(asyncio.to_thread(run_backfill_sync))
    return True


@app.on_event("startup")
async def startup() -> None:
    progress = load_progress()
    if progress:
        state.update({key: value for key, value in progress.items() if key in state})
    if AUTO_START:
        await ensure_task_started()


@app.get("/", response_class=HTMLResponse)
async def index():
    status_class = "ok" if not state.get("last_error") else "bad"
    html = f"""
<!doctype html>
<html lang="no">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sun2 backfill</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#eef2f6;color:#17202a}}
main{{max-width:980px;margin:0 auto;padding:1rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.7rem}}
.card{{background:white;border:1px solid #d8dee4;border-radius:10px;padding:1rem;margin:.75rem 0;box-shadow:0 2px 10px rgba(0,0,0,.06)}}
.metric{{background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;padding:.75rem}}
.metric span{{display:block;color:#667085;font-size:.78rem}}
.metric strong{{display:block;margin-top:.2rem;font-size:1.05rem}}
.ok{{color:#16803c;font-weight:750}}.bad{{color:#b42318;font-weight:750}}
button{{border:0;border-radius:8px;background:#4b86c2;color:white;padding:.65rem .9rem;font-weight:750;margin-right:.4rem}}
.stop{{background:#b42318}} pre{{white-space:pre-wrap;background:#0f172a;color:#e5e7eb;border-radius:8px;padding:.75rem;overflow:auto}}
</style></head>
<body><main>
<h1>Sun2 backfill</h1>
<section class="card grid">
<div class="metric"><span>Status</span><strong class="{status_class}">{'Kjører' if state.get('running') else ('Feil' if state.get('last_error') else 'Klar')}</strong></div>
<div class="metric"><span>Sist dato</span><strong>{state.get('last_date') or '-'}</strong></div>
<div class="metric"><span>Sist OK</span><strong>{state.get('last_success_date') or '-'}</strong></div>
<div class="metric"><span>Lastet ned</span><strong>{state.get('downloaded', 0)}</strong></div>
<div class="metric"><span>Hoppet over</span><strong>{state.get('skipped', 0)}</strong></div>
<div class="metric"><span>Feil</span><strong>{state.get('failed', 0)}</strong></div>
</section>
<section class="card">
<form method="post" action="/start" style="display:inline"><button type="submit">Start</button></form>
<form method="post" action="/stop" style="display:inline"><button class="stop" type="submit">Stopp</button></form>
</section>
<section class="card"><pre>{json.dumps(state, ensure_ascii=False, indent=2)}</pre></section>
</main></body></html>
"""
    return HTMLResponse(html)


@app.post("/start")
async def start():
    started = await ensure_task_started()
    if not started:
        return RedirectResponse("/", status_code=303)
    return RedirectResponse("/", status_code=303)


@app.post("/stop")
async def stop():
    global stop_requested
    stop_requested = True
    state["stop_requested"] = True
    return RedirectResponse("/", status_code=303)


@app.get("/json")
async def json_status():
    return JSONResponse(state)
