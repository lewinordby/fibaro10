# Roborock_logger og Renhold

Oppdatert 15.08.2026.

`Roborock_logger` er den lokale innlesingsappen for robotstøvsugere. Den kjører på QNAP/Docker i samme nett som robotene og sender ferdig strukturerte data til Fibaro10.

## Hvorfor lokal logger

Roborock-data kommer fra to steder:

- Roborock cloud for konto, robotliste, metadata, planer og kartkanal
- lokal LAN-tilkobling for raskere status og historikk fra robotene

Den lokale loggeren gjør at hovedappen slipper å snakke direkte med Roborock ved sidevisning. Fibaro10 viser bare data som allerede ligger i egen database.

## API i Fibaro10

Fibaro10 tar imot:

```text
POST /api/renhold/ingest
POST /api/renhold/telemetry/ingest
```

Og viser:

```text
GET /renhold/oversikt
GET /renhold/robot/{duid}
GET /renhold/json
```

Data lagres i egne tabeller for:

- roboter
- statusmålinger
- vaskjobber
- planlagte jobber
- forbruksdeler
- kart
- probe-resultater
- sync-kjøringer
- telemetrimålinger
- telemetrihendelser
- historiske øyeblikksbilder av renholdsplanen

## QNAP / Docker

Mappen ligger i repoet:

```text
roborock_logger
```

Typisk drift:

```bash
cd roborock_logger
docker compose up -d --build
```

Webflate:

```text
http://192.168.20.218:8095
```

Hvis Fibaro10 senere flyttes til en annen host eller port, endres bare API-base i loggerens miljø:

```env
FIBARO10_API_BASE_URL=http://fibaro10:8110
```

til for eksempel:

```env
FIBARO10_API_BASE_URL=http://192.168.20.x:8000
```

## Drift og kontroll

Normal sync skjer periodisk fra loggeren. Status for siste vellykkede Roborock-sync vises i:

```text
Admin -> Datakilder -> Roborock logger
```

I hovedappen vises robotene under:

```text
Renhold -> Oversikt
```

Derfra kan man åpne hver robot og se status, teknisk identitet, siste jobber, planer, kart og rå statuspakker.

Oversikten er en operativ kontrollflate. Øverst vises samlet robotpark, aktive jobber, dagens rengjøring og antall
roboter som krever handling. Reelle avvik listes deretter med årsak, neste plan og eventuell vannsperre. De
kompakte robotkortene viser bare tilstand nå, batteri, dagens jobber og neste plan. Normale beholderverdier,
gårsdagens historikk, forbruksdeler og øvrig telemetri ligger på robotsiden eller i Nattrapporten, slik at
oversikten ikke skjuler det som faktisk må følges opp.

I robotdetaljen vises også komplett telemetri. Dynamisk status leses hvert minutt. En bredere kontroll av
modellspesifikke lesekall kjøres hvert 15. minutt. Se `docs/roborock-telemetri.md` for hele feltkatalogen.

## Legge til en ny robot

1. Legg roboten til på vanlig måte i Roborock-appen, gi den et tydelig navn og velg tidssonen `Europe/Oslo`.
2. Koble roboten til IOT-nettet som bruker adresser i `192.168.2.x`. Lokal status og historikk krever at QNAP-en kan nå roboten på dette nettet.
3. Del roboten med Roborock-kontoen `roborock.sun2@gmail.com`. Loggeren leser både kontoens egne og delte roboter.
4. Åpne `http://192.168.20.218:8095` og trykk `Finn nye roboter`. Handlingen henter Roborock-hjemmet på nytt uten én-times hurtigbuffer.
5. Kontroller at roboten vises på logger-siden med navn, modell og lokal IP.
6. Åpne `Bygg og drift -> Renhold -> Roboter` i Lilletorget. Fibaro10 oppretter roboten automatisk ved første mottatte synk; det skal ikke legges inn noen databasepost manuelt.

Hvis roboten finnes i cloud, men mangler lokal IP, sjekk at den er på IOT-nettet og at `ROBOROCK_SUBNET=192.168.2.` fortsatt er riktig. Bruk `Synk med kart` etter første vellykkede oppdagelse for å hente kartet med en gang.

## Tidssoner

Planene fra Roborock er lokal klokketid og skal for eksempel vises som `23:30`. Historiske vaskjobber kommer som Unix-tid i UTC. Fibaro10 konverterer disse til `Europe/Oslo` ved API-visning, inkludert riktig sommer- og vintertid.

«Neste plan» beregnes fra både lokal klokketid og planens ukedager. En mandagsplan kan derfor ikke bli presentert
som neste jobb på en tirsdag bare fordi klokkeslettet ligger nærmest. Oversikten viser konkret neste forekomst, for
eksempel `I morgen kl. 23:30`, mens robotdetaljen også viser selve gjentakelsesregelen.

## Datakvalitet og belastning

- Minutt-telemetrien er den ferskeste kilden for aktiv/ferdig-status. Femminuttersstatusen brukes som historikk og reserve.
- Oversikten henter siste status, telemetri og forbruksdeler per robot, ikke et felles begrenset radutvalg.
- Dagens og gårsdagens jobber hentes etter lokale døgnskiller i `Europe/Oslo`.
- Fullt søk etter lokale Roborock-adresser gjøres ved ny robot, cloud-oppfriskning eller lokal feil. Kjente friske
  adresser brukes direkte mellom søkene.
- Kart hentes ved oppstart når `MAP_SYNC_ON_START=true`, og ellers ved manuell `Synk med kart`.
- En ugyldig linje i den lokale sendekøen flyttes til `pending_batches.invalid.jsonl`; øvrige batcher fortsetter.
- Etter en vellykket cloud-synk behandles planlisten som et komplett øyeblikksbilde. Planer som ikke lenger
  finnes hos Roborock tas straks ut av aktive beregninger og merkes med slettet tidspunkt i Fibaro10. Ved feil
  i cloud-kallet blir ingen planer slettet. Dersom samme plan-ID senere kommer tilbake, aktiveres raden igjen.

## Soner og rengjøringsprofiler

På detaljsiden til hver robot kan en global sone kobles til robotens lokale kartsegment. Deaktiverte testplaner
kl. `12:01` til `12:59` brukes bare til å lese inn koblingen: `12:01` betyr Sone 1, `12:02` betyr Sone 2 osv.

En sone kan ikke startes uten at en aktiv rengjøringsprofil er valgt. Profilen angir eksplisitt:

- renholdstype: støvsuging, vask eller støvsuging med vask
- sugekraft: stille, balansert, turbo, maks eller maks+
- vannmengde: av, lav, medium eller høy
- vaskemønster: standard, dyp, dyp+ eller hurtig
- én, to eller tre runder

Fibaro10 leveres med vanlig og intensiv profil for hver renholdstype. Masterbrukeren kan opprette egne profiler,
redigere standardprofilene og deaktivere profiler som ikke skal brukes. Før sonen startes sender Roborock_logger
alle profilverdiene lokalt til roboten, leser status tilbake og avviser jobben dersom roboten ikke bekrefter de
bestilte innstillingene. Valgt profil, sone, segment, bruker og bekreftede verdier lagres i kontrollhistorikken.

Roborocks `Custom`- og `Smart`-moduser er foreløpig ikke tilgjengelige i profilbyggeren. Kodene alene er ikke
tilstrekkelige; de trenger ekstra modellavhengige vendorparametere og ville derfor ikke gitt en entydig fast profil.

## Robotstyring og moppevask i dokk

Detaljsiden skiller mellom tre typer handlinger:

- `Renhold nå` starter, pauser, fortsetter eller stopper roboten.
- `Moppevask i dokk` bestemmer hvor grundig og hvor ofte moppene vaskes mens en gulvvask pågår.
- `Diagnostikk og funksjonstest` kontrollerer forbindelsen eller gjør en kort kontrollert start- og stopptest.

Moppeintervallet er ikke en plan for hvor ofte gulvet skal vaskes. `Hvert 10. minutt` betyr at roboten returnerer
til dokken omtrent hvert tiende minutt under aktiv gulvvask for å vaske moppene. Fast intervall slår av Roborocks
automatiske intervallvalg. Støttede valg er 10, 15, 20 og 25 minutter, med styrke Lett, Balansert, Dyp eller Ekstra dyp.

Fibaro10 sender begge innstillingene lokalt til roboten, leser dem tilbake og godtar ikke endringen før roboten
bekrefter verdiene. De bekreftede verdiene lagres straks som telemetri og brukes av robotsiden og historiske
nattrapporter. Innstillingene kan ikke endres mens roboten rengjør. Roboter uten vaskefunksjon i dokken viser bare
at funksjonen ikke støttes.

## Inngangsstyrt støvsuging for 1.etg B

Robotsiden for `1.etg B` har en egen automatikk som kan starte én felles støvsugingsjobb i én eller flere valgte
soner. Standardoppsettet er deaktivert, med 10 åpninger av inngangsdøren, minst 60 minutter mellom automatiske
starter og Sone 1 valgt. Automatikken kan først aktiveres når alle valgte soner er koblet til gyldige kartsegmenter.

Telleren bruker bare reelle tilstandsendringer for inngangsdørens HC3-enhet `541`. Følgende må være oppfylt:

- døråpningene har skjedd samme dag og etter dagens åpningstid startet
- antall åpninger har nådd den konfigurerte terskelen
- inngangsdøren er lukket
- første automatiske start er tidligst ett minimumsintervall etter dagens åpningstid
- konfigurert minimumstid har gått siden forrige automatiske støvsuging startet
- kontrollen skjer før dagens stengetid
- minst én valgt sone, en aktiv ren støvsugingsprofil og Roborock-styring er tilgjengelig

Åpningstiden hentes fra `Ventilasjon -> Innstillinger` (`open_from` og `close_at`). Ved hver ny driftsdag starter
både åpningstelleren og tidslåsen på nytt ved `open_from`. Med dagens åpning kl. 07:00 og minimumsintervall 60
minutter kan første jobb dermed aldri starte før kl. 08:00. Nattens hendelser og forrige dags siste robotstart tas ikke med.
Når åpningsterskelen nås før minimumsintervallet er utløpt, beholdes telleren og jobben starter automatisk så snart
minimumstiden er nådd; det kreves ingen ny døråpning. Telleren nullstilles etter en vellykket start eller med
`Nullstill teller`, men ikke når oppsettet lagres. Mellom senere starter samme driftsdag måles minimumsintervallet
fra forrige vellykkede start og påvirkes ikke av en manuell nullstilling av telleren. Ved ny driftsdag brukes dagens
åpningstid som nytt tidsanker.
Hvis roboten avviser en start,
beholdes telleren og Fibaro10 venter fem minutter før nytt forsøk. Alle forsøk lagres i den samme kontrollhistorikken
som manuelle robotkommandoer, med bruker `door_automation`.

## Plan mot utførelse i nattrapporten

Ved hver faktisk endring i Roborock-planen lagrer Fibaro10 et tidsstemplet øyeblikksbilde. Nattrapporten bruker
dermed planen som var gjeldende på det aktuelle tidspunktet. En plan som legges til, pauses eller fjernes midt
på natten påvirker bare starter etter endringen. Eldre netter fra før planhistorikken ble etablert blir ikke
etterberegnet mot dagens plan; rapporten viser i stedet tydelig at plangrunnlaget mangler.

Nattrapporten sammenholder bare planlagte Roborock-starter (`start_type=3`) med de lagrede planene. Manuelle,
dørstyrte og andre starter vises fortsatt i tidslinjen og tabellen som `Øvrig jobb`, men de inngår ikke i
vurderingen av om nattplanen var ferdig før åpning. Planlagt start og faktisk start kobles innenfor et
kontrollvindu fra 45 minutter før til 90 minutter etter planen. Oppstart mer enn 10 minutter fra planen merkes
som forsinket, og en plan som fortsatt ikke har en jobb 20 minutter etter start merkes som uteblitt.

For en avsluttet natt viser hver robot først de faktiske jobbene med tidspunkt, type, resultat, batteri ved start
og slutt, antall registrerte moppevasker og vannstatus. Vannstatusen er `OK` når en vaskejobb har telemetri uten
rapportert vannmangel, `Vannmangel` med klokkeslett når roboten meldte mangel, og `Ikke relevant` for ren
støvsuging. Endringer i rentvann, skittentvann, vann i robot, rengjøringsmiddel og vannfilter listes med nøyaktig
tidspunkt under den aktuelle roboten. Historisk plan og tekniske robotinnstillinger kan foldes ut ved behov.

Nattvinduet er kl. 22:00-08:00. Den røde bakgrunnen viser åpningstid med sikkerhetsmargin til kl. 23:45 på
kvelden og fra kl. 06:45 om morgenen. Bare jobbene i den lagrede planen vurderes mot fristen kl. 06:45.

Renhold-oversikten har i tillegg en døgnlinje for inneværende dag fra kl. 00:00 til 24:00. Den bruker samme
planmarkører og jobbstatus som nattrapporten, men tar også med ikke-planlagte jobber, inngangsstyrt rengjøring
og andre jobber som utløses i åpningstiden. En blå loddrett linje viser tidspunktet dataene sist ble bygget for.
Pågående rengjøring vises direkte fra den aktive robotsyklusen selv før den ferdige jobben er tilgjengelig i
Roborocks jobbhistorikk.

## Feilsøking

Hvis Renhold viser gamle data:

1. Sjekk Admin -> Datakilder.
2. Åpne Roborock_logger på QNAP og se om den har feilmelding.
3. Kontroller at robotene er online i Roborock.
4. Kontroller at logger-brukeren i Fibaro10 fortsatt virker.
5. Sjekk lokal kø hvis Fibaro10 har vært nede:

```text
/data/pending_batches.jsonl
```

Batcher i kø sendes på nytt ved neste vellykkede sync.

En eventuell isolert, ugyldig kølinje beholdes for feilsøking i:

```text
/data/pending_batches.invalid.jsonl
```
