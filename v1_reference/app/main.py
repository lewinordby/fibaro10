import html
import os
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse


APP_BUILD = os.getenv("APP_BUILD", "v1-reference")
SOURCE_COMMIT = os.getenv("V1_SOURCE_COMMIT", "487044d")
PORT = os.getenv("V1_REFERENCE_PORT", "8111")


@dataclass(frozen=True)
class V1Page:
    section: str
    path: str
    title: str
    purpose: str


def p(section: str, path: str, title: str, purpose: str) -> V1Page:
    return V1Page(section, path, title, purpose)


PAGES: tuple[V1Page, ...] = (
    p("Status", "/status/dashboard", "Dashboard", "Samlet status, drift akkurat naa, siste hendelser og datakilder."),
    p("Status", "/status/nokkeltall", "Nokkeltall", "Korte tallkort for dag, uke og maaned."),
    p("Status", "/status/omsetning", "Omsetning", "Omsetning fordelt paa soling og parkering."),
    p("Status", "/status/dagslinje", "Dagslinje", "Aktivitet gjennom dagen paa tvers av drift."),
    p("Status", "/status/statistikk", "Statistikk", "Topplister og utvikling over tid."),
    p("Status", "/status/datakilder", "Datakilder", "Importjobber, alder og siste vellykkede oppdatering."),
    p("Parkering", "/parkering/oversikt", "Oversikt", "Dagens parkeringer, oppdatering, kort og siste biler."),
    p("Parkering", "/parkering/prognose", "Prognose", "Tempo, historikk og forventet parkeringsomsetning."),
    p("Parkering", "/parkering/parkeringer", "Parkeringer", "Tabell for enkeltparkeringer med status og bilinfo."),
    p("Parkering", "/parkering/statistikk", "Statistikk", "Aggregert parkeringshistorikk og topplister."),
    p("Parkering", "/parkering/bilstatistikk", "Bilstatistikk", "Merke, type, omraade og frekvens."),
    p("Parkering", "/parkering/omrade", "Omraade", "Fordeling av parkerte biler etter omraade."),
    p("Parkering", "/parkering/omrade-oppslag", "Oppslag", "Arbeidsliste for biler som maa sjekkes manuelt."),
    p("Parkering", "/parkering/kjoretoy", "Kjoretoy", "Sok, eierdata og parkeringshistorikk per bil."),
    p("Soling", "/soling/dagslinje", "Dagslinje", "Soltimer tegnet som romspor gjennom dagen."),
    p("Soling", "/soling/prognose", "Prognose", "Forventet solomsetning basert paa tempo og historikk."),
    p("Soling", "/soling/oversikt", "Statistikk", "Rombruk, omsetning, antall og utvikling."),
    p("Soling", "/soling/detaljer", "Detaljer", "Detaljerte tall for rom og perioder."),
    p("Soling", "/soling/enkeltimer", "Enkeltimer", "Liste over solinger, bilder, rom, bruker og betaling."),
    p("Soling", "/soling/senger", "Senger", "Mapping mellom Sun2-seng og fysisk rom."),
    p("Soling", "/soling/medlemmer", "Medlemmer", "Medlemsliste og kundedata fra Sun2."),
    p("Lys", "/lys/dagslogg-lux", "Dagslogg", "Lux og lysstatus gjennom valgt dag."),
    p("Lys", "/lys/hendelser", "Hendelser", "Av/paa-hendelser fra lysstyring."),
    p("Lys", "/lys/lux-logging", "Malinger", "Raa lux-malinger og kilder."),
    p("Lys", "/lys/innstillinger", "Innstillinger", "Terskler og styringsregler for lys."),
    p("Ventilasjon", "/ventilasjon/dagslogg-temp", "Dagslogg", "Temperatur, fukt og viftestatus gjennom dagen."),
    p("Ventilasjon", "/ventilasjon/hendelser", "Hendelser", "Raa ventilasjons- og avfukterhendelser."),
    p("Ventilasjon", "/ventilasjon/temp-logg", "Temp logg", "Historisk temperatur og fukt."),
    p("Ventilasjon", "/ventilasjon/yr-logg", "Yr logg", "Yr-data brukt i drift og analyse."),
    p("Ventilasjon", "/ventilasjon/innstillinger", "Innstillinger", "Regler og grenser for ventilasjon."),
    p("Energi", "/energi/status", "Status", "Realtime effekt, kWh, grafer og Elvia-avstemming."),
    p("Energi", "/energi/kurser", "Kurser", "Register over kurser, maalere og grupper."),
    p("Energi", "/energi/laster", "Laster", "Register over laster og estimert effekt."),
    p("Energi", "/energi/forbruk-per-seng", "Forbruk/seng", "Beregning av solsengenes stromforbruk."),
    p("Energi", "/energi/elvia", "Elvia", "Opplasting og kontroll av Elvia-filer."),
    p("Renhold", "/renhold/oversikt", "Oversikt", "Roborock-status, jobber og historikk."),
    p("AI", "/ai/sok", "Sok", "Tidlig AI-sok mot valgte datasett."),
    p("AI", "/ai/innstillinger", "Innstillinger", "Datasett og AI-konfigurasjon."),
    p("Konto", "/konto/oversikt", "Oversikt", "Konto, snarveier og teknisk drift."),
    p("Konto", "/konto/build", "Build", "Buildlogg og endringshistorikk."),
    p("Konto", "/konto/teknisk", "Teknisk", "Arkitektur, containere og datakilder."),
    p("Konto", "/konto/manual", "Manual", "Brukermanual for V1-funksjonalitet."),
    p("Konto", "/konto/brukere-og-tilgang", "Brukere", "Brukere, roller og tilgangsnokler."),
)

ALIASES = {
    "/": "/status/dashboard",
    "/parkering": "/parkering/oversikt",
    "/soling": "/soling/dagslinje",
    "/energi": "/energi/status",
    "/lys": "/lys/dagslogg-lux",
    "/ventilasjon": "/ventilasjon/dagslogg-temp",
    "/renhold": "/renhold/oversikt",
    "/ai": "/ai/sok",
    "/konto": "/konto/oversikt",
}
PAGE_BY_PATH = {page.path: page for page in PAGES}
SECTIONS = tuple(dict.fromkeys(page.section for page in PAGES))

app = FastAPI(title="Fibaro10 V1 referanse", docs_url=None, redoc_url=None)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def pages_for(section: str) -> list[V1Page]:
    return [page for page in PAGES if page.section == section]


def badge(text: str, tone: str = "") -> str:
    return f'<span class="badge {esc(tone)}">{esc(text)}</span>'


def render_metric(label: str, value: str, sub: str = "", tone: str = "") -> str:
    return f"""
    <article class="metric-card {esc(tone)}">
      <span>{esc(label)}</span>
      <strong>{esc(value)}</strong>
      <small>{esc(sub)}</small>
    </article>
    """


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{esc(item)}</th>" for item in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"""
    <div class="table-wrap">
      <table>
        <thead><tr>{head}</tr></thead>
        <tbody>{body}</tbody>
      </table>
    </div>
    """


def render_chart(class_name: str = "chart") -> str:
    points = [42, 46, 50, 48, 54, 58, 63, 71, 76, 82, 86, 90]
    bars = "".join(f'<i style="height:{value}%"></i>' for value in points)
    return f"""
    <div class="{esc(class_name)}">
      <div class="chart-grid">{bars}</div>
      <div class="axis"><span>06</span><span>09</span><span>12</span><span>15</span><span>18</span><span>21</span><span>00</span></div>
    </div>
    """


def render_timeline(kind: str = "sun") -> str:
    rooms = [
        ("Rom 1", [("08:20", 10, 8, "standard"), ("12:10", 35, 9, "member"), ("17:25", 70, 7, "standard")]),
        ("Rom 2", [("09:05", 15, 11, "member"), ("14:40", 55, 10, "no-member")]),
        ("VIP", [("10:15", 24, 13, "standard"), ("18:05", 75, 9, "member")]),
        ("Rom 4", [("11:30", 31, 8, "no-member"), ("16:00", 64, 12, "standard")]),
    ]
    if kind == "parking":
        rooms = [
            ("Plasser", [("07:50", 8, 7, "parking"), ("08:30", 14, 15, "parking"), ("11:20", 33, 12, "parking-hot"), ("15:10", 62, 20, "parking-full")]),
            ("Omsetning", [("08:00", 10, 10, "parking"), ("12:00", 42, 12, "parking-hot"), ("16:00", 68, 13, "parking")]),
        ]
    lines = []
    for label, items in rooms:
        blocks = "".join(
            f'<a class="block {tone}" style="left:{left}%;width:{width}%" title="{esc(time)} {esc(label)}"><span>{esc(time)}</span></a>'
            for time, left, width, tone in items
        )
        lines.append(f'<div class="row-label">{esc(label)}</div><div class="line">{blocks}</div><div class="row-total">{len(items)} stk</div>')
    return f"""
    <section class="timeline-card">
      <header><h2>{'Dagslinje' if kind != 'parking' else 'Belegg gjennom dagen'}</h2><p>Dummydata for aa vise gammel V1-flate.</p></header>
      <div class="timeline-grid">
        <div></div><div class="time-axis"><span>06</span><span>09</span><span>12</span><span>15</span><span>18</span><span>21</span><span>00</span></div><div></div>
        {''.join(lines)}
      </div>
    </section>
    """


def render_status_demo(page: V1Page) -> str:
    return f"""
    <section class="hero">
      <div>
        <p class="kicker">Status akkurat naa</p>
        <h1>Aapent <span>stenger 23:00</span></h1>
      </div>
      <div class="hero-side">
        {badge("Datakilder frakoblet", "good")}
        {badge("Dummydata", "warn")}
      </div>
    </section>
    <section class="split-two">
      <div class="panel">
        <h2>Lys</h2>
        <div class="switch-grid">
          {badge("Lyslist dekor Av")} {badge("Reklameplakater Av")} {badge("Spot foran Av")} {badge("Parkeringslys Av")}
        </div>
      </div>
      <div class="panel">
        <h2>Ventilasjon</h2>
        <div class="switch-grid">
          {badge("Innl. VIP Av")} {badge("Innl. 2.etg Av")} {badge("Tak Av")} {badge("Avfukter Paa", "good")}
        </div>
      </div>
    </section>
    <section class="metric-grid">
      {render_metric("I dag", "4 637 kr", "Sol 1 073 kr / parkering 3 564 kr", "parking")}
      {render_metric("Uke", "40 593 kr", "Sammenlignet med forrige uke", "sun")}
      {render_metric("Maaned", "159 781 kr", "Til og med samme datatidspunkt", "revenue")}
      {render_metric("Strom naa", "12 600 W", "27,3 kWh i dag", "energy")}
    </section>
    <section class="split-two">
      <div class="panel">
        <h2>Siste hendelser</h2>
        {render_table(["Tid", "Hendelse", "Verdi"], [["10:41", "Siste soling", "Rom 12 Super VIP"], ["10:38", "Siste parkering", "EC65740"], ["10:51", "Energi sist lest", "12 600 W"], ["10:50", "Temp sist lest", "Skyet"]])}
      </div>
      <div class="panel">
        <h2>Status datakilder</h2>
        {render_table(["Kilde", "Status", "Alder"], [["Energi fra HC3", "OK", "Akkurat naa"], ["EasyPark import", "OK", "11 min"], ["Yr API", "OK", "1 min"], ["Sun2 enkelttimer", "Treg", "9 min"]])}
      </div>
    </section>
    """


def render_parking_demo(page: V1Page) -> str:
    if page.path == "/parkering/kjoretoy":
        return f"""
        <section class="panel">
          <div class="tool-row"><input value="nordby" aria-label="Sok"><button>Sok</button>{badge("Eksakt sok med hermetegn", "warn")}</div>
          {render_table(["Regnr", "Kjoretoy", "Navn", "Omraade", "Parkeringer", "Totalt"], [["EC65740", "Volvo XC60, graa", "Lise Nordby", "Lillehammer", "42", "12 840 kr"], ["HWN31L", "BMW 320, svart", "Ikke funnet", "Sverige", "3", "420 kr"], ["DY71543", "VW Golf, hvit", "Ikke funnet", "Danmark", "2", "280 kr"]])}
        </section>
        <section class="panel detail">
          <h2>Valgt bil: EC65740</h2>
          <div class="field-grid">
            <div><span>Eier</span><strong>Lise Nordby</strong></div><div><span>Eierskifte</span><strong>14.03.2024</strong></div><div><span>Merke/type</span><strong>Volvo XC60</strong></div><div><span>Farge</span><strong>Graa</strong></div>
          </div>
        </section>
        """
    return f"""
    <section class="metric-grid">
      {render_metric("Paa gaaende", "12", "sist oppdatert 8 min siden", "parking")}
      {render_metric("Omsetning i dag", "3 564 kr", "39 parkeringer", "parking")}
      {render_metric("Prognose", "7 900 kr", "basert paa dagens tempo", "revenue")}
      {render_metric("Uten omraade", "18", "klikkbar arbeidsliste", "warn")}
    </section>
    <section class="control-card">
      <div><span>Valgt dag</span><strong>28.06.2026</strong></div>
      <div class="button-row"><button>Forrige</button><button>I dag</button><button>Neste</button><button>Oppdater EasyPark</button></div>
    </section>
    {render_timeline("parking")}
    <section class="panel">
      <h2>Siste parkeringer</h2>
      {render_table(["Status", "Start", "Slutt", "Regnr", "Bil", "Eier", "Tidligere", "Belop", "Kamera"], [["Paa gaar", "10:38", "-", "EC65740", "Volvo XC60 graa", "Lise Nordby", "42 / 12 840 kr", "140 kr", "Start"], ["Avsluttet", "09:52", "10:24", "DF22311", "Toyota Yaris sort", "Ola Hansen", "8 / 1 120 kr", "70 kr", "Start / Slutt"], ["Avsluttet", "08:11", "09:45", "HWN31L", "BMW 320 svart", "Ikke funnet", "3 / 420 kr", "210 kr", "Start / Slutt"]])}
    </section>
    """


def render_sun_demo(page: V1Page) -> str:
    if page.path == "/soling/enkeltimer":
        return f"""
        <section class="panel">
          <div class="tool-row"><input value="28.06.2026" aria-label="Dato"><button>Vis dag</button>{badge("Bildearkiv dummy", "warn")}</div>
          {render_table(["Tid", "Rom", "Kunde", "Belop", "Bilde", "Handling"], [["09:12", "Rom 12 VIP", "Medlem 1043", "170 kr", "5 bilder", "Sett hovedbilde"], ["10:41", "Rom 11", "Drop-in", "90 kr", "mangler", "Velg bilde"], ["12:04", "Rom 8", "Medlem 8821", "110 kr", "5 bilder", "Apne arkiv"]])}
        </section>
        """
    return f"""
    <section class="metric-grid">
      {render_metric("Solinger", "18", "snitt 11,8 min", "sun")}
      {render_metric("Soltid", "3,5 t", "212 minutter totalt", "sun")}
      {render_metric("Omsetning", "2 180 kr", "121 kr per soling", "revenue")}
      {render_metric("Mest brukt", "VIP", "hoyest inntjening: Rom 12", "energy")}
    </section>
    {render_timeline("sun")}
    <section class="panel">
      <h2>Romfordeling</h2>
      {render_chart("chart sun-chart")}
    </section>
    """


def render_ventilation_demo(page: V1Page) -> str:
    return f"""
    <section class="summary-strip">
      {render_metric("1.etg", "22,4 C", "48% fukt", "vent")}
      {render_metric("2.etg", "22,7 C", "49% fukt", "vent")}
      {render_metric("VIP", "22,3 C", "48% fukt", "vent")}
      {render_metric("Kjeller", "15,5 C", "76% fukt", "vent")}
    </section>
    <section class="panel">
      <div class="panel-head"><h2>Dagslogg temperatur</h2><div class="button-row"><button>Forrige dag</button><button>I dag</button><button>Neste dag</button></div></div>
      <div class="line-chart">
        <svg viewBox="0 0 900 260" role="img" aria-label="Dummy temperaturgraf">
          <g stroke="#dfe6ef" stroke-width="1"><path d="M0 50h900M0 100h900M0 150h900M0 200h900M90 0v240M270 0v240M450 0v240M630 0v240M810 0v240"/></g>
          <polyline fill="none" stroke="#7a6a94" stroke-width="3" points="0,48 120,62 260,70 420,80 550,78 650,55 720,63 900,45"/>
          <polyline fill="none" stroke="#d86f55" stroke-width="3" points="0,92 150,96 300,104 500,116 700,111 900,105"/>
          <polyline fill="none" stroke="#4f8ca6" stroke-width="3" points="0,160 160,166 330,178 520,184 700,176 900,168"/>
          <line x1="540" y1="0" x2="540" y2="240" stroke="#5aa36b" stroke-dasharray="7 7" stroke-width="2"/>
          <line x1="602" y1="0" x2="602" y2="240" stroke="#5aa36b" stroke-dasharray="7 7" stroke-width="2"/>
        </svg>
      </div>
      <div class="state-lanes"><span>VIP</span><i></i><span>2.etg</span><i></i><span>Tak</span><i></i><span>Avf.</span><i></i></div>
    </section>
    """


def render_light_demo(page: V1Page) -> str:
    return f"""
    <section class="metric-grid">
      {render_metric("Lux naa", "3 335", "ute styring sensor", "light")}
      {render_metric("Dekor", "Av", "sist endret 08:02", "light")}
      {render_metric("Spot foran", "Av / Av", "glassvegg og massasje", "light")}
      {render_metric("Gatelys", "Av", "styrt av lux", "light")}
    </section>
    <section class="panel"><h2>Lux gjennom dagen</h2>{render_chart("chart light-chart")}</section>
    <section class="panel">{render_table(["Tid", "Kilde", "Lux", "Handling"], [["06:45", "Sensor", "142", "Gatelys paa"], ["08:12", "Sensor", "860", "Gatelys av"], ["09:45", "Sensor", "3335", "Normal"]])}</section>
    """


def render_energy_demo(page: V1Page) -> str:
    return f"""
    <section class="metric-grid">
      {render_metric("Strom naa", "12 600 W", "HC3 realtime", "energy")}
      {render_metric("Diff", "1 120 W", "beregnet fra maalere", "warn")}
      {render_metric("I dag", "27,3 kWh", "1 300 samples", "energy")}
      {render_metric("Elvia", "26,8 kWh", "kontrollfil", "energy")}
    </section>
    <section class="panel"><h2>Forbruk gjennom dagen</h2>{render_chart("chart energy-chart")}</section>
    <section class="split-two">
      <div class="panel"><h2>Kurser</h2>{render_table(["Kurs", "Gruppe", "Effekt"], [["5", "Lys", "420 W"], ["29", "Ventilasjon", "320 W"], ["449", "Annet", "180 W"]])}</div>
      <div class="panel"><h2>Laster</h2>{render_table(["Last", "Estimat", "Status"], [["Takvifte", "320 W", "Paa"], ["Avfukter", "180 W", "Paa"], ["Solseng VIP", "3 200 W", "Av"]])}</div>
    </section>
    """


def render_cleaning_demo(page: V1Page) -> str:
    return f"""
    <section class="metric-grid">
      {render_metric("Roboter", "3", "alle online", "clean")}
      {render_metric("Siste jobb", "I dag 07:20", "Butikk 42 min", "clean")}
      {render_metric("Batteri lavest", "64%", "Roborock S8", "clean")}
    </section>
    <section class="panel">{render_table(["Robot", "Rom", "Status", "Neste"], [["Roborock 1", "Butikk", "Lader", "23:30"], ["Roborock 2", "Gang", "Klar", "23:45"], ["Roborock 3", "Bakrom", "Vasker", "Naa"]])}</section>
    """


def render_admin_demo(page: V1Page) -> str:
    return f"""
    <section class="metric-grid">
      {render_metric("Build", "1311", "dummy fra V1-stil", "admin")}
      {render_metric("Brukere", "4", "master + viewer", "admin")}
      {render_metric("Datakilder", "frakoblet", "referansemodus", "warn")}
    </section>
    <section class="panel">
      <h2>{esc(page.title)}</h2>
      <p class="lead">{esc(page.purpose)}</p>
      {render_table(["Felt", "Dummyverdi", "Kommentar"], [["Kildecommit", SOURCE_COMMIT, "Historisk V1"], ["Modus", "reference_only", "ingen skriving"], ["Formaal", "Sammenligne funksjoner", "mot V2"]])}
    </section>
    """


def render_demo(page: V1Page) -> str:
    if page.section == "Status":
        return render_status_demo(page)
    if page.section == "Parkering":
        return render_parking_demo(page)
    if page.section == "Soling":
        return render_sun_demo(page)
    if page.section == "Ventilasjon":
        return render_ventilation_demo(page)
    if page.section == "Lys":
        return render_light_demo(page)
    if page.section == "Energi":
        return render_energy_demo(page)
    if page.section == "Renhold":
        return render_cleaning_demo(page)
    return render_admin_demo(page)


def render_main_nav(active_path: str) -> str:
    buttons = []
    active_section = PAGE_BY_PATH.get(active_path, PAGES[0]).section
    for section in SECTIONS:
        href = pages_for(section)[0].path
        buttons.append(f'<a class="nav-button {"active" if section == active_section else ""}" href="{esc(href)}">{esc(section)}</a>')
    subs = "".join(
        f'<a class="sub-button {"active" if page.path == active_path else ""}" href="{esc(page.path)}">{esc(page.title)}</a>'
        for page in pages_for(active_section)
    )
    return f'<nav class="main-nav">{"".join(buttons)}</nav><nav class="sub-nav">{subs}</nav>'


def render_shell(page: V1Page, content: str) -> str:
    return f"""<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fibaro10 V1 dummy</title>
  <style>
    :root {{
      --bg:#eef2f6; --panel:#fff; --soft:#f8fafc; --line:#d8dee7; --line-soft:#edf2f7;
      --text:#15202b; --muted:#667085; --navy:#071a45; --brand:#1f6f78;
      --parking:#356fbd; --sun:#d89524; --energy:#3d8b5c; --vent:#4f8ca6; --light:#df705d; --red:#c94747;
      --shadow:0 8px 22px rgba(15,23,42,.06);
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:linear-gradient(180deg,#f7f9fc 0%,var(--bg) 60%,#eef3f8 100%); color:var(--text); font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; font-size:14px; }}
    .site-header {{ position:sticky; top:0; z-index:10; background:rgba(255,255,255,.96); border-bottom:1px solid var(--line); box-shadow:0 3px 14px rgba(7,26,69,.05); }}
    .brand-bar {{ max-width:1260px; margin:0 auto; padding:.55rem .8rem; display:grid; grid-template-columns:auto 1fr; gap:.75rem; align-items:center; }}
    .brand {{ display:flex; align-items:center; gap:.55rem; text-decoration:none; color:var(--navy); font-weight:900; }}
    .brand-mark {{ width:2rem; height:2rem; display:grid; place-items:center; border-radius:8px; background:var(--navy); color:white; font-size:.8rem; }}
    .brand small {{ display:block; color:var(--muted); font-weight:760; font-size:.68rem; margin-top:.05rem; }}
    .navs {{ min-width:0; display:grid; gap:.35rem; }}
    .main-nav,.sub-nav {{ display:flex; flex-wrap:wrap; gap:.35rem; align-items:center; }}
    .nav-button,.sub-button,button {{ min-height:2rem; display:inline-flex; align-items:center; justify-content:center; padding:.36rem .64rem; border-radius:9px; border:1px solid var(--line); background:#fff; color:var(--navy); text-decoration:none; font-weight:830; font-size:.78rem; box-shadow:0 2px 7px rgba(7,26,69,.035); }}
    .nav-button.active,.sub-button.active {{ border-color:#b7c9e8; background:#edf5ff; color:#174b9a; }}
    .sub-button {{ min-height:1.8rem; font-size:.72rem; color:#344154; }}
    main {{ max-width:1260px; margin:0 auto; padding:.9rem .8rem 2rem; }}
    .page-title {{ display:flex; justify-content:space-between; gap:1rem; align-items:flex-end; margin:0 0 .75rem; }}
    h1 {{ margin:0; color:var(--navy); font-size:clamp(1.35rem,2vw,1.78rem); line-height:1.08; letter-spacing:0; }}
    h1 span {{ color:var(--muted); font-size:.86rem; font-weight:700; margin-left:.35rem; }}
    h2 {{ margin:0; color:var(--navy); font-size:1rem; }}
    p {{ margin:0; }}
    .lead,.page-title p {{ color:var(--muted); line-height:1.38; }}
    .badge {{ display:inline-flex; align-items:center; min-height:1.5rem; padding:.12rem .5rem; border-radius:999px; border:1px solid var(--line); background:#fff; color:#344154; font-size:.7rem; font-weight:850; white-space:nowrap; }}
    .badge.good {{ border-color:#b9dbc3; background:#edf8f0; color:#2f6d3d; }}
    .badge.warn {{ border-color:#efd392; background:#fff8e6; color:#805b12; }}
    .dummy-note {{ margin-bottom:.75rem; padding:.62rem .78rem; border:1px solid #efd392; border-radius:12px; background:#fff8e6; color:#735214; font-weight:740; }}
    .hero,.panel,.metric-card,.timeline-card,.control-card {{ border:1px solid var(--line); border-radius:14px; background:rgba(255,255,255,.96); box-shadow:var(--shadow); }}
    .hero {{ display:flex; justify-content:space-between; gap:1rem; align-items:center; padding:.85rem .95rem; margin-bottom:.75rem; }}
    .hero-side,.button-row,.switch-grid,.tool-row {{ display:flex; flex-wrap:wrap; gap:.42rem; align-items:center; }}
    .split-two {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.72rem; margin-bottom:.75rem; }}
    .panel {{ padding:.82rem .9rem; margin-bottom:.75rem; overflow:hidden; }}
    .panel-head {{ display:flex; justify-content:space-between; gap:1rem; align-items:center; margin-bottom:.65rem; }}
    .metric-grid,.summary-strip {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(10.5rem,1fr)); gap:.58rem; margin-bottom:.75rem; }}
    .metric-card {{ min-height:4.05rem; padding:.62rem .72rem; border-top:3px solid #d7e6e9; }}
    .metric-card.parking {{ border-top-color:var(--parking); }} .metric-card.sun {{ border-top-color:var(--sun); }} .metric-card.energy {{ border-top-color:var(--energy); }}
    .metric-card.vent {{ border-top-color:var(--vent); }} .metric-card.light {{ border-top-color:var(--light); }} .metric-card.revenue,.metric-card.warn {{ border-top-color:var(--red); }}
    .metric-card span,.control-card span,.field-grid span {{ display:block; color:var(--muted); font-size:.66rem; font-weight:850; text-transform:uppercase; letter-spacing:.04em; }}
    .metric-card strong,.control-card strong,.field-grid strong {{ display:block; margin-top:.12rem; color:var(--navy); font-size:1.18rem; line-height:1.04; font-weight:880; }}
    .metric-card small {{ display:block; margin-top:.22rem; color:var(--muted); font-size:.72rem; }}
    .control-card {{ display:flex; justify-content:space-between; gap:1rem; align-items:center; padding:.68rem .78rem; margin-bottom:.75rem; }}
    input {{ min-height:2rem; border:1px solid var(--line); border-radius:9px; padding:.35rem .55rem; font:inherit; }}
    .table-wrap {{ overflow:auto; border:1px solid var(--line-soft); border-radius:12px; background:#fff; margin-top:.58rem; }}
    table {{ width:100%; border-collapse:separate; border-spacing:0; font-size:.82rem; }}
    th,td {{ padding:.52rem .64rem; border-bottom:1px solid var(--line-soft); text-align:left; white-space:nowrap; }}
    th {{ background:#f7f9fc; color:#657187; font-size:.64rem; text-transform:uppercase; font-weight:850; }}
    tr:last-child td {{ border-bottom:0; }}
    .chart {{ height:15rem; padding:.7rem .7rem .35rem; border:1px solid var(--line-soft); border-radius:12px; background:linear-gradient(180deg,#fbfdff,#f6f9fd); }}
    .chart-grid {{ height:12rem; display:grid; grid-template-columns:repeat(12,1fr); gap:.42rem; align-items:end; border-bottom:1px solid #cfd9e6; }}
    .chart-grid i {{ display:block; min-height:8px; border-radius:5px 5px 2px 2px; background:linear-gradient(180deg,var(--parking),#234f91); }}
    .sun-chart .chart-grid i {{ background:linear-gradient(180deg,var(--sun),#b56d12); }} .energy-chart .chart-grid i {{ background:linear-gradient(180deg,var(--energy),#286541); }} .light-chart .chart-grid i {{ background:linear-gradient(180deg,var(--light),#bc4e3d); }}
    .axis,.time-axis {{ display:flex; justify-content:space-between; color:var(--muted); font-size:.66rem; font-weight:760; margin-top:.35rem; }}
    .timeline-card {{ margin-bottom:.75rem; overflow:auto; }}
    .timeline-card header {{ display:flex; justify-content:space-between; gap:1rem; padding:.75rem .85rem .55rem; border-bottom:1px solid var(--line-soft); }}
    .timeline-grid {{ min-width:860px; display:grid; grid-template-columns:5.5rem minmax(720px,1fr) 4.8rem; gap:.42rem .62rem; align-items:center; padding:.8rem .85rem 1rem; }}
    .row-label {{ color:var(--navy); font-weight:850; text-align:right; }}
    .row-total {{ color:var(--muted); font-size:.72rem; font-weight:800; }}
    .line {{ position:relative; height:2.45rem; border:1px solid #dbe6f2; border-radius:10px; background:linear-gradient(90deg,rgba(219,230,242,.72) 1px,transparent 1px),linear-gradient(180deg,#fbfdff,#f6f9fd); background-size:calc(100% / 18) 100%,100% 100%; overflow:hidden; }}
    .block {{ position:absolute; top:.42rem; height:1.55rem; border-radius:7px; background:linear-gradient(180deg,#3f7fbd,#2f6fa9); color:white; text-decoration:none; box-shadow:0 3px 9px rgba(63,127,189,.24); overflow:hidden; }}
    .block.member {{ background:linear-gradient(180deg,var(--energy),#2f7747); }} .block.no-member,.block.parking-hot {{ background:linear-gradient(180deg,var(--sun),#b56d12); }} .block.parking-full {{ background:linear-gradient(180deg,var(--red),#9e2f2f); }}
    .block span {{ display:block; padding:.22rem .34rem; font-size:.62rem; font-weight:850; white-space:nowrap; }}
    .line-chart svg {{ width:100%; height:18rem; display:block; border:1px solid var(--line-soft); border-radius:12px; background:#fff; }}
    .state-lanes {{ display:grid; grid-template-columns:4rem 1fr; gap:.35rem .55rem; align-items:center; margin-top:.55rem; color:var(--navy); font-weight:850; }}
    .state-lanes i {{ height:1.4rem; border:1px solid #dbe6f2; border-radius:8px; background:linear-gradient(90deg,#fff 0 45%,#dff4e6 45% 58%,#fff 58%); }}
    .field-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(11rem,1fr)); gap:.5rem; margin-top:.6rem; }}
    .field-grid div {{ border:1px solid var(--line-soft); border-radius:10px; padding:.55rem .65rem; background:#f8fafc; }}
    @media (max-width:760px) {{ .brand-bar,.split-two,.control-card,.page-title {{ grid-template-columns:1fr; display:grid; }} .hero {{ align-items:flex-start; flex-direction:column; }} }}
  </style>
</head>
<body>
  <header class="site-header">
    <div class="brand-bar">
      <a class="brand" href="/status/dashboard"><span class="brand-mark">LT</span><span>Lilletorget<small>Fibaro10 V1 dummy</small></span></a>
      <div class="navs">{render_main_nav(page.path)}</div>
    </div>
  </header>
  <main>
    <section class="page-title">
      <div><h1>{esc(page.title)}</h1><p>{esc(page.purpose)}</p></div>
      <div class="hero-side">{badge('Datakilder frakoblet', 'good')}{badge('V1 dummydata', 'warn')}</div>
    </section>
    <div class="dummy-note">Dette er en visuell V1-referanse med dummydata. Den viser hvordan grensesnitt og funksjoner var tenkt, men gjør ingen databasekall, import, skraping eller skriving.</div>
    {content}
  </main>
</body>
</html>"""


def render_unknown(path: str) -> str:
    page = V1Page("Status", "/status/dashboard", "Ukjent V1-rute", f"{path} finnes ikke i V1-referansen.")
    return render_shell(page, "<section class=\"panel\"><p>Velg en side i menyen for aa se V1-grensesnittet med dummydata.</p></section>")


@app.get("/health")
async def health():
    return JSONResponse(
        {
            "ok": True,
            "service": "fibaro10_v1_reference",
            "mode": "reference_only",
            "data_sources": "disabled",
            "source_commit": SOURCE_COMMIT,
            "build": APP_BUILD,
            "pages": len(PAGES),
        }
    )


@app.get("/{full_path:path}", response_class=HTMLResponse)
async def reference_page(full_path: str):
    path = "/" + full_path.strip("/")
    if path == "/":
        path = "/status/dashboard"
    path = ALIASES.get(path, path)
    page = PAGE_BY_PATH.get(path)
    if not page:
        return HTMLResponse(render_unknown(path))
    return HTMLResponse(render_shell(page, render_demo(page)))
