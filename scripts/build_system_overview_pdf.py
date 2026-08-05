from __future__ import annotations

import ast
import json
import re
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
OUTPUT_FILE = OUTPUT_DIR / "fibaro10-komplett-oversikt.pdf"
HEALTH_URL = "http://192.168.20.218:8110/health?details=true"

PRIMARY = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#dbe4ef")
SOFT = colors.HexColor("#f8fafc")
BLUE = colors.HexColor("#2563eb")
ORANGE = colors.HexColor("#f59e0b")
GREEN = colors.HexColor("#16a34a")
RED = colors.HexColor("#dc2626")
PURPLE = colors.HexColor("#7c3aed")
TEAL = colors.HexColor("#0891b2")


MODULE_PURPOSES: dict[str, str] = {
    "status": "Operativt dashboard for omsetning, parkering, soling og drift.",
    "omsetning": "Samlede økonomitall, periodeutvikling og års-/månedsanalyser.",
    "parkering": "Parkeringer, kjøretøydata, områder, prognoser, oppgjør og datakvalitet.",
    "soling": "Soltimer, senger, medlemmer, produkter, prognoser, oppgjør og bilder.",
    "koble": "Kobler parkeringer mot SUN2-brukere basert på gjentatte tidsmessige treff.",
    "energi": "HC3-energi, Elvia-kontroll, kurser, laster og forbruk per seng.",
    "ventilasjon": "Temperatur, fukt, Yr, viftestyring, hendelser og regler.",
    "lys": "Utelys, lux, skydekke, solhøyde, hendelser og regler.",
    "solrom": "Operativ status for solrom 1-12 med dørstatus og koblet soltime.",
    "solrom-2": "Alternativ arbeidsflate for solrom med avvik og romdetaljer.",
    "dorer2": "Nyere dørflate for solrom og byggdører med situasjon og romdetaljer.",
    "dorer": "Eksisterende dørflater, alarm, solrom, romkontroll og rådata.",
    "vedlikehold": "Vedlikeholdsoppgaver og Lilletorget-besøk koblet fra OwnTracks.",
    "renhold": "Roborock-roboter, renholdsstatus og robotdata.",
    "mobil": "Samler og speiler mobilskjermer i desktopflaten.",
    "ideer": "Vurderingsområde for nye funksjoner og forbedringsforslag.",
    "manual": "Webmanual med kapittelstruktur, rutiner og feilsøking.",
    "admin": "Systemdrift, datakilder, buildlogg, brukere, teknisk kontroll og verktøy.",
}


VIEW_PURPOSES: dict[tuple[str, str], str] = {
    ("status", "omsetning"): "Dashboard for dagens, ukens, månedens og årets omsetning med sammenligninger.",
    ("status", "parkering"): "Dashboard for parkeringsaktivitet, nye kjøretøy og operativ status.",
    ("status", "soling"): "Dashboard for solingsaktivitet og utvikling.",
    ("status", "drift"): "Datakilder, klima, energi, lys og viftestyring akkurat nå.",
    ("omsetning", "oversikt"): "Årsoversikt, toppdager/-måneder og nøkkeltall for omsetning.",
    ("omsetning", "sammenligning"): "Akkumulert dag/uke/måned mot referanseperioder.",
    ("omsetning", "akkumulert"): "Akkumulert årsutvikling for omsetning mot tidligere år.",
    ("omsetning", "manedsoversikt"): "Månedsvis søylediagram og tabeller for månedstall.",
    ("parkering", "oversikt"): "Ukestatistikk, siste parkeringer og parkeringsnøkkeltall.",
    ("parkering", "parkeringer"): "Daglig arbeidsliste for parkeringer med EasyPark-oppdatering.",
    ("parkering", "dagslinje"): "Visuell beleggs- og kapasitetslinje for parkeringsplasser.",
    ("parkering", "tidspunkt"): "Fordeling av parkeringstid og omsetning per ukedag og klokkeslett.",
    ("parkering", "kjoretoy"): "Søk, kjøretøy/eierdata, historikk og datakvalitet per bil.",
    ("parkering", "omrade"): "Områdeanalyse med dato eller tidsrom.",
    ("parkering", "prognose"): "Parkeringsprognoser etter import og historisk utvikling.",
    ("parkering", "sammenligning"): "Akkumulert årssammenligning for parkering.",
    ("parkering", "oppgjor"): "Park Nordic/EasyPark-oppgjør og kontroll mot interne summer.",
    ("parkering", "oppslag"): "SVV, Biluppgifter, Tjekbil, område og kjøretøydatakvalitet.",
    ("parkering", "bilstatistikk"): "Skjult analyseflate for bilstatistikk.",
    ("soling", "oversikt"): "Analyseflate for soling med årsgrafer og nøkkeltall.",
    ("soling", "sammenligning"): "Akkumulert årssammenligning for soling.",
    ("soling", "dagslinje"): "Daglig tidslinje for rom/senger med salg, bilder og energi.",
    ("soling", "enkeltimer"): "Arbeidsflate for soltimer, SUN2-id, bilder og manuell kontroll.",
    ("soling", "oppgjor"): "Solingsoppgjør/kreditnota og kontroll mot SUN2-tall.",
    ("soling", "prognose"): "Solingsprognoser og utvikling.",
    ("soling", "produkter"): "Produktsalg fra SUN2 per dag/måned.",
    ("soling", "senger"): "Rom- og sengmetadata fra SUN2.",
    ("soling", "medlemmer"): "SUN2-medlemmer og medlemsgrunnlag.",
    ("soling", "statistikk"): "Supplerende solingsstatistikk.",
    ("soling", "detaljer"): "Detaljvisninger for solingsgrunnlag.",
    ("koble", "oversikt"): "Status og nøkkeltall for koblingsmotoren.",
    ("koble", "sun2"): "Kontroll gruppert på SUN2-id og mulige bilkoblinger.",
    ("koble", "biltreff"): "Biler med gjentatte soltreff og parkeringssummer.",
    ("koble", "kandidater"): "Manuell bekreftelse/avvisning av koblingskandidater.",
    ("koble", "treffgrunnlag"): "Rågrunnlag for parkering/SUN2-treff.",
    ("koble", "jobb"): "Worker-status, parametere og behandlingstall.",
    ("energi", "status"): "Overblikk over sanntidsforbruk, differanse og energikilder.",
    ("energi", "elvia-kontroll"): "Kontroll mellom Elvia-import og HC3-målinger.",
    ("energi", "kurser"): "Elektriske kurser og metadata.",
    ("energi", "laster"): "Definerte laster og kobling mot målere.",
    ("energi", "forbruk-per-seng"): "Beregnet energiforbruk per solseng.",
    ("energi", "elvia"): "Opplasting/import av Elvia-filer.",
    ("energi", "verktoy"): "Tekniske energiverktøy.",
    ("ventilasjon", "dagslogg"): "Temperaturgraf, fukt og viftestyring gjennom valgt dag.",
    ("ventilasjon", "temp-logg"): "Temperatur- og fuktlogg fordelt på inne, ute, ventilasjon og kjeller.",
    ("ventilasjon", "yr-logg"): "Yr-data med temperatur, fukt, skydekke, vind og værdata.",
    ("ventilasjon", "hendelser"): "Viftehendelser og styringsårsaker.",
    ("ventilasjon", "innstillinger"): "Terskler, driftstid og ventilasjonsregler.",
    ("lys", "dagslogg"): "Lux, skydekke, solhøyde og lyshendelser gjennom dagen.",
    ("lys", "lux-logging"): "Lux-logg og målegrunnlag.",
    ("lys", "hendelser"): "På/av-hendelser for lys med årsak.",
    ("lys", "innstillinger"): "Regler og terskler for utelys.",
    ("solrom", "oversikt"): "Operativ status for solrom nå.",
    ("solrom", "dagskontroll"): "Dagskontroll med rom, dører, soltimer og tidslinjer.",
    ("solrom", "rom"): "Skjult detaljvisning for ett solrom.",
    ("solrom-2", "oversikt"): "Alternativ nåflate for solrom.",
    ("solrom-2", "dagskontroll"): "Dagsmatrise for alle solrom.",
    ("solrom-2", "avvik"): "Avvik, varsler og usikre koblinger.",
    ("solrom-2", "rom"): "Skjult romdetalj.",
    ("dorer2", "oversikt"): "Situasjon for solrom og dører med prioriterte avvik.",
    ("dorer2", "rom"): "Skjult romdetalj.",
    ("dorer2", "bygg"): "Byggdører vurdert mot normalposisjon.",
    ("dorer", "oversikt"): "Kompakt status for solrom og andre dører.",
    ("dorer", "oversikt-ny"): "Alternativ dørstatusflate.",
    ("dorer", "romkontroll"): "Romkontroll med soltimer og dørperioder.",
    ("dorer", "romkontroll-ny"): "Alternativ romkontroll.",
    ("dorer", "romkontroll-ny2"): "Romkontroll med faner, tidslinje og hendelser.",
    ("dorer", "soltimer"): "Kobling mellom dørperioder og soltimer.",
    ("dorer", "alarm"): "Alarm når solrom er lukket uten tilhørende soltime.",
    ("dorer", "solrom"): "Solromsstatus via dørdata.",
    ("dorer", "solrom-ny"): "Alternativ solromsvisning.",
    ("dorer", "andre"): "Andre byggdører.",
    ("dorer", "radata"): "Alle dørhendelser fra HC3.",
    ("vedlikehold", "oversikt"): "Vedlikeholdslogger og oppgaver.",
    ("vedlikehold", "besok"): "Lilletorget-besøk fra OwnTracks koblet til oppgaver.",
    ("renhold", "oversikt"): "Renholdsstatus og siste aktivitet.",
    ("renhold", "roboter"): "Roborock-status og robotdata.",
    ("ideer", "oversikt"): "Samlet vurdering av nye ideer.",
    ("ideer", "kontroll"): "Kontrollforslag og forbedringer.",
    ("ideer", "innsikt"): "Analyse- og innsiktsideer.",
    ("ideer", "automatisering"): "Automatiseringsforslag.",
    ("ideer", "arbeidsflyt"): "Arbeidsflyt og praktiske forbedringer.",
    ("mobil", "oversikt"): "Rutenett med mobilskjermer i desktopflaten.",
    ("manual", "oversikt"): "Kapitteloversikt og lenker.",
    ("manual", "daglig-bruk"): "Daglig bruk og rutiner.",
    ("manual", "menyvalg"): "Forklaring av menyvalg.",
    ("manual", "okonomi"): "Økonomi, oppgjør og avstemming.",
    ("manual", "bygg-drift"): "Energi, ventilasjon, lys, dører, renhold og vedlikehold.",
    ("manual", "system"): "Systemkart og teknisk oversikt.",
    ("manual", "datagrunnlag"): "Datakilder og lagring.",
    ("manual", "hc3-energi"): "HC3 energioppsamlinger og målerdekning.",
    ("manual", "rutiner"): "Driftsrutiner og kontrollpunkter.",
    ("manual", "feilsoking"): "Feilsøking og typiske feilbilder.",
    ("admin", "oppgaver"): "Systemoppgaver og forbedringspunkter.",
    ("admin", "kontroll"): "Tverrgående kontrollflater.",
    ("admin", "datakvalitet"): "Dataproblemer på tvers av domener.",
    ("admin", "analyse"): "Tekniske analyser.",
    ("admin", "drift"): "Driftsstatus og systemhelse.",
    ("admin", "build"): "Buildlogg og endringshistorikk.",
    ("admin", "datakilder"): "Importstatus og forklaring per datakilde.",
    ("admin", "systemkart"): "Komponenter, underapper og URL-er.",
    ("admin", "ai"): "AI-innstillinger og AI-logg.",
    ("admin", "teknisk"): "Teknisk drift og verktøy.",
    ("admin", "brukere"): "Brukeradministrasjon.",
    ("admin", "verktoy"): "Tekniske verktøy.",
}


SYSTEM_COMPONENTS = [
    ("fibaro10", "FastAPI/PostgreSQL hovedapp, V2 desktop, API og admin.", "Kritisk", "http://192.168.20.218:8110/"),
    ("online_dashboard", "Ekstern begrenset dashboardflate.", "Høy", "https://online.lilletorget.net/"),
    ("maintenance_mobile", "Mobil registrering av vedlikehold mot samme brukerbase.", "Normal", "https://vedl.lilletorget.net/"),
    ("alarm_mobile", "Mobil alarmstatus for dører, solrom, pullerter og trapp.", "Høy", "https://alarm.lilletorget.net/"),
    ("fibaro10ipad", "iPad-tilpasset dashboardflate.", "Normal", "https://ipad.lilletorget.net/"),
    ("owntracks_service", "HTTP-mottak, waypoints, lokasjoner og besøk.", "Normal", "https://owntracks.lilletorget.net/"),
    ("owntracks_postgres", "PostgreSQL-database for OwnTracks.", "Høy", "intern"),
    ("fibaro10_proxy", "Caddy reverse proxy for eksterne underapper.", "Kritisk", "8081/8443"),
    ("axis_camera_snapshots", "Axis snapshot-arkiv og soltimebilder.", "Høy", "http://192.168.20.218:8125/"),
    ("car_info_lookup", "Svenske og danske kjøretøyoppslag.", "Normal", "http://192.168.20.218:8126/"),
    ("sun2_session_scraper", "SUN2 enkelttimer, senger, medlemmer, produkt og finansgrunnlag.", "Kritisk", "http://192.168.20.218:8099/"),
    ("sun2_importer", "Import av SUN2 dagsfiler/romsummer.", "Lav/verktøy", "http://192.168.20.218:8096/"),
    ("sun2_backfill_downloader", "Historisk SUN2-filnedlasting.", "Lav/verktøy", "http://192.168.20.218:8097/"),
    ("parking_sun_linker", "Bakgrunnsmotor for parkering/SUN2-kobling.", "Høy", "http://192.168.20.218:8127/"),
    ("easypark_downloader", "EasyPark-nedlasting og importtrigger.", "Kritisk", "http://192.168.20.218:8109/status"),
]


DATA_SOURCE_EXPLANATIONS = {
    "hc3_light_5min": "HC3 lysrunner poster lux og lysstyring ca. hvert 5.-7. minutt.",
    "hc3_ventilation_5min": "HC3 ventilasjonsrunner poster temperatur, fukt, viftestyring og styringsmodus.",
    "yr_weather_refresh": "MET/Yr-data lagres sammen med ventilasjon og brukes i vær-/lys-/analyseflater.",
    "hc3_energy_1min": "HC3 logger realtime effekt hvert 30. sekund; health tolererer kort forsinkelse.",
    "roborock_sync": "Roborock-status, historikk, forbruksdeler og kartdata synkes fra Roborock.",
    "sun2_daily_download": "SUN2 dagsfil lastes ned for romstatistikk.",
    "sun2_room_daily_import": "SUN2 dagsfil importeres til rom-/dagsstatistikk.",
    "sun2_sessions_import": "SUN2 enkelttimer skrapes løpende og kobles mot bilder/rom.",
    "sun2_beds_import": "Seng-/rommetadata fra SUN2.",
    "sun2_members_import": "SUN2-medlemsgrunnlag.",
    "sun2_product_sales_daily_import": "Daglig produktsalg fra SUN2.",
    "sun2_product_sales_monthly_import": "Månedskontroll av produktsalg fra SUN2.",
    "sun2_finance_settlement_monthly_import": "Månedlig finans-/oppgjørsgrunnlag fra SUN2.",
    "elvia_monthly_import": "Manuelt importert Elvia månedsfil for energikontroll.",
    "easypark_parking_import": "EasyPark CSV lastes ned via separat downloader og importeres til parkering.",
    "parking_history_import": "Engangs-/arkivmigrering av historiske parkeringer og kjøretøydata.",
    "parking_vehicle_svv_sync": "Statens vegvesen-oppslag for norske kjøretøy.",
    "parking_vehicle_biluppgifter_sync": "Svenske kjøretøyoppslag etter SVV uten treff.",
    "parking_vehicle_tjekbil_sync": "Danske kjøretøyoppslag etter SVV uten treff.",
    "parking_sun_link_worker": "Koblingsmotor som finner sannsynlige bil/SUN2-sammenhenger.",
    "owntracks_site_visits": "OwnTracks-besøk på Lilletorget hentes inn og kobles mot vedlikehold.",
    "hc3_door_events": "HC3 dørhendelser fra block-/Lua-scener per dør.",
    "hc3_door_poll_sync": "Fibaro10 spør HC3 ved uventede dørstatuser for å korrigere stale status.",
}


def register_fonts() -> tuple[str, str]:
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("AppFont", str(regular)))
        pdfmetrics.registerFont(TTFont("AppFont-Bold", str(bold)))
        return "AppFont", "AppFont-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()


def p(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(str(text if text is not None else "").replace("\n", "<br/>"), style)


def clean(text: Any) -> str:
    if text is None:
        return "-"
    value = str(text)
    replacements = {
        "Ã¦": "æ",
        "Ã¸": "ø",
        "Ã¥": "å",
        "Ã†": "Æ",
        "Ã˜": "Ø",
        "Ã…": "Å",
        "Â°C": "°C",
        "nÃ¥": "nå",
        "mÃ¥": "må",
        "fÃ¸r": "før",
        "kjÃ¸": "kjø",
        "vÃ¦": "væ",
        "Ã©": "é",
        "â€“": "-",
        "â€œ": '"',
        "â€": '"',
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    return value


def format_health_time(value: Any) -> str:
    if not value:
        return "-"
    text = clean(value)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    return dt.strftime("%d.%m.%Y %H:%M")


def fetch_health() -> dict[str, Any]:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "unknown", "error": str(exc), "sources": [], "storage": [], "app": {}}


def parse_ts_string_map(content: str, export_name: str) -> dict[str, str]:
    match = re.search(rf"export const {export_name}: Record<string, string> = \{{(.*?)\}};", content, re.S)
    if not match:
        return {}
    out: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip().rstrip(",")
        if not line or ":" not in line:
            continue
        key_text, value_text = line.split(":", 1)
        key_text = key_text.strip().strip('"')
        value_text = value_text.strip()
        if value_text.startswith('"') and value_text.endswith('"'):
            out[key_text] = ast.literal_eval(value_text)
    return out


def parse_module_views() -> tuple[dict[str, str], dict[str, list[dict[str, Any]]]]:
    content = (ROOT / "desktop_v2" / "src" / "moduleViews.ts").read_text(encoding="utf-8")
    labels = parse_ts_string_map(content, "MODULE_LABELS")
    nav_labels = parse_ts_string_map(content, "MODULE_NAVIGATION_LABELS")
    labels.update(nav_labels)

    views: dict[str, list[dict[str, Any]]] = defaultdict(list)
    in_views = False
    current_module: str | None = None
    for raw in content.splitlines():
        line = raw.strip()
        if line.startswith("export const MODULE_VIEWS"):
            in_views = True
            continue
        if not in_views:
            continue
        if line.startswith("};"):
            break
        module_match = re.match(r'(?:"([^"]+)"|([A-Za-z0-9_-]+)):\s*\[', line)
        if module_match:
            current_module = module_match.group(1) or module_match.group(2)
            continue
        if current_module and line.startswith("],"):
            current_module = None
            continue
        if current_module:
            view_match = re.search(r'key:\s*"([^"]+)".*?label:\s*"([^"]+)"(.*)', line)
            if view_match:
                views[current_module].append(
                    {
                        "key": view_match.group(1),
                        "label": view_match.group(2),
                        "hidden": "hidden: true" in view_match.group(3),
                    }
                )
    return labels, dict(views)


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=24,
            leading=29,
            textColor=PRIMARY,
            spaceAfter=8,
            alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=10,
            leading=14,
            textColor=MUTED,
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName=FONT_BOLD,
            fontSize=16,
            leading=20,
            textColor=PRIMARY,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName=FONT_BOLD,
            fontSize=12,
            leading=15,
            textColor=PRIMARY,
            spaceBefore=8,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=8.5,
            leading=11.5,
            textColor=PRIMARY,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=7,
            leading=9,
            textColor=PRIMARY,
        ),
        "smallMuted": ParagraphStyle(
            "SmallMuted",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=7,
            leading=9,
            textColor=MUTED,
        ),
        "tableHead": ParagraphStyle(
            "TableHead",
            parent=base["BodyText"],
            fontName=FONT_BOLD,
            fontSize=7,
            leading=8.5,
            textColor=colors.white,
            alignment=TA_LEFT,
        ),
        "table": ParagraphStyle(
            "Table",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=6.7,
            leading=8.2,
            textColor=PRIMARY,
        ),
        "tableRight": ParagraphStyle(
            "TableRight",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=6.7,
            leading=8.2,
            textColor=PRIMARY,
            alignment=TA_RIGHT,
        ),
        "badge": ParagraphStyle(
            "Badge",
            parent=base["BodyText"],
            fontName=FONT_BOLD,
            fontSize=7,
            leading=8,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
    }


ST = styles()


def table(data: list[list[Any]], widths: list[float], header: bool = True, repeat_rows: int = 1) -> Table:
    converted: list[list[Any]] = []
    for row_index, row in enumerate(data):
        converted_row = []
        for cell in row:
            style = ST["tableHead"] if header and row_index == 0 else ST["table"]
            converted_row.append(cell if isinstance(cell, Flowable) else p(clean(cell), style))
        converted.append(converted_row)
    tbl = Table(converted, colWidths=widths, repeatRows=repeat_rows if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ]
        )
    for idx in range(1 if header else 0, len(data)):
        if idx % 2 == 0:
            commands.append(("BACKGROUND", (0, idx), (-1, idx), SOFT))
    tbl.setStyle(TableStyle(commands))
    return tbl


def bullet_list(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(p(clean(item), ST["body"]), leftIndent=8) for item in items],
        bulletType="bullet",
        start="circle",
        bulletFontName=FONT,
        bulletFontSize=5,
        leftIndent=14,
    )


class SystemMap(Flowable):
    def __init__(self, width: float, height: float = 50 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        self.width = min(self.width, availWidth)
        return self.width, self.height

    def draw_box(self, x, y, w, h, title, detail, color):
        title = clean(title)
        detail = clean(detail)
        self.canv.setStrokeColor(color)
        self.canv.setFillColor(colors.white)
        self.canv.roundRect(x, y, w, h, 5, stroke=1, fill=1)
        self.canv.setFillColor(color)
        self.canv.setFont(FONT_BOLD, 7.5)
        self.canv.drawString(x + 5, y + h - 10.5, title)
        self.canv.setFillColor(PRIMARY)
        self.canv.setFont(FONT, 6)
        for i, line in enumerate(detail.split("|")):
            self.canv.drawString(x + 5, y + h - 20 - (i * 7), line)

    def arrow(self, x1, y1, x2, y2, color=LINE):
        self.canv.setStrokeColor(color)
        self.canv.setLineWidth(1)
        self.canv.line(x1, y1, x2, y2)
        self.canv.setFillColor(color)
        if x2 >= x1:
            points = [(x2, y2), (x2 - 5, y2 + 3), (x2 - 5, y2 - 3)]
        else:
            points = [(x2, y2), (x2 + 5, y2 + 3), (x2 + 5, y2 - 3)]
        pth = self.canv.beginPath()
        pth.moveTo(*points[0])
        pth.lineTo(*points[1])
        pth.lineTo(*points[2])
        pth.close()
        self.canv.drawPath(pth, stroke=0, fill=1)

    def draw(self):
        w = self.width
        col = (w - 28) / 3
        y_top = self.height - 30
        self.draw_box(0, y_top, col, 28, "Eksterne kilder", "EasyPark, SUN2, SVV|Yr, Elvia, Roborock", BLUE)
        self.draw_box(col + 14, y_top, col, 28, "QNAP/Fibaro10", "FastAPI, PostgreSQL|React V2 og API", PRIMARY)
        self.draw_box((col + 14) * 2, y_top, col, 28, "Brukerflater", "Desktop, iPad, mobil|online, vedlikehold", GREEN)
        self.draw_box(0, y_top - 48, col, 28, "HC3", "Energi, lys, ventilasjon|dører og styring", ORANGE)
        self.draw_box(col + 14, y_top - 48, col, 28, "Sideapper", "Axis, Koble, OwnTracks|kjøretøy og SUN2", TEAL)
        self.draw_box((col + 14) * 2, y_top - 48, col, 28, "Kontroll", "Datakilder, buildlogg|manual og systemkart", PURPLE)
        self.draw_box(col + 14, y_top - 96, col, 28, "Backup/arkiv", "Deploy-backup, QNAP backup|Axis og databasedump", RED)
        self.arrow(col, y_top + 14, col + 14, y_top + 14, BLUE)
        self.arrow(col, y_top - 34, col + 14, y_top - 34, ORANGE)
        self.arrow((col + 14) * 2 - 14, y_top + 14, (col + 14) * 2, y_top + 14, GREEN)
        self.arrow((col + 14) * 2 - 14, y_top - 34, (col + 14) * 2, y_top - 34, PURPLE)
        self.arrow(col + 14 + col / 2, y_top - 48, col + 14 + col / 2, y_top - 68, RED)


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 12 * mm, "Fibaro10 komplett oversikt")
    canvas.drawRightString(A4[0] - doc.rightMargin, 12 * mm, f"Side {doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(doc.leftMargin, 16 * mm, A4[0] - doc.rightMargin, 16 * mm)
    canvas.restoreState()


def section(title: str):
    return p(title, ST["h1"])


def subsection(title: str):
    return p(title, ST["h2"])


def module_tables(labels: dict[str, str], views: dict[str, list[dict[str, Any]]]) -> list[Flowable]:
    story: list[Flowable] = []
    ordered_modules = [
        "status",
        "omsetning",
        "parkering",
        "soling",
        "koble",
        "energi",
        "ventilasjon",
        "lys",
        "solrom",
        "solrom-2",
        "dorer2",
        "dorer",
        "vedlikehold",
        "renhold",
        "mobil",
        "ideer",
        "manual",
        "admin",
    ]
    group_names = {
        "status": "Dashboard",
        "omsetning": "Økonomi",
        "parkering": "Økonomi",
        "soling": "Økonomi",
        "koble": "Økonomi",
        "energi": "Bygg og drift",
        "ventilasjon": "Bygg og drift",
        "lys": "Bygg og drift",
        "solrom": "Bygg og drift",
        "solrom-2": "Bygg og drift",
        "dorer2": "Bygg og drift",
        "dorer": "Bygg og drift",
        "vedlikehold": "Bygg og drift",
        "renhold": "Bygg og drift",
        "mobil": "System",
        "ideer": "System",
        "manual": "System",
        "admin": "System",
    }
    overview_rows = [["Gruppe", "Meny", "Hovedformål", "Undersider"]]
    for module in ordered_modules:
        overview_rows.append(
            [
                group_names.get(module, "-"),
                labels.get(module, module),
                MODULE_PURPOSES.get(module, "-"),
                str(len(views.get(module, []))),
            ]
        )
    story.append(table(overview_rows, [28 * mm, 28 * mm, 93 * mm, 20 * mm]))
    story.append(Spacer(1, 8))
    for module in ordered_modules:
        module_views = views.get(module, [])
        if not module_views:
            continue
        rows = [["Underside", "Rute", "Rolle / funksjon"]]
        for view in module_views:
            hidden = " (skjult)" if view.get("hidden") else ""
            route = f"/{module}/{view['key']}"
            rows.append(
                [
                    f"{view['label']}{hidden}",
                    route,
                    VIEW_PURPOSES.get((module, view["key"]), "Funksjon dokumentert i appen, men mangler egen tekst i PDF-generatoren."),
                ]
            )
        story.append(KeepTogether([subsection(labels.get(module, module)), table(rows, [38 * mm, 40 * mm, 91 * mm])]))
        story.append(Spacer(1, 6))
    return story


def data_sources_table(health: dict[str, Any]) -> list[Flowable]:
    sources = health.get("sources") or []
    rows = [["Nr", "Datakilde", "Kategori", "Status", "Sist / neste", "Forklaring"]]
    for item in sources:
        last_next = f"Sist: {clean(item.get('detail'))}"
        if item.get("nextExpectedAt"):
            last_next += f"\nNeste: {format_health_time(item.get('nextExpectedAt'))}"
        rows.append(
            [
                str(item.get("sourceNo", "")),
                clean(item.get("title") or item.get("label") or item.get("jobName")),
                clean(item.get("category")),
                clean(item.get("statusText") or item.get("status")),
                last_next,
                DATA_SOURCE_EXPLANATIONS.get(item.get("jobName"), clean(item.get("message"))),
            ]
        )
    return [table(rows, [9 * mm, 36 * mm, 22 * mm, 17 * mm, 38 * mm, 47 * mm])]


def component_table() -> Table:
    rows = [["Komponent", "Kritikalitet", "URL/port", "Formål"]]
    for name, purpose, criticality, url in SYSTEM_COMPONENTS:
        rows.append([name, criticality, url, purpose])
    return table(rows, [34 * mm, 20 * mm, 39 * mm, 76 * mm])


def storage_table(health: dict[str, Any]) -> Table:
    storage = health.get("storage") or []
    groups: dict[str, list[str]] = defaultdict(list)
    for name in storage:
        prefix = str(name).split("_", 1)[0]
        groups[prefix].append(name)
    rows = [["Område", "Tabeller"]]
    for prefix in sorted(groups):
        rows.append([prefix, ", ".join(sorted(groups[prefix]))])
    return table(rows, [27 * mm, 142 * mm])


def build_story() -> list[Flowable]:
    labels, views = parse_module_views()
    health = fetch_health()
    app = health.get("app") or {}
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    source_summary = health.get("summary", {}).get("sources", {})

    story: list[Flowable] = []
    story.append(p("Fibaro10 - komplett oversikt", ST["title"]))
    story.append(
        p(
            f"Generert {generated_at}. Live Fibaro10: build {app.get('build', '-')}, commit {app.get('commit', '-')}, "
            f"status {health.get('status', '-')}. Datakilder: {source_summary.get('ok', 0)}/{source_summary.get('total', len(health.get('sources', [])))} OK.",
            ST["subtitle"],
        )
    )
    story.append(SystemMap(169 * mm))
    story.append(Spacer(1, 8))
    story.append(section("1. Sammendrag"))
    story.append(
        bullet_list(
            [
                "Fibaro10 er hovedsystemet for daglig drift, økonomi, parkering, soling, bygg/teknikk og admin.",
                "Hovedappen består av FastAPI, PostgreSQL, React/TypeScript V2 og flere separate QNAP-sideapper.",
                "Admin > Datakilder er operativ fasit for importstatus, siste kjøring, neste forventede kjøring og feilmeldinger.",
                "Underapper holdes separate der det gir stabilitet: OwnTracks, vedlikehold mobil, iPad, Axis, kjøretøyoppslag, EasyPark og Koble worker.",
                "Alle faste hovedruter blir testet i live-smoke ved deploy.",
            ]
        )
    )
    story.append(Spacer(1, 8))
    story.append(section("2. Hovedmeny og alle funksjoner"))
    story.extend(module_tables(labels, views))
    story.append(PageBreak())
    story.append(section("3. Datakilder"))
    story.append(
        p(
            "Tabellen under er hentet fra live /health?details=true ved generering. Den viser alle datakilder som Fibaro10 selv overvåker.",
            ST["body"],
        )
    )
    story.extend(data_sources_table(health))
    story.append(PageBreak())
    story.append(section("4. Systemkomponenter og webflater"))
    story.append(component_table())
    story.append(Spacer(1, 8))
    story.append(section("5. Lagring"))
    story.append(
        p(
            "Listen under er tabellene Fibaro10 rapporterer fra health-endepunktet. OwnTracks har i tillegg egen PostgreSQL-database.",
            ST["body"],
        )
    )
    story.append(storage_table(health))
    story.append(PageBreak())
    story.append(section("6. Viktige drifts- og kontrollprinsipper"))
    story.append(
        bullet_list(
            [
                "Deploy skal gå via scripts/deploy-qnap.ps1. Den kjører tester, frontend-build, backup, container-rebuild, health og live-smoke.",
                "HC3 poster lys, ventilasjon, energi og dørhendelser inn i Fibaro10. Fibaro10 leser også HC3 direkte ved noen kontrollbehov.",
                "Energi bruker realtime W som primært grunnlag; akkumulert kWh brukes som kontroll der det finnes.",
                "Parkering oppdateres via EasyPark CSV og etterfølgende prognose/kjøretøyoppslag.",
                "Soling oppdateres fra SUN2 enkelttimer, dagsfiler, produkter, medlemmer og oppgjør.",
                "Oppgjør kontrolleres mot interne summer, ikke omvendt. Avvik skal være synlige.",
                "Dør- og solromsfunksjoner bruker HC3-dørhendelser, SUN2-soltimer og energimarkører for å tolke bruk.",
                "Vedlikehold kobles til Lilletorget-besøk fra OwnTracks der det finnes relevante besøk.",
            ]
        )
    )
    story.append(Spacer(1, 8))
    story.append(section("7. Nøkkelfiler"))
    story.append(
        table(
            [
                ["Fil", "Rolle"],
                ["main.py", "FastAPI-app, datamodeller, API, ingest og HTML-fallbackruter."],
                ["desktop_v2/src/moduleViews.ts", "Menystruktur og undersider for V2."],
                ["desktop_v2/src/AppRoutes.tsx", "React-ruter og spesialruter."],
                ["scripts/hc3_ventilation_runner_scene_363.lua", "Aktiv HC3-ventilasjonsstyring."],
                ["scripts/hc3_light_runner_scene_362.lua", "Aktiv HC3-utelysstyring."],
                ["scripts/hc3_energy_logger.lua", "HC3 energilogging til Fibaro10."],
                ["docker-compose.qnap.yml", "QNAP-tjenester for hovedsystem og sideapper."],
                ["Caddyfile", "Ekstern reverse proxy for online, owntracks, vedlikehold og iPad."],
                ["docs/", "Driftsdokumentasjon, systemoversikt, funksjonsstruktur og manualgrunnlag."],
            ],
            [55 * mm, 114 * mm],
        )
    )
    return story


def build_pdf() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT_FILE),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=20 * mm,
        title="Fibaro10 komplett oversikt",
        author="Fibaro10 / Codex",
    )
    doc.build(build_story(), onFirstPage=header_footer, onLaterPages=header_footer)
    return OUTPUT_FILE


if __name__ == "__main__":
    print(build_pdf())
