# Funksjonsstruktur for Fibaro10 V2

Oppdatert 10.07.2026.

Dette dokumentet beskriver dagens funksjonsdeling i V2. Målet er å unngå overlapp mellom sider og gjøre videre utvikling mer forutsigbar.

## Prinsipp

Hver side skal ha én hovedrolle:

| Rolle | Formål | Eksempler |
| --- | --- | --- |
| Dashboard | Rask status og utvikling | Dashboard omsetning, parkering, soling og drift |
| Oversikt/analyse | Hovedtall, trender og nøkkeltabeller | Omsetning oversikt, Parkering oversikt, Soling oversikt |
| Arbeidsflate | Daglig arbeid med konkrete rader | Parkeringer, Kjøretøy, Enkeltimer, Besøk |
| Kontroll | Avstemming mot eksterne kilder | Oppgjør, Elvia-kontroll, Datakvalitet |
| Teknisk drift | Jobber, datakilder, system og verktøy | Datakilder, Systemkart, Buildlogg, Koble jobb |

Hvis en side får flere roller samtidig, skal den enten deles eller flyttes inn som seksjon på en eksisterende side.

## Hovedgrupper

| Gruppe | Innhold | Rolle |
| --- | --- | --- |
| Dashboard | Status | Operativt overblikk. |
| Økonomi | Omsetning, Parkering, Soling, Koble | Tall, aktivitet, oppgjør og kobling mellom betaling/bruk. |
| Bygg og drift | Energi, Ventilasjon, Lys, Solrom, Dører, Renhold, Vedlikehold | Teknisk drift og fysisk anlegg. |
| System | Ideer, Mobil, Admin | Systemoversikt, utvikling, manualer og kontrollflater. |

## Modulstruktur

### Dashboard

- `Omsetning`: viktigste økonomiske status, sammenligninger og oppdatertgrunnlag.
- `Parkering`: antall, aktivitet, kjøretøy og parkeringsstatus.
- `Soling`: antall, aktivitet, senger og solingsstatus.
- `Drift`: datakilder, energi, klima og operativ helsetilstand.

Dashboard skal vise nok til å ta raske valg, men ikke bli en komplett arbeidsflate.

### Omsetning

- `Oversikt`: års-/periodeoversikt, topp dager/måneder og samlet økonomi.
- `Periodesammenligning`: akkumulert sammenligning for dag/uke/måned.
- `Årssammenligning`: akkumulert årskurve for omsetning.
- `Månedsoversikt`: månedsgraf og månedstabeller.

Oppgjør ligger under Parkering og Soling fordi kontrollen eies av hvert fagdomene. Omsetning kan vise totalsammenstilling, men skal ikke overta detaljkontroll.

### Parkering

- `Oversikt`: analyseflate med ukesstatistikk og siste parkeringer.
- `Parkeringer`: daglig arbeidsflate med dagsvalg, EasyPark-oppdatering og radliste.
- `Dagslinje`: visuell kapasitets-/beleggsflate.
- `Kjøretøy`: søk, eier/kjøretøydata og historikk per bil.
- `Områder`: områdeanalyse med dato/tidsrom.
- `Prognose`: parkeringsprognoser etter import.
- `Årssammenligning`: akkumulert årssammenligning for parkering.
- `Oppgjør`: Park Nordic/EasyPark-oppgjør og kontroll mot interne kilder.
- `Datakvalitet`: SVV, Sverige/Danmark, område og kjøretøydata.

`Bilstatistikk` finnes som skjult rute og bør ikke utvides før innholdet har en tydelig rolle.

### Soling

- `Oversikt`: analyseflate for soling.
- `Årssammenligning`: akkumulert årssammenligning for soling.
- `Dagslinje`: daglig aktivitetslinje per seng/rom.
- `Enkeltimer`: arbeidsflate for soltimer, bilder, SUN2-id og manuell kontroll.
- `Oppgjør`: solingsoppgjør/kreditnota og kontroll mot SUN2.
- `Prognose`: solingsprognoser hvis operativ verdi.
- `Produkter`: produktsalg fra SUN2.
- `Senger`: rom/sengmetadata.
- `Medlemmer`: SUN2-medlemmer.
- `Statistikk` og `Detaljer`: beholdes, men bør ikke få ny funksjonalitet uten klar avgrensning mot Oversikt.

### Koble

Koble er et eget domene fordi det binder parkering og soling sammen.

- `Oversikt`: status, nøkkeltall og jobbstyring.
- `SUN2-kontroll`: grupperer biltreff etter SUN2-id.
- `Biltreff`: biler med gjentatte soltreff.
- `Kandidater`: manuell bekreftelse/avvisning.
- `Treffgrunnlag`: rågrunnlag for parkerings-/soltreff.
- `Jobb`: worker-status og parametere.

Koble skal ikke skrive endelig sannhet uten manuell bekreftelse.

### Energi

- `Status`: overblikk over forbruk og differanse.
- `Elvia-kontroll`: kontroll mellom Elvia-import og HC3-målinger.
- `Kurser`: kursoversikt.
- `Laster`: definerte laster.
- `Forbruk per seng`: beregnet forbruk per solseng.
- `Elvia`: opplasting og månedsdata.
- `Verktøy`: teknisk energiverktøy.

### Ventilasjon og lys

- Ventilasjon: `Dagslogg`, `Temperatur og fukt`, `Yr-logg`, `Hendelser`, `Innstillinger`.
- Lys: `Dagslogg`, `Lux-logg`, `Hendelser`, `Innstillinger`.

Regel: Dagslogg er visuell tidsserie. Innstillinger er styringsregler. Hendelser er rå/operativ logg.

### Solrom

- `Nå`: operativ status for rom 1-12 med ledig/i bruk, dørstatus, koblet Sun2-time, forventet ut og varselnivå.
- `Dagskontroll`: valgt dato med høyere romkort, åpningstidslinje og hendelsesliste per rom for dør, soltime, inngang og effektmarkører.
- `Romdetalj`: skjult/klikkbar rute fra romkort for historikk på ett rom.

Solrom bruker motsatt semantikk av byggdører: åpen dør betyr normalt ledig, lukket dør betyr normalt i bruk.

### Dører2

- `Situasjon`: ny operativ flate som sorterer solrom etter varsel og viser romkart med dør, Sun2-time og effekt i samme tidslinje.
- `Romdetalj`: skjult/klikkbar rute fra romkort. Viser valgt rom, dagslinje, hendelser nyest først og perioder med forventet ut.
- `Byggdører`: byggdører vurdert mot normalposisjon, med avvik først og siste endringer.

Dører2 er en ny arbeidsflate ved siden av eksisterende Dører/Solrom. Den skal brukes til å vurdere om rom eller byggdører krever handling.

### Dører

- `Oversikt`: kompakt status for solrom og andre dører.
- `Andre dører`: byggdører som normalt skal vurderes annerledes enn solrom.
- `Rådata`: alle dørhendelser fra HC3.

Eldre romkontroll-varianter ligger fortsatt som skjulte ruter for sammenligning, men daglig solromdrift skal bruke hovedmenyen `Solrom`.

### Vedlikehold og renhold

- `Vedlikehold/Oversikt`: vedlikeholdslogger, oppgaver og oppfølging.
- `Vedlikehold/Besøk`: OwnTracks-besøk på Lilletorget koblet til oppgaver.
- `Renhold/Oversikt`: renholdsstatus.
- `Renhold/Roboter`: Roborock-status og robotdata.

Mobil vedlikeholdsregistrering ligger i egen app på `vedl.lilletorget.net`, men skriver til samme datagrunnlag.

### System

- `Ideer`: midlertidig vurderingsområde for nye funksjoner.
- `Mobil`: speiling av mobilskjermer i rutenett.
- `Manual/Oversikt`: intern manual og lenker, med egne undersider for daglig bruk, menyvalg, økonomi, bygg/drift, system, datagrunnlag, rutiner og feilsøking.
- `Admin/Oppgaver`: systemoppgaver og forbedringspunkter.
- `Admin/Kontroll`: avstemminger og kontrollinnganger.
- `Admin/Datakvalitet`: dataproblemer på tvers.
- `Admin/Analyse`: tekniske analyser.
- `Admin/Drift`: driftsstatus.
- `Admin/Buildlogg`: leveransehistorikk.
- `Admin/Datakilder`: importstatus og datakildeforklaring.
- `Admin/Systemkart`: komponenter, underapper og URL-er.
- `Admin/AI`: AI-innstillinger.
- `Admin/Teknisk`: teknisk drift.
- `Admin/Brukere`: brukeradministrasjon.
- `Admin/Verktøy`: tekniske verktøy.

## Regel for nye sider

1. Plasser siden i eksisterende hovedgruppe.
2. Definer om siden er dashboard, oversikt, arbeidsflate, kontroll eller teknisk drift.
3. Ikke lag en ny side hvis en eksisterende side kan få en tydelig seksjon uten overlapp.
4. Store datasett skal ha eksplisitt begrensning, filter eller egen detaljside.
5. Dokumenter ny side i `docs/desktop-v2.md`, og legg den inn i route-audit/smoke hvis den skal være fast menyvalg.
