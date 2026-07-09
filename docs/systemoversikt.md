# Systemoversikt

Oppdatert 10.07.2026.

Dette dokumentet beskriver hva Fibaro10-installasjonen består av nå. Kildene er `docker-compose.qnap.yml`, `Caddyfile`, `system_inventory.py`, `import_jobs.py` og siste QNAP-status.

## Nøkkeltall

- 18 dokumenterte systemkomponenter i `system_inventory.py`.
- 16 komponenter er aktive i daglig drift eller som aktivt verktøy.
- 14 komponenter har webflate eller lokal statusflate. Tabellen under slår `fibaro10` og `desktop_v2` sammen som én hovedflate.
- 22 datakilder/importjobber er definert i `import_jobs.py`.
- Produksjonsbuild ved siste sjekk: Fibaro10 build `1507`.
- QNAP-appmappe: `/share/CACHEDEV1_DATA/Public/containerdata/fibaro10`.
- Backup/arkivvolum: `/share/CACHEDEV3_DATA/fibaro10_archive`.

## Webflater

| Flate | URL | Formål |
| --- | --- | --- |
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
| `online_dashboard` | Høy | Ekstern begrenset dashboardflate. |
| `maintenance_mobile` | Normal | Mobil vedlikeholdsregistrering mot Fibaro10 API. |
| `fibaro10ipad` | Normal | iPad-grensesnitt mot Fibaro10 API. |
| `owntracks_service` | Normal | HTTP-mottak, PostgreSQL-basert OwnTracks-app og API. |
| `owntracks_postgres` | Høy | PostgreSQL-database for OwnTracks. |
| `axis_camera_snapshots` | Høy | Tar Axis-bilder hvert 5. sekund i åpningstidsvindu og rydder buffer. |
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
- Deploy-backuper lagres i `/share/CACHEDEV3_DATA/fibaro10_archive/fibaro10_deploy_backups`.
- Nattlig/manuel full backup håndteres av `scripts/qnap-backup.sh`.
- Restore-test kjøres fra Windows med `scripts/verify-qnap-backup.ps1`.

## Kvalitetssjekk

Standard deploy går gjennom:

1. `scripts/check-local.ps1`
2. Git push til `main`
3. QNAP backup av runtimefiler/data
4. `docker compose up -d --build` for relevante tjenester
5. Health-check
6. Smoke-check
7. Innlogget live-smoke gjennom desktop-rutene

Dette er den normale veien for å holde produksjon og dokumentert systemtilstand synkronisert.
