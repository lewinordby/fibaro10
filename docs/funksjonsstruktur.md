# Funksjonsstruktur for Fibaro10 V2

Dette dokumentet beskriver ønsket funksjonsdeling i V2. Målet er å unngå overlapp mellom sider og gjøre videre utvikling mer forutsigbar.

## Prinsipp

Hver side skal ha én hovedrolle:

| Rolle | Formål | Eksempler |
| --- | --- | --- |
| Dashboard | Rask status og utvikling | Dashboard omsetning, parkering, soling, drift |
| Oversikt | Analyse og hovedtall for et domene | Omsetning oversikt, Soling oversikt |
| Arbeidsflate | Daglig arbeid med konkrete rader | Parkeringer, Kjøretøy, Enkeltimer, Produkter |
| Kontroll | Avstemming mot eksterne kilder | Oppgjør, Elvia-kontroll, Datakvalitet |
| Teknisk drift | Jobber, datakilder, system og verktøy | Datakilder, Systemkart, Buildlogg, OwnTracks |

## Anbefalt menyopprydding

### Omsetning

Behold:

- `Oversikt`
- `Månedsoversikt`
- `Årssammenligning`
- `Periodesammenligning`

Unngå at oppgjør og avstemming ligger direkte under Omsetning. Det hører bedre hjemme på domenene Parkering og Soling, mens totalsammenstilling kan vises som tabell på omsetningsoversikten.

### Parkering

Behold:

- `Parkeringer` som standard arbeidsflate
- `Dagslinje`
- `Kjøretøy`
- `Områder`
- `Prognose`
- `Årssammenligning`
- `Oppgjør`
- `Datakvalitet`

Skjult/utfaset fra meny:

- `Oversikt` er bevart som rute, men skal ikke være hovedinngang fordi den overlapper med dashboard, parkeringer og kjøretøy.
- `Bilstatistikk` er bevart som rute, men skal løftes inn i `Kjøretøy` når tallene trengs.

### Soling

Behold:

- `Oversikt`
- `Årssammenligning`
- `Dagslinje`
- `Enkeltimer`
- `Senger`
- `Medlemmer`
- `Produkter`
- `Oppgjør`

Vurder sammenslåing:

- `Statistikk` og `Detaljer` bør enten få klart ulike formål eller samles i `Oversikt`.
- `Prognose` bør beholdes bare hvis den faktisk brukes operativt.

### Energi

Behold:

- `Status`
- `Elvia`
- `Forbruk per seng`
- `Kurser`
- `Laster`

Vurder sammenslåing:

- `Elvia-kontroll` kan bli en fane/seksjon under `Elvia`.
- `Verktøy` kan flyttes til Admin hvis den bare er teknisk.

### Admin

Admin bør være teknisk og operativt, ikke for vanlig analyse.

Behold:

- `Oppgaver`
- `Kontroll`
- `Datakvalitet`
- `Datakilder`
- `Systemkart`
- `OwnTracks`
- `Buildlogg`
- `Brukere`
- `AI`

Vurder sammenslåing:

- `Drift`, `Teknisk`, `Manual` og `Verktøy` bør etter hvert samles i én tydelig driftsside eller fjernes hvis innholdet er duplikat.

`Kontroll` er inngangen til avstemminger som bruker eksterne kilder mot Fibaro10-data. Selve fagflatene ligger fortsatt under riktig domene, for eksempel parkering/oppgjør, soling/oppgjør og energi/Elvia.

## Neste oppryddingsregel

Når en ny side legges til, skal den plasseres i én av rollene over. Hvis siden passer i flere roller, er det normalt et tegn på at den bør deles eller at eksisterende side bør utvides i stedet.
