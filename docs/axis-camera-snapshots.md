# Axis camera snapshots

`axis_camera_snapshots` er en liten tilleggsapp som henter JPEG-bilder fra et Axis-kamera og lagrer dem på disk.

## QNAP

Appen kjører som egen Docker-container sammen med Fibaro10:

- Container: `axis_camera_snapshots`
- Lokal webflate: `http://192.168.20.218:8125`
- Snapshot-mappe på QNAP: `/share/CACHEDEV1_DATA/Public/containerdata/fibaro10/axis_camera_snapshots/snapshots`
- Config/state: `/share/CACHEDEV1_DATA/Public/containerdata/fibaro10/axis_camera_snapshots/data`

## Miljøvariabler

Legg dette i QNAP `.env` eller endre verdiene i appens webflate:

```env
AXIS_SNAPSHOT_ENABLED=true
AXIS_CAMERA_IP=192.168.101.65
AXIS_USERNAME=root
AXIS_PASSWORD=sett-passord-her
AXIS_INTERVAL_SECONDS=5
AXIS_CAPTURE_START_TIME=06:45
AXIS_CAPTURE_END_TIME=23:00
AXIS_RETENTION_DAYS=7
AXIS_AUTH_MODE=digest
```

Hvis `AXIS_SNAPSHOT_URL` ikke settes, bygges den fra `AXIS_CAMERA_IP`:

```text
http://<ip>/axis-cgi/jpg/image.cgi
```

`AXIS_AUTH_MODE` kan være `auto`, `basic` eller `digest`. Testkameraet svarer med Digest-auth, så `digest` gir renest logg.

Automatisk lagring kjører bare i lagringsvinduet `AXIS_CAPTURE_START_TIME` til `AXIS_CAPTURE_END_TIME`.
Starttidspunktet bør ligge litt før åpningstid fordi SUN2-bildeserien henter bilder før selve solingstiden. Med åpning rundt 07:00 gir `06:45` nok margin for første kunde.
Manuell `Hent bilde nå` i webflaten kan fortsatt brukes til test utenfor vinduet.

## Soltimebilder

Snapshot-mappen brukes som korttidsbuffer. Bilder som skal høre til en SUN2-soltime kopieres inn i Fibaro10-databasen som varige vedlegg i `sun2_tanning_session_images`.

Kobling kjøres fra `Soling -> Enkeltimer` med knappen `Koble bilder`, eller via API:

```text
POST /api/actions/soling/link-snapshot-images?days=7&tolerance_seconds=8
```

For hver soltime matches fem bilder nær beregnet SUN2-bildetid. SUN2 Owner leverer vanligvis `Tidspunkt` med minuttpresisjon, for eksempel `17:46`, ikke `17:46:32`. Fibaro10 tolker derfor minuttpresise rader som sekund `30`.

```text
SUN2_AXIS_SNAPSHOT_MINUTE_ASSUMED_SECOND=30
SUN2_AXIS_SNAPSHOT_OFFSET_SECONDS=15
```

Bildeserien bruker offset `-25`, `-20`, `-15`, `-10` og `-5` sekunder fra beregnet start. `-15` er hovedbildet som vises i listen. Eksempel: `17:46` tolkes som `17:46:30` og gir lagrede bilder rundt `17:46:05`, `17:46:10`, `17:46:15`, `17:46:20` og `17:46:25`. Hvis SUN2 en gang leverer sekunder, brukes faktisk sekundverdi.

Eksisterende koblinger kan rekobles med:

```text
POST /api/actions/soling/link-snapshot-images?days=7&tolerance_seconds=8&replace=true
```

Manuelt bildebytte gjøres fra `Soling -> Enkeltimer`. Åpne en soltime for å se de fem lagrede bildene direkte på posten. `Forrige` og `Neste` blar bare i denne fem-bildersserien. `Sett som hovedbilde` markerer valgt lagret bilde som hovedbildet uten å endre bildeserien. `Bildearkiv` åpner hele Axis-arkivet rundt valgt bilde; bla eldre/nyere og trykk `Bruk dette bildet` for å hente inn et annet arkivbilde som hovedbilde. Frontend bruker tidsbaserte snapshot-ID-er, ikke filstier:

```text
GET  /api/soling/enkeltimer/{session_id}/image-browser
GET  /api/soling/axis-snapshots/{snapshot_id}/image
POST /api/soling/enkeltimer/{session_id}/image?snapshot_id=YYYYMMDDHHMMSS
POST /api/soling/enkeltimer/{session_id}/bilder/{image_id}/primary
```

`POST` krever master- eller innstillingstilgang, fordi soltimepostens bildevalg endres i databasen.

Når et bilde er koblet til en soltime, er det uavhengig av 7-dagers retention i snapshot-bufferen.

## Drift

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy-qnap.ps1
```

Health:

```text
http://192.168.20.218:8125/health
```

Siste lagrede bilde vises på forsiden og kan hentes direkte her:

```text
http://192.168.20.218:8125/latest.jpg
```

Manuell test:

```text
http://192.168.20.218:8125/capture-now
```
