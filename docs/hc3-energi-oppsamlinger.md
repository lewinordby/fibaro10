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

## Akkumulert kWh

| QuickApp | Navn | Medlemmer |
|---:|---|---|
| 335 | Varmepumper A | 226, 230, 234 |
| 336 | Lys A | 201, 208, 213, 275, 280, 286, 287, 292, 293, 299, 303, 207, 298, 143, 186, 424, 425, 440 |
| 337 | Massasje A | 398, 308, 313, 318, 323 |
| 328 | Annet A | 269, 247, 367, 372, 377, 405, 406, 160, 130, 449 |

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

QuickApp 331 `Differanse R` og 334 `Differanse A` finnes i HC3, men sendes ikke lenger til Fibaro10. Differanse har ingen hensikt aa logge separat fordi Fibaro10 beregner den fra realtime-verdiene.

Forbruksdelta og dagsforbruk i Fibaro10 beregnes fra realtime W-samples hvert 30. sekund. Fibaro10 lagrer energisamples i 30-sekunders bucket, slik at to samples i samme minutt ikke overskriver hverandre. Akkumulerte kWh-verdier fra HC3 logges som kontrollverdier, men brukes ikke som grunnlag for dagsforbruket. Dette er valgt fordi reset i en akkumulerende undermaler kan skjules i en samlet QuickApp-verdi.

## Rapporteringsfrekvens

Kontroll 08.06.2026 viste at Fibaro10 leste HC3 hvert 30. sekund, men flere Fibaro Switch 2-enheter hadde `Periodic power reports` satt til standardverdien 3600 sekunder. Dette gir for treg periodisk W-rapportering for realtime-basert forbruksberegning.

Endret i HC3:

- Parameter 58 `Periodic power reports` er satt til 30 sekunder på Fibaro FGS213/FGS223-noder 51, 52, 53, 65, 66, 68, 69, 70, 85, 89 og 92.
- Parameter 59 `Periodic energy reports` er ikke endret, siden Fibaro10 ikke bruker akkumulert kWh som grunnlag for dagsforbruk. Unntak: node 85 hadde allerede parameter 59 satt til 15 sekunder.
- Dimmere og ukjente modeller ble ikke endret. For disse må rapporteringsparametre vurderes separat per modell.

HC3-endepunkt brukt for lesing:

```text
/api/zwave/hc/configuration/{nodeId}
```

HC3-endepunkt brukt for endring:

```text
POST /api/zwave/configuration_parameters/{addr}/58/value
Body: {"value": 30}
```

## Kjente umalte laster

- Kurs 35 `AVTREKKSVIFTE TAK (LOFT SYD OVER ROM 9)` er en 3-fas avtrekksvifte uten effektmåler. Den styres av HC3 device 134 og er registrert i Fibaro10 lastregister som estimert 320 W når den gar.
- Kurs 5 `TERMINAL/ REGISTRERING OG KREMAUTOMAT` har måler og skal ikke regnes som en umalt hovedkandidat uten ny kontroll.
- Kurs 29 `VVBEREDER UNDER ROM 8 + STIKK VIP BOD` har måler via HC3 `84.0 Varmtvann`: device 399 for realtime W og 398 for akkumulert kWh. Den ligger i Massasje-gruppen.

Solsenganalysen bruker ra energidifferanse, men korrigerer analyseverdien for kjente umalte laster med kjent status. Per 08.06.2026 trekkes 320 W fra nar ventilasjonsloggen viser at takvifte/avtrekk er pa. Selve energiloggen endres ikke.

## Kontroll

HC3-vedlikeholdsappen kan brukes til live-kontroll:

```text
http://192.168.20.218:8108
```

API:

```text
http://192.168.20.218:8108/api/status
```
