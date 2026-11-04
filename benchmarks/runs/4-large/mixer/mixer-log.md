# Mixer log

Project: Unified CRM · Mode: plan (selection by auto-pick, per the operator) · Sources: A MegaCRM, B DealFlow

The decision history and integration log for this run. Add a line for every
phase, every decision and every approval. Never rewrite past lines; add a new
one that corrects them.

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | Capabilities recorded: browser, web_fetch, repository_access, external_api and network set to not-needed | both sources are local own-code folders; network, installs and running source code are not approved for this run | benchmark-operator (task instructions) |
| 2026-11-04 | recon | Scan findings: none for A (408 files) or B (1 file); no AI-instruction files; nothing to acknowledge | scan_source.py output | n/a |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-04 | recon | A MegaCRM: local folder, scanned (0 findings), indexed 408 files / 25 modules; 5 modules analysed, 20 generated gen_* modules skipped after a full-text template check of all 400 files; 4 features; coverage complete; size S | valid | CP1 |
| 2026-11-04 | recon | B DealFlow: local folder (1 file), scanned (0 findings), indexed 1 module, analysed; 2 features; coverage complete; size S | valid | CP1 |
| 2026-11-04 | extraction | Menu M01-M06 built: 1 group (pipeline: M03, M04, similar, combine); 4 unique rows (M01, M02, M05, M06); no identical, complementary, incompatible or skip rows | validate_feature_menu.py --allow-no-keep: consistent | CP2 |
| 2026-11-04 | selection | Auto-pick: keep all six rows (M01-M06); nothing dropped or deferred. M03+M04 combined into U03 (one configurable pipeline); M01->U01, M02->U02 (improve: transactional merge), M05->U04 (improve: header row, fixed export list), M06->U05 (improve: skip closed deals, dedupe) | every row is a source core-loop feature or a must; the only group (pipeline, similar) is combined; no incompatible or skip rows; no `could` rows to defer. Validator: picks consistent, 2 warnings (M03/M04 conflict to settle in phase 4) | benchmark-operator (pre-approved in task), approval A01 |
| 2026-11-04 | compatibility | 10 conflicts (1 critical, 4 high, 3 medium, 2 low) resolved per compat/resolutions.json: uuid keys with legacy ids; configurable Stage table seeded with A's stages plus 'closed' for B; User + Deal.owner_id; nullable contact_id; reminders skip closed stages and dedupe; title text; tz-aware moved_at; merge leaves moved_at alone | recommendations from check_compatibility.py plus 6 manual conflicts; dependency check: no conflicts, lodash/react declared but not imported in A; vulnerabilities not checked (no network approval) | benchmark-operator (pre-approved in task), approvals A02 (migration:deal, plan only) and A03 |
| 2026-11-04 | compatibility | check_compatibility.py --write --strict; validate_project.py --phase compatibility | both exit 0; note: A's foreign key had been written as "Contact.id" and the script expects the entity name "Contact"; corrected in A's source.json | CP4 |
| 2026-11-04 | architecture | Modular monolith (alternatives: microservices poor, service-oriented poor, event-driven partial, hybrid partial); D01 Django 5.2 + Python 3.12, D02 server-rendered templates (drop React/lodash), D03 PostgreSQL/SQLite, D04 cron command for reminders, D05 Django email backend, D06 six modules (accounts, contacts, pipeline, contact-merge, reporting, reminders), D07 uuid + legacy ids, D08 Stage table with outcome, D09 User/owner_id with admin/member and one can() check, D10 REST /api/v1; slices V1 (M01, M03, M04), V2 (M02), V3 (M05), V4 (M06) | drivers in design/architecture.md | benchmark-operator (pre-approved in task), approval A05 |
| 2026-11-04 | architecture | Rerun of check_compatibility.py after architecture.json listed fields: migration:deal gained field-level steps (contact_id, stage, title, owner_email) and migration:contact appeared (email "text unique" vs "text"; arch type corrected to "text unique"); contact re-key added to the plan; migration-plan.md updated | migration:contact approved as a plan only | benchmark-operator (pre-approved in task), approval A04 |
| 2026-11-04 | architecture | validate_artifacts.py, check_dependencies.py, check_compatibility.py --strict, validate_project.py --phase architecture | all exit 0; plan mode: run stops here; nothing installed, run, or fetched | CP5 |
