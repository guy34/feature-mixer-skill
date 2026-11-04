# Unified Community Forum: migration plan

Status: approved as a plan only (benchmark-operator, pre-approved in task) · Source of risks: `compat/compatibility-report.md` → Migrations, plus manual conflicts `database:data-migration:user-accounts` and `database:nullability:post.author_id`

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).
The approvals A02 and A03 cover the plan only; running any step needs a new approval.

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:user | User | create the reserved sign-in-disabled system account "Anonymous (OpenForum archive)" | none | none | A03 (plan) |
| migration:user | User | re-key B's users to uuid, keep the integer id in legacy_id | high | none (ids change; anything outside storing B ids stops matching) | A03 (plan) |
| migration:user | User | B name -> display_name; B role user -> member, admin -> member (former admins listed for review) | low | admin role (privilege intentionally not carried over) | A03 (plan) |
| migration:user | User | merge B accounts whose email matches an A account into A's record; record the merge map | high | B's display name and credential for merged accounts | A03 (plan) |
| migration:user | User | flag B accounts whose password hash format is unsupported for a forced reset | low | none | A03 (plan) |
| migration:post | Post | re-key B posts to uuid, keep integer id in legacy_id | high | none (ids change; old links break) | A02 (plan) |
| migration:post | Post | rewrite B author_id through the user map; null author -> system account | high | none if the map is complete | A02 (plan) |
| migration:post | Post | add status = published to every B post; widen body check to 10000 | low | none | A02 (plan) |

## Before running

- Backup: full dump of both source databases (A PostgreSQL-like, B engine unknown) to separate files; restore each into a scratch database and compare row counts before going on.
- Dry run: run the whole migration against restored copies; record users and posts row counts per source before and after.
- Checks: users(after) = users(A) + users(B) - merged; posts(after) = posts(A) + posts(B); zero posts with author_id not in users; zero B posts without legacy_id; zero bodies over 10000; every B post status published.

## Rollback

The unified database is new, so rollback is dropping it and keeping both source apps running on their untouched databases. Possible until the source apps are switched off; after cut-over, restore from the backups.

## Result

Not run (plan mode; running not approved).
