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

List planlagte jobber:

```powershell
python scripts\roborock_probe.py schedules --email roborock.sun2@gmail.com
```

List siste utførte jobber/rengjøringer:

```powershell
python scripts\roborock_probe.py clean-history --email roborock.sun2@gmail.com --limit 5
```

Denne bruker lokal LAN-tilkobling mot roboten. Standard IP er foreløpig `192.168.2.91`. Hvis roboten får ny IP kan den overstyres slik:

```powershell
python scripts\roborock_probe.py clean-history --email roborock.sun2@gmail.com --host 192.168.x.x --limit 5
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

Det finnes to aktive planlagte jobber:

- Jobb `4118662`: cron `0 3 * * ?`, aktiv, gjentas, segmenter `21,23,18,20,16`, repeat `2`, fan power `105`, mop mode `303`.
- Jobb `4072519`: cron `0 2 * * ?`, aktiv, gjentas, segmenter `21,16,18,20,23`, repeat `1`, fan power `104`, mop mode `300`.

Siste utførte jobber kan hentes via lokal kanal. Eksempel på siste fem ved test:

- 2026-05-22 02:00-02:39, 39,9 min, 37,78 m², fullført, feil `0`.
- 2026-05-21 21:02-21:10, 5,2 min, 4,78 m², fullført, feil `0`.
- 2026-05-21 03:00-08:45, 147,1 min, 40,21 m², fullført, feil `0`.
- 2026-05-21 02:00-02:37, 37,8 min, 38,59 m², fullført, feil `0`.
- 2026-05-20 03:00-08:42, 151,1 min, 39,88 m², fullført, feil `0`.

## Praktisk vurdering

For Fibaro10 er det tryggest å starte med REST-basert status fra `home`/`devices`, siden dette allerede fungerer stabilt. Der får vi blant annet online-status, batteri, firmware, modell og rå statusfelter.

Planlagte jobber kan hentes stabilt via REST. Siste utførte rengjøringer hentes stabilt via lokal LAN-tilkobling mot robotens port `58867`, med `local_key` fra Roborock cloud-data. Cloud-MQTT/RPC timeout-er foreløpig fra dette Windows-miljøet.

Neste steg kan være å lage en egen Roborock-side i grensesnittet, eller å logge status og planlagte jobber periodisk på samme måte som lys og ventilasjon.
