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

## Rollback

<How to undo each step, and until when it is possible.>

## Result

<Filled after running: date, approval id, counts, checks passed.>
