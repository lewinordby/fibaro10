import html
import os
from dataclasses import dataclass
from typing import Iterable

from fastapi import FastAPI, Request
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
    features: tuple[str, ...]
    sources: tuple[str, ...]


PAGES: tuple[V1Page, ...] = (
    V1Page(
        "Status",
        "/status/dashboard",
        "Dashboard",
        "Samlet driftsside med status akkurat nå, siste hendelser og snarveier videre.",
        ("Åpning/status", "Lys og ventilasjon", "Siste soling og parkering", "Datakildestatus"),
        ("Fibaro10 database", "HC3", "EasyPark", "Sun2", "Yr", "Roborock"),
    ),
    V1Page(
        "Status",
        "/status/nokkeltall",
        "Nøkkeltall",
        "Kompakt oversikt over sentrale tall for drift, parkering, soling og energi.",
        ("Dag/uke/måned", "Soling", "Parkering", "Energi"),
        ("Fibaro10 database", "EasyPark", "Sun2", "HC3"),
    ),
    V1Page(
        "Status",
        "/status/omsetning",
        "Omsetning",
        "Måneds- og dagsbaserte grafer for samlet omsetning.",
        ("Omsetningsgraf", "Soling", "Parkering", "Tabeller"),
        ("EasyPark", "Sun2"),
    ),
    V1Page(
        "Status",
        "/status/dagslinje",
        "Dagslinje",
        "Tidslinje for daglig aktivitet på tvers av parkering og soling.",
        ("Aktivitet gjennom dagen", "Soling", "Parkering"),
        ("EasyPark", "Sun2"),
    ),
    V1Page(
        "Status",
        "/status/statistikk",
        "Statistikk",
        "Mer langsiktige statistikkbilder og fordelinger.",
        ("Topplister", "Utvikling", "Fordelinger"),
        ("Fibaro10 database",),
    ),
    V1Page(
        "Status",
        "/status/datakilder",
        "Datakilder",
        "Oversikt over importjobber, sist kjørte kilder og status.",
        ("Jobbstatus", "Siste kjøring", "Feil og advarsler"),
        ("Importstatus-tabeller",),
    ),
    V1Page(
        "Parkering",
        "/parkering/oversikt",
        "Oversikt",
        "Parkeringsdashboard med dagens aktivitet, siste parkeringer og nøkkeltall.",
        ("Pågående/avsluttede parkeringer", "Omsetning", "Siste parkeringer", "Kjøretøydata"),
        ("EasyPark", "SVV", "Fibaro10 database"),
    ),
    V1Page(
        "Parkering",
        "/parkering/prognose",
        "Prognose",
        "Parkeringsprognose basert på historikk og tempo i aktuell periode.",
        ("Dagsprognose", "Månedsprognose", "Manuell lagring"),
        ("EasyPark", "Historikk"),
    ),
    V1Page(
        "Parkering",
        "/parkering/parkeringer",
        "Parkeringer",
        "Tabell for søk og kontroll av enkeltparkeringer.",
        ("Dato/filter", "Registreringsnummer", "Status", "Beløp"),
        ("EasyPark",),
    ),
    V1Page(
        "Parkering",
        "/parkering/statistikk",
        "Statistikk",
        "Aggregert parkeringsstatistikk og utvikling.",
        ("Topplister", "Område", "Kjøretøy", "Omsetning"),
        ("EasyPark", "SVV"),
    ),
    V1Page(
        "Parkering",
        "/parkering/bilstatistikk",
        "Bilstatistikk",
        "Oversikt over kjøretøy, frekvens, merker og bruksmønster.",
        ("Merke/type", "Antall parkeringer", "Eier-/kjøretøyfelter"),
        ("SVV", "EasyPark"),
    ),
    V1Page(
        "Parkering",
        "/parkering/omrade",
        "Område",
        "Analyse av parkeringsområde og områdefordeling.",
        ("Områdefilter", "Ikke funnet", "Søk"),
        ("EasyPark", "SVV", "Manuelle områdeverdier"),
    ),
    V1Page(
        "Parkering",
        "/parkering/omrade-oppslag",
        "Oppslag",
        "Arbeidsflate for kjøretøy der område/eier måtte sjekkes manuelt.",
        ("Mangler område", "Manuell oppdatering", "Kopiliste"),
        ("SVV", "Manuell kontroll"),
    ),
    V1Page(
        "Parkering",
        "/parkering/kjoretoy",
        "Kjøretøy",
        "Søk og detaljvisning for biler, eiere og parkeringshistorikk.",
        ("Bil/eier-søk", "Kjøretøydetaljer", "Parkeringshistorikk"),
        ("EasyPark", "SVV"),
    ),
    V1Page(
        "Soling",
        "/soling/dagslinje",
        "Dagslinje",
        "Dagsvis tidslinje for soltimer med rom, bilder og nøkkeltall.",
        ("Soltimer", "Romlinjer", "Bilder", "Energi-/omsetningskort"),
        ("Sun2", "Axis", "HC3"),
    ),
    V1Page(
        "Soling",
        "/soling/prognose",
        "Prognose",
        "Prognose for soling basert på historikk og tempo.",
        ("Dag/måned", "Historikk", "Manuell prognose"),
        ("Sun2",),
    ),
    V1Page(
        "Soling",
        "/soling/oversikt",
        "Statistikk",
        "Oversikt over soling, rom, topplister og utvikling.",
        ("År/måned", "Rom", "Omsetning", "Antall"),
        ("Sun2",),
    ),
    V1Page(
        "Soling",
        "/soling/detaljer",
        "Detaljer",
        "Detaljerte nøkkeltall for soling og rombruk.",
        ("Romfordeling", "Utvikling", "Detaljgrafer"),
        ("Sun2",),
    ),
    V1Page(
        "Soling",
        "/soling/enkeltimer",
        "Enkeltimer",
        "Liste over enkeltsolinger med rom, bruker, beløp, status og bilder.",
        ("Søk", "Bildevalg", "Rom", "Betaling"),
        ("Sun2", "Axis"),
    ),
    V1Page(
        "Soling",
        "/soling/senger",
        "Senger",
        "Fasit mellom Sun2-seng, fysisk rom og intern romidentitet.",
        ("Sun2-id", "Fysisk rom", "Navnemapping"),
        ("Sun2",),
    ),
    V1Page(
        "Soling",
        "/soling/medlemmer",
        "Medlemmer",
        "Medlems-/kunderegister slik det kunne utledes fra Sun2.",
        ("Sun2-id", "Navn", "Telefon/e-post der kjent"),
        ("Sun2",),
    ),
    V1Page(
        "Lys",
        "/lys/dagslogg-lux",
        "Dagslogg",
        "Lux- og lysstatus gjennom valgt dag.",
        ("Luxgraf", "Lysstatus", "Dagvelger"),
        ("HC3",),
    ),
    V1Page(
        "Lys",
        "/lys/hendelser",
        "Hendelser",
        "Rå hendelseslogg for lysstyring.",
        ("Tid", "Enhet", "Status", "Kilde"),
        ("HC3",),
    ),
    V1Page(
        "Lys",
        "/lys/lux-logging",
        "Målinger",
        "Tabell over luxmålinger og relevante lysverdier.",
        ("Lux", "Kilde", "Tid"),
        ("HC3",),
    ),
    V1Page(
        "Lys",
        "/lys/innstillinger",
        "Innstillinger",
        "Regler og terskler som HC3-scenen kunne hente.",
        ("Grenseverdier", "Tidsvinduer", "Endringshistorikk"),
        ("Fibaro10 database", "HC3"),
    ),
    V1Page(
        "Ventilasjon",
        "/ventilasjon/dagslogg-temp",
        "Dagslogg",
        "Temperatur, fukt og ventilasjonsstatus gjennom valgt dag.",
        ("Temperaturgraf", "Fukt", "Viftehendelser", "Dagvelger"),
        ("HC3", "Yr"),
    ),
    V1Page(
        "Ventilasjon",
        "/ventilasjon/hendelser",
        "Hendelser",
        "Rå hendelseslogg for ventilasjon og avfukter.",
        ("Tid", "Enhet", "På/av", "Modus"),
        ("HC3",),
    ),
    V1Page(
        "Ventilasjon",
        "/ventilasjon/temp-logg",
        "Temp logg",
        "Historisk temperatur- og fuktlogg.",
        ("Inne", "Ute", "Loft", "Kjeller", "Fukt"),
        ("HC3", "Yr"),
    ),
    V1Page(
        "Ventilasjon",
        "/ventilasjon/yr-logg",
        "Yr logg",
        "Værdata fra Yr brukt sammen med drift og analyse.",
        ("Temperatur", "Fukt", "Vind", "Skydekke"),
        ("Yr",),
    ),
    V1Page(
        "Ventilasjon",
        "/ventilasjon/innstillinger",
        "Innstillinger",
        "Regler og styringsparametre for ventilasjon.",
        ("Modus", "Grenser", "Tidsvinduer", "Endringshistorikk"),
        ("Fibaro10 database", "HC3"),
    ),
    V1Page(
        "Energi",
        "/energi/status",
        "Status",
        "Energioversikt med realtime effekt, kWh og sammenligning mot Elvia.",
        ("Realtime W", "Dagsforbruk", "Elvia", "Kurver"),
        ("HC3", "Elvia"),
    ),
    V1Page(
        "Energi",
        "/energi/kurser",
        "Kurser",
        "Register over elektriske kurser og målere.",
        ("Kursnummer", "Måler", "Gruppe", "PDF"),
        ("Fibaro10 database",),
    ),
    V1Page(
        "Energi",
        "/energi/laster",
        "Laster",
        "Register over strømforbrukere og estimater.",
        ("Last", "Effekt", "Gruppe", "Aktiv"),
        ("Fibaro10 database", "HC3"),
    ),
    V1Page(
        "Energi",
        "/energi/forbruk-per-seng",
        "Forbruk/seng",
        "Beregning av solsengenes strømforbruk basert på perioder med én aktiv seng.",
        ("Sun2 timer", "HC3 differanse", "Estimert kWh"),
        ("Sun2", "HC3"),
    ),
    V1Page(
        "Energi",
        "/energi/elvia",
        "Elvia",
        "Opplasting og visning av Elvia-forbruksfiler.",
        ("Filopplasting", "Månedsdata", "Avstemming"),
        ("Elvia filer",),
    ),
    V1Page(
        "Renhold",
        "/renhold/oversikt",
        "Oversikt",
        "Roborock-status, kart, planlagte jobber og renholdshistorikk.",
        ("Robotstatus", "Jobber", "Batteri", "Historikk"),
        ("Roborock",),
    ),
    V1Page(
        "AI",
        "/ai/sok",
        "Søk",
        "Tidlig AI-søk mot utvalgte datasett og logger.",
        ("Datasettvalg", "Spørsmål", "Kilder"),
        ("Fibaro10 database", "OpenAI hvis konfigurert"),
    ),
    V1Page(
        "AI",
        "/ai/innstillinger",
        "Innstillinger",
        "Konfigurasjon for AI-datasett og søk.",
        ("Datasett", "Tilgang", "Logger"),
        ("Fibaro10 database",),
    ),
    V1Page(
        "Konto",
        "/konto/oversikt",
        "Oversikt",
        "Konto- og driftsside med snarveier til teknisk informasjon.",
        ("Profil", "Snarveier", "Driftslenker"),
        ("Ingen ekstern kilde",),
    ),
    V1Page(
        "Konto",
        "/konto/build",
        "Build",
        "Historisk buildlogg og endringsoversikt.",
        ("Buildliste", "Detaljer", "Endringshistorikk"),
        ("Buildlogg i kode",),
    ),
    V1Page(
        "Konto",
        "/konto/teknisk",
        "Teknisk",
        "Teknisk oversikt over arkitektur, datakilder og driftsoppsett.",
        ("Arkitektur", "Containere", "Kilder", "Feilsøking"),
        ("Dokumentasjon i V1",),
    ),
    V1Page(
        "Konto",
        "/konto/manual",
        "Manual",
        "Brukermanual for V1-funksjonaliteten.",
        ("Parkering", "Soling", "Energi", "Ventilasjon", "Lys"),
        ("Dokumentasjon i V1",),
    ),
    V1Page(
        "Konto",
        "/konto/brukere-og-tilgang",
        "Brukere",
        "Administrasjon av brukere og tilgangsnøkler.",
        ("Brukere", "Roller", "Aktiv/deaktiv"),
        ("Fibaro10 database",),
    ),
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
}

PAGE_BY_PATH = {page.path: page for page in PAGES}
SECTIONS = tuple(dict.fromkeys(page.section for page in PAGES))

app = FastAPI(title="Fibaro10 V1 referanse", docs_url=None, redoc_url=None)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def section_pages(section: str) -> list[V1Page]:
    return [page for page in PAGES if page.section == section]


def source_text(values: Iterable[str]) -> str:
    return ", ".join(values) if values else "Ingen"


def render_nav(active_path: str) -> str:
    chunks: list[str] = []
    for section in SECTIONS:
        items = section_pages(section)
        active = any(item.path == active_path for item in items)
        chunks.append(f'<section class="nav-group {"active" if active else ""}">')
        chunks.append(f"<h2>{esc(section)}</h2>")
        for item in items:
            chunks.append(
                f'<a class="nav-link {"current" if item.path == active_path else ""}" href="{esc(item.path)}">'
                f"<span>{esc(item.title)}</span>"
                f"<small>{esc(item.path)}</small>"
                "</a>"
            )
        chunks.append("</section>")
    return "".join(chunks)


def render_page_card(page: V1Page) -> str:
    features = "".join(f"<li>{esc(feature)}</li>" for feature in page.features)
    sources = "".join(f"<span>{esc(source)}</span>" for source in page.sources)
    return f"""
    <article class="page-card">
      <div>
        <p class="kicker">{esc(page.section)}</p>
        <h1>{esc(page.title)}</h1>
        <p class="path">{esc(page.path)}</p>
      </div>
      <p class="purpose">{esc(page.purpose)}</p>
      <div class="split">
        <section>
          <h3>Funksjoner i V1</h3>
          <ul>{features}</ul>
        </section>
        <section>
          <h3>Datakilder V1 brukte</h3>
          <div class="pill-row">{sources}</div>
        </section>
      </div>
      <div class="notice">
        Datakilder er frakoblet i denne referansevisningen. Siden viser hva V1 hadde av funksjonalitet,
        men gjør ingen databasekall, import, skraping eller skriving.
      </div>
    </article>
    """


def render_overview() -> str:
    groups = []
    for section in SECTIONS:
        items = section_pages(section)
        links = "".join(
            f'<a href="{esc(item.path)}"><strong>{esc(item.title)}</strong><span>{esc(item.purpose)}</span></a>'
            for item in items
        )
        groups.append(
            f"""
            <section class="overview-group">
              <div class="group-head">
                <h2>{esc(section)}</h2>
                <span>{len(items)} sider</span>
              </div>
              <div class="overview-links">{links}</div>
            </section>
            """
        )
    return "".join(groups)


def render_unknown(path: str) -> str:
    return f"""
    <article class="page-card">
      <p class="kicker">V1 referanse</p>
      <h1>Ukjent V1-rute</h1>
      <p class="path">{esc(path)}</p>
      <p class="purpose">Denne ruten finnes ikke i den registrerte V1-menyen fra commit {esc(SOURCE_COMMIT)}.</p>
      <div class="notice">Velg en side i menyen for å se hva slags funksjonalitet V1 hadde.</div>
    </article>
    """


def render_shell(active_path: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fibaro10 V1 referanse</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f7fb;
      --panel: #ffffff;
      --text: #152033;
      --muted: #6a7485;
      --line: #dfe6ef;
      --blue: #2f5fd7;
      --gold: #d99a24;
      --green: #3d8b5c;
      --red: #c94747;
      --shadow: 0 14px 34px rgba(17, 31, 52, .08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background: var(--bg);
    }}
    .app {{
      display: grid;
      grid-template-columns: 310px minmax(0, 1fr);
      min-height: 100vh;
    }}
    aside {{
      position: sticky;
      top: 0;
      height: 100vh;
      overflow: auto;
      padding: 24px 18px;
      border-right: 1px solid var(--line);
      background: #fff;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 22px;
    }}
    .mark {{
      display: grid;
      place-items: center;
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: linear-gradient(135deg, var(--blue), #6f8cf4);
      color: #fff;
      font-weight: 850;
    }}
    .brand strong {{ display: block; font-size: 18px; }}
    .brand span:last-child {{ color: var(--muted); font-size: 12px; }}
    .nav-group {{ margin: 0 0 16px; }}
    .nav-group h2 {{
      margin: 0 0 6px;
      color: #2d3748;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    .nav-link {{
      display: grid;
      gap: 2px;
      padding: 8px 10px;
      border-radius: 8px;
      color: inherit;
      text-decoration: none;
    }}
    .nav-link:hover {{ background: #f2f5fb; }}
    .nav-link.current {{
      background: #edf3ff;
      color: #143f9d;
      box-shadow: inset 3px 0 0 var(--blue);
    }}
    .nav-link span {{ font-size: 14px; font-weight: 750; }}
    .nav-link small {{ color: var(--muted); font-size: 11px; }}
    main {{ padding: 28px; }}
    .topbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .topbar h1 {{
      margin: 0;
      font-size: 24px;
      letter-spacing: 0;
    }}
    .status-row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .status-row span {{
      padding: 7px 10px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      color: var(--muted);
      font-size: 12px;
      font-weight: 720;
    }}
    .status-row span:first-child {{
      color: #1f6c42;
      border-color: #bfe5cc;
      background: #effaf3;
    }}
    .page-card, .overview-group {{
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
      box-shadow: var(--shadow);
    }}
    .page-card {{ padding: 26px; }}
    .kicker {{
      margin: 0 0 6px;
      color: var(--blue);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .09em;
      font-weight: 850;
    }}
    .page-card h1 {{ margin: 0; font-size: 32px; letter-spacing: 0; }}
    .path {{ margin: 8px 0 0; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .purpose {{ margin: 24px 0; max-width: 860px; color: #344154; font-size: 18px; line-height: 1.45; }}
    .split {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 18px; }}
    .split section {{
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8fafc;
    }}
    h3 {{ margin: 0 0 12px; font-size: 15px; }}
    ul {{ margin: 0; padding-left: 18px; color: #354154; line-height: 1.7; }}
    .pill-row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .pill-row span {{
      padding: 8px 10px;
      border-radius: 999px;
      background: #fff;
      border: 1px solid var(--line);
      color: #354154;
      font-size: 13px;
      font-weight: 700;
    }}
    .notice {{
      margin-top: 18px;
      padding: 14px 16px;
      border-radius: 8px;
      border: 1px solid #f0d7a0;
      background: #fff8eb;
      color: #735214;
      line-height: 1.45;
      font-weight: 680;
    }}
    .overview {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    .overview-group {{ padding: 18px; }}
    .group-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;
    }}
    .group-head h2 {{ margin: 0; font-size: 18px; }}
    .group-head span {{ color: var(--muted); font-size: 12px; font-weight: 760; }}
    .overview-links {{ display: grid; gap: 8px; }}
    .overview-links a {{
      display: grid;
      gap: 3px;
      padding: 10px 12px;
      border-radius: 8px;
      background: #f8fafc;
      color: inherit;
      text-decoration: none;
    }}
    .overview-links a:hover {{ background: #edf3ff; }}
    .overview-links strong {{ font-size: 14px; }}
    .overview-links span {{ color: var(--muted); font-size: 12px; line-height: 1.35; }}
    @media (max-width: 920px) {{
      .app {{ grid-template-columns: 1fr; }}
      aside {{ position: relative; height: auto; }}
      .split, .overview {{ grid-template-columns: 1fr; }}
      main {{ padding: 18px; }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <div class="brand">
        <span class="mark">V1</span>
        <span><strong>Fibaro10 V1</strong><span>Historisk referanse</span></span>
      </div>
      {render_nav(active_path)}
    </aside>
    <main>
      <div class="topbar">
        <h1>V1-funksjonalitet</h1>
        <div class="status-row">
          <span>Datakilder frakoblet</span>
          <span>Kildecommit {esc(SOURCE_COMMIT)}</span>
          <span>Build {esc(APP_BUILD)}</span>
          <span>Port {esc(PORT)}</span>
        </div>
      </div>
      {content}
    </main>
  </div>
</body>
</html>"""


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
async def reference_page(request: Request, full_path: str):
    path = "/" + full_path.strip("/")
    if path == "/":
        path = "/status/dashboard"
    path = ALIASES.get(path, path)
    page = PAGE_BY_PATH.get(path)
    if page:
        content = render_page_card(page)
        active_path = page.path
    elif full_path.strip() == "oversikt":
        content = f'<div class="overview">{render_overview()}</div>'
        active_path = "/status/dashboard"
    else:
        content = render_unknown(path)
        active_path = path
    return HTMLResponse(render_shell(active_path, content))
