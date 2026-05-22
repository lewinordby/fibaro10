# Sun2_importer

`Sun2_importer` erstatter den gamle `sol_import`-flyten.

Den poller katalogen der `sun2_download` legger CSV-filene, parser romstatistikk og sender resultatet til Fibaro10:

```text
POST /api/sun2/room-stats/ingest
```

Fibaro10 lagrer data i:

- `sun2_room_daily_stats`
- `sun2_import_runs`

## Viktige valg

- `sun2_download` kan fortsette som i dag.
- Importen er idempotent: samme rom/dato kan sendes flere ganger uten duplikater.
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
```

## Lokal start

```bash
docker compose up -d --build
```

Apnes pa:

```text
http://QNAP-IP:8096
```
