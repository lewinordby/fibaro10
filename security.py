from typing import MutableMapping


DEFAULT_HSTS_MAX_AGE_SECONDS = 60 * 60 * 24 * 180

BASE_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def security_headers(*, hsts_enabled: bool = False, hsts_max_age_seconds: int = DEFAULT_HSTS_MAX_AGE_SECONDS) -> dict[str, str]:
    headers = dict(BASE_SECURITY_HEADERS)
    if hsts_enabled:
        headers["Strict-Transport-Security"] = f"max-age={max(0, hsts_max_age_seconds)}; includeSubDomains"
    return headers


def apply_security_headers(
    headers: MutableMapping[str, str],
    *,
    hsts_enabled: bool = False,
    hsts_max_age_seconds: int = DEFAULT_HSTS_MAX_AGE_SECONDS,
) -> None:
    for key, value in security_headers(hsts_enabled=hsts_enabled, hsts_max_age_seconds=hsts_max_age_seconds).items():
        if key not in headers:
            headers[key] = value
