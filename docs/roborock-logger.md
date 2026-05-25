# Roborock_logger og Renhold

`Roborock_logger` er den lokale innlesingsappen for robotstøvsugere. Den kjører på QNAP/Docker i samme nett som robotene og sender ferdig strukturerte data til Fibaro10.

## Hvorfor lokal logger

Roborock-data kommer fra to steder:

- Roborock cloud for konto, robotliste, metadata, planer og kartkanal
- lokal LAN-tilkobling for raskere status og historikk fra robotene

Den lokale loggeren gjør at hovedappen slipper å snakke direkte med Roborock ved sidevisning. Fibaro10 viser bare data som allerede ligger i egen database.

## API i Fibaro10

Fibaro10 tar imot:

```text
POST /api/renhold/ingest
```

Og viser:

```text
GET /renhold/oversikt
GET /renhold/robot/{duid}
GET /renhold/json
```

Data lagres i egne tabeller for:

- roboter
- statusmålinger
- vaskjobber
- planlagte jobber
- forbruksdeler
- kart
- probe-resultater
- sync-kjøringer

## QNAP / Docker

Mappen ligger i repoet:

```text
roborock_logger
```

Typisk drift:

```bash
cd roborock_logger
docker compose up -d --build
```

Webflate:

```text
http://QNAP-IP:8095
```

Hvis Fibaro10 senere flyttes lokalt, endres bare API-base i loggerens miljø:

```env
FIBARO10_API_BASE_URL=https://fibaro10.onrender.com
```

til for eksempel:

```env
FIBARO10_API_BASE_URL=http://192.168.20.x:8000
```

## Drift og kontroll

Normal sync skjer periodisk fra loggeren. Status for siste vellykkede Roborock-sync vises i:

```text
Status -> Datakilder -> Roborock logger
```

I hovedappen vises robotene under:

```text
Renhold -> Oversikt
```

Derfra kan man åpne hver robot og se status, teknisk identitet, siste jobber, planer, kart og rå statuspakker.

## Feilsøking

Hvis Renhold viser gamle data:

1. Sjekk Status -> Datakilder.
2. Åpne Roborock_logger på QNAP og se om den har feilmelding.
3. Kontroller at robotene er online i Roborock.
4. Kontroller at logger-brukeren i Fibaro10 fortsatt virker.
5. Sjekk lokal kø hvis Fibaro10 har vært nede:

```text
/data/pending_batches.jsonl
```

Batcher i kø sendes på nytt ved neste vellykkede sync.
