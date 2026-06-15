# Fibaro10 svensk biloppslag

Egen app for sakte og kontrollert oppslag av svenske registreringsnummer. Standardkilde er Biluppgifter.se.

## Formaal

Appen brukes bare for biler der Fibaro10 allerede har forsokt SVV, men ikke har faatt rad i `kjoretoy_nokkeldata`. Den skal ikke brukes som generell skraper.

## Sikkerhetsregler

- Kun skilt som matcher svensk standardformat sendes til svensk oppslagskilde:
  - `ABC123`
  - `ABC12D`, der siste tegn ikke er `O`
- Kandidater hentes fra Fibaro10 via internt legacy-endepunkt `/api/parkering/kjoretoy/car-info-kandidater`.
- Naar SVV akkurat har gitt permanent uten-treff paa et svensk-formatert skilt, kan Fibaro10 trigge direkteoppslag paa akkurat det skiltet.
- Standard backlog er en bil per oppslag og 300 sekunder mellom faktiske eksterne kall.
- Hvis kilden svarer med rate-limit eller Cloudflare, settes global pause for appen.
- Ved bekreftet svensk bil poster appen resultatet tilbake til Fibaro10, som setter `omrade = Sverige` hvis omraadet er blankt eller `ikke funnet`.

## Relevante felt

Parseren lagrer blant annet:

- bekreftet svensk bil
- kilde-URL
- bil/modelltittel
- aarsmodell
- forstegangsregistrering hvis siden viser det
- biltype/karosseri hvis siden viser det
- farge
- drivstoff/motor
- girkasse
- effekt
- kilometerstand
- kontrollfrist/inspeksjon hvis siden viser det
- alle faktalinjer parseren klarer aa lese
- kort raatekstutdrag for senere forbedring

## Miljovariabler

- `FIBARO10_BASE_URL`
- `CAR_INFO_APP_TOKEN` for intern tilgang mot Fibaro10 og valgfri beskyttelse av manuell trigger
- `FIBARO10_USERNAME` og `FIBARO10_PASSWORD` kan brukes i stedet for token
- `CAR_INFO_URL_TEMPLATE`, standard `https://biluppgifter.se/fordon/{plate_lower}/`
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
