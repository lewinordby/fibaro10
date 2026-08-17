# Funksjonsparitet mellom Fibaro10 og Mantis

Oppdatert 17.08.2026, build 1795.

Dette dokumentet er kontrollisten for flyttingen fra Fibaro10-grensesnittet til
Mantis-appene på `ny.lilletorget.net`. Adapterne på port 8151-8158 er fortsatt
dataveien mellom Mantis og kjernen. En funksjon regnes ikke som flyttet bare
fordi en rute finnes. Data, handlinger, detaljvisning, filtrering og
direktelenker skal også virke.

## Statusforklaring

- **Komplett**: arbeidsflyten finnes i mikroappen og har relevant spesialvisning eller redigering.
- **Komplett i tabellflate**: funksjonen bruker felles tabellvisning med søk, eksaktsøk, sortering og paginering.
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
| Områder, eksterne oppslag og datakvalitet | Parkering / Områder og Oppslag | Komplett |
| Arbeidslister for manglende navn og område | Parkering / Navnoppslag og Områdeoppslag | Komplett |
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
| Prognose og statistikk | Soling / Analyse | Komplett i tabellflate |
| Rom-, måneds-, års- og importdetaljer | Soling / Datadetaljer | Komplett fra build 1641 |
| Senger, medlemmer og produkter | Soling / Kunder og senger, Oppgjør | Komplett i tabellflate |
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
| Roborock-status, kart, planer, forbruksdeler og historikk | Bygg og drift / Renhold | Komplett |

Alternative sider med navn som oversikt-ny, romkontroll-ny, romkontroll-ny2, solrom-ny,
Solrom-2 og Dører2 er fortsatt tilgjengelige under **Alternative dørvisninger**. De beholdes som
egne vurderingsflater inntil brukeren har valgt hvilke visninger som skal være permanente.

## Energi

| Arbeidsflyt | Mikroapp | Status |
| --- | --- | --- |
| Sanntid, fordeling og historikk | Energi / Status | Komplett |
| Elvia mot HC3 | Energi / Kontroll | Komplett |
| Elvia-opplasting | Energi / Import | Komplett |
| Kurs, Z-Wave-enheter, utganger, målere og laster | Energi / Kurs og last | Komplett |
| Redigering av hierarki, HC3-koblinger, samlemålere og laster | Energi / Kurs og last | Komplett |
| Forbruk per solseng | Energi / Forbruk per seng | Komplett |

## Vedlikehold

| Arbeidsflyt | Mikroapp | Status |
| --- | --- | --- |
| Opprette, søke og redigere oppgaver | Vedlikehold / Oppgaver | Komplett |
| Besøk fra OwnTracks | Vedlikehold / Besøk | Komplett |
| Besøksnotat, rå OwnTracks-data og tilknyttede oppgaver | Besøksdetalj | Komplett |

## Operasjonssentral, eiendeler og rapporter

| Arbeidsflyt | Mantis-app | Status |
| --- | --- | --- |
| Prioritert arbeidskø og kritiske hendelser | Operasjonssentral | Komplett |
| Operative kontroller og behandlet historikk | Operasjonssentral | Komplett |
| Datakvalitet, automatiseringsverksted og universalsøk | Operasjonssentral | Komplett |
| Teknisk eiendelsregister og synkronisering | Eiendeler | Komplett |
| Samlet katalog over økonomi-, drift- og kontrollrapporter | Rapporter | Komplett |

## System

| Arbeidsflyt | Mikroapp | Status |
| --- | --- | --- |
| Datakilder, planer og kjøringer | System / Datakilder | Komplett |
| Jobber, kontroll og datakvalitet | System / Drift | Komplett |
| Brukere, roller og passord | System / Brukere | Komplett |
| Varslingsabonnement med direkte åpning i ntfy | System / Varslinger | Komplett |
| Systemkart og filtrerbare, klikkbare undersystemer | System / Arkitektur | Komplett |
| Manual med kapitler | System / Manual | Komplett |
| Buildlogg og builddetaljer | System / Buildlogg | Komplett |
| Mobilforhåndsvisninger | System / Mobilflater | Komplett |
| Idébank med mål, byggetrinn og kontrollpunkter | System / Ideer | Komplett |

## Felles arbeidsflyter

Alle tabellbaserte sider skal ha stabil sortering. Tabeller med minst åtte lokale rader skal ha søk,
og anførselstegn rundt søketeksten skal gi eksakt token-treff. Store lokale tabeller sideinndeles med
valg mellom 25, 50 og 100 rader. Serverpaginering og serverfiltre skal beholdes når API-et tilbyr dette.

## Testkrav

Før utrulling skal minst følgende være grønt:

1. Mantis `npm run build` og `npm run verify`.
2. Backendens `tests/test_domain_microapps.py` og dokumentasjonstester.
3. Domenetester for berørte API-er.
4. Direkte lasting av alle 127 Mantis-ruter og berørte detaljruter.
5. API-respons uten 401, 403, 404 eller 5xx på spesialvisningene.
6. Visuell kontroll i lyst og mørkt tema på desktop.
7. Direkte handlinger som abonnement, opplasting, redigering og detaljåpning skal prøves uten å endre produksjonsdata.
