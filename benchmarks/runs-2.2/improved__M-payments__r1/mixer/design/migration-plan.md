# Unified Billing: migration plan

Status: approved as a plan (benchmark operator, pre-approved) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).

**No migration is run in this project.** All three sources keep their
orders and subscriptions only as in-memory Python dicts (observed: A-E01,
B-E01, C-E01); there is no database and no existing data to move. The
unified module starts empty. The steps below are the mapping that would
apply if the user later imports data from the source apps. Their high
risk comes from narrowing types, and running them would need a new
`migration` approval.

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:order | Order | add amount_cents, status, charge_id, attempt_key, refund_state, refund_id | low | none | plan: resolutions.json |
| migration:order | Order | A.Order.amount (number, unit unknown) to amount_cents (integer minor units) | high | fractional values; wrong unit if A stored major units | plan: resolutions.json; running: not approved, none to run |
| migration:order | Order | A.Order.paid (boolean) to status: true becomes 'paid' unless C's status says cancelled or refunded; false becomes 'pending' | low | none | plan: resolutions.json |
| migration:renewal | Renewal | B.Subscription.customer (any) to customer (text) | high | non-text customer values would be rejected | plan: resolutions.json; running: not approved, none to run |
| migration:renewal | Renewal | B.Subscription.price (number, unit unknown) to price_cents (integer) | high | fractional values; wrong unit | plan: resolutions.json; running: not approved, none to run |

## Before running

- Backup: export every source record to JSON and restore it into a scratch copy once to prove the export works.
- Dry run: convert the copy, counting records before and after, and listing every rejected value (non-integer amount, non-text customer) instead of dropping it.
- Checks: count of orders before = after; sum of amounts (in cents) before = after; every A paid=true order maps to paid, cancelled or refunded.

## Existing data

None. The sources have no persistence (in-memory dicts only), so there are no tables and no row counts.

## Rollback

The unified store is new and separate; rolling back means discarding it. The source data is never changed.

## If a step fails part-way

1. Stop. Do not re-run the migration and do not fix forward on live data.
2. Record which steps completed (each step writes its own log line).
3. Restore from the backup, or apply that step's rollback.
4. Compare row counts and checks with the numbers recorded before the run.
5. Tell the user what happened and what you propose; continue only with a new approval.

Prefer steps that run inside one transaction; split the rest into steps that are each safe to re-run.

## Result

Not run: there is no source data to migrate (2026-11-05).
