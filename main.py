from datetime import date, datetime, time, timedelta
from email.utils import parsedate_to_datetime
from io import StringIO
from copy import deepcopy
from collections import defaultdict
from functools import lru_cache
from statistics import median
from types import SimpleNamespace
from typing import Any, Dict, Optional
import asyncio
import calendar
import csv
import hashlib
import json
import math
import os
import re
from urllib.parse import parse_qs, quote, quote_plus, urlencode, urlparse
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, BigInteger, Column, Date, DateTime, Float, Integer, JSON, String, Text, UniqueConstraint, and_, case, cast, delete, func, or_, select, text as sql_text, tuple_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from dateutil import parser as dtparser

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
LOCAL_TZ = ZoneInfo("Europe/Oslo")
SUN2_SESSIONS_QUIET_START_HOUR = 0
SUN2_SESSIONS_QUIET_END_HOUR = 7
MASTER_ACCESS_KEY_HASH = os.getenv(
    "MASTER_ACCESS_KEY_HASH",
    "752ede847bd180ef3d2700d117d297ced1b25664b946a3639fb7a3b2be93d5d1",
)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
AUTH_USER_COOKIE_NAME = "fibaro10_access_username"
AUTH_COOKIE_NAME = "fibaro10_access_password"
ACCESS_FAILED_DISABLE_THRESHOLD = max(1, int(os.getenv("ACCESS_FAILED_DISABLE_THRESHOLD", "3")))
PUBLIC_PREFIXES = ("/static/",)
PUBLIC_PATHS = {"/health", "/favicon.ico", "/auth/login"}


def env_float(name: str, default: str) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return float(default)


MET_LAT = env_float("MET_LAT", "61.1153")
MET_LON = env_float("MET_LON", "10.4662")
MET_USER_AGENT = os.getenv("MET_USER_AGENT", "fibaro10/1.0 http://192.168.20.218:8110")
MET_WEATHER_CACHE = {"expires": datetime.min, "value": None}
SUMMARY_CACHE_TTL = timedelta(minutes=5)
SUMMARY_CACHE: Dict[str, Dict[str, Any]] = {}
NTFY_BASE_URL = os.getenv("NTFY_BASE_URL", "https://ntfy.sh").rstrip("/")
NTFY_LIGHTS_TOPIC = os.getenv("NTFY_LIGHTS_TOPIC", f"sun2-lys-{MASTER_ACCESS_KEY_HASH[:12]}")
NTFY_VENTILATION_TOPIC = os.getenv("NTFY_VENTILATION_TOPIC", f"sun2-ventilasjon-{MASTER_ACCESS_KEY_HASH[:12]}")
NTFY_ACCESS_TOPIC = os.getenv("NTFY_ACCESS_TOPIC", f"sun2-tilgang-{MASTER_ACCESS_KEY_HASH[:12]}")
SVV_API_KEY = os.getenv("SVV_API_KEY", "").strip()
SVV_API_URL = os.getenv(
    "SVV_API_URL",
    "https://www.vegvesen.no/ws/no/vegvesen/kjoretoy/felles/datautlevering/enkeltoppslag/kjoretoydata",
).strip()
SVV_API_AUTH_HEADER = os.getenv("SVV_API_AUTH_HEADER", "SVV-Authorization").strip()
SVV_API_AUTH_PREFIX = os.getenv("SVV_API_AUTH_PREFIX", "Apikey").strip()
SVV_SYNC_ENABLED = os.getenv("SVV_SYNC_ENABLED", "true").strip().lower() in {"1", "true", "yes", "ja"}
SVV_SYNC_INTERVAL_MINUTES = max(1, int(os.getenv("SVV_SYNC_INTERVAL_MINUTES", "10")))
SVV_SYNC_BATCH_SIZE = max(1, int(os.getenv("SVV_SYNC_BATCH_SIZE", "50")))
SVV_IMPORT_SYNC_BATCH_SIZE = max(0, int(os.getenv("SVV_IMPORT_SYNC_BATCH_SIZE", "5")))
SVV_RETRY_AFTER_HOURS = max(1, int(os.getenv("SVV_RETRY_AFTER_HOURS", "24")))
SVV_TRANSIENT_RETRY_AFTER_MINUTES = max(5, int(os.getenv("SVV_TRANSIENT_RETRY_AFTER_MINUTES", "30")))
SVV_PERMANENT_NO_DATA_STATUSES = {204, 400, 404}
SVV_TRANSIENT_STATUSES = {429, 500, 502, 503, 504}
svv_sync_task: Optional[asyncio.Task] = None
NTFY_TIMEOUT_SECONDS = env_float("NTFY_TIMEOUT_SECONDS", "4")
NTFY_ACCESS_COOLDOWN_MINUTES = env_float("NTFY_ACCESS_COOLDOWN_MINUTES", "30")
EASYPARK_DOWNLOADER_URL = os.getenv("EASYPARK_DOWNLOADER_URL", "http://127.0.0.1:8109").rstrip("/")
APP_VERSION = os.getenv("APP_VERSION", "1")
APP_BUILD = os.getenv("APP_BUILD", "1041")
BUILD_LOG = [
    {
        "version": "1",
        "build": "1041",
        "date": "08.06.2026",
        "title": "Oppdaterer HC3 energioppsamling",
        "changes": [
            "Tilpasser beregnet energidifferanse etter at avfukter inngaar i Annet-oppsamlingen.",
            "Beholder avfukter som separat logget felt, men trekker den ikke dobbelt i differanseberegningen.",
        ],
    },
    {
        "version": "1",
        "build": "1040",
        "date": "08.06.2026",
        "title": "Lagrer komplett Yr-datagrunnlag",
        "changes": [
            "Logger flere strukturerte analysefelt fra komplett MET/Yr-varsel.",
            "Lagrer full MET/Yr-respons med HTTP-headere som raw JSON for senere analyser.",
            "Oppdaterer eksisterende Yr-rad med komplett datagrunnlag naar samme varsel allerede finnes.",
        ],
    },
    {
        "version": "1",
        "build": "1039",
        "date": "08.06.2026",
        "title": "Henter komplett Yr-varsel",
        "changes": [
            "Bytter Yr/MET-henting fra compact til complete for å få vindkast og nedbørsannsynlighet.",
            "Lar de nye analysefeltene fylles når MET leverer dem.",
        ],
    },
    {
        "version": "1",
        "build": "1038",
        "date": "08.06.2026",
        "title": "Utvider Yr-logging",
        "changes": [
            "Logger vindkast fra Yr/MET når feltet leveres.",
            "Logger nedbørsannsynlighet neste 1 og 6 timer når feltet leveres.",
            "Oppdaterer eksisterende Yr-rad med nye felter når samme varsel allerede er lagret.",
        ],
    },
    {
        "version": "1",
        "build": "1037",
        "date": "08.06.2026",
        "title": "Strammer mobilvisning",
        "changes": [
            "Gjør viftestatus mer kompakt på mobil i temp-loggen.",
            "Reduserer høyden på hvert målekort uten å fjerne statusinformasjon.",
        ],
    },
    {
        "version": "1",
        "build": "1036",
        "date": "08.06.2026",
        "title": "Rydder temp-loggdesign",
        "changes": [
            "Gjør temp-loggen mer kompakt med roligere kort og tydeligere seksjoner.",
            "Gir Inne-seksjonen mer plass på desktop og bedre flyt på mobil.",
            "Forenkler header, viftestatus og målefelt visuelt.",
        ],
    },
    {
        "version": "1",
        "build": "1035",
        "date": "08.06.2026",
        "title": "Forenkler temp-oversikt",
        "changes": [
            "Fjerner Styring fra Ute-seksjonen i temp-loggen.",
            "Fjerner estimert solsengverdi fra Inne-seksjonen.",
        ],
    },
    {
        "version": "1",
        "build": "1034",
        "date": "08.06.2026",
        "title": "Tydeliggjør uteverdier",
        "changes": [
            "Endrer Ute-seksjonen i temp-loggen til Styring, Netatmo og Yr.",
            "Flytter Netatmo-fukt til Netatmo-raden.",
        ],
    },
    {
        "version": "1",
        "build": "1033",
        "date": "08.06.2026",
        "title": "Forenkler temp logg",
        "changes": [
            "Fjerner Diff og Kilde fra temp-loggens visning.",
            "Beholder temperatur og fukt i Ventilasjon-gruppen.",
        ],
    },
    {
        "version": "1",
        "build": "1032",
        "date": "08.06.2026",
        "title": "Justerer temp logg-grupper",
        "changes": [
            "Samler loft og innluft i en egen Ventilasjon-gruppe.",
            "Legger uteverdier og Yr i en egen Ute-gruppe.",
            "Legger kjellerverdier i en egen Kjeller-gruppe.",
        ],
    },
    {
        "version": "1",
        "build": "1031",
        "date": "08.06.2026",
        "title": "Rydder temp logg",
        "changes": [
            "Deler temp loggen inn i gruppene Inne, Ute og loft, og Teknisk.",
            "Viser temperatur og fukt samlet per sone for raskere lesing.",
            "Beholder viftestatus, modus og regelhjelp øverst i hver måling.",
        ],
    },
    {
        "version": "1",
        "build": "1030",
        "date": "08.06.2026",
        "title": "Logger fukt i ventilasjon",
        "changes": [
            "Logger fukt for 1.etg, 2.etg, VIP, ute, Yr, loft, luftinntak og kjeller.",
            "Viser fuktverdier i ventilasjonsloggene og online-dashboardet.",
            "Oppdaterer HC3 ventilasjonsrunner scene 363 med fuktsensorene.",
        ],
    },
    {
        "version": "1",
        "build": "1029",
        "date": "08.06.2026",
        "title": "Legger inn kjeller og avfukter",
        "changes": [
            "Logger temperatur og fukt fra kjeller i ventilasjonsloggen.",
            "Legger avfukter inn som styrbar klimaenhet.",
            "Logger avfukterens effekt og kWh i HC3 energiloggen.",
        ],
    },
    {
        "version": "1",
        "build": "1028",
        "date": "06.06.2026",
        "title": "Retter HC3 målerlogging",
        "changes": [
            "Gjør rådata fra HC3 måleravlesninger JSON-sikre slik at timestamp ikke stopper lagring.",
        ],
    },
    {
        "version": "1",
        "build": "1027",
        "date": "05.06.2026",
        "title": "Teller pågående parkeringer",
        "changes": [
            "Viser antall pågående parkeringer direkte i overskriften på Parkering/Oversikt.",
        ],
    },
    {
        "version": "1",
        "build": "1026",
        "date": "31.05.2026",
        "title": "Dato i kjøretøytabell",
        "changes": [
            "Endrer Parkering/Kjøretøy slik at først sett og sist sett viser både dato og klokkeslett.",
            "Legger inn eget kort datoformat for historikkfelt som ikke bare skal vise klokkeslett.",
        ],
    },
    {
        "version": "1",
        "build": "1025",
        "date": "31.05.2026",
        "title": "Deler temperaturkort",
        "changes": [
            "Splitter temperaturfeltet i online-dashboardet i to kort: Inne og Ute.",
            "Inne-kortet viser snittet stort med 1.etg, 2.etg og VIP som underverdier.",
            "Ute-kortet viser beregnet utetemperatur stort med Ute, Innluft og Yr som underverdier.",
        ],
    },
    {
        "version": "1",
        "build": "1024",
        "date": "31.05.2026",
        "title": "Retter klikkbare mobilkort",
        "changes": [
            "Retter klikkbare kort i online-dashboardet slik at seksjonene Lys og Ventilasjon ikke fragmenteres som inline-elementer.",
            "Fjerner de hvite restflatene som kunne vises rett over Lys, rett under Ventilasjon og nederst på mobilforsiden.",
            "Beholder den kompakte mobile forsiden og rydder CSS-regelen slik at kortlenker oppfører seg likt.",
        ],
    },
    {
        "version": "1",
        "build": "1023",
        "date": "31.05.2026",
        "title": "Mobil overflow-fiks",
        "changes": [
            "Retter online-dashboardet slik at temperaturkort, lyskort og ventilasjonskort ikke kan presse siden bredere enn mobilskjermen.",
            "Gjør temperaturkortet mer kompakt på smal skjerm og lar ekstra temperaturverdier bryte til to kolonner.",
            "Legger inn tydelige overflow-vakter i mobil-CSS-en uten å endre den enkle forsidemodellen.",
        ],
    },
    {
        "version": "1",
        "build": "1022",
        "date": "31.05.2026",
        "title": "Enklere mobilforside",
        "changes": [
            "Forenkler forsiden i online-dashboardet slik at soling og parkering viser i dag/i går kompakt med skråstrek.",
            "Flytter detaljer som beløp, siste hendelser, uke og måned til undersidene.",
            "Reduserer høyden på hovedkortene for et raskere mobiloverblikk.",
        ],
    },
    {
        "version": "1",
        "build": "1021",
        "date": "31.05.2026",
        "title": "Mobilapp med detaljsider",
        "changes": [
            "Gjør logoen i online-dashboardet til fast vei tilbake til forsiden.",
            "Legger inn ett-nivå detaljsider for soling, parkering, energi, temperatur, lys og ventilasjon.",
            "Gjør aktuelle kort klikkbare og legger en tilgangsstyrt EasyPark-oppdatering på parkeringsdetaljen.",
        ],
    },
    {
        "version": "1",
        "build": "1020",
        "date": "31.05.2026",
        "title": "Rikere mobilapp",
        "changes": [
            "Utvider online-dashboardet med åpningstid, strøm akkurat nå og forbruk hittil i dag.",
            "Legger inn sammenligning mot i går for soling og parkering, samt siste registrerte soling og parkering.",
            "Legger inn kompakte uke- og månedstall for soling og parkering i den offentlige mobilvisningen.",
        ],
    },
    {
        "version": "1",
        "build": "1019",
        "date": "31.05.2026",
        "title": "Ryddigere energioversikter",
        "changes": [
            "Rydder opp i grensesnittet for Energi > Kurser og Energi > Laster.",
            "Gjør handlingsknapper, filter, PDF-uttak og registrering mer samlet og mindre støyende.",
            "Legger registrering av ny last i et sammenleggbart panel slik at oversikten er lettere å bruke til daglig.",
        ],
    },
    {
        "version": "1",
        "build": "1018",
        "date": "31.05.2026",
        "title": "PDF-eksport for energi",
        "changes": [
            "Legger inn PDF-uttak for kursliste og lastregister under Energi.",
            "PDF-ene lages direkte i appen uten ekstra avhengigheter og deles automatisk over flere sider.",
        ],
    },
    {
        "version": "1",
        "build": "1017",
        "date": "31.05.2026",
        "title": "Redigerbar kursliste",
        "changes": [
            "Legger inn edit-modus pa Energi > Kurser slik at kursbeskrivelse, vern, kabel, JFB, status og notat kan endres direkte i grensesnittet.",
            "Lagring skjer per kursrad slik at tavledokumentasjonen kan holdes levende uten ny Excel-import.",
        ],
    },
    {
        "version": "1",
        "build": "1016",
        "date": "31.05.2026",
        "title": "Energi kurs og laster",
        "changes": [
            "Legger inn egne datatabeller for elektriske kurser og praktiske laster under Energi.",
            "Seeder kursliste 37 som tavledokumentasjon uten a overskrive senere endringer.",
            "Legger inn sider for kursliste og lastregister med kobling mot kurs, Fibaro-id, Z-Wave-id og forventet effekt.",
        ],
    },
    {
        "version": "1",
        "build": "1015",
        "date": "31.05.2026",
        "title": "Bedre prognosemodell",
        "changes": [
            "Retter dagsprognoser slik at soling ikke straffes for manglende natt- og for-apning-data.",
            "Endrer maneds- og arsprognose slik at dagens tempo sammenlignes med forventet aktivitet hittil, ikke hele dagen.",
            "Fjerner dobbel nedjustering av resterende del av innevarende dag i prognosegrunnlaget.",
        ],
    },
    {
        "version": "1",
        "build": "1014",
        "date": "30.05.2026",
        "title": "CSS-gjennomgang",
        "changes": [
            "Rydder ansvarsdelingen mellom app.css, Lilletorget designsystem og fast venstremeny.",
            "Reduserer app.css til tokens, baseoppsett og få sidespesifikke regler slik at komponenter ikke defineres dobbelt.",
            "Oppdaterer CSS-cache for å sikre at QNAP-løsningen laster den ryddede stilstrukturen.",
        ],
    },
    {
        "version": "1",
        "build": "1013",
        "date": "30.05.2026",
        "title": "Retter norske tegn",
        "changes": [
            "Retter feil kodede norske tegn i parkeringsprognose og dashboardkort.",
            "Retter ukedagsnavn og års-/månedsoverskrifter som kunne vises som mojibake.",
            "Retter tegn i små SUN2-statusapper slik at På og går vises riktig.",
        ],
    },
    {
        "version": "1",
        "build": "1012",
        "date": "30.05.2026",
        "title": "Oppdatert dokumentasjon",
        "changes": [
            "Skriver sluttbrukermanualen på nytt med ryddig kapittelinndeling, korrekt norsk tegnsett og oppdatert forklaring av alle hovedområder.",
            "Skriver teknisk manual på nytt med QNAP-produksjon, intern hovedapp, offentlig online-dashboard, containere, porter, dataflyt, API, database, sikkerhet og feilsøking.",
            "Dokumenterer skillet mellom full intern Fibaro10-app og separat offentlig nøkkeltall-app for mobil.",
            "Legger inn tydeligere driftsrutiner for parkering, soling, lys, ventilasjon, energi, renhold og datakilder.",
        ],
    },
    {
        "version": "1",
        "build": "1011",
        "date": "30.05.2026",
        "title": "Kontrollert fargeløft",
        "changes": [
            "Legger inn et samlet fargelag i designsystemet med svake aksentflater per hovedområde.",
            "Gir kort, paneler, tabellhoder og statusmerker mer visuell retning uten å endre layout.",
            "Beholder grønn/rød statuslogikk for på/av og ok/feil slik at driftssignaler fortsatt er tydelige.",
            "Oppdaterer CSS-cache slik at QNAP-løsningen laster det nye uttrykket med en gang.",
        ],
    },
    {
        "version": "1",
        "build": "1010",
        "date": "30.05.2026",
        "title": "Design- og CSS-opprydding",
        "changes": [
            "Rydder app.css ned til rene grunnvariabler, temafarger og felles komponentregler.",
            "Gjør owner-nav.css til eneste kilde for fast venstremeny og gjør menyen mer kompakt.",
            "Fjerner gamle overlappende mobil- og layoutregler fra app.css som kunne gi ulik bredde mellom sider.",
            "Oppdaterer CSS-cache slik at QNAP-løsningen laster det nye designlaget umiddelbart.",
            "Beholder buildloggen som fast historikk for synlige endringer i løsningen.",
        ],
    },
    {
        "version": "1",
        "build": "1009",
        "date": "30.05.2026",
        "title": "SVV og statusstatistikk",
        "changes": [
            "Gjør SVV-berikelsen mer robust ved midlertidige feil fra Statens vegvesen.",
            "Stopper SVV-batchen etter første 429/500/502/503/504 slik at mange biler ikke feilmerkes når tjenesten er nede.",
            "Viser tydelig statusmelding når kjøretøy venter på ny SVV-prøve etter midlertidig feil.",
            "Endrer Status/Statistikk slik at grafen bare viser samlet beløp for soling og parkering.",
            "Legger inn valg mellom ukevis beløp og akkumulert årskurve på Status/Statistikk.",
        ],
    },
    {
        "version": "1",
        "build": "1008",
        "date": "29.05.2026",
        "title": "CSS-opprydding",
        "changes": [
            "Fjerner gamle overlappende designlag fra app.css slik at Lilletorget-systemet styrer farger, kort, knapper og typografi.",
            "Flytter nødvendige kompatibilitetsregler for parkering, filtre og klikkbare merker til felles designsystem.",
            "Oppdaterer CSS-cache slik at QNAP-løsningen laster den ryddede stilen uten gammel nettlesercache.",
        ],
    },
    {
        "version": "1",
        "build": "1007",
        "date": "29.05.2026",
        "title": "Teknisk driftsside",
        "changes": [
            "Bygger om teknisk side til en samlet driftsoversikt for hovedapp, online-dashboard, QNAP, HC3 og lokale loggerapper.",
            "Legger inn vedlikeholdslenker til de viktigste sidene for status, parkering, soling, lys, ventilasjon, energi, renhold og AI.",
            "Dokumenterer containere, porter, dataflyt, driftsrutiner, API-endepunkter, feilsøking og hva som bør beholdes eller kan arkiveres.",
        ],
    },
    {
        "version": "1",
        "build": "1006",
        "date": "29.05.2026",
        "title": "Lik sidestart",
        "changes": [
            "Gjør toppfelt på dashboard, soling, lys, ventilasjon og konto til samme høyde, plassering og typestørrelse.",
            "Legger inn manglende sidetopper på logg- og innstillingssider slik at de starter likt.",
            "Oppdaterer CSS-cache for å sikre at den ryddede toppstilen brukes i QNAP-løsningen.",
        ],
    },
    {
        "version": "1",
        "build": "1005",
        "date": "29.05.2026",
        "title": "Presise sidetopper",
        "changes": [
            "Strammer sidetoppene til fast plassering, fast tittelst\u00f8rrelse og lik venstrejustering.",
            "Skiller direkte h1-sidetopper fra toppfelt med handlinger, slik at de f\u00e5r samme visuelle geometri.",
            "Oppdaterer CSS-cache slik at den nye toppstilen lastes p\u00e5 alle sider.",
        ],
    },
    {
        "version": "1",
        "build": "1004",
        "date": "29.05.2026",
        "title": "Felles sidetopper",
        "changes": [
            "Innf\u00f8rer et felles system for overskrifter, hjelpetekster og topphandlinger p\u00e5 sidene.",
            "Legger til manglende sidetopper p\u00e5 status-dagslinje, lyslogg og ventilasjonslogg.",
            "Rydder fontst\u00f8rrelser og avstand i toppfelt slik at sidene starter mer likt.",
        ],
    },
    {
        "version": "1",
        "build": "1003",
        "date": "29.05.2026",
        "title": "Retter tegnsett i buildlogg",
        "changes": [
            "Rydder buildloggen slik at norske tegn vises riktig.",
            "Ingen funksjonell endring i prognoser eller \u00f8vrige sider.",
        ],
    },
    {
        "version": "1",
        "build": "1002",
        "date": "29.05.2026",
        "title": "Lagrede prognoser",
        "changes": [
            "Legger til knapp for \u00e5 lagre prognose p\u00e5 b\u00e5de Soling/Prognose og Parkering/Prognose.",
            "Hver lagring tar vare p\u00e5 dag-, m\u00e5neds- og \u00e5rsprognosen slik den s\u00e5 ut akkurat da.",
            "Prognosesidene viser en tabell med lagrede prognoser og faktisk utvikling s\u00e5 langt.",
            "Avvik vises for antall og kroner slik at vi kan se hvor godt modellen treffer over tid.",
        ],
    },
    {
        "version": "1",
        "build": "1001",
        "date": "29.05.2026",
        "title": "Parkering prognose",
        "changes": [
            "Legger til egen prognoseside for parkering under Parkering.",
            "Prognosen beregner forventet antall parkeringer, inntekt og varighet for dag, måned og år.",
            "Modellen bruker historikk, ukedag, sesong, helligdager og tempo hittil i perioden.",
            "Parkering-menyen har fått nytt valg for prognose.",
        ],
    },
    {
        "version": "1",
        "build": "1000",
        "date": "29.05.2026",
        "title": "Første nummererte build",
        "changes": [
            "Innfører fast versjonsnummer og buildnummer i menyen.",
            "Buildnummeret er klikkbart og åpner denne buildloggen.",
            "Mobilappen logger nå innlogging, refresh og avviste innlogginger som brukeraktivitet.",
            "Parkering/Område viser både andel unike biler og andel parkeringer, uten grafisk stolpefelt.",
            "Dette er startpunktet for videre bygglogg: fremtidige endringer legges inn her med nytt buildnummer.",
        ],
    }
]

app = FastAPI(title="Fibaro10")
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.globals.update(app_version=APP_VERSION, app_build=APP_BUILD, build_log=BUILD_LOG)


def format_local_datetime(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    if isinstance(value, (int, float)):
        value = datetime.utcfromtimestamp(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(LOCAL_TZ).strftime("%d.%m.%Y %H:%M:%S")


def format_local_time(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    if isinstance(value, (int, float)):
        value = datetime.utcfromtimestamp(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(LOCAL_TZ).strftime("%H:%M")


def format_source_datetime(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value)
    if value.tzinfo is not None:
        value = value.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return value.strftime("%d.%m.%Y %H:%M:%S")


def format_source_time(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value)
    if value.tzinfo is not None:
        value = value.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return value.strftime("%H:%M")


def format_source_datetime_short(value: Optional[datetime]) -> str:
    if not value:
        return "-"
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value)
    if value.tzinfo is not None:
        value = value.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return value.strftime("%d.%m.%Y %H:%M")


templates.env.filters["localtime"] = format_local_datetime
templates.env.filters["localtime_short"] = format_local_time
templates.env.filters["source_time"] = format_source_datetime
templates.env.filters["source_time_short"] = format_source_time
templates.env.filters["source_datetime_short"] = format_source_datetime_short


ROBOROCK_STATE_LABELS = {
    1: "Starter opp",
    2: "Venter",
    3: "Hviler",
    4: "Klar",
    5: "Fjernstyring",
    6: "Rengjør",
    7: "Returnerer til dock",
    8: "Lader",
    9: "Ladefeil",
    10: "Pause",
    11: "Flekkrengjøring",
    12: "Feil",
    13: "Slår av",
    14: "Oppdaterer",
    15: "Dokker",
    16: "Går til målpunkt",
    17: "Sonerengjøring",
    18: "Romrengjøring",
    22: "Tømmer støvbeholder",
    23: "Vasker mopp",
    26: "Går til moppvask",
    28: "Kartlegger",
}

ROBOROCK_ERROR_LABELS = {
    0: "Ingen feil",
    1: "Laser/sensor-feil",
    2: "Støtfanger sitter fast",
    3: "Hjul henger",
    4: "Kantsensor må rengjøres",
    5: "Hovedbørste sitter fast",
    6: "Sidebørste sitter fast",
    7: "Hjul sitter fast",
    8: "Robot sitter fast",
    9: "Støvbeholder mangler",
    10: "Filter blokkert eller vått",
    11: "Magnetstripe/no-go oppdaget",
    12: "Lavt batteri",
    13: "Ladefeil",
    14: "Batterifeil",
    15: "Vegg-/avstandssensor må rengjøres",
    16: "Robot står skjevt",
    17: "Sidebørstemodul-feil",
    18: "Viftefeil",
    21: "Vertikal støtfanger trykket inn",
    22: "Dock-posisjonsfeil",
    23: "Dock-lokalisering mislyktes",
    24: "No-go-sone eller usynlig vegg",
    26: "Vannfilter må rengjøres",
}

ROBOROCK_FAN_LABELS = {
    101: "Stille",
    102: "Balansert",
    103: "Turbo",
    104: "Maks",
    105: "Maks+",
}

ROBOROCK_MOP_LABELS = {
    300: "Standard",
    301: "Lav",
    302: "Medium",
    303: "Høy",
}

ROBOROCK_WATER_LABELS = {
    200: "Av",
    201: "Lav",
    202: "Medium",
    203: "Høy",
}

ROBOROCK_CHARGE_LABELS = {
    0: "Ikke på lader",
    1: "På lader",
    2: "Lader",
}

ROBOROCK_DAYS = {
    "0": "søn",
    "1": "man",
    "2": "tir",
    "3": "ons",
    "4": "tor",
    "5": "fre",
    "6": "lør",
    "7": "søn",
    "SUN": "søn",
    "MON": "man",
    "TUE": "tir",
    "WED": "ons",
    "THU": "tor",
    "FRI": "fre",
    "SAT": "lør",
}


def roborock_label(mapping: Dict[int, str], value: Any, fallback_prefix: str = "Kode") -> str:
    number = int_value(value)
    if number is None:
        return "-"
    return mapping.get(number, f"{fallback_prefix} {number}")


def roborock_state_label(value: Any) -> str:
    return roborock_label(ROBOROCK_STATE_LABELS, value, "Statuskode")


def roborock_error_label(value: Any) -> str:
    return roborock_label(ROBOROCK_ERROR_LABELS, value, "Feilkode")


def roborock_fan_label(value: Any) -> str:
    return roborock_label(ROBOROCK_FAN_LABELS, value, "Nivå")


def roborock_mop_label(value: Any) -> str:
    return roborock_label(ROBOROCK_MOP_LABELS, value, "Nivå")


def roborock_water_label(value: Any) -> str:
    return roborock_label(ROBOROCK_WATER_LABELS, value, "Nivå")


def roborock_charge_label(value: Any) -> str:
    return roborock_label(ROBOROCK_CHARGE_LABELS, value, "Ladestatus")


def roborock_signal_label(value: Any) -> str:
    rssi = int_value(value)
    if rssi is None:
        return "-"
    if rssi >= -55:
        quality = "svært bra"
    elif rssi >= -67:
        quality = "bra"
    elif rssi >= -75:
        quality = "svak"
    else:
        quality = "dårlig"
    return f"{quality} ({rssi} dBm)"


def roborock_bool_label(value: Any) -> str:
    if value is None:
        return "-"
    return "Ja" if bool_value(value) else "Nei"


def format_seconds_as_hours(value: Any) -> str:
    seconds = int_value(value)
    if seconds is None:
        return "-"
    hours = seconds / 3600
    if hours < 1:
        return f"{round(seconds / 60)} min"
    return f"{hours:.1f} t"


def roborock_cron_parts(cron: Optional[str]) -> Optional[tuple[int, int, str]]:
    if not cron:
        return None
    parts = cron.split()
    if len(parts) < 5:
        return None
    minute = int_value(parts[0])
    hour = int_value(parts[1])
    if minute is None or hour is None:
        return None
    return minute, hour, parts[4]


def roborock_schedule_minutes(schedule: Any) -> int:
    parts = roborock_cron_parts(getattr(schedule, "cron", None))
    if not parts:
        return 24 * 60 + 1
    minute, hour, _ = parts
    return hour * 60 + minute


def roborock_next_schedule_score(schedule: Any) -> int:
    minutes = roborock_schedule_minutes(schedule)
    if minutes > 24 * 60:
        return minutes
    now = datetime.now(LOCAL_TZ)
    now_minutes = now.hour * 60 + now.minute
    return minutes - now_minutes if minutes >= now_minutes else minutes + (24 * 60 - now_minutes)


def roborock_schedule_text(schedule: Any) -> str:
    cron = getattr(schedule, "cron", None)
    parts = roborock_cron_parts(cron)
    if not parts:
        return cron or "-"
    minute, hour, day_field = parts
    time_text = f"{hour:02d}:{minute:02d}"
    if day_field in {"*", "?", ""}:
        return f"Hver dag kl. {time_text}"
    days = [ROBOROCK_DAYS.get(day.strip().upper(), day.strip()) for day in day_field.split(",") if day.strip()]
    if days:
        return f"{', '.join(days)} kl. {time_text}"
    return f"Kl. {time_text}"


def roborock_rounds_label(value: Any) -> str:
    number = int_value(value)
    if number is None:
        return "-"
    return f"{number} runde" if number == 1 else f"{number} runder"


def roborock_json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, indent=2, default=str)


def json_safe_model_payload(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return json.loads(model.json())


templates.env.filters["roborock_state"] = roborock_state_label
templates.env.filters["roborock_error"] = roborock_error_label
templates.env.filters["roborock_fan"] = roborock_fan_label
templates.env.filters["roborock_mop"] = roborock_mop_label
templates.env.filters["roborock_water"] = roborock_water_label
templates.env.filters["roborock_charge"] = roborock_charge_label
templates.env.filters["roborock_signal"] = roborock_signal_label
templates.env.filters["yesno"] = roborock_bool_label
templates.env.filters["hours"] = format_seconds_as_hours
templates.env.filters["schedule_text"] = roborock_schedule_text
templates.env.filters["rounds"] = roborock_rounds_label
templates.env.filters["pretty_json"] = roborock_json

Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


@app.middleware("http")
async def access_key_middleware(request: Request, call_next):
    if is_public_request(request):
        return await call_next(request)

    username, password = presented_credentials(request)
    access_key = await find_access_key(username, password)
    if not access_key:
        await log_access_attempt(request, False, "missing_or_invalid_key", attempted_username=username)
        if wants_html(request):
            return templates.TemplateResponse(
                request,
                "login.html",
                {"error": "Mangler eller ugyldig brukernavn/passord"},
                status_code=401,
            )
        return JSONResponse({"detail": "Ugyldig eller manglende brukernavn/passord"}, status_code=401)

    request.state.access_key_id = access_key.id
    request.state.access_key_name = access_key.name
    request.state.auth_role = access_role(access_key)
    request.state.auth_is_master = request.state.auth_role == "master"
    request.state.auth_can_settings = request.state.auth_role in ["master", "settings"]
    await log_access_attempt(request, True, "ok", access_key)
    return await call_next(request)


class OutdoorLightEvent(Base):
    __tablename__ = "utelys_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True, default="device_change")
    action = Column(String, index=True, nullable=True)
    device_key = Column(String, index=True, nullable=True)
    device_id = Column(Integer, index=True, nullable=True)
    device_name = Column(String, nullable=True)
    mode = Column(String, index=True, nullable=True)
    reason = Column(Text, nullable=True)
    source = Column(Text, nullable=True)
    lux = Column(Float, nullable=True)
    value = Column(Float, nullable=True)
    state = Column(Boolean, nullable=True)
    extra = Column(JSON, nullable=True)


class OutdoorLightSample(Base):
    __tablename__ = "utelys_samples"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    bucket_start = Column(DateTime, index=True, nullable=False)
    mode = Column(String, index=True, nullable=True)
    source = Column(Text, nullable=True)
    lux = Column(Float, nullable=True)
    value = Column(Float, nullable=True)
    light_lyslist = Column(Boolean, nullable=True)
    light_reklame = Column(Boolean, nullable=True)
    light_spot_glass_275 = Column(Boolean, nullable=True)
    light_spot_glass_299 = Column(Boolean, nullable=True)
    light_spot_inngang = Column(Boolean, nullable=True)
    light_parkering = Column(Boolean, nullable=True)
    weather_symbol = Column(String, nullable=True)
    weather_text = Column(String, nullable=True)
    extra = Column(JSON, nullable=True)


class VentilationEvent(Base):
    __tablename__ = "ventilasjon_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True, default="fan_change")
    action = Column(String, index=True, nullable=True)
    device_key = Column(String, index=True, nullable=True)
    device_id = Column(Integer, index=True, nullable=True)
    device_name = Column(String, nullable=True)
    mode = Column(String, index=True, nullable=True)
    reason = Column(Text, nullable=True)
    source = Column(Text, nullable=True)
    value = Column(Float, nullable=True)
    state = Column(Boolean, nullable=True)

    temp_1etg = Column(Float, nullable=True)
    temp_2etg = Column(Float, nullable=True)
    temp_vip = Column(Float, nullable=True)
    temp_ute = Column(Float, nullable=True)
    temp_loft = Column(Float, nullable=True)
    humidity_1etg = Column(Float, nullable=True)
    humidity_2etg = Column(Float, nullable=True)
    humidity_vip = Column(Float, nullable=True)
    humidity_ute = Column(Float, nullable=True)
    humidity_yr = Column(Float, nullable=True)
    humidity_loft = Column(Float, nullable=True)
    temp_kjeller = Column(Float, nullable=True)
    humidity_kjeller = Column(Float, nullable=True)
    temp_passiv = Column(Float, nullable=True)
    temp_luftinntak = Column(Float, nullable=True)
    humidity_passiv = Column(Float, nullable=True)
    humidity_luftinntak = Column(Float, nullable=True)
    diff_w = Column(Float, nullable=True)
    power_w = Column(Float, nullable=True)
    energy_kwh = Column(Float, nullable=True)

    fan_vip = Column(Boolean, nullable=True)
    fan_2etg = Column(Boolean, nullable=True)
    fan_tak = Column(Boolean, nullable=True)
    fan_avfukter = Column(Boolean, nullable=True)
    extra = Column(JSON, nullable=True)


class VentilationSample(Base):
    __tablename__ = "ventilasjon_samples"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    bucket_start = Column(DateTime, index=True, nullable=False)
    mode = Column(String, index=True, nullable=True)
    source = Column(Text, nullable=True)

    temp_1etg = Column(Float, nullable=True)
    temp_2etg = Column(Float, nullable=True)
    temp_vip = Column(Float, nullable=True)
    temp_ute = Column(Float, nullable=True)
    temp_ute_netatmo = Column(Float, nullable=True)
    temp_yr = Column(Float, nullable=True)
    temp_loft = Column(Float, nullable=True)
    humidity_1etg = Column(Float, nullable=True)
    humidity_2etg = Column(Float, nullable=True)
    humidity_vip = Column(Float, nullable=True)
    humidity_ute = Column(Float, nullable=True)
    humidity_yr = Column(Float, nullable=True)
    humidity_loft = Column(Float, nullable=True)
    temp_kjeller = Column(Float, nullable=True)
    humidity_kjeller = Column(Float, nullable=True)
    temp_passiv = Column(Float, nullable=True)
    temp_luftinntak = Column(Float, nullable=True)
    humidity_passiv = Column(Float, nullable=True)
    humidity_luftinntak = Column(Float, nullable=True)
    temp_min_inne = Column(Float, nullable=True)
    temp_avg_inne = Column(Float, nullable=True)
    temp_max_inne = Column(Float, nullable=True)

    diff_w = Column(Float, nullable=True)
    estimated_sunbeds = Column(Integer, nullable=True)
    afterrun_active = Column(Boolean, nullable=True)
    heat_need = Column(Boolean, nullable=True)
    cool_need = Column(Boolean, nullable=True)
    open_time = Column(Boolean, nullable=True)
    pre_cooling = Column(Boolean, nullable=True)
    exhaust_time_allowed = Column(Boolean, nullable=True)

    fan_vip = Column(Boolean, nullable=True)
    fan_2etg = Column(Boolean, nullable=True)
    fan_tak = Column(Boolean, nullable=True)
    fan_avfukter = Column(Boolean, nullable=True)
    extra = Column(JSON, nullable=True)


class YrForecastSample(Base):
    __tablename__ = "yr_forecast_samples"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    bucket_start = Column(DateTime, index=True, nullable=False)
    source = Column(Text, nullable=True)
    api_updated_at = Column(DateTime, nullable=True)
    last_modified = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, index=True, nullable=True)
    next_fetch_after = Column(DateTime, nullable=True)
    age_seconds = Column(Integer, nullable=True)
    forecast_time = Column(DateTime, nullable=True)
    symbol_code = Column(String, nullable=True)
    weather_text = Column(String, nullable=True)
    air_temperature = Column(Float, nullable=True)
    air_temperature_percentile_10 = Column(Float, nullable=True)
    air_temperature_percentile_90 = Column(Float, nullable=True)
    relative_humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    wind_speed_of_gust = Column(Float, nullable=True)
    wind_speed_percentile_10 = Column(Float, nullable=True)
    wind_speed_percentile_90 = Column(Float, nullable=True)
    wind_from_direction = Column(Float, nullable=True)
    cloud_area_fraction = Column(Float, nullable=True)
    cloud_area_fraction_high = Column(Float, nullable=True)
    cloud_area_fraction_medium = Column(Float, nullable=True)
    cloud_area_fraction_low = Column(Float, nullable=True)
    fog_area_fraction = Column(Float, nullable=True)
    dew_point_temperature = Column(Float, nullable=True)
    air_pressure_at_sea_level = Column(Float, nullable=True)
    ultraviolet_index_clear_sky = Column(Float, nullable=True)
    precipitation_next_1h = Column(Float, nullable=True)
    precipitation_next_1h_min = Column(Float, nullable=True)
    precipitation_next_1h_max = Column(Float, nullable=True)
    precipitation_next_6h = Column(Float, nullable=True)
    precipitation_next_6h_min = Column(Float, nullable=True)
    precipitation_next_6h_max = Column(Float, nullable=True)
    probability_of_precipitation_next_1h = Column(Float, nullable=True)
    probability_of_precipitation_next_6h = Column(Float, nullable=True)
    probability_of_precipitation_next_12h = Column(Float, nullable=True)
    probability_of_thunder_next_1h = Column(Float, nullable=True)
    air_temperature_min_next_6h = Column(Float, nullable=True)
    air_temperature_max_next_6h = Column(Float, nullable=True)
    symbol_confidence_next_12h = Column(String, nullable=True)
    temp_1h = Column(Float, nullable=True)
    temp_3h = Column(Float, nullable=True)
    temp_6h = Column(Float, nullable=True)
    temp_12h = Column(Float, nullable=True)
    temp_24h = Column(Float, nullable=True)
    symbol_1h = Column(String, nullable=True)
    symbol_3h = Column(String, nullable=True)
    symbol_6h = Column(String, nullable=True)
    symbol_12h = Column(String, nullable=True)
    symbol_24h = Column(String, nullable=True)
    temp_min_next_6h = Column(Float, nullable=True)
    temp_max_next_6h = Column(Float, nullable=True)
    extra = Column(JSON, nullable=True)
    raw = Column(JSON, nullable=True)


class GenericEvent(Base):
    __tablename__ = "event_data"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    system = Column(String, index=True, nullable=False)
    event_type = Column(String, index=True, default="status")
    action = Column(String, index=True, nullable=True)
    device_key = Column(String, index=True, nullable=True)
    device_id = Column(Integer, index=True, nullable=True)
    device_name = Column(String, nullable=True)
    mode = Column(String, index=True, nullable=True)
    reason = Column(Text, nullable=True)
    source = Column(Text, nullable=True)
    lux = Column(Float, nullable=True)
    value = Column(Float, nullable=True)
    state = Column(Boolean, nullable=True)
    extra = Column(JSON, nullable=True)


class ImportJobStatus(Base):
    __tablename__ = "import_job_status"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    category = Column(String, index=True, nullable=False)
    source = Column(String, index=True, nullable=True)
    status = Column(String, index=True, nullable=False, default="unknown")
    status_text = Column(String, nullable=True)
    last_started_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True, index=True)
    last_failed_at = Column(DateTime, nullable=True, index=True)
    last_run_at = Column(DateTime, nullable=True, index=True)
    next_expected_at = Column(DateTime, nullable=True, index=True)
    expected_interval_minutes = Column(Integer, nullable=True)
    warning_after_minutes = Column(Integer, nullable=True)
    records_imported = Column(Integer, nullable=True)
    records_total = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class ImportJobRun(Base):
    __tablename__ = "import_job_runs"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String, index=True, nullable=False)
    title = Column(String, nullable=True)
    category = Column(String, index=True, nullable=True)
    source = Column(String, index=True, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, default=datetime.utcnow, index=True)
    ok = Column(Boolean, index=True, nullable=True)
    status = Column(String, index=True, nullable=True)
    records_imported = Column(Integer, nullable=True)
    records_total = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockRobot(Base):
    __tablename__ = "roborock_robots"

    id = Column(Integer, primary_key=True, index=True)
    duid = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    product = Column(String, nullable=True)
    model = Column(String, nullable=True)
    firmware = Column(String, nullable=True)
    protocol_version = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    local_ip = Column(String, nullable=True)
    cloud_online = Column(Boolean, nullable=True)
    shared = Column(Boolean, nullable=True)
    time_zone_id = Column(String, nullable=True)
    last_seen_at = Column(DateTime, nullable=True, index=True)
    last_cloud_at = Column(DateTime, nullable=True)
    last_local_at = Column(DateTime, nullable=True)
    last_status_at = Column(DateTime, nullable=True)
    last_map_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    capabilities = Column(JSON, nullable=True)
    extra = Column(JSON, nullable=True)


class RoborockStatusSample(Base):
    __tablename__ = "roborock_status_samples"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, nullable=True)
    state_code = Column(Integer, nullable=True)
    state_name = Column(String, nullable=True)
    battery = Column(Integer, nullable=True)
    error_code = Column(Integer, nullable=True)
    in_cleaning = Column(Boolean, nullable=True)
    in_returning = Column(Boolean, nullable=True)
    clean_time_seconds = Column(Integer, nullable=True)
    clean_area_m2 = Column(Float, nullable=True)
    fan_power = Column(Integer, nullable=True)
    water_box_mode = Column(Integer, nullable=True)
    mop_mode = Column(Integer, nullable=True)
    dock_type = Column(Integer, nullable=True)
    charge_status = Column(Integer, nullable=True)
    clean_percent = Column(Integer, nullable=True)
    local_ip = Column(String, nullable=True)
    rssi = Column(Integer, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockCleanJob(Base):
    __tablename__ = "roborock_clean_jobs"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    record_id = Column(String, index=True, nullable=False)
    begin_at = Column(DateTime, index=True, nullable=True)
    end_at = Column(DateTime, index=True, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    area_m2 = Column(Float, nullable=True)
    cleaned_area_m2 = Column(Float, nullable=True)
    complete = Column(Boolean, nullable=True)
    error_code = Column(Integer, nullable=True)
    start_type = Column(Integer, nullable=True)
    clean_type = Column(Integer, nullable=True)
    finish_reason = Column(Integer, nullable=True)
    dust_collection_status = Column(Integer, nullable=True)
    avoid_count = Column(Integer, nullable=True)
    wash_count = Column(Integer, nullable=True)
    clean_times = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class RoborockSchedule(Base):
    __tablename__ = "roborock_schedules"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    schedule_id = Column(String, index=True, nullable=False)
    cron = Column(String, nullable=True)
    enabled = Column(Boolean, nullable=True)
    repeated = Column(Boolean, nullable=True)
    segments = Column(String, nullable=True)
    fan_power = Column(Integer, nullable=True)
    mop_mode = Column(Integer, nullable=True)
    water_box_mode = Column(Integer, nullable=True)
    repeat = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class RoborockConsumableSnapshot(Base):
    __tablename__ = "roborock_consumables"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    main_brush_work_time = Column(Integer, nullable=True)
    side_brush_work_time = Column(Integer, nullable=True)
    filter_work_time = Column(Integer, nullable=True)
    sensor_dirty_time = Column(Integer, nullable=True)
    dust_collection_work_times = Column(Integer, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockMapSnapshot(Base):
    __tablename__ = "roborock_maps"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    image_bytes = Column(Integer, nullable=True)
    raw_bytes = Column(Integer, nullable=True)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    rooms = Column(Integer, nullable=True)
    zones = Column(Integer, nullable=True)
    charger = Column(JSON, nullable=True)
    vacuum_position = Column(JSON, nullable=True)
    image_base64 = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockProbeResult(Base):
    __tablename__ = "roborock_probe_results"

    id = Column(Integer, primary_key=True, index=True)
    robot_duid = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, index=True, nullable=True)
    command = Column(String, index=True, nullable=True)
    ok = Column(Boolean, nullable=True)
    error = Column(Text, nullable=True)
    result_type = Column(String, nullable=True)
    raw = Column(JSON, nullable=True)


class RoborockSyncRun(Base):
    __tablename__ = "roborock_sync_runs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    collector_id = Column(String, index=True, nullable=True)
    source = Column(String, nullable=True)
    ok = Column(Boolean, nullable=True)
    robots_count = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class Sun2RoomDailyStat(Base):
    __tablename__ = "sun2_room_daily_stats"
    __table_args__ = (UniqueConstraint("stat_date", "room", name="uq_sun2_room_daily_stats_date_room"),)

    id = Column(Integer, primary_key=True, index=True)
    stat_date = Column(Date, index=True, nullable=False)
    room_id = Column(String, index=True, nullable=True)
    room_key = Column(String, index=True, nullable=True)
    room = Column(String, index=True, nullable=False)
    source_room_name = Column(String, nullable=True)
    sun2_bed_id = Column(String, index=True, nullable=True)
    total_soletid_minutter = Column(Float, nullable=True)
    totalt_antall_solinger = Column(Integer, nullable=True)
    solinger_medlemmer = Column(Integer, nullable=True)
    solinger_ikke_medlemmer = Column(Integer, nullable=True)
    totalt_inntjent_kr = Column(Float, nullable=True)
    inntjent_medlemmer_kr = Column(Float, nullable=True)
    inntjent_ikke_medlemmer_kr = Column(Float, nullable=True)
    source = Column(String, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class Sun2ImportRun(Base):
    __tablename__ = "sun2_import_runs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    collector_id = Column(String, index=True, nullable=True)
    source = Column(String, nullable=True)
    ok = Column(Boolean, nullable=True)
    stat_date = Column(Date, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    rows_count = Column(Integer, nullable=True)
    inserted_count = Column(Integer, nullable=True)
    updated_count = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class Sun2TanningSession(Base):
    __tablename__ = "sun2_tanning_sessions"
    __table_args__ = (
        UniqueConstraint("source", "source_session_id", name="uq_sun2_session_source_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_session_id = Column(String, index=True, nullable=False)
    started_at = Column(DateTime, index=True, nullable=False)
    ended_at = Column(DateTime, index=True, nullable=True)
    stat_date = Column(Date, index=True, nullable=False)
    room_id = Column(String, index=True, nullable=True)
    room_key = Column(String, index=True, nullable=True)
    room = Column(String, index=True, nullable=True)
    source_room_name = Column(String, nullable=True)
    sun2_user_id = Column(String, index=True, nullable=True)
    sun2_center_id = Column(String, index=True, nullable=True)
    sun2_bed_id = Column(String, index=True, nullable=True)
    user_name = Column(String, index=True, nullable=True)
    user_identifier = Column(String, index=True, nullable=True)
    customer_type = Column(String, index=True, nullable=True)
    gender = Column(String, index=True, nullable=True)
    payment_method = Column(String, index=True, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    paid_amount_kr = Column(Float, nullable=True)
    status = Column(String, index=True, nullable=True)
    source = Column(String, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class Sun2Bed(Base):
    __tablename__ = "sun2_beds"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, index=True, nullable=True)
    physical_room_number = Column(Integer, index=True, nullable=True)
    display_room_number = Column(Integer, index=True, nullable=True)
    sun2_center_id = Column(String, index=True, nullable=True)
    sun2_bed_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    source_room_name = Column(String, nullable=True)
    bed_model = Column(String, index=True, nullable=True)
    bed_model_id = Column(String, index=True, nullable=True)
    max_minutes = Column(Float, nullable=True)
    startup_minutes = Column(Float, nullable=True)
    cooldown_minutes = Column(Float, nullable=True)
    current_price_per_min = Column(Float, nullable=True)
    status = Column(String, index=True, nullable=True)
    status_code = Column(String, index=True, nullable=True)
    lamp_status = Column(Text, nullable=True)
    source = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class Sun2Member(Base):
    __tablename__ = "sun2_members"

    id = Column(Integer, primary_key=True, index=True)
    sun2_user_id = Column(String, unique=True, index=True, nullable=False)
    sun2_center_id = Column(String, index=True, nullable=True)
    name = Column(String, index=True, nullable=True)
    display_name = Column(String, index=True, nullable=True)
    initials = Column(String, index=True, nullable=True)
    age = Column(Integer, index=True, nullable=True)
    email = Column(String, index=True, nullable=True)
    phone = Column(String, index=True, nullable=True)
    profile_url = Column(Text, nullable=True)
    customer_type = Column(String, index=True, nullable=True)
    gender = Column(String, index=True, nullable=True)
    birth_date = Column(Date, index=True, nullable=True)
    member_since = Column(Date, index=True, nullable=True)
    last_seen_at = Column(DateTime, index=True, nullable=True)
    status = Column(String, index=True, nullable=True)
    balance_kr = Column(Float, nullable=True)
    total_spent_kr = Column(Float, nullable=True)
    visits_count = Column(Integer, nullable=True)
    source = Column(String, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class Sun2SessionImportRun(Base):
    __tablename__ = "sun2_session_import_runs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    collector_id = Column(String, index=True, nullable=True)
    source = Column(String, nullable=True)
    ok = Column(Boolean, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    period_first = Column(DateTime, index=True, nullable=True)
    period_last = Column(DateTime, index=True, nullable=True)
    rows_count = Column(Integer, nullable=True)
    inserted_count = Column(Integer, nullable=True)
    updated_count = Column(Integer, nullable=True)
    skipped_count = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class EnergyHourlyConsumption(Base):
    __tablename__ = "energy_hourly_consumption"
    __table_args__ = (UniqueConstraint("meter_id", "measured_at", name="uq_energy_hourly_meter_time"),)

    id = Column(Integer, primary_key=True, index=True)
    meter_id = Column(String, index=True, nullable=False)
    measured_at = Column(DateTime, index=True, nullable=False)
    stat_date = Column(Date, index=True, nullable=False)
    year = Column(Integer, index=True, nullable=False)
    month = Column(Integer, index=True, nullable=False)
    day = Column(Integer, index=True, nullable=False)
    hour = Column(Integer, index=True, nullable=False)
    consumption_kwh = Column(Float, nullable=False)
    production_kwh = Column(Float, nullable=True)
    status = Column(String, index=True, nullable=True)
    is_verified = Column(Boolean, nullable=True)
    is_estimated = Column(Boolean, index=True, nullable=True)
    is_public_holiday = Column(Boolean, nullable=True)
    use_weekend_prices = Column(Boolean, nullable=True)
    source = Column(String, index=True, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw = Column(JSON, nullable=True)


class EnergyImportRun(Base):
    __tablename__ = "energy_import_runs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    meter_id = Column(String, index=True, nullable=True)
    source = Column(String, nullable=True)
    ok = Column(Boolean, nullable=True)
    source_file = Column(String, index=True, nullable=True)
    period_first = Column(DateTime, index=True, nullable=True)
    period_last = Column(DateTime, index=True, nullable=True)
    days_count = Column(Integer, nullable=True)
    hours_count = Column(Integer, nullable=True)
    inserted_count = Column(Integer, nullable=True)
    updated_count = Column(Integer, nullable=True)
    skipped_count = Column(Integer, nullable=True)
    total_kwh = Column(Float, nullable=True)
    estimated_hours_count = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    raw = Column(JSON, nullable=True)


class EnergyFibaroSample(Base):
    __tablename__ = "energy_fibaro_samples"
    __table_args__ = (UniqueConstraint("bucket_start", name="uq_energy_fibaro_bucket"),)

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    bucket_start = Column(DateTime, index=True, nullable=False)
    source = Column(String, index=True, nullable=True)

    inntak_w = Column(Float, nullable=True)
    varmepumper_w = Column(Float, nullable=True)
    belysning_w = Column(Float, nullable=True)
    massasje_w = Column(Float, nullable=True)
    annet_w = Column(Float, nullable=True)
    avfukter_w = Column(Float, nullable=True)
    differanse_fibaro_w = Column(Float, nullable=True)
    differanse_beregnet_w = Column(Float, nullable=True)

    inntak_kwh = Column(Float, nullable=True)
    varmepumper_kwh = Column(Float, nullable=True)
    belysning_kwh = Column(Float, nullable=True)
    massasje_kwh = Column(Float, nullable=True)
    annet_kwh = Column(Float, nullable=True)
    avfukter_kwh = Column(Float, nullable=True)
    differanse_fibaro_kwh = Column(Float, nullable=True)
    differanse_beregnet_kwh = Column(Float, nullable=True)

    inntak_delta_kwh = Column(Float, nullable=True)
    varmepumper_delta_kwh = Column(Float, nullable=True)
    belysning_delta_kwh = Column(Float, nullable=True)
    massasje_delta_kwh = Column(Float, nullable=True)
    annet_delta_kwh = Column(Float, nullable=True)
    avfukter_delta_kwh = Column(Float, nullable=True)
    differanse_fibaro_delta_kwh = Column(Float, nullable=True)
    differanse_beregnet_delta_kwh = Column(Float, nullable=True)

    inntak_reset = Column(Boolean, nullable=True)
    varmepumper_reset = Column(Boolean, nullable=True)
    belysning_reset = Column(Boolean, nullable=True)
    massasje_reset = Column(Boolean, nullable=True)
    annet_reset = Column(Boolean, nullable=True)
    avfukter_reset = Column(Boolean, nullable=True)
    differanse_fibaro_reset = Column(Boolean, nullable=True)

    extra = Column(JSON, nullable=True)


class EnergyCircuit(Base):
    __tablename__ = "energy_circuits"

    id = Column(Integer, primary_key=True, index=True)
    circuit_no = Column(Integer, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    breaker_type = Column(String, nullable=True)
    breaker_rating_a = Column(Float, nullable=True)
    breaker_characteristic = Column(String, nullable=True)
    cable_spec = Column(String, nullable=True)
    cable_length_m = Column(Float, nullable=True)
    install_method = Column(String, nullable=True)
    terminal_ref = Column(String, nullable=True)
    rcd_ma = Column(Float, nullable=True)
    is_sunbed = Column(Boolean, index=True, nullable=True)
    note = Column(Text, nullable=True)
    status = Column(String, index=True, nullable=True)
    source = Column(String, index=True, nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)


class EnergyLoad(Base):
    __tablename__ = "energy_loads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    load_type = Column(String, index=True, nullable=True)
    area = Column(String, index=True, nullable=True)
    circuit_no = Column(Integer, index=True, nullable=True)
    expected_power_w = Column(Float, nullable=True)
    measured_direct = Column(Boolean, nullable=True)
    fibaro_device_id = Column(Integer, index=True, nullable=True)
    fibaro_meter_id = Column(Integer, index=True, nullable=True)
    zwave_switch_id = Column(Integer, index=True, nullable=True)
    controllable = Column(Boolean, nullable=True)
    critical = Column(Boolean, nullable=True)
    active = Column(Boolean, index=True, default=True)
    note = Column(Text, nullable=True)
    source = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)


class Hc3MeterReading(Base):
    __tablename__ = "hc3_meter_readings"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    kilde = Column(String, index=True, nullable=False)
    status = Column(String, index=True, nullable=False)
    fibaroid = Column(Integer, index=True, nullable=False)
    verdi1 = Column(Float, nullable=False)
    verdi2 = Column(Float, nullable=True)
    forklaring = Column(Text, nullable=True)
    source = Column(String, index=True, nullable=True)
    raw = Column(JSON, nullable=True)


class ParkingSession(Base):
    __tablename__ = "parkering"
    __table_args__ = (UniqueConstraint("source_system", "parking_id", name="parkering_uq"),)

    id = Column(BigInteger, primary_key=True, index=True)
    parking_area = Column(Text, nullable=False)
    source_system = Column(Text, nullable=False)
    area_number = Column(Integer, nullable=False, index=True)
    parking_id = Column(BigInteger, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True, index=True)
    parking_time_min = Column(Float, nullable=True)
    fee_ex_vat = Column(Float, nullable=True)
    fee_inc_vat = Column(Float, nullable=True)
    fee_vat = Column(Float, nullable=True)
    car_license_number = Column(Text, nullable=True, index=True)
    user_interface = Column(Text, nullable=True)
    subtype = Column(Text, nullable=True)
    status = Column(Text, nullable=False, index=True)
    imported_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    raw_filename = Column(Text, nullable=True)


class ForecastSnapshot(Base):
    __tablename__ = "forecast_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    domain = Column(String, nullable=False, index=True)
    period_type = Column(String, nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    generated_at = Column(DateTime, nullable=True)
    created_by = Column(String, nullable=True)

    forecast_sessions = Column(Float, nullable=True)
    forecast_paid = Column(Float, nullable=True)
    forecast_minutes = Column(Float, nullable=True)
    forecast_vehicles = Column(Float, nullable=True)

    actual_sessions_at_save = Column(Float, nullable=True)
    actual_paid_at_save = Column(Float, nullable=True)
    actual_minutes_at_save = Column(Float, nullable=True)
    actual_vehicles_at_save = Column(Float, nullable=True)

    model_sessions = Column(Float, nullable=True)
    day_fraction = Column(Float, nullable=True)
    tempo = Column(Float, nullable=True)
    raw = Column(JSON, nullable=True)


class ParkingVehicle(Base):
    __tablename__ = "kjoretoy"

    plate = Column(Text, primary_key=True)
    navn = Column(Text, nullable=True)
    omrade = Column(Text, nullable=True, index=True)
    omrade_kilde = Column(Text, nullable=True)
    omrade_oppdatert = Column(DateTime, nullable=True)
    sun2_id = Column(Text, nullable=True, index=True)
    notat = Column(Text, nullable=True)
    first_seen = Column(DateTime, nullable=True, index=True)
    last_seen = Column(DateTime, nullable=True, index=True)
    parkering_count = Column(BigInteger, nullable=True)
    paid_total = Column(Float, nullable=True)
    svv_fetched_at = Column(DateTime, nullable=True, index=True)
    svv_status = Column(Integer, nullable=True)
    svv_error = Column(Text, nullable=True)
    svv_data = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ParkingVehicleDetails(Base):
    __tablename__ = "kjoretoy_nokkeldata"

    plate = Column(Text, primary_key=True)
    vin = Column(Text, nullable=True)
    merke = Column(Text, nullable=True, index=True)
    modell = Column(Text, nullable=True, index=True)
    typebetegnelse = Column(Text, nullable=True)
    kjoretoyklasse_kode = Column(Text, nullable=True)
    kjoretoyklasse_navn = Column(Text, nullable=True, index=True)
    registreringsstatus_kode = Column(Text, nullable=True)
    registreringsstatus_tekst = Column(Text, nullable=True)
    forstegangsregistrert_norge = Column(Date, nullable=True)
    pkk_kontrollfrist = Column(Date, nullable=True)
    egenvekt_kg = Column(Integer, nullable=True)
    nyttelast_kg = Column(Integer, nullable=True)
    tillatt_totalvekt_kg = Column(Integer, nullable=True)
    tillatt_vogntogvekt_kg = Column(Integer, nullable=True)
    tillatt_tilhengervekt_med_brems_kg = Column(Integer, nullable=True)
    tillatt_tilhengervekt_uten_brems_kg = Column(Integer, nullable=True)
    seter_totalt = Column(Integer, nullable=True)
    lengde_mm = Column(Integer, nullable=True)
    bredde_mm = Column(Integer, nullable=True)
    hoyde_mm = Column(Integer, nullable=True)
    rekkevidde_wltp_km = Column(Integer, nullable=True)
    elforbruk_wltp_wh_km = Column(Integer, nullable=True)
    motoreffekt_samlet_kw = Column(Float, nullable=True)
    motoreffekt_kontinuerlig_kw = Column(Float, nullable=True)
    maks_hastighet_kmt = Column(Integer, nullable=True)
    stoy_db = Column(Integer, nullable=True)
    abs = Column(Boolean, nullable=True)
    farge = Column(Text, nullable=True)
    svv_godkjennings_id = Column(Text, nullable=True)
    svv_teknisk_gyldig_fra = Column(Date, nullable=True)
    sist_synkronisert = Column(DateTime, default=datetime.utcnow, nullable=False)


class AiQueryLog(Base):
    __tablename__ = "ai_query_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    username = Column(String, index=True, nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    ok = Column(Boolean, index=True, nullable=True)
    error = Column(Text, nullable=True)
    tool_calls_count = Column(Integer, nullable=True)
    raw = Column(JSON, nullable=True)


class AccessKey(Base):
    __tablename__ = "access_keys"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    key_hash = Column(String, unique=True, index=True, nullable=False)
    key_prefix = Column(String, index=True, nullable=False)
    key_plaintext = Column(String, nullable=True)
    role = Column(String, default="viewer", index=True)
    is_master = Column(Boolean, default=False, index=True)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_seen_at = Column(DateTime, nullable=True)
    last_notified_at = Column(DateTime, nullable=True)
    last_ip = Column(String, nullable=True)
    last_user_agent = Column(Text, nullable=True)
    uses_count = Column(Integer, default=0)


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    access_key_id = Column(Integer, nullable=True, index=True)
    key_name = Column(String, nullable=True)
    key_prefix = Column(String, nullable=True, index=True)
    path = Column(Text, nullable=False)
    method = Column(String, nullable=False)
    ip = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, default=True, index=True)
    reason = Column(String, nullable=True)


class ControlConfig(Base):
    __tablename__ = "control_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    values = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_by = Column(String, nullable=True)


class ControlConfigHistory(Base):
    __tablename__ = "control_config_history"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String, index=True, nullable=False)
    version = Column(Integer, nullable=False)
    values = Column(JSON, nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, index=True)
    changed_by = Column(String, nullable=True)
    reason = Column(Text, nullable=True)


class LegacyLogIn(BaseModel):
    temperature: float
    humidity: float
    timestamp: datetime
    source: str


class Hc3MeterReadingIn(BaseModel):
    kilde: str
    status: str
    fibaroid: int
    verdi1: float
    verdi2: Optional[float] = None
    forklaring: Optional[str] = None
    ts: Optional[datetime] = None
    source: Optional[str] = "HC3"


class EventDataIn(BaseModel):
    system: str
    event_type: str = "status"
    timestamp: Optional[datetime] = None
    action: Optional[str] = None
    device_key: Optional[str] = None
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    mode: Optional[str] = None
    reason: Optional[str] = None
    source: Optional[str] = None
    bucket_start: Optional[datetime] = None

    temp_1etg: Optional[float] = None
    temp_2etg: Optional[float] = None
    temp_vip: Optional[float] = None
    temp_ute: Optional[float] = None
    temp_ute_netatmo: Optional[float] = None
    temp_yr: Optional[float] = None
    temp_loft: Optional[float] = None
    humidity_1etg: Optional[float] = None
    humidity_2etg: Optional[float] = None
    humidity_vip: Optional[float] = None
    humidity_ute: Optional[float] = None
    humidity_yr: Optional[float] = None
    humidity_loft: Optional[float] = None
    temp_kjeller: Optional[float] = None
    humidity_kjeller: Optional[float] = None
    temp_passiv: Optional[float] = None
    temp_luftinntak: Optional[float] = None
    humidity_passiv: Optional[float] = None
    humidity_luftinntak: Optional[float] = None
    temp_min_inne: Optional[float] = None
    temp_avg_inne: Optional[float] = None
    temp_max_inne: Optional[float] = None
    lux: Optional[float] = None
    weather_type: Optional[str] = None
    weather_symbol: Optional[str] = None
    weather_text: Optional[str] = None
    yr_weather: Optional[str] = None
    yr_symbol: Optional[str] = None
    diff_w: Optional[float] = None
    power_w: Optional[float] = None
    energy_kwh: Optional[float] = None
    value: Optional[float] = None
    estimated_sunbeds: Optional[int] = None

    fan_vip: Optional[bool] = None
    fan_2etg: Optional[bool] = None
    fan_tak: Optional[bool] = None
    fan_avfukter: Optional[bool] = None
    light_lyslist: Optional[bool] = None
    light_reklame: Optional[bool] = None
    light_spot_glass_275: Optional[bool] = None
    light_spot_glass_299: Optional[bool] = None
    light_spot_inngang: Optional[bool] = None
    light_parkering: Optional[bool] = None
    afterrun_active: Optional[bool] = None
    heat_need: Optional[bool] = None
    cool_need: Optional[bool] = None
    open_time: Optional[bool] = None
    pre_cooling: Optional[bool] = None
    exhaust_time_allowed: Optional[bool] = None
    state: Optional[bool] = None

    values: Dict[str, Any] = Field(default_factory=dict)
    extra: Dict[str, Any] = Field(default_factory=dict)


class EnergyFibaroIn(BaseModel):
    source: str = "HC3 ENERGI"
    timestamp: Optional[datetime] = None
    bucket_start: Optional[datetime] = None

    inntak_w: Optional[float] = None
    varmepumper_w: Optional[float] = None
    belysning_w: Optional[float] = None
    massasje_w: Optional[float] = None
    annet_w: Optional[float] = None
    avfukter_w: Optional[float] = None
    differanse_fibaro_w: Optional[float] = None

    inntak_kwh: Optional[float] = None
    varmepumper_kwh: Optional[float] = None
    belysning_kwh: Optional[float] = None
    massasje_kwh: Optional[float] = None
    annet_kwh: Optional[float] = None
    avfukter_kwh: Optional[float] = None
    differanse_fibaro_kwh: Optional[float] = None

    extra: Dict[str, Any] = Field(default_factory=dict)


class RoborockIngestIn(BaseModel):
    source: str = "Roborock_logger"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    message: Optional[str] = None
    robots: list[Dict[str, Any]] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class Sun2RoomStatIn(BaseModel):
    stat_date: date
    room: str
    room_id: Optional[str] = None
    room_key: Optional[str] = None
    source_room_name: Optional[str] = None
    sun2_bed_id: Optional[str] = None
    total_soletid_minutter: Optional[float] = None
    totalt_antall_solinger: Optional[int] = None
    solinger_medlemmer: Optional[int] = None
    solinger_ikke_medlemmer: Optional[int] = None
    totalt_inntjent_kr: Optional[float] = None
    inntjent_medlemmer_kr: Optional[float] = None
    inntjent_ikke_medlemmer_kr: Optional[float] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class Sun2RoomStatsIngestIn(BaseModel):
    source: str = "sun2_importer"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    stat_date: Optional[date] = None
    source_file: Optional[str] = None
    message: Optional[str] = None
    rows: list[Sun2RoomStatIn] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class Sun2TanningSessionIn(BaseModel):
    source_session_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    stat_date: Optional[date] = None
    room_id: Optional[str] = None
    room: Optional[str] = None
    room_key: Optional[str] = None
    source_room_name: Optional[str] = None
    sun2_user_id: Optional[str] = None
    sun2_center_id: Optional[str] = None
    sun2_bed_id: Optional[str] = None
    user_name: Optional[str] = None
    user_identifier: Optional[str] = None
    customer_type: Optional[str] = None
    gender: Optional[str] = None
    payment_method: Optional[str] = None
    duration_minutes: Optional[float] = None
    paid_amount_kr: Optional[float] = None
    status: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class Sun2TanningSessionsIngestIn(BaseModel):
    source: str = "sun2_session_scraper"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    source_file: Optional[str] = None
    message: Optional[str] = None
    rows: list[Sun2TanningSessionIn] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class Sun2BedIn(BaseModel):
    room_id: Optional[str] = None
    physical_room_number: Optional[int] = None
    display_room_number: Optional[int] = None
    sun2_center_id: Optional[str] = None
    sun2_bed_id: str
    name: str
    source_room_name: Optional[str] = None
    bed_model: Optional[str] = None
    bed_model_id: Optional[str] = None
    max_minutes: Optional[float] = None
    startup_minutes: Optional[float] = None
    cooldown_minutes: Optional[float] = None
    current_price_per_min: Optional[float] = None
    status: Optional[str] = None
    status_code: Optional[str] = None
    lamp_status: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class Sun2BedsIngestIn(BaseModel):
    source: str = "sun2_session_scraper"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    message: Optional[str] = None
    beds: list[Sun2BedIn] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class Sun2MemberIn(BaseModel):
    sun2_user_id: str
    sun2_center_id: Optional[str] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    initials: Optional[str] = None
    age: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    profile_url: Optional[str] = None
    customer_type: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    member_since: Optional[date] = None
    last_seen_at: Optional[datetime] = None
    status: Optional[str] = None
    balance_kr: Optional[float] = None
    total_spent_kr: Optional[float] = None
    visits_count: Optional[int] = None
    source_file: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class Sun2MembersIngestIn(BaseModel):
    source: str = "sun2_session_scraper"
    collector_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ok: bool = True
    message: Optional[str] = None
    members: list[Sun2MemberIn] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class ImportStatusReportIn(BaseModel):
    job_name: str
    title: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    ok: Optional[bool] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    next_expected_at: Optional[datetime] = None
    expected_interval_minutes: Optional[int] = None
    warning_after_minutes: Optional[int] = None
    records_imported: Optional[int] = None
    records_total: Optional[int] = None
    duration_seconds: Optional[float] = None
    message: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class ParkingVehicleNameUpdate(BaseModel):
    navn: str = Field("", max_length=500)
    sun2_id: Optional[str] = Field(None, max_length=120)
    notat: Optional[str] = Field(None, max_length=2000)
    source: Optional[str] = Field(None, max_length=120)
    raw: Dict[str, Any] = Field(default_factory=dict)


class ParkingVehicleAreaUpdate(BaseModel):
    omrade: str = Field("", max_length=240)
    source: Optional[str] = Field(None, max_length=120)
    raw: Dict[str, Any] = Field(default_factory=dict)


LIGHT_COLUMNS = [
    "id", "timestamp", "event_type", "action", "device_key", "device_id", "device_name",
    "mode", "reason", "source", "lux", "value", "state", "extra",
]

LIGHT_SAMPLE_COLUMNS = [
    "id", "timestamp", "bucket_start", "mode", "source", "lux", "value",
    "light_lyslist", "light_reklame", "light_spot_glass_275", "light_spot_glass_299",
    "light_spot_inngang", "light_parkering", "weather_symbol", "weather_text", "extra",
]

VENT_COLUMNS = [
    "id", "timestamp", "event_type", "action", "device_key", "device_id", "device_name",
    "mode", "reason", "source", "value", "state", "temp_1etg", "temp_2etg",
    "temp_vip", "temp_ute", "temp_loft", "humidity_1etg", "humidity_2etg",
    "humidity_vip", "humidity_ute", "humidity_yr", "humidity_loft",
    "temp_kjeller", "humidity_kjeller", "temp_passiv", "temp_luftinntak",
    "humidity_passiv", "humidity_luftinntak", "diff_w", "power_w", "energy_kwh",
    "fan_vip", "fan_2etg", "fan_tak", "fan_avfukter", "extra",
]

GENERIC_COLUMNS = [
    "id", "timestamp", "system", "event_type", "action", "device_key", "device_id",
    "device_name", "mode", "reason", "source", "lux", "value", "state", "extra",
]

VENT_SAMPLE_COLUMNS = [
    "id", "timestamp", "bucket_start", "mode", "source", "temp_1etg", "temp_2etg",
    "temp_vip", "temp_ute", "temp_ute_netatmo", "temp_yr", "temp_loft",
    "humidity_1etg", "humidity_2etg", "humidity_vip", "humidity_ute",
    "humidity_yr", "humidity_loft", "temp_passiv", "temp_kjeller",
    "humidity_kjeller", "temp_luftinntak", "humidity_passiv",
    "humidity_luftinntak", "temp_min_inne", "temp_avg_inne", "temp_max_inne", "diff_w", "estimated_sunbeds",
    "afterrun_active", "heat_need", "cool_need", "open_time", "pre_cooling",
    "exhaust_time_allowed", "fan_vip", "fan_2etg", "fan_tak", "fan_avfukter", "extra",
]

YR_SAMPLE_COLUMNS = [
    "id", "timestamp", "bucket_start", "source", "api_updated_at", "last_modified",
    "expires_at", "next_fetch_after", "age_seconds", "forecast_time", "symbol_code",
    "weather_text", "air_temperature", "air_temperature_percentile_10",
    "air_temperature_percentile_90", "relative_humidity", "wind_speed",
    "wind_speed_of_gust", "wind_speed_percentile_10", "wind_speed_percentile_90",
    "wind_from_direction", "cloud_area_fraction", "cloud_area_fraction_high",
    "cloud_area_fraction_medium", "cloud_area_fraction_low", "fog_area_fraction",
    "dew_point_temperature", "air_pressure_at_sea_level", "ultraviolet_index_clear_sky",
    "precipitation_next_1h", "precipitation_next_1h_min", "precipitation_next_1h_max",
    "precipitation_next_6h", "precipitation_next_6h_min", "precipitation_next_6h_max",
    "probability_of_precipitation_next_1h", "probability_of_precipitation_next_6h",
    "probability_of_precipitation_next_12h", "probability_of_thunder_next_1h",
    "air_temperature_min_next_6h", "air_temperature_max_next_6h",
    "symbol_confidence_next_12h", "temp_1h", "temp_3h", "temp_6h", "temp_12h",
    "temp_24h", "symbol_1h", "symbol_3h", "symbol_6h", "symbol_12h",
    "symbol_24h", "temp_min_next_6h", "temp_max_next_6h", "extra", "raw",
]

ROBOROCK_ROBOT_COLUMNS = [
    "id", "duid", "name", "product", "model", "firmware", "protocol_version",
    "serial_number", "local_ip", "cloud_online", "shared", "time_zone_id",
    "last_seen_at", "last_cloud_at", "last_local_at", "last_status_at",
    "last_map_at", "last_error", "capabilities", "extra",
]

ROBOROCK_STATUS_COLUMNS = [
    "id", "robot_duid", "timestamp", "source", "state_code", "state_name",
    "battery", "error_code", "in_cleaning", "in_returning", "clean_time_seconds",
    "clean_area_m2", "fan_power", "water_box_mode", "mop_mode", "dock_type",
    "charge_status", "clean_percent", "local_ip", "rssi", "raw",
]

ROBOROCK_JOB_COLUMNS = [
    "id", "robot_duid", "record_id", "begin_at", "end_at", "duration_seconds",
    "duration_minutes", "area_m2", "cleaned_area_m2", "complete", "error_code",
    "start_type", "clean_type", "finish_reason", "dust_collection_status",
    "avoid_count", "wash_count", "clean_times", "updated_at", "raw",
]

ROBOROCK_SCHEDULE_COLUMNS = [
    "id", "robot_duid", "schedule_id", "cron", "enabled", "repeated", "segments",
    "fan_power", "mop_mode", "water_box_mode", "repeat", "updated_at", "raw",
]

ROBOROCK_MAP_COLUMNS = [
    "id", "robot_duid", "timestamp", "image_bytes", "raw_bytes", "image_width",
    "image_height", "rooms", "zones", "charger", "vacuum_position", "raw",
]

SUN2_ROOM_COLUMNS = [
    "id", "stat_date", "room_id", "room_key", "room", "source_room_name", "sun2_bed_id", "total_soletid_minutter",
    "totalt_antall_solinger", "solinger_medlemmer", "solinger_ikke_medlemmer",
    "totalt_inntjent_kr", "inntjent_medlemmer_kr", "inntjent_ikke_medlemmer_kr",
    "source", "source_file", "imported_at", "raw",
]

SUN2_IMPORT_COLUMNS = [
    "id", "timestamp", "collector_id", "source", "ok", "stat_date", "source_file",
    "rows_count", "inserted_count", "updated_count", "message", "raw",
]

SUN2_SESSION_COLUMNS = [
    "id", "source_session_id", "started_at", "ended_at", "stat_date", "room_id", "room_key",
    "room", "source_room_name", "sun2_user_id", "sun2_center_id", "sun2_bed_id", "user_name",
    "user_identifier", "customer_type", "gender", "payment_method", "duration_minutes",
    "paid_amount_kr", "status", "source", "source_file", "imported_at", "raw",
]

SUN2_BED_COLUMNS = [
    "id", "room_id", "physical_room_number", "display_room_number", "sun2_center_id",
    "sun2_bed_id", "name", "source_room_name", "bed_model", "bed_model_id",
    "max_minutes", "startup_minutes", "cooldown_minutes", "current_price_per_min",
    "status", "status_code", "lamp_status", "source", "imported_at", "raw",
]

SUN2_MEMBER_COLUMNS = [
    "id", "sun2_user_id", "sun2_center_id", "name", "display_name", "initials", "age",
    "email", "phone", "profile_url", "customer_type", "gender", "birth_date",
    "member_since", "last_seen_at", "status", "balance_kr", "total_spent_kr",
    "visits_count", "source", "source_file", "imported_at", "raw",
]

SUN2_SESSION_IMPORT_COLUMNS = [
    "id", "timestamp", "collector_id", "source", "ok", "source_file",
    "period_first", "period_last", "rows_count", "inserted_count", "updated_count",
    "skipped_count", "message", "raw",
]

ENERGY_HOURLY_COLUMNS = [
    "id", "meter_id", "measured_at", "stat_date", "year", "month", "day", "hour",
    "consumption_kwh", "production_kwh", "status", "is_verified", "is_estimated",
    "is_public_holiday", "use_weekend_prices", "source", "source_file", "imported_at", "raw",
]

ENERGY_IMPORT_COLUMNS = [
    "id", "timestamp", "meter_id", "source", "ok", "source_file", "period_first", "period_last",
    "days_count", "hours_count", "inserted_count", "updated_count", "skipped_count", "total_kwh",
    "estimated_hours_count", "message", "raw",
]

ENERGY_FIBARO_COLUMNS = [
    "id", "timestamp", "bucket_start", "source",
    "inntak_w", "varmepumper_w", "belysning_w", "massasje_w", "annet_w", "avfukter_w",
    "differanse_fibaro_w", "differanse_beregnet_w",
    "inntak_kwh", "varmepumper_kwh", "belysning_kwh", "massasje_kwh", "annet_kwh", "avfukter_kwh",
    "differanse_fibaro_kwh", "differanse_beregnet_kwh",
    "inntak_delta_kwh", "varmepumper_delta_kwh", "belysning_delta_kwh",
    "massasje_delta_kwh", "annet_delta_kwh", "avfukter_delta_kwh", "differanse_fibaro_delta_kwh",
    "differanse_beregnet_delta_kwh",
    "inntak_reset", "varmepumper_reset", "belysning_reset", "massasje_reset",
    "annet_reset", "avfukter_reset", "differanse_fibaro_reset", "extra",
]

AI_QUERY_COLUMNS = [
    "id", "timestamp", "username", "question", "answer", "ok", "error", "tool_calls_count", "raw",
]

AI_DATASETS = {
    "soling_daily": {
        "table": "sun2_room_daily_stats",
        "title": "Soling per rom per dag",
        "description": "SUN2-statistikk med soltid, antall solinger og inntjent beløp per rom og dato.",
        "columns": SUN2_ROOM_COLUMNS,
        "time_column": "stat_date",
    },
    "soling_sessions": {
        "table": "sun2_tanning_sessions",
        "title": "Enkelt-solinger",
        "description": "En rad per soltime/soling hentet fra SUN2 owner, med starttid, rom, bruker, varighet og betalt belop.",
        "columns": SUN2_SESSION_COLUMNS,
        "time_column": "started_at",
    },
    "soling_beds": {
        "table": "sun2_beds",
        "title": "SUN2 senger og fysisk rom",
        "description": "Fast mapping mellom fysisk rom-id, SUN2 seng-id, SUN2-navn, modell, status og gjeldende innstillinger.",
        "columns": SUN2_BED_COLUMNS,
        "time_column": "imported_at",
    },
    "soling_members": {
        "table": "sun2_members",
        "title": "SUN2 medlemmer",
        "description": "SUN2-brukere/medlemmer med fast SUN2-id og eventuell profilinfo fra medlemssider.",
        "columns": SUN2_MEMBER_COLUMNS,
        "time_column": "imported_at",
    },
    "energy_hourly": {
        "table": "energy_hourly_consumption",
        "title": "Elvia strømforbruk per time",
        "description": "Importerte Elvia-timesverdier med kWh, måler, dato og status.",
        "columns": ENERGY_HOURLY_COLUMNS,
        "time_column": "measured_at",
    },
    "energy_fibaro": {
        "table": "energy_fibaro_samples",
        "title": "Fibaro strømlogging",
        "description": "Minuttlogging fra HC3 med realtime effekt, akkumulert kWh, beregnet differanse og reset-markering.",
        "columns": ENERGY_FIBARO_COLUMNS,
        "time_column": "bucket_start",
    },
    "light_events": {
        "table": "utelys_events",
        "title": "Lys hendelser",
        "description": "På/av-hendelser for lys, med lux, enhet, årsak og modus.",
        "columns": LIGHT_COLUMNS,
        "time_column": "timestamp",
    },
    "light_samples": {
        "table": "utelys_samples",
        "title": "Lys 5-minutters logging",
        "description": "Regelmessige lys- og lux-prøver med status for alle lysgrupper.",
        "columns": LIGHT_SAMPLE_COLUMNS,
        "time_column": "timestamp",
    },
    "ventilation_events": {
        "table": "ventilasjon_events",
        "title": "Ventilasjon hendelser",
        "description": "Start/stopp-hendelser for vifter med temperaturer, effekt og årsak.",
        "columns": VENT_COLUMNS,
        "time_column": "timestamp",
    },
    "ventilation_samples": {
        "table": "ventilasjon_samples",
        "title": "Ventilasjon 5-minutters logging",
        "description": "Temperaturer, viftestatus, effekt og beregnet driftsmodus.",
        "columns": VENT_SAMPLE_COLUMNS,
        "time_column": "timestamp",
    },
    "yr_forecast": {
        "table": "yr_forecast_samples",
        "title": "Yr værdata",
        "description": "Værvarsel og observasjonsnære verdier hentet fra Yr/MET.",
        "columns": YR_SAMPLE_COLUMNS,
        "time_column": "timestamp",
    },
    "renhold_robots": {
        "table": "roborock_robots",
        "title": "Roborock roboter",
        "description": "Robotmetadata, modell, serienummer, IP, firmware og siste kontakt.",
        "columns": ROBOROCK_ROBOT_COLUMNS,
        "time_column": "last_seen_at",
    },
    "renhold_status": {
        "table": "roborock_status_samples",
        "title": "Roborock status",
        "description": "Statusprøver fra robotene med batteri, tilstand, rengjøring og signal.",
        "columns": ROBOROCK_STATUS_COLUMNS,
        "time_column": "timestamp",
    },
    "renhold_jobs": {
        "table": "roborock_clean_jobs",
        "title": "Roborock jobber",
        "description": "Historiske rengjøringsjobber med tid, areal, varighet og sluttstatus.",
        "columns": ROBOROCK_JOB_COLUMNS,
        "time_column": "begin_at",
    },
    "generic_events": {
        "table": "event_data",
        "title": "Generelle logghendelser",
        "description": "Eldre og generelle loggposter fra HC3 og scripts.",
        "columns": GENERIC_COLUMNS,
        "time_column": "timestamp",
    },
}


SUN2_SUM_FIELDS = [
    "total_soletid_minutter",
    "totalt_antall_solinger",
    "solinger_medlemmer",
    "solinger_ikke_medlemmer",
    "totalt_inntjent_kr",
    "inntjent_medlemmer_kr",
    "inntjent_ikke_medlemmer_kr",
]


def empty_sun2_summary(period: str) -> Dict[str, Any]:
    return {
        "period": period,
        "period_label": period,
        "total_soletid_minutter": 0.0,
        "total_soletid_timer": 0.0,
        "totalt_antall_solinger": 0,
        "solinger_medlemmer": 0,
        "solinger_ikke_medlemmer": 0,
        "totalt_inntjent_kr": 0.0,
        "inntjent_medlemmer_kr": 0.0,
        "inntjent_ikke_medlemmer_kr": 0.0,
        "days": set(),
        "rooms": set(),
    }


def add_sun2_row_to_summary(summary: Dict[str, Any], row: Any) -> None:
    for field in SUN2_SUM_FIELDS:
        summary[field] += getattr(row, field) or 0
    if row.stat_date:
        summary["days"].add(row.stat_date)
    if row.room:
        summary["rooms"].add(row.room)


def finalize_sun2_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(summary)
    summary["total_soletid_timer"] = summary["total_soletid_minutter"] / 60
    summary["days_count"] = len(summary.pop("days", []))
    summary["rooms_count"] = len(summary.pop("rooms", []))
    return summary


def build_sun2_summaries(rows: list[Any]) -> Dict[str, Any]:
    daily: Dict[str, Dict[str, Any]] = {}
    monthly: Dict[str, Dict[str, Any]] = {}
    yearly: Dict[str, Dict[str, Any]] = {}
    weekly: Dict[str, Dict[int, Dict[str, Any]]] = {}
    total = empty_sun2_summary("Totalt")
    first_date = None
    last_date = None

    for row in rows:
        if not row.stat_date:
            continue
        first_date = row.stat_date if first_date is None else min(first_date, row.stat_date)
        last_date = row.stat_date if last_date is None else max(last_date, row.stat_date)
        day_key = row.stat_date.isoformat()
        month_key = row.stat_date.strftime("%Y-%m")
        year_key = str(row.stat_date.year)
        iso_year, iso_week, _ = row.stat_date.isocalendar()
        iso_year_key = str(iso_year)
        daily.setdefault(day_key, empty_sun2_summary(day_key))
        monthly.setdefault(month_key, empty_sun2_summary(month_key))
        yearly.setdefault(year_key, empty_sun2_summary(year_key))
        weekly.setdefault(iso_year_key, {})
        weekly[iso_year_key].setdefault(iso_week, empty_sun2_summary(f"{iso_year_key}-W{iso_week:02d}"))
        daily[day_key]["period_label"] = row.stat_date.strftime("%d.%m.%Y")
        add_sun2_row_to_summary(daily[day_key], row)
        add_sun2_row_to_summary(monthly[month_key], row)
        add_sun2_row_to_summary(yearly[year_key], row)
        add_sun2_row_to_summary(weekly[iso_year_key][iso_week], row)
        add_sun2_row_to_summary(total, row)

    daily_items = [finalize_sun2_summary(daily[key]) for key in sorted(daily, reverse=True)]
    monthly_items = [finalize_sun2_summary(monthly[key]) for key in sorted(monthly, reverse=True)]
    yearly_items = [finalize_sun2_summary(yearly[key]) for key in sorted(yearly, reverse=True)]
    top_sort = lambda item: (
        item["totalt_inntjent_kr"],
        item["totalt_antall_solinger"],
        item["total_soletid_minutter"],
    )
    count_sort = lambda item: (
        item["totalt_antall_solinger"],
        item["totalt_inntjent_kr"],
        item["total_soletid_minutter"],
    )
    weekly_chart = []
    palette = ["#3f7fbd", "#df705d", "#52a464", "#726189", "#f2b84b", "#2f8fa3", "#8b5cf6", "#ef4444"]
    for index, year_key in enumerate(sorted(weekly.keys())):
        weeks = weekly[year_key]
        weekly_chart.append(
            {
                "year": year_key,
                "color": palette[index % len(palette)],
                "revenue": [round(finalize_sun2_summary(weeks[week])["totalt_inntjent_kr"], 2) if week in weeks else None for week in range(1, 54)],
                "count": [int(finalize_sun2_summary(weeks[week])["totalt_antall_solinger"]) if week in weeks else None for week in range(1, 54)],
            }
        )

    return {
        "daily": daily_items,
        "monthly": monthly_items,
        "yearly": yearly_items,
        "weekly_chart": weekly_chart,
        "top_days": sorted(daily_items, key=top_sort, reverse=True)[:10],
        "top_months": sorted(monthly_items, key=top_sort, reverse=True)[:10],
        "top_days_by_count": sorted(daily_items, key=count_sort, reverse=True)[:10],
        "top_months_by_count": sorted(monthly_items, key=count_sort, reverse=True)[:10],
        "total": finalize_sun2_summary(total),
        "first_date": first_date,
        "last_date": last_date,
    }


def empty_energy_summary(period: str) -> Dict[str, Any]:
    return {
        "period": period,
        "period_label": period,
        "consumption_kwh": 0.0,
        "production_kwh": 0.0,
        "hours_count": 0,
        "estimated_hours_count": 0,
        "days": set(),
    }


def add_energy_row_to_summary(summary: Dict[str, Any], row: Any) -> None:
    summary["consumption_kwh"] += row.consumption_kwh or 0
    summary["production_kwh"] += row.production_kwh or 0
    summary["hours_count"] += 1
    if row.is_estimated:
        summary["estimated_hours_count"] += 1
    if row.stat_date:
        summary["days"].add(row.stat_date)


def finalize_energy_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(summary)
    summary["days_count"] = len(summary.pop("days", []))
    return summary


def build_energy_summaries(rows: list[Any]) -> Dict[str, Any]:
    daily: Dict[str, Dict[str, Any]] = {}
    monthly: Dict[str, Dict[str, Any]] = {}
    yearly: Dict[str, Dict[str, Any]] = {}
    total = empty_energy_summary("Totalt")
    first_at = None
    last_at = None

    for row in rows:
        if not row.measured_at:
            continue
        first_at = row.measured_at if first_at is None else min(first_at, row.measured_at)
        last_at = row.measured_at if last_at is None else max(last_at, row.measured_at)
        day_key = row.stat_date.isoformat()
        month_key = f"{row.year:04d}-{row.month:02d}"
        year_key = str(row.year)
        daily.setdefault(day_key, empty_energy_summary(day_key))
        monthly.setdefault(month_key, empty_energy_summary(month_key))
        yearly.setdefault(year_key, empty_energy_summary(year_key))
        daily[day_key]["period_label"] = row.stat_date.strftime("%d.%m.%Y")
        add_energy_row_to_summary(daily[day_key], row)
        add_energy_row_to_summary(monthly[month_key], row)
        add_energy_row_to_summary(yearly[year_key], row)
        add_energy_row_to_summary(total, row)

    daily_items = [finalize_energy_summary(daily[key]) for key in sorted(daily, reverse=True)]
    monthly_items = [finalize_energy_summary(monthly[key]) for key in sorted(monthly, reverse=True)]
    yearly_items = [finalize_energy_summary(yearly[key]) for key in sorted(yearly, reverse=True)]
    top_sort = lambda item: (item["consumption_kwh"], item["hours_count"])

    return {
        "daily": daily_items,
        "monthly": monthly_items,
        "yearly": yearly_items,
        "top_days": sorted(daily_items, key=top_sort, reverse=True)[:10],
        "top_months": sorted(monthly_items, key=top_sort, reverse=True)[:10],
        "total": finalize_energy_summary(total),
        "first_at": first_at,
        "last_at": last_at,
    }


def int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def float_or_zero(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def finalized_sun2_aggregate(row: Dict[str, Any], period: str, period_label: Optional[str] = None) -> Dict[str, Any]:
    item = empty_sun2_summary(period)
    item["period_label"] = period_label or period
    for field in SUN2_SUM_FIELDS:
        item[field] = float_or_zero(row.get(field))
    item["total_soletid_timer"] = item["total_soletid_minutter"] / 60
    item["days_count"] = int_or_zero(row.get("days_count"))
    item["rooms_count"] = int_or_zero(row.get("rooms_count"))
    return item


def finalized_energy_aggregate(row: Dict[str, Any], period: str, period_label: Optional[str] = None) -> Dict[str, Any]:
    item = empty_energy_summary(period)
    item["period_label"] = period_label or period
    item["consumption_kwh"] = float_or_zero(row.get("consumption_kwh"))
    item["production_kwh"] = float_or_zero(row.get("production_kwh"))
    item["hours_count"] = int_or_zero(row.get("hours_count"))
    item["estimated_hours_count"] = int_or_zero(row.get("estimated_hours_count"))
    item["days_count"] = int_or_zero(row.get("days_count"))
    return item


def sun2_sum_columns() -> list[Any]:
    return [func.coalesce(func.sum(getattr(Sun2RoomDailyStat, field)), 0).label(field) for field in SUN2_SUM_FIELDS]


def energy_sum_columns() -> list[Any]:
    return [
        func.coalesce(func.sum(EnergyHourlyConsumption.consumption_kwh), 0).label("consumption_kwh"),
        func.coalesce(func.sum(EnergyHourlyConsumption.production_kwh), 0).label("production_kwh"),
        func.count(EnergyHourlyConsumption.id).label("hours_count"),
        func.coalesce(
            func.sum(case((EnergyHourlyConsumption.is_estimated.is_(True), 1), else_=0)),
            0,
        ).label("estimated_hours_count"),
    ]


def empty_fast_sun2_summary(period: str, period_label: Optional[str] = None) -> Dict[str, Any]:
    item = {field: 0.0 for field in SUN2_SUM_FIELDS}
    item.update(
        {
            "period": period,
            "period_label": period_label or period,
            "total_soletid_timer": 0.0,
            "days_count": 0,
            "rooms_count": 0,
            "rows_count": 0,
        }
    )
    return item


def add_fast_sun2_summary(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    for field in SUN2_SUM_FIELDS:
        target[field] += float_or_zero(source.get(field))
    target["total_soletid_timer"] = target["total_soletid_minutter"] / 60
    target["days_count"] += int_or_zero(source.get("days_count"))
    target["rows_count"] += int_or_zero(source.get("rows_count"))
    target["rooms_count"] = max(int_or_zero(target.get("rooms_count")), int_or_zero(source.get("rooms_count")))


def empty_fast_energy_summary(period: str, period_label: Optional[str] = None) -> Dict[str, Any]:
    return {
        "period": period,
        "period_label": period_label or period,
        "consumption_kwh": 0.0,
        "production_kwh": 0.0,
        "hours_count": 0,
        "estimated_hours_count": 0,
        "days_count": 0,
    }


def add_fast_energy_summary(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    target["consumption_kwh"] += float_or_zero(source.get("consumption_kwh"))
    target["production_kwh"] += float_or_zero(source.get("production_kwh"))
    target["hours_count"] += int_or_zero(source.get("hours_count"))
    target["estimated_hours_count"] += int_or_zero(source.get("estimated_hours_count"))
    target["days_count"] += int_or_zero(source.get("days_count"))


async def build_sun2_summaries_fast(session) -> Dict[str, Any]:
    daily_rows = (
        await session.execute(
            select(
                Sun2RoomDailyStat.stat_date.label("stat_date"),
                *sun2_sum_columns(),
                func.count(Sun2RoomDailyStat.id).label("rows_count"),
                func.count(func.distinct(Sun2RoomDailyStat.room)).label("rooms_count"),
            )
            .group_by(Sun2RoomDailyStat.stat_date)
            .order_by(Sun2RoomDailyStat.stat_date.desc())
        )
    ).mappings().all()

    daily_items = []
    monthly: Dict[str, Dict[str, Any]] = {}
    yearly: Dict[str, Dict[str, Any]] = {}
    weekly: Dict[str, Dict[int, Dict[str, Any]]] = {}
    total = empty_fast_sun2_summary("Totalt")
    first_date = None
    last_date = None

    for row in daily_rows:
        stat_date = row.get("stat_date")
        if not stat_date:
            continue
        first_date = stat_date if first_date is None else min(first_date, stat_date)
        last_date = stat_date if last_date is None else max(last_date, stat_date)
        source = dict(row)
        source["days_count"] = 1
        item = finalized_sun2_aggregate(source, stat_date.isoformat(), stat_date.strftime("%d.%m.%Y"))
        item["rows_count"] = int_or_zero(row.get("rows_count"))
        daily_items.append(item)

        month_key = stat_date.strftime("%Y-%m")
        year_key = str(stat_date.year)
        monthly.setdefault(month_key, empty_fast_sun2_summary(month_key))
        yearly.setdefault(year_key, empty_fast_sun2_summary(year_key))
        add_fast_sun2_summary(monthly[month_key], item)
        add_fast_sun2_summary(yearly[year_key], item)
        add_fast_sun2_summary(total, item)

        iso_year, iso_week, _ = stat_date.isocalendar()
        iso_year_key = str(iso_year)
        weekly.setdefault(iso_year_key, {})
        weekly[iso_year_key].setdefault(iso_week, {"revenue": 0.0, "count": 0})
        weekly[iso_year_key][iso_week]["revenue"] += float_or_zero(item.get("totalt_inntjent_kr"))
        weekly[iso_year_key][iso_week]["count"] += int_or_zero(item.get("totalt_antall_solinger"))

    daily_dates_subquery = select(Sun2RoomDailyStat.stat_date).distinct()
    session_filters = [Sun2TanningSession.stat_date.not_in(daily_dates_subquery)]
    customer_type = func.lower(func.coalesce(Sun2TanningSession.customer_type, ""))
    is_member = customer_type.like("%medlem%") & ~customer_type.like("%ikke%")
    live_session_query = (
        select(
            Sun2TanningSession.stat_date.label("stat_date"),
            func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("total_soletid_minutter"),
            func.count(Sun2TanningSession.id).label("totalt_antall_solinger"),
            func.coalesce(func.sum(case((is_member, 1), else_=0)), 0).label("solinger_medlemmer"),
            func.coalesce(func.sum(case((~is_member, 1), else_=0)), 0).label("solinger_ikke_medlemmer"),
            func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("totalt_inntjent_kr"),
            func.coalesce(func.sum(case((is_member, Sun2TanningSession.paid_amount_kr), else_=0)), 0).label("inntjent_medlemmer_kr"),
            func.coalesce(func.sum(case((~is_member, Sun2TanningSession.paid_amount_kr), else_=0)), 0).label("inntjent_ikke_medlemmer_kr"),
            func.count(Sun2TanningSession.id).label("rows_count"),
            func.count(func.distinct(Sun2TanningSession.room_id)).label("rooms_count"),
        )
        .group_by(Sun2TanningSession.stat_date)
        .order_by(Sun2TanningSession.stat_date.desc())
    )
    if session_filters:
        live_session_query = live_session_query.where(*session_filters)
    live_session_rows = (await session.execute(live_session_query)).mappings().all()
    for row in live_session_rows:
        stat_date = row.get("stat_date")
        if not stat_date:
            continue
        first_date = stat_date if first_date is None else min(first_date, stat_date)
        last_date = stat_date if last_date is None else max(last_date, stat_date)
        source = dict(row)
        source["days_count"] = 1
        item = finalized_sun2_aggregate(source, stat_date.isoformat(), stat_date.strftime("%d.%m.%Y"))
        item["rows_count"] = int_or_zero(row.get("rows_count"))
        daily_items.append(item)

        month_key = stat_date.strftime("%Y-%m")
        year_key = str(stat_date.year)
        monthly.setdefault(month_key, empty_fast_sun2_summary(month_key))
        yearly.setdefault(year_key, empty_fast_sun2_summary(year_key))
        add_fast_sun2_summary(monthly[month_key], item)
        add_fast_sun2_summary(yearly[year_key], item)
        add_fast_sun2_summary(total, item)

        iso_year, iso_week, _ = stat_date.isocalendar()
        iso_year_key = str(iso_year)
        weekly.setdefault(iso_year_key, {})
        weekly[iso_year_key].setdefault(iso_week, {"revenue": 0.0, "count": 0})
        weekly[iso_year_key][iso_week]["revenue"] += float_or_zero(item.get("totalt_inntjent_kr"))
        weekly[iso_year_key][iso_week]["count"] += int_or_zero(item.get("totalt_antall_solinger"))

    daily_items = sorted(daily_items, key=lambda item: item["period"], reverse=True)
    monthly_items = [monthly[key] for key in sorted(monthly, reverse=True)]
    yearly_items = [yearly[key] for key in sorted(yearly, reverse=True)]
    palette = ["#3f7fbd", "#df705d", "#52a464", "#726189", "#f2b84b", "#2f8fa3", "#8b5cf6", "#ef4444"]
    weekly_chart = []
    for index, year in enumerate(sorted(weekly.keys())):
        weeks = weekly[year]
        weekly_chart.append(
            {
                "year": year,
                "color": palette[index % len(palette)],
                "revenue": [round(weeks[week]["revenue"], 2) if week in weeks else None for week in range(1, 54)],
                "count": [weeks[week]["count"] if week in weeks else None for week in range(1, 54)],
            }
        )

    top_sort = lambda item: (
        item["totalt_inntjent_kr"],
        item["totalt_antall_solinger"],
        item["total_soletid_minutter"],
    )
    count_sort = lambda item: (
        item["totalt_antall_solinger"],
        item["totalt_inntjent_kr"],
        item["total_soletid_minutter"],
    )
    return {
        "daily": daily_items,
        "monthly": monthly_items,
        "yearly": yearly_items,
        "weekly_chart": weekly_chart,
        "top_days": sorted(daily_items, key=top_sort, reverse=True)[:10],
        "top_months": sorted(monthly_items, key=top_sort, reverse=True)[:10],
        "top_days_by_count": sorted(daily_items, key=count_sort, reverse=True)[:10],
        "top_months_by_count": sorted(monthly_items, key=count_sort, reverse=True)[:10],
        "total": total,
        "first_date": first_date,
        "last_date": last_date,
        "total_rows": int_or_zero(total.get("rows_count")),
    }


async def build_energy_summaries_fast(session) -> Dict[str, Any]:
    daily_rows = (
        await session.execute(
            select(
                EnergyHourlyConsumption.stat_date.label("stat_date"),
                *energy_sum_columns(),
            )
            .group_by(EnergyHourlyConsumption.stat_date)
            .order_by(EnergyHourlyConsumption.stat_date.desc())
        )
    ).mappings().all()

    daily_items = []
    monthly: Dict[str, Dict[str, Any]] = {}
    yearly: Dict[str, Dict[str, Any]] = {}
    total = empty_fast_energy_summary("Totalt")
    first_at = None
    last_at = None

    for row in daily_rows:
        stat_date = row.get("stat_date")
        if not stat_date:
            continue
        item = finalized_energy_aggregate(dict(row, days_count=1), stat_date.isoformat(), stat_date.strftime("%d.%m.%Y"))
        daily_items.append(item)
        month_key = stat_date.strftime("%Y-%m")
        year_key = str(stat_date.year)
        monthly.setdefault(month_key, empty_fast_energy_summary(month_key))
        yearly.setdefault(year_key, empty_fast_energy_summary(year_key))
        add_fast_energy_summary(monthly[month_key], item)
        add_fast_energy_summary(yearly[year_key], item)
        add_fast_energy_summary(total, item)

    bounds = (
        await session.execute(
            select(
                func.min(EnergyHourlyConsumption.measured_at).label("first_at"),
                func.max(EnergyHourlyConsumption.measured_at).label("last_at"),
            )
        )
    ).mappings().first() or {}
    first_at = bounds.get("first_at")
    last_at = bounds.get("last_at")
    monthly_items = [monthly[key] for key in sorted(monthly, reverse=True)]
    yearly_items = [yearly[key] for key in sorted(yearly, reverse=True)]
    top_sort = lambda item: (item["consumption_kwh"], item["hours_count"])

    return {
        "daily": daily_items,
        "monthly": monthly_items,
        "yearly": yearly_items,
        "top_days": sorted(daily_items, key=top_sort, reverse=True)[:10],
        "top_months": sorted(monthly_items, key=top_sort, reverse=True)[:10],
        "total": total,
        "first_at": first_at,
        "last_at": last_at,
    }


async def cached_summaries(cache_key: str, builder, session, force: bool = False) -> Dict[str, Any]:
    now = datetime.utcnow()
    cached = SUMMARY_CACHE.get(cache_key)
    if not force and cached and cached.get("expires", datetime.min) > now:
        return cached["value"]
    value = await builder(session)
    SUMMARY_CACHE[cache_key] = {"expires": now + SUMMARY_CACHE_TTL, "value": value}
    return value


async def get_sun2_summaries(session, force: bool = False) -> Dict[str, Any]:
    return await cached_summaries("sun2", build_sun2_summaries_fast, session, force)


async def get_energy_summaries(session, force: bool = False) -> Dict[str, Any]:
    return await cached_summaries("energy", build_energy_summaries_fast, session, force)


async def sun2_period_snapshot(session, start_day: date, end_day: date) -> SimpleNamespace:
    """Return SUN2 totals using daily files where available and live sessions only for missing days."""
    daily_rows = (
        await session.execute(
            select(
                Sun2RoomDailyStat.stat_date.label("stat_date"),
                *sun2_sum_columns(),
                func.count(func.distinct(Sun2RoomDailyStat.room)).label("rooms"),
            )
            .where(Sun2RoomDailyStat.stat_date >= start_day, Sun2RoomDailyStat.stat_date < end_day)
            .group_by(Sun2RoomDailyStat.stat_date)
        )
    ).mappings().all()
    daily_dates = {row["stat_date"] for row in daily_rows if row.get("stat_date")}
    totals = {"sessions": 0, "minutes": 0.0, "paid": 0.0, "rooms": 0}
    for row in daily_rows:
        totals["sessions"] += int_or_zero(row.get("totalt_antall_solinger"))
        totals["minutes"] += float_or_zero(row.get("total_soletid_minutter"))
        totals["paid"] += float_or_zero(row.get("totalt_inntjent_kr"))
        totals["rooms"] = max(totals["rooms"], int_or_zero(row.get("rooms")))

    session_filters = [
        Sun2TanningSession.stat_date >= start_day,
        Sun2TanningSession.stat_date < end_day,
    ]
    if daily_dates:
        session_filters.append(Sun2TanningSession.stat_date.not_in(daily_dates))
    session_row = (
        await session.execute(
            select(
                func.count(Sun2TanningSession.id).label("sessions"),
                func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("minutes"),
                func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                func.count(func.distinct(Sun2TanningSession.room_id)).label("rooms"),
            ).where(*session_filters)
        )
    ).one()
    totals["sessions"] += int_or_zero(session_row.sessions)
    totals["minutes"] += float_or_zero(session_row.minutes)
    totals["paid"] += float_or_zero(session_row.paid)
    totals["rooms"] = max(totals["rooms"], int_or_zero(session_row.rooms))
    return SimpleNamespace(**totals)


def empty_parking_summary(period: str, period_label: Optional[str] = None) -> Dict[str, Any]:
    return {
        "period": period,
        "period_label": period_label or period,
        "sessions": 0,
        "paid": 0.0,
        "minutes": 0.0,
        "vehicles": 0,
        "days_count": 0,
    }


async def build_parking_summaries_fast(session) -> Dict[str, Any]:
    stat_date_expr = func.date(ParkingSession.start_time).label("stat_date")
    daily_rows = (
        await session.execute(
            select(
                stat_date_expr,
                func.count(ParkingSession.id).label("sessions"),
                func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                func.coalesce(func.sum(ParkingSession.parking_time_min), 0).label("minutes"),
                func.count(func.distinct(ParkingSession.car_license_number)).label("vehicles"),
            )
            .group_by(stat_date_expr)
            .order_by(stat_date_expr.desc())
        )
    ).mappings().all()

    daily_items = []
    monthly: Dict[str, Dict[str, Any]] = {}
    yearly: Dict[str, Dict[str, Any]] = {}
    weekly: Dict[str, Dict[int, Dict[str, Any]]] = {}
    total = empty_parking_summary("Totalt")
    first_date = None
    last_date = None

    for row in daily_rows:
        stat_day = row.get("stat_date")
        if not stat_day:
            continue
        if isinstance(stat_day, str):
            stat_day = date.fromisoformat(stat_day)
        first_date = stat_day if first_date is None else min(first_date, stat_day)
        last_date = stat_day if last_date is None else max(last_date, stat_day)
        item = empty_parking_summary(stat_day.isoformat(), stat_day.strftime("%d.%m.%Y"))
        item["sessions"] = int_or_zero(row.get("sessions"))
        item["paid"] = float_or_zero(row.get("paid"))
        item["minutes"] = float_or_zero(row.get("minutes"))
        item["vehicles"] = int_or_zero(row.get("vehicles"))
        item["days_count"] = 1
        daily_items.append(item)

        month_key = stat_day.strftime("%Y-%m")
        year_key = str(stat_day.year)
        iso_year, iso_week, _ = stat_day.isocalendar()
        iso_year_key = str(iso_year)
        monthly.setdefault(month_key, empty_parking_summary(month_key))
        yearly.setdefault(year_key, empty_parking_summary(year_key))
        weekly.setdefault(iso_year_key, {})
        weekly[iso_year_key].setdefault(iso_week, {"revenue": 0.0, "count": 0})
        weekly[iso_year_key][iso_week]["revenue"] += item["paid"]
        weekly[iso_year_key][iso_week]["count"] += item["sessions"]
        for target in (monthly[month_key], yearly[year_key], total):
            target["sessions"] += item["sessions"]
            target["paid"] += item["paid"]
            target["minutes"] += item["minutes"]
            target["vehicles"] = max(target["vehicles"], item["vehicles"])
            target["days_count"] += 1

    monthly_items = [monthly[key] for key in sorted(monthly, reverse=True)]
    yearly_items = [yearly[key] for key in sorted(yearly, reverse=True)]
    palette = ["#4e8793", "#d59a18", "#071943", "#52a464", "#df705d", "#726189", "#2f8fa3", "#8b5cf6"]
    weekly_chart = []
    for index, year in enumerate(sorted(weekly.keys())):
        weeks = weekly[year]
        weekly_chart.append(
            {
                "year": year,
                "color": palette[index % len(palette)],
                "revenue": [round(weeks[week]["revenue"], 2) if week in weeks else None for week in range(1, 54)],
                "count": [weeks[week]["count"] if week in weeks else None for week in range(1, 54)],
            }
        )
    top_sort = lambda item: (item["paid"], item["sessions"], item["minutes"])
    count_sort = lambda item: (item["sessions"], item["paid"], item["minutes"])
    return {
        "daily": daily_items,
        "monthly": monthly_items,
        "yearly": yearly_items,
        "weekly_chart": weekly_chart,
        "top_days": sorted(daily_items, key=top_sort, reverse=True)[:10],
        "top_months": sorted(monthly_items, key=top_sort, reverse=True)[:10],
        "top_days_by_count": sorted(daily_items, key=count_sort, reverse=True)[:10],
        "top_months_by_count": sorted(monthly_items, key=count_sort, reverse=True)[:10],
        "total": total,
        "first_date": first_date,
        "last_date": last_date,
    }


async def get_parking_summaries(session, force: bool = False) -> Dict[str, Any]:
    return await cached_summaries("parking", build_parking_summaries_fast, session, force)


def combine_business_summaries(sun: Dict[str, Any], parking: Dict[str, Any]) -> Dict[str, Any]:
    def combine_items(left: list[Dict[str, Any]], right: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        combined: Dict[str, Dict[str, Any]] = {}
        for item in left:
            key = item["period"]
            combined.setdefault(
                key,
                {
                    "period": key,
                    "period_label": item.get("period_label", key),
                    "sun_paid": 0.0,
                    "parking_paid": 0.0,
                    "sun_count": 0,
                    "parking_count": 0,
                },
            )
            combined[key]["sun_paid"] += float_or_zero(item.get("totalt_inntjent_kr"))
            combined[key]["sun_count"] += int_or_zero(item.get("totalt_antall_solinger"))
        for item in right:
            key = item["period"]
            combined.setdefault(
                key,
                {
                    "period": key,
                    "period_label": item.get("period_label", key),
                    "sun_paid": 0.0,
                    "parking_paid": 0.0,
                    "sun_count": 0,
                    "parking_count": 0,
                },
            )
            combined[key]["parking_paid"] += float_or_zero(item.get("paid"))
            combined[key]["parking_count"] += int_or_zero(item.get("sessions"))
        for item in combined.values():
            item["total_paid"] = item["sun_paid"] + item["parking_paid"]
            item["total_count"] = item["sun_count"] + item["parking_count"]
        return list(combined.values())

    daily = combine_items(sun.get("daily", []), parking.get("daily", []))
    monthly = combine_items(sun.get("monthly", []), parking.get("monthly", []))
    weekly: Dict[str, Dict[str, Any]] = {}
    palette = ["#4e8793", "#d59a18", "#071943", "#52a464", "#df705d", "#726189", "#2f8fa3", "#8b5cf6"]
    for source in (sun.get("weekly_chart", []), parking.get("weekly_chart", [])):
        for series in source:
            year = str(series.get("year") or "")
            if not year.isdigit() or int(year) < 2023:
                continue
            weekly.setdefault(
                year,
                {
                    "year": year,
                    "revenue": [0.0 for _ in range(53)],
                    "count": [0 for _ in range(53)],
                    "has_value": [False for _ in range(53)],
                },
            )
            for index in range(53):
                revenue_values = series.get("revenue") or []
                count_values = series.get("count") or []
                revenue = revenue_values[index] if index < len(revenue_values) else None
                count = count_values[index] if index < len(count_values) else None
                if revenue is not None:
                    weekly[year]["revenue"][index] += float_or_zero(revenue)
                    weekly[year]["has_value"][index] = True
                if count is not None:
                    weekly[year]["count"][index] += int_or_zero(count)
                    weekly[year]["has_value"][index] = True
    weekly_chart = []
    for index, year in enumerate(sorted(weekly.keys())):
        item = weekly[year]
        weekly_chart.append(
            {
                "year": year,
                "color": palette[index % len(palette)],
                "revenue": [
                    round(item["revenue"][week], 2) if item["has_value"][week] else None
                    for week in range(53)
                ],
                "count": [
                    item["count"][week] if item["has_value"][week] else None
                    for week in range(53)
                ],
            }
        )
    top_sort = lambda item: (item["total_paid"], item["total_count"])
    return {
        "top_days": sorted(daily, key=top_sort, reverse=True)[:10],
        "top_months": sorted(monthly, key=top_sort, reverse=True)[:10],
        "weekly_chart": weekly_chart,
    }


def clear_summary_cache(*keys: str) -> None:
    for key in keys:
        SUMMARY_CACHE.pop(key, None)
        prefix = f"{key}:"
        for cached_key in list(SUMMARY_CACHE):
            if cached_key.startswith(prefix):
                SUMMARY_CACHE.pop(cached_key, None)


LIGHT_TIMELINE_DEVICES = [
    {"key": "lyslist", "name": "Lyslist dekor", "sample_attr": "light_lyslist", "legacy_ids": [425]},
    {"key": "reklame", "name": "Reklameplakater", "sample_attr": "light_reklame", "legacy_ids": [427]},
    {"key": "spot_glass_275", "name": "Spot foran glassvegg", "sample_attr": "light_spot_glass_275", "legacy_ids": [275]},
    {"key": "spot_glass_299", "name": "Spot foran massasje", "sample_attr": "light_spot_glass_299", "legacy_ids": [299]},
    {"key": "spot_inngang", "name": "6xspot over inngang", "sample_attr": "light_spot_inngang", "legacy_ids": [424]},
    {"key": "parkering", "name": "Parkeringslys/gatelys", "sample_attr": "light_parkering", "legacy_ids": [440]},
]

VENT_TIMELINE_DEVICES = [
    {"key": "vip_intake", "name": "Innluft VIP", "sample_attr": "fan_vip", "legacy_ids": [130]},
    {"key": "floor_intake", "name": "Innluft 2.etg", "sample_attr": "fan_2etg", "legacy_ids": [160]},
    {"key": "roof_exhaust", "name": "Avtrekk tak/loft", "sample_attr": "fan_tak", "legacy_ids": [134]},
    {"key": "dehumidifier_basement", "name": "Avfukter kjeller", "sample_attr": "fan_avfukter", "legacy_ids": [449]},
]

DAY_ZOOM_OPTIONS = [
    {"key": "all", "label": "Hele døgnet", "start_hour": 0, "end_hour": 24, "ticks": [0, 6, 12, 18, 24]},
    {"key": "night", "label": "Natt 00-06", "start_hour": 0, "end_hour": 6, "ticks": [0, 2, 4, 6]},
    {"key": "day", "label": "Dag 06-24", "start_hour": 6, "end_hour": 24, "ticks": [6, 12, 18, 24]},
]

WEATHER_LABELS = {
    "clearsky": "Klarvær",
    "clearsky_day": "Klarvær",
    "clearsky_night": "Klarvær",
    "clearsky_polartwilight": "Klarvær",
    "fair": "Lettskyet",
    "fair_day": "Lettskyet",
    "fair_night": "Lettskyet",
    "fair_polartwilight": "Lettskyet",
    "partlycloudy": "Delvis skyet",
    "partlycloudy_day": "Delvis skyet",
    "partlycloudy_night": "Delvis skyet",
    "partlycloudy_polartwilight": "Delvis skyet",
    "cloudy": "Skyet",
    "fog": "Tåke",
    "lightrain": "Lett regn",
    "rain": "Regn",
    "heavyrain": "Kraftig regn",
    "lightsnow": "Lett snø",
    "snow": "Snø",
    "heavysnow": "Kraftig snø",
    "sleet": "Sludd",
    "lightsleet": "Lett sludd",
    "thunderstorm": "Torden",
    "rainshowers": "Regnbyger",
    "lightrainshowers": "Lette regnbyger",
    "heavyrainshowers": "Kraftige regnbyger",
    "snowshowers": "Snøbyger",
    "lightsnowshowers": "Lette snøbyger",
    "heavysnowshowers": "Kraftige snøbyger",
}

STARTUP_COLUMNS = {
    "utelys_events": [
        ("device_key", "VARCHAR"),
    ],
    "ventilasjon_events": [
        ("device_key", "VARCHAR"),
        ("humidity_1etg", "DOUBLE PRECISION"),
        ("humidity_2etg", "DOUBLE PRECISION"),
        ("humidity_vip", "DOUBLE PRECISION"),
        ("humidity_ute", "DOUBLE PRECISION"),
        ("humidity_yr", "DOUBLE PRECISION"),
        ("humidity_loft", "DOUBLE PRECISION"),
        ("temp_kjeller", "DOUBLE PRECISION"),
        ("humidity_kjeller", "DOUBLE PRECISION"),
        ("humidity_passiv", "DOUBLE PRECISION"),
        ("humidity_luftinntak", "DOUBLE PRECISION"),
        ("fan_avfukter", "BOOLEAN"),
    ],
    "event_data": [
        ("device_key", "VARCHAR"),
    ],
    "utelys_samples": [
        ("light_spot_glass_275", "BOOLEAN"),
        ("light_spot_glass_299", "BOOLEAN"),
        ("weather_symbol", "VARCHAR"),
        ("weather_text", "VARCHAR"),
    ],
    "ventilasjon_samples": [
        ("temp_ute_netatmo", "DOUBLE PRECISION"),
        ("temp_yr", "DOUBLE PRECISION"),
        ("humidity_1etg", "DOUBLE PRECISION"),
        ("humidity_2etg", "DOUBLE PRECISION"),
        ("humidity_vip", "DOUBLE PRECISION"),
        ("humidity_ute", "DOUBLE PRECISION"),
        ("humidity_yr", "DOUBLE PRECISION"),
        ("humidity_loft", "DOUBLE PRECISION"),
        ("temp_kjeller", "DOUBLE PRECISION"),
        ("humidity_kjeller", "DOUBLE PRECISION"),
        ("humidity_passiv", "DOUBLE PRECISION"),
        ("humidity_luftinntak", "DOUBLE PRECISION"),
        ("temp_min_inne", "DOUBLE PRECISION"),
        ("temp_avg_inne", "DOUBLE PRECISION"),
        ("temp_max_inne", "DOUBLE PRECISION"),
        ("estimated_sunbeds", "INTEGER"),
        ("afterrun_active", "BOOLEAN"),
        ("heat_need", "BOOLEAN"),
        ("cool_need", "BOOLEAN"),
        ("open_time", "BOOLEAN"),
        ("pre_cooling", "BOOLEAN"),
        ("exhaust_time_allowed", "BOOLEAN"),
        ("fan_avfukter", "BOOLEAN"),
    ],
    "access_keys": [
        ("key_plaintext", "VARCHAR"),
        ("role", "VARCHAR"),
        ("last_notified_at", "TIMESTAMP"),
    ],
    "yr_forecast_samples": [
        ("api_updated_at", "TIMESTAMP"),
        ("last_modified", "TIMESTAMP"),
        ("expires_at", "TIMESTAMP"),
        ("next_fetch_after", "TIMESTAMP"),
        ("age_seconds", "INTEGER"),
        ("wind_speed_of_gust", "DOUBLE PRECISION"),
        ("probability_of_precipitation_next_1h", "DOUBLE PRECISION"),
        ("probability_of_precipitation_next_6h", "DOUBLE PRECISION"),
        ("air_temperature_percentile_10", "DOUBLE PRECISION"),
        ("air_temperature_percentile_90", "DOUBLE PRECISION"),
        ("wind_speed_percentile_10", "DOUBLE PRECISION"),
        ("wind_speed_percentile_90", "DOUBLE PRECISION"),
        ("cloud_area_fraction_high", "DOUBLE PRECISION"),
        ("cloud_area_fraction_medium", "DOUBLE PRECISION"),
        ("cloud_area_fraction_low", "DOUBLE PRECISION"),
        ("ultraviolet_index_clear_sky", "DOUBLE PRECISION"),
        ("precipitation_next_1h_min", "DOUBLE PRECISION"),
        ("precipitation_next_1h_max", "DOUBLE PRECISION"),
        ("precipitation_next_6h_min", "DOUBLE PRECISION"),
        ("precipitation_next_6h_max", "DOUBLE PRECISION"),
        ("probability_of_precipitation_next_12h", "DOUBLE PRECISION"),
        ("probability_of_thunder_next_1h", "DOUBLE PRECISION"),
        ("air_temperature_min_next_6h", "DOUBLE PRECISION"),
        ("air_temperature_max_next_6h", "DOUBLE PRECISION"),
        ("symbol_confidence_next_12h", "VARCHAR"),
        ("raw", "JSON"),
    ],
    "roborock_robots": [
        ("serial_number", "VARCHAR"),
        ("last_map_at", "TIMESTAMP"),
    ],
    "kjoretoy": [
        ("navn", "TEXT"),
        ("omrade", "TEXT"),
        ("omrade_kilde", "TEXT"),
        ("omrade_oppdatert", "TIMESTAMP"),
        ("sun2_id", "TEXT"),
        ("notat", "TEXT"),
    ],
    "sun2_room_daily_stats": [
        ("room_id", "VARCHAR"),
        ("room_key", "VARCHAR"),
        ("source_room_name", "VARCHAR"),
        ("sun2_bed_id", "VARCHAR"),
    ],
    "sun2_tanning_sessions": [
        ("room_id", "VARCHAR"),
        ("sun2_user_id", "VARCHAR"),
        ("sun2_center_id", "VARCHAR"),
        ("sun2_bed_id", "VARCHAR"),
        ("gender", "VARCHAR"),
        ("payment_method", "VARCHAR"),
    ],
    "sun2_members": [
        ("sun2_center_id", "VARCHAR"),
        ("name", "VARCHAR"),
        ("display_name", "VARCHAR"),
        ("initials", "VARCHAR"),
        ("age", "INTEGER"),
        ("email", "VARCHAR"),
        ("phone", "VARCHAR"),
        ("profile_url", "TEXT"),
        ("customer_type", "VARCHAR"),
        ("gender", "VARCHAR"),
        ("birth_date", "DATE"),
        ("member_since", "DATE"),
        ("last_seen_at", "TIMESTAMP"),
        ("status", "VARCHAR"),
        ("balance_kr", "DOUBLE PRECISION"),
        ("total_spent_kr", "DOUBLE PRECISION"),
        ("visits_count", "INTEGER"),
        ("source", "VARCHAR"),
        ("source_file", "VARCHAR"),
        ("imported_at", "TIMESTAMP"),
        ("raw", "JSON"),
    ],
    "energy_fibaro_samples": [
        ("differanse_beregnet_w", "DOUBLE PRECISION"),
        ("differanse_beregnet_kwh", "DOUBLE PRECISION"),
        ("differanse_beregnet_delta_kwh", "DOUBLE PRECISION"),
        ("inntak_reset", "BOOLEAN"),
        ("varmepumper_reset", "BOOLEAN"),
        ("belysning_reset", "BOOLEAN"),
        ("massasje_reset", "BOOLEAN"),
        ("annet_reset", "BOOLEAN"),
        ("avfukter_w", "DOUBLE PRECISION"),
        ("avfukter_kwh", "DOUBLE PRECISION"),
        ("avfukter_delta_kwh", "DOUBLE PRECISION"),
        ("avfukter_reset", "BOOLEAN"),
        ("differanse_fibaro_reset", "BOOLEAN"),
    ],
    "energy_circuits": [
        ("is_sunbed", "BOOLEAN"),
    ],
}

PERFORMANCE_INDEXES = [
    (
        "ix_sun2_sessions_stat_started",
        "CREATE INDEX IF NOT EXISTS ix_sun2_sessions_stat_started "
        "ON sun2_tanning_sessions (stat_date, started_at DESC)",
    ),
    (
        "ix_sun2_sessions_room_stat",
        "CREATE INDEX IF NOT EXISTS ix_sun2_sessions_room_stat "
        "ON sun2_tanning_sessions (room_id, stat_date)",
    ),
    (
        "ix_sun2_sessions_user_stat",
        "CREATE INDEX IF NOT EXISTS ix_sun2_sessions_user_stat "
        "ON sun2_tanning_sessions (sun2_user_id, stat_date)",
    ),
    (
        "ix_sun2_sessions_payment_stat",
        "CREATE INDEX IF NOT EXISTS ix_sun2_sessions_payment_stat "
        "ON sun2_tanning_sessions (payment_method, stat_date)",
    ),
    (
        "ix_sun2_sessions_status_stat",
        "CREATE INDEX IF NOT EXISTS ix_sun2_sessions_status_stat "
        "ON sun2_tanning_sessions (status, stat_date)",
    ),
    (
        "ix_sun2_sessions_customer_stat",
        "CREATE INDEX IF NOT EXISTS ix_sun2_sessions_customer_stat "
        "ON sun2_tanning_sessions (customer_type, stat_date)",
    ),
    (
        "ix_sun2_members_name",
        "CREATE INDEX IF NOT EXISTS ix_sun2_members_name "
        "ON sun2_members (name)",
    ),
    (
        "ix_sun2_members_display_name",
        "CREATE INDEX IF NOT EXISTS ix_sun2_members_display_name "
        "ON sun2_members (display_name)",
    ),
    (
        "ix_sun2_members_status_type",
        "CREATE INDEX IF NOT EXISTS ix_sun2_members_status_type "
        "ON sun2_members (status, customer_type)",
    ),
    (
        "ix_sun2_room_daily_date_room",
        "CREATE INDEX IF NOT EXISTS ix_sun2_room_daily_date_room "
        "ON sun2_room_daily_stats (stat_date, room_id)",
    ),
    (
        "ix_energy_hourly_year_month",
        "CREATE INDEX IF NOT EXISTS ix_energy_hourly_year_month "
        "ON energy_hourly_consumption (year, month)",
    ),
    (
        "ix_energy_hourly_date_meter",
        "CREATE INDEX IF NOT EXISTS ix_energy_hourly_date_meter "
        "ON energy_hourly_consumption (stat_date, meter_id)",
    ),
    (
        "ix_energy_fibaro_bucket",
        "CREATE INDEX IF NOT EXISTS ix_energy_fibaro_bucket "
        "ON energy_fibaro_samples (bucket_start DESC)",
    ),
    (
        "ix_energy_fibaro_timestamp",
        "CREATE INDEX IF NOT EXISTS ix_energy_fibaro_timestamp "
        "ON energy_fibaro_samples (timestamp DESC)",
    ),
    (
        "ix_vent_samples_bucket_mode",
        "CREATE INDEX IF NOT EXISTS ix_vent_samples_bucket_mode "
        "ON ventilasjon_samples (bucket_start, mode)",
    ),
    (
        "ix_light_samples_bucket_mode",
        "CREATE INDEX IF NOT EXISTS ix_light_samples_bucket_mode "
        "ON utelys_samples (bucket_start, mode)",
    ),
    (
        "ix_import_runs_job_finished",
        "CREATE INDEX IF NOT EXISTS ix_import_runs_job_finished "
        "ON import_job_runs (job_name, finished_at DESC)",
    ),
    (
        "ix_parkering_plate_start",
        "CREATE INDEX IF NOT EXISTS ix_parkering_plate_start "
        "ON parkering (upper(car_license_number), start_time DESC)",
    ),
    (
        "ix_parkering_start_status",
        "CREATE INDEX IF NOT EXISTS ix_parkering_start_status "
        "ON parkering (start_time DESC, status)",
    ),
    (
        "ix_kjoretoy_merke_modell",
        "CREATE INDEX IF NOT EXISTS ix_kjoretoy_merke_modell "
        "ON kjoretoy_nokkeldata (merke, modell)",
    ),
    (
        "ix_kjoretoy_sun2_id",
        "CREATE INDEX IF NOT EXISTS ix_kjoretoy_sun2_id "
        "ON kjoretoy (sun2_id)",
    ),
]


IMPORT_JOB_DEFINITIONS = {
    "hc3_light_5min": {
        "title": "Lys / lux fra HC3",
        "category": "Lys",
        "source": "HC3",
        "expected_interval_minutes": 7,
        "warning_after_minutes": 15,
        "description": "5-minutters luxlogg og status for utelys.",
    },
    "hc3_ventilation_5min": {
        "title": "Ventilasjon / temperatur fra HC3",
        "category": "Ventilasjon",
        "source": "HC3",
        "expected_interval_minutes": 7,
        "warning_after_minutes": 15,
        "description": "5-minutters temperatur, effekt og viftestatus.",
    },
    "yr_weather_refresh": {
        "title": "Yr API",
        "category": "Vær",
        "source": "MET/Yr",
        "expected_interval_minutes": 70,
        "warning_after_minutes": 130,
        "description": "Værvarsel hentet fra Yr/MET når forrige varsel går ut.",
    },
    "hc3_energy_1min": {
        "title": "Energi fra HC3",
        "category": "Energi",
        "source": "HC3",
        "expected_interval_minutes": 2,
        "warning_after_minutes": 5,
        "description": "Minuttlogging av realtime effekt og akkumulert kWh fra Fibaro.",
    },
    "roborock_sync": {
        "title": "Roborock logger",
        "category": "Renhold",
        "source": "QNAP",
        "expected_interval_minutes": 10,
        "warning_after_minutes": 30,
        "description": "Robotstatus, planlagte jobber og siste lokale/cloud-data.",
    },
    "sun2_daily_download": {
        "title": "Sun2 dagsfil nedlasting",
        "category": "Soling",
        "source": "QNAP",
        "expected_interval_minutes": 36 * 60,
        "warning_after_minutes": 72 * 60,
        "description": "Nattlig nedlasting av SUN2 dagsfil for import.",
    },
    "sun2_room_daily_import": {
        "title": "Sun2 dagsimport rom",
        "category": "Soling",
        "source": "QNAP",
        "expected_interval_minutes": 36 * 60,
        "warning_after_minutes": 72 * 60,
        "description": "Daglige summer per rom fra Sun2.",
    },
    "sun2_sessions_import": {
        "title": "Sun2 enkelttimer",
        "category": "Soling",
        "source": "QNAP",
        "expected_interval_minutes": 7,
        "warning_after_minutes": 20,
        "description": "Import av enkeltsolinger fra Sun2.",
    },
    "sun2_beds_import": {
        "title": "Sun2 senger",
        "category": "Soling",
        "source": "QNAP",
        "expected_interval_minutes": 7 * 24 * 60,
        "warning_after_minutes": 14 * 24 * 60,
        "description": "Seng-/rommetadata fra Sun2.",
    },
    "sun2_members_import": {
        "title": "Sun2 medlemmer",
        "category": "Soling",
        "source": "QNAP",
        "expected_interval_minutes": 7 * 24 * 60,
        "warning_after_minutes": 14 * 24 * 60,
        "description": "Medlemsregister og profilfelter fra Sun2.",
    },
    "elvia_monthly_import": {
        "title": "Elvia månedsfil",
        "category": "Energi",
        "source": "Manuell opplasting",
        "expected_interval_minutes": 40 * 24 * 60,
        "warning_after_minutes": 55 * 24 * 60,
        "description": "Månedlig import av strømforbruk fra Elvia.",
    },
    "easypark_parking_import": {
        "title": "EasyPark import",
        "category": "Parkering",
        "source": "EasyPark",
        "expected_interval_minutes": 26 * 60,
        "warning_after_minutes": 50 * 60,
        "description": "Automatisk nedlasting og import av parkeringsliste fra EasyPark.",
    },
    "parking_history_import": {
        "title": "Parkering historikk",
        "category": "Parkering",
        "source": "QNAP appdb",
        "expected_interval_minutes": None,
        "warning_after_minutes": None,
        "description": "Migrert EasyPark-historikk med kjoretoydata fra Statens vegvesen.",
    },
    "parking_vehicle_svv_sync": {
        "title": "Kjøretøydata fra SVV",
        "category": "Parkering",
        "source": "Statens vegvesen",
        "expected_interval_minutes": 30,
        "warning_after_minutes": 90,
        "description": "Løpende berikelse av registreringsnummer som mangler tekniske kjøretøydata.",
    },
}


CONFIG_DEFINITIONS = {
    "lights": {
        "title": "Lysstyring",
        "subtitle": "Terskler, driftstid og forklaring for utelys",
        "theme": "theme-light",
        "settings_path": "/lys/innstillinger",
        "api_path": "/api/config/lights",
        "groups": [
            {
                "title": "Felles drift",
                "description": "Gjelder alle lys unntatt parkeringslys der feltet sier at åpningstid ignoreres.",
                "fields": [
                    {"key": "open_from", "label": "Start før åpning", "type": "time", "default": "06:45", "unit": "", "help": "Tidligste tidspunkt lys som følger åpningstid kan være på."},
                    {"key": "close_at", "label": "Normal av-tid", "type": "time", "default": "23:00", "unit": "", "help": "Standard av-tid for lys som følger åpningstid."},
                    {"key": "entrance_close_at", "label": "Inngang av-tid", "type": "time", "default": "23:20", "unit": "", "help": "6xspot over inngang kan stå litt lenger enn øvrige fasadelys."},
                    {"key": "decision_delay_seconds", "label": "Bekreftelsestid", "type": "int", "default": 120, "unit": "sek", "help": "Lux må bekreftes etter denne forsinkelsen før lys endres."},
                    {"key": "config_poll_minutes", "label": "HC3 henter config", "type": "int", "default": 5, "unit": "min", "help": "Hvor ofte HC3 bør kontrollere om versjon er endret."},
                ],
            },
            {
                "title": "Luxgrenser",
                "description": "På-grense er lav lux. Av-grense er høyere lux for å gi hysterese og unngå flimring.",
                "fields": [
                    {"key": "lyslist_on_lux", "label": "Lyslist på under", "type": "float", "default": 1000, "unit": "lux", "help": "Dekorlys på fasade."},
                    {"key": "lyslist_off_lux", "label": "Lyslist av over", "type": "float", "default": 1500, "unit": "lux", "help": "Må være høyere enn på-grensen."},
                    {"key": "reklame_on_lux", "label": "Reklame på under", "type": "float", "default": 500, "unit": "lux", "help": "Reklameplakater på tegelfasade."},
                    {"key": "reklame_off_lux", "label": "Reklame av over", "type": "float", "default": 700, "unit": "lux", "help": "Må være høyere enn på-grensen."},
                    {"key": "spot_glass_on_lux", "label": "Spot foran på under", "type": "float", "default": 1500, "unit": "lux", "help": "Spot 275 og 299 foran glassveggen."},
                    {"key": "spot_glass_off_lux", "label": "Spot foran av over", "type": "float", "default": 2000, "unit": "lux", "help": "Må være høyere enn på-grensen."},
                    {"key": "spot_inngang_on_lux", "label": "6xspot inngang på under", "type": "float", "default": 100, "unit": "lux", "help": "Behovsstyrt inngangslys."},
                    {"key": "spot_inngang_off_lux", "label": "6xspot inngang av over", "type": "float", "default": 150, "unit": "lux", "help": "Må være høyere enn på-grensen."},
                    {"key": "parkering_on_lux", "label": "Parkering på under", "type": "float", "default": 50, "unit": "lux", "help": "Parkeringslys/gatelys."},
                    {"key": "parkering_off_lux", "label": "Parkering av over", "type": "float", "default": 80, "unit": "lux", "help": "Parkeringslys følger ikke åpningstid."},
                ],
            },
        ],
    },
    "ventilation": {
        "title": "Ventilasjonsstyring",
        "subtitle": "Temperaturgrenser, driftstid og forklaring for vifter",
        "theme": "theme-vent",
        "settings_path": "/ventilasjon/innstillinger",
        "api_path": "/api/config/ventilation",
        "groups": [
            {
                "title": "Drift og sikkerhet",
                "description": "Disse grensene hindrer trekk, undertrykk og unødvendig varmetap.",
                "fields": [
                    {"key": "open_from", "label": "Åpningstid fra", "type": "time", "default": "07:00", "unit": "", "help": "Normal start for ventilasjonslogikk."},
                    {"key": "close_at", "label": "Stenging", "type": "time", "default": "23:00", "unit": "", "help": "Normal stengetid."},
                    {"key": "pre_cooling_from", "label": "Forkjøling fra", "type": "time", "default": "05:30", "unit": "", "help": "Kan brukes på varme dager når ute fortsatt er kaldt."},
                    {"key": "exhaust_stop_before_close_minutes", "label": "Stopp avtrekk før stenging", "type": "int", "default": 60, "unit": "min", "help": "Sparer varme mot natten."},
                    {"key": "mechanical_min_outdoor_temp", "label": "Sperr mekanisk under", "type": "float", "default": 7.0, "unit": "°C", "help": "Avtrekk og innluft stoppes når ute er kaldere enn dette."},
                    {"key": "intake_min_outdoor_temp", "label": "Innluft minimum ute", "type": "float", "default": 10.0, "unit": "°C", "help": "Hindrer kald innblåsing."},
                ],
            },
            {
                "title": "Innluft",
                "description": "Innluft skal bare gå når ute faktisk hjelper, og alltid gi luft inn dersom avtrekk er aktivt.",
                "fields": [
                    {"key": "vip_start_temp", "label": "VIP innluft start", "type": "float", "default": 23.8, "unit": "°C", "help": "VIP-viften vurderer primært VIP-temperatur."},
                    {"key": "vip_stop_temp", "label": "VIP innluft stopp", "type": "float", "default": 23.2, "unit": "°C", "help": "Lavere enn start for hysterese."},
                    {"key": "floor_start_temp", "label": "1./2.etg innluft start", "type": "float", "default": 23.8, "unit": "°C", "help": "2.etg-viften vurderer 1.etg og 2.etg."},
                    {"key": "floor_stop_temp", "label": "1./2.etg innluft stopp", "type": "float", "default": 23.2, "unit": "°C", "help": "Lavere enn start for hysterese."},
                    {"key": "outdoor_cooler_delta", "label": "Ute må være kaldere", "type": "float", "default": 1.5, "unit": "°C", "help": "Ute må være minst så mye kaldere enn sonen."},
                    {"key": "max_indoor_heat_need_temp", "label": "Varmebehov under", "type": "float", "default": 21.5, "unit": "°C", "help": "Under denne temperaturen unngår vi kjølende ventilasjon."},
                ],
            },
            {
                "title": "Avtrekk tak/loft",
                "description": "Avtrekk skal ikke gå bare fordi solsenger er i bruk hvis lokalet trenger varme.",
                "fields": [
                    {"key": "loft_exhaust_start_temp", "label": "Takvifte start loft", "type": "float", "default": 30.0, "unit": "°C", "help": "Starter når loftet er varmt nok og ute ikke er for kaldt."},
                    {"key": "loft_exhaust_stop_temp", "label": "Takvifte stopp loft", "type": "float", "default": 28.0, "unit": "°C", "help": "Stopper lavere enn start for hysterese."},
                    {"key": "indoor_allow_exhaust_temp", "label": "Avtrekk tillatt når inne over", "type": "float", "default": 25.0, "unit": "°C", "help": "Hindrer at varme blåses ut når lokalet er kaldt."},
                    {"key": "sunbed_power_1_threshold_w", "label": "Antatt 1 solseng over", "type": "int", "default": 4000, "unit": "W", "help": "Differanse mellom total og målt øvrig forbruk."},
                    {"key": "sunbed_power_2_threshold_w", "label": "Antatt 2 solsenger over", "type": "int", "default": 12000, "unit": "W", "help": "Brukes for vurdering og logging."},
                    {"key": "afterrun_minutes", "label": "Ettergang", "type": "int", "default": 20, "unit": "min", "help": "Hvor lenge vifter kan gå etter siste tydelige varmebelastning."},
                ],
            },
            {
                "title": "Kjeller og avfukter",
                "description": "Avfukteren styres av fukt i kjeller med hysterese.",
                "fields": [
                    {"key": "basement_humidity_start", "label": "Avfukter på over", "type": "float", "default": 60.0, "unit": "%", "help": "Starter avfukter når kjellerfukt er over denne verdien."},
                    {"key": "basement_humidity_stop", "label": "Avfukter av under", "type": "float", "default": 55.0, "unit": "%", "help": "Stopper avfukter når kjellerfukt er under denne verdien."},
                    {"key": "basement_min_temp", "label": "Sperr under kjellertemp", "type": "float", "default": 5.0, "unit": "°C", "help": "Hindrer drift hvis kjelleren er for kald for trygg avfukting."},
                ],
            },
        ],
    },
}


CONTROL_DEVICES = {
    "lights": {
        "lux_sensor": {"key": "lux_ute", "name": "Luxsensor ute", "role": "sensor"},
        "groups": [
            {
                "key": "lyslist",
                "name": "Lyslist fasade",
                "on_lux_key": "lyslist_on_lux",
                "off_lux_key": "lyslist_off_lux",
                "time_from_key": "open_from",
                "time_to_key": "close_at",
                "follows_opening_hours": True,
            },
            {
                "key": "reklame",
                "name": "Reklameplakater tegelfasade",
                "on_lux_key": "reklame_on_lux",
                "off_lux_key": "reklame_off_lux",
                "time_from_key": "open_from",
                "time_to_key": "close_at",
                "follows_opening_hours": True,
            },
            {
                "key": "spot_glass",
                "name": "Spot foran glassvegg",
                "on_lux_key": "spot_glass_on_lux",
                "off_lux_key": "spot_glass_off_lux",
                "time_from_key": "open_from",
                "time_to_key": "close_at",
                "follows_opening_hours": True,
            },
            {
                "key": "spot_inngang",
                "name": "6xspot over inngang",
                "on_lux_key": "spot_inngang_on_lux",
                "off_lux_key": "spot_inngang_off_lux",
                "time_from_key": "open_from",
                "time_to_key": "entrance_close_at",
                "follows_opening_hours": True,
            },
            {
                "key": "parkering",
                "name": "Parkeringslys",
                "on_lux_key": "parkering_on_lux",
                "off_lux_key": "parkering_off_lux",
                "time_from_key": None,
                "time_to_key": None,
                "follows_opening_hours": False,
            },
        ],
    },
    "ventilation": {
        "sensors": {
            "outdoor_temp": {"key": "outdoor_temp", "name": "Utetemperatur"},
            "netatmo_main": {"key": "netatmo_main", "name": "Netatmo hovedenhet"},
            "basement_temp": {"key": "basement_temp", "name": "Kjeller temperatur", "device_id": 444},
            "basement_humidity": {"key": "basement_humidity", "name": "Kjeller fukt", "device_id": 445},
            "passive_intake": {"name": "Pass innluft"},
        },
        "fans": [
            {"key": "vip_intake", "name": "Innluft VIP", "zone": "VIP"},
            {"key": "floor_intake", "name": "Innluft 1./2.etg", "zone": "1.etg/2.etg"},
            {"key": "roof_exhaust", "name": "Takvifte avtrekk", "zone": "Loft"},
            {"key": "dehumidifier_basement", "name": "Avfukter kjeller", "zone": "Kjeller", "device_id": 449},
        ],
    },
}


def config_definition(key: str) -> Optional[Dict[str, Any]]:
    return CONFIG_DEFINITIONS.get(key)


def config_defaults(key: str) -> Dict[str, Any]:
    definition = config_definition(key)
    values: Dict[str, Any] = {}
    if not definition:
        return values
    for group in definition["groups"]:
        for field in group["fields"]:
            values[field["key"]] = deepcopy(field["default"])
    return values


def value_from_payload(data: EventDataIn, key: str):
    explicit = getattr(data, key)
    if explicit is not None:
        return explicit
    return data.values.get(key)


def json_value(value):
    if isinstance(value, (dict, list)):
        import json

        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def repair_mojibake(value: Any) -> Any:
    if not isinstance(value, str) or ("Ã" not in value and "Â" not in value):
        return value
    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value


def room_key_from_name(value: Any) -> Optional[str]:
    text = repair_mojibake(value)
    if not isinstance(text, str):
        return None
    match = re.search(r"\brom\s*0*(\d+)\b", text, re.IGNORECASE)
    if not match:
        return None
    return f"rom_{int(match.group(1)):02d}"


SUN2_ROOM_MAP_BY_DISPLAY = {
    1: {"room_id": "rom-01", "physical_room_number": 1, "display_room_number": 1, "sun2_bed_id": "640"},
    2: {"room_id": "rom-02", "physical_room_number": 2, "display_room_number": 2, "sun2_bed_id": "641"},
    3: {"room_id": "rom-03", "physical_room_number": 3, "display_room_number": 3, "sun2_bed_id": "642"},
    4: {"room_id": "rom-04", "physical_room_number": 4, "display_room_number": 4, "sun2_bed_id": "643"},
    5: {"room_id": "rom-05", "physical_room_number": 5, "display_room_number": 5, "sun2_bed_id": "644"},
    6: {"room_id": "rom-06", "physical_room_number": 6, "display_room_number": 6, "sun2_bed_id": "645"},
    7: {"room_id": "rom-07", "physical_room_number": 7, "display_room_number": 7, "sun2_bed_id": "646"},
    8: {"room_id": "rom-08", "physical_room_number": 8, "display_room_number": 8, "sun2_bed_id": "647"},
    9: {"room_id": "rom-09", "physical_room_number": 9, "display_room_number": 9, "sun2_bed_id": "648"},
    10: {"room_id": "rom-11", "physical_room_number": 11, "display_room_number": 10, "sun2_bed_id": "679"},
    11: {"room_id": "rom-12", "physical_room_number": 12, "display_room_number": 11, "sun2_bed_id": "680"},
    12: {"room_id": "rom-13", "physical_room_number": 13, "display_room_number": 12, "sun2_bed_id": "681"},
}

SUN2_ROOM_UNKNOWN_OLD_10 = {
    "room_id": "rom-10",
    "physical_room_number": 10,
    "display_room_number": None,
    "sun2_bed_id": "649",
}


def normalize_room_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower().replace("_", "-")
    match = re.search(r"(?:rom[-\s]*)?0*(\d{1,2})$", text)
    if not match:
        return None
    number = int(match.group(1))
    if 1 <= number <= 13:
        return f"rom-{number:02d}"
    return None


def sun2_room_identity(value: Any = None, room_id: Any = None, bed_id: Any = None) -> Dict[str, Any]:
    explicit_room_id = normalize_room_id(room_id)
    bed_id_text = (repair_mojibake(bed_id) or "").strip()
    if explicit_room_id:
        physical_number = int(explicit_room_id.rsplit("-", 1)[-1])
        identity = {
            "room_id": explicit_room_id,
            "physical_room_number": physical_number,
            "display_room_number": None,
            "sun2_bed_id": bed_id_text or None,
        }
        for item in list(SUN2_ROOM_MAP_BY_DISPLAY.values()) + [SUN2_ROOM_UNKNOWN_OLD_10]:
            if item["room_id"] == explicit_room_id:
                identity.update(item)
                if bed_id_text:
                    identity["sun2_bed_id"] = bed_id_text
                break
        return identity

    text_value = repair_mojibake(value)
    text = str(text_value).strip() if text_value is not None else ""
    if text in {".", "-", ""}:
        identity = dict(SUN2_ROOM_UNKNOWN_OLD_10)
        if bed_id_text:
            identity["sun2_bed_id"] = bed_id_text
        return identity

    match = re.search(r"\brom\s*0*(\d{1,2})\b", text, re.IGNORECASE)
    if match:
        display_number = int(match.group(1))
        identity = dict(SUN2_ROOM_MAP_BY_DISPLAY.get(display_number) or {})
        if identity:
            if bed_id_text:
                identity["sun2_bed_id"] = bed_id_text
            return identity

    explicit_from_value = normalize_room_id(text)
    if explicit_from_value:
        return sun2_room_identity(room_id=explicit_from_value, bed_id=bed_id_text)
    return {"room_id": None, "physical_room_number": None, "display_room_number": None, "sun2_bed_id": bed_id_text or None}


def sun2_room_label(room_id: Optional[str], source_name: Optional[str] = None) -> str:
    normalized = normalize_room_id(room_id)
    source = (repair_mojibake(source_name) or "").strip()
    if not normalized:
        return source or "-"
    number = int(normalized.rsplit("-", 1)[-1])
    if source and source not in {".", "-"}:
        return f"Rom {number} - {source}"
    if normalized == "rom-10":
        return "Rom 10 - tidligere SUN2-navn '.'"
    return f"Rom {number}"


SUN2_ROOM_OPTIONS = [
    {"value": f"rom-{number:02d}", "label": f"Rom {number}"}
    for number in range(1, 14)
]


def bool_value(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "ja"}:
            return True
        if normalized in {"0", "false", "no", "off", "nei"}:
            return False
    return None


def int_value(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def float_value(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        normalized = value.strip().replace("\u00a0", "").replace(" ", "")
        if "," in normalized and "." in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        elif "," in normalized:
            normalized = normalized.replace(",", ".")
        value = normalized
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def nested_total(value: Any) -> Optional[float]:
    if not isinstance(value, dict):
        return None
    return float_value(value.get("Total"))


def consumption_value(value: Any) -> Optional[float]:
    if not isinstance(value, dict):
        return None
    return float_value(value.get("Value"))


def meter_id_from_filename(filename: Optional[str]) -> str:
    match = re.match(r"(\d+)", filename or "")
    return match.group(1) if match else "elvia"


def parse_elvia_json_payload(content: bytes, filename: str) -> Dict[str, Any]:
    data = json.loads(content.decode("utf-8-sig"))
    meter_id = meter_id_from_filename(filename)
    rows: list[Dict[str, Any]] = []
    day_ids = set()
    month_days: Dict[str, set[int]] = {}
    estimated_hours = 0

    for year_data in data.get("Years") or []:
        for month_data in year_data.get("Months") or []:
            for day_data in month_data.get("Days") or []:
                day = date(int(day_data["Year"]), int(day_data["Month"]), int(day_data["Day"]))
                day_ids.add(day)
                month_key = f"{day.year:04d}-{day.month:02d}"
                month_days.setdefault(month_key, set()).add(day.day)
                for hour_data in day_data.get("Hours") or []:
                    measured_at = datetime(
                        int(hour_data["Year"]),
                        int(hour_data["Month"]),
                        int(hour_data["Day"]),
                        int(hour_data["Hour"]),
                    )
                    consumption = consumption_value(hour_data.get("Consumption"))
                    if consumption is None:
                        continue
                    production = consumption_value(hour_data.get("Production"))
                    status = (hour_data.get("Consumption") or {}).get("Status")
                    is_estimated = status != "OK"
                    if is_estimated:
                        estimated_hours += 1
                    rows.append(
                        {
                            "meter_id": meter_id,
                            "measured_at": measured_at,
                            "stat_date": measured_at.date(),
                            "year": measured_at.year,
                            "month": measured_at.month,
                            "day": measured_at.day,
                            "hour": measured_at.hour,
                            "consumption_kwh": consumption,
                            "production_kwh": production,
                            "status": status,
                            "is_verified": bool_value((hour_data.get("Consumption") or {}).get("IsVerified")),
                            "is_estimated": is_estimated,
                            "is_public_holiday": bool_value(hour_data.get("IsPublicHoliday")),
                            "use_weekend_prices": bool_value(hour_data.get("UseWeekendPrices")),
                            "raw": hour_data,
                        }
                    )

    rows.sort(key=lambda item: item["measured_at"])
    first_at = rows[0]["measured_at"] if rows else None
    last_at = rows[-1]["measured_at"] if rows else None
    partial_months = []
    for month_key, days in sorted(month_days.items()):
        year_number, month_number = [int(part) for part in month_key.split("-")]
        expected_days = calendar.monthrange(year_number, month_number)[1]
        if len(days) != expected_days:
            partial_months.append(
                {
                    "month": month_key,
                    "days": len(days),
                    "expected_days": expected_days,
                    "first_day": min(days),
                    "last_day": max(days),
                }
            )
    return {
        "meter_id": meter_id,
        "rows": rows,
        "first_at": first_at,
        "last_at": last_at,
        "days_count": len(day_ids),
        "hours_count": len(rows),
        "total_kwh": sum(row["consumption_kwh"] for row in rows),
        "estimated_hours_count": estimated_hours,
        "partial_months": partial_months,
        "source_file": filename,
    }


def timestamp_value(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(value)
    if isinstance(value, str):
        parsed = parse_datetime(value)
        if parsed:
            return parsed
        try:
            return datetime.utcfromtimestamp(int(value))
        except (TypeError, ValueError):
            return None
    return None


def area_m2_from_payload(value: Any) -> Optional[float]:
    number = float_value(value)
    if number is None:
        return None
    if number > 100000:
        return round(number / 1_000_000, 2)
    return number


def first_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    if isinstance(value, dict):
        return value
    return {}


def roborock_schedule_params(schedule: Dict[str, Any]) -> Dict[str, Any]:
    params = (((schedule.get("param") or {}).get("params")) or [])
    return params[0] if params and isinstance(params[0], dict) else {}


def hash_access_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_username(value: str) -> str:
    return value.strip().casefold()


def credential_hash(username: str, password: str) -> str:
    return hash_access_key(normalize_username(username) + "\0" + password)


def credential_prefix(username: str, password: str) -> str:
    return "key_" + credential_hash(username, password)[:8]


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def presented_credentials(request: Request) -> tuple[Optional[str], Optional[str]]:
    username = (
        request.query_params.get("username")
        or request.headers.get("x-access-username")
        or request.cookies.get(AUTH_USER_COOKIE_NAME)
    )
    password = (
        request.query_params.get("password")
        or request.headers.get("x-access-password")
        or request.cookies.get(AUTH_COOKIE_NAME)
    )
    return username, password


def wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept or "*/*" in accept


def is_public_request(request: Request) -> bool:
    path = request.url.path
    if path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
        return True
    if request.method == "GET" and (path == "/api/config" or path.startswith("/api/config/")):
        return True
    return request.method == "POST" and path in {"/events", "/log", "/api/energi/fibaro", "/api/hc3/measurements/log"}


async def parse_form_body(request: Request) -> Dict[str, str]:
    raw = (await request.body()).decode("utf-8")
    parsed = parse_qs(raw, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


async def log_access_attempt(
    request: Request,
    success: bool,
    reason: str,
    access_key: Optional[AccessKey] = None,
    attempted_username: Optional[str] = None,
):
    notify_master = success and should_publish_access_ntfy(request, access_key, reason)
    now_value = datetime.utcnow()
    normalized_attempted_username = normalize_username(attempted_username or "")
    async with async_session() as session:
        log_row = AccessLog(
            access_key_id=access_key.id if access_key else None,
            key_name=access_key.name if access_key else normalized_attempted_username or None,
            key_prefix=access_key.key_prefix if access_key else None,
            path=request.url.path,
            method=request.method,
            ip=client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
            success=success,
            reason=reason,
        )
        session.add(log_row)
        if access_key and success:
            values = {
                "last_seen_at": now_value,
                "last_ip": client_ip(request),
                "last_user_agent": request.headers.get("user-agent", ""),
                "uses_count": func.coalesce(AccessKey.uses_count, 0) + 1,
            }
            if notify_master:
                values["last_notified_at"] = now_value
            await session.execute(update(AccessKey).where(AccessKey.id == access_key.id).values(**values))
        elif not success and normalized_attempted_username and normalized_attempted_username != "master":
            await session.flush()
            user_result = await session.execute(
                select(AccessKey)
                .where(AccessKey.name == normalized_attempted_username)
                .where(AccessKey.is_master == False)
                .where(AccessKey.active == True)
                .order_by(AccessKey.id.desc())
                .limit(1)
            )
            user_key = user_result.scalars().first()
            if user_key:
                recent_failures = (
                    await session.execute(
                        select(AccessLog.success)
                        .where(AccessLog.key_name == normalized_attempted_username)
                        .order_by(AccessLog.timestamp.desc(), AccessLog.id.desc())
                        .limit(ACCESS_FAILED_DISABLE_THRESHOLD)
                    )
                ).scalars().all()
                if len(recent_failures) >= ACCESS_FAILED_DISABLE_THRESHOLD and all(value is False for value in recent_failures):
                    user_key.active = False
                    log_row.access_key_id = user_key.id
                    log_row.key_prefix = user_key.key_prefix
                    log_row.reason = f"{reason}_auto_deactivated_after_{ACCESS_FAILED_DISABLE_THRESHOLD}_failures"
        await session.commit()
    if notify_master and access_key:
        asyncio.create_task(
            publish_access_ntfy(
                access_key.name,
                access_key.role,
                access_key.is_master,
                request.method,
                request.url.path,
                client_ip(request),
                reason,
            )
        )


async def find_access_key(username: Optional[str], password: Optional[str]) -> Optional[AccessKey]:
    if not username or not password:
        return None
    normalized_username = normalize_username(username)
    if normalized_username == "master":
        hashed = hash_access_key(password)
    else:
        hashed = credential_hash(normalized_username, password)
    async with async_session() as session:
        result = await session.execute(
            select(AccessKey)
            .where(AccessKey.name == normalized_username)
            .where(AccessKey.key_hash == hashed)
            .where(AccessKey.active == True)
        )
        return result.scalars().first()


def require_master(request: Request):
    if not getattr(request.state, "auth_is_master", False):
        return JSONResponse({"detail": "Masterbruker kreves"}, status_code=403)
    return None


def access_role(access_key: Optional[AccessKey]) -> str:
    if not access_key:
        return "viewer"
    if access_key.is_master:
        return "master"
    role = (access_key.role or "viewer").strip().lower()
    if role not in ["viewer", "settings"]:
        return "viewer"
    return role


def access_role_label(role: Optional[str], is_master: bool = False) -> str:
    if is_master or role == "master":
        return "Master"
    if role == "settings":
        return "Innstillinger"
    return "Vanlig"


def require_settings_access(request: Request):
    if not getattr(request.state, "auth_can_settings", False):
        return JSONResponse({"detail": "Tilgang til innstillinger kreves"}, status_code=403)
    return None


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def sample_bucket(value: Optional[datetime]) -> datetime:
    stamp = value or datetime.utcnow()
    minute = (stamp.minute // 5) * 5
    return stamp.replace(minute=minute, second=0, microsecond=0)


def normalize_local_naive(value: Optional[datetime]) -> Optional[datetime]:
    if not value:
        return None
    if value.tzinfo is not None:
        return value.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return value.replace(tzinfo=None)


def utc_naive_to_local_naive(value: Optional[datetime]) -> Optional[datetime]:
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(LOCAL_TZ).replace(tzinfo=None)


def local_naive_to_utc_naive(value: Optional[datetime]) -> Optional[datetime]:
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=LOCAL_TZ)
    return value.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def minute_bucket(value: Optional[datetime]) -> datetime:
    stamp = normalize_local_naive(value) or local_now_naive()
    return stamp.replace(second=0, microsecond=0)


def parse_day(value: Optional[str]) -> date:
    if value:
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return datetime.now(LOCAL_TZ).date()


def parse_config_value(raw: Optional[str], field: Dict[str, Any]):
    field_type = field.get("type")
    if field_type == "bool":
        return raw in {"on", "true", "1", "yes"}
    if raw in (None, ""):
        return deepcopy(field["default"])
    if field_type == "int":
        try:
            return int(float(raw))
        except ValueError:
            return int(field["default"])
    if field_type == "float":
        try:
            return float(str(raw).replace(",", "."))
        except ValueError:
            return float(field["default"])
    return str(raw).strip()


def merge_config_values(key: str, values: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged = config_defaults(key)
    if values:
        for item_key, value in values.items():
            if item_key in merged:
                merged[item_key] = value
    return merged


def config_values_from_form(key: str, form: Dict[str, str]) -> Dict[str, Any]:
    definition = config_definition(key)
    values = config_defaults(key)
    if not definition:
        return values
    for group in definition["groups"]:
        for field in group["fields"]:
            values[field["key"]] = parse_config_value(form.get(field["key"]), field)
    return values


def time_minutes(value: str) -> Optional[int]:
    try:
        hour, minute = str(value).split(":", 1)
        return int(hour) * 60 + int(minute)
    except (TypeError, ValueError):
        return None


def validate_config_values(key: str, values: Dict[str, Any]) -> list[str]:
    errors: list[str] = []

    def require_increasing(label: str, low_key: str, high_key: str):
        if float(values[high_key]) <= float(values[low_key]):
            errors.append(f"{label}: av-grensen må være høyere enn på-grensen.")

    def require_lower_stop(label: str, stop_key: str, start_key: str):
        if float(values[stop_key]) >= float(values[start_key]):
            errors.append(f"{label}: stoppgrensen må være lavere enn startgrensen.")

    def require_time_order(label: str, start_key: str, stop_key: str):
        start = time_minutes(str(values[start_key]))
        stop = time_minutes(str(values[stop_key]))
        if start is None or stop is None:
            errors.append(f"{label}: tidspunkt må være på formatet HH:MM.")
        elif stop <= start:
            errors.append(f"{label}: sluttid må være senere enn starttid.")

    if key == "lights":
        require_time_order("Lys åpningstid", "open_from", "close_at")
        require_increasing("Lyslist", "lyslist_on_lux", "lyslist_off_lux")
        require_increasing("Reklameplakater", "reklame_on_lux", "reklame_off_lux")
        require_increasing("Spot foran glassvegg", "spot_glass_on_lux", "spot_glass_off_lux")
        require_increasing("6xspot inngang", "spot_inngang_on_lux", "spot_inngang_off_lux")
        require_increasing("Parkeringslys", "parkering_on_lux", "parkering_off_lux")
        if int(values["decision_delay_seconds"]) < 0 or int(values["decision_delay_seconds"]) > 900:
            errors.append("Bekreftelsestid bør være mellom 0 og 900 sekunder.")
        if int(values["config_poll_minutes"]) < 1 or int(values["config_poll_minutes"]) > 60:
            errors.append("HC3 config-henting bør være mellom 1 og 60 minutter.")
    elif key == "ventilation":
        require_time_order("Ventilasjon åpningstid", "open_from", "close_at")
        require_lower_stop("VIP innluft", "vip_stop_temp", "vip_start_temp")
        require_lower_stop("1./2.etg innluft", "floor_stop_temp", "floor_start_temp")
        require_lower_stop("Takvifte loft", "loft_exhaust_stop_temp", "loft_exhaust_start_temp")
        require_lower_stop("Avfukter kjeller", "basement_humidity_stop", "basement_humidity_start")
        if int(values["afterrun_minutes"]) < 0 or int(values["afterrun_minutes"]) > 180:
            errors.append("Ettergang bør være mellom 0 og 180 minutter.")
        if int(values["exhaust_stop_before_close_minutes"]) < 0 or int(values["exhaust_stop_before_close_minutes"]) > 240:
            errors.append("Stopp avtrekk før stenging bør være mellom 0 og 240 minutter.")

    return errors


def light_rules(values: Dict[str, Any]) -> list[str]:
    return [
        f"Lyslist slås på når lux er under {values['lyslist_on_lux']} og av når lux er over {values['lyslist_off_lux']}, innen {values['open_from']}-{values['close_at']}.",
        f"Reklameplakater slås på når lux er under {values['reklame_on_lux']} og av når lux er over {values['reklame_off_lux']}, innen {values['open_from']}-{values['close_at']}.",
        f"Spot foran glassvegg slås på under {values['spot_glass_on_lux']} lux og av over {values['spot_glass_off_lux']} lux, innen {values['open_from']}-{values['close_at']}.",
        f"6xspot over inngang slås på under {values['spot_inngang_on_lux']} lux og av over {values['spot_inngang_off_lux']} lux, fra {values['open_from']} til {values['entrance_close_at']}.",
        f"Parkeringslys slås på under {values['parkering_on_lux']} lux og av over {values['parkering_off_lux']} lux uavhengig av åpningstid.",
        f"Alle lysendringer bekreftes etter {values['decision_delay_seconds']} sekunder for å unngå flimring.",
    ]


def ventilation_rules(values: Dict[str, Any]) -> list[str]:
    return [
        f"Normal ventilasjon vurderes mellom {values['open_from']} og {values['close_at']}; forkjøling kan starte {values['pre_cooling_from']} på varme dager.",
        f"Mekanisk ventilasjon sperres når utetemperaturen er under {values['mechanical_min_outdoor_temp']}°C.",
        f"VIP innluft starter over {values['vip_start_temp']}°C og stopper under {values['vip_stop_temp']}°C når ute er minst {values['outdoor_cooler_delta']}°C kaldere.",
        f"2.etg innluft vurderer 1.etg og 2.etg, starter over {values['floor_start_temp']}°C og stopper under {values['floor_stop_temp']}°C.",
        f"Takvifte starter når loftet er over {values['loft_exhaust_start_temp']}°C og stopper under {values['loft_exhaust_stop_temp']}°C, men ikke hvis inne er under {values['indoor_allow_exhaust_temp']}°C.",
        f"Avtrekk stoppes {values['exhaust_stop_before_close_minutes']} minutter før stenging for å spare varme mot natten.",
        "Hvis avtrekk er aktivt skal minst én innluftsvifte være tilgjengelig, så vi unngår unødvendig undertrykk.",
    ]


def config_rules(key: str, values: Dict[str, Any]) -> list[str]:
    if key == "lights":
        return light_rules(values)
    if key == "ventilation":
        return ventilation_rules(values)
    return []


def config_summary_rows(key: str, values: Dict[str, Any]) -> list[Dict[str, str]]:
    if key == "lights":
        rows = []
        for group in CONTROL_DEVICES["lights"]["groups"]:
            window = "Hele døgnet"
            if group["follows_opening_hours"]:
                window = f"{values[group['time_from_key']]}-{values[group['time_to_key']]}"
            rows.append(
                {
                    "name": group["name"],
                    "device": group["key"],
                    "start": f"PÅ under {values[group['on_lux_key']]} lux",
                    "stop": f"AV over {values[group['off_lux_key']]} lux",
                    "window": window,
                    "note": "Styres av lux og tidsvindu" if group["follows_opening_hours"] else "Styres av lux uavhengig av åpningstid",
                }
            )
        return rows

    if key == "ventilation":
        return [
            {
                "name": "Innluft VIP",
                "device": "vip_intake",
                "start": f"Start over {values['vip_start_temp']}°C",
                "stop": f"Stopp under {values['vip_stop_temp']}°C",
                "window": f"{values['open_from']}-{values['close_at']}",
                "note": f"VIP vurderes mot ute minst {values['outdoor_cooler_delta']}°C kaldere",
            },
            {
                "name": "Innluft 1./2.etg",
                "device": "floor_intake",
                "start": f"Start over {values['floor_start_temp']}°C",
                "stop": f"Stopp under {values['floor_stop_temp']}°C",
                "window": f"{values['open_from']}-{values['close_at']}",
                "note": "Bruker 1.etg og 2.etg som grunnlag",
            },
            {
                "name": "Takvifte avtrekk",
                "device": "roof_exhaust",
                "start": f"Loft over {values['loft_exhaust_start_temp']}°C",
                "stop": f"Loft under {values['loft_exhaust_stop_temp']}°C",
                "window": f"Stopper {values['exhaust_stop_before_close_minutes']} min før stenging",
                "note": f"Ikke tillatt hvis inne er under {values['indoor_allow_exhaust_temp']}°C",
            },
            {
                "name": "Avfukter kjeller",
                "device": "dehumidifier_basement",
                "start": f"Fukt over {values['basement_humidity_start']}%",
                "stop": f"Fukt under {values['basement_humidity_stop']}%",
                "window": f"Sperret under {values['basement_min_temp']}°C",
                "note": "Bruker kjeller temperatur/fukt fra HC3 444/445",
            },
            {
                "name": "Mekanisk sperre",
                "device": "-",
                "start": f"Tillatt over {values['mechanical_min_outdoor_temp']}°C ute",
                "stop": f"Sperret under {values['mechanical_min_outdoor_temp']}°C ute",
                "window": "Gjelder alle vifter",
                "note": "Hindrer kald trekk og unødvendig varmetap",
            },
        ]

    return []


def config_stat_cards(key: str, values: Dict[str, Any], version: int) -> list[Dict[str, str]]:
    if key == "lights":
        return [
            {"label": "Aktiv versjon", "value": str(version), "detail": "HC3 leser denne versjonen"},
            {"label": "Runner-scene", "value": "362", "detail": "Kortkjørende Lua-styring"},
            {"label": "Luxsensor", "value": "433", "detail": "Brukes av alle lysregler"},
            {"label": "Sjekkintervall", "value": f"{values['config_poll_minutes']} min", "detail": "Trigger-scenen starter runneren"},
        ]
    if key == "ventilation":
        return [
            {"label": "Aktiv versjon", "value": str(version), "detail": "HC3 leser denne versjonen"},
            {"label": "Runner-scene", "value": "363", "detail": "Kortkjørende Lua-styring"},
            {"label": "Driftstid", "value": f"{values['open_from']}-{values['close_at']}", "detail": "Normal vurderingsperiode"},
            {"label": "Utesperre", "value": f"{values['mechanical_min_outdoor_temp']}°C", "detail": "Stopper mekanisk ventilasjon"},
        ]
    return []


def config_operational_notes(key: str, values: Dict[str, Any]) -> list[Dict[str, str]]:
    if key == "lights":
        return [
            {
                "title": "Når tar endringen effekt?",
                "text": f"Trigger-scenen starter lys-runneren hvert {values['config_poll_minutes']} minutt. Runneren henter alltid siste config-versjon fra appen før den vurderer lux.",
            },
            {
                "title": "Rask test",
                "text": "Sett globalvariabelen UTE_LYS_TEST_LUX i HC3 til ønsket lux-verdi og kjør scene 362. Variabelen tømmes automatisk etter testen.",
            },
            {
                "title": "Hysterese",
                "text": "Lys slås på under på-grensen og av over av-grensen. Hvis lux ligger mellom disse verdiene beholdes gjeldende status.",
            },
        ]
    if key == "ventilation":
        return [
            {
                "title": "Når tar endringen effekt?",
                "text": "Trigger-scenen starter ventilasjons-runneren hvert 5. minutt. Runneren henter alltid siste config-versjon fra appen før den styrer viftene.",
            },
            {
                "title": "Rask test",
                "text": "Bruk VENT_TEST_TEMP_INNE, VENT_TEST_TEMP_UTE og VENT_TEST_DIFF_W i HC3 og kjør scene 363. Testvariablene tømmes automatisk etter kjøring.",
            },
            {
                "title": "Sikkerhet",
                "text": "Mekanisk ventilasjon sperres ved for lav utetemperatur, og avtrekk skal ikke gå uten at innluft er vurdert samtidig.",
            },
        ]
    return []


def config_devices(key: str) -> Dict[str, Any]:
    return deepcopy(CONTROL_DEVICES.get(key, {}))


def config_payload(row: ControlConfig) -> Dict[str, Any]:
    values = merge_config_values(row.key, row.values)
    return {
        "system": row.key,
        "version": row.version,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "updated_by": row.updated_by,
        "values": values,
        "devices": config_devices(row.key),
        "rules": config_rules(row.key, values),
        "fallback_note": "HC3 skal bruke sist kjente verdier hvis API-et ikke kan nås.",
    }


async def get_or_create_config(session, key: str) -> Optional[ControlConfig]:
    if key not in CONFIG_DEFINITIONS:
        return None
    row = (await session.execute(select(ControlConfig).where(ControlConfig.key == key))).scalars().first()
    if row:
        row.values = merge_config_values(key, row.values)
        return row
    row = ControlConfig(key=key, version=1, values=config_defaults(key), updated_by="system")
    session.add(row)
    session.add(ControlConfigHistory(config_key=key, version=1, values=row.values, changed_by="system", reason="Standardverdier opprettet"))
    await session.commit()
    await session.refresh(row)
    return row


def day_zoom_config(value: Optional[str]):
    for option in DAY_ZOOM_OPTIONS:
        if option["key"] == value:
            return option
    return DAY_ZOOM_OPTIONS[0]


def day_zoom_window(selected_day: date, zoom_key: Optional[str]):
    config = day_zoom_config(zoom_key)
    day_start = datetime.combine(selected_day, time.min)
    window_start = day_start + timedelta(hours=config["start_hour"])
    window_end = day_start + timedelta(hours=config["end_hour"])
    ticks = [
        {
            "label": f"{hour:02d}" if hour < 24 else "24",
            "left": percent_between(day_start + timedelta(hours=hour), window_start, window_end),
        }
        for hour in config["ticks"]
    ]
    return config, window_start, window_end, ticks


def local_now_naive() -> datetime:
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)


def display_action(action: Optional[str]) -> str:
    if action == "PAA":
        return "PÅ"
    return action or ""


def clean_display_text(value: Optional[str]) -> str:
    return (value or "").replace("innbl?sing", "innblåsing").replace("innblasing", "innblåsing").replace("KJ?LING", "KJØLING").replace("KJOLING", "KJØLING").replace("kj?lebehov", "kjølebehov").replace("kjolebehov", "kjølebehov")


def ntfy_host() -> str:
    parsed = urlparse(NTFY_BASE_URL)
    return parsed.netloc or parsed.path.strip("/")


def ntfy_topic_url(topic: str) -> str:
    return f"{NTFY_BASE_URL}/{quote(topic, safe='')}"


def ntfy_subscribe_url(topic: str, display_name: str) -> str:
    return f"ntfy://{ntfy_host()}/{quote(topic, safe='')}?display={quote_plus(display_name)}"


def publish_ntfy_message(topic: str, title: str, message: str, tags: str = "", priority: str = "3") -> None:
    headers = {"Title": title, "Priority": priority}
    if tags:
        headers["Tags"] = tags
    request = urllib.request.Request(
        ntfy_topic_url(topic),
        data=message.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=NTFY_TIMEOUT_SECONDS):
        pass


def should_publish_access_ntfy(request: Request, access_key: Optional[AccessKey], reason: str) -> bool:
    if not access_key or access_key.is_master:
        return False
    if reason != "login" and (request.method != "GET" or not wants_html(request)):
        return False
    if reason != "login" and request.url.path.startswith("/auth/"):
        return False
    last_notified = access_key.last_notified_at or access_key.last_seen_at
    if not last_notified:
        return True
    return datetime.utcnow() - last_notified >= timedelta(minutes=NTFY_ACCESS_COOLDOWN_MINUTES)


async def publish_access_ntfy(
    username: str,
    role: Optional[str],
    is_master: bool,
    method: str,
    path: str,
    ip: str,
    reason: str,
) -> bool:
    role_label = access_role_label(role, is_master)
    action = "logget inn" if reason == "login" else "bruker løsningen"
    message = (
        f"{username} ({role_label}) {action}. "
        f"Side: {method} {path}. "
        f"IP: {ip or '-'}."
    )
    try:
        await asyncio.to_thread(
            publish_ntfy_message,
            NTFY_ACCESS_TOPIC,
            "SUN2 brukeraktivitet",
            message,
            "bust_in_silhouette",
            "3",
        )
        return True
    except Exception:
        return False


async def publish_light_ntfy(event: OutdoorLightEvent) -> bool:
    state = state_from_event(event)
    if state is None:
        return False
    action = "P\u00c5" if state else "AV"
    device_name = event.device_name or event.device_key or "Ukjent lys"
    pieces = [f"{device_name} er {action}."]
    if event.lux is not None:
        pieces.append(f"Lux: {event.lux:.0f}.")
    detail = clean_display_text(event.reason or event.source or "")
    if detail:
        pieces.append(f"\u00c5rsak: {detail}.")
    try:
        await asyncio.to_thread(
            publish_ntfy_message,
            NTFY_LIGHTS_TOPIC,
            f"SUN2 lys {action}",
            " ".join(pieces),
            "bulb",
            "3",
        )
        return True
    except Exception:
        return False


async def publish_ventilation_ntfy(event: VentilationEvent) -> bool:
    state = state_from_event(event)
    if state is None:
        return False
    action = "P\u00c5" if state else "AV"
    device_name = event.device_name or event.device_key or "Ukjent vifte"
    pieces = [f"{device_name} er {action}."]
    if event.mode:
        pieces.append(f"Modus: {clean_display_text(event.mode)}.")
    temps = []
    if event.temp_1etg is not None:
        temps.append(f"1.etg {event.temp_1etg:.1f}\u00b0")
    if event.temp_2etg is not None:
        temps.append(f"2.etg {event.temp_2etg:.1f}\u00b0")
    if event.temp_vip is not None:
        temps.append(f"VIP {event.temp_vip:.1f}\u00b0")
    if event.humidity_1etg is not None:
        temps.append(f"fukt 1.etg {event.humidity_1etg:.0f}%")
    if event.humidity_2etg is not None:
        temps.append(f"fukt 2.etg {event.humidity_2etg:.0f}%")
    if event.humidity_vip is not None:
        temps.append(f"fukt VIP {event.humidity_vip:.0f}%")
    if event.temp_kjeller is not None:
        temps.append(f"kjeller {event.temp_kjeller:.1f}\u00b0")
    if event.humidity_kjeller is not None:
        temps.append(f"fukt kjeller {event.humidity_kjeller:.0f}%")
    if event.temp_ute is not None:
        temps.append(f"ute {event.temp_ute:.1f}\u00b0")
    if event.temp_loft is not None:
        temps.append(f"loft {event.temp_loft:.1f}\u00b0")
    if temps:
        pieces.append("Temp: " + ", ".join(temps) + ".")
    if event.diff_w is not None:
        pieces.append(f"Diff: {event.diff_w:.0f} W.")
    detail = clean_display_text(event.reason or event.source or "")
    if detail:
        pieces.append(f"\u00c5rsak: {detail}.")
    try:
        await asyncio.to_thread(
            publish_ntfy_message,
            NTFY_VENTILATION_TOPIC,
            f"SUN2 ventilasjon {action}",
            " ".join(pieces),
            "dash",
            "3",
        )
        return True
    except Exception:
        return False


def state_from_event(row):
    if row.action == "PAA":
        return True
    if row.action == "AV":
        return False
    if row.state is not None:
        return bool(row.state)
    return None


def percent_between(value: datetime, start: datetime, end: datetime) -> float:
    total = (end - start).total_seconds()
    if total <= 0:
        return 0
    seconds = (value - start).total_seconds()
    return round(max(0, min(100, seconds / total * 100)), 3)


def span_width(start_value: datetime, end_value: datetime, day_start: datetime, day_end: datetime) -> float:
    return round(max(0, percent_between(end_value, day_start, day_end) - percent_between(start_value, day_start, day_end)), 3)


def add_segment(segments, start_value: datetime, end_value: datetime):
    if end_value <= start_value:
        return
    if segments and segments[-1]["end_dt"] == start_value:
        segments[-1]["end_dt"] = end_value
    else:
        segments.append({"start_dt": start_value, "end_dt": end_value})


def display_segments(raw_segments, day_start: datetime, day_end: datetime):
    return [
        {
            "left": percent_between(segment["start_dt"], day_start, day_end),
            "width": span_width(segment["start_dt"], segment["end_dt"], day_start, day_end),
            "start": segment["start_dt"].strftime("%H:%M"),
            "end": segment["end_dt"].strftime("%H:%M"),
        }
        for segment in raw_segments
    ]


def total_from_segments(segments) -> str:
    total_minutes = int(round(sum((segment["end_dt"] - segment["start_dt"]).total_seconds() / 60 for segment in segments)))
    return f"{total_minutes // 60}t {total_minutes % 60}m"


def lux_scale(values):
    max_value = max([value for value in values if value is not None] or [100])
    for axis_max, step in [(200, 50), (1000, 250), (2000, 500), (5000, 1000), (10000, 2000), (20000, 5000)]:
        if max_value <= axis_max:
            return {"max": float(axis_max), "step": step}
    return {"max": 20000.0, "step": 5000}


def lux_y(value: float, max_lux: float) -> float:
    graph_top = 22
    graph_bottom = 278
    graph_mid = (graph_top + graph_bottom) / 2
    scale_break = 2000.0
    usable = graph_bottom - graph_top
    if max_lux <= 0:
        return graph_bottom
    value = max(0, min(value, max_lux))
    if max_lux <= scale_break:
        return round(graph_bottom - (value / max_lux) * usable, 2)
    if value <= scale_break:
        return round(graph_bottom - (value / scale_break) * (graph_bottom - graph_mid), 2)
    return round(graph_mid - ((value - scale_break) / (max_lux - scale_break)) * (graph_mid - graph_top), 2)


def lux_tick_values(max_lux: float):
    if max_lux <= 200:
        values = [50, 100, 150, 200]
    elif max_lux <= 1000:
        values = [100, 250, 500, 750, 1000]
    elif max_lux <= 2000:
        values = [250, 500, 1000, 1500, 2000]
    else:
        values = [500, 1000, 1500, 2000, 5000, 10000, 15000, 20000]
    return [value for value in values if value <= max_lux]


def lux_tick_label(value: int) -> str:
    if value >= 1000:
        return f"{value // 1000}K" if value % 1000 == 0 else f"{value / 1000:g}K"
    return str(value)


def temp_axis(values):
    valid_values = [float(value) for value in values if value is not None]
    if not valid_values:
        return {"min": 0.0, "max": 30.0, "step": 5.0}

    raw_min = min(valid_values)
    raw_max = max(valid_values)
    lower = math.floor(raw_min - 1)
    upper = math.ceil(raw_max + 1)
    if upper - lower < 4:
        center = (upper + lower) / 2
        lower = math.floor(center - 2)
        upper = math.ceil(center + 2)

    span = upper - lower
    if span <= 8:
        step = 1.0
    elif span <= 16:
        step = 2.0
    else:
        step = 5.0

    lower = math.floor(lower / step) * step
    upper = math.ceil(upper / step) * step
    return {"min": float(lower), "max": float(upper), "step": step}


def temp_y(value: float, axis_min: float, axis_max: float) -> float:
    graph_top = 22
    graph_bottom = 278
    usable = graph_bottom - graph_top
    if axis_max <= axis_min:
        return graph_bottom
    ratio = (value - axis_min) / (axis_max - axis_min)
    return round(graph_bottom - max(0, min(1, ratio)) * usable, 2)


def temp_label(value) -> str:
    if value is None:
        return "-"
    return f"{float(value):.1f}°"


def minutes_since(value: Optional[datetime], now_value: Optional[datetime] = None) -> Optional[int]:
    if not value:
        return None
    now_value = now_value or local_now_naive()
    delta = now_value - value
    return max(0, int(delta.total_seconds() // 60))


def age_label(minutes: Optional[int]) -> str:
    if minutes is None:
        return "Ingen data"
    if minutes < 1:
        return "Akkurat nå"
    if minutes < 60:
        return f"{minutes} min siden"
    hours = minutes // 60
    rest = minutes % 60
    if hours < 24:
        return f"{hours}t {rest}m siden"
    days = hours // 24
    return f"{days}d siden"


def average_value(values):
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def latest_timestamp_from(*rows):
    timestamps = [row.timestamp for row in rows if row is not None and row.timestamp is not None]
    if not timestamps:
        return None
    return max(timestamps)


def nested_extra_value(value, keys):
    if value is None:
        return None
    if isinstance(value, dict):
        for key in keys:
            found = value.get(key)
            if found not in (None, ""):
                if isinstance(found, (dict, list)):
                    nested = nested_extra_value(found, keys)
                    if nested not in (None, ""):
                        return nested
                    continue
                return found
        for child in value.values():
            found = nested_extra_value(child, keys)
            if found not in (None, ""):
                return found
    elif isinstance(value, list):
        for child in value:
            found = nested_extra_value(child, keys)
            if found not in (None, ""):
                return found
    return None


def weather_label(value) -> Optional[str]:
    if value in (None, ""):
        return None
    raw = str(value).strip()
    key = raw.lower().replace("-", "_")
    if key in WEATHER_LABELS:
        return WEATHER_LABELS[key]
    for suffix in ("_day", "_night", "_polartwilight"):
        if key.endswith(suffix) and key[: -len(suffix)] in WEATHER_LABELS:
            return WEATHER_LABELS[key[: -len(suffix)]]
    cleaned = raw.replace("_", " ").replace("-", " ")
    return cleaned[:1].upper() + cleaned[1:] if cleaned else None


def weather_from_rows(*rows) -> Optional[str]:
    keys = [
        "weather_text",
        "weather_type",
        "yr_weather",
        "weather",
        "condition_text",
        "condition",
        "summary",
        "symbol_code",
        "weather_symbol",
        "yr_symbol",
        "next_1_hours_symbol_code",
    ]
    for row in rows:
        if row is None:
            continue
        for attr in ("weather_text", "weather_type", "yr_weather", "weather_symbol", "yr_symbol"):
            label = weather_label(getattr(row, attr, None))
            if label:
                return label
        extra = getattr(row, "extra", None)
        found = nested_extra_value(extra, keys)
        label = weather_label(found)
        if label:
            return label
    return None


def met_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo:
        stamp = stamp.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return stamp


def http_header_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        stamp = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if stamp.tzinfo:
        stamp = stamp.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return stamp


def met_age_seconds(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def met_next_fetch_after(forecast: Optional[Dict[str, Any]], now_value: Optional[datetime] = None) -> datetime:
    now_value = now_value or datetime.utcnow()
    expires_at = (forecast or {}).get("expires_at")
    if isinstance(expires_at, datetime) and expires_at > now_value:
        return expires_at + timedelta(minutes=1)
    return now_value + timedelta(minutes=1)


def met_details(entry: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not entry:
        return {}
    return entry.get("data", {}).get("instant", {}).get("details", {}) or {}


def met_period_details(entry: Optional[Dict[str, Any]], period: str) -> Dict[str, Any]:
    if not entry:
        return {}
    return entry.get("data", {}).get(period, {}).get("details", {}) or {}


def met_period_symbol(entry: Optional[Dict[str, Any]]) -> Optional[str]:
    if not entry:
        return None
    data = entry.get("data", {})
    for period in ("next_1_hours", "next_6_hours", "next_12_hours"):
        symbol = data.get(period, {}).get("summary", {}).get("symbol_code")
        if symbol:
            return symbol
    return None


def met_value(details: Dict[str, Any], key: str) -> Optional[float]:
    value = details.get(key)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def met_entry_at(timeseries: list[Dict[str, Any]], base_time: Optional[datetime], hours: int) -> Optional[Dict[str, Any]]:
    if not timeseries or not base_time:
        return None
    target = base_time + timedelta(hours=hours)
    entries = [(met_time(entry.get("time")), entry) for entry in timeseries]
    entries = [(stamp, entry) for stamp, entry in entries if stamp is not None]
    if not entries:
        return None
    future_entries = [(stamp, entry) for stamp, entry in entries if stamp >= target]
    source = future_entries or entries
    return min(source, key=lambda item: abs((item[0] - target).total_seconds()))[1]


def met_forecast_from_payload(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    timeseries = payload.get("properties", {}).get("timeseries", [])
    if not timeseries:
        return None
    meta = payload.get("properties", {}).get("meta", {}) or {}
    current = timeseries[0]
    forecast_time = met_time(current.get("time"))
    details = met_details(current)
    symbol = met_period_symbol(current)
    next_1h = met_period_details(current, "next_1_hours")
    next_6h = met_period_details(current, "next_6_hours")
    next_12h = met_period_details(current, "next_12_hours")
    next_12h_summary = current.get("data", {}).get("next_12_hours", {}).get("summary", {}) or {}
    forecast: Dict[str, Any] = {
        "symbol": symbol or "",
        "text": weather_label(symbol),
        "api_updated_at": met_time(meta.get("updated_at")),
        "forecast_time": forecast_time,
        "air_temperature": met_value(details, "air_temperature"),
        "air_temperature_percentile_10": met_value(details, "air_temperature_percentile_10"),
        "air_temperature_percentile_90": met_value(details, "air_temperature_percentile_90"),
        "relative_humidity": met_value(details, "relative_humidity"),
        "wind_speed": met_value(details, "wind_speed"),
        "wind_speed_of_gust": met_value(details, "wind_speed_of_gust"),
        "wind_speed_percentile_10": met_value(details, "wind_speed_percentile_10"),
        "wind_speed_percentile_90": met_value(details, "wind_speed_percentile_90"),
        "wind_from_direction": met_value(details, "wind_from_direction"),
        "cloud_area_fraction": met_value(details, "cloud_area_fraction"),
        "cloud_area_fraction_high": met_value(details, "cloud_area_fraction_high"),
        "cloud_area_fraction_medium": met_value(details, "cloud_area_fraction_medium"),
        "cloud_area_fraction_low": met_value(details, "cloud_area_fraction_low"),
        "fog_area_fraction": met_value(details, "fog_area_fraction"),
        "dew_point_temperature": met_value(details, "dew_point_temperature"),
        "air_pressure_at_sea_level": met_value(details, "air_pressure_at_sea_level"),
        "ultraviolet_index_clear_sky": met_value(details, "ultraviolet_index_clear_sky"),
        "precipitation_next_1h": met_value(next_1h, "precipitation_amount"),
        "precipitation_next_1h_min": met_value(next_1h, "precipitation_amount_min"),
        "precipitation_next_1h_max": met_value(next_1h, "precipitation_amount_max"),
        "precipitation_next_6h": met_value(next_6h, "precipitation_amount"),
        "precipitation_next_6h_min": met_value(next_6h, "precipitation_amount_min"),
        "precipitation_next_6h_max": met_value(next_6h, "precipitation_amount_max"),
        "probability_of_precipitation_next_1h": met_value(next_1h, "probability_of_precipitation"),
        "probability_of_precipitation_next_6h": met_value(next_6h, "probability_of_precipitation"),
        "probability_of_precipitation_next_12h": met_value(next_12h, "probability_of_precipitation"),
        "probability_of_thunder_next_1h": met_value(next_1h, "probability_of_thunder"),
        "air_temperature_min_next_6h": met_value(next_6h, "air_temperature_min"),
        "air_temperature_max_next_6h": met_value(next_6h, "air_temperature_max"),
        "symbol_confidence_next_12h": next_12h_summary.get("symbol_confidence"),
    }
    for hours in (1, 3, 6, 12, 24):
        entry = met_entry_at(timeseries, forecast_time, hours)
        forecast[f"temp_{hours}h"] = met_value(met_details(entry), "air_temperature")
        forecast[f"symbol_{hours}h"] = met_period_symbol(entry)
    next_6h_values = []
    if forecast_time:
        for entry in timeseries:
            stamp = met_time(entry.get("time"))
            temp = met_value(met_details(entry), "air_temperature")
            if stamp and temp is not None and forecast_time <= stamp <= forecast_time + timedelta(hours=6):
                next_6h_values.append(temp)
    forecast["temp_min_next_6h"] = min(next_6h_values) if next_6h_values else None
    forecast["temp_max_next_6h"] = max(next_6h_values) if next_6h_values else None
    forecast["raw_meta"] = meta
    forecast["timeseries_count"] = len(timeseries)
    return forecast if forecast["text"] or forecast["air_temperature"] is not None else None


def fetch_met_weather() -> Optional[Dict[str, Any]]:
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/complete?lat={MET_LAT:.4f}&lon={MET_LON:.4f}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": MET_USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            headers = response.headers
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None
    forecast = met_forecast_from_payload(payload)
    if forecast:
        forecast["last_modified"] = http_header_time(headers.get("Last-Modified"))
        forecast["expires_at"] = http_header_time(headers.get("Expires"))
        forecast["age_seconds"] = met_age_seconds(headers.get("Age"))
        forecast["next_fetch_after"] = met_next_fetch_after(forecast)
        forecast["raw_payload"] = payload
        forecast["raw_headers"] = dict(headers.items())
        forecast["raw_endpoint"] = url
        forecast["raw_coordinates"] = {"lat": MET_LAT, "lon": MET_LON}
    return forecast


async def met_weather_cached() -> Optional[Dict[str, Any]]:
    now_value = datetime.utcnow()
    if MET_WEATHER_CACHE["expires"] > now_value:
        return MET_WEATHER_CACHE["value"]
    value = await asyncio.to_thread(fetch_met_weather)
    MET_WEATHER_CACHE["value"] = value
    MET_WEATHER_CACHE["expires"] = met_next_fetch_after(value, now_value) if value else now_value + timedelta(minutes=5)
    return value


def build_now_status(latest_sample, latest_light_sample, latest_light, latest_yr_sample=None):
    indoor_values = [
        {"label": "1.etg", "value": latest_sample.temp_1etg if latest_sample else None},
        {"label": "2.etg", "value": latest_sample.temp_2etg if latest_sample else None},
        {"label": "VIP", "value": latest_sample.temp_vip if latest_sample else None},
        {"label": "Kjeller", "value": latest_sample.temp_kjeller if latest_sample else None},
    ]
    humidity_values = [
        {"label": "1.etg", "value": latest_sample.humidity_1etg if latest_sample else None},
        {"label": "2.etg", "value": latest_sample.humidity_2etg if latest_sample else None},
        {"label": "VIP", "value": latest_sample.humidity_vip if latest_sample else None},
        {"label": "Loft", "value": latest_sample.humidity_loft if latest_sample else None},
        {"label": "Kjeller", "value": latest_sample.humidity_kjeller if latest_sample else None},
        {"label": "Yr", "value": latest_sample.humidity_yr if latest_sample else None},
    ]
    outdoor_ute = None
    outdoor_yr = None
    if latest_sample:
        outdoor_ute = latest_sample.temp_ute if latest_sample.temp_ute is not None else latest_sample.temp_ute_netatmo
        outdoor_yr = latest_sample.temp_yr
    outdoor_yr_api = latest_yr_sample.air_temperature if latest_yr_sample else None
    outdoor_values = [
        {"label": "Ute", "value": outdoor_ute},
        {"label": "Yr HC3", "value": outdoor_yr},
        {"label": "Yr API", "value": outdoor_yr_api},
    ]
    lux = None
    if latest_light_sample and latest_light_sample.lux is not None:
        lux = latest_light_sample.lux
    elif latest_light and latest_light.lux is not None:
        lux = latest_light.lux
    timestamp = latest_timestamp_from(latest_sample, latest_light_sample, latest_light, latest_yr_sample)
    weather = weather_from_rows(latest_yr_sample, latest_light_sample, latest_sample, latest_light)
    outdoor_avg_values = [outdoor_ute, outdoor_yr_api if outdoor_yr_api is not None else outdoor_yr]
    weather_card = {
        "text": weather,
        "temperature": latest_yr_sample.air_temperature if latest_yr_sample else None,
        "temp_6h": latest_yr_sample.temp_6h if latest_yr_sample else None,
        "humidity": latest_yr_sample.relative_humidity if latest_yr_sample else None,
        "wind": latest_yr_sample.wind_speed if latest_yr_sample else None,
        "precipitation": latest_yr_sample.precipitation_next_1h if latest_yr_sample else None,
        "clouds": latest_yr_sample.cloud_area_fraction if latest_yr_sample else None,
        "basement_humidity": latest_sample.humidity_kjeller if latest_sample else None,
        "timestamp": latest_yr_sample.timestamp if latest_yr_sample else None,
        "api_updated_at": latest_yr_sample.api_updated_at if latest_yr_sample else None,
        "expires_at": latest_yr_sample.expires_at if latest_yr_sample else None,
        "next_fetch_after": latest_yr_sample.next_fetch_after if latest_yr_sample else None,
    }
    return {
        "timestamp": timestamp,
        "mode": latest_sample.mode if latest_sample else None,
        "indoor_avg": average_value([item["value"] for item in indoor_values]),
        "indoor_values": indoor_values,
        "humidity_values": humidity_values,
        "outdoor_avg": average_value(outdoor_avg_values),
        "outdoor_values": outdoor_values,
        "lux": lux,
        "weather": weather,
        "weather_card": weather_card,
        "has_data": any(
            value is not None
            for value in [
                lux,
                weather,
                *[item["value"] for item in indoor_values],
                *[item["value"] for item in outdoor_values],
            ]
        ),
    }


def freshness_item(name: str, row, expected_minutes: int, warning_minutes: Optional[int] = None):
    warning_minutes = warning_minutes or expected_minutes * 2
    stamp = row.timestamp if row else None
    age_minutes = minutes_since(stamp)
    if age_minutes is None:
        status = "bad"
        status_text = "Mangler"
    elif age_minutes <= expected_minutes:
        status = "ok"
        status_text = "OK"
    elif age_minutes <= warning_minutes:
        status = "warn"
        status_text = "Treg"
    else:
        status = "bad"
        status_text = "Gammel"
    return {
        "name": name,
        "age": age_label(age_minutes),
        "status": status,
        "status_text": status_text,
        "timestamp": stamp,
    }


def import_job_definition(job_name: str) -> Dict[str, Any]:
    fallback = {
        "title": job_name.replace("_", " ").title(),
        "category": "Annet",
        "source": None,
        "expected_interval_minutes": None,
        "warning_after_minutes": None,
        "description": "",
    }
    return {**fallback, **IMPORT_JOB_DEFINITIONS.get(job_name, {})}


def import_job_status_from_age(stamp: Optional[datetime], expected_minutes: Optional[int], warning_minutes: Optional[int]) -> tuple[str, str]:
    age_minutes = minutes_since(stamp)
    return import_job_status_from_minutes(age_minutes, expected_minutes, warning_minutes)


def import_job_status_from_minutes(age_minutes: Optional[int], expected_minutes: Optional[int], warning_minutes: Optional[int]) -> tuple[str, str]:
    if age_minutes is None:
        return "bad", "Mangler"
    if expected_minutes is None:
        return "ok", "OK"
    warning_minutes = warning_minutes or expected_minutes * 2
    if age_minutes <= expected_minutes:
        return "ok", "OK"
    if age_minutes <= warning_minutes:
        return "warn", "Treg"
    return "bad", "Gammel"


def sun2_sessions_active_minutes_since(stamp: Optional[datetime], now_value: Optional[datetime] = None) -> Optional[int]:
    if stamp is None:
        return None
    now_value = now_value or local_now_naive()
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone(LOCAL_TZ).replace(tzinfo=None)
    if now_value.tzinfo is not None:
        now_value = now_value.astimezone(LOCAL_TZ).replace(tzinfo=None)
    if stamp >= now_value:
        return 0

    total = 0.0
    day = stamp.date()
    while day <= now_value.date():
        active_start = datetime.combine(day, time(hour=SUN2_SESSIONS_QUIET_END_HOUR))
        active_end = datetime.combine(day + timedelta(days=1), time.min)
        segment_start = max(stamp, active_start)
        segment_end = min(now_value, active_end)
        if segment_end > segment_start:
            total += (segment_end - segment_start).total_seconds() / 60
        day += timedelta(days=1)
    return int(total)


def import_job_age(row: Optional[ImportJobStatus]) -> str:
    stamp = row.last_success_at if row else None
    return age_label(minutes_since(stamp))


def format_short_number(value: Any, decimals: int = 0) -> str:
    number = float_or_zero(value)
    if decimals:
        return f"{number:,.{decimals}f}".replace(",", " ")
    return f"{round(number):,}".replace(",", " ")


def format_signed_short_number(value: Any, decimals: int = 0) -> str:
    number = float_or_zero(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{format_short_number(number, decimals)}"


def dashboard_compare_detail(
    label: str,
    current_count: Any,
    current_paid: Any,
    previous_count: Any,
    previous_paid: Any,
) -> str:
    count_delta = float_or_zero(current_count) - float_or_zero(previous_count)
    paid_delta = float_or_zero(current_paid) - float_or_zero(previous_paid)
    return f"vs {label}: {format_signed_short_number(count_delta)} stk / {format_signed_short_number(paid_delta)} kr"


def dashboard_compare_value(current: Any, previous: Any) -> str:
    return f"{format_short_number(current)}/{format_short_number(previous)}"


def dashboard_money_compare(current: Any, previous: Any) -> str:
    return f"{format_short_number(current)}/{format_short_number(previous)} kr"


@lru_cache(maxsize=64)
def easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


@lru_cache(maxsize=4096)
def norwegian_holiday_name(day: date) -> str:
    easter = easter_sunday(day.year)
    holidays = {
        date(day.year, 1, 1): "Nyttårsdag",
        easter - timedelta(days=3): "Skjærtorsdag",
        easter - timedelta(days=2): "Langfredag",
        easter: "1. påskedag",
        easter + timedelta(days=1): "2. påskedag",
        date(day.year, 5, 1): "Arbeidernes dag",
        date(day.year, 5, 17): "17. mai",
        easter + timedelta(days=39): "Kristi himmelfartsdag",
        easter + timedelta(days=49): "1. pinsedag",
        easter + timedelta(days=50): "2. pinsedag",
        date(day.year, 12, 25): "1. juledag",
        date(day.year, 12, 26): "2. juledag",
    }
    return holidays.get(day, "")


def month_distance(a: int, b: int) -> int:
    raw = abs(a - b)
    return min(raw, 12 - raw)


def iter_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def month_end(day: date) -> date:
    return date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])


def weighted_average(values: list[tuple[float, float]]) -> tuple[float, float, int]:
    weighted_sum = sum(value * weight for value, weight in values)
    weight_sum = sum(weight for _, weight in values)
    if weight_sum <= 0:
        return 0.0, 0.0, 0
    return weighted_sum / weight_sum, weight_sum, len(values)


def sun2_history_weight(target_day: date, historical_day: date, today: date) -> float:
    if historical_day >= today:
        return 0.0
    age_years = max(0.0, (today - historical_day).days / 365.25)
    recency = 0.72 ** age_years
    month_diff = month_distance(target_day.month, historical_day.month)
    season = {0: 1.75, 1: 1.35, 2: 1.05, 3: 0.82}.get(month_diff, 0.55)
    weekday = 1.35 if target_day.weekday() == historical_day.weekday() else 0.82
    target_holiday = bool(norwegian_holiday_name(target_day))
    history_holiday = bool(norwegian_holiday_name(historical_day))
    holiday = 1.8 if target_holiday and history_holiday else 1.0 if target_holiday == history_holiday else 0.55
    return max(0.0, recency * season * weekday * holiday)


def sun2_daily_model(target_day: date, history: Dict[date, Dict[str, float]], today: date) -> Dict[str, Any]:
    sessions_values = []
    paid_values = []
    minutes_values = []
    for historical_day, item in history.items():
        weight = sun2_history_weight(target_day, historical_day, today)
        if weight <= 0:
            continue
        sessions_values.append((float_or_zero(item.get("sessions")), weight))
        paid_values.append((float_or_zero(item.get("paid")), weight))
        minutes_values.append((float_or_zero(item.get("minutes")), weight))
    sessions, weight_sum, comparable_days = weighted_average(sessions_values)
    paid, _, _ = weighted_average(paid_values)
    minutes, _, _ = weighted_average(minutes_values)
    return {
        "day": target_day,
        "sessions": sessions,
        "paid": paid,
        "minutes": minutes,
        "weight_sum": weight_sum,
        "comparable_days": comparable_days,
        "holiday": norwegian_holiday_name(target_day),
    }


def sun2_period_actual(history: Dict[date, Dict[str, float]], start: date, end: date) -> Dict[str, float]:
    total = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0}
    for day in iter_dates(start, end):
        item = history.get(day) or {}
        total["sessions"] += float_or_zero(item.get("sessions"))
        total["paid"] += float_or_zero(item.get("paid"))
        total["minutes"] += float_or_zero(item.get("minutes"))
    return total


def sun2_apply_tempo(actual: float, expected: float, minimum: float = 0.62, maximum: float = 1.65) -> float:
    if expected <= 0:
        return 1.0
    return max(minimum, min(maximum, actual / expected))


def opening_day_fraction(minute_of_day: int, opening_minute: int = 7 * 60, closing_minute: int = 23 * 60, power: float = 0.92) -> float:
    if minute_of_day <= opening_minute:
        return 0.0
    if minute_of_day >= closing_minute:
        return 1.0
    linear_fraction = (minute_of_day - opening_minute) / (closing_minute - opening_minute)
    return max(0.0, min(1.0, linear_fraction ** power))


def weighted_intraday_fraction(
    target_day: date,
    today: date,
    rows: list[tuple[date, float, float]],
    weight_fn,
    fallback_fraction: float,
    min_weighted_total: float = 25.0,
) -> float:
    elapsed_weighted = 0.0
    total_weighted = 0.0
    for historical_day, elapsed_count, total_count in rows:
        total_count = float_or_zero(total_count)
        if total_count <= 0:
            continue
        weight = weight_fn(target_day, historical_day, today)
        if weight <= 0:
            continue
        elapsed_weighted += float_or_zero(elapsed_count) * weight
        total_weighted += total_count * weight
    if total_weighted < min_weighted_total:
        return fallback_fraction
    return max(0.0, min(1.0, elapsed_weighted / total_weighted))


async def sun2_historical_day_fraction(
    session,
    target_day: date,
    today: date,
    history: Dict[date, Dict[str, float]],
    minute_of_day: int,
    fallback_fraction: float,
) -> float:
    if fallback_fraction <= 0.0 or fallback_fraction >= 1.0 or not history:
        return fallback_fraction
    first_day = min(history)
    minute_expr = func.extract("hour", Sun2TanningSession.started_at) * 60 + func.extract("minute", Sun2TanningSession.started_at)
    result = await session.execute(
        select(
            Sun2TanningSession.stat_date,
            func.coalesce(func.sum(case((minute_expr <= minute_of_day, 1), else_=0)), 0),
            func.count(Sun2TanningSession.id),
        )
        .where(Sun2TanningSession.stat_date >= first_day)
        .where(Sun2TanningSession.stat_date < today)
        .group_by(Sun2TanningSession.stat_date)
    )
    rows = [(row[0], row[1], row[2]) for row in result.all()]
    return weighted_intraday_fraction(target_day, today, rows, sun2_history_weight, fallback_fraction)


async def parking_historical_day_fraction(
    session,
    target_day: date,
    today: date,
    history: Dict[date, Dict[str, float]],
    minute_of_day: int,
    fallback_fraction: float,
) -> float:
    if fallback_fraction <= 0.0 or fallback_fraction >= 1.0 or not history:
        return fallback_fraction
    first_day = min(history)
    minute_expr = func.extract("hour", ParkingSession.start_time) * 60 + func.extract("minute", ParkingSession.start_time)
    result = await session.execute(
        select(
            cast(ParkingSession.start_time, Date),
            func.coalesce(func.sum(case((minute_expr <= minute_of_day, 1), else_=0)), 0),
            func.count(ParkingSession.id),
        )
        .where(ParkingSession.start_time >= datetime.combine(first_day, time.min))
        .where(ParkingSession.start_time < datetime.combine(today, time.min))
        .group_by(cast(ParkingSession.start_time, Date))
    )
    rows = [(row[0], row[1], row[2]) for row in result.all()]
    return weighted_intraday_fraction(target_day, today, rows, parking_history_weight, fallback_fraction)


def intraday_forecast_value(
    actual: float,
    model: float,
    day_fraction: float,
    minute_of_day: int,
    opening_minute: int,
    minimum_expected_now: float = 3.0,
) -> tuple[float, float]:
    actual = float_or_zero(actual)
    model = float_or_zero(model)
    day_fraction = max(0.01, min(1.0, day_fraction))
    if model <= 0:
        projected = actual / day_fraction if day_fraction > 0 else actual
        return max(actual, projected), 1.0

    expected_now = model * day_fraction
    if minute_of_day <= opening_minute or expected_now < minimum_expected_now:
        return max(actual, model), 1.0

    observed_tempo = actual / expected_now if expected_now > 0 else 1.0
    confidence = max(0.0, min(1.0, (day_fraction - 0.14) / 0.55))
    blended_tempo = 1.0 + (observed_tempo - 1.0) * confidence

    if day_fraction < 0.35:
        min_tempo, max_tempo = (0.78, 1.35)
    elif day_fraction < 0.65:
        min_tempo, max_tempo = (0.58, 1.55)
    else:
        min_tempo, max_tempo = (0.42, 1.75)
    tempo = max(min_tempo, min(max_tempo, blended_tempo))
    return max(actual, model * tempo), tempo


async def build_sun2_forecast(session, today: date, now_local: datetime) -> Dict[str, Any]:
    cache_key = f"sun2_forecast:{today.isoformat()}:{now_local.hour:02d}:{now_local.minute // 5}"
    now_utc = datetime.utcnow()
    cached = SUMMARY_CACHE.get(cache_key)
    if cached and cached.get("expires", datetime.min) > now_utc:
        return cached["value"]

    summaries = await get_sun2_summaries(session)
    history: Dict[date, Dict[str, float]] = {}
    for item in summaries.get("daily", []):
        period = item.get("period")
        try:
            day = date.fromisoformat(period)
        except (TypeError, ValueError):
            continue
        history[day] = {
            "sessions": float_or_zero(item.get("totalt_antall_solinger")),
            "paid": float_or_zero(item.get("totalt_inntjent_kr")),
            "minutes": float_or_zero(item.get("total_soletid_minutter")),
        }
    model_cutoff = today - timedelta(days=1461)
    model_history = {
        day: item
        for day, item in history.items()
        if model_cutoff <= day < today
    }
    if len(model_history) < 180:
        model_history = {day: item for day, item in history.items() if day < today}

    actual_today = history.get(today, {"sessions": 0.0, "paid": 0.0, "minutes": 0.0})
    minute_of_day = now_local.hour * 60 + now_local.minute
    opening_minute = 7 * 60
    closing_minute = 23 * 60
    day_fraction = opening_day_fraction(minute_of_day, opening_minute, closing_minute, power=0.86)
    day_fraction = await sun2_historical_day_fraction(session, today, today, model_history, minute_of_day, day_fraction)
    model_today = sun2_daily_model(today, model_history, today)
    actual_sessions = float_or_zero(actual_today.get("sessions"))
    actual_paid = float_or_zero(actual_today.get("paid"))
    actual_minutes = float_or_zero(actual_today.get("minutes"))
    day_sessions, session_tempo = intraday_forecast_value(
        actual_sessions,
        model_today["sessions"],
        day_fraction,
        minute_of_day,
        opening_minute,
        minimum_expected_now=3.0,
    )
    day_paid = max(actual_paid, float_or_zero(model_today.get("paid")) * session_tempo)
    day_minutes = max(actual_minutes, float_or_zero(model_today.get("minutes")) * session_tempo)

    def forecast_period(start: date, end: date, label: str) -> Dict[str, Any]:
        actual_end = min(today, end)
        actual = sun2_period_actual(history, start, actual_end) if actual_end >= start else {"sessions": 0.0, "paid": 0.0, "minutes": 0.0}
        expected_so_far = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0}
        remaining_base = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0}
        today_remaining = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0}
        future_days = []
        for day in iter_dates(start, end):
            model = sun2_daily_model(day, model_history, today)
            if day < today:
                expected_so_far["sessions"] += model["sessions"]
                expected_so_far["paid"] += model["paid"]
                expected_so_far["minutes"] += model["minutes"]
            elif day == today:
                expected_so_far["sessions"] += model["sessions"] * day_fraction
                expected_so_far["paid"] += model["paid"] * day_fraction
                expected_so_far["minutes"] += model["minutes"] * day_fraction
            else:
                remaining_base["sessions"] += model["sessions"]
                remaining_base["paid"] += model["paid"]
                remaining_base["minutes"] += model["minutes"]
                future_days.append(model)
        tempo_sessions = sun2_apply_tempo(actual["sessions"], expected_so_far["sessions"])
        tempo_paid = sun2_apply_tempo(actual["paid"], expected_so_far["paid"])
        tempo_minutes = sun2_apply_tempo(actual["minutes"], expected_so_far["minutes"])
        if start <= today <= end:
            actual["sessions"] = max(actual["sessions"], actual_sessions)
            actual["paid"] = max(actual["paid"], actual_paid)
            actual["minutes"] = max(actual["minutes"], actual_minutes)
            today_remaining["sessions"] = max(0.0, day_sessions - actual_sessions)
            today_remaining["paid"] = max(0.0, day_paid - actual_paid)
            today_remaining["minutes"] = max(0.0, day_minutes - actual_minutes)
        forecast = {
            "sessions": actual["sessions"] + today_remaining["sessions"] + remaining_base["sessions"] * tempo_sessions,
            "paid": actual["paid"] + today_remaining["paid"] + remaining_base["paid"] * tempo_paid,
            "minutes": actual["minutes"] + today_remaining["minutes"] + remaining_base["minutes"] * tempo_minutes,
        }
        important_days = sorted(
            [item for item in future_days if item.get("holiday")],
            key=lambda item: item["day"],
        )[:8]
        return {
            "label": label,
            "start": start,
            "end": end,
            "actual": actual,
            "expected_so_far": expected_so_far,
            "forecast": forecast,
            "tempo": tempo_sessions,
            "remaining_days": max(0, (end - today).days),
            "important_days": important_days,
        }

    month_start = date(today.year, today.month, 1)
    year_start = date(today.year, 1, 1)
    month = forecast_period(month_start, month_end(today), "Inneværende måned")
    year = forecast_period(year_start, date(today.year, 12, 31), "Inneværende år")
    weekday_names = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
    day = {
        "label": "I dag",
        "date": today,
        "weekday": weekday_names[today.weekday()],
        "holiday": norwegian_holiday_name(today),
        "actual": actual_today,
        "forecast": {"sessions": day_sessions, "paid": day_paid, "minutes": day_minutes},
        "model": model_today,
        "day_fraction": day_fraction,
        "remaining_fraction": max(0.0, 1.0 - day_fraction),
        "comparable_days": model_today["comparable_days"],
    }
    value = {
        "day": day,
        "month": month,
        "year": year,
        "history_first_date": summaries.get("first_date"),
        "history_last_date": summaries.get("last_date"),
        "generated_at": now_local,
    }
    SUMMARY_CACHE[cache_key] = {"expires": now_utc + timedelta(minutes=3), "value": value}
    return value


def parking_daily_model(target_day: date, history: Dict[date, Dict[str, float]], today: date) -> Dict[str, Any]:
    sessions_values = []
    paid_values = []
    minutes_values = []
    vehicles_values = []
    for historical_day, item in history.items():
        weight = parking_history_weight(target_day, historical_day, today)
        if weight <= 0:
            continue
        sessions_values.append((float_or_zero(item.get("sessions")), weight))
        paid_values.append((float_or_zero(item.get("paid")), weight))
        minutes_values.append((float_or_zero(item.get("minutes")), weight))
        vehicles_values.append((float_or_zero(item.get("vehicles")), weight))
    sessions, weight_sum, comparable_days = weighted_average(sessions_values)
    paid, _, _ = weighted_average(paid_values)
    minutes, _, _ = weighted_average(minutes_values)
    vehicles, _, _ = weighted_average(vehicles_values)
    return {
        "day": target_day,
        "sessions": sessions,
        "paid": paid,
        "minutes": minutes,
        "vehicles": vehicles,
        "weight_sum": weight_sum,
        "comparable_days": comparable_days,
        "holiday": norwegian_holiday_name(target_day),
    }


def parking_period_actual(history: Dict[date, Dict[str, float]], start: date, end: date) -> Dict[str, float]:
    total = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0, "vehicles": 0.0}
    for day in iter_dates(start, end):
        item = history.get(day) or {}
        total["sessions"] += float_or_zero(item.get("sessions"))
        total["paid"] += float_or_zero(item.get("paid"))
        total["minutes"] += float_or_zero(item.get("minutes"))
        total["vehicles"] += float_or_zero(item.get("vehicles"))
    return total


def parking_history_weight(target_day: date, historical_day: date, today: date) -> float:
    if historical_day >= today:
        return 0.0
    age_years = max(0.0, (today - historical_day).days / 365.25)
    recency = 0.74 ** age_years
    month_diff = month_distance(target_day.month, historical_day.month)
    season = {0: 1.85, 1: 1.38, 2: 1.05, 3: 0.78}.get(month_diff, 0.48)

    target_weekday = target_day.weekday()
    history_weekday = historical_day.weekday()
    target_is_sunday = target_weekday == 6
    history_is_sunday = history_weekday == 6
    if target_is_sunday:
        weekday = 3.2 if history_is_sunday else 0.035
    elif history_is_sunday:
        weekday = 0.10
    else:
        weekday = 1.45 if target_weekday == history_weekday else 0.78

    target_holiday = bool(norwegian_holiday_name(target_day))
    history_holiday = bool(norwegian_holiday_name(historical_day))
    holiday = 1.8 if target_holiday and history_holiday else 1.0 if target_holiday == history_holiday else 0.50
    return max(0.0, recency * season * weekday * holiday)


async def build_parking_forecast(session, today: date, now_local: datetime) -> Dict[str, Any]:
    cache_key = f"parking_forecast:{today.isoformat()}:{now_local.hour:02d}:{now_local.minute // 5}"
    now_utc = datetime.utcnow()
    cached = SUMMARY_CACHE.get(cache_key)
    if cached and cached.get("expires", datetime.min) > now_utc:
        return cached["value"]

    summaries = await get_parking_summaries(session)
    history: Dict[date, Dict[str, float]] = {}
    for item in summaries.get("daily", []):
        period = item.get("period")
        try:
            day = date.fromisoformat(period)
        except (TypeError, ValueError):
            continue
        history[day] = {
            "sessions": float_or_zero(item.get("sessions")),
            "paid": float_or_zero(item.get("paid")),
            "minutes": float_or_zero(item.get("minutes")),
            "vehicles": float_or_zero(item.get("vehicles")),
        }

    model_cutoff = today - timedelta(days=1461)
    model_history = {
        day: item
        for day, item in history.items()
        if model_cutoff <= day < today
    }
    if len(model_history) < 180:
        model_history = {day: item for day, item in history.items() if day < today}

    actual_today = history.get(today, {"sessions": 0.0, "paid": 0.0, "minutes": 0.0, "vehicles": 0.0})
    minute_of_day = now_local.hour * 60 + now_local.minute
    opening_minute = 7 * 60
    closing_minute = 23 * 60
    day_fraction = opening_day_fraction(minute_of_day, opening_minute, closing_minute, power=0.9)
    day_fraction = await parking_historical_day_fraction(session, today, today, model_history, minute_of_day, day_fraction)

    model_today = parking_daily_model(today, model_history, today)
    actual_sessions = float_or_zero(actual_today.get("sessions"))
    actual_paid = float_or_zero(actual_today.get("paid"))
    actual_minutes = float_or_zero(actual_today.get("minutes"))
    actual_vehicles = float_or_zero(actual_today.get("vehicles"))
    day_sessions, session_tempo = intraday_forecast_value(
        actual_sessions,
        model_today["sessions"],
        day_fraction,
        minute_of_day,
        opening_minute,
        minimum_expected_now=4.0,
    )
    day_paid = max(actual_paid, float_or_zero(model_today.get("paid")) * session_tempo)
    day_minutes = max(actual_minutes, float_or_zero(model_today.get("minutes")) * session_tempo)
    day_vehicles = max(actual_vehicles, float_or_zero(model_today.get("vehicles")) * session_tempo)

    def forecast_period(start: date, end: date, label: str) -> Dict[str, Any]:
        actual_end = min(today, end)
        actual = parking_period_actual(history, start, actual_end) if actual_end >= start else {"sessions": 0.0, "paid": 0.0, "minutes": 0.0, "vehicles": 0.0}
        expected_so_far = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0, "vehicles": 0.0}
        remaining_base = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0, "vehicles": 0.0}
        today_remaining = {"sessions": 0.0, "paid": 0.0, "minutes": 0.0, "vehicles": 0.0}
        future_days = []
        for day in iter_dates(start, end):
            model = parking_daily_model(day, model_history, today)
            if day < today:
                expected_so_far["sessions"] += model["sessions"]
                expected_so_far["paid"] += model["paid"]
                expected_so_far["minutes"] += model["minutes"]
                expected_so_far["vehicles"] += model["vehicles"]
            elif day == today:
                expected_so_far["sessions"] += model["sessions"] * day_fraction
                expected_so_far["paid"] += model["paid"] * day_fraction
                expected_so_far["minutes"] += model["minutes"] * day_fraction
                expected_so_far["vehicles"] += model["vehicles"] * day_fraction
            else:
                remaining_base["sessions"] += model["sessions"]
                remaining_base["paid"] += model["paid"]
                remaining_base["minutes"] += model["minutes"]
                remaining_base["vehicles"] += model["vehicles"]
                future_days.append(model)
        tempo_sessions = sun2_apply_tempo(actual["sessions"], expected_so_far["sessions"])
        tempo_paid = sun2_apply_tempo(actual["paid"], expected_so_far["paid"])
        tempo_minutes = sun2_apply_tempo(actual["minutes"], expected_so_far["minutes"])
        tempo_vehicles = sun2_apply_tempo(actual["vehicles"], expected_so_far["vehicles"])
        if start <= today <= end:
            actual["sessions"] = max(actual["sessions"], actual_sessions)
            actual["paid"] = max(actual["paid"], actual_paid)
            actual["minutes"] = max(actual["minutes"], actual_minutes)
            actual["vehicles"] = max(actual["vehicles"], actual_vehicles)
            today_remaining["sessions"] = max(0.0, day_sessions - actual_sessions)
            today_remaining["paid"] = max(0.0, day_paid - actual_paid)
            today_remaining["minutes"] = max(0.0, day_minutes - actual_minutes)
            today_remaining["vehicles"] = max(0.0, day_vehicles - actual_vehicles)
        forecast = {
            "sessions": actual["sessions"] + today_remaining["sessions"] + remaining_base["sessions"] * tempo_sessions,
            "paid": actual["paid"] + today_remaining["paid"] + remaining_base["paid"] * tempo_paid,
            "minutes": actual["minutes"] + today_remaining["minutes"] + remaining_base["minutes"] * tempo_minutes,
            "vehicles": actual["vehicles"] + today_remaining["vehicles"] + remaining_base["vehicles"] * tempo_vehicles,
        }
        important_days = sorted(
            [item for item in future_days if item.get("holiday")],
            key=lambda item: item["day"],
        )[:8]
        return {
            "label": label,
            "start": start,
            "end": end,
            "actual": actual,
            "expected_so_far": expected_so_far,
            "forecast": forecast,
            "tempo": tempo_sessions,
            "remaining_days": max(0, (end - today).days),
            "important_days": important_days,
        }

    month_start = date(today.year, today.month, 1)
    year_start = date(today.year, 1, 1)
    month = forecast_period(month_start, month_end(today), "Inneværende måned")
    year = forecast_period(year_start, date(today.year, 12, 31), "Inneværende år")
    weekday_names = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
    day = {
        "label": "I dag",
        "date": today,
        "weekday": weekday_names[today.weekday()],
        "holiday": norwegian_holiday_name(today),
        "actual": actual_today,
        "forecast": {"sessions": day_sessions, "paid": day_paid, "minutes": day_minutes, "vehicles": day_vehicles},
        "model": model_today,
        "day_fraction": day_fraction,
        "remaining_fraction": max(0.0, 1.0 - day_fraction),
        "comparable_days": model_today["comparable_days"],
    }
    value = {
        "day": day,
        "month": month,
        "year": year,
        "history_first_date": summaries.get("first_date"),
        "history_last_date": summaries.get("last_date"),
        "generated_at": now_local,
    }
    SUMMARY_CACHE[cache_key] = {"expires": now_utc + timedelta(minutes=3), "value": value}
    return value


def forecast_period_label(period_type: str, start: date, end: date) -> str:
    if period_type == "day":
        return start.strftime("%d.%m.%Y")
    if period_type == "month":
        return start.strftime("%m.%Y")
    if period_type == "year":
        return str(start.year)
    return f"{start.strftime('%d.%m.%Y')} - {end.strftime('%d.%m.%Y')}"


def db_naive_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return value


async def actual_for_forecast_period(session, domain: str, start: date, end: date) -> Dict[str, float]:
    if domain == "sun2":
        row = await sun2_period_snapshot(session, start, end + timedelta(days=1))
        return {
            "sessions": float_or_zero(row.sessions),
            "paid": float_or_zero(row.paid),
            "minutes": float_or_zero(row.minutes),
            "vehicles": 0.0,
        }

    start_at = datetime.combine(start, time.min)
    end_at = datetime.combine(end + timedelta(days=1), time.min)
    row = (
        await session.execute(
            select(
                func.count(ParkingSession.id).label("sessions"),
                func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                func.coalesce(func.sum(ParkingSession.parking_time_min), 0).label("minutes"),
                func.count(func.distinct(ParkingSession.car_license_number)).label("vehicles"),
            ).where(
                ParkingSession.start_time >= start_at,
                ParkingSession.start_time < end_at,
            )
        )
    ).one()
    return {
        "sessions": float_or_zero(row.sessions),
        "paid": float_or_zero(row.paid),
        "minutes": float_or_zero(row.minutes),
        "vehicles": float_or_zero(row.vehicles),
    }


def forecast_snapshot_from_period(
    *,
    domain: str,
    period_type: str,
    start: date,
    end: date,
    period: Dict[str, Any],
    generated_at: Optional[datetime],
    created_by: Optional[str],
) -> ForecastSnapshot:
    forecast = period.get("forecast") or {}
    actual = period.get("actual") or {}
    model = period.get("model") or {}
    return ForecastSnapshot(
        domain=domain,
        period_type=period_type,
        period_start=start,
        period_end=end,
        generated_at=db_naive_utc(generated_at),
        created_by=created_by,
        forecast_sessions=float_or_zero(forecast.get("sessions")),
        forecast_paid=float_or_zero(forecast.get("paid")),
        forecast_minutes=float_or_zero(forecast.get("minutes")),
        forecast_vehicles=float_or_zero(forecast.get("vehicles")),
        actual_sessions_at_save=float_or_zero(actual.get("sessions")),
        actual_paid_at_save=float_or_zero(actual.get("paid")),
        actual_minutes_at_save=float_or_zero(actual.get("minutes")),
        actual_vehicles_at_save=float_or_zero(actual.get("vehicles")),
        model_sessions=float_or_zero(model.get("sessions")),
        day_fraction=period.get("day_fraction"),
        tempo=period.get("tempo"),
        raw={
            "label": period.get("label"),
            "holiday": period.get("holiday"),
            "comparable_days": period.get("comparable_days"),
            "remaining_days": period.get("remaining_days"),
        },
    )


async def save_forecast_snapshots(session, domain: str, forecast: Dict[str, Any], created_by: Optional[str]) -> None:
    today = forecast["day"]["date"]
    month = forecast["month"]
    year = forecast["year"]
    session.add(
        forecast_snapshot_from_period(
            domain=domain,
            period_type="day",
            start=today,
            end=today,
            period=forecast["day"],
            generated_at=forecast.get("generated_at"),
            created_by=created_by,
        )
    )
    session.add(
        forecast_snapshot_from_period(
            domain=domain,
            period_type="month",
            start=month["start"],
            end=month["end"],
            period=month,
            generated_at=forecast.get("generated_at"),
            created_by=created_by,
        )
    )
    session.add(
        forecast_snapshot_from_period(
            domain=domain,
            period_type="year",
            start=year["start"],
            end=year["end"],
            period=year,
            generated_at=forecast.get("generated_at"),
            created_by=created_by,
        )
    )


async def saved_forecast_table(session, domain: str, limit: int = 18) -> list[Dict[str, Any]]:
    rows = (
        await session.execute(
            select(ForecastSnapshot)
            .where(ForecastSnapshot.domain == domain)
            .order_by(ForecastSnapshot.created_at.desc(), ForecastSnapshot.id.desc())
            .limit(limit)
        )
    ).scalars().all()
    today = local_now_naive().date()
    items = []
    for row in rows:
        actual = await actual_for_forecast_period(session, domain, row.period_start, row.period_end)
        forecast = {
            "sessions": float_or_zero(row.forecast_sessions),
            "paid": float_or_zero(row.forecast_paid),
            "minutes": float_or_zero(row.forecast_minutes),
            "vehicles": float_or_zero(row.forecast_vehicles),
        }
        items.append(
            {
                "id": row.id,
                "created_at": row.created_at,
                "created_by": row.created_by,
                "period_type": row.period_type,
                "period_label": forecast_period_label(row.period_type, row.period_start, row.period_end),
                "period_done": row.period_end < today,
                "forecast": forecast,
                "actual": actual,
                "delta": {
                    "sessions": actual["sessions"] - forecast["sessions"],
                    "paid": actual["paid"] - forecast["paid"],
                    "minutes": actual["minutes"] - forecast["minutes"],
                },
            }
        )
    return items


templates.env.filters["short_number"] = format_short_number


ENERGY_FIBARO_AREAS = [
    {"key": "inntak", "label": "Inntak", "tone": "energy"},
    {"key": "varmepumper", "label": "Varmepumper", "tone": "vent"},
    {"key": "belysning", "label": "Belysning", "tone": "light"},
    {"key": "massasje", "label": "Massasje", "tone": "sun2"},
    {"key": "annet", "label": "Annet", "tone": "status"},
    {"key": "avfukter", "label": "Avfukter", "tone": "vent"},
    {"key": "differanse_beregnet", "label": "Differanse", "tone": "admin"},
]

ENERGY_CIRCUIT_SEED_SOURCE = "kursliste_37.xlsx"
ENERGY_CIRCUIT_SEED_ROWS = [
    {"circuit_no": 1, "description": "SENG ROM 1", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 18, "install_method": "B", "rcd_ma": 30},
    {"circuit_no": 2, "description": "ROM 2 SENG", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 17, "install_method": "B2", "rcd_ma": 30},
    {"circuit_no": 3, "description": "VARMEPUMPE \u00d8ST + stikk loft vip mrk 3.", "breaker_type": "Malthe Win", "breaker_rating_a": 16, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 20, "install_method": "B2", "rcd_ma": 30},
    {"circuit_no": 4, "description": "VARMEPUMPE VEST/OVER HOVEDINNGANG", "breaker_type": "Malthe Win", "breaker_rating_a": 16, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 5, "description": "TERMINAL/ REGISTRERING OG KREMAUTOMAT", "breaker_type": "Malthe Win", "breaker_rating_a": 16, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 12, "install_method": "A2", "rcd_ma": 30},
    {"circuit_no": 6, "description": "LOFT OVER LAGER/TAVLEROM vip", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 7, "description": "PARKERINGSAUTOMAT/STIKK LOFT VIP MRK. 7", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 40, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 8, "description": "LOFT NORD (OVER SENG 1+2+3) BOD NOR + TILFLUKTSTR\u00d8M/LAGER", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 40, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 9, "description": "STIKK BODROM VED SOL 7 og 8, STIKK KRYP FRA SOL 9 + STIKK V/DATASKAP BOD SSKAP", "breaker_type": "Malthe Win", "breaker_rating_a": 16, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 18, "install_method": "B2", "rcd_ma": 30, "note": "STIKK MASSAJE (h\u00e5ndskrift)"},
    {"circuit_no": 10, "description": "LYS MIDTEN+STIKK TELLUS+TV NEDE+LOFT SYD", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 40, "install_method": "B2", "rcd_ma": 30},
    {"circuit_no": 11, "description": "LYS SOLROM 1-10 + GANG OPPE", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 43, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 12, "description": "SOL ROM 3", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 13, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 13, "description": "ROM 4 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 14, "description": "ROM 5 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 13, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 15, "description": "ROM 6 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 16, "description": "ROM 8 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 17, "description": "ROM 7 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 13, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 18, "description": "ROM 10 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 19, "description": "ROM 9 SOL", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 13, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 20, "description": "HOVEDBRYTER 21 TIL 30", "breaker_type": "LAST", "breaker_rating_a": 63, "cable_spec": "3x10+J", "cable_length_m": 1, "install_method": "E"},
    {"circuit_no": 21, "description": "LYS VIP (ROM 11,12,13 OG FELLESAREALE)", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 16, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 22, "description": "STIKK UTVENDIG FOR SKILT P\u00c5 TEGELVEGG", "breaker_type": "Malthe Win", "breaker_rating_a": 15, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 23, "description": "STIKK OVER VINDUER HOVEDINNGANG + BRUSAUTOMAT", "breaker_type": "Malthe Win", "breaker_rating_a": 15, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 24, "description": "Parkeringsautomat, plakatlys, front spot vip, 2xgatelys parkering", "status": "mangler vern-data"},
    {"circuit_no": 25, "description": "LOFT 9 OG 10 LYS/STIKK", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30, "note": "VASKEMASKIN MAS. (h\u00e5ndskrift)"},
    {"circuit_no": 26, "description": "LYS SSKAP,LAGER,WC-VASK,B\u00d8TTEKOTT (vip)", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30, "note": "LYSBAD MAS (h\u00e5ndskrift)"},
    {"circuit_no": 27, "description": "VIFTE VIP, VARMEKABEL TAKRENNE", "breaker_type": "Malthe Win", "breaker_rating_a": 13, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 28, "description": "STIKK LOFT SYD(EKSTRA)", "breaker_type": "Malthe Win", "breaker_rating_a": 10, "breaker_characteristic": "C", "cable_spec": "2x1,5+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30, "note": "VARME FOLIE MAS. (h\u00e5ndskrift)"},
    {"circuit_no": 29, "description": "VVBEREDER UNDER ROM 8 + STIKK VIP BOD", "breaker_type": "Malthe Win", "breaker_rating_a": 15, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 15, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 30, "description": "VARMEPUMPE VIP", "breaker_type": "Malthe Win", "breaker_rating_a": 16, "breaker_characteristic": "C", "cable_spec": "2x2,5+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 31, "description": "BRYTER VARMEKABEL I TAKRENNE", "status": "mangler vern-data"},
    {"circuit_no": 32, "description": "ROM 11 SOL (vip)", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 10, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 33, "description": "ROM 12 SOL (vip)", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 14, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 34, "description": "ROM 13 SOL (vip)", "breaker_type": "Malthe Win", "breaker_rating_a": 32, "breaker_characteristic": "C", "cable_spec": "3x6+J", "cable_length_m": 16, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 35, "description": "AVTREKKSVIFTE TAK (LOFT SYD OVER ROM 9)", "breaker_type": "Malthe Win", "breaker_rating_a": 16, "breaker_characteristic": "C", "cable_spec": "3x1,5+J", "cable_length_m": 12, "install_method": "C", "rcd_ma": 30},
    {"circuit_no": 36, "description": "KOBLINGSUR FOR AVTREKK VIP", "status": "mangler vern-data"},
    {"circuit_no": 37, "description": "HOVEDSIKRING/OVERBELASTNINGSVERN", "breaker_type": "NH", "install_method": "GL", "status": "hovedvern"},
]

ENERGY_ACCUMULATED_KEYS = ["inntak", "varmepumper", "belysning", "massasje", "annet", "avfukter", "differanse_fibaro"]
ENERGY_SUB_KEYS = ["varmepumper", "belysning", "massasje", "annet"]
# HC3 accumulated kWh samples are end-stamped. For hourly comparison against
# Elvia, show the delta on the hour it belongs to, not the hour it was posted.
ENERGY_HC3_HOURLY_DISPLAY_OFFSET = timedelta(hours=1)
ENERGY_HOURLY_COMPARE_FIELDS = [
    "stat_date", "year", "month", "day", "hour", "consumption_kwh", "production_kwh",
    "status", "is_verified", "is_estimated", "is_public_holiday", "use_weekend_prices",
]


async def seed_energy_circuits(session) -> None:
    count = await session.scalar(select(func.count(EnergyCircuit.id)))
    if count:
        return
    now_value = datetime.utcnow()
    for row in ENERGY_CIRCUIT_SEED_ROWS:
        status = row.get("status") or ("aktiv" if row.get("breaker_rating_a") else "ukjent")
        session.add(
            EnergyCircuit(
                circuit_no=row["circuit_no"],
                description=row.get("description"),
                breaker_type=row.get("breaker_type"),
                breaker_rating_a=row.get("breaker_rating_a"),
                breaker_characteristic=row.get("breaker_characteristic"),
                cable_spec=row.get("cable_spec"),
                cable_length_m=row.get("cable_length_m"),
                install_method=row.get("install_method"),
                terminal_ref=row.get("terminal_ref"),
                rcd_ma=row.get("rcd_ma"),
                note=row.get("note"),
                status=status,
                source=ENERGY_CIRCUIT_SEED_SOURCE,
                imported_at=now_value,
                updated_at=now_value,
            )
        )


def sum_optional(values: list[Optional[float]]) -> Optional[float]:
    if any(value is None for value in values):
        return None
    return sum(float(value or 0) for value in values)


def calculated_difference(main_value: Optional[float], values: list[Optional[float]]) -> Optional[float]:
    sub_sum = sum_optional(values)
    if main_value is None or sub_sum is None:
        return None
    return float(main_value) - sub_sum


def accumulated_delta(current: Optional[float], previous: Optional[float]) -> tuple[Optional[float], bool]:
    if current is None:
        return None, False
    if previous is None:
        return None, False
    current_value = float(current)
    previous_value = float(previous)
    if current_value + 0.0001 >= previous_value:
        return max(current_value - previous_value, 0.0), False
    return max(current_value, 0.0), True


def energy_hour_has_changed(existing: EnergyHourlyConsumption, row: Dict[str, Any]) -> bool:
    for field in ENERGY_HOURLY_COMPARE_FIELDS:
        current = getattr(existing, field)
        incoming = row.get(field)
        if isinstance(current, float) or isinstance(incoming, float):
            if current is None or incoming is None:
                if current != incoming:
                    return True
            elif abs(float(current) - float(incoming)) > 0.000001:
                return True
        elif current != incoming:
            return True
    return False


def dashboard_alert(level: str, title: str, detail: str, href: str = "/status/datakilder") -> Dict[str, str]:
    return {"level": level, "title": title, "detail": detail, "href": href}


async def record_import_job(
    session,
    job_name: str,
    *,
    ok: bool = True,
    title: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    next_expected_at: Optional[datetime] = None,
    expected_interval_minutes: Optional[int] = None,
    warning_after_minutes: Optional[int] = None,
    records_imported: Optional[int] = None,
    records_total: Optional[int] = None,
    duration_seconds: Optional[float] = None,
    message: Optional[str] = None,
    raw: Optional[Dict[str, Any]] = None,
) -> ImportJobStatus:
    definition = import_job_definition(job_name)
    finished_at = finished_at or local_now_naive()
    title = title or definition["title"]
    category = category or definition["category"]
    source = source or definition.get("source")
    expected_interval_minutes = expected_interval_minutes if expected_interval_minutes is not None else definition.get("expected_interval_minutes")
    warning_after_minutes = warning_after_minutes if warning_after_minutes is not None else definition.get("warning_after_minutes")
    if next_expected_at is None and ok and expected_interval_minutes:
        next_expected_at = finished_at + timedelta(minutes=expected_interval_minutes)
    status = "ok" if ok else "bad"
    status_text = "OK" if ok else "Feil"

    session.add(
        ImportJobRun(
            job_name=job_name,
            title=title,
            category=category,
            source=source,
            started_at=started_at,
            finished_at=finished_at,
            ok=ok,
            status=status,
            records_imported=records_imported,
            records_total=records_total,
            duration_seconds=duration_seconds,
            message=message,
            raw=raw or {},
        )
    )

    existing = (
        await session.execute(select(ImportJobStatus).where(ImportJobStatus.job_name == job_name))
    ).scalars().first()
    if not existing:
        existing = ImportJobStatus(job_name=job_name, title=title, category=category)
        session.add(existing)
    existing.title = title
    existing.category = category
    existing.source = source
    existing.status = status
    existing.status_text = status_text
    existing.last_started_at = started_at or existing.last_started_at
    existing.last_run_at = finished_at
    if ok:
        existing.last_success_at = finished_at
    else:
        existing.last_failed_at = finished_at
    existing.next_expected_at = next_expected_at
    existing.expected_interval_minutes = expected_interval_minutes
    existing.warning_after_minutes = warning_after_minutes
    existing.records_imported = records_imported
    existing.records_total = records_total
    existing.duration_seconds = duration_seconds
    existing.message = message
    existing.raw = raw or {}
    return existing


async def mark_import_job_running(
    session,
    job_name: str,
    *,
    message: Optional[str] = None,
    source: Optional[str] = None,
    raw: Optional[Dict[str, Any]] = None,
) -> ImportJobStatus:
    definition = import_job_definition(job_name)
    started_at = local_now_naive()
    existing = (
        await session.execute(select(ImportJobStatus).where(ImportJobStatus.job_name == job_name))
    ).scalars().first()
    if not existing:
        existing = ImportJobStatus(job_name=job_name, title=definition["title"], category=definition["category"])
        session.add(existing)
    existing.title = definition["title"]
    existing.category = definition["category"]
    existing.source = source or definition.get("source")
    existing.status = "running"
    existing.status_text = "Kjører"
    existing.last_started_at = started_at
    existing.last_run_at = started_at
    existing.message = message or "Import kjører"
    existing.raw = raw or {}
    return existing


async def fallback_import_job_status(session, job_name: str) -> Dict[str, Any]:
    if job_name == "hc3_light_5min":
        row = (await session.execute(select(OutdoorLightSample).order_by(OutdoorLightSample.timestamp.desc()).limit(1))).scalars().first()
        return {"last_success_at": row.timestamp if row else None, "message": "Sist funnet i luxloggen" if row else ""}
    if job_name == "hc3_ventilation_5min":
        row = (await session.execute(select(VentilationSample).order_by(VentilationSample.timestamp.desc()).limit(1))).scalars().first()
        return {"last_success_at": row.timestamp if row else None, "message": "Sist funnet i temploggen" if row else ""}
    if job_name == "yr_weather_refresh":
        row = (await session.execute(select(YrForecastSample).order_by(YrForecastSample.timestamp.desc()).limit(1))).scalars().first()
        return {"last_success_at": utc_naive_to_local_naive(row.timestamp) if row else None, "message": row.weather_text if row else ""}
    if job_name == "hc3_energy_1min":
        row = (await session.execute(select(EnergyFibaroSample).order_by(EnergyFibaroSample.bucket_start.desc()).limit(1))).scalars().first()
        return {
            "last_success_at": row.bucket_start if row else None,
            "message": f"Inntak {format_short_number(row.inntak_w)} W" if row and row.inntak_w is not None else "Sist funnet i energiloggen" if row else "",
        }
    if job_name == "roborock_sync":
        row = (await session.execute(select(RoborockSyncRun).order_by(RoborockSyncRun.timestamp.desc()).limit(1))).scalars().first()
        return {"last_success_at": row.timestamp if row and row.ok is not False else None, "last_failed_at": row.timestamp if row and row.ok is False else None, "message": row.message if row else "", "records_total": row.robots_count if row else None}
    if job_name == "sun2_room_daily_import":
        row = (await session.execute(select(Sun2ImportRun).order_by(Sun2ImportRun.timestamp.desc()).limit(1))).scalars().first()
        return {"last_success_at": row.timestamp if row and row.ok is not False else None, "last_failed_at": row.timestamp if row and row.ok is False else None, "message": row.message if row else "", "records_total": row.rows_count if row else None}
    if job_name == "sun2_sessions_import":
        row = (await session.execute(select(Sun2SessionImportRun).order_by(Sun2SessionImportRun.timestamp.desc()).limit(1))).scalars().first()
        return {"last_success_at": row.timestamp if row and row.ok is not False else None, "last_failed_at": row.timestamp if row and row.ok is False else None, "message": row.message if row else "", "records_total": row.rows_count if row else None}
    if job_name == "sun2_beds_import":
        row = (await session.execute(select(Sun2Bed).order_by(Sun2Bed.imported_at.desc()).limit(1))).scalars().first()
        count = (await session.execute(select(func.count()).select_from(Sun2Bed))).scalar_one()
        return {"last_success_at": row.imported_at if row else None, "message": "Sist funnet i senger-tabellen" if row else "", "records_total": count}
    if job_name == "sun2_members_import":
        row = (await session.execute(select(Sun2Member).order_by(Sun2Member.imported_at.desc()).limit(1))).scalars().first()
        count = (await session.execute(select(func.count()).select_from(Sun2Member))).scalar_one()
        return {"last_success_at": row.imported_at if row else None, "message": "Sist funnet i medlemstabellen" if row else "", "records_total": count}
    if job_name == "elvia_monthly_import":
        row = (await session.execute(select(EnergyImportRun).order_by(EnergyImportRun.timestamp.desc()).limit(1))).scalars().first()
        return {"last_success_at": row.timestamp if row and row.ok is not False else None, "last_failed_at": row.timestamp if row and row.ok is False else None, "message": row.message if row else "", "records_total": row.hours_count if row else None}
    return {}


async def import_status_rows(session) -> list[Dict[str, Any]]:
    existing = {
        row.job_name: row
        for row in (
            await session.execute(select(ImportJobStatus))
        ).scalars().all()
    }
    rows = []
    for job_name, definition in IMPORT_JOB_DEFINITIONS.items():
        row = existing.get(job_name)
        fallback = {} if row else await fallback_import_job_status(session, job_name)
        stamp = row.last_success_at if row else fallback.get("last_success_at")
        last_failed_at = row.last_failed_at if row else fallback.get("last_failed_at")
        expected_minutes = definition.get("expected_interval_minutes")
        warning_minutes = definition.get("warning_after_minutes")
        next_expected_at = row.next_expected_at if row else None
        if stamp and expected_minutes:
            calculated_next = stamp + timedelta(minutes=expected_minutes)
            if not next_expected_at or abs((next_expected_at - calculated_next).total_seconds()) > 60:
                next_expected_at = calculated_next
        if job_name == "sun2_sessions_import" and expected_minutes:
            now_for_sun2 = local_now_naive()
            live_start_today = datetime.combine(now_for_sun2.date(), time(hour=SUN2_SESSIONS_QUIET_END_HOUR))
            if now_for_sun2 < live_start_today:
                next_expected_at = live_start_today
            elif stamp and stamp < live_start_today:
                next_expected_at = live_start_today + timedelta(minutes=expected_minutes)
        if row and row.status == "running":
            status, status_text = "running", "Kjører"
        elif job_name == "sun2_sessions_import":
            active_age_minutes = sun2_sessions_active_minutes_since(stamp)
            status, status_text = import_job_status_from_minutes(
                active_age_minutes,
                expected_minutes,
                warning_minutes,
            )
        else:
            status, status_text = import_job_status_from_age(
                stamp,
                expected_minutes,
                warning_minutes,
            )
        if row and row.status != "running" and last_failed_at and (not stamp or last_failed_at > stamp):
            status, status_text = "bad", "Feil"
        rows.append(
            {
                "job_name": job_name,
                "title": row.title if row else definition["title"],
                "category": row.category if row else definition["category"],
                "source": row.source if row and row.source else definition.get("source"),
                "description": definition.get("description", ""),
                "status": status,
                "status_text": status_text,
                "age": age_label(sun2_sessions_active_minutes_since(stamp)) if job_name == "sun2_sessions_import" else (import_job_age(row) if row else age_label(minutes_since(stamp))),
                "last_success_at": stamp,
                "last_run_at": row.last_run_at if row else stamp,
                "last_failed_at": last_failed_at,
                "next_expected_at": next_expected_at,
                "records_imported": row.records_imported if row else None,
                "records_total": row.records_total if row else fallback.get("records_total"),
                "duration_seconds": row.duration_seconds if row else None,
                "message": row.message if row else fallback.get("message", ""),
            }
        )
    return rows


def light_status_text(row: OutdoorLightSample) -> str:
    active = []
    for device in LIGHT_TIMELINE_DEVICES:
        if light_sample_state(row, device):
            active.append(device["name"])
    return ", ".join(active) if active else "Alt av"


def event_detail(system: str, row) -> str:
    pieces = []
    if system == "lys" and row.lux is not None:
        pieces.append(f"Lux {row.lux:.0f}")
    if system == "ventilasjon":
        if row.temp_1etg is not None:
            pieces.append(f"1.etg {row.temp_1etg:.1f}°")
        if row.temp_2etg is not None:
            pieces.append(f"2.etg {row.temp_2etg:.1f}°")
        if row.temp_vip is not None:
            pieces.append(f"VIP {row.temp_vip:.1f}°")
        if row.humidity_1etg is not None:
            pieces.append(f"fukt 1.etg {row.humidity_1etg:.0f}%")
        if row.humidity_2etg is not None:
            pieces.append(f"fukt 2.etg {row.humidity_2etg:.0f}%")
        if row.humidity_vip is not None:
            pieces.append(f"fukt VIP {row.humidity_vip:.0f}%")
        if row.temp_kjeller is not None:
            pieces.append(f"kjeller {row.temp_kjeller:.1f}°")
        if row.humidity_kjeller is not None:
            pieces.append(f"fukt kjeller {row.humidity_kjeller:.0f}%")
        if row.temp_ute is not None:
            pieces.append(f"ute {row.temp_ute:.1f}°")
        if row.diff_w is not None:
            pieces.append(f"diff {row.diff_w:.0f} W")
    return ", ".join(pieces)


def light_sample_state(row, device) -> Optional[bool]:
    attr = device.get("sample_attr")
    value = getattr(row, attr, None)
    if value is None:
        return None
    return bool(value)


def sample_state(row, device) -> Optional[bool]:
    attr = device.get("sample_attr")
    if not row or not attr:
        return None
    value = getattr(row, attr, None)
    if value is None:
        return None
    return bool(value)


def event_extra_key(row) -> Optional[str]:
    extra = getattr(row, "extra", None) or {}
    if isinstance(extra, dict):
        key = extra.get("device_key") or extra.get("key")
        if key:
            return str(key)
    return None


def event_device_key(row, devices) -> Optional[str]:
    key = getattr(row, "device_key", None) or event_extra_key(row)
    if key:
        return str(key)
    device_id = getattr(row, "device_id", None)
    device_name = (getattr(row, "device_name", None) or "").strip().lower()
    for device in devices:
        if device_id is not None and device_id in device.get("legacy_ids", []):
            return device["key"]
        if device_name and device_name == device["name"].strip().lower():
            return device["key"]
    return None


def event_matches_device(row, device, devices) -> bool:
    return event_device_key(row, devices) == device["key"]


def dedupe_samples_by_bucket(rows):
    buckets = {}
    for row in rows:
        buckets[row.bucket_start or row.timestamp] = row
    return [buckets[key] for key in sorted(buckets)]


def point_from_row(row, day_start: datetime, day_end: datetime, system: str):
    event_time = max(day_start, min(day_end, row.timestamp))
    reason = clean_display_text(row.reason or row.source or "")
    return {
        "left": percent_between(event_time, day_start, day_end),
        "time": event_time.strftime("%H:%M"),
        "action": display_action(row.action),
        "action_class": "on" if row.action == "PAA" else "off" if row.action == "AV" else "neutral",
        "reason": reason,
        "detail": event_detail(system, row),
    }


def build_timeline_item(device, rows, previous_row, day_start: datetime, day_end: datetime, timeline_end: datetime, system: str):
    state = state_from_event(previous_row) if previous_row else False
    if state is None:
        state = False
    cursor = day_start
    raw_segments = []
    points = []

    for row in rows:
        if row.timestamp >= timeline_end:
            break
        event_time = max(day_start, min(timeline_end, row.timestamp))
        if state and event_time > cursor:
            add_segment(raw_segments, cursor, event_time)

        new_state = state_from_event(row)
        points.append(point_from_row(row, day_start, day_end, system))
        if new_state is not None:
            state = new_state
            cursor = event_time

    if state and cursor < timeline_end:
        add_segment(raw_segments, cursor, timeline_end)

    return {
        "id": device["key"],
        "name": device["name"],
        "segments": display_segments(raw_segments, day_start, day_end),
        "points": points,
        "total": total_from_segments(raw_segments),
    }


async def build_timeline_group(model, devices, system: str, day_start: datetime, day_end: datetime, timeline_end: datetime):
    async with async_session() as session:
        day_result = await session.execute(
            select(model)
            .where(model.timestamp >= day_start)
            .where(model.timestamp < timeline_end)
            .order_by(model.timestamp.asc())
        )
        rows = day_result.scalars().all()
        previous = {}
        for device in devices:
            previous_candidates = (await session.execute(
                select(model)
                .where(model.timestamp < day_start)
                .order_by(model.timestamp.desc())
                .limit(300)
            )).scalars().all()
            previous[device["key"]] = next((row for row in previous_candidates if event_matches_device(row, device, devices)), None)

    rows_by_device = {device["key"]: [] for device in devices}
    for row in rows:
        key = event_device_key(row, devices)
        if key in rows_by_device:
            rows_by_device[key].append(row)

    return [
        build_timeline_item(device, rows_by_device.get(device["key"], []), previous.get(device["key"]), day_start, day_end, timeline_end, system)
        for device in devices
    ]


async def build_light_timeline_group(day_start: datetime, day_end: datetime, timeline_end: datetime):
    async with async_session() as session:
        event_result = await session.execute(
            select(OutdoorLightEvent)
            .where(OutdoorLightEvent.timestamp >= day_start)
            .where(OutdoorLightEvent.timestamp < timeline_end)
            .order_by(OutdoorLightEvent.timestamp.asc())
        )
        event_rows = event_result.scalars().all()
        sample_result = await session.execute(
            select(OutdoorLightSample)
            .where(OutdoorLightSample.timestamp >= day_start)
            .where(OutdoorLightSample.timestamp < timeline_end)
            .order_by(OutdoorLightSample.timestamp.asc())
        )
        sample_rows = sample_result.scalars().all()
        sample_rows = dedupe_samples_by_bucket(sample_rows)
        previous_sample_result = await session.execute(
            select(OutdoorLightSample)
            .where(OutdoorLightSample.timestamp < day_start)
            .order_by(OutdoorLightSample.timestamp.desc())
            .limit(1)
        )
        previous_sample = previous_sample_result.scalars().first()
        previous_events = {}
        for device in LIGHT_TIMELINE_DEVICES:
            previous_candidates = (await session.execute(
                select(OutdoorLightEvent)
                .where(OutdoorLightEvent.timestamp < day_start)
                .order_by(OutdoorLightEvent.timestamp.desc())
                .limit(300)
            )).scalars().all()
            previous_events[device["key"]] = next(
                (row for row in previous_candidates if event_matches_device(row, device, LIGHT_TIMELINE_DEVICES)),
                None,
            )

    events_by_device = {device["key"]: [] for device in LIGHT_TIMELINE_DEVICES}
    for row in event_rows:
        key = event_device_key(row, LIGHT_TIMELINE_DEVICES)
        if key in events_by_device:
            events_by_device[key].append(row)

    items = []
    for device in LIGHT_TIMELINE_DEVICES:
        state = light_sample_state(previous_sample, device) if previous_sample else None
        if state is None and previous_events.get(device["key"]):
            state = state_from_event(previous_events[device["key"]])
        if state is None:
            state = False
        cursor = day_start
        raw_segments = []
        points = [point_from_row(row, day_start, day_end, "lys") for row in events_by_device.get(device["key"], [])]
        sample_points = []
        state_changes = []

        for row in sample_rows:
            sample_time = row.bucket_start or row.timestamp
            if sample_time >= timeline_end:
                break
            event_time = max(day_start, min(timeline_end, sample_time))
            new_state = light_sample_state(row, device)
            if new_state is None:
                continue
            state_changes.append({
                "time": event_time,
                "state": new_state,
                "source": "sample",
                "lux": row.lux,
            })

        for row in events_by_device.get(device["key"], []):
            if row.timestamp >= timeline_end:
                continue
            event_time = max(day_start, min(timeline_end, row.timestamp))
            new_state = state_from_event(row)
            if new_state is None:
                continue
            state_changes.append({
                "time": event_time,
                "state": new_state,
                "source": "event",
                "lux": row.lux,
            })

        state_changes.sort(key=lambda item: (item["time"], 0 if item["source"] == "sample" else 1))

        for change in state_changes:
            event_time = change["time"]
            new_state = change["state"]
            if state and event_time > cursor:
                add_segment(raw_segments, cursor, event_time)
            if new_state != state and change["source"] == "sample":
                action = "PAA" if new_state else "AV"
                has_event_point = any(point["time"] == event_time.strftime("%H:%M") and point["action"] == display_action(action) for point in points)
                if not has_event_point:
                    sample_points.append({
                        "left": percent_between(event_time, day_start, day_end),
                        "time": event_time.strftime("%H:%M"),
                        "action": display_action(action),
                        "action_class": "on" if new_state else "off",
                        "reason": "Statusendring fra 5-minutters luxlogg",
                        "detail": f"Lux {change['lux']:.0f}" if change["lux"] is not None else "",
                    })
            state = new_state
            cursor = event_time

        if state and cursor < timeline_end:
            add_segment(raw_segments, cursor, timeline_end)

        all_points = sorted(points + sample_points, key=lambda point: point["time"])
        items.append({
            "id": device["key"],
            "name": device["name"],
            "segments": display_segments(raw_segments, day_start, day_end),
            "points": all_points,
            "total": total_from_segments(raw_segments),
        })

    return items


async def build_light_chart_markers(day_start: datetime, day_end: datetime, timeline_end: datetime):
    light_colors = {
        "lyslist": "#df705d",
        "reklame": "#f2b84b",
        "spot_glass_275": "#3f7fbd",
        "spot_glass_299": "#2f8fa3",
        "spot_inngang": "#726189",
        "parkering": "#52a464",
    }
    light_shorts = {
        "lyslist": "Lyslist",
        "reklame": "Reklame",
        "spot_glass_275": "Glass",
        "spot_glass_299": "Massasje",
        "spot_inngang": "Inngang",
        "parkering": "Parkering",
    }
    devices = [
        {
            **device,
            "short": light_shorts.get(device["key"], device["name"]),
            "color": light_colors.get(device["key"], "#df705d"),
            "default": True,
        }
        for device in LIGHT_TIMELINE_DEVICES
    ]

    async with async_session() as session:
        event_rows = (
            await session.execute(
                select(OutdoorLightEvent)
                .where(OutdoorLightEvent.timestamp >= day_start)
                .where(OutdoorLightEvent.timestamp < timeline_end)
                .order_by(OutdoorLightEvent.timestamp.asc())
            )
        ).scalars().all()
        sample_rows = (
            await session.execute(
                select(OutdoorLightSample)
                .where(OutdoorLightSample.timestamp >= day_start)
                .where(OutdoorLightSample.timestamp < timeline_end)
                .order_by(OutdoorLightSample.timestamp.asc())
            )
        ).scalars().all()
        sample_rows = dedupe_samples_by_bucket(sample_rows)
        previous_sample = (
            await session.execute(
                select(OutdoorLightSample)
                .where(OutdoorLightSample.timestamp < day_start)
                .order_by(OutdoorLightSample.timestamp.desc())
                .limit(1)
            )
        ).scalars().first()
        previous_candidates = (
            await session.execute(
                select(OutdoorLightEvent)
                .where(OutdoorLightEvent.timestamp < day_start)
                .order_by(OutdoorLightEvent.timestamp.desc())
                .limit(300)
            )
        ).scalars().all()

    events_by_device = {device["key"]: [] for device in devices}
    for row in event_rows:
        key = event_device_key(row, LIGHT_TIMELINE_DEVICES)
        if key in events_by_device:
            events_by_device[key].append(row)

    markers = []
    light_lane_y = {device["key"]: 34 + index * 13 for index, device in enumerate(devices)}
    for device in devices:
        state = light_sample_state(previous_sample, device) if previous_sample else None
        if state is None:
            previous_event = next(
                (row for row in previous_candidates if event_matches_device(row, device, LIGHT_TIMELINE_DEVICES)),
                None,
            )
            state = state_from_event(previous_event) if previous_event else None
        if state is None:
            state = False

        changes = []
        for row in sample_rows:
            sample_time = row.bucket_start or row.timestamp
            if sample_time is None or sample_time >= timeline_end:
                continue
            new_state = light_sample_state(row, device)
            if new_state is None:
                continue
            changes.append(
                {
                    "time": max(day_start, min(timeline_end, sample_time)),
                    "state": new_state,
                    "source_order": 0,
                    "detail": f"Lux {row.lux:.0f}" if row.lux is not None else "",
                    "reason": "Statusendring fra 5-minutters luxlogg",
                }
            )

        for row in events_by_device.get(device["key"], []):
            if row.timestamp >= timeline_end:
                continue
            new_state = state_from_event(row)
            if new_state is None:
                continue
            detail = event_detail("lys", row)
            reason = clean_display_text(row.reason or row.source or "")
            changes.append(
                {
                    "time": max(day_start, min(timeline_end, row.timestamp)),
                    "state": new_state,
                    "source_order": 1,
                    "detail": detail,
                    "reason": reason,
                }
            )

        seen = set()
        for change in sorted(changes, key=lambda item: (item["time"], item["source_order"])):
            if change["state"] == state:
                continue
            action = "PÅ" if change["state"] else "AV"
            action_class = "on" if change["state"] else "off"
            marker_key = (device["key"], change["time"].replace(second=0, microsecond=0), action_class)
            if marker_key in seen:
                state = change["state"]
                continue
            seen.add(marker_key)
            markers.append(
                {
                    "light_key": device["key"],
                    "light_name": device["name"],
                    "light_short": device["short"],
                    "color": device["color"],
                    "x": percent_between(change["time"], day_start, day_end) * 10,
                    "lane_y": light_lane_y.get(device["key"], 34),
                    "time": change["time"].strftime("%H:%M"),
                    "action": action,
                    "class": action_class,
                    "detail": change["detail"],
                    "reason": change["reason"],
                }
            )
            state = change["state"]

    return {"lights": devices, "events": markers}


async def fetch_lux_samples(day_start: datetime, timeline_end: datetime):
    async with async_session() as session:
        sample_result = await session.execute(
            select(OutdoorLightSample)
            .where(OutdoorLightSample.timestamp >= day_start)
            .where(OutdoorLightSample.timestamp < timeline_end)
            .order_by(OutdoorLightSample.timestamp.asc())
        )
        sample_rows = dedupe_samples_by_bucket(sample_result.scalars().all())

    samples = []
    lux_values = []
    for row in sample_rows:
        sample_time = row.bucket_start or row.timestamp
        lux_value = row.lux if row.lux is not None else row.value
        if sample_time is None or lux_value is None:
            continue
        lux_values.append(lux_value)
        samples.append(
            {
                "time_dt": sample_time,
                "time": sample_time.strftime("%H:%M"),
                "lux": round(lux_value, 1),
                "lux_label": f"{lux_value:.0f}",
                "mode": row.mode or "",
                "source": row.source or "",
                "lights": light_status_text(row),
            }
        )
    return samples, lux_values


async def build_lux_day(day_start: datetime, day_end: datetime, timeline_end: datetime, scale_values: Optional[list] = None):
    samples, lux_values = await fetch_lux_samples(day_start, timeline_end)

    scale = lux_scale(scale_values if scale_values is not None else lux_values)
    max_lux = scale["max"]
    points = []
    for sample in samples:
        points.append(
            {
                **sample,
                "x": percent_between(sample["time_dt"], day_start, day_end) * 10,
                "y": lux_y(float(sample["lux"]), max_lux),
            }
        )
    polyline = " ".join(f"{point['x']:.2f},{point['y']:.2f}" for point in points)

    y_ticks = [
        {
            "label": lux_tick_label(value),
            "value": value,
            "y": lux_y(float(value), max_lux),
            "symbol_radius": round(2.2 + math.sqrt(value / max_lux) * 3.8, 2),
            "symbol_opacity": round(0.25 + math.sqrt(value / max_lux) * 0.55, 2),
        }
        for value in lux_tick_values(max_lux)
    ]
    reference_lines = [
        {"label": f"{lux_tick_label(value)} lux", "value": value, "y": lux_y(float(value), max_lux)}
        for value in [100, 1000, 2000]
        if value <= max_lux
    ]

    lux_only = [sample["lux"] for sample in samples]
    summary = {
        "count": len(samples),
        "min": f"{min(lux_only):.0f}" if lux_only else "-",
        "max": f"{max(lux_only):.0f}" if lux_only else "-",
        "latest": f"{lux_only[-1]:.0f}" if lux_only else "-",
        "latest_time": samples[-1]["time"] if samples else "-",
        "scale_max": f"{max_lux:.0f}",
        "scale_step": f"{scale['step']:.0f}",
        "scale_break": "2000",
    }
    return {
        "points": points,
        "polyline": polyline,
        "y_ticks": y_ticks,
        "reference_lines": reference_lines,
        "samples_desc": list(reversed(samples)),
        "summary": summary,
    }


def build_lux_sparkline(sample_rows, day_start: datetime, day_end: datetime):
    rows = dedupe_samples_by_bucket(sample_rows)
    values = []
    points = []
    for row in rows:
        sample_time = row.bucket_start or row.timestamp
        lux_value = row.lux if row.lux is not None else row.value
        if sample_time is None or lux_value is None:
            continue
        values.append(float(lux_value))
        points.append((sample_time, float(lux_value)))
    if not points:
        return {"polyline": "", "count": 0}
    max_lux = lux_scale(values)["max"]
    polyline = " ".join(
        f"{percent_between(sample_time, day_start, day_end) * 10:.2f},{lux_y(value, max_lux):.2f}"
        for sample_time, value in points
    )
    return {"polyline": polyline, "count": len(points)}


async def build_temp_day(day_start: datetime, day_end: datetime, timeline_end: datetime):
    series_config = [
        {"key": "temp_1etg", "label": "1.etg", "class": "one", "color": "#df705d", "default": True},
        {"key": "temp_2etg", "label": "2.etg", "class": "two", "color": "#f2b84b", "default": True},
        {"key": "temp_vip", "label": "VIP", "class": "vip", "color": "#8b5cf6", "default": True},
        {"key": "temp_ute", "label": "Ute styring", "class": "outdoor", "color": "#2f8fa3", "default": True},
        {"key": "temp_ute_netatmo", "label": "Ute Netatmo", "class": "outdoor-netatmo", "color": "#14b8a6", "default": False},
        {"key": "temp_yr", "label": "Yr API", "class": "yr", "color": "#4b7fbb", "default": True},
        {"key": "temp_loft", "label": "Loft", "class": "loft", "color": "#726189", "default": True},
        {"key": "temp_kjeller", "label": "Kjeller", "class": "basement", "color": "#2f8fa3", "default": True},
        {"key": "temp_passiv", "label": "Pass innluft", "class": "passive", "color": "#52a464", "default": False},
        {"key": "temp_luftinntak", "label": "Luftinntak", "class": "intake", "color": "#9a660f", "default": False},
        {"key": "temp_min_inne", "label": "Min inne", "class": "indoor-min", "color": "#93c5fd", "default": False},
        {"key": "temp_avg_inne", "label": "Snitt inne", "class": "indoor-avg", "color": "#3f7fbd", "default": False},
        {"key": "temp_max_inne", "label": "Maks inne", "class": "indoor-max", "color": "#1d4ed8", "default": False},
    ]
    fan_config = [
        {**VENT_TIMELINE_DEVICES[0], "short": "VIP", "color": "#52a464", "default": True},
        {**VENT_TIMELINE_DEVICES[1], "short": "2.etg", "color": "#3f7fbd", "default": True},
        {**VENT_TIMELINE_DEVICES[2], "short": "Tak", "color": "#726189", "default": True},
        {**VENT_TIMELINE_DEVICES[3], "short": "Avf.", "color": "#2f8fa3", "default": True},
    ]
    fan_by_key = {fan["key"]: fan for fan in fan_config}

    async with async_session() as session:
        sample_result = await session.execute(
            select(VentilationSample)
            .where(VentilationSample.timestamp >= day_start)
            .where(VentilationSample.timestamp < timeline_end)
            .order_by(VentilationSample.timestamp.asc())
        )
        sample_rows = dedupe_samples_by_bucket(sample_result.scalars().all())
        fan_result = await session.execute(
            select(VentilationEvent)
            .where(VentilationEvent.timestamp >= day_start)
            .where(VentilationEvent.timestamp < timeline_end)
            .order_by(VentilationEvent.timestamp.asc())
        )
        fan_rows = fan_result.scalars().all()

    samples = []
    all_values = []
    for row in sample_rows:
        sample_time = row.bucket_start or row.timestamp
        if sample_time is None:
            continue

        sample = {
            "time_dt": sample_time,
            "time": sample_time.strftime("%H:%M"),
            "mode": row.mode or "",
            "source": row.source or "",
        }
        has_value = False
        for series in series_config:
            value = getattr(row, series["key"], None)
            sample[series["key"]] = value
            sample[f"{series['key']}_label"] = temp_label(value)
            if value is not None:
                has_value = True
                all_values.append(value)
        if has_value:
            samples.append(sample)

    axis = temp_axis(all_values)
    series_items = []
    for series in series_config:
        points = []
        values = []
        for sample in samples:
            value = sample[series["key"]]
            if value is None:
                continue
            values.append(value)
            points.append(
                {
                    "x": percent_between(sample["time_dt"], day_start, day_end) * 10,
                    "y": temp_y(float(value), axis["min"], axis["max"]),
                }
            )
        series_items.append(
            {
                **series,
                "polyline": " ".join(f"{point['x']:.2f},{point['y']:.2f}" for point in points),
                "latest": temp_label(values[-1]) if values else "-",
                "min": temp_label(min(values)) if values else "-",
                "max": temp_label(max(values)) if values else "-",
            }
        )

    y_ticks = []
    tick = axis["min"]
    while tick <= axis["max"] + 0.001:
        y_ticks.append({"label": temp_label(tick), "y": temp_y(tick, axis["min"], axis["max"])})
        tick += axis["step"]

    fan_events = []
    for row in fan_rows:
        fan_key = event_device_key(row, VENT_TIMELINE_DEVICES)
        if fan_key not in fan_by_key:
            continue
        state = state_from_event(row)
        if state is None:
            continue
        fan = fan_by_key[fan_key]
        event_time = max(day_start, min(timeline_end, row.timestamp))
        fan_events.append(
            {
                "fan_key": fan_key,
                "fan_name": fan["name"],
                "fan_short": fan["short"],
                "color": fan["color"],
                "x": percent_between(event_time, day_start, day_end) * 10,
                "time": event_time.strftime("%H:%M"),
                "action": "PÅ" if state else "AV",
                "class": "on" if state else "off",
                "detail": clean_display_text(row.reason or row.source or ""),
            }
        )

    visible_series_count = sum(1 for series in series_items if series["polyline"])
    summary = {
        "count": len(samples),
        "fan_event_count": len(fan_events),
        "latest_time": samples[-1]["time"] if samples else "-",
        "axis_min": temp_label(axis["min"]),
        "axis_max": temp_label(axis["max"]),
        "series_count": visible_series_count,
    }
    return {
        "series": series_items,
        "fans": fan_config,
        "fan_events": fan_events,
        "y_ticks": y_ticks,
        "samples_desc": list(reversed(samples)),
        "summary": summary,
    }


def row_to_dict(row, columns):
    out = {}
    for column in columns:
        if column == "extra":
            continue
        value = getattr(row, column)
        out[column] = value.isoformat() if isinstance(value, (datetime, date)) else value
    if hasattr(row, "extra"):
        out["extra"] = row.extra or {}
    return out


def energy_fibaro_sample_payload(data: EnergyFibaroIn, previous: Optional[EnergyFibaroSample]) -> Dict[str, Any]:
    timestamp = normalize_local_naive(data.timestamp) or local_now_naive()
    bucket_start = minute_bucket(data.bucket_start or timestamp)
    values: Dict[str, Any] = {
        "timestamp": timestamp,
        "bucket_start": bucket_start,
        "source": data.source,
        "inntak_w": data.inntak_w,
        "varmepumper_w": data.varmepumper_w,
        "belysning_w": data.belysning_w,
        "massasje_w": data.massasje_w,
        "annet_w": data.annet_w,
        "avfukter_w": data.avfukter_w,
        "differanse_fibaro_w": data.differanse_fibaro_w,
        "inntak_kwh": data.inntak_kwh,
        "varmepumper_kwh": data.varmepumper_kwh,
        "belysning_kwh": data.belysning_kwh,
        "massasje_kwh": data.massasje_kwh,
        "annet_kwh": data.annet_kwh,
        "avfukter_kwh": data.avfukter_kwh,
        "differanse_fibaro_kwh": data.differanse_fibaro_kwh,
        "extra": data.extra or {},
    }
    values["differanse_beregnet_w"] = calculated_difference(
        values["inntak_w"],
        [values[f"{key}_w"] for key in ENERGY_SUB_KEYS],
    )
    values["differanse_beregnet_kwh"] = calculated_difference(
        values["inntak_kwh"],
        [values[f"{key}_kwh"] for key in ENERGY_SUB_KEYS],
    )

    reset_flags: Dict[str, bool] = {}
    for key in ENERGY_ACCUMULATED_KEYS:
        delta, reset = accumulated_delta(
            values.get(f"{key}_kwh"),
            getattr(previous, f"{key}_kwh", None) if previous else None,
        )
        values[f"{key}_delta_kwh"] = delta
        if key != "differanse_fibaro":
            values[f"{key}_reset"] = reset
        else:
            values["differanse_fibaro_reset"] = reset
        reset_flags[key] = reset

    values["differanse_beregnet_delta_kwh"] = calculated_difference(
        values.get("inntak_delta_kwh"),
        [values.get(f"{key}_delta_kwh") for key in ENERGY_SUB_KEYS],
    )
    values["extra"] = {
        **(values.get("extra") or {}),
        "reset_flags": reset_flags,
        "calculated_by": "fibaro10",
    }
    return values


async def upsert_energy_fibaro_sample(session, data: EnergyFibaroIn) -> EnergyFibaroSample:
    timestamp = normalize_local_naive(data.timestamp) or local_now_naive()
    bucket_start = minute_bucket(data.bucket_start or timestamp)
    previous = (
        await session.execute(
            select(EnergyFibaroSample)
            .where(EnergyFibaroSample.bucket_start < bucket_start)
            .order_by(EnergyFibaroSample.bucket_start.desc())
            .limit(1)
        )
    ).scalars().first()
    values = energy_fibaro_sample_payload(
        EnergyFibaroIn(**{**data.dict(), "timestamp": timestamp, "bucket_start": bucket_start}),
        previous,
    )
    existing = (
        await session.execute(
            select(EnergyFibaroSample)
            .where(EnergyFibaroSample.bucket_start == bucket_start)
            .limit(1)
        )
    ).scalars().first()
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        return existing
    record = EnergyFibaroSample(**values)
    session.add(record)
    return record


def energy_area_cards(latest: Optional[EnergyFibaroSample], totals: Dict[str, float], reset_counts: Dict[str, int]) -> list[Dict[str, Any]]:
    cards = []
    for area in ENERGY_FIBARO_AREAS:
        key = area["key"]
        cards.append(
            {
                **area,
                "power_w": getattr(latest, f"{key}_w", None) if latest else None,
                "energy_kwh": getattr(latest, f"{key}_kwh", None) if latest else None,
                "today_kwh": totals.get(f"{key}_delta_kwh", 0.0),
                "resets_today": reset_counts.get(key, 0),
            }
        )
    return cards


def percentile(values: list[float], percent: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percent
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[int(position)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def sunbed_session_bounds(row: Sun2TanningSession) -> tuple[datetime, datetime] | None:
    if not row.started_at:
        return None
    start_at = normalize_local_naive(row.started_at)
    end_at = normalize_local_naive(row.ended_at)
    if not start_at:
        return None
    if not end_at:
        end_at = start_at + timedelta(minutes=float(row.duration_minutes or 15))
    if end_at <= start_at:
        end_at = start_at + timedelta(minutes=max(1.0, float(row.duration_minutes or 1)))
    return start_at, end_at


def build_sunbed_power_analysis(
    sessions: list[Sun2TanningSession],
    samples: list[Any],
    bed_lookup: Dict[str, Any],
) -> Dict[str, Any]:
    warmup_minutes = 2
    cooldown_minutes = 3
    stop_before_end_minutes = 1
    min_samples_per_session = 3
    session_items = []
    for row in sessions:
        room_id = normalize_room_id(row.room_id)
        bounds = sunbed_session_bounds(row)
        if not room_id or not bounds:
            continue
        start_at, end_at = bounds
        session_items.append(
            {
                "id": row.id,
                "room_id": room_id,
                "sun2_bed_id": row.sun2_bed_id,
                "start": start_at,
                "end": end_at,
                "measure_start": start_at + timedelta(minutes=warmup_minutes),
                "measure_end": end_at - timedelta(minutes=stop_before_end_minutes),
                "occupied_end": end_at + timedelta(minutes=cooldown_minutes),
                "duration_minutes": max(0.0, (end_at - start_at).total_seconds() / 60),
            }
        )

    events = []
    sessions_by_id = {}
    for item in session_items:
        sessions_by_id[item["id"]] = item
        events.append((item["start"], 1, item["id"]))
        events.append((item["occupied_end"], -1, item["id"]))
    events.sort(key=lambda item: (item[0], item[1]))

    sample_items = []
    for sample in samples:
        bucket = sample.get("bucket_start") if isinstance(sample, dict) else getattr(sample, "bucket_start", None)
        bucket = normalize_local_naive(bucket)
        value = sample.get("differanse_beregnet_w") if isinstance(sample, dict) else getattr(sample, "differanse_beregnet_w", None)
        if value is None:
            value = sample.get("differanse_fibaro_w") if isinstance(sample, dict) else getattr(sample, "differanse_fibaro_w", None)
        try:
            diff_w = float(value)
        except (TypeError, ValueError):
            continue
        if bucket is not None:
            sample_items.append({"time": bucket, "diff_w": diff_w})
    sample_items.sort(key=lambda item: item["time"])

    active: set[int] = set()
    event_index = 0
    classified = []
    baseline_by_day_hour: Dict[tuple[date, int], list[float]] = defaultdict(list)
    baseline_by_day: Dict[date, list[float]] = defaultdict(list)
    baseline_global: list[float] = []
    overlap_samples = 0

    for sample in sample_items:
        sample_time = sample["time"]
        while event_index < len(events) and events[event_index][0] <= sample_time:
            _, action, session_id = events[event_index]
            if action == 1:
                active.add(session_id)
            else:
                active.discard(session_id)
            event_index += 1
        if len(active) == 0:
            baseline_by_day_hour[(sample_time.date(), sample_time.hour)].append(sample["diff_w"])
            baseline_by_day[sample_time.date()].append(sample["diff_w"])
            baseline_global.append(sample["diff_w"])
            classified.append({**sample, "session_id": None, "state": "baseline"})
        elif len(active) == 1:
            session_id = next(iter(active))
            classified.append({**sample, "session_id": session_id, "state": "single"})
        else:
            overlap_samples += 1
            classified.append({**sample, "session_id": None, "state": "overlap", "active_count": len(active)})

    global_baseline = median(baseline_global) if baseline_global else None
    per_room: Dict[str, Dict[str, Any]] = {}
    per_session: Dict[int, Dict[str, Any]] = {}
    candidate_sessions: Dict[int, Dict[str, Any]] = {}
    used_samples = 0
    rejected_low = 0
    missing_baseline = 0
    rejected_warmup_cooldown = 0
    rejected_short_sessions = 0
    rejected_short_samples = 0

    for sample in classified:
        if sample["state"] != "single":
            continue
        session_id = sample["session_id"]
        session_item = sessions_by_id.get(session_id)
        if not session_item:
            continue
        sample_time = sample["time"]
        if not (session_item["measure_start"] <= sample_time < session_item["measure_end"]):
            rejected_warmup_cooldown += 1
            continue
        baseline_values = baseline_by_day_hour.get((sample_time.date(), sample_time.hour)) or baseline_by_day.get(sample_time.date())
        baseline = median(baseline_values) if baseline_values else global_baseline
        if baseline is None:
            missing_baseline += 1
            continue
        net_w = sample["diff_w"] - baseline
        if net_w <= 500:
            rejected_low += 1
            continue

        if session_id not in candidate_sessions:
            candidate_sessions[session_id] = {
                **session_item,
                "net_values": [],
                "observed_values": [],
                "baseline_values": [],
            }
        candidate_sessions[session_id]["net_values"].append(net_w)
        candidate_sessions[session_id]["observed_values"].append(sample["diff_w"])
        candidate_sessions[session_id]["baseline_values"].append(baseline)

    for session_id, session_item in candidate_sessions.items():
        net_values = session_item["net_values"]
        if len(net_values) < min_samples_per_session:
            rejected_short_sessions += 1
            rejected_short_samples += len(net_values)
            continue
        room_id = session_item["room_id"]
        bed = bed_lookup.get(room_id)
        if room_id not in per_room:
            per_room[room_id] = {
                "room_id": room_id,
                "label": sun2_room_label(room_id, getattr(bed, "name", None) if bed else None),
                "sun2_bed_id": getattr(bed, "sun2_bed_id", None) if bed else session_item.get("sun2_bed_id"),
                "bed_model": getattr(bed, "bed_model", None) if bed else None,
                "samples_count": 0,
                "sessions": set(),
                "net_values": [],
                "observed_values": [],
                "baseline_values": [],
                "estimated_kwh": 0.0,
                "duration_minutes": 0.0,
            }
        target = per_room[room_id]
        target["samples_count"] += len(net_values)
        target["sessions"].add(session_id)
        target["net_values"].extend(net_values)
        target["observed_values"].extend(session_item["observed_values"])
        target["baseline_values"].extend(session_item["baseline_values"])
        target["estimated_kwh"] += sum(net_values) / 1000 / 60
        used_samples += len(net_values)
        per_session[session_id] = {
            **session_item,
            "label": target["label"],
            "net_values": list(net_values),
            "observed_values": list(session_item["observed_values"]),
            "baseline_values": list(session_item["baseline_values"]),
        }

    rooms = []
    for item in per_room.values():
        net_values = item.pop("net_values")
        observed_values = item.pop("observed_values")
        baseline_values = item.pop("baseline_values")
        session_count = len(item.pop("sessions"))
        avg_w = sum(net_values) / len(net_values) if net_values else None
        median_w = median(net_values) if net_values else None
        estimate_w = median_w
        item.update(
            {
                "sessions_count": session_count,
                "avg_w": avg_w,
                "median_w": median_w,
                "estimate_w": estimate_w,
                "p25_w": percentile(net_values, 0.25),
                "p75_w": percentile(net_values, 0.75),
                "min_w": min(net_values) if net_values else None,
                "max_w": max(net_values) if net_values else None,
                "avg_observed_w": sum(observed_values) / len(observed_values) if observed_values else None,
                "avg_baseline_w": sum(baseline_values) / len(baseline_values) if baseline_values else None,
                "kwh_10_min": (estimate_w or 0) / 1000 * (10 / 60),
                "kwh_15_min": (estimate_w or 0) / 1000 * (15 / 60),
                "kwh_20_min": (estimate_w or 0) / 1000 * (20 / 60),
                "confidence": "Høy" if len(net_values) >= 60 and session_count >= 5 else "Middels" if len(net_values) >= 20 and session_count >= 2 else "Lav",
            }
        )
        rooms.append(item)
    rooms.sort(key=lambda item: (item.get("room_id") or ""))

    observations = []
    for item in per_session.values():
        net_values = item["net_values"]
        if not net_values:
            continue
        observations.append(
            {
                "session_id": item["id"],
                "room_id": item["room_id"],
                "label": item["label"],
                "start": item["start"],
                "end": item["end"],
                "duration_minutes": item["duration_minutes"],
                "samples_count": len(net_values),
                "avg_w": sum(net_values) / len(net_values),
                "median_w": median(net_values),
                "avg_observed_w": sum(item["observed_values"]) / len(item["observed_values"]),
                "avg_baseline_w": sum(item["baseline_values"]) / len(item["baseline_values"]),
            }
        )
    observations.sort(key=lambda item: item["start"], reverse=True)

    return {
        "rooms": rooms,
        "observations": observations[:80],
        "summary": {
            "sessions_total": len(session_items),
            "energy_samples_total": len(sample_items),
            "baseline_samples": len(baseline_global),
            "single_samples": used_samples,
            "overlap_samples": overlap_samples,
            "missing_baseline_samples": missing_baseline,
            "rejected_low_samples": rejected_low,
            "rejected_warmup_cooldown_samples": rejected_warmup_cooldown,
            "rejected_short_sessions": rejected_short_sessions,
            "rejected_short_samples": rejected_short_samples,
            "global_baseline_w": global_baseline,
            "rooms_count": len(rooms),
            "warmup_minutes": warmup_minutes,
            "cooldown_minutes": cooldown_minutes,
            "stop_before_end_minutes": stop_before_end_minutes,
            "min_samples_per_session": min_samples_per_session,
        },
    }


def merged_extra(data: EventDataIn):
    extra = dict(data.extra or {})
    if data.device_key:
        extra["device_key"] = data.device_key
    if data.values:
        extra["values"] = data.values
    for key in ("weather_type", "weather_symbol", "weather_text", "yr_weather", "yr_symbol"):
        value = getattr(data, key)
        if value not in (None, ""):
            extra[key] = value
    return extra or None


def light_from_payload(data: EventDataIn) -> OutdoorLightEvent:
    return OutdoorLightEvent(
        timestamp=data.timestamp or datetime.utcnow(),
        event_type=data.event_type,
        action=data.action,
        device_key=data.device_key,
        device_id=data.device_id,
        device_name=data.device_name,
        mode=data.mode,
        reason=data.reason,
        source=data.source,
        lux=value_from_payload(data, "lux"),
        value=value_from_payload(data, "value"),
        state=value_from_payload(data, "state"),
        extra=merged_extra(data),
    )


def payload_weather_symbol(data: EventDataIn) -> Optional[str]:
    return (
        data.weather_symbol
        or data.yr_symbol
        or nested_extra_value(data.extra, ["weather_symbol", "yr_symbol", "symbol_code", "next_1_hours_symbol_code"])
        or nested_extra_value(data.values, ["weather_symbol", "yr_symbol", "symbol_code", "next_1_hours_symbol_code"])
    )


def payload_weather_text(data: EventDataIn) -> Optional[str]:
    return (
        data.weather_text
        or data.weather_type
        or data.yr_weather
        or nested_extra_value(data.extra, ["weather_text", "weather_type", "yr_weather", "weather", "condition_text", "condition"])
        or nested_extra_value(data.values, ["weather_text", "weather_type", "yr_weather", "weather", "condition_text", "condition"])
    )


def light_sample_from_payload(data: EventDataIn, met_weather: Optional[Dict[str, Any]] = None) -> OutdoorLightSample:
    timestamp = data.timestamp or datetime.utcnow()
    weather_symbol = payload_weather_symbol(data) or ((met_weather or {}).get("symbol") or None)
    weather_text = weather_label(payload_weather_text(data)) or ((met_weather or {}).get("text") or None)
    return OutdoorLightSample(
        timestamp=timestamp,
        bucket_start=data.bucket_start or sample_bucket(timestamp),
        mode=data.mode,
        source=data.source,
        lux=value_from_payload(data, "lux"),
        value=value_from_payload(data, "value"),
        light_lyslist=value_from_payload(data, "light_lyslist"),
        light_reklame=value_from_payload(data, "light_reklame"),
        light_spot_glass_275=value_from_payload(data, "light_spot_glass_275"),
        light_spot_glass_299=value_from_payload(data, "light_spot_glass_299"),
        light_spot_inngang=value_from_payload(data, "light_spot_inngang"),
        light_parkering=value_from_payload(data, "light_parkering"),
        weather_symbol=weather_symbol,
        weather_text=weather_text,
        extra=merged_extra(data),
    )


def yr_sample_from_forecast(
    timestamp: datetime,
    bucket_start: datetime,
    source: Optional[str],
    forecast: Dict[str, Any],
) -> YrForecastSample:
    return YrForecastSample(
        timestamp=timestamp,
        bucket_start=bucket_start,
        source=source or "MET/Yr Locationforecast",
        api_updated_at=forecast.get("api_updated_at"),
        last_modified=forecast.get("last_modified"),
        expires_at=forecast.get("expires_at"),
        next_fetch_after=forecast.get("next_fetch_after"),
        age_seconds=forecast.get("age_seconds"),
        forecast_time=forecast.get("forecast_time"),
        symbol_code=forecast.get("symbol") or None,
        weather_text=forecast.get("text") or None,
        air_temperature=forecast.get("air_temperature"),
        air_temperature_percentile_10=forecast.get("air_temperature_percentile_10"),
        air_temperature_percentile_90=forecast.get("air_temperature_percentile_90"),
        relative_humidity=forecast.get("relative_humidity"),
        wind_speed=forecast.get("wind_speed"),
        wind_speed_of_gust=forecast.get("wind_speed_of_gust"),
        wind_speed_percentile_10=forecast.get("wind_speed_percentile_10"),
        wind_speed_percentile_90=forecast.get("wind_speed_percentile_90"),
        wind_from_direction=forecast.get("wind_from_direction"),
        cloud_area_fraction=forecast.get("cloud_area_fraction"),
        cloud_area_fraction_high=forecast.get("cloud_area_fraction_high"),
        cloud_area_fraction_medium=forecast.get("cloud_area_fraction_medium"),
        cloud_area_fraction_low=forecast.get("cloud_area_fraction_low"),
        fog_area_fraction=forecast.get("fog_area_fraction"),
        dew_point_temperature=forecast.get("dew_point_temperature"),
        air_pressure_at_sea_level=forecast.get("air_pressure_at_sea_level"),
        ultraviolet_index_clear_sky=forecast.get("ultraviolet_index_clear_sky"),
        precipitation_next_1h=forecast.get("precipitation_next_1h"),
        precipitation_next_1h_min=forecast.get("precipitation_next_1h_min"),
        precipitation_next_1h_max=forecast.get("precipitation_next_1h_max"),
        precipitation_next_6h=forecast.get("precipitation_next_6h"),
        precipitation_next_6h_min=forecast.get("precipitation_next_6h_min"),
        precipitation_next_6h_max=forecast.get("precipitation_next_6h_max"),
        probability_of_precipitation_next_1h=forecast.get("probability_of_precipitation_next_1h"),
        probability_of_precipitation_next_6h=forecast.get("probability_of_precipitation_next_6h"),
        probability_of_precipitation_next_12h=forecast.get("probability_of_precipitation_next_12h"),
        probability_of_thunder_next_1h=forecast.get("probability_of_thunder_next_1h"),
        air_temperature_min_next_6h=forecast.get("air_temperature_min_next_6h"),
        air_temperature_max_next_6h=forecast.get("air_temperature_max_next_6h"),
        symbol_confidence_next_12h=forecast.get("symbol_confidence_next_12h"),
        temp_1h=forecast.get("temp_1h"),
        temp_3h=forecast.get("temp_3h"),
        temp_6h=forecast.get("temp_6h"),
        temp_12h=forecast.get("temp_12h"),
        temp_24h=forecast.get("temp_24h"),
        symbol_1h=forecast.get("symbol_1h"),
        symbol_3h=forecast.get("symbol_3h"),
        symbol_6h=forecast.get("symbol_6h"),
        symbol_12h=forecast.get("symbol_12h"),
        symbol_24h=forecast.get("symbol_24h"),
        temp_min_next_6h=forecast.get("temp_min_next_6h"),
        temp_max_next_6h=forecast.get("temp_max_next_6h"),
        extra=yr_sample_extra(forecast),
        raw=yr_sample_raw(forecast),
    )


YR_FORECAST_ASSIGNMENTS = [
    ("api_updated_at", "api_updated_at"),
    ("last_modified", "last_modified"),
    ("expires_at", "expires_at"),
    ("next_fetch_after", "next_fetch_after"),
    ("age_seconds", "age_seconds"),
    ("forecast_time", "forecast_time"),
    ("symbol_code", "symbol"),
    ("weather_text", "text"),
    ("air_temperature", "air_temperature"),
    ("air_temperature_percentile_10", "air_temperature_percentile_10"),
    ("air_temperature_percentile_90", "air_temperature_percentile_90"),
    ("relative_humidity", "relative_humidity"),
    ("wind_speed", "wind_speed"),
    ("wind_speed_of_gust", "wind_speed_of_gust"),
    ("wind_speed_percentile_10", "wind_speed_percentile_10"),
    ("wind_speed_percentile_90", "wind_speed_percentile_90"),
    ("wind_from_direction", "wind_from_direction"),
    ("cloud_area_fraction", "cloud_area_fraction"),
    ("cloud_area_fraction_high", "cloud_area_fraction_high"),
    ("cloud_area_fraction_medium", "cloud_area_fraction_medium"),
    ("cloud_area_fraction_low", "cloud_area_fraction_low"),
    ("fog_area_fraction", "fog_area_fraction"),
    ("dew_point_temperature", "dew_point_temperature"),
    ("air_pressure_at_sea_level", "air_pressure_at_sea_level"),
    ("ultraviolet_index_clear_sky", "ultraviolet_index_clear_sky"),
    ("precipitation_next_1h", "precipitation_next_1h"),
    ("precipitation_next_1h_min", "precipitation_next_1h_min"),
    ("precipitation_next_1h_max", "precipitation_next_1h_max"),
    ("precipitation_next_6h", "precipitation_next_6h"),
    ("precipitation_next_6h_min", "precipitation_next_6h_min"),
    ("precipitation_next_6h_max", "precipitation_next_6h_max"),
    ("probability_of_precipitation_next_1h", "probability_of_precipitation_next_1h"),
    ("probability_of_precipitation_next_6h", "probability_of_precipitation_next_6h"),
    ("probability_of_precipitation_next_12h", "probability_of_precipitation_next_12h"),
    ("probability_of_thunder_next_1h", "probability_of_thunder_next_1h"),
    ("air_temperature_min_next_6h", "air_temperature_min_next_6h"),
    ("air_temperature_max_next_6h", "air_temperature_max_next_6h"),
    ("symbol_confidence_next_12h", "symbol_confidence_next_12h"),
    ("temp_1h", "temp_1h"),
    ("temp_3h", "temp_3h"),
    ("temp_6h", "temp_6h"),
    ("temp_12h", "temp_12h"),
    ("temp_24h", "temp_24h"),
    ("symbol_1h", "symbol_1h"),
    ("symbol_3h", "symbol_3h"),
    ("symbol_6h", "symbol_6h"),
    ("symbol_12h", "symbol_12h"),
    ("symbol_24h", "symbol_24h"),
    ("temp_min_next_6h", "temp_min_next_6h"),
    ("temp_max_next_6h", "temp_max_next_6h"),
]


def yr_sample_extra(forecast: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "raw_meta": forecast.get("raw_meta") or {},
        "timeseries_count": forecast.get("timeseries_count"),
    }


def yr_sample_raw(forecast: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "endpoint": forecast.get("raw_endpoint"),
        "coordinates": forecast.get("raw_coordinates"),
        "headers": forecast.get("raw_headers") or {},
        "payload": forecast.get("raw_payload") or {},
    }


def update_yr_sample_from_forecast(record: YrForecastSample, forecast: Dict[str, Any]) -> None:
    for attr, key in YR_FORECAST_ASSIGNMENTS:
        value = forecast.get(key)
        if attr == "symbol_code":
            value = value or None
        elif attr == "weather_text":
            value = value or None
        setattr(record, attr, value)
    record.extra = yr_sample_extra(forecast)
    record.raw = yr_sample_raw(forecast)


async def save_yr_sample_for_payload(data: EventDataIn, forecast: Optional[Dict[str, Any]] = None) -> Optional[int]:
    forecast = forecast or await met_weather_cached()
    if not forecast:
        return None
    timestamp = data.timestamp or datetime.utcnow()
    bucket_start = data.bucket_start or sample_bucket(timestamp)
    expires_at = forecast.get("expires_at")
    api_updated_at = forecast.get("api_updated_at")
    async with async_session() as session:
        stmt = select(YrForecastSample).limit(1)
        if expires_at:
            stmt = stmt.where(YrForecastSample.expires_at == expires_at)
        elif api_updated_at:
            stmt = stmt.where(YrForecastSample.api_updated_at == api_updated_at)
        else:
            stmt = stmt.where(YrForecastSample.bucket_start == bucket_start)
        existing = (await session.execute(stmt)).scalars().first()
        if existing:
            update_yr_sample_from_forecast(existing, forecast)
            await session.commit()
            return existing.id
        record = yr_sample_from_forecast(timestamp, bucket_start, data.source, forecast)
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record.id


def vent_from_payload(data: EventDataIn) -> VentilationEvent:
    return VentilationEvent(
        timestamp=data.timestamp or datetime.utcnow(),
        event_type=data.event_type,
        action=data.action,
        device_key=data.device_key,
        device_id=data.device_id,
        device_name=data.device_name,
        mode=data.mode,
        reason=data.reason,
        source=data.source,
        value=value_from_payload(data, "value"),
        state=value_from_payload(data, "state"),
        temp_1etg=value_from_payload(data, "temp_1etg"),
        temp_2etg=value_from_payload(data, "temp_2etg"),
        temp_vip=value_from_payload(data, "temp_vip"),
        temp_ute=value_from_payload(data, "temp_ute"),
        temp_loft=value_from_payload(data, "temp_loft"),
        humidity_1etg=value_from_payload(data, "humidity_1etg"),
        humidity_2etg=value_from_payload(data, "humidity_2etg"),
        humidity_vip=value_from_payload(data, "humidity_vip"),
        humidity_ute=value_from_payload(data, "humidity_ute"),
        humidity_yr=value_from_payload(data, "humidity_yr"),
        humidity_loft=value_from_payload(data, "humidity_loft"),
        temp_kjeller=value_from_payload(data, "temp_kjeller"),
        humidity_kjeller=value_from_payload(data, "humidity_kjeller"),
        temp_passiv=value_from_payload(data, "temp_passiv"),
        temp_luftinntak=value_from_payload(data, "temp_luftinntak"),
        humidity_passiv=value_from_payload(data, "humidity_passiv"),
        humidity_luftinntak=value_from_payload(data, "humidity_luftinntak"),
        diff_w=value_from_payload(data, "diff_w"),
        power_w=value_from_payload(data, "power_w"),
        energy_kwh=value_from_payload(data, "energy_kwh"),
        fan_vip=value_from_payload(data, "fan_vip"),
        fan_2etg=value_from_payload(data, "fan_2etg"),
        fan_tak=value_from_payload(data, "fan_tak"),
        fan_avfukter=value_from_payload(data, "fan_avfukter"),
        extra=merged_extra(data),
    )


def vent_sample_from_payload(data: EventDataIn) -> VentilationSample:
    timestamp = data.timestamp or datetime.utcnow()
    return VentilationSample(
        timestamp=timestamp,
        bucket_start=data.bucket_start or sample_bucket(timestamp),
        mode=data.mode,
        source=data.source,
        temp_1etg=value_from_payload(data, "temp_1etg"),
        temp_2etg=value_from_payload(data, "temp_2etg"),
        temp_vip=value_from_payload(data, "temp_vip"),
        temp_ute=value_from_payload(data, "temp_ute"),
        temp_ute_netatmo=value_from_payload(data, "temp_ute_netatmo"),
        temp_yr=value_from_payload(data, "temp_yr"),
        temp_loft=value_from_payload(data, "temp_loft"),
        humidity_1etg=value_from_payload(data, "humidity_1etg"),
        humidity_2etg=value_from_payload(data, "humidity_2etg"),
        humidity_vip=value_from_payload(data, "humidity_vip"),
        humidity_ute=value_from_payload(data, "humidity_ute"),
        humidity_yr=value_from_payload(data, "humidity_yr"),
        humidity_loft=value_from_payload(data, "humidity_loft"),
        temp_kjeller=value_from_payload(data, "temp_kjeller"),
        humidity_kjeller=value_from_payload(data, "humidity_kjeller"),
        temp_passiv=value_from_payload(data, "temp_passiv"),
        temp_luftinntak=value_from_payload(data, "temp_luftinntak"),
        humidity_passiv=value_from_payload(data, "humidity_passiv"),
        humidity_luftinntak=value_from_payload(data, "humidity_luftinntak"),
        temp_min_inne=value_from_payload(data, "temp_min_inne"),
        temp_avg_inne=value_from_payload(data, "temp_avg_inne"),
        temp_max_inne=value_from_payload(data, "temp_max_inne"),
        diff_w=value_from_payload(data, "diff_w"),
        estimated_sunbeds=value_from_payload(data, "estimated_sunbeds"),
        afterrun_active=value_from_payload(data, "afterrun_active"),
        heat_need=value_from_payload(data, "heat_need"),
        cool_need=value_from_payload(data, "cool_need"),
        open_time=value_from_payload(data, "open_time"),
        pre_cooling=value_from_payload(data, "pre_cooling"),
        exhaust_time_allowed=value_from_payload(data, "exhaust_time_allowed"),
        fan_vip=value_from_payload(data, "fan_vip"),
        fan_2etg=value_from_payload(data, "fan_2etg"),
        fan_tak=value_from_payload(data, "fan_tak"),
        fan_avfukter=value_from_payload(data, "fan_avfukter"),
        extra=merged_extra(data),
    )


async def upsert_kjeller_measurement_sample(session, timestamp: datetime, fibaroid: int, value: float, source: str) -> Optional[int]:
    field_map = {
        408: "humidity_1etg",
        344: "humidity_2etg",
        347: "humidity_vip",
        350: "humidity_ute",
        353: "humidity_loft",
        357: "humidity_luftinntak",
        359: "humidity_2etg",
        362: "humidity_vip",
        444: "temp_kjeller",
        445: "humidity_kjeller",
    }
    field = field_map.get(fibaroid)
    if not field:
        return None
    bucket_start = sample_bucket(timestamp)
    row = (
        await session.execute(
            select(VentilationSample)
            .where(VentilationSample.bucket_start == bucket_start)
            .order_by(VentilationSample.id.desc())
            .limit(1)
        )
    ).scalars().first()
    if not row:
        row = VentilationSample(
            timestamp=timestamp,
            bucket_start=bucket_start,
            source=source,
            extra={"measurement_source": "hc3_meter_readings"},
        )
        session.add(row)
        await session.flush()
    else:
        row.timestamp = max(row.timestamp or timestamp, timestamp)
        row.source = row.source or source
        row.extra = {
            **(row.extra or {}),
            "measurement_source": "hc3_meter_readings",
        }
    setattr(row, field, value)
    return row.id


def generic_from_payload(data: EventDataIn) -> GenericEvent:
    return GenericEvent(
        timestamp=data.timestamp or datetime.utcnow(),
        system=data.system,
        event_type=data.event_type,
        action=data.action,
        device_key=data.device_key,
        device_id=data.device_id,
        device_name=data.device_name,
        mode=data.mode,
        reason=data.reason,
        source=data.source,
        lux=value_from_payload(data, "lux"),
        value=value_from_payload(data, "value"),
        state=value_from_payload(data, "state"),
        extra=merged_extra(data),
    )


def apply_common_filters(stmt, model, event_type, action, device_key, device_id, mode, source_contains, from_ts, to_ts):
    if event_type:
        stmt = stmt.where(model.event_type == event_type)
    if action:
        stmt = stmt.where(model.action == action)
    if device_key:
        stmt = stmt.where(model.device_key == device_key)
    if device_id is not None:
        stmt = stmt.where(model.device_id == device_id)
    if mode:
        stmt = stmt.where(model.mode == mode)
    if source_contains:
        stmt = stmt.where(model.source.ilike(f"%{source_contains}%"))
    if from_ts:
        stmt = stmt.where(model.timestamp >= from_ts)
    if to_ts:
        stmt = stmt.where(model.timestamp <= to_ts)
    return stmt


async def save_record(record) -> int:
    async with async_session() as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record.id


async def ingest_roborock_robot(session, robot_data: Dict[str, Any], batch_time: datetime, source: str) -> Dict[str, Any]:
    duid = robot_data.get("duid") or robot_data.get("robot_duid")
    if not duid:
        return {"ok": False, "error": "Mangler DUID"}

    meta = robot_data.get("metadata") or robot_data
    network = robot_data.get("network") or {}
    capabilities = robot_data.get("capabilities") or robot_data.get("probe_results") or {}
    local_ip = robot_data.get("local_ip") or network.get("ip") or meta.get("local_ip")
    status = first_dict(robot_data.get("status"))
    consumable = first_dict(robot_data.get("consumables") or robot_data.get("consumable"))
    cloud_online = bool_value(meta.get("online") if "online" in meta else meta.get("cloud_online"))

    existing = (
        await session.execute(select(RoborockRobot).where(RoborockRobot.duid == duid))
    ).scalars().first()
    if not existing:
        existing = RoborockRobot(duid=duid, name=meta.get("name") or duid)
        session.add(existing)

    existing.name = meta.get("name") or existing.name or duid
    existing.product = robot_data.get("product") or meta.get("product") or meta.get("product_id") or existing.product
    existing.model = robot_data.get("model") or meta.get("model") or existing.model
    existing.firmware = meta.get("firmware") or meta.get("fv") or existing.firmware
    existing.protocol_version = meta.get("protocol_version") or meta.get("pv") or existing.protocol_version
    existing.serial_number = robot_data.get("serial_number") or meta.get("serial_number") or meta.get("sn") or existing.serial_number
    existing.local_ip = local_ip or existing.local_ip
    existing.cloud_online = cloud_online if cloud_online is not None else existing.cloud_online
    existing.shared = bool_value(meta.get("shared") if "shared" in meta else meta.get("share"))
    existing.time_zone_id = meta.get("time_zone_id") or meta.get("timezone") or existing.time_zone_id
    existing.last_seen_at = batch_time
    if robot_data.get("cloud"):
        existing.last_cloud_at = batch_time
    if status or network:
        existing.last_local_at = batch_time
    if status:
        existing.last_status_at = batch_time
    if robot_data.get("map"):
        existing.last_map_at = batch_time
    existing.last_error = robot_data.get("last_error") or robot_data.get("error") or None
    existing.capabilities = capabilities or existing.capabilities
    existing.extra = {
        "source": source,
        "metadata": meta,
        "summary": robot_data.get("clean_summary"),
    }

    if status:
        session.add(
            RoborockStatusSample(
                robot_duid=duid,
                timestamp=batch_time,
                source=source,
                state_code=int_value(status.get("state")),
                state_name=status.get("state_name") or roborock_state_label(status.get("state")),
                battery=int_value(status.get("battery")),
                error_code=int_value(status.get("error_code") if "error_code" in status else status.get("error")),
                in_cleaning=bool_value(status.get("in_cleaning")),
                in_returning=bool_value(status.get("in_returning")),
                clean_time_seconds=int_value(status.get("clean_time")),
                clean_area_m2=area_m2_from_payload(status.get("clean_area")),
                fan_power=int_value(status.get("fan_power")),
                water_box_mode=int_value(status.get("water_box_mode")),
                mop_mode=int_value(status.get("mop_mode")),
                dock_type=int_value(status.get("dock_type")),
                charge_status=int_value(status.get("charge_status")),
                clean_percent=int_value(status.get("clean_percent")),
                local_ip=local_ip,
                rssi=int_value(network.get("rssi")),
                raw={"status": status, "network": network},
            )
        )

    if consumable:
        session.add(
            RoborockConsumableSnapshot(
                robot_duid=duid,
                timestamp=batch_time,
                main_brush_work_time=int_value(consumable.get("main_brush_work_time")),
                side_brush_work_time=int_value(consumable.get("side_brush_work_time")),
                filter_work_time=int_value(consumable.get("filter_work_time")),
                sensor_dirty_time=int_value(consumable.get("sensor_dirty_time")),
                dust_collection_work_times=int_value(consumable.get("dust_collection_work_times")),
                raw=consumable,
            )
        )

    for job in robot_data.get("clean_jobs") or robot_data.get("jobs") or []:
        record_id = str(job.get("id") or job.get("record_id") or "")
        if not record_id:
            continue
        existing_job = (
            await session.execute(
                select(RoborockCleanJob)
                .where(RoborockCleanJob.robot_duid == duid)
                .where(RoborockCleanJob.record_id == record_id)
            )
        ).scalars().first()
        if not existing_job:
            existing_job = RoborockCleanJob(robot_duid=duid, record_id=record_id)
            session.add(existing_job)
        existing_job.begin_at = timestamp_value(job.get("begin") or job.get("begin_at"))
        existing_job.end_at = timestamp_value(job.get("end") or job.get("end_at"))
        existing_job.duration_seconds = int_value(job.get("duration_seconds") or job.get("duration"))
        existing_job.duration_minutes = float_value(job.get("duration_minutes"))
        existing_job.area_m2 = float_value(job.get("area_m2")) or area_m2_from_payload(job.get("area"))
        existing_job.cleaned_area_m2 = float_value(job.get("cleaned_area_m2")) or area_m2_from_payload(job.get("cleaned_area"))
        existing_job.complete = bool_value(job.get("complete"))
        existing_job.error_code = int_value(job.get("error") if "error" in job else job.get("error_code"))
        existing_job.start_type = int_value(job.get("start_type"))
        existing_job.clean_type = int_value(job.get("clean_type"))
        existing_job.finish_reason = int_value(job.get("finish_reason"))
        existing_job.dust_collection_status = int_value(job.get("dust_collection_status"))
        existing_job.avoid_count = int_value(job.get("avoid_count"))
        existing_job.wash_count = int_value(job.get("wash_count"))
        existing_job.clean_times = int_value(job.get("clean_times"))
        existing_job.updated_at = batch_time
        existing_job.raw = job

    for schedule in robot_data.get("schedules") or []:
        schedule_id = str(schedule.get("id") or schedule.get("schedule_id") or "")
        if not schedule_id:
            continue
        params = roborock_schedule_params(schedule)
        existing_schedule = (
            await session.execute(
                select(RoborockSchedule)
                .where(RoborockSchedule.robot_duid == duid)
                .where(RoborockSchedule.schedule_id == schedule_id)
            )
        ).scalars().first()
        if not existing_schedule:
            existing_schedule = RoborockSchedule(robot_duid=duid, schedule_id=schedule_id)
            session.add(existing_schedule)
        existing_schedule.cron = schedule.get("cron")
        existing_schedule.enabled = bool_value(schedule.get("enabled"))
        existing_schedule.repeated = bool_value(schedule.get("repeated"))
        existing_schedule.segments = params.get("segments")
        existing_schedule.fan_power = int_value(params.get("fan_power"))
        existing_schedule.mop_mode = int_value(params.get("mop_mode"))
        existing_schedule.water_box_mode = int_value(params.get("water_box_mode"))
        existing_schedule.repeat = int_value(params.get("repeat"))
        existing_schedule.updated_at = batch_time
        existing_schedule.raw = schedule

    map_data = robot_data.get("map") or {}
    if map_data:
        image_size = map_data.get("image_size") or []
        if not isinstance(image_size, list):
            image_size = []
        session.add(
            RoborockMapSnapshot(
                robot_duid=duid,
                timestamp=batch_time,
                image_bytes=int_value(map_data.get("image_bytes")),
                raw_bytes=int_value(map_data.get("raw_bytes")),
                image_width=int_value(image_size[0] if len(image_size) > 0 else map_data.get("image_width")),
                image_height=int_value(image_size[1] if len(image_size) > 1 else map_data.get("image_height")),
                rooms=int_value(map_data.get("rooms")),
                zones=int_value(map_data.get("zones")),
                charger=map_data.get("charger"),
                vacuum_position=map_data.get("vacuum_position"),
                image_base64=map_data.get("image_base64"),
                raw={key: value for key, value in map_data.items() if key != "image_base64"},
            )
        )

    for probe in robot_data.get("probe_results") or []:
        session.add(
            RoborockProbeResult(
                robot_duid=duid,
                timestamp=batch_time,
                source=probe.get("source") or source,
                command=probe.get("command") or probe.get("name"),
                ok=bool_value(probe.get("ok")),
                error=probe.get("error"),
                result_type=probe.get("type") or probe.get("result_type"),
                raw=probe,
            )
        )
    return {"ok": True, "duid": duid}


async def ingest_sun2_room_stats(session, data: Sun2RoomStatsIngestIn, batch_time: datetime) -> Dict[str, int]:
    inserted = 0
    updated = 0
    batch_date = data.stat_date
    for row in data.rows:
        source_room_name = (repair_mojibake(row.source_room_name or row.room) or "").strip()
        room = (repair_mojibake(row.room) or source_room_name).strip()
        room_key = (repair_mojibake(row.room_key) or room_key_from_name(source_room_name) or room_key_from_name(room) or room).strip()
        identity = sun2_room_identity(source_room_name or room, row.room_id, row.sun2_bed_id)
        if not room:
            continue
        stat_date = row.stat_date or batch_date
        existing = (
            await session.execute(
                select(Sun2RoomDailyStat)
                .where(Sun2RoomDailyStat.stat_date == stat_date)
                .where(Sun2RoomDailyStat.room_key == room_key)
            )
        ).scalars().first()
        if not existing:
            existing = (
                await session.execute(
                    select(Sun2RoomDailyStat)
                    .where(Sun2RoomDailyStat.stat_date == stat_date)
                    .where(Sun2RoomDailyStat.room == room)
                )
            ).scalars().first()
        if not existing:
            same_day = (
                await session.execute(
                    select(Sun2RoomDailyStat).where(Sun2RoomDailyStat.stat_date == stat_date)
                )
            ).scalars().all()
            existing = next(
                (
                    candidate for candidate in same_day
                    if repair_mojibake(candidate.room) == room
                    or repair_mojibake(candidate.source_room_name) == source_room_name
                    or (candidate.room_key and repair_mojibake(candidate.room_key) == room_key)
                ),
                None,
            )
        if not existing:
            existing = Sun2RoomDailyStat(stat_date=stat_date, room=room)
            session.add(existing)
            inserted += 1
        else:
            updated += 1

        existing.room_key = room_key
        existing.room_id = identity.get("room_id")
        existing.room = room
        existing.source_room_name = source_room_name
        existing.sun2_bed_id = identity.get("sun2_bed_id")
        existing.total_soletid_minutter = row.total_soletid_minutter
        existing.totalt_antall_solinger = row.totalt_antall_solinger
        existing.solinger_medlemmer = row.solinger_medlemmer
        existing.solinger_ikke_medlemmer = row.solinger_ikke_medlemmer
        existing.totalt_inntjent_kr = row.totalt_inntjent_kr
        existing.inntjent_medlemmer_kr = row.inntjent_medlemmer_kr
        existing.inntjent_ikke_medlemmer_kr = row.inntjent_ikke_medlemmer_kr
        existing.source = data.source
        existing.source_file = data.source_file
        existing.imported_at = batch_time
        existing.raw = row.raw or {}

    return {"inserted": inserted, "updated": updated}


async def ingest_sun2_beds(session, data: Sun2BedsIngestIn, batch_time: datetime) -> Dict[str, int]:
    inserted = 0
    updated = 0
    skipped = 0
    for row in data.beds:
        bed_id = (repair_mojibake(row.sun2_bed_id) or "").strip()
        name = (repair_mojibake(row.name) or "").strip()
        if not bed_id or not name:
            skipped += 1
            continue
        identity = sun2_room_identity(row.source_room_name or name, row.room_id, bed_id)
        existing = (
            await session.execute(
                select(Sun2Bed).where(Sun2Bed.sun2_bed_id == bed_id)
            )
        ).scalars().first()
        if not existing:
            existing = Sun2Bed(sun2_bed_id=bed_id, name=name)
            session.add(existing)
            inserted += 1
        else:
            updated += 1

        existing.room_id = row.room_id or identity.get("room_id")
        existing.physical_room_number = row.physical_room_number or identity.get("physical_room_number")
        existing.display_room_number = row.display_room_number or identity.get("display_room_number")
        existing.sun2_center_id = (repair_mojibake(row.sun2_center_id) or "").strip() or None
        existing.sun2_bed_id = bed_id
        existing.name = name
        existing.source_room_name = (repair_mojibake(row.source_room_name) or name).strip() or None
        existing.bed_model = (repair_mojibake(row.bed_model) or "").strip() or None
        existing.bed_model_id = (repair_mojibake(row.bed_model_id) or "").strip() or None
        existing.max_minutes = row.max_minutes
        existing.startup_minutes = row.startup_minutes
        existing.cooldown_minutes = row.cooldown_minutes
        existing.current_price_per_min = row.current_price_per_min
        existing.status = (repair_mojibake(row.status) or "").strip() or None
        existing.status_code = (repair_mojibake(row.status_code) or "").strip() or None
        existing.lamp_status = (repair_mojibake(row.lamp_status) or "").strip() or None
        existing.source = data.source
        existing.imported_at = batch_time
        existing.raw = row.raw or {}
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


async def ingest_sun2_members(session, data: Sun2MembersIngestIn, batch_time: datetime) -> Dict[str, int]:
    inserted = 0
    updated = 0
    skipped = 0
    source = data.source or "sun2_session_scraper"
    for row in data.members:
        sun2_user_id = (repair_mojibake(row.sun2_user_id) or "").strip()
        if not sun2_user_id:
            skipped += 1
            continue
        existing = (
            await session.execute(
                select(Sun2Member).where(Sun2Member.sun2_user_id == sun2_user_id)
            )
        ).scalars().first()
        if not existing:
            existing = Sun2Member(sun2_user_id=sun2_user_id)
            session.add(existing)
            inserted += 1
        else:
            updated += 1

        existing.sun2_center_id = (repair_mojibake(row.sun2_center_id) or "").strip() or existing.sun2_center_id
        existing.name = (repair_mojibake(row.name) or "").strip() or None
        existing.display_name = (repair_mojibake(row.display_name) or "").strip() or existing.name or None
        existing.initials = (repair_mojibake(row.initials) or "").strip() or None
        existing.age = row.age
        existing.email = (repair_mojibake(row.email) or "").strip() or None
        existing.phone = (repair_mojibake(row.phone) or "").strip() or None
        existing.profile_url = (repair_mojibake(row.profile_url) or "").strip() or None
        existing.customer_type = (repair_mojibake(row.customer_type) or "").strip() or None
        existing.gender = (repair_mojibake(row.gender) or "").strip() or None
        existing.birth_date = row.birth_date
        existing.member_since = row.member_since
        existing.last_seen_at = row.last_seen_at
        existing.status = (repair_mojibake(row.status) or "").strip() or None
        existing.balance_kr = row.balance_kr
        existing.total_spent_kr = row.total_spent_kr
        existing.visits_count = row.visits_count
        existing.source = source
        existing.source_file = (repair_mojibake(row.source_file or "") or "").strip() or None
        existing.imported_at = batch_time
        existing.raw = row.raw or {}
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


async def ingest_sun2_tanning_sessions(session, data: Sun2TanningSessionsIngestIn, batch_time: datetime) -> Dict[str, int]:
    inserted = 0
    updated = 0
    skipped = 0
    source = data.source or "sun2_session_scraper"
    source_file = (repair_mojibake(data.source_file) or "").strip()
    replaced = 0

    if source_file and data.rows:
        result = await session.execute(
            delete(Sun2TanningSession)
            .where(Sun2TanningSession.source == source)
            .where(Sun2TanningSession.source_file == source_file)
        )
        replaced = int(result.rowcount or 0)

    for row in data.rows:
        source_session_id = (repair_mojibake(row.source_session_id) or "").strip()
        if not source_session_id or not row.started_at:
            skipped += 1
            continue
        source_room_name = (repair_mojibake(row.source_room_name or row.room) or "").strip()
        room = (repair_mojibake(row.room) or source_room_name).strip()
        room_key = (repair_mojibake(row.room_key) or room_key_from_name(source_room_name) or room_key_from_name(room) or "").strip()
        identity = sun2_room_identity(source_room_name or room, row.room_id, row.sun2_bed_id)
        stat_date = row.stat_date or row.started_at.date()

        existing = (
            await session.execute(
                select(Sun2TanningSession)
                .where(Sun2TanningSession.source == source)
                .where(Sun2TanningSession.source_session_id == source_session_id)
            )
        ).scalars().first()

        if not existing:
            legacy_source_session_id = str((row.raw or {}).get("legacy_source_session_id") or "").strip()
            if legacy_source_session_id:
                existing = (
                    await session.execute(
                        select(Sun2TanningSession)
                        .where(Sun2TanningSession.source == source)
                        .where(Sun2TanningSession.source_session_id == legacy_source_session_id)
                    )
                ).scalars().first()

        if not existing:
            natural_query = (
                select(Sun2TanningSession)
                .where(Sun2TanningSession.source == source)
                .where(Sun2TanningSession.started_at == row.started_at)
                .where(Sun2TanningSession.stat_date == stat_date)
                .where(Sun2TanningSession.duration_minutes == row.duration_minutes)
                .where(Sun2TanningSession.paid_amount_kr == row.paid_amount_kr)
            )
            if identity.get("sun2_bed_id"):
                natural_query = natural_query.where(Sun2TanningSession.sun2_bed_id == identity.get("sun2_bed_id"))
            elif identity.get("room_id"):
                natural_query = natural_query.where(Sun2TanningSession.room_id == identity.get("room_id"))
            if row.sun2_user_id:
                natural_query = natural_query.where(Sun2TanningSession.sun2_user_id == row.sun2_user_id)
            elif row.user_identifier:
                natural_query = natural_query.where(Sun2TanningSession.user_identifier == row.user_identifier)
            existing = (await session.execute(natural_query)).scalars().first()

        if not existing:
            existing = Sun2TanningSession(source=source, source_session_id=source_session_id)
            session.add(existing)
            inserted += 1
        else:
            updated += 1

        existing.source = source
        existing.source_session_id = source_session_id
        existing.started_at = row.started_at
        existing.ended_at = row.ended_at
        existing.stat_date = stat_date
        existing.room_id = identity.get("room_id")
        existing.room_key = room_key or None
        existing.room = room or None
        existing.source_room_name = source_room_name or None
        existing.sun2_user_id = (repair_mojibake(row.sun2_user_id) or "").strip() or None
        existing.sun2_center_id = (repair_mojibake(row.sun2_center_id) or "").strip() or None
        existing.sun2_bed_id = identity.get("sun2_bed_id")
        existing.user_name = (repair_mojibake(row.user_name) or "").strip() or None
        existing.user_identifier = (repair_mojibake(row.user_identifier) or "").strip() or None
        existing.customer_type = (repair_mojibake(row.customer_type) or "").strip() or None
        existing.gender = (repair_mojibake(row.gender) or "").strip() or None
        existing.payment_method = (repair_mojibake(row.payment_method) or "").strip() or None
        existing.duration_minutes = row.duration_minutes
        existing.paid_amount_kr = row.paid_amount_kr
        existing.status = (repair_mojibake(row.status) or "").strip() or None
        existing.source_file = source_file or data.source_file
        existing.imported_at = batch_time
        existing.raw = row.raw or {}

    return {"inserted": inserted, "updated": updated, "skipped": skipped, "replaced": replaced}


async def backfill_sun2_room_identity(session) -> Dict[str, int]:
    counts = {"daily": 0, "sessions": 0}
    for model, key in [(Sun2RoomDailyStat, "daily"), (Sun2TanningSession, "sessions")]:
        source_text = func.lower(func.trim(func.coalesce(model.source_room_name, model.room, model.room_key, "")))
        missing_identity = or_(model.room_id.is_(None), model.sun2_bed_id.is_(None))
        old_room = await session.execute(
            update(model)
            .where(missing_identity)
            .where(or_(source_text == ".", source_text == "-"))
            .values(room_id=SUN2_ROOM_UNKNOWN_OLD_10["room_id"], sun2_bed_id=SUN2_ROOM_UNKNOWN_OLD_10["sun2_bed_id"])
        )
        counts[key] += int(old_room.rowcount or 0)

        for display_number, identity in SUN2_ROOM_MAP_BY_DISPLAY.items():
            room_text = f"rom {display_number}"
            result = await session.execute(
                update(model)
                .where(missing_identity)
                .where(or_(source_text == room_text, source_text.like(f"{room_text} %")))
                .values(room_id=identity["room_id"], sun2_bed_id=identity["sun2_bed_id"])
            )
            counts[key] += int(result.rowcount or 0)
    return counts


async def ingest_elvia_hours(session, parsed: Dict[str, Any], batch_time: datetime) -> Dict[str, int]:
    rows = parsed["rows"]
    if not rows:
        return {"inserted": 0, "updated": 0, "skipped": 0}

    meter_id = parsed["meter_id"]
    first_at = parsed["first_at"]
    last_at = parsed["last_at"]
    existing_rows = (
        await session.execute(
            select(EnergyHourlyConsumption)
            .where(EnergyHourlyConsumption.meter_id == meter_id)
            .where(EnergyHourlyConsumption.measured_at >= first_at)
            .where(EnergyHourlyConsumption.measured_at <= last_at)
        )
    ).scalars().all()
    existing_by_time = {row.measured_at: row for row in existing_rows}
    inserted = 0
    updated = 0
    skipped = 0

    for row in rows:
        existing = existing_by_time.get(row["measured_at"])
        if not existing:
            existing = EnergyHourlyConsumption(meter_id=meter_id, measured_at=row["measured_at"])
            session.add(existing)
            inserted += 1
        else:
            if not energy_hour_has_changed(existing, row):
                skipped += 1
                continue
            updated += 1

        existing.stat_date = row["stat_date"]
        existing.year = row["year"]
        existing.month = row["month"]
        existing.day = row["day"]
        existing.hour = row["hour"]
        existing.consumption_kwh = row["consumption_kwh"]
        existing.production_kwh = row["production_kwh"]
        existing.status = row["status"]
        existing.is_verified = row["is_verified"]
        existing.is_estimated = row["is_estimated"]
        existing.is_public_holiday = row["is_public_holiday"]
        existing.use_weekend_prices = row["use_weekend_prices"]
        existing.source = "elvia"
        existing.source_file = parsed["source_file"]
        existing.imported_at = batch_time
        existing.raw = row["raw"]

    return {"inserted": inserted, "updated": updated, "skipped": skipped}


async def run_elvia_import_background(content: bytes, filename: str):
    started_at = local_now_naive()
    batch_time = datetime.utcnow()
    try:
        parsed = parse_elvia_json_payload(content, filename)
        if not parsed["rows"]:
            raise ValueError("Filen inneholder ingen timeverdier som kan importeres.")
        async with async_session() as session:
            counts = await ingest_elvia_hours(session, parsed, batch_time)
            message = (
                f"{counts['inserted']} nye, {counts['updated']} oppdatert, "
                f"{counts['skipped']} uendret for måler {parsed['meter_id']}."
            )
            session.add(
                EnergyImportRun(
                    timestamp=batch_time,
                    meter_id=parsed["meter_id"],
                    source="elvia",
                    ok=True,
                    source_file=filename,
                    period_first=parsed["first_at"],
                    period_last=parsed["last_at"],
                    days_count=parsed["days_count"],
                    hours_count=parsed["hours_count"],
                    inserted_count=counts["inserted"],
                    updated_count=counts["updated"],
                    skipped_count=counts["skipped"],
                    total_kwh=parsed["total_kwh"],
                    estimated_hours_count=parsed["estimated_hours_count"],
                    message=message,
                    raw={"partial_months": parsed["partial_months"]},
                )
            )
            await record_import_job(
                session,
                "elvia_monthly_import",
                source="elvia",
                started_at=started_at,
                finished_at=local_now_naive(),
                records_imported=counts["inserted"] + counts["updated"],
                records_total=parsed["hours_count"],
                duration_seconds=(local_now_naive() - started_at).total_seconds(),
                message=message,
                raw={"source_file": filename, "partial_months": parsed["partial_months"], "counts": counts},
            )
            await session.commit()
        clear_summary_cache("energy")
    except (json.JSONDecodeError, UnicodeDecodeError):
        error = "Filen kunne ikke leses som gyldig JSON."
        async with async_session() as session:
            session.add(EnergyImportRun(timestamp=batch_time, source="elvia", ok=False, source_file=filename, message=error))
            await record_import_job(
                session,
                "elvia_monthly_import",
                ok=False,
                source="elvia",
                started_at=started_at,
                finished_at=local_now_naive(),
                duration_seconds=(local_now_naive() - started_at).total_seconds(),
                message=error,
                raw={"source_file": filename},
            )
            await session.commit()
    except Exception as exc:
        error = str(exc)
        async with async_session() as session:
            session.add(EnergyImportRun(timestamp=batch_time, source="elvia", ok=False, source_file=filename, message=error))
            await record_import_job(
                session,
                "elvia_monthly_import",
                ok=False,
                source="elvia",
                started_at=started_at,
                finished_at=local_now_naive(),
                duration_seconds=(local_now_naive() - started_at).total_seconds(),
                message=error,
                raw={"source_file": filename},
            )
            await session.commit()


async def fetch_rows(model, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, limit, time_basis: str = "source"):
    from_ts = parse_datetime(from_text)
    to_ts = parse_datetime(to_text)
    if time_basis == "utc":
        from_ts = local_naive_to_utc_naive(from_ts)
        to_ts = local_naive_to_utc_naive(to_ts)
    limit = max(1, min(limit, 10000))
    stmt = select(model).order_by(model.timestamp.desc()).limit(limit)
    stmt = apply_common_filters(stmt, model, event_type, action, device_key, device_id, mode, source_contains, from_ts, to_ts)
    async with async_session() as session:
        result = await session.execute(stmt)
        return result.scalars().all(), limit


async def csv_response(model, columns, filename, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, time_basis: str = "source"):
    rows, _ = await fetch_rows(model, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, 10000, time_basis=time_basis)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        row_dict = row_to_dict(row, columns)
        writer.writerow([json_value(row_dict.get(column)) for column in columns])
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def ai_jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: ai_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [ai_jsonable(item) for item in value]
    return value


def ai_dataset_overview() -> list[Dict[str, Any]]:
    return [
        {
            "key": key,
            "table": dataset["table"],
            "title": repair_mojibake(dataset["title"]),
            "description": repair_mojibake(dataset["description"]),
            "time_column": dataset.get("time_column"),
            "columns_count": len(dataset["columns"]),
        }
        for key, dataset in AI_DATASETS.items()
    ]


def ai_dataset_schema(dataset_key: str) -> Dict[str, Any]:
    dataset = AI_DATASETS.get((dataset_key or "").strip())
    if not dataset:
        return {"ok": False, "error": "Ukjent datasett", "datasets": list(AI_DATASETS)}
    return {
        "ok": True,
        "key": dataset_key,
        "table": dataset["table"],
        "title": repair_mojibake(dataset["title"]),
        "description": repair_mojibake(dataset["description"]),
        "time_column": dataset.get("time_column"),
        "columns": dataset["columns"],
    }


def validate_ai_sql(sql: str) -> tuple[bool, str]:
    sql_clean = (sql or "").strip()
    if not re.match(r"(?is)^select\b", sql_clean):
        return False, "Kun SELECT-spørringer er tillatt."
    if ";" in sql_clean or "--" in sql_clean or "/*" in sql_clean or "*/" in sql_clean:
        return False, "Kommentarer og flere SQL-setninger er ikke tillatt."
    forbidden = r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|execute|call|merge|vacuum|analyze)\b"
    if re.search(forbidden, sql_clean, flags=re.IGNORECASE):
        return False, "Spørringen inneholder ikke-tillatte SQL-kommandoer."
    from_match = re.search(r"(?is)\bfrom\b(.*?)(\bwhere\b|\bgroup\b|\border\b|\blimit\b|$)", sql_clean)
    if from_match and "," in from_match.group(1):
        return False, "Bruk eksplisitt JOIN i stedet for kommaseparerte tabeller."
    allowed_tables = {dataset["table"].lower() for dataset in AI_DATASETS.values()}
    used_tables = {
        match.group(1).split(".")[-1].strip('"').lower()
        for match in re.finditer(r"(?is)\b(?:from|join)\s+([a-zA-Z_][\w.]*)", sql_clean)
    }
    if not used_tables:
        return False, "Fant ingen tabell i spørringen."
    unknown = sorted(table for table in used_tables if table not in allowed_tables)
    if unknown:
        return False, f"Tabellen er ikke godkjent for AI-søk: {', '.join(unknown)}"
    return True, ""


async def run_safe_ai_sql(sql: str, limit: int = 200) -> Dict[str, Any]:
    ok, error = validate_ai_sql(sql)
    if not ok:
        return {"ok": False, "error": error, "rows": []}
    safe_limit = max(1, min(int_value(limit) or 200, 500))
    wrapped_sql = f"SELECT * FROM ({sql.strip()}) AS ai_query LIMIT {safe_limit}"
    async with async_session() as session:
        result = await session.execute(sql_text(wrapped_sql))
        rows = [dict(row._mapping) for row in result.fetchall()]
    return {
        "ok": True,
        "limit": safe_limit,
        "count": len(rows),
        "rows": ai_jsonable(rows),
    }


def ai_tools_definition() -> list[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": "list_datasets",
            "description": "Lister alle datasett og tabeller som kan brukes til analyse.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "type": "function",
            "name": "get_dataset_schema",
            "description": "Henter tabellnavn, kolonner og beskrivelse for ett datasett.",
            "parameters": {
                "type": "object",
                "properties": {"dataset": {"type": "string"}},
                "required": ["dataset"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "run_safe_sql",
            "description": "Kjører en trygg SELECT-spørring mot godkjente tabeller. Bruk alltid LIMIT eller argumentet limit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                },
                "required": ["sql"],
                "additionalProperties": False,
            },
        },
    ]


async def run_ai_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "list_datasets":
        return {"ok": True, "datasets": ai_dataset_overview()}
    if name == "get_dataset_schema":
        return ai_dataset_schema(str(arguments.get("dataset") or ""))
    if name == "run_safe_sql":
        return await run_safe_ai_sql(str(arguments.get("sql") or ""), int_value(arguments.get("limit")) or 200)
    return {"ok": False, "error": f"Ukjent verktøy: {name}"}


AI_CONFIG_KEY = "ai"


def openai_env_api_key() -> str:
    return (os.getenv("OPENAI_API_KEY") or "").strip()


def mask_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    value = str(value)
    if len(value) <= 10:
        return "********"
    return f"{value[:7]}...{value[-4:]}"


async def get_ai_config() -> ControlConfig:
    async with async_session() as session:
        row = (await session.execute(select(ControlConfig).where(ControlConfig.key == AI_CONFIG_KEY))).scalars().first()
        if row:
            return row
        row = ControlConfig(
            key=AI_CONFIG_KEY,
            version=1,
            values={"openai_api_key": "", "openai_model": OPENAI_MODEL},
            updated_by="system",
        )
        session.add(row)
        session.add(
            ControlConfigHistory(
                config_key=AI_CONFIG_KEY,
                version=1,
                values={"openai_api_key": "", "openai_model": OPENAI_MODEL},
                changed_by="system",
                reason="AI-innstillinger opprettet",
            )
        )
        await session.commit()
        await session.refresh(row)
        return row


async def effective_openai_settings() -> Dict[str, Any]:
    env_key = openai_env_api_key()
    row = await get_ai_config()
    values = row.values or {}
    stored_key = str(values.get("openai_api_key") or "").strip()
    stored_model = str(values.get("openai_model") or "").strip()
    return {
        "api_key": env_key or stored_key,
        "source": "Servermiljøvariabel" if env_key else ("App-innstilling" if stored_key else "Mangler"),
        "has_env_key": bool(env_key),
        "has_stored_key": bool(stored_key),
        "stored_key_masked": mask_secret(stored_key),
        "model": stored_model or OPENAI_MODEL,
        "config": row,
    }


def openai_responses_request(payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    if not api_key:
        raise RuntimeError("OpenAI API key mangler.")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=75) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI svarte {exc.code}: {body[:800]}") from exc


def response_output_text(response: Dict[str, Any]) -> str:
    if response.get("output_text"):
        return str(response["output_text"]).strip()
    parts = []
    for item in response.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                parts.append(str(content["text"]))
    return "\n".join(parts).strip()


def response_function_calls(response: Dict[str, Any]) -> list[Dict[str, Any]]:
    return [item for item in response.get("output", []) or [] if item.get("type") == "function_call"]


async def ask_ai(question: str, username: str) -> Dict[str, Any]:
    question = (question or "").strip()
    if not question:
        return {"ok": False, "answer": "", "error": "Skriv inn et spørsmål først.", "tool_calls": []}
    openai_settings = await effective_openai_settings()
    api_key = openai_settings["api_key"]
    model = openai_settings["model"]
    if not api_key:
        return {
            "ok": False,
            "answer": "",
            "error": "OpenAI API key mangler. Legg den inn under AI > Innstillinger eller som OPENAI_API_KEY på serveren.",
            "tool_calls": [],
        }

    system_prompt = (
        "Du er analyseassistent for SUN2 Lillehammer sin Fibaro10-applikasjon. "
        "Svar på norsk, kort og konkret, men forklar metode når tallene kan misforstås. "
        "Du har bare lov til å bruke verktøyene for å se datasett, skjema og lese data. "
        "Ikke finn opp tall. Hvis data mangler, si det tydelig. "
        "Når du trenger data, bruk først list_datasets eller get_dataset_schema, og kjør deretter run_safe_sql. "
        "SQL skal være enkel SELECT mot godkjente tabeller."
    )
    tools = ai_tools_definition()
    conversation_items = [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": question}],
        }
    ]
    payload = {
        "model": model,
        "instructions": system_prompt,
        "tools": tools,
        "input": conversation_items,
    }
    response = await asyncio.to_thread(openai_responses_request, payload, api_key)
    tool_log: list[Dict[str, Any]] = []

    for _ in range(6):
        calls = response_function_calls(response)
        if not calls:
            answer = response_output_text(response)
            return {"ok": bool(answer), "answer": answer, "error": "" if answer else "Fikk ikke svar fra modellen.", "tool_calls": tool_log}

        outputs = []
        for call in calls:
            try:
                args = json.loads(call.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            result = await run_ai_tool(call.get("name") or "", args)
            tool_log.append(
                {
                    "name": call.get("name"),
                    "arguments": args,
                    "ok": result.get("ok", True),
                    "count": result.get("count"),
                    "error": result.get("error"),
                }
            )
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call.get("call_id"),
                    "output": json.dumps(result, ensure_ascii=False, default=str),
                }
            )
        conversation_items.extend(response.get("output", []) or [])
        conversation_items.extend(outputs)
        response = await asyncio.to_thread(
            openai_responses_request,
            {
                "model": model,
                "instructions": system_prompt,
                "tools": tools,
                "input": conversation_items,
            },
            api_key,
        )

    return {"ok": False, "answer": response_output_text(response), "error": "AI-søket stoppet etter for mange verktøykall.", "tool_calls": tool_log}


async def recent_ai_logs(limit: int = 10) -> list[AiQueryLog]:
    async with async_session() as session:
        result = await session.execute(select(AiQueryLog).order_by(AiQueryLog.timestamp.desc()).limit(limit))
        return result.scalars().all()


@app.on_event("startup")
async def startup():
    global svv_sync_task
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for table_name, columns in STARTUP_COLUMNS.items():
            for column_name, column_type in columns:
                await conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type}")
        for _, statement in PERFORMANCE_INDEXES:
            await conn.execute(sql_text(statement))
        await conn.execute(delete(OutdoorLightEvent).where(OutdoorLightEvent.source == "CODEX TEST"))
        await conn.execute(delete(VentilationEvent).where(VentilationEvent.source == "CODEX TEST"))
    async with async_session() as session:
        result = await session.execute(select(AccessKey).where(AccessKey.key_hash == MASTER_ACCESS_KEY_HASH))
        master = result.scalars().first()
        if master:
            master.name = "master"
            master.key_prefix = "sun2_master"
            master.is_master = True
            master.role = "master"
            master.active = True
        else:
            session.add(
                AccessKey(
                    name="master",
                    key_hash=MASTER_ACCESS_KEY_HASH,
                    key_prefix="sun2_master",
                    role="master",
                    is_master=True,
                    active=True,
                )
            )
        legacy_shared = (
            await session.execute(
                select(AccessKey)
                .where(AccessKey.is_master == False)
                .where(AccessKey.key_plaintext.isnot(None))
            )
        ).scalars().all()
        for key in legacy_shared:
            username = normalize_username(key.name)
            password = key.key_plaintext or ""
            if not key.role:
                key.role = "viewer"
            if username and password:
                key.name = username
                key.key_hash = credential_hash(username, password)
                key.key_prefix = credential_prefix(username, password)
        await session.commit()
    async with async_session() as session:
        for config_key in CONFIG_DEFINITIONS:
            await get_or_create_config(session, config_key)
        await seed_energy_circuits(session)
        await session.commit()
    if SVV_SYNC_ENABLED and SVV_API_KEY and svv_sync_task is None:
        svv_sync_task = asyncio.create_task(parking_vehicle_svv_worker())


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "storage": [
            "utelys_events", "utelys_samples", "ventilasjon_events", "ventilasjon_samples",
            "yr_forecast_samples", "control_configs", "control_config_history", "event_data",
            "roborock_robots", "roborock_status_samples", "roborock_clean_jobs",
            "roborock_schedules", "roborock_consumables", "roborock_maps",
            "import_job_status", "import_job_runs",
            "sun2_room_daily_stats", "sun2_import_runs", "sun2_tanning_sessions",
            "sun2_beds", "sun2_session_import_runs", "energy_hourly_consumption",
            "energy_import_runs", "energy_fibaro_samples", "energy_circuits", "energy_loads", "hc3_meter_readings",
            "parkering", "kjoretoy", "kjoretoy_nokkeldata", "ai_query_logs",
        ],
    }


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(
        "static/favicon.ico",
        media_type="image/x-icon",
        headers={"Cache-Control": "public, max-age=604800, immutable"},
    )


@app.get("/auth/login", response_class=HTMLResponse)
async def login_view(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": ""})


def redirect_keep_query(request: Request, target: str, status_code: int = 307) -> RedirectResponse:
    query = request.url.query
    if query:
        separator = "&" if "?" in target else "?"
        target = f"{target}{separator}{query}"
    return RedirectResponse(target, status_code=status_code)


def redirect_with_query_params(request: Request, target: str, status_code: int = 303, **params: Any) -> RedirectResponse:
    query = dict(request.query_params)
    query.update({key: str(value) for key, value in params.items() if value not in (None, "")})
    if query:
        separator = "&" if "?" in target else "?"
        target = f"{target}{separator}{urlencode(query)}"
    return RedirectResponse(target, status_code=status_code)


def should_use_secure_cookie(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
    return request.url.scheme == "https" or forwarded_proto == "https"


@app.post("/auth/login")
async def login_submit(request: Request):
    form = await parse_form_body(request)
    username = normalize_username(form.get("username") or "")
    password = (form.get("password") or "").strip()
    access_key = await find_access_key(username, password)
    if not access_key:
        await log_access_attempt(request, False, "failed_login", attempted_username=username)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Ugyldig brukernavn eller passord"},
            status_code=401,
        )
    response = RedirectResponse("/status/dashboard", status_code=303)
    secure_cookie = should_use_secure_cookie(request)
    response.set_cookie(
        AUTH_USER_COOKIE_NAME,
        username,
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
    await log_access_attempt(request, True, "login", access_key)
    return response


@app.post("/konto/logg-ut")
async def logout():
    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie(AUTH_USER_COOKIE_NAME)
    response.delete_cookie(AUTH_COOKIE_NAME)
    return response


@app.get("/ai")
async def ai_redirect(request: Request):
    return redirect_keep_query(request, "/ai/sok", status_code=303)


@app.get("/lys")
async def lights_redirect(request: Request):
    return redirect_keep_query(request, "/lys/dagslogg-lux", status_code=307)


@app.get("/ventilasjon")
async def ventilation_redirect(request: Request):
    return redirect_keep_query(request, "/ventilasjon/dagslogg-temp", status_code=307)


@app.get("/ai/sok", response_class=HTMLResponse)
async def ai_search_view(request: Request):
    openai_settings = await effective_openai_settings()
    context = {
        "question": "",
        "result": None,
        "datasets": ai_dataset_overview(),
        "logs": await recent_ai_logs(),
        "api_ready": bool(openai_settings["api_key"]),
        "model": openai_settings["model"],
    }
    return templates.TemplateResponse(request, "ai_search.html", context)


@app.post("/ai/sok", response_class=HTMLResponse)
async def ai_search_submit(request: Request):
    form = await parse_form_body(request)
    question = (form.get("question") or "").strip()
    username = getattr(request.state, "access_key_name", "") or ""
    try:
        result = await ask_ai(question, username)
    except Exception as exc:
        result = {"ok": False, "answer": "", "error": str(exc), "tool_calls": []}
    async with async_session() as session:
        session.add(
            AiQueryLog(
                username=username,
                question=question,
                answer=result.get("answer") or None,
                ok=bool(result.get("ok")),
                error=result.get("error") or None,
                tool_calls_count=len(result.get("tool_calls") or []),
                raw={"tool_calls": result.get("tool_calls") or []},
            )
        )
        await session.commit()
    openai_settings = await effective_openai_settings()
    context = {
        "question": question,
        "result": result,
        "datasets": ai_dataset_overview(),
        "logs": await recent_ai_logs(),
        "api_ready": bool(openai_settings["api_key"]),
        "model": openai_settings["model"],
    }
    return templates.TemplateResponse(request, "ai_search.html", context)


@app.get("/ai/innstillinger", response_class=HTMLResponse)
async def ai_settings_view(request: Request):
    settings = await effective_openai_settings()
    return templates.TemplateResponse(
        request,
        "ai_settings.html",
        {
            "settings": settings,
            "saved": False,
            "error": "",
            "openai_key_url": "https://platform.openai.com/api-keys",
        },
    )


@app.post("/ai/innstillinger", response_class=HTMLResponse)
async def ai_settings_update(request: Request):
    forbidden = require_settings_access(request)
    if forbidden:
        return forbidden
    form = await parse_form_body(request)
    new_key = (form.get("openai_api_key") or "").strip()
    model = (form.get("openai_model") or OPENAI_MODEL).strip() or OPENAI_MODEL
    clear_key = form.get("clear_openai_api_key") == "1"
    if new_key and not new_key.startswith("sk-"):
        settings = await effective_openai_settings()
        settings["model"] = model
        return templates.TemplateResponse(
            request,
            "ai_settings.html",
            {
                "settings": settings,
                "saved": False,
                "error": "Nøkkelen ser ikke ut som en OpenAI API key. Den starter normalt med sk-.",
                "openai_key_url": "https://platform.openai.com/api-keys",
            },
            status_code=400,
        )
    changed_by = getattr(request.state, "access_key_name", "") or "master"
    async with async_session() as session:
        row = (await session.execute(select(ControlConfig).where(ControlConfig.key == AI_CONFIG_KEY))).scalars().first()
        if not row:
            row = ControlConfig(
                key=AI_CONFIG_KEY,
                version=1,
                values={"openai_api_key": "", "openai_model": model},
                updated_by=changed_by,
            )
            session.add(row)
            await session.flush()
        values = dict(row.values or {})
        if clear_key:
            values["openai_api_key"] = ""
        elif new_key:
            values["openai_api_key"] = new_key
        values["openai_model"] = model
        row.values = values
        row.version = (row.version or 1) + 1
        row.updated_at = datetime.utcnow()
        row.updated_by = changed_by
        history_values = dict(values)
        if history_values.get("openai_api_key"):
            history_values["openai_api_key"] = mask_secret(history_values["openai_api_key"])
        session.add(
            ControlConfigHistory(
                config_key=AI_CONFIG_KEY,
                version=row.version,
                values=history_values,
                changed_by=changed_by,
                reason="AI-innstillinger endret",
            )
        )
        await session.commit()
    settings = await effective_openai_settings()
    return templates.TemplateResponse(
        request,
        "ai_settings.html",
        {
            "settings": settings,
            "saved": True,
            "error": "",
            "openai_key_url": "https://platform.openai.com/api-keys",
        },
    )


@app.get("/api/ai/datasets/json")
async def ai_datasets_json():
    return {"datasets": ai_dataset_overview()}


@app.get("/api/ai/logs/json")
async def ai_logs_json(limit: int = Query(25, ge=1, le=200)):
    logs = await recent_ai_logs(limit)
    return {"rows": [row_to_dict(row, AI_QUERY_COLUMNS) for row in logs]}


@app.get("/konto/oversikt", response_class=HTMLResponse)
async def account_view(request: Request):
    return templates.TemplateResponse(
        request,
        "account.html",
        {
            "ntfy_access_subscribe_url": ntfy_subscribe_url(NTFY_ACCESS_TOPIC, "SUN2 tilgang"),
            "ntfy_access_web_url": ntfy_topic_url(NTFY_ACCESS_TOPIC),
            "ntfy_access_cooldown_minutes": int(NTFY_ACCESS_COOLDOWN_MINUTES),
        },
    )


@app.get("/konto/build", response_class=HTMLResponse)
async def account_build_view(request: Request):
    return templates.TemplateResponse(
        request,
        "build_log.html",
        {
            "current_version": APP_VERSION,
            "current_build": APP_BUILD,
            "build_rows": BUILD_LOG,
        },
    )


@app.get("/konto/teknisk", response_class=HTMLResponse)
async def account_technical_view(request: Request):
    return templates.TemplateResponse(request, "technical.html", {})


@app.get("/konto/manual", response_class=HTMLResponse)
async def account_manual_view(request: Request):
    return templates.TemplateResponse(request, "manual.html", {})


@app.get("/energi/testside", response_class=HTMLResponse)
async def energy_view(request: Request):
    return RedirectResponse("/energi/status", status_code=307)


async def admin_keys_context(
    request: Request,
    session,
    created_username: str = "",
    created_key: str = "",
    error: str = "",
) -> Dict[str, Any]:
    key_rows = (await session.execute(select(AccessKey).order_by(AccessKey.created_at.desc()))).scalars().all()
    selected_key = None
    try:
        selected_key_id = int(request.query_params.get("key_id") or "0")
    except ValueError:
        selected_key_id = 0
    if selected_key_id:
        selected_key = next((key for key in key_rows if key.id == selected_key_id), None)

    log_query = select(AccessLog).order_by(AccessLog.timestamp.desc()).limit(200)
    if selected_key:
        log_query = (
            select(AccessLog)
            .where((AccessLog.access_key_id == selected_key.id) | (AccessLog.key_name == selected_key.name))
            .order_by(AccessLog.timestamp.desc())
            .limit(200)
        )
    log_rows = (await session.execute(log_query)).scalars().all()
    return {
        "keys": key_rows,
        "logs": log_rows,
        "selected_key": selected_key,
        "created_username": created_username,
        "created_key": created_key,
        "error": error,
        "ntfy_access_subscribe_url": ntfy_subscribe_url(NTFY_ACCESS_TOPIC, "SUN2 tilgang"),
        "ntfy_access_web_url": ntfy_topic_url(NTFY_ACCESS_TOPIC),
        "ntfy_access_cooldown_minutes": int(NTFY_ACCESS_COOLDOWN_MINUTES),
    }


@app.get("/konto/brukere-og-tilgang", response_class=HTMLResponse)
async def keys_view(request: Request):
    forbidden = require_master(request)
    if forbidden:
        return forbidden
    async with async_session() as session:
        context = await admin_keys_context(request, session)
    return templates.TemplateResponse(request, "keys.html", context)


@app.post("/konto/brukere-og-tilgang")
async def keys_create(request: Request):
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
    existing_hash = credential_hash(username, password)
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
            key_prefix=credential_prefix(username, password),
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


@app.post("/konto/brukere-og-tilgang/deaktiver")
async def keys_disable(request: Request):
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


@app.post("/konto/brukere-og-tilgang/aktiver")
async def keys_enable(request: Request):
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


@app.post("/konto/brukere-og-tilgang/rolle")
async def keys_role_update(request: Request):
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


async def config_context(config_key: str):
    definition = config_definition(config_key)
    if not definition:
        return None
    async with async_session() as session:
        row = await get_or_create_config(session, config_key)
        history = (
            await session.execute(
                select(ControlConfigHistory)
                .where(ControlConfigHistory.config_key == config_key)
                .order_by(ControlConfigHistory.changed_at.desc())
                .limit(20)
            )
        ).scalars().all()
    values = merge_config_values(config_key, row.values)
    return {
        "definition": definition,
        "config_key": config_key,
        "config": row,
        "values": values,
        "rules": config_rules(config_key, values),
        "summary_rows": config_summary_rows(config_key, values),
        "stat_cards": config_stat_cards(config_key, values, row.version),
        "operational_notes": config_operational_notes(config_key, values),
        "devices": config_devices(config_key),
        "history": history,
        "saved": False,
        "errors": [],
    }


@app.get("/api/config")
async def api_control_configs():
    async with async_session() as session:
        rows = [await get_or_create_config(session, config_key) for config_key in CONFIG_DEFINITIONS]
    return {"configs": [config_payload(row) for row in rows if row]}


@app.get("/api/config/{config_key}")
async def api_control_config(config_key: str):
    if config_key not in CONFIG_DEFINITIONS:
        return JSONResponse({"detail": "Ukjent konfigurasjon"}, status_code=404)
    async with async_session() as session:
        row = await get_or_create_config(session, config_key)
    return config_payload(row)


@app.get("/lys/innstillinger", response_class=HTMLResponse)
async def light_settings_view(request: Request):
    context = await config_context("lights")
    return templates.TemplateResponse(request, "control_settings.html", context)


@app.post("/lys/innstillinger", response_class=HTMLResponse)
async def light_settings_update(request: Request):
    return await update_settings(request, "lights")


@app.get("/ventilasjon/innstillinger", response_class=HTMLResponse)
async def ventilation_settings_view(request: Request):
    context = await config_context("ventilation")
    return templates.TemplateResponse(request, "control_settings.html", context)


@app.post("/ventilasjon/innstillinger", response_class=HTMLResponse)
async def ventilation_settings_update(request: Request):
    return await update_settings(request, "ventilation")


async def update_settings(request: Request, config_key: str):
    forbidden = require_settings_access(request)
    if forbidden:
        return forbidden
    form = await parse_form_body(request)
    values = config_values_from_form(config_key, form)
    errors = validate_config_values(config_key, values)
    if errors:
        context = await config_context(config_key)
        context["values"] = values
        context["rules"] = config_rules(config_key, values)
        context["summary_rows"] = config_summary_rows(config_key, values)
        context["stat_cards"] = config_stat_cards(config_key, values, context["config"].version)
        context["operational_notes"] = config_operational_notes(config_key, values)
        context["errors"] = errors
        return templates.TemplateResponse(request, "control_settings.html", context, status_code=400)
    reason = (form.get("reason") or "Endret i grensesnittet").strip()
    changed_by = getattr(request.state, "access_key_name", "") or "master"
    async with async_session() as session:
        row = await get_or_create_config(session, config_key)
        row.values = values
        row.version = (row.version or 1) + 1
        row.updated_at = datetime.utcnow()
        row.updated_by = changed_by
        session.add(
            ControlConfigHistory(
                config_key=config_key,
                version=row.version,
                values=deepcopy(values),
                changed_by=changed_by,
                reason=reason,
            )
        )
        await session.commit()
    context = await config_context(config_key)
    context["saved"] = True
    return templates.TemplateResponse(request, "control_settings.html", context)


@app.get("/")
async def root_redirect(request: Request):
    return redirect_keep_query(request, "/status/dashboard", status_code=303)


@app.get("/status/dashboard", response_class=HTMLResponse)
async def index(request: Request):
    today = local_now_naive().date()
    async with async_session() as session:
        lights = (await session.execute(select(OutdoorLightEvent).order_by(OutdoorLightEvent.timestamp.desc()).limit(200))).scalars().all()
        light_samples = (await session.execute(select(OutdoorLightSample).order_by(OutdoorLightSample.timestamp.desc()).limit(1))).scalars().all()
        ventilation = (await session.execute(select(VentilationEvent).order_by(VentilationEvent.timestamp.desc()).limit(100))).scalars().all()
        samples = (await session.execute(select(VentilationSample).order_by(VentilationSample.timestamp.desc()).limit(1))).scalars().all()
        yr_samples = (await session.execute(select(YrForecastSample).order_by(YrForecastSample.timestamp.desc()).limit(1))).scalars().all()
        import_rows = await import_status_rows(session)
        today = local_now_naive().date()
        yesterday = today - timedelta(days=1)
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        previous_week_start = week_start - timedelta(days=7)
        previous_month_last = month_start - timedelta(days=1)
        previous_month_start = previous_month_last.replace(day=1)
        previous_year_start = date(today.year - 1, 1, 1)
        today_start = datetime.combine(today, time.min)
        yesterday_start = today_start - timedelta(days=1)
        tomorrow_start = today_start + timedelta(days=1)
        week_start_dt = datetime.combine(week_start, time.min)
        month_start_dt = datetime.combine(month_start, time.min)
        year_start_dt = datetime.combine(year_start, time.min)
        previous_week_start_dt = datetime.combine(previous_week_start, time.min)
        previous_month_start_dt = datetime.combine(previous_month_start, time.min)
        previous_year_start_dt = datetime.combine(previous_year_start, time.min)
        current_week_span = tomorrow_start - week_start_dt
        current_month_span = tomorrow_start - month_start_dt
        current_year_span = tomorrow_start - year_start_dt
        previous_week_end_dt = previous_week_start_dt + current_week_span
        previous_month_end_dt = min(previous_month_start_dt + current_month_span, month_start_dt)
        previous_year_end_dt = min(previous_year_start_dt + current_year_span, year_start_dt)
        now_dt = local_now_naive()
        lux_spark_rows = (
            await session.execute(
                select(OutdoorLightSample)
                .where(OutdoorLightSample.timestamp >= today_start)
                .where(OutdoorLightSample.timestamp < min(now_dt, tomorrow_start))
                .order_by(OutdoorLightSample.timestamp.asc())
            )
        ).scalars().all()
        today_sun = (
            await session.execute(
                select(
                    func.count(Sun2TanningSession.id).label("sessions"),
                    func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("minutes"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                    func.count(func.distinct(Sun2TanningSession.room_id)).label("rooms"),
                ).where(Sun2TanningSession.stat_date == today)
            )
        ).one()
        week_sun = (
            await session.execute(
                select(
                    func.count(Sun2TanningSession.id).label("sessions"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                ).where(
                    Sun2TanningSession.stat_date >= week_start,
                    Sun2TanningSession.stat_date <= today,
                )
            )
        ).one()
        month_sun = (
            await session.execute(
                select(
                    func.count(Sun2TanningSession.id).label("sessions"),
                    func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("minutes"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                    func.count(func.distinct(Sun2TanningSession.room_id)).label("rooms"),
                ).where(
                    Sun2TanningSession.stat_date >= month_start,
                    Sun2TanningSession.stat_date <= today,
                )
            )
        ).one()
        year_sun = (
            await session.execute(
                select(
                    func.count(Sun2TanningSession.id).label("sessions"),
                    func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("minutes"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                    func.count(func.distinct(Sun2TanningSession.room_id)).label("rooms"),
                ).where(
                    Sun2TanningSession.stat_date >= year_start,
                    Sun2TanningSession.stat_date <= today,
                )
            )
        ).one()
        yesterday_sun = (
            await session.execute(
                select(
                    func.count(Sun2TanningSession.id).label("sessions"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                ).where(Sun2TanningSession.stat_date == yesterday)
            )
        ).one()
        previous_week_sun = (
            await session.execute(
                select(
                    func.count(Sun2TanningSession.id).label("sessions"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                ).where(
                    Sun2TanningSession.stat_date >= previous_week_start,
                    Sun2TanningSession.stat_date < previous_week_end_dt.date(),
                )
            )
        ).one()
        previous_month_sun = (
            await session.execute(
                select(
                    func.count(Sun2TanningSession.id).label("sessions"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                ).where(
                    Sun2TanningSession.stat_date >= previous_month_start,
                    Sun2TanningSession.stat_date < previous_month_end_dt.date(),
                )
            )
        ).one()
        previous_year_sun = (
            await session.execute(
                select(
                    func.count(Sun2TanningSession.id).label("sessions"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid"),
                ).where(
                    Sun2TanningSession.stat_date >= previous_year_start,
                    Sun2TanningSession.stat_date < previous_year_end_dt.date(),
                )
            )
        ).one()
        tomorrow = today + timedelta(days=1)
        today_sun = await sun2_period_snapshot(session, today, tomorrow)
        yesterday_sun = await sun2_period_snapshot(session, yesterday, today)
        week_sun = await sun2_period_snapshot(session, week_start, tomorrow)
        month_sun = await sun2_period_snapshot(session, month_start, tomorrow)
        year_sun = await sun2_period_snapshot(session, year_start, tomorrow)
        previous_week_sun = await sun2_period_snapshot(session, previous_week_start, previous_week_end_dt.date())
        previous_month_sun = await sun2_period_snapshot(session, previous_month_start, previous_month_end_dt.date())
        previous_year_sun = await sun2_period_snapshot(session, previous_year_start, previous_year_end_dt.date())
        today_parking = (
            await session.execute(
                select(
                    func.count(ParkingSession.id).label("sessions"),
                    func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                ).where(
                    ParkingSession.start_time >= today_start,
                    ParkingSession.start_time < tomorrow_start,
                )
            )
        ).one()
        week_parking = (
            await session.execute(
                select(
                    func.count(ParkingSession.id).label("sessions"),
                    func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                ).where(
                    ParkingSession.start_time >= week_start_dt,
                    ParkingSession.start_time < tomorrow_start,
                )
            )
        ).one()
        month_parking = (
            await session.execute(
                select(
                    func.count(ParkingSession.id).label("sessions"),
                    func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                ).where(
                    ParkingSession.start_time >= month_start_dt,
                    ParkingSession.start_time < tomorrow_start,
                )
            )
        ).one()
        year_parking = (
            await session.execute(
                select(
                    func.count(ParkingSession.id).label("sessions"),
                    func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                ).where(
                    ParkingSession.start_time >= year_start_dt,
                    ParkingSession.start_time < tomorrow_start,
                )
            )
        ).one()
        yesterday_parking = (
            await session.execute(
                select(
                    func.count(ParkingSession.id).label("sessions"),
                    func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                ).where(
                    ParkingSession.start_time >= yesterday_start,
                    ParkingSession.start_time < today_start,
                )
            )
        ).one()
        previous_week_parking = (
            await session.execute(
                select(
                    func.count(ParkingSession.id).label("sessions"),
                    func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                ).where(
                    ParkingSession.start_time >= previous_week_start_dt,
                    ParkingSession.start_time < previous_week_end_dt,
                )
            )
        ).one()
        previous_month_parking = (
            await session.execute(
                select(
                    func.count(ParkingSession.id).label("sessions"),
                    func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                ).where(
                    ParkingSession.start_time >= previous_month_start_dt,
                    ParkingSession.start_time < previous_month_end_dt,
                )
            )
        ).one()
        previous_year_parking = (
            await session.execute(
                select(
                    func.count(ParkingSession.id).label("sessions"),
                    func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0).label("paid"),
                ).where(
                    ParkingSession.start_time >= previous_year_start_dt,
                    ParkingSession.start_time < previous_year_end_dt,
                )
            )
        ).one()
        active_parking = (
            await session.execute(
                select(func.count(ParkingSession.id)).where(
                    ParkingSession.start_time <= now_dt,
                    or_(
                        ParkingSession.end_time.is_(None),
                        ParkingSession.end_time >= now_dt,
                        func.lower(func.coalesce(ParkingSession.status, "")) == "ongoing",
                    ),
                )
            )
        ).scalar_one()
        today_energy = (
            await session.execute(
                select(
                    func.coalesce(func.sum(EnergyHourlyConsumption.consumption_kwh), 0).label("kwh"),
                    func.count(EnergyHourlyConsumption.id).label("hours"),
                    func.max(EnergyHourlyConsumption.measured_at).label("last_at"),
                ).where(EnergyHourlyConsumption.stat_date == today)
            )
        ).one()
        latest_energy_sample = (
            await session.execute(
                select(EnergyFibaroSample)
                .order_by(EnergyFibaroSample.bucket_start.desc())
                .limit(1)
            )
        ).scalars().first()
        today_energy_fibaro = (
            await session.execute(
                select(
                    func.coalesce(func.sum(EnergyFibaroSample.inntak_delta_kwh), 0).label("kwh"),
                    func.count(EnergyFibaroSample.id).label("samples"),
                )
                .where(EnergyFibaroSample.bucket_start >= datetime.combine(today, time.min))
                .where(EnergyFibaroSample.bucket_start < datetime.combine(today, time.min) + timedelta(days=1))
            )
        ).one()
        robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
        schedules = (
            await session.execute(
                select(RoborockSchedule)
                .where(RoborockSchedule.enabled == True)
                .order_by(RoborockSchedule.cron)
            )
        ).scalars().all()

    latest_light_by_key = {}
    for row in lights:
        key = event_device_key(row, LIGHT_TIMELINE_DEVICES)
        if key and key not in latest_light_by_key:
            latest_light_by_key[key] = row

    latest_vent_by_key = {}
    for row in ventilation:
        key = event_device_key(row, VENT_TIMELINE_DEVICES)
        if key and key not in latest_vent_by_key:
            latest_vent_by_key[key] = row

    latest_sample = samples[0] if samples else None
    latest_light_sample = light_samples[0] if light_samples else None
    latest_yr_sample = yr_samples[0] if yr_samples else None
    latest_light = lights[0] if lights else None
    now_status = build_now_status(latest_sample, latest_light_sample, latest_light, latest_yr_sample)
    lux_sparkline = build_lux_sparkline(lux_spark_rows, today_start, tomorrow_start)

    light_status = []
    for device in LIGHT_TIMELINE_DEVICES:
        row = latest_light_by_key.get(device["key"])
        light_sample_value = light_sample_state(latest_light_sample, device) if latest_light_sample else None
        event_state = state_from_event(row) if row else None
        light_status.append(
            {
                "id": device["key"],
                "name": device["name"],
                "row": row,
                "state": light_sample_value if light_sample_value is not None else event_state,
                "sample_time": latest_light_sample.timestamp if light_sample_value is not None else None,
                "lux": row.lux if row and row.lux is not None else (
                    latest_light_sample.lux
                    if latest_light_sample and latest_light_sample.lux is not None
                    else None
                ),
            }
        )
    vent_status = [
        {
            "id": device["key"],
            "name": device["name"],
            "row": latest_vent_by_key.get(device["key"]),
            "state": sample_state(latest_sample, device),
        }
        for device in VENT_TIMELINE_DEVICES
    ]
    vent_status.append(
        {
            "id": "loft_recovery",
            "name": "Loft > 1.etg gjenvinning",
            "row": None,
            "state": False,
            "dummy_reason": "Planlagt varmegjenvinning fra loft til 1.etg. Ikke koblet til styring ennå.",
        }
    )
    freshness_items = [
        freshness_item("Temp logg", latest_sample, 7, 15),
        freshness_item("Lux logging", latest_light_sample, 7, 15),
        freshness_item("Yr API", latest_yr_sample, 70, 130),
        freshness_item("Lys-hendelser", lights[0] if lights else None, 120, 360),
        freshness_item("Ventilasjonshendelser", ventilation[0] if ventilation else None, 120, 360),
    ]
    import_counts = {
        "ok": sum(1 for row in import_rows if row["status"] == "ok"),
        "warn": sum(1 for row in import_rows if row["status"] == "warn"),
        "bad": sum(1 for row in import_rows if row["status"] == "bad"),
        "total": len(import_rows),
    }
    attention_items = []
    event_freshness_names = {"Lys-hendelser", "Ventilasjonshendelser"}
    for item in freshness_items:
        if item["name"] in event_freshness_names:
            continue
        if item["status"] in {"warn", "bad"}:
            attention_items.append(
                dashboard_alert(
                    item["status"],
                    item["name"],
                    f"{item['status_text']} - sist sett {item['age']}.",
                    "/status/datakilder",
                )
            )
    for row in import_rows:
        if row["status"] in {"warn", "bad"}:
            attention_items.append(
                dashboard_alert(
                    row["status"],
                    row["title"],
                    f"{row['status_text']} - {row['age']}.",
                    "/status/datakilder",
                )
            )
    missing_light_status = [item["name"] for item in light_status if item["state"] is None]
    if missing_light_status:
        attention_items.append(
            dashboard_alert(
                "warn",
                "Lysstatus",
                f"Mangler sikker status for {len(missing_light_status)} lys.",
                "/lys/hendelser",
            )
        )
    missing_vent_status = [item["name"] for item in vent_status if item["state"] is None]
    if missing_vent_status:
        attention_items.append(
            dashboard_alert(
                "warn",
                "Ventilasjonsstatus",
                f"Mangler sikker status for {len(missing_vent_status)} vifter.",
                "/ventilasjon/hendelser",
            )
        )
    attention_items = attention_items[:6]

    recent_robot_cutoff = local_now_naive() - timedelta(minutes=20)
    active_robots = [
        robot for robot in robots
        if robot.last_seen_at and robot.last_seen_at >= recent_robot_cutoff
    ]
    next_schedule = sorted(schedules, key=roborock_next_schedule_score)[0] if schedules else None
    focus_cards = [
        {
            "title": "Solinger i dag",
            "value": dashboard_compare_value(today_sun.sessions, yesterday_sun.sessions),
            "unit": "stk",
            "detail": f"{dashboard_money_compare(today_sun.paid, yesterday_sun.paid)} - {format_short_number(today_sun.minutes / 60, 1)} t - {today_sun.rooms or 0} rom",
            "href": "/soling/prognose",
            "tone": "sun2",
            "compare": True,
        },
        {
            "title": "Parkering i dag",
            "value": dashboard_compare_value(today_parking.sessions, yesterday_parking.sessions),
            "unit": "stk",
            "detail": f"{dashboard_money_compare(today_parking.paid, yesterday_parking.paid)} - {active_parking or 0} aktive naa",
            "href": f"/parkering/oversikt?day={today.isoformat()}",
            "tone": "parking",
            "compare": True,
        },
        {
            "title": "Sol uke",
            "value": dashboard_compare_value(week_sun.sessions, previous_week_sun.sessions),
            "unit": "sol",
            "href": "/soling/prognose",
            "detail": f"{dashboard_money_compare(week_sun.paid, previous_week_sun.paid)} hittil",
            "tone": "week",
            "compare": True,
        },
        {
            "title": "Parkering uke",
            "value": dashboard_compare_value(week_parking.sessions, previous_week_parking.sessions),
            "unit": "stk",
            "detail": f"{dashboard_money_compare(week_parking.paid, previous_week_parking.paid)} - {active_parking or 0} aktive naa",
            "href": f"/parkering/oversikt?day={today.isoformat()}",
            "tone": "parking",
            "compare": True,
        },
        {
            "title": "Sol hittil mnd",
            "value": dashboard_compare_value(month_sun.sessions, previous_month_sun.sessions),
            "unit": "stk",
            "detail": f"{dashboard_money_compare(month_sun.paid, previous_month_sun.paid)} - {format_short_number(month_sun.minutes / 60, 1)} t - {month_sun.rooms or 0} rom",
            "href": "/soling/prognose",
            "tone": "sun2",
            "compare": True,
        },
        {
            "title": "Parkering hittil mnd",
            "value": dashboard_compare_value(month_parking.sessions, previous_month_parking.sessions),
            "unit": "stk",
            "detail": f"{format_short_number(month_parking.paid)} kr hittil denne måneden",
            "href": f"/parkering/oversikt?day={today.isoformat()}",
            "tone": "parking",
            "compare": True,
        },
        {
            "title": "Sol hittil år",
            "value": format_short_number(year_sun.sessions),
            "unit": "stk",
            "detail": f"{format_short_number(year_sun.paid)} kr - {format_short_number(year_sun.minutes / 60, 1)} t",
            "href": "/soling/prognose",
            "tone": "sun2",
        },
        {
            "title": "Parkering hittil år",
            "value": format_short_number(year_parking.sessions),
            "unit": "stk",
            "detail": f"{format_short_number(year_parking.paid)} kr hittil i år",
            "href": "/parkering/statistikk",
            "tone": "parking",
        },
    ]
    focus_cards[6]["title"] = f"Sol hittil {today.year}"
    focus_cards[7]["title"] = f"Parkering hittil {today.year}"
    focus_cards[0]["value"] = dashboard_compare_value(today_sun.sessions, yesterday_sun.sessions)
    focus_cards[0]["detail"] = f"{dashboard_money_compare(today_sun.paid, yesterday_sun.paid)} - {format_short_number(today_sun.minutes / 60, 1)} t - {today_sun.rooms or 0} rom"
    focus_cards[1]["value"] = dashboard_compare_value(today_parking.sessions, yesterday_parking.sessions)
    focus_cards[1]["detail"] = f"{dashboard_money_compare(today_parking.paid, yesterday_parking.paid)} - {active_parking or 0} aktive naa"
    focus_cards[2]["value"] = dashboard_compare_value(week_sun.sessions, previous_week_sun.sessions)
    focus_cards[2]["detail"] = f"{dashboard_money_compare(week_sun.paid, previous_week_sun.paid)} hittil"
    focus_cards[3]["value"] = dashboard_compare_value(week_parking.sessions, previous_week_parking.sessions)
    focus_cards[3]["detail"] = f"{dashboard_money_compare(week_parking.paid, previous_week_parking.paid)} - {active_parking or 0} aktive naa"
    focus_cards[4]["value"] = dashboard_compare_value(month_sun.sessions, previous_month_sun.sessions)
    focus_cards[4]["detail"] = f"{dashboard_money_compare(month_sun.paid, previous_month_sun.paid)} - {format_short_number(month_sun.minutes / 60, 1)} t - {month_sun.rooms or 0} rom"
    focus_cards[5]["value"] = dashboard_compare_value(month_parking.sessions, previous_month_parking.sessions)
    focus_cards[5]["detail"] = f"{dashboard_money_compare(month_parking.paid, previous_month_parking.paid)} hittil"
    focus_cards[6]["value"] = dashboard_compare_value(year_sun.sessions, previous_year_sun.sessions)
    focus_cards[6]["detail"] = f"{dashboard_money_compare(year_sun.paid, previous_year_sun.paid)} - {format_short_number(year_sun.minutes / 60, 1)} t"
    focus_cards[7]["value"] = dashboard_compare_value(year_parking.sessions, previous_year_parking.sessions)
    focus_cards[7]["detail"] = f"{dashboard_money_compare(year_parking.paid, previous_year_parking.paid)} hittil"
    for card in focus_cards:
        card["compare"] = True
    ops_cards = [
        {
            "title": "Datakilder",
            "value": f"{import_counts['ok']}/{import_counts['total']}",
            "unit": "OK",
            "detail": f"{import_counts['warn']} treg, {import_counts['bad']} feil/gammel",
            "href": "/status/datakilder",
            "tone": "status",
        },
        {
            "title": "Soling i dag",
            "value": format_short_number(today_sun.sessions),
            "unit": "stk",
            "detail": f"{format_short_number(today_sun.minutes / 60, 1)} t - {format_short_number(today_sun.paid)} kr - {today_sun.rooms or 0} rom",
            "href": f"/soling/dagslinje?day={today.isoformat()}",
            "tone": "sun2",
        },
        {
            "title": "Strøm i dag",
            "value": format_short_number(today_energy_fibaro.kwh if today_energy_fibaro.samples else today_energy.kwh, 1),
            "unit": "kWh",
            "detail": (
                f"Nå {format_short_number(latest_energy_sample.inntak_w)} W - {today_energy_fibaro.samples or 0} minuttverdier"
                if latest_energy_sample
                else f"{today_energy.hours or 0} timer importert" + (f" - sist {today_energy.last_at.strftime('%H:%M')}" if today_energy.last_at else "")
            ),
            "href": "/energi/status",
            "tone": "energy",
        },
        {
            "title": "Renhold",
            "value": f"{len(active_robots)}/{len(robots)}",
            "unit": "aktive",
            "detail": f"Neste: {roborock_schedule_text(next_schedule)}" if next_schedule else "Ingen aktiv plan funnet",
            "href": "/renhold/oversikt",
            "tone": "cleaning",
        },
    ]

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "latest_light": latest_light,
            "latest_light_sample": latest_light_sample,
            "latest_vent": ventilation[0] if ventilation else None,
            "latest_sample": latest_sample,
            "latest_yr_sample": latest_yr_sample,
            "now_status": now_status,
            "light_status": light_status,
            "ntfy_lights_subscribe_url": ntfy_subscribe_url(NTFY_LIGHTS_TOPIC, "SUN2 lys"),
            "ntfy_lights_web_url": ntfy_topic_url(NTFY_LIGHTS_TOPIC),
            "ntfy_ventilation_subscribe_url": ntfy_subscribe_url(NTFY_VENTILATION_TOPIC, "SUN2 ventilasjon"),
            "ntfy_ventilation_web_url": ntfy_topic_url(NTFY_VENTILATION_TOPIC),
            "vent_status": vent_status,
            "freshness_items": freshness_items,
            "focus_cards": focus_cards,
            "ops_cards": ops_cards,
            "lux_sparkline": lux_sparkline,
            "attention_items": attention_items,
        },
    )


@app.get("/status/statistikk", response_class=HTMLResponse)
async def status_statistics_view(request: Request):
    async with async_session() as session:
        sun_summaries = await get_sun2_summaries(session)
        parking_summaries = await get_parking_summaries(session)
    combined_stats = combine_business_summaries(sun_summaries, parking_summaries)
    return templates.TemplateResponse(
        request,
        "status_statistics.html",
        {"combined_stats": combined_stats},
    )


@app.get("/status/datakilder", response_class=HTMLResponse)
async def import_status_view(request: Request):
    async with async_session() as session:
        rows = await import_status_rows(session)
        runs = (
            await session.execute(
                select(ImportJobRun)
                .where(ImportJobRun.job_name.in_(list(IMPORT_JOB_DEFINITIONS)))
                .order_by(ImportJobRun.finished_at.desc())
                .limit(80)
            )
        ).scalars().all()
    counts = {
        "ok": sum(1 for row in rows if row["status"] == "ok"),
        "warn": sum(1 for row in rows if row["status"] == "warn"),
        "bad": sum(1 for row in rows if row["status"] == "bad"),
        "total": len(rows),
    }
    return templates.TemplateResponse(
        request,
        "import_status.html",
        {"rows": rows, "runs": runs, "counts": counts},
    )


@app.get("/status/dagslinje", response_class=HTMLResponse)
async def day_view(request: Request, day: Optional[str] = None, zoom: Optional[str] = "all"):
    selected_day = parse_day(day)
    zoom_config, window_start, window_end, ticks = day_zoom_window(selected_day, zoom)
    now_local = local_now_naive()
    is_today = selected_day == now_local.date()
    if is_today:
        if now_local < window_start:
            timeline_end = window_start
        elif now_local > window_end:
            timeline_end = window_end
        else:
            timeline_end = now_local
    else:
        timeline_end = window_end
    now_marker = percent_between(now_local, window_start, window_end) if is_today and window_start <= now_local <= window_end else None
    light_items = await build_light_timeline_group(window_start, window_end, timeline_end)
    vent_items = await build_timeline_group(VentilationEvent, VENT_TIMELINE_DEVICES, "ventilasjon", window_start, window_end, timeline_end)
    return templates.TemplateResponse(
        request,
        "day.html",
        {
            "selected_day": selected_day.isoformat(),
            "prev_day": (selected_day - timedelta(days=1)).isoformat(),
            "next_day": (selected_day + timedelta(days=1)).isoformat(),
            "zoom": zoom_config["key"],
            "zoom_label": zoom_config["label"],
            "zoom_options": DAY_ZOOM_OPTIONS,
            "is_today": is_today,
            "now_marker": now_marker,
            "now_label": now_local.strftime("%H:%M") if is_today else "",
            "light_items": light_items,
            "vent_items": vent_items,
            "ticks": ticks,
        },
    )


@app.get("/lys/dagslogg-lux", response_class=HTMLResponse)
async def day_lux_view(request: Request, day: Optional[str] = None, compare_previous: bool = False):
    selected_day = parse_day(day)
    day_start = datetime.combine(selected_day, time.min)
    day_end = day_start + timedelta(days=1)
    previous_day_start = day_start - timedelta(days=1)
    previous_day_end = day_start
    now_local = local_now_naive()
    is_today = selected_day == now_local.date()
    timeline_end = min(now_local, day_end) if is_today else day_end
    now_marker = percent_between(now_local, day_start, day_end) if is_today else None
    previous_lux_day = None
    if compare_previous:
        _, current_values = await fetch_lux_samples(day_start, timeline_end)
        _, previous_values = await fetch_lux_samples(previous_day_start, previous_day_end)
        lux_values = current_values + previous_values
        lux_day = await build_lux_day(day_start, day_end, timeline_end, lux_values)
        previous_lux_day = await build_lux_day(previous_day_start, previous_day_end, previous_day_end, lux_values)
    else:
        lux_day = await build_lux_day(day_start, day_end, timeline_end)
    light_chart = await build_light_chart_markers(day_start, day_end, timeline_end)
    compare_query = "&compare_previous=1" if compare_previous else ""
    return templates.TemplateResponse(
        request,
        "day_lux.html",
        {
            "selected_day": selected_day.isoformat(),
            "prev_day": (selected_day - timedelta(days=1)).isoformat(),
            "next_day": (selected_day + timedelta(days=1)).isoformat(),
            "compare_previous": compare_previous,
            "compare_query": compare_query,
            "previous_day_label": (selected_day - timedelta(days=1)).strftime("%d.%m.%Y"),
            "is_today": is_today,
            "now_marker": now_marker,
            "now_label": now_local.strftime("%H:%M") if is_today else "",
            "lux_day": lux_day,
            "light_chart": light_chart,
            "previous_lux_day": previous_lux_day,
            "ticks": [
                {"label": "00", "x": 0},
                {"label": "06", "x": 250},
                {"label": "12", "x": 500},
                {"label": "18", "x": 750},
                {"label": "24", "x": 1000},
            ],
        },
    )


@app.get("/ventilasjon/dagslogg-temp", response_class=HTMLResponse)
async def day_temp_view(request: Request, day: Optional[str] = None):
    selected_day = parse_day(day)
    day_start = datetime.combine(selected_day, time.min)
    day_end = day_start + timedelta(days=1)
    now_local = local_now_naive()
    is_today = selected_day == now_local.date()
    timeline_end = min(now_local, day_end) if is_today else day_end
    now_marker = percent_between(now_local, day_start, day_end) if is_today else None
    temp_day = await build_temp_day(day_start, day_end, timeline_end)
    return templates.TemplateResponse(
        request,
        "day_temp.html",
        {
            "selected_day": selected_day.isoformat(),
            "prev_day": (selected_day - timedelta(days=1)).isoformat(),
            "next_day": (selected_day + timedelta(days=1)).isoformat(),
            "is_today": is_today,
            "now_marker": now_marker,
            "now_label": now_local.strftime("%H:%M") if is_today else "",
            "temp_day": temp_day,
            "ticks": [
                {"label": "00", "x": 0},
                {"label": "06", "x": 250},
                {"label": "12", "x": 500},
                {"label": "18", "x": 750},
                {"label": "24", "x": 1000},
            ],
        },
    )


@app.post("/log")
async def legacy_log_data(data: LegacyLogIn):
    record = GenericEvent(
        timestamp=data.timestamp,
        system="legacy",
        event_type="legacy_log",
        source=data.source,
        value=data.temperature,
        extra={"temperature": data.temperature, "humidity": data.humidity},
    )
    event_id = await save_record(record)
    return {"status": "ok", "id": event_id, "table": "event_data"}


@app.post("/api/hc3/measurements/log")
async def hc3_meter_reading_log(data: Hc3MeterReadingIn):
    timestamp = normalize_local_naive(data.ts) or local_now_naive()
    reading = Hc3MeterReading(
        timestamp=timestamp,
        kilde=data.kilde,
        status=data.status,
        fibaroid=data.fibaroid,
        verdi1=data.verdi1,
        verdi2=data.verdi2,
        forklaring=data.forklaring,
        source=data.source or "HC3",
        raw=json_safe_model_payload(data),
    )
    async with async_session() as session:
        session.add(reading)
        await session.flush()
        kjeller_sample_id = await upsert_kjeller_measurement_sample(
            session,
            timestamp,
            data.fibaroid,
            data.verdi1,
            data.source or "HC3",
        )
        await record_import_job(
            session,
            "hc3_meter_readings",
            source=data.source or "HC3",
            records_imported=1,
            records_total=1,
            message=f"{data.status} {data.kilde} {data.verdi1:g}",
            raw={
                "id": reading.id,
                "fibaroid": data.fibaroid,
                "kilde": data.kilde,
                "status": data.status,
                "kjeller_sample_id": kjeller_sample_id,
            },
        )
        await session.commit()
        return {"status": "ok", "id": reading.id, "table": "hc3_meter_readings", "kjeller_sample_id": kjeller_sample_id}


@app.post("/events")
async def log_event(data: EventDataIn):
    system = (data.system or "").lower()
    if system in {"utelys", "ute_lys", "lys"}:
        if data.event_type in {"sample", "sample_5min", "learning_sample"}:
            met_weather = None
            if not payload_weather_symbol(data) and not payload_weather_text(data):
                met_weather = await met_weather_cached()
            yr_sample_id = await save_yr_sample_for_payload(data, met_weather)
            event_id = await save_record(light_sample_from_payload(data, met_weather))
            async with async_session() as session:
                await record_import_job(
                    session,
                    "hc3_light_5min",
                    source=data.source or "HC3",
                    records_imported=1,
                    records_total=1,
                    message=f"Lux {data.lux:.0f}" if data.lux is not None else "5-minutters sample mottatt",
                    raw={"event_id": event_id, "yr_sample_id": yr_sample_id},
                )
                if yr_sample_id:
                    await record_import_job(
                        session,
                        "yr_weather_refresh",
                        source="MET/Yr",
                        records_imported=1,
                        records_total=1,
                        message="Yr-data lagret sammen med luxsample",
                        raw={"yr_sample_id": yr_sample_id},
                    )
                await session.commit()
            return {"status": "ok", "id": event_id, "table": "utelys_samples", "yr_sample_id": yr_sample_id}
        event = light_from_payload(data)
        event_id = await save_record(event)
        ntfy_sent = await publish_light_ntfy(event)
        return {"status": "ok", "id": event_id, "table": "utelys_events", "ntfy_sent": ntfy_sent}
    if system in {"ventilasjon", "ventilation", "vent"}:
        if data.event_type in {"sample", "sample_5min", "sample_15min", "learning_sample"}:
            yr_sample_id = await save_yr_sample_for_payload(data)
            event_id = await save_record(vent_sample_from_payload(data))
            async with async_session() as session:
                await record_import_job(
                    session,
                    "hc3_ventilation_5min",
                    source=data.source or "HC3",
                    records_imported=1,
                    records_total=1,
                    message=f"Modus {data.mode}" if data.mode else "5-minutters sample mottatt",
                    raw={"event_id": event_id, "yr_sample_id": yr_sample_id},
                )
                if yr_sample_id:
                    await record_import_job(
                        session,
                        "yr_weather_refresh",
                        source="MET/Yr",
                        records_imported=1,
                        records_total=1,
                        message="Yr-data lagret sammen med ventilasjonssample",
                        raw={"yr_sample_id": yr_sample_id},
                    )
                await session.commit()
            return {"status": "ok", "id": event_id, "table": "ventilasjon_samples", "yr_sample_id": yr_sample_id}
        event = vent_from_payload(data)
        event_id = await save_record(event)
        ntfy_sent = await publish_ventilation_ntfy(event)
        return {"status": "ok", "id": event_id, "table": "ventilasjon_events", "ntfy_sent": ntfy_sent}
    event_id = await save_record(generic_from_payload(data))
    return {"status": "ok", "id": event_id, "table": "event_data"}


@app.post("/api/import-status/report")
async def import_status_report(data: ImportStatusReportIn):
    definition = import_job_definition(data.job_name)
    ok = data.ok if data.ok is not None else (data.status not in {"bad", "failed", "error"})
    finished_at = data.finished_at or local_now_naive()
    async with async_session() as session:
        row = await record_import_job(
            session,
            data.job_name,
            ok=bool(ok),
            title=data.title or definition["title"],
            category=data.category or definition["category"],
            source=data.source or definition.get("source"),
            started_at=data.started_at,
            finished_at=finished_at,
            next_expected_at=data.next_expected_at,
            expected_interval_minutes=data.expected_interval_minutes,
            warning_after_minutes=data.warning_after_minutes,
            records_imported=data.records_imported,
            records_total=data.records_total,
            duration_seconds=data.duration_seconds,
            message=data.message,
            raw=data.raw,
        )
        await session.commit()
        await session.refresh(row)
    return {"status": "ok", "job_name": row.job_name, "job_status": row.status, "last_success_at": row.last_success_at}


@app.get("/api/import-status/json")
async def import_status_json():
    async with async_session() as session:
        rows = await import_status_rows(session)
    return {"rows": rows}


@app.post("/api/renhold/ingest")
async def roborock_ingest(data: RoborockIngestIn):
    batch_time = data.timestamp or datetime.utcnow()
    results = []
    async with async_session() as session:
        session.add(
            RoborockSyncRun(
                timestamp=batch_time,
                collector_id=data.collector_id,
                source=data.source,
                ok=data.ok,
                robots_count=len(data.robots),
                message=data.message,
                raw={"extra": data.extra},
            )
        )
        for robot in data.robots:
            results.append(await ingest_roborock_robot(session, robot, batch_time, data.source))
        await record_import_job(
            session,
            "roborock_sync",
            ok=data.ok,
            source=data.source,
            records_imported=len(data.robots),
            records_total=len(data.robots),
            message=data.message or f"{len(data.robots)} roboter synkronisert",
            raw={"collector_id": data.collector_id, "extra": data.extra},
        )
        await session.commit()
    return {"status": "ok", "robots": results}


@app.post("/api/sun2/room-stats/ingest")
async def sun2_room_stats_ingest(data: Sun2RoomStatsIngestIn):
    batch_time = data.timestamp or datetime.utcnow()
    async with async_session() as session:
        counts = await ingest_sun2_room_stats(session, data, batch_time)
        session.add(
            Sun2ImportRun(
                timestamp=batch_time,
                collector_id=data.collector_id,
                source=data.source,
                ok=data.ok,
                stat_date=data.stat_date,
                source_file=data.source_file,
                rows_count=len(data.rows),
                inserted_count=counts["inserted"],
                updated_count=counts["updated"],
                message=data.message,
                raw={"extra": data.extra},
            )
        )
        await record_import_job(
            session,
            "sun2_room_daily_import",
            ok=data.ok,
            source=data.source,
            records_imported=counts["inserted"] + counts["updated"],
            records_total=len(data.rows),
            message=data.message or f"{len(data.rows)} romrader for {data.stat_date or '-'}",
            raw={"collector_id": data.collector_id, "source_file": data.source_file, "counts": counts},
        )
        await session.commit()
    clear_summary_cache("sun2")
    return {"status": "ok", **counts, "rows": len(data.rows)}


@app.post("/api/sun2/sessions/ingest")
async def sun2_sessions_ingest(data: Sun2TanningSessionsIngestIn):
    batch_time = data.timestamp or datetime.utcnow()
    period_first = min((row.started_at for row in data.rows if row.started_at), default=None)
    period_last = max((row.started_at for row in data.rows if row.started_at), default=None)
    async with async_session() as session:
        counts = await ingest_sun2_tanning_sessions(session, data, batch_time)
        session.add(
            Sun2SessionImportRun(
                timestamp=batch_time,
                collector_id=data.collector_id,
                source=data.source,
                ok=data.ok,
                source_file=data.source_file,
                period_first=period_first,
                period_last=period_last,
                rows_count=len(data.rows),
                inserted_count=counts["inserted"],
                updated_count=counts["updated"],
                skipped_count=counts["skipped"],
                message=data.message,
                raw={"extra": data.extra},
            )
        )
        await record_import_job(
            session,
            "sun2_sessions_import",
            ok=data.ok,
            source=data.source,
            records_imported=counts["inserted"] + counts["updated"],
            records_total=len(data.rows),
            message=data.message or f"{len(data.rows)} enkelttimer mottatt",
            raw={"collector_id": data.collector_id, "source_file": data.source_file, "counts": counts},
        )
        await session.commit()
    clear_summary_cache("sun2", "sun2_sessions", "sun2_session_options", "sun2_session_database_total")
    return {"status": "ok", **counts, "rows": len(data.rows)}


@app.post("/api/sun2/beds/ingest")
async def sun2_beds_ingest(data: Sun2BedsIngestIn):
    batch_time = data.timestamp or datetime.utcnow()
    async with async_session() as session:
        counts = await ingest_sun2_beds(session, data, batch_time)
        await record_import_job(
            session,
            "sun2_beds_import",
            ok=data.ok,
            source=data.source,
            records_imported=counts["inserted"] + counts["updated"],
            records_total=len(data.beds),
            message=data.message or f"{len(data.beds)} senger mottatt",
            raw={"collector_id": data.collector_id, "counts": counts},
        )
        await session.commit()
    clear_summary_cache("sun2_session_options")
    return {"status": "ok", **counts, "beds": len(data.beds)}


@app.post("/api/sun2/members/ingest")
async def sun2_members_ingest(data: Sun2MembersIngestIn):
    batch_time = data.timestamp or datetime.utcnow()
    async with async_session() as session:
        counts = await ingest_sun2_members(session, data, batch_time)
        await record_import_job(
            session,
            "sun2_members_import",
            ok=data.ok,
            source=data.source,
            records_imported=counts["inserted"] + counts["updated"],
            records_total=len(data.members),
            message=data.message or f"{len(data.members)} medlemmer mottatt",
            raw={"collector_id": data.collector_id, "counts": counts},
        )
        await session.commit()
    clear_summary_cache("sun2_members")
    return {"status": "ok", **counts, "members": len(data.members)}


@app.post("/api/sun2/backfill-room-identity")
async def sun2_backfill_room_identity():
    async with async_session() as session:
        counts = await backfill_sun2_room_identity(session)
        await session.commit()
    clear_summary_cache("sun2", "sun2_sessions", "sun2_session_options", "sun2_session_database_total")
    return {"status": "ok", **counts}


@app.get("/sun2/room-stats")
async def sun2_room_stats_legacy_redirect(request: Request):
    return redirect_keep_query(request, "/soling/detaljer", status_code=307)


@app.get("/sun2/room-stats/json")
async def sun2_room_stats_json_legacy_redirect(request: Request):
    return redirect_keep_query(request, "/api/sun2/room-stats/json", status_code=307)


@app.get("/parkering")
async def parking_redirect(request: Request):
    return redirect_keep_query(request, "/parkering/oversikt", status_code=307)


def normalize_plate(value: Optional[str]) -> str:
    return re.sub(r"\s+", "", (value or "").strip().upper())


EASYPARK_REQUIRED_COLUMNS = {
    "Parking area",
    "Source parking system",
    "Area number",
    "Parking ID",
    "Start date",
}


def decode_easypark_csv(content: bytes) -> str:
    if not content:
        return ""
    if content.startswith(b"\xff\xfe") or content.startswith(b"\xfe\xff"):
        return content.decode("utf-16", errors="replace")
    if len(content) > 2 and content[1] == 0:
        return content.decode("utf-16le", errors="replace")
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def clean_easypark_value(value: Any) -> str:
    return str(value or "").replace("\x00", "").strip().strip('"').strip()


def easypark_float(value: Any) -> Optional[float]:
    text_value = clean_easypark_value(value).replace("\xa0", " ").replace(" ", "")
    if not text_value:
        return None
    text_value = text_value.replace(",", ".")
    try:
        return float(text_value)
    except ValueError:
        return None


def easypark_int(value: Any) -> Optional[int]:
    number = easypark_float(value)
    if number is None:
        text_value = re.sub(r"\D+", "", clean_easypark_value(value))
        return int(text_value) if text_value else None
    return int(number)


def easypark_timestamp(value: Any) -> Optional[datetime]:
    text_value = clean_easypark_value(value)
    if not text_value:
        return None
    parsed = dtparser.parse(text_value)
    if parsed.tzinfo is not None:
        return parsed.astimezone(LOCAL_TZ).replace(tzinfo=None)
    return parsed.replace(tzinfo=None)


def easypark_minutes(value: Any, start_at: Optional[datetime], end_at: Optional[datetime]) -> Optional[float]:
    explicit = easypark_float(value)
    if explicit is not None:
        return explicit
    if start_at and end_at:
        return round((end_at - start_at).total_seconds() / 60, 2)
    return None


def parse_easypark_csv(content: bytes, filename: str) -> Dict[str, Any]:
    text_value = decode_easypark_csv(content)
    sample = text_value[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
    except csv.Error:
        dialect = csv.excel()
        dialect.delimiter = ";"
    reader = csv.DictReader(StringIO(text_value), dialect=dialect)
    fieldnames = [clean_easypark_value(name) for name in (reader.fieldnames or [])]
    missing = sorted(EASYPARK_REQUIRED_COLUMNS - set(fieldnames))
    if missing:
        raise ValueError(f"EasyPark-filen mangler kolonner: {', '.join(missing)}")

    rows: list[Dict[str, Any]] = []
    skipped = 0
    for raw_row in reader:
        row = {clean_easypark_value(key): clean_easypark_value(value) for key, value in raw_row.items() if key is not None}
        parking_id = easypark_int(row.get("Parking ID"))
        area_number = easypark_int(row.get("Area number"))
        start_at = easypark_timestamp(row.get("Start date"))
        if not parking_id or not area_number or not start_at:
            skipped += 1
            continue
        end_at = easypark_timestamp(row.get("End date"))
        rows.append(
            {
                "parking_area": row.get("Parking area") or "",
                "source_system": row.get("Source parking system") or "EasyPark",
                "area_number": area_number,
                "parking_id": parking_id,
                "start_time": start_at,
                "end_time": end_at,
                "parking_time_min": easypark_minutes(row.get("Parking time"), start_at, end_at),
                "fee_ex_vat": easypark_float(row.get("Parking fee excluding VAT")),
                "fee_inc_vat": easypark_float(row.get("Parking fee including VAT")),
                "fee_vat": easypark_float(row.get("Parking fee VAT")),
                "car_license_number": normalize_plate(row.get("Car license number")) or None,
                "user_interface": row.get("User interface") or None,
                "subtype": row.get("SubType") or None,
                "status": row.get("Status") or "Ukjent",
                "imported_at": datetime.utcnow(),
                "raw_filename": filename,
            }
        )
    return {"rows": rows, "skipped": skipped, "filename": filename}


async def ingest_easypark_csv(session, content: bytes, filename: str) -> Dict[str, Any]:
    parsed = parse_easypark_csv(content, filename)
    rows = parsed["rows"]
    if not rows:
        return {"total": 0, "inserted": 0, "updated": 0, "unchanged": 0, "skipped": parsed["skipped"], "first_at": None, "last_at": None}

    inserted_count = 0
    updated_count = 0
    for start in range(0, len(rows), 1000):
        chunk = rows[start:start + 1000]
        keys = [(row["source_system"], row["parking_id"]) for row in chunk]
        existing_keys = {
            tuple(row)
            for row in (
                await session.execute(
                    select(ParkingSession.source_system, ParkingSession.parking_id).where(
                        tuple_(ParkingSession.source_system, ParkingSession.parking_id).in_(keys)
                    )
                )
            ).all()
        }
        insert_stmt = pg_insert(ParkingSession).values(chunk)
        excluded = insert_stmt.excluded
        update_where = or_(
            ParkingSession.end_time.is_(None),
            func.lower(func.coalesce(ParkingSession.status, "")).in_(["ongoing", "active", "started"]),
            ParkingSession.parking_area.is_distinct_from(excluded.parking_area),
            ParkingSession.area_number.is_distinct_from(excluded.area_number),
            ParkingSession.start_time.is_distinct_from(excluded.start_time),
            ParkingSession.end_time.is_distinct_from(excluded.end_time),
            ParkingSession.parking_time_min.is_distinct_from(excluded.parking_time_min),
            ParkingSession.fee_ex_vat.is_distinct_from(excluded.fee_ex_vat),
            ParkingSession.fee_inc_vat.is_distinct_from(excluded.fee_inc_vat),
            ParkingSession.fee_vat.is_distinct_from(excluded.fee_vat),
            ParkingSession.car_license_number.is_distinct_from(excluded.car_license_number),
            ParkingSession.user_interface.is_distinct_from(excluded.user_interface),
            ParkingSession.subtype.is_distinct_from(excluded.subtype),
            ParkingSession.status.is_distinct_from(excluded.status),
        )
        stmt = (
            insert_stmt
            .on_conflict_do_update(
                index_elements=["source_system", "parking_id"],
                set_={
                    "parking_area": excluded.parking_area,
                    "area_number": excluded.area_number,
                    "start_time": excluded.start_time,
                    "end_time": excluded.end_time,
                    "parking_time_min": excluded.parking_time_min,
                    "fee_ex_vat": excluded.fee_ex_vat,
                    "fee_inc_vat": excluded.fee_inc_vat,
                    "fee_vat": excluded.fee_vat,
                    "car_license_number": excluded.car_license_number,
                    "user_interface": excluded.user_interface,
                    "subtype": excluded.subtype,
                    "status": excluded.status,
                    "imported_at": excluded.imported_at,
                    "raw_filename": excluded.raw_filename,
                },
                where=update_where,
            )
            .returning(ParkingSession.source_system, ParkingSession.parking_id)
        )
        affected_keys = {tuple(row) for row in (await session.execute(stmt)).all()}
        inserted_count += len(affected_keys - existing_keys)
        updated_count += len(affected_keys & existing_keys)
    first_at = min(row["start_time"] for row in rows)
    last_at = max(row["start_time"] for row in rows)
    return {
        "total": len(rows),
        "inserted": inserted_count,
        "updated": updated_count,
        "unchanged": len(rows) - inserted_count - updated_count,
        "skipped": parsed["skipped"],
        "first_at": first_at,
        "last_at": last_at,
    }


async def refresh_parking_vehicle_summary(session) -> int:
    result = await session.execute(
        sql_text(
            """
            INSERT INTO kjoretoy (plate, first_seen, last_seen, parkering_count, paid_total, updated_at)
            SELECT
                upper(regexp_replace(car_license_number, '\\s+', '', 'g')) AS plate,
                min(start_time) AS first_seen,
                max(start_time) AS last_seen,
                count(*) AS parkering_count,
                round(sum(coalesce(fee_inc_vat, 0))::numeric, 2)::float AS paid_total,
                now() AS updated_at
            FROM parkering
            WHERE car_license_number IS NOT NULL AND btrim(car_license_number) <> ''
            GROUP BY 1
            ON CONFLICT (plate) DO UPDATE SET
                first_seen = coalesce(least(kjoretoy.first_seen, EXCLUDED.first_seen), kjoretoy.first_seen, EXCLUDED.first_seen),
                last_seen = coalesce(greatest(kjoretoy.last_seen, EXCLUDED.last_seen), kjoretoy.last_seen, EXCLUDED.last_seen),
                parkering_count = EXCLUDED.parkering_count,
                paid_total = EXCLUDED.paid_total,
                updated_at = now()
            RETURNING plate
            """
        )
    )
    return len(result.fetchall())


def import_counts_for_json(counts: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: (value.isoformat() if isinstance(value, datetime) else value)
        for key, value in counts.items()
    }


def compact_plate(value: Optional[str]) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value or "").upper()


def first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def data_path(data: Any, *path: Any) -> Any:
    current = data
    for key in path:
        if current is None:
            return None
        if isinstance(key, int):
            if not isinstance(current, list) or len(current) <= key:
                return None
            current = current[key]
        elif isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def code_text(value: Any) -> Any:
    if isinstance(value, dict):
        return first_value(value.get("kodeNavn"), value.get("kodeBeskrivelse"), value.get("kodeVerdi"))
    return value


def parse_int_value(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return None


def parse_float_value(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def parse_date_value(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def first_vehicle_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    vehicles = raw.get("kjoretoydataListe")
    if isinstance(vehicles, list) and vehicles:
        return vehicles[0] if isinstance(vehicles[0], dict) else {}
    return raw if isinstance(raw, dict) else {}


def svv_detail_values(plate: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    vehicle = first_vehicle_data(raw)
    tech = data_path(vehicle, "godkjenning", "tekniskGodkjenning")
    data = data_path(tech, "tekniskeData") or {}
    generelt = data_path(data, "generelt") or {}
    klassifisering = data_path(tech, "kjoretoyklassifisering") or {}
    weights = data_path(data, "vekter") or {}
    dimensions = data_path(data, "dimensjoner") or {}
    personer = data_path(data, "persontall") or {}
    miljodata = data_path(data, "miljodata") or {}
    motor = data_path(data, "motorOgDrivverk", "motor") or []
    motor0 = motor[0] if isinstance(motor, list) and motor else {}
    color = first_value(
        code_text(data_path(data, "karosseriOgLasteplan", "rFarge", 0)),
        code_text(data_path(data, "karosseriOgLasteplan", "farge", 0)),
    )
    return {
        "plate": compact_plate(plate),
        "vin": data_path(vehicle, "kjoretoyId", "understellsnummer"),
        "merke": first_value(
            data_path(generelt, "merke", 0, "merke"),
            data_path(generelt, "merke", 0, "merkeNavn"),
            data_path(generelt, "merke", 0),
        ),
        "modell": first_value(
            data_path(generelt, "handelsbetegnelse", 0),
            data_path(generelt, "modell"),
        ),
        "typebetegnelse": data_path(generelt, "typebetegnelse"),
        "kjoretoyklasse_kode": data_path(klassifisering, "tekniskKode", "kodeVerdi"),
        "kjoretoyklasse_navn": code_text(data_path(klassifisering, "tekniskKode")),
        "registreringsstatus_kode": data_path(vehicle, "registrering", "registreringsstatus", "kodeVerdi"),
        "registreringsstatus_tekst": code_text(data_path(vehicle, "registrering", "registreringsstatus")),
        "forstegangsregistrert_norge": parse_date_value(data_path(vehicle, "forstegangsregistrering", "registrertForstegangNorgeDato")),
        "pkk_kontrollfrist": parse_date_value(data_path(vehicle, "periodiskKjoretoyKontroll", "kontrollfrist")),
        "egenvekt_kg": parse_int_value(first_value(data_path(weights, "egenvekt"), data_path(weights, "egenvektMinimum"))),
        "nyttelast_kg": parse_int_value(data_path(weights, "nyttelast")),
        "tillatt_totalvekt_kg": parse_int_value(data_path(weights, "tillattTotalvekt")),
        "tillatt_vogntogvekt_kg": parse_int_value(data_path(weights, "tillattVogntogvekt")),
        "tillatt_tilhengervekt_med_brems_kg": parse_int_value(data_path(weights, "tillattTilhengervektMedBrems")),
        "tillatt_tilhengervekt_uten_brems_kg": parse_int_value(data_path(weights, "tillattTilhengervektUtenBrems")),
        "seter_totalt": parse_int_value(first_value(data_path(personer, "sitteplasserTotalt"), data_path(personer, "sitteplasserForan"))),
        "lengde_mm": parse_int_value(data_path(dimensions, "lengde")),
        "bredde_mm": parse_int_value(data_path(dimensions, "bredde")),
        "hoyde_mm": parse_int_value(data_path(dimensions, "hoyde")),
        "rekkevidde_wltp_km": parse_int_value(data_path(miljodata, "wltpKjoretoyspesifikk", "rekkeviddeKm")),
        "elforbruk_wltp_wh_km": parse_int_value(data_path(miljodata, "wltpKjoretoyspesifikk", "elforbrukWhPerKm")),
        "motoreffekt_samlet_kw": parse_float_value(data_path(motor0, "drivstoff", 0, "maksEffektPrTime")),
        "motoreffekt_kontinuerlig_kw": parse_float_value(data_path(motor0, "drivstoff", 0, "maksNettoEffekt")),
        "maks_hastighet_kmt": parse_int_value(data_path(data, "maksimumHastighet", "hastighet")),
        "stoy_db": parse_int_value(data_path(data, "miljodata", "stoy", "standstoy")),
        "abs": data_path(data, "bremser", "abs"),
        "farge": color,
        "svv_godkjennings_id": first_value(
            data_path(tech, "godkjenningsId"),
            data_path(vehicle, "godkjenning", "forstegangsGodkjenning", "godkjenningsId"),
        ),
        "svv_teknisk_gyldig_fra": parse_date_value(first_value(data_path(tech, "gyldigFraDato"), data_path(tech, "gyldigFraDatoTid"))),
        "sist_synkronisert": datetime.utcnow(),
    }


def svv_api_lookup_sync(plate: str) -> Dict[str, Any]:
    if not SVV_API_KEY:
        raise RuntimeError("SVV_API_KEY mangler.")
    params = urlencode({"kjennemerke": compact_plate(plate)})
    url = f"{SVV_API_URL}?{params}"
    auth_value = " ".join(part for part in [SVV_API_AUTH_PREFIX, SVV_API_KEY] if part).strip()
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            SVV_API_AUTH_HEADER: auth_value,
            "User-Agent": "fibaro10/1.0",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        status_code = response.getcode()
        payload = response.read().decode("utf-8", errors="replace")
    if status_code == 204 or not payload.strip():
        raise LookupError("Ingen kjøretøydata fra SVV")
    return json.loads(payload)


async def svv_candidate_plates(session, limit: int) -> list[str]:
    retry_before = datetime.utcnow() - timedelta(hours=SVV_RETRY_AFTER_HOURS)
    transient_retry_before = datetime.utcnow() - timedelta(minutes=SVV_TRANSIENT_RETRY_AFTER_MINUTES)
    permanent_no_data = list(SVV_PERMANENT_NO_DATA_STATUSES)
    transient_statuses = list(SVV_TRANSIENT_STATUSES)
    rows = (
        await session.execute(
            select(ParkingVehicle.plate)
            .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
            .where(ParkingVehicle.plate.isnot(None))
            .where(ParkingVehicle.plate != "")
            .where(
                or_(
                    ParkingVehicle.svv_status.is_(None),
                    ParkingVehicle.svv_fetched_at.is_(None),
                    and_(
                        ParkingVehicleDetails.plate.is_(None),
                        ParkingVehicle.svv_status.notin_(permanent_no_data),
                        ParkingVehicle.svv_status.notin_(transient_statuses),
                    ),
                    and_(
                        ParkingVehicle.svv_status.notin_([200, *permanent_no_data]),
                        ParkingVehicle.svv_status.notin_(transient_statuses),
                        ParkingVehicle.svv_fetched_at < retry_before,
                    ),
                    and_(
                        ParkingVehicle.svv_status.in_(transient_statuses),
                        ParkingVehicle.svv_fetched_at < transient_retry_before,
                    ),
                )
            )
            .order_by(
                case((ParkingVehicleDetails.plate.is_(None), 0), else_=1),
                ParkingVehicle.svv_fetched_at.asc().nullsfirst(),
                ParkingVehicle.last_seen.desc().nullslast(),
            )
            .limit(limit)
        )
    ).scalars().all()
    return [plate for plate in rows if compact_plate(plate)]


async def upsert_vehicle_svv_data(session, plate: str, raw: Dict[str, Any], status_code: int = 200, error: Optional[str] = None) -> bool:
    plate_value = compact_plate(plate)
    vehicle = (await session.execute(select(ParkingVehicle).where(ParkingVehicle.plate == plate_value))).scalars().first()
    if not vehicle:
        return False
    now = datetime.utcnow()
    vehicle.svv_fetched_at = now
    vehicle.svv_status = status_code
    vehicle.svv_error = error
    vehicle.svv_data = raw if raw else None
    vehicle.updated_at = now
    if status_code != 200 or not raw:
        return False
    values = svv_detail_values(plate_value, raw)
    detail = (await session.execute(select(ParkingVehicleDetails).where(ParkingVehicleDetails.plate == plate_value))).scalars().first()
    if not detail:
        detail = ParkingVehicleDetails(plate=plate_value)
        session.add(detail)
    for key, value in values.items():
        setattr(detail, key, value)
    return True


async def run_vehicle_svv_sync(limit: int = SVV_SYNC_BATCH_SIZE, source: str = "background") -> Dict[str, Any]:
    started_at = local_now_naive()
    if not SVV_API_KEY:
        async with async_session() as session:
            await record_import_job(
                session,
                "parking_vehicle_svv_sync",
                ok=False,
                source=source,
                started_at=started_at,
                records_imported=0,
                records_total=0,
                message="SVV_API_KEY mangler.",
            )
            await session.commit()
        return {"ok": False, "processed": 0, "updated": 0, "failed": 0, "message": "SVV_API_KEY mangler."}
    processed = updated = no_data = failed = 0
    errors: list[str] = []
    async with async_session() as session:
        plates = await svv_candidate_plates(session, limit)
        if not plates:
            transient_retry_before = datetime.utcnow() - timedelta(minutes=SVV_TRANSIENT_RETRY_AFTER_MINUTES)
            transient_waiting = (
                await session.execute(
                    select(func.count())
                    .select_from(ParkingVehicle)
                    .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                    .where(ParkingVehicleDetails.plate.is_(None))
                    .where(ParkingVehicle.svv_status.in_(list(SVV_TRANSIENT_STATUSES)))
                    .where(ParkingVehicle.svv_fetched_at >= transient_retry_before)
                )
            ).scalar_one()
            if transient_waiting:
                message = f"SVV svarte midlertidig feil sist. {transient_waiting} kj\u00f8ret\u00f8y venter p\u00e5 ny pr\u00f8ve."
                await record_import_job(
                    session,
                    "parking_vehicle_svv_sync",
                    ok=False,
                    source=source,
                    started_at=started_at,
                    records_imported=0,
                    records_total=transient_waiting,
                    message=message,
                    raw={"transient_waiting": transient_waiting},
                )
                await session.commit()
                return {"ok": False, "processed": 0, "updated": 0, "no_data": 0, "failed": transient_waiting, "errors": [message]}
        for plate in plates:
            processed += 1
            try:
                raw = await asyncio.to_thread(svv_api_lookup_sync, plate)
                if await upsert_vehicle_svv_data(session, plate, raw, 200, None):
                    updated += 1
            except LookupError as exc:
                no_data += 1
                message = str(exc)[:240] or "Ingen kjøretøydata fra SVV"
                await upsert_vehicle_svv_data(session, plate, {}, 204, message)
            except urllib.error.HTTPError as exc:
                message = "Ikke funnet eller ugyldig kjennemerke hos SVV" if exc.code in SVV_PERMANENT_NO_DATA_STATUSES else f"HTTP {exc.code}"
                if exc.code not in SVV_PERMANENT_NO_DATA_STATUSES:
                    body = exc.read().decode("utf-8", errors="replace").strip()[:160]
                    if body:
                        message = f"{message}: {body}"
                if exc.code in SVV_PERMANENT_NO_DATA_STATUSES:
                    no_data += 1
                else:
                    failed += 1
                    errors.append(f"{plate}: {message}")
                await upsert_vehicle_svv_data(session, plate, {}, exc.code, message)
                if exc.code in SVV_TRANSIENT_STATUSES:
                    await session.commit()
                    break
            except json.JSONDecodeError:
                no_data += 1
                message = "Tomt eller uleselig svar fra SVV"
                await upsert_vehicle_svv_data(session, plate, {}, 204, message)
            except Exception as exc:
                failed += 1
                message = str(exc)[:240]
                errors.append(f"{plate}: {message}")
                await upsert_vehicle_svv_data(session, plate, {}, 0, message)
            await session.commit()
        job_ok = failed == 0
        await record_import_job(
            session,
            "parking_vehicle_svv_sync",
            ok=job_ok,
            source=source,
            started_at=started_at,
            records_imported=updated,
            records_total=processed,
            message=f"{updated} oppdatert, {no_data} uten treff, {failed} feilet, {processed} behandlet.",
            raw={"errors": errors[:20], "no_data": no_data},
        )
        await session.commit()
    return {"ok": failed == 0, "processed": processed, "updated": updated, "no_data": no_data, "failed": failed, "errors": errors[:20]}


async def parking_vehicle_svv_worker() -> None:
    await asyncio.sleep(30)
    while True:
        try:
            await run_vehicle_svv_sync(SVV_SYNC_BATCH_SIZE, "SVV bakgrunn")
        except Exception:
            pass
        await asyncio.sleep(SVV_SYNC_INTERVAL_MINUTES * 60)


@app.post("/api/parkering/import-csv")
async def parking_easypark_import_csv(request: Request):
    started_at = local_now_naive()
    filename = "easypark.csv"
    try:
        form = await request.form()
        upload = form.get("file")
        if not upload or not hasattr(upload, "read"):
            raise ValueError("Velg en CSV-fil fra EasyPark.")
        filename = getattr(upload, "filename", None) or filename
        content = await upload.read()
        if not content:
            raise ValueError("Filen er tom.")
        async with async_session() as session:
            counts = await ingest_easypark_csv(session, content, filename)
            vehicle_count = await refresh_parking_vehicle_summary(session)
            message = (
                f"{counts['inserted']} nye, {counts['updated']} oppdatert, {counts['unchanged']} uendret, "
                f"{counts['skipped']} hoppet over fra {filename}"
            )
            await record_import_job(
                session,
                "easypark_parking_import",
                ok=True,
                source="EasyPark CSV",
                started_at=started_at,
                records_imported=counts["inserted"] + counts["updated"],
                records_total=counts["total"],
                message=message,
                raw={
                    "filename": filename,
                    "counts": import_counts_for_json(counts),
                    "vehicles_refreshed": vehicle_count,
                },
            )
            await session.commit()
        clear_summary_cache("parking")
        if SVV_IMPORT_SYNC_BATCH_SIZE and SVV_API_KEY and SVV_SYNC_ENABLED:
            asyncio.create_task(run_vehicle_svv_sync(SVV_IMPORT_SYNC_BATCH_SIZE, "EasyPark import"))
        return {"status": "ok", **counts, "vehicles_refreshed": vehicle_count}
    except Exception as exc:
        async with async_session() as session:
            await record_import_job(
                session,
                "easypark_parking_import",
                ok=False,
                source="EasyPark CSV",
                started_at=started_at,
                records_imported=0,
                records_total=0,
                message=str(exc),
                raw={"filename": filename},
            )
            await session.commit()
        return JSONResponse({"status": "error", "detail": str(exc)}, status_code=400)


@app.post("/api/parkering/svv-sync")
async def parking_vehicle_svv_sync_api(request: Request, limit: int = Query(SVV_SYNC_BATCH_SIZE, ge=1, le=500)):
    forbidden = require_settings_access(request)
    if forbidden:
        return forbidden
    result = await run_vehicle_svv_sync(limit, "Manuell")
    return result


def parking_slot_remainder_minutes(row: ParkingSession) -> Optional[int]:
    duration = row.parking_time_min
    if duration is None and row.start_time and row.end_time:
        duration = (row.end_time - row.start_time).total_seconds() / 60
    if duration is None or duration <= 0:
        return None
    remainder = duration % 30
    if remainder < 1 or remainder > 29:
        return None
    return int(round(30 - remainder))


def parking_vehicle_year(details: Optional[ParkingVehicleDetails]) -> Optional[int]:
    if not details:
        return None
    source = details.forstegangsregistrert_norge or details.svv_teknisk_gyldig_fra
    return source.year if source else None


def parking_vehicle_label(details: Optional[ParkingVehicleDetails]) -> str:
    if not details:
        return "Ukjent kjøretøy"
    text = " ".join(part for part in [details.merke, details.modell, details.typebetegnelse] if part)
    return text or "Ukjent kjøretøy"


def parking_vehicle_summary(details: Optional[ParkingVehicleDetails]) -> Optional[str]:
    if not details:
        return None
    label = parking_vehicle_label(details)
    year = parking_vehicle_year(details)
    summary = f"{year} {label}" if year else label
    color = (details.farge or "").strip()
    return f"{summary} - {color}" if color else summary


def parking_source_label(source_system: Optional[str]) -> str:
    return (source_system or "").strip() or "-"


def parking_duration_minutes(row: ParkingSession, now: Optional[datetime] = None) -> Optional[float]:
    if row.parking_time_min is not None:
        return row.parking_time_min
    if row.start_time and row.end_time:
        return max(0, (row.end_time - row.start_time).total_seconds() / 60)
    if row.start_time and (row.status or "").strip().lower() == "ongoing":
        now = now or local_now_naive()
        return max(0, (now - row.start_time).total_seconds() / 60)
    return None


def parking_day_time_label(value: Optional[datetime], selected_day: date) -> str:
    if not value:
        return "-"
    offset = (value.date() - selected_day).days
    suffix = f" {offset:+d}" if offset else ""
    return f"{value.strftime('%H:%M')}{suffix}"


def parking_row_context(
    row: ParkingSession,
    vehicle: Optional[ParkingVehicle] = None,
    details: Optional[ParkingVehicleDetails] = None,
    now: Optional[datetime] = None,
    selected_day: Optional[date] = None,
) -> Dict[str, Any]:
    plate = normalize_plate(row.car_license_number)
    selected_day = selected_day or local_now_naive().date()
    return {
        "session": row,
        "plate": plate,
        "vehicle_name": vehicle.navn if vehicle else None,
        "vehicle_area": vehicle.omrade if vehicle else None,
        "vehicle_title": parking_vehicle_summary(details),
        "source_label": parking_source_label(row.source_system),
        "parking_count": vehicle.parkering_count if vehicle else None,
        "duration_minutes": parking_duration_minutes(row, now),
        "start_label": parking_day_time_label(row.start_time, selected_day),
        "end_label": parking_day_time_label(row.end_time, selected_day),
    }


async def parking_period_summary(session, label: str, start_at: datetime, end_at: datetime) -> Dict[str, Any]:
    row = (
        await session.execute(
            select(
                func.count(ParkingSession.id),
                func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0),
            ).where(
                ParkingSession.start_time >= start_at,
                ParkingSession.start_time < end_at,
            )
        )
    ).first()
    return {"label": label, "count": row[0] or 0, "paid": row[1] or 0}


def easypark_recent_period() -> tuple[date, date]:
    today = local_now_naive().date()
    return today - timedelta(days=1), today


def easypark_downloader_request(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    query = urlencode({key: value for key, value in params.items() if value is not None})
    url = f"{EASYPARK_DOWNLOADER_URL}{path}"
    if query:
        url = f"{url}?{query}"
    request = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ugyldig svar fra EasyPark-downloader: {payload[:240]}") from exc


@app.post("/parkering/refresh")
async def parking_refresh(request: Request):
    forbidden = require_settings_access(request)
    if forbidden:
        return forbidden
    from_day, to_day = easypark_recent_period()
    started_at = local_now_naive()
    try:
        result = await asyncio.to_thread(
            easypark_downloader_request,
            "/sync-period",
            {"from_date": from_day.isoformat(), "to_date": to_day.isoformat()},
        )
        status = result.get("status")
        if status == "busy":
            outcome = "busy"
        elif status == "error":
            raise RuntimeError(str(result.get("detail") or result.get("last_error") or "EasyPark-import feilet"))
        else:
            outcome = "ok"
    except Exception as exc:
        async with async_session() as session:
            await record_import_job(
                session,
                "easypark_parking_import",
                ok=False,
                source="EasyPark downloader",
                started_at=started_at,
                records_imported=0,
                records_total=0,
                message=str(exc),
                raw={"period": {"from": from_day.isoformat(), "to": to_day.isoformat()}},
            )
            await session.commit()
        outcome = "error"
    day = request.query_params.get("day")
    suffix = f"?day={quote(day)}&refresh={outcome}" if day else f"?refresh={outcome}"
    return RedirectResponse(f"/parkering/oversikt{suffix}", status_code=303)


@app.get("/parkering/oversikt", response_class=HTMLResponse)
async def parking_overview_view(
    request: Request,
    refresh: Optional[str] = None,
    day: Optional[date] = Query(None),
):
    now = local_now_naive()
    today = now.date()
    selected_day = day or today
    selected_start = datetime.combine(selected_day, time.min)
    selected_end = selected_start + timedelta(days=1)
    today_start = datetime.combine(today, time.min)
    tomorrow_start = today_start + timedelta(days=1)
    yesterday_start = today_start - timedelta(days=1)
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, time.min)
    previous_month_end = month_start_dt
    previous_month_start = datetime.combine((month_start - timedelta(days=1)).replace(day=1), time.min)
    week_start = today_start - timedelta(days=today.weekday())
    previous_week_start = week_start - timedelta(days=7)
    normalized_session_plate = func.upper(func.replace(ParkingSession.car_license_number, " ", ""))
    async with async_session() as session:
        period_cards = [
            await parking_period_summary(session, "I dag", today_start, tomorrow_start),
            await parking_period_summary(session, "I går", yesterday_start, today_start),
            await parking_period_summary(session, "Denne uken", week_start, tomorrow_start),
            await parking_period_summary(session, "Forrige uke", previous_week_start, week_start),
            await parking_period_summary(session, "Denne måneden", month_start_dt, tomorrow_start),
            await parking_period_summary(session, "Forrige måned", previous_month_start, previous_month_end),
        ]
        today_rows = (
            await session.execute(
                select(ParkingSession, ParkingVehicle, ParkingVehicleDetails)
                .outerjoin(ParkingVehicle, ParkingVehicle.plate == normalized_session_plate)
                .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == normalized_session_plate)
                .where(
                    ParkingSession.start_time < selected_end,
                    or_(
                        ParkingSession.end_time.is_(None),
                        ParkingSession.end_time >= selected_start,
                        func.lower(func.coalesce(ParkingSession.status, "")) == "ongoing",
                    ),
                )
                .order_by(ParkingSession.start_time.desc())
            )
        ).all()
        ongoing_today = [
            parking_row_context(row, vehicle, details, now, selected_day)
            for row, vehicle, details in today_rows
            if (row.status or "").strip().lower() == "ongoing"
        ]
        completed_today = [
            parking_row_context(row, vehicle, details, now, selected_day)
            for row, vehicle, details in today_rows
            if (row.status or "").strip().lower() != "ongoing"
        ]
        last_parking_at = (
            await session.execute(
                select(func.max(ParkingSession.imported_at))
            )
        ).scalar_one()
        easypark_row = (
            await session.execute(
                select(ImportJobStatus).where(ImportJobStatus.job_name == "easypark_parking_import")
            )
        ).scalars().first()
        easypark_status = None
        if easypark_row:
            definition = import_job_definition("easypark_parking_import")
            if easypark_row.status == "running":
                status, status_text = "running", "Kjører"
            else:
                status, status_text = import_job_status_from_age(
                    easypark_row.last_success_at,
                    definition.get("expected_interval_minutes"),
                    definition.get("warning_after_minutes"),
                )
            easypark_status = {
                "status": status,
                "status_text": status_text,
                "last_success_at": easypark_row.last_success_at,
                "records_total": easypark_row.records_total,
                "message": easypark_row.message,
            }
    refresh_messages = {
        "ok": {"level": "good", "text": "EasyPark er hentet for i går og i dag."},
        "busy": {"level": "warn", "text": "EasyPark-importen kjører allerede. Prøv igjen litt senere."},
        "error": {"level": "bad", "text": "EasyPark-importen feilet. Se datakilder for detaljer."},
    }
    refresh_from, refresh_to = easypark_recent_period()
    return templates.TemplateResponse(
        request,
        "parking_overview.html",
        {
            "today": today,
            "selected_day": selected_day,
            "previous_day": selected_day - timedelta(days=1),
            "next_day": selected_day + timedelta(days=1),
            "period_cards": period_cards,
            "ongoing_today": ongoing_today,
            "completed_today": completed_today,
            "last_parking_at": last_parking_at,
            "easypark_status": easypark_status,
            "refresh_period": {"from_day": refresh_from, "to_day": refresh_to},
            "refresh_message": refresh_messages.get(refresh or ""),
            "can_settings": getattr(request.state, "auth_can_settings", False),
        },
    )


@app.get("/parkering/statistikk", response_class=HTMLResponse)
async def parking_statistics_view(request: Request):
    async with async_session() as session:
        summaries = await get_parking_summaries(session)
    return templates.TemplateResponse(
        request,
        "parking_statistics.html",
        {
            "top_days": summaries["top_days"],
            "top_months": summaries["top_months"],
            "top_days_by_count": summaries["top_days_by_count"],
            "top_months_by_count": summaries["top_months_by_count"],
            "weekly_chart": summaries["weekly_chart"],
            "grand_total": summaries["total"],
            "first_date": summaries["first_date"],
            "last_date": summaries["last_date"],
        },
    )


@app.get("/parkering/prognose", response_class=HTMLResponse)
async def parking_forecast_view(request: Request):
    now_local = datetime.now(LOCAL_TZ)
    today = now_local.date()
    async with async_session() as session:
        forecast = await build_parking_forecast(session, today, now_local)
        saved_forecasts = await saved_forecast_table(session, "parking")
    response = templates.TemplateResponse(
        request,
        "parking_forecast.html",
        {
            "forecast": forecast,
            "day": forecast["day"],
            "month": forecast["month"],
            "year": forecast["year"],
            "saved_forecasts": saved_forecasts,
            "saved": request.query_params.get("saved") == "1",
        },
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/parkering/prognose/lagre")
async def parking_forecast_save(request: Request):
    now_local = datetime.now(LOCAL_TZ)
    today = now_local.date()
    async with async_session() as session:
        forecast = await build_parking_forecast(session, today, now_local)
        await save_forecast_snapshots(session, "parking", forecast, getattr(request.state, "access_key_name", None))
        await session.commit()
    return RedirectResponse("/parkering/prognose?saved=1", status_code=303)


@app.get("/parkering/bilstatistikk", response_class=HTMLResponse)
async def parking_vehicle_statistics_view(request: Request):
    async with async_session() as session:
        top_plates = (
            await session.execute(
                select(
                    ParkingVehicle.plate,
                    ParkingVehicle.parkering_count,
                    ParkingVehicle.paid_total,
                    ParkingVehicleDetails.merke,
                    ParkingVehicleDetails.modell,
                    ParkingVehicleDetails.kjoretoyklasse_navn,
                    ParkingVehicle.navn,
                    ParkingVehicle.omrade,
                )
                .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                .order_by(ParkingVehicle.parkering_count.desc().nullslast(), ParkingVehicle.paid_total.desc().nullslast())
                .limit(50)
            )
        ).all()
        make_expr = func.coalesce(ParkingVehicleDetails.merke, "Ukjent")
        top_makes = (
            await session.execute(
                select(
                    make_expr,
                    func.count(ParkingVehicleDetails.plate),
                )
                .group_by(make_expr)
                .order_by(func.count(ParkingVehicleDetails.plate).desc())
                .limit(50)
            )
        ).all()
        vehicle_total = (
            await session.execute(select(func.count(func.distinct(ParkingVehicle.plate))))
        ).scalar_one()
        vehicle_with_details = (
            await session.execute(select(func.count(func.distinct(ParkingVehicleDetails.plate))))
        ).scalar_one()
    return templates.TemplateResponse(
        request,
        "parking_vehicle_statistics.html",
        {
            "top_plates": top_plates,
            "top_makes": top_makes,
            "vehicle_total": vehicle_total,
            "vehicle_with_details": vehicle_with_details,
        },
    )


@app.get("/parkering/omrade", response_class=HTMLResponse)
async def parking_area_overview_view(request: Request):
    valid_area_condition = and_(
        func.trim(func.coalesce(ParkingVehicle.omrade, "")) != "",
        func.lower(func.trim(func.coalesce(ParkingVehicle.omrade, ""))) != "ikke funnet",
    )
    area_expr = func.trim(ParkingVehicle.omrade)
    async with async_session() as session:
        rows = (
            await session.execute(
                select(
                    area_expr.label("omrade"),
                    func.count(func.distinct(ParkingVehicle.plate)).label("vehicle_count"),
                    func.coalesce(func.sum(ParkingVehicle.parkering_count), 0).label("parking_count"),
                    func.coalesce(func.sum(ParkingVehicle.paid_total), 0).label("paid_total"),
                    func.max(ParkingVehicle.last_seen).label("last_seen"),
                )
                .where(valid_area_condition)
                .group_by(area_expr)
                .order_by(func.count(func.distinct(ParkingVehicle.plate)).desc(), area_expr.asc())
            )
        ).all()
        vehicle_total = (
            await session.execute(select(func.count(func.distinct(ParkingVehicle.plate))))
        ).scalar_one()
        vehicle_with_area = (
            await session.execute(
                select(func.count(func.distinct(ParkingVehicle.plate))).where(valid_area_condition)
            )
        ).scalar_one()
        parking_with_area = sum(int(getattr(row, "parking_count", 0) or 0) for row in rows)
    missing_area = max((vehicle_total or 0) - (vehicle_with_area or 0), 0)
    return templates.TemplateResponse(
        request,
        "parking_areas.html",
        {
            "rows": rows,
            "vehicle_total": vehicle_total,
            "vehicle_with_area": vehicle_with_area,
            "missing_area": missing_area,
            "parking_with_area": parking_with_area,
            "coverage_percent": round((vehicle_with_area / vehicle_total) * 100, 1) if vehicle_total else 0,
        },
    )


@app.get("/parkering/parkeringer", response_class=HTMLResponse)
async def parking_sessions_view(
    request: Request,
    plate: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    conditions = []
    plate_value = normalize_plate(plate)
    if plate_value:
        conditions.append(func.upper(func.replace(ParkingSession.car_license_number, " ", "")) == plate_value)
    from_day = parse_day(date_from) if date_from else None
    to_day = parse_day(date_to) if date_to else None
    if from_day:
        conditions.append(ParkingSession.start_time >= datetime.combine(from_day, time.min))
    if to_day:
        conditions.append(ParkingSession.start_time < datetime.combine(to_day + timedelta(days=1), time.min))
    if status:
        conditions.append(ParkingSession.status == status)

    normalized_session_plate = func.upper(func.replace(ParkingSession.car_license_number, " ", ""))
    async with async_session() as session:
        stmt = (
            select(ParkingSession, ParkingVehicle, ParkingVehicleDetails)
            .outerjoin(ParkingVehicle, ParkingVehicle.plate == normalized_session_plate)
            .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == normalized_session_plate)
            .order_by(ParkingSession.start_time.desc())
            .limit(limit)
        )
        count_stmt = select(func.count(ParkingSession.id))
        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)
        result_rows = (await session.execute(stmt)).all()
        count = (await session.execute(count_stmt)).scalar_one()
        statuses = (
            await session.execute(
                select(ParkingSession.status)
                .group_by(ParkingSession.status)
                .order_by(ParkingSession.status)
            )
        ).scalars().all()
    return templates.TemplateResponse(
        request,
        "parking_sessions.html",
        {
            "rows": [
                {
                    "session": row,
                    "vehicle": vehicle,
                    "details": details,
                    "year": parking_vehicle_year(details),
                    "early_minutes": parking_slot_remainder_minutes(row),
                    "plate": normalize_plate(row.car_license_number),
                }
                for row, vehicle, details in result_rows
            ],
            "count": count,
            "statuses": statuses,
            "filters": {
                "plate": plate or "",
                "date_from": date_from or "",
                "date_to": date_to or "",
                "status": status or "",
                "limit": limit,
            },
        },
    )


@app.get("/parkering/kjoretoy", response_class=HTMLResponse)
async def parking_vehicles_view(
    request: Request,
    plate: Optional[str] = None,
    navn: Optional[str] = None,
    omrade: Optional[str] = None,
    sun2_id: Optional[str] = None,
    merke: Optional[str] = None,
    modell: Optional[str] = None,
    ryddet: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
):
    conditions = []

    def add_contains(column, value: Optional[str]):
        query = (value or "").strip()
        if query:
            conditions.append(func.upper(func.coalesce(column, "")).like(f"%{query.upper()}%"))

    plate_query = compact_plate(plate or "")
    if plate_query:
        conditions.append(func.upper(func.replace(ParkingVehicle.plate, " ", "")).like(f"%{plate_query.upper()}%"))

    add_contains(ParkingVehicle.navn, navn)
    add_contains(ParkingVehicle.omrade, omrade)
    add_contains(ParkingVehicle.sun2_id, sun2_id)
    add_contains(ParkingVehicleDetails.merke, merke)

    model_query = (modell or "").strip()
    if model_query:
        like = f"%{model_query.upper()}%"
        conditions.append(
            or_(
                func.upper(func.coalesce(ParkingVehicleDetails.modell, "")).like(like),
                func.upper(func.coalesce(ParkingVehicleDetails.typebetegnelse, "")).like(like),
            )
        )

    async with async_session() as session:
        stmt = (
            select(ParkingVehicle, ParkingVehicleDetails)
            .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
            .order_by(ParkingVehicle.last_seen.desc().nullslast())
            .limit(limit)
        )
        count_stmt = select(func.count(ParkingVehicle.plate)).outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)
        rows = (await session.execute(stmt)).all()
        count = (await session.execute(count_stmt)).scalar_one()
        valid_area_condition = and_(
            func.trim(func.coalesce(ParkingVehicle.omrade, "")) != "",
            func.lower(func.trim(func.coalesce(ParkingVehicle.omrade, ""))) != "ikke funnet",
        )
        vehicle_total = (
            await session.execute(select(func.count(func.distinct(ParkingVehicle.plate))))
        ).scalar_one()
        vehicle_with_area = (
            await session.execute(
                select(func.count(func.distinct(ParkingVehicle.plate))).where(valid_area_condition)
            )
        ).scalar_one()
    return templates.TemplateResponse(
        request,
        "parking_vehicles.html",
        {
            "rows": rows,
            "count": count,
            "vehicle_area_stats": {
                "total": vehicle_total,
                "with_area": vehicle_with_area,
                "missing_area": max((vehicle_total or 0) - (vehicle_with_area or 0), 0),
                "coverage_percent": round((vehicle_with_area / vehicle_total) * 100, 1) if vehicle_total else 0,
            },
            "filters": {
                "plate": plate or "",
                "navn": navn or "",
                "omrade": omrade or "",
                "sun2_id": sun2_id or "",
                "merke": merke or "",
                "modell": modell or "",
                "limit": limit,
            },
            "cleanup_count": ryddet,
        },
    )


@app.post("/parkering/kjoretoy/rydd-ikke-funnet")
async def parking_vehicle_clear_not_found_area(request: Request):
    forbidden = require_settings_access(request)
    if forbidden:
        return forbidden
    async with async_session() as session:
        result = await session.execute(
            update(ParkingVehicle)
            .where(func.lower(func.trim(func.coalesce(ParkingVehicle.omrade, ""))) == "ikke funnet")
            .values(
                omrade=None,
                omrade_kilde=None,
                omrade_oppdatert=None,
            )
        )
        await session.commit()
    return redirect_with_query_params(request, "/parkering/kjoretoy", ryddet=result.rowcount or 0)


def vehicle_missing_name_condition():
    return or_(ParkingVehicle.navn.is_(None), func.trim(ParkingVehicle.navn) == "")


def vehicle_missing_area_condition():
    return or_(ParkingVehicle.omrade.is_(None), func.trim(ParkingVehicle.omrade) == "")


async def parking_missing_name_rows(session, limit: int, offset: int = 0):
    return (
        await session.execute(
            select(ParkingVehicle, ParkingVehicleDetails)
            .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
            .where(vehicle_missing_name_condition())
            .order_by(ParkingVehicle.last_seen.desc().nullslast(), ParkingVehicle.plate.asc())
            .offset(offset)
            .limit(limit)
        )
    ).all()


async def parking_missing_area_rows(session, limit: int, offset: int = 0):
    return (
        await session.execute(
            select(ParkingVehicle, ParkingVehicleDetails)
            .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
            .where(vehicle_missing_area_condition())
            .order_by(ParkingVehicle.last_seen.desc().nullslast(), ParkingVehicle.plate.asc())
            .offset(offset)
            .limit(limit)
        )
    ).all()


def parking_vehicle_lookup_payload(vehicle: ParkingVehicle, details: Optional[ParkingVehicleDetails] = None) -> Dict[str, Any]:
    return {
        "plate": vehicle.plate,
        "navn": vehicle.navn,
        "omrade": vehicle.omrade,
        "sun2_id": vehicle.sun2_id,
        "notat": vehicle.notat,
        "last_seen": vehicle.last_seen.isoformat() if vehicle.last_seen else None,
        "parkering_count": vehicle.parkering_count,
        "vehicle": parking_vehicle_summary(details),
        "make": details.merke if details else None,
        "model": details.modell if details else None,
        "year": parking_vehicle_year(details),
    }


@app.get("/parkering/navn-oppslag", response_class=HTMLResponse)
async def parking_name_lookup_view(request: Request, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    async with async_session() as session:
        rows = await parking_missing_name_rows(session, limit, offset)
        count = (
            await session.execute(
                select(func.count(ParkingVehicle.plate)).where(vehicle_missing_name_condition())
            )
        ).scalar_one()
    plates = "\n".join(vehicle.plate for vehicle, _ in rows)
    return templates.TemplateResponse(
        request,
        "parking_name_lookup.html",
        {
            "rows": rows,
            "count": count,
            "plates": plates,
            "limit": limit,
            "offset": offset,
            "next_offset": offset + limit,
            "prev_offset": max(0, offset - limit),
        },
    )


@app.get("/parkering/omrade-oppslag", response_class=HTMLResponse)
async def parking_area_lookup_view(request: Request, limit: int = Query(1000, ge=1, le=1000), offset: int = Query(0, ge=0)):
    async with async_session() as session:
        rows = await parking_missing_area_rows(session, limit, offset)
        count = (
            await session.execute(
                select(func.count(ParkingVehicle.plate)).where(vehicle_missing_area_condition())
            )
        ).scalar_one()
    plates = "\n".join(vehicle.plate for vehicle, _ in rows)
    return templates.TemplateResponse(
        request,
        "parking_name_lookup.html",
        {
            "rows": rows,
            "count": count,
            "plates": plates,
            "limit": limit,
            "offset": offset,
            "next_offset": offset + limit,
            "prev_offset": max(0, offset - limit),
            "mode": "omrade",
            "title": "Områdeoppslag",
            "description": "biler mangler område. Denne siden gir extensionen neste pakke på",
        },
    )


@app.get("/api/parkering/kjoretoy/mangler-navn")
async def parking_missing_names_api(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    format: str = "json",
):
    forbidden = require_settings_access(request)
    if forbidden:
        return forbidden
    async with async_session() as session:
        rows = await parking_missing_name_rows(session, limit, offset)
        count = (
            await session.execute(
                select(func.count(ParkingVehicle.plate)).where(vehicle_missing_name_condition())
            )
        ).scalar_one()
    payload = [parking_vehicle_lookup_payload(vehicle, details) for vehicle, details in rows]
    if format == "txt":
        text_body = "\n".join(item["plate"] for item in payload) + ("\n" if payload else "")
        return StreamingResponse(iter([text_body]), media_type="text/plain; charset=utf-8")
    return {"count": count, "limit": limit, "offset": offset, "rows": payload}


@app.get("/api/parkering/kjoretoy/mangler-omrade")
async def parking_missing_areas_api(
    request: Request,
    limit: int = Query(1000, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    format: str = "json",
):
    forbidden = require_settings_access(request)
    if forbidden:
        return forbidden
    async with async_session() as session:
        rows = await parking_missing_area_rows(session, limit, offset)
        count = (
            await session.execute(
                select(func.count(ParkingVehicle.plate)).where(vehicle_missing_area_condition())
            )
        ).scalar_one()
    payload = [parking_vehicle_lookup_payload(vehicle, details) for vehicle, details in rows]
    if format == "txt":
        text_body = "\n".join(item["plate"] for item in payload) + ("\n" if payload else "")
        return StreamingResponse(iter([text_body]), media_type="text/plain; charset=utf-8")
    return {"count": count, "limit": limit, "offset": offset, "rows": payload}


@app.post("/api/parkering/kjoretoy/{plate}/navn")
async def parking_vehicle_name_api(request: Request, plate: str, data: ParkingVehicleNameUpdate):
    forbidden = require_settings_access(request)
    if forbidden:
        return forbidden
    plate_value = normalize_plate(plate)
    name = (data.navn or "").strip()
    if not plate_value:
        return JSONResponse({"detail": "Mangler registreringsnummer"}, status_code=400)
    if not name:
        return JSONResponse({"detail": "Navn mangler"}, status_code=400)
    async with async_session() as session:
        vehicle = (await session.execute(select(ParkingVehicle).where(ParkingVehicle.plate == plate_value))).scalars().first()
        if not vehicle:
            return JSONResponse({"detail": "Kjoretoy ikke funnet"}, status_code=404)
        vehicle.navn = name
        if data.sun2_id is not None:
            vehicle.sun2_id = data.sun2_id.strip() or None
        if data.notat is not None:
            vehicle.notat = data.notat.strip() or None
        note_bits = []
        if data.source:
            note_bits.append(f"kilde={data.source.strip()}")
        if data.raw:
            note_bits.append(f"raw={json.dumps(data.raw, ensure_ascii=False)[:1000]}")
        if note_bits:
            base_note = vehicle.notat.strip() if vehicle.notat else ""
            auto_note = f"Automatisk navneoppslag {local_now_naive().strftime('%Y-%m-%d %H:%M')}: " + " | ".join(note_bits)
            vehicle.notat = f"{base_note}\n{auto_note}".strip()
        vehicle.updated_at = datetime.utcnow()
        await session.commit()
    return {"status": "ok", "plate": plate_value, "navn": name}


@app.post("/api/parkering/kjoretoy/{plate}/omrade")
async def parking_vehicle_area_api(request: Request, plate: str, data: ParkingVehicleAreaUpdate):
    forbidden = require_settings_access(request)
    if forbidden:
        return forbidden
    plate_value = normalize_plate(plate)
    area = (data.omrade or "").strip()
    if not plate_value:
        return JSONResponse({"detail": "Mangler registreringsnummer"}, status_code=400)
    if not area:
        return JSONResponse({"detail": "Område mangler"}, status_code=400)
    async with async_session() as session:
        vehicle = (await session.execute(select(ParkingVehicle).where(ParkingVehicle.plate == plate_value))).scalars().first()
        if not vehicle:
            return JSONResponse({"detail": "Kjoretoy ikke funnet"}, status_code=404)
        vehicle.omrade = area
        vehicle.omrade_kilde = (data.source or "manual-browser-helper").strip() or "manual-browser-helper"
        vehicle.omrade_oppdatert = datetime.utcnow()
        vehicle.updated_at = datetime.utcnow()
        await session.commit()
    return {"status": "ok", "plate": plate_value, "omrade": area}


@app.get("/parkering/kjoretoy/{plate}", response_class=HTMLResponse)
async def parking_vehicle_detail_view(request: Request, plate: str, saved: Optional[str] = None):
    plate_value = normalize_plate(plate)
    if not plate_value:
        raise HTTPException(status_code=404, detail="Mangler registreringsnummer")

    normalized_session_plate = func.upper(func.replace(ParkingSession.car_license_number, " ", ""))
    async with async_session() as session:
        result = (
            await session.execute(
                select(ParkingVehicle, ParkingVehicleDetails)
                .outerjoin(ParkingVehicleDetails, ParkingVehicleDetails.plate == ParkingVehicle.plate)
                .where(ParkingVehicle.plate == plate_value)
            )
        ).first()
        if not result:
            raise HTTPException(status_code=404, detail="Kjøretøy ikke funnet")
        vehicle, details = result
        stats = (
            await session.execute(
                select(
                    func.count(ParkingSession.id),
                    func.coalesce(func.sum(ParkingSession.fee_inc_vat), 0),
                    func.coalesce(func.sum(ParkingSession.parking_time_min), 0),
                    func.min(ParkingSession.start_time),
                    func.max(ParkingSession.start_time),
                ).where(normalized_session_plate == plate_value)
            )
        ).first()
        recent_sessions_result = (
            await session.execute(
                select(ParkingSession)
                .where(normalized_session_plate == plate_value)
                .order_by(ParkingSession.start_time.desc())
                .limit(20)
            )
        ).scalars().all()

    detail_rows = []
    if details:
        detail_rows = [
            ("Merke", details.merke),
            ("Modell", details.modell),
            ("Typebetegnelse", details.typebetegnelse),
            ("Årsmodell", parking_vehicle_year(details)),
            ("Farge", details.farge),
            ("Kjøretøyklasse", details.kjoretoyklasse_navn),
            ("Registreringsstatus", details.registreringsstatus_tekst),
            ("Førstegangsregistrert Norge", details.forstegangsregistrert_norge),
            ("PKK kontrollfrist", details.pkk_kontrollfrist),
            ("Egenvekt", f"{details.egenvekt_kg} kg" if details.egenvekt_kg is not None else None),
            ("Nyttelast", f"{details.nyttelast_kg} kg" if details.nyttelast_kg is not None else None),
            ("Tillatt totalvekt", f"{details.tillatt_totalvekt_kg} kg" if details.tillatt_totalvekt_kg is not None else None),
            ("Seter", details.seter_totalt),
            ("Lengde", f"{details.lengde_mm} mm" if details.lengde_mm is not None else None),
            ("Bredde", f"{details.bredde_mm} mm" if details.bredde_mm is not None else None),
            ("Høyde", f"{details.hoyde_mm} mm" if details.hoyde_mm is not None else None),
            ("Rekkevidde WLTP", f"{details.rekkevidde_wltp_km} km" if details.rekkevidde_wltp_km is not None else None),
            ("Elforbruk WLTP", f"{details.elforbruk_wltp_wh_km} Wh/km" if details.elforbruk_wltp_wh_km is not None else None),
            ("Motoreffekt", f"{details.motoreffekt_samlet_kw} kW" if details.motoreffekt_samlet_kw is not None else None),
            ("SVV teknisk gyldig fra", details.svv_teknisk_gyldig_fra),
            ("Sist synkronisert", details.sist_synkronisert),
            ("VIN", details.vin),
        ]
    detail_rows = [(label, value) for label, value in detail_rows if value not in (None, "")]

    return templates.TemplateResponse(
        request,
        "parking_vehicle_detail.html",
        {
            "plate": plate_value,
            "vehicle": vehicle,
            "details": details,
            "title": parking_vehicle_label(details),
            "year": parking_vehicle_year(details),
            "stats": {
                "sessions": stats[0] or 0,
                "paid": stats[1] or 0,
                "minutes": stats[2] or 0,
                "first": stats[3],
                "last": stats[4],
            },
            "recent_sessions": [
                {
                    "session": row,
                    "early_minutes": parking_slot_remainder_minutes(row),
                }
                for row in recent_sessions_result
            ],
            "detail_rows": detail_rows,
            "saved": saved == "1",
        },
    )


@app.post("/parkering/kjoretoy/{plate}", response_class=HTMLResponse)
async def parking_vehicle_detail_save(request: Request, plate: str):
    if not getattr(request.state, "auth_can_settings", False):
        raise HTTPException(status_code=403, detail="Du må ha innstillingstilgang for å endre kjøretøyfelt.")
    plate_value = normalize_plate(plate)
    form = await request.form()
    async with async_session() as session:
        vehicle = (await session.execute(select(ParkingVehicle).where(ParkingVehicle.plate == plate_value))).scalars().first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Kjøretøy ikke funnet")
        vehicle.navn = (form.get("navn") or "").strip() or None
        previous_area = vehicle.omrade
        vehicle.omrade = (form.get("omrade") or "").strip() or None
        if vehicle.omrade and vehicle.omrade != previous_area:
            vehicle.omrade_kilde = "manuell"
            vehicle.omrade_oppdatert = datetime.utcnow()
        vehicle.sun2_id = (form.get("sun2_id") or "").strip() or None
        vehicle.notat = (form.get("notat") or "").strip() or None
        vehicle.updated_at = datetime.utcnow()
        await session.commit()
    return redirect_keep_query(request, f"/parkering/kjoretoy/{quote(plate_value)}?saved=1", status_code=303)


@app.get("/energi")
async def energy_redirect(request: Request):
    return redirect_keep_query(request, "/energi/status", status_code=307)


@app.get("/energi/oversikt", response_class=HTMLResponse)
async def energy_overview_legacy_redirect(request: Request):
    return redirect_keep_query(request, "/energi/status", status_code=307)


@app.get("/energi/soling", response_class=HTMLResponse)
async def energy_soling_legacy_redirect(request: Request):
    return redirect_keep_query(request, "/soling/detaljer", status_code=307)


@app.post("/api/energi/fibaro")
async def energy_fibaro_ingest(data: EnergyFibaroIn):
    async with async_session() as session:
        record = await upsert_energy_fibaro_sample(session, data)
        await session.flush()
        await record_import_job(
            session,
            "hc3_energy_1min",
            source=data.source or "HC3",
            records_imported=1,
            records_total=1,
            message=f"Inntak {format_short_number(record.inntak_w)} W" if record.inntak_w is not None else "Energisample mottatt",
            raw={"sample_id": record.id, "bucket_start": record.bucket_start.isoformat() if record.bucket_start else None},
        )
        await session.commit()
        await session.refresh(record)
    return {
        "status": "ok",
        "id": record.id,
        "bucket_start": record.bucket_start.isoformat() if record.bucket_start else None,
        "differanse_beregnet_w": record.differanse_beregnet_w,
        "resets": {
            "inntak": record.inntak_reset,
            "varmepumper": record.varmepumper_reset,
            "belysning": record.belysning_reset,
            "massasje": record.massasje_reset,
            "annet": record.annet_reset,
            "avfukter": record.avfukter_reset,
            "differanse_fibaro": record.differanse_fibaro_reset,
        },
    }


@app.get("/energi/status", response_class=HTMLResponse)
async def energy_status_view(request: Request, day: Optional[str] = None):
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
        "differanse_fibaro": sum(1 for row in today_rows if row.differanse_fibaro_reset),
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


def form_text(form, key: str) -> Optional[str]:
    value = form.get(key)
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def form_int(form, key: str) -> Optional[int]:
    value = form_text(form, key)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def form_float(form, key: str) -> Optional[float]:
    value = form_text(form, key)
    if value is None:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def form_bool(form, key: str, default: bool = False) -> bool:
    if key not in form:
        return default
    return str(form.get(key)).strip().lower() in {"1", "true", "on", "yes", "ja"}


def circuit_technical_label(circuit: EnergyCircuit) -> str:
    parts = []
    if circuit.breaker_type:
        parts.append(circuit.breaker_type)
    if circuit.breaker_rating_a is not None:
        parts.append(f"{circuit.breaker_rating_a:g} A")
    if circuit.breaker_characteristic:
        parts.append(str(circuit.breaker_characteristic))
    return " / ".join(parts) if parts else "-"


def energy_circuit_is_sunbed(circuit: EnergyCircuit) -> bool:
    if circuit.is_sunbed is not None:
        return bool(circuit.is_sunbed)
    return "solseng" in (circuit.description or "").strip().lower()


def normalize_energy_sunbed_filter(value: Optional[str]) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"hide", "skjul", "exclude", "nei", "0"}:
        return "hide"
    if normalized in {"only", "kun", "ja", "1"}:
        return "only"
    return ""


def filter_energy_circuits_by_sunbed(circuits: list[EnergyCircuit], sunbeds: Optional[str]) -> list[EnergyCircuit]:
    sunbed_filter = normalize_energy_sunbed_filter(sunbeds)
    if sunbed_filter == "hide":
        return [row for row in circuits if not energy_circuit_is_sunbed(row)]
    if sunbed_filter == "only":
        return [row for row in circuits if energy_circuit_is_sunbed(row)]
    return circuits


def energy_query_url(path: str, **params: Any) -> str:
    clean = {key: value for key, value in params.items() if value not in (None, "", False)}
    query = urlencode(clean)
    return f"{path}?{query}" if query else path


def pdf_literal(value: Any) -> bytes:
    text_value = "" if value is None else str(value)
    raw = text_value.encode("cp1252", errors="replace")
    out = bytearray()
    out.append(ord("("))
    for byte in raw:
        if byte in (40, 41, 92):
            out.append(92)
            out.append(byte)
        elif byte < 32 or byte > 126:
            out.extend(f"\\{byte:03o}".encode("ascii"))
        else:
            out.append(byte)
    out.append(ord(")"))
    return bytes(out)


def pdf_text(x: float, y: float, text_value: Any, size: float = 8, bold: bool = False) -> bytes:
    font = "F2" if bold else "F1"
    return b"BT /%b %.2f Tf 1 0 0 1 %.2f %.2f Tm %b Tj ET\n" % (
        font.encode("ascii"),
        size,
        x,
        y,
        pdf_literal(text_value),
    )


def pdf_line(x1: float, y1: float, x2: float, y2: float, gray: float = 0.82, width: float = 0.45) -> bytes:
    return f"{gray:.2f} G {width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S\n".encode("ascii")


def pdf_fill_rect(x: float, y: float, width: float, height: float, gray: float = 0.96) -> bytes:
    return f"{gray:.2f} g {x:.2f} {y:.2f} {width:.2f} {height:.2f} re f 0 g\n".encode("ascii")


def wrap_pdf_text(value: Any, max_chars: int) -> list[str]:
    text_value = re.sub(r"\s+", " ", "" if value is None else str(value)).strip()
    if not text_value:
        return ["-"]
    words = text_value.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        if len(word) > max_chars:
            if current:
                lines.append(current)
                current = ""
            for index in range(0, len(word), max_chars):
                lines.append(word[index:index + max_chars])
            continue
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or ["-"]


def assemble_pdf(page_streams: list[bytes], page_width: float, page_height: float) -> bytes:
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    }
    kids = []
    next_id = 5
    for stream in page_streams:
        page_id = next_id
        content_id = next_id + 1
        next_id += 2
        kids.append(f"{page_id} 0 R")
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width:.2f} {page_height:.2f}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")
        objects[content_id] = b"<< /Length %d >>\nstream\n%b\nendstream" % (len(stream), stream)
    objects[2] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>".encode("ascii")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for object_id in sorted(objects):
        offsets[object_id] = len(pdf)
        pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
        pdf.extend(objects[object_id])
        pdf.extend(b"\nendobj\n")
    xref_at = len(pdf)
    max_id = max(objects)
    pdf.extend(f"xref\n0 {max_id + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for object_id in range(1, max_id + 1):
        pdf.extend(f"{offsets.get(object_id, 0):010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def build_table_pdf(title: str, subtitle: str, columns: list[dict[str, Any]], rows: list[list[Any]]) -> bytes:
    page_width = 841.89
    page_height = 595.28
    margin = 28.0
    header_height = 74.0
    footer_height = 18.0
    line_height = 9.5
    body_size = 7.4
    header_size = 7.0
    available_width = page_width - margin * 2
    scale = available_width / sum(float(column["width"]) for column in columns)
    col_widths = [float(column["width"]) * scale for column in columns]
    generated_label = f"Generert {local_now_naive().strftime('%d.%m.%Y %H:%M')}"

    def draw_page_header(page_num: int) -> tuple[bytearray, float]:
        content = bytearray()
        y = page_height - margin
        content.extend(pdf_text(margin, y - 5, title, 16, True))
        content.extend(pdf_text(margin, y - 23, subtitle, 8.4, False))
        content.extend(pdf_text(page_width - margin - 118, y - 5, generated_label, 7.5, False))
        content.extend(pdf_text(page_width - margin - 44, margin - 4, f"Side {page_num}", 7.0, False))
        table_top = page_height - margin - header_height
        content.extend(pdf_fill_rect(margin, table_top - 15, available_width, 18, 0.95))
        x = margin
        for column, width in zip(columns, col_widths):
            content.extend(pdf_text(x + 3, table_top - 8, column["label"], header_size, True))
            x += width
        content.extend(pdf_line(margin, table_top - 17, page_width - margin, table_top - 17, 0.78, 0.55))
        return content, table_top - 24

    page_streams: list[bytes] = []
    page_num = 1
    content, y = draw_page_header(page_num)
    bottom = margin + footer_height
    for row in rows:
        wrapped_cells = []
        max_lines = 1
        for value, width in zip(row, col_widths):
            max_chars = max(4, int(width / (body_size * 0.52)))
            lines = wrap_pdf_text(value, max_chars)[:5]
            wrapped_cells.append(lines)
            max_lines = max(max_lines, len(lines))
        row_height = max(17, 7 + max_lines * line_height)
        if y - row_height < bottom:
            page_streams.append(bytes(content))
            page_num += 1
            content, y = draw_page_header(page_num)
        content.extend(pdf_line(margin, y + 4, page_width - margin, y + 4, 0.9, 0.35))
        x = margin
        for lines, width, column in zip(wrapped_cells, col_widths, columns):
            text_x = x + 3
            if column.get("align") == "right":
                text_x = x + max(3, width - 52)
            for index, line in enumerate(lines):
                content.extend(pdf_text(text_x, y - index * line_height, line, body_size, False))
            x += width
        y -= row_height
    page_streams.append(bytes(content))
    return assemble_pdf(page_streams, page_width, page_height)


def pdf_response(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/energi/kurser", response_class=HTMLResponse)
async def energy_circuits_view(
    request: Request,
    edit: Optional[str] = None,
    sunbeds: Optional[str] = None,
    view: Optional[str] = None,
):
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


@app.post("/energi/kurser/{circuit_no}")
async def energy_circuit_save(request: Request, circuit_no: int):
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


@app.get("/energi/kurser/pdf")
async def energy_circuits_pdf(sunbeds: Optional[str] = None):
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
    )
    return pdf_response(pdf_bytes, f"lilletorget_energi_kursliste_{local_now_naive().date().isoformat()}.pdf")


@app.get("/energi/laster", response_class=HTMLResponse)
async def energy_loads_view(
    request: Request,
    q: Optional[str] = None,
    circuit: Optional[int] = None,
    load_type: Optional[str] = None,
    active: Optional[str] = None,
    sunbeds: Optional[str] = None,
):
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


@app.get("/energi/laster/pdf")
async def energy_loads_pdf(
    q: Optional[str] = None,
    circuit: Optional[int] = None,
    load_type: Optional[str] = None,
    active: Optional[str] = None,
    sunbeds: Optional[str] = None,
):
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
    )
    return pdf_response(pdf_bytes, f"lilletorget_energi_laster_{local_now_naive().date().isoformat()}.pdf")


@app.post("/energi/laster", response_class=HTMLResponse)
async def energy_load_save(request: Request):
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


@app.post("/energi/laster/{load_id}/aktiv")
async def energy_load_toggle_active(request: Request, load_id: int):
    form = await request.form()
    async with async_session() as session:
        load = await session.get(EnergyLoad, load_id)
        if not load:
            raise HTTPException(status_code=404, detail="Last ikke funnet")
        load.active = form_bool(form, "active")
        load.updated_at = datetime.utcnow()
        await session.commit()
    return redirect_keep_query(request, "/energi/laster", status_code=303)


@app.get("/api/energi/fibaro/json")
async def energy_fibaro_json(limit: int = 300):
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


@app.get("/energi/forbruk-per-seng", response_class=HTMLResponse)
async def energy_sunbed_consumption_view(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    today = local_now_naive().date()
    end_day = parse_day(date_to) if date_to else today
    start_day = parse_day(date_from) if date_from else end_day - timedelta(days=30)
    if start_day > end_day:
        start_day, end_day = end_day, start_day
    max_days = 120
    if (end_day - start_day).days > max_days:
        start_day = end_day - timedelta(days=max_days)
    start_at = datetime.combine(start_day, time.min)
    end_at = datetime.combine(end_day + timedelta(days=1), time.min)

    async with async_session() as session:
        session_rows = (
            await session.execute(
                select(Sun2TanningSession)
                .where(Sun2TanningSession.started_at >= start_at)
                .where(Sun2TanningSession.started_at < end_at)
                .where(Sun2TanningSession.room_id.is_not(None))
                .order_by(Sun2TanningSession.started_at.asc())
            )
        ).scalars().all()
        energy_rows = (
            await session.execute(
                select(
                    EnergyFibaroSample.bucket_start.label("bucket_start"),
                    EnergyFibaroSample.differanse_beregnet_w.label("differanse_beregnet_w"),
                    EnergyFibaroSample.differanse_fibaro_w.label("differanse_fibaro_w"),
                )
                .where(EnergyFibaroSample.bucket_start >= start_at)
                .where(EnergyFibaroSample.bucket_start < end_at)
                .order_by(EnergyFibaroSample.bucket_start.asc())
            )
        ).mappings().all()
        bed_rows = (
            await session.execute(
                select(Sun2Bed).where(Sun2Bed.room_id.is_not(None))
            )
        ).scalars().all()

    bed_lookup = {bed.room_id: bed for bed in bed_rows if bed.room_id}
    analysis = build_sunbed_power_analysis(session_rows, [dict(row) for row in energy_rows], bed_lookup)
    max_power = max([float_or_zero(room.get("estimate_w")) for room in analysis["rooms"]] or [0.0])
    response = templates.TemplateResponse(
        request,
        "energy_sunbeds.html",
        {
            "date_from": start_day.isoformat(),
            "date_to": end_day.isoformat(),
            "max_days": max_days,
            "analysis": analysis,
            "rooms": analysis["rooms"],
            "observations": analysis["observations"],
            "summary": analysis["summary"],
            "max_power": max_power,
        },
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/soling")
async def sun2_redirect(request: Request):
    return redirect_keep_query(request, "/soling/dagslinje", status_code=307)


@app.get("/soling/oversikt", response_class=HTMLResponse)
async def sun2_overview_view(request: Request):
    async with async_session() as session:
        summaries = await get_sun2_summaries(session)
        latest_import = (
            await session.execute(
                select(Sun2ImportRun)
                .order_by(Sun2ImportRun.timestamp.desc())
                .limit(1)
            )
        ).scalars().first()
    return templates.TemplateResponse(
        request,
        "sun2_overview.html",
        {
            "top_days": summaries["top_days"],
            "top_months": summaries["top_months"],
            "top_days_by_count": summaries["top_days_by_count"],
            "top_months_by_count": summaries["top_months_by_count"],
            "grand_total": summaries["total"],
            "weekly_chart": summaries["weekly_chart"],
            "first_date": summaries["first_date"],
            "last_date": summaries["last_date"],
            "total_rows": summaries["total_rows"],
            "latest_import": latest_import,
        },
    )


@app.get("/soling/prognose", response_class=HTMLResponse)
async def sun2_forecast_view(request: Request):
    now_local = datetime.now(LOCAL_TZ)
    today = now_local.date()
    async with async_session() as session:
        forecast = await build_sun2_forecast(session, today, now_local)
        saved_forecasts = await saved_forecast_table(session, "sun2")
    response = templates.TemplateResponse(
        request,
        "sun2_forecast.html",
        {
            "forecast": forecast,
            "day": forecast["day"],
            "month": forecast["month"],
            "year": forecast["year"],
            "saved_forecasts": saved_forecasts,
            "saved": request.query_params.get("saved") == "1",
        },
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/soling/prognose/lagre")
async def sun2_forecast_save(request: Request):
    now_local = datetime.now(LOCAL_TZ)
    today = now_local.date()
    async with async_session() as session:
        forecast = await build_sun2_forecast(session, today, now_local)
        await save_forecast_snapshots(session, "sun2", forecast, getattr(request.state, "access_key_name", None))
        await session.commit()
    return RedirectResponse("/soling/prognose?saved=1", status_code=303)


@app.get("/soling/detaljer", response_class=HTMLResponse)
async def sun2_room_stats_view(request: Request, limit: int = 150):
    limit = max(1, min(limit, 1000))
    async with async_session() as session:
        summaries = await get_sun2_summaries(session)
        rows = (
            await session.execute(
                select(Sun2RoomDailyStat)
                .order_by(Sun2RoomDailyStat.stat_date.desc(), Sun2RoomDailyStat.room)
                .limit(limit)
            )
        ).scalars().all()
        imports = (
            await session.execute(
                select(Sun2ImportRun)
                .order_by(Sun2ImportRun.timestamp.desc())
                .limit(25)
            )
        ).scalars().all()
    return templates.TemplateResponse(
        request,
        "sun2_room_stats.html",
        {
            "rows": rows,
            "imports": imports,
            "limit": limit,
            "monthly_totals": summaries["monthly"],
            "yearly_totals": summaries["yearly"],
            "grand_total": summaries["total"],
            "first_date": summaries["first_date"],
            "last_date": summaries["last_date"],
            "total_rows": summaries["total_rows"],
        },
    )


async def get_sun2_session_options(session) -> Dict[str, list[str]]:
    cache_key = "sun2_session_options"
    now_value = datetime.utcnow()
    cached = SUMMARY_CACHE.get(cache_key)
    if cached and cached.get("expires", datetime.min) > now_value:
        return cached["value"]

    def distinct_text(column):
        return (
            select(column)
            .where(column.is_not(None))
            .where(column != "")
            .distinct()
            .order_by(column)
        )

    bed_rows = (
        await session.execute(
            select(Sun2Bed)
            .where(Sun2Bed.room_id.is_not(None))
            .order_by(Sun2Bed.physical_room_number, Sun2Bed.room_id)
        )
    ).scalars().all()
    room_ids = [
        {
            "value": bed.room_id,
            "label": sun2_room_label(bed.room_id, bed.name),
        }
        for bed in bed_rows
        if bed.room_id
    ] or list(SUN2_ROOM_OPTIONS)
    seen_room_ids = set()
    deduped_room_ids = []
    for item in room_ids:
        if item["value"] in seen_room_ids:
            continue
        seen_room_ids.add(item["value"])
        deduped_room_ids.append(item)

    value = {
        "room_ids": deduped_room_ids,
        "rooms": (await session.execute(distinct_text(Sun2TanningSession.room))).scalars().all(),
        "payments": (await session.execute(distinct_text(Sun2TanningSession.payment_method))).scalars().all(),
        "statuses": (await session.execute(distinct_text(Sun2TanningSession.status))).scalars().all(),
        "customers": (await session.execute(distinct_text(Sun2TanningSession.customer_type))).scalars().all(),
    }
    SUMMARY_CACHE[cache_key] = {"expires": now_value + timedelta(minutes=30), "value": value}
    return value


async def get_sun2_session_database_total(session) -> Dict[str, Any]:
    cache_key = "sun2_session_database_total"
    now_value = datetime.utcnow()
    cached = SUMMARY_CACHE.get(cache_key)
    if cached and cached.get("expires", datetime.min) > now_value:
        return cached["value"]
    value = (
        await session.execute(
            select(
                func.count(Sun2TanningSession.id).label("sessions_count"),
                func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                func.count(func.distinct(Sun2TanningSession.sun2_user_id)).label("unique_users_count"),
            )
        )
    ).mappings().first() or {}
    value = dict(value)
    SUMMARY_CACHE[cache_key] = {"expires": now_value + timedelta(minutes=5), "value": value}
    return value


@app.get("/soling/enkeltimer", response_class=HTMLResponse)
async def sun2_sessions_view(
    request: Request,
    limit: int = 50,
    page: int = 1,
    scope: Optional[str] = None,
    sun2_user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    room_id: Optional[str] = None,
    room: Optional[str] = None,
    payment_method: Optional[str] = None,
    status: Optional[str] = None,
    customer_type: Optional[str] = None,
    q: Optional[str] = None,
):
    limit = max(25, min(limit, 1000))
    page = max(1, page)
    active_sun2_user_id = (sun2_user_id or "").strip()
    active_room_id = normalize_room_id(room_id)
    active_room = (room or "").strip()
    active_payment_method = (payment_method or "").strip()
    active_status = (status or "").strip()
    active_customer_type = (customer_type or "").strip()
    active_q = (q or "").strip()
    active_scope = (scope or "recent").strip().lower()
    if active_scope not in {"recent", "all"}:
        active_scope = "recent"
    active_date_from = None
    active_date_to = None
    try:
        active_date_from = date.fromisoformat(date_from) if date_from else None
    except ValueError:
        active_date_from = None
    try:
        active_date_to = date.fromisoformat(date_to) if date_to else None
    except ValueError:
        active_date_to = None
    user_has_filters = any([
        active_sun2_user_id,
        active_date_from,
        active_date_to,
        active_room_id,
        active_room,
        active_payment_method,
        active_status,
        active_customer_type,
        active_q,
    ])
    auto_recent_window = active_scope != "all" and not user_has_filters
    if auto_recent_window:
        active_date_to = datetime.now(LOCAL_TZ).date()
        active_date_from = active_date_to - timedelta(days=119)

    session_filters = []
    if active_sun2_user_id:
        session_filters.append(Sun2TanningSession.sun2_user_id == active_sun2_user_id)
    if active_date_from:
        session_filters.append(Sun2TanningSession.stat_date >= active_date_from)
    if active_date_to:
        session_filters.append(Sun2TanningSession.stat_date <= active_date_to)
    if active_room_id:
        session_filters.append(Sun2TanningSession.room_id == active_room_id)
    if active_room:
        session_filters.append(Sun2TanningSession.room == active_room)
    if active_payment_method:
        session_filters.append(Sun2TanningSession.payment_method == active_payment_method)
    if active_status:
        session_filters.append(Sun2TanningSession.status == active_status)
    if active_customer_type:
        session_filters.append(Sun2TanningSession.customer_type == active_customer_type)
    if active_q:
        like = f"%{active_q.lower()}%"
        q_room_id = normalize_room_id(active_q)
        numeric_match = re.fullmatch(r"\d{1,2}", active_q)
        if numeric_match:
            q_room_id = normalize_room_id(f"rom-{int(active_q):02d}")
        search_terms = [
            func.lower(func.coalesce(Sun2TanningSession.user_name, "")).like(like),
            func.lower(func.coalesce(Sun2TanningSession.user_identifier, "")).like(like),
            func.lower(func.coalesce(Sun2TanningSession.sun2_user_id, "")).like(like),
            func.lower(func.coalesce(Sun2TanningSession.room_id, "")).like(like),
            func.lower(func.coalesce(Sun2TanningSession.room, "")).like(like),
            func.lower(func.coalesce(Sun2TanningSession.source_room_name, "")).like(like),
            func.lower(func.coalesce(Sun2TanningSession.sun2_bed_id, "")).like(like),
            func.lower(func.coalesce(Sun2TanningSession.payment_method, "")).like(like),
            func.lower(func.coalesce(Sun2TanningSession.status, "")).like(like),
            func.lower(func.coalesce(Sun2TanningSession.source_file, "")).like(like),
        ]
        if q_room_id:
            search_terms.append(Sun2TanningSession.room_id == q_room_id)
        session_filters.append(or_(
            *search_terms,
        ))

    async with async_session() as session:
        options = await get_sun2_session_options(session)
        room_id_options = options["room_ids"]
        room_options = options["rooms"]
        payment_options = options["payments"]
        status_options = options["statuses"]
        customer_options = options["customers"]

        rows_query = select(Sun2TanningSession)
        if session_filters:
            rows_query = rows_query.where(*session_filters)
        offset = (page - 1) * limit
        rows = (
            await session.execute(
                rows_query
                .order_by(Sun2TanningSession.started_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
        imports = (
            await session.execute(
                select(Sun2SessionImportRun)
                .order_by(Sun2SessionImportRun.timestamp.desc())
                .limit(10)
            )
        ).scalars().all()
        analytics_cache_parts = {
            "scope": active_scope,
            "sun2_user_id": active_sun2_user_id,
            "date_from": active_date_from.isoformat() if active_date_from else "",
            "date_to": active_date_to.isoformat() if active_date_to else "",
            "room_id": active_room_id or "",
            "room": active_room,
            "payment_method": active_payment_method,
            "status": active_status,
            "customer_type": active_customer_type,
            "q": active_q,
        }
        analytics_cache_key = "sun2_sessions:" + hashlib.sha1(
            json.dumps(analytics_cache_parts, sort_keys=True).encode("utf-8")
        ).hexdigest()
        now_value = datetime.utcnow()
        cached_analytics = SUMMARY_CACHE.get(analytics_cache_key)
        if cached_analytics and cached_analytics.get("expires", datetime.min) > now_value:
            analytics = cached_analytics["value"]
            total = analytics["total"]
            database_total = analytics["database_total"]
            total_count = int((total or {}).get("sessions_count") or 0)
            monthly = analytics.get("monthly", [])
            chart_granularity = analytics["chart_granularity"]
            daily = analytics["daily"]
            hourly_rows = analytics["hourly_rows"]
            top_rooms = analytics["top_rooms"]
            top_users = analytics["top_users"]
            payment_breakdown = analytics["payment_breakdown"]
            status_breakdown = analytics["status_breakdown"]
        else:
            total_query = select(
                func.count(Sun2TanningSession.id).label("sessions_count"),
                func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                func.coalesce(func.avg(Sun2TanningSession.duration_minutes), 0).label("avg_duration_minutes"),
                func.coalesce(func.avg(Sun2TanningSession.paid_amount_kr), 0).label("avg_paid_amount_kr"),
                func.count(func.distinct(Sun2TanningSession.sun2_user_id)).label("unique_users_count"),
                func.min(Sun2TanningSession.started_at).label("first_at"),
                func.max(Sun2TanningSession.started_at).label("last_at"),
            )
            if session_filters:
                total_query = total_query.where(*session_filters)
            total = dict((await session.execute(total_query)).mappings().first() or {})
            database_total = total
            if session_filters:
                database_total = await get_sun2_session_database_total(session)
            total_count = int((total or {}).get("sessions_count") or 0)
            monthly = []

            chart_span_days = None
            if active_date_from and active_date_to:
                chart_span_days = (active_date_to - active_date_from).days + 1
            chart_granularity = "month" if (active_scope == "all" or (chart_span_days and chart_span_days > 370)) else "day"
            if chart_granularity == "month":
                chart_year_part = func.extract("year", Sun2TanningSession.stat_date)
                chart_month_part = func.extract("month", Sun2TanningSession.stat_date)
                day_query = (
                    select(
                        chart_year_part.label("year"),
                        chart_month_part.label("month"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                    )
                    .group_by(chart_year_part, chart_month_part)
                    .order_by(chart_year_part.asc(), chart_month_part.asc())
                )
            else:
                day_query = (
                    select(
                        Sun2TanningSession.stat_date.label("day"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                    )
                    .group_by(Sun2TanningSession.stat_date)
                    .order_by(Sun2TanningSession.stat_date.asc())
                )
            if session_filters:
                day_query = day_query.where(*session_filters)
            daily = [dict(item) for item in (await session.execute(day_query)).mappings().all()]

            hour_part = func.extract("hour", Sun2TanningSession.started_at)
            hourly_query = (
                select(
                    hour_part.label("hour"),
                    func.count(Sun2TanningSession.id).label("sessions_count"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                )
                .group_by(hour_part)
                .order_by(hour_part.asc())
            )
            if session_filters:
                hourly_query = hourly_query.where(*session_filters)
            hourly_rows = [dict(item) for item in (await session.execute(hourly_query)).mappings().all()]

            top_rooms_query = (
                select(
                    Sun2TanningSession.room_id.label("room_id"),
                    func.max(Sun2TanningSession.room).label("source_room_name"),
                    func.count(Sun2TanningSession.id).label("sessions_count"),
                    func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                )
                .group_by(Sun2TanningSession.room_id)
                .order_by(func.count(Sun2TanningSession.id).desc())
                .limit(10)
            )
            if session_filters:
                top_rooms_query = top_rooms_query.where(*session_filters)
            top_rooms = [
                {
                    **dict(item),
                    "label": sun2_room_label(item.get("room_id"), item.get("source_room_name")),
                }
                for item in (await session.execute(top_rooms_query)).mappings().all()
            ]

            top_users_query = (
                select(
                    Sun2TanningSession.sun2_user_id.label("sun2_user_id"),
                    func.max(Sun2TanningSession.user_name).label("user_name"),
                    func.count(Sun2TanningSession.id).label("sessions_count"),
                    func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                    func.max(Sun2TanningSession.started_at).label("last_at"),
                )
                .where(Sun2TanningSession.sun2_user_id.is_not(None))
                .where(Sun2TanningSession.sun2_user_id != "")
                .group_by(Sun2TanningSession.sun2_user_id)
                .order_by(func.count(Sun2TanningSession.id).desc())
                .limit(10)
            )
            if session_filters:
                top_users_query = top_users_query.where(*session_filters)
            top_users = [dict(item) for item in (await session.execute(top_users_query)).mappings().all()]

            payment_query = (
                select(
                    Sun2TanningSession.payment_method.label("label"),
                    func.count(Sun2TanningSession.id).label("sessions_count"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                )
                .group_by(Sun2TanningSession.payment_method)
                .order_by(func.count(Sun2TanningSession.id).desc())
                .limit(8)
            )
            if session_filters:
                payment_query = payment_query.where(*session_filters)
            payment_breakdown = [dict(item) for item in (await session.execute(payment_query)).mappings().all()]

            status_query = (
                select(
                    Sun2TanningSession.status.label("label"),
                    func.count(Sun2TanningSession.id).label("sessions_count"),
                )
                .group_by(Sun2TanningSession.status)
                .order_by(func.count(Sun2TanningSession.id).desc())
                .limit(8)
            )
            if session_filters:
                status_query = status_query.where(*session_filters)
            status_breakdown = [dict(item) for item in (await session.execute(status_query)).mappings().all()]

            SUMMARY_CACHE[analytics_cache_key] = {
                "expires": now_value + SUMMARY_CACHE_TTL,
                "value": {
                    "total": total,
                    "database_total": database_total,
                    "monthly": monthly,
                    "chart_granularity": chart_granularity,
                    "daily": daily,
                    "hourly_rows": hourly_rows,
                    "top_rooms": top_rooms,
                    "top_users": top_users,
                    "payment_breakdown": payment_breakdown,
                    "status_breakdown": status_breakdown,
                },
            }
        page_count = max(1, math.ceil(total_count / limit))
        if page > page_count:
            page = page_count
            offset = (page - 1) * limit
            rows = (
                await session.execute(
                    rows_query
                    .order_by(Sun2TanningSession.started_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
            ).scalars().all()

    filter_values = {
        "limit": limit,
        "page": page,
        "scope": active_scope,
        "sun2_user_id": active_sun2_user_id,
        "date_from": active_date_from.isoformat() if active_date_from else "",
        "date_to": active_date_to.isoformat() if active_date_to else "",
        "room_id": active_room_id or "",
        "room": active_room,
        "payment_method": active_payment_method,
        "status": active_status,
        "customer_type": active_customer_type,
        "q": active_q,
    }
    def query_url(**updates):
        params = dict(filter_values)
        params.update(updates)
        if params.get("scope") == "recent" and not params.get("date_from") and not params.get("date_to"):
            params.pop("scope", None)
        params = {key: value for key, value in params.items() if value not in (None, "", 0)}
        return f"/soling/enkeltimer?{urlencode(params)}"

    hourly_lookup = {int(item.get("hour") or 0): item for item in hourly_rows}
    hourly = [
        {
            "hour": hour,
            "label": f"{hour:02d}",
            "sessions_count": int((hourly_lookup.get(hour) or {}).get("sessions_count") or 0),
            "paid_amount_kr": float((hourly_lookup.get(hour) or {}).get("paid_amount_kr") or 0),
        }
        for hour in range(24)
    ]
    peak_hour = max(hourly, key=lambda item: item["sessions_count"], default=None)
    best_day = max(daily, key=lambda item: item.get("sessions_count") or 0, default=None)
    daily_chart = [
        {
            "date": (
                item.get("day").isoformat()
                if chart_granularity == "day" and item.get("day")
                else f"{int(item.get('year')):04d}-{int(item.get('month')):02d}-01"
            ),
            "label": (
                item.get("day").strftime("%d.%m.%Y")
                if chart_granularity == "day" and item.get("day")
                else f"{int(item.get('month')):02d}.{int(item.get('year')):04d}"
            ),
            "sessions_count": int(item.get("sessions_count") or 0),
            "duration_hours": round(float(item.get("duration_minutes") or 0) / 60, 2),
            "paid_amount_kr": round(float(item.get("paid_amount_kr") or 0), 2),
        }
        for item in daily
    ]
    active_filter_count = sum(1 for key in ["sun2_user_id", "room_id", "room", "payment_method", "status", "customer_type", "q"] if filter_values.get(key))
    if user_has_filters and (filter_values.get("date_from") or filter_values.get("date_to")):
        active_filter_count += 1
    pagination = {
        "page": page,
        "page_count": page_count,
        "limit": limit,
        "total_count": total_count,
        "from_row": min(total_count, offset + 1) if total_count else 0,
        "to_row": min(total_count, offset + len(rows)),
        "prev_url": query_url(page=max(1, page - 1)) if page > 1 else "",
        "next_url": query_url(page=min(page_count, page + 1)) if page < page_count else "",
        "pages": [
            {"number": number, "url": query_url(page=number), "active": number == page}
            for number in range(max(1, page - 2), min(page_count, page + 2) + 1)
        ],
    }
    return templates.TemplateResponse(
        request,
        "sun2_sessions.html",
        {
            "rows": rows,
            "imports": imports,
            "limit": limit,
            "total": total or {},
            "database_total": database_total or {},
            "monthly": monthly,
            "daily_chart": daily_chart,
            "chart_granularity": chart_granularity,
            "auto_recent_window": auto_recent_window,
            "hourly": hourly,
            "peak_hour": peak_hour,
            "best_day": best_day,
            "top_rooms": top_rooms,
            "top_users": top_users,
            "payment_breakdown": payment_breakdown,
            "status_breakdown": status_breakdown,
            "room_id_options": room_id_options,
            "room_options": room_options,
            "payment_options": payment_options,
            "status_options": status_options,
            "customer_options": customer_options,
            "filters": filter_values,
            "active_filter_count": active_filter_count,
            "pagination": pagination,
            "query_url": query_url,
            "active_sun2_user_id": active_sun2_user_id,
        },
    )


@app.get("/soling/dagslinje", response_class=HTMLResponse)
async def sun2_day_timeline_view(request: Request, day: Optional[str] = None):
    try:
        selected = date.fromisoformat(day) if day else datetime.now(LOCAL_TZ).date()
    except ValueError:
        selected = datetime.now(LOCAL_TZ).date()

    day_start = datetime.combine(selected, time.min)
    day_end = day_start + timedelta(days=1)
    visible_room_numbers = list(range(1, 10)) + [11, 12, 13]
    visible_room_ids = [f"rom-{number:02d}" for number in visible_room_numbers]
    room_lookup = {
        room_id: {
            "room_id": room_id,
            "label": f"Rom {int(room_id.rsplit('-', 1)[-1])}",
            "sessions": [],
            "count": 0,
            "minutes": 0.0,
            "paid": 0.0,
        }
        for room_id in visible_room_ids
    }

    async with async_session() as session:
        rows = (
            await session.execute(
                select(Sun2TanningSession)
                .where(Sun2TanningSession.stat_date == selected)
                .where(Sun2TanningSession.room_id.in_(visible_room_ids))
                .order_by(Sun2TanningSession.room_id.asc(), Sun2TanningSession.started_at.asc())
            )
        ).scalars().all()
        energy_rows = (
            await session.execute(
                select(
                    EnergyHourlyConsumption.hour.label("hour"),
                    func.coalesce(func.sum(EnergyHourlyConsumption.consumption_kwh), 0).label("consumption_kwh"),
                    func.coalesce(func.sum(EnergyHourlyConsumption.production_kwh), 0).label("production_kwh"),
                    func.count(EnergyHourlyConsumption.id).label("rows_count"),
                )
                .where(EnergyHourlyConsumption.stat_date == selected)
                .group_by(EnergyHourlyConsumption.hour)
                .order_by(EnergyHourlyConsumption.hour.asc())
            )
        ).mappings().all()

    totals = {"sessions_count": 0, "duration_minutes": 0.0, "duration_hours": 0.0, "paid_amount_kr": 0.0}
    aggregate_sessions = []
    for row in rows:
        room_id = normalize_room_id(row.room_id)
        if room_id not in room_lookup or not row.started_at:
            continue
        start_at = row.started_at
        end_at = row.ended_at
        if getattr(start_at, "tzinfo", None):
            start_at = start_at.astimezone(LOCAL_TZ).replace(tzinfo=None)
        if end_at and getattr(end_at, "tzinfo", None):
            end_at = end_at.astimezone(LOCAL_TZ).replace(tzinfo=None)
        if not end_at:
            end_at = start_at + timedelta(minutes=float(row.duration_minutes or 15))
        if end_at <= start_at:
            end_at = start_at + timedelta(minutes=max(1.0, float(row.duration_minutes or 1)))

        clamped_start = max(day_start, min(day_end, start_at))
        clamped_end = max(clamped_start, min(day_end, end_at))
        duration_minutes = max(0.0, (clamped_end - clamped_start).total_seconds() / 60)
        if duration_minutes <= 0:
            continue

        left = round(((clamped_start - day_start).total_seconds() / 86400) * 100, 4)
        width = max(0.18, round(((clamped_end - clamped_start).total_seconds() / 86400) * 100, 4))
        customer_type = (row.customer_type or "").lower()
        kind = "standard"
        if "ikke" in customer_type:
            kind = "no-member"
        elif "medlem" in customer_type:
            kind = "member"
        paid = float(row.paid_amount_kr or 0)
        label = f"{start_at:%H:%M}"
        title_parts = [
            f"{room_lookup[room_id]['label']} {start_at:%H:%M}-{end_at:%H:%M}",
            f"{duration_minutes:.0f} min",
        ]
        if row.user_name:
            title_parts.append(str(row.user_name))
        if paid:
            title_parts.append(f"{paid:.0f} kr")
        item = {
            "left": left,
            "width": width,
            "label": label,
            "title": " | ".join(title_parts),
            "kind": kind,
            "href": f"/soling/enkeltimer?date_from={selected.isoformat()}&date_to={selected.isoformat()}&room_id={room_id}",
        }
        room_lookup[room_id]["sessions"].append(item)
        aggregate_sessions.append({**item, "label": room_lookup[room_id]["label"]})
        room_lookup[room_id]["count"] += 1
        room_lookup[room_id]["minutes"] += duration_minutes
        room_lookup[room_id]["paid"] += paid
        totals["sessions_count"] += 1
        totals["duration_minutes"] += duration_minutes
        totals["paid_amount_kr"] += paid

    totals["duration_hours"] = round(totals["duration_minutes"] / 60, 2)
    rooms = [room_lookup[room_id] for room_id in visible_room_ids]
    busiest_room = max(rooms, key=lambda item: item["count"], default=None)
    if busiest_room and not busiest_room["count"]:
        busiest_room = None
    today = datetime.now(LOCAL_TZ).date()
    now_marker = None
    if selected == today:
        now_local = datetime.now(LOCAL_TZ).replace(tzinfo=None)
        now_marker = round(max(0, min(100, ((now_local - day_start).total_seconds() / 86400) * 100)), 3)
    ticks = [{"label": f"{hour:02d}", "left": round(hour / 24 * 100, 4)} for hour in range(0, 25, 2)]
    energy_lookup = {int(item.get("hour") or 0): item for item in energy_rows}
    energy_hours = []
    max_energy_kwh = max([float((item.get("consumption_kwh") or 0)) for item in energy_rows] or [0.0])
    total_energy_kwh = sum(float((item.get("consumption_kwh") or 0)) for item in energy_rows)
    for hour in range(24):
        item = energy_lookup.get(hour) or {}
        consumption = float(item.get("consumption_kwh") or 0)
        production = float(item.get("production_kwh") or 0)
        energy_hours.append(
            {
                "hour": hour,
                "left": round(hour / 24 * 100, 4),
                "width": round(100 / 24, 4),
                "height": round((consumption / max_energy_kwh) * 100, 2) if max_energy_kwh else 0,
                "consumption_kwh": consumption,
                "production_kwh": production,
                "title": f"{hour:02d}:00-{(hour + 1) % 24:02d}:00 | {consumption:.2f} kWh",
            }
        )
    peak_energy_hour = max(energy_hours, key=lambda item: item["consumption_kwh"], default=None)
    if peak_energy_hour and not peak_energy_hour["consumption_kwh"]:
        peak_energy_hour = None
    energy_summary = {
        "hours_count": len([item for item in energy_hours if item["consumption_kwh"] > 0]),
        "total_kwh": total_energy_kwh,
        "max_kwh": max_energy_kwh,
        "peak_hour": peak_energy_hour,
    }

    return templates.TemplateResponse(
        request,
        "sun2_day_timeline.html",
        {
            "selected_day": selected.isoformat(),
            "selected_day_label": selected.strftime("%d.%m.%Y"),
            "prev_day": (selected - timedelta(days=1)).isoformat(),
            "next_day": (selected + timedelta(days=1)).isoformat(),
            "rooms": rooms,
            "aggregate_sessions": aggregate_sessions,
            "totals": totals,
            "busiest_room": busiest_room,
            "ticks": ticks,
            "now_marker": now_marker,
            "energy_hours": energy_hours,
            "energy_summary": energy_summary,
        },
    )


@app.get("/soling/senger", response_class=HTMLResponse)
async def sun2_beds_view(request: Request):
    async with async_session() as session:
        beds = (
            await session.execute(
                select(Sun2Bed).order_by(Sun2Bed.physical_room_number, Sun2Bed.room_id, Sun2Bed.name)
            )
        ).scalars().all()
        totals_rows = (
            await session.execute(
                select(
                    Sun2TanningSession.room_id.label("room_id"),
                    func.count(Sun2TanningSession.id).label("sessions_count"),
                    func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                    func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                    func.max(Sun2TanningSession.started_at).label("last_at"),
                )
                .group_by(Sun2TanningSession.room_id)
            )
        ).mappings().all()
    totals = {item["room_id"]: item for item in totals_rows}
    return templates.TemplateResponse(
        request,
        "sun2_beds.html",
        {
            "beds": beds,
            "totals": totals,
            "room_label": sun2_room_label,
        },
    )


@app.get("/soling/medlemmer", response_class=HTMLResponse)
async def sun2_members_view(
    request: Request,
    q: str = "",
    customer_type: str = "",
    status: str = "",
    limit: int = 250,
):
    search = (q or "").strip()
    active_customer_type = (customer_type or "").strip()
    active_status = (status or "").strip()
    limit = max(25, min(limit, 1000))
    filters = []
    if search:
        like = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(func.coalesce(Sun2Member.sun2_user_id, "")).like(like),
                func.lower(func.coalesce(Sun2Member.name, "")).like(like),
                func.lower(func.coalesce(Sun2Member.display_name, "")).like(like),
                func.lower(func.coalesce(Sun2Member.initials, "")).like(like),
                func.lower(func.coalesce(Sun2Member.email, "")).like(like),
                func.lower(func.coalesce(Sun2Member.phone, "")).like(like),
            )
        )
    if active_customer_type:
        filters.append(Sun2Member.customer_type == active_customer_type)
    if active_status:
        filters.append(Sun2Member.status == active_status)

    async with async_session() as session:
        rows_query = select(Sun2Member)
        for condition in filters:
            rows_query = rows_query.where(condition)
        members = (
            await session.execute(
                rows_query
                .order_by(Sun2Member.imported_at.desc(), Sun2Member.name, Sun2Member.display_name, Sun2Member.sun2_user_id)
                .limit(limit)
            )
        ).scalars().all()
        member_ids = [member.sun2_user_id for member in members if member.sun2_user_id]
        stats = {}
        if member_ids:
            stats_rows = (
                await session.execute(
                    select(
                        Sun2TanningSession.sun2_user_id.label("sun2_user_id"),
                        func.count(Sun2TanningSession.id).label("sessions_count"),
                        func.coalesce(func.sum(Sun2TanningSession.duration_minutes), 0).label("duration_minutes"),
                        func.coalesce(func.sum(Sun2TanningSession.paid_amount_kr), 0).label("paid_amount_kr"),
                        func.max(Sun2TanningSession.started_at).label("last_session_at"),
                        func.max(Sun2TanningSession.user_name).label("session_name"),
                    )
                    .where(Sun2TanningSession.sun2_user_id.in_(member_ids))
                    .group_by(Sun2TanningSession.sun2_user_id)
                )
            ).mappings().all()
            stats = {item["sun2_user_id"]: item for item in stats_rows}
        totals = (
            await session.execute(
                select(
                    func.count(Sun2Member.id).label("members_count"),
                    func.count(Sun2Member.name).label("named_count"),
                    func.count(Sun2Member.email).label("email_count"),
                    func.count(Sun2Member.phone).label("phone_count"),
                    func.max(Sun2Member.imported_at).label("last_imported_at"),
                )
            )
        ).mappings().first() or {}
        customer_options = (
            await session.execute(
                select(Sun2Member.customer_type).where(Sun2Member.customer_type.is_not(None)).distinct().order_by(Sun2Member.customer_type)
            )
        ).scalars().all()
        status_options = (
            await session.execute(
                select(Sun2Member.status).where(Sun2Member.status.is_not(None)).distinct().order_by(Sun2Member.status)
            )
        ).scalars().all()
        known_from_sessions = (
            await session.execute(
                select(func.count(func.distinct(Sun2TanningSession.sun2_user_id)))
                .where(Sun2TanningSession.sun2_user_id.is_not(None))
                .where(Sun2TanningSession.sun2_user_id != "")
            )
        ).scalar_one()
    return templates.TemplateResponse(
        request,
        "sun2_members.html",
        {
            "members": members,
            "stats": stats,
            "totals": totals,
            "known_from_sessions": known_from_sessions,
            "filters": {
                "q": search,
                "customer_type": active_customer_type,
                "status": active_status,
                "limit": limit,
            },
            "customer_options": customer_options,
            "status_options": status_options,
        },
    )


@app.get("/api/sun2/room-stats/json")
async def sun2_room_stats_json(limit: int = 300):
    limit = max(1, min(limit, 5000))
    async with async_session() as session:
        summaries = await get_sun2_summaries(session)
        rows = (
            await session.execute(
                select(Sun2RoomDailyStat)
                .order_by(Sun2RoomDailyStat.stat_date.desc(), Sun2RoomDailyStat.room)
                .limit(limit)
            )
        ).scalars().all()
        imports = (
            await session.execute(
                select(Sun2ImportRun)
                .order_by(Sun2ImportRun.timestamp.desc())
                .limit(min(limit, 500))
            )
        ).scalars().all()
    return {
        "rows": [row_to_dict(row, SUN2_ROOM_COLUMNS) for row in rows],
        "imports": [row_to_dict(row, SUN2_IMPORT_COLUMNS) for row in imports],
        "daily_totals": summaries["daily"],
        "monthly_totals": summaries["monthly"],
        "yearly_totals": summaries["yearly"],
        "top_days": summaries["top_days"],
        "top_months": summaries["top_months"],
        "top_days_by_count": summaries["top_days_by_count"],
        "top_months_by_count": summaries["top_months_by_count"],
        "grand_total": summaries["total"],
        "first_date": summaries["first_date"],
        "last_date": summaries["last_date"],
        "total_rows": summaries["total_rows"],
    }


@app.get("/api/sun2/beds/json")
async def sun2_beds_json():
    async with async_session() as session:
        rows = (
            await session.execute(
                select(Sun2Bed).order_by(Sun2Bed.physical_room_number, Sun2Bed.room_id, Sun2Bed.name)
            )
        ).scalars().all()
    return {"rows": [row_to_dict(row, SUN2_BED_COLUMNS) for row in rows]}


@app.get("/api/sun2/members/json")
async def sun2_members_json(limit: int = 300, q: Optional[str] = None):
    limit = max(1, min(limit, 5000))
    search = (q or "").strip()
    async with async_session() as session:
        rows_query = select(Sun2Member)
        if search:
            like = f"%{search.lower()}%"
            rows_query = rows_query.where(
                or_(
                    func.lower(func.coalesce(Sun2Member.sun2_user_id, "")).like(like),
                    func.lower(func.coalesce(Sun2Member.name, "")).like(like),
                    func.lower(func.coalesce(Sun2Member.display_name, "")).like(like),
                    func.lower(func.coalesce(Sun2Member.initials, "")).like(like),
                    func.lower(func.coalesce(Sun2Member.email, "")).like(like),
                    func.lower(func.coalesce(Sun2Member.phone, "")).like(like),
                )
            )
        rows = (
            await session.execute(
                rows_query
                .order_by(Sun2Member.imported_at.desc(), Sun2Member.sun2_user_id)
                .limit(limit)
            )
        ).scalars().all()
    return {"rows": [row_to_dict(row, SUN2_MEMBER_COLUMNS) for row in rows], "q": search or None}


@app.get("/api/sun2/sessions/json")
async def sun2_sessions_json(limit: int = 300, sun2_user_id: Optional[str] = None):
    limit = max(1, min(limit, 5000))
    active_sun2_user_id = (sun2_user_id or "").strip()
    async with async_session() as session:
        rows_query = select(Sun2TanningSession)
        if active_sun2_user_id:
            rows_query = rows_query.where(Sun2TanningSession.sun2_user_id == active_sun2_user_id)
        rows = (
            await session.execute(
                rows_query
                .order_by(Sun2TanningSession.started_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        imports = (
            await session.execute(
                select(Sun2SessionImportRun)
                .order_by(Sun2SessionImportRun.timestamp.desc())
                .limit(min(limit, 500))
            )
        ).scalars().all()
    return {
        "rows": [row_to_dict(row, SUN2_SESSION_COLUMNS) for row in rows],
        "imports": [row_to_dict(row, SUN2_SESSION_IMPORT_COLUMNS) for row in imports],
        "sun2_user_id": active_sun2_user_id or None,
    }


@app.get("/energi/elvia", response_class=HTMLResponse)
async def energy_elvia_view(request: Request):
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


@app.post("/energi/elvia", response_class=HTMLResponse)
async def energy_elvia_upload(request: Request, background_tasks: BackgroundTasks):
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


@app.get("/api/energi/elvia/json")
async def energy_elvia_json(limit: int = 300):
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


@app.get("/renhold/oversikt", response_class=HTMLResponse)
async def cleaning_overview(request: Request):
    async with async_session() as session:
        robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
        latest_status = {}
        latest_jobs = {}
        next_schedules = {}
        robot_duids = [robot.duid for robot in robots]
        if robot_duids:
            latest_status_subq = (
                select(
                    RoborockStatusSample.robot_duid.label("robot_duid"),
                    func.max(RoborockStatusSample.timestamp).label("latest_at"),
                )
                .where(RoborockStatusSample.robot_duid.in_(robot_duids))
                .group_by(RoborockStatusSample.robot_duid)
                .subquery()
            )
            status_rows = (
                await session.execute(
                    select(RoborockStatusSample).join(
                        latest_status_subq,
                        (RoborockStatusSample.robot_duid == latest_status_subq.c.robot_duid)
                        & (RoborockStatusSample.timestamp == latest_status_subq.c.latest_at),
                    )
                )
            ).scalars().all()
            latest_status = {row.robot_duid: row for row in status_rows}

            latest_job_subq = (
                select(
                    RoborockCleanJob.robot_duid.label("robot_duid"),
                    func.max(RoborockCleanJob.begin_at).label("latest_at"),
                )
                .where(RoborockCleanJob.robot_duid.in_(robot_duids))
                .group_by(RoborockCleanJob.robot_duid)
                .subquery()
            )
            job_rows = (
                await session.execute(
                    select(RoborockCleanJob).join(
                        latest_job_subq,
                        (RoborockCleanJob.robot_duid == latest_job_subq.c.robot_duid)
                        & (RoborockCleanJob.begin_at == latest_job_subq.c.latest_at),
                    )
                )
            ).scalars().all()
            latest_jobs = {row.robot_duid: row for row in job_rows}

            schedule_rows = (
                await session.execute(
                    select(RoborockSchedule)
                    .where(RoborockSchedule.robot_duid.in_(robot_duids))
                    .where(RoborockSchedule.enabled == True)
                )
            ).scalars().all()
            schedules_by_robot: Dict[str, list[RoborockSchedule]] = {}
            for schedule in schedule_rows:
                schedules_by_robot.setdefault(schedule.robot_duid, []).append(schedule)
            next_schedules = {
                duid: min(schedules, key=roborock_next_schedule_score)
                for duid, schedules in schedules_by_robot.items()
                if schedules
            }
    return templates.TemplateResponse(
        request,
        "cleaning_overview.html",
        {
            "robots": robots,
            "latest_status": latest_status,
            "latest_jobs": latest_jobs,
            "next_schedules": next_schedules,
        },
    )


@app.get("/renhold/robot/{duid}", response_class=HTMLResponse)
async def cleaning_robot_detail(request: Request, duid: str):
    async with async_session() as session:
        robot = (await session.execute(select(RoborockRobot).where(RoborockRobot.duid == duid))).scalars().first()
        if not robot:
            return JSONResponse({"detail": "Ukjent robot"}, status_code=404)
        statuses = (
            await session.execute(
                select(RoborockStatusSample)
                .where(RoborockStatusSample.robot_duid == duid)
                .order_by(RoborockStatusSample.timestamp.desc())
                .limit(100)
            )
        ).scalars().all()
        jobs = (
            await session.execute(
                select(RoborockCleanJob)
                .where(RoborockCleanJob.robot_duid == duid)
                .order_by(RoborockCleanJob.begin_at.desc())
                .limit(50)
            )
        ).scalars().all()
        schedules = (
            await session.execute(
                select(RoborockSchedule)
                .where(RoborockSchedule.robot_duid == duid)
                .order_by(RoborockSchedule.cron)
            )
        ).scalars().all()
        consumables = (
            await session.execute(
                select(RoborockConsumableSnapshot)
                .where(RoborockConsumableSnapshot.robot_duid == duid)
                .order_by(RoborockConsumableSnapshot.timestamp.desc())
                .limit(1)
            )
        ).scalars().first()
        latest_map = (
            await session.execute(
                select(RoborockMapSnapshot)
                .where(RoborockMapSnapshot.robot_duid == duid)
                .order_by(RoborockMapSnapshot.timestamp.desc())
                .limit(1)
            )
        ).scalars().first()
    return templates.TemplateResponse(
        request,
        "cleaning_robot.html",
        {
            "robot": robot,
            "latest_status": statuses[0] if statuses else None,
            "statuses": statuses,
            "jobs": jobs,
            "schedules": schedules,
            "consumables": consumables,
            "latest_map": latest_map,
        },
    )


@app.get("/renhold/json")
async def cleaning_json(limit: int = 100):
    limit = max(1, min(limit, 1000))
    async with async_session() as session:
        robots = (await session.execute(select(RoborockRobot).order_by(RoborockRobot.name))).scalars().all()
        jobs = (await session.execute(select(RoborockCleanJob).order_by(RoborockCleanJob.begin_at.desc()).limit(limit))).scalars().all()
        statuses = (await session.execute(select(RoborockStatusSample).order_by(RoborockStatusSample.timestamp.desc()).limit(limit))).scalars().all()
    return {
        "robots": [row_to_dict(row, ROBOROCK_ROBOT_COLUMNS) for row in robots],
        "jobs": [row_to_dict(row, ROBOROCK_JOB_COLUMNS) for row in jobs],
        "statuses": [row_to_dict(row, ROBOROCK_STATUS_COLUMNS) for row in statuses],
    }


@app.get("/lys/hendelser", response_class=HTMLResponse)
async def lights_view(
    request: Request,
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_key: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 300,
):
    rows, limit = await fetch_rows(OutdoorLightEvent, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, limit)
    filters = {"event_type": event_type or "", "action": action or "", "device_key": device_key or "", "device_id": device_id or "", "mode": mode or "", "source_contains": source_contains or "", "from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "lights.html", {"rows": rows, "filters": filters})


@app.get("/lights/json")
async def lights_json(
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_key: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(OutdoorLightEvent, event_type, action, device_key, device_id, mode, source_contains, from_text, to_text, limit)
    return {"count": len(rows), "rows": [row_to_dict(row, LIGHT_COLUMNS) for row in rows]}


@app.get("/lights/download")
async def lights_download(
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_key: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(OutdoorLightEvent, LIGHT_COLUMNS, "utelys_events.csv", event_type, action, device_key, device_id, mode, source_contains, from_text, to_text)


@app.get("/lights/samples/json")
async def light_samples_json(
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(OutdoorLightSample, None, None, None, None, mode, None, from_text, to_text, limit)
    return {"count": len(rows), "rows": [row_to_dict(row, LIGHT_SAMPLE_COLUMNS) for row in rows]}


@app.get("/lys/lux-logging", response_class=HTMLResponse)
async def light_samples_view(
    request: Request,
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 200,
):
    rows, limit = await fetch_rows(OutdoorLightSample, None, None, None, None, mode, None, from_text, to_text, limit)
    filters = {"mode": mode or "", "from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "light_samples.html", {"rows": rows, "filters": filters})


@app.get("/lights/samples/download")
async def light_samples_download(
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(OutdoorLightSample, LIGHT_SAMPLE_COLUMNS, "utelys_samples.csv", None, None, None, None, mode, None, from_text, to_text)


@app.get("/ventilasjon/hendelser", response_class=HTMLResponse)
async def ventilation_view(
    request: Request,
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_key: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 300,
):
    rows, limit = await fetch_rows(VentilationEvent, "fan_change", action, device_key, device_id, mode, source_contains, from_text, to_text, limit)
    filters = {"event_type": "fan_change", "action": action or "", "device_key": device_key or "", "device_id": device_id or "", "mode": mode or "", "source_contains": source_contains or "", "from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "ventilation.html", {"rows": rows, "filters": filters})


@app.get("/ventilation/json")
async def ventilation_json(
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_key: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(VentilationEvent, "fan_change", action, device_key, device_id, mode, source_contains, from_text, to_text, limit)
    return {"count": len(rows), "rows": [row_to_dict(row, VENT_COLUMNS) for row in rows]}


@app.get("/ventilation/download")
async def ventilation_download(
    event_type: Optional[str] = None,
    action: Optional[str] = None,
    device_key: Optional[str] = None,
    device_id: Optional[int] = None,
    mode: Optional[str] = None,
    source_contains: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(VentilationEvent, VENT_COLUMNS, "ventilasjon_events.csv", "fan_change", action, device_key, device_id, mode, source_contains, from_text, to_text)


@app.get("/ventilasjon/temp-logg", response_class=HTMLResponse)
async def ventilation_samples_view(
    request: Request,
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 200,
):
    rows, limit = await fetch_rows(VentilationSample, None, None, None, None, mode, None, from_text, to_text, limit)
    filters = {"mode": mode or "", "from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "ventilation_samples.html", {"rows": rows, "filters": filters})


@app.get("/ventilation/samples/json")
async def ventilation_samples_json(
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(VentilationSample, None, None, None, None, mode, None, from_text, to_text, limit)
    return {"count": len(rows), "rows": [row_to_dict(row, VENT_SAMPLE_COLUMNS) for row in rows]}


@app.get("/ventilation/samples/download")
async def ventilation_samples_download(
    mode: Optional[str] = None,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(VentilationSample, VENT_SAMPLE_COLUMNS, "ventilasjon_samples.csv", None, None, None, None, mode, None, from_text, to_text)


@app.get("/ventilasjon/yr-logg", response_class=HTMLResponse)
async def yr_samples_view(
    request: Request,
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 500,
):
    rows, limit = await fetch_rows(YrForecastSample, None, None, None, None, None, None, from_text, to_text, limit, time_basis="utc")
    filters = {"from": from_text or "", "to": to_text or "", "limit": limit}
    return templates.TemplateResponse(request, "yr_samples.html", {"rows": rows, "filters": filters})


@app.get("/yr/samples/json")
async def yr_samples_json(
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
    limit: int = 1000,
):
    rows, _ = await fetch_rows(YrForecastSample, None, None, None, None, None, None, from_text, to_text, limit, time_basis="utc")
    return {"count": len(rows), "rows": [row_to_dict(row, YR_SAMPLE_COLUMNS) for row in rows]}


@app.get("/yr/samples/download")
async def yr_samples_download(
    from_text: Optional[str] = Query(default=None, alias="from"),
    to_text: Optional[str] = Query(default=None, alias="to"),
):
    return await csv_response(YrForecastSample, YR_SAMPLE_COLUMNS, "yr_forecast_samples.csv", None, None, None, None, None, None, from_text, to_text, time_basis="utc")


@app.get("/download")
@app.get("/events/download")
async def generic_download():
    return await csv_response(GenericEvent, GENERIC_COLUMNS, "event_data.csv", None, None, None, None, None, None, None, None)


@app.get("/events/json")
async def events_json(limit: int = 1000):
    limit = max(1, min(limit, 10000))
    async with async_session() as session:
        result = await session.execute(select(GenericEvent).order_by(GenericEvent.timestamp.desc()).limit(limit))
        rows = result.scalars().all()
    return {"count": len(rows), "rows": [row_to_dict(row, GENERIC_COLUMNS) for row in rows]}
