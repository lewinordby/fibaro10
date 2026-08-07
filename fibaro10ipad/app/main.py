from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from html import escape
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

load_dotenv()

FIBARO10_BASE_URL = os.getenv("FIBARO10_BASE_URL", "http://fibaro10:8110").rstrip("/")
FIBARO10_APP_URL = os.getenv("FIBARO10_APP_URL", "http://192.168.20.218:8110").rstrip("/")
APP_BUILD = os.getenv("FIBARO10_IPAD_APP_BUILD", os.getenv("APP_BUILD", "1477"))
APP_COMMIT = os.getenv("FIBARO10_IPAD_APP_COMMIT", os.getenv("APP_COMMIT", "unknown"))
ASSET_VERSION = f"{APP_BUILD}-{APP_COMMIT[:7]}"

SESSION_COOKIE_NAME = "lilletorget_ipad_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30

ALLOWED_MODULES: dict[str, set[str]] = {
    "parkering": {"oversikt", "parkeringer", "dagslinje", "kjoretoy", "prognose"},
    "soling": {"oversikt", "enkeltimer", "dagslinje", "produkter"},
    "energi": {"status", "elvia", "solsenger"},
    "ventilasjon": {"dagslogg", "temp-logg", "yr-logg"},
    "lys": {"dagslogg", "status"},
    "renhold": {"oversikt"},
    "vedlikehold": {"oversikt", "besok"},
}

app = FastAPI(title="Lilletorget iPad", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="fibaro10ipad/app/static"), name="assets")


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
        "User-Agent": "lilletorget-ipad/1",
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


async def optional_fibaro_request(path: str, session_token_value: str, *, timeout: int = 25) -> dict[str, Any]:
    try:
        payload = await fibaro_request(path, session_token_value, timeout=timeout)
    except HTTPException as exc:
        return {"error": str(exc.detail), "statusCode": exc.status_code}
    if isinstance(payload, dict):
        return payload
    return {"value": payload}


def safe_go_path(path: str) -> str:
    raw = str(path or "/").strip()
    if not raw.startswith("/"):
        raw = f"/{raw}"
    if raw.startswith("//") or "\\" in raw:
        return "/"
    return raw


@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "fibaro10ipad",
        "fibaro10": FIBARO10_BASE_URL,
        "build": APP_BUILD,
        "commit": APP_COMMIT,
    }


@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse("/static/lilletorget-favicon.png", status_code=307)


@app.get("/manifest.webmanifest")
async def manifest():
    return JSONResponse(
        {
            "name": "Lilletorget iPad",
            "short_name": "Lilletorget",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#f5f7fb",
            "theme_color": "#10233f",
            "icons": [
                {"src": "/static/lilletorget-favicon.png", "sizes": "512x512", "type": "image/png"},
            ],
        }
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not session_token(request):
        return RedirectResponse("/auth/login", status_code=303)
    return HTMLResponse(INDEX_HTML)


@app.get("/auth/login", response_class=HTMLResponse)
async def login_view(request: Request):
    token = session_token(request)
    if token:
        try:
            await fibaro_request("/api/auth/me", token, timeout=12)
        except HTTPException:
            response = HTMLResponse(login_html("Økten er utløpt. Logg inn på nytt."))
            response.delete_cookie(SESSION_COOKIE_NAME)
            return response
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(login_html())


@app.post("/auth/login")
async def login_submit(request: Request):
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
        return HTMLResponse(login_html(error), status_code=401)
    response = RedirectResponse("/", status_code=303)
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


@app.get("/go")
async def go(path: str = "/"):
    return RedirectResponse(f"{FIBARO10_APP_URL}{quote(safe_go_path(path), safe='/?=&:%#')}", status_code=307)


@app.get("/api/bootstrap")
async def api_bootstrap(request: Request):
    token = require_session(request)
    user_payload, overview_payload, health_payload = await asyncio.gather(
        fibaro_request("/api/auth/me", token, timeout=12),
        fibaro_request("/api/overview", token, timeout=25),
        optional_fibaro_request("/health?details=true", token, timeout=20),
    )
    return {
        "generatedAt": datetime.now().isoformat(),
        "app": {
            "name": "Lilletorget iPad",
            "build": APP_BUILD,
            "commit": APP_COMMIT,
            "fibaro10AppUrl": FIBARO10_APP_URL,
        },
        "user": user_payload,
        "overview": overview_payload,
        "health": health_payload,
    }


@app.get("/api/module/{module}")
async def api_module(module: str, request: Request, view: Optional[str] = None, day: Optional[str] = None):
    token = require_session(request)
    module_key = str(module or "").strip().casefold()
    view_key = str(view or "").strip().casefold()
    allowed_views = ALLOWED_MODULES.get(module_key)
    if not allowed_views:
        raise HTTPException(status_code=404, detail="Ukjent modul")
    if view_key and view_key not in allowed_views:
        raise HTTPException(status_code=400, detail="Denne visningen er ikke åpnet for iPad-appen")
    params: dict[str, str] = {}
    if view_key:
        params["view"] = view_key
    if day:
        params["day"] = day
    query = f"?{urlencode(params)}" if params else ""
    return await fibaro_request(f"/api/modules/{module_key}{query}", token, timeout=30)


@app.get("/api/doors")
async def api_doors(request: Request):
    token = require_session(request)
    return await fibaro_request("/api/hc3/doors/status", token, timeout=20)


def login_html(error: str = "") -> str:
    error_html = f'<div class="login-error">{escape(error)}</div>' if error else ""
    return f"""<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Logg inn · Lilletorget iPad</title>
  <link rel="icon" type="image/png" href="/static/lilletorget-favicon.png">
  <link rel="stylesheet" href="/assets/ipad.css?v={ASSET_VERSION}">
</head>
<body class="login-body">
  <main class="login-screen">
    <section class="login-brand" aria-label="Lilletorget iPad">
      <img src="/static/lilletorget-mark.png" alt="">
      <p>Lilletorget</p>
      <h1>iPad</h1>
      <span>Driftsflate for 13 tommer iPad Pro</span>
    </section>
    <section class="login-panel">
      <p class="eyebrow">Fibaro10</p>
      <h2>Logg inn</h2>
      <p class="muted">Samme brukerbase som hovedappen. Denne flaten er optimalisert for rask oversikt på iPad.</p>
      {error_html}
      <form method="post" action="/auth/login" class="login-form">
        <label>Brukernavn<input name="username" autocomplete="username" required autofocus></label>
        <label>Passord<input type="password" name="password" autocomplete="current-password" required></label>
        <button type="submit">Logg inn</button>
      </form>
    </section>
  </main>
</body>
</html>"""


INDEX_HTML = f"""<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#10233f">
  <title>Lilletorget iPad</title>
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="icon" type="image/png" href="/static/lilletorget-favicon.png">
  <link rel="stylesheet" href="/assets/ipad.css?v={ASSET_VERSION}">
  <script src="/assets/ipad.js?v={ASSET_VERSION}" defer></script>
</head>
<body>
  <main class="ipad-app">
    <aside class="app-rail" aria-label="Hovedmeny">
      <a class="rail-brand" href="/" aria-label="Lilletorget iPad">
        <img src="/static/lilletorget-mark.png" alt="">
        <span>Lilletorget</span>
        <small>iPad</small>
      </a>
      <nav class="mode-tabs" aria-label="Hovedvisning">
        <button class="is-active" type="button" data-view="overview"><span>O</span>Oversikt</button>
        <button type="button" data-view="parking"><span>P</span>Parkering</button>
        <button type="button" data-view="sun"><span>S</span>Soling</button>
        <button type="button" data-view="ops"><span>D</span>Drift</button>
      </nav>
      <div class="rail-status">
        <span>Build</span>
        <strong id="buildBadge">1476</strong>
      </div>
    </aside>

    <section class="app-stage">
    <header class="stage-toolbar">
      <div class="title-stack">
        <p class="eyebrow">Lilletorget iPad</p>
        <h1 id="mainTitle">Oversikt</h1>
      </div>
      <div class="status-pills" aria-label="Status">
        <span id="topOperatingStatus" class="top-pill">Henter åpning</span>
        <span id="topDatasourceStatus" class="top-pill">Datakilder</span>
        <span id="topLatestSun" class="top-pill">Siste soling</span>
        <span id="topLatestParking" class="top-pill">Siste parkering</span>
      </div>
      <div id="syncStatus" class="sync-status">Henter data</div>
      <div class="top-actions">
        <button id="refreshButton" class="icon-button" type="button" aria-label="Oppdater">↻</button>
        <form method="post" action="/konto/logg-ut">
          <button id="userButton" class="user-button" type="submit" title="Logg ut">?</button>
        </form>
      </div>
    </header>

    <section id="overviewView" class="view is-active">
      <div id="periodGrid" class="period-grid"></div>
    </section>

    <section id="parkingView" class="view">
      <div class="workspace-grid">
        <article class="panel panel-focus">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Parkering</p>
              <h2>Akkurat nå</h2>
            </div>
            <a class="panel-link" href="/go?path=/parkering/parkeringer">Hovedapp</a>
          </div>
          <div id="parkingCards" class="mini-card-grid"></div>
        </article>
        <article class="panel">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Historikk</p>
              <h2>Siste parkering</h2>
            </div>
            <a class="panel-link" href="/go?path=/parkering/oversikt">Oversikt</a>
          </div>
          <div id="parkingList" class="event-list"></div>
        </article>
      </div>
    </section>

    <section id="sunView" class="view">
      <div class="workspace-grid">
        <article class="panel panel-focus">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Soling</p>
              <h2>Akkurat nå</h2>
            </div>
            <a class="panel-link" href="/go?path=/soling/enkeltimer">Enkelttimer</a>
          </div>
          <div id="sunCards" class="mini-card-grid"></div>
        </article>
        <article class="panel">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Historikk</p>
              <h2>Siste soling</h2>
            </div>
            <a class="panel-link" href="/go?path=/soling/dagslinje">Dagslinje</a>
          </div>
          <div id="sunList" class="event-list"></div>
        </article>
      </div>
    </section>

    <section id="opsView" class="view">
      <div class="ops-grid">
        <article class="panel command-panel">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Drift</p>
              <h2>Status akkurat nå</h2>
            </div>
            <a class="panel-link" href="/go?path=/dashboard/drift">Drift</a>
          </div>
          <div id="operatingStatus" class="operating-status"></div>
          <div class="strip-stack">
            <div>
              <h3>Lys</h3>
              <div id="lightStrip" class="state-strip"></div>
            </div>
            <div>
              <h3>Ventilasjon</h3>
              <div id="fanStrip" class="state-strip"></div>
            </div>
          </div>
        </article>
        <article class="panel">
          <div class="panel-head">
            <h2>Datakilder</h2>
            <a class="panel-link" href="/go?path=/admin/datakilder">Alle</a>
          </div>
          <div id="serviceList" class="service-list"></div>
        </article>
      </div>
    </section>
    </section>
  </main>
</body>
</html>"""
