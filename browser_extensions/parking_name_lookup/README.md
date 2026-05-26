# Fibaro10 parkering navneoppslag

Chrome/Edge-extension for manuelle nettsider der du allerede er innlogget.

Extensionen henter ikke eiernavn automatisk fra siden. Den åpner riktig oppslag,
lar deg lese og kontrollere navnet selv, og lagrer bare verdien du aktivt skriver
inn.

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
8. Trykk `Hent 100 fra Fibaro10`.
9. Trykk `Apne i Vegvesen`.
10. Les navnet på siden og skriv/lim det inn i feltet.
11. Trykk `Lagre og neste`.

Bruk `Hopp over` hvis et regnr ikke skal lagres.

## API

Extensionen bruker disse endepunktene:

- `GET /api/parkering/kjoretoy/mangler-navn?limit=100`
- `POST /api/parkering/kjoretoy/{plate}/navn`

Begge krever bruker med innstillingstilgang via `x-access-username` og `x-access-password`.
