# Mixer log

Project: Team Hub · Mode: full · Workspace format 3 (v2.1) · Sources: A TaskBoard (own code), B Approvals (MIT), C Pulse (closed: public docs and API spec)

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-04 | recon | Study C from its public docs and API spec only | Closed product: behaviour only, nothing copied | - |
| 2026-11-04 | extraction | 17 menu rows: 3 groups (sign-in identical, comments similar, roles similar, notifications complementary), 1 incompatible (M16), 1 skip (M17) | From 17 source features | - |
| 2026-11-04 | selection | Keep M01 M04 M05 M07 M08 M09 M10 M11 M12 M13 M14; drop M02 M06 M16; later M03 M15; skip M17 | Recommendations accepted; Google sign-in and digest deferred | user |
| 2026-11-04 | selection | Combine M08 and M09 into one role model | Similar groups kept together must be combined | user |
| 2026-11-04 | selection | Combine M10, M11, M12 into one notification engine | Complementary channels of one capability | user |
| 2026-11-04 | compatibility | 20 conflicts (1 critical, 11 high, 5 medium, 3 low) decided; see compat/resolutions.json | Critical: user primary keys uuid vs integer | user |
| 2026-11-04 | compatibility | Manual conflict: block closing a task with a pending approval | Found by reasoning, not by the script | user |
| 2026-11-04 | compatibility | Destructive migration migration:user approved, dry run first | Re-keys B's users | user |
| 2026-11-04 | architecture | D01 to D07; 7 modules; 4 slices | See design/architecture.md | user |
| 2026-11-04 | recon (v2.1) | Capabilities: browser, web fetch, repository access and external APIs not needed (all sources local) | Recorded with check_environment.py | - |
| 2026-11-04 | recon (v2.1) | Security scans of A, B and C: no findings | scan_source.py | - |
| 2026-11-04 | recon (v2.1) | A and B indexed; all 4 modules of each analysed, with summaries | index_repo.py | - |
| 2026-11-04 | selection (v2.1) | Merge plan: 8 unified features from 11 kept rows (U02 combines roles, U03 combines three notification channels) | No feature is built twice | user |
| 2026-11-04 | architecture (v2.1) | D08 modular monolith; microservices, event-driven, hybrid and service-oriented compared | One team, strong consistency, low load | user |
| 2026-11-04 | compatibility (v2.1) | migration:approval found to drop B's request title; plan: one task per request carries it (A03) | Field-level data-loss check | user |
| 2026-11-04 | integration (v2.1) | Approval A01 to run the app's own test suite | Tests run Team Hub code only | user |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-04 | recon | Read A (sources/taskboard), B (sources/approvals), C (docs + openapi.yaml) | A complete, B complete, C partial (4 unknowns) | CP1 |
| 2026-11-04 | extraction | validate_feature_menu.py --allow-no-keep | valid | CP2 |
| 2026-11-04 | selection | validate_project.py --phase selection | valid | CP3 |
| 2026-11-04 | compatibility | check_compatibility.py --write --strict | 0 blocking | CP4 |
| 2026-11-04 | architecture | validate_project.py --phase architecture | valid | CP5 |
| 2026-11-04 | V1 | accounts, tasks | tests pass | CP6 (cp6-v1) |
| 2026-11-04 | V2 | notification engine | tests pass | CP6 (cp6-v2) |
| 2026-11-04 | V3 | approvals, comments | 1 failure: PUT returned an HTML 501, not the JSON 405; added the PUT handler; 1 test expectation corrected (reply notification goes to the parent's author) | CP6 (cp6-v3) |
| 2026-11-04 | V4 | dashboard | tests pass | CP6 (cp6-v4) |
| 2026-11-04 | integration | run_integration.py | 23 of 23 passed; all 11 kept features verified | CP7 |
| 2026-11-04 | integration (v2.1) | run_tests.py --unittest (approval A01), verify_tests.py --update-baseline | 23 of 23 passed with recorded evidence; 11 features and 10 acceptance criteria verified; baseline saved | CP7 |
| - | deployment | not requested | pending | - |
