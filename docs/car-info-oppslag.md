# Car.info-oppslag for svenske biler

`car_info_lookup` er en separat QNAP-app som beriker parkering/kjoretoy med svenske biler som SVV ikke finner.

## Flyt

1. Fibaro10 importerer parkeringer og oppretter rader i `kjoretoy`.
2. SVV-sync forsoker aa hente norske kjoretoydata.
3. Hvis SVV er forsokt, men `kjoretoy_nokkeldata` fortsatt mangler, kan bilen bli kandidat for car.info.
4. Kandidaten maa matche svensk standardformat:
   - `ABC123`
   - `ABC12D`, der siste tegn ikke er `O`
5. `car_info_lookup` henter en bil per intervall fra Fibaro10.
6. Ved bekreftet svensk side hos car.info poster appen strukturert resultat tilbake.
7. Fibaro10 setter `omrade = Sverige` hvis feltet er blankt eller `ikke funnet`.

## Hvorfor egen app

Car.info har lav rate-limit for gratis/personlig bruk. Derfor skal dette kjore sakte, med global backoff ved `coffee break`/429, og ikke som en bulk-crawler inne i hovedappen.

## Standardintervall

QNAP-compose setter standard til en kandidat hvert 45. minutt og global pause i 240 minutter ved rate-limit.

## Intern tilgang

Sett `CAR_INFO_APP_TOKEN` i QNAP `.env`. Fibaro10 godtar denne tokenen kun paa car.info-kandidatlisten og car.info-resultatpostingen. Da trenger ikke bakgrunnsappen masterbruker eller plaintext-passord.

## Kontroll

- Appstatus: `http://192.168.20.218:8126/health`
- Manuell Fibaro10-trigger: `POST /api/actions/parkering/car-info-sync?limit=1`
- Svensk skiltfilter: `GET /api/svensk-skilt/{plate}`

## Lagrede felt

Fibaro10 lagrer:

- `car_info_fetched_at`
- `car_info_status`
- `car_info_error`
- `car_info_url`
- `car_info_data`

`car_info_data` inneholder bekreftelse paa svensk bil, tittel, beskrivelse, relevante normaliserte felter, alle leste faktalinjer og et kort raatekstutdrag. Normaliserte felter inkluderer blant annet `first_registered`, `vehicle_type`, `color`, `fuel`, `transmission`, `power`, `engine`, `mileage`, `inspection_valid_to`, `classification`, `generation`, `drivetrain`, `fuel_consumption_combined`, `co2_combined`, `tank_volume` og `seats` naar siden viser dem.
