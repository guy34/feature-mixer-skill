# Team Hub: migration plan

Status: approved (A02, A03) · Source of risks: `compat/compatibility-report.md` → Migrations

The example starts from an empty database, so nothing here has been run.
The plan applies only if real TaskBoard (A) or Approvals (B) data is
imported. Nothing runs without the approvals recorded in
`project.json` → `approvals`.

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:user | User | re-key B's integer user ids to uuid; keep the old id in `legacy_id`; rewrite B's foreign keys | high | B's numeric ids (kept in `legacy_id`) | A02 |
| migration:user | User | copy B's `full_name` into `name` | low | none | A02 |
| migration:approval | Approval | re-key B's requests, requester and approver ids to uuid through the user mapping | high | B's numeric ids (mapping kept in an import log) | A03 |
| migration:approval | Approval | B's request `title` is not a field of Approval: create one task per request with that title and link the approval to it | high | none if the step runs; the title otherwise | A03 |

## Before running

- Backup: dump A's and B's databases; restore the dumps into a scratch
  database and confirm row counts match.
- Dry run: run the import against copies; compare counts of users, requests,
  comments and outbox rows before and after.
- Checks: every B request has exactly one linked task with the same title;
  no approval or comment points at a missing user; every `legacy_id` is
  unique.

## Rollback

The import writes to a new Team Hub database only. Until the old apps are
switched off, rollback is deleting that database and importing again.

## Result

Not run: the example uses an empty database.
