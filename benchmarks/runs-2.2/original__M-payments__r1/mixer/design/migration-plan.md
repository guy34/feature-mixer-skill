# Unified Billing: migration plan

Status: approved as a plan (benchmark operator, pre-approved) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs. No source app persists data (all three keep orders and subscriptions as
in-memory dicts passed in by the caller), so there is no data to move. The mapping is recorded so that
any future import of Billfold/Orderly order dicts is done the same way.

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:order | Order | A.amount (number) -> amount_cents (integer cents) | high | non-integer amounts rejected | plan only (resolutions.json) |
| migration:order | Order | A.paid (bool) -> status (True=paid, False=pending) | high | none if C.status is also present (C wins) | plan only (resolutions.json) |

## Before running

- Backup: not applicable (no persisted data).
- Dry run: not applicable.
- Checks: count of orders and sum of amount_cents before and after an import.

## Rollback

Not applicable; nothing is run.

## Result

Not run (nothing to migrate).
