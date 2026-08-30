# Fibaro10 core modules

Updated 2026-08-30, build 1833.

## Forecasts and settlements (1833)

`services/forecasts/` owns calendar/holiday weighting, daily and period models,
forecast assembly and snapshot persistence. Builders receive the existing cache
and summary reader explicitly. They neither own a second cache nor commit the
caller's transaction. The import-triggered save still follows the same import.
Sixty-four frozen payload/SQL contracts come from build 1832, not the refactor.

`services/settlements/` separates parsing, source queries, control calculations,
field presentation, full responses, Gmail retrieval and reconciliation. Existing
credit-note signs, pre-2026 source availability and VAT/control rules are unchanged.
Parsing and source reads are not coupled to a web request or engine creation.
Shared response primitives live in `services/presentation.py`.

This stage reduces main.py from 37,904 to 34,689 physical lines. The full local
suite passes (557 tests, two unavailable optional Roborock tests skipped).
Subsequent stages will be deployed together to avoid repeated worker restarts.

## Scope

The first three stages of splitting `main.py` are complete, not a rewrite or a new
microservice. The web and worker processes still run the same application,
use the same PostgreSQL database and expose the same public endpoints.
Frontend, collectors, schedules, authentication policy and database schema
are unchanged.

The entry point has decreased from 43,580 to 40,340 lines in build 1830 and
to 39,128 physical lines in build 1831, then 37,904 in build 1832. The goal
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
| `fibaro_core/services/summaries/sun.py` | Daily-import precedence, live-session fallback, batch period queries, totals, top lists and year curves. |
| `fibaro_core/services/summaries/parking.py` | Parking aggregates, batch cutoff queries, top lists and year curves. |
| `fibaro_core/services/summaries/energy.py` | Daily, monthly and yearly energy aggregates and estimated-hour counts. |
| `fibaro_core/services/summaries/revenue.py` | Combined revenue, day/week/month rankings and accumulated year curves. |
| `fibaro_core/services/summaries/periods.py` | Calendar normalization, ISO week identity, year navigation and the effective month helpers. |
| `fibaro_core/services/comparisons/windows.py` | Source cutoffs, shared day/week/month windows, navigation and timeline coordinates. |
| `fibaro_core/services/comparisons/overview.py` | Explicit dashboard period plans, batched source snapshots and the four comparison cards. |
| `fibaro_core/services/comparisons/chart.py` | Comparison response assembly with an explicit session, clock value, import status and timeline reader. |
| `fibaro_core/services/comparisons/years.py` | Pure annual-comparison response builders for sun, parking and revenue. |
| `value_parsing.py` | Existing value parsers plus the extracted int_or_zero / float_or_zero conversions. |
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

## Calculation boundaries

Summary builders receive a session from the caller and only execute reads.
They do not create engines, retrieve credentials, start imports or own caches.
The existing `SUMMARY_CACHE`, five-minute lifetime, forced refresh and prefix
invalidation remain in main. The comparison modules receive the current clock
value and import status explicitly; sun and parking retain independent cutoffs
when last-successful timestamps exist. No comparison module starts an import.

The migration preserves these rules:

- SUN2 daily reports take precedence over individual sessions for the same
  day, including a daily report with zero sales. Sessions fill missing days.
- Period boundaries are start-inclusive and end-exclusive. Time snapshots
  use the exact supplied timestamp, including seconds.
- Batch time snapshots still execute one query for all requested periods;
  SUN2 date snapshots execute three. Aggregate builders retain their query counts.
- Weeks use ISO week-years. Calendar-year curves keep the existing ordinal
  day alignment and leap-year behavior.
- Existing room/vehicle rollups retain their maximum-daily-count semantics;
  they have not been changed into distinct counts across the whole period.
- Ranking still excludes the current/future period and nonpositive historical
  totals, with ties receiving the same rank.

The two shadowed definitions of `add_months` and `month_label` were removed.
Only their previously effective implementations remain, now in periods.py.
In particular, `add_months` returns the first day of the destination month;
this release does not silently switch to preserving the input day number.

## Comparison boundaries

Main still owns request parsing, database sessions, cached summary retrieval,
import-status retrieval, and the room/parking event reader. The comparison chart
receives that timeline reader explicitly, avoiding reverse imports or duplicated
room mapping. HTTP paths, query defaults, validation and response shapes remain
unchanged. The full overview retains its non-business fields.

The dashboard now derives day/week/month windows from the same function as the
comparison chart. Frozen dataclasses describe current, previous and extra
reference periods. All four cards use one presenter, with revenue/count ranking
selected by scope. Snapshot reads remain batched: eight full SUN2 periods,
twelve SUN2 cutoff periods and twenty parking periods. These use the same
existing three batch helpers (five underlying SQL queries).

Important preserved behavior, not new guarantees:

- A newer failed import does not advance a source cutoff. UTC timestamps are
  converted to Oslo local time; future source timestamps are clamped to now.
- Without a successful source timestamp or explicit fallback, the existing
  policy falls back to now. This release does not introduce a missing-data state.
- Past selected periods are complete. A future anchor is clamped to today.
- Day charts span 06:00-24:00 and week charts show the full week. Reference
  lanes extend through the full reference period, while comparison totals still
  use the matching source cutoff. Month chart behavior is unchanged.
- Dashboard year references use elapsed local calendar days, not month/day
  matching. Annual charts retain ordinal-day alignment and daily rather than
  intraday granularity. Leap-year offsets have not been reinterpreted.
- ISO week 53 falls back to the final available week of the prior ISO year.
- Comparisons, forecasts and settlements are separate ownership boundaries;
  the latter two are not modified in this stage.

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
- `test_summary_calculations.py` runs independently of main, with explicit
  assertions and output/SQL fingerprints captured from build 1830 before
  moving code. Cases cover mixed source history, refunds, missing values,
  ISO boundaries, leap years, top-20 lists and exact timestamp limits.
- `test_summary_runtime.py` verifies re-exports, source-specific cutoffs,
  cache behavior and the absence of shadowed top-level function definitions.
- `test_comparison_contracts.py` compares 1,176 deterministic dashboard/chart/year
  scenarios with output and requested-period fingerprints recorded before moving
  build 1831 code. Seven additional full-overview cases replay the original
  build 1831 function and include non-business fields and query structure.
- `test_comparison_windows.py` checks exact source timestamps, UTC conversion,
  stale/missing/future sources, shorter months, leap years, ISO weeks, navigation,
  ranking basis, totals and batched reads without importing main.
- `test_comparison_runtime.py` exercises HTTP validation, session closure on
  errors, reference selection and the difference between full chart lanes and
  cutoff-based comparison totals.

Do not regenerate `tests/fixtures/core_contracts.json` just to make a refactor
pass. Only intentionally accepted public-contract changes justify a new
snapshot; review the changed sections first.
The same restriction applies to `tests/fixtures/summary_contracts.json`.
It also applies to `comparison_contracts.json` and `overview_full_contracts.json`.

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

1. Forecasts, then settlement calculations, as separate domain extractions.
2. Read-oriented domain endpoints using explicit sessions and cache ownership.
3. Import orchestration, alarm evaluation and background workers, preserving
   locks, schedules, transaction boundaries and lifecycle ownership.
4. Remaining HTTP composition and obsolete compatibility imports.

Each step needs domain behavior tests as well as unchanged contract snapshots.
Shared state must have a single owner. Never create a second scheduler or
database engine inside an extracted router to make imports work.
