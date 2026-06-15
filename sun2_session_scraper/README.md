# Sun2_session_scraper

Skraper listen over enkelt-solinger fra SUN2 Owner og lager en importfil per måned:

```text
Sun2_sessions_YYYY-MM.json
```

Filene kan beholdes som råarkiv, og kan også sendes direkte til Fibaro10:

```text
POST /api/sun2/sessions/ingest
POST /api/sun2/beds/ingest
POST /api/sun2/product-sales/ingest
```

## Hvorfor egen app

`sun2_importer` håndterer romstatistikk per dag. Denne appen håndterer enkeltlinjer: starttid, rom, bruker, varighet, betalt beløp og status. Det gir mye bedre grunnlag for analyse av bruksmønster senere.

Appen kan også lese SUN2 sin sengeliste fra `settings_beds.php`. Den listen brukes som fasit for fast fysisk `room_id`, SUN2 `sun2_bed_id`, dagens SUN2-navn, modell, pris, maks soletid og status.

Appen henter også produktsalg. Daglig jobb henter en dag av gangen slik at Fibaro10 kan gruppere produktsalg per dato. Månedlig jobb henter hele forrige måned og brukes som avstemming mot Altera/Sun2-oppgjør. Begge jobbene poster til samme idempotente tabell i Fibaro10, så månedskontrollen dobbeltteller ikke salg som allerede er hentet daglig.

Rom-mappingen er bevisst historisk:

- SUN2-navn `.` eller `-` = fysisk `rom-10`
- SUN2 `Rom 1` til `Rom 9` = fysisk `rom-01` til `rom-09`
- SUN2 `Rom 10`, `Rom 11`, `Rom 12` = fysisk `rom-11`, `rom-12`, `rom-13`

## Miljøvariabler

```env
SUN2_USERNAME=sun2.lillehammer@gmail.com
SUN2_PASSWORD=...

# Bruk LIST_URL hvis vi finner eksakt URL til siden i SUN2 Owner.
# Hvis den står tom prøver appen å klikke seg frem via NAVIGATION_LABELS.
BASE_URL=https://sun2owner.repayal.com
LIST_URL=
NAVIGATION_LABELS=Statistikk|Bruker|Liste
PRODUCT_SALES_URL=
PRODUCT_SALES_NAVIGATION_LABELS=Rapporter|Produktsalg

START_DATE=2026-05-01
END_DATE=
OUT_DIR=/data/session_exports
ERROR_DIR=/data/session_errors
STATUS_FILE=/data/session_scraper_status.json
PAUSE_SECONDS=2
SKIP_EXISTING=1
AUTO_START=0

# Nattlig plan. Enkelttimer, senger og medlemmer kjores paa ulike tidspunkt.
SCHEDULE_ENABLED=1
SCHEDULE_SESSIONS_TIME=02:10
SCHEDULE_BEDS_TIME=02:40
SCHEDULE_MEMBERS_TIME=03:10
SCHEDULE_PRODUCT_SALES_DAILY_TIME=03:30
SCHEDULE_PRODUCT_SALES_MONTHLY_TIME=03:55
SCHEDULE_PRODUCT_SALES_MONTHLY_DAY=2
SCHEDULE_POLL_SECONDS=60

# Live-sync henter dagens enkelttimer hvert 5. minutt.
LIVE_SYNC_ENABLED=1
LIVE_SYNC_INTERVAL_SECONDS=300

POST_TO_FIBARO10=1
FIBARO10_API_BASE_URL=http://fibaro10:8110
FIBARO10_API_USERNAME=logger
FIBARO10_API_PASSWORD=robotx
COLLECTOR_ID=qnap-sun2-session-scraper
```

Tom `END_DATE` betyr i dag.

## Kontroll

```text
GET  /
GET  /json
POST /start
POST /stop
POST /sync-current-month
POST /sync-today
POST /sync-beds
POST /sync-members
POST /sync-month?year=2026&month=5
POST /sync-product-sales-yesterday
POST /sync-product-sales-previous-month
POST /sync-product-sales-day
POST /sync-product-sales-month?year=2026&month=5
```

## Nattlig flyt

Denne appen har ikke en egen import-app ved siden av seg. Den skraper data og poster direkte til Fibaro10:

- `02:10`: enkelttimer for inneværende måned
- `02:40`: seng-/rommetadata
- `03:10`: medlemmer og profilfelter
- `03:30`: produktsalg for gårsdagen
- `03:55` dag 2 i måneden: produktsalg for hele forrige måned til avstemming

I tillegg hentes dagens enkelttimer hvert 5. minutt når `LIVE_SYNC_ENABLED=1`. Den jobben skriver en egen dagsfil, for eksempel `Sun2_sessions_2026-05-24.json`, og bruker samme idempotente API-import som månedsjobben.

Alle jobbene rapporterer status til Fibaro10, slik at Datakilder viser om nattjobbene faktisk har gått.

## Viktig første test

Første gang bør `POST_TO_FIBARO10=0` brukes. Da ser vi at JSON-filene får riktige kolonner og verdier. Når parseren treffer riktig tabell, settes `POST_TO_FIBARO10=1`.
