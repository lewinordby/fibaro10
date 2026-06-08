# HC3 energioppsamlinger

Sist kontrollert og oppdatert: 08.06.2026.

Denne oversikten dokumenterer hvilke HC3 QuickApps som summerer realtime effekt og akkumulert energi for Fibaro10.

## Realtime W

| QuickApp | Navn | Medlemmer |
|---:|---|---|
| 237 | Varmepumper R | 226, 230, 234 |
| 305 | Belysning R | 201, 208, 213, 275, 280, 286, 287, 292, 293, 299, 303, 207, 298, 143, 186, 424, 425, 440 |
| 333 | Massasje R | 309, 314, 319, 324, 399 |
| 332 | Annet R | 269, 247, 368, 373, 378, 405, 406, 160, 130, 449 |
| 331 | Differanse R | 221 minus 237, 305, 333 og 332 |

## Akkumulert kWh

| QuickApp | Navn | Medlemmer |
|---:|---|---|
| 335 | Varmepumper A | 226, 230, 234 |
| 336 | Lys A | 201, 208, 213, 275, 280, 286, 287, 292, 293, 299, 303, 207, 298, 143, 186, 424, 425, 440 |
| 337 | Massasje A | 398, 308, 313, 318, 323 |
| 328 | Annet A | 269, 247, 367, 372, 377, 405, 406, 160, 130, 449 |
| 334 | Differanse A | 220 minus 335, 336, 337 og 328 |

## Endring 08.06.2026

Lagt inn i Annet:

- 130: 35.0 Vifte VIP - NY
- 449: 95.0 Avfukter kjeller

Lagt inn i Lys/Belysning:

- 143: 39.0 soppelbod
- 186: 47.0 Lys kjeller
- 424: 89.1 6xspot over inngang
- 425: 89.2 Lyslist over inngang
- 440: 92.1 Gatelys parkering x2

Fibaro10 logger fortsatt avfukter separat som `avfukter_w` og `avfukter_kwh`, men beregnet differanse trekker ikke avfukter separat etter denne endringen siden avfukter inngar i Annet.

## Kontroll

HC3-vedlikeholdsappen kan brukes til live-kontroll:

```text
http://192.168.20.218:8108
```

API:

```text
http://192.168.20.218:8108/api/status
```
