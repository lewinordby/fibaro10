# API-kontrakter

Dette prosjektet har to tydelige kontraktflater mellom backend og desktop-frontend:

- `api_types.py` eier Python-typene for backendpayloads som brukes på tvers av moduler.
- `desktop_v2/src/api.ts` eier TypeScript-typene som frontenden bruker når den kaller backend.

Når et API-endepunkt endrer struktur, skal begge filene oppdateres i samme build. Backendfunksjoner som bygger egne payloads bør returnere typer fra `api_types.py`, ikke bare `Dict[str, Any]`.

Kontrakter som er typefestet nå:

- `/api/admin/builds`
- `/api/admin/builds/{build}`
- `/health`

Lokal kvalitetssjekk kjører Python-kompilering, Python unit-tester, TypeScript typecheck, Vite build, UI smoke-test og whitespace-sjekk:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-local.ps1
```
