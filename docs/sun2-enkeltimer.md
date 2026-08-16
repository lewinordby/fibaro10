# SUN2 enkelttimer

Oppdatert 16.08.2026.

Dette dokumentet beskriver flyten for å hente enkelt-solinger fra SUN2 Owner og vise dem i Lilletorget drift.

## Formål

Dagsfilene fra SUN2 gir gode totalsummer per rom og dato, men de sier lite om når på dagen solingene skjedde. Enkelttimer brukes derfor til:

- dagslinje per fysisk rom
- raskere status på dagens aktivitet
- søk på SUN2-id, rom, periode, betaling og status
- kobling mot energimålinger for å estimere forbruk per seng

## Arkitektur

```text
SUN2 Owner
  -> sun2_session_scraper på QNAP/Docker
  -> JSON-fil i lokal data-katalog
  -> POST /api/sun2/sessions/ingest
  -> Fibaro10-tabeller
     - sun2_tanning_sessions
     - sun2_session_import_runs
  -> Soling -> Dagslinje / Enkeltimer / Detaljer
```

## Drift

Skraperen kjøres løpende, omtrent hvert 5. minutt. Den henter nyere enkelttimer og poster dem til Fibaro10. Importen er idempotent: samme soling kan sendes på nytt uten at den skal telles dobbelt.

Datakildestatus vises i:

```text
Admin -> Datakilder -> Sun2 enkelttimer
```

Forventet rytme i Fibaro10 er nå:

- OK: siste vellykkede import innen ca. 7 minutter
- Varsel: eldre enn ca. 20 minutter

## Rom-identitet

SUN2-navn har endret seg over tid. Appen bruker derfor egen fysisk rom-id:

- Rom 1-9 mappes direkte til fysisk rom 1-9.
- Gamle rader med `Solarium -` mappes til gammelt fysisk rom 10.
- Nyere SUN2-rom 10, 11 og 12 mappes til fysisk rom 11, 12 og 13.
- Fysisk rom 10 er tatt ut av drift og vises derfor ikke som aktivt rom i dagslinjen.

Aktiv romkobling for VIP er derfor:

| Visning | Intern rom-ID | Sun2-seng |
| --- | --- | --- |
| Solrom 10 | `rom-11` | `679` |
| Solrom 11 | `rom-12` | `680` |
| Solrom 12 | `rom-13` | `681` |

Sun2-seng-ID brukes som stabil identitet dersom en importert rad har en eldre eller feil rom-ID.

## Døralarm og soltime

Når en solromdør lukkes, leter Fibaro10 etter en betalt time for riktig Sun2-seng. Koblingen godtas når betalingen
ligger nær den konkrete dørlukkingen, eller når døren lukkes på nytt mens en fysisk soltime allerede pågår. En
gammel avsluttet soltime kan derfor ikke skjule en ny dørlukking.

Alarmforløpet er:

- 0-8 minutter: normal ventetid. Ingen advarsel eller melding.
- 8-15 minutter: gul observasjon i grensesnittet. Ingen melding.
- 15 minutter: Fibaro10 ber `sun2_session_scraper` kjøre en ekstra synkronisering av dagens enkelttimer.
- 17 minutter: ett ordinært varsel dersom synkroniseringen var vellykket og riktig soltime fortsatt mangler.
- 20 minutter: ett ordinært varsel dersom Sun2-synkroniseringen feilet. Meldingen sier at datakilden ikke kunne bekreftes.
- 25 minutter: én kritisk eskalering dersom døren fortsatt er lukket uten soltime.

Rett før en melding legges i ntfy-køen, spør Fibaro10 HC3 direkte om den aktuelle døren. Dersom HC3 viser at
døren er åpen, korrigeres lokal status og varselet stoppes. Varsler identifiseres med rom, dørlukking, årsak og
eventuell soltime. Det sendes derfor ikke et nytt varsel hvert 15. minutt for samme hendelse; samme dørlukking kan
bare gi ett ordinært varsel og eventuelt én kritisk eskalering.

Overtidsalarmen er uendret: gul markering etter 5 minutter over forventet solslutt og ett varsel etter 10 minutter,
også da med fersk kontroll mot HC3 før utsending. API-kall fra grensesnittet er lesende og kan ikke sende alarm.

## Samspill med energi

Energi -> Forbruk per seng bruker enkelttimer sammen med HC3 differanseforbruk. En soling brukes bare i beregningen når:

- nøyaktig én seng er i bruk
- alle andre senger har vært stoppet i minst 3 minutter
- målingen starter tidligst 2 minutter etter solingens start
- målingen stopper senest 1 minutt før solingen slutter
- det finnes minst 3 rene minuttmålinger

Dette reduserer risikoen for at kjølevifter eller overlappende solinger gir feil estimat.

## Feilsøking

Hvis enkelttimer ikke oppdateres:

1. Sjekk Admin -> Datakilder.
2. Sjekk webflaten til `sun2_session_scraper` på QNAP.
3. Se etter feilfiler i scraperens `data/session_errors`.
4. Kontroller at Fibaro10-brukeren loggeren bruker fortsatt har tilgang.
5. Sammenlign antall i SUN2 Owner med Soling -> Enkeltimer for samme periode.

Hvis SUN2-siden endrer seg, må selektorene i scraperen justeres. Debug-HTML og skjermbilde lagres når skraperen ikke klarer å lese rader.
