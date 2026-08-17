# Dokumentasjonsoversikt

Oppdatert 17.08.2026, build 1795.

Dette er inngangen til dokumentasjonen for Lilletorget-plattformen. Gjeldende
brukerflate er Mantis-serien på `https://ny.lilletorget.net`. Fibaro10-repoet
eier fortsatt API, database, forretningsregler, bakgrunnsjobber, integrasjoner
og flere separate mobil- og datatjenester.

## Fasit og prioritet

Når dokumenter sier forskjellige ting, brukes denne rekkefølgen:

1. `System -> Datakilder` for operativ status og siste kjøring.
2. `System -> Systemkart` for tjenester, avhengigheter og webflater.
3. `System -> Manual` for gjeldende bruk av løsningen.
4. `packages/platform/src/app-definitions.json` i Mantis-repoet for aktive
   apper, ruter og menystruktur.
5. Compose, Caddy og tjenestekode for tekniske detaljer.

## Levende dokumentasjon

| Side | Adresse | Bruk |
| --- | --- | --- |
| Manual | `https://ny.lilletorget.net/system/manual` | Gjeldende bruker- og driftsmanual med kapitler. |
| Menystruktur | `https://ny.lilletorget.net/system/manual/menystruktur` | Alle elleve apper og aktive sider. |
| Datakilder | `https://ny.lilletorget.net/system/datakilder` | Status, rytme, avhengigheter og siste feil per datakilde. |
| Systemkart | `https://ny.lilletorget.net/system/systemkart` | Komponenter, tjenester og forbindelser. |
| Undersystemer | `https://ny.lilletorget.net/system/undersystemer` | Klikkbare lenker til webflater og health-endepunkter. |
| Buildlogg | `https://ny.lilletorget.net/system/build` | Bestilling, endringer, apper, tester og deploy per build. |

## Gjeldende dokumenter

| Fil | Innhold |
| --- | --- |
| `docs/kort-brukermanual.md` | Kort operativ manual med gjeldende Mantis-stier. |
| `docs/systemoversikt.md` | Komponenter, webflater, porter, proxy, datakilder og backup. |
| `docs/mikroapp-porter.md` | Skillet mellom Mantis på 8170 og fag-API-ene på 8151-8158. |
| `docs/intern-https.md` | DNS, TLS, intern tilgang og PWA på `ny.lilletorget.net`. |
| `docs/utviklingsoppsett.md` | Lokal utvikling, test, deploy til QNAP, backup og restore. |
| `docs/api-kontrakter.md` | Backend/frontend-kontrakter og typed payloads. |
| `docs/MICROAPP_PARITY.md` | Funksjonskontroll mellom reserveflaten og fagappene. |
| `docs/arbeidsflater-2026-08-17.md` | Operasjonssentral, eiendeler, rapporter og analyseinnganger. |

Den tekniske PDF-en genereres fra
`scripts/generate-system-documentation-pdf.py` til
`output/pdf/lilletorget-systemarkitektur-og-teknisk-dokumentasjon.pdf`.

## Fagdokumentasjon

| Fil | Område |
| --- | --- |
| `docs/owntracks-http.md` | OwnTracks HTTP, waypoints, PostgreSQL og besøk. |
| `docs/axis-camera-snapshots.md` | Axis-arkiv, tidsvinduer og bilder på soltimer. |
| `docs/car-info-oppslag.md` | Norske, svenske og danske kjøretøyoppslag. |
| `docs/hc3-dorer.md` | Dørsensorer, logger-scener, statuskontroll og alarmer. |
| `docs/hc3-energi-oppsamlinger.md` | HC3-energigrupper, enheter, medlemmer og hull. |
| `docs/sun2-enkeltimer.md` | SUN2-timer, romidentitet, energi og bilder. |
| `docs/roborock-logger.md` | Lokal Roborock-tjeneste og drift. |
| `docs/roborock-datakilder.md` | Tilgjengelige Roborock-kilder og felt. |
| `docs/roborock-telemetri.md` | Telemetrifelt, intervaller og modellstøtte. |
| `docs/dreame-logger.md` | Aqua10/Dreame-tjeneste, dataflyt og drift. |
| `docs/render-online-dashboard.md` | Ekstern, begrenset dashboardflate. |

## Tjenester med egen README

`maintenance_mobile`, `alarm_mobile`, `car_info_lookup`,
`easypark_downloader`, `roborock_logger`, `dreame_logger`,
`sun2_session_scraper`, `sun2_importer`, `sun2_backfill_downloader`,
`hc3_vedlikehold`, `parking_sun_linker` og nettlesertilleggene har egne
README-filer ved kildekoden.

## Historiske referanser

Følgende dokumenter beskriver tidligere brukerflater. De beholdes for
funksjonskontroll og historikk, men skal ikke brukes som dagens navigasjonsmanual:

| Fil | Historisk rolle |
| --- | --- |
| `docs/desktop-v2.md` | Samlet Fibaro10 Desktop V2 på port 8110. |
| `docs/funksjonsstruktur.md` | Meny- og sideprinsipper fra V2-generasjonen. |
| `docs/kvalitetsstatus-2026-08-07.md` | Daterte testresultater for den daværende løsningen. |
| `static/manualer/sun2_driftsmanual.pdf` | Eldre statisk driftsmanual; nettmanualen er gjeldende. |

Historiske URL-er under `app.lilletorget.net`, `fibaro10.lilletorget.net` og
rene V2-ruter kan fortsatt finnes i disse dokumentene med vilje.

## Dokumentasjonsregel

En endring i apper, ruter, porter, datakilder, deploy eller backup er ikke ferdig
før nettmanualen og relevante repo-dokumenter er oppdatert i samme build.
Dokumentasjonskontrollene kjøres som del av ordinær test og Mantis `npm run verify`.
