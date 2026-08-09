# Lilletorget Omsetning

Selvstendig, skrivebeskyttet fagapplikasjon for omsetning. Appen kjører ved
siden av Fibaro10 på `https://app.lilletorget.net/omsetning/`.

## Ansvar

- omsetningsdashboard med samme datatidspunkt som Fibaro10
- ukesutvikling og topplister
- akkumulert periodesammenligning
- årssammenligning
- månedsoversikt

Backend-proxyen tillater kun disse Fibaro10-kallene:

- `GET /api/auth/me`
- `GET /api/overview`
- `GET /api/modules/omsetning`
- `GET /api/status/comparison`
- `GET /api/omsetning/year-comparison`
- `GET /api/revenue/month`

Innlogging valideres av Fibaro10 og bruker samme brukerkontoer.

## Frontend

- React 19 og TypeScript
- Vite 6
- Tailwind CSS 4
- kjøpt og lisensiert Mosaic React-mal fra Cruip som komplett designsystem
- Mosaic sine SVG-ikoner og komponentmønstre
- Mosaic sine Chart.js-komponenter for interaktive diagrammer
- Mosaic lyst og mørkt tema, med systemtema som standard og lagret manuelt valg

Mosaic-grunnlaget ligger i den felles pakken `packages/mosaic-theme`. Appen har
bare en minimal Tailwind-inngang som genererer klassene den selv bruker. Inter
leveres lokalt som en hash-navngitt WOFF2-fil og krever ingen ekstern fonttjeneste.

## Lokal kontroll

```powershell
cd revenue_app/frontend
npm ci
npm run build
npm audit --audit-level=moderate
cd ../..
python -m unittest revenue_app.tests.test_main
```

## Isolert deploy

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy-revenue-app-qnap.ps1
```

Deployskriptet bygger og erstatter bare `revenue_app` og restarter ikke
Fibaro10 eller andre fagapper.
