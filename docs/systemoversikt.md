# Systemoversikt

Oppdatert 02.08.2026.

Dette dokumentet beskriver hva Fibaro10-installasjonen består av nå. Kildene er `docker-compose.qnap.yml`, `Caddyfile`, `system_inventory.py`, `import_jobs.py` og siste QNAP-status.

## Nøkkeltall

- 29 dokumenterte systemkomponenter i `system_inventory.py`.
- 26 komponenter er aktive i daglig drift eller som aktivt verktøy.
- 24 komponenter har webflate eller lokal statusflate.
- 23 datakilder/importjobber er aktive i Fibaro10.
- Produksjonsbuild ved siste sjekk: Fibaro10 build `1629`.
- QNAP-appmappe: `/share/CACHEDEV1_DATA/Public/containerdata/fibaro10`.
- Backup/arkivvolum: `/share/CACHEDEV3_DATA/fibaro10_archive`.

## Webflater

| Flate | URL | Formål |
| --- | --- | --- |
| Lilletorget-skall | `http://192.168.20.218:8150/` | Felles intern appvelger og live tjenestestatus. |
| Omsetning | `http://192.168.20.218:8151/` | Utskilt fagapp for omsetning og sammenligning. |
| Parkering | `http://192.168.20.218:8152/` | Utskilt fagapp for parkeringer, kjøretøy, oppgjør og analyse. |
| Soling | `http://192.168.20.218:8153/` | Soltimer, dagslinje, bilder, produkter, medlemmer og oppgjør. |
| Energi | `http://192.168.20.218:8154/` | Sanntidsforbruk, Elvia, kurs/last og analyse per solseng. |
| Bygg og drift | `http://192.168.20.218:8155/` | Ventilasjon, lys, dører, solrom, pullerter og renhold. |
| Vedlikehold | `http://192.168.20.218:8156/` | Besøk, oppgaver og vedlikeholdshistorikk. |
| System | `http://192.168.20.218:8157/` | Datakilder, brukere, build, manual, varslinger og systemstatus. |
| Koble | `http://192.168.20.218:8158/` | Kandidater og kontroll av koblinger mellom biler og Sun2-ID. |
| Fibaro10 hovedapp | `http://192.168.20.218:8110/` | Daglig drift, V2 desktop, API og admin. |
| Online dashboard | `https://online.lilletorget.net/` | Ekstern begrenset mobil/dashboardflate. |
| Vedlikehold mobil | `https://vedl.lilletorget.net/` | Rask mobilregistrering av vedlikeholdsoppgaver. |
| Fibaro10 iPad | `https://ipad.lilletorget.net/` | iPad-tilpasset dashboardflate. |
| OwnTracks | `https://owntracks.lilletorget.net/` | Lokasjonsmottak, waypoints, opphold og sonebesøk. |
| Axis snapshots | `http://192.168.20.218:8125/` | Lokal status/test for snapshot-service. |
| Nordiske kjøretøyoppslag | `http://192.168.20.218:8126/` | Lokal status/API for svenske og danske biloppslag. |
| SUN2 enkelttimer | `http://192.168.20.218:8099/` | Lokal status/API for session scraper. |
| EasyPark downloader | `http://192.168.20.218:8109/status` | Lokal statusflate for EasyPark-nedlasting. |
| Koble worker | `http://192.168.20.218:8127/` | Lokal status/API for parkering/SUN2-koblingsmotor. |
| Roborock logger | `http://192.168.20.218:8095/` | Lokal status/API for robotstøvsugere og sync. |
| SUN2 importer | `http://192.168.20.218:8096/` | Verktøy for historiske/daglige SUN2-romsummer. |
| SUN2 backfill | `http://192.168.20.218:8097/` | Verktøy for historisk SUN2-filnedlasting. |

## Docker-tjenester på QNAP

| Tjeneste | Kritikalitet | Formål |
| --- | --- | --- |
| `fibaro10` | Kritisk | FastAPI backend, V2 frontend, database-API, admin og ingest. |
| `shell_app` | Normal | Intern appvelger, live tjenestestatus og felles inngang til mikroappene. |
| `online_dashboard` | Høy | Ekstern begrenset dashboardflate. |
| `maintenance_mobile` | Normal | Mobil vedlikeholdsregistrering mot Fibaro10 API. |
| `fibaro10ipad` | Normal | iPad-grensesnitt mot Fibaro10 API. |
| `revenue_app` | Normal | Fagapp for omsetning på egen port og med egen build. |
| `parking_app` | Høy | Utskilt parkeringsapp med daglig drift, kjøretøy, oppgjør og analyse på egen port og med egen build. |
| `sun_app` | Høy | Utskilt app for soltimer, bilder, produkter, oppgjør og analyse. |
| `energy_app` | Høy | Utskilt app for energi, Elvia, kurs/last og solsengforbruk. |
| `operations_app` | Høy | Utskilt app for ventilasjon, lys, dører, pullerter og renhold. |
| `maintenance_app` | Normal | Utskilt app for besøk og vedlikeholdsoppgaver. |
| `system_app` | Normal | Utskilt app for administrasjon, datakilder, manual og build. |
| `link_app` | Normal | Utskilt kontrollflate for koblingsmotoren. |
| `owntracks_service` | Normal | HTTP-mottak, PostgreSQL-basert OwnTracks-app og API. |
| `owntracks_postgres` | Høy | PostgreSQL-database for OwnTracks. |
| `axis_camera_snapshots` | Høy | Tar Axis-bilder hvert 5. sekund i åpningstidsvindu og rydder buffer. |
| `unifi_protect_events` | Høy | Lokal Protect Ledger, kameraarkiv og klassisk pullert-/trappekontroll. |
| `visual_anomaly_service` | Normal | CPU-basert lokal PatchCore-kontroll av tre pullertflater og trappa. |
| `car_info_lookup` | Normal | Svenske Biluppgifter og danske Tjekbil-oppslag etter SVV. |
| `sun2_session_scraper` | Kritisk | Løpende SUN2 enkelttimer, senger, medlemmer, produkter og finansgrunnlag. |
| `sun2_importer` | Lav/verktøy | Aktiv container som importerer SUN2 dagsfiler og romsummer. |
| `sun2_backfill_downloader` | Lav/verktøy | Aktiv container som laster ned historiske SUN2 dagsfiler. |
| `roborock_logger` | Normal | Separat compose/container for Roborock-status, historikk, planer og kartdata. |
| `parking_sun_linker` | Høy | Bakgrunnsmotor for kobling mellom parkeringer og SUN2-brukere. |
| `fibaro10_proxy` | Kritisk | Caddy reverse proxy for `online`, `vedl`, `ipad` og `owntracks`. |
| `easypark_downloader` | Kritisk | Separat compose/app for EasyPark-nedlasting og importtrigger. |

## Offentlig proxy

`Caddyfile` eksponerer disse domenene:

| Domene | Intern tjeneste | Kommentar |
| --- | --- | --- |
| `online.lilletorget.net` | `online_dashboard:8111` | Begrenset ekstern flate. |
| `owntracks.lilletorget.net` | `owntracks_service:8128` | Tokenbeskyttet OwnTracks. Direkte interne `/api/owntracks/*` skjules eksternt. |
| `vedl.lilletorget.net` | `maintenance_mobile:8112` | Samme brukerbase som Fibaro10. |
| `ipad.lilletorget.net` | `fibaro10ipad:8113` | Samme brukerbase som Fibaro10. |
| `192.168.20.218:8150` | `shell_app:8150` | Felles intern inngang og appvelger. |
| `192.168.20.218:8151` | `revenue_app:8151` | Intern omsetningsapp. Samme brukerbase som Fibaro10. |
| `192.168.20.218:8152` | `parking_app:8152` | Intern parkeringsapp. Samme brukerbase som Fibaro10. |
| `192.168.20.218:8153` | `sun_app:8153` | Intern solingsapp. Samme brukerbase som Fibaro10. |
| `192.168.20.218:8154` | `energy_app:8154` | Intern energiapp. Samme brukerbase som Fibaro10. |
| `192.168.20.218:8155` | `operations_app:8155` | Intern bygg- og driftsapp. Samme brukerbase som Fibaro10. |
| `192.168.20.218:8156` | `maintenance_app:8156` | Intern vedlikeholdsapp. Samme brukerbase som Fibaro10. |
| `192.168.20.218:8157` | `system_app:8157` | Intern systemapp. Samme brukerbase som Fibaro10. |
| `192.168.20.218:8158` | `link_app:8158` | Intern Koble-app. Samme brukerbase som Fibaro10. |

## Datakilder

| Nr | Jobb | Kategori | Kilde | Forventet rytme |
| --- | --- | --- | --- | --- |
| 1 | Lys / lux fra HC3 | Lys | HC3 | ca. 7 min |
| 2 | Ventilasjon / temperatur fra HC3 | Ventilasjon | HC3 | ca. 7 min |
| 3 | Yr API | Vær | MET/Yr | ca. 70 min |
| 4 | Energi fra HC3 | Energi | HC3 | ca. 2 min statusgrense, data logges hvert 30. sekund |
| 5 | Roborock logger | Renhold | QNAP | ca. 10 min |
| 6 | Sun2 dagsfil nedlasting | Soling | QNAP | ca. 36 timer |
| 7 | Sun2 dagsimport rom | Soling | QNAP | ca. 36 timer |
| 8 | Sun2 enkelttimer | Soling | QNAP | ca. 7 min |
| 9 | Sun2 senger | Soling | QNAP | ca. 7 dager |
| 10 | Sun2 medlemmer | Soling | QNAP | ca. 7 dager |
| 11 | Sun2 produktsalg daglig | Soling | QNAP | ca. 36 timer |
| 12 | Sun2 produktsalg månedskontroll | Soling | QNAP | ca. 40 dager |
| 13 | Sun2 finansoppgjør | Soling | QNAP | ca. 40 dager |
| 14 | Elvia månedsfil | Energi | Manuell opplasting | ca. 40 dager |
| 15 | EasyPark import | Parkering | EasyPark | planlagte importtidspunkt, health-grense ca. 26 timer |
| 16 | Parkering historikk | Parkering | QNAP appdb | migrert arkivgrunnlag |
| 17 | Kjøretøydata fra SVV | Parkering | Statens vegvesen | ca. 30 min |
| 18 | Biluppgifter Sverige | Parkering | Biluppgifter.se | event/backlog etter SVV uten treff |
| 19 | Tjekbil Danmark | Parkering | Tjekbil.dk | event/backlog etter SVV uten treff |
| 20 | Koble parkering/SUN2 | Koble | `parking_sun_linker` | ca. 10 min |
| 21 | OwnTracks Lilletorget-besøk | Vedlikehold | OwnTracks | ca. 2 min |
| 22 | Dørhendelser fra HC3 | Bygg og drift | HC3 | hendelsesstyrt |

`Admin -> Datakilder` er operativ fasit for status, siste kjøring, alder, feilmelding og forklaring per kilde.

## Lagring og backup

- Hovedappen bruker PostgreSQL via miljøvariabelen `DATABASE_URL`.
- OwnTracks bruker egen PostgreSQL-container `owntracks_postgres`.
- Axis snapshot-buffer ligger på eget arkivvolum via `AXIS_HOST_SNAPSHOT_DIR`.
- Protect-bilder ligger på SSD-arkivvolumet via `UNIFI_PROTECT_HOST_SNAPSHOT_DIR`.
- AI-modeller og kalibreringsmetadata ligger på SSD via `VISUAL_AI_HOST_DATA_DIR` og tas med i nattlig backup.
- Deploy-backuper lagres i `/share/CACHEDEV3_DATA/fibaro10_archive/fibaro10_deploy_backups`.
- Nattlig/manuel full backup håndteres av `scripts/qnap-backup.sh` og inkluderer separate SQL-dumper for Fibaro10 og OwnTracks samt Roborock-data.
- Restore-test kjøres fra Windows med `scripts/verify-qnap-backup.ps1` og leser begge SQL-dumpene inn i midlertidige databaser.

## Kvalitetssjekk

Standard deploy går gjennom:

1. `scripts/check-local.ps1`
2. Git push til `main`
3. QNAP backup av runtimefiler/data
4. Compose-validering og `docker compose up -d --build` for kjernen, fagappene og alle aktive importer-/bakgrunnstjenester
5. Health-check av 24 HTTP-endepunkter, 23 datakilder og alle forventede containere
6. Smoke-check av interne flater, importører og eksterne proxyadresser
7. Innlogget live-smoke gjennom desktop- og fagapprutene, med p50/p95-måling

Den lokale kontrollen kompilerer all sporet Python-kode og kjører også testene for vedlikeholdsmobil, Protect/pullerter og faste AI-profiler. Frontendkontrollen kjører `npm audit` for alle aktive flater. Hovedflaten
har et eksplisitt avvik for React Router-rådet `GHSA-qwww-vcr4-c8h2`, fordi
rådet bare gjelder RSC-modus mens Fibaro10 bruker ren `BrowserRouter` uten
React Server Components eller router-actions. Alle øvrige funn på moderat
eller høyere nivå stopper kontrollen.

Mikroappene har i tillegg egne, raskere løp:

- `scripts/deploy-domain-app-qnap.ps1` for én app.
- `scripts/deploy-all-domain-apps-qnap.ps1` for alle fagappene.
- `scripts/smoke-domain-apps.ps1` for alle registrerte fagappruter.

Dette er den normale veien for å holde produksjon og dokumentert systemtilstand synkronisert.
