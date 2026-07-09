# Gjennomgang av Fibaro10 / Lilletorget drift

Oppdatert 10.07.2026.

Dette dokumentet oppsummerer status etter de siste rundene med design, ytelse, datakilder, energi og dokumentasjon.

## Nåværende hovedbilde

Appen er nå et samlet driftspanel for Lilletorget:

- Status og datakilder
- Lys og lux
- Ventilasjon, temperatur og Yr
- Renhold / Roborock
- Soling / SUN2
- Energi / HC3 og Elvia
- AI-søk når OpenAI-kvote er tilgjengelig
- Admin, tilgang, manual, systemkart og teknisk oversikt

## Viktigste endringer siden første gjennomgang

- PDF-manualen er erstattet av levende dokumentasjon under `Admin -> Manual`.
- Teknisk dokumentasjon og systemkart ligger under `Admin -> Teknisk` og `Admin -> Systemkart`.
- Menyen er redesignet som V2 React/Ant Design-flate med hovedgruppene Dashboard, Økonomi, Bygg og drift og System.
- Navigasjons- og designsystemet ligger i `desktop_v2/src/styles/`.
- SUN2 enkelttimer kjøres nå løpende omtrent hvert 5. minutt, ikke bare nattlig.
- `Admin -> Datakilder` viser nå riktig forventet intervall og forklaring for alle datakilder.
- Energi har fått HC3 logging hvert 30. sekund, Elvia-import og Forbruk per seng.
- Tidssoner er ryddet: SUN2 og Elvia vises som kildetid, mens HC3/Yr vises i Europe/Oslo.
- Favicon og Lilletorget-logo er satt i appen.

## Stabilitet

Sist testet:

- Python-kompilering av hovedapp og lokale apper OK.
- Viktige live-sider svarer `200`.
- Viktige JSON-endepunkter svarer `200`.
- Favicon svarer `200`.
- Ingen kritiske 500-feil funnet i siste smoke-test.

## Kjente forbedringsområder

- `main.py` er fortsatt stor. På sikt bør den deles i moduler for auth, status, lys, ventilasjon, soling, energi, renhold og AI.
- Enkelte loggsider og JSON-endepunkter kan bli store. Neste ytelsesløft bør være mer server-side filtrering, paginering og kompakte API-svar.
- AI-søk er avhengig av korrekt OpenAI API-nøkkel og aktiv API-kvote. ChatGPT-abonnement alene gir ikke API-kvote.
- SUN2-skraping er avhengig av at SUN2 Owner ikke endrer HTML-strukturen vesentlig.

## Operativ kontroll

Daglig kontroll bør starte her:

```text
Dashboard -> Omsetning
Admin -> Datakilder
Admin -> Systemkart
```

Datakilder er spesielt viktig fordi det viser om lokale loggere og HC3 faktisk sender data.

## Neste anbefalte tekniske steg

1. Indeksere eller optimalisere de tyngste dataspørringene når datamengdene vokser.
2. Lage tydeligere paginering på de største logg- og importtabellene.
3. Splitte `main.py` i mindre moduler når funksjonaliteten er rolig.
4. Lage mer historikk/avviksanalyse for energi mot Elvia.
5. Videreutvikle AI-søk når API-kvote er på plass.
