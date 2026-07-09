# Roborock-integrasjon

Oppdatert 10.07.2026.

Dette er test- og bakgrunnsnotatet for Roborock-integrasjonen. Løpende drift er nå beskrevet i `docs/roborock-logger.md`.

## Nåværende status

Roborock-data vises i hovedappen under:

```text
Renhold -> Oversikt
Renhold -> Robot
```

Datakildestatus vises under:

```text
Admin -> Datakilder -> Roborock logger
```

Hovedappen henter ikke Roborock-data direkte ved sidevisning. `Roborock_logger` kjører lokalt på QNAP/Docker, henter cloud/LAN-data og poster strukturerte batcher til Fibaro10.

## Login og token

Login fungerer med egen delt Roborock-bruker. Roborock binder e-postkode til `header_clientid`, derfor lagrer scripts en stabil klient-ID lokalt per e-postadresse.

Lokale filer som ikke skal inn i Git:

```text
%USERPROFILE%\.fibaro10\roborock_client_ids.json
%USERPROFILE%\.fibaro10\roborock_user_data.pickle
```

## Nyttige testkommandoer

Send kode:

```powershell
python scripts\roborock_probe.py request-code --email roborock.sun2@gmail.com
```

Logg inn med kode:

```powershell
python scripts\roborock_probe.py login --email roborock.sun2@gmail.com --code KODE
```

Vis lagret login uten hemmelige verdier:

```powershell
python scripts\roborock_probe.py cache-info
```

Hent enhetsoversikt:

```powershell
python scripts\roborock_probe.py devices --email roborock.sun2@gmail.com
```

Hent cloud-probe:

```powershell
python scripts\roborock_probe.py cloud-probe --email roborock.sun2@gmail.com
```

Test lokal LAN-lesing:

```powershell
python scripts\roborock_probe.py local-read-probe --email roborock.sun2@gmail.com
```

Finn lokale kandidater:

```powershell
python scripts\roborock_probe.py scan-local
```

Hent siste jobber:

```powershell
python scripts\roborock_probe.py clean-history --email roborock.sun2@gmail.com --limit 5
```

Hent kartbilde:

```powershell
python scripts\roborock_probe.py map-image --email roborock.sun2@gmail.com --output roborock_output\map.png
```

## Viktige funn

- Cloud/REST er best for robotliste, metadata, planer og kartkanal.
- Lokal LAN er best for status, historikk og enkelte tekniske kommandoer.
- Kart via Roborock cloud fungerer. Historisk kart per rengjøring er ikke bekreftet stabilt.
- Planlagte jobber kan hentes stabilt.
- Siste utførte jobber kan hentes via lokal kanal når robot og nett er tilgjengelig.

## Praktisk vurdering

For drift skal `Roborock_logger` brukes, ikke manuelle scripts. Scripts beholdes som testverktøy for ny robot, firmwareendringer og feilsøking.
