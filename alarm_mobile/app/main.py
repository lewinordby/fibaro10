from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from html import escape
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

load_dotenv()

FIBARO10_BASE_URL = os.getenv("FIBARO10_BASE_URL", "http://fibaro10:8110").rstrip("/")
ALARM_MOBILE_BUILD = os.getenv("ALARM_MOBILE_BUILD", "3")
SESSION_COOKIE_NAME = "lilletorget_alarm_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30

app = FastAPI(title="Lilletorget Alarm", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="alarm_mobile/app/static"), name="assets")


def normalize_username(value: Any) -> str:
    return str(value or "").strip().casefold()


def json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def session_token(request: Request) -> Optional[str]:
    return request.cookies.get(SESSION_COOKIE_NAME) or None


def require_session(request: Request) -> str:
    token = session_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Ikke innlogget")
    return token


def secure_cookie(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
    return request.url.scheme == "https" or forwarded == "https"


def safe_next_path(value: Any) -> str:
    path = str(value or "/").strip()
    if not path.startswith("/") or path.startswith("//") or "\r" in path or "\n" in path:
        return "/"
    return path[:1200]


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
        "User-Agent": "lilletorget-alarm-mobile/1",
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


def fibaro_binary_request_sync(path: str, session_token_value: str, *, timeout: int = 25) -> tuple[bytes, str]:
    request = UrlRequest(
        f"{FIBARO10_BASE_URL}{path}",
        headers={
            "Accept": "image/jpeg",
            "X-Session-Token": session_token_value,
            "User-Agent": "lilletorget-alarm-mobile/1",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read(), response.headers.get_content_type() or "image/jpeg"
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=exc.code, detail=detail or exc.reason) from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Fibaro10 er ikke tilgjengelig: {exc.reason}") from exc


async def fibaro_binary_request(path: str, session_token_value: str) -> tuple[bytes, str]:
    return await asyncio.to_thread(fibaro_binary_request_sync, path, session_token_value)


def monitor_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    monitors = [
        (item, "camera") for item in (payload.get("camera_monitors") or [])
    ] + [
        (item, "asset") for item in (payload.get("asset_monitors") or [])
    ]
    for monitor, monitor_kind in monitors:
        if not isinstance(monitor, dict) or not monitor.get("camera_id"):
            continue
        camera_id = str(monitor["camera_id"])
        asset_key = str(monitor.get("asset_key") or "")
        encoded_id = quote(camera_id, safe="")
        encoded_asset = quote(asset_key, safe="")
        crop = dict(monitor.get("display_crop") or {})
        crop["aspectRatio"] = round(float(crop.get("width") or 16) / float(crop.get("height") or 9), 4)
        images: dict[str, str] = {}
        for kind, source_key, stamp_key in (
            ("baseline", "baseline_url", "baseline_captured_at"),
            ("latest", "latest_url", "latest_captured_at"),
            ("overlay", "overlay_url", "latest_captured_at"),
        ):
            if not monitor.get(source_key):
                continue
            stamp = quote(str(monitor.get(stamp_key) or "current"), safe="")
            if monitor_kind == "asset":
                images[kind] = f"/api/bollards/assets/{encoded_asset}/{kind}?captured={stamp}"
            else:
                images[kind] = f"/api/bollards/cameras/{encoded_id}/{kind}/crop?captured={stamp}"
        items.append(
            {
                "id": str(monitor.get("monitor_id") or camera_id),
                "cameraId": camera_id,
                "assetKey": asset_key or None,
                "name": str(monitor.get("display_name") or monitor.get("camera_name") or camera_id),
                "kind": str(monitor.get("item_type") or "bollards"),
                "status": str(monitor.get("status") or "unknown"),
                "lastCheckedAt": monitor.get("last_checked_at"),
                "baselineCapturedAt": monitor.get("baseline_captured_at"),
                "latestCapturedAt": monitor.get("latest_captured_at"),
                "changeScore": monitor.get("change_score"),
                "lastError": monitor.get("last_error"),
                "crop": crop,
                "images": images,
            }
        )
    return items


async def safe_fibaro(path: str, session_token_value: str) -> tuple[Any, Optional[str]]:
    try:
        return await fibaro_request(path, session_token_value), None
    except HTTPException as exc:
        return None, str(exc.detail)


async def alarm_bootstrap(session_token_value: str) -> dict[str, Any]:
    user_result, doors_result, bollards_result, notifications_result = await asyncio.gather(
        safe_fibaro("/api/auth/me", session_token_value),
        safe_fibaro("/api/hc3/doors/alarm?history_limit=150", session_token_value),
        safe_fibaro("/api/unifi-protect/bollards", session_token_value),
        safe_fibaro("/api/system/notifications", session_token_value),
    )
    errors = {
        name: error
        for name, (_, error) in {
            "user": user_result,
            "doors": doors_result,
            "bollards": bollards_result,
            "notifications": notifications_result,
        }.items()
        if error
    }
    bollards = bollards_result[0] if isinstance(bollards_result[0], dict) else {}
    return {
        "generatedAt": datetime.now().astimezone().isoformat(),
        "build": ALARM_MOBILE_BUILD,
        "user": user_result[0] or {"username": "Innlogget"},
        "doors": doors_result[0] or {},
        "bollards": {
            "summary": bollards.get("summary") or {},
            "settings": bollards.get("settings") or {},
            "runtime": bollards.get("runtime") or {},
            "incidents": bollards.get("incidents") or [],
            "monitors": monitor_payload(bollards),
        },
        "notifications": notifications_result[0] or {},
        "errors": errors,
    }


@app.get("/health")
async def health():
    return {"ok": True, "service": "alarm_mobile", "build": ALARM_MOBILE_BUILD, "fibaro10": FIBARO10_BASE_URL}


@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse("/static/lilletorget-favicon.png", status_code=307)


@app.get("/manifest.webmanifest")
async def manifest():
    return JSONResponse(
        {
            "name": "Lilletorget Alarm",
            "short_name": "Alarm",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#f3f4f6",
            "theme_color": "#111827",
            "icons": [{"src": "/static/lilletorget-favicon.png", "sizes": "512x512", "type": "image/png"}],
        }
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not session_token(request):
        destination = safe_next_path(f"{request.url.path}?{request.url.query}" if request.url.query else request.url.path)
        return RedirectResponse(f"/auth/login?next={quote(destination, safe='')}", status_code=303)
    return HTMLResponse(INDEX_HTML)


@app.get("/auth/login", response_class=HTMLResponse)
async def login_view(request: Request):
    next_path = safe_next_path(request.query_params.get("next"))
    token = session_token(request)
    if token:
        try:
            await fibaro_request("/api/auth/me", token, timeout=12)
        except HTTPException:
            response = HTMLResponse(login_html("Økten er utløpt. Logg inn på nytt.", next_path))
            response.delete_cookie(SESSION_COOKIE_NAME)
            return response
        return RedirectResponse(next_path, status_code=303)
    return HTMLResponse(login_html("", next_path))


@app.post("/auth/login")
async def login_submit(request: Request):
    next_path = safe_next_path(request.query_params.get("next"))
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
        return HTMLResponse(login_html(error, next_path), status_code=401)
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
    return await alarm_bootstrap(require_session(request))


@app.post("/api/notifications/bollards/test")
async def api_bollard_test(request: Request):
    return await fibaro_request(
        "/api/unifi-protect/bollards/mobile-notifications/test",
        require_session(request),
        method="POST",
    )


@app.get("/api/doors/rooms/{room_id}")
async def api_door_room(request: Request, room_id: str):
    return await fibaro_request(
        f"/api/hc3/doors/sunroom-sessions/{quote(room_id, safe='')}",
        require_session(request),
    )


async def image_response(request: Request, path: str) -> Response:
    content, content_type = await fibaro_binary_request(path, require_session(request))
    return Response(content=content, media_type=content_type, headers={"Cache-Control": "private, no-store"})


@app.get("/api/bollards/cameras/{camera_id}/{kind}/crop")
async def api_camera_image(request: Request, camera_id: str, kind: str):
    if kind not in {"baseline", "latest", "overlay"}:
        raise HTTPException(status_code=400, detail="Ukjent bildetype")
    return await image_response(
        request,
        f"/api/unifi-protect/bollards/cameras/{quote(camera_id, safe='')}/{kind}/crop",
    )


@app.get("/api/bollards/assets/{asset_key}/{kind}")
async def api_asset_image(request: Request, asset_key: str, kind: str):
    if kind not in {"baseline", "latest", "overlay"}:
        raise HTTPException(status_code=400, detail="Ukjent bildetype")
    return await image_response(
        request,
        f"/api/unifi-protect/bollards/assets/{quote(asset_key, safe='')}/{kind}",
    )


def login_html(error: str, next_path: str) -> str:
    action = f"/auth/login?next={quote(next_path, safe='')}"
    error_html = f'<p class="login-error">{escape(error)}</p>' if error else ""
    return f"""<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#111827">
  <title>Logg inn · Alarm</title>
  <link rel="icon" type="image/png" href="/static/lilletorget-favicon.png">
  <link rel="stylesheet" href="/assets/alarm-mobile.css?v=3">
</head>
<body class="login-body">
  <main class="login-screen">
    <img class="login-logo" src="/static/lilletorget-mark.png" alt="Lilletorget">
    <section class="login-panel">
      <p class="eyebrow">Lilletorget</p>
      <h1>Alarm</h1>
      <p class="muted">Logg inn med samme bruker som i Fibaro10.</p>
      {error_html}
      <form class="login-form" method="post" action="{action}">
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
  <meta name="theme-color" content="#111827">
  <title>Lilletorget Alarm</title>
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="icon" type="image/png" href="/static/lilletorget-favicon.png">
  <link rel="stylesheet" href="/assets/alarm-mobile.css?v=3">
  <script src="/assets/alarm-mobile.js?v=3" defer></script>
</head>
<body>
  <header class="topbar">
    <img class="brand-mark" src="/static/lilletorget-mark.png" alt="">
    <div class="brand-copy"><strong>Alarm</strong><span id="lastUpdated">Henter status</span></div>
    <button id="refreshButton" class="icon-button" type="button" aria-label="Oppdater" title="Oppdater">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 4v5h5M4 13a8.1 8.1 0 0 0 15.5 2M20 20v-5h-5"/></svg>
    </button>
  </header>

  <main class="app-shell">
    <section id="overviewView" class="view"></section>
    <section id="doorsView" class="view is-hidden"></section>
    <section id="bollardsView" class="view is-hidden"></section>
    <section id="bollardDetailView" class="view is-hidden"></section>
    <section id="accountView" class="view is-hidden"></section>
    <p id="appMessage" class="app-message" role="status"></p>
  </main>

  <nav class="bottom-nav" aria-label="Alarmnavigasjon">
    <button type="button" data-view="overview" class="is-active">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3v18h18M7 16l4-5 4 3 5-7"/></svg><span>Status</span>
    </button>
    <button type="button" data-view="doors">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 4h6v16h-6M13 4 5 2v20l8-2zM9 12h.01"/></svg><span>Dører</span>
    </button>
    <button type="button" data-view="bollards">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12M8 3v18h8V3M5 21h14M8 8h8"/></svg><span>Pullerter</span>
    </button>
    <button type="button" data-view="account">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 21a8 8 0 0 0-16 0M12 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8"/></svg><span>Konto</span>
    </button>
  </nav>
</body>
</html>"""
