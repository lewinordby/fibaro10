# Roborock-integrasjon

Dette er foreløpig et testspor for å hente Roborock-enheter og status med `python-roborock`.

## Status

Direkte innlogging mot Roborock er testet med:

- e-postkode via ny API-flyt
- e-postkode via gammel API-flyt
- passord-login
- passord-login med eksplisitt totrinnsflagg

Roborock svarer med `need two step validate` på passordflyten, men returnerer ikke en token eller en session-id som scriptet kan fullføre videre med. E-postkodene blir avvist av Roborock sine API-endepunkter, selv når riktig region og avtaleversjon brukes.

## Script

Scriptet ligger her:

```powershell
scripts\roborock_probe.py
```

Nyttige kommandoer:

```powershell
python scripts\roborock_probe.py account-info --email lewi.nordby@gmail.com
python scripts\roborock_probe.py request-code --email lewi.nordby@gmail.com
python scripts\roborock_probe.py login --email lewi.nordby@gmail.com --code KODE
python scripts\roborock_probe.py request-code-legacy --email lewi.nordby@gmail.com
python scripts\roborock_probe.py legacy-login --email lewi.nordby@gmail.com --code KODE
python scripts\roborock_probe.py password-probe --email lewi.nordby@gmail.com
```

Når login er lagret:

```powershell
python scripts\roborock_probe.py cache-info
python scripts\roborock_probe.py devices --email lewi.nordby@gmail.com
python scripts\roborock_probe.py status --email lewi.nordby@gmail.com
```

## Import fra Home Assistant eller annen tokenkilde

Hvis Roborock allerede er satt opp i Home Assistant, kan `user_data` normalt ligge i:

```text
/config/.storage/core.config_entries
```

Importer slik:

```powershell
python scripts\roborock_probe.py import-user-data --file C:\sti\til\core.config_entries
```

Scriptet støtter også en ren JSON-fil som enten er selve `user_data`-objektet, eller et objekt med feltet `user_data`.

## Anbefalt vei videre

Lag helst en egen Roborock-bruker for integrasjoner og del roboten til denne brukeren fra Roborock-appen. Da slipper vi å bruke hovedkontoen, og vi kan rotere eller fjerne tilgangen senere uten å berøre privat konto.

Når vi får tak i en fungerende `user_data`, kan vi hente enhetsliste, status, forbruksdeler og eventuelt bygge en egen side i Fibaro10-grensesnittet.
