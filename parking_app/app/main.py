from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles


FIBARO10_BASE_URL = os.getenv("FIBARO10_BASE_URL", "http://fibaro10:8110").rstrip("/")
FIBARO10_APP_URL = os.getenv("FIBARO10_APP_URL", "http://192.168.20.218:8110").rstrip("/")
SHELL_APP_URL = os.getenv("SHELL_APP_URL", "http://192.168.20.218:8150").rstrip("/")
BUILD_FILE = Path(__file__).resolve().parents[1] / "BUILD"
DEFAULT_BUILD = BUILD_FILE.read_text(encoding="utf-8").strip() if BUILD_FILE.exists() else "1"
APP_BUILD = os.getenv("PARKING_APP_BUILD", DEFAULT_BUILD)
APP_COMMIT = os.getenv("PARKING_APP_COMMIT", os.getenv("APP_COMMIT", "unknown"))
APP_STARTED_AT = os.getenv("PARKING_APP_STARTED_AT", "runtime")
AUTH_USER_COOKIE_NAME = "fibaro10_access_username"
AUTH_COOKIE_NAME = "fibaro10_access_password"
STATIC_DIR = Path(__file__).resolve().parent / "static" / "dist"

ALLOWED_CORE_GET_PATHS = {
    "auth/me",
    "modules/parkering",
    "parkering/year-comparison",
    "parkering/time-distribution",
    "parkering/weekly-averages",
    "parkering/weekly-averages/years",
}
ALLOWED_CORE_GET_PATTERNS = (
    re.compile(r"parking/vehicles/[a-z0-9-]+"),
    re.compile(r"settlements/\d+"),
    re.compile(r"settlements/\d+/attachment"),
)
ALLOWED_CORE_POST_PATHS = {
    "actions/parkering/fetch-settlements",
    "actions/parkering/save-forecast",
    "actions/parkering/refresh",
    "actions/parkering/svv-sync",
    "actions/parkering/car-info-sync",
    "actions/parkering/clear-area-not-found",
}
ALLOWED_CORE_POST_PATTERNS = (re.compile(r"parking/vehicles/[a-z0-9-]+/clear-not-found"),)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    application.state.core_client = httpx.AsyncClient(
        base_url=FIBARO10_BASE_URL,
        timeout=httpx.Timeout(35.0, connect=8.0),
        follow_redirects=False,
        limits=httpx.Limits(max_connections=30, max_keepalive_connections=10),
    )
    yield
    await application.state.core_client.aclose()


app = FastAPI(title="Lilletorget Parkering", docs_url=None, redoc_url=None, lifespan=lifespan)
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


def secure_cookie(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
    return request.url.scheme == "https" or forwarded_proto == "https"


def forwarded_headers(request: Request, *, accept: str = "application/json") -> dict[str, str]:
    headers = {
        "Accept": accept,
        "User-Agent": "lilletorget-parking-app/1",
    }
    cookie = request.headers.get("cookie")
    if cookie:
        headers["Cookie"] = cookie
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        headers["X-Forwarded-For"] = forwarded_for
    elif request.client:
        headers["X-Forwarded-For"] = request.client.host
    return headers


async def core_get(request: Request, path: str) -> httpx.Response:
    client: httpx.AsyncClient = request.app.state.core_client
    try:
        return await client.get(f"/{path}", params=request.query_params, headers=forwarded_headers(request))
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Fibaro10 er ikke tilgjengelig: {exc}") from exc


async def core_post(request: Request, path: str) -> httpx.Response:
    client: httpx.AsyncClient = request.app.state.core_client
    headers = forwarded_headers(request)
    if content_type := request.headers.get("content-type"):
        headers["Content-Type"] = content_type
    try:
        return await client.post(f"/{path}", params=request.query_params, content=await request.body(), headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Fibaro10 er ikke tilgjengelig: {exc}") from exc


def proxy_response(response: httpx.Response) -> Response:
    headers: dict[str, str] = {}
    for name in ("cache-control", "etag", "last-modified", "content-disposition"):
        value = response.headers.get(name)
        if value:
            headers[name] = value
    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("content-type", "application/json").split(";", 1)[0],
        headers=headers,
    )


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
async def health() -> dict[str, object]:
    return {
        "ok": True,
        "service": "parking_app",
        "build": APP_BUILD,
        "commit": APP_COMMIT,
        "startedAt": APP_STARTED_AT,
    }


@app.get("/ready")
async def ready(request: Request) -> JSONResponse:
    client: httpx.AsyncClient = request.app.state.core_client
    try:
        response = await client.get("/health", timeout=8.0)
        response.raise_for_status()
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        return JSONResponse({"ok": False, "service": "parking_app", "core": str(exc)}, status_code=503)
    return JSONResponse({"ok": True, "service": "parking_app", "core": "ready"})


@app.get("/favicon.ico")
async def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/app/config")
async def app_config() -> dict[str, str]:
    return {
        "name": "Lilletorget Parkering",
        "build": APP_BUILD,
        "commit": APP_COMMIT,
        "fibaro10AppUrl": FIBARO10_APP_URL,
        "shellAppUrl": SHELL_APP_URL,
    }


@app.api_route("/api/{core_path:path}", methods=["GET", "POST"])
async def proxy_core_api(core_path: str, request: Request) -> Response:
    normalized = core_path.strip("/").casefold()
    if request.method == "GET":
        allowed = normalized in ALLOWED_CORE_GET_PATHS or any(pattern.fullmatch(normalized) for pattern in ALLOWED_CORE_GET_PATTERNS)
        if not allowed:
            raise HTTPException(status_code=404, detail="Endepunktet er ikke tilgjengelig i parkeringsappen")
        return proxy_response(await core_get(request, f"api/{normalized}"))
    allowed = normalized in ALLOWED_CORE_POST_PATHS or any(pattern.fullmatch(normalized) for pattern in ALLOWED_CORE_POST_PATTERNS)
    if not allowed:
        raise HTTPException(status_code=404, detail="Handlingen er ikke tilgjengelig i parkeringsappen")
    return proxy_response(await core_post(request, f"api/{normalized}"))


@app.get("/auth/login", response_class=HTMLResponse)
async def login_view(request: Request) -> Response:
    if request.cookies.get(AUTH_USER_COOKIE_NAME) and request.cookies.get(AUTH_COOKIE_NAME):
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(login_html())


@app.post("/auth/login")
async def login_submit(request: Request) -> Response:
    body = await request.body()
    client: httpx.AsyncClient = request.app.state.core_client
    try:
        core_response = await client.post(
            "/auth/login",
            content=body,
            headers={
                **forwarded_headers(request, accept="text/html"),
                "Content-Type": request.headers.get("content-type", "application/x-www-form-urlencoded"),
            },
        )
    except httpx.RequestError:
        return HTMLResponse(login_html("Fibaro10 er ikke tilgjengelig akkurat nå."), status_code=502)

    if core_response.status_code not in {302, 303, 307, 308}:
        return HTMLResponse(login_html("Ugyldig brukernavn eller passord."), status_code=401)

    response = RedirectResponse("/", status_code=303)
    for cookie in core_response.headers.get_list("set-cookie"):
        response.headers.append("set-cookie", cookie)
    return response


@app.post("/konto/logg-ut")
async def logout(request: Request) -> RedirectResponse:
    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie(AUTH_USER_COOKIE_NAME, secure=secure_cookie(request), samesite="lax")
    response.delete_cookie(AUTH_COOKIE_NAME, secure=secure_cookie(request), samesite="lax")
    return response


def index_html() -> str:
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return "<!doctype html><html lang='no'><body><h1>Frontend er ikke bygget</h1></body></html>"
    return index_path.read_text(encoding="utf-8")


@app.get("/{path:path}", response_class=HTMLResponse)
async def frontend(path: str, request: Request) -> Response:
    if not request.cookies.get(AUTH_USER_COOKIE_NAME) or not request.cookies.get(AUTH_COOKIE_NAME):
        return RedirectResponse("/auth/login", status_code=303)
    return HTMLResponse(index_html())


def login_html(error: str = "") -> str:
    index = index_html()
    match = re.search(r'href="(/assets/[^"]+\.css)"', index)
    css_href = match.group(1) if match else ""
    error_html = f'<div class="mt-5 rounded-lg bg-red-500/20 px-3 py-2 text-sm text-red-700">{error}</div>' if error else ""
    return f"""<!doctype html>
<html lang="no"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><title>Logg inn - Parkering</title><link rel="stylesheet" href="{css_href}"></head>
<body class="font-inter antialiased bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400">
<main class="bg-white dark:bg-gray-900"><div class="flex min-h-[100dvh] flex-col justify-center"><div class="mx-auto w-full max-w-sm px-4 py-8">
<h1 class="mb-2 text-3xl font-bold text-gray-800 dark:text-gray-100">Parkering</h1><p class="mb-6 text-sm text-gray-500 dark:text-gray-400">Bruk samme konto som i Fibaro10.</p>
<form method="post" action="/auth/login"><div class="space-y-4"><div><label class="mb-1 block text-sm font-medium" for="username">Brukernavn</label><input id="username" class="form-input w-full" name="username" autocomplete="username" autofocus required></div><div><label class="mb-1 block text-sm font-medium" for="password">Passord</label><input id="password" class="form-input w-full" type="password" name="password" autocomplete="current-password" required></div></div>{error_html}<div class="mt-6 flex justify-end"><button class="btn bg-gray-900 text-gray-100 hover:bg-gray-800 dark:bg-gray-100 dark:text-gray-800 dark:hover:bg-white" type="submit">Logg inn</button></div></form>
</div></div></main></body></html>"""
