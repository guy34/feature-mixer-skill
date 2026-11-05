# <Product name>: migration plan

Status: draft | approved · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:user | User | re-key B's users to uuid | high | none (ids change) | A04 |

## Before running

- Backup: <how, where, verified restore>
- Dry run: <on a copy of real data, with row counts before and after>
- Checks: <queries proving nothing was lost: counts, sums, orphaned rows>

## Existing data

<Which databases hold real data, row counts per table before anything runs, and the restore you tested.>

## Rollback

<How to undo each step, and until when it is possible.>

## If a step fails part-way

1. Stop. Do not re-run the migration and do not fix forward on live data.
2. Record which steps completed (each step writes its own log line).
3. Restore from the backup, or apply that step's rollback.
4. Compare row counts and checks with the numbers recorded before the run.
5. Tell the user what happened and what you propose; continue only with a new approval.

Prefer steps that run inside one transaction; split the rest into steps that are each safe to re-run.

## Result

<Filled after running: date, approval id, counts, checks passed.>
