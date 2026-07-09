# OwnTracks HTTP

Oppdatert 10.07.2026.

OwnTracks er en separat HTTP-tjeneste ved siden av Fibaro10. Tjenesten tar imot posisjoner, waypoints og transition-hendelser fra OwnTracks-appen, lagrer raadata i egen database og eksponerer et eget administrasjonsgrensesnitt/API.

QNAP-oppsettet bruker PostgreSQL via `owntracks_postgres`. Den gamle SQLite-filen beholdes som migrerings- og rollback-kilde, men normal drift skal bruke `OWNTRACKS_DATABASE_URL`.

## Primar URL

- Administrasjon: `https://owntracks.lilletorget.net/`
- Publisering fra app: `https://owntracks.lilletorget.net/pub?token=<OWNTRACKS_HTTP_TOKEN>`
- Health: `https://owntracks.lilletorget.net/health`
- Lokal tjeneste: `owntracks_service` paa port `8128`
- Runtime-database: PostgreSQL-service `owntracks_postgres`
- Gammel SQLite-kilde/rollback: `owntracks_service/data/owntracks.db`
- Migrering: `python -m app.migrate_sqlite_to_postgres --source sqlite:////data/owntracks.db --target "$OWNTRACKS_DATABASE_URL"`

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

Siden `Kjente steder` viser dette som en praktisk oversikt i en todelt arbeidsflate:

- tabell over alle steder til venstre
- valgt sted med status, kategori, noekkeltall, kart og besoksliste til hoyre
- aktivt besok og hvor lenge det har vart
- siste relevante enter og leave
- total tid i valgt globalt tidsfilter
- tydelig tekst om at upresise hendelser beholdes, men ikke styrer status

Klikk paa et sted i venstre tabell for aa vise detaljene. Detaljpanelet viser et lite kart og en besoksliste med `Kom`, `Dro` og `Hvor lenge`. Hvis besoket fortsatt er aktivt, vises `Pagaende` i dro-feltet, og varigheten beregnes frem til naa.

Waypoints kan kategoriseres direkte i waypoint-dialogen. Kategorien lagres paa waypointet og vises i listen, detaljpanelet og API-et. Dette brukes forelopig bare som struktur i grensesnittet, men kan senere brukes til filtrering eller rapporter.

Kategorifilteret i toppfeltet brukes aktivt paa `Kjente steder`, `Opphold`, `Kart`, `Sonebesok` og `Waypoints`.

Siden `Opphold` er den praktiske rapporten for hvor man har vaert. Den viser total tid, aktive opphold, tid per kategori og en detaljliste over hvert besok i valgt tidsfilter.

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

## Fibaro10 API

Fibaro10 skal hente ferdig tolket status fra:

- Internt: `http://owntracks_service:8128/api/owntracks/fibaro-summary`
- Eksternt/tokenbeskyttet: `https://owntracks.lilletorget.net/owntracks/api/fibaro-summary?token=<OWNTRACKS_HTTP_TOKEN>`
- Internt, besoksliste: `http://owntracks_service:8128/api/owntracks/visits?waypointName=Lilletorget%203`
- Eksternt/tokenbeskyttet, besoksliste: `https://owntracks.lilletorget.net/owntracks/api/visits?waypointName=Lilletorget%203&token=<OWNTRACKS_HTTP_TOKEN>`

Payloaden inneholder `activePlace`, `activePlaces`, `places`, `totals`, `latestLocation` og `quality`. Dette skal brukes fremfor at Fibaro10 tolker raadata selv.

`/api/owntracks/visits` er laget for Fibaro10-synk og returnerer bare sonebesok. Det kan filtreres med `hours`, `start`, `end`, `topic`, `waypointName` og `include_short`. Korte lukkede opphold skjules som standard med samme policy som i OwnTracks-oversiktene.

## Fibaro10-integrasjon

Fibaro10 skal ikke eie OwnTracks-data. Riktig modell er:

```text
OwnTracks app
  -> owntracks.lilletorget.net
     -> owntracks_service
        -> PostgreSQL
        -> SQLite beholdt som migrerings-/rollback-kilde
        -> API til Fibaro10 ved behov
```

Fibaro10 henter Lilletorget-besok via visits-API-et, lagrer dem i egen `site_visits`-tabell og kobler vedlikeholdsoppgaver med `site_visit_id`. OwnTracks skriver ikke direkte i Fibaro10-databasen.
