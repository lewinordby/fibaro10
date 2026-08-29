# Omsetning API-adapter

Intern, avgrenset adapter mellom Mantis-appen Omsetning og Fibaro10-kjernen.
Tjenesten leverer ikke et eget brukergrensesnitt. Gjeldende flate er
`https://ny.lilletorget.net/omsetning/`.

Adapteren håndterer felles innlogging, videresender bare godkjente
omsetningsendepunkter og eksponerer `/health`, `/ready` og `/api/app/config`.

## Lokal kontroll

```powershell
python -m pytest tests/test_domain_microapps.py -q
```

## Isolert deploy

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy-domain-app-qnap.ps1 -App revenue
```

Deploy bygger bare `revenue_app`. Mantis-frontenden bygges i det separate
`lilletorget-mantis`-repoet.
