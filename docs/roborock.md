# Roborock-integrasjon

Dette er et testspor for å hente Roborock-enheter og status med `python-roborock`.

## Status

Login fungerer nå med egen delt Roborock-bruker:

```text
roborock.sun2@gmail.com
```

Viktig funn: Roborock binder e-postkoden til `header_clientid`. Scriptet lagrer derfor en stabil klient-ID lokalt per e-postadresse i:

```text
C:\Users\mrnor\.fibaro10\roborock_client_ids.json
```

Selve Roborock-token lagres lokalt i:

```text
C:\Users\mrnor\.fibaro10\roborock_user_data.pickle
```

Disse filene skal ikke legges i Git.

## Kommandoer

Send kode:

```powershell
python scripts\roborock_probe.py request-code --email roborock.sun2@gmail.com
```

Logg inn med koden:

```powershell
python scripts\roborock_probe.py login --email roborock.sun2@gmail.com --code KODE
```

Vis lagret login uten hemmelige verdier:

```powershell
python scripts\roborock_probe.py cache-info
```

Hent rask enhetsoversikt via REST:

```powershell
python scripts\roborock_probe.py devices --email roborock.sun2@gmail.com
```

Hent rå home-data via REST:

```powershell
python scripts\roborock_probe.py home --email roborock.sun2@gmail.com
```

Full device manager/MQTT finnes også, men kan bruke lang tid eller henge hvis MQTT-oppkoblingen ikke blir klar:

```powershell
python scripts\roborock_probe.py devices-live --email roborock.sun2@gmail.com
```

## Første funn

Den delte roboten vises i Roborock API-et som:

- Navn: `1.etg A`
- Produkt: `Roborock Qrevo`
- Modell: `roborock.vacuum.a75`
- Firmware: `02.20.60`
- Delt enhet: ja
- Online: ja
- Statuskode `8`: `charging`
- Feilkode `0`: ingen feil

## Praktisk vurdering

For Fibaro10 er det tryggest å starte med REST-basert status fra `home`/`devices`, siden dette allerede fungerer stabilt. Der får vi blant annet online-status, batteri, firmware, modell og rå statusfelter.

Neste steg kan være å lage en egen Roborock-side i grensesnittet, eller å logge status periodisk på samme måte som lys og ventilasjon.
