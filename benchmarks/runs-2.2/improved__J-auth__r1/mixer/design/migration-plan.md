# Unified Identity: migration plan

Status: approved (plan only) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in `project.json` → `approvals`
(action `migration`, target `migration:user`).

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:user | User | re-key A integer ids and B 'lu-n' ids to new text ids, old id kept in legacy_id | high | none (ids change) | plan approved in resolutions.json; not run |
| migration:user | User | map roles A user->editor, B member->viewer | high | none | plan approved; not run |
| migration:user | User | normalise emails; move A salt/hash to PasswordCredential, B provider/subject to Identity | low | none | plan approved; not run |

## Before running

- Backup: not applicable now; no persisted source data exists.
- Dry run: required on a copy if data is ever imported.
- Checks: user counts per source equal unified users plus linked identities; every credential and identity resolves.

## Existing data

None. Passbook, Linkup and Roster keep their records in process memory only; nothing persists between runs.

## Rollback

Not applicable while nothing runs; an import would write to a new store and leave the sources untouched.

## If a step fails part-way

1. Stop. Do not re-run the migration and do not fix forward on live data.
2. Record which steps completed (each step writes its own log line).
3. Restore from the backup, or apply that step's rollback.
4. Compare row counts and checks with the numbers recorded before the run.
5. Tell the user what happened and what you propose; continue only with a new approval.

## Result

Not run: no source data to migrate.
