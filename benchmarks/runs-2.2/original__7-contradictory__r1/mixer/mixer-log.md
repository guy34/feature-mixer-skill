# Mixer log

Project: Shelfie + Readr unified reading app · Mode: plan (selection: auto-pick) · Sources: A Shelfie, B Readr

The decision history and integration log for this run. Add a row for every
decision and approval to the first table, and a row for every phase, slice
and run to the second (insert rows at the end of the right table, not at the
end of the file). Never rewrite past rows; add a new one that corrects them.

Benchmark note: no user is present in this run. A benchmark operator pre-approved Claude's
recommendation at every phase checkpoint (selection, compatibility, architecture) and the
auto-pick selection mode named in task.md. Those approvals are recorded below with
"benchmark operator" as the approver. Not approved: installing packages, network access,
running any code from sources/.

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | Mode plan, selection auto-pick, both sources own-code (code_reuse allowed) | Stated in task.md ("Both are my own code") | benchmark operator (pre-approved) |
| 2026-11-04 | setup | Where Shelfie's docs and code disagree, the code is the truth; doc claims are recorded as documented evidence and flagged as contradicted | task.md: "Shelfie's documentation is old; trust what the apps actually do" | user instruction in task.md |
| 2026-11-04 | selection | Auto-pick: keep M01 library, M02 Shelfie ratings, M04 JSON export, M05 reading lists; drop M03 Readr ratings | M01/M05 are each app's core loop and what the user asked for; M02 and M03 are identical 1-5 star ratings, M02 kept as more complete (HTTP + DB CHECK), M03 dropped as duplicate (its capability survives in U02); M04 is a low-risk should. No could rows, no deferrals. Merge plan U01-U04 | benchmark operator (pre-approved; auto-pick per task.md) |
| 2026-11-04 | compatibility | application:rule:rating-scale (high): 1-5 integer stars, as both codebases do; Shelfie's documented 1-10 'score' not built | User said trust the code; Shelfie's handler, DB CHECK and Readr all agree on 1-5 | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | application:session:session (high): email+password accounts, server-side sessions via http-only signed cookie | Neither source had working auth; multi-person app needs it | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | application:authorization-model:model (high): per-user ownership, one can() check on every route and query | Neither source had any authorization | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Medium/low decided: JSON export (documented CSV not built); ignore documented 3 services/PostgreSQL; one Book entity; rating unique per user+book with upsert and commits; list entries unique with FKs on; /api/v1 prefix; documented SESSION_SECRET replaces unused SHELFIE_SESSION_SECRET | Code is the truth; fix both apps' integrity gaps | Claude (no approval needed; included in summary approved by benchmark operator) |
| 2026-11-04 | compatibility | migration:book low risk; no source data imported in this plan | Existence of real data in shelfie.db/readr.db unknown | benchmark operator (pre-approved) |
| 2026-11-04 | architecture | D01 design from code where Shelfie's docs disagree; D02 Python stdlib only; D03 SQLite WAL + FKs; D04 modular monolith (microservices/SOA/event-driven/hybrid poor fit; the documented 3-service design was never built) | Drivers: one owner, small scope, strong consistency, no installs | benchmark operator (pre-approved) |
| 2026-11-04 | architecture | D05 email/password + scrypt + server-side cookie sessions; D06 one role 'reader' with ownership via can(); D07 REST /api/v1 with one error shape | Neither source had auth | benchmark operator (pre-approved) |
| 2026-11-04 | architecture | D08 ratings 1-5 upsert; D09 JSON export one row per book, no CSV; D10 server-rendered HTML; D11 no source data import (an import would be high risk: id collisions, ratings collapse); D12 rebuild everything | Code is the truth; fix integrity gaps | benchmark operator (pre-approved) |
| 2026-11-04 | architecture | Slices V1 (M01, M02 + accounts), V2 (M05), V3 (M04); plan mode: run stops here, nothing built | mode plan per task.md | benchmark operator (pre-approved) |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | check_environment.py; browser, web_fetch, repository_access, external_api, network recorded as not-needed (local inputs only, network not approved) | capabilities.json written | - |
| 2026-11-04 | recon | A Shelfie: scanned (0 findings), indexed, read 4 of 4 files (app.py, README.md, openapi.yaml, docs/architecture.md); 2 of 2 modules analysed; no capability limits (local files) | 3 features (A-F01..A-F03), coverage complete, size S. Docs contradict code on export format/path (CSV vs JSON), rating scale (1-10 vs 1-5), database (PostgreSQL vs SQLite), architecture (3 services vs one process) and API prefix (/api/v1 vs /api); undocumented required env var SHELFIE_SESSION_SECRET (unused). Code treated as truth; doc claims kept as contradicted documented evidence. No auth, no commit. | CP1 |
| 2026-11-04 | recon | B Readr: scanned (0 findings), indexed, read 1 of 1 file (readr.py); 1 of 1 module analysed | 2 features (B-F01, B-F02), coverage complete, size S. No create/read functions, no entry point, no commit, no auth. | CP1 |
| 2026-11-04 | extraction | Built feature-menu.csv from 5 source features | 5 rows: group ratings (identical: M02 A, M03 B); unique: M01 library (A), M04 export (A), M05 reading lists (B). Strategies: improve x4, reject x1. The documented-only CSV export is not a menu row (never implemented). validate_feature_menu.py --allow-no-keep: consistent | CP2 |
| 2026-11-04 | selection | validate_feature_menu.py --set keep/drop; merge-plan.json written | keep 4, drop 1, consistent | CP3 |
| 2026-11-04 | compatibility | check_compatibility.py --write --strict (aliases List->ReadingList, ListBook->ReadingListItem; 7 manual conflicts from docs-vs-code and integrity review) | 10 conflicts (3 high, 5 medium, 2 low), all resolved; 1 migration (Book, low) | CP4 |
| 2026-11-04 | architecture | prd.md, architecture.md/.json, schema.sql, api.md, migration-plan.md; validate_artifacts, check_dependencies, check_compatibility --strict (rerun with architecture), validate_project --phase architecture | all pass; 7 modules, 6 entities, 19 endpoints, 3 slices | CP5 |
