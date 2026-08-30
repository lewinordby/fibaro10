# Lilletorget / Fibaro10

Produksjonsplattform for omsetning, parkering, soling, energi, bygg og drift,
vedlikehold, kamera, lokasjon og systemkontroll.

## Gjeldende brukerflate

Den primære brukerflaten er Mantis-serien:

https://app.lilletorget.net

Den består av tretten fagapper og en appvelger under samme origin: Omsetning,
Parkering, Soling, Koble, Bygg, Renhold, Kontroll, Energi, Vedlikehold,
Operasjon, Eiendeler, Rapporter og System.

Mantis-kildekoden ligger i det separate private repoet
https://github.com/lewinordby/lilletorget-mantis. Dette repoet eier Fibaro10-
kjernen, fagadapterne, integrasjonene, mobilflatene og driftsverktøyene.

## Arkitektur

- Fibaro10 på port 8110: FastAPI, forretningsregler, PostgreSQL, jobber og API.
- Fagadaptere på port 8151-8158: autentisering og fagkontrakter mot kjernen.
- Mantis på port 8170: gjeldende React/MUI-brukerflate med 116 fagruter.
- Separate innsamlere: EasyPark, SUN2, Axis, UniFi Protect, kjøretøyoppslag,
  Roborock, Dreame, OwnTracks og koblingsmotor.
- Caddy: intern HTTPS med offentlig betrodde sertifikater og LAN/VPN-grense.

`main.py` er inngangspunktet til kjernen. `fibaro_core/` eier nå felles
databasemodeller, valideringsmodeller og de første isolerte API-routerne.
Summer, rangering og årskurver ligger i egne fagmoduler under
`fibaro_core/services/summaries/`.
Dette er interne moduler i samme tjeneste, ikke nye mikroapper.
Se [modulgrensene](docs/core-modules.md) før videre oppsplitting.

## Dokumentasjon

Start i docs/README.md.

Viktigste innganger:

- docs/kort-brukermanual.md
- docs/systemoversikt.md
- docs/utviklingsoppsett.md
- docs/core-modules.md
- docs/intern-https.md
- docs/mikroapp-porter.md

Levende manual:

https://app.lilletorget.net/system/manual

## Lokal kontroll

    python -m pytest
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-local.ps1

## Produksjonsdeploy

    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy-qnap.ps1

Mantis bygges, testes og deployes separat fra lilletorget-mantis-repoet.
Se docs/utviklingsoppsett.md før oppsett av ny maskin eller gjenoppretting.

## Sikkerhet

Faktiske nøkler, passord, tokens og databaseadresser ligger i runtime-.env og
skal ikke inn i Git. Nattbackupen inneholder gjenopprettingskritiske
konfigurasjoner og må behandles som sensitiv.
