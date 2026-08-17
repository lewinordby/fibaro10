# Kort brukermanual for Lilletorget

Oppdatert 17.08.2026, build 1795.

Den levende og klikkbare manualen ligger under
`https://ny.lilletorget.net/system/manual`. Dette dokumentet er en kort
tekstversjon for Git, backup og gjenoppretting.

## Start her

| Behov | Gå til | Bruk |
| --- | --- | --- |
| Se økonomisk status | `/omsetning/` | Omsetning fra parkering og soling med relevante sammenligninger. |
| Se saker som må følges opp | `/operasjon/` | Prioritert arbeidskø, kritiske hendelser og kontroller. |
| Sjekke om data er ferske | `/system/datakilder` | Sist OK, alder, neste kjøring, avhengigheter og feil. |
| Finne en tjeneste | `/system/undersystemer` | Klikkbare webflater og health-lenker. |
| Forstå arkitekturen | `/system/systemkart` | Komponenter, forbindelser og teknisk rolle. |
| Se hva som er endret | `/system/build` | Bestilling, endringer, apper, tester og deploy. |
| Brukere og tilgang | `/system/brukere` | Brukere, roller, passord og tilgang. |

Alle stier over ligger under `https://ny.lilletorget.net`.

## De elleve appene

| App | Start | Hovedformål |
| --- | --- | --- |
| Omsetning | `/omsetning/` | Samlet økonomi, måned, år og periodesammenligning. |
| Parkering | `/parkering/` | Parkeringer, kjøretøy, oppgjør, prognose og analyse. |
| Soling | `/soling/` | Soltimer, bilder, dagslinje, produkter, medlemmer og oppgjør. |
| Koble | `/koble/` | Kontroll av sannsynlige koblinger mellom bil og SUN2-ID. |
| Bygg | `/bygg/` | Ventilasjon, klima og lys. |
| Renhold | `/renhold/` | Robotstatus, planer, vann og nattrapporter. |
| Kontroll | `/kontroll/` | Dører, solrom, alarmer, pullerter og fasadekontroll. |
| Energi | `/energi/` | Sanntidsforbruk, Elvia, kurs/last og forbruk per seng. |
| Vedlikehold | `/vedlikehold/` | Oppgaver, besøk, notater og historikk. |
| Operasjonssentral | `/operasjon/` | Arbeidskø, kritiske avvik, datakvalitet og søk. |
| Eiendeler | `/eiendeler/` | Teknisk register, plassering, service og garanti. |
| Rapporter | `/rapporter/` | Samlet inngang til økonomiske og operative rapporter. |
| System | `/system/` | Datakilder, jobber, brukere, manual, build og verktøy. |

## Daglig kontroll

1. Åpne Omsetning og kontroller total, parkering, soling og kildetidspunkt.
2. Åpne Operasjonssentral og se om noe står i arbeidskø eller som kritisk.
3. Bruk Parkering -> Parkeringer for dagens aktive og avsluttede parkeringer.
4. Bruk Soling -> Dagslinje eller Soltimer for dagens rom og timer.
5. Bruk Bygg og drift for dører, klima, lys, pullerter og renhold.
6. Gå til System -> Datakilder før du konkluderer med at en graf eller sum er feil.

## Når noe ser feil ut

| Problem | Sjekk først | Deretter |
| --- | --- | --- |
| Tall mangler eller virker gamle | `/system/datakilder` | Kontroller sist OK, alder, neste kjøring og feilmelding. |
| Parkering stemmer ikke | `/parkering/parkeringer` | Sjekk EasyPark-import, kilde og oppgjør. |
| Soling stemmer ikke | `/soling/enkeltimer` | Sjekk timer, dagslinje, produkter, bilder og SUN2-jobber. |
| Strøm avviker | `/energi/elvia-kontroll` | Kontroller målebrudd, nullstillinger og manglende laster. |
| Lys eller ventilasjon virker feil | `/bygg/lys` eller `/bygg/ventilasjon` | Se måleverdier, hendelser og innstillinger samme dag. |
| Robotjobb mangler | `/renhold/rapport` | Sammenlign gjeldende plan, faktisk jobb, batteri og vannstatus. |
| En app svarer ikke | `/system/systemkart` | Finn riktig tjeneste, health-lenke og avhengighet. |

## Viktige datakilder

- HC3: energi, lys, ventilasjon, dører og styringsstatus.
- EasyPark og Flowbird/ParkNordic: parkering, betaling og oppgjør.
- SUN2: soltimer, produkter, medlemmer, senger og finansgrunnlag.
- Axis og UniFi Protect: bilder, tidslenker og fysisk kontroll.
- Yr: temperatur, fukt, vind, skydekke og nedbør.
- Elvia: manuelt importert kontrollgrunnlag for strøm.
- Roborock og Dreame: robotstatus, planer, telemetri, vann og jobber.
- OwnTracks: waypoints, sonebesøk og vedlikeholdsbesøk.
- SVV, Biluppgifter og Tjekbil: norske, svenske og danske kjøretøydata.

## Roller og ansvar

- Mantis på `ny.lilletorget.net` er gjeldende brukerflate.
- Fibaro10 er produksjonskritisk kjerne/API og intern reserveflate.
- Fag-API-ene på port 8151-8158 oversetter mellom Mantis og Fibaro10.
- Innsamlere kjører separat slik at EasyPark, SUN2, kamera og roboter kan
  feilsøkes uten å stoppe resten av løsningen.
- Datakilder er fasit for friskhet. Buildloggen er fasit for endringer.
- Originaldata og kildereferanser skal beholdes når det er mulig.

## Mobil- og spesialflater

| Flate | Adresse |
| --- | --- |
| Online dashboard | `https://online.lilletorget.net` |
| Vedlikehold mobil | `https://vedl.lilletorget.net` |
| Alarm mobil | `https://alarm.lilletorget.net` |
| iPad | `https://ipad.lilletorget.net` |
| OwnTracks | `https://owntracks.lilletorget.net` |

Bruk `/system/undersystemer` for oppdatert katalog over alle webflater.
