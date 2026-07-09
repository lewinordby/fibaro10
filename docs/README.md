# Dokumentasjonsoversikt

Oppdatert 10.07.2026.

Dette repoet dokumenterer hovedappen `Fibaro10 / Lilletorget drift`, underappene som kjører ved siden av den, HC3-scriptene og importjobbene som fyller databasen.

## Levende dokumentasjon i appen

| Side | Bruk |
| --- | --- |
| `Admin -> Manual` | Sluttbruker- og driftsinnganger for daglig bruk. |
| `Admin -> Systemkart` | Klikkbar oversikt over apper, underapper, webflater, lokale URL-er og health-lenker. |
| `Admin -> Datakilder` | Operativ status for alle importjobber og eksterne datakilder. |
| `Admin -> Buildlogg` | Leveransehistorikk med bestilling, endringer, berørte applikasjoner og måledata per build. |
| `Admin -> Teknisk` | Teknisk driftsflate og verktøykoblinger. |

`/konto/manual` finnes fortsatt som redirect til `/admin/manual`.

## Viktige dokumenter i repoet

| Fil | Innhold |
| --- | --- |
| `docs/systemoversikt.md` | Dagens systemkart: komponenter, webflater, porter, proxy, datakilder og backup. |
| `docs/utviklingsoppsett.md` | Lokal utvikling på Windows, ny PC, deploy til QNAP, smoke, backup og restore-test. |
| `docs/desktop-v2.md` | Faktisk V2-meny, ruter, frontendstruktur og API-flater. |
| `docs/funksjonsstruktur.md` | Prinsipper og gjeldende funksjonsdeling for hovedmenyene. |
| `docs/api-kontrakter.md` | Backend/frontend-kontrakter, typed payloads og kvalitetssjekk. |
| `docs/owntracks-http.md` | Separat OwnTracks HTTP-tjeneste, token, waypoints, PostgreSQL og Fibaro10-integrasjon. |
| `docs/axis-camera-snapshots.md` | Axis snapshot-arkiv, åpningstidsvindu og kobling av bilder til soltimer. |
| `docs/car-info-oppslag.md` | Svenske og danske kjøretøyoppslag etter SVV. |
| `docs/hc3-dorer.md` | HC3 magnetfølere, dørlogger-scener og klargjorte solrom/byggdører. |
| `docs/hc3-energi-oppsamlinger.md` | HC3 energigrupper og undermålere. |
| `docs/sun2-enkeltimer.md` | SUN2 enkelttimer, romidentitet og kobling mot energi/bilder. |
| `docs/roborock-logger.md` | Drift av lokal Roborock-logger på QNAP/Docker. |
| `docs/roborock-datakilder.md` | Hvilke Roborock-data som kan hentes fra cloud og lokal LAN. |
| `docs/render-online-dashboard.md` | Notater om ekstern online dashboard-flate. |

## Underapper med egen README

| Mappe | Innhold |
| --- | --- |
| `maintenance_mobile/README.md` | Mobil vedlikeholdsapp på `vedl.lilletorget.net`. |
| `car_info_lookup/README.md` | Nordiske kjøretøyoppslag. |
| `easypark_downloader/README.md` | EasyPark-nedlasting og påloggingsflyt. |
| `roborock_logger/README.md` | Lokal Roborock-logger og webflate på port 8095. |
| `sun2_session_scraper/README.md` | Løpende skraping/import av SUN2 enkelttimer, produkter og finansgrunnlag. |
| `sun2_importer/README.md` | Import av SUN2 romsummer fra nedlastede dagsfiler. |
| `sun2_backfill_downloader/README.md` | Nattlig og historisk nedlasting av SUN2 romstatistikk. |
| `hc3_vedlikehold/README.md` | Lokal HC3-verktøyapp for energigrupper og loggerkontroll. |
| `axis_camera_snapshots/` | Snapshot-service. Hoveddokumentasjon ligger i `docs/axis-camera-snapshots.md`. |
| `parking_sun_linker/README.md` | Koblingsmotor mellom parkeringer og SUN2-brukere. |
| `browser_extensions/parking_name_lookup/README.md` | Manuelt områdeoppslag via Vegvesen-side. |
| `browser_extensions/parking_manual_name/README.md` | Manuelt navneoppslag for kjøretøy. |
| `migrations/README.md` | Regler for database-migrasjoner. |

## HC3-scener i repoet

| Fil | Bruk |
| --- | --- |
| `scripts/hc3_energy_logger.lua` | Logger HC3 effekt og akkumulert kWh til `/api/energi/fibaro`, inkludert avfukter fra device 449. |
| `scripts/hc3_ventilation_runner_scene_363.lua` | Aktiv ventilasjonsrunner for HC3 scene 363. Logger temperatur/fukt, Yr-fukt og viftestatus. |
| `scripts/hc3_basement_dehumidifier.lua` | Styrer avfukter 449 fra kjellertemperatur 444 og kjellerfukt 445. |
| `scripts/hc3_door_event_logger.lua` | Felles/manuell dørlogger til `/api/hc3/door-events`. |
| `scripts/upsert_hc3_single_door_logger_scenes.py` | Oppretter tynne Lua-logger-scener og block-trigger-scener per dør. |

## Driftsprinsipper

- Fibaro10-grensesnittet viser data fra egen database, ikke direkte fra tredjeparts-API-er.
- HC3 poster lys, ventilasjon, energi og dørhendelser direkte til Fibaro10.
- QNAP/Docker kjører lokale tjenester for SUN2, EasyPark, Axis, kjøretøyoppslag, OwnTracks, iPad, vedlikehold mobil og koblingsmotor.
- `Admin -> Datakilder` er fasit for om en datakilde faktisk går.
- `Admin -> Systemkart` er fasit for hvilke underapper og webflater som inngår.
- Deploy til QNAP skal gå via `scripts/deploy-qnap.ps1`, som kjører lokal sjekk, push, backup, rebuild, health og live-smoke.
- Elvia er manuell månedlig import fordi eksporten krever BankID.
- SUN2/Elvia-tidspunkter behandles som kildens lokale tid, mens Yr/HC3 vises i Europe/Oslo.
