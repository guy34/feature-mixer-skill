# Unified CRM: migration plan

Status: approved as a plan only (approval A02, benchmark-operator, pre-approved in task) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).
A02 approves this written plan only; executing it needs a new approval.
Note: neither source has a working database (A's `table()` helper is a stub;
B's db is injected), so where existing data lives is unknown. This plan
applies only if the user has real MegaCRM or DealFlow data to import.

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:deal | Deal | re-key A's integer ids and B's ids (type unknown) to uuid; keep legacy_source + legacy_id | high | none (ids change; anything outside storing old ids stops matching) | A02 (plan only) |
| migration:deal | Deal | A.stage text and B.stage (type unknown) -> stage_id uuid FK: A 1:1 to seeded stages; B new->lead, contacted->qualified, negotiating->proposal, closed->closed (outcome unspecified); any other B value becomes an extra configured stage | high | flagged by the script as stage; mitigated: every distinct value maps to a Stage row, the dry run fails if any deal has no stage_id | A02 (plan only) |
| migration:deal | Deal | A.contact_id integer -> uuid through the Contact legacy_id map | high | flagged as contact_id; mitigated: dry run fails on any contact_id with no mapped contact | A02 + A04 (plan only) |
| migration:deal | Deal | B.title (type unknown) -> text not null | high | flagged as title; B rows with empty or non-string titles are listed by the dry run for the user, never silently dropped | A02 (plan only) |
| migration:deal | Deal | B.owner_email (type unknown) -> owner_id uuid: one User per distinct lower-cased email; A's deals get the default owner the user names | high | flagged as owner_email; the value is kept on User.email; invalid emails are listed by the dry run | A02 (plan only) |
| migration:deal | Deal | add value_cents (B: null), currency (DEFAULT_CURRENCY), moved_at (A: import time; B naive values read as UTC), contact_id (B: null) | low | none | A02 (plan only) |
| migration:contact | Contact | re-key A's integer ids to uuid, keep legacy_source='A' + legacy_id; email stays text unique (case-insensitive check reports clashes before import) | high | none (ids change); case-only email duplicates are listed for the user to merge | A04 (plan only) |

## Before running

- Backup: copy each source database to a dated file; verify the copy opens and row counts match.
- Dry run: run the import into a fresh copy of the unified database; report rows per entity before and after, the stage mapping counts, and every row the casts flagged.
- Checks: count(deals A)+count(deals B) = count(unified deals); sum(value_cents) for A's deals unchanged; no deal with a contact_id that has no contact; every deal has an owner_id and a stage_id; every legacy_id is unique per legacy_source.

## Rollback

The import writes only to a new unified database, so rollback is discarding
it; the source databases are never modified. Possible until the team starts
writing to the unified database; after that, reverse mapping via legacy_id.

## Result

Not run (plan mode).
