from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Pattern

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .auth import AUTH_SESSION_COOKIE_NAME, clear_auth_cookies, forwarded_auth_headers
from .pwa import PWA_ICON_PATH, PwaConfig, inject_pwa_head, pwa_head_tags, register_pwa


PROXY_METHODS = ("GET", "POST", "PATCH", "PUT", "DELETE")
ProxyAdapter = Callable[[Request, httpx.AsyncClient, dict[str, str]], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class DomainAppConfig:
    name: str
    short_name: str
    service: str
    build_env: str
    commit_env: str
    app_dir: Path
    port: int
    allowed_paths: dict[str, set[str]] = field(default_factory=dict)
    allowed_patterns: dict[str, tuple[Pattern[str], ...]] = field(default_factory=dict)
    resource_patterns: tuple[Pattern[str], ...] = field(default_factory=tuple)
    adapters: dict[str, ProxyAdapter] = field(default_factory=dict)
    pwa_description: str = "Operativ arbeidsflate for Lilletorget."
    pwa_theme_color: str = "#4f46e5"
    pwa_background_color: str = "#f8fafc"
    pwa_categories: tuple[str, ...] = ("business", "productivity")

    def build(self) -> str:
        build_file = self.app_dir / "BUILD"
        fallback = build_file.read_text(encoding="utf-8").strip() if build_file.exists() else "1"
        return os.getenv(self.build_env, fallback)


def create_domain_app(config: DomainAppConfig) -> FastAPI:
    core_base_url = os.getenv("FIBARO10_BASE_URL", "http://fibaro10:8110").rstrip("/")
    core_app_url = os.getenv("FIBARO10_APP_URL", "http://192.168.20.218:8110").rstrip("/")
    shell_app_url = os.getenv("SHELL_APP_URL", "http://192.168.20.218:8150").rstrip("/")
    build = config.build()
    commit = os.getenv(config.commit_env, os.getenv("APP_COMMIT", "unknown"))
    started_at = os.getenv(f"{config.service.upper()}_STARTED_AT", "runtime")
    static_dir = config.app_dir / "app" / "static" / "dist"
    pwa = PwaConfig(
        name=config.name,
        short_name=config.short_name,
        description=config.pwa_description,
        theme_color=config.pwa_theme_color,
        background_color=config.pwa_background_color,
        categories=config.pwa_categories,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.core_client = httpx.AsyncClient(
            base_url=core_base_url,
            timeout=httpx.Timeout(45.0, connect=8.0),
            follow_redirects=False,
            limits=httpx.Limits(max_connections=30, max_keepalive_connections=10),
        )
        yield
        await application.state.core_client.aclose()

    app = FastAPI(title=config.name, docs_url=None, redoc_url=None, lifespan=lifespan)
    register_pwa(app, pwa)
    app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)
    if static_dir.exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    def forwarded_headers(request: Request, *, accept: str = "application/json") -> dict[str, str]:
        return forwarded_auth_headers(request, accept=accept, user_agent=f"lilletorget-{config.service}/1")

    async def core_request(request: Request, path: str) -> httpx.Response:
        client: httpx.AsyncClient = request.app.state.core_client
        try:
            return await client.request(
                request.method,
                f"/{path}",
                params=request.query_params,
                content=await request.body() if request.method != "GET" else None,
                headers=forwarded_headers(request),
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Fibaro10 er ikke tilgjengelig: {exc}") from exc

    def proxy_response(response: httpx.Response) -> Response:
        headers = {
            name: value
            for name in ("cache-control", "etag", "last-modified", "content-disposition")
            if (value := response.headers.get(name))
        }
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "application/json").split(";", 1)[0],
            headers=headers,
        )

    def path_allowed(method: str, path: str) -> bool:
        normalized_method = method.upper()
        if path in config.allowed_paths.get(normalized_method, set()):
            return True
        return any(pattern.fullmatch(path) for pattern in config.allowed_patterns.get(normalized_method, ()))

    @lru_cache(maxsize=1)
    def index_html() -> str:
        index_path = static_dir / "index.html"
        if not index_path.exists():
            return inject_pwa_head(
                "<!doctype html><html lang='no'><head><title>Frontend mangler</title></head><body><h1>Frontend er ikke bygget</h1></body></html>",
                pwa,
            )
        return inject_pwa_head(index_path.read_text(encoding="utf-8"), pwa)

    def login_html(error: str = "") -> str:
        match = re.search(r'href="(/assets/[^"]+\.css)"', index_html())
        css_href = match.group(1) if match else ""
        error_html = f'<div class="mt-5 rounded-lg bg-red-500/20 px-3 py-2 text-sm text-red-700">{error}</div>' if error else ""
        return f"""<!doctype html>
<html lang="no"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><title>Logg inn - {config.short_name}</title>{pwa_head_tags(pwa)}<link rel="stylesheet" href="{css_href}"></head>
<body class="font-inter antialiased bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400">
<main class="bg-white dark:bg-gray-900"><div class="flex min-h-[100dvh] flex-col justify-center"><div class="mx-auto w-full max-w-sm px-4 py-8">
<h1 class="mb-2 text-3xl font-bold text-gray-800 dark:text-gray-100">{config.short_name}</h1><p class="mb-6 text-sm text-gray-500 dark:text-gray-400">Bruk samme konto som i Fibaro10.</p>
<form method="post" action="/auth/login"><div class="space-y-4"><div><label class="mb-1 block text-sm font-medium" for="username">Brukernavn</label><input id="username" class="form-input w-full" name="username" autocomplete="username" autofocus required></div><div><label class="mb-1 block text-sm font-medium" for="password">Passord</label><input id="password" class="form-input w-full" type="password" name="password" autocomplete="current-password" required></div></div>{error_html}<div class="mt-6 flex justify-end"><button class="btn bg-gray-900 text-gray-100 hover:bg-gray-800 dark:bg-gray-100 dark:text-gray-800 dark:hover:bg-white" type="submit">Logg inn</button></div></form>
</div></div></main></body></html>"""

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
        return {"ok": True, "service": config.service, "build": build, "commit": commit, "startedAt": started_at}

    @app.get("/ready")
    async def ready(request: Request) -> JSONResponse:
        client: httpx.AsyncClient = request.app.state.core_client
        try:
            response = await client.get("/health", timeout=8.0)
            response.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            return JSONResponse({"ok": False, "service": config.service, "core": str(exc)}, status_code=503)
        return JSONResponse({"ok": True, "service": config.service, "core": "ready"})

    @app.get("/favicon.ico")
    async def favicon() -> FileResponse:
        return FileResponse(PWA_ICON_PATH, media_type="image/png")

    @app.get("/api/app/config")
    async def app_config() -> dict[str, str]:
        return {"name": config.name, "build": build, "commit": commit, "fibaro10AppUrl": core_app_url, "shellAppUrl": shell_app_url}

    @app.api_route("/api/{core_path:path}", methods=list(PROXY_METHODS))
    async def proxy_core_api(core_path: str, request: Request) -> Response:
        clean_path = core_path.strip("/")
        normalized = clean_path.casefold()
        if request.method == "GET" and normalized in config.adapters:
            client: httpx.AsyncClient = request.app.state.core_client
            try:
                payload = await config.adapters[normalized](request, client, forwarded_headers(request))
            except httpx.HTTPStatusError as exc:
                return proxy_response(exc.response)
            except httpx.RequestError as exc:
                raise HTTPException(status_code=502, detail=f"Fibaro10 er ikke tilgjengelig: {exc}") from exc
            return JSONResponse(payload)
        if not path_allowed(request.method, normalized):
            raise HTTPException(status_code=404, detail=f"Endepunktet er ikke tilgjengelig i {config.short_name}")
        return proxy_response(await core_request(request, f"api/{clean_path}"))

    @app.get("/auth/login", response_class=HTMLResponse)
    async def login_view(request: Request) -> Response:
        if request.cookies.get(AUTH_SESSION_COOKIE_NAME):
            client: httpx.AsyncClient = request.app.state.core_client
            try:
                validation = await client.get("/api/auth/me", headers=forwarded_headers(request))
            except httpx.RequestError:
                return HTMLResponse(login_html("Fibaro10 er ikke tilgjengelig akkurat nå."), status_code=502)
            if validation.status_code == 200:
                return RedirectResponse("/", status_code=303)
            response = HTMLResponse(login_html("Økten er utløpt. Logg inn på nytt."))
            clear_auth_cookies(response, request)
            return response
        return HTMLResponse(login_html())

    @app.post("/auth/login")
    async def login_submit(request: Request) -> Response:
        client: httpx.AsyncClient = request.app.state.core_client
        try:
            core_response = await client.post(
                "/auth/login",
                content=await request.body(),
                headers=forwarded_headers(request, accept="text/html"),
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
        client: httpx.AsyncClient = request.app.state.core_client
        try:
            await client.delete("/api/auth/session", headers=forwarded_headers(request))
        except httpx.RequestError:
            pass
        response = RedirectResponse("/auth/login", status_code=303)
        clear_auth_cookies(response, request)
        return response

    @app.get("/{path:path}", response_class=HTMLResponse)
    async def frontend(path: str, request: Request) -> Response:
        normalized = path.strip("/").casefold()
        if any(pattern.fullmatch(normalized) for pattern in config.resource_patterns):
            return proxy_response(await core_request(request, normalized))
        if not request.cookies.get(AUTH_SESSION_COOKIE_NAME):
            return RedirectResponse("/auth/login", status_code=303)
        return HTMLResponse(index_html())

    return app
