# Porter og applikasjonslag

Oppdatert 29.08.2026, build 1818.

Løsningen har to brukergrensesnittgenerasjoner som må skilles tydelig fra
API-laget. Gjeldende brukerflate er Mantis på port 8170. Port 8151-8158 er
fortsatt operative fag-API-er og reserveflater, ikke kilde for nytt design.

## Gjeldende Mantis-stack

| Vertsport | Tjeneste | Rolle |
| ---: | --- | --- |
| 8170 | lilletorget_mantis | Nginx som leverer alle tretten Mantis-bygg og ruter API-kall til fag-API-ene. |

Caddy eksponerer containeren som ett internt HTTPS-domene på formen
https://ny.lilletorget.net/<app>/<side>.

Appene er Omsetning, Parkering, Soling, Koble, Bygg, Renhold, Kontroll, Energi,
Vedlikehold, Operasjonssentral, Eiendeler, Rapporter og System. Hver app har
eget statisk bygg under dist/<app>, men hele serien leveres fra samme image.

## Fag-API-er og forrige brukerflate

| Port | Tjeneste | Gjeldende rolle |
| ---: | --- | --- |
| 8150 | shell_app | Forrige appvelger/reserve, ikke primær brukerinngang. |
| 8151 | revenue_app | Omsetningsadapter og tidligere fagfrontend. |
| 8152 | parking_app | Parkeringsadapter og tidligere fagfrontend. |
| 8153 | sun_app | Solingsadapter og tidligere fagfrontend. |
| 8154 | energy_app | Energiadapter og tidligere fagfrontend. |
| 8155 | operations_app | Adapter for bygg og drift. |
| 8156 | maintenance_app | Vedlikeholdsadapter. |
| 8157 | system_app | Systemadapter, også for operasjon, eiendeler og rapporter. |
| 8158 | link_app | Adapter for koblingsmotoren. |

Mantis bruker disse tjenestene for autentisering og fagdata. De skal derfor ikke
stoppes selv om brukergrensesnittet på app.lilletorget.net er reserve.

## Ansvarsdeling

| Kodeområde | Ansvar | Normal påvirkning |
| --- | --- | --- |
| lilletorget-mantis/apps/* | Ett inngangspunkt per Mantis-app. | Den aktuelle appens inngang. |
| lilletorget-mantis/packages/mantis | Mantis-skall, tema og leverandørkomponenter. | Alle Mantis-appene. |
| lilletorget-mantis/packages/platform | Ruting, API-klient, kontrakter og fagvisninger. | Berørte Mantis-apper. |
| packages/microapp-ui | Delt rammeverk for forrige mikroappgenerasjon. | Bare reservegenerasjonen. |
| revenue_app til link_app | Backendadaptere og eldre frontend. | Det aktuelle fag-API-et. |
| main.py og domenemoduler | Fibaro10 API, regler, database og jobber. | Kjerne og berørte adaptere. |

Autoritativ Mantis-meny ligger i
lilletorget-mantis/packages/platform/src/app-definitions.json. En side skal
ikke dokumenteres som aktiv før den finnes der og består produksjonssmoke.

## Utvikling og utrulling

Mantis-repo:

    npm ci
    npm run build
    npm run verify
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy-qnap.ps1

Fibaro10/fag-API-er:

    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-local.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy-qnap.ps1

En gammel fagapp kan fortsatt rulles isolert med
scripts/deploy-domain-app-qnap.ps1, men det bygger ikke Mantis-flaten.

## Praktisk regel

- Brukere åpner https://ny.lilletorget.net.
- Mantis leveres på 8170.
- Fag-API-ene på 8151-8158 må være friske.
- Fibaro10-kjernen på 8110 må være frisk.
- app.lilletorget.net og fibaro10.lilletorget.net er reserver og
  funksjonsreferanser, ikke primær navigasjon.
