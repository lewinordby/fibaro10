# Roborock datakilder

Oppdatert 10.07.2026.

Dette dokumentet beskriver hvilke data som kan hentes fra Roborock, og hvordan de bør brukes i Lilletorget drift.

## Prinsipp

Roborock-data skal hentes av lokal logger og lagres i Fibaro10-databasen. Brukergrensesnittet skal ikke hente direkte fra Roborock.

```text
Roborock cloud / lokal LAN
  -> Roborock_logger på QNAP
  -> POST /api/renhold/ingest
  -> Fibaro10 database
  -> Renhold-sidene i appen
```

## Testede roboter

| Navn | Produkt | Modell | Cloud | Lokal LAN | Kart |
| --- | --- | --- | --- | --- | --- |
| 1.etg A | Roborock Qrevo | `roborock.vacuum.a75` | OK | OK | OK |
| 1.etg B | S8 | `roborock.vacuum.a51` | OK | OK | OK |

Kontoen har robotene som delte enheter.

## Cloud / REST

Cloud/REST er best egnet for metadata og oppsett.

| Datatype | Felt / verdi | Bruk |
| --- | --- | --- |
| Robotliste | navn, DUID, produkt, modell, firmware, delt status, online | Grunnstamme for robotoversikt. |
| Home-data | home-id, romliste, enheter, produkter | Oppdagelse av nye roboter og rom. |
| Planer | schedule-id, cron, aktiv, segmenter, fan power, mop mode | Vise neste planlagte jobb. |
| Rå statusfelter | numeriske statuskoder fra cloud | Supplerende status når lokal LAN ikke svarer. |
| Kartkanal | kartbilde, rom, laderposisjon, robotposisjon | Vise kart i robotdetaljer. |

## Lokal LAN

Lokal LAN er best egnet for hyppigere driftsdata.

| Kommando | Innhold |
| --- | --- |
| `get_status` | state, battery, clean_time, clean_area, error_code, fan_power, mop_mode, charge_status. |
| `get_consumable` | børster, filter, sensor og støvtømming brukt tid. |
| `get_clean_summary` | total tid, total areal, antall vask og siste record-id-er. |
| `get_clean_record` | start/slutt, varighet, areal, completed/error, finish_reason. |
| `get_network_info` | SSID, IP, MAC/BSSID, RSSI. |
| `get_serial_number` | serienummer der roboten støtter det. |
| `get_room_mapping` | segment-id mot Roborock-rom. |
| `get_timezone` | robotens tidssone. |

## Kart

Kart hentes via Roborock cloud-kartkanal. Dette fungerer for aktivt/nåværende kart. Historisk kart per rengjøring er ikke bekreftet stabilt.

Hvis vi vil ha kart etter hver rengjøring fremover, bør loggeren hente kart rett etter at en jobb er ferdig og lagre det som snapshot.

## Anbefalt lagring i Fibaro10

| Tabelltype | Oppdatering |
| --- | --- |
| Roboter | Ved oppstart og når robotliste endres. |
| Statusmålinger | Periodisk sync fra loggeren. |
| Planlagte jobber | Ved oppstart og periodisk. |
| Utførte jobber | Ved endret historikk. |
| Forbruksdeler | Periodisk, typisk sjeldnere enn status. |
| Kart | Ved sync med kart eller når kart endres. |
| Probe-resultater | Ved ny robot eller feilsøking. |

## Feilsøking

1. Sjekk Admin -> Datakilder -> Roborock logger.
2. Sjekk Roborock_logger sin webflate på QNAP.
3. Sjekk at roboten er online i Roborock.
4. Sjekk om lokal IP har endret seg.
5. Sjekk pending-kø i loggeren hvis Fibaro10 har vært nede.

## Kilder

- Lokalt testet `python-roborock`.
- Roborock API-dokumentasjon for biblioteket.
- Data observert gjennom Roborock_logger og Fibaro10.
