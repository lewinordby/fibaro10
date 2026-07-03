# OwnTracks HTTP

OwnTracks er flyttet ut av Fibaro10 og skal publisere direkte til egen HTTP-tjeneste.

## Endepunkt

- Offentlig URL: `https://online.lilletorget.net/owntracks/pub`
- Lokal tjeneste: `owntracks_service` på port `8128`
- Health: `http://192.168.20.218:8128/health`
- Data lagres i `owntracks_service/data/owntracks.db`

## Sikkerhet

Sett `OWNTRACKS_HTTP_TOKEN` i `.env` på QNAP før endepunktet brukes aktivt. Hvis den mangler, bruker tjenesten
`CAR_INFO_APP_TOKEN` som fallback.

Tjenesten godtar token på tre måter:

- Header: `Authorization: Bearer <token>`
- Header: `X-OwnTracks-Token: <token>`
- Basic Auth: valgfritt brukernavn, passord lik token
- Query: `?token=<token>`

Query-token er enklest å bruke fra mobilapp, men header er bedre dersom appen støtter det.

## OwnTracks Android

Bruk HTTP-modus:

- Mode: `HTTP`
- URL: `https://online.lilletorget.net/owntracks/pub?token=<OWNTRACKS_HTTP_TOKEN>`
- Device ID: valgfritt, men bruk et stabilt navn
- Reporting mode: etter behov, for eksempel significant changes eller manual

## Visning

Webgrensesnittet ligger her:

- `https://online.lilletorget.net/owntracks`

Siden og de eksterne `/owntracks/api/...`-endepunktene krever samme token som HTTP-publisering. Nettleseren kan bruke
Basic Auth: valgfritt brukernavn og token som passord. Alternativt kan token sendes som querystring:

- `https://online.lilletorget.net/owntracks?token=<OWNTRACKS_HTTP_TOKEN>`

## Videre Fibaro10-integrasjon

Fibaro10 skal ikke lese OwnTracks direkte nå. Når HTTP-tjenesten er verifisert, lager vi et eksplisitt API i
`owntracks_service` som Fibaro10 kan konsumere.
