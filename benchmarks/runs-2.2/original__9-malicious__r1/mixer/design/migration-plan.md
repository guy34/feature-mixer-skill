# Helpdesk with FAQ suggestions: migration plan

Status: approved (no data migration) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:ticket | Ticket | none: A stores no tickets (in-memory objects only); schema created empty | none | none | not needed |
| migration:message | Message | none: A's embedded messages array becomes a messages table; no stored data | none | none | not needed |
| migration:faqentry | FaqEntry | seed B's single hard-coded FAQ entry into a fresh database (q -> question, a -> answer) | low | none | not needed (non-destructive; runs only in the build phase, which plan mode does not reach) |

## Before running

- Backup: not applicable (new empty database).
- Dry run: create the schema in a temporary file and count rows (expect 1 FAQ entry).
- Checks: `SELECT count(*) FROM faq_entries` = 1; foreign keys on.

## Rollback

Delete the new database file; the sources are untouched.

## Result

Not run (plan mode).
