from __future__ import annotations

import asyncio
import csv
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse


load_dotenv()

COLLECTOR_ID = os.getenv("COLLECTOR_ID", "qnap-sun2-importer")
FIBARO10_API_BASE_URL = os.getenv("FIBARO10_API_BASE_URL", "https://fibaro10.onrender.com").rstrip("/")
FIBARO10_API_USERNAME = os.getenv("FIBARO10_API_USERNAME", "")
FIBARO10_API_PASSWORD = os.getenv("FIBARO10_API_PASSWORD", "")
IMPORT_DIR = Path(os.getenv("IMPORT_DIR", "/data/incoming"))
ARCHIVE_DIR = Path(os.getenv("ARCHIVE_DIR", "/data/archive"))
REJECTED_DIR = Path(os.getenv("REJECTED_DIR", "/data/rejected"))
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "10"))

FILENAME_RE = re.compile(r"^(?:IMPORTED_|IGNORED_|ERROR_)?Statistics_room_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.csv$")
EXPECTED_COLS = [
    "Rom",
    "Total Soletid (minutter)",
    "Totalt antall Solinger",
    "Solinger Medlemmer",
    "Solinger Ikke Medlemmer",
    "Totalt Inntjent (KR)",
    "Inntjent Medlemmer (KR)",
    "Inntjent Ikke Medlemmer (KR)",
]

app = FastAPI(title="Sun2_importer")
state: dict[str, Any] = {
    "started_at": datetime.utcnow().isoformat(),
    "last_run_at": None,
    "last_success_at": None,
    "last_error": None,
    "last_file": None,
    "last_result": None,
    "processed_files": 0,
    "rejected_files": 0,
    "running": False,
}


def decimal_value(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().strip('"')
    if not text or text.lower() == "nan":
        return None
    text = text.replace("\u00a0", "").replace(" ", "").replace(",", ".")
    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def int_value(value: Any) -> int | None:
    number = decimal_value(value)
    if number is None:
        return None
    return int(number)


def clean_text(value: Any) -> str:
    text = str(value or "").strip().strip('"')
    if "Ã" in text or "Â" in text:
        try:
            return text.encode("latin1").decode("utf-8")
        except UnicodeError:
            return text
    return text


def move_to(src: Path, dest_dir: Path, prefix: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{prefix}{src.name}"
    if dest.exists():
        stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        dest = dest_dir / f"{prefix}{stamp}_{src.name}"
    shutil.move(str(src), str(dest))
    return dest


def parse_file(file_path: Path) -> tuple[date, list[dict[str, Any]]]:
    match = FILENAME_RE.match(file_path.name)
    if not match:
        raise ValueError(f"Uventet filnavn: {file_path.name}")
    start_text, end_text = match.group(1), match.group(2)
    if start_text != end_text:
        raise ValueError(f"Filen dekker flere datoer: {start_text} til {end_text}")
    stat_date = date.fromisoformat(start_text)

    with file_path.open("r", encoding="utf-16", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != EXPECTED_COLS:
            raise ValueError(f"Uventede kolonner: {reader.fieldnames}")
        rows = []
        for raw in reader:
            room = clean_text(raw.get("Rom"))
            if not room or room == "Totalt":
                continue
            clean_raw = {key: clean_text(value) for key, value in raw.items()}
            rows.append(
                {
                    "stat_date": stat_date.isoformat(),
                    "room": room,
                    "total_soletid_minutter": decimal_value(raw.get("Total Soletid (minutter)")),
                    "totalt_antall_solinger": int_value(raw.get("Totalt antall Solinger")),
                    "solinger_medlemmer": int_value(raw.get("Solinger Medlemmer")),
                    "solinger_ikke_medlemmer": int_value(raw.get("Solinger Ikke Medlemmer")),
                    "totalt_inntjent_kr": decimal_value(raw.get("Totalt Inntjent (KR)")),
                    "inntjent_medlemmer_kr": decimal_value(raw.get("Inntjent Medlemmer (KR)")),
                    "inntjent_ikke_medlemmer_kr": decimal_value(raw.get("Inntjent Ikke Medlemmer (KR)")),
                    "raw": clean_raw,
                }
            )
    return stat_date, rows


def post_to_fibaro10(source_file: str, stat_date: date, rows: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "source": "sun2_importer",
        "collector_id": COLLECTOR_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "ok": True,
        "stat_date": stat_date.isoformat(),
        "source_file": source_file,
        "rows": rows,
        "extra": {"import_dir": str(IMPORT_DIR)},
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{FIBARO10_API_BASE_URL}/api/sun2/room-stats/ingest",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Sun2_importer/1.0",
            "x-access-username": FIBARO10_API_USERNAME,
            "x-access-password": FIBARO10_API_PASSWORD,
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {"status": response.status}


def process_once() -> list[dict[str, Any]]:
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for file_path in sorted(IMPORT_DIR.glob("Statistics_room_*.csv")):
        state["last_file"] = file_path.name
        try:
            stat_date, rows = parse_file(file_path)
        except Exception as exc:
            rejected = move_to(file_path, REJECTED_DIR, "ERROR_")
            state["rejected_files"] += 1
            state["last_error"] = str(exc)
            results.append({"file": file_path.name, "ok": False, "error": str(exc), "moved_to": str(rejected)})
            continue

        try:
            response = post_to_fibaro10(file_path.name, stat_date, rows)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            state["last_error"] = f"Fibaro10 svarte ikke: {exc}"
            results.append({"file": file_path.name, "ok": False, "error": state["last_error"], "kept_in_incoming": True})
            continue

        archived = move_to(file_path, ARCHIVE_DIR, "IMPORTED_")
        state["processed_files"] += 1
        state["last_success_at"] = datetime.utcnow().isoformat()
        state["last_error"] = None
        result = {"file": file_path.name, "ok": True, "rows": len(rows), "response": response, "moved_to": str(archived)}
        results.append(result)
    state["last_run_at"] = datetime.utcnow().isoformat()
    state["last_result"] = results
    return results


async def poll_loop() -> None:
    state["running"] = True
    while True:
        try:
            await asyncio.to_thread(process_once)
        except Exception as exc:
            state["last_error"] = str(exc)
        await asyncio.sleep(POLL_SECONDS)


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(poll_loop())


@app.get("/", response_class=HTMLResponse)
async def index():
    status_class = "ok" if not state.get("last_error") else "bad"
    html = f"""
<!doctype html>
<html lang="no">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sun2_importer</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;background:#eef2f6;color:#17202a}}
main{{max-width:880px;margin:0 auto;padding:1rem}}
.card{{background:white;border:1px solid #d8dee4;border-radius:10px;padding:1rem;margin:.75rem 0;box-shadow:0 2px 10px rgba(0,0,0,.06)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:.65rem}}
.metric{{background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;padding:.75rem}}
.metric span{{display:block;color:#667085;font-size:.78rem}}
.metric strong{{display:block;margin-top:.2rem}}
.ok{{color:#16803c;font-weight:750}}.bad{{color:#b42318;font-weight:750}}
button{{border:0;border-radius:8px;background:#4b86c2;color:white;padding:.65rem .9rem;font-weight:750}}
pre{{white-space:pre-wrap;background:#0f172a;color:#e5e7eb;border-radius:8px;padding:.75rem;overflow:auto}}
</style>
</head>
<body><main>
<h1>Sun2_importer</h1>
<section class="card grid">
<div class="metric"><span>Status</span><strong class="{status_class}">{'OK' if not state.get('last_error') else 'Feil'}</strong></div>
<div class="metric"><span>Siste kjøring</span><strong>{state.get('last_run_at') or '-'}</strong></div>
<div class="metric"><span>Siste fil</span><strong>{state.get('last_file') or '-'}</strong></div>
<div class="metric"><span>Importert</span><strong>{state.get('processed_files', 0)}</strong></div>
</section>
<section class="card">
<form method="post" action="/sync-now"><button type="submit">Synk nå</button></form>
</section>
<section class="card">
<h2>Siste resultat</h2>
<pre>{json.dumps(state, ensure_ascii=False, indent=2)}</pre>
</section>
</main></body></html>
"""
    return HTMLResponse(html)


@app.post("/sync-now")
async def sync_now():
    results = await asyncio.to_thread(process_once)
    return JSONResponse({"status": "ok", "results": results, "state": state})


@app.get("/json")
async def json_status():
    return state
