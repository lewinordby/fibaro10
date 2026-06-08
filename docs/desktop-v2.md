# Fibaro10 desktop v2

`desktop_v2` er primært desktop-grensesnitt for Fibaro10. Den gamle Jinja-baserte UI-en beholdes foreløpig som backend-/fallback-kode, men vanlig GET-navigasjon til gamle HTML-områder redirectes til v2.

## Mål

- Flytte nytt desktop-UI over til React, TypeScript, Ant Design og ECharts.
- Bruke eksisterende FastAPI/Postgres-backend som datamotor.
- Eksponere nye JSON-kontrakter under `/api/v2` i stedet for å kopiere template-logikk.
- Fase ut gammel HTML-UI uten å bryte ingest, API-er, POST-handlinger eller importjobber.

## URL-er

- Ny desktop-revisjon: `/v2`
- V2 oversikt: `/v2/oversikt`
- V2 omsetning: `/v2/omsetning`
- V2 drift: `/v2/drift`
- Gamle hovedområder som `/status`, `/parkering`, `/soling`, `/energi`, `/ventilasjon`, `/lys`, `/renhold`, `/konto` og `/ai` redirectes til v2 etter innlogging.

Alle v2-ruter ligger bak samme innlogging som hovedappen.

## Frontend

Prosjektet ligger i `desktop_v2/`.

Lokalt:

```powershell
cd desktop_v2
npm.cmd install
npm.cmd run dev
```

Vite dev-server proxyer `/api` til `http://127.0.0.1:8110`.

Produksjonsbygg:

```powershell
cd desktop_v2
npm.cmd run build
```

Bygget havner i `desktop_v2/dist/`. Denne mappen skal ikke committes.

## Backend

V2 bruker disse endepunktene:

- `GET /api/v2/overview`
- `GET /api/v2/revenue/month?month=YYYY-MM`

FastAPI server React-appen fra `desktop_v2/dist/index.html` på `/v2` og `/v2/{path}`.

## Docker/QNAP

`Dockerfile` har egen Node-buildstage:

1. Installerer `desktop_v2` med `npm ci`.
2. Kjører `npm run build`.
3. Kopierer `desktop_v2/dist` inn i Python-containeren.

Det betyr at en ny maskin eller QNAP kan bygge v2 direkte fra Git uten lokale buildfiler.

## Videre utvikling

Anbefalt retning:

- Flytt resterende POST-handlinger og redigeringsskjemaer gradvis inn i v2.
- Når alle operative handlinger er dekket i v2, kan gamle templates og HTML-ruter slettes fysisk.
- Flytt beregninger videre fra store HTML-ruter til små backend-funksjoner og `/api/v2`-endepunkter.
- Ikke koble v2 mot `online_dashboard`; bruk hovedappens database/API.
- Hold gamle API- og ingest-ruter stabile så HC3, EasyPark, SUN2, Roborock og online-dashboard ikke påvirkes.
