# Fibaro10 core modules

Updated 2026-08-30, build 1830.

## Scope

This is the first stage of splitting `main.py`, not a rewrite or a new
microservice. The web and worker processes still run the same application,
use the same PostgreSQL database and expose the same public endpoints.
Frontend, collectors, schedules, authentication policy and database schema
are unchanged.

The entry point has decreased from 43,580 to 40,340 physical lines. The goal
is clearer ownership and isolated testing; this change does not claim faster
SQL queries or a measured reduction in user-facing response time.

## Ownership

| Location | Responsibility |
| --- | --- |
| `main.py` | Loads dotenv, creates runtime resources, registers middleware, lifecycle and routers. Still contains domains not yet extracted. |
| `fibaro_core/database.py` | One shared declarative Base; explicit engine and session factory creation. No engine is created on import. |
| `fibaro_core/config.py` | Shared snapshot-offset setting used by the Sun2 model and image logic. Environment is loaded by main before imports. |
| `fibaro_core/models/` | All 63 existing SQLAlchemy models, grouped by domain. No queries or running jobs. |
| `fibaro_core/schemas/` | All 41 existing Pydantic input contracts, grouped by domain. |
| `fibaro_core/schema_bootstrap.py` | Existing startup column/index definitions, applied by the existing startup procedure. |
| `fibaro_core/export_definitions.py` | Static export columns and dataset descriptions. |
| `fibaro_core/services/assets.py` | Asset input mapping and output serialization. |
| `fibaro_core/services/automations.py` | Automation-workbench input mapping and output serialization. Does not execute rules. |
| `fibaro_core/routers/assets.py` | Four existing asset endpoints: list, create, update and discover. |
| `fibaro_core/routers/automations.py` | Three existing workbench endpoints: list, create and update. |
| `time_formatting.py` | Existing time helpers, including the extracted `api_local_iso`. Naive local timestamps retain their original meaning. |

Model domains are building, cleaning, energy, finance, linking, maintenance,
parking, sun and system. Models retain their exact table names, defaults,
indexes and relationships. There is only one Base and metadata registry.
No database migration is required for this extraction.

## Dependency direction

```text
main.py (runtime composition)
  -> router factories (session factory + authorization callback)
     -> services (mapping and domain behavior)
        -> schemas / models / shared helpers
           -> shared Base / configuration
```

Core modules must never import `main`. Router factories receive dependencies
explicitly and create no database or background worker of their own. Existing
middleware still handles normal authentication; write endpoints retain their
existing settings-access checks.

Main re-exports model, schema and helper names while existing scripts and
tests still import them there. These are aliases to the same definitions,
not duplicate implementations. New domain code should import the owning
module directly.

## Verification

```powershell
python -m pytest tests -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test-deploy-plan.ps1
git diff --check
```

The focused core tests are also included in `scripts/check-local.ps1`:

- `test_core_contracts.py` compares database DDL/defaults/indexes, static
  definitions, OpenAPI schemas/operations and route order with a snapshot
  recorded from build 1829 before extraction.
- `test_core_architecture.py` checks isolated imports, shared model identity,
  absence of reverse imports, explicit database creation and timezone behavior.
- `test_core_routers.py` exercises HTTP reads, writes, filters, validation,
  forbidden access, missing records, discovery deduplication and commit failures
  with injected test sessions. These tests never write to production.
- Existing operational workspace tests import their domain services directly.

Do not regenerate `tests/fixtures/core_contracts.json` just to make a refactor
pass. Only intentionally accepted public-contract changes justify a new
snapshot; review the changed sections first.

## Deployment

Changes under `fibaro_core/` map to the `fibaro10` core deployment target.
The new package is included by the existing Docker build. The core rollout
builds the inactive web slot, verifies health/build, switches the gateway and
then updates the core worker. Collectors and frontend applications must not
be restarted for this extraction.

Before rollout, verify the production checkout and preserve a rollback copy.
Do not reset or clean away runtime data or unrelated work. Verify the new
core endpoints through the authenticated adapters and compare collector
container start times before/after rollout.

## Remaining extraction

Most of main still needs modularization. Continue with one bounded domain at
a time, not by blindly moving endpoint decorators:

1. Summary calculations and queries for sun, parking, energy and revenue.
2. Read-oriented domain endpoints using explicit sessions and cache ownership.
3. Import orchestration, alarm evaluation and background workers, preserving
   locks, schedules, transaction boundaries and lifecycle ownership.
4. Remaining HTTP composition and obsolete compatibility imports.

Each step needs domain behavior tests as well as unchanged contract snapshots.
Shared state must have a single owner. Never create a second scheduler or
database engine inside an extracted router to make imports work.
