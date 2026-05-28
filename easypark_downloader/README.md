# EasyPark downloader

Liten QNAP-container som logger inn i EasyPark, laster ned CSV-rapport og sender filen til Fibaro10.

## Drift

- `GET /health` viser om appen lever.
- `GET /status` viser siste kjøring, siste fil, siste periode og eventuell feil.
- `POST /sync-now` starter en nedlasting med standardperioden EasyPark viser.
- `POST /sync-now?from_date=2026-01-01&to_date=2026-01-31` laster ned valgt periode.
- `POST /sync-period?from_date=2026-01-01&to_date=2026-01-31` er en tydelig variant for perioder.
- `POST /backfill-year?year=2026` kjører måned for måned fra 1. januar til dagens dato.

Containeren bruker persistent browserprofil i `./data/browser-profile`, slik at EasyPark-sesjonen kan gjenbrukes gjennom dagen. Tidspunkt for siste fullførte EasyPark-login lagres i `./data/auth-state.json`, men brukes bare som statusinformasjon. Appen kaster ikke lenger sesjonen bare fordi den har blitt eldre enn et visst antall timer. Ny full login tvinges kun på tidspunktene i `EASYPARK_FORCE_LOGIN_TIMES`, normalt nattjobben kl. 03:00.

Hvis EasyPark krever ny sikkerhetskontroll tidligere enn dette, forsøker appen fortsatt å hente verifikasjonskode fra Gmail når kodefeltet vises.

EasyPark sitt datofilter tillater maks ett år per eksport. Backfill kjøres derfor i månedlige biter, og Fibaro10 dedupliserer på `source_system` + `parking_id`.

Anbefalt fast drift er nattlig henting: `EASYPARK_RUN_AT=03:00`, `EASYPARK_SCHEDULE_MODE=recent`, `EASYPARK_RECENT_DAYS=2` og `EASYPARK_RUN_ON_START=false`. Da henter appen i går og i dag hver natt. Ved behov kan Fibaro10 sin parkeringsside starte samme henting manuelt med knappen "Hent fra EasyPark nå".

For mer forutsigbar drift kan `EASYPARK_RUN_TIMES` brukes i stedet for enkelt-tidspunkt/intervall, for eksempel `03:00,12:00,15:00,18:00,21:00`. Med `EASYPARK_FORCE_LOGIN_TIMES=03:00` forsøker appen først å logge ut med eksisterende EasyPark-profil, sletter deretter lokal profil, laster inn login-siden på nytt og starter nattjobben med ren innlogging og ny Gmail-kodeflyt. Kjøringene senere på dagen kan da gjenbruke samme dags-session.
