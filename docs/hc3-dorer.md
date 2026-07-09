# HC3 dorer

Fibaro10 logger magnetfolere fra HC3 i tabellen `door_events`.

## Anbefalt modell for mange dorer

For mange dorer skal ikke en endring lese alle dorer. Modellen er:

1. En HC3 block scene per dor med OR for apnet/lukket.
2. En liten HC3 Lua scene per dor.
3. Block-scenen starter bare Lua-scenen for samme dor.
4. Lua-scenen leser `value` for sin egen `DEVICE_ID` og poster en konkret hendelse til Fibaro10.

Dette gir riktig oppforsel hvis to dorer endrer status samtidig. Da starter to ulike logger-scener og Fibaro10 mottar to separate hendelser.

## Eksisterende tre dorer

| HC3 device | Nkkel | Navn |
| --- | --- | --- |
| 453 | `door_453` | Bod/kjokken |
| 447 | `door_447` | Kjeller luke |
| 413 | `door_413` | Arbeidsrom |

## Klargjorte dorer uten HC3-id

Disse ligger i Fibaro10 som planlagte sensorer og vises som `Klargjort` frem til faktisk HC3 device-id legges inn.

| Nkkel | Navn | Gruppe | Avdeling |
| --- | --- | --- | --- |
| `door_solrom_01` | Solrom 1 | Solrom | 1.etg |
| `door_solrom_02` | Solrom 2 | Solrom | 1.etg |
| `door_solrom_03` | Solrom 3 | Solrom | 1.etg |
| `door_solrom_04` | Solrom 4 | Solrom | 2.etg |
| `door_solrom_05` | Solrom 5 | Solrom | 2.etg |
| `door_solrom_06` | Solrom 6 | Solrom | 2.etg |
| `door_solrom_07` | Solrom 7 | Solrom | 2.etg |
| `door_solrom_08` | Solrom 8 | Solrom | 2.etg |
| `door_solrom_09` | Solrom 9 | Solrom | 1.etg |
| `door_solrom_10` | Solrom 10 | Solrom | VIP |
| `door_solrom_11` | Solrom 11 | Solrom | VIP |
| `door_solrom_12` | Solrom 12 | Solrom | VIP |
| `door_inngang` | Inngang | Andre dorer | Bygg |
| `door_massasjestudio` | Massasjestudio | Andre dorer | Bygg |
| `door_vaskerom` | Vaskerom | Andre dorer | Bygg |
| `door_papirlager` | Papirlager | Andre dorer | Bygg |

## Installer HC3-scener

Kjor denne fra repoet nar HC3-credentials er tilgjengelig i miljovariabler:

```powershell
$env:HC3_BASE_URL = "http://192.168.1.10"
$env:HC3_USER = "<hc3-bruker>"
$env:HC3_PASS = "<hc3-passord>"
python scripts/upsert_hc3_single_door_logger_scenes.py
```

Scriptet oppretter eller oppdaterer disse Lua-scenene:

- `Dorlogger 453 - Bod/kjokken`
- `Dorlogger 447 - Kjeller luke`
- `Dorlogger 413 - Arbeidsrom`

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
