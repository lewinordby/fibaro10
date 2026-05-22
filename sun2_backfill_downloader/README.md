# Sun2_backfill_downloader

Historisk nedlasting av SUN2 romstatistikk uten aa stoppe den daglige `sun2_download`.

Appen logger inn i SUN2 owner, gjenbruker samme browser-session, og henter en CSV per dato:

```text
Statistics_room_YYYY-MM-DD_YYYY-MM-DD.csv
```

Filer lagres raatt i `OUT_DIR`. De skal deretter importeres av `sun2_importer`.

## Miljovariabler

```env
SUN2_USERNAME=sun2.lillehammer@gmail.com
SUN2_PASSWORD=...
START_DATE=2017-03-01
END_DATE=
OUT_DIR=/data/backfill_raw
ERROR_DIR=/data/backfill_errors
STATUS_FILE=/data/backfill_status.json
PAUSE_SECONDS=2
SKIP_EXISTING=1
AUTO_START=0
```

Tom `END_DATE` betyr i gaar.

## Kontroll

```text
GET  /
GET  /json
POST /start
POST /stop
```

Hvis containeren restartes, leser den `STATUS_FILE` og fortsetter fra neste dato. Eksisterende filer hoppes over.
