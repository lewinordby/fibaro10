# API-kontrakter

Oppdatert 29.08.2026.

Løsningen har tre kontraktlag:

1. Fibaro10-kjernen eier data, regler og hoved-API.
2. Adapterne på port 8151-8158 avgrenser hvilke endepunkter hver Mantis-app kan bruke.
3. `lilletorget-mantis/packages/platform` eier TypeScript-typer, API-klient og fagvisninger.

Når en payload endres, skal backendtype, adapterens tillatelsesliste og Mantis-typen
kontrolleres i samme build.

## Viktige kontrakter

| Endpoint | Backend | Mantis | Formål |
| --- | --- | --- | --- |
| `GET /health` | `HealthPayload` | health-kontrakt | Container- og deploykontroll. |
| `GET /api/admin/builds` | `BuildLogResponsePayload` | buildliste | Lett liste uten fulle bestillinger. |
| `GET /api/admin/builds/{build}` | `BuildLogEntryPayload` | builddetalj | Full bestilling, endringer og tester. |
| `GET /api/modules/{module}` | `ModulePayload` | modulkontrakt | Kort, grafer, tabeller, handlinger og filtre. |
| `GET /api/overview` | dashboardpayload | oversiktskontrakt | Omsetning, parkering, soling og drift. |
| `GET /api/import-status/{jobName}` | importstatus | datakildedetalj | Historikk, feil og neste kjøring. |
| `GET /api/status/comparison` | sammenligning | sammenligningskontrakt | Akkumulert dag, uke og måned. |
| `GET /api/*/year-comparison` | årssammenligning | fagspesifikke typer | Omsetning, parkering og soling. |
| `GET /api/energy/hc3-devices` | HC3-inventar | energi-kontrakt | Enheter og siste kjente verdier. |
| `GET /api/energy/nodes/live` | liveverdier | energi-kontrakt | Effekt og bryterstatus. |
| `POST/PATCH /api/energy/nodes` | `V2EnergyNodeIn` | `EnergyNodeInput` | Energitopologi. |
| `POST/PATCH /api/energy/loads` | `V2EnergyLoadIn` | last-input | Laster og teoretisk effekt. |

## Adapterregler

- Adapterne har ingen HTML-frontend eller statiske frontendfiler.
- Ukjente ruter skal gi `404` og ukjente API-ruter skal ikke videresendes.
- Innlogging valideres i Fibaro10 og bruker den felles opake sesjonscookien.
- Delte HTTP-klienter skal ikke lagre cookies mellom forespørsler.
- Skrivekall krever gyldig origin og brukerrettighet.
- Ressursstier som bilder og vedlegg beholder store og små bokstaver.

## Kvalitetssjekk

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-local.ps1
```

Mantis kontrolleres i eget repo med `npm run verify`. Endringer som berører begge
repoer skal bestå begge kvalitetsportene før deploy.
