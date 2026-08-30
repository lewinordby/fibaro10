# Utviklingsoppsett

Oppdatert 30.08.2026.

## Repoer

| Repo | Ansvar |
| --- | --- |
| `workspace/fibaro10` | API, database, adaptere, mobilapper, jobber og integrasjoner. |
| `workspace/lilletorget-mantis` | Gjeldende PC-grensesnitt på `app.lilletorget.net`. |
| `workspace/lilletorget-kiosk` | Intern 1920 x 1080 robotkiosk. |

Repoene committes, testes og deployes hver for seg. Det skal ikke kopieres CSS
eller frontendkode tilbake til Fibaro10-adapterne.

## Lokal oppstart og test

Fra Fibaro10-repoet:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-local.ps1
```

Fra Mantis-repoet:

```powershell
npm ci
npm run build
npm run verify
```

OwnTracks er den eneste Node-frontenden i Fibaro10-repoets generelle
kvalitetsport. Mobilappene er serverrendret og deler `packages/mobile-appkit`.

## Deploy

Backend og aktive adaptere:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy-qnap.ps1
```

Mantis deployes fra Mantis-repoet med dets `scripts/deploy-qnap.ps1`. Kiosk
deployes fra kiosk-repoet. Standard backenddeploy bruker blå/grønn kjerneswitch,
starter worker på ny versjon og bygger bare berørte tjenester. Kandidaten må
bestå health før trafikken flyttes; smoke kjøres etterpå. Ved oppstartsfeil
tilbakeføres berørt tjeneste. Se [deploy- og rollbackreglene](quality-release-1837.md).
Bruk `-PlanOnly` før utrulling. På Linux brukes `pwsh`; aktiver venv med
`source .venv/bin/activate`. Deploy- og testscript kaller hverandre i samme
PowerShell-prosess slik at lister og parametere bevares.

Nyttige kontroller:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev-check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\qnap-status.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\health-check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-deploy-plan.ps1
```

Innlogget smoke bruker en dedikert testbruker i den ignorerte filen
`.env.live-smoke`. Den opprettes eller roteres med
`scripts/provision-live-smoke-user.ps1`.

## Produksjon

- QNAP: `192.168.20.218`
- SSH-alias: `qnap-fibaro10`
- Backendkode: `/share/CACHEDEV1_DATA/Public/containerdata/fibaro10`
- Mantis-releaser: `/share/CACHEDEV3_DATA/lilletorget-mantis/releases`
- Primær app: `https://app.lilletorget.net`
- Kiosk: `https://kiosk.lilletorget.net`
- Mobil: `https://online.lilletorget.net`, `https://vedl.lilletorget.net` og `https://alarm.lilletorget.net`
- Lokasjon: `https://owntracks.lilletorget.net`

Interne navn bruker offentlig DNS til privat QNAP-adresse og offentlig betrodd
sertifikat. De er bare tilgjengelige fra LAN eller VPN. Se `docs/intern-https.md`.

## Integrasjoner og hemmeligheter

Alle nøkler, app-passord og tokens ligger i runtime `.env` eller tjenestens egen
`.env`; de skal aldri legges i Git. EasyPark og Park Nordic bruker Gmail-verdier
fra runtimekonfigurasjonen. Roborock og Dreame har egne compose/runtimefiler og
bygges bare når deres tjeneste er berørt.

## Backup og restore

`scripts/qnap-backup.sh` lager nattlig backup med runtimefiler, importerdata,
modeller og separate PostgreSQL-dumper for Fibaro10 og OwnTracks.
`scripts/qnap-full-restore-backup.sh` lager en komplett gjenopprettingspakke med
aktiv Fibaro10-, Mantis- og kiosk-kildekode, tjenestedata og instruksjoner.
Axis-arkivet tas ikke med, men bilder knyttet til soltimer beholdes i databasen.

Backuper lagres på Vol3 og publiseres først etter validering og SHA-256-kontroll.
Restore verifiseres med `scripts/verify-qnap-backup.ps1`. Globale Docker-prune-
eller slettkommandoer skal ikke brukes; opprydding gjøres på navngitte gamle
containere, images og kataloger.
