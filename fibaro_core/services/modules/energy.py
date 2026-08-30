"""Energy module response assembly, independent of HTTP registration."""

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from energy_helpers import energy_circuit_is_sunbed
from energy_helpers import filter_energy_circuits_by_sunbed
from energy_helpers import normalize_energy_sunbed_filter
from fibaro_core.models import EnergyCircuit
from fibaro_core.models import EnergyFibaroSample
from fibaro_core.models import EnergyImportRun
from fibaro_core.models import EnergyLoad
from fibaro_core.models import EnergyNode
from fibaro_core.services.presentation import api_card
from fibaro_core.services.presentation import api_chart
from fibaro_core.services.presentation import api_table
from fibaro_core.services.presentation import format_short_number
from fibaro_core.services.summaries.periods import add_months
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from time_formatting import api_local_iso
from typing import Any
from v2_navigation import v2_module_title
from value_parsing import float_or_zero


@dataclass
class Dependencies:
    api_config_value_rows: Any
    api_day_navigation: Any
    api_energy_circuit_edit: Any
    api_energy_load_edit: Any
    api_filter: Any
    api_filter_int: Any
    api_filter_options: Any
    api_filter_value: Any
    api_pick: Any
    api_tool_row: Any
    build_energy_circuit_loads_payload: Any
    circuit_row_api: Any
    cumulative_energy_points: Any
    decimate_rows: Any
    energy_elvia_control_module_payload: Any
    energy_elvia_module_payload: Any
    load_row_api: Any
    load_sunbed_power_analysis: Any
    parse_day: Any


async def render(session, request, module, view, q, day, now_dt, dependencies):
    api_config_value_rows = dependencies.api_config_value_rows
    api_day_navigation = dependencies.api_day_navigation
    api_energy_circuit_edit = dependencies.api_energy_circuit_edit
    api_energy_load_edit = dependencies.api_energy_load_edit
    api_filter = dependencies.api_filter
    api_filter_int = dependencies.api_filter_int
    api_filter_options = dependencies.api_filter_options
    api_filter_value = dependencies.api_filter_value
    api_pick = dependencies.api_pick
    api_tool_row = dependencies.api_tool_row
    build_energy_circuit_loads_payload = dependencies.build_energy_circuit_loads_payload
    circuit_row_api = dependencies.circuit_row_api
    cumulative_energy_points = dependencies.cumulative_energy_points
    decimate_rows = dependencies.decimate_rows
    energy_elvia_control_module_payload = dependencies.energy_elvia_control_module_payload
    energy_elvia_module_payload = dependencies.energy_elvia_module_payload
    load_row_api = dependencies.load_row_api
    load_sunbed_power_analysis = dependencies.load_sunbed_power_analysis
    parse_day = dependencies.parse_day
    params = request.query_params
    today = now_dt.date()
    tomorrow = today + timedelta(days=1)
    today_start = datetime.combine(today, time.min)
    tomorrow_start = datetime.combine(tomorrow, time.min)
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, time.min)
    previous_month_start = add_months(month_start, -1)
    previous_month_start_dt = datetime.combine(previous_month_start, time.min)
    year_start_dt = datetime.combine(date(today.year, 1, 1), time.min)
    selected_day = parse_day(day)
    selected_day_start = datetime.combine(selected_day, time.min)
    selected_day_end = selected_day_start + timedelta(days=1)
    energy_q_value = api_filter_value(params, "q")
    energy_circuit_value = api_filter_value(params, "circuit")
    energy_load_type_value = api_filter_value(params, "load_type")
    energy_active_value = api_filter_value(params, "active")
    energy_sunbeds_value = normalize_energy_sunbed_filter(api_filter_value(params, "sunbeds"))
    energy_sunbed_date_from = api_filter_value(params, "date_from")
    energy_sunbed_date_to = api_filter_value(params, "date_to")
    energy_limit_value = api_filter_int(params, "limit", 500, 25, 1000)
    if view == "elvia-kontroll":
        return await energy_elvia_control_module_payload(session, selected_day, today)
    if view == "elvia":
        return await energy_elvia_module_payload(session)
    if view == "forbruk-per-seng":
        energy_sunbeds_data = await load_sunbed_power_analysis(
            session,
            energy_sunbed_date_from or None,
            energy_sunbed_date_to or None,
            today,
        )
        sunbed_summary = energy_sunbeds_data["summary"]
        filters = [
            api_filter("date_from", "Fra", "date", energy_sunbeds_data["dateFrom"]),
            api_filter("date_to", "Til", "date", energy_sunbeds_data["dateTo"]),
        ]
        energy_cards = [
            api_card("Senger med estimat", sunbed_summary.get("rooms_count"), "stk", "Rom med rene målepunkter", "sun2", href="/energi/forbruk-per-seng"),
            api_card("Rene målepunkter", sunbed_summary.get("single_samples"), "stk", f"Intervall {format_short_number(sunbed_summary.get('sample_interval_seconds'))} sek", "energy", href="/energi/forbruk-per-seng"),
            api_card("Baseline", format_short_number(sunbed_summary.get("global_baseline_w")), "W", "Median uten aktiv solseng", "energy", href="/energi/forbruk-per-seng"),
            api_card("Takvifte korrigert", sunbed_summary.get("roof_exhaust_adjusted_samples"), "stk", f"-{format_short_number(sunbed_summary.get('roof_exhaust_adjustment_w'))} W ved på", "vent", href="/energi/forbruk-per-seng"),
        ]
        return {
            "title": v2_module_title("energi", "forbruk-per-seng"),
            "subtitle": "Estimert forbruk per solseng beregnet fra realtime differanseforbruk.",
            "cards": energy_cards,
            "charts": [],
            "tables": [],
            "filters": filters,
            "energyElvia": None,
            "energySunbeds": energy_sunbeds_data,
        }
    if view in {"kurs-last", "kurser", "laster", "verktoy"}:
        all_circuits = (
            await session.execute(select(EnergyCircuit).order_by(EnergyCircuit.circuit_no.asc()))
        ).scalars().all()
        circuits = filter_energy_circuits_by_sunbed(all_circuits, energy_sunbeds_value if view == "kurser" else None)
        sunbed_circuit_numbers = [row.circuit_no for row in all_circuits if energy_circuit_is_sunbed(row)]
        sunbed_filter_options = [
            {"label": "Skjul solsenger", "value": "hide"},
            {"label": "Kun solsenger", "value": "only"},
        ]
        circuit_options = [
            {
                "label": f"{row.circuit_no} - {row.description}" if row.description else str(row.circuit_no),
                "value": str(row.circuit_no),
            }
            for row in all_circuits
            if row.circuit_no is not None
        ]

        energy_circuit_no = None
        if energy_circuit_value:
            try:
                energy_circuit_no = int(energy_circuit_value)
            except ValueError:
                energy_circuit_no = None
        load_conditions = []
        if energy_q_value:
            pattern = f"%{energy_q_value}%"
            load_conditions.append(
                or_(
                    EnergyLoad.name.ilike(pattern),
                    EnergyLoad.area.ilike(pattern),
                    EnergyLoad.note.ilike(pattern),
                    EnergyLoad.load_type.ilike(pattern),
                )
            )
        if energy_circuit_no is not None:
            load_conditions.append(EnergyLoad.circuit_no == energy_circuit_no)
        if energy_load_type_value:
            load_conditions.append(EnergyLoad.load_type == energy_load_type_value)
        if energy_active_value == "1":
            load_conditions.append(EnergyLoad.active.is_(True))
        elif energy_active_value == "0":
            load_conditions.append(EnergyLoad.active.is_(False))
        if energy_sunbeds_value == "hide":
            load_conditions.append(or_(EnergyLoad.circuit_no.is_(None), ~EnergyLoad.circuit_no.in_(sunbed_circuit_numbers)))
        elif energy_sunbeds_value == "only":
            load_conditions.append(EnergyLoad.circuit_no.in_(sunbed_circuit_numbers))

        load_stmt = select(EnergyLoad).order_by(EnergyLoad.active.desc(), EnergyLoad.circuit_no.asc(), EnergyLoad.name.asc()).limit(energy_limit_value)
        load_count_stmt = select(func.count(EnergyLoad.id))
        if load_conditions:
            load_stmt = load_stmt.where(*load_conditions)
            load_count_stmt = load_count_stmt.where(*load_conditions)
        loads = (await session.execute(load_stmt)).scalars().all()
        filtered_load_count = (await session.execute(load_count_stmt)).scalar_one()

        if view == "kurs-last":
            hierarchy_loads = (
                await session.execute(
                    select(EnergyLoad).order_by(EnergyLoad.active.desc(), EnergyLoad.circuit_no.asc(), EnergyLoad.name.asc())
                )
            ).scalars().all()
            hierarchy_nodes = (
                await session.execute(
                    select(EnergyNode).order_by(EnergyNode.active.desc(), EnergyNode.circuit_no.asc(), EnergyNode.parent_node_id.asc(), EnergyNode.name.asc())
                )
            ).scalars().all()
            circuit_loads = build_energy_circuit_loads_payload(all_circuits, hierarchy_loads, hierarchy_nodes)
            circuit_loads["canManage"] = bool(getattr(request.state, "auth_can_settings", False))
            circuit_summary = circuit_loads["summary"]
            return {
                "title": "Energi · kurs/last",
                "subtitle": "Hierarki over elektriske kurser, laster og hvordan energimålere dekker dem.",
                "cards": [
                    api_card("Kurser", circuit_summary.get("circuits"), "stk", "Registrert i kursregisteret", "energy", href="/energi/kurs-last"),
                    api_card("Laster", circuit_summary.get("activeLoads"), "aktive", f"{circuit_summary.get('loads')} totalt", "status", href="/energi/laster"),
                    api_card("Kursmålt", circuit_summary.get("circuitMeterCount"), "kurs", "Alle aktive laster på samme måler", "energy", href="/energi/kurs-last"),
                    api_card("Uten måler", circuit_summary.get("unmeteredLoadCount"), "laster", "Mangler egen energimåler", "status", href="/energi/kurs-last"),
                    api_card("Forventet effekt", format_short_number(circuit_summary.get("expectedPowerW")), "W", "Aktive registrerte laster", "energy", href="/energi/kurs-last"),
                ],
                "charts": [],
                "tables": [],
                "filters": [],
                "energyElvia": None,
                "energySunbeds": None,
                "energyCircuitLoads": circuit_loads,
            }

        if view == "kurser":
            return {
                "title": v2_module_title("energi", "kurser"),
                "subtitle": "Kursregister med tekniske data og solsengmerking.",
                "cards": [
                    api_card("Kurser", len(circuits), "stk", "Valgt kursfilter", "energy", href="/energi/kurser"),
                    api_card("Solsengkurser", sum(1 for row in circuits if energy_circuit_is_sunbed(row)), "stk", "Blant viste", "sun2", href="/energi/forbruk-per-seng"),
                    api_card("Med vern", sum(1 for row in circuits if row.breaker_rating_a is not None), "stk", "Registrert", "status", href="/energi/kurser"),
                    api_card("Uten vern", sum(1 for row in circuits if row.breaker_rating_a is None), "stk", "Mangler data", "status", href="/energi/kurser"),
                ],
                "charts": [],
                "tables": [api_table("Kurser", ["circuit_no", "description", "breaker", "breaker_type", "is_sunbed", "status", "note"], [circuit_row_api(row) for row in circuits], edit=api_energy_circuit_edit())],
                "filters": [api_filter("sunbeds", "Solsenger", "select", energy_sunbeds_value, options=sunbed_filter_options)],
                "energyElvia": None,
                "energySunbeds": None,
            }

        load_type_options = api_filter_options(
            (
                await session.execute(
                    select(EnergyLoad.load_type)
                    .where(EnergyLoad.load_type.is_not(None))
                    .where(func.trim(EnergyLoad.load_type) != "")
                    .distinct()
                    .order_by(EnergyLoad.load_type.asc())
                )
            ).scalars().all()
        )
        if view == "laster":
            return {
                "title": "Energi · laster",
                "subtitle": "Lastregister med målere, kurser og forventet effekt.",
                "cards": [
                    api_card("Treff", filtered_load_count, "stk", f"Viser {len(loads)} laster", "energy", href="/energi/laster"),
                    api_card("Aktive vist", sum(1 for row in loads if row.active), "stk", "I tabellen", "status", href="/energi/laster"),
                    api_card("Direktemålt", sum(1 for row in loads if row.measured_direct), "stk", "I tabellen", "energy", href="/energi/laster"),
                    api_card("Effekt vist", format_short_number(sum(float_or_zero(row.expected_power_w) for row in loads)), "W", "For viste rader", "energy", href="/energi/laster"),
                ],
                "charts": [],
                "tables": [api_table("Laster", ["name", "load_type", "area", "circuit_no", "power_profile", "expected_power_w", "fibaro_device_id", "fibaro_meter_id", "active"], [load_row_api(row) for row in loads], edit=api_energy_load_edit())],
                "filters": [
                    api_filter("q", "Søk", "text", energy_q_value, "Navn, område, type eller notat"),
                    api_filter("circuit", "Kurs", "select", energy_circuit_value, options=circuit_options),
                    api_filter("load_type", "Type", "select", energy_load_type_value, options=load_type_options),
                    api_filter("active", "Aktiv", "select", energy_active_value, options=[{"label": "Aktive", "value": "1"}, {"label": "Inaktive", "value": "0"}]),
                    api_filter("sunbeds", "Solsenger", "select", energy_sunbeds_value, options=sunbed_filter_options),
                    api_filter("limit", "Antall", "number", energy_limit_value),
                ],
                "energyElvia": None,
                "energySunbeds": None,
            }

        latest = (
            await session.execute(select(EnergyFibaroSample).order_by(EnergyFibaroSample.bucket_start.desc()).limit(1))
        ).scalars().first()
        today_sample_count = (
            await session.execute(
                select(func.count(EnergyFibaroSample.id))
                .where(EnergyFibaroSample.bucket_start >= today_start)
                .where(EnergyFibaroSample.bucket_start < tomorrow_start)
            )
        ).scalar_one()
        elvia_import_count = (
            await session.execute(select(func.count(EnergyImportRun.id)))
        ).scalar_one()
        return {
            "title": "Energi · verktøy",
            "subtitle": "Snarveier og teknisk datagrunnlag for energi.",
            "cards": [
                api_card("Inntak nå", format_short_number(latest.inntak_w if latest else None), "W", "Realtime", "energy", href="/energi/status"),
                api_card("Samples i dag", today_sample_count, "stk", "Realtime energilogging", "energy", href="/energi/status"),
                api_card("Diff nå", format_short_number(latest.differanse_beregnet_w if latest else None), "W", "Beregnet fra realtime", "energy", href="/energi/status"),
                api_card("Laster", filtered_load_count, "stk", "Aktive og registrerte", "status", href="/energi/laster"),
            ],
            "charts": [],
            "tables": [
                api_table(
                    "Energiverktøy",
                    ["tool", "path", "description", "count"],
                    [
                        api_tool_row("Energi status", "/energi/status", "Realtime energiside med Elvia-sammenligning.", today_sample_count),
                        api_tool_row("Kurser", "/energi/kurser", "Kursregister med redigering og tekniske data.", len(circuits)),
                        api_tool_row("Laster", "/energi/laster", "Lastregister med målere, kurser og forventet effekt.", len(loads)),
                        api_tool_row("Elvia", "/energi/elvia", "Import og kontroll av Elvia-timesdata.", elvia_import_count),
                        api_tool_row("Kurs-PDF", "/classic/energi/kurser/pdf", "Eksporter kurslisten som PDF.", len(circuits)),
                        api_tool_row("Last-PDF", "/classic/energi/laster/pdf", "Eksporter lastlisten som PDF.", len(loads)),
                    ],
                ),
                api_table(
                    "Datagrunnlag",
                    ["key", "value"],
                    api_config_value_rows(
                        {
                            "samples_i_dag": today_sample_count,
                            "siste_sample": latest.bucket_start if latest else None,
                            "inntak_na_w": latest.inntak_w if latest else None,
                            "differanse_na_w": latest.differanse_beregnet_w if latest else None,
                            "aktive_laster": sum(1 for row in loads if row.active),
                            "direktemalte_laster": sum(1 for row in loads if row.measured_direct),
                        }
                    ),
                ),
            ],
            "filters": [],
            "energyElvia": None,
            "energySunbeds": None,
        }
    latest = (
        await session.execute(select(EnergyFibaroSample).order_by(EnergyFibaroSample.bucket_start.desc()).limit(1))
    ).scalars().first()
    selected_energy_rows = (
        await session.execute(
            select(EnergyFibaroSample)
            .where(EnergyFibaroSample.bucket_start >= selected_day_start)
            .where(EnergyFibaroSample.bucket_start < selected_day_end)
            .order_by(EnergyFibaroSample.bucket_start.desc())
        )
    ).scalars().all()
    registered_load_count = (
        await session.execute(select(func.count(EnergyLoad.id)))
    ).scalar_one()
    total_kwh = sum(float_or_zero(row.inntak_delta_kwh) for row in selected_energy_rows)
    chronological_energy_rows = list(reversed(selected_energy_rows))
    # 720 points cover a full day at two-minute visual resolution and keep the
    # multi-series response compact enough for quick tablet navigation.
    energy_chart_rows = decimate_rows(chronological_energy_rows, 720)
    energy_chart_items = [
        ("inntak", "Inntak", "#15803d"),
        ("varmepumper", "Varmepumper", "#0891b2"),
        ("belysning", "Belysning", "#ca8a04"),
        ("massasje", "Massasje", "#f59e0b"),
        ("annet", "Annet", "#64748b"),
        ("avfukter", "Avfukter", "#14b8a6"),
    ]
    power_series = [
        {
            "name": label,
            "data": [
                [api_local_iso(row.bucket_start), getattr(row, f"{key}_w", None)]
                for row in energy_chart_rows
                if row.bucket_start
            ],
            "color": color,
        }
        for key, label, color in energy_chart_items
    ]
    consumption_series = [
        {
            "name": label,
            "data": decimate_rows(
                cumulative_energy_points(chronological_energy_rows, f"{key}_delta_kwh"),
                720,
            ),
            "color": color,
            "smooth": False,
        }
        for key, label, color in energy_chart_items
    ]
    charts = [
        api_chart(
            "Energi status",
            [],
            power_series,
            f"{selected_day.strftime('%d.%m.%Y')} vises som helt døgn. Velg realtime effekt eller akkumulert forbruk.",
            "line",
            360,
            metrics=[
                {"key": "power", "label": "Effekt", "unit": "W", "series": power_series},
                {"key": "consumption", "label": "Forbruk", "unit": "kWh", "series": consumption_series},
            ],
            default_metric="power",
            x_axis_type="time",
            x_axis_min=api_local_iso(selected_day_start),
            x_axis_max=api_local_iso(selected_day_end),
            disable_zoom=True,
            day_navigation=api_day_navigation(selected_day, today),
        )
    ]
    energy_table_columns = [
        "bucket_start", "inntak_w", "varmepumper_w", "belysning_w",
        "massasje_w", "annet_w", "avfukter_w", "differanse_beregnet_w",
    ]
    tables = [
        api_table(
            "Energisamples valgt dag",
            energy_table_columns,
            [api_pick(row, energy_table_columns) for row in selected_energy_rows[:500]],
        ),
    ]
    filters = []
    energy_cards = [
        api_card("Inntak nå", format_short_number(latest.inntak_w if latest else None), "W", "Realtime", "energy", href="/energi/status"),
        api_card("Forbruk i dag" if selected_day == today else "Forbruk valgt dag", format_short_number(total_kwh, 1), "kWh", f"{len(selected_energy_rows)} samples", "energy", href="/energi/status"),
        api_card("Diff nå", format_short_number(latest.differanse_beregnet_w if latest else None), "W", "Beregnet fra realtime", "energy", href="/energi/status"),
        api_card("Laster", registered_load_count, "stk", "Registrert i lastregisteret", "status", href="/energi/laster"),
    ]
    return {
        "title": v2_module_title("energi", view),
        "subtitle": "Realtime HC3-måling, kursregister og lastregister.",
        "cards": energy_cards,
        "charts": charts,
        "tables": tables,
        "filters": filters,
        "energyElvia": None,
        "energySunbeds": None,
    }

