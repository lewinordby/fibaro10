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
AXIS_INTERVAL_SECONDS=10
AXIS_RETENTION_DAYS=7
AXIS_AUTH_MODE=digest
```

Hvis `AXIS_SNAPSHOT_URL` ikke settes, bygges den fra `AXIS_CAMERA_IP`:

```text
http://<ip>/axis-cgi/jpg/image.cgi
```

`AXIS_AUTH_MODE` kan være `auto`, `basic` eller `digest`. Testkameraet svarer med Digest-auth, så `digest` gir renest logg.

## Soltimebilder

Snapshot-mappen brukes som korttidsbuffer. Bilder som skal høre til en SUN2-soltime kopieres inn i Fibaro10-databasen som varige vedlegg i `sun2_tanning_session_images`.

Kobling kjøres fra `Soling -> Enkeltimer` med knappen `Koble bilder`, eller via API:

```text
POST /api/actions/soling/link-snapshot-images?days=7&tolerance_seconds=15
```

For hver soltime matches bildet nærmest `started_at - 10 sekunder`. Når et bilde er koblet til en soltime, er det uavhengig av 7-dagers retention i snapshot-bufferen.

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
