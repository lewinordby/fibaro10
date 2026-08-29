# Systemoversikt

Oppdatert 29.08.2026.

Lilletorget består av ett domeneorientert PC-grensesnitt, tre mobile flater,
en kiosk, en API-kjerne og separate innsamlings- og bakgrunnstjenester. Gamle
desktop-, mikroapp-, iPad- og V1-grensesnitt er avviklet.

## Brukerflater

| Flate | URL | Formål |
| --- | --- | --- |
| Mantis | `https://app.lilletorget.net/` | Primær PC-app og installert PWA. |
| Kiosk | `https://kiosk.lilletorget.net/` | Fast robotstatus for 1920 x 1080. |
| Dashboard mobil | `https://online.lilletorget.net/` | Mobil status og daglig oversikt. |
| Vedlikehold mobil | `https://vedl.lilletorget.net/` | Rask oppgaveregistrering. |
| Alarm mobil | `https://alarm.lilletorget.net/` | Dører, solrom, pullerter og varsler. |
| OwnTracks | `https://owntracks.lilletorget.net/` | Lokasjoner, waypoints og besøk. |

Mantis har tretten apper under samme origin: Omsetning, Parkering, Soling,
Koble, Bygg, Renhold, Kontroll, Energi, Vedlikehold, Operasjonssentral,
Eiendeler, Rapporter og System. Felles origin gir én innlogging og ett
PWA-scope.

## Hovedarkitektur

```text
Nettleser/PWA
    |
    v
Caddy (TLS, privat LAN/VPN)
    |
    +--> Mantis/Nginx :8170
    |       |
    |       +--> API-adaptere :8151-8158
    |                    |
    +--------------------+--> Fibaro10 API :8110
                                      |
                                      +--> PostgreSQL
                                      +--> HC3, SUN2, EasyPark, Elvia og Yr
                                      +--> Roborock, Dreame, Axis og UniFi
                                      +--> OwnTracks og kjøretøyoppslag
```

## Aktive kjernetjenester

| Tjeneste | Rolle |
| --- | --- |
| `lilletorget_mantis` | Nginx og alle Mantis-appbygg. |
| `fibaro10` | Stabil Caddy-gateway til aktiv blå/grønn API-kjerne. |
| `fibaro10_blue` / `fibaro10_green` | Web-API; bare aktivt spor mottar trafikk. |
| `fibaro10_worker` | Bakgrunnsjobber og planlagt arbeid. |
| `revenue_app` til `link_app` | Åtte API-adaptere uten egne brukerflater. |
| `fibaro10_proxy` | TLS, privat tilgang, domener og sikkerhetsheadere. |
| `online_dashboard` | Mobil dashboard. |
| `maintenance_mobile` | Mobil vedlikehold. |
| `alarm_mobile` | Mobil alarm. |
| `lilletorget_kiosk` | Robotkiosk i eget repo/container. |

Adapterfordeling:

- `revenue_app`: Omsetning
- `parking_app`: Parkering
- `sun_app`: Soling
- `energy_app`: Energi
- `operations_app`: Bygg, Renhold og Kontroll
- `maintenance_app`: Vedlikehold
- `system_app`: System, Operasjonssentral, Eiendeler og Rapporter
- `link_app`: Koble

## Data- og integrasjonstjenester

| Tjeneste | Data |
| --- | --- |
| `easypark_downloader` | Planlagte EasyPark-importer og importtrigger. |
| `sun2_session_scraper` | Enkelttimer, senger, medlemmer, produkter og finans. |
| `sun2_importer` / `sun2_backfill_downloader` | Dagsfiler og historikk. |
| `roborock_logger` | Roborock-status, telemetri, kart, planer og jobber. |
| `dreame_logger` | Aqua10/Dreame-status, telemetri, planer og jobber. |
| `axis_camera_snapshots` | Åpningstidsbegrensede snapshots for soltimer. |
| `unifi_protect_events` | Kamera- og kjøretøyhendelser samt pullertkontroll. |
| `visual_anomaly_service` | Lokal bildeforskjell/AI for pullerter og trapp. |
| `car_info_lookup` | Svenske og danske kjøretøyoppslag etter SVV. |
| `parking_sun_linker` | Kandidater mellom parkering og SUN2-ID. |
| `owntracks_service` / `owntracks_postgres` | Posisjoner, waypoints og besøk. |

`System -> Datakilder` er operativ fasit for rytme, siste vellykkede kjøring,
alder og feil. Tjenestenes `/health` brukes til prosesshelse; faglig datakvalitet
avgjøres av importstatus, ikke bare av at containeren kjører.

## Nettverk og innlogging

- `app.lilletorget.net` og de interne appnavnene peker til privat QNAP-adresse.
- Caddy godtar interne flater bare fra LAN/VPN.
- Offentlig betrodd TLS utstedes med DNS-01; klientene trenger ikke lokale sertifikater.
- `lilletorget_session` er en opak, tilbakekallbar cookie for `.lilletorget.net`.
- Cookien er `Secure`, `HttpOnly` og `SameSite=Lax`.
- Adapterne lagrer aldri brukerens cookie i en delt HTTP-klient.

Gamle domener kan i en overgangsperiode svare med redirect til riktig Mantis-sti,
men de har ingen egen app eller container. De skal ikke installeres som PWA.

## Lagring og backup

- Fibaro10 og OwnTracks bruker separate PostgreSQL-databaser.
- Axis-buffer og Protect-bilder ligger på arkivvolum.
- Modeller og kalibrering ligger på SSD/arkivvolum.
- Nattlig backup inneholder runtimefiler, SQL-dumper, importerdata og tjenestedata.
- Komplett restore-pakke inneholder aktiv kode for Fibaro10, Mantis og kiosk samt oppsettsinstruksjon.
- Originalfiler og virksomhetsdata slettes ikke som del av frontendopprydding.
- Docker-opprydding er navngitt og kontrollert; datavolumer prunes aldri globalt.

## Drift og kvalitet

Backend kontrolleres med `scripts/check-local.ps1`, deployplan-test, health og
smoke. Mantis kontrolleres med `npm run verify`. Deploy bygger bare berørte
tjenester, mens endringer i kjerne og felles kontrakter utløser bredere kontroll.
Buildloggen lagrer bestilling, berørte apper, endringer, tester og deploystatus.
