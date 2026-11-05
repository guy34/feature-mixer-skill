# Shelfie + Readr unified reading app: migration plan

Status: approved (plan: no source data is imported) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).

## Steps

The unified app starts from an empty database (`design/schema.sql`). No data moves from `shelfie.db` or
`readr.db` in this plan (decision D11): neither file is in the source folders, and whether either holds real data
is unknown. Also, both apps never commit their writes, so any file may hold only empty tables.

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:book | Book | create empty table (adds author, owner_id) | none | none | not needed (no data moved) |
| migration:rating | Rating | create empty table | none | none | not needed |
| migration:readinglist | ReadingList | create empty table | none | none | not needed |
| migration:readinglistitem | ReadingListItem | create empty table | none | none | not needed |

### If the user later wants to import existing data

`check_compatibility.py` rates these steps low because the field types match. By reasoning they are **high risk**
and would each need their own `migration` approval and a dry run:

| Step | Risk | What could be lost or changed |
| --- | --- | --- |
| Import A and B books into one table | high | A and B both number books from 1, so ids collide: B's books must be re-keyed and B's list entries rewritten; the same title in both apps becomes two books unless deduplicated by a rule the user picks |
| Import ratings | high | both apps append many rating rows per book; the unified model keeps one per user per book, so all but one value (e.g. the last row) is discarded. Readr's table has no CHECK, so out-of-range values would be rejected |
| Import list entries | low/high | duplicate (list, book) rows collapse to one; entries pointing at missing lists or books are dropped |
| Assign an owner | low | every imported row goes to one user account the user names |

## Before running

- Backup: copy both source `.db` files and the new database; verify the copies open.
- Dry run: on copies, with row counts per table before and after.
- Checks: book counts per source, ratings collapsed count, list entries dropped count, zero orphaned rows.

## Rollback

The import only writes to the new database; restore its backup. Source files are never modified.

## Result

Not run (plan mode; no import planned).
