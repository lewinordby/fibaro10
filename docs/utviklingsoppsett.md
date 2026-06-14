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

## Backup

Deploy-scriptet tar backup av `.env`, `.env.*`, EasyPark `.env` og EasyPark runtime-data for hver deploy.

QNAP-backup-scriptet ligger i `scripts/qnap-backup.sh` og tar vare paa `.env`, EasyPark runtime-data og PostgreSQL-dump naar `postgres-1` er tilgjengelig:

```sh
sh /share/CACHEDEV1_DATA/Public/containerdata/fibaro10/scripts/qnap-backup.sh
```

Backuper lagres under `/share/CACHEDEV1_DATA/Public/containerdata/backups/fibaro10`, og de 20 nyeste beholdes.

## Restore-test

Bruk denne fra utviklingsmaskinen for aa verifisere at backupen faktisk kan brukes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-qnap-backup.ps1
```

Scriptet kjorer `qnap-backup.sh`, sjekker at backupmappen og SQL-dumpen finnes, oppretter en midlertidig PostgreSQL-database, leser dumpen inn i den og sletter testdatabasen etterpaa. Produksjonsdatabasen endres ikke.

Hvis du kun vil sjekke backupfilene uten SQL-restore:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-qnap-backup.ps1 -SkipSqlRestore
```
