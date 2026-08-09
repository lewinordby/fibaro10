from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from microapp_backend import PwaConfig, inject_pwa_head, register_pwa, render_login_page
from microapp_backend.auth import AUTH_SESSION_COOKIE_NAME, clear_auth_cookies, forwarded_auth_headers
from microapp_backend.pwa import PWA_ICON_PATH


FIBARO10_BASE_URL = os.getenv("FIBARO10_BASE_URL", "http://fibaro10:8110").rstrip("/")
SHELL_APP_URL = os.getenv("SHELL_APP_URL", "https://app.lilletorget.net").rstrip("/")


def shell_app_path(path: str) -> str:
    return f"{SHELL_APP_URL}/{path.strip('/')}/"


REVENUE_BASE_URL = os.getenv("REVENUE_BASE_URL", "http://revenue_app:8151").rstrip("/")
REVENUE_APP_URL = shell_app_path("omsetning")
PARKING_BASE_URL = os.getenv("PARKING_BASE_URL", "http://parking_app:8152").rstrip("/")
PARKING_APP_URL = shell_app_path("parkering")
SUN_BASE_URL = os.getenv("SUN_BASE_URL", "http://sun_app:8153").rstrip("/")
SUN_APP_URL = shell_app_path("soling")
ENERGY_BASE_URL = os.getenv("ENERGY_BASE_URL", "http://energy_app:8154").rstrip("/")
ENERGY_APP_URL = shell_app_path("energi")
OPERATIONS_BASE_URL = os.getenv("OPERATIONS_BASE_URL", "http://operations_app:8155").rstrip("/")
OPERATIONS_APP_URL = shell_app_path("drift")
MAINTENANCE_BASE_URL = os.getenv("MAINTENANCE_BASE_URL", "http://maintenance_app:8156").rstrip("/")
MAINTENANCE_APP_URL = shell_app_path("vedlikehold")
SYSTEM_BASE_URL = os.getenv("SYSTEM_BASE_URL", "http://system_app:8157").rstrip("/")
SYSTEM_APP_URL = shell_app_path("system")
LINK_BASE_URL = os.getenv("LINK_BASE_URL", "http://link_app:8158").rstrip("/")
LINK_APP_URL = shell_app_path("koble")
BUILD_FILE = Path(__file__).resolve().parents[1] / "BUILD"
DEFAULT_BUILD = BUILD_FILE.read_text(encoding="utf-8").strip() if BUILD_FILE.exists() else "1"
APP_BUILD = os.getenv("SHELL_APP_BUILD", DEFAULT_BUILD)
APP_COMMIT = os.getenv("SHELL_APP_COMMIT", os.getenv("APP_COMMIT", "unknown"))
STATIC_DIR = Path(__file__).resolve().parent / "static" / "dist"
PWA = PwaConfig(
    name="Lilletorget",
    short_name="Lilletorget",
    description="Appvelger og samlet inngang til Lilletorget-systemet.",
    theme_color="#4f46e5",
    categories=("business", "productivity", "utilities"),
)


APP_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "revenue",
        "name": "Omsetning",
        "category": "Økonomi",
        "description": "Dashboard, utvikling og sammenligning av omsetning.",
        "url": REVENUE_APP_URL,
        "healthUrl": f"{REVENUE_BASE_URL}/health",
        "tone": "revenue",
        "icon": "chart",
        "available": True,
    },
    {
        "id": "parking",
        "name": "Parkering",
        "category": "Økonomi",
        "description": "Parkeringer, kjøretøy, oppgjør og analyse.",
        "url": PARKING_APP_URL,
        "healthUrl": f"{PARKING_BASE_URL}/health",
        "tone": "parking",
        "icon": "parking",
        "available": True,
    },
    {"id": "sun", "name": "Soling", "category": "Økonomi", "description": "Soltimer, produkter, bilder og oppgjør.", "url": SUN_APP_URL, "healthUrl": f"{SUN_BASE_URL}/health", "tone": "sun", "icon": "sun", "available": True},
    {"id": "link", "name": "Koble", "category": "Økonomi", "description": "Kandidater og kontroll av kjøretøy mot Sun2-ID.", "url": LINK_APP_URL, "healthUrl": f"{LINK_BASE_URL}/health", "tone": "revenue", "icon": "link", "available": True},
    {"id": "energy", "name": "Energi", "category": "Bygg og drift", "description": "Forbruk, målere og kursstruktur.", "url": ENERGY_APP_URL, "healthUrl": f"{ENERGY_BASE_URL}/health", "tone": "energy", "icon": "energy", "available": True},
    {"id": "operations", "name": "Bygg og drift", "category": "Bygg og drift", "description": "Ventilasjon, lys, dører, pullerter og renhold.", "url": OPERATIONS_APP_URL, "healthUrl": f"{OPERATIONS_BASE_URL}/health", "tone": "operations", "icon": "building", "available": True},
    {"id": "maintenance", "name": "Vedlikehold", "category": "Bygg og drift", "description": "Besøk, oppgaver og historikk.", "url": MAINTENANCE_APP_URL, "healthUrl": f"{MAINTENANCE_BASE_URL}/health", "tone": "maintenance", "icon": "tools", "available": True},
    {"id": "system", "name": "System", "category": "Administrasjon", "description": "Datakilder, manual, build og systemstatus.", "url": SYSTEM_APP_URL, "healthUrl": f"{SYSTEM_BASE_URL}/health", "tone": "system", "icon": "settings", "available": True},
]


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    application.state.http = httpx.AsyncClient(
        timeout=httpx.Timeout(8.0, connect=3.0),
        follow_redirects=False,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    yield
    await application.state.http.aclose()


app = FastAPI(title="Lilletorget", docs_url=None, redoc_url=None, lifespan=lifespan)
register_pwa(app, PWA)
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


def forwarded_headers(request: Request, *, accept: str = "application/json") -> dict[str, str]:
    return forwarded_auth_headers(request, accept=accept, user_agent="lilletorget-shell/1")


async def current_user(request: Request) -> dict[str, Any]:
    if not request.cookies.get(AUTH_SESSION_COOKIE_NAME):
        raise HTTPException(status_code=401, detail="Innlogging kreves")
    client: httpx.AsyncClient = request.app.state.http
    try:
        response = await client.get(f"{FIBARO10_BASE_URL}/api/auth/me", headers=forwarded_headers(request))
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="Innloggingstjenesten er ikke tilgjengelig") from exc
    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Innlogging kreves")
    if response.is_error:
        raise HTTPException(status_code=502, detail="Kunne ikke validere innlogging")
    return response.json()


async def probe(application: FastAPI, definition: dict[str, Any]) -> dict[str, Any]:
    result = {key: value for key, value in definition.items() if key != "healthUrl"}
    if not definition["available"]:
        return {**result, "status": "planned", "statusText": "Planlagt", "build": None}
    client: httpx.AsyncClient = application.state.http
    try:
        response = await client.get(definition["healthUrl"])
        response.raise_for_status()
        payload = response.json()
        healthy = bool(payload.get("ok", payload.get("status") == "ok"))
        return {
            **result,
            "status": "ok" if healthy else "warning",
            "statusText": "Klar" if healthy else "Sjekk status",
            "build": str(payload.get("build") or payload.get("app", {}).get("build") or "-"),
        }
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError):
        return {**result, "status": "down", "statusText": "Ikke tilgjengelig", "build": None}


@app.middleware("http")
async def response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path.startswith("/assets/"):
        response.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
    return response


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "service": "shell_app", "build": APP_BUILD, "commit": APP_COMMIT}


@app.get("/ready")
async def ready(request: Request) -> JSONResponse:
    client: httpx.AsyncClient = request.app.state.http
    try:
        response = await client.get(f"{FIBARO10_BASE_URL}/health")
        response.raise_for_status()
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        return JSONResponse({"ok": False, "service": "shell_app", "auth": str(exc)}, status_code=503)
    return JSONResponse({"ok": True, "service": "shell_app", "auth": "ready"})


@app.get("/favicon.ico")
async def favicon() -> FileResponse:
    return FileResponse(PWA_ICON_PATH, media_type="image/png")


@app.get("/api/app/config")
async def app_config() -> dict[str, str]:
    return {"name": "Lilletorget", "build": APP_BUILD, "shellUrl": SHELL_APP_URL}


@app.get("/api/auth/me")
async def auth_me(request: Request) -> dict[str, Any]:
    return await current_user(request)


@app.get("/api/apps")
async def apps(request: Request) -> dict[str, Any]:
    await current_user(request)
    rows = await asyncio.gather(*(probe(request.app, definition) for definition in APP_DEFINITIONS))
    active = [row for row in rows if row["available"]]
    return {
        "apps": rows,
        "summary": {
            "available": len(active),
            "healthy": sum(1 for row in active if row["status"] == "ok"),
            "planned": sum(1 for row in rows if not row["available"]),
        },
    }


@app.get("/auth/login", response_class=HTMLResponse)
async def login_view(request: Request) -> Response:
    if request.cookies.get(AUTH_SESSION_COOKIE_NAME):
        try:
            await current_user(request)
        except HTTPException as exc:
            if exc.status_code != 401:
                return HTMLResponse(login_html("Innloggingstjenesten er ikke tilgjengelig."), status_code=502)
            response = HTMLResponse(login_html("Økten er utløpt. Logg inn på nytt."))
            clear_auth_cookies(response, request)
            return response
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(login_html())


@app.post("/auth/login")
async def login_submit(request: Request) -> Response:
    body = await request.body()
    client: httpx.AsyncClient = request.app.state.http
    try:
        core_response = await client.post(
            f"{FIBARO10_BASE_URL}/auth/login",
            content=body,
            headers={**forwarded_headers(request, accept="text/html"), "Content-Type": request.headers.get("content-type", "application/x-www-form-urlencoded")},
        )
    except httpx.RequestError:
        return HTMLResponse(login_html("Innloggingstjenesten er ikke tilgjengelig."), status_code=502)
    if core_response.status_code not in {302, 303, 307, 308}:
        return HTMLResponse(login_html("Ugyldig brukernavn eller passord."), status_code=401)
    response = RedirectResponse("/", status_code=303)
    for cookie in core_response.headers.get_list("set-cookie"):
        response.headers.append("set-cookie", cookie)
    return response


@app.post("/konto/logg-ut")
async def logout(request: Request) -> RedirectResponse:
    client: httpx.AsyncClient = request.app.state.http
    try:
        await client.delete(f"{FIBARO10_BASE_URL}/api/auth/session", headers=forwarded_headers(request))
    except httpx.RequestError:
        pass
    response = RedirectResponse("/auth/login", status_code=303)
    clear_auth_cookies(response, request)
    return response


def index_html() -> str:
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return inject_pwa_head(
            "<!doctype html><html lang='no'><head><title>Frontend mangler</title></head><body><h1>Frontend er ikke bygget</h1></body></html>",
            PWA,
        )
    return inject_pwa_head(index_path.read_text(encoding="utf-8"), PWA)


@app.get("/{path:path}", response_class=HTMLResponse)
async def frontend(path: str, request: Request) -> Response:
    if not request.cookies.get(AUTH_SESSION_COOKIE_NAME):
        return RedirectResponse("/auth/login", status_code=303)
    return HTMLResponse(index_html())


def login_html(error: str = "") -> str:
    return render_login_page(app_name="Apper", build=APP_BUILD, pwa=PWA, error=error)
