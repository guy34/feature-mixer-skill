# Shared expenses with receipt scanning: migration plan

Status: approved (plan only; benchmark operator, pre-approved) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:expense | Expense | none: no source data is moved (Spendly keeps expenses only in memory; Tallyho data is not imported) | none | none | plan approved in compat/resolutions.json |
| migration:budget | Budget | none: Tallyho budgets are not imported | none | none | plan approved |
| migration:budgetmember | BudgetMember | none: Tallyho memberships are not imported | none | none | plan approved |
| migration:user | User | none: new sign-ups only | none | none | decided |

The checker flags these as high-risk because the types and units differ (Tallyho decimal major units and
unknown id types vs bigint minor units and uuid). Those risks only apply if data is ever imported.

## Before running

- Backup: not applicable (empty database; schema created from the first migration).
- Dry run: if a Tallyho import is added later, run it on a copy with row counts and per-budget sums before and after.
- Checks: per currency, sum(amount_minor) / 10^exponent equals the source sum; every expense has a budget and a valid category.

## Existing data

None found. Spendly's `EXPENSES` list is in memory (`spendly.py:2`); the user should confirm they keep no
Spendly data elsewhere. Tallyho data stays in Tallyho.

## Rollback

The first schema migration on an empty database is rolled back by dropping the database. A future import
would run in one transaction per budget.

## If a step fails part-way

1. Stop. Do not re-run the migration and do not fix forward on live data.
2. Record which steps completed (each step writes its own log line).
3. Restore from the backup, or apply that step's rollback.
4. Compare row counts and checks with the numbers recorded before the run.
5. Tell the user what happened and what you propose; continue only with a new approval.

## Result

Not run (plan mode).
