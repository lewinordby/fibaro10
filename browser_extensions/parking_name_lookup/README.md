# Fibaro10 parkering omradeoppslag

Chrome/Edge-extension for manuelle nettsider der du allerede er innlogget.

Extensionen lagrer ikke eiernavn. Den åpner riktig oppslag, lar deg lese område
selv, og lagrer bare grovt område, for eksempel `Lillehammer`.

## Bruk

1. Gå til `chrome://extensions` eller `edge://extensions`.
2. Slå på utviklermodus.
3. Velg `Load unpacked` / `Last inn upakket`.
4. Velg denne mappen: `browser_extensions/parking_name_lookup`.
5. Åpne siden som skal brukes til oppslag og logg inn manuelt.
6. Åpne extensionen.
7. Fyll inn:
   - Fibaro10 URL
   - brukernavn/passord med innstillingstilgang
   Verdiene lagres automatisk lokalt i nettleseren. Du kan også trykke
   `Lagre oppsett`.
8. Trykk `Hent 100 fra Fibaro10`.
9. Trykk `Apne i Vegvesen`.
10. Trykk `Les omrade og lagre` for å lese feltet `Område` og skrive det til Fibaro10.
11. Når dette fungerer på ett regnr kan du bruke `Auto liste`.

Bruk `Stopp` for å avbryte listen. Extensionen leser kun feltet `Område`.

## API

Extensionen bruker disse endepunktene:

- `GET /api/parkering/kjoretoy/mangler-omrade?limit=100`
- `POST /api/parkering/kjoretoy/{plate}/omrade`

Begge krever bruker med innstillingstilgang via `x-access-username` og `x-access-password`.
