# Roborock datakilder

Dette dokumentet oppsummerer hva vi kan hente fra Roborock, fordelt på cloud/REST, cloud kartkanal og lokal LAN-tilkobling. Målet er å bruke dette som grunnlag for en lokal logger som fyller en database løpende, og deretter vise dataene i hovedapplikasjonen.

## Testet robot

- Navn: `1.etg A`
- DUID: `22dp228bUjRzmteABcjU69`
- Produkt: `Roborock Qrevo`
- Modell: `roborock.vacuum.a75`
- Firmware: `02.20.60`
- Lokal IP ved test: `192.168.2.91`
- Protokoll: `1.0`
- Kontoen har roboten som delt enhet.

## Cloud / REST

Cloud/REST er best egnet for metadata og oppsett som ikke trenger sekund-for-sekund-oppdatering.

Vi kan hente:

| Datatype | Hva vi får | Kommentar |
| --- | --- | --- |
| Home-data | home-id, navn, romliste, enheter, mottatte/delte enheter, produkter | Gir også `local_key`, men den skal aldri lagres åpent i app-logg. |
| Enhetsmetadata | navn, DUID, serienummerfelt, firmware, modell, produkt-id, delt status, online-status, tidssone | God grunnstamme for `robots`-tabell. |
| Rå statusfelter | statuskode, batteri, fan power, vannmodus, feilkode, ladestatus osv. | Kommer som numeriske datapunkter i `device_status`. |
| Planlagte jobber | jobb-id, cron, aktiv/deaktiv, repetisjon, segmenter, fan power, mop mode, water mode | Stabilt via REST. |
| Scener/rutiner | id og navn | Foreløpig funnet: `1.etg u solrim` og `Full Cleaning`. |
| Produktliste/skjema | produktkategorier og modellinformasjon | Mest nyttig for kartlegging av modeller. |

Kommando:

```powershell
python scripts\roborock_probe.py cloud-probe --email roborock.sun2@gmail.com
```

## Lokal LAN

Lokal LAN er best egnet for hyppig logging av drift/status, fordi den går direkte mot roboten på port `58867`.

Følgende lesekommandoer svarte på Qrevo-testen:

| Datatype | Kommando | Eksempler på felt |
| --- | --- | --- |
| Nåstatus | `get_status` | state, battery, clean_time, clean_area, error_code, in_cleaning, fan_power, water_box_mode, mop_mode, dock_type, charge_status, last_clean_t, clean_percent |
| Forbruksdeler | `get_consumable` | main_brush_work_time, side_brush_work_time, filter_work_time, sensor_dirty_time, dust_collection_work_times |
| Rengjøringssummering | `get_clean_summary` | total tid, total areal, antall vask, støvtømminger, siste record-id-er |
| Enkeltjobber | `get_clean_record` | start/slutt, varighet, areal, completed/error, start_type, clean_type, finish_reason, avoid_count, wash_count |
| Nettverk | `get_network_info` | SSID, IP, MAC, BSSID, RSSI |
| Lyd | `get_sound_volume` | volum |
| Ikke forstyrr | `get_dnd_timer` | start/slutt, enabled, handlinger for dry/dust/led/resume/volume |
| Barnesikring | `get_child_lock_status` | lock_status |
| LED | `get_led_status` | av/på |
| Støvtømming | `get_dust_collection_mode` | mode |
| Smart vask | `get_smart_wash_params` | smart_wash, wash_interval |
| Moppvaskmodus | `get_wash_towel_mode` | wash_mode |
| Romkobling | `get_room_mapping` | segment-id mot Roborock rom-id |
| Tidssone | `get_timezone` | Europe/Oslo |
| Timere | `get_timer`, `get_server_timer`, `get_timer_summary` | lokale/serverbaserte timer-id-er |
| Serienummer | `get_serial_number` | serial_number |
| Teppemodus | `get_carpet_mode` | enable, terskler og stall_time |
| Suge-/custom mode | `get_custom_mode` | nivåkode |
| Vannmodus | `get_water_box_custom_mode` | water_box_mode, distance_off |
| Kartstatus | `get_map_status` | statuskode |

Følgende ble testet, men støttes ikke av denne roboten eller svarte ikke:

| Kommando | Resultat |
| --- | --- |
| `get_flow_led_status` | unknown method |
| `get_dock_info` | unknown method |
| `get_persist_map` | unknown method |
| `get_clean_record_map` | timeout lokalt og via cloud-kartkanal ved test |

Kommando:

```powershell
python scripts\roborock_probe.py local-read-probe --email roborock.sun2@gmail.com
```

Med rådata:

```powershell
python scripts\roborock_probe.py local-read-probe --email roborock.sun2@gmail.com --include-data
```

## Kart

Kartbilde hentes via Roborock sin cloud-kartkanal:

```powershell
python scripts\roborock_probe.py map-image --email roborock.sun2@gmail.com --output roborock_output\map.png
```

Ved test fikk vi:

- PNG-bilde: `1684 x 2288`
- Rå kartdata: 529 510 bytes
- Ferdig PNG: 46 509 bytes
- 14 rom i kartdata
- Laderposisjon og robotposisjon

Lokale kartforsøk svarte ikke. `get_clean_record_map` finnes som kommando i biblioteket, men ga timeout i våre tester både lokalt og via cloud-kartkanalen. Foreløpig bør vi derfor regne med at vi får aktivt/nåværende kart, ikke historisk kart per rengjøring.

Hvis vi vil ha kart per rengjøring fremover, bør loggeren hente og lagre kartet rett etter at en jobb er fullført.

## Anbefalt lokal database

Første versjon bør være enkel og robust:

| Tabell | Innhold | Oppdatering |
| --- | --- | --- |
| `robots` | DUID, navn, modell, produkt, firmware, delt/egen, tidssone | Ved oppstart og deretter sjelden |
| `robot_status_samples` | tidspunkt, state, battery, error_code, in_cleaning, fan_power, water_box_mode, mop_mode, charge_status, clean_percent, dock_type | Hvert 1-5 minutt |
| `robot_network_samples` | tidspunkt, IP, SSID, RSSI, MAC/BSSID | Hvert 15-60 minutt |
| `robot_consumables` | børster/filter/sensor/støvtømming brukt tid | Daglig eller hver 6. time |
| `robot_clean_jobs` | record-id, start/slutt, varighet, areal, fullført, feil, start_type, clean_type, finish_reason | Polling hvert 5-15 minutt og ved endret historikk |
| `robot_schedules` | schedule-id, cron, aktiv, segmenter, nivåer | Ved oppstart og daglig |
| `robot_routines` | scene-id, navn | Ved oppstart og daglig |
| `robot_maps` | tidspunkt, filnavn/raw-hash, romantall, laderposisjon, robotposisjon | Ved oppstart, etter rengjøring, og når kart endres |
| `robot_probe_results` | kommando, kilde, ok/feil, sist testet | Ved ny robot eller etter firmwareendring |

## Anbefalt loggerflyt

1. Start lokalt på en PC/server i samme nett som robotene.
2. Hent cloud/REST ved oppstart for enhetsliste, `local_key`, planer og rutiner.
3. Bruk lokal LAN for hyppig status og historikk.
4. Hent kart fra cloud etter fullført jobb eller ved manuell refresh.
5. Lagre rå JSON i tillegg til normaliserte felt i starten. Da kan vi forbedre tolkningen senere uten å miste data.
6. Vis summerte data i hovedapplikasjonen, ikke direkte fra Roborock API-et.

## Kilder

- Lokalt installert `python-roborock`-bibliotek i Codex-runtime.
- Roborock API-dokumentasjon for `python-roborock`: https://python-roborock.readthedocs.io/en/latest/api_commands.html
