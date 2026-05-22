# Roborock_logger

`Roborock_logger` er en liten lokal app som skal kjøre på QNAP/Docker i samme nett som Roborock-robotene.

Den gjør tre ting:

1. Logger inn mot Roborock cloud med den delte kontoen.
2. Leser robotene lokalt på LAN der det er mulig.
3. Sender ferdig strukturerte data til Fibaro10 sitt API.

Fibaro10 kan ligge eksternt på Render nå, og senere lokalt. Da endres bare `FIBARO10_API_BASE_URL`.

## Oppsett

Kopier `.env.example` til `.env`:

```bash
cp .env.example .env
```

Viktigste felter:

```env
ROBOROCK_EMAIL=roborock.sun2@gmail.com
FIBARO10_API_BASE_URL=https://fibaro10.onrender.com
FIBARO10_API_USERNAME=logger
FIBARO10_API_PASSWORD=passord-fra-fibaro10
```

Brukeren i Fibaro10 kan være en vanlig bruker. Loggeren bruker headerne `x-access-username` og `x-access-password`.

## Starte med Docker

```bash
docker compose up -d --build
```

Åpne:

```text
http://QNAP-IP:8095
```

Første gang:

1. Trykk `Send kode`.
2. Skriv inn e-postkoden fra Roborock.
3. Trykk `Lagre login`.
4. Trykk `Synk nå`.

## Hva sendes til Fibaro10

Loggeren sender batcher til:

```text
/api/renhold/ingest
```

Batchen kan inneholde:

- robotmetadata
- cloud-status
- lokal LAN-status
- nettverksdata
- forbruksdeler
- rengjøringshistorikk
- planlagte jobber
- scener
- kartdata med PNG base64 ved kart-sync
- probe-resultater og feil

Hvis Fibaro10 er nede, legges batchen i lokal kø i `/data/pending_batches.jsonl` og forsøkes sendt igjen senere.
