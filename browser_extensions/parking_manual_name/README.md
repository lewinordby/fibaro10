# Fibaro10 parkering navneoppslag

Chrome/Edge-extension for manuell registrering av navn på biler i Fibaro10.

Denne extensionen gjør ikke automatisk uthenting av navn. Den henter en liste over biler som mangler navn, lar deg åpne oppslagssiden for aktivt registreringsnummer, og lagrer navnet du selv skriver inn.

## Bruk

1. Gå til `chrome://extensions` eller `edge://extensions`.
2. Slå på utviklermodus.
3. Velg `Load unpacked` / `Last inn upakket`.
4. Velg mappen `browser_extensions/parking_manual_name`.
5. Åpne extensionen.
6. Fyll inn Fibaro10 URL, brukernavn, passord og URL-mal.
7. Trykk `Lagre oppsett`.
8. Trykk `Hent liste`.
9. Skriv navn og trykk `Lagre og neste`.

## API

Extensionen bruker disse endepunktene:

- `GET /api/parkering/kjoretoy/mangler-navn?limit=500`
- `POST /api/parkering/kjoretoy/{plate}/navn`

Begge krever bruker med innstillingstilgang via `x-access-username` og `x-access-password`.
