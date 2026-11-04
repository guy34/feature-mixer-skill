# Unified Notes: migration plan

Status: approved as a plan only (not for execution) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, targets `migration:note`, `migration:tag`, `migration:notetag`).
The benchmark operator approved this plan as a plan (A02); no `migration`
action approval exists, so nothing may be run yet.

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:note | Note | create unified `notes` table (uuid id, legacy_id, title, body, pinned, created_at, updated_at) | none | none | plan only (A02) |
| migration:note | Note | copy A's notes: new uuid per row, A's integer id into legacy_id, pinned = false, updated_at = created_at | high (re-key) | none; old integer ids stop matching outside the app | plan only (A02) |
| migration:tag | Tag | copy A's tags with new uuid ids, legacy_id = old id; names case-folded unique | high (re-key) | case-variant tag names merge into one | plan only (A02) |
| migration:notetag | NoteTag | rewrite A's note_tags pairs to the new uuids via legacy_id; drop duplicate pairs | high (re-key) | duplicate pairs (no information); a pair whose legacy id has no match would be rejected and reported | plan only (A02) |
| migration:note | Note | import B from a JSON dump of GET /api/notes if supplied: keep uuid, content → body, pinned, updatedAt → updated_at, created_at = updatedAt | low | none (B keeps no stored data otherwise) | plan only (A02) |
| migration:note | Tag | map B labels (B.Note.labels is dropped from Note; its values move to Tag/NoteTag) to tags: trim, case-fold, de-duplicate, link | low | duplicate and case-variant labels collapse | plan only (A02) |

## Before running

- Backup: copy A's SQLite file to `backups/quicknotes-<date>.db` and the B JSON dump to `backups/`; verify by opening the copy and counting rows.
- Dry run: run the migration into a fresh database file from the copies; record row counts of notes, tags and note_tags before and after.
- Checks: notes(A)+notes(B) = unified notes; every legacy_id unique; no orphaned note_tags; every distinct case-folded label/tag appears once; titles and bodies byte-identical (compare SHA-256 per note).

## Rollback

The migration writes a new database file and never edits A's file, so rollback
is: stop the unified app and point it back at nothing (or the previous unified
file). Possible until users start writing new notes to the unified database.

## Result

Not run (plan mode; running a migration not approved).
