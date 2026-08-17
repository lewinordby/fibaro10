# Systemoversikt

Oppdatert 17.08.2026.

Dette dokumentet beskriver hva Fibaro10-installasjonen består av nå. Kildene er `docker-compose.qnap.yml`, `Caddyfile`, `system_inventory.py`, `import_jobs.py` og siste QNAP-status.

## Nøkkeltall

- 31 dokumenterte systemkomponenter i `system_inventory.py`.
- 28 komponenter er aktive i dagens runtime eller som aktivt verktøy; Dreame er klargjort for aktivering.
- 26 komponenter har webflate eller lokal statusflate.
- 24 datakilder/importjobber er definert i Fibaro10.
- Produksjonsbuild ved siste sjekk: Fibaro10 build `1793`; commit settes ved deploy.
- QNAP-appmappe: `/share/CACHEDEV1_DATA/Public/containerdata/fibaro10`.
- Backup/arkivvolum: `/share/CACHEDEV3_DATA/fibaro10_archive`.

## Webflater

Den nye Mantis-serien bruker ett internt domene og omfatter elleve selvstendige
applikasjoner: Omsetning, Parkering, Soling, Koble, Bygg og drift, Energi,
Vedlikehold, Operasjonssentral, Eiendeler, Rapporter og System. De tre nyeste
inngangene er:

| Flate | URL | Formål |
| --- | --- | --- |
| Operasjonssentral | `https://ny.lilletorget.net/operasjon/` | Arbeidskø, datakvalitet, automatisering og universalsøk. |
| Eiendeler | `https://ny.lilletorget.net/eiendeler/` | Teknisk register med garanti, service og HC3-kobling. |
| Rapporter | `https://ny.lilletorget.net/rapporter/` | Samlet inngang til økonomi-, drift- og kontrollrapporter. |

| Flate | URL | Formål |
| --- | --- | --- |
| Lilletorget-skall | `https://app.lilletorget.net/` | Felles intern appvelger og live tjenestestatus. |
| Omsetning | `https://app.lilletorget.net/omsetning/` | Utskilt fagapp for omsetning og sammenligning. |
| Parkering | `https://app.lilletorget.net/parkering/` | Utskilt fagapp for parkeringer, kjøretøy, oppgjør og analyse. |
| Soling | `https://app.lilletorget.net/soling/` | Soltimer, dagslinje, bilder, produkter, medlemmer og oppgjør. |
| Energi | `https://app.lilletorget.net/energi/` | Sanntidsforbruk, Elvia, kurs/last og analyse per solseng. |
| Bygg og drift | `https://app.lilletorget.net/drift/` | Ventilasjon, lys, dører, solrom, pullerter og renhold. |
| Vedlikehold | `https://app.lilletorget.net/vedlikehold/` | Besøk, oppgaver og vedlikeholdshistorikk. |
| System | `https://app.lilletorget.net/system/` | Datakilder, brukere, build, manual, varslinger og systemstatus. |
| Koble | `https://app.lilletorget.net/koble/` | Kandidater og kontroll av koblinger mellom biler og Sun2-ID. |
| Fibaro10 reserveflate | `https://fibaro10.lilletorget.net/` | Samlet desktopreserve mot den kritiske Fibaro10-kjernen, kun tilgjengelig internt/VPN. |
| Fibaro10 HTTP-reserve | `http://192.168.20.218:8110/` | Teknisk reserve, API og helsesjekker. |
| Online dashboard | `https://online.lilletorget.net/` | Ekstern begrenset mobil/dashboardflate. |
| Vedlikehold mobil | `https://vedl.lilletorget.net/` | Rask mobilregistrering av vedlikeholdsoppgaver. |
| Alarm mobil | `https://alarm.lilletorget.net/` | Dør-, solrom-, pullert- og trappealarmer med direkte lenker fra ntfy. |
| Fibaro10 iPad | `https://ipad.lilletorget.net/` | iPad-tilpasset dashboardflate. |
| OwnTracks | `https://owntracks.lilletorget.net/` | Lokasjonsmottak, waypoints, opphold og sonebesøk. |
| Axis snapshots | `http://192.168.20.218:8125/` | Lokal status/test for snapshot-service. |
| Nordiske kjøretøyoppslag | `http://192.168.20.218:8126/` | Lokal status/API for svenske og danske biloppslag. |
| SUN2 enkelttimer | `http://192.168.20.218:8099/` | Lokal status/API for session scraper. |
| EasyPark downloader | `http://192.168.20.218:8109/status` | Lokal statusflate for EasyPark-nedlasting. |
| Koble worker | `http://192.168.20.218:8127/` | Lokal status/API for parkering/SUN2-koblingsmotor. |
| Roborock logger | `http://192.168.20.218:8095/` | Lokal status/API for robotstøvsugere og sync. |
| Dreame logger | `http://192.168.20.218:8094/` | Lokal status/API for Aqua10, Dreamehome og sync. |
| SUN2 importer | `http://192.168.20.218:8096/` | Verktøy for historiske/daglige SUN2-romsummer. |
| SUN2 backfill | `http://192.168.20.218:8097/` | Verktøy for historisk SUN2-filnedlasting. |

De tre mobilflatene `online_dashboard`, `maintenance_mobile` og `alarm_mobile`
bruker et felles, kjøpt AppKit Mobile-tema fra `packages/mobile-appkit`. Pakken
eier typografi, farger, safe-area, toppfelt, bunnnavigasjon, skjemaer og
lyst/mørkt systemtema. Appenes dataflyt og domenevisninger ligger fortsatt i
hver enkelt app.

## Docker-tjenester på QNAP

| Tjeneste | Kritikalitet | Formål |
| --- | --- | --- |
| `fibaro10` | Kritisk | FastAPI-kjerne, database-API, admin, ingest og samlet desktopreserve. |
| `shell_app` | Normal | Intern appvelger, live tjenestestatus og felles inngang til mikroappene. |
| `online_dashboard` | Høy | Ekstern begrenset dashboardflate. |
| `maintenance_mobile` | Normal | Mobil vedlikeholdsregistrering mot Fibaro10 API. |
| `alarm_mobile` | Høy | Mobil alarmflate mot dør- og Protect-API-ene i Fibaro10. |
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
| `dreame_logger` | Normal | Separat compose/container for Dreame/Aqua10-status, historikk, planer og styring. |
| `parking_sun_linker` | Høy | Bakgrunnsmotor for kobling mellom parkeringer og SUN2-brukere. |
| `fibaro10_proxy` | Kritisk | Caddy reverse proxy for offentlige mobilflater og intern HTTPS til Fibaro10. |
| `easypark_downloader` | Kritisk | Separat compose/app for EasyPark-nedlasting og importtrigger. |

## Proxy og intern HTTPS

`Caddyfile` eksponerer disse domenene:

| Domene | Intern tjeneste | Kommentar |
| --- | --- | --- |
| `fibaro10.lilletorget.net:443` | `fibaro10:8110` | Hovedapp med offentlig betrodd sertifikat, kun LAN/VPN. |
| `app.lilletorget.net:443` | `shell_app:8150` og fagappene `8151-8158` | Felles PWA-origin; Caddy ruter hver fagapp etter sti. |
| `omsetning.lilletorget.net:443` | `revenue_app:8151` | Intern omsetningsapp. |
| `parkering.lilletorget.net:443` | `parking_app:8152` | Intern parkeringsapp. |
| `soling.lilletorget.net:443` | `sun_app:8153` | Intern solingsapp. |
| `energi.lilletorget.net:443` | `energy_app:8154` | Intern energiapp. |
| `drift.lilletorget.net:443` | `operations_app:8155` | Intern bygg- og driftsapp. |
| `vedlikehold.lilletorget.net:443` | `maintenance_app:8156` | Intern vedlikeholdsapp. |
| `system.lilletorget.net:443` | `system_app:8157` | Intern systemapp. |
| `koble.lilletorget.net:443` | `link_app:8158` | Intern Koble-app. |
| `online.lilletorget.net` | `online_dashboard:8111` | Begrenset ekstern flate. |
| `owntracks.lilletorget.net` | `owntracks_service:8128` | Tokenbeskyttet OwnTracks. Direkte interne `/api/owntracks/*` skjules eksternt. |
| `vedl.lilletorget.net` | `maintenance_mobile:8112` | Samme brukerbase som Fibaro10. |
| `alarm.lilletorget.net` | `alarm_mobile:8114` | Samme brukerbase som Fibaro10. Åpnes direkte fra ntfy-varsler. |
| `ipad.lilletorget.net` | `fibaro10ipad:8113` | Samme brukerbase som Fibaro10. |
| `192.168.20.218:8114` | `alarm_mobile:8114` | Lokal reserveadresse for alarmappen. |

## Felles innlogging i mikroappene

`fibaro10.lilletorget.net`, appvelgeren og mikroappene på portserien 8150-8158 bruker
én felles, opak sesjonscookie. Cookien heter `lilletorget_session`, gjelder for
`.lilletorget.net` og settes med `Secure`, `HttpOnly` og `SameSite=Lax`. Passordet
lagres ikke i nettlesercookien. Utlogging fra én av disse appene tilbakekaller den
samme databasesesjonen og fjerner den felles cookien.

Den brede cookien er et bevisst arkitekturvalg og skal ikke snevres inn til
`app.lilletorget.net` så lenge reserveflaten, appvelgeren og de separate
subdomenene skal dele innlogging. Den inneholder bare en opak, tilbakekallbar
sesjonsnøkkel og er beskyttet med `Secure`, `HttpOnly` og `SameSite=Lax`.

Domeneappene videresender bare cookien som følger den enkelte innkommende
forespørselen. Den delte HTTP-forbindelsespoolen avviser all cookie-lagring, og
innloggingskallet bruker en egen kortlivet klient. Dermed kan en brukers sesjon
ikke bli liggende i app-prosessen og arves av en annen forespørsel. Produksjonssmoke
kontrollerer anonym `401` på alle appenes `/api/auth/me` etter hver utrulling.

Direkte lokal utvikling via IP eller `localhost` får ingen domenecookie; der settes
samme cookien bare for det lokale vertsnavnet. Domenet kan overstyres med
`AUTH_SESSION_COOKIE_DOMAIN`, eller deaktiveres med en tom verdi.

## Felles installert desktopapp

`app.lilletorget.net` er hovedidentiteten for den installerte PWA-en `Lilletorget`.
Alle fagappene presenteres som stier under den samme origin-en, mens Caddy fortsatt
ruter dem til separate containere og buildløp. Dermed ligger hele den installerte
opplevelsen i vanlig manifest-scope `/`, uten `scope_extensions` eller association-
filer. Appbytte blir værende i samme standalone-vindu uten ekstra adresselinje.

Bare appvelgeren skal installeres. Etter manifestendringer må gamle separate
installasjoner av Fibaro10 eller fagappene avinstalleres før `Lilletorget` installeres
på nytt fra appvelgeren.

## Roller for brukerflatene

`https://app.lilletorget.net/` er primær inngang for daglig arbeid. Fagappene er
egne bygg og containere, men presenteres som stier under samme origin. Fibaro10
på port 8110 er fortsatt produksjonskritisk fordi den eier API, datamodell,
bakgrunnsjobber og flere administrative funksjoner. `desktop_v2` som leveres fra
Fibaro10 beholdes som samlet operativ reserve og funksjonsreferanse, men ny
fagfunksjonalitet skal som hovedregel implementeres i riktig mikroapp.

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
| 23 | HC3 dørstatus ved avvik | Bygg og drift | Fibaro10 / HC3 API | ca. 2 min ved behov |
| 24 | Dreame logger | Renhold | QNAP / Dreamehome | ca. 5 min |

`Admin -> Datakilder` er operativ fasit for status, siste kjøring, alder, feilmelding og forklaring per kilde.

## Lagring og backup

- Hovedappen bruker PostgreSQL via miljøvariabelen `DATABASE_URL`.
- OwnTracks bruker egen PostgreSQL-container `owntracks_postgres`.
- Axis snapshot-buffer ligger på eget arkivvolum via `AXIS_HOST_SNAPSHOT_DIR`.
- Protect-bilder ligger på SSD-arkivvolumet via `UNIFI_PROTECT_HOST_SNAPSHOT_DIR`.
- AI-modeller og kalibreringsmetadata ligger på SSD via `VISUAL_AI_HOST_DATA_DIR` og tas med i nattlig backup.
- Deploy-backuper lagres i `/share/CACHEDEV3_DATA/fibaro10_archive/fibaro10_deploy_backups`.
- Nattlig/manuell full backup håndteres av `scripts/qnap-backup.sh` og inkluderer separate SQL-dumper for Fibaro10 og OwnTracks samt Roborock- og Dreame-data. Backupen publiseres atomisk med SHA-256-kontrollsummer og kan replikeres til en annen maskin med `BACKUP_REPLICA_TARGET`.
- Restore-test kjøres fra Windows med `scripts/verify-qnap-backup.ps1` og leser begge SQL-dumpene inn i midlertidige databaser.
- `Varslinger -> Oversikt` leser statusfilene for nattbackup og full gjenopprettingsbackup via to separate, skrivebeskyttede containermonteringer. Backupfeil og for gamle backuper blir aktive hendelser.
- Det operative hendelsessenteret samler også feilede datakilder, aktive døralarmer, pullertavvik og ntfy-kø. Kvittering og operatørnotat lagres separat i `operational_incident_reviews`; kildesystemets status overskrives aldri.
- `scripts/qnap-health-watch.sh` kontrollerer alle webtjenester, begge nattbackupene og ledig plass på Vol1-Vol3 hvert femte minutt.
- `scripts/qnap-docker-maintenance.sh` rydder ukentlig ubrukte bygglag og images eldre enn 14 dager, men aldri containere eller datavolumer. Dette bevarer normalt minst ett tidligere byggesett som cache.
- Fibaro10 beholder tekniske suksesslogger i 90 dager, tekniske feillogger i 365 dager og sendte varslingskøposter i 30 dager. Virksomhetsdata har ingen automatisk retention.

## Kvalitetssjekk

Standard deploy går gjennom:

1. `scripts/check-local.ps1`
2. Git push til `main`
3. QNAP backup av runtimefiler/data
4. Git-diff mot kjørende QNAP-commit og bygging av bare berørte tjenester. Ukjente endringer gir full rebuild som sikker fallback.
5. Health-check av alle dokumenterte HTTP-endepunkter, 24 datakilder og forventede containere
6. Smoke-check av interne flater, importører og eksterne proxyadresser
7. Innlogget live-smoke gjennom desktop- og fagapprutene, med p50/p95-måling
8. Anonym sesjonskontroll, sikkerhetsheadere og cache-regler for alle Mantis-appene

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

Siste samlede og daterte verifikasjon ligger i `docs/kvalitetsstatus-2026-08-07.md`.
