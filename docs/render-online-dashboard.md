# Render-basert online dashboard

Oppdatert 10.07.2026.

Maalet er at QNAP ikke trenger inngaaende internettrafikk for mobilgrensesnittet. QNAP/Fibaro10 er datakilde internt og pusher et begrenset snapshot ut til Render. Render viser bare siste publiserte tall fra egen Postgres-database.

Status per nå: dagens `online_dashboard` kjører på QNAP og eksponeres via `online.lilletorget.net`. Dette dokumentet beskriver Render-cutover-modellen hvis mobilflaten senere skal flyttes helt ut av QNAP.

## Arkitektur

1. `online_dashboard` paa QNAP kjoerer i `source`-modus.
2. QNAP bygger et offentlig snapshot fra interne tabeller.
3. Snapshotet inneholder aggregater, statusverdier, tider og ukediagram. Registreringsnummer og interne radlister publiseres ikke.
4. QNAP pusher snapshotet til Render-endepunktet `/api/snapshot/ingest` med bearer-token.
5. `online_dashboard` paa Render kjoerer i `snapshot`-modus og leser bare tabellen `online_dashboard_snapshots`.
6. Naar Render virker, kan WAN port forward til QNAP fjernes.

## Render-tjeneste

Bruk samme Dockerfile som dagens online-dashboard:

```text
online_dashboard/Dockerfile
```

Render trenger en Postgres-database og disse environment variables:

```text
DATABASE_URL=<Render Postgres internal database url>
ONLINE_DASHBOARD_MODE=snapshot
PUBLIC_DASHBOARD_INGEST_TOKEN=<lang tilfeldig token>
PUBLIC_DASHBOARD_USERNAME=<mobilbruker>
PUBLIC_DASHBOARD_PASSWORD=<sterkt passord>
PUBLIC_DASHBOARD_SESSION_SECRET=<lang tilfeldig hemmelighet>
PUBLIC_DASHBOARD_SHOW_MONEY=1
PUBLIC_DASHBOARD_PUBLIC=0
```

`PUBLIC_DASHBOARD_SHOW_MONEY=1` viser omsetningstall. Sett den til `0` hvis Render bare skal vise drift/status uten kroner.

Appen godtar baade `postgresql://...`, `postgres://...` og `postgresql+asyncpg://...` for `DATABASE_URL`.

## QNAP/source

Legg dette i QNAP `.env` naar Render-endepunktet finnes:

```text
ONLINE_DASHBOARD_MODE=source
PUBLIC_DASHBOARD_SYNC_ENABLED=1
PUBLIC_DASHBOARD_SYNC_URL=https://<render-app>.onrender.com
PUBLIC_DASHBOARD_SYNC_TOKEN=<samme verdi som PUBLIC_DASHBOARD_INGEST_TOKEN paa Render>
PUBLIC_DASHBOARD_SYNC_INTERVAL_SECONDS=15
PUBLIC_DASHBOARD_SYNC_TIMEOUT_SECONDS=12
```

Hvis `PUBLIC_DASHBOARD_SYNC_URL` peker til base-URL, legger appen automatisk til `/api/snapshot/ingest`.

## Oppdateringsmodell

QNAP beregner snapshot periodisk og sammenligner endringshash. Push sendes bare naar publiserte tall/statusverdier er endret. Standard intervall er 15 sekunder.

Denne modellen fanger endringer fra EasyPark, Sun2, HC3 energi, lys og ventilasjon uten at alle interne ingest-punkter maa endres. Den er derfor robust for eksisterende importjobber.

## Cutover

1. Opprett Render Postgres.
2. Opprett Render Web Service fra repoet med `online_dashboard/Dockerfile`.
3. Sett Render-env fra seksjonen over.
4. Deploy Render.
5. Sjekk `https://<render-app>.onrender.com/health`.
6. Sett QNAP `.env` for sync.
7. Deploy QNAP med `scripts/deploy-qnap.ps1`.
8. Sjekk at Render mottar snapshot og viser tall.
9. Fjern WAN port forward til QNAP `8443`.
10. Oppdater DNS for mobilgrensesnittet hvis domenet skal flyttes til Render.

## Sikkerhet

- Render mottar kun bearer-token-beskyttet snapshot-ingest.
- Render UI bruker egen HMAC-basert session-cookie, ikke QNAP access keys.
- QNAP trenger ikke inbound trafikk etter cutover.
- Snapshotet publiserer aggregater og status, ikke registreringsnummer eller full intern historikk.
- Interne styringsflater i `fibaro10` forblir paa internt nett.
