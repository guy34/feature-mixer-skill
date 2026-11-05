# Unified Community Forum: migration plan

Status: plan approved (benchmark operator, pre-approved, compatibility phase) · running: NOT approved · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).
Whether Boardly or OpenForum hold real data is unknown; if neither does, no
migration is needed and the app starts from `schema.sql`.

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:user | User | copy A users as is (uuid kept), imported_from = 'A' | low | none | plan only |
| migration:user | User | copy B users with new uuid, legacy_id = B id, name → display_name | high | none (ids change; old id kept in legacy_id) | plan only |
| migration:user | User | B role user/admin → member; merge B users whose lower-cased email already exists in A into the A account | high | B-only role "admin" (no observed powers) | plan only |
| migration:post | Post | copy A posts as is (uuid, status, timestamps) | low | none | plan only |
| migration:post | Post | copy B posts with new uuid, legacy_id = B id, author_id via users legacy map (null stays null), status published, imported_from = 'B' | high | none (ids change; old id kept) | plan only |
| migration:post | Post | B created_at (no time zone) → timestamptz using B's server time zone | high | wrong times if the zone is guessed: blocked until the user states it | plan only |

## Before running

- Backup: pg_dump of the target, and copies of both source databases; restore tested on a scratch database.
- Dry run: on copies, recording row counts per table before and after.
- Checks: users A + B − merged-by-email = users; posts A + B = posts; no post with a dangling author; every B post has legacy_id; no body over 10000; counts of B posts with null author unchanged.

## Existing data

Unknown: no data, row counts or database files are in either source folder.
To be filled before any run.

## Rollback

Each step runs in one transaction per entity. Until the app goes live, roll
back by dropping the target database and restoring the backup. After go-live,
rows imported from B can be removed by `imported_from = 'B'`.

## If a step fails part-way

1. Stop. Do not re-run the migration and do not fix forward on live data.
2. Record which steps completed (each step writes its own log line).
3. Restore from the backup, or apply that step's rollback.
4. Compare row counts and checks with the numbers recorded before the run.
5. Tell the user what happened and what you propose; continue only with a new approval.

## Result

Not run (plan mode).
