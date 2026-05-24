# Sun2_importer

`Sun2_importer` erstatter den gamle `sol_import`-flyten.

Den poller katalogen der `sun2_backfill_downloader` legger nattlige CSV-filer, parser romstatistikk og sender resultatet til Fibaro10:

```text
POST /api/sun2/room-stats/ingest
```

Fibaro10 lagrer data i:

- `sun2_room_daily_stats`
- `sun2_import_runs`

## Viktige valg

- `sun2_download` kan fortsette som i dag.
- Importen er idempotent: samme rom/dato kan sendes flere ganger uten duplikater.
- Importen sender også fast fysisk `room_id` og SUN2 `sun2_bed_id`, slik at historiske navneendringer ikke ødelegger rapporter.
- SUN2 `.` eller `-` blir fysisk `rom-10`; SUN2 `Rom 10`-`Rom 12` blir fysisk `rom-11`-`rom-13`.
- Hvis Fibaro10 ikke svarer, blir filen liggende i `incoming` og forsokes igjen.
- Parsefeil flyttes til `rejected`.
- Vellykket import flyttes til `archive`.

## Miljovariabler

```env
FIBARO10_API_BASE_URL=https://fibaro10.onrender.com
FIBARO10_API_USERNAME=logger
FIBARO10_API_PASSWORD=passord-fra-fibaro10
COLLECTOR_ID=qnap-sun2-importer
IMPORT_DIR=/data/incoming
ARCHIVE_DIR=/data/archive
REJECTED_DIR=/data/rejected
POLL_SECONDS=10

# Skal settes likt som i sun2_backfill_downloader slik at begge ser samme /data.
SUN2_DAILY_DATA_DIR=/share/Container/sun2_daily_data
```

## Lokal start

```bash
docker compose up -d --build
```

Apnes pa:

```text
http://QNAP-IP:8096
```

## Nattlig flyt

1. `sun2_backfill_downloader` laster ned gaarsdagens `Statistics_room_YYYY-MM-DD_YYYY-MM-DD.csv` til `/data/incoming`.
2. `sun2_importer` oppdager filen innen `POLL_SECONDS`.
3. Filen sendes til Fibaro10, flyttes til `archive` ved suksess og rapporteres i Datakilder.
