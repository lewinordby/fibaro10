# Fibaro10 nordisk biloppslag

Egen app for sakte og kontrollert fallback-oppslag av utenlandske registreringsnummer. Svenske skilt hentes fra Biluppgifter.se. Danske skilt hentes fra Tjekbil sitt DMR-API.

## Formaal

Appen brukes bare for biler der Fibaro10 allerede har forsokt SVV, men ikke har faatt rad i `kjoretoy_nokkeldata`. Den skal ikke brukes som generell skraper.

## Sikkerhetsregler

- SVV/Vegvesen kjoeres alltid forst.
- Kun permanent uten-treff hos SVV kan trigge ekstern fallback.
- Svenske kandidater maa matche svensk standardformat:
  - `ABC123`
  - `ABC12D`, der siste tegn ikke er `O`
- Danske kandidater maa matche dansk standardformat:
  - `DY71543`
  - `AA12345`
- Dansk format overlapper norske skilt. Derfor settes `omrade = Danmark` bare naar Tjekbil returnerer samme registreringsnummer og faktisk kjoretoydata.
- Kandidater hentes fra Fibaro10 via internt legacy-endepunkt `/api/parkering/kjoretoy/car-info-kandidater`.
- Naar SVV akkurat har gitt permanent uten-treff paa svensk eller dansk format, kan Fibaro10 trigge direkteoppslag paa akkurat det skiltet.
- Standard backlog er en bil per oppslag og 300 sekunder mellom faktiske eksterne kall.
- Hvis en kilde svarer med rate-limit eller Cloudflare, settes global pause for appen.

## Relevante felt

Parserne lagrer blant annet:

- bekreftet land og kilde
- kilde-URL
- bil/modelltittel
- aarsmodell
- forstegangsregistrering hvis kilden viser det
- siste eierbytte/statusdato hvis kilden viser det
- biltype/karosseri hvis kilden viser det
- farge
- drivstoff/motor
- girkasse
- effekt
- kilometerstand
- kontrollfrist/inspeksjon hvis kilden viser det
- alle faktalinjer parseren klarer aa lese
- kort raatekstutdrag for senere forbedring

## Miljovariabler

- `FIBARO10_BASE_URL`
- `CAR_INFO_APP_TOKEN` for intern tilgang mot Fibaro10 og valgfri beskyttelse av manuell trigger
- `FIBARO10_USERNAME` og `FIBARO10_PASSWORD` kan brukes i stedet for token
- `CAR_INFO_URL_TEMPLATE`, standard `https://biluppgifter.se/fordon/{plate_lower}/`
- `TJEKBIL_URL_TEMPLATE`, standard `https://www.tjekbil.dk/api/v3/dmr/regnr/{plate}`
- `CAR_INFO_RUN_INTERVAL_MINUTES`, standard `30`
- `CAR_INFO_BATCH_SIZE`, standard `1`
- `CAR_INFO_REQUEST_DELAY_SECONDS`, standard `300`
- `CAR_INFO_RATE_LIMIT_BACKOFF_MINUTES`, standard `240`
- `CAR_INFO_BACKLOG_ENABLED`, standard `true`
- `CAR_INFO_BACKLOG_MAX_PER_CYCLE`, standard `12`
- `CAR_INFO_BACKLOG_DELAY_SECONDS`, standard minst `300`

## Endepunkter

- `GET /health`
- `POST /api/run-once?limit=1`
- `POST /api/run-plate/{plate}`
- `POST /api/run-backlog?max_items=12`
- `GET /api/svensk-skilt/{plate}`
- `GET /api/dansk-skilt/{plate}`
