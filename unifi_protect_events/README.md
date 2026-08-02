# Protect Ledger – UniFi Protect hendelser

Tjenesten kobler direkte til den offisielle lokale UniFi Protect-integrasjonen,
lytter på WebSocket-endepunktet og lagrer én oppdatert rad per Protect-hendelse i
PostgreSQL. Råmeldingen beholdes i `raw` som JSONB. For hver unik hendelse som
passerer lagringsfilteret hentes også ett JPEG-stillbilde fra kameraet.
Hele dataflyten går lokalt mellom UniFi-gatewayen, QNAP og Fibaro10; tjenesten
bruker ikke UniFi Cloud eller eksterne analyseleverandører.

Tjenesten har sitt eget responsive administrasjonsgrensesnitt på port `8130` og
er ikke en del av Fibaro10-grensesnittet. Der kan du:

- velge kameraer, hovedhendelser og AI-/lyddeteksjoner som skal lagres
- se alle muligheter kameraene rapporterer, også før de er observert
- søke og filtrere historikken og åpne stillbildet og rådata for en hendelse
- velge oppbevaringstid, bildekvalitet og maksimal bildestørrelse
- følge PostgreSQL- og bildelagring og se et revisjonsspor over innstillinger
- ta imot alle kjente og ukjente skilt-/ansiktsregistreringer fra Alarm Manager
- bruke et versjonert, tokenbeskyttet API og SSE-strøm fra Fibaro10
- se gjeldende PL-build og en søkbar, egen buildlogg

## Forutsetninger

- QNAP/serveren må kunne nå Protect-konsollens lokale IP eller VPN-adresse på port 443.
- Opprett en lokal nøkkel i UniFi under **Settings > Control Plane > Integrations**.
- WebSocket kan ikke brukes gjennom UniFi Cloud Connector. URL-en må peke direkte på konsollen.

## Konfigurasjon

Legg verdiene i den ignorerte `.env`-filen på QNAP:

```dotenv
UNIFI_PROTECT_NVR_URL=https://192.168.1.1
UNIFI_PROTECT_API_KEY=REPLACE_WITH_LOCAL_API_KEY
UNIFI_PROTECT_VERIFY_SSL=false
UNIFI_PROTECT_CONSOLE_KEY=lilletorget

# Tom verdi betyr alle kameraer/hendelsestyper.
UNIFI_PROTECT_CAMERA_IDS=
UNIFI_PROTECT_EVENT_TYPES=
UNIFI_PROTECT_HOST_SNAPSHOT_DIR=/share/CACHEDEV3_DATA/fibaro10_archive/unifi_protect/snapshots
UNIFI_PROTECT_READ_API_TOKEN=REPLACE_WITH_LONG_RANDOM_TOKEN
UNIFI_PROTECT_WEBHOOK_TOKEN=REPLACE_WITH_ANOTHER_LONG_RANDOM_TOKEN
UNIFI_PROTECT_WEBHOOK_ALLOWED_IPS=192.168.1.1
UNIFI_PROTECT_SNAPSHOT_WORKERS=2
UNIFI_PROTECT_SNAPSHOT_QUEUE_SIZE=1000
UNIFI_PROTECT_RECOGNITION_SNAPSHOT_WORKERS=2
PROTECT_LEDGER_VERSION=1
PROTECT_LEDGER_BUILD=16
```

`DATABASE_URL` gjenbrukes fra Fibaro10. Det selvsignerte `unifi.local`-sertifikatet
krever `UNIFI_PROTECT_VERIFY_SSL=false` inntil konsollen eventuelt får et sertifikat
som QNAP stoler på.

## Tilkoblingstest

Fra repoet:

```bash
python scripts/probe_unifi_protect.py --env-file .env.unifi.local
```

Testen leser kameralisten og fullfører en WebSocket-handshake. Nøkkelen skrives ikke ut.

## Start på QNAP

```bash
python scripts/run-migrations.py
docker compose -f docker-compose.qnap.yml --profile unifi-protect up -d --build unifi_protect_events
```

Grensesnittet finnes på `http://192.168.20.218:8130/`. Status finnes på
`http://192.168.20.218:8130/health`. `/ready` svarer 200 først når
både databasen og WebSocket-forbindelsen er oppe.

Gjeldende build vises nederst i hovedmenyen og på
`http://192.168.20.218:8130/builds`. Buildnummeret finnes også i `/health`,
`GET /api/v1/build` og `GET /api/v1/builds`. PL bruker egne miljøvariabler, slik
at buildnummeret ikke blandes med Fibaro10 eller OwnTracks.

## Tabeller

- `unifi_protect_cameras`: siste kjente kameraegenskaper og navn.
- `unifi_protect_events`: hendelser deduplisert på konsoll + Protect event-ID.
- `unifi_protect_event_type_config`: katalog og lagringsvalg for hovedtyper.
- `unifi_protect_detection_type_config`: alle rapporterte AI-/lydmuligheter.
- `unifi_protect_settings`: global lagrings-, bilde- og oppbevaringspolicy.
- `unifi_protect_config_history`: revisjonsspor for endringer i grensesnittet.
- `unifi_protect_alarm_webhooks`: dedupliserte, komplette Alarm Manager-kall.
- `unifi_protect_recognitions`: normaliserte skilt, ansikter og personer av interesse.

En `add`-melding oppretter raden. Senere `update`-meldinger oppdaterer samme rad,
fyller blant annet sluttid og øker `update_count`. Det gjør gjenoppkobling trygg uten
å opprette dubletter.

Stillbildene ligger som filer utenfor databasen under
`UNIFI_PROTECT_HOST_SNAPSHOT_DIR`. Nye gjenkjenninger får et eget høyoppløst bilde
fra kamera-ID-en i webhooken. Hentingen tidsstyres mot OCR-tidspunktet, og bildets
kamera, tidspunkt og tidsavvik lagres på gjenkjenningen. Generelle hendelsesbilder
brukes ikke som OCR-dokumentasjon. Separate, avgrensede arbeidskøer gjør at trege
kameraer ikke blokkerer webhook- eller WebSocket-innlesingen.

## Lokalt API for Fibaro10

Alle `/api/v1/*`-lesekall krever `Authorization: Bearer <UNIFI_PROTECT_READ_API_TOKEN>`
eller samme verdi i `X-API-Key`. Viktige endepunkter:

- `GET /api/v1/status`, `/build`, `/builds`, `/cameras`, `/capabilities` og `/stats`
- `GET /api/v1/events` og `/recognitions` med stabile markører i `next_cursor`
- `GET /api/v1/recognitions/{id}` med rå trigger/webhook og hendelseskobling
- `GET /api/v1/recognitions/{id}/snapshot` med gjenkjenningens tidsstyrte kamerabilde
- `GET /api/v1/license-plates/daily?from=...&to=...` med ferdig normalisering,
  registervalidering og OCR-variantmerking
- `GET /api/v1/license-plates/{plate}` med cachet valideringsspor per kilde
- `GET /api/v1/events/{id}/snapshot`
- `GET /api/v1/stream` som sender SSE-hendelsene `event` og `recognition`
- `POST /api/v1/webhooks/unifi-alarm` med `UNIFI_PROTECT_WEBHOOK_TOKEN`

Fibaro10 tilbyr i tillegg autentiserte proxy-endepunkter under
`/api/unifi-protect/*`. Det gjør at Fibaro10-sider kan bruke de samme dataene uten
å eksponere tjenestetokenet til nettleseren. Komplett kontrakt finnes på `/docs`.

## Alle bilskilt og kjente personer

WebSocket-strømmen forteller at et skilt eller ansikt er sett, men inneholder ikke
selve skiltverdien eller personnavnet. Opprett derfor lokale Alarm Manager-regler
for både **License plate · Known** og **License plate · Unknown** med HTTP POST til
`http://192.168.20.218:8130/api/v1/webhooks/unifi-alarm`. Gjenta for kjente og
ukjente ansikter ved behov. Gatewayens lokale IP godkjennes med
`UNIFI_PROTECT_WEBHOOK_ALLOWED_IPS`, siden Protects POST-oppsett ikke tilbyr
egendefinerte headere. Andre avsendere bruker webhook-tokenet som Bearer-token,
`X-API-Key` eller `?token=...`.

Ledger lagrer hele det originale JSON-kallet, normaliserer verdien og prøver å koble
registreringen til nærmeste WebSocket-hendelse og stillbilde. Hvis en bestemt
Protect-versjon ikke sender selve verdien, beholdes registreringen og rådataene,
men appen markerer verdien som ikke sendt.

Integrasjonssiden viser fire live-kontroller for kjent/ukjent skilt og
kjent/ukjent ansikt. En kontroll blir grønn først etter at den aktuelle varianten
er mottatt. Protects offentlige API har ikke et støttet endepunkt for å opprette
Alarm Manager-regler; de fire reglene opprettes derfor én gang i Protects eget
grensesnitt.

## Validering av registreringsnummer

Protect Ledger eier hele kvalitetsløpet før data presenteres i Fibaro10:

1. normaliser verdien fra UniFi uten å slette råobservasjonen
2. kontroller lokal `kjoretoy`-/`parkering`-historikk i PostgreSQL
3. kontroller Statens vegvesen når lokal historikk ikke gir treff
4. kontroller Biluppgifter.se for svensk standardformat
5. kontroller Tjekbil.dk for dansk standardformat
6. marker `not_found` / `likely_misread` bare når alle relevante oppslag er
   fullført uten treff

Midlertidig feil, timeout eller rate-limit gir `error` med nytt kontrolltidspunkt,
aldri «sannsynlig feillesing». Resultatene caches i
`unifi_protect_plate_validations`, mens en bakgrunnskø prioriterer nye deteksjoner.
Råhendelser og bilder forblir lokale; kun normalisert registreringsnummer sendes
til aktiverte registerkilder.

Den lokale Biler-siden finnes på `http://192.168.20.218:8130/plates`.

## Lagringskapasitet

JPEG-størrelsen varierer med kamera, motiv og valgt kvalitet. Et enkelt overslag er:

```text
hendelser per dag × gjennomsnittlig JPEG-størrelse × oppbevaringsdager
```

Eksempel: 1 000 hendelser/dag × 500 KB × 365 dager er omtrent 174 GB. Appens
lagringsside viser faktisk bildestørrelse, antall stillbilder og eventuelle feil.
