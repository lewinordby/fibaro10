# Lilletorget Parkering

Selvstendig fagapplikasjon for parkering. Appen kjører ved siden av Fibaro10
på `https://parkering.lilletorget.net:8443` og bruker Fibaro10 som avgrenset data- og
autentiserings-API.

## Funksjoner

- oversikt, ukesutvikling og topplister
- alle parkeringer per dag med kjøretøy, historikk og UniFi-lenker
- visuell dagslinje med 23 plasser og fast beleggsakse
- kjøretøysøk, kjøretøydetaljer, områder og datakvalitet
- parkeringsprognose og Park Nordic-oppgjør
- akkumulert årssammenligning med valgbare år
- tidspunktfordeling og ukesnitt per parkering

Backend-proxyen tillater bare parkeringsrelaterte Fibaro10-kall. Innlogging
valideres av Fibaro10 og bruker samme brukerkontoer.

## Frontend

- React 19, TypeScript, Vite 6 og Tailwind CSS 4
- kjøpt og lisensiert Mosaic React-mal fra Cruip
- Mosaic lyst og mørkt tema samt Chart.js-grafer
- parkeringsfargen er Mosaics godkjente `sky`-farge

Mosaic-grunnlaget ligger i den felles pakken `packages/mosaic-theme`. Appen har
bare en minimal Tailwind-inngang som genererer klassene den selv bruker. Inter
leveres lokalt som en hash-navngitt WOFF2-fil og krever ingen ekstern fonttjeneste.

## Lokal kontroll

```powershell
cd parking_app/frontend
npm ci
npm run build
npm audit --audit-level=moderate
cd ../..
python -m unittest parking_app.tests.test_main
```

## Isolert deploy

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy-parking-app-qnap.ps1
```

Deployskriptet bygger og erstatter bare `parking_app`.
