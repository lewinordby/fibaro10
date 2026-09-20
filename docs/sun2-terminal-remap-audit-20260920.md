# SUN2 terminal output remapping: evidence audit

Audit date: 2026-09-20. The evidence sections below describe the state before
correction. Implementation and production verification are recorded at the end.

## Conclusion

The evidence strongly supports **2026-09-11 as the first day of the new VIP
room/output assignment**. The last documented session under the old assignment
was room 12 on **2026-09-10 at 17:59**. The first documented session under the new
assignment was room 12 on **2026-09-11 at 12:33**.

These are payment/session timestamps, NOT measured electrical relay transitions.
There is no relay telemetry in the evidence used here. The exact physical
changeover time cannot be established from these records.

The user confirmed the following physical change:

| Customer room | Previous terminal output | Current terminal output | Current actual SUN2 bed ID |
| --- | ---: | ---: | ---: |
| 10 | 11 | 10 | 649 |
| 11 | 12 | 11 | 679 |
| 12 | 13 | 12 | 680 |

SUN2 bed record 681, previously associated with output 13, is now named `...`
and disabled. This audit does not infer that its electrical output was observed
turning off at a particular time.

## Evidence and Time Basis

Payment/session and door timestamps below are local Europe/Oslo time (UTC+02:00
on these dates). Export creation timestamps are UTC. Do not apply a blanket
timezone conversion to all naive timestamps in the application.

Sources were read from existing archives and database tables, without requesting
an additional SUN2 scrape, changing HC3, restarting services or writing to the
production database. Database verification queries used read-only transactions.

### Original Daily Exports

Archive directory on QNAP:

`/share/CACHEDEV2_DATA/fibaro10_runtime/sun2_session_scraper/data/session_exports`

Inside `sun2_session_scraper`: `/data/session_exports`.

| Original archive | Export created, local time | Evidence |
| --- | --- | --- |
| `Sun2_sessions_2026-09-10.json` | 10 Sep 23:33:38 | Last VIP session: room 12, 17:59, 20 minutes, NOK 220; old name retained |
| `Sun2_sessions_2026-09-11.json` | 11 Sep 23:39:26 | Room 12 at 12:33 and 12:55; room 11 at 15:37; new names present |
| `Sun2_sessions_2026-09-12.json` | 12 Sep 23:44:49 | First observed new room 10 session at 21:18 |

The first observed room 10 session is NOT evidence of a separate changeover date.
The original 10 Sep export still used the old names late that evening; the 11 Sep
export used the new names. This supports the day boundary, but is not a log of
when the terminal configuration or wiring was changed.

### Independent Door Corroboration

Door sensor 539, `door_solrom_12`, retained its physical room assignment.

| Payment | Purchased duration | Relevant door close | Door open | Interpretation |
| --- | ---: | --- | --- | --- |
| 10 Sep 17:59 | 20 min | 18:01:10 | 18:25:47 | Consistent with expected start 18:02, end 18:22, then exit |
| 11 Sep 12:33 | 12 min | 12:34:02 | 12:50:23 | Consistent with expected start 12:36, end 12:48, then exit |
| 11 Sep 12:55 | 12 min | 12:58:03 | 13:11:43 | Consistent with expected start 12:58, end 13:10, then exit |

The start/end estimates apply the existing three-minute delay assumption; they
are not measurements of UV operation. Intermediate door opens/closes are retained
in `door_events`, not treated as separate paid sessions for this comparison.

`sun2_room_daily_stats` independently preserves the old room names on 9-10 Sep
and new names on 11-12 Sep. On 10 Sep it has one room 12 session; on 11 Sep it has
six room 12 sessions and one room 11 session, matching the daily session archive.

## Historical Data Problem

The current monthly SUN2 export applies current bed names to transactions from
before the changeover. Consequently, a new download is not a reliable source of
the historical physical room name.

The monthly archive audited here was created at 2026-09-20 05:01:13 UTC and
contains 1-19 Sep. It was compared against original daily archives for 1-10 Sep.

| Original physical room, 1-10 Sep | Original sessions | Original minutes | Original amount | Name in current monthly export |
| --- | ---: | ---: | ---: | --- |
| 11 | 16 | 349 | NOK 3,839.00 | Room 12 Super VIP |
| 12 | 36 | 754 | NOK 8,294.00 | `...` |
| Total affected | 52 | 1,103 | NOK 12,133.00 | Historical labels changed |

There were no room 10 sessions in this specific ten-day sample.

After reversing the name reassignment for this historical interval, the two
archives match exactly as multisets across ALL 262 sessions, including timestamp,
room, member identity, purchased duration and amount. Duplicate occurrences were
preserved by using multiset counts, not a set or first-match lookup. Personal
identifiers were used only for comparison and are not included in this report.

### Two Sessions Collapsed During Database Import

| Period 1-10 Sep | Sessions | Minutes | Amount |
| --- | ---: | ---: | ---: |
| Original daily archives / current monthly archive | 262 | 5,136 | NOK 50,365.16 |
| Current `sun2_tanning_sessions` | 260 | 5,091 | NOK 49,870.16 |
| Difference | 2 | 45 | NOK 495.00 |

At each of these timestamps, the archives contain two distinct sessions, one in
room 11 and one in room 12, with distinct source session IDs:

- 1 Sep 13:35: two sessions of 25 minutes / NOK 275 each.
- 2 Sep 22:57: two sessions of 20 minutes / NOK 220 each.

The database has only one row at each timestamp, both named `...`. The pairs
share member, timestamp, duration and amount, but are for different rooms.

The natural-key fallback in `ingest_sun2_tanning_sessions` omits the room
constraint entirely when both bed ID and room ID are unknown. The `...` row can
therefore match and overwrite the other room's row. This code path explains the
two observed collapses; the source export itself contains both records.

For the complete audited monthly export (1-19 Sep), source totals are 522
sessions, 10,230 minutes and NOK 100,341.20. Database daily counts, durations and
amounts match on 3-19 Sep; the same two shortfalls occur on 1-2 Sep. This does NOT
establish whether every dashboard or accounting total is affected, since some
views use separate daily statistics rather than individual sessions.

## Current Mapping Problem

Actual current `sun2_beds` metadata has IDs 649/679/680 for rooms 10/11/12.
However, the session scraper still derives IDs 679/680/681 from the room labels.
Those bed IDs on session records are assigned by application code, not read from a bed ID in
each transaction. They cannot independently prove which output was used.

The current bed metadata also retains legacy internal room IDs and physical
numbers because the room helper still contains the old assignment. Several
consumers use these IDs for status checks, door/session matching and alarms.

At audit time, 66 post-change VIP sessions were present through 20 Sep 07:18:
14 room 10 sessions, 25 room 11 sessions and 27 room 12 sessions. Their displayed
source names are current, but their derived bed IDs still use the old mapping.

Relevant implementation locations:

- `sun2_helpers.py`: `SUN2_ROOM_MAP_BY_DISPLAY`, `sun2_room_identity`.
- QNAP deployment `sun2_session_scraper/app/main.py`: `room_identity`, session
  normalization, stable source ID generation and actual bed metadata extraction.
- QNAP deployment `sun2_importer/app/main.py`: duplicated room identity mapping.
- `fibaro_core/services/runtime/sun.py`: session ingestion, natural-key fallback,
  source-file replacement and room identity backfill.
- `fibaro_core/services/runtime/sunroom.py`: current bed lookup and historical
  session canonicalization.
- `online_dashboard/app/main.py`: mobile door/room configuration.

## Requirements for a Safe Correction

1. Preserve the daily archives before any re-import. Current source labels can
   rewrite history; original exports are essential evidence.
2. Model physical room, terminal output, SUN2 bed record and legacy internal room
   ID as different identities. Keep the old and new assignments with validity
   periods. Use 11 Sep as the supported session-date boundary for these observed
   records; do not present midnight as a measured electrical switching time.
3. Distinguish when a transaction occurred from when its source label was read.
   A date-aware mapping alone is insufficient if a historical transaction is
   downloaded with its new label. Preserve the source name and import provenance.
4. Fix unknown-room natural-key matching before restoring data. An unknown room
   must not match a known, different room merely because other fields coincide.
5. Restore the 52 historical room assignments and the two missing individual
   sessions from the original evidence. Restore their identities, not just text.
6. Correct current bed/status matching and all ingest producers together. Do not
   globally rename `rom-11`/`rom-12`/`rom-13` or replace bed IDs across history.
7. Preserve session primary keys and attached images. The existing ten-day
   database sample has 1,296 images attached to its 260 sessions. Bulk source-file
   replacement is unsafe as a shortcut; images use a cascading session FK.
8. Regression-test both epochs, repeated imports, simultaneous same-member
   payments in different rooms, disabled beds, door/alarm matching and mobile
   display. Confirm exact counts, durations and amounts before and after.
9. Verify that historical re-imports do not create duplicates or change source
   IDs in ways that detach images or alarm associations. Keep a database backup
   and a reversible migration rather than editing production piecemeal.

## Archive Fingerprints

SHA-256 values observed during this audit:

```text
Sun2_sessions_2026-09-01.json
287ecd1ef5c159b272beefb913685f5ccbc70129e515cb33ba84eeefb74ad3ed
Sun2_sessions_2026-09-02.json
c38009a3af4c80d860b58771d2e6243fc83cf907456f79f6fb2bc41005e15669
Sun2_sessions_2026-09-10.json
dcf66b855401b5c08440ef279475023493e0be5316653b2a035f42aed5f9b843
Sun2_sessions_2026-09-11.json
c3c8abfd9ce6b59a7d41fdfba1e2368a7e09463a3320d18f3038c6921bcac65d
Sun2_sessions_2026-09-12.json
5550f98ca368434a9ddf07999c061b5fb0c1c8b6387c9c6d81802cafa3c0d3ac
Sun2_sessions_2026-09.json
aadebee37e2c62ea4c5fcd0239061d909b11a89c9a1ae57a7c72b617f9fa4398
```

No operational changes, migrations or deployments were made for this audit.

## Correction: Build 1855

The correction uses `sun2_room_mapping.py` in the core, mobile dashboard and
both SUN2 collectors. Physical rooms retain their existing internal database
identities; only dated terminal/bed associations change. Original daily exports
and newly downloaded historical transactions are interpreted separately.

Session ingestion updates existing rows in place. It never deletes a source
file's sessions, never matches an unknown room against a known room, and keeps
existing primary keys and source IDs. PostgreSQL serializes concurrent session
imports with a transaction advisory lock.

The repair script `scripts/repair_sun2_terminal_remap.py` defaults to rollback.
It requires the original daily archives and refuses unexpected or ambiguous
records. Before commit it checks exact historical multisets, whole-database
session counts and every existing image association. It then replays the monthly
archive plus ten original daily archives inside a savepoint, checks identities,
amounts and images, and rolls that verification back without advancing sync times.

Verified rollback result on production data:

- 50 existing historical sessions corrected, two missing sessions restored.
- 262 sessions / NOK 50,365.16 for 1-10 September, matching original archives.
- 66 newer session bed IDs, 25 daily statistic bed IDs and three bed records corrected.
- All 10,373 existing image rows and associations preserved.
- Ten images recovered for the two restored sessions. These reuse archived
  payment-camera frames only when member, payment timestamp, default target
  timestamp and offset match. They are not inferred images of a particular room
  or proof of a person's identity; manually selected/shifted frames are excluded.
- 784 imported rows replayed with zero inserted/replaced sessions and no changed
  stable identities, amounts or image associations.
- Regression suite: 748 passed plus 24 subtests; deployment-plan tests passed.

### Backup and Recovery

Protected backup directory on QNAP:
`/share/CACHEDEV3_DATA/fibaro10_archive/sun2-remap-20260920`.

`before.dump` contains the session, image, daily-statistic, bed and alarm tables.
`session-archives.tgz` preserves all source exports. The dump table-of-contents
was verified with `pg_restore --list`.

```text
before.dump SHA-256
038ac6706f34b88288815eae1771a20cad24925fb0ca95555aba47278b750836
session-archives.tgz SHA-256
91748dc2c6bf61f3c824dcbd0c00dcc3cc0d00c7656d336e0c1e610fb9b304d8
```

Run the repair in the core image with production environment, read-only archive
mount, and `--archive-dir /archives --report /repair-output/report.json`.
Only `--apply` commits. Any failed assertion rolls back the transaction. Reports
omit member identifiers. Re-running after a successful repair must produce zero
repairs and still pass the reimport checks.

Do not restore the whole backup over subsequently imported data. If recovery is
needed, restore into a separate database, compare the affected records and apply
a reviewed targeted recovery while SUN2 ingestion is paused. Old application
images alone are not a data rollback and would restore the defective mapping.

### Production Verification, 20 September 2026

The repair was committed and build 1855 deployed to the core web/worker,
mobile dashboard and both SUN2 collectors. HC3 configuration, schedules, alarm
thresholds, EasyPark and robot services were not changed. Web/API rollout used
the existing blue/green mechanism; ingestion and the worker were briefly paused
during the data transaction. Backup reports `applied.json` and
`post-deploy-idempotency.json` record the result.

- A second repair run found zero historical/current/statistic/bed updates,
  zero missing sessions and zero images needing recovery. All 784 replayed rows
  again preserved session identities, totals and images.
- A real automatic SUN2 import succeeded at 08:07:16 UTC / 10:07:16 Oslo,
  inserting one new session and updating the existing session rather than
  deleting/recreating it. The collector reported no error.
- API checks verified the three actual bed IDs, all three room-detail histories,
  retired bed 681, door status, door/session matching and alarm endpoints.
- Browser checks verified the mobile room list and details for rooms 10, 11, 12.
- The desktop room-11 filter for 1-2 September displayed room 11, opened session
  details and rendered a saved Axis image. Images on both simultaneous-session
  pairs returned successfully, including the restored sessions.
- The checked pages produced no JavaScript errors. All affected services were
  healthy; EasyPark and Roborock retained their existing container IDs.

The checks validate the observed transition and preserved history. They do not
claim an exact electrical switch time or prove that future source-site changes
cannot require a new mapping version.
