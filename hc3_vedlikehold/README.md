# HC3 vedlikehold

Oppdatert 10.07.2026.

Lokal vedlikeholdsapp for Fibaro HC3. Appen er laget for å kjøre på QNAP/Docker i samme nett som HC3.

## Hva appen gjør

- Leser energigruppe-QuickAppene i HC3.
- Viser hvilke undermålere som inngår i hver energigruppe.
- Oppdaterer beskrivelsefeltet på energigruppene i HC3.
- Viser status for energilogg-scenen.
- Kan starte energilogg-scenen på nytt fra et enkelt webgrensesnitt.

## Oppsett

Kopier `.env.example` til `.env` og fyll inn HC3-passordet:

```bash
cp .env.example .env
```

Start appen:

```bash
docker compose up -d --build
```

Åpne:

```text
http://192.168.20.218:8108
```

Appen skal være lokal. Den bør ikke eksponeres åpent på internett.
