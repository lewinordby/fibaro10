# Roborock_logger og Renhold

Oppdatert 12.08.2026.

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
http://192.168.20.218:8095
```

Hvis Fibaro10 senere flyttes til en annen host eller port, endres bare API-base i loggerens miljø:

```env
FIBARO10_API_BASE_URL=http://fibaro10:8110
```

til for eksempel:

```env
FIBARO10_API_BASE_URL=http://192.168.20.x:8000
```

## Drift og kontroll

Normal sync skjer periodisk fra loggeren. Status for siste vellykkede Roborock-sync vises i:

```text
Admin -> Datakilder -> Roborock logger
```

I hovedappen vises robotene under:

```text
Renhold -> Oversikt
```

Derfra kan man åpne hver robot og se status, teknisk identitet, siste jobber, planer, kart og rå statuspakker.

## Legge til en ny robot

1. Legg roboten til på vanlig måte i Roborock-appen, gi den et tydelig navn og velg tidssonen `Europe/Oslo`.
2. Koble roboten til IOT-nettet som bruker adresser i `192.168.2.x`. Lokal status og historikk krever at QNAP-en kan nå roboten på dette nettet.
3. Del roboten med Roborock-kontoen `roborock.sun2@gmail.com`. Loggeren leser både kontoens egne og delte roboter.
4. Åpne `http://192.168.20.218:8095` og trykk `Finn nye roboter`. Handlingen henter Roborock-hjemmet på nytt uten én-times hurtigbuffer.
5. Kontroller at roboten vises på logger-siden med navn, modell og lokal IP.
6. Åpne `Bygg og drift -> Renhold -> Roboter` i Lilletorget. Fibaro10 oppretter roboten automatisk ved første mottatte synk; det skal ikke legges inn noen databasepost manuelt.

Hvis roboten finnes i cloud, men mangler lokal IP, sjekk at den er på IOT-nettet og at `ROBOROCK_SUBNET=192.168.2.` fortsatt er riktig. Bruk `Synk med kart` etter første vellykkede oppdagelse for å hente kartet med en gang.

## Tidssoner

Planene fra Roborock er lokal klokketid og skal for eksempel vises som `23:30`. Historiske vaskjobber kommer som Unix-tid i UTC. Fibaro10 konverterer disse til `Europe/Oslo` ved API-visning, inkludert riktig sommer- og vintertid.

## Feilsøking

Hvis Renhold viser gamle data:

1. Sjekk Admin -> Datakilder.
2. Åpne Roborock_logger på QNAP og se om den har feilmelding.
3. Kontroller at robotene er online i Roborock.
4. Kontroller at logger-brukeren i Fibaro10 fortsatt virker.
5. Sjekk lokal kø hvis Fibaro10 har vært nede:

```text
/data/pending_batches.jsonl
```

Batcher i kø sendes på nytt ved neste vellykkede sync.
