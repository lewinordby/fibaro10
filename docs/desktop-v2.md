# Fibaro10 Desktop V2

Oppdatert 10.07.2026.

`desktop_v2` er primært desktop-grensesnitt for Fibaro10. React-appen ligger på rene hovedruter uten separat URL-prefix, for eksempel `/status/omsetning`, `/parkering/parkeringer`, `/soling/dagslinje` og `/admin/datakilder`.

## Mål

- Bruke React, TypeScript, Ant Design og ECharts som primær desktopflate.
- Bruke eksisterende FastAPI/PostgreSQL-backend som datamotor.
- Eksponere JSON-kontrakter under `/api` i stedet for å kopiere template-logikk.
- La gamle HTML-ruter kun være redirects eller tekniske ingest-/fallbackruter.
- Holde underapper som OwnTracks, vedlikehold mobil og iPad separate, men lenket fra systemkart/manual.

## Hovedmeny

Venstremenyen er delt i fire grupper:

| Gruppe | Menyvalg | Hovedformål |
| --- | --- | --- |
| Dashboard | Dashboard | Fire operative dashboard: omsetning, parkering, soling og drift. |
| Økonomi | Omsetning, Parkering, Soling, Koble | Omsetning, parkering, soling og kobling mellom parkering/SUN2. |
| Bygg og drift | Energi, Ventilasjon, Lys, Solrom, Dører, Renhold, Vedlikehold | Teknisk drift, byggstatus, miljø, renhold og oppgaver/besøk. |
| System | Ideer, Mobil, Admin | Forslag, mobilskjermspeiling og administrasjon. |

## Gjeldende ruter

### Dashboard

- `/status/omsetning`
- `/status/parkering`
- `/status/soling`
- `/status/drift`
- `/status/sammenligning`

### Omsetning

- `/omsetning/oversikt`
- `/omsetning/sammenligning`
- `/omsetning/akkumulert`
- `/omsetning/manedsoversikt`

### Parkering

- `/parkering/oversikt`
- `/parkering/parkeringer`
- `/parkering/dagslinje`
- `/parkering/kjoretoy`
- `/parkering/kjoretoy/:plate`
- `/parkering/omrade`
- `/parkering/prognose`
- `/parkering/sammenligning`
- `/parkering/oppgjor`
- `/parkering/oppgjor/:settlementId`
- `/parkering/oppslag`
- `/parkering/bilstatistikk` finnes som skjult rute

### Soling

- `/soling/oversikt`
- `/soling/sammenligning`
- `/soling/dagslinje`
- `/soling/enkeltimer`
- `/soling/oppgjor`
- `/soling/oppgjor/:settlementId`
- `/soling/prognose`
- `/soling/produkter`
- `/soling/senger`
- `/soling/medlemmer`
- `/soling/statistikk`
- `/soling/detaljer`

### Koble

- `/koble/oversikt`
- `/koble/sun2`
- `/koble/biltreff`
- `/koble/kandidater`
- `/koble/treffgrunnlag`
- `/koble/jobb`

Koble bruker sideappen `parking_sun_linker`, men all styring, status og manuell bekreftelse skjer i Fibaro10-grensesnittet.

### Energi

- `/energi/status`
- `/energi/elvia-kontroll`
- `/energi/kurser`
- `/energi/laster`
- `/energi/forbruk-per-seng`
- `/energi/elvia`
- `/energi/verktoy`

### Ventilasjon og lys

- `/ventilasjon/dagslogg`
- `/ventilasjon/temp-logg`
- `/ventilasjon/yr-logg`
- `/ventilasjon/hendelser`
- `/ventilasjon/innstillinger`
- `/lys/dagslogg`
- `/lys/lux-logging`
- `/lys/hendelser`
- `/lys/innstillinger`

### Solrom, dører, renhold og vedlikehold

- `/solrom/oversikt`
- `/solrom/dagskontroll`
- `/solrom/rom` finnes som skjult detaljrute fra solromkort.
- `/dorer2/oversikt`
- `/dorer2/rom` finnes som skjult detaljrute fra Dører2-romkort.
- `/dorer2/bygg`
- `/dorer/oversikt`
- `/dorer/andre`
- `/dorer/radata`
- Eldre solrom-/romkontrollruter under `/dorer` er synlige igjen for sammenligning mens designet vurderes.
- `/renhold/oversikt`
- `/renhold/roboter`
- `/vedlikehold/oversikt`
- `/vedlikehold/besok`
- `/vedlikehold/besok/:visitId`

Vedlikehold/Besøk henter Lilletorget-opphold fra OwnTracks via Fibaro10 og kobler vedlikeholdsoppgaver til riktig besøk.

### System

- `/ideer/oversikt`
- `/ideer/kontroll`
- `/ideer/innsikt`
- `/ideer/automatisering`
- `/ideer/arbeidsflyt`
- `/mobil/oversikt`
- `/manual/oversikt`
- `/manual/daglig-bruk`
- `/manual/menyvalg`
- `/manual/okonomi`
- `/manual/bygg-drift`
- `/manual/system`
- `/manual/datagrunnlag`
- `/manual/rutiner`
- `/manual/feilsoking`
- `/admin/oppgaver`
- `/admin/kontroll`
- `/admin/datakvalitet`
- `/admin/analyse`
- `/admin/drift`
- `/admin/build`
- `/admin/build/:build`
- `/admin/datakilder`
- `/admin/datakilder/:jobName`
- `/admin/systemkart`
- `/admin/ai`
- `/admin/teknisk`
- `/admin/brukere`
- `/admin/verktoy`

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
- `GET /api/status/comparison`
- `GET /api/revenue/month?month=YYYY-MM`
- `GET /api/omsetning/year-comparison`
- `GET /api/parkering/year-comparison`
- `GET /api/soling/year-comparison`
- `GET /api/modules/{module}?view={view}`
- `GET /api/parking/vehicles/{plate}`
- `GET /api/admin/builds`
- `GET /api/admin/builds/{build}`
- `GET /api/import-status/{jobName}`
- `POST /api/actions/...` for operative handlinger

FastAPI server React-appen fra `desktop_v2/dist/index.html` på alle hovedrutene. Ingest/API-ruter for HC3, EasyPark, SUN2, Roborock, Axis og underapper skal holdes stabile.

## Docker/QNAP

`Dockerfile` har egen Node-buildstage:

1. Installerer `desktop_v2` med `npm ci`.
2. Kjører `npm run build`.
3. Kopierer `desktop_v2/dist` inn i Python-containeren.

Det betyr at en ny maskin eller QNAP kan bygge desktopflaten direkte fra Git uten lokale buildfiler.

## Kvalitetssjekk

Før deploy skal standard sjekk kjøres:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-local.ps1
```

Dette dekker Python-tester, TypeScript, Vite-build, OwnTracks-build, CSS-parse/audit, bundle-audit, route-audit og UI-smoke.

## Videre utvikling

- Nye sider skal legges i eksisterende hovedgruppe og ha én tydelig rolle.
- Store datalister skal respektere valgt antall/range, og detaljer skal hentes på undersider når mulig.
- Ikke koble desktopflaten mot `online_dashboard`; bruk hovedappens database/API.
- Hold underapper separate der det gir stabilitet: OwnTracks, vedlikehold mobil, iPad, Axis, kjøretøyoppslag og Koble worker.
