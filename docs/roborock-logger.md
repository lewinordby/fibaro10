# Roborock_logger og Renhold i Fibaro10

## Mål

`Roborock_logger` kjører lokalt på QNAP/Docker i samme nett som robotene. Den leser Roborock cloud og lokal LAN, og sender ferdig strukturerte data til Fibaro10.

Fibaro10 kan ligge på Render nå og flyttes lokalt senere. Da endres bare:

```env
FIBARO10_API_BASE_URL=https://fibaro10.onrender.com
```

til for eksempel:

```env
FIBARO10_API_BASE_URL=http://192.168.2.x:8000
```

## Fibaro10

Fibaro10 har fått:

- `POST /api/renhold/ingest`
- `GET /renhold/oversikt`
- `GET /renhold/robot/{duid}`
- `GET /renhold/json`

Data lagres i egne tabeller:

- `roborock_robots`
- `roborock_status_samples`
- `roborock_clean_jobs`
- `roborock_schedules`
- `roborock_consumables`
- `roborock_maps`
- `roborock_probe_results`
- `roborock_sync_runs`

Loggeren sender med vanlig Fibaro10-bruker i HTTP-headere:

```text
x-access-username
x-access-password
```

Lag gjerne en egen bruker i Fibaro10 som heter `logger`.

## QNAP / Docker

Mappen ligger i repoet:

```text
roborock_logger
```

Oppsett:

```bash
cd roborock_logger
cp .env.example .env
docker compose up -d --build
```

Åpne:

```text
http://QNAP-IP:8095
```

Første gangs bruk:

1. Send Roborock-kode fra webflaten.
2. Skriv inn koden og lagre login.
3. Trykk `Synk nå`.
4. Trykk `Synk med kart` når kart skal overføres.

Hvis Fibaro10 ikke svarer, legges batcher i lokal kø:

```text
/data/pending_batches.jsonl
```

De sendes på nytt ved neste vellykkede sync.
