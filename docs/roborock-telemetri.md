# Roborock-telemetri

Oppdatert 13.08.2026.

## Formål

Telemetriloggen samler alle lesbare verdier som er nyttige for drift og videre analyse. Den er laget for å
vise hva robotene faktisk rapporterer før vi bestemmer hvilke verdier som skal gi varsler, nøkkeltall eller
vedlikeholdsoppgaver.

Dataflyten er:

```text
Roborock lokal LAN-API
  -> Roborock_logger
  -> POST /api/renhold/telemetry/ingest
  -> roborock_telemetry_samples / roborock_telemetry_events / roborock_probe_results
  -> Bygg og drift -> Renhold -> Robotvaskere -> valgt robot
```

## Intervaller

| Løp | Standard | Innhold |
| --- | ---: | --- |
| Dynamisk telemetri | 60 sekunder | Status, batteri, rengjøring, lading, dokk, vann/tank, signal og komplett råstatus. |
| Utvidet API-kontroll | 15 minutter | Innstillinger, forbruksdeler, summer, planer og øvrige modellspesifikke lesekall. |
| Ordinær Roborock-synk | 5 minutter | Robotregister, vaskhistorikk, planer, forbruksdeler og øvrig eksisterende synk. |

Renholdsoversikten lar minutt-telemetrien overstyre en eldre femminuttersstatus når de er uenige. Det hindrer at en
avsluttet jobb blir stående som aktiv frem til neste ordinære synk.

Et kall som robotmodellen eksplisitt avviser som ukjent eller ikke støttet, hoppes over resten av prosessens
levetid. Det prøves på nytt etter omstart eller ny utrulling. Dette hindrer unødvendig belastning.

## Dynamiske verdier

Følgende normaliseres og lagres i `roborock_telemetry_samples`. Den komplette leverandørresponsen lagres i
tillegg som JSON, slik at nye felt ikke går tapt.

| Område | Verdier |
| --- | --- |
| Robot | statuskode og navn, batteri, feilkode, rengjøring pågår, returnerer, rengjøringstid, areal og prosent. |
| Rengjøring | sugekraft, vannmodus og moppmodus. |
| Lading | ladestatus og om aktiv lading pågår. |
| Dokk | dokktype, dokkfeil, støvtømming, automatisk støvtømming, moppevask, vaskefase, vaskeklar og tørking. |
| Vann og beholdere | vannmangel, vanntankstatus, tank montert, rentvann, skittentvann, støvpose, rengjøringsmiddel og vaskefilter. |
| Nettverk | lokal IP, RSSI og Roborock-feltene `dss` og `rss`. |
| Rådata | samtlige felter fra `GET_STATUS` og `GET_NETWORK_INFO`. |

Verdier som ikke finnes på en modell vises som `Ikke støttet`, ikke som en feiltilstand.

## Utvidede lesekall

Loggeren prøver følgende skrivefrie kommandoer. Resultatet og støttestatusen vises under `API-dekning` på
robotdetaljen.

```text
GET_CONSUMABLE
GET_CLEAN_SUMMARY
GET_SOUND_VOLUME
GET_DND_TIMER
GET_CHILD_LOCK_STATUS
GET_LED_STATUS
GET_FLOW_LED_STATUS
GET_DUST_COLLECTION_MODE
GET_DUST_COLLECTION_SWITCH_STATUS
GET_SMART_WASH_PARAMS
GET_WASH_TOWEL_MODE
GET_WASH_TOWEL_PARAMS
GET_WASH_WATER_TEMPERATURE
GET_AUTO_DELIVERY_CLEANING_FLUID
APP_GET_DRYER_SETTING
GET_MOP_MOTOR_STATUS
GET_WATER_BOX_CUSTOM_MODE
GET_HANDLE_LEAK_WATER_STATUS
GET_ROOM_MAPPING
GET_TIMEZONE
GET_TIMER
GET_SERVER_TIMER
GET_TIMER_SUMMARY
GET_SERIAL_NUMBER
GET_CARPET_MODE
GET_CUSTOM_MODE
GET_DOCK_INFO
GET_MAP_STATUS
GET_PERSIST
GET_VALLEY_ELECTRICITY_TIMER
```

Qrevo/P10-modellene gir blant annet dokk-, moppevask-, tørke-, vann- og smartvaskverdier. S8 med enkel
auto-tømmestasjon har færre dokkfunksjoner og vil derfor korrekt vise flere kall som ikke støttet.

## Hendelser

`roborock_telemetry_events` får bare en rad når en viktig tilstand endres. Første måling etablerer
utgangspunktet og lager ingen kunstige hendelser.

Endringer logges for:

- robotstatus, lading og robotfeil
- dokkfeil, støvtømming, moppevask, vaskefase og tørking
- rentvann, skittentvann, støvpose, rengjøringsmiddel og vannmangel
- vanntank montert og automatisk støvtømming

Feilkoder og dokkfeil merkes kritiske. Problemtilstander for vann og beholdere merkes som advarsler. Dette
gir et stabilt grunnlag for varsling senere uten å varsle på hvert minuttpunkt.

## Det API-et ikke gir oss

De testede robotene rapporterer ikke direkte:

- effekt i watt eller energi i kWh
- liter rentvann eller skittentvann
- prosentnivå i vannbeholder eller støvpose
- et sikkert tidspunkt for fysisk tømming eller påfylling dersom statuskoden ikke endres

Strømforbruk må derfor måles på strømtilførselen til dokken. Faktisk vannforbruk må eventuelt beregnes fra
statusendringer og vaskesykluser, eller måles med ekstern sensor. Roborock-statusene kan fortsatt brukes til
å oppdage tomt rentvann, full skittentvannstank, full/manglende støvpose og enkelte dokkfeil der modellen
rapporterer dette.

## Naturlige neste steg

Når loggen har samlet representative data, bør vi vurdere:

1. Varsling ved tomt rentvann, full skittentvannstank, støvposeproblem eller dokkfeil.
2. Beregnet ladeforløp og unormal tid på lader kombinert med ekstern energimåling.
3. Automatisk vedlikeholdspost basert på forbruksdel-timer eller gjentatte feil.
4. Kontroll av planlagt mot faktisk rengjøring og om roboten fullfører hele arealet.
5. Sammenstilling av støvtømming, moppevask og vannstatus med tidspunkt for manuell oppfølging.

Ingen av disse automatiseringene bør aktiveres før vi har sett hvilke koder hver robot faktisk sender i
normal drift og ved reelle mangeltilstander.
