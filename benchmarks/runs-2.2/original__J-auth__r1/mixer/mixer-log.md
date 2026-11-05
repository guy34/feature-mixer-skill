# Mixer log

Project: Unified Identity · Mode: full, selection auto-pick · Sources: A Passbook, B Linkup, C Roster

The decision history and integration log for this run. Add a row for every
decision and approval to the first table, and a row for every phase, slice
and run to the second (insert rows at the end of the right table, not at the
end of the file). Never rewrite past rows; add a new one that corrects them.

No user is present in this run. A benchmark operator pre-approved Claude's
recommendation at every phase checkpoint (selection, compatibility,
architecture) and approved running the new app's own test suite in `app/`.
Rows approved that way say "benchmark operator (pre-approved)". The
decisions written in `task.md` (account linking rule, role mapping, role
change rules) are the user's own and are recorded as "user".

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-05 | setup | Mode full, selection auto-pick, build in `app/`, standard library only | Stated in the task and by the operator | user / benchmark operator (pre-approved) |
| 2026-11-05 | setup | B Linkup `code_reuse` = not-allowed although the task calls it MIT | No licence file in `sources/linkup`; the engine says no licence file means not-allowed. B's behaviour is rebuilt, no code copied. Adding the MIT LICENSE file would allow reuse | Claude (rule) |
| 2026-11-05 | setup | Account linking: a federated sign-in joins an existing account only when the provider says the email is verified; otherwise a separate account | User decision in task.md | user |
| 2026-11-05 | setup | Role mapping: A `user` -> `editor`, B `member` -> `viewer`, C `viewer`/`editor`/`admin` unchanged; only an admin can change roles; nobody can raise their own role | User decision in task.md | user |
| 2026-11-05 | selection | Auto-pick: keep M01, M02, M03 (sign-in group, complementary -> combine into U01) | Core loop of A and B, all must; one identity store for both sign-in methods | benchmark operator (pre-approved) |
| 2026-11-05 | selection | Auto-pick: keep M04 (U02) and M05 (U03, improve); nothing dropped or deferred | Core loop of C, must; M05 needs M04 | benchmark operator (pre-approved) |
| 2026-11-05 | compatibility | Account linking only on email_verified True, else separate account (critical) | User decision in task.md | user |
| 2026-11-05 | compatibility | Role mapping A user->editor, B member->viewer, C unchanged; one RBAC model; admin-only role changes; no self-raise (high x3) | User decision in task.md | user |
| 2026-11-05 | compatibility | uuid text ids for one User entity (critical PK + high field type); Identity table for (provider, subject); duplicate registration rejected; actor from session and role validated; both sign-in methods offered | Safety and data integrity; recommended defaults | benchmark operator (pre-approved) |
| 2026-11-05 | compatibility | migration:user plan approved (re-key with legacy_id); nothing to run: sources keep data in memory only | No persisted data exists | benchmark operator (pre-approved) |
| 2026-11-05 | architecture | D01-D10 (modular monolith in app/unified/identity.py; stdlib; uuid ids with Identity and Session; verified-email join; role mapping; set_role rules; bootstrap only while no admin; expiring server-side tokens; PBKDF2 310k; duplicates rejected); slices V1 (M01-M03), V2 (M04-M05) | See architecture.md | benchmark operator (pre-approved); D04, D05, D06 core rules: user |
| 2026-11-05 | implementation | A01: run the new app's own unittest suite in app/ | Needed to prove each feature | benchmark operator (pre-approved) |
| 2026-11-05 | deployment | Not deployed | Not requested; deployment not approved | - |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-05 | setup | check_environment.py; browser, web_fetch, repository_access, external_api set to not-needed (local sources only), network unavailable (not approved) | capabilities.json written; docker available for isolation, not needed (no source code is run) | - |
| 2026-11-05 | recon | scan_source.py on A, B, C; index_repo.py on A, B, C | 1 file each, no findings (0 high); 1 module each | - |
| 2026-11-05 | recon | A Passbook: sources/passbook (local, 1 file, scanned, indexed) | 1/1 modules analysed, 2 features, coverage complete, size S; no scan findings | CP1 |
| 2026-11-05 | recon | B Linkup: sources/linkup (local, 1 file, scanned, indexed) | 1/1 modules analysed, 1 feature, coverage partial (OAuth exchange, session mechanism and licence file unknown), size S; no scan findings | CP1 |
| 2026-11-05 | recon | C Roster: sources/roster (local, 1 file, scanned, indexed) | 1/1 modules analysed, 2 features, coverage complete, size S; no scan findings; no AI-instruction text in any source | CP1 |
| 2026-11-05 | extraction | feature-menu.csv built; validate_feature_menu.py --allow-no-keep | 5 rows: group sign-in (complementary) M01, M02, M03; unique M04, M05; validator clean | CP2 |
| 2026-11-05 | selection | validate_feature_menu.py --set keep; merge-plan.json U01-U03; validate_project.py --phase selection | 5 kept, 0 dropped, 0 deferred; valid | CP3 |
| 2026-11-05 | compatibility | check_compatibility.py --write --strict; validate_project.py --phase compatibility | 2 critical, 7 high, 2 medium: all resolved; exit 0 | CP4 |
| 2026-11-05 | architecture | validate_artifacts.py, check_dependencies.py, check_compatibility.py --strict, validate_project.py --phase architecture | all valid; no dependency conflicts; vulnerability audit not run (no packages, no network) | CP5 |
| 2026-11-05 | implementation V1+V2 | app/unified/identity.py (one required module, so both slices were written together) and app/tests/test_identity.py; run_tests.py --unittest tests --approval A01 (run 20261105T130716734720Z) | 33 passed of 33; V1 (M01-M03) and V2 (M04-M05) done; nothing harder than planned | CP6 |
| 2026-11-05 | integration | verify_tests.py; verify_tests.py --rerun --update-baseline (under A01); merge-plan validation set to verified; validate_project.py --phase integration | 33 of 33 passed and verified; M01-M05 and U01-U03 verified; baseline saved; not testable here: real OAuth provider, persistence, load, data migration | CP7 |
