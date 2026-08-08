# Utviklingsoppsett

Oppdatert 10.07.2026.

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

Deploy-scriptet pusher `main` til GitHub, logger inn paa QNAP via SSH, henter `origin/main`, tar backup av runtimefiler, bygger/restarter relevante containere og kjorer health/smoke checks.

Per 10.07.2026 bygges/restartes blant annet:

- `owntracks_service`
- `fibaro10_proxy`
- `fibaro10`
- `online_dashboard`
- `maintenance_mobile`
- `alarm_mobile`
- `fibaro10ipad`
- `axis_camera_snapshots`
- `car_info_lookup`
- `sun2_session_scraper`
- `parking_sun_linker`
- `easypark_downloader`

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

Dette oppretter `C:\Users\<bruker>\.ssh\id_ed25519_qnap_fibaro10`, legger inn SSH-aliaset `qnap-fibaro10`, setter repoet som safe Git-directory og setter lokal Git-identitet for repoet. Det installerer ogsaa Python-avhengigheter, alle elleve frontendmiljoer og Playwright Chromium, slik at `check-local.ps1` kan kjores direkte paa en ny maskin.

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

Standard deploy sammenligner QNAP-commit med commiten som skal rulles ut og bygger bare tjenestene som faktisk er berort. Endringer i `main.py` eller `desktop_v2` rulles ut med to kjernespor: ny versjon bygges og helsesjekkes i det inaktive sporet, den stabile `fibaro10`-gatewayen flytter trafikken, og forrige spor stoppes forst etter et vellykket bytte. Bakgrunnsjobbene kjorer i `fibaro10_worker` og startes pa ny versjon etter at webtrafikken er flyttet. EasyPark og Roborock bygges bare nar deres egne filer endres; en endring i hovedstackens Compose-fil starter dem ikke pa nytt. Ukjente filtyper utloser bevisst full rebuild av hovedstacken. Selve deployplanen kan regresjonstestes med `scripts/test-deploy-plan.ps1`.

Aktivt kjernespor lagres pa QNAP i `/share/CACHEDEV3_DATA/fibaro10_runtime/active-slot`. `scripts/deploy-core-qnap.sh` eier byttet og skal ikke kalles manuelt uten at `APP_BUILD` og `APP_COMMIT` er satt. Vanlig inngang er alltid `scripts/deploy-qnap.ps1`.

## V1-referanse

V1 er en valgfri frakoblet referansevisning, ikke en gammel live-app mot produksjonsdatabasen.
V2 paa port `8110` er daglig drift og skal behandles som produksjon. V1-referansen skal bare brukes for aa sammenligne gamle funksjoner mot V2, og den trenger ikke kjoere til daglig.

- Adresse: `http://192.168.20.218:8111`
- Container: `fibaro10_v1`
- Compose-fil: `docker-compose.v1-reference.yml`
- Appkode: `v1_reference/`
- Kildecommit for meny/funksjoner: `487044d`

Referansen viser V1-menyen og forklarer hva de gamle sidene gjorde. Den bruker ikke `.env`, database, HC3, EasyPark, Sun2, Yr, Roborock eller andre datakilder. Dette er valgt fordi den gamle V1-appen kunne henge seg paa tunge lesesider, og fordi formaalet naa bare er aa sammenligne funksjonalitet.

Merk: `online_dashboard` bruker ogsaa intern port `8111` inne i containeren, men er ikke eksponert direkte paa host-port 8111 i hoved-compose. V1-referansen bruker host-port `192.168.20.218:8111` bare naar den startes med egen compose-fil.

Deploy/oppdater referansen slik:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy-qnap-v1-history.ps1
```

Dette scriptet er isolert: det laster bare opp `v1_reference/` og `docker-compose.v1-reference.yml`, bygger/restarter bare `fibaro10_v1`, og skal ikke kjoere `docker-compose.qnap.yml`, `git reset` eller restart av V2.

## Produksjon

- QNAP: `192.168.20.218`
- SSH-alias: `qnap-fibaro10`
- Appmappe: `/share/CACHEDEV1_DATA/Public/containerdata/fibaro10`
- Intern app (anbefalt): `https://fibaro10.lilletorget.net`
- Intern HTTP-reserve og API-adresse: `http://192.168.20.218:8110`
- Online dashboard: `https://online.lilletorget.net`
- iPad-grensesnitt: `https://ipad.lilletorget.net`
- Vedlikehold mobil: `https://vedl.lilletorget.net`
- Alarm mobil: `https://alarm.lilletorget.net` eller lokalt `http://192.168.20.218:8114`
- OwnTracks: `https://owntracks.lilletorget.net`
- Systemkart i appen: `https://fibaro10.lilletorget.net/admin/systemkart`
- Datakilder i appen: `https://fibaro10.lilletorget.net/admin/datakilder`
- Docker: `/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker`
- Git paa QNAP leveres via Entware i `/opt/bin/git`.

### Intern HTTPS

Hovedappen og mikroappene bruker offentlig DNS og et offentlig betrodd Let's Encrypt-
sertifikat. DNS-navnene peker til QNAPs private adresse, og virker derfor bare pa
lokalnettet eller via VPN. Det skal ikke installeres lokal DNS eller rotsertifikat pa
PC, nettbrett eller telefon. Se `docs/intern-https.md` for alle navn, fornyelse,
sikkerhet og gjenoppretting.

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

QNAP-backup-scriptet ligger i `scripts/qnap-backup.sh` og tar vare paa alle runtime-`.env`-filer, importerdata, AI-modeller, Roborock-data og separate SQL-dumper av baade Fibaro10- og OwnTracks-databasen:

```sh
sh /share/CACHEDEV1_DATA/Public/containerdata/fibaro10/scripts/qnap-backup.sh
```

Backuper lagres under `/share/CACHEDEV3_DATA/fibaro10_archive/fibaro10_backups`, og de 20 nyeste beholdes. Backupen bygges i en midlertidig katalog og blir ikke synlig som ferdig før begge PostgreSQL-dumpene er validert. Hver backup har `CHECKSUMS.sha256`, `BACKUP_MANIFEST.txt`, og siste resultat ligger i `LATEST_STATUS.txt`. Axis snapshot-arkivet er flyttet til eget arkivvolum og tas ikke med i standard backup; bilder som er knyttet til soltimer ligger i PostgreSQL.

En ekstra kopi til en annen maskin eller et montert eksternt mål kan aktiveres uten kodeendring:

```sh
BACKUP_REPLICA_TARGET='backup@annen-maskin:/backup/fibaro10' sh scripts/qnap-backup.sh
```

Lokal backup regnes fortsatt som fullført hvis den eksterne kopien feiler, men `LATEST_STATUS.txt` settes til `warning` og `replica_status=error`.

Teknisk historikk ryddes automatisk av Fibaro10. Vellykkede tilgangs- og importlogger beholdes 90 dager, feil beholdes 365 dager, sendte ntfy-køposter 30 dager og utløpte sesjoner 30 dager. Parkering, soling, energi, dokumenter, bilder, dørhistorikk og alarmer slettes ikke av denne jobben.

Docker vedlikeholdes ukentlig med `scripts/qnap-docker-maintenance.sh`. Scriptet sletter bare ubrukte bygglag og ubrukte images eldre enn 14 dager, slik at minst ett ukentlig byggesett normalt beholdes som cache. Kjørende containere, nettverk i bruk og Docker-volumer berøres ikke.

## Restore-test

Bruk denne fra utviklingsmaskinen for aa verifisere at backupen faktisk kan brukes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-qnap-backup.ps1
```

Scriptet kjorer `qnap-backup.sh`, sjekker at backupmappen og begge SQL-dumpene finnes, oppretter midlertidige PostgreSQL-databaser i hver databasecontainer, leser dumpene inn og sletter testdatabasene etterpaa. Produksjonsdatabasene endres ikke.

For at restore-testen skal gaa raskt hopper den normalt over Axis snapshot-arkivet. Full snapshot-backup kan testes eksplisitt:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-qnap-backup.ps1 -IncludeSnapshots
```

Hvis du kun vil sjekke backupfilene uten SQL-restore:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-qnap-backup.ps1 -SkipSqlRestore
```
