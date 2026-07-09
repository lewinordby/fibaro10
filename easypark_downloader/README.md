# EasyPark downloader

Oppdatert 10.07.2026.

Liten QNAP-container som logger inn i EasyPark, laster ned CSV-rapport og sender filen til Fibaro10.

## Drift

- `GET /health` viser om appen lever.
- `GET /status` viser siste kjoring, siste fil, siste periode og eventuell feil.
- `POST /sync-now` starter en nedlasting med standardperioden EasyPark viser.
- `POST /sync-now?from_date=2026-01-01&to_date=2026-01-31` laster ned valgt periode.
- `POST /sync-period?from_date=2026-01-01&to_date=2026-01-31` er en tydelig variant for perioder.
- `POST /queue-sync-now` og `POST /queue-sync-period?from_date=2026-01-01&to_date=2026-01-31` starter samme jobb i bakgrunnen og svarer med en gang.
- `POST /backfill-year?year=2026` kjorer maned for maned fra 1. januar til dagens dato.

Containeren bruker persistent browserprofil i `./data/browser-profile`, slik at EasyPark-sesjonen kan gjenbrukes sa lenge EasyPark godtar den. Tidspunkt for siste fullforte EasyPark-login lagres i `./data/auth-state.json`, men brukes bare som statusinformasjon. Appen kaster ikke sesjonen bare fordi den har blitt eldre enn et visst antall timer, og nattjobben skal normalt ikke tvinge ny login.

Etter en vellykket import tar appen en kopi av siste fungerende browserprofil til `./data/last-good-browser-profile`. Hvis EasyPark senere returnerer reCAPTCHA eller tilsvarende login-feil, restaurerer appen automatisk denne profilen og prover samme import en gang til for a unnga at en korrupt loginflyt stopper fast drift.

Hvis EasyPark krever ny sikkerhetskontroll, forsoker appen a hente verifikasjonskode fra Gmail nar kodefeltet faktisk vises.
Etter at EasyPark er bedt om a sende kode, prover appen Gmail flere ganger i opptil `EASYPARK_CODE_WAIT_SECONDS`, standard 120 sekunder.

EasyPark sitt datofilter tillater maks ett ar per eksport. Backfill kjorer derfor i manedlige biter, og Fibaro10 dedupliserer pa `source_system` + `parking_id`.

Anbefalt fast drift er henting flere ganger daglig: `EASYPARK_RUN_TIMES=08:00,10:00,12:00,14:00,16:00,18:00,20:00,23:00`, `EASYPARK_SCHEDULE_MODE=recent`, `EASYPARK_RECENT_DAYS=2` og `EASYPARK_RUN_ON_START=false`. Da henter appen i gar og i dag på faste tidspunkt. Fibaro10 lagrer en ny parkeringsprognose etter hver vellykkede import. Ved behov kan Fibaro10 sin parkeringsside starte samme henting manuelt med knappen "Oppdater tall".

`EASYPARK_FORCE_LOGIN_TIMES` skal normalt sta tom, fordi tvungen logout kan bryte en fortsatt gyldig EasyPark-session og skape kodefeil uten at EasyPark faktisk har sendt ny kode.
