# Mixer log

Project: Unified Notes · Mode: plan (selection by auto-pick, per operator) · Sources: A QuickNotes, B Jotter

The decision history and integration log for this run. Add a line for every
phase, every decision and every approval. Never rewrite past lines; add a new
one that corrects them.

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | Mode plan; auto-pick for selection; build target `app/` (not built in plan mode) | task.md and operator instructions | benchmark-operator (pre-approved in task) |
| 2026-11-04 | setup | Not approved: installing anything, network access, running source code | operator instructions | benchmark-operator (pre-approved in task) |
| 2026-11-04 | recon | Both sources recorded as own-code, code_reuse allowed (no licence files; user states they are own code) | task.md | user (task.md) |
| 2026-11-04 | selection | Keep M01+M02 (combine into U01 Notes: A's persistent SQL + B's status codes, pinning order) | similar group, both core loop; combine required to keep both | benchmark-operator (pre-approved in task) |
| 2026-11-04 | selection | Keep M03 (A shared tags), drop M04 (B free-text labels) | similar; A's model is unique, reusable, filterable; labels migrate to tags | benchmark-operator (pre-approved in task) |
| 2026-11-04 | selection | Keep M05 (A title+body search), drop M06 (B title-only) | similar; A is a superset | benchmark-operator (pre-approved in task) |
| 2026-11-04 | selection | Keep M07 preview (A), M08 pin (B), M09 export (B), all with improvements | unique, core loop of their source; low risk | benchmark-operator (pre-approved in task) |
| 2026-11-04 | selection | Merge plan U01-U06 approved (A01) | validate_project --phase selection exit 0 | benchmark-operator (pre-approved in task) |
| 2026-11-04 | compatibility | database:primary-key:note (critical): uuid for Note and Tag, A ids in legacy_id | merged data, matches B's public ids | benchmark-operator (pre-approved in task) |
| 2026-11-04 | compatibility | application:api:note-update-semantics (high): whitelist title/body | B's Object.assign allows overwriting id/pinned | benchmark-operator (pre-approved in task) |
| 2026-11-04 | compatibility | application:business-rule:notes.list.order (high): pinned first, then created_at desc | combines A's order and B's pinning | benchmark-operator (pre-approved in task) |
| 2026-11-04 | compatibility | medium/low: one Note table; Python runtime; snake_case; labels->tags; B has no stored data; slug+id export names | safe defaults | benchmark-operator (pre-approved in task) |
| 2026-11-04 | compatibility | migration:note (high risk, destructive re-key) approved as a PLAN ONLY (A02); execution not approved | operator instructions | benchmark-operator (pre-approved in task) |
| 2026-11-04 | architecture | D01 Python+Flask, D02 SQLite, D03 static HTML+JS, D04 Markdown+nh3, D05 local single user no auth, D06 modular monolith, D07 REST /api/v1, D08 uuid+legacy_id / list order / whitelisted update | see design/architecture.md | benchmark-operator (pre-approved in task) |
| 2026-11-04 | architecture | Migration plans migration:note, migration:tag, migration:notetag approved as plans only (A02) | rerun of check_compatibility after architecture.json listed new high-risk re-key steps | benchmark-operator (pre-approved in task) |
| 2026-11-04 | architecture | Architecture approved (A04); plan mode stops here | validate_project --phase architecture exit 0 | benchmark-operator (pre-approved in task) |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | check_environment.py; browser, web_fetch, repository_access, external_api, network set not-needed (local folders only, network not approved) | capabilities.json written | - |
| 2026-11-04 | recon | A QuickNotes: local folder, 3 of 3 files read, 1 of 1 module analysed, scan: 0 findings; 4 features; coverage complete (4 unknowns: absent db helper, no frontend); size S | valid | CP1 |
| 2026-11-04 | recon | B Jotter: local folder, 3 of 3 files read, 1 of 1 module analysed, scan: 0 findings; 5 features; coverage complete (4 unknowns: bootstrap, no frontend, export zip vs JSON); size S | valid | CP1 |
| 2026-11-04 | extraction | Menu built: 9 rows from 9 source features; groups notes-crud (M01,M02 similar), tagging (M03,M04 similar), search (M05,M06 similar); unique M07, M08, M09 | validate_feature_menu.py --allow-no-keep: consistent | CP2 |
| 2026-11-04 | selection | Auto-pick applied with validate_feature_menu.py --set; 7 keep, 2 drop, 0 later | consistent | CP3 |
| 2026-11-04 | compatibility | check_compatibility.py --write --strict: 9 conflicts (1 critical, 2 high, 4 medium, 2 low) all resolved; no audit run (network not approved: vulnerabilities not checked) | exit 0 | CP4 |
| 2026-11-04 | architecture | validate_artifacts, check_dependencies (no audit: network not approved; vulnerabilities not checked), validate_project --phase architecture | all exit 0 | CP5 |
