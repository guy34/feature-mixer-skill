# Mixer log

Project: Unified Community Forum · Mode: plan (selection: manual) · Sources: A Boardly, B OpenForum

The decision history and integration log for this run. Add a row for every
decision and approval to the first table, and a row for every phase, slice
and run to the second (insert rows at the end of the right table, not at the
end of the file). Never rewrite past rows; add a new one that corrects them.

Benchmark note: no user is present in this run. A benchmark operator
pre-approved Claude's recommendation at every phase checkpoint (selection,
compatibility, architecture) and the selection mode named in task.md
(manual, the default). Each such approval below is recorded as given by
"benchmark operator" and is marked "pre-approved by the operator". Not
approved, and not done: installing packages, network access, running any
code from sources/. Plan mode builds and runs nothing.

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | Mode plan, selection manual; A Boardly own-code (reuse allowed); B OpenForum open-source, MIT licence read in sources/openforum/LICENSE (reuse allowed, keep notice) | task.md names both sources, rights and mode | task.md (user request) |
| 2026-11-04 | selection | Keep M01 (A cookie-session sign-in, improved) and drop M02 (B JWT) | one session mechanism; B's token has a hard-coded signing key, no expiry, no algorithms list | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | selection | Keep and combine M03 + M04 into one create-post (U02): signed-in author, starts pending, one length limit decided at compatibility | both apps' core loop; one posting path | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | selection | Keep M05 pre-moderation (A); drop M06 instant publishing (B) | incompatible pair; review before publishing protects a community forum and is the user's own app's model | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | selection | Defer M07 anonymous posting (B) to later | needs abuse protection neither source has; A requires an author | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | selection | Keep and combine M08 + M09 into one read rule (U04); keep M10 post list, drop duplicate M11 | public reading of published posts (B) with A's moderation status; neither source has a list endpoint, rebuild one | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | selection | Phase approval recorded with approvals.py approve-phase (fingerprint of picks and merge plan) | selection validator passed; mode manual | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | compatibility | Primary keys (critical): uuid for User and Post; B integer ids kept in legacy_id with imported_from = 'B' | A's type; merged data needs one key type | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | compatibility | Session: http-only secure SameSite=Lax cookie session, no JWT; nothing from B's token code or hard-coded key reused | safe default for web; B's key is a scan finding | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | compatibility | max_post_length = 10000 for everyone (B's value), handler 422 plus check constraint | keeps every existing post from both apps valid; every post is reviewed anyway | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | compatibility | Read rule: published posts public; pending/rejected only to author and moderators, else 404 | combines B's public reading with A's moderation; closes A's leak of pending posts | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | compatibility | Roles {member, moderator}; A:member->member, A:moderator->moderator, B:user->member, B:admin->member | B admin has no observed powers; no escalation; promotion by hand | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | compatibility | Imported B posts: status published, imported_from = 'B'; null author only on imported B rows (check constraint) | they were already public; anonymous posting stays deferred for new posts | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | compatibility | created_at as UTC timestamptz; B's naive timestamps converted only after the user states B's server time zone (open) | B's time zone is unknown; not guessed | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | compatibility | Routes /login and /posts one screen each; one GET /api/v1/posts/{id} and one POST /api/v1/posts; User and Post merged (B name -> display_name, aliases.json) | one route and endpoint per job | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | compatibility | migration:post and migration:user: plans approved only; running either needs a separate migration approval; whether real data exists is unknown | high-risk re-keying | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | compatibility | Phase approval recorded with approvals.py approve-phase | check_compatibility --strict exit 0; validate_project compatibility valid | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | selection | Re-approved selection after a status-only change: menu compatibility M03, M04, M08, M09 conflict -> adaptable; merge-plan U02, U04 compatibility -> resolved. No picks, unified features or behaviour changed; no later phase affected | compatibility gate asks for the kept rows' compatibility column to be updated; validate_project.py flagged the fingerprint change | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | architecture | D01 modular monolith (alternatives: microservices poor, service-oriented poor, event-driven partial, hybrid poor) | one team, consistency between moderation and visibility, modest scale | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | architecture | D02-D04 Node.js 22 + Express 4, PostgreSQL 16, React 18 SPA (Vite); D05 cookie sessions in PostgreSQL; D06 argon2id; D07 REST /api/v1 with one error shape and cursor pagination; D08 read rule only in platform can(); D09 env configuration; D10 no B code copied, A moderation handlers adapted | see design/architecture.md | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | architecture | Slices V1 (M01, M03, M04, M05, M08, M09) and V2 (M10); 15 acceptance criteria AC01-AC15 incl. journey AC13 | core loop first | benchmark operator (pre-approved by the operator) |
| 2026-11-04 | architecture | Phase approval recorded with approvals.py approve-phase. Plan mode: run ends; implementation and integration stay pending | task.md mode plan | benchmark operator (pre-approved by the operator) |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | check_environment.py; Claude set browser, web_fetch, repository_access, external_api to not-needed and network to unavailable (not approved) | capabilities.json written | - |
| 2026-11-04 | setup | Process note: an initial `find` over the run folder listed the file names (names only, no contents) under sources/ before scan_source.py ran. No source content was read or printed before the scans | disclosed deviation from "scan before listing" | - |
| 2026-11-04 | recon | A Boardly: scan (0 findings), index (1 module, 3 files), read 3 of 3 files | 5 features (A-F01..A-F05), coverage partial (7 unknowns: db layer, session middleware, password storage, list endpoint), size S | CP1 |
| 2026-11-04 | recon | B OpenForum: scan (2 medium weak-secret: hard-coded JWT signing key in api.py:6 and :14, value not copied; no high findings, no AI-instruction text), index (1 module, 3 files), read 3 of 3 files; MIT licence confirmed | 6 features (B-F01..B-F06), coverage partial (7 unknowns: framework, db layer, PyJWT version, admin powers), size S. Capability limits: none affected (local folders only) | CP1 |
| 2026-11-04 | extraction | Built feature-menu.csv: 11 rows from 11 source features. Groups: sign-in similar (M01 A, M02 B); posting similar (M03 A, M04 B); publication incompatible (M05 A vs M06 B); reading similar (M08 A, M09 B); post-list identical (M10 A, M11 B); unique: M07 (B anonymous posting) | validate_feature_menu.py --allow-no-keep: consistent | CP2 |
| 2026-11-04 | selection | validate_feature_menu.py --set keep/drop/later; merge-plan.json U01-U05; validate_project.py --phase selection | keep 7, drop 3, later 1; picks consistent; 5 warnings (4 compat conflicts to resolve, M10 low-confidence evidence) | CP3 |
| 2026-11-04 | compatibility | check_compatibility.py --write --strict (aliases.json, 3 manual conflicts, resolutions.json); check_dependencies.py (no manifests; no audit run: network not approved, so vulnerabilities not checked) | 2 critical, 18 high, 6 medium, all resolved; 2 high-risk migration plans approved; suggestion: B imports jwt without declaring it | CP4 |
| 2026-11-04 | architecture | Wrote prd.md, architecture.md, architecture.json, schema.sql, api.md, migration-plan.md; reran check_compatibility (no dropped fields: B ids kept in legacy_id), validate_artifacts, check_dependencies, validate_project --phase architecture | valid; nothing built, installed or run (plan mode) | CP5 |
