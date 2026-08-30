"""Application middleware, bound explicitly by the composition root."""

from dataclasses import dataclass
from fastapi import Request
from fastapi.responses import JSONResponse
from observability import cache_control_for_path, response_timing_headers
from security import apply_security_headers
from time import perf_counter
from typing import Any, Callable


@dataclass
class Dependencies:
    SECURITY_HSTS_ENABLED: Any
    SECURITY_HSTS_MAX_AGE_SECONDS: Any
    SLOW_REQUEST_WARNING_MS: Any
    access_role: Any
    find_access_key: Any
    find_auth_session: Any
    has_car_info_app_access: Any
    has_koble_worker_access: Any
    is_car_info_app_request_path: Any
    is_koble_worker_request_path: Any
    is_public_request: Any
    log_access_attempt: Any
    logger: Any
    presented_credentials: Any
    presented_session_token: Any
    templates: Any
    wants_html: Any


def create_handlers(dependencies: Dependencies):
    async def access_key_middleware(request: Request, call_next):
        access_role = dependencies.access_role
        find_access_key = dependencies.find_access_key
        find_auth_session = dependencies.find_auth_session
        has_car_info_app_access = dependencies.has_car_info_app_access
        has_koble_worker_access = dependencies.has_koble_worker_access
        is_car_info_app_request_path = dependencies.is_car_info_app_request_path
        is_koble_worker_request_path = dependencies.is_koble_worker_request_path
        is_public_request = dependencies.is_public_request
        log_access_attempt = dependencies.log_access_attempt
        presented_credentials = dependencies.presented_credentials
        presented_session_token = dependencies.presented_session_token
        templates = dependencies.templates
        wants_html = dependencies.wants_html
        if is_public_request(request):
            return await call_next(request)

        if is_car_info_app_request_path(request.url.path) and has_car_info_app_access(request):
            request.state.access_key_id = None
            request.state.access_key_name = "car_info_lookup"
            request.state.auth_role = "settings"
            request.state.auth_is_master = False
            request.state.auth_can_settings = True
            return await call_next(request)

        if is_koble_worker_request_path(request.url.path) and has_koble_worker_access(request):
            request.state.access_key_id = None
            request.state.access_key_name = "parking_sun_linker"
            request.state.auth_role = "settings"
            request.state.auth_is_master = False
            request.state.auth_can_settings = True
            return await call_next(request)

        auth_session_id = None
        attempted_username = None
        session_token = presented_session_token(request)
        if session_token:
            auth_session = await find_auth_session(session_token)
            access_key = auth_session[0] if auth_session else None
            auth_session_id = auth_session[1] if auth_session else None
        else:
            username, password = presented_credentials(request)
            attempted_username = username
            access_key = await find_access_key(username, password)
        if not access_key:
            await log_access_attempt(request, False, "missing_or_invalid_session" if session_token else "missing_or_invalid_key", attempted_username=attempted_username)
            if wants_html(request):
                return templates.TemplateResponse(
                    request,
                    "login.html",
                    {"error": "Mangler eller ugyldig brukernavn/passord"},
                    status_code=401,
                )
            return JSONResponse({"detail": "Ugyldig eller manglende brukernavn/passord"}, status_code=401)

        request.state.access_key_id = access_key.id
        request.state.access_key_name = access_key.name
        request.state.auth_session_id = auth_session_id
        request.state.auth_role = access_role(access_key)
        request.state.auth_is_master = request.state.auth_role == "master"
        request.state.auth_can_settings = request.state.auth_role in ["master", "settings"]
        await log_access_attempt(request, True, "ok", access_key)
        return await call_next(request)

    async def security_headers_middleware(request: Request, call_next):
        SECURITY_HSTS_ENABLED = dependencies.SECURITY_HSTS_ENABLED
        SECURITY_HSTS_MAX_AGE_SECONDS = dependencies.SECURITY_HSTS_MAX_AGE_SECONDS
        SLOW_REQUEST_WARNING_MS = dependencies.SLOW_REQUEST_WARNING_MS
        logger = dependencies.logger
        started_at = perf_counter()
        response = await call_next(request)
        duration_ms = (perf_counter() - started_at) * 1000
        apply_security_headers(
            response.headers,
            hsts_enabled=SECURITY_HSTS_ENABLED,
            hsts_max_age_seconds=SECURITY_HSTS_MAX_AGE_SECONDS,
        )
        for key, value in response_timing_headers(duration_ms).items():
            response.headers.setdefault(key, value)
        cache_control = cache_control_for_path(request.url.path)
        if cache_control:
            response.headers.setdefault("Cache-Control", cache_control)
        if duration_ms >= SLOW_REQUEST_WARNING_MS and request.url.path != "/health":
            logger.warning(
                "Slow request %s %s completed in %.1f ms with status %s",
                request.method,
                request.url.path,
                duration_ms,
                response.status_code,
            )
        return response

    return {
        "access_key_middleware": access_key_middleware,
        "security_headers_middleware": security_headers_middleware,
    }
