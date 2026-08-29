# Dokumentasjonsoversikt

Oppdatert 29.08.2026.

Dette er inngangen til dokumentasjonen for Lilletorget. Den eneste ordinære
PC-flaten er Mantis på `https://ny.lilletorget.net`. Mobilflatene beholdes som
separate, oppgaveorienterte apper. Fibaro10-repoet eier API, database,
forretningsregler, bakgrunnsjobber og integrasjoner.

## Operativ fasit

1. `System -> Datakilder` viser reell status, siste kjøring og feil.
2. `System -> Systemkart` viser aktive tjenester og avhengigheter.
3. `System -> Manual` beskriver gjeldende bruk.
4. Mantis `packages/platform/src/app-definitions.json` eier aktive apper og ruter.
5. Compose, Caddy og tjenestekode er teknisk fasit.

## Levende dokumentasjon

| Side | Adresse |
| --- | --- |
| Manual | `https://ny.lilletorget.net/system/manual` |
| Menystruktur | `https://ny.lilletorget.net/system/manual/menystruktur` |
| Datakilder | `https://ny.lilletorget.net/system/datakilder` |
| Systemkart | `https://ny.lilletorget.net/system/systemkart` |
| Undersystemer | `https://ny.lilletorget.net/system/undersystemer` |
| Buildlogg | `https://ny.lilletorget.net/system/build` |

## Gjeldende dokumenter

| Fil | Innhold |
| --- | --- |
| `docs/kort-brukermanual.md` | Kort operativ brukerhjelp. |
| `docs/systemoversikt.md` | Aktiv arkitektur, tjenester og dataflyt. |
| `docs/mikroapp-porter.md` | Porter og skillet mellom UI og API-adaptere. |
| `docs/intern-https.md` | DNS, TLS, intern tilgang og PWA. |
| `docs/utviklingsoppsett.md` | Test, deploy, backup og restore. |
| `docs/api-kontrakter.md` | Kontrakten mellom kjerne, adaptere og Mantis. |

Fagdokumentene for OwnTracks, kamera, kjøretøy, HC3, energi, SUN2, Roborock
og Dreame ligger i samme katalog. Tjenester med egen drift har også README ved
kildekoden.

Den tekniske PDF-en genereres med
`scripts/generate-system-documentation-pdf.py`.

## Avgrensning

Gamle desktop-, mikroapp-, iPad- og V1-grensesnitt er fjernet. Historiske
buildloggoppføringer beholdes som revisjonsspor, men er ikke driftsdokumentasjon.
En endring i apper, ruter, porter, deploy eller backup er ikke ferdig før denne
dokumentasjonen er oppdatert og testene består.
