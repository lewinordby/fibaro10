# Nordisk biloppslag for utenlandske biler

`car_info_lookup` er en separat QNAP-app som beriker parkering/kjoretoy med utenlandske biler som SVV ikke finner. Svenske skilt slas opp hos Biluppgifter.se. Danske skilt slas opp hos Tjekbil. `car_info_lookup`-navnet beholdes som teknisk kompatibilitet.

## Flyt

1. Fibaro10 importerer parkeringer og oppretter rader i `kjoretoy`.
2. SVV-sync forsoker aa hente norske kjoretoydata.
3. Hvis SVV er forsokt og svarer permanent uten treff, kan bilen bli kandidat for nordisk fallback.
4. Svenske kandidater maa matche svensk standardformat: `ABC123` eller `ABC12D`, der siste tegn ikke er `O`.
5. Danske kandidater maa matche dansk standardformat: `DY71543` eller `AA12345`.
6. Naar SVV-jobben faar permanent uten-treff paa et stoettet format, trigger Fibaro10 et direkte oppslag paa akkurat det skiltet.
7. Backlog-jobben tar fortsatt eldre kandidater rolig hvis direkteoppslaget ikke kjoerer, for eksempel ved backoff.
8. Ved bekreftet ekstern kilde poster appen strukturert resultat tilbake.
9. Fibaro10 setter `omrade = Sverige` eller `omrade = Danmark` hvis feltet er blankt eller `ikke funnet`.

## Viktig om danske skilt

Dansk format overlapper norsk format. Derfor brukes Tjekbil bare etter at SVV allerede har gitt permanent uten-treff, og Fibaro10 setter bare Danmark naar Tjekbil bekrefter samme registreringsnummer med kjoretoydata.

## Hvorfor egen app

Eksterne oppslagssider kan ha rate-limit eller Cloudflare. Derfor skal dette kjoere sakte, med global backoff ved sperre/429, og ikke som en bulk-crawler inne i hovedappen.

## Standardintervall

QNAP-oppsettet kjoerer direkteoppslag etter SVV-uten-treff og backlog-modus for eldre kandidater. Direkteoppslag skjer straks hvis appen ikke er i backoff. Backlog prioriterer svensk-format kandidater foran dansk-format kandidater, venter normalt 20 sekunder mellom svenske Biluppgifter-kall og 60 sekunder mellom danske Tjekbil-kall, og fortsetter til koeen er tom eller en kilde svarer med Cloudflare/rate-limit/429. Ved rate-limit lagres statusen i Fibaro10 og appen tar global pause i 240 minutter foer den fortsetter automatisk.

## Intern tilgang

Sett `CAR_INFO_APP_TOKEN` i QNAP `.env`. Fibaro10 godtar denne tokenen kun paa kandidatlisten og resultatpostingen for nordisk biloppslag. Da trenger ikke bakgrunnsappen masterbruker eller plaintext-passord.

## Kontroll

- Appstatus: `http://192.168.20.218:8126/health`
- Manuell Fibaro10-trigger: `POST /api/actions/parkering/car-info-sync?limit=1`
- Direkte intern trigger: `POST http://192.168.20.218:8126/api/run-plate/{plate}`
- Manuell backlog-syklus: `POST http://192.168.20.218:8126/api/run-backlog?max_items=12`
- Svensk skiltfilter: `GET /api/svensk-skilt/{plate}`
- Dansk skiltfilter: `GET /api/dansk-skilt/{plate}`

## Lagrede felt

Fibaro10 lagrer:

- `car_info_fetched_at`
- `car_info_status`
- `car_info_error`
- `car_info_url`
- `car_info_data`

`car_info_data` inneholder provider, landkode, bekreftelse, tittel, beskrivelse, relevante normaliserte felter, alle leste faktalinjer og et kort raatekstutdrag. Normaliserte felter inkluderer blant annet `first_registered`, `latest_owner_change`, `vehicle_type`, `body_type`, `color`, `fuel`, `transmission`, `power`, `engine`, `mileage`, `inspection_valid_to`, `classification`, `drivetrain`, `fuel_consumption_combined`, `range_wltp`, `vin` og `seats` naar kilden viser dem.
