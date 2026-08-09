from __future__ import annotations

import os
from typing import Optional

from fastapi import Request
from starlette.responses import Response


AUTH_SESSION_COOKIE_NAME = "lilletorget_session"
LEGACY_AUTH_COOKIE_NAMES = (
    "fibaro10_session",
    "fibaro10_access_username",
    "fibaro10_access_password",
)
DEFAULT_AUTH_SESSION_COOKIE_DOMAIN = ".lilletorget.net"


def request_is_secure(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
    return request.url.scheme == "https" or forwarded_proto == "https"


def request_public_host(request: Request) -> str:
    forwarded_host = request.headers.get("x-forwarded-host", "").split(",", 1)[0].strip()
    host = forwarded_host or request.headers.get("host", "").strip()
    if host.startswith("["):
        return host.split("]", 1)[0].lstrip("[").lower().rstrip(".")
    return host.split(":", 1)[0].lower().rstrip(".")


def auth_cookie_domain(request: Request) -> Optional[str]:
    configured = os.getenv("AUTH_SESSION_COOKIE_DOMAIN", DEFAULT_AUTH_SESSION_COOKIE_DOMAIN).strip()
    if not configured:
        return None
    suffix = configured.lstrip(".").lower().rstrip(".")
    host = request_public_host(request)
    if host == suffix or host.endswith(f".{suffix}"):
        return configured
    return None


def set_auth_session_cookie(response: Response, request: Request, token: str, *, max_age: int) -> None:
    secure = request_is_secure(request)
    domain = auth_cookie_domain(request)

    # Remove cookies from the old per-app login before establishing shared SSO.
    for name in (AUTH_SESSION_COOKIE_NAME, *LEGACY_AUTH_COOKIE_NAMES):
        response.delete_cookie(name, path="/", secure=secure, httponly=True, samesite="lax")

    response.set_cookie(
        AUTH_SESSION_COOKIE_NAME,
        token,
        max_age=max_age,
        path="/",
        domain=domain,
        httponly=True,
        secure=secure,
        samesite="lax",
    )


def clear_auth_cookies(response: Response, request: Request) -> None:
    secure = request_is_secure(request)
    domain = auth_cookie_domain(request)
    for name in (AUTH_SESSION_COOKIE_NAME, *LEGACY_AUTH_COOKIE_NAMES):
        response.delete_cookie(name, path="/", secure=secure, httponly=True, samesite="lax")
        if domain:
            response.delete_cookie(
                name,
                path="/",
                domain=domain,
                secure=secure,
                httponly=True,
                samesite="lax",
            )


def forwarded_auth_headers(request: Request, *, user_agent: str, accept: str = "application/json") -> dict[str, str]:
    headers = {"Accept": accept, "User-Agent": user_agent}
    for source, target in (
        ("cookie", "Cookie"),
        ("content-type", "Content-Type"),
        ("x-forwarded-for", "X-Forwarded-For"),
    ):
        if value := request.headers.get(source):
            headers[target] = value
    if "X-Forwarded-For" not in headers and request.client:
        headers["X-Forwarded-For"] = request.client.host

    headers["X-Forwarded-Host"] = (
        request.headers.get("x-forwarded-host", "").split(",", 1)[0].strip()
        or request.headers.get("host", "").strip()
    )
    headers["X-Forwarded-Proto"] = (
        request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
        or request.url.scheme
    )
    return headers
