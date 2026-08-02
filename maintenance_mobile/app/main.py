from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import time
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
MAINTENANCE_MOBILE_BUILD = os.getenv("MAINTENANCE_MOBILE_BUILD", "1465")
SESSION_COOKIE_NAME = "lilletorget_maintenance_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30
SESSION_SECRET = (
    os.getenv("MAINTENANCE_MOBILE_SESSION_SECRET")
    or os.getenv("PUBLIC_DASHBOARD_SESSION_SECRET")
    or os.getenv("PUBLIC_DASHBOARD_PASSWORD")
    or "change-this-maintenance-mobile-secret"
)

app = FastAPI(title="Lilletorget Vedlikehold", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="maintenance_mobile/app/static"), name="assets")


def json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def normalize_username(value: Any) -> str:
    return str(value or "").strip().casefold()


def b64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def sign_payload(payload: str) -> str:
    return hmac.new(SESSION_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def make_session_token(username: str, password: str) -> str:
    payload = {
        "u": normalize_username(username),
        "p": password,
        "iat": int(time.time()),
    }
    body = b64_encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return f"{body}.{sign_payload(body)}"


def read_session_token(token: str) -> Optional[tuple[str, str]]:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    if not hmac.compare_digest(sign_payload(body), signature):
        return None
    try:
        payload = json.loads(b64_decode(body).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None
    issued_at = int(payload.get("iat") or 0)
    if issued_at <= 0 or time.time() - issued_at > SESSION_MAX_AGE_SECONDS:
        return None
    username = normalize_username(payload.get("u"))
    password = str(payload.get("p") or "")
    if not username or not password:
        return None
    return username, password


def session_credentials(request: Request) -> Optional[tuple[str, str]]:
    return read_session_token(request.cookies.get(SESSION_COOKIE_NAME, ""))


def require_session(request: Request) -> tuple[str, str]:
    credentials = session_credentials(request)
    if not credentials:
        raise HTTPException(status_code=401, detail="Ikke innlogget")
    return credentials


def secure_cookie(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
    return request.url.scheme == "https" or forwarded_proto == "https"


def fibaro_request_sync(
    path: str,
    username: str,
    password: str,
    *,
    method: str = "GET",
    payload: Optional[dict[str, Any]] = None,
    timeout: int = 25,
) -> Any:
    data = None
    headers = {
        "Accept": "application/json",
        "X-Access-Username": username,
        "X-Access-Password": password,
        "User-Agent": "lilletorget-maintenance-mobile/1",
    }
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
    username: str,
    password: str,
    *,
    method: str = "GET",
    payload: Optional[dict[str, Any]] = None,
    timeout: int = 25,
) -> Any:
    return await asyncio.to_thread(
        fibaro_request_sync,
        path,
        username,
        password,
        method=method,
        payload=payload,
        timeout=timeout,
    )


def fibaro_binary_request_sync(
    path: str,
    username: str,
    password: str,
    *,
    timeout: int = 25,
) -> tuple[bytes, str]:
    request = UrlRequest(
        f"{FIBARO10_BASE_URL}{path}",
        headers={
            "Accept": "image/jpeg",
            "X-Access-Username": username,
            "X-Access-Password": password,
            "User-Agent": "lilletorget-maintenance-mobile/1",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read(), response.headers.get_content_type() or "image/jpeg"
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


async def fibaro_binary_request(
    path: str,
    username: str,
    password: str,
    *,
    timeout: int = 25,
) -> tuple[bytes, str]:
    return await asyncio.to_thread(
        fibaro_binary_request_sync,
        path,
        username,
        password,
        timeout=timeout,
    )


def mobile_bollard_camera_payload(payload: dict[str, Any], *, cropped: bool = False) -> dict[str, Any]:
    items = []
    monitors = [
        (monitor, "camera") for monitor in (payload.get("camera_monitors") or [])
    ] + [
        (monitor, "asset") for monitor in (payload.get("asset_monitors") or [])
    ]
    for monitor, monitor_kind in monitors:
        if not isinstance(monitor, dict) or not monitor.get("camera_id"):
            continue
        camera_id = str(monitor["camera_id"])
        encoded_id = quote(camera_id, safe="")
        asset_key = str(monitor.get("asset_key") or "")
        encoded_asset_key = quote(asset_key, safe="")
        crop = dict(monitor.get("display_crop") or {})
        crop["aspectRatio"] = round(
            float(crop.get("width") or 16) / float(crop.get("height") or 9),
            4,
        )
        images = {}
        for kind, source_key, stamp_key in (
            ("latest", "latest_url", "latest_captured_at"),
            ("overlay", "overlay_url", "latest_captured_at"),
            ("baseline", "baseline_url", "baseline_captured_at"),
        ):
            if monitor.get(source_key):
                stamp = quote(str(monitor.get(stamp_key) or "current"), safe="")
                if monitor_kind == "asset":
                    images[kind] = f"/api/bollards/assets/{encoded_asset_key}/{kind}?captured={stamp}"
                else:
                    crop_suffix = "/crop" if cropped else ""
                    images[kind] = f"/api/bollards/cameras/{encoded_id}/{kind}{crop_suffix}?captured={stamp}"
        items.append(
            {
                "cameraId": str(monitor.get("monitor_id") or camera_id),
                "cameraName": str(monitor.get("display_name") or monitor.get("camera_name") or camera_id),
                "itemType": str(monitor.get("item_type") or "bollards"),
                "status": str(monitor.get("status") or "unknown"),
                "lastCheckedAt": monitor.get("last_checked_at"),
                "latestCapturedAt": monitor.get("latest_captured_at"),
                "baselineCapturedAt": monitor.get("baseline_captured_at"),
                "changeScore": monitor.get("change_score"),
                "changedFraction": monitor.get("changed_fraction"),
                "lastError": monitor.get("last_error"),
                "crop": crop,
                "images": images,
            }
        )
    return {
        "comparisonMode": payload.get("comparison_mode"),
        "items": items,
    }


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
    recent_rows = maintenance_rows(module_payload)[:120]
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
            "name": "Lilletorget Vedlikehold",
            "short_name": "Vedlikehold",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#f4f7fb",
            "theme_color": "#0f766e",
            "icons": [
                {"src": "/static/lilletorget-favicon.png", "sizes": "512x512", "type": "image/png"},
            ],
        }
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not session_credentials(request):
        return RedirectResponse("/auth/login", status_code=303)
    return HTMLResponse(INDEX_HTML)


@app.get("/varsler", response_class=HTMLResponse)
async def notifications_page(request: Request):
    if not session_credentials(request):
        return RedirectResponse("/auth/login?next=/varsler", status_code=303)
    return HTMLResponse(INDEX_HTML)


@app.get("/auth/login", response_class=HTMLResponse)
async def login_view(request: Request):
    next_path = "/varsler" if request.query_params.get("next") == "/varsler" else "/"
    if session_credentials(request):
        return RedirectResponse(next_path, status_code=303)
    return HTMLResponse(login_html(next_path=next_path))


@app.post("/auth/login")
async def login_submit(request: Request):
    next_path = "/varsler" if request.query_params.get("next") == "/varsler" else "/"
    form = await request.form()
    username = normalize_username(form.get("username"))
    password = str(form.get("password") or "").strip()
    error = ""
    if not username or not password:
        error = "Brukernavn og passord må fylles ut."
    else:
        try:
            await fibaro_request("/api/auth/me", username, password, timeout=12)
        except HTTPException:
            error = "Ugyldig brukernavn eller passord."
    if error:
        return HTMLResponse(login_html(error, next_path=next_path), status_code=401)
    response = RedirectResponse(next_path, status_code=303)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        make_session_token(username, password),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=secure_cookie(request),
        samesite="lax",
    )
    return response


@app.post("/konto/logg-ut")
async def logout():
    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@app.get("/api/bootstrap")
async def api_bootstrap(request: Request):
    username, password = require_session(request)
    user_payload, module_payload = await asyncio.gather(
        fibaro_request("/api/auth/me", username, password),
        fibaro_request("/api/modules/vedlikehold", username, password),
    )
    renhold_payload = None
    try:
        renhold_payload = await fibaro_request("/api/modules/renhold", username, password)
    except HTTPException:
        renhold_payload = None
    return bootstrap_payload(module_payload, user_payload, renhold_payload)


@app.post("/api/maintenance/logs")
async def api_create_maintenance_log(request: Request):
    username, password = require_session(request)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Ugyldig payload")
    result = await fibaro_request("/api/maintenance/logs", username, password, method="POST", payload=payload)
    return result


@app.patch("/api/maintenance/logs/{log_id}")
async def api_update_maintenance_log(request: Request, log_id: int):
    username, password = require_session(request)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Ugyldig payload")
    module_payload = await fibaro_request("/api/modules/vedlikehold", username, password)
    existing = maintenance_row_by_id(module_payload, log_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Vedlikeholdsposten finnes ikke")
    if normalize_username(existing.get("performed_by")) != normalize_username(username):
        raise HTTPException(status_code=403, detail="Du kan bare redigere egne vedlikeholdsposter")
    payload["performed_by"] = existing.get("performed_by") or username
    result = await fibaro_request(f"/api/maintenance/logs/{log_id}", username, password, method="PATCH", payload=payload)
    return result


@app.get("/api/notifications")
async def api_notifications(request: Request):
    username, password = require_session(request)
    return await fibaro_request(
        "/api/unifi-protect/bollards/mobile-notifications",
        username,
        password,
    )


@app.post("/api/notifications/bollards/test")
async def api_test_bollard_notification(request: Request):
    username, password = require_session(request)
    return await fibaro_request(
        "/api/unifi-protect/bollards/mobile-notifications/test",
        username,
        password,
        method="POST",
    )


@app.get("/api/bollards/cameras")
async def api_bollard_cameras(request: Request, geometry: str = ""):
    username, password = require_session(request)
    payload = await fibaro_request("/api/unifi-protect/bollards", username, password)
    return mobile_bollard_camera_payload(
        payload,
        cropped=geometry == "fixed_source_pixel_crop",
    )


@app.get("/api/bollards/cameras/{camera_id}/{kind}")
async def api_bollard_camera_image(request: Request, camera_id: str, kind: str):
    username, password = require_session(request)
    if kind not in {"baseline", "latest", "overlay"}:
        raise HTTPException(status_code=400, detail="Ukjent bildetype")
    encoded_id = quote(camera_id, safe="")
    content, content_type = await fibaro_binary_request(
        f"/api/unifi-protect/bollards/cameras/{encoded_id}/{kind}",
        username,
        password,
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "private, no-store"},
    )


@app.get("/api/bollards/cameras/{camera_id}/{kind}/crop")
async def api_bollard_camera_crop(request: Request, camera_id: str, kind: str):
    username, password = require_session(request)
    if kind not in {"baseline", "latest", "overlay"}:
        raise HTTPException(status_code=400, detail="Ukjent bildetype")
    encoded_id = quote(camera_id, safe="")
    content, content_type = await fibaro_binary_request(
        f"/api/unifi-protect/bollards/cameras/{encoded_id}/{kind}/crop",
        username,
        password,
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "private, no-store"},
    )


@app.get("/api/bollards/assets/{asset_key}/{kind}")
async def api_bollard_asset_image(request: Request, asset_key: str, kind: str):
    username, password = require_session(request)
    if kind not in {"baseline", "latest", "overlay"}:
        raise HTTPException(status_code=400, detail="Ukjent bildetype")
    encoded_asset_key = quote(asset_key, safe="")
    content, content_type = await fibaro_binary_request(
        f"/api/unifi-protect/bollards/assets/{encoded_asset_key}/{kind}",
        username,
        password,
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "private, no-store"},
    )


def login_html(error: str = "", *, next_path: str = "/") -> str:
    error_html = f'<div class="login-error">{escape(error)}</div>' if error else ""
    login_action = "/auth/login?next=/varsler" if next_path == "/varsler" else "/auth/login"
    return f"""<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Logg inn · Vedlikehold</title>
  <link rel="icon" type="image/png" href="/static/lilletorget-favicon.png">
  <link rel="stylesheet" href="/assets/maintenance-mobile.css?v=1465">
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
  <meta name="theme-color" content="#0f766e">
  <title>Lilletorget Vedlikehold</title>
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="icon" type="image/png" href="/static/lilletorget-favicon.png">
  <link rel="stylesheet" href="/assets/maintenance-mobile.css?v=1465">
  <script src="/assets/maintenance-mobile.js?v=1465" defer></script>
</head>
<body>
  <header class="app-topbar">
    <div class="brand-logo">
      <img src="/static/lilletorget-mark.png" alt="">
    </div>
    <strong class="brand-title">Lilletorget, <span>vedlikehold</span></strong>
    <button id="notificationsButton" class="user-button notification-button" type="button" title="Varsler" aria-label="Åpne varselabonnementer">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg>
    </button>
    <button id="profileButton" class="user-button" type="button" title="Bruker" aria-label="Åpne brukerprofil">
        <span id="topUserInitial" class="user-initial" aria-hidden="true">?</span>
    </button>
  </header>
  <main class="app-shell">
    <section id="taskScreen" class="screen">
      <section class="task-hero">
        <h1>Hva skal registreres?</h1>
      </section>

      <a class="notification-entry" href="/varsler">
        <span class="notification-entry-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg>
        </span>
        <span class="notification-entry-copy"><strong>Pullert- og trappevarsler</strong><small>Abonner og send testvarsel</small></span>
        <span class="notification-entry-arrow" aria-hidden="true">›</span>
      </a>

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

        <button id="submitButton" class="primary-button" type="submit">Lagre</button>
        <p id="formMessage" class="form-message" role="status"></p>
      </form>
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

    <section id="notificationsScreen" class="screen is-hidden">
      <section class="entry-head sub-topbar notifications-head">
        <button id="notificationsBackButton" class="back-button" type="button" aria-label="Tilbake">
          <img src="/static/lilletorget-mark.png" alt="">
        </button>
        <div class="entry-title-block">
          <h1>Varsler</h1>
          <p class="entry-user-line">Abonnement på mobilvarsler</p>
        </div>
        <span class="sub-topbar-spacer" aria-hidden="true"></span>
      </section>

      <section class="notification-card">
        <div class="notification-card-head">
          <div>
            <p class="eyebrow">Overvåking</p>
            <h2>Pullerter og trapp ved Solstudio</h2>
          </div>
          <span id="bollardNotificationBadge" class="status-pill is-loading">Henter</span>
        </div>
        <p id="bollardNotificationSummary" class="notification-summary">Henter status fra Protect Ledger...</p>
        <dl class="notification-details">
          <div><dt>Overvåking</dt><dd id="bollardMonitoringStatus">–</dd></div>
          <div><dt>Siste kontroll</dt><dd id="bollardLastCheck">–</dd></div>
          <div><dt>Aktive avvik</dt><dd id="bollardActiveIncidents">–</dd></div>
        </dl>
        <a id="bollardSubscribeLink" class="subscription-button is-disabled" href="#" aria-disabled="true">Abonner på varsler</a>
        <button id="bollardTestButton" class="test-notification-button" type="button" disabled>Send testvarsel</button>
        <a id="bollardWebLink" class="channel-web-link is-hidden" href="#" target="_blank" rel="noopener">Åpne varselkanalen i nettleser</a>
        <p id="notificationMessage" class="form-message notification-message" role="status"></p>
        <p id="bollardPrivacy" class="privacy-note">Kun alarmtekst sendes. Bilder, registreringsnummer og analysedata forblir lokale.</p>
      </section>

      <section class="camera-inspection-card">
        <div class="camera-inspection-head">
          <div>
            <p class="eyebrow">Kamerainspeksjon</p>
            <h2>Referanse og siste bilde</h2>
          </div>
          <button id="refreshBollardCameras" class="camera-refresh-button" type="button">Oppdater</button>
        </div>
        <p class="camera-inspection-intro">Referanse og siste bilde har opptakstid på hver sin side av skyveren. Begge står fast i nøyaktig samme kontrollutsnitt.</p>
        <div id="bollardCameraList" class="bollard-camera-list" aria-live="polite"></div>
        <p id="bollardCameraMessage" class="form-message" role="status">Henter kamerabilder...</p>
      </section>

      <section class="notification-help">
        <h2>Slik kobler du til</h2>
        <ol>
          <li>Installer ntfy-appen og tillat varsler.</li>
          <li>Trykk «Abonner på varsler» over.</li>
          <li>Kom tilbake hit og send et testvarsel.</li>
        </ol>
        <p>Dette abonnementet er separat fra dørvarsler.</p>
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
      <div id="recentList" class="recent-list"></div>
    </section>
  </main>
</body>
</html>"""
