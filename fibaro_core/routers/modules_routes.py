"""Module dispatch only; each domain owns its response builder."""
from dataclasses import dataclass
from typing import Any, Callable, Optional
from fastapi import APIRouter, HTTPException, Request
from fibaro_core.routers.bundle import RouterBundle
from time_formatting import local_now_naive



@dataclass
class Dependencies:
    async_session: Callable[..., Any]
    handlers: dict[str, Callable[..., Any]]


def create_router(dependencies: Dependencies) -> RouterBundle:
    router = APIRouter()

    @router.get("/api/modules/{module}")
    async def api_v2_module(request: Request, module: str, view: Optional[str] = None, q: Optional[str] = None, day: Optional[str] = None):
        module = module.strip().lower()
        view = (view or "").strip().lower()
        now_dt = local_now_naive()
        async with dependencies.async_session() as session:
            handler = dependencies.handlers.get(module)
            if handler is not None:
                return await handler(session, request, module, view, q, day, now_dt)
        raise HTTPException(status_code=404, detail="Ukjent v2-modul")

    return RouterBundle(router, {"api_v2_module": api_v2_module}, dependencies)
