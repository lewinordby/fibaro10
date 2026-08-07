from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from html import escape
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

FIBARO10_BASE_URL = os.getenv("FIBARO10_BASE_URL", "http://fibaro10:8110").rstrip("/")
MAINTENANCE_MOBILE_BUILD = os.getenv("MAINTENANCE_MOBILE_BUILD", "1469")
SESSION_COOKIE_NAME = "lilletorget_maintenance_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30

app = FastAPI(title="Lilletorget Vedlikehold", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="maintenance_mobile/app/static"), name="assets")


def json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def normalize_username(value: Any) -> str:
    return str(value or "").strip().casefold()


def session_token(request: Request) -> Optional[str]:
    return request.cookies.get(SESSION_COOKIE_NAME) or None


def require_session(request: Request) -> str:
    token = session_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Ikke innlogget")
    return token


def secure_cookie(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
    return request.url.scheme == "https" or forwarded_proto == "https"


def fibaro_request_sync(
    path: str,
    session_token_value: str,
    *,
    method: str = "GET",
    payload: Optional[dict[str, Any]] = None,
    timeout: int = 25,
) -> Any:
    data = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "lilletorget-maintenance-mobile/1",
    }
    if session_token_value:
        headers["X-Session-Token"] = session_token_value
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False, default=json_safe).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = UrlRequest(f"{FIBARO10_BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
            message = parsed.get("detail") or parsed.get("message") or detail
        except json.JSONDecodeError:
            message = detail or exc.reason
        raise HTTPException(status_code=exc.code, detail=message) from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Fibaro10 er ikke tilgjengelig: {exc.reason}") from exc
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Fibaro10 svarte ikke med gyldig JSON") from exc


async def fibaro_request(
    path: str,
    session_token_value: str,
    *,
    method: str = "GET",
    payload: Optional[dict[str, Any]] = None,
    timeout: int = 25,
) -> Any:
    return await asyncio.to_thread(
        fibaro_request_sync,
        path,
        session_token_value,
        method=method,
        payload=payload,
        timeout=timeout,
    )


def fields_by_key(module_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    for table in module_payload.get("tables") or []:
        edit = table.get("edit") if isinstance(table, dict) else None
        if isinstance(edit, dict) and edit.get("kind") == "maintenance-log":
            return {field.get("key"): field for field in edit.get("fields") or [] if isinstance(field, dict)}
    return {}


def maintenance_rows(module_payload: dict[str, Any]) -> list[dict[str, Any]]:
    for table in module_payload.get("tables") or []:
        if isinstance(table, dict) and table.get("title") == "Vedlikeholdslogg":
            rows = table.get("rows") or []
            return [row for row in rows if isinstance(row, dict)]
    return []


def maintenance_row_by_id(module_payload: dict[str, Any], log_id: int) -> Optional[dict[str, Any]]:
    for row in maintenance_rows(module_payload):
        try:
            row_id = int(row.get("id") or 0)
        except (TypeError, ValueError):
            continue
        if row_id == log_id:
            return row
    return None


def roborock_options(module_payload: Optional[dict[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(module_payload, dict):
        return []
    for table in module_payload.get("tables") or []:
        if not isinstance(table, dict) or table.get("title") not in {"Roboter", "Robotdetaljer"}:
            continue
        rows = table.get("rows") or []
        result = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            label = str(row.get("name") or "").strip()
            if not label or label.casefold() in seen:
                continue
            seen.add(label.casefold())
            result.append({"label": label, "value": label})
        return result
    return []


def option_values(field: Optional[dict[str, Any]]) -> list[dict[str, str]]:
    options = (field or {}).get("options") or []
    result = []
    for option in options:
        if not isinstance(option, dict):
            continue
        label = str(option.get("label") or option.get("value") or "").strip()
        value = str(option.get("value") or option.get("label") or "").strip()
        if label and value:
            result.append({"label": label, "value": value})
    return result


def bootstrap_payload(
    module_payload: dict[str, Any],
    user_payload: dict[str, Any],
    renhold_payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    fields = fields_by_key(module_payload)
    recent_rows = maintenance_rows(module_payload)[:300]
    default_performed_at = (fields.get("performed_at") or {}).get("defaultValue")
    return {
        "user": user_payload,
        "cards": module_payload.get("cards") or [],
        "recent": recent_rows,
        "defaults": {
            "performed_at": default_performed_at,
            "target_type": "Seng",
            "action_type": "Kontroll",
            "priority": "Normal",
            "status": "Utført",
            "presence_type": "Tilstede Sun2",
        },
        "options": {
            "presence_type": option_values(fields.get("presence_type")),
            "target_type": option_values(fields.get("target_type")),
            "room_id": option_values(fields.get("room_id")),
            "action_type": option_values(fields.get("action_type")),
            "priority": option_values(fields.get("priority")),
            "status": option_values(fields.get("status")),
            "tags": option_values(fields.get("tags")),
            "robots": roborock_options(renhold_payload),
        },
    }


@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "maintenance_mobile",
        "build": MAINTENANCE_MOBILE_BUILD,
        "fibaro10": FIBARO10_BASE_URL,
    }


@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse("/static/lilletorget-favicon.png", status_code=307)


@app.get("/manifest.webmanifest")
async def manifest():
    return JSONResponse(
        {
            "id": "/",
            "name": "Lilletorget Vedlikehold",
            "short_name": "Vedlikehold",
            "description": "Rask registrering og oppfølging av vedlikehold på Lilletorget.",
            "lang": "nb-NO",
            "dir": "ltr",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "display_override": ["standalone", "minimal-ui"],
            "orientation": "portrait",
            "background_color": "#f4f7fb",
            "theme_color": "#755ff8",
            "categories": ["business", "productivity", "utilities"],
            "prefer_related_applications": False,
            "icons": [
                {"src": "/static/pwa-icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                {"src": "/static/pwa-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                {"src": "/static/pwa-icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
            ],
            "launch_handler": {"client_mode": "navigate-existing"},
        },
        media_type="application/manifest+json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not session_token(request):
        return RedirectResponse("/auth/login", status_code=303)
    return HTMLResponse(INDEX_HTML)


@app.get("/auth/login", response_class=HTMLResponse)
async def login_view(request: Request):
    next_path = "/"
    token = session_token(request)
    if token:
        try:
            await fibaro_request("/api/auth/me", token, timeout=12)
        except HTTPException:
            response = HTMLResponse(login_html("Økten er utløpt. Logg inn på nytt.", next_path=next_path))
            response.delete_cookie(SESSION_COOKIE_NAME)
            return response
        return RedirectResponse(next_path, status_code=303)
    return HTMLResponse(login_html(next_path=next_path))


@app.post("/auth/login")
async def login_submit(request: Request):
    next_path = "/"
    form = await request.form()
    username = normalize_username(form.get("username"))
    password = str(form.get("password") or "").strip()
    error = ""
    if not username or not password:
        error = "Brukernavn og passord må fylles ut."
    else:
        try:
            session_payload = await fibaro_request(
                "/api/auth/session",
                "",
                method="POST",
                payload={"username": username, "password": password},
                timeout=12,
            )
        except HTTPException:
            error = "Ugyldig brukernavn eller passord."
    if error:
        return HTMLResponse(login_html(error, next_path=next_path), status_code=401)
    response = RedirectResponse(next_path, status_code=303)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        str(session_payload.get("sessionToken") or ""),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=secure_cookie(request),
        samesite="lax",
    )
    return response


@app.post("/konto/logg-ut")
async def logout(request: Request):
    token = session_token(request)
    if token:
        try:
            await fibaro_request("/api/auth/session", token, method="DELETE", timeout=8)
        except HTTPException:
            pass
    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@app.get("/api/bootstrap")
async def api_bootstrap(request: Request):
    token = require_session(request)
    user_payload, module_payload = await asyncio.gather(
        fibaro_request("/api/auth/me", token),
        fibaro_request("/api/modules/vedlikehold", token),
    )
    renhold_payload = None
    try:
        renhold_payload = await fibaro_request("/api/modules/renhold", token)
    except HTTPException:
        renhold_payload = None
    return bootstrap_payload(module_payload, user_payload, renhold_payload)


@app.post("/api/maintenance/logs")
async def api_create_maintenance_log(request: Request):
    token = require_session(request)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Ugyldig payload")
    result = await fibaro_request("/api/maintenance/logs", token, method="POST", payload=payload)
    return result


@app.patch("/api/maintenance/logs/{log_id}")
async def api_update_maintenance_log(request: Request, log_id: int):
    token = require_session(request)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Ugyldig payload")
    user_payload, module_payload = await asyncio.gather(
        fibaro_request("/api/auth/me", token),
        fibaro_request("/api/modules/vedlikehold", token),
    )
    username = normalize_username(user_payload.get("username"))
    existing = maintenance_row_by_id(module_payload, log_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Vedlikeholdsposten finnes ikke")
    if normalize_username(existing.get("performed_by")) != normalize_username(username):
        raise HTTPException(status_code=403, detail="Du kan bare redigere egne vedlikeholdsposter")
    payload["performed_by"] = existing.get("performed_by") or username
    result = await fibaro_request(f"/api/maintenance/logs/{log_id}", token, method="PATCH", payload=payload)
    return result


def login_html(error: str = "", *, next_path: str = "/") -> str:
    error_html = f'<div class="login-error">{escape(error)}</div>' if error else ""
    login_action = "/auth/login"
    return f"""<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#755ff8">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="Vedlikehold">
  <title>Logg inn · Vedlikehold</title>
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="apple-touch-icon" href="/static/pwa-icon-512.png">
  <link rel="icon" type="image/png" href="/static/lilletorget-favicon.png">
  <link rel="stylesheet" href="/assets/maintenance-mobile.css?v=1469">
</head>
<body class="login-body">
  <main class="login-screen">
    <section class="login-brand">
      <img src="/static/lilletorget-login.png" alt="Lilletorget">
    </section>
    <section class="login-panel">
      <p class="eyebrow">Lilletorget</p>
      <h1>Vedlikehold</h1>
      <p class="muted">Samme brukere som Fibaro10. Alle innloggede brukere kan registrere arbeid og observasjoner.</p>
      {error_html}
      <form method="post" action="{login_action}" class="login-form">
        <label>Brukernavn<input name="username" autocomplete="username" required autofocus></label>
        <label>Passord<input type="password" name="password" autocomplete="current-password" required></label>
        <button type="submit">Logg inn</button>
      </form>
    </section>
  </main>
</body>
</html>"""


INDEX_HTML = """<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#755ff8">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="Vedlikehold">
  <title>Lilletorget Vedlikehold</title>
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="apple-touch-icon" href="/static/pwa-icon-512.png">
  <link rel="icon" type="image/png" href="/static/lilletorget-favicon.png">
  <link rel="stylesheet" href="/assets/maintenance-mobile.css?v=1469">
  <script src="/assets/maintenance-mobile.js?v=1469" defer></script>
</head>
<body>
  <header class="app-topbar">
    <div class="brand-logo">
      <img src="/static/lilletorget-mark.png" alt="">
    </div>
    <strong class="brand-title">Lilletorget, <span>vedlikehold</span></strong>
    <button id="profileButton" class="user-button" type="button" title="Bruker" aria-label="Åpne brukerprofil">
        <span id="topUserInitial" class="user-initial" aria-hidden="true">?</span>
    </button>
  </header>
  <main class="app-shell">
    <section id="taskScreen" class="screen">
      <section class="task-hero">
        <h1>Hva skal registreres?</h1>
      </section>

      <section id="taskGrid" class="task-grid" aria-label="Vedlikeholdsoppgaver"></section>
      <p id="taskMessage" class="task-message" role="status"></p>
    </section>

    <section id="entryScreen" class="screen is-hidden">
      <section class="entry-head sub-topbar">
        <button id="backButton" class="back-button" type="button" aria-label="Tilbake">
          <img src="/static/lilletorget-mark.png" alt="">
        </button>
        <div class="entry-title-block">
          <h1 class="entry-title-line"><span id="taskTitle">Vedlikehold</span><button id="timeButton" class="time-button" type="button" aria-expanded="false"><span aria-hidden="true">, </span><strong id="timeButtonLabel">N&aring;</strong></button></h1>
          <p id="taskSubtitle" class="muted"></p>
          <p id="entryUserLine" class="entry-user-line"></p>
        </div>
        <span class="sub-topbar-spacer" aria-hidden="true"></span>
      </section>

      <form id="maintenanceForm" class="entry-card">
        <input id="performed_by" name="performed_by" type="hidden">
        <div id="timeField" class="time-field is-hidden">
          <label>Tidspunkt<input id="performed_at" name="performed_at" type="datetime-local" required></label>
        </div>

        <section id="roomField" class="room-field is-hidden">
          <p class="field-label">Seng / rom</p>
          <select id="room_id" name="room_id" class="room-select"></select>
          <div id="roomQuickGrid" class="room-quick-grid" aria-label="Velg seng eller rom"></div>
        </section>

        <section id="robotField" class="robot-field is-hidden">
          <div class="field-line">
            <p class="field-label">Robotvaskere</p>
            <button id="robotAllButton" class="text-button" type="button">Alle</button>
          </div>
          <div id="robotQuickGrid" class="robot-quick-grid" aria-label="Velg robotvaskere"></div>
        </section>

        <section id="targetChoiceField" class="target-choice-field is-hidden">
          <div class="field-line">
            <p id="targetChoiceLabel" class="field-label">Valg</p>
            <button id="targetChoiceAllButton" class="text-button" type="button">Alle</button>
          </div>
          <div id="targetChoiceGrid" class="target-choice-grid" aria-label="Velg enheter"></div>
        </section>

        <section id="standardTaskField" class="standard-task-field is-hidden">
          <p class="field-label">Oppgaver</p>
          <div id="standardTaskGrid" class="standard-task-grid" aria-label="Velg standardoppgaver"></div>
        </section>

        <section class="note-panel">
          <label id="noteField" class="note-field"><span class="visually-hidden">Notat</span><textarea id="summary" name="summary" rows="3" placeholder="Skriv eventuelt kort hva som ble gjort eller avvik du fant."></textarea></label>
        </section>

        <div class="form-row follow-row">
          <label class="toggle-line"><input id="follow_up_needed" name="follow_up_needed" type="checkbox"> Må følges opp</label>
          <label>Varighet<input id="duration_minutes" name="duration_minutes" type="number" min="0" inputmode="numeric" placeholder="min"></label>
        </div>

        <label id="followUpField" class="is-hidden">Oppfølging<textarea id="follow_up_text" name="follow_up_text" rows="3" placeholder="Hva må gjøres videre?"></textarea></label>

        <div class="form-actions">
          <button id="submitButton" class="primary-button" type="submit">Lagre</button>
          <button id="submitNextButton" class="secondary-button" type="submit">Lagre og ny</button>
        </div>
        <p id="formMessage" class="form-message" role="status"></p>
      </form>
    </section>

    <section id="detailScreen" class="screen is-hidden">
      <section class="entry-head sub-topbar detail-head">
        <button id="detailBackButton" class="back-button" type="button" aria-label="Tilbake">
          <img src="/static/lilletorget-mark.png" alt="">
        </button>
        <div class="entry-title-block">
          <h1>Vedlikeholdspost</h1>
          <p class="entry-user-line">Detaljer</p>
        </div>
        <span class="sub-topbar-spacer" aria-hidden="true"></span>
      </section>
      <article id="detailContent" class="detail-card"></article>
    </section>

    <section id="profileScreen" class="screen is-hidden">
      <section class="entry-head sub-topbar profile-head">
        <button id="profileBackButton" class="back-button" type="button" aria-label="Tilbake">
          <img src="/static/lilletorget-mark.png" alt="">
        </button>
        <div class="entry-title-block">
          <h1>Bruker</h1>
          <p class="entry-user-line">Konto og utlogging</p>
        </div>
        <span class="sub-topbar-spacer" aria-hidden="true"></span>
      </section>

      <section class="profile-card">
        <div class="profile-identity">
          <span id="profileInitial" class="profile-initial" aria-hidden="true">?</span>
          <div>
            <h2 id="profileUserName">Bruker</h2>
            <p id="profileUserRole" class="muted">Henter bruker...</p>
          </div>
        </div>
        <dl id="profileDetails" class="profile-details"></dl>
        <form method="post" action="/konto/logg-ut">
          <button class="primary-button logout-button" type="submit">Logg ut</button>
        </form>
      </section>
    </section>

    <section id="recentCard" class="recent-card">
      <div class="section-head">
        <div>
          <p class="eyebrow">Historikk</p>
          <h2 id="recentTitle">Siste registreringer</h2>
          <p id="recentSubtitle" class="muted">Siste vedlikeholdsposter på tvers av kategorier.</p>
        </div>
      </div>
      <div class="history-filters" role="group" aria-label="Filtrer historikk">
        <button type="button" class="is-active" data-history-filter="all" aria-pressed="true">Alle <span>0</span></button>
        <button type="button" data-history-filter="today" aria-pressed="false">I dag <span>0</span></button>
        <button type="button" data-history-filter="follow-up" aria-pressed="false">Oppfølging <span>0</span></button>
        <button type="button" data-history-filter="mine" aria-pressed="false">Mine <span>0</span></button>
      </div>
      <label class="history-search">
        <span class="visually-hidden">Søk i vedlikeholdshistorikken</span>
        <input id="historySearch" type="search" placeholder="Søk i registreringer" autocomplete="off">
        <button id="historySearchClear" class="history-search-clear is-hidden" type="button" aria-label="Tøm søk">×</button>
      </label>
      <p id="historyResultMeta" class="history-result-meta"></p>
      <div id="recentList" class="recent-list"></div>
      <button id="historyMoreButton" class="history-more-button is-hidden" type="button">Vis flere</button>
    </section>
  </main>
</body>
</html>"""
