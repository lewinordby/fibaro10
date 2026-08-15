# Roborock_logger

Oppdatert 13.08.2026.

`Roborock_logger` er en liten lokal app som skal kjøre på QNAP/Docker i samme nett som Roborock-robotene.

Den gjør tre ting:

1. Logger inn mot Roborock cloud med den delte kontoen.
2. Leser robotene lokalt på LAN der det er mulig.
3. Sender ferdig strukturerte data til Fibaro10 sitt API.

Fibaro10 kjører lokalt på QNAP. Hvis den senere flyttes, endres bare `FIBARO10_API_BASE_URL`.

## Oppsett

Kopier `.env.example` til `.env`:

```bash
cp .env.example .env
```

Viktigste felter:

```env
ROBOROCK_EMAIL=roborock.sun2@gmail.com
FIBARO10_API_BASE_URL=http://fibaro10:8110
FIBARO10_API_USERNAME=logger
FIBARO10_API_PASSWORD=passord-fra-fibaro10
ROBOROCK_WATER_INTERLOCK_ENABLED=true
```

Brukeren i Fibaro10 kan være en vanlig bruker. Loggeren bruker headerne `x-access-username` og `x-access-password`.

## Starte med Docker

```bash
docker compose up -d --build
```

Åpne:

```text
http://192.168.20.218:8095
```

Første gang:

1. Trykk `Send kode`.
2. Skriv inn e-postkoden fra Roborock.
3. Trykk `Lagre login`.
4. Trykk `Synk nå`.

## Legge til en robot senere

1. Legg roboten til i Roborock-appen og sett tidssonen til `Europe/Oslo`.
2. Koble den til IOT-nettet `192.168.2.x`.
3. Del roboten med `roborock.sun2@gmail.com`.
4. Åpne loggerens webflate og trykk `Finn nye roboter`.
5. Kontroller at navn, modell og lokal IP vises før du eventuelt henter kart.

`Finn nye roboter` bruker `/sync-now?refresh=true` og hopper over hurtigbufferen for Roborock-hjemmet. Fibaro10 oppretter roboten automatisk ved første mottatte batch.

## Hva sendes til Fibaro10

Loggeren sender batcher til:

```text
/api/renhold/ingest
```

Batchen kan inneholde:

- robotmetadata
- cloud-status
- lokal LAN-status
- nettverksdata
- forbruksdeler
- rengjøringshistorikk
- planlagte jobber
- scener
- kartdata med PNG base64 ved kart-sync
- probe-resultater og feil

Hvis Fibaro10 er nede, legges batchen i lokal kø i `/data/pending_batches.jsonl` og forsøkes sendt igjen senere.
En ugyldig kølinje flyttes til `/data/pending_batches.invalid.jsonl`, slik at den kan undersøkes uten å blokkere
resten av køen.

Loggeren bruker kjente lokale IP-adresser mellom synkroniseringene. Hele IOT-nettet skannes ved cloud-oppfriskning,
når en ny robot mangler adresse eller etter en lokal telemetilfeil. Dette reduserer vanlig nettverksbelastning uten
å hindre automatisk oppdagelse. Med `MAP_SYNC_ON_START=true` hentes kart én gang etter at loggeren starter.

## Kontroll og rengjøringsprofiler

Fibaro10 kan sende en tokenbeskyttet sonekommando til loggeren. Kommandoen må inneholde kartsegment og en
fullstendig rengjøringsprofil med type, sugekraft, vannmengde, vaskemønster og antall runder. Loggeren setter og
verifiserer profilverdiene via lokal LAN-kommunikasjon før `app_segment_clean` startes. Forsøket lagres i den lokale
append-only kontrolloggen med innstillinger og status før og etter.

Kun deterministiske innstillinger som støttes av robotmodellene i anlegget godtas. `Custom` og `Smart` avvises fordi
de krever flere modellavhengige parametere enn selve moduskoden.

## Automatisk vannsperre

Loggeren kontrollerer `clear_water_status`, som er Roborocks status for rentvannstanken i dokken, ved hver
telemetriinnsamling (normalt hvert 60. sekund). Sperren er kontinuerlig og venter ikke til et bestemt klokkeslett:

1. Når rentvann i dokken går til tom, settes alle aktive vaskeplaner for den roboten på pause.
2. Rene støvsugeplaner, identifisert med `water_box_mode=200`, berøres ikke.
3. Planene sperren faktisk satte på pause lagres i `/data/state.json`.
4. Når rentvann igjen rapporteres OK, aktiveres bare disse planene på nytt.
5. En plan som er slettet mens sperren er aktiv blir ikke opprettet på nytt.
6. Hver endring verifiseres ved å lese planstatus tilbake fra roboten og logges i `/data/control_commands.jsonl`.

Sperren kan slås av med `ROBOROCK_WATER_INTERLOCK_ENABLED=false`, men standard og anbefalt verdi er `true`.
Fibaro10 mottar status, sperretid, eventuelle feil og hvilke vaskeplaner som er satt på pause sammen med hvert
telemetrisample.

Følgende vannsignaler holdes adskilt i data og grensesnitt:

- `clear_water_status`: rentvann i dokken, og eneste signal som styrer den automatiske sperren.
- `dirty_water_status`: skittentvann i dokken.
- `clean_fluid_status`: rengjøringsmiddel i dokken.
- `water_shortage_status`: roboten registrerer vannmangel under drift; dette er ikke en nivåmåler.
- `water_box_status`: vanntanken i roboten er montert.
- `water_box_carriage_status`: moppen er montert.
- `water_box_filter_status`: vannfilterstatus.
- `dock_error_status`: samlet dokkfeil; vises som diagnose, men styrer ikke sperren.
