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

## OwnTracks Android

Bruk HTTP-modus:

- Mode: `HTTP`
- URL: `https://owntracks.lilletorget.net/pub?token=<OWNTRACKS_HTTP_TOKEN>`
- Device ID: stabilt navn, for eksempel `Lewi`
- Reporting mode: etter behov, for eksempel `Move` eller `Significant Changes`
- Publish Waypoints: kan brukes for aa synkronisere waypoints fra telefonen til serveren

Vellykket publisering svarer med tom JSON-array: `[]`. Dette er formatet OwnTracks Android forventer.

## Presisjon og databruk

OwnTracks-data deles i to nivaa:

- Raadata: alle meldinger lagres uendret i databasen og vises under Meldinger.
- Beregningsdata: kartspor, sonebesok og waypointforslag bruker bare posisjoner med presisjon maks `30 m`.

Standardgrensen styres av:

- `OWNTRACKS_MAX_CALCULATION_ACCURACY_M=30`

Dette betyr at et punkt med for eksempel `acc=95` fortsatt er synlig som raadata, men det brukes ikke til aa tegne spor, aapne/lukke sonebesok eller foreslaa nye waypoints. UI viser dette med `Brukes` eller `Lav presisjon` i meldingstabellene, og dashboard/kart viser hvor mange punkt som er filtrert bort.

Enter/leave-hendelser behandles etter samme prinsipp:

- Presis `Enter`: kan sette waypoint til inne og aapne/oppdatere sonebesok.
- Presis `Leave`: kan sette waypoint til ute og lukke sonebesok.
- Upresis `Enter` eller `Leave`: lagres som hendelse/raadata, men endrer ikke inne/ute-status.

Soneberegningen bruker hysterese. Et besok aapnes naar et presist punkt er innenfor soneradius, men lukkes foerst naar et presist punkt er tydelig utenfor `radius + buffer`. Dette hindrer at et kjent sted faar flere korte besok fordi telefonen hopper litt rundt sonegrensen.

Siden `Kjente steder` viser dette som en praktisk oversikt:

- en boks per aktivt waypoint
- aktivt besok og hvor lenge det har vart
- siste relevante enter og leave
- total tid i valgt globalt tidsfilter
- tydelig tekst om at upresise hendelser beholdes, men ikke styrer status

Klikk paa `Totalt i periode` paa et kjent sted for aa aapne detaljsiden. Den viser et lite kart og en besoksliste med `Kom`, `Dro` og `Hvor lenge`. Hvis besoket fortsatt er aktivt, vises `Pagaende` i dro-feltet, og varigheten beregnes frem til naa.

Grensen kan overstyres mer detaljert hvis det trengs:

- `OWNTRACKS_ZONE_VISIT_ACCURACY_CAP_M`: egen grense for sonebesok.
- `OWNTRACKS_STOP_SUGGESTION_MAX_ACCURACY_M`: egen grense for waypointforslag.
- `OWNTRACKS_DATA_QUALITY_MAX_ACCURACY_M`: egen grense for diagnose/advarsler.

Anbefalt drift er aa la disse staa lik hovedgrensen, slik at grensesnitt, diagnose og beregninger forklarer samme virkelighet.

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
