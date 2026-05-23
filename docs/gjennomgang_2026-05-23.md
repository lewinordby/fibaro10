# Gjennomgang av Fibaro10 - 23.05.2026

Dette er en praktisk gjennomgang etter en design- og kodeopprydding. Målet var å forbedre brukeropplevelse, ytelse og sluttbrukerdokumentasjon uten å gjøre store strukturelle endringer som kan skape risiko i drift.

## Viktigste funn

- Appen fungerer godt som ett samlet driftspanel, men flere sider hadde litt ulik visuell rytme. En felles poleringsrunde i `static/app.css` gjør kort, tabeller og navigasjon roligere og mer konsistent.
- `main.py` er stor og bør på sikt deles opp i moduler for lys, ventilasjon, renhold, soling, energi, AI og auth. Det er likevel tydelige funksjonsgrenser, så det er trygt å gjøre mindre forbedringer videre.
- Solinggrafen hadde en subtil JavaScript-feil der år kunne behandles ulikt som tall og tekst. Det kunne gjøre avhuking upålitelig etter at et år var slått av/på.
- Tunge HTML- og JSON-svar kan bli store etter hvert som datamengdene vokser. GZip-komprimering er lagt på som lavrisiko ytelsesforbedring.
- Sluttbrukeren manglet et tydelig sted å gå for forklaring. PDF-manualen er nå lagt inn som statisk fil og lenket fra dashboard og konto.

## Endringer gjennomført

- La til GZip-komprimering i FastAPI for HTML/JSON over 1 KB.
- La til hurtigkort på Status: Dagslinje, Lux mot i går, Temperatur og Manual.
- La inn manual-lenke under Konto.
- Polerte global CSS for fokusmarkering, kort, tabeller, hover og mobilbredder.
- Fikset årvalg i solinggrafen og lagrer valgte år i nettleserens `localStorage`.
- Bygget ny PDF-manual: `static/manualer/sun2_driftsmanual.pdf`.
- La inn generator for manualen: `scripts/build_user_manual.py`.

## Anbefalte neste steg

- Del `main.py` i flere moduler når appen er rolig i drift. Start med rene områder som `renhold`, `soling` og `energi`.
- Lag en enkel adminside for dokumentasjon/versjon, slik at manual, siste deploy og systemstatus kan ses på ett sted.
- Vurder databaseindekser hvis datamengdene for Elvia, soling eller 5-minutterslogger blir merkbart tregere.
- Når energiområdet videreutvikles, bør det få egen graf for forbruk per dag/uke og sammenligning mot soling.
- AI-søk bør få ferdige eksempelspørsmål per datasett når API-kvoten er på plass.
