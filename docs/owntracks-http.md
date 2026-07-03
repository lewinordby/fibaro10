# OwnTracks HTTP

OwnTracks er en separat HTTP-tjeneste ved siden av Fibaro10. Tjenesten tar imot posisjoner, waypoints og transition-hendelser fra OwnTracks-appen, lagrer raadata i egen SQLite-fil og eksponerer et eget administrasjonsgrensesnitt/API.

Databasebytte er ikke gjort i denne revisjonen. SQLite beholdes til mottak, visning og Fibaro10-integrasjon er stabilt.

## Primar URL

- Administrasjon: `https://owntracks.lilletorget.net/`
- Publisering fra app: `https://owntracks.lilletorget.net/pub?token=<OWNTRACKS_HTTP_TOKEN>`
- Health: `https://owntracks.lilletorget.net/health`
- Lokal tjeneste: `owntracks_service` paa port `8128`
- Datafil: `owntracks_service/data/owntracks.db`

`owntracks.lilletorget.net` maa peke til samme offentlige IP som `online.lilletorget.net`.

## Overgangs-URL

Gammel URL beholdes midlertidig slik at telefonen ikke slutter aa publisere foer appinnstillinger er endret:

- `https://online.lilletorget.net/owntracks`
- `https://online.lilletorget.net/owntracks/pub?token=<OWNTRACKS_HTTP_TOKEN>`

Ny konfigurasjon skal bruke `owntracks.lilletorget.net`.

## OwnTracks Android

Bruk HTTP-modus:

- Mode: `HTTP`
- URL: `https://owntracks.lilletorget.net/pub?token=<OWNTRACKS_HTTP_TOKEN>`
- Device ID: stabilt navn, for eksempel `Lewi`
- Reporting mode: etter behov, for eksempel `Move` eller `Significant Changes`
- Publish Waypoints: kan brukes for aa synkronisere waypoints fra telefonen til serveren

Vellykket publisering svarer med tom JSON-array: `[]`. Dette er formatet OwnTracks Android forventer.

## Sikkerhet

Sett `OWNTRACKS_HTTP_TOKEN` i `.env` paa QNAP. Hvis den mangler, bruker tjenesten `CAR_INFO_APP_TOKEN` som fallback.

Tjenesten godtar token paa disse maaten:

- `Authorization: Bearer <token>`
- `X-OwnTracks-Token: <token>`
- Basic Auth med valgfritt brukernavn og token som passord
- Query: `?token=<token>`

Administrasjonssiden og eksterne `/owntracks/api/...`-endepunkter krever samme token. Nettleser kan bruke Basic Auth eller query-token:

- `https://owntracks.lilletorget.net/?token=<OWNTRACKS_HTTP_TOKEN>`

Direkte interne `/api/owntracks/...`-ruter er ikke eksponert via `owntracks.lilletorget.net` i Caddy. Ekstern visning skal bruke de tokenbeskyttede `/owntracks/api/...`-rutene.

## Buildlogg

OwnTracks har egen buildinfo uavhengig av Fibaro10:

- Build vises i administrasjonsgrensesnittet.
- JSON-endepunkt: `https://owntracks.lilletorget.net/owntracks/api/build-log?token=<OWNTRACKS_HTTP_TOKEN>`
- Runtime-build settes med `OWNTRACKS_APP_BUILD`.
- Commit settes fra deploy via `OWNTRACKS_APP_COMMIT`.

## Fibaro10-integrasjon

Fibaro10 skal ikke eie OwnTracks-data. Riktig modell er:

```text
OwnTracks app
  -> owntracks.lilletorget.net
     -> owntracks_service
        -> egen SQLite-database naa
        -> PostgreSQL senere
        -> API til Fibaro10 ved behov
```

Fibaro10 skal etter hvert hente bare relevante data via API, for eksempel siste besok, aktive soner eller oppsummerte tidsperioder.
