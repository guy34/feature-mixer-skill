# Mixer log

Project: Expense app (Tallyho x Spendly) · Mode: plan (selection: auto-pick) · Sources: A Tallyho (closed), B Spendly (own code)

The decision history and integration log for this run. Add a row for every
decision and approval to the first table, and a row for every phase, slice
and run to the second (insert rows at the end of the right table, not at the
end of the file). Never rewrite past rows; add a new one that corrects them.

Benchmark run: no user is present. A benchmark operator pre-approved Claude's recommendation at every phase
checkpoint (selection, compatibility, architecture) and the auto-pick selection mode named in task.md. Every
approval below recorded as "benchmark operator" was pre-approved by the operator, not given live. Not approved:
installing packages, network access, running any code from sources/.

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-04 | recon | Capabilities: browser, web_fetch, external_api and network unavailable (network not approved); repository_access not needed | Recorded from the session's real limits; Tallyho's live product, website and the user's account cannot be inspected | n/a (fact) |
| 2026-11-04 | recon | Tallyho (A) closed, code_reuse not-allowed; Spendly (B) own code, code_reuse allowed | task.md: Tallyho is a closed product, Spendly is the user's own app | n/a (from task) |
| 2026-11-04 | recon | The user's notes (my-notes.md) recorded as documented (user-reported), not observed | Claude did not see that behaviour; only the screenshots are observed | n/a |
| 2026-11-04 | selection | Keep M01 receipt scanning, M03 shared budgets, M04 invites, M09 Spendly categories | Requested by the user (core of each source's slice); invites are how members join a shared budget | benchmark operator (pre-approved) |
| 2026-11-04 | selection | Keep M05 and M06 combined into one expense record (U01) | similar group expense-entry: Tallyho has merchant/currency/date, Spendly has integer cents, validated category and note; one record avoids two entry paths | benchmark operator (pre-approved) |
| 2026-11-04 | selection | Keep M02 currency conversion, M07 member removal, M08 monthly reset (should) | Part of the receipt and shared-budget behaviour the user asked for; low added risk | benchmark operator (pre-approved) |
| 2026-11-04 | selection | Drop M10 Tallyho category field | similar alternative to M09; the user asked for Spendly's categories and Tallyho's values are unknown | benchmark operator (pre-approved) |
| 2026-11-04 | selection | Defer M11 public API with personal access tokens (later) | could, not requested, adds a second credential type | benchmark operator (pre-approved) |
| 2026-11-04 | selection | Merge plan U01-U08 approved (approvals.py approve-phase, fingerprint stored) | auto-pick selection named in task.md is the selection approval; pre-approved by the benchmark operator | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Authorization: one budget-membership model (owner, member); personal budget per user for solo use; one can_access check (AC05) | resolves application:authorization-model (high) | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Sessions: http-only Secure SameSite=Lax cookie sessions; no personal access tokens (M11 deferred) (AC09) | resolves application:session (high) | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Tenancy: budget is the tenant boundary, budget_id on Expense, BudgetMember, Invitation (AC05) | resolves application:tenancy-model (high) | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Currency: convert to the budget's currency, keep original amount, currency, rate and rate date (AC04) | resolves conversion-target-currency (high): home-currency totals would differ per member | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Scanned expenses must get a category on the review screen, no default (AC03) | resolves scanned-expense-category (high): Tallyho scan sets none, Spendly requires one | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Removed member loses access at once; their expenses stay and count (AC07) | resolves access-after-member-removal (high): keeps Tallyho's user-reported behaviour, closes the unknown access gap | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Money: integer minor units + ISO currency; decimal input parsed by currency exponent; > 0 (AC10) | resolves expense.amount field-type and units (high) | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | One Expense entity; uuid key; hard delete by adder or owner; currency/date required with form defaults; monthly period = calendar month in budget tz (AC08) | resolves entity-meaning (high) and 4 medium + 1 info conflicts | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | migration:expense plan: no data migrated (Spendly stores nothing; Tallyho import out of scope); any future migration needs its own approval | flagged destructive by the checker (unit/type change) | benchmark operator (pre-approved) |
| 2026-11-04 | selection | Re-approved selection after the compatibility column of M02, M05, M06 and merge-plan status of U01, U04 changed to adaptable/resolved; picks unchanged | validate_project.py reported the selection files changed after approval | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | After the architecture draft the checker found User without a tenant key (critical) and destructive migrations for Budget and BudgetMember: User marked shared (D11); migration:budget, migration:budgetmember plans approved as "no data migrated"; migration:user decided (new sign-ups only). Compatibility re-approved | a person belongs to several budgets; no source data is moved | benchmark operator (pre-approved) |
| 2026-11-04 | architecture | D01 Python 3.12 + Django 5; D02 PostgreSQL, bigint minor units + currency; D03 mobile-first server-rendered web with camera capture; D04 private object storage, 90-day retention for receipt images | see architecture.md | benchmark operator (pre-approved) |
| 2026-11-04 | architecture | D05 modular monolith (alternatives: microservices poor, service-oriented poor, event-driven partial, hybrid partial) with OCR, FX and email adapters | one team, strong consistency, low volume; external services faked in tests | benchmark operator (pre-approved) |
| 2026-11-04 | architecture | D06 roles owner/member + personal budget + one can_access; D07 convert to budget currency; D08 scan review flags date, requires category; D09 no deployment, no migration; D10 REST /api/v1, one error shape; D11 User shared across budgets | compatibility decisions and the user's notes | benchmark operator (pre-approved) |
| 2026-11-04 | architecture | Slices V1 (M05, M06, M09) -> V2 (M01) -> V3 (M03, M04) -> V4 (M07) -> V5 (M08) -> V6 (M02) approved; plan mode ends here | core loop first, then musts, then shoulds | benchmark operator (pre-approved) |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-04 | recon | check_environment.py; scan_source.py on both sources (A: 6 files, B: 1 file, no findings; acknowledged) | ok | |
| 2026-11-04 | recon | A Tallyho: help pages, API description, 2 screenshots, user's notes. No browser/web fetch. 9 features (A-F01..F09), 12 evidence, coverage partial (14 unknowns), size M | valid | CP1 |
| 2026-11-04 | recon | B Spendly: local folder, indexed (1 module of 1 analysed, 1 file read). 2 features (B-F01..F02), coverage complete, size S. Nothing run | valid | CP1 |
| 2026-11-04 | extraction | Menu M01-M11: groups expense-entry (M05, M06: similar), categories (M09, M10: similar); 7 unique rows (M01-M04, M07, M08, M11). Strategies: combine 2, improve 2, adapt 1, rebuild 5, reject 1 | valid | CP2 |
| 2026-11-04 | selection | validate_feature_menu.py, validate_project.py --phase selection | keep 9, drop 1, later 1; valid | CP3 |
| 2026-11-04 | compatibility | check_compatibility.py --write --strict; check_dependencies.py (no packages; vulnerabilities not checked, no audit) | 9 high, 4 medium, 1 info: all resolved; no open conflicts | CP4 |
| 2026-11-04 | architecture | validate_artifacts.py, check_dependencies.py, check_compatibility.py --strict, validate_project.py --phase architecture; wrote prd.md, architecture.md/.json, schema.sql, api.md, migration-plan.md | valid; 0 open conflicts | CP5 |
| 2026-11-04 | plan end | Plan mode: implementation and integration left pending. Nothing built, nothing run, no tests | - | - |
