"""Assets API with explicit database and authorization dependencies."""

from collections.abc import Callable
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from time_formatting import api_local_iso, local_now_naive
from sqlalchemy import or_, select
from cleaning_robot_domain import cleaning_provider_label
from fibaro_core.models.cleaning import RoborockRobot
from fibaro_core.models.energy import EnergyNode
from fibaro_core.models.sun import Sun2Bed
from fibaro_core.models.system import AssetRegistryItem
from fibaro_core.schemas.system import AssetRegistryInput
from fibaro_core.services.assets import (
    asset_registry_payload,
    apply_asset_registry_input,
)


def create_assets_router(
    session_factory: async_sessionmaker[AsyncSession],
    require_settings_access: Callable[[Request], Optional[Response]],
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/system/assets")
    async def api_system_assets(
        q: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ):
        query = select(AssetRegistryItem)
        needle = (q or "").strip()
        if needle:
            pattern = f"%{needle}%"
            query = query.where(
                or_(
                    AssetRegistryItem.name.ilike(pattern),
                    AssetRegistryItem.location.ilike(pattern),
                    AssetRegistryItem.manufacturer.ilike(pattern),
                    AssetRegistryItem.model.ilike(pattern),
                    AssetRegistryItem.serial_no.ilike(pattern),
                    AssetRegistryItem.notes.ilike(pattern),
                )
            )
        if category:
            query = query.where(AssetRegistryItem.category == category)
        if status:
            query = query.where(AssetRegistryItem.status == status)
        query = query.order_by(AssetRegistryItem.category, AssetRegistryItem.location, AssetRegistryItem.name)
        async with session_factory() as session:
            rows = (await session.execute(query)).scalars().all()
        return {"generatedAt": api_local_iso(local_now_naive()), "assets": [asset_registry_payload(row) for row in rows]}

    @router.post("/api/system/assets")
    async def api_system_asset_create(request: Request, payload: AssetRegistryInput):
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        now_dt = local_now_naive()
        row = AssetRegistryItem(created_at=now_dt, updated_at=now_dt)
        apply_asset_registry_input(row, payload, now_dt)
        async with session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return {"status": "ok", "message": "Eiendelen er opprettet.", "asset": asset_registry_payload(row)}

    @router.patch("/api/system/assets/{asset_id}")
    async def api_system_asset_update(request: Request, asset_id: int, payload: AssetRegistryInput):
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        async with session_factory() as session:
            row = await session.get(AssetRegistryItem, asset_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Eiendelen finnes ikke")
            apply_asset_registry_input(row, payload, local_now_naive())
            await session.commit()
            await session.refresh(row)
        return {"status": "ok", "message": "Eiendelen er oppdatert.", "asset": asset_registry_payload(row)}

    @router.post("/api/system/assets/discover")
    async def api_system_assets_discover(request: Request):
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        now_dt = local_now_naive()
        created = 0
        async with session_factory() as session:
            existing = {
                (str(category).casefold(), str(name).casefold())
                for category, name in (await session.execute(select(AssetRegistryItem.category, AssetRegistryItem.name))).all()
            }
            beds = (await session.execute(select(Sun2Bed).order_by(Sun2Bed.name))).scalars().all()
            robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
            energy_nodes = (await session.execute(select(EnergyNode).where(EnergyNode.active.is_(True)).order_by(EnergyNode.name))).scalars().all()
            candidates = [
                AssetRegistryItem(
                    name=bed.name,
                    category="Solseng",
                    location=f"Solrom {bed.display_room_number or bed.physical_room_number}" if (bed.display_room_number or bed.physical_room_number) else bed.room_id,
                    manufacturer="",
                    model=bed.bed_model,
                    owner_app="Soling",
                    status="I drift",
                    extra={"sun2BedId": bed.sun2_bed_id},
                    created_at=now_dt,
                    updated_at=now_dt,
                )
                for bed in beds
                if (bed.name or "").strip() not in {"", "."}
            ] + [
                AssetRegistryItem(
                    name=robot.name,
                    category="Robotvasker",
                    manufacturer=cleaning_provider_label(robot.provider),
                    model=robot.model or robot.product,
                    serial_no=robot.serial_number,
                    owner_app="Bygg og drift",
                    status="I drift" if robot.integration_status == "active" else robot.integration_status,
                    extra={"robotUid": robot.duid},
                    created_at=now_dt,
                    updated_at=now_dt,
                )
                for robot in robots
            ] + [
                AssetRegistryItem(
                    name=node.name,
                    category="Z-Wave-enhet",
                    location=node.area,
                    manufacturer=node.manufacturer,
                    model=node.model,
                    hc3_device_id=node.hc3_device_id or node.hc3_power_device_id,
                    owner_app="Energi",
                    status="I drift",
                    extra={"energyNodeId": node.id, "nodeType": node.node_type},
                    created_at=now_dt,
                    updated_at=now_dt,
                )
                for node in energy_nodes
            ]
            for candidate in candidates:
                key = (candidate.category.casefold(), candidate.name.casefold())
                if key in existing:
                    continue
                session.add(candidate)
                existing.add(key)
                created += 1
            await session.commit()
        return {"status": "ok", "message": f"{created} nye eiendeler ble funnet og lagt til.", "created": created}

    return router
