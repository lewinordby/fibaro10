# Dreame-logger og Aqua10

## Formål

`dreame_logger` er et eget undersystem for Dreame-robotene. Første robot er klargjort med navnet `Aqua10`. Tjenesten kjører separat fra `roborock_logger`, slik at innlogging, cloud-feil, oppgraderinger og restart hos én leverandør ikke stopper den andre.

Renhold-grensesnittet er felles. Fibaro10 lagrer robotene i samme domenemodell, men beholder `provider`, leverandør-ID og leverandørtilpassede kontroller. Eksisterende Roborock-ID-er endres ikke; Dreame-ID-er får prefikset `dreame:`.

## Dataflyt

```text
Dreamehome -> dreame_logger:8094 -> /api/renhold/ingest -> PostgreSQL -> Renhold
                                      /api/renhold/telemetry/ingest
```

Tjenesten henter og normaliserer:

- robotnavn, modell, serienummer, cloud-status og batteri
- tilstand, feil, lading, dokk og pågående rengjøring
- rentvann, skittentvann, støvpose og dokkstatus der modellen rapporterer dette
- jobbhistorikk med start, varighet, areal og resultat
- aktive planer som Dreamehome gjør tilgjengelige
- hovedbørste, sidebørste, filter, sensor, mopp og rengjøringsmiddel i prosent der det finnes
- relevante innstillinger som sugekraft, vannmengde, rengjøringsmodus og moppevask

## Vann- og beholdermapping

Fibaro10 viser leverandøruavhengige navn, men beholder Dreames originale kode i telemetrien:

| Dreame-signal | Visning i Fibaro10 | Betydning |
|---|---|---|
| `CLEAN_WATER_TANK_STATUS` | Rentvann i dokk | OK, lite, tomt, ikke montert eller kontrollerer |
| `LOW_WATER_WARNING` | Vannvarsel | Skiller lite vann, tomt, manglende tank og utilstrekkelig vann til vask |
| `DIRTY_WATER_TANK_STATUS` | Skittentvann i dokk | OK eller full/ikke montert |
| `DETERGENT_STATUS` | Rengjøringsmiddel | OK, lite eller deaktivert |
| `WATER_TANK` | Vanntank i robot | Om robotens tank er montert; ikke nivå i liter eller prosent |
| `WATER_VOLUME` | Vannmengde ved vask | Valgt dosering ved vask, ikke innholdet i en tank |

Fibaro10 mottar ikke et nøyaktig vann- eller såpenivå i prosent eller liter fra Aqua10. Et varsel
om lite vann markeres for oppfølging, men gjør ikke alene en ferdig jobb mislykket. Varslene tomt,
ikke nok vann til rengjøring og tank ikke montert regnes som blokkerende vannmangel.

## Automatisk vannsperre

`dreame_logger` kontrollerer vannstatus ved hver femminutters synkronisering. Når Aqua10 rapporterer
lite, tomt eller manglende rentvann, deaktiveres alle planene som er aktive i Dreamehome. Tjenesten
lagrer plan-ID, tidspunkt, opprinnelig Dreame-status og tidspunktet planen ble pauset. Endringen regnes
ikke som vellykket før den nye statusen er verifisert.

Når rentvannet igjen rapporteres uttrykkelig `OK`, aktiveres bare planene som vannsperren selv pauset.
Planer som slettes mens sperren er aktiv, blir ikke opprettet på nytt. Ukjent eller utdatert vannstatus
fører aldri til automatisk gjenopptak. Sperren kan nøddeaktiveres med
`DREAME_WATER_INTERLOCK_ENABLED=false`, men er aktiv som standard.

Kartbehandling er bevisst deaktivert i første fase. Det holder minnebruken lav og reduserer risikoen i den løpende status- og historikkinnlesingen. Kart kan vurderes separat etter at Aqua10 er aktiv og stabil.

## Første oppsett

1. Legg Aqua10 til i Dreamehome og kontroller at roboten er online.
2. Gi roboten navnet `Aqua10`.
3. Legg Dreamehome-kontoen i `dreame_logger/.env` på QNAP:

```env
DREAME_USERNAME=
DREAME_PASSWORD=
DREAME_COUNTRY=eu
DREAME_ACCOUNT_TYPE=dreame
DREAME_WATER_INTERLOCK_ENABLED=true
```

4. Deploy normalt med `scripts/deploy-qnap.ps1` eller bygg tjenesten direkte fra `dreame_logger/docker-compose.qnap.yml`.
5. Åpne `http://192.168.20.218:8094/` og kjør en synkronisering.
6. Kontroller `Admin -> Datakilder -> Dreame logger` og `Renhold -> Oversikt`.

Før kontoopplysningene er lagt inn, kjører tjenesten friskt og rapporterer at Aqua10 er klargjort, men venter på konto. Grensesnittet viser ingen oppdiktede status- eller batteriverdier.

## Styring og sikkerhet

Fibaro10 kan sende `start`, `pause`, `fortsett`, `stopp` og `til dokk` via en separat tilfeldig kontrolltoken. Roborock-spesifikke soner, profiler og moppevaskkommandoer vises ikke for Dreame. Mer avansert Aqua10-styring legges først til etter at kommandoene er observert og verifisert mot den faktiske roboten.

Webflaten er bundet til QNAPs interne adresse. Hemmeligheter ligger bare i runtime-`.env`; de skal ikke inn i Git. Ved manglende kontakt med Fibaro10 legges ferdige batcher i en lokal, varig kø og sendes ved neste vellykkede synk.

## Drift og gjenoppretting

- Web/status: `http://192.168.20.218:8094/`
- Health: `http://192.168.20.218:8094/health`
- Container: `dreame_logger`
- Compose: `dreame_logger/docker-compose.qnap.yml`
- Data: Docker-volum `dreame_logger_dreame_logger_data`
- Datakilde: nummer 24, `dreame_sync`
- Normal synk: hvert 5. minutt
- Varselgrense: 20 minutter

Nattbackupen tar med `dreame_logger/.env` og innholdet i `/data`. Ved restore opprettes volumet, filene legges tilbake og tjenesten startes etter at Fibaro10-nettverket og kjernen er tilgjengelige.

## Teknisk avhengighet

Docker-bygget bruker en fast commit av den MIT-lisensierte `Tasshack/dreame-vacuum`-integrasjonen med Dreamehome- og Aqua10-støtte. Commit er låst i Dockerfile for reproduserbare builds. Et valgfritt analyseendepunkt i upstream-koden erstattes med loopback under bygging, slik at denne tjenesten ikke sender robotidentitet til tredjepartsanalyse.
