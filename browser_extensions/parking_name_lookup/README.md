# Fibaro10 parkering områdeoppslag

Chrome/Edge-extension for å lese `Område` fra Vegvesen-siden du allerede er innlogget på, og skrive dette tilbake til Fibaro10.

Extensionen lagrer ikke eiernavn. Den lagrer bare grovt område, for eksempel `Lillehammer`.

## Bruk

1. Gå til `chrome://extensions` eller `edge://extensions`.
2. Slå på utviklermodus.
3. Velg `Load unpacked` / `Last inn upakket`.
4. Velg mappen `browser_extensions/parking_name_lookup`.
5. Logg inn på Vegvesen-siden i nettleseren.
6. Åpne extensionen.
7. Fyll inn Fibaro10 URL, brukernavn, passord og URL-mal.
8. Trykk `Lagre oppsett`.
9. Trykk `Hent og skriv 1000`.

Knappen henter inntil 1000 biler som mangler område, åpner hvert registreringsnummer hos Vegvesen, leser feltet `Område` og skriver verdien til Fibaro10.

## API

Extensionen bruker disse endepunktene:

- `GET /api/parkering/kjoretoy/mangler-omrade?limit=1000`
- `POST /api/parkering/kjoretoy/{plate}/omrade`

Begge krever bruker med innstillingstilgang via `x-access-username` og `x-access-password`.
