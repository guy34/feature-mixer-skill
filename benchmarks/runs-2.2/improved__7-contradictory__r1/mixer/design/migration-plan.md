# Shelfie + Readr reading app: migration plan

Status: approved (plan only; benchmark operator, pre-approved) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).
Plan mode: nothing has been run.

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:book | Book | create the unified table with author (nullable) and owner_id, on a new empty database | low | none (no existing data is moved) | compat/resolutions.json (plan) |

## Before running

- Backup: not applicable for a fresh database. If an import is ever planned, copy shelfie.db and readr.db first and verify the copies open.
- Dry run: not applicable now; an import would be dry-run on copies with row counts per table before and after.
- Checks: schema created; PRAGMA foreign_key_check returns nothing.

## Existing data

Unknown. No shelfie.db or readr.db was provided, and the sources' code never commits writes (inferred), so they may hold little or nothing. Importing both would collide on integer book ids (re-key Readr's books and rewrite its ratings and list_books rows) and need an owner for every row: a high-risk migration that needs its own plan and approval (compat decision database:data-migration:existing-data-import).

## Rollback

Delete the new database file; the sources' files are never touched.

## If a step fails part-way

1. Stop. Do not re-run the migration and do not fix forward on live data.
2. Record which steps completed (each step writes its own log line).
3. Restore from the backup, or apply that step's rollback.
4. Compare row counts and checks with the numbers recorded before the run.
5. Tell the user what happened and what you propose; continue only with a new approval.

## Result

Not run (plan mode).
