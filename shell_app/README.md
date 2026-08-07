# Lilletorget-skall

Intern inngang til de brukerrettede mikroappene. Skallet kjører på
`https://app.lilletorget.net:8443` og inneholder bare appregister, helsestatus,
innlogging og navigasjon.

Skallet har ingen fagdata eller forretningslogikk. Det validerer brukeren mot
Fibaro10 og måler aktive tjenester gjennom deres `/health`-endepunkter.

## Frontend

- React 19 og TypeScript
- Vite 6
- Tailwind CSS 4
- Kjøpt og lisensiert Mosaic React-mal fra Cruip som komplett designsystem
- Mosaic sine SVG-ikoner, komponentmønstre og lyse/mørke tema
- Ingen lokal visuell profil, logo eller tillegg-CSS

Mosaic-grunnlaget ligger i den felles pakken `packages/mosaic-theme`. Appen har
bare en minimal Tailwind-inngang som genererer klassene den selv bruker. Inter
leveres lokalt som en hash-navngitt WOFF2-fil og krever ingen ekstern fonttjeneste.

## Lokal kontroll

```powershell
cd shell_app/frontend
npm install
npm run build
npm audit --audit-level=moderate
cd ../..
python -m unittest shell_app.tests.test_main
```

## Isolert deploy

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy-shell-app-qnap.ps1
```

Deployskriptet bygger og erstatter bare `shell_app` og restarter ikke Fibaro10
eller andre fagapper.
