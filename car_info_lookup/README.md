# Fibaro10 car.info-oppslag

Egen app for sakte og kontrollert oppslag av svenske registreringsnummer hos car.info.

## Formaal

Appen brukes bare for biler der Fibaro10 allerede har forsokt SVV, men ikke har faatt rad i `kjoretoy_nokkeldata`. Den skal ikke brukes som generell skraper.

## Sikkerhetsregler

- Kun skilt som matcher svensk standardformat sendes til car.info:
  - `ABC123`
  - `ABC12D`, der siste tegn ikke er `O`
- Kandidater hentes fra Fibaro10 via `/api/parkering/kjoretoy/car-info-kandidater`.
- Standard er en bil per kjoreintervall.
- Hvis car.info svarer med rate-limit/coffee break, settes global pause for appen.
- Ved bekreftet svensk bil poster appen resultatet tilbake til Fibaro10, som setter `omrade = Sverige` hvis omraadet er blankt eller `ikke funnet`.

## Relevante felt

Parseren lagrer blant annet:

- bekreftet svensk bil
- car.info URL
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
- `CAR_INFO_URL_TEMPLATE`, standard `https://www.car.info/sv-se/license-plate/S/{plate}`
- `CAR_INFO_RUN_INTERVAL_MINUTES`, standard `45`
- `CAR_INFO_BATCH_SIZE`, standard `1`
- `CAR_INFO_RATE_LIMIT_BACKOFF_MINUTES`, standard `240`

## Endepunkter

- `GET /health`
- `POST /api/run-once?limit=1`
- `GET /api/svensk-skilt/{plate}`
