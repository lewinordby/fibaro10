# Lilletorget Vedlikehold mobil

Oppdatert 10.07.2026.

Egen mobilflate for rask vedlikeholdsregistrering på `https://vedl.lilletorget.net`.

## Formål

- Bruke samme brukernavn/passord som Fibaro10.
- Skrive til samme `maintenance_log_entries`-grunnlag via Fibaro10 API.
- Gjøre registrering fra mobil raskere enn hovedappen.
- Automatisk tagge oppgaver etter valgt kategori og valgt utstyr.
- Vise bare relevante tidligere oppgaver nederst på registreringssiden.

## Førsteside

Førstesiden har store raske valg:

- Robotvaskere
- Varmepumper
- Solsenger
- Kremautomat
- Annet

Hvert valg åpner en kompakt registreringsside. Tidspunkt settes automatisk til nå, men kan endres fra toppfeltet.

## Kategorier og standardoppgaver

Robotvaskere:

- Velg én, flere eller alle robotvaskere.
- Robotnavn hentes fra Fibaro10/Roborock-grunnlaget.
- Standardoppgaver: `Rengjort`, `Skiftet mopper`, `Skiftet valse`, `Rengjort brett`.

Varmepumper:

- Valg: `1.etg`, `2.etg`, `VIP`.
- Standardoppgaver: `Renset filter`, `Endret innstilling`.

Egne poster kan åpnes og redigeres av brukeren som opprettet dem.

## Samspill med Fibaro10

Mobilappen er en separat FastAPI-app, men er ikke egen datakilde. Den sender og henter data via Fibaro10:

```text
maintenance_mobile
  -> FIBARO10_BASE_URL=http://fibaro10:8110
  -> Fibaro10 API
  -> maintenance_log_entries
```

I Fibaro10 vises samme datagrunnlag under:

- `Vedlikehold -> Oversikt`
- `Vedlikehold -> Besøk`

Besøk kommer fra OwnTracks via Fibaro10 og kobles til vedlikeholdsoppgaver basert på tidspunkt.

## Miljøvariabler

- `FIBARO10_BASE_URL`: intern URL til Fibaro10, normalt `http://fibaro10:8110`.
- `MAINTENANCE_MOBILE_SESSION_SECRET`: HMAC-secret for mobilappens egen sesjonscookie.

## Drift

Tjenesten bygges og startes av hoveddeploy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy-qnap.ps1
```

Health:

```text
https://vedl.lilletorget.net/health
```
