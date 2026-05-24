# Sun2_backfill_downloader

Nedlasting av SUN2 romstatistikk.

Appen har to bruksomrader:

- nattlig dagsnedlasting av gaarsdagen til importmappen
- manuell historisk backfill naar vi trenger aa fylle gamle data

Appen logger inn i SUN2 owner, gjenbruker samme browser-session, og henter en CSV per dato:

```text
Statistics_room_YYYY-MM-DD_YYYY-MM-DD.csv
```

Historisk backfill lagres raatt i `OUT_DIR`. Nattlig dagsnedlasting lagres i `DAILY_OUT_DIR`, normalt `/data/incoming`, slik at `sun2_importer` importerer filen automatisk.

## Miljovariabler

```env
SUN2_USERNAME=sun2.lillehammer@gmail.com
SUN2_PASSWORD=...
START_DATE=2017-03-01
END_DATE=
OUT_DIR=/data/backfill_raw
DAILY_OUT_DIR=/data/incoming
ERROR_DIR=/data/backfill_errors
STATUS_FILE=/data/backfill_status.json
PAUSE_SECONDS=2
SKIP_EXISTING=1
AUTO_START=0

# Nattlig dagsnedlasting. Dette laster normalt ned gaarsdagen kl 01:05.
DAILY_DOWNLOAD_ENABLED=1
DAILY_DOWNLOAD_TIME=01:05
DAILY_DOWNLOAD_DAYS_BACK=1
SCHEDULE_POLL_SECONDS=60

# Brukes bare til aa rapportere status inn i Fibaro10.
FIBARO10_API_BASE_URL=https://fibaro10.onrender.com
FIBARO10_API_USERNAME=logger
FIBARO10_API_PASSWORD=robotx
COLLECTOR_ID=qnap-sun2-daily-downloader
```

Tom `END_DATE` betyr i gaar.

## Kontroll

```text
GET  /
GET  /json
POST /start
POST /stop
POST /download-yesterday
```

Hvis containeren restartes, leser den `STATUS_FILE` og fortsetter fra neste dato. Eksisterende filer hoppes over.

## Deling av mappe med importer

`sun2_backfill_downloader` og `sun2_importer` maa bruke samme host-mappe for `/data` dersom dagsfilene skal ga rett til import. Sett samme absolutte sti i begge `.env`-filer:

```env
SUN2_DAILY_DATA_DIR=/share/Container/sun2_daily_data
```
