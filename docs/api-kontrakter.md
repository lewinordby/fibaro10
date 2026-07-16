# API-kontrakter

Oppdatert 16.07.2026.

Dette prosjektet har to tydelige kontraktflater mellom backend og desktop-frontend:

- `api_types.py` eier Python-typene for backendpayloads som brukes på tvers av moduler.
- `desktop_v2/src/api.ts` eier TypeScript-typene som frontenden bruker når den kaller backend.

Når et API-endepunkt endrer struktur, skal begge filene oppdateres i samme build.

## Typefestede kontrakter

| Endpoint | Backendtype | Frontendtype | Kommentar |
| --- | --- | --- | --- |
| `GET /health` | `HealthPayload` | `HealthResponse`/healthtyper i `api.ts` | Brukes av QNAP health, smoke og admin. |
| `GET /api/admin/builds` | `BuildLogResponsePayload` med `BuildLogListRowPayload[]` | `BuildLogResponse` med `BuildLogListEntry[]` | Lett liste: build, dato, overskrift, path og aktiv-markering. |
| `GET /api/admin/builds/{build}` | `BuildLogEntryPayload` | `BuildLogEntry` | Full detalj med prompt/bestilling, endringer, applikasjoner og måledata. |
| `GET /api/modules/{module}` | `ModulePayload` | `ModulePayload` | Felles modulkontrakt for kort, grafer, tabeller, handlinger og filtre. |
| `GET /api/overview` | dynamisk dashboardpayload | `OverviewResponse` | Dashboard for omsetning, parkering, soling og drift. |
| `GET /api/import-status/{jobName}` | importstatuspayload | `ImportStatusDetail` | Detaljside for datakilde. |
| `GET /api/status/comparison` | sammenligningspayload | `StatusComparisonResponse` | Akkumulert dag/uke/måned-sammenligning. |
| `GET /api/*/year-comparison` | årssammenligning | egne year comparison-typer | Omsetning, parkering og soling. |
| `GET /api/energy/hc3-devices` | HC3-enhetsliste | `Hc3EnergyDevicesResponse` | Live HC3-inventar med fallback til siste snapshot. |
| `GET /api/energy/nodes/live` | liveverdier per energipunkt | `EnergyNodesLiveResponse` | Effekt og bryterstatus for registrerte HC3-ID-er. |
| `POST/PATCH /api/energy/nodes` | `V2EnergyNodeIn` | `EnergyNodeInput` | Oppretter og redigerer enhet, utgang eller underenhet. HC3-ID-er, egenskaper og unik kobling valideres før lagring. Ved kursflytting følger hele grenen og lastene med. |
| `POST/PATCH /api/energy/loads` | `V2EnergyLoadIn` | `EnergyLoadCreateInput` | Oppretter og redigerer last direkte på kurs eller under energipunkt. Støtter normaliserte profiler for ukjent, fast og variabel effekt. |

## Buildlogg

Buildlogg har bevisst delt kontrakt:

- Listen `/api/admin/builds` skal være liten og rask.
- Detaljen `/api/admin/builds/{build}` skal inneholde hele endringsgrunnlaget.

Dette hindrer at Admin/Buildlogg laster hundrevis av gamle prompts og endringslister bare for å vise tabellen.

## Modulpayload

`ModulePayload` er fleksibel, men skal holdes strukturert:

- `cards`: små nøkkeltall med `title`, `value`, `unit`, `detail`, `tone` og valgfri `href`.
- `charts`: chart-definisjoner som frontend rendrer med ECharts.
- `tables`: tabeller med `title`, `columns`, `rows`, valgfri `edit` og `meta`.
- `actions`: POST/PATCH-handlinger som frontend viser som knapper.
- `filters`: serverstyrte filterfelter.

Store datasett skal ikke sendes på oversiktssider uten eksplisitt behov. Bruk `limit`, dato/range eller egen detaljside.

## Kvalitetssjekk

Standard lokal sjekk:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-local.ps1
```

Denne kjører:

- Python syntax check
- Python unit tests
- desktop V2 TypeScript typecheck og Vite build
- OwnTracks frontend typecheck og build
- CSS parse
- CSS audit
- bundle audit
- route audit
- UI smoke
- Git whitespace check

Innlogget live-smoke kjøres automatisk av `scripts/deploy-qnap.ps1` når `.env.live-smoke` finnes.

## Praktisk regel

Hvis en frontendtype endres i `desktop_v2/src/api.ts`, skal tilsvarende backendkontrakt eller payloadbygger gjennomgås samtidig. Hvis payloaden er stor, mål størrelse og vurder om listen kan deles fra detaljvisningen.
