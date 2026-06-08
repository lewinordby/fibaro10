# Fibaro10 desktop v2

`desktop_v2` er en separat desktop-revisjon av Fibaro10-grensesnittet. Den kjører ved siden av dagens Jinja-baserte hovedapp.

## Mål

- Beholde dagens løsning uendret mens ny revisjon utvikles.
- Flytte nytt desktop-UI over til React, TypeScript, Ant Design og ECharts.
- Bruke eksisterende FastAPI/Postgres-backend som datamotor.
- Eksponere nye JSON-kontrakter under `/api/v2` i stedet for å kopiere template-logikk.
- Gjøre det mulig å utvikle gammel og ny revisjon i hver sin retning.

## URL-er

- Ny desktop-revisjon: `/v2`
- V2 oversikt: `/v2/oversikt`
- V2 omsetning: `/v2/omsetning`
- V2 drift: `/v2/drift`
- Dagens grensesnitt: `/status/dashboard`

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

- Behold eksisterende Jinja-sider som stabil driftsoverflate til v2 har tatt over nok funksjon.
- Lag nye v2-sider domenevis: Parkering, Soling, Energi, Ventilasjon, Lys, Renhold.
- Flytt beregninger gradvis fra store HTML-ruter til små backend-funksjoner og `/api/v2`-endepunkter.
- Ikke koble v2 mot `online_dashboard`; bruk hovedappens database/API.
- Hold `desktop_v2` som egen frontendpakke til gammel revisjon kan fases ut eller arkiveres.
