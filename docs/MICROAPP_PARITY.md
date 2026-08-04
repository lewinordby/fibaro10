# Funksjonsparitet mellom Fibaro10 og mikroappene

Dette dokumentet er kontrollisten for flyttingen fra Fibaro10-grensesnittet til mikroappene på port 8151-8158.
En funksjon regnes ikke som flyttet bare fordi en rute finnes. Data, handlinger, detaljvisning, filtrering og
direktelenker skal også virke.

## Statusforklaring

- **Komplett**: arbeidsflyten finnes i mikroappen og har relevant spesialvisning eller redigering.
- **Delt**: funksjonen finnes, men presentasjonen deles med den generiske modulvisningen.
- **Arkivert**: et tidligere designforsøk, ikke en egen funksjon. Dataene finnes i den valgte sluttvisningen.

## Omsetning

| Arbeidsflyt | Mikroapp | Status |
| --- | --- | --- |
| Operativt dashboard | Omsetning / Dashboard | Komplett |
| Ukeutvikling, topplister og nøkkeltall | Omsetning / Oversikt | Komplett |
| Måned dag for dag | Omsetning / Måned | Komplett |
| Akkumulert årssammenligning | Omsetning / År | Komplett |
| Dag-, uke- og månedssammenligning | Omsetning / Periodesammenligning | Komplett |

## Parkering

| Arbeidsflyt | Mikroapp | Status |
| --- | --- | --- |
| Aktivitetsdashboard | Parkering / Dashboard | Komplett fra build 1641 |
| Ukeutvikling og siste parkeringer | Parkering / Oversikt | Komplett |
| Dagsliste uten sideinndeling | Parkering / Liste | Komplett |
| Belegg og 23 plasser | Parkering / Dagslinje | Komplett |
| Kjøretøy, eier og parkeringshistorikk | Parkering / Register | Komplett |
| Kameraobservasjoner og OCR-kontroll | Parkering / Observerte biler | Komplett |
| Områder, eksterne oppslag og datakvalitet | Parkering / Områder og Oppslag | Delt |
| Periode-, års-, tidspunkt- og ukeanalyse | Parkering / Analyse | Komplett |
| ParkNordic-oppgjør og originalbilag | Parkering / Oppgjør | Komplett |

## Soling

| Arbeidsflyt | Mikroapp | Status |
| --- | --- | --- |
| Aktivitetsdashboard | Soling / Dashboard | Komplett fra build 1641 |
| Ukeutvikling og nøkkeltall | Soling / Oversikt | Komplett |
| Dagslinje med energi | Soling / Dagslinje | Komplett |
| Enkelttimer, Sun2-ID og bildearkiv | Soling / Enkelttimer | Komplett |
| Periode- og årssammenligning | Soling / Analyse | Komplett fra build 1641 |
| Prognose og statistikk | Soling / Analyse | Delt |
| Rom-, måneds-, års- og importdetaljer | Soling / Datadetaljer | Komplett fra build 1641 |
| Senger, medlemmer og produkter | Soling / Kunder og senger, Oppgjør | Delt |
| Altera-kreditnota og originalbilag | Soling / Oppgjør | Komplett |

## Koble

| Arbeidsflyt | Mikroapp | Status |
| --- | --- | --- |
| Kandidater med sannsynlighet | Koble / Kandidater | Komplett |
| Sun2-kontroll og biltreff | Koble / Kontroll | Komplett |
| Bekreft og avvis | Koble / Kandidater | Komplett |
| Treffgrunnlag | Koble / Treffgrunnlag | Komplett |
| Jobbstatus og parametere | Koble / Jobbstatus | Komplett |

## Bygg og drift

| Arbeidsflyt | Mikroapp | Status |
| --- | --- | --- |
| Samlet driftsstatus | Bygg og drift / Driftsoversikt | Komplett |
| Ventilasjonsgrafer og styringsregler | Bygg og drift / Ventilasjon | Komplett |
| Lysgrafer og styringsregler | Bygg og drift / Lys | Komplett |
| Dørstatus og andre dører | Bygg og drift / Dører | Komplett fra build 1641 |
| Solrom med aktiv soltime | Bygg og drift / Solrom | Komplett |
| Dør, soltime, effekt og dagshendelser | Bygg og drift / Romkontroll | Komplett |
| Alarmhistorikk og avvik | Bygg og drift / Alarm og Avvik | Komplett fra build 1641 |
| Pullert, fasade og trapp med bilder og AI | Bygg og drift / Pullerter | Komplett |
| Roborock-status og historikk | Bygg og drift / Renhold | Delt |

Tidligere sider med navn som oversikt-ny, romkontroll-ny, romkontroll-ny2, solrom-ny,
Solrom-2 og Dører2 var parallelle designforsøk. De er arkivert som referansekode. Funksjonene de
undersøkte er samlet i Dører, Solrom og Romkontroll.

## Energi

| Arbeidsflyt | Mikroapp | Status |
| --- | --- | --- |
| Sanntid, fordeling og historikk | Energi / Status | Komplett |
| Elvia mot HC3 | Energi / Kontroll | Komplett |
| Elvia-opplasting | Energi / Import | Komplett |
| Kurs, Z-Wave-enheter, målere og laster | Energi / Kurs og last | Komplett |
| Redigering av kurser og laster | Energi / Kurser og Laster | Komplett |
| Forbruk per solseng | Energi / Forbruk per seng | Komplett |

## Vedlikehold

| Arbeidsflyt | Mikroapp | Status |
| --- | --- | --- |
| Opprette, søke og redigere oppgaver | Vedlikehold / Oppgaver | Komplett |
| Besøk fra OwnTracks | Vedlikehold / Besøk | Komplett |
| Besøksnotat og tilknyttede oppgaver | Besøksdetalj | Komplett |

## System

| Arbeidsflyt | Mikroapp | Status |
| --- | --- | --- |
| Datakilder, planer og kjøringer | System / Datakilder | Komplett |
| Jobber, kontroll og datakvalitet | System / Drift | Komplett |
| Brukere, roller og passord | System / Brukere | Komplett |
| Varslingsabonnement | System / Varslinger | Komplett |
| Systemkart og klikkbare undersystemer | System / Arkitektur | Komplett |
| Manual med kapitler | System / Manual | Komplett |
| Buildlogg og builddetaljer | System / Buildlogg | Komplett |
| Mobilforhåndsvisninger | System / Mobilflater | Komplett |

## Testkrav

Før utrulling skal minst følgende være grønt:

1. Alle frontend-bygg.
2. tests/test_domain_microapps.py.
3. Domenetester for berørte apper.
4. Direkte lasting av alle nye ruter etter innlogging.
5. API-respons uten 401, 403, 404 eller 5xx på spesialvisningene.
6. Visuell kontroll i lys modus på desktop.
