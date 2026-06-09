# Fibaro10 Desktop

`desktop_v2` er primart desktop-grensesnitt for Fibaro10. React-appen ligger pa rene hovedruter uten separat URL-prefix, for eksempel `/status/oversikt`, `/parkering/kjoretoy` og `/soling/dagslinje`.

## Mal

- Bruke React, TypeScript, Ant Design og ECharts som primar desktopflate.
- Bruke eksisterende FastAPI/Postgres-backend som datamotor.
- Eksponere JSON-kontrakter under `/api` i stedet for a kopiere template-logikk.
- Fase ut gammel HTML-UI uten a bryte ingest, API-er, POST-handlinger eller importjobber.

## URL-er

- Startside: `/status/oversikt`
- Status omsetning: `/status/omsetning`
- Status drift: `/status/drift`
- Parkering: `/parkering/oversikt`, `/parkering/parkeringer`, `/parkering/kjoretoy`
- Soling: `/soling/dagslinje`, `/soling/enkeltimer`, `/soling/senger`
- Energi: `/energi/status`, `/energi/kurser`, `/energi/laster`
- Ventilasjon og lys: `/ventilasjon/dagslogg`, `/lys/dagslogg`
- Historisk V1 for manuell sammenligning: `http://192.168.20.218:8111`

Alle desktop-ruter ligger bak samme innlogging som hovedappen.

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

Desktopflaten bruker blant annet disse endepunktene:

- `GET /api/overview`
- `GET /api/revenue/month?month=YYYY-MM`
- `GET /api/modules/{module}`
- `GET /api/parking/vehicles/{plate}`

FastAPI server React-appen fra `desktop_v2/dist/index.html` pa hovedrutene `/status`, `/parkering`, `/soling`, `/energi`, `/ventilasjon`, `/lys`, `/renhold` og `/admin`.

## Docker/QNAP

`Dockerfile` har egen Node-buildstage:

1. Installerer `desktop_v2` med `npm ci`.
2. Kjorer `npm run build`.
3. Kopierer `desktop_v2/dist` inn i Python-containeren.

Det betyr at en ny maskin eller QNAP kan bygge desktopflaten direkte fra Git uten lokale buildfiler.

## Videre utvikling

- Flytt resterende POST-handlinger og redigeringsskjemaer gradvis inn i desktopflaten.
- Nar alle operative handlinger er dekket i desktopflaten, kan gamle templates og HTML-ruter slettes fysisk.
- Flytt beregninger videre fra store HTML-ruter til sma backend-funksjoner og `/api`-endepunkter.
- Ikke koble desktopflaten mot `online_dashboard`; bruk hovedappens database/API.
- Hold gamle ingest-ruter stabile sa HC3, EasyPark, SUN2, Roborock og online-dashboard ikke pavirkes.
