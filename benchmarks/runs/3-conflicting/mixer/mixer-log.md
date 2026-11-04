# Mixer log

Project: Unified Community Forum · Mode: plan (selection by auto-pick, per operator) · Sources: A Boardly, B OpenForum

The decision history and integration log for this run. Add a line for every
phase, every decision and every approval. Never rewrite past lines; add a new
one that corrects them.

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | Mode plan; selection by auto-pick; no installs, no network, no running source code | task.md and operator instructions | benchmark-operator (pre-approved in task) |
| 2026-11-04 | recon | Capabilities: browser, web_fetch, repository_access, external_api, network recorded not-needed (both sources are local folders) | check_environment.py | - |
| 2026-11-04 | recon | Scans: A and B no findings (acknowledged). Manual note: B signs JWTs with a hard-coded literal key (scanner pattern needs 8+ chars, so it was not flagged); value not copied | security engine s3 | - |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-04 | recon | A Boardly: local dir, 3/3 files, 1/1 module analysed, 5 features, coverage complete (6 unknowns), size S. B OpenForum: local dir, 3/3 files, 1/1 module, 5 features, coverage complete (6 unknowns), size S. No capability limits affected reading. | validate_project --phase recon exit 0 | CP1 |
| 2026-11-04 | extraction | 10 menu rows (one per source feature). Groups: sign-in similar (M01,M02), read-post similar (M03,M04), create-post similar (M05,M06), post-list identical (M09,M10); unique M07; incompatible M08 | validate_feature_menu --allow-no-keep exit 0; validate_project --phase extraction exit 0 | CP2 |

## Decisions and approvals (continued)

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-04 | selection | Keep M01 (A cookie sign-in, improve) | similar sign-in group: safer http-only session, carries moderator role; B's JWT key is hard-coded with no expiry | benchmark-operator (pre-approved in task), A01 |
| 2026-11-04 | selection | Drop M02 (B JWT sign-in) | second session mechanism for the same job; must-have dropped as a duplicate, B users migrate to M01 | benchmark-operator (pre-approved in task), A01 |
| 2026-11-04 | selection | Keep M03 + M04, combine (read post) | public reading of published posts from B, status-based visibility from A | benchmark-operator (pre-approved in task), A01 |
| 2026-11-04 | selection | Keep M05 (A create, pending) | feeds the moderation queue; core loop of A | benchmark-operator (pre-approved in task), A01 |
| 2026-11-04 | selection | Drop M06 (B create, immediate publish) | contradicts "every post waits for a moderator" (conflicts with M07); must-have dropped, create capability survives via M05 | benchmark-operator (pre-approved in task), A01 |
| 2026-11-04 | selection | Keep M07 (moderation queue, improve) | unique core-loop feature of A | benchmark-operator (pre-approved in task), A01 |
| 2026-11-04 | selection | Drop M08 (anonymous posting) | incompatible with required author (M05) and sign-in; auto-pick drops incompatible rows; could return later as moderated anonymous posts | benchmark-operator (pre-approved in task), A01 |
| 2026-11-04 | selection | Keep M09, drop M10 (post list, identical) | one /posts list; neither source has a list endpoint, so rebuild | benchmark-operator (pre-approved in task), A01 |
| 2026-11-04 | selection | Merge plan U01-U05 written | every kept row in one unified feature | benchmark-operator (pre-approved in task), A01 |
| 2026-11-04 | recon (correction) | Fixed foreign_keys.references in both source.json files from "User.id" to "User" (entity name) after the analysis reported spurious missing-entity FKs | format error, no fact changed | - |
| 2026-11-04 | compatibility | 17 conflicts (1 critical, 12 high incl. 4 manual, 4 medium), all decided in compat/resolutions.json: uuid keys + legacy_id; one cookie session; roles member/moderator (B admin -> member, listed for review); public read of published posts; pre-moderate new posts, B posts migrate as published; limit 10000; legacy anonymous posts -> reserved system account; same-email user merge; B token code not reused | check_compatibility --strict exit 0 | benchmark-operator (pre-approved in task), A04 |
| 2026-11-04 | compatibility | Destructive migrations migration:post and migration:user approved as plans only (design/migration-plan.md); nothing run | operator: plans only | benchmark-operator (pre-approved in task), A02, A03 |
| 2026-11-04 | architecture | D01-D09: modular monolith (alternatives microservices, service-oriented, event-driven poor; hybrid partial); Node 22 + Express 4, PostgreSQL 16 uuid + legacy_id, EJS pages, http-only cookie session, argon2id, roles member/moderator (B admin -> member), REST + one error shape, limit 10000, pre-moderation | see design/architecture.md | benchmark-operator (pre-approved in task), A05 |
| 2026-11-04 | architecture | Reran check_compatibility with architecture.json: migration:post gains step "B author_id integer to uuid" (already in migration-plan.md, approved as plan A02); no new conflicts. check_dependencies: no conflicts; vulnerabilities not checked (no audit run: network/installs not approved) | - | - |
| 2026-11-04 | architecture | Plan mode: run stops here. Nothing installed, run, migrated or deployed | mode plan | - |
| 2026-11-04 | architecture | prd.md, architecture.md/.json, schema.sql, api.md, migration-plan.md written | validate_artifacts exit 0; validate_project --phase architecture (see next line) | CP5 |
| 2026-11-04 | architecture | validate_project --phase architecture | exit 0, 3 warnings (low-confidence A-F05/B-F05/M09: no list endpoint in either source) | CP5 |
