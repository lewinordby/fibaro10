# Utviklingsoppsett

Dette repoet er satt opp for rask lokal utvikling paa Windows og direkte idriftsetting paa QNAP.

## Daglig arbeidsflyt

1. Jobb lokalt i repoet.
2. Kjor en rask sjekk ved behov:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev-check.ps1
```

3. Commit endringer.
4. Deploy til QNAP:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy-qnap.ps1
```

Deploy-scriptet pusher `main` til GitHub, logger inn paa QNAP via SSH, henter `origin/main`, tar backup av runtimefiler, bygger `fibaro10` og `online_dashboard`, og kjorer health/smoke checks.

For innlogget live-smoke maa det finnes en lokal `.env.live-smoke` med en dedikert testbruker. Opprett eller roter denne slik:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\provision-live-smoke-user.ps1
```

Scriptet oppretter/oppdaterer `fibaro-smoke` som vanlig lesebruker paa QNAP og skriver passordet til `.env.live-smoke`. Filen er ignorert av Git og skal ikke commit'es.

## Ny PC

Kjor lokal setup fra repo-roten:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local-dev.ps1
```

Hvis QNAP ikke allerede har public key-en, kjor:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local-dev.ps1 -InstallQnapKey
```

Dette oppretter `C:\Users\<bruker>\.ssh\id_ed25519_qnap_fibaro10`, legger inn SSH-aliaset `qnap-fibaro10`, setter repoet som safe Git-directory og setter lokal Git-identitet for repoet.

GitHub-auth lagres av Git Credential Manager. Hvis push feiler, kjor:

```powershell
git credential-manager github login --username lewinordby --browser --force
```

## Nyttige kommandoer

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev-check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\qnap-status.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\health-check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy-qnap.ps1
```

`dev-check.ps1` verifiserer lokal Git-status, GitHub-push dry-run, QNAP SSH, QNAP repo/Docker og web health/smoke.

`qnap-status.ps1` viser QNAP host, git commit/status, compose-status, siste containerlogger og health-watch-logg. Loggutskrift redakterer `username=` og `password=` query-parametre.

`smoke-check.ps1` sjekker de viktigste sidene etter deploy. Auth-beskyttede sider kan svare `401` eller `403`; det regnes som OK naar health-endepunktene svarer og auth-laget beskytter siden.

`desktop_v2/scripts/smoke-live.mjs` sjekker alltid QNAP `/health`. Hvis `.env.live-smoke` finnes, logger den i tillegg inn med `fibaro-smoke` og gaar gjennom alle desktop-rutene som ogsaa brukes av lokal UI-smoke. Deploy-scriptet kjorer denne live-smoken automatisk etter vanlig smoke.

## V1-referanse

V1 paa port `8111` er naa en frakoblet referansevisning, ikke en gammel live-app mot produksjonsdatabasen.
V2 paa port `8110` er daglig drift og skal behandles som produksjon. V1-referansen skal bare brukes for aa sammenligne gamle funksjoner mot V2.

- Adresse: `http://192.168.20.218:8111`
- Container: `fibaro10_v1`
- Compose-fil: `docker-compose.v1-reference.yml`
- Appkode: `v1_reference/`
- Kildecommit for meny/funksjoner: `487044d`

Referansen viser V1-menyen og forklarer hva de gamle sidene gjorde. Den bruker ikke `.env`, database, HC3, EasyPark, Sun2, Yr, Roborock eller andre datakilder. Dette er valgt fordi den gamle V1-appen kunne henge seg paa tunge lesesider, og fordi formaalet naa bare er aa sammenligne funksjonalitet.

Deploy/oppdater referansen slik:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy-qnap-v1-history.ps1
```

Dette scriptet er isolert: det laster bare opp `v1_reference/` og `docker-compose.v1-reference.yml`, bygger/restarter bare `fibaro10_v1`, og skal ikke kjoere `docker-compose.qnap.yml`, `git reset` eller restart av V2.

## Produksjon

- QNAP: `192.168.20.218`
- SSH-alias: `qnap-fibaro10`
- Appmappe: `/share/CACHEDEV1_DATA/Public/containerdata/fibaro10`
- Intern app: `http://192.168.20.218:8110`
- Online dashboard: `https://online.lilletorget.net`
- Docker: `/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker`
- Git paa QNAP leveres via Entware i `/opt/bin/git`.

## Gmail-importer

EasyPark-import og Park Nordic-oppgjor bruker Gmail IMAP med app-passord i QNAP `.env`.
Park Nordic-oppgjor kan bruke egne variabler, men faller tilbake til EasyPark-variablene hvis de ikke er satt:

```env
SETTLEMENT_GMAIL_EMAIL=
SETTLEMENT_GMAIL_APP_PASSWORD=
PARKING_SETTLEMENT_SENDER=fredrik@parknordic.no
# Valgfri. Hvis tom brukes INBOX + automatisk funnet Gmail All Mail/All e-post.
SETTLEMENT_GMAIL_MAILBOXES=
```

Hvis `SETTLEMENT_GMAIL_EMAIL` og `SETTLEMENT_GMAIL_APP_PASSWORD` mangler, brukes `EASYPARK_GMAIL_EMAIL` og `EASYPARK_GMAIL_APP_PASSWORD`.
Selve hemmelige verdier skal bare ligge i runtime `.env`, ikke i Git.

### Historiske parkeringsoppgjor

For perioder foer 2026 finnes normalt ikke Flowbird/Park Nordic som `source_system=flowbird-parknordic` i EasyPark-importen.
Da var Flowbird/Park Nordic ikke integrert mot EasyPark-importen, og tallene kom i stedet som et eget vedlegg.

Dagens oppgjorskontroll er derfor riktig for perioder der databasen har begge disse kildene:

- `source_system=EasyPark`
- `source_system=flowbird-parknordic`

For eldre oppgjor maa kontrollen senere utvides til aa lese og summere det historiske Flowbird/Park Nordic-vedlegget.
Uten dette vedlegget vil brutto mynt/kortautomat ikke kunne kontrolleres automatisk mot intern kilde for perioder foer 2026.

## Backup

Deploy-scriptet tar backup av `.env`, `.env.*`, EasyPark `.env` og EasyPark runtime-data for hver deploy.

QNAP-backup-scriptet ligger i `scripts/qnap-backup.sh` og tar vare paa `.env`, EasyPark runtime-data, Axis snapshot-arkiv og PostgreSQL-dump naar `postgres-1` er tilgjengelig:

```sh
sh /share/CACHEDEV1_DATA/Public/containerdata/fibaro10/scripts/qnap-backup.sh
```

Backuper lagres under `/share/CACHEDEV3_DATA/fibaro10_archive/fibaro10_backups`, og de 20 nyeste beholdes. Axis snapshot-arkivet er flyttet til eget arkivvolum og tas ikke med i standard backup.

## Restore-test

Bruk denne fra utviklingsmaskinen for aa verifisere at backupen faktisk kan brukes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-qnap-backup.ps1
```

Scriptet kjorer `qnap-backup.sh`, sjekker at backupmappen og SQL-dumpen finnes, oppretter en midlertidig PostgreSQL-database, leser dumpen inn i den og sletter testdatabasen etterpaa. Produksjonsdatabasen endres ikke.

For at restore-testen skal gaa raskt hopper den normalt over Axis snapshot-arkivet. Full snapshot-backup kan testes eksplisitt:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-qnap-backup.ps1 -IncludeSnapshots
```

Hvis du kun vil sjekke backupfilene uten SQL-restore:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-qnap-backup.ps1 -SkipSqlRestore
```
