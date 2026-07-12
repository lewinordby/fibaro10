# Kort brukermanual for Lilletorget drift

Oppdatert 12.07.2026, build 1533.

Dette er tekstversjonen av den korte oversiktsmanualen. Den levende manualen ligger nå som eget hovedmenyvalg `Manual`, med egne undersider for oversikt, daglig bruk, menyvalg, datagrunnlag, rutiner og feilsøking.

## Start her

| Behov | Gå til | Bruk |
| --- | --- | --- |
| Se dagens drift | `/status/omsetning` | Dashboard for omsetning, parkering, soling og drift akkurat nå. |
| Sjekke om data er ferske | `/admin/datakilder` | Importjobber, HC3, SUN2, EasyPark, Yr og underapper. |
| Finne en tjeneste | `/admin/systemkart` | Apper, underapper, porter, URL-er og health-lenker. |
| Se hva som sist ble endret | `/admin/build` | Buildlogg med bestilling, endringer, tester og berørte apper. |
| Brukere og tilgang | `/admin/brukere` | Roller, master-funksjoner, passord og tilgangslogg. |

## Hovedområder

| Område | Gå til | Hva du kan se/gjøre |
| --- | --- | --- |
| Omsetning | `/omsetning/oversikt` | År, måned, dag, toppdager, toppmåneder og samlet kontroll mot oppgjør. |
| Parkering | `/parkering/parkeringer` | Dagens parkeringer, kjøretøy, eier, bilinfo, områder, kamera og oppgjør. |
| Soling | `/soling/dagslinje` | Soltimer, rom, senger, medlemmer, produkter, bilder, prognoser og oppgjør. |
| Koble | `/koble/oversikt` | Sannsynlige koblinger mellom bilnummer og SUN2-ID basert på tidstreff. |
| Energi | `/energi/status` | Realtime HC3-forbruk, kurser, laster, Elvia-kontroll og forbruk per seng. |
| Ventilasjon | `/ventilasjon/dagslogg` | Temperatur, fuktighet, Yr, viftehendelser og ventilasjonsinnstillinger. |
| Lys | `/lys/dagslogg` | Lux, skydekke, solhøyde, lysstatus, hendelser og styringsregler. |
| Dører | `/dorer/romkontroll` | Solrom, andre dører, åpne/lukke-historikk, romstatus, tidslinjevarianter og soltimekobling. |
| Vedlikehold | `/vedlikehold/besok` | Besøk på Lilletorget og oppgaver utført under hvert besøk. |
| Renhold | `/renhold/oversikt` | Roborock-status, siste jobber, robotdetaljer og loggerstatus. |
| Mobil og iPad | `/mobil/oversikt` | Kontroll av hva de lette mobil- og iPad-flatene viser. |
| Ideer | `/ideer/oversikt` | Forslag, analyseideer og mulige forbedringer før de flyttes inn i fagområder. |

## Når noe ser feil ut

| Problem | Sjekk først | Tiltak |
| --- | --- | --- |
| Tall mangler eller virker gamle | `Admin -> Datakilder` | Sjekk sist OK, alder, melding og neste planlagte jobb før du vurderer grafen. |
| Parkering stemmer ikke | `Parkering -> Parkeringer` | Sjekk EasyPark-import, dagens liste og kilde EasyPark/flowbird-parknordic. |
| Soling stemmer ikke | `Soling -> Enkeltimer` | Sjekk enkelttimer, dagslinje, produkter, bildearkiv og SUN2-scraper. |
| Strøm eller forbruk avviker | `Energi -> Elvia-kontroll` | Bruk Elvia som kontroll og HC3 som løpende datagrunnlag. |
| Lys eller ventilasjon virker feil | `Lys -> Dagslogg` og `Ventilasjon -> Dagslogg` | Sjekk lux, skydekke, solhøyde, temperatur, fukt og hendelser samme dag. |
| En underapp svarer ikke | `Admin -> Systemkart` | Bruk health-lenke, lokal URL og compose-service for å finne riktig tjeneste. |

## Underapper og datakilder

Løsningen består av hovedappen `fibaro10` og flere sideapper. De viktigste er:

| App | Bruk |
| --- | --- |
| `online_dashboard` | Begrenset ekstern mobilvisning på `online.lilletorget.net`. |
| `maintenance_mobile` | Mobil vedlikeholdsregistrering på `vedl.lilletorget.net`. |
| `fibaro10ipad` | Egen iPad-flate på `ipad.lilletorget.net`. |
| `owntracks_service` | Egen OwnTracks HTTP-server, waypoints og sonebesøk på `owntracks.lilletorget.net`. |
| `axis_camera_snapshots` | Henter og rydder Axis-bilder som kobles til soltimer. |
| `sun2_session_scraper` | Henter SUN2 enkelttimer, senger, medlemmer og produktsalg. |
| `easypark_downloader` | Henter EasyPark-data og holder parkeringsgrunnlaget oppdatert. |
| `car_info_lookup` | Svenske og danske kjøretøyoppslag etter SVV. |
| `parking_sun_linker` | Bakgrunnsmotor for kobling mellom parkering og SUN2-ID. |
| `roborock_logger` | Logger robotvaskere og vaskehistorikk. |

Bruk `Admin -> Systemkart` for klikkbare lenker, porter og health-status. Bruk `Admin -> Datakilder` for å se om datagrunnlaget faktisk er ferskt.

## Viktige prinsipper

- Hovedappen viser data fra egen database, ikke direkte fra tredjepartsflater i sanntid.
- HC3 poster energi, lys, ventilasjon og dørhendelser inn i Fibaro10.
- SUN2, EasyPark, Axis, OwnTracks, Roborock og kjøretøyoppslag kjører som egne tjenester ved siden av hovedappen.
- Datakilder er fasit for om en import eller logger er frisk.
- Buildlogg er fasit for hva som er endret og hvilke tester som ble kjørt.
- Systemkart er fasit for hvilke underapper og webflater som finnes.
