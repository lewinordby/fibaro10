# Parkering API-adapter

Intern, avgrenset adapter mellom Mantis-appen Parkering og Fibaro10-kjernen.
Tjenesten leverer ikke et eget brukergrensesnitt. Gjeldende flate er
`https://app.lilletorget.net/parkering/`.

Adapteren håndterer felles innlogging og videresender bare godkjente
parkeringsendepunkter. Den eksponerer `/health`, `/ready` og
`/api/app/config` for drift og overvåking.

## Lokal kontroll

```powershell
python -m pytest tests/test_domain_microapps.py -q
```

## Isolert deploy

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy-domain-app-qnap.ps1 -App parking
```

Deploy bygger bare `parking_app`. Mantis-frontenden bygges i det separate
`lilletorget-mantis`-repoet.
