"""Access HTTP routes; runtime services are supplied by composition."""

from build_log import APP_BUILD
from dataclasses import dataclass
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fibaro_core.models import AccessKey, AccessLog
from fibaro_core.routers.bundle import RouterBundle
from fibaro_core.schemas import V2AccessUserCreate, V2AccessUserUpdate
from microapp_backend import render_login_page
from microapp_backend.auth import clear_auth_cookies, set_auth_session_cookie
from sqlalchemy import select, update
from typing import Any, Callable
import json


@dataclass
class Dependencies:
    AUTH_COOKIE_NAME: Any
    AUTH_SESSION_MAX_AGE_SECONDS: Any
    AUTH_USER_COOKIE_NAME: Any
    FIBARO10_PWA: Any
    access_key_prefix: Callable[..., Any]
    access_password_hash: Callable[..., Any]
    access_role: Callable[..., Any]
    access_role_label: Callable[..., Any]
    async_session: Callable[..., Any]
    create_auth_session: Callable[..., Any]
    find_access_key: Callable[..., Any]
    log_access_attempt: Callable[..., Any]
    normalize_username: Callable[..., Any]
    parse_form_body: Callable[..., Any]
    redirect_keep_query: Callable[..., Any]
    require_master: Callable[..., Any]
    revoke_auth_session: Callable[..., Any]
    should_use_secure_cookie: Callable[..., Any]
    templates: Any


def create_router(dependencies: Dependencies) -> RouterBundle:
    router = APIRouter()


    @router.get("/auth/login", response_class=HTMLResponse)
    async def login_view(request: Request):
        FIBARO10_PWA = dependencies.FIBARO10_PWA
        return HTMLResponse(render_login_page(app_name="Fibaro10", build=APP_BUILD, pwa=FIBARO10_PWA))

    @router.post("/auth/login")
    async def login_submit(request: Request):
        AUTH_SESSION_MAX_AGE_SECONDS = dependencies.AUTH_SESSION_MAX_AGE_SECONDS
        FIBARO10_PWA = dependencies.FIBARO10_PWA
        create_auth_session = dependencies.create_auth_session
        find_access_key = dependencies.find_access_key
        log_access_attempt = dependencies.log_access_attempt
        normalize_username = dependencies.normalize_username
        parse_form_body = dependencies.parse_form_body
        form = await parse_form_body(request)
        username = normalize_username(form.get("username") or "")
        password = (form.get("password") or "").strip()
        access_key = await find_access_key(username, password)
        if not access_key:
            await log_access_attempt(request, False, "failed_login", attempted_username=username)
            return HTMLResponse(
                render_login_page(
                    app_name="Fibaro10",
                    build=APP_BUILD,
                    pwa=FIBARO10_PWA,
                    error="Ugyldig brukernavn eller passord.",
                ),
                status_code=401,
            )
        response = RedirectResponse("/", status_code=303)
        session_token = await create_auth_session(access_key, request)
        set_auth_session_cookie(response, request, session_token, max_age=AUTH_SESSION_MAX_AGE_SECONDS)
        await log_access_attempt(request, True, "login", access_key)
        return response

    @router.post("/konto/logg-ut")
    async def logout(request: Request):
        revoke_auth_session = dependencies.revoke_auth_session
        await revoke_auth_session(getattr(request.state, "auth_session_id", None))
        response = RedirectResponse("/auth/login", status_code=303)
        clear_auth_cookies(response, request)
        return response

    @router.post("/api/auth/session")
    async def api_auth_session_create(request: Request):
        AUTH_SESSION_MAX_AGE_SECONDS = dependencies.AUTH_SESSION_MAX_AGE_SECONDS
        access_role = dependencies.access_role
        create_auth_session = dependencies.create_auth_session
        find_access_key = dependencies.find_access_key
        log_access_attempt = dependencies.log_access_attempt
        normalize_username = dependencies.normalize_username
        try:
            payload = await request.json()
        except (ValueError, json.JSONDecodeError):
            payload = {}
        username = normalize_username(str(payload.get("username") or "")) if isinstance(payload, dict) else ""
        password = str(payload.get("password") or "").strip() if isinstance(payload, dict) else ""
        access_key = await find_access_key(username, password)
        if not access_key:
            await log_access_attempt(request, False, "failed_session_login", attempted_username=username)
            raise HTTPException(status_code=401, detail="Ugyldig brukernavn eller passord")
        session_token = await create_auth_session(access_key, request)
        await log_access_attempt(request, True, "session_login", access_key)
        return {
            "sessionToken": session_token,
            "expiresIn": AUTH_SESSION_MAX_AGE_SECONDS,
            "username": access_key.name,
            "role": access_role(access_key),
        }

    @router.delete("/api/auth/session")
    async def api_auth_session_delete(request: Request):
        revoke_auth_session = dependencies.revoke_auth_session
        await revoke_auth_session(getattr(request.state, "auth_session_id", None))
        return {"ok": True}

    @router.get("/api/auth/me")
    async def api_auth_me(request: Request):
        access_role_label = dependencies.access_role_label
        role = getattr(request.state, "auth_role", "viewer")
        is_master = bool(getattr(request.state, "auth_is_master", False))
        return {
            "username": getattr(request.state, "access_key_name", None),
            "role": role,
            "roleLabel": access_role_label(role, is_master),
            "isMaster": is_master,
            "canSettings": bool(getattr(request.state, "auth_can_settings", False)),
            "appBuild": APP_BUILD,
        }

    @router.get("/konto/brukere-og-tilgang", response_class=HTMLResponse)
    async def keys_view(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/admin/brukere", status_code=303)

    @router.post("/konto/brukere-og-tilgang")
    async def keys_create(request: Request):
        access_key_prefix = dependencies.access_key_prefix
        access_password_hash = dependencies.access_password_hash
        async_session = dependencies.async_session
        normalize_username = dependencies.normalize_username
        parse_form_body = dependencies.parse_form_body
        require_master = dependencies.require_master
        templates = dependencies.templates
        forbidden = require_master(request)
        if forbidden:
            return forbidden
        form = await parse_form_body(request)
        username = normalize_username(form.get("username") or form.get("name") or "")[:80]
        password = (form.get("password") or form.get("access_key") or "").strip()
        role = (form.get("role") or "viewer").strip().lower()
        if role not in ["viewer", "settings"]:
            role = "viewer"
        if not username:
            async with async_session() as session:
                key_rows = (await session.execute(select(AccessKey).order_by(AccessKey.created_at.desc()))).scalars().all()
                log_rows = (await session.execute(select(AccessLog).order_by(AccessLog.timestamp.desc()).limit(200))).scalars().all()
            return templates.TemplateResponse(
                request,
                "keys.html",
                {
                    "keys": key_rows,
                    "logs": log_rows,
                    "created_username": "",
                    "created_key": "",
                    "error": "Brukernavn må fylles ut.",
                },
                status_code=400,
            )
        if len(password) < 5:
            async with async_session() as session:
                key_rows = (await session.execute(select(AccessKey).order_by(AccessKey.created_at.desc()))).scalars().all()
                log_rows = (await session.execute(select(AccessLog).order_by(AccessLog.timestamp.desc()).limit(200))).scalars().all()
            return templates.TemplateResponse(
                request,
                "keys.html",
                {
                    "keys": key_rows,
                    "logs": log_rows,
                    "created_username": "",
                    "created_key": "",
                    "error": "Passordet må være minst 5 tegn.",
                },
                status_code=400,
            )
        existing_hash = access_password_hash(username, password, is_master=False)
        async with async_session() as session:
            existing = (
                await session.execute(select(AccessKey).where(AccessKey.key_hash == existing_hash))
            ).scalars().first()
            if existing:
                key_rows = (await session.execute(select(AccessKey).order_by(AccessKey.created_at.desc()))).scalars().all()
                log_rows = (await session.execute(select(AccessLog).order_by(AccessLog.timestamp.desc()).limit(200))).scalars().all()
                return templates.TemplateResponse(
                    request,
                    "keys.html",
                    {
                        "keys": key_rows,
                        "logs": log_rows,
                        "created_username": "",
                        "created_key": "",
                        "error": "Denne kombinasjonen av brukernavn og passord finnes allerede.",
                    },
                    status_code=400,
                )
            record = AccessKey(
                name=username,
                key_hash=existing_hash,
                key_prefix=access_key_prefix(username, password, is_master=False),
                key_plaintext=password,
                role=role,
                is_master=False,
                active=True,
            )
            session.add(record)
            await session.commit()
            key_rows = (await session.execute(select(AccessKey).order_by(AccessKey.created_at.desc()))).scalars().all()
            log_rows = (await session.execute(select(AccessLog).order_by(AccessLog.timestamp.desc()).limit(200))).scalars().all()
        return templates.TemplateResponse(
            request,
            "keys.html",
            {"keys": key_rows, "logs": log_rows, "created_username": username, "created_key": password, "error": ""},
        )

    @router.post("/konto/brukere-og-tilgang/deaktiver")
    async def keys_disable(request: Request):
        async_session = dependencies.async_session
        parse_form_body = dependencies.parse_form_body
        require_master = dependencies.require_master
        forbidden = require_master(request)
        if forbidden:
            return forbidden
        form = await parse_form_body(request)
        try:
            key_id = int(form.get("key_id") or "0")
        except ValueError:
            key_id = 0
        async with async_session() as session:
            await session.execute(
                update(AccessKey)
                .where(AccessKey.id == key_id)
                .where(AccessKey.is_master == False)
                .values(active=False)
            )
            await session.commit()
        return RedirectResponse("/konto/brukere-og-tilgang", status_code=303)

    @router.post("/konto/brukere-og-tilgang/aktiver")
    async def keys_enable(request: Request):
        async_session = dependencies.async_session
        parse_form_body = dependencies.parse_form_body
        require_master = dependencies.require_master
        forbidden = require_master(request)
        if forbidden:
            return forbidden
        form = await parse_form_body(request)
        try:
            key_id = int(form.get("key_id") or "0")
        except ValueError:
            key_id = 0
        async with async_session() as session:
            await session.execute(
                update(AccessKey)
                .where(AccessKey.id == key_id)
                .where(AccessKey.is_master == False)
                .values(active=True)
            )
            await session.commit()
        return RedirectResponse("/konto/brukere-og-tilgang", status_code=303)

    @router.post("/konto/brukere-og-tilgang/rolle")
    async def keys_role_update(request: Request):
        async_session = dependencies.async_session
        parse_form_body = dependencies.parse_form_body
        require_master = dependencies.require_master
        forbidden = require_master(request)
        if forbidden:
            return forbidden
        form = await parse_form_body(request)
        try:
            key_id = int(form.get("key_id") or "0")
        except ValueError:
            key_id = 0
        role = (form.get("role") or "viewer").strip().lower()
        if role not in ["viewer", "settings"]:
            role = "viewer"
        async with async_session() as session:
            await session.execute(
                update(AccessKey)
                .where(AccessKey.id == key_id)
                .where(AccessKey.is_master == False)
                .values(role=role)
            )
            await session.commit()
        return RedirectResponse("/konto/brukere-og-tilgang", status_code=303)

    @router.post("/api/admin/users")
    async def api_v2_admin_user_create(request: Request, data: V2AccessUserCreate):
        access_key_prefix = dependencies.access_key_prefix
        access_password_hash = dependencies.access_password_hash
        async_session = dependencies.async_session
        normalize_username = dependencies.normalize_username
        require_master = dependencies.require_master
        forbidden = require_master(request)
        if forbidden:
            return forbidden
        username = normalize_username(data.username)[:80]
        password = data.password.strip()
        role = (data.role or "viewer").strip().lower()
        if role not in ["viewer", "settings"]:
            role = "viewer"
        if not username:
            raise HTTPException(status_code=400, detail="Brukernavn må fylles ut.")
        if username == "master":
            raise HTTPException(status_code=400, detail="Brukernavnet master er reservert.")
        if len(password) < 5:
            raise HTTPException(status_code=400, detail="Passordet må være minst 5 tegn.")
        existing_hash = access_password_hash(username, password, is_master=False)
        async with async_session() as session:
            existing = (
                await session.execute(select(AccessKey).where(AccessKey.name == username))
            ).scalars().first()
            if existing:
                raise HTTPException(status_code=409, detail="Brukernavnet finnes allerede.")
            record = AccessKey(
                name=username,
                key_hash=existing_hash,
                key_prefix=access_key_prefix(username, password, is_master=False),
                key_plaintext=password,
                role=role,
                is_master=False,
                active=True,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
        return {"status": "ok", "message": f"Bruker {username} er opprettet.", "id": record.id}

    @router.patch("/api/admin/users/{key_id}")
    async def api_v2_admin_user_update(request: Request, key_id: int, data: V2AccessUserUpdate):
        AUTH_COOKIE_NAME = dependencies.AUTH_COOKIE_NAME
        AUTH_USER_COOKIE_NAME = dependencies.AUTH_USER_COOKIE_NAME
        access_key_prefix = dependencies.access_key_prefix
        access_password_hash = dependencies.access_password_hash
        async_session = dependencies.async_session
        require_master = dependencies.require_master
        should_use_secure_cookie = dependencies.should_use_secure_cookie
        forbidden = require_master(request)
        if forbidden:
            return forbidden
        values = data.dict(exclude_unset=True)
        async with async_session() as session:
            row = await session.get(AccessKey, key_id)
            if not row:
                raise HTTPException(status_code=404, detail="Bruker ikke funnet")
            if row.is_master:
                password = str(values.get("password") or "").strip()
                if not password:
                    raise HTTPException(status_code=400, detail="Nytt passord må fylles ut for å endre masterbrukeren.")
                if len(password) < 5:
                    raise HTTPException(status_code=400, detail="Passordet må være minst 5 tegn.")
                row.name = "master"
                row.role = "master"
                row.active = True
                row.is_master = True
                row.key_hash = access_password_hash("master", password, is_master=True)
                row.key_prefix = access_key_prefix("master", password, is_master=True)
                row.key_plaintext = None
                await session.commit()
                response = JSONResponse({"status": "ok", "message": "Masterpassordet er oppdatert."})
                secure_cookie = should_use_secure_cookie(request)
                response.set_cookie(
                    AUTH_USER_COOKIE_NAME,
                    "master",
                    max_age=60 * 60 * 24 * 365,
                    httponly=True,
                    secure=secure_cookie,
                    samesite="lax",
                )
                response.set_cookie(
                    AUTH_COOKIE_NAME,
                    password,
                    max_age=60 * 60 * 24 * 365,
                    httponly=True,
                    secure=secure_cookie,
                    samesite="lax",
                )
                return response
            if "role" in values:
                role = (values.get("role") or "viewer").strip().lower()
                if role not in ["viewer", "settings"]:
                    role = "viewer"
                row.role = role
            if "active" in values:
                row.active = bool(values["active"])
            if "password" in values:
                password = str(values.get("password") or "").strip()
                if password:
                    if len(password) < 5:
                        raise HTTPException(status_code=400, detail="Passordet må være minst 5 tegn.")
                    row.key_hash = access_password_hash(row.name, password, is_master=False)
                    row.key_prefix = access_key_prefix(row.name, password, is_master=False)
                    row.key_plaintext = password
            await session.commit()
        return {"status": "ok", "message": f"Bruker {row.name} er lagret."}

    return RouterBundle(router, {
        "api_auth_me": api_auth_me,
        "api_auth_session_create": api_auth_session_create,
        "api_auth_session_delete": api_auth_session_delete,
        "api_v2_admin_user_create": api_v2_admin_user_create,
        "api_v2_admin_user_update": api_v2_admin_user_update,
        "keys_create": keys_create,
        "keys_disable": keys_disable,
        "keys_enable": keys_enable,
        "keys_role_update": keys_role_update,
        "keys_view": keys_view,
        "login_submit": login_submit,
        "login_view": login_view,
        "logout": logout,
    }, dependencies)
