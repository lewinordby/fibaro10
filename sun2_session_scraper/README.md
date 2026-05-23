# Sun2_session_scraper

Skraper listen over enkelt-solinger fra SUN2 Owner og lager en importfil per måned:

```text
Sun2_sessions_YYYY-MM.json
```

Filene kan beholdes som råarkiv, og kan også sendes direkte til Fibaro10:

```text
POST /api/sun2/sessions/ingest
```

## Hvorfor egen app

`sun2_importer` håndterer romstatistikk per dag. Denne appen håndterer enkeltlinjer: starttid, rom, bruker, varighet, betalt beløp og status. Det gir mye bedre grunnlag for analyse av bruksmønster senere.

## Miljøvariabler

```env
SUN2_USERNAME=sun2.lillehammer@gmail.com
SUN2_PASSWORD=...

# Bruk LIST_URL hvis vi finner eksakt URL til siden i SUN2 Owner.
# Hvis den står tom prøver appen å klikke seg frem via NAVIGATION_LABELS.
BASE_URL=https://sun2owner.repayal.com
LIST_URL=
NAVIGATION_LABELS=Statistikk|Bruker|Liste

START_DATE=2026-05-01
END_DATE=
OUT_DIR=/data/session_exports
ERROR_DIR=/data/session_errors
STATUS_FILE=/data/session_scraper_status.json
PAUSE_SECONDS=2
SKIP_EXISTING=1
AUTO_START=0

POST_TO_FIBARO10=1
FIBARO10_API_BASE_URL=https://fibaro10.onrender.com
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
POST /sync-month?year=2026&month=5
```

## Viktig første test

Første gang bør `POST_TO_FIBARO10=0` brukes. Da ser vi at JSON-filene får riktige kolonner og verdier. Når parseren treffer riktig tabell, settes `POST_TO_FIBARO10=1`.
