"""Automations API with explicit database and authorization dependencies."""

from collections.abc import Callable
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from time_formatting import api_local_iso, local_now_naive
from sqlalchemy import select
from fibaro_core.models.system import AutomationWorkbenchRule
from fibaro_core.schemas.system import AutomationWorkbenchInput
from fibaro_core.services.automations import (
    automation_workbench_payload,
    apply_automation_workbench_input,
)


def create_automations_router(
    session_factory: async_sessionmaker[AsyncSession],
    require_settings_access: Callable[[Request], Optional[Response]],
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/system/automations")
    async def api_system_automations():
        async with session_factory() as session:
            rows = (
                await session.execute(
                    select(AutomationWorkbenchRule).order_by(
                        AutomationWorkbenchRule.enabled.desc(),
                        AutomationWorkbenchRule.domain,
                        AutomationWorkbenchRule.name,
                    )
                )
            ).scalars().all()
        return {"generatedAt": api_local_iso(local_now_naive()), "automations": [automation_workbench_payload(row) for row in rows]}

    @router.post("/api/system/automations")
    async def api_system_automation_create(request: Request, payload: AutomationWorkbenchInput):
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        now_dt = local_now_naive()
        row = AutomationWorkbenchRule(created_at=now_dt, updated_at=now_dt)
        apply_automation_workbench_input(row, payload, now_dt)
        async with session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return {"status": "ok", "message": "Automatiseringen er opprettet.", "automation": automation_workbench_payload(row)}

    @router.patch("/api/system/automations/{automation_id}")
    async def api_system_automation_update(request: Request, automation_id: int, payload: AutomationWorkbenchInput):
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        async with session_factory() as session:
            row = await session.get(AutomationWorkbenchRule, automation_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Automatiseringen finnes ikke")
            apply_automation_workbench_input(row, payload, local_now_naive())
            await session.commit()
            await session.refresh(row)
        return {"status": "ok", "message": "Automatiseringen er oppdatert.", "automation": automation_workbench_payload(row)}

    return router
