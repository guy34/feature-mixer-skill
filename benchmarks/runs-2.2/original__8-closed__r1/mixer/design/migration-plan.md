# Unified expense app: migration plan

Status: approved (benchmark operator, pre-approved) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).

## Steps

No data migration runs. The unified database starts empty.

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:expense | Expense | none: Spendly keeps expenses only in memory; no Tallyho data is imported | none in practice (report lists high for a hypothetical import from undocumented types) | none | resolutions.json (plan: no migration) |
| migration:budget | Budget | none: no Tallyho import | as above | none | resolutions.json |
| migration:membership | Membership | none: no Tallyho import | as above | none | resolutions.json |
| migration:user | User | none: no Tallyho import | as above | none | resolutions.json |

Schema creation (Django migrations from empty, `schema.sql`) is not a data
migration but still runs only with a `migration` approval at implementation.

## Before running

- Backup: not applicable (empty database).
- Dry run: run the schema migrations on a throwaway database first.
- Checks: every table, constraint and index in `schema.sql` exists.

## Rollback

Drop the new, empty database. If a Tallyho import is added later, it needs
its own plan here: export through Tallyho's API with the user's token
(network approval), map amount and date types once known, dry run on a copy,
and row-count and sum checks.

## Result

Not run (plan mode).
