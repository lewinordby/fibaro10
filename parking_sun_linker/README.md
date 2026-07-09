# Parking Sun Linker

Oppdatert 10.07.2026.

`parking_sun_linker` er en separat QNAP-container som finner sannsynlige koblinger mellom parkeringer og SUN2-brukere.

## Formål

Motoren leter etter mønstre der samme bil har minst to parkeringer som etterfølges av soltimer på samme SUN2-id innenfor valgt tidsvindu. Forslagene brukes til manuell kontroll i Fibaro10, ikke som automatisk fasit.

## Flyt

```text
parking_sun_linker
  -> GET /api/koble/worker/config
  -> leser parkering og sun2_tanning_sessions fra PostgreSQL
  -> POST /api/koble/worker/status
  -> POST /api/koble/worker/results
  -> Fibaro10 / Koble
```

Worker-token sendes i headeren `x-koble-token`.

## Styring i Fibaro10

Bruk hovedappen:

- `Koble -> Oversikt`: totaler og status.
- `Koble -> Kandidater`: bekreft eller avvis forslag.
- `Koble -> Biltreff`: biler med gjentatte soltreff.
- `Koble -> SUN2-kontroll`: gruppert etter SUN2-id.
- `Koble -> Treffgrunnlag`: rågrunnlag.
- `Koble -> Jobb`: start/stopp, parametere og worker-status.

Parametere lagres i Fibaro10, blant annet:

- minimum antall parkeringer/treff
- maks minutter mellom parkering og soltime
- hvor langt tilbake bilenes historikk skal vurderes
- pause når jobben er ajour

## Miljøvariabler

- `DATABASE_URL`: PostgreSQL-tilgang til Fibaro10-databasen.
- `FIBARO10_BASE_URL`: intern Fibaro10 URL, normalt `http://fibaro10:8110`.
- `KOBLE_WORKER_TOKEN`: token for worker-API. Faller tilbake til `CAR_INFO_APP_TOKEN` hvis ikke satt.
- `KOBLE_RUN_ON_START`: om jobben skal starte ved containerstart.
- `KOBLE_LOOP_SLEEP_SECONDS`: pause mellom batcher.
- `KOBLE_BATCH_SIZE`: antall parkeringer per batch.

## Drift

Tjenesten bygges og startes av hoveddeploy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy-qnap.ps1
```

Health:

```text
http://192.168.20.218:8127/health
```

Datakildestatus vises i `Admin -> Datakilder -> Koble parkering/SUN2`.
