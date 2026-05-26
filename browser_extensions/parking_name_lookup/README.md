# Fibaro10 parkering navneoppslag

Chrome/Edge-extension for manuelle nettsider der du allerede er innlogget.

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
   - CSS-selector for søkefelt
   - CSS-selector for søkeknapp, eller la stå tomt for Enter
   - CSS-selector for feltet som inneholder navnet
8. Trykk `Hent 100 fra Fibaro10`.
9. Trykk `Test 1`.
10. Når første treff er riktig, trykk `Start`.

Jobben stopper hvis popupen lukkes. La derfor extension-vinduet stå åpent mens listen kjøres.

## API

Extensionen bruker disse endepunktene:

- `GET /api/parkering/kjoretoy/mangler-navn?limit=100`
- `POST /api/parkering/kjoretoy/{plate}/navn`

Begge krever bruker med innstillingstilgang via `x-access-username` og `x-access-password`.
