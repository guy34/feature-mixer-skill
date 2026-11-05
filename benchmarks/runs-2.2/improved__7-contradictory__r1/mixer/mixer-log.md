# Mixer log

Project: Shelfie + Readr reading app · Mode: plan (selection: auto-pick) · Sources: A Shelfie, B Readr

The decision history and integration log for this run. Add a row for every
decision and approval to the first table, and a row for every phase, slice
and run to the second (insert rows at the end of the right table, not at the
end of the file). Never rewrite past rows; add a new one that corrects them.

Benchmark run: no user is present. A benchmark operator pre-approved Claude's
recommendation at every phase checkpoint (selection, compatibility,
architecture) and the auto-pick selection mode named in task.md. Every phase
approval below is recorded with "benchmark operator" as the approver and was
pre-approved by the operator, not given live. Not approved: installing
packages, network access, running any code from sources/. Plan mode: nothing
is built or tested.

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | Mode plan, selection auto-pick; both sources own-code, code reuse allowed | Stated in task.md ("Both are my own code"; "Mode: plan. Selection: auto-pick.") | user (task.md) |
| 2026-11-04 | recon | Where Shelfie's docs (README, docs/architecture.md, openapi.yaml) disagree with app.py, the code wins | task.md: "Shelfie's documentation is old; trust what the apps actually do"; engines/reconnaissance.md section 5 | user (task.md) |
| 2026-11-04 | selection | Auto-pick: keep M01 Book library (A, must, improve: add/edit/remove books, per-person), keep M02 Rate 1-5 stars (A, must, improve: one rating per person per book), keep M04 JSON export (A, could, adapt: low risk, works on kept data), keep M05 Reading lists (B, must, improve: full list lifecycle) | Core loop the user named (library, ratings, lists) plus Shelfie's small export; Shelfie's rating chosen over Readr's identical one because it also has an API and a DB CHECK | benchmark operator (auto-pick mode in task.md; pre-approved by the operator) |
| 2026-11-04 | selection | Drop M03 Readr rating (must) | Identical to M02 (1-5, appended); keep one per identical group, the more complete | benchmark operator (pre-approved) |
| 2026-11-04 | selection | Not on the menu: CSV export, 1-10 rating scale, /api/v1 paths, PostgreSQL, three-service gateway | Documentation-only claims in Shelfie contradicted by its code (A-C01..A-C08); the user said to trust what the apps do | user (task.md) |
| 2026-11-04 | selection | Phase approval recorded with approvals.py approve-phase (fingerprint fba7727a3f6e...) | Pre-approved by the benchmark operator; no live user | benchmark operator |
| 2026-11-04 | compatibility | Authorization: owner-only model (every row has owner_id; one permission check; others' ids answer 404); no roles | Neither source has auth; the user wants "people" to keep libraries; Shelfie's documented gateway auth does not exist in code | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Session: email + password (stdlib scrypt), server-side session, http-only SameSite=Lax cookie; SHELFIE_SESSION_SECRET dropped | Safer default; nothing to carry over (Shelfie's secret is unused) | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Book: A and B Book are the same thing; one Book (title required, author optional, owner_id) | Same table shape and use in both (A-E01, B-E03) | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Existing data: start empty; any import of shelfie.db/readr.db (id re-keying) needs its own plan and approval | No database files provided; whether real data exists is unknown | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Rating 1-5 stars (not docs' 1-10 score); one rating per person per book; JSON export (not docs' CSV); /api/... paths (not /api/v1); commit every write and enable foreign keys | Code wins over Shelfie's old docs; source append and no-commit behaviour fixed | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Phase approval recorded with approvals.py approve-phase (fingerprint 6028fde021bd...) | Pre-approved by the benchmark operator | benchmark operator |
| 2026-11-04 | architecture | D01 Python stdlib + SQLite; D02 static page + vanilla JS; D03 modular monolith (alternatives microservices/service-oriented/event-driven/hybrid rated poor); D04 accounts + owner-only access; D05 1-5 stars one per person per book; D06 JSON export, no CSV; D07 /api REST, one error shape, no paging; D08 commit writes, FKs on, cascades; D09 empty DB, no import; D10 export route before {id} | Built from what the sources' code does; Shelfie's outdated docs (PostgreSQL, 3 services, /api/v1, CSV, 1-10) not used | benchmark operator (pre-approved) |
| 2026-11-04 | architecture | Phase approval recorded with approvals.py approve-phase | Pre-approved by the benchmark operator; plan mode ends here | benchmark operator |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | check_environment.py: terminal, python, docker available; network unavailable (not approved); browser, web_fetch, repository_access, external_api not-needed (local sources only) | capabilities.json written | - |
| 2026-11-04 | setup | Process note: a `find` of the run folder at session start printed source file *names* (not contents) before scan_source.py ran, contrary to "nothing from a source opened before its scan". No contents were read before the scans; both scans found nothing | recorded for honesty | - |
| 2026-11-04 | recon | scan_source.py on A and B (0 findings each, acknowledged); index_repo.py (A 4 files/2 modules, B 1 file/1 module); read every file | A Shelfie: 3 features, 18 evidence, 8 doc-vs-code contradictions (CSV vs JSON export, 1-10 vs 1-5, score vs stars, /api/v1 vs /api, PostgreSQL vs SQLite, 3 services vs 1 process, gateway auth vs none), modules 2/2, coverage complete, size S. B Readr: 2 features, 9 evidence, 0 contradictions, modules 1/1, coverage complete, size S. No code run (not approved); persistence (no commit) only inferred | CP1 |
| 2026-11-04 | extraction | feature-menu.csv: 5 rows | group rating (identical, 2 rows: M02 A, M03 B); unique: M01, M04, M05; validator clean | CP2 |
| 2026-11-04 | selection | validate_feature_menu.py --set (auto-pick), merge-plan.json U01-U04 | keep 4, drop 1; picks consistent; validate_project selection valid | CP3 |
| 2026-11-04 | compatibility | check_compatibility.py --write --strict with 6 manual conflicts; check_dependencies.py | 10 conflicts (high 4, medium 5, low 1) all resolved; migration Book low risk on a fresh DB; no dependency conflicts (no packages); vulnerabilities not checked (no packages, no network) | CP4 |
| 2026-11-04 | architecture | prd.md, architecture.md/.json, schema.sql, api.md, migration-plan.md; validate_artifacts, check_compatibility --strict, check_dependencies | all valid; 7 modules (no cycles), 6 entities, 19 endpoints, 4 slices V1-V4; migrations listed for Book (low, approved plan), Rating/ReadingList/ListBook (low, "merge rows" steps not applicable: D09 starts empty, nothing moved) | CP5 |
| 2026-11-04 | end of plan mode | - | Nothing built or tested; implementation and integration left pending; no source code run, nothing installed, no network | CP5 |
