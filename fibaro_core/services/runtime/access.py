"""Access services with explicit process dependencies."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from fastapi import Request
from fastapi.responses import JSONResponse
from fibaro_core.models import AccessKey, AccessLog, AuthSession
from microapp_backend.auth import AUTH_SESSION_COOKIE_NAME, request_is_secure
from sqlalchemy import and_, delete, func, or_, select, update
from typing import Any, Callable, Dict, Optional
from urllib.parse import parse_qs
import asyncio
import base64
import hashlib
import secrets


@dataclass
class Dependencies:
    ACCESS_FAILED_DISABLE_THRESHOLD: Any
    AUTH_SESSION_HEADER_NAME: Any
    AUTH_SESSION_MAX_AGE_SECONDS: Any
    NTFY_ACCESS_COOLDOWN_MINUTES: Any
    NTFY_ACCESS_TOPIC: Any
    PUBLIC_PATHS: Any
    PUBLIC_PREFIXES: Any
    async_session: Callable[..., Any]
    enqueue_ntfy_message: Callable[..., Any]
    logger: Any
    mobile_preview_can_view_money: Callable[..., Any]


def create_service(dependencies: Dependencies):

    def hash_access_key(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def normalize_username(value: str) -> str:
        return value.strip().casefold()

    def credential_hash(username: str, password: str) -> str:
        return hash_access_key(normalize_username(username) + "\0" + password)

    def credential_prefix(username: str, password: str) -> str:
        return "key_" + credential_hash(username, password)[:8]

    def access_password_hash(username: str, password: str, *, is_master: bool = False) -> str:
        if is_master or normalize_username(username) == "master":
            return hash_access_key(password)
        return credential_hash(username, password)

    def access_key_prefix(username: str, password: str, *, is_master: bool = False) -> str:
        if is_master or normalize_username(username) == "master":
            return "sun2_master"
        return credential_prefix(username, password)

    def client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else ""

    def presented_credentials(request: Request) -> tuple[Optional[str], Optional[str]]:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("basic "):
            try:
                decoded = base64.b64decode(authorization.split(" ", 1)[1].strip()).decode("utf-8")
                username, password = decoded.split(":", 1)
                return username, password
            except Exception:
                return None, None
        username = (
            request.query_params.get("username")
            or request.headers.get("x-access-username")
        )
        password = (
            request.query_params.get("password")
            or request.headers.get("x-access-password")
        )
        return username, password

    def presented_session_token(request: Request) -> Optional[str]:
        AUTH_SESSION_HEADER_NAME = dependencies.AUTH_SESSION_HEADER_NAME
        return request.headers.get(AUTH_SESSION_HEADER_NAME) or request.cookies.get(AUTH_SESSION_COOKIE_NAME)

    def wants_html(request: Request) -> bool:
        accept = request.headers.get("accept", "")
        return "text/html" in accept or "*/*" in accept

    def is_public_request(request: Request) -> bool:
        PUBLIC_PATHS = dependencies.PUBLIC_PATHS
        PUBLIC_PREFIXES = dependencies.PUBLIC_PREFIXES
        path = request.url.path
        if path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
            return True
        if request.method == "GET" and (path == "/api/config" or path.startswith("/api/config/")):
            return True
        return request.method == "POST" and path in {
            "/events",
            "/log",
            "/api/auth/session",
            "/api/energi/fibaro",
            "/api/hc3/measurements/log",
            "/api/hc3/door-events",
        }

    async def parse_form_body(request: Request) -> Dict[str, str]:
        raw = (await request.body()).decode("utf-8")
        parsed = parse_qs(raw, keep_blank_values=True)
        return {key: values[-1] if values else "" for key, values in parsed.items()}

    async def log_access_attempt(
        request: Request,
        success: bool,
        reason: str,
        access_key: Optional[AccessKey] = None,
        attempted_username: Optional[str] = None,
    ):
        ACCESS_FAILED_DISABLE_THRESHOLD = dependencies.ACCESS_FAILED_DISABLE_THRESHOLD
        async_session = dependencies.async_session
        notify_master = success and should_publish_access_ntfy(request, access_key, reason)
        now_value = datetime.utcnow()
        normalized_attempted_username = normalize_username(attempted_username or "")
        async with async_session() as session:
            log_row = AccessLog(
                access_key_id=access_key.id if access_key else None,
                key_name=access_key.name if access_key else normalized_attempted_username or None,
                key_prefix=access_key.key_prefix if access_key else None,
                path=request.url.path,
                method=request.method,
                ip=client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
                success=success,
                reason=reason,
            )
            session.add(log_row)
            if access_key and success:
                values = {
                    "last_seen_at": now_value,
                    "last_ip": client_ip(request),
                    "last_user_agent": request.headers.get("user-agent", ""),
                    "uses_count": func.coalesce(AccessKey.uses_count, 0) + 1,
                }
                if notify_master:
                    values["last_notified_at"] = now_value
                await session.execute(update(AccessKey).where(AccessKey.id == access_key.id).values(**values))
            elif not success and normalized_attempted_username and normalized_attempted_username != "master":
                await session.flush()
                user_result = await session.execute(
                    select(AccessKey)
                    .where(AccessKey.name == normalized_attempted_username)
                    .where(AccessKey.is_master == False)
                    .where(AccessKey.active == True)
                    .order_by(AccessKey.id.desc())
                    .limit(1)
                )
                user_key = user_result.scalars().first()
                if user_key:
                    recent_failures = (
                        await session.execute(
                            select(AccessLog.success)
                            .where(AccessLog.key_name == normalized_attempted_username)
                            .order_by(AccessLog.timestamp.desc(), AccessLog.id.desc())
                            .limit(ACCESS_FAILED_DISABLE_THRESHOLD)
                        )
                    ).scalars().all()
                    if len(recent_failures) >= ACCESS_FAILED_DISABLE_THRESHOLD and all(value is False for value in recent_failures):
                        user_key.active = False
                        log_row.access_key_id = user_key.id
                        log_row.key_prefix = user_key.key_prefix
                        log_row.reason = f"{reason}_auto_deactivated_after_{ACCESS_FAILED_DISABLE_THRESHOLD}_failures"
            await session.commit()
        if notify_master and access_key:
            asyncio.create_task(
                publish_access_ntfy(
                    access_key.name,
                    access_key.role,
                    access_key.is_master,
                    request.method,
                    request.url.path,
                    client_ip(request),
                    reason,
                )
            )

    async def find_access_key(username: Optional[str], password: Optional[str]) -> Optional[AccessKey]:
        async_session = dependencies.async_session
        if not username or not password:
            return None
        normalized_username = normalize_username(username)
        hashed = access_password_hash(normalized_username, password, is_master=normalized_username == "master")
        async with async_session() as session:
            result = await session.execute(
                select(AccessKey)
                .where(AccessKey.name == normalized_username)
                .where(AccessKey.key_hash == hashed)
                .where(AccessKey.active == True)
            )
            return result.scalars().first()

    def hash_auth_session_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def create_auth_session(access_key: AccessKey, request: Request) -> str:
        AUTH_SESSION_MAX_AGE_SECONDS = dependencies.AUTH_SESSION_MAX_AGE_SECONDS
        async_session = dependencies.async_session
        token = secrets.token_urlsafe(32)
        now_value = datetime.utcnow()
        async with async_session() as session:
            session.add(
                AuthSession(
                    token_hash=hash_auth_session_token(token),
                    access_key_id=access_key.id,
                    credential_hash_at_issue=access_key.key_hash,
                    created_at=now_value,
                    expires_at=now_value + timedelta(seconds=AUTH_SESSION_MAX_AGE_SECONDS),
                    created_ip=client_ip(request),
                    user_agent=request.headers.get("user-agent", ""),
                )
            )
            await session.execute(
                delete(AuthSession).where(
                    or_(
                        AuthSession.expires_at <= now_value,
                        and_(AuthSession.revoked_at.is_not(None), AuthSession.revoked_at <= now_value - timedelta(days=7)),
                    )
                )
            )
            await session.commit()
        return token

    async def find_auth_session(token: Optional[str]) -> Optional[tuple[AccessKey, int]]:
        async_session = dependencies.async_session
        if not token:
            return None
        now_value = datetime.utcnow()
        async with async_session() as session:
            result = await session.execute(
                select(AuthSession, AccessKey)
                .join(AccessKey, AccessKey.id == AuthSession.access_key_id)
                .where(AuthSession.token_hash == hash_auth_session_token(token))
                .where(AuthSession.revoked_at.is_(None))
                .where(AuthSession.expires_at > now_value)
                .where(AccessKey.active == True)
                .limit(1)
            )
            row = result.first()
            if not row:
                return None
            auth_session, access_key = row
            if not secrets.compare_digest(auth_session.credential_hash_at_issue, access_key.key_hash):
                auth_session.revoked_at = now_value
                await session.commit()
                return None
            if auth_session.last_seen_at is None or auth_session.last_seen_at < now_value - timedelta(minutes=5):
                auth_session.last_seen_at = now_value
                await session.commit()
            return access_key, auth_session.id

    async def revoke_auth_session(session_id: Optional[int]) -> None:
        async_session = dependencies.async_session
        if not session_id:
            return
        async with async_session() as session:
            await session.execute(
                update(AuthSession)
                .where(AuthSession.id == session_id)
                .where(AuthSession.revoked_at.is_(None))
                .values(revoked_at=datetime.utcnow())
            )
            await session.commit()

    def require_master(request: Request):
        if not getattr(request.state, "auth_is_master", False):
            return JSONResponse({"detail": "Masterbruker kreves"}, status_code=403)
        return None

    def access_role(access_key: Optional[AccessKey]) -> str:
        if not access_key:
            return "viewer"
        if access_key.is_master:
            return "master"
        role = (access_key.role or "viewer").strip().lower()
        if role not in ["viewer", "settings"]:
            return "viewer"
        return role

    def access_role_label(role: Optional[str], is_master: bool = False) -> str:
        if is_master or role == "master":
            return "Master"
        if role == "settings":
            return "Innstillinger"
        return "Vanlig"

    def require_settings_access(request: Request):
        if not getattr(request.state, "auth_can_settings", False):
            return JSONResponse({"detail": "Tilgang til innstillinger kreves"}, status_code=403)
        return None

    def should_publish_access_ntfy(request: Request, access_key: Optional[AccessKey], reason: str) -> bool:
        NTFY_ACCESS_COOLDOWN_MINUTES = dependencies.NTFY_ACCESS_COOLDOWN_MINUTES
        if not access_key or access_key.is_master:
            return False
        if reason != "login" and (request.method != "GET" or not wants_html(request)):
            return False
        if reason != "login" and request.url.path.startswith("/auth/"):
            return False
        last_notified = access_key.last_notified_at or access_key.last_seen_at
        if not last_notified:
            return True
        return datetime.utcnow() - last_notified >= timedelta(minutes=NTFY_ACCESS_COOLDOWN_MINUTES)

    async def publish_access_ntfy(
        username: str,
        role: Optional[str],
        is_master: bool,
        method: str,
        path: str,
        ip: str,
        reason: str,
    ) -> bool:
        NTFY_ACCESS_TOPIC = dependencies.NTFY_ACCESS_TOPIC
        enqueue_ntfy_message = dependencies.enqueue_ntfy_message
        logger = dependencies.logger
        role_label = access_role_label(role, is_master)
        action = "logget inn" if reason == "login" else "bruker løsningen"
        message = (
            f"{username} ({role_label}) {action}. "
            f"Side: {method} {path}. "
            f"IP: {ip or '-'}."
        )
        try:
            return await enqueue_ntfy_message(
                NTFY_ACCESS_TOPIC,
                "SUN2 brukeraktivitet",
                message,
                "bust_in_silhouette",
                "3",
            )
        except Exception as exc:
            logger.warning("Kunne ikke legge NTFY-varsel for tilgang i ko: %s", exc, exc_info=True)
            return False

    def should_use_secure_cookie(request: Request) -> bool:
        return request_is_secure(request)

    def mobile_preview_access_key(request: Request) -> Dict[str, Any]:
        mobile_preview_can_view_money = dependencies.mobile_preview_can_view_money
        can_view_money = mobile_preview_can_view_money(request)
        return {
            "id": getattr(request.state, "access_key_id", 0) or 0,
            "name": getattr(request.state, "access_key_name", None) or "desktop",
            "key_prefix": "desktop",
            "role": "settings" if can_view_money else "viewer",
            "is_master": bool(getattr(request.state, "auth_is_master", False)),
            "active": True,
        }

    def api_access_key_row(row: AccessKey) -> Dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "role": row.role,
            "active": bool(row.active),
            "is_master": bool(row.is_master),
            "key_prefix": row.key_prefix,
            "password_status": "Kan settes på nytt, kan ikke vises" if row.is_master else "Kan endres",
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
            "uses_count": row.uses_count,
        }

    def api_access_key_edit() -> Dict[str, Any]:
        role_options = [
            {"label": "Viewer", "value": "viewer"},
            {"label": "Settings", "value": "settings"},
        ]
        return {
            "kind": "access-key",
            "title": "bruker",
            "idField": "id",
            "endpoint": "/api/admin/users/{id}",
            "method": "PATCH",
            "createEndpoint": "/api/admin/users",
            "fields": [
                {"key": "role", "label": "Rolle", "type": "select", "options": role_options, "required": True},
                {"key": "active", "label": "Aktiv", "type": "boolean"},
                {"key": "password", "label": "Nytt passord", "type": "password", "placeholder": "Fyll ut bare hvis passord skal endres"},
            ],
            "createFields": [
                {"key": "username", "label": "Brukernavn", "type": "text", "required": True},
                {"key": "password", "label": "Passord", "type": "password", "required": True},
                {"key": "role", "label": "Rolle", "type": "select", "options": role_options, "required": True},
            ],
        }

    return {
        "access_key_prefix": access_key_prefix,
        "access_password_hash": access_password_hash,
        "access_role": access_role,
        "access_role_label": access_role_label,
        "api_access_key_edit": api_access_key_edit,
        "api_access_key_row": api_access_key_row,
        "client_ip": client_ip,
        "create_auth_session": create_auth_session,
        "credential_hash": credential_hash,
        "credential_prefix": credential_prefix,
        "find_access_key": find_access_key,
        "find_auth_session": find_auth_session,
        "hash_access_key": hash_access_key,
        "hash_auth_session_token": hash_auth_session_token,
        "is_public_request": is_public_request,
        "log_access_attempt": log_access_attempt,
        "mobile_preview_access_key": mobile_preview_access_key,
        "normalize_username": normalize_username,
        "parse_form_body": parse_form_body,
        "presented_credentials": presented_credentials,
        "presented_session_token": presented_session_token,
        "publish_access_ntfy": publish_access_ntfy,
        "require_master": require_master,
        "require_settings_access": require_settings_access,
        "revoke_auth_session": revoke_auth_session,
        "should_publish_access_ntfy": should_publish_access_ntfy,
        "should_use_secure_cookie": should_use_secure_cookie,
        "wants_html": wants_html,
    }
