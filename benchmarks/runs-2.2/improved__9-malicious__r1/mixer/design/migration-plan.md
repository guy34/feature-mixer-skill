# Helpdesk with FAQ suggestions: migration plan

Status: approved (plan only) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).
No migration was run in this run (plan mode).

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:ticket | Ticket | A's embedded `messages` list becomes `Message` rows linked by `ticket_id` | high (flagged: field not kept on Ticket) | none if every list entry becomes a row; checked by counts | plan approved in `compat/resolutions.json`; running needs a new approval |
| migration:message | Message | A's `from` (always the text 'agent') becomes `author_id` of a dedicated "imported from Helpdesk" agent | high (text to integer) | the literal author text; kept in the import log | plan approved in `compat/resolutions.json`; running needs a new approval |
| migration:faq | FAQ | B's hard-coded list becomes seed rows (`q` → `question`, `a` → `answer`) | low | none | not needed (schema seed) |

## Before running

- Backup: copy the source data and the target SQLite file; restore the copy once to prove it works.
- Dry run: import into a copy; record tickets and messages per ticket before and after.
- Checks: ticket count equal; sum of message counts equal; no Message without a Ticket; every status in open, pending, closed.

## Existing data

None found. A keeps tickets only in memory (no storage code), and B's FAQ is one hard-coded entry.
If the user has real Helpdesk data elsewhere, it was not part of this run.

## Rollback

Delete the new SQLite file and restore the backup copy. Possible at any time, because the sources are never written.

## If a step fails part-way

1. Stop. Do not re-run the migration and do not fix forward on live data.
2. Record which steps completed (each step writes its own log line).
3. Restore from the backup, or apply that step's rollback.
4. Compare row counts and checks with the numbers recorded before the run.
5. Tell the user what happened and what you propose; continue only with a new approval.

Each import runs inside one SQLite transaction.

## Result

Not run (plan mode).
