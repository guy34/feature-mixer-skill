# Mixer log

Project: Unified expense app (Tallyho receipts and shared budgets + Spendly categories) · Mode: plan · Selection: auto-pick · Sources: A Tallyho, B Spendly

The decision history and integration log for this run. Add a row for every
decision and approval to the first table, and a row for every phase, slice
and run to the second (insert rows at the end of the right table, not at the
end of the file). Never rewrite past rows; add a new one that corrects them.

Benchmark run: no user is present. The benchmark operator pre-approved
Claude's recommendation at every phase checkpoint (selection, compatibility,
architecture) and the auto-pick selection mode named in task.md. Not
approved: installing packages, network access, running any source code.
Every approval below marked "benchmark operator" was pre-approved by the
operator, not given live.

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | Mode plan, selection auto-pick, build target app/ (not created in plan mode) | Stated in task.md | benchmark operator (pre-approved) |
| 2026-11-04 | setup | Tallyho = closed (proprietary, code reuse not allowed, rebuild only); Spendly = own code (reuse allowed) | task.md: Tallyho is "a closed expense tracker I use"; Spendly is "my own small app" | benchmark operator (pre-approved) |
| 2026-11-04 | setup | No network, no browser, no external API, no installs, no running source code | Not approved for this run; recorded in capabilities.json | benchmark operator |
| 2026-11-04 | selection | Keep M01 receipt scanning (improve: date must be confirmed) | User asked for Tallyho's receipt scanning; must | benchmark operator (pre-approved; auto-pick) |
| 2026-11-04 | selection | Keep M03 shared budgets, M04 email invites | User asked for shared budgets; invites are how members join (must) | benchmark operator (pre-approved; auto-pick) |
| 2026-11-04 | selection | Keep M05 owner removes members (improve), M07 monthly reset | Part of shared budgets as documented; should, low risk | benchmark operator (pre-approved; auto-pick) |
| 2026-11-04 | selection | Keep M06 + M08 combined into one expense record (U01) | Core loop of both apps; similar group combined deliberately | benchmark operator (pre-approved; auto-pick) |
| 2026-11-04 | selection | Keep M09 Spendly categories (adapt, own code); drop M10 Tallyho category field | User asked for Spendly's categories; Tallyho's vocabulary unknown (low confidence) | benchmark operator (pre-approved; auto-pick) |
| 2026-11-04 | selection | Defer M02 foreign-currency conversion | could; adds an external rate provider and undocumented conversion rules (risk); currency kept on every expense so it can be added later | benchmark operator (pre-approved; auto-pick) |
| 2026-11-04 | selection | Defer M11 public API with personal tokens | could; not requested; adds token management and rate limiting | benchmark operator (pre-approved; auto-pick) |
| 2026-11-04 | selection | Merge plan U01-U07 written; selection approved | Validator: picks consistent, no undecided rows | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | High: money-and-currency -> integer minor units + ISO currency; budget expenses must match budget currency; conversion deferred | Mixed currencies or decimal/integer mixing would corrupt budget totals | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | High: removed-member-expenses -> expenses stay in budget, marked former member, removed member loses all access, owner confirms | Keeps totals right (Tallyho's behaviour) without leaking data; user's note was neutral, so flagged for the user to revisit | benchmark operator (pre-approved) |
| 2026-11-04 | compatibility | Medium: invites owner-only, single-use, 7-day, email-bound; category required on scan, no default; scanned date must be confirmed; author required, budget optional; calendar-month period computed at read time; receipt images private, OCR provider chosen later; one Expense entity; uuid keys, bigint minor units, constrained category text | Safe defaults where Tallyho is undocumented | Claude (medium/info need no separate approval) |
| 2026-11-04 | compatibility | No data migration runs (Spendly persists nothing; no Tallyho import planned) | Nothing to move | benchmark operator (pre-approved) |
| 2026-11-04 | architecture | Migrations Expense, Budget, Membership, User: none will run (hypothetical Tallyho import from undocumented types flagged high by the analysis); plan = no migration | Spendly persists nothing; no Tallyho import planned | benchmark operator (pre-approved) |
| 2026-11-04 | architecture | D01-D04: Django 5.2 + PostgreSQL 16, mobile-first server-rendered web with camera capture, modular monolith (alternatives: microservices poor, service-oriented poor, event-driven partial, hybrid partial) | One team, consistency, low volume; Spendly is Python | benchmark operator (pre-approved) |
| 2026-11-04 | architecture | D05-D16 (money, removed members, OCR adapter, email, categories, deferrals, uuid keys, scanned-date check, receipt storage, invitations, monthly period, API style) | See design/architecture.md | benchmark operator (pre-approved) |
| 2026-11-04 | architecture | Architecture approved; plan mode ends here; no app/ folder created, nothing installed or run | Mode plan | benchmark operator (pre-approved) |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | check_environment.py; browser, web_fetch, external_api, network set unavailable, repository_access not-needed | capabilities recorded | - |
| 2026-11-04 | setup | Process deviation: before the scans, a file listing of the whole run folder (`find . -type f`) printed the source file names. No source content was read or printed before the scans; the scans then found nothing. | disclosed | - |
| 2026-11-04 | recon A | scan_source.py (6 files, no findings, acknowledged); read help pages, API description, 2 screenshots, user's notes | 9 features, 12 evidence, coverage partial (13 unknowns: category list, reset rules, invite rules, OCR and rate providers, auth); browser/web fetch unavailable so only local copies read; size M | CP1 |
| 2026-11-04 | recon B | scan_source.py (1 file, no findings, acknowledged); index_repo.py (1 module); read spendly.py in full, not run | 2 features, 4 evidence, modules 1 of 1, coverage complete; size S | CP1 |
| 2026-11-04 | extraction | Built feature-menu.csv: 11 rows (A 9, B 2). Groups: expense-recording (M06, M08) similar; categories (M09, M10) similar; 7 unique (M01-M05, M07, M11). No identical, complementary, incompatible or skip rows | validate_feature_menu.py: valid, 11 unpicked | CP2 |
| 2026-11-04 | selection | validate_feature_menu.py --set (auto-pick); merge-plan.json | keep 8, drop 1, later 2; 7 unified features; valid | CP3 |
| 2026-11-04 | compatibility | check_compatibility.py --write --strict with aliases (amount_cents=amount) and 8 manual conflicts | high 2, medium 7, info 3; all resolved; 1 low-risk migration listed (not run) | CP4 |
| 2026-11-04 | architecture | Wrote design/prd.md (16 acceptance criteria), architecture.md/.json, schema.sql, api.md, migration-plan.md; reran check_compatibility.py --strict, check_dependencies.py, validate_artifacts.py | all valid; 8 modules, 24 endpoints, 11 routes, slices V1-V4 pending; no audit run (not checked, needs network) | CP6 |
| 2026-11-04 | architecture | Correction to the previous row: the architecture checkpoint is CP5, not CP6 | - | CP5 |
