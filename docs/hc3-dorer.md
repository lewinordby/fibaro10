# HC3 dorer

Oppdatert 12.07.2026.

Fibaro10 logger magnetfolere fra HC3 i tabellen `door_events`.

## Anbefalt modell for mange dorer

For mange dorer skal ikke en endring lese alle dorer. Modellen er:

1. En HC3 block scene per dor med OR for apnet/lukket.
2. En liten HC3 Lua scene per dor.
3. Block-scenen starter bare Lua-scenen for samme dor.
4. Lua-scenen leser `value` for sin egen `DEVICE_ID` og poster en konkret hendelse til Fibaro10.

Dette gir riktig oppforsel hvis to dorer endrer status samtidig. Da starter to ulike logger-scener og Fibaro10 mottar to separate hendelser.

## Statuskontroll fra Fibaro10

HC3-triggerne er fortsatt primaerkilden, men Fibaro10 har ogsa en sikkerhetsjobb som jevnlig spor HC3 API direkte om faktisk status for alle konfigurerte dorer.

- Jobb: `hc3_door_poll_sync`
- Standard intervall: 30 sekunder
- Datakilde: `Admin -> Datakilder -> HC3 dorstatuskontroll`
- HC3-konfig: `.env.hc3-watchdog` pa QNAP, lastet inn i `fibaro10`-containeren

Jobben skriver ikke nye rader nar Fibaro10 og HC3 allerede er enige. Den skriver bare en `door_sync`-hendelse med kilde `HC3 POLL SYNC` hvis siste Fibaro10-status ikke stemmer med HC3 sin faktiske `value`.

Manuell tvangssync kan kjoeres mot:

```text
POST /api/hc3/doors/poll-sync
```

## Eksisterende tre dorer

| HC3 device | Nkkel | Navn |
| --- | --- | --- |
| 453 | `door_453` | Bod/kjokken |
| 447 | `door_447` | Kjeller luke |
| 413 | `door_413` | Arbeidsrom |

## Monterte dorer

Disse ligger i Fibaro10 med fast kobling mot HC3 device-id. Solrom 2 og Solrom 3 er fortsatt klargjort uten HC3-id fordi HC3 ikke har monterte `doorSensor`-enheter med disse navnene ved siste kontroll.

| HC3 device | Nkkel | Navn | Gruppe | Avdeling |
| --- | --- | --- | --- | --- |
| 459 | `door_solrom_01` | Solrom 1 | Solrom | 1.etg |
| - | `door_solrom_02` | Solrom 2 | Solrom | 1.etg |
| - | `door_solrom_03` | Solrom 3 | Solrom | 1.etg |
| 465 | `door_solrom_04` | Solrom 4 | Solrom | 2.etg |
| 463 | `door_solrom_05` | Solrom 5 | Solrom | 2.etg |
| 469 | `door_solrom_06` | Solrom 6 | Solrom | 2.etg |
| 471 | `door_solrom_07` | Solrom 7 | Solrom | 2.etg |
| 473 | `door_solrom_08` | Solrom 8 | Solrom | 2.etg |
| 475 | `door_solrom_09` | Solrom 9 | Solrom | 1.etg |
| 477 | `door_solrom_10` | Solrom 10 | Solrom | VIP |
| 479 | `door_solrom_11` | Solrom 11 | Solrom | VIP |
| 491 | `door_solrom_12` | Solrom 12 | Solrom | VIP |
| 499 | `door_inngang` | Inngang | Andre dorer | Bygg |
| 483 | `door_massasjestudio` | Massasjestudio | Andre dorer | Bygg |
| 489 | `door_vaskerom` | Vaskerom | Andre dorer | Bygg |
| 487 | `door_papirlager` | Papirlager | Andre dorer | Bygg |
| 493 | `door_vaktmesterlager` | Vaktmesterlager | Andre dorer | Bygg |
| 495 | `door_toalett` | Toalett | Andre dorer | Bygg |

## Installer HC3-scener

Kjor denne fra repoet nar HC3-credentials er tilgjengelig i miljovariabler:

```powershell
$env:HC3_BASE_URL = "http://192.168.1.10"
$env:HC3_USER = "<hc3-bruker>"
$env:HC3_PASS = "<hc3-passord>"
python scripts/upsert_hc3_single_door_logger_scenes.py
```

Scriptet oppretter eller oppdaterer en Lua-scene per montert dor, for eksempel:

- `Dorlogger 459 - Solrom 1`
- `Dorlogger 453 - Bod/kjokken`
- `Dorlogger 499 - Inngang`

Det skriver ogsa en scene-map til `outputs/hc3_inventory/door_single_scene_map_*.json`.

Scriptet oppretter eller oppdaterer ogsa en block-trigger-scene per dor:

- `Dortrigger <device> - <navn>`

```text
IF <dorens sensor> value == true
OR <dorens sensor> value == false
THEN run scene <Dorlogger ...>
```

Block-scenen skal ikke inneholde API-url, JSON eller forretningslogikk. Den skal bare starte riktig tynn Lua-scene.

## Manuell sync

Den gamle felles Lua-scenen kan beholdes som manuell sync/test. Den skal ikke brukes som fast trigger for alle dorer nar alle 19 dorer er lagt inn.
