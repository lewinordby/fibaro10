# Porter og applikasjonslag

Oppdatert 29.08.2026.

## Brukerflater

| Port | Tjeneste | Rolle |
| ---: | --- | --- |
| 8170 | `lilletorget_mantis` | Alle tretten PC-mikroapper under `ny.lilletorget.net`. |
| 8163 | `lilletorget_kiosk` | Intern robotkiosk. |
| 8111 | `online_dashboard` | Mobil dashboard. |
| 8112 | `maintenance_mobile` | Mobil vedlikeholdsapp. |
| 8114 | `alarm_mobile` | Mobil alarm- og kontrollapp. |
| 8128 | `owntracks_service` | OwnTracks web/API. |

Mantis-appene er Omsetning, Parkering, Soling, Koble, Bygg, Renhold,
Kontroll, Energi, Vedlikehold, Operasjonssentral, Eiendeler, Rapporter og
System. De bygges i repoet `lilletorget-mantis` og leveres av én Nginx-container.

## API-lag

| Port | Tjeneste | Mantis-områder |
| ---: | --- | --- |
| 8110 | `fibaro10` | Kjerne-API for hele plattformen. |
| 8151 | `revenue_app` | Omsetning. |
| 8152 | `parking_app` | Parkering. |
| 8153 | `sun_app` | Soling. |
| 8154 | `energy_app` | Energi. |
| 8155 | `operations_app` | Bygg, Renhold og Kontroll. |
| 8156 | `maintenance_app` | Vedlikehold. |
| 8157 | `system_app` | System, Operasjonssentral, Eiendeler og Rapporter. |
| 8158 | `link_app` | Koble. |

Port 8151-8158 er API-adaptere uten egne HTML-fronter. De må være i drift fordi
Mantis bruker dem til autentisering, tilgangsavgrensning og fagdata. Port 8110
er API og teknisk health-endepunkt, ikke en reserve-desktop.

## Ansvarsdeling

| Kodeområde | Ansvar |
| --- | --- |
| `lilletorget-mantis/apps` | Inngang per Mantis-app. |
| `lilletorget-mantis/packages/mantis` | Kjøpt Mantis-skall og tema. |
| `lilletorget-mantis/packages/platform` | Ruting, typer, API-klient og fagvisninger. |
| `revenue_app` til `link_app` | Smale API-adaptere. |
| `main.py` og domenemoduler | Data, regler, database og jobber. |
| `packages/mobile-appkit` | Felles designsystem for mobilflatene. |

## Praktisk regel

- Brukere åpner `https://ny.lilletorget.net`.
- Mantis bygges og deployes fra sitt eget repo.
- Backend og adaptere bygges og deployes fra Fibaro10-repoet.
- Gamle porter 8150, 8113, 8160-8162 og 8171 er avviklet.
