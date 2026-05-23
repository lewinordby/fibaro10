# SUN2 enkeltimer

Dette er den nye flyten for å hente ut alle enkelt-solinger fra SUN2 Owner.

## Arkitektur

```text
SUN2 Owner
  -> sun2_session_scraper
  -> Sun2_sessions_YYYY-MM.json
  -> POST /api/sun2/sessions/ingest
  -> Fibaro10-tabeller
     - sun2_tanning_sessions
     - sun2_session_import_runs
  -> Soling > Enkeltimer
```

## Hvorfor dette er separat

Eksisterende `sun2_importer` importerer dagsstatistikk per rom. Den er god til totaler, men ikke til å forstå når på dagen solingene skjer, hvem som bruker hva, og hvordan enkeltøkter fordeler seg.

`sun2_session_scraper` henter derfor rålinjene fra listen over brukernes siste solinger og lagrer en rad per økt.

## Første driftstest

Start med:

```env
POST_TO_FIBARO10=0
```

Kjør én måned i grensesnittet:

```text
http://QNAP-IP:8099
```

Kontroller filen:

```text
sun2_session_scraper/data/session_exports/Sun2_sessions_YYYY-MM.json
```

Når kolonnene treffer riktig, sett:

```env
POST_TO_FIBARO10=1
```

Da sendes data inn til Fibaro10 automatisk.

## Justering hvis SUN2-siden endrer seg

Hvis skraperen ikke finner riktig side automatisk, fyll inn eksakt URL:

```env
LIST_URL=https://...
```

Hvis den finner siden, men feil tabell, sjekk debugfilene i:

```text
sun2_session_scraper/data/session_errors
```

Der lagres HTML og skjermbilde når den ikke klarer å hente rader.
