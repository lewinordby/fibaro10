"""System module response assembly, independent of HTTP registration."""

from build_log import APP_BUILD, BUILD_LOG, api_build_log_row
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from fibaro_core.models import AccessKey, AccessLog, AiQueryLog
from fibaro_core.services.presentation import api_card, api_table, format_short_number
from fibaro_core.services.summaries.periods import add_months
from sqlalchemy import select
from system_inventory import system_component_rows, system_component_summary, system_web_interface_rows
from typing import Any
from v2_navigation import v2_module_title


@dataclass
class Dependencies:
    ai_dataset_overview: Any
    api_access_key_edit: Any
    api_access_key_row: Any
    api_admin_manual_payload: Any
    api_config_value_rows: Any
    api_import_status_rows: Any
    api_pick: Any
    api_tool_row: Any
    build_admin_data_quality: Any
    build_admin_relation_analysis: Any
    build_admin_task_rows: Any
    build_reconciliation_control: Any
    effective_openai_settings: Any
    import_status_rows: Any
    row_to_dict: Any


async def render(session, request, module, view, q, day, now_dt, dependencies):
    ai_dataset_overview = dependencies.ai_dataset_overview
    api_access_key_edit = dependencies.api_access_key_edit
    api_access_key_row = dependencies.api_access_key_row
    api_admin_manual_payload = dependencies.api_admin_manual_payload
    api_config_value_rows = dependencies.api_config_value_rows
    api_import_status_rows = dependencies.api_import_status_rows
    api_pick = dependencies.api_pick
    api_tool_row = dependencies.api_tool_row
    build_admin_data_quality = dependencies.build_admin_data_quality
    build_admin_relation_analysis = dependencies.build_admin_relation_analysis
    build_admin_task_rows = dependencies.build_admin_task_rows
    build_reconciliation_control = dependencies.build_reconciliation_control
    effective_openai_settings = dependencies.effective_openai_settings
    import_status_rows = dependencies.import_status_rows
    row_to_dict = dependencies.row_to_dict
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
    import_rows = []
    import_api_rows = []
    admin_task_rows = []
    ai_logs = []
    access_keys = []
    access_logs = []
    import_views = {"", "drift", "oppgaver", "datakvalitet", "datakilder", "teknisk", "manual"}
    if view in import_views:
        import_rows = await import_status_rows(session)
        import_api_rows = api_import_status_rows(import_rows)
    if view in {"", "drift", "oppgaver"}:
        admin_task_rows = await build_admin_task_rows(session, import_rows, now_dt)
    if view == "ai":
        ai_logs = (
            await session.execute(
                select(AiQueryLog)
                .order_by(AiQueryLog.timestamp.desc())
                .limit(80)
            )
        ).scalars().all()
    if view in {"brukere", "manual", "verktoy"}:
        access_keys = (
            await session.execute(
                select(AccessKey)
                .order_by(AccessKey.created_at.desc())
                .limit(200)
            )
        ).scalars().all()
    if view == "brukere":
        access_logs = (
            await session.execute(
                select(AccessLog)
                .order_by(AccessLog.timestamp.desc())
                .limit(120)
            )
        ).scalars().all()

    admin_tools = [
        api_tool_row("Buildlogg", "/admin/build", "Klikkbar leveransehistorikk med detaljvisning per build.", len(BUILD_LOG)),
        api_tool_row("Teknisk", "/admin/teknisk", "Teknisk driftsside.", None),
        api_tool_row("Manual", "/manual/oversikt", "Intern manual og driftsnotater.", None),
        api_tool_row("Brukere og tilgang", "/admin/brukere", "Administrer brukere, roller og tilgang.", len(access_keys) if access_keys else None),
        api_tool_row("AI-innstillinger", "/admin/ai", "Sett modell og API-nøkkel for analyseassistent.", len(ai_logs) if ai_logs else None),
        api_tool_row("Health", "/health", "Rask serverhelse og lagringsliste.", None),
        api_tool_row("Events JSON", "/events/json", "Generiske hendelser som JSON.", None),
        api_tool_row("Events CSV", "/download", "Generiske hendelser som CSV.", None),
    ]
    build_log_columns = ["date", "build", "headline"]
    urgent_task_count = sum(
        1 for row in admin_task_rows if row["severity"] in {"Kritisk", "Høy"}
    )
    problem_import_rows = [
        row for row in import_api_rows if row.get("status") != "ok"
    ]
    ok_import_count = len(import_api_rows) - len(problem_import_rows)
    actions = []
    charts = []
    reconciliation = None
    admin_cards = []
    tables = []
    if view in {"", "drift"}:
        admin_cards = [
            api_card("Datakilder", f"{ok_import_count}/{len(import_api_rows)}", "OK", "Alle ferske" if not problem_import_rows else f"{len(problem_import_rows)} krever kontroll", "danger" if problem_import_rows else "status", href="/admin/datakilder"),
            api_card("Krever oppfølging", len(admin_task_rows), "stk", "Samlet arbeidsliste", "danger" if urgent_task_count else "status", href="/admin/oppgaver"),
            api_card("Kritisk / høy", urgent_task_count, "stk", "Prioriteres først", "danger" if urgent_task_count else "status", href="/admin/oppgaver"),
            api_card("Siste build", APP_BUILD, "", BUILD_LOG[0]["title"], "status", href="/admin/build"),
        ]
        if problem_import_rows:
            tables.append(
                api_table(
                    "Datakilder som krever oppmerksomhet",
                    ["source_no", "title", "category", "status", "age", "message"],
                    problem_import_rows,
                )
            )
        tables.append(
            api_table(
                "Siste endringer",
                build_log_columns,
                [api_build_log_row(row) for row in BUILD_LOG[:8]],
            )
        )

    if view == "oppgaver":
        actions = [
            {
                "key": "easypark-refresh",
                "label": "Oppdater EasyPark",
                "method": "POST",
                "path": "/api/actions/parkering/refresh",
                "confirm": "Starte EasyPark-import for siste periode og oppdatere parkeringsgrunnlaget?",
                "tone": "primary",
            },
            {
                "key": "svv-sync",
                "label": "Kjør SVV-sync",
                "method": "POST",
                "path": "/api/actions/parkering/svv-sync",
                "confirm": "Starte nytt oppslag mot Statens vegvesen for kjøretøy som mangler data?",
                "tone": "default",
            },
            {
                "key": "link-sun-images",
                "label": "Koble solbilder",
                "method": "POST",
                "path": "/api/actions/soling/link-snapshot-images?days=14",
                "confirm": "Koble Axis-bilder mot soltimer siste 14 dager?",
                "tone": "default",
            },
            {
                "key": "clear-area-not-found",
                "label": "Fjern område ikke funnet",
                "method": "POST",
                "path": "/api/actions/parkering/clear-area-not-found",
                "confirm": "Nullstille område 'ikke funnet' slik at disse kan behandles på nytt?",
                "tone": "default",
            },
        ]
        admin_cards = [
            api_card("Åpne oppgaver", len(admin_task_rows), "stk", f"{urgent_task_count} kritisk/høy", "status", href="/admin/oppgaver"),
            api_card("Datakilder", sum(1 for row in admin_task_rows if row["domain"] == "Datakilde"), "stk", "Treg eller feil", "status", href="/admin/datakilder"),
            api_card("Parkering", sum(1 for row in admin_task_rows if row["domain"] == "Parkering"), "stk", "Navn, område og oppslag", "parking", href="/parkering/oppslag"),
            api_card("Sist kontrollert", now_dt.strftime("%H:%M"), "", now_dt.strftime("%d.%m.%Y"), "status", href="/admin/oppgaver"),
        ]
        tables = [
            api_table(
                "Oppgaver og avvik",
                ["severity", "domain", "item", "problem", "detail", "count", "recommended_action", "path"],
                admin_task_rows,
            ),
            api_table(
                "Kontrollgrunnlag",
                ["key", "value"],
                api_config_value_rows(
                    {
                        "datakilder_totalt": len(import_rows),
                        "datakilder_ikke_ok": sum(1 for row in import_rows if row["status"] != "ok"),
                        "oppgaver_kritisk_hoy": urgent_task_count,
                        "oppgaver_totalt": len(admin_task_rows),
                    }
                ),
            ),
        ]
    elif view == "kontroll":
        reconciliation = await build_reconciliation_control(session, now_dt)
        reconciliation_summary_row = reconciliation["summary"]
        reconciliation_checks = [
            check
            for group in reconciliation["groups"]
            for check in group["checks"]
        ]
        admin_cards = [
            api_card(
                "Samlet status",
                reconciliation_summary_row["overall_label"],
                "",
                f"{reconciliation_summary_row['total']} kontroller vurdert",
                "status",
                href="/admin/kontroll",
            ),
            api_card(
                "Stemmer",
                reconciliation_summary_row["ok"],
                "stk",
                "Innenfor definert toleranse",
                "status",
                href="/admin/kontroll",
            ),
            api_card(
                "Avvik",
                reconciliation_summary_row["critical"],
                "stk",
                "Krever kontroll",
                "revenue" if reconciliation_summary_row["critical"] else "status",
                href="/admin/kontroll",
            ),
            api_card(
                "Mangler grunnlag",
                reconciliation_summary_row["missing"],
                "stk",
                "Bilag eller systemdata mangler",
                "status",
                href="/admin/kontroll",
            ),
        ]
        tables = [
            api_table(
                "Avstemminger",
                [
                    "status_label",
                    "domain",
                    "title",
                    "period",
                    "actual_label",
                    "actual_value",
                    "reference_label",
                    "reference_value",
                    "difference",
                    "difference_percent",
                    "unit",
                    "detail",
                    "path",
                ],
                reconciliation_checks,
            ),
            api_table(
                "Kontrollregler",
                ["key", "value"],
                api_config_value_rows(
                    {
                        "oppgjor_toleranse": "1 kr eks. mva",
                        "energi_toleranse": "maks 1 kWh eller 2 %",
                        "energi_kritisk": "over 3 ganger toleransen",
                        "dorkontroll": "ingen aktive alarmer",
                        "koblingsjobb": "aktiv worker sett siste 3 min",
                        "generert": reconciliation["generated_at"],
                    }
                ),
            ),
        ]
    elif view == "datakvalitet":
        data_quality = await build_admin_data_quality(session, import_rows, now_dt)
        actions = [
            {
                "key": "easypark-refresh",
                "label": "Oppdater EasyPark",
                "method": "POST",
                "path": "/api/actions/parkering/refresh",
                "confirm": "Starte EasyPark-import for siste periode?",
                "tone": "primary",
            },
            {
                "key": "svv-sync",
                "label": "Kjør SVV-sync",
                "method": "POST",
                "path": "/api/actions/parkering/svv-sync",
                "confirm": "Starte nytt oppslag mot Statens vegvesen?",
                "tone": "default",
            },
            {
                "key": "link-sun-images",
                "label": "Koble solbilder",
                "method": "POST",
                "path": "/api/actions/soling/link-snapshot-images?days=14",
                "confirm": "Koble Axis-bilder mot soltimer siste 14 dager?",
                "tone": "default",
            },
        ]
        admin_cards = [
            api_card("Datakvalitet", format_short_number(data_quality["score"]), "%", "Vektet score for sentrale datakilder", "status", href="/admin/datakvalitet"),
            api_card("OK", data_quality["ok_count"], "stk", "Målepunkter innenfor mål", "status", href="/admin/datakvalitet"),
            api_card("Varsel", data_quality["warn_count"], "stk", "Bør følges opp", "status", href="/admin/datakvalitet"),
            api_card("Feil", data_quality["bad_count"], "stk", "Krever tiltak", "status", href="/admin/oppgaver"),
        ]
        tables = [
            api_table(
                "Datakvalitet",
                ["domain", "metric", "status", "value", "target", "coverage_percent", "missing_count", "sample_count", "detail", "recommended_action", "path"],
                data_quality["rows"],
            ),
            api_table(
                "Avvik fra mål",
                ["domain", "metric", "status", "value", "target", "missing_count", "detail", "recommended_action", "path"],
                data_quality["issue_rows"],
            ),
        ]
    elif view == "analyse":
        relation_analysis = await build_admin_relation_analysis(session, now_dt)
        strongest_sun = relation_analysis["strongest_sun"]
        strongest_parking = relation_analysis["strongest_parking"]
        strongest_revenue = relation_analysis["strongest_revenue"]
        admin_cards = [
            api_card(
                "Analyserte dager",
                relation_analysis["analysed_days"],
                "stk",
                f"{relation_analysis['start_day'].strftime('%d.%m')} - {relation_analysis['end_day'].strftime('%d.%m')}",
                "status",
                href="/admin/analyse",
            ),
            api_card(
                "Soling",
                strongest_sun["factor"] if strongest_sun else "-",
                "",
                f"r={strongest_sun['correlation']} · {strongest_sun['direction']}" if strongest_sun else "For lite data",
                "sun2",
                href="/soling/oversikt",
            ),
            api_card(
                "Parkering",
                strongest_parking["factor"] if strongest_parking else "-",
                "",
                f"r={strongest_parking['correlation']} · {strongest_parking['direction']}" if strongest_parking else "For lite data",
                "parking",
                href="/parkering/sammenligning",
            ),
            api_card(
                "Omsetning",
                strongest_revenue["factor"] if strongest_revenue else "-",
                "",
                f"r={strongest_revenue['correlation']} · {strongest_revenue['direction']}" if strongest_revenue else "For lite data",
                "revenue",
                href="/omsetning/oversikt",
            ),
        ]
        tables = [
            api_table(
                "Sammenhenger",
                ["target", "factor", "correlation", "strength", "direction", "sample_days", "detail"],
                relation_analysis["correlation_rows"],
            ),
            api_table(
                "Dagsgrunnlag",
                [
                    "day",
                    "weekday",
                    "sun_count",
                    "sun_paid",
                    "parking_count",
                    "parking_paid",
                    "total_paid",
                    "air_temperature",
                    "relative_humidity",
                    "wind_speed",
                    "cloud_area_fraction",
                    "avg_inntak_w",
                    "avg_diff_w",
                    "weather_samples",
                    "energy_samples",
                ],
                relation_analysis["day_rows"],
            ),
        ]
        charts = [relation_analysis["chart"]]
    elif view == "build":
        current_build_row = BUILD_LOG[0]
        builds_today = sum(1 for row in BUILD_LOG if row.get("date") == current_build_row.get("date"))
        admin_cards = [
            api_card("Aktiv build", APP_BUILD, "", current_build_row.get("headline"), "status", href="/admin/build"),
            api_card("Loggførte builds", len(BUILD_LOG), "stk", "Komplett leveransehistorikk", "status", href="/admin/build"),
            api_card("I dag", builds_today, "stk", current_build_row.get("date"), "status", href="/admin/build"),
            api_card("Berørte apper", len(current_build_row.get("applications") or []), "stk", "I aktiv build", "status", href="/admin/build"),
        ]
        tables = [
            api_table(
                "Buildlogg",
                build_log_columns,
                [api_build_log_row(row) for row in BUILD_LOG[:80]],
                meta={"rowLinkColumns": ["date", "build", "headline"]},
            ),
            api_table("Buildverktøy", ["tool", "path", "description", "count"], [admin_tools[0], admin_tools[1], admin_tools[5]]),
        ]
    elif view == "datakilder":
        admin_cards = [
            api_card("Datakilder", len(import_api_rows), "stk", "Registrert i systemet", "status", href="/admin/datakilder"),
            api_card("OK", ok_import_count, "stk", "Ferske og vellykkede", "status", href="/admin/datakilder"),
            api_card("Krever kontroll", len(problem_import_rows), "stk", "Feil eller utdaterte", "danger" if problem_import_rows else "status", href="/admin/datakilder"),
            api_card("Områder", len({str(row.get('category') or '') for row in import_api_rows}), "stk", "Fagområder med datakilder", "status", href="/admin/datakilder"),
        ]
        tables = [
            api_table("Datakilder", ["source_no", "title", "category", "status", "status_text", "age", "last_success_at", "message"], import_api_rows),
            api_table(
                "Dataverktøy",
                ["tool", "path", "description", "count"],
                [
                    api_tool_row("Health", "/health", "Serverhelse og lagringstabeller.", len(import_rows)),
                    api_tool_row("Yr CSV", "/yr/samples/download", "Last ned Yr-samples.", None),
                    api_tool_row("Lys CSV", "/lights/samples/download", "Last ned lys-samples.", None),
                    api_tool_row("Ventilasjon CSV", "/ventilation/samples/download", "Last ned ventilasjonssamples.", None),
                ],
            ),
        ]
    elif view == "systemkart":
        inventory = system_component_summary()
        admin_cards = [
            api_card("Komponenter", inventory["components"], "stk", "Apper, tjenester og verktøy i løsningen", "status", href="/admin/systemkart"),
            api_card("Aktive", inventory["active"], "stk", "Kjører eller brukes i daglig drift", "status", href="/admin/systemkart"),
            api_card("Kritiske", inventory["critical"], "stk", "Påvirker drift eller datagrunnlag direkte", "status", href="/admin/systemkart"),
            api_card("Webflater", inventory["web_interfaces"], "stk", "Underapper med klikkbart webgrensesnitt", "status", href="/admin/systemkart"),
        ]
        tables = [
            api_table(
                "Underapper med webgrensesnitt",
                ["component", "area", "interface", "web_url", "local_url", "health_url", "status"],
                system_web_interface_rows(),
            ),
            api_table(
                "Systemkomponenter",
                ["component", "area", "role", "runtime", "compose_service", "interface", "web_url", "local_url", "health_url", "health", "status", "criticality"],
                system_component_rows(),
            ),
            api_table("Områder", ["area", "count"], inventory["area_rows"]),
            api_table("Status", ["status", "count"], inventory["status_rows"]),
        ]
    elif view == "ai":
        ai_settings = await effective_openai_settings()
        successful_ai_logs = sum(1 for row in ai_logs if row.ok)
        admin_cards = [
            api_card("Modell", ai_settings["model"], "", "Aktiv modell", "status", href="/admin/ai"),
            api_card("API-nøkkel", "Ja" if ai_settings["has_env_key"] or ai_settings["has_stored_key"] else "Nei", "", ai_settings["source"], "status", href="/admin/ai"),
            api_card("Spørringer", len(ai_logs), "stk", "I siste loggutvalg", "status", href="/admin/ai"),
            api_card("Vellykket", successful_ai_logs, "stk", f"{len(ai_logs) - successful_ai_logs} feilet", "status", href="/admin/ai"),
        ]
        tables = [
            api_table(
                "AI-status",
                ["key", "value"],
                api_config_value_rows(
                    {
                        "modell": ai_settings["model"],
                        "nokkelkilde": ai_settings["source"],
                        "miljovariabel": ai_settings["has_env_key"],
                        "lagret_nokkel": ai_settings["has_stored_key"],
                    }
                ),
            ),
            api_table("Datasett", ["key", "table", "title", "time_column", "columns_count"], ai_dataset_overview()),
            api_table(
                "AI-logg",
                ["timestamp", "username", "question", "ok", "error"],
                [api_pick(row, ["timestamp", "username", "question", "ok", "error"]) for row in ai_logs],
            ),
            api_table("AI-verktøy", ["tool", "path", "description", "count"], [admin_tools[4], api_tool_row("Datasett JSON", "/api/ai/datasets/json", "AI-godkjente datasett.", len(ai_dataset_overview())), api_tool_row("AI-logg JSON", "/api/ai/logs/json", "Siste AI-spørringer som JSON.", len(ai_logs))]),
        ]
    elif view == "teknisk":
        tables = [
            api_table("Tekniske verktøy", ["tool", "path", "description", "count"], admin_tools),
            api_table("Datakilder", ["source_no", "title", "category", "status", "status_text", "age", "last_success_at", "message"], import_api_rows),
        ]
    elif view == "brukere":
        active_user_count = sum(1 for row in access_keys if row.active)
        master_user_count = sum(1 for row in access_keys if row.is_master)
        admin_cards = [
            api_card("Brukere", len(access_keys), "stk", f"{active_user_count} aktive", "status", href="/admin/brukere"),
            api_card("Vanlige brukere", max(0, len(access_keys) - master_user_count), "stk", "Kan administreres her", "status", href="/admin/brukere"),
            api_card("Master", master_user_count, "stk", "Passord kan settes på nytt av master", "status", href="/admin/brukere"),
            api_card("Tilgangslogg", len(access_logs), "rader", "Siste innlogginger og API-kall", "status", href="/admin/brukere"),
        ]
        tables = [
            api_table("Brukere", ["name", "role", "active", "is_master", "key_prefix", "password_status", "created_at", "last_seen_at", "uses_count"], [api_access_key_row(row) for row in access_keys], edit=api_access_key_edit()),
            api_table("Siste tilgangslogg", ["timestamp", "key_name", "path", "method", "success", "reason"], [row_to_dict(row, ["timestamp", "key_name", "path", "method", "success", "reason"]) for row in access_logs]),
            api_table(
                "Brukerverktøy",
                ["tool", "path", "description", "count"],
                [
                    api_tool_row("Ny bruker", "/admin/brukere", "Bruk Ny-knappen over brukertabellen.", len(access_keys)),
                    api_tool_row("Tilgangslogg", "/admin/brukere", "Se siste autentiseringer og avviste kall i tabellen.", len(access_logs)),
                ],
            ),
        ]
    elif view == "manual":
        inventory = system_component_summary()
        admin_cards = [
            api_card("Manual", "Aktiv", "", "Lenker og driftsinnganger samlet", "status", href="/manual/oversikt"),
            api_card("Systemkart", inventory["components"], "stk", "Komponenter og underapper", "status", href="/admin/systemkart"),
            api_card("Datakilder", len(import_rows), "stk", "Status og forklaring per kilde", "status", href="/admin/datakilder"),
            api_card("Build", APP_BUILD, "", BUILD_LOG[0]["title"], "status", href="/admin/build"),
        ]
        tables = [
            api_table(
                "Manual og drift",
                ["tool", "path", "description", "count"],
                [
                    api_tool_row("Manual", "/manual/oversikt", "Intern manual med driftsrutiner og lenker til dagens flater.", None),
                    api_tool_row("Systemkart", "/admin/systemkart", "Oversikt over komponenter, underapper, webflater og health-lenker.", len(system_component_rows())),
                    api_tool_row("Datakilder", "/admin/datakilder", "Status for importjobber og eksterne datakilder.", len(import_rows)),
                    api_tool_row("Buildlogg", "/admin/build", "Endringshistorikk for løsningen.", len(BUILD_LOG)),
                    api_tool_row("Teknisk", "/admin/teknisk", "Teknisk driftsflate.", None),
                    api_tool_row("Brukere", "/admin/brukere", "Brukere, roller og tilgangslogg.", len(access_keys)),
                ],
            ),
            api_table(
                "Daglige arbeidsflater",
                ["tool", "path", "description", "count"],
                [
                    api_tool_row("Dashboard", "/status/omsetning", "Hoveddashboard for omsetning, parkering og soling.", None),
                    api_tool_row("Omsetning", "/omsetning/oversikt", "Årsoversikt, toppdager og oppgjørskontroll.", None),
                    api_tool_row("Parkering", "/parkering/oversikt", "Ukesstatistikk, hovedtall og importkontroll.", None),
                    api_tool_row("Soling", "/soling/oversikt", "Soling, enkelttimer, produkter og bildegrunnlag.", None),
                    api_tool_row("Energi", "/energi/status", "Realtime energi, kurs, laster og Elvia-kontroll.", None),
                    api_tool_row("Ventilasjon", "/ventilasjon/dagslogg", "Temperatur, fukt, vifter og hendelser.", None),
                    api_tool_row("Vedlikehold", "/vedlikehold/besok", "Besøk og tilknyttede vedlikeholdsoppgaver.", None),
                    api_tool_row("Koble", "/koble/oversikt", "Koblingsmotor for parkering mot SUN2.", None),
                ],
            ),
            api_table(
                "Underapper med webgrensesnitt",
                ["component", "area", "interface", "web_url", "local_url", "health_url", "status"],
                system_web_interface_rows(),
            ),
        ]
        admin_cards, tables = api_admin_manual_payload(import_rows, access_keys)
    elif view == "verktoy":
        tables = [api_table("Adminverktøy", ["tool", "path", "description", "count"], admin_tools)]
    return {
        "title": v2_module_title("admin", view),
        "subtitle": "Build, datakilder, teknisk drift og AI-logg.",
        "cards": admin_cards,
        "charts": charts,
        "tables": tables,
        "actions": actions,
        "reconciliation": reconciliation,
    }

