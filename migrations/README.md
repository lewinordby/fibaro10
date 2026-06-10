# Database migrations

This folder is the source-controlled home for schema and data migrations.

## Practice

- Create one file per change in `migrations/versions`.
- Use the format `yyyyMMdd_HHmm_short_name.sql`.
- Keep each migration idempotent when practical.
- Record manual production execution in the build log.
- Do not edit old migrations after they have been run on QNAP. Add a new one instead.

## Create a new file

```powershell
.\scripts\new-migration.ps1 "add-energy-index"
```

## Run migrations

```powershell
python .\scripts\run-migrations.py --list
python .\scripts\run-migrations.py --dry-run
python .\scripts\run-migrations.py
```

The app does not auto-run these migrations during deploy yet. They are an audit trail and a controlled deploy step.
