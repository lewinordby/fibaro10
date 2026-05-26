# EasyPark downloader

Liten QNAP-container som logger inn i EasyPark, laster ned CSV-rapport og sender filen til Fibaro10.

## Drift

- `GET /health` viser om appen lever.
- `GET /status` viser siste kjøring, siste fil, siste periode og eventuell feil.
- `POST /sync-now` starter en nedlasting med standardperioden EasyPark viser.
- `POST /sync-now?from_date=2026-01-01&to_date=2026-01-31` laster ned valgt periode.
- `POST /sync-period?from_date=2026-01-01&to_date=2026-01-31` er en tydelig variant for perioder.
- `POST /backfill-year?year=2026` kjører måned for måned fra 1. januar til dagens dato.

Containeren bruker persistent browserprofil i `./data/browser-profile`, slik at EasyPark-sesjonen kan gjenbrukes. Hvis EasyPark krever ny sikkerhetskontroll, forsøker appen å hente verifikasjonskode fra Gmail.

EasyPark sitt datofilter tillater maks ett år per eksport. Backfill kjøres derfor i månedlige biter, og Fibaro10 dedupliserer på `source_system` + `parking_id`.

Anbefalt fast drift er nattlig henting: `EASYPARK_RUN_AT=03:00`, `EASYPARK_SCHEDULE_MODE=recent`, `EASYPARK_RECENT_DAYS=2` og `EASYPARK_RUN_ON_START=false`. Da henter appen i går og i dag hver natt. Ved behov kan Fibaro10 sin parkeringsside starte samme henting manuelt med knappen "Hent fra EasyPark nå".
