"""Energy HTTP routes; runtime services are supplied by composition."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from energy_helpers import (
    circuit_technical_label,
    energy_circuit_is_sunbed,
    energy_query_url,
    filter_energy_circuits_by_sunbed,
    form_bool,
    form_float,
    form_int,
    form_text,
    normalize_energy_sunbed_filter,
)
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fibaro_core.export_definitions import ENERGY_FIBARO_COLUMNS, ENERGY_HOURLY_COLUMNS, ENERGY_IMPORT_COLUMNS
from fibaro_core.models import (
    EnergyCircuit,
    EnergyFibaroSample,
    EnergyHourlyConsumption,
    EnergyImportRun,
    EnergyLoad,
    EnergyNode,
    ImportJobStatus,
)
from fibaro_core.routers.bundle import RouterBundle
from fibaro_core.schemas import V2EnergyCircuitUpdate, V2EnergyLoadIn, V2EnergyNodeIn
from pathlib import Path
from pdf_exports import build_table_pdf, pdf_response
from sqlalchemy import func, or_, select, update
from time_formatting import local_now_naive
from typing import Any, Callable, Optional
from value_parsing import float_or_zero
import asyncio
import json


@dataclass
class Dependencies:
    ENERGY_HC3_HOURLY_DISPLAY_OFFSET: Any
    HC3_ENERGY_LIVE_TIMEOUT_SECONDS: Any
    __file__: Any
    async_session: Callable[..., Any]
    clean_energy_load_values: Callable[..., Any]
    clean_energy_node_values: Callable[..., Any]
    default_energy_node_name: Callable[..., Any]
    energy_area_cards: Callable[..., Any]
    energy_node_branch_ids: Callable[..., Any]
    energy_node_from_values: Callable[..., Any]
    find_or_create_energy_node_for_load: Callable[..., Any]
    get_energy_summaries: Callable[..., Any]
    hc3_devices_request: Callable[..., Any]
    hc3_energy_device_summary: Callable[..., Any]
    hc3_energy_nodes_live: Callable[..., Any]
    load_sunbed_power_analysis: Callable[..., Any]
    mark_import_job_running: Callable[..., Any]
    parse_day: Callable[..., Any]
    redirect_keep_query: Callable[..., Any]
    redirect_with_query_params: Callable[..., Any]
    require_settings_access: Callable[..., Any]
    row_to_dict: Callable[..., Any]
    run_elvia_import_background: Callable[..., Any]
    templates: Any
    validate_energy_load_power_values: Callable[..., Any]
    validate_energy_node_hc3_values: Callable[..., Any]
    validate_energy_node_link_uniqueness: Callable[..., Any]
    validate_energy_node_parent: Callable[..., Any]
    validate_energy_node_profile_values: Callable[..., Any]


def create_router(dependencies: Dependencies) -> RouterBundle:
    router = APIRouter()


    @router.get("/energi/testside", response_class=HTMLResponse)
    async def energy_view(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/energi/verktoy", status_code=303)

    @router.patch("/api/energy/circuits/{circuit_no}")
    async def api_v2_energy_circuit_update(request: Request, circuit_no: int, data: V2EnergyCircuitUpdate):
        async_session = dependencies.async_session
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        values = data.dict(exclude_unset=True)
        text_fields = {"description", "breaker_type", "breaker_characteristic", "cable_spec", "install_method", "terminal_ref", "status", "note"}
        async with async_session() as session:
            circuit = (
                await session.execute(select(EnergyCircuit).where(EnergyCircuit.circuit_no == circuit_no))
            ).scalars().first()
            if not circuit:
                raise HTTPException(status_code=404, detail="Kurs ikke funnet")
            for key, value in values.items():
                if key in text_fields and value is not None:
                    value = str(value).strip() or None
                setattr(circuit, key, value)
            if not circuit.status:
                circuit.status = "ukjent"
            circuit.updated_at = datetime.utcnow()
            await session.commit()
        return {"status": "ok", "message": f"Kurs {circuit_no} er lagret."}

    @router.post("/api/energy/nodes")
    async def api_v2_energy_node_create(request: Request, data: V2EnergyNodeIn):
        async_session = dependencies.async_session
        clean_energy_node_values = dependencies.clean_energy_node_values
        default_energy_node_name = dependencies.default_energy_node_name
        energy_node_from_values = dependencies.energy_node_from_values
        require_settings_access = dependencies.require_settings_access
        validate_energy_node_hc3_values = dependencies.validate_energy_node_hc3_values
        validate_energy_node_link_uniqueness = dependencies.validate_energy_node_link_uniqueness
        validate_energy_node_parent = dependencies.validate_energy_node_parent
        validate_energy_node_profile_values = dependencies.validate_energy_node_profile_values
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        values = clean_energy_node_values(data.dict(exclude_unset=True))
        circuit_no = values.get("circuit_no")
        if circuit_no is None:
            raise HTTPException(status_code=400, detail="Kurs må fylles ut.")
        name = str(values.get("name") or "").strip()
        if not name:
            name = default_energy_node_name(circuit_no, values.get("hc3_power_device_id") or values.get("hc3_device_id"), [])
        if values.get("aggregate_group_key") is not None and values.get("hc3_power_device_id") is None:
            raise HTTPException(status_code=400, detail="Bare et punkt med sanntidsmåling kan inngå i en HC3-samlemåler.")
        validate_energy_node_profile_values(values)
        await validate_energy_node_hc3_values(values)
        now_value = datetime.utcnow()
        async with async_session() as session:
            await validate_energy_node_parent(session, circuit_no, values.get("parent_node_id"))
            power_id = values.get("hc3_power_device_id")
            await validate_energy_node_link_uniqueness(
                session,
                power_id,
                values.get("hc3_energy_device_id"),
                values.get("hc3_switch_device_id"),
            )
            node = energy_node_from_values(values, name, now_value)
            session.add(node)
            await session.commit()
            await session.refresh(node)
        return {"status": "ok", "message": f"{node.name} er opprettet.", "id": node.id}

    @router.patch("/api/energy/nodes/{node_id}")
    async def api_v2_energy_node_update(request: Request, node_id: int, data: V2EnergyNodeIn):
        async_session = dependencies.async_session
        clean_energy_node_values = dependencies.clean_energy_node_values
        energy_node_branch_ids = dependencies.energy_node_branch_ids
        require_settings_access = dependencies.require_settings_access
        validate_energy_node_hc3_values = dependencies.validate_energy_node_hc3_values
        validate_energy_node_link_uniqueness = dependencies.validate_energy_node_link_uniqueness
        validate_energy_node_parent = dependencies.validate_energy_node_parent
        validate_energy_node_profile_values = dependencies.validate_energy_node_profile_values
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        values = clean_energy_node_values(data.dict(exclude_unset=True))
        async with async_session() as session:
            node = await session.get(EnergyNode, node_id)
            if not node:
                raise HTTPException(status_code=404, detail="Tilkoblingspunkt ikke funnet.")
            circuit_no = values.get("circuit_no", node.circuit_no)
            if circuit_no is None:
                raise HTTPException(status_code=400, detail="Kurs må fylles ut.")
            parent_node_id = values.get("parent_node_id", node.parent_node_id)
            await validate_energy_node_parent(session, circuit_no, parent_node_id, node_id=node_id)
            if "name" in values and not values.get("name"):
                raise HTTPException(status_code=400, detail="Navn må fylles ut.")
            power_id = values.get("hc3_power_device_id", node.hc3_power_device_id)
            energy_id = values.get("hc3_energy_device_id", node.hc3_energy_device_id)
            aggregate_group_key = values.get("aggregate_group_key", node.aggregate_group_key)
            if aggregate_group_key is not None and power_id is None:
                raise HTTPException(status_code=400, detail="Bare et punkt med sanntidsmåling kan inngå i en HC3-samlemåler.")
            effective_hc3_values = {
                "hc3_device_id": values.get("hc3_device_id", node.hc3_device_id),
                "hc3_power_device_id": power_id,
                "hc3_energy_device_id": energy_id,
                "hc3_switch_device_id": values.get("hc3_switch_device_id", node.hc3_switch_device_id),
                "has_meter": values.get("has_meter", node.has_meter),
                "has_switch": values.get("has_switch", node.has_switch),
            }
            validate_energy_node_profile_values({
                "node_type": values.get("node_type", node.node_type),
                "parent_node_id": parent_node_id,
                "endpoint_key": values.get("endpoint_key", node.endpoint_key),
                "hc3_power_device_id": power_id,
            })
            await validate_energy_node_hc3_values(effective_hc3_values)
            await validate_energy_node_link_uniqueness(
                session,
                power_id,
                energy_id,
                effective_hc3_values.get("hc3_switch_device_id"),
                node_id=node_id,
            )
            now_value = datetime.utcnow()
            if circuit_no != node.circuit_no:
                all_nodes = (await session.execute(select(EnergyNode))).scalars().all()
                branch_ids = energy_node_branch_ids(all_nodes, node_id)
                for branch_node in all_nodes:
                    if branch_node.id is not None and int(branch_node.id) in branch_ids:
                        branch_node.circuit_no = circuit_no
                        branch_node.updated_at = now_value
                await session.execute(
                    update(EnergyLoad)
                    .where(EnergyLoad.energy_node_id.in_(branch_ids))
                    .values(circuit_no=circuit_no, updated_at=now_value)
                )
            for key, value in values.items():
                setattr(node, key, value)
            node.updated_at = now_value
            await session.commit()
        return {"status": "ok", "message": f"{node.name} er lagret.", "id": node.id}

    @router.get("/api/energy/hc3-devices")
    async def api_v2_energy_hc3_devices(
        request: Request,
        q: Optional[str] = Query(None),
        limit: int = Query(500, ge=1, le=1000),
    ):
        HC3_ENERGY_LIVE_TIMEOUT_SECONDS = dependencies.HC3_ENERGY_LIVE_TIMEOUT_SECONDS
        __file__ = dependencies.__file__
        hc3_devices_request = dependencies.hc3_devices_request
        hc3_energy_device_summary = dependencies.hc3_energy_device_summary
        require_settings_access = dependencies.require_settings_access
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        source = "HC3 live"
        error = None
        try:
            devices = await asyncio.to_thread(hc3_devices_request, HC3_ENERGY_LIVE_TIMEOUT_SECONDS)
            rows = [hc3_energy_device_summary(device) for device in devices]
        except Exception as exc:
            source = "Lagret HC3-inventar"
            error = str(exc)
            snapshot_path = Path(__file__).resolve().parent / "docs" / "hc3-energy-inventory-current.json"
            rows = []
            if snapshot_path.exists():
                try:
                    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
                    rows = [hc3_energy_device_summary(device) for device in snapshot.get("all_devices") or [] if isinstance(device, dict)]
                except Exception as snapshot_exc:
                    error = f"{error} · inventar kunne ikke leses: {snapshot_exc}"
        query = str(q or "").strip().lower()
        if query:
            rows = [
                row
                for row in rows
                if query in " ".join(
                    str(row.get(key) or "").lower()
                    for key in ("id", "name", "type", "baseType", "manufacturer", "model", "parentId")
                )
            ]
        rows.sort(key=lambda row: (row.get("dead") is True, row.get("enabled") is False, str(row.get("name") or ""), row.get("id") or 0))
        return {"source": source, "error": error, "count": len(rows), "devices": rows[:limit]}

    @router.get("/api/energy/nodes/live")
    async def api_v2_energy_nodes_live(request: Request):
        async_session = dependencies.async_session
        hc3_energy_nodes_live = dependencies.hc3_energy_nodes_live
        async with async_session() as session:
            nodes = (
                await session.execute(
                    select(EnergyNode)
                    .where(EnergyNode.active.isnot(False))
                    .order_by(EnergyNode.circuit_no.asc(), EnergyNode.parent_node_id.asc(), EnergyNode.name.asc())
                )
            ).scalars().all()
        return await hc3_energy_nodes_live(nodes)

    @router.post("/api/energy/loads")
    async def api_v2_energy_load_create(request: Request, data: V2EnergyLoadIn):
        async_session = dependencies.async_session
        clean_energy_load_values = dependencies.clean_energy_load_values
        find_or_create_energy_node_for_load = dependencies.find_or_create_energy_node_for_load
        require_settings_access = dependencies.require_settings_access
        validate_energy_load_power_values = dependencies.validate_energy_load_power_values
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        values = validate_energy_load_power_values(clean_energy_load_values(data.dict(exclude_unset=True)))
        name = str(values.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Navn må fylles ut.")
        if values.get("circuit_no") is None and values.get("energy_node_id") is None:
            raise HTTPException(status_code=400, detail="Lasten må knyttes til en kurs eller en registrert enhet.")
        now_value = datetime.utcnow()
        async with async_session() as session:
            await find_or_create_energy_node_for_load(session, values)
            load = EnergyLoad(name=name, created_at=now_value, updated_at=now_value, source="manual")
            for key, value in values.items():
                if key == "name":
                    continue
                if isinstance(value, str):
                    value = value.strip() or None
                setattr(load, key, value)
            if load.active is None:
                load.active = True
            session.add(load)
            await session.commit()
            await session.refresh(load)
        return {"status": "ok", "message": f"Last {load.name} er opprettet.", "id": load.id}

    @router.patch("/api/energy/loads/{load_id}")
    async def api_v2_energy_load_update(request: Request, load_id: int, data: V2EnergyLoadIn):
        async_session = dependencies.async_session
        clean_energy_load_values = dependencies.clean_energy_load_values
        find_or_create_energy_node_for_load = dependencies.find_or_create_energy_node_for_load
        require_settings_access = dependencies.require_settings_access
        validate_energy_load_power_values = dependencies.validate_energy_load_power_values
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        values = clean_energy_load_values(data.dict(exclude_unset=True))
        async with async_session() as session:
            load = await session.get(EnergyLoad, load_id)
            if not load:
                raise HTTPException(status_code=404, detail="Last ikke funnet")
            validate_energy_load_power_values(values, existing=load)
            if "name" in values and not str(values.get("name") or "").strip():
                raise HTTPException(status_code=400, detail="Navn må fylles ut.")
            await find_or_create_energy_node_for_load(session, values)
            for key, value in values.items():
                if isinstance(value, str):
                    value = value.strip() or None
                setattr(load, key, value)
            load.source = load.source or "manual"
            load.updated_at = datetime.utcnow()
            await session.commit()
        return {"status": "ok", "message": f"Last {load.name} er lagret."}

    @router.get("/energi")
    async def energy_redirect(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/energi/status", status_code=307)

    @router.get("/energi/oversikt", response_class=HTMLResponse)
    async def energy_overview_legacy_redirect(request: Request):
        redirect_keep_query = dependencies.redirect_keep_query
        return redirect_keep_query(request, "/energi/status", status_code=307)

    @router.post("/api/energy/elvia/upload")
    async def api_energy_elvia_upload(request: Request, background_tasks: BackgroundTasks):
        async_session = dependencies.async_session
        mark_import_job_running = dependencies.mark_import_job_running
        require_settings_access = dependencies.require_settings_access
        run_elvia_import_background = dependencies.run_elvia_import_background
        forbidden = require_settings_access(request)
        if forbidden:
            return forbidden
        try:
            form = await request.form()
            upload = form.get("file")
            filename = Path(getattr(upload, "filename", "") or "").name
            if not upload or not filename or not hasattr(upload, "read"):
                return JSONResponse({"detail": "Velg en JSON-fil fra Elvia før du importerer."}, status_code=400)
            content = await upload.read()
            if not content:
                return JSONResponse({"detail": "Filen er tom."}, status_code=400)
            async with async_session() as session:
                await mark_import_job_running(
                    session,
                    "elvia_monthly_import",
                    source="Manuell opplasting",
                    message=f"Importerer {filename}",
                    raw={"source_file": filename},
                )
                await session.commit()
            background_tasks.add_task(run_elvia_import_background, content, filename)
            return {"status": "ok", "message": f"Importen er startet for {filename}.", "filename": filename}
        except Exception as exc:
            return JSONResponse({"detail": str(exc)}, status_code=400)

    @router.get("/energi/status", response_class=HTMLResponse)
    async def energy_status_view(request: Request, day: Optional[str] = None):
        ENERGY_HC3_HOURLY_DISPLAY_OFFSET = dependencies.ENERGY_HC3_HOURLY_DISPLAY_OFFSET
        async_session = dependencies.async_session
        energy_area_cards = dependencies.energy_area_cards
        parse_day = dependencies.parse_day
        templates = dependencies.templates
        today = local_now_naive().date()
        selected_day = parse_day(day)
        day_start = datetime.combine(selected_day, time.min)
        day_end = day_start + timedelta(days=1)
        async with async_session() as session:
            latest = (
                await session.execute(
                    select(EnergyFibaroSample)
                    .order_by(EnergyFibaroSample.bucket_start.desc())
                    .limit(1)
                )
            ).scalars().first()
            today_rows = (
                await session.execute(
                    select(EnergyFibaroSample)
                    .where(EnergyFibaroSample.bucket_start >= day_start)
                    .where(EnergyFibaroSample.bucket_start < day_end)
                    .order_by(EnergyFibaroSample.bucket_start.desc())
                )
            ).scalars().all()
            rows = (
                await session.execute(
                    select(EnergyFibaroSample)
                    .order_by(EnergyFibaroSample.bucket_start.desc())
                    .limit(120)
                )
            ).scalars().all()
            compare_start = day_start + ENERGY_HC3_HOURLY_DISPLAY_OFFSET
            compare_end = day_end + ENERGY_HC3_HOURLY_DISPLAY_OFFSET
            compare_rows = (
                await session.execute(
                    select(EnergyFibaroSample)
                    .where(EnergyFibaroSample.bucket_start >= compare_start)
                    .where(EnergyFibaroSample.bucket_start < compare_end)
                    .order_by(EnergyFibaroSample.bucket_start.asc())
                )
            ).scalars().all()
            elvia_today = (
                await session.execute(
                    select(func.coalesce(func.sum(EnergyHourlyConsumption.consumption_kwh), 0))
                    .where(EnergyHourlyConsumption.stat_date == selected_day)
                )
            ).scalar_one()
            elvia_hours = (
                await session.execute(
                    select(EnergyHourlyConsumption.hour, EnergyHourlyConsumption.consumption_kwh)
                    .where(EnergyHourlyConsumption.stat_date == selected_day)
                    .order_by(EnergyHourlyConsumption.hour)
                )
            ).all()
            latest_elvia = (
                await session.execute(
                    select(EnergyHourlyConsumption)
                    .order_by(EnergyHourlyConsumption.measured_at.desc())
                    .limit(1)
                )
            ).scalars().first()
            latest_elvia_import = (
                await session.execute(
                    select(EnergyImportRun)
                    .order_by(EnergyImportRun.timestamp.desc())
                    .limit(1)
                )
            ).scalars().first()

        totals = {
            "inntak_delta_kwh": sum(float_or_zero(row.inntak_delta_kwh) for row in today_rows),
            "varmepumper_delta_kwh": sum(float_or_zero(row.varmepumper_delta_kwh) for row in today_rows),
            "belysning_delta_kwh": sum(float_or_zero(row.belysning_delta_kwh) for row in today_rows),
            "massasje_delta_kwh": sum(float_or_zero(row.massasje_delta_kwh) for row in today_rows),
            "annet_delta_kwh": sum(float_or_zero(row.annet_delta_kwh) for row in today_rows),
            "avfukter_delta_kwh": sum(float_or_zero(row.avfukter_delta_kwh) for row in today_rows),
            "differanse_beregnet_delta_kwh": sum(float_or_zero(row.differanse_beregnet_delta_kwh) for row in today_rows),
        }
        reset_counts = {
            "inntak": sum(1 for row in today_rows if row.inntak_reset),
            "varmepumper": sum(1 for row in today_rows if row.varmepumper_reset),
            "belysning": sum(1 for row in today_rows if row.belysning_reset),
            "massasje": sum(1 for row in today_rows if row.massasje_reset),
            "annet": sum(1 for row in today_rows if row.annet_reset),
            "avfukter": sum(1 for row in today_rows if row.avfukter_reset),
        }
        measured_by_hour = {hour: 0.0 for hour in range(24)}
        for row in compare_rows:
            if row.bucket_start is None:
                continue
            display_time = row.bucket_start - ENERGY_HC3_HOURLY_DISPLAY_OFFSET
            if display_time.date() != selected_day:
                continue
            measured_by_hour[display_time.hour] += float_or_zero(row.inntak_delta_kwh)

        elvia_by_hour = {hour: 0.0 for hour in range(24)}
        elvia_present = set()
        for hour, consumption_kwh in elvia_hours:
            if hour is None:
                continue
            elvia_by_hour[int(hour)] += float_or_zero(consumption_kwh)
            elvia_present.add(int(hour))

        hourly_max = max(
            [0.1]
            + [measured_by_hour[hour] for hour in range(24)]
            + [elvia_by_hour[hour] for hour in range(24)]
        )
        hourly_energy = []
        for hour in range(24):
            measured_kwh = measured_by_hour[hour]
            elvia_kwh = elvia_by_hour[hour]
            hourly_energy.append(
                {
                    "hour": f"{hour:02d}",
                    "measured_kwh": measured_kwh,
                    "elvia_kwh": elvia_kwh,
                    "has_elvia": hour in elvia_present,
                    "measured_height": round((measured_kwh / hourly_max) * 100, 2) if hourly_max else 0,
                    "elvia_height": round((elvia_kwh / hourly_max) * 100, 2) if hourly_max else 0,
                }
            )
        measured_day_kwh = totals["inntak_delta_kwh"]
        measured_compare_kwh = sum(measured_by_hour.values())
        elvia_day_kwh = float_or_zero(elvia_today)
        energy_deviation_kwh = measured_compare_kwh - elvia_day_kwh
        latest_elvia_day = latest_elvia.stat_date if latest_elvia else None
        elvia_missing_for_day = latest_elvia_day is None or selected_day > latest_elvia_day
        return templates.TemplateResponse(
            request,
            "energy.html",
            {
                "latest": latest,
                "rows": rows,
                "area_cards": energy_area_cards(latest, totals, reset_counts),
                "totals": totals,
                "sample_count": len(today_rows),
                "elvia_today_kwh": elvia_day_kwh,
                "measured_compare_kwh": measured_compare_kwh,
                "compare_sample_count": len(compare_rows),
                "hourly_energy": hourly_energy,
                "hourly_max_kwh": hourly_max,
                "energy_deviation_kwh": energy_deviation_kwh,
                "latest_elvia": latest_elvia,
                "latest_elvia_import": latest_elvia_import,
                "latest_elvia_day": latest_elvia_day.isoformat() if latest_elvia_day else None,
                "elvia_missing_for_day": elvia_missing_for_day,
                "selected_day": selected_day.isoformat(),
                "selected_day_label": selected_day.strftime("%d.%m.%Y"),
                "prev_day": (selected_day - timedelta(days=1)).isoformat(),
                "next_day": (selected_day + timedelta(days=1)).isoformat(),
                "is_today": selected_day == today,
                "today": today.isoformat(),
            },
        )

    @router.get("/energi/kurser", response_class=HTMLResponse)
    async def energy_circuits_view(
        request: Request,
        edit: Optional[str] = None,
        sunbeds: Optional[str] = None,
        view: Optional[str] = None,
    ):
        async_session = dependencies.async_session
        templates = dependencies.templates
        sunbed_filter = normalize_energy_sunbed_filter(sunbeds)
        hierarchy_mode = (view or "").strip().lower() in {"hierarki", "hierarchy", "tree"}
        async with async_session() as session:
            all_circuits = (
                await session.execute(
                    select(EnergyCircuit).order_by(EnergyCircuit.circuit_no.asc())
                )
            ).scalars().all()
            circuits = filter_energy_circuits_by_sunbed(all_circuits, sunbed_filter)
            visible_circuit_numbers = [row.circuit_no for row in circuits]
            load_rows = (
                await session.execute(
                    select(
                        EnergyLoad.circuit_no,
                        func.count(EnergyLoad.id).label("count"),
                        func.coalesce(func.sum(EnergyLoad.expected_power_w), 0).label("expected_power_w"),
                    )
                    .where(EnergyLoad.circuit_no.is_not(None))
                    .where(EnergyLoad.circuit_no.in_(visible_circuit_numbers))
                    .group_by(EnergyLoad.circuit_no)
                )
            ).all()
            course_load_rows = (
                await session.execute(
                    select(EnergyLoad)
                    .where(EnergyLoad.circuit_no.is_not(None))
                    .where(EnergyLoad.circuit_no.in_(visible_circuit_numbers))
                    .order_by(EnergyLoad.circuit_no.asc(), EnergyLoad.active.desc(), EnergyLoad.name.asc())
                )
            ).scalars().all()
        load_lookup = {
            row.circuit_no: {
                "count": int(row.count or 0),
                "expected_power_w": float_or_zero(row.expected_power_w),
            }
            for row in load_rows
        }
        course_load_lookup = defaultdict(list)
        for row in course_load_rows:
            course_load_lookup[row.circuit_no].append(row)
        summary = {
            "circuits": len(circuits),
            "with_breaker": sum(1 for row in circuits if row.breaker_rating_a is not None),
            "missing_breaker": sum(1 for row in circuits if row.breaker_rating_a is None),
            "sunbed_circuits": sum(1 for row in circuits if energy_circuit_is_sunbed(row)),
            "loads": sum(item["count"] for item in load_lookup.values()),
            "expected_power_w": sum(item["expected_power_w"] for item in load_lookup.values()),
        }
        edit_mode = (edit or "").strip().lower() in {"1", "true", "yes", "ja"}
        view_value = "hierarki" if hierarchy_mode else ""
        urls = {
            "all": energy_query_url("/energi/kurser", edit="1" if edit_mode else "", view=view_value),
            "hide_sunbeds": energy_query_url("/energi/kurser", edit="1" if edit_mode else "", sunbeds="hide", view=view_value),
            "only_sunbeds": energy_query_url("/energi/kurser", edit="1" if edit_mode else "", sunbeds="only", view=view_value),
            "hierarchy": energy_query_url("/energi/kurser", edit="1" if edit_mode else "", sunbeds=sunbed_filter, view="hierarki"),
            "table": energy_query_url("/energi/kurser", edit="1" if edit_mode else "", sunbeds=sunbed_filter),
            "edit": energy_query_url("/energi/kurser", edit="1", sunbeds=sunbed_filter, view=view_value),
            "view": energy_query_url("/energi/kurser", sunbeds=sunbed_filter, view=view_value),
            "pdf": energy_query_url("/energi/kurser/pdf", sunbeds=sunbed_filter),
        }
        return templates.TemplateResponse(
            request,
            "energy_circuits.html",
            {
                "circuits": circuits,
                "load_lookup": load_lookup,
                "course_load_lookup": course_load_lookup,
                "summary": summary,
                "edit_mode": edit_mode,
                "hierarchy_mode": hierarchy_mode,
                "sunbed_filter": sunbed_filter,
                "urls": urls,
                "circuit_technical_label": circuit_technical_label,
                "energy_circuit_is_sunbed": energy_circuit_is_sunbed,
            },
        )

    @router.post("/energi/kurser/{circuit_no}")
    async def energy_circuit_save(request: Request, circuit_no: int):
        async_session = dependencies.async_session
        form = await request.form()
        async with async_session() as session:
            circuit = (
                await session.execute(
                    select(EnergyCircuit).where(EnergyCircuit.circuit_no == circuit_no)
                )
            ).scalars().first()
            if not circuit:
                raise HTTPException(status_code=404, detail="Kurs ikke funnet")
            if "description" in form:
                circuit.description = form_text(form, "description")
            if "breaker_type" in form:
                circuit.breaker_type = form_text(form, "breaker_type")
            if "breaker_rating_a" in form:
                circuit.breaker_rating_a = form_float(form, "breaker_rating_a")
            if "breaker_characteristic" in form:
                circuit.breaker_characteristic = form_text(form, "breaker_characteristic")
            if "cable_spec" in form:
                circuit.cable_spec = form_text(form, "cable_spec")
            if "cable_length_m" in form:
                circuit.cable_length_m = form_float(form, "cable_length_m")
            if "install_method" in form:
                circuit.install_method = form_text(form, "install_method")
            if "terminal_ref" in form:
                circuit.terminal_ref = form_text(form, "terminal_ref")
            if "rcd_ma" in form:
                circuit.rcd_ma = form_float(form, "rcd_ma")
            if "is_sunbed" in form:
                circuit.is_sunbed = form_bool(form, "is_sunbed")
            if "status" in form:
                circuit.status = form_text(form, "status") or "ukjent"
            if "note" in form:
                circuit.note = form_text(form, "note")
            circuit.updated_at = datetime.utcnow()
            await session.commit()
        return_view = "hierarki" if form_text(form, "return_view") == "hierarki" else ""
        return_sunbeds = normalize_energy_sunbed_filter(form_text(form, "return_sunbeds"))
        target = energy_query_url("/energi/kurser", edit="1", sunbeds=return_sunbeds, view=return_view)
        return RedirectResponse(f"{target}#kurs-{circuit_no}", status_code=303)

    @router.get("/energi/kurser/pdf")
    async def energy_circuits_pdf(sunbeds: Optional[str] = None):
        async_session = dependencies.async_session
        sunbed_filter = normalize_energy_sunbed_filter(sunbeds)
        async with async_session() as session:
            all_circuits = (
                await session.execute(
                    select(EnergyCircuit).order_by(EnergyCircuit.circuit_no.asc())
                )
            ).scalars().all()
            circuits = filter_energy_circuits_by_sunbed(all_circuits, sunbed_filter)
            visible_circuit_numbers = [row.circuit_no for row in circuits]
            load_rows = (
                await session.execute(
                    select(
                        EnergyLoad.circuit_no,
                        func.count(EnergyLoad.id).label("count"),
                        func.coalesce(func.sum(EnergyLoad.expected_power_w), 0).label("expected_power_w"),
                    )
                    .where(EnergyLoad.circuit_no.is_not(None))
                    .where(EnergyLoad.circuit_no.in_(visible_circuit_numbers))
                    .group_by(EnergyLoad.circuit_no)
                )
            ).all()
        load_lookup = {
            row.circuit_no: {
                "count": int(row.count or 0),
                "expected_power_w": float_or_zero(row.expected_power_w),
            }
            for row in load_rows
        }
        rows = []
        for circuit in circuits:
            load_info = load_lookup.get(circuit.circuit_no, {"count": 0, "expected_power_w": 0})
            rows.append(
                [
                    circuit.circuit_no,
                    circuit.description or "-",
                    f"{circuit.breaker_rating_a:g} A" if circuit.breaker_rating_a is not None else "-",
                    "ja" if energy_circuit_is_sunbed(circuit) else "nei",
                    load_info["count"],
                    f"{load_info['expected_power_w']:,.0f} W".replace(",", " "),
                    circuit.status or "-",
                    circuit.note or "-",
                ]
            )
        pdf_bytes = build_table_pdf(
            "Energi - kursliste",
            "Elektriske kurser med vern, kabel, jordfeilbryter og koblede laster."
            + (" PDF-en følger valgt solsengfilter." if sunbed_filter else ""),
            [
                {"label": "Kurs", "width": 34, "align": "right"},
                {"label": "Beskrivelse", "width": 255},
                {"label": "A", "width": 45, "align": "right"},
                {"label": "Solseng", "width": 48},
                {"label": "Laster", "width": 44, "align": "right"},
                {"label": "Effekt", "width": 70, "align": "right"},
                {"label": "Status", "width": 72},
                {"label": "Notat", "width": 178},
            ],
            rows,
            generated_at=local_now_naive(),
        )
        return pdf_response(pdf_bytes, f"lilletorget_energi_kursliste_{local_now_naive().date().isoformat()}.pdf")

    @router.get("/energi/laster", response_class=HTMLResponse)
    async def energy_loads_view(
        request: Request,
        q: Optional[str] = None,
        circuit: Optional[int] = None,
        load_type: Optional[str] = None,
        active: Optional[str] = None,
        sunbeds: Optional[str] = None,
    ):
        async_session = dependencies.async_session
        templates = dependencies.templates
        q_value = (q or "").strip()
        sunbed_filter = normalize_energy_sunbed_filter(sunbeds)
        async with async_session() as session:
            circuits = (
                await session.execute(
                    select(EnergyCircuit).order_by(EnergyCircuit.circuit_no.asc())
                )
            ).scalars().all()
            type_rows = (
                await session.execute(
                    select(EnergyLoad.load_type)
                    .where(EnergyLoad.load_type.is_not(None))
                    .where(func.trim(EnergyLoad.load_type) != "")
                    .distinct()
                    .order_by(EnergyLoad.load_type.asc())
                )
            ).all()
            sunbed_circuit_numbers = [row.circuit_no for row in circuits if energy_circuit_is_sunbed(row)]
            query = select(EnergyLoad).order_by(EnergyLoad.active.desc(), EnergyLoad.circuit_no.asc(), EnergyLoad.name.asc())
            if q_value:
                pattern = f"%{q_value}%"
                query = query.where(
                    or_(
                        EnergyLoad.name.ilike(pattern),
                        EnergyLoad.area.ilike(pattern),
                        EnergyLoad.note.ilike(pattern),
                        EnergyLoad.load_type.ilike(pattern),
                    )
                )
            if circuit:
                query = query.where(EnergyLoad.circuit_no == circuit)
            if load_type:
                query = query.where(EnergyLoad.load_type == load_type)
            if active == "1":
                query = query.where(EnergyLoad.active.is_(True))
            elif active == "0":
                query = query.where(EnergyLoad.active.is_(False))
            if sunbed_filter == "hide":
                query = query.where(or_(EnergyLoad.circuit_no.is_(None), ~EnergyLoad.circuit_no.in_(sunbed_circuit_numbers)))
            elif sunbed_filter == "only":
                query = query.where(EnergyLoad.circuit_no.in_(sunbed_circuit_numbers))
            loads = (await session.execute(query)).scalars().all()
            all_loads = (await session.execute(select(EnergyLoad))).scalars().all()
        circuit_lookup = {row.circuit_no: row for row in circuits}
        summary = {
            "loads": len(all_loads),
            "active": sum(1 for row in all_loads if row.active),
            "direct": sum(1 for row in all_loads if row.measured_direct),
            "expected_power_w": sum(float_or_zero(row.expected_power_w) for row in all_loads if row.active),
        }
        return templates.TemplateResponse(
            request,
            "energy_loads.html",
            {
                "loads": loads,
                "circuits": circuits,
                "circuit_lookup": circuit_lookup,
                "load_types": [row.load_type for row in type_rows if row.load_type],
                "summary": summary,
                "filters": {
                    "q": q_value,
                    "circuit": circuit,
                    "load_type": load_type or "",
                    "active": active or "",
                    "sunbeds": sunbed_filter,
                },
                "energy_circuit_is_sunbed": energy_circuit_is_sunbed,
            },
        )

    @router.get("/energi/laster/pdf")
    async def energy_loads_pdf(
        q: Optional[str] = None,
        circuit: Optional[int] = None,
        load_type: Optional[str] = None,
        active: Optional[str] = None,
        sunbeds: Optional[str] = None,
    ):
        async_session = dependencies.async_session
        q_value = (q or "").strip()
        sunbed_filter = normalize_energy_sunbed_filter(sunbeds)
        async with async_session() as session:
            circuit_rows = (
                await session.execute(
                    select(EnergyCircuit).order_by(EnergyCircuit.circuit_no.asc())
                )
            ).scalars().all()
            sunbed_circuit_numbers = [row.circuit_no for row in circuit_rows if energy_circuit_is_sunbed(row)]
            query = select(EnergyLoad).order_by(EnergyLoad.active.desc(), EnergyLoad.circuit_no.asc(), EnergyLoad.name.asc())
            if q_value:
                pattern = f"%{q_value}%"
                query = query.where(
                    or_(
                        EnergyLoad.name.ilike(pattern),
                        EnergyLoad.area.ilike(pattern),
                        EnergyLoad.note.ilike(pattern),
                        EnergyLoad.load_type.ilike(pattern),
                    )
                )
            if circuit:
                query = query.where(EnergyLoad.circuit_no == circuit)
            if load_type:
                query = query.where(EnergyLoad.load_type == load_type)
            if active == "1":
                query = query.where(EnergyLoad.active.is_(True))
            elif active == "0":
                query = query.where(EnergyLoad.active.is_(False))
            if sunbed_filter == "hide":
                query = query.where(or_(EnergyLoad.circuit_no.is_(None), ~EnergyLoad.circuit_no.in_(sunbed_circuit_numbers)))
            elif sunbed_filter == "only":
                query = query.where(EnergyLoad.circuit_no.in_(sunbed_circuit_numbers))
            loads = (await session.execute(query)).scalars().all()
        circuit_lookup = {row.circuit_no: row for row in circuit_rows}
        rows = []
        for load in loads:
            ids = []
            if load.fibaro_device_id:
                ids.append(f"Fibaro enhet {load.fibaro_device_id}")
            if load.fibaro_meter_id:
                ids.append(f"måler {load.fibaro_meter_id}")
            if load.zwave_switch_id:
                ids.append(f"Z-Wave {load.zwave_switch_id}")
            flags = []
            if load.measured_direct:
                flags.append("direkte målt")
            if load.controllable:
                flags.append("kan styres")
            if load.critical:
                flags.append("kritisk")
            circuit_label = "-"
            if load.circuit_no:
                circuit = circuit_lookup.get(load.circuit_no)
                circuit_label = f"{load.circuit_no} - {circuit.description}" if circuit else str(load.circuit_no)
                if circuit and energy_circuit_is_sunbed(circuit):
                    circuit_label += " (solseng)"
            rows.append(
                [
                    load.name,
                    load.load_type or "-",
                    load.area or "-",
                    circuit_label,
                    f"{load.expected_power_w:,.0f} W".replace(",", " ") if load.expected_power_w is not None else "-",
                    ", ".join(ids) if ids else "-",
                    ", ".join(flags) if flags else "-",
                    "aktiv" if load.active else "inaktiv",
                    load.note or "-",
                ]
            )
        subtitle = "Praktiske laster med kurs, forventet effekt og Fibaro/Z-Wave-koblinger."
        if q_value or circuit or load_type or active or sunbed_filter:
            subtitle += " PDF-en følger filtreringen i skjermbildet."
        pdf_bytes = build_table_pdf(
            "Energi - lastregister",
            subtitle,
            [
                {"label": "Last", "width": 145},
                {"label": "Type", "width": 70},
                {"label": "Område", "width": 72},
                {"label": "Kurs", "width": 200},
                {"label": "Effekt", "width": 64, "align": "right"},
                {"label": "ID-er", "width": 115},
                {"label": "Egenskaper", "width": 112},
                {"label": "Status", "width": 54},
                {"label": "Notat", "width": 140},
            ],
            rows,
            generated_at=local_now_naive(),
        )
        return pdf_response(pdf_bytes, f"lilletorget_energi_laster_{local_now_naive().date().isoformat()}.pdf")

    @router.post("/energi/laster", response_class=HTMLResponse)
    async def energy_load_save(request: Request):
        async_session = dependencies.async_session
        redirect_keep_query = dependencies.redirect_keep_query
        form = await request.form()
        name = form_text(form, "name")
        if not name:
            return redirect_keep_query(request, "/energi/laster?error=missing_name", status_code=303)
        load_id = form_int(form, "load_id")
        now_value = datetime.utcnow()
        async with async_session() as session:
            if load_id:
                load = await session.get(EnergyLoad, load_id)
                if not load:
                    raise HTTPException(status_code=404, detail="Last ikke funnet")
            else:
                load = EnergyLoad(created_at=now_value)
                session.add(load)
            load.name = name
            load.load_type = form_text(form, "load_type")
            load.area = form_text(form, "area")
            load.circuit_no = form_int(form, "circuit_no")
            load.expected_power_w = form_float(form, "expected_power_w")
            load.measured_direct = form_bool(form, "measured_direct")
            load.fibaro_device_id = form_int(form, "fibaro_device_id")
            load.fibaro_meter_id = form_int(form, "fibaro_meter_id")
            load.zwave_switch_id = form_int(form, "zwave_switch_id")
            load.controllable = form_bool(form, "controllable")
            load.critical = form_bool(form, "critical")
            load.active = form_bool(form, "active", default=True)
            load.note = form_text(form, "note")
            load.source = "manual"
            load.updated_at = now_value
            await session.commit()
        suffix = f"?circuit={load.circuit_no}" if load.circuit_no else ""
        return redirect_keep_query(request, f"/energi/laster{suffix}", status_code=303)

    @router.post("/energi/laster/{load_id}/aktiv")
    async def energy_load_toggle_active(request: Request, load_id: int):
        async_session = dependencies.async_session
        redirect_keep_query = dependencies.redirect_keep_query
        form = await request.form()
        async with async_session() as session:
            load = await session.get(EnergyLoad, load_id)
            if not load:
                raise HTTPException(status_code=404, detail="Last ikke funnet")
            load.active = form_bool(form, "active")
            load.updated_at = datetime.utcnow()
            await session.commit()
        return redirect_keep_query(request, "/energi/laster", status_code=303)

    @router.get("/api/energi/fibaro/json")
    async def energy_fibaro_json(limit: int = 300):
        async_session = dependencies.async_session
        row_to_dict = dependencies.row_to_dict
        limit = max(1, min(limit, 5000))
        async with async_session() as session:
            rows = (
                await session.execute(
                    select(EnergyFibaroSample)
                    .order_by(EnergyFibaroSample.bucket_start.desc())
                    .limit(limit)
                )
            ).scalars().all()
        return {"rows": [row_to_dict(row, ENERGY_FIBARO_COLUMNS) for row in rows]}

    @router.get("/classic/energi/forbruk-per-seng", response_class=HTMLResponse)
    @router.get("/energi/forbruk-per-seng", response_class=HTMLResponse)
    async def energy_sunbed_consumption_view(
        request: Request,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ):
        async_session = dependencies.async_session
        load_sunbed_power_analysis = dependencies.load_sunbed_power_analysis
        templates = dependencies.templates
        today = local_now_naive().date()
        async with async_session() as session:
            analysis = await load_sunbed_power_analysis(session, date_from, date_to, today)
        response = templates.TemplateResponse(
            request,
            "energy_sunbeds.html",
            {
                "date_from": analysis["dateFrom"],
                "date_to": analysis["dateTo"],
                "max_days": analysis["maxDays"],
                "analysis": analysis,
                "rooms": analysis["rooms"],
                "observations": analysis["observations"],
                "summary": analysis["summary"],
                "max_power": analysis["maxPower"],
            },
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @router.get("/energi/elvia", response_class=HTMLResponse)
    async def energy_elvia_view(request: Request):
        async_session = dependencies.async_session
        get_energy_summaries = dependencies.get_energy_summaries
        templates = dependencies.templates
        message = request.query_params.get("message", "")
        error = request.query_params.get("error", "")
        async with async_session() as session:
            summaries = await get_energy_summaries(session)
            rows = (
                await session.execute(
                    select(EnergyHourlyConsumption)
                    .order_by(EnergyHourlyConsumption.measured_at.desc())
                    .limit(24)
                )
            ).scalars().all()
            imports = (
                await session.execute(
                    select(EnergyImportRun)
                    .order_by(EnergyImportRun.timestamp.desc())
                    .limit(25)
                )
            ).scalars().all()
            elvia_status = (
                await session.execute(select(ImportJobStatus).where(ImportJobStatus.job_name == "elvia_monthly_import"))
            ).scalars().first()
        return templates.TemplateResponse(
            request,
            "energy_elvia.html",
            {
                "rows": list(reversed(rows)),
                "imports": imports,
                "elvia_status": elvia_status,
                "summaries": summaries,
                "message": message,
                "error": error,
                "import_result": None,
            },
        )

    @router.post("/energi/elvia", response_class=HTMLResponse)
    async def energy_elvia_upload(request: Request, background_tasks: BackgroundTasks):
        async_session = dependencies.async_session
        get_energy_summaries = dependencies.get_energy_summaries
        mark_import_job_running = dependencies.mark_import_job_running
        redirect_with_query_params = dependencies.redirect_with_query_params
        run_elvia_import_background = dependencies.run_elvia_import_background
        templates = dependencies.templates
        message = ""
        error = ""
        import_result = None
        if not getattr(request.state, "auth_can_settings", False):
            error = "Du må ha innstillingstilgang for å importere Elvia-filer."
        else:
            try:
                form = await request.form()
                upload = form.get("file")
                filename = getattr(upload, "filename", "") or ""
                if not upload or not filename:
                    raise ValueError("Velg en JSON-fil fra Elvia før du importerer.")
                content = await upload.read()
                async with async_session() as session:
                    await mark_import_job_running(
                        session,
                        "elvia_monthly_import",
                        source="Manuell opplasting",
                        message=f"Importerer {filename}",
                        raw={"source_file": filename},
                    )
                    await session.commit()
                background_tasks.add_task(run_elvia_import_background, content, filename)
                message = f"Importen er startet for {filename}. Siden kan brukes mens jobben kjører."
                return redirect_with_query_params(request, "/energi/elvia", message=message)
            except (json.JSONDecodeError, UnicodeDecodeError):
                error = "Filen kunne ikke leses som gyldig JSON."
            except Exception as exc:
                error = str(exc)

        async with async_session() as session:
            summaries = await get_energy_summaries(session, force=bool(import_result and not error))
            rows = (
                await session.execute(
                    select(EnergyHourlyConsumption)
                    .order_by(EnergyHourlyConsumption.measured_at.desc())
                    .limit(24)
                )
            ).scalars().all()
            imports = (
                await session.execute(
                    select(EnergyImportRun)
                    .order_by(EnergyImportRun.timestamp.desc())
                    .limit(25)
                )
            ).scalars().all()
            elvia_status = (
                await session.execute(select(ImportJobStatus).where(ImportJobStatus.job_name == "elvia_monthly_import"))
            ).scalars().first()
        return templates.TemplateResponse(
            request,
            "energy_elvia.html",
            {
                "rows": list(reversed(rows)),
                "imports": imports,
                "elvia_status": elvia_status,
                "summaries": summaries,
                "message": message,
                "error": error,
                "import_result": import_result,
            },
        )

    @router.get("/api/energi/elvia/json")
    async def energy_elvia_json(limit: int = 300):
        async_session = dependencies.async_session
        get_energy_summaries = dependencies.get_energy_summaries
        row_to_dict = dependencies.row_to_dict
        limit = max(1, min(limit, 5000))
        async with async_session() as session:
            summaries = await get_energy_summaries(session)
            rows = (
                await session.execute(
                    select(EnergyHourlyConsumption)
                    .order_by(EnergyHourlyConsumption.measured_at.desc())
                    .limit(limit)
                )
            ).scalars().all()
            imports = (
                await session.execute(
                    select(EnergyImportRun)
                    .order_by(EnergyImportRun.timestamp.desc())
                    .limit(min(limit, 500))
                )
            ).scalars().all()
        return {
            "rows": [row_to_dict(row, ENERGY_HOURLY_COLUMNS) for row in rows],
            "imports": [row_to_dict(row, ENERGY_IMPORT_COLUMNS) for row in imports],
            "daily_totals": summaries["daily"],
            "monthly_totals": summaries["monthly"],
            "yearly_totals": summaries["yearly"],
            "top_days": summaries["top_days"],
            "top_months": summaries["top_months"],
            "grand_total": summaries["total"],
            "first_at": summaries["first_at"],
            "last_at": summaries["last_at"],
            "total_rows": summaries["total"]["hours_count"],
        }

    @router.get("/classic/energi/kurser/pdf")
    async def classic_energy_circuits_pdf(sunbeds: Optional[str] = None):
        return await energy_circuits_pdf(sunbeds)

    @router.get("/classic/energi/laster/pdf")
    async def classic_energy_loads_pdf(
        q: Optional[str] = None,
        circuit: Optional[int] = None,
        load_type: Optional[str] = None,
        active: Optional[str] = None,
        sunbeds: Optional[str] = None,
    ):
        return await energy_loads_pdf(q, circuit, load_type, active, sunbeds)

    return RouterBundle(router, {
        "api_energy_elvia_upload": api_energy_elvia_upload,
        "api_v2_energy_circuit_update": api_v2_energy_circuit_update,
        "api_v2_energy_hc3_devices": api_v2_energy_hc3_devices,
        "api_v2_energy_load_create": api_v2_energy_load_create,
        "api_v2_energy_load_update": api_v2_energy_load_update,
        "api_v2_energy_node_create": api_v2_energy_node_create,
        "api_v2_energy_node_update": api_v2_energy_node_update,
        "api_v2_energy_nodes_live": api_v2_energy_nodes_live,
        "classic_energy_circuits_pdf": classic_energy_circuits_pdf,
        "classic_energy_loads_pdf": classic_energy_loads_pdf,
        "energy_circuit_save": energy_circuit_save,
        "energy_circuits_pdf": energy_circuits_pdf,
        "energy_circuits_view": energy_circuits_view,
        "energy_elvia_json": energy_elvia_json,
        "energy_elvia_upload": energy_elvia_upload,
        "energy_elvia_view": energy_elvia_view,
        "energy_fibaro_json": energy_fibaro_json,
        "energy_load_save": energy_load_save,
        "energy_load_toggle_active": energy_load_toggle_active,
        "energy_loads_pdf": energy_loads_pdf,
        "energy_loads_view": energy_loads_view,
        "energy_overview_legacy_redirect": energy_overview_legacy_redirect,
        "energy_redirect": energy_redirect,
        "energy_status_view": energy_status_view,
        "energy_sunbed_consumption_view": energy_sunbed_consumption_view,
        "energy_view": energy_view,
    }, dependencies)
