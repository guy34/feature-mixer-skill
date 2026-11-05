# Mixer log

Project: Unified Billing · Mode: full, selection auto-pick · Sources: A Billfold, B Subscribe, C Orderly

The decision history and integration log for this run. Add a row for every
decision and approval to the first table, and a row for every phase, slice
and run to the second (insert rows at the end of the right table, not at the
end of the file). Never rewrite past rows; add a new one that corrects them.

No user is present in this run. A benchmark operator pre-approved Claude's
recommendation at every phase checkpoint (selection, compatibility,
architecture) and pre-approved running the new app's own test suite in
`app/`. Each of those approvals is recorded below as "benchmark operator
(pre-approved)". The decisions written in `task.md` are the user's. Not
approved: installing any package, network access, running any code from
`sources/`, deployment.

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | Mode full, selection auto-pick, build in `app/`, module `app/unified/billing.py` with the API in task.md | Stated in the run instructions and task.md | user (task.md) / benchmark operator |
| 2026-11-04 | setup | Mock gateway only (`gateway.py`); never charge twice, never apply a webhook twice, consistent orders on gateway timeout or failed write, refund a cancelled paid order exactly once | Requirements written in task.md | user (task.md) |
| 2026-11-04 | setup | Rights for A, B, C recorded as own-code with code_reuse `unknown`: task.md states no rights and no source has a licence file. Nothing is copied; every feature is rebuilt | Rights could not be determined; rebuilding is safe under any rights | Claude (recorded as unknown, not guessed) |
| 2026-11-05 | selection | Auto-pick: keep M01-M07 (all 7); drop none, defer none. M01, M02, M04, M05 kept as each source's core loop, improved (A's double-charge and double-webhook flaws, C's cancel without refund); M03 kept as B's core loop (should), improved with a per-period duplicate check; M06 ledger and M07 create/look up orders kept because the user asked for them in task.md. Merge plan U01-U07, one per row (no merge groups) | Auto-pick rules: every source's core loop and every must; data integrity first | benchmark operator (pre-approved; approvals.py approve-phase) |
| 2026-11-05 | compatibility | 10 conflicts resolved (resolutions.json): critical charge-idempotency (required key, one gateway key per order written before the call, no charge for a paid order); high gateway-timeout (retry once with the same key, else stay pending and reconcile), webhook-idempotency (event-id dedupe in the same write), cancel-paid-order (refund once, end refunded, idempotent cancel), order-payment-state (single status field, transition table), write-failure (one atomic write per change, intent before gateway calls); medium renewal-duplicates (one order per subscription per period), duplicate-entity order (merged), amount-units (integer cents); info primary key (app-generated 'ord_<n>'). Migration:order risk low (fields added; no real data exists to move) | User requirements in task.md; data integrity first | benchmark operator (pre-approved; approvals.py approve-phase) |
| 2026-11-05 | compatibility (change) | Added plan approvals for migration:order (A.Order.amount number to integer cents) and migration:renewal (B customer any to text, price to integer cents), found once architecture.json listed fields; no source data exists, so nothing runs (design/migration-plan.md). Fixed a field-type label (charge_id 'text, nullable' to 'text') that the checker read as a narrowing. Compatibility re-approved | Changed after approval: the skill requires showing and re-approving | benchmark operator (pre-approved; approvals.py approve-phase) |
| 2026-11-05 | architecture | Modular monolith (alternatives: microservices poor, event-driven partial, service-oriented poor, hybrid poor); Python stdlib in one file app/unified/billing.py with sections store, gateway-adapter, orders, ledger, payments, refunds, webhooks, subscriptions, facade; entities Order (A+C), LedgerEntry, IdempotencyKey, WebhookEvent (new), Renewal (B); no auth/HTTP/UI (D09); slices V1 core loop (M07, M04, M01, M06), V2 webhooks (M02), V3 cancel+refund (M05), V4 renewals (M03); decisions D01-D09 | Drivers: strong consistency and exactly-once money movement in one small library | benchmark operator (pre-approved; approvals.py approve-phase) |
| 2026-11-05 | implementation | Run the new app's unittest suite in app/ (approval A01, scoped to cwd app, unittest start tests, 8h) | Running the new app's own tests is pre-approved for this run | benchmark operator (pre-approved; approvals.py grant) |
| 2026-11-05 | architecture (change) | Slice status V1-V4 set to done in architecture.json; validate_project reported the design as changed after approval, so the phase was re-approved. No design decision changed | Status-only change required by the implementation engine | benchmark operator (pre-approved; approvals.py approve-phase) |
| 2026-11-05 | selection (change) | merge-plan.json validation set to verified for U01-U07 and tests lists filled from the verified run; picks unchanged. Selection re-approved | Required by the validation engine at the end of integration | benchmark operator (pre-approved; approvals.py approve-phase) |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | check_environment.py; browser, web_fetch, repository_access, external_api not needed (local sources, mock gateway); network unavailable (not approved) | capabilities recorded | - |
| 2026-11-04 | recon | Scanned (no findings, acknowledged), indexed and read A sources/billfold (1/1 module, 1 file), B sources/subscribe (1/1), C sources/orderly (1/1), plus the user's description in task.md; no capability limits affected these local inputs | A: 2 features, B: 1, C: 2; coverage complete for all; size S each; rights unknown (no licence) | CP1 |
| 2026-11-04 | extraction | Built feature-menu.csv from the 3 source reports | 7 rows: 5 from sources (A 2, B 1, C 2), 2 new requested by the user in task.md (M06 ledger, M07 create/look up orders); all unique (no merge groups: the features share the Order entity but have different jobs); strategies improve 5, rebuild 2; validate_feature_menu passes | CP2 |
| 2026-11-05 | selection | validate_feature_menu.py --set keep M01-M07; merge-plan.json U01-U07; validate_project --phase selection | valid; approval recorded with fingerprint | CP3 |
| 2026-11-05 | compatibility | check_compatibility.py --write --strict with 8 manual conflicts | critical 1, high 5, medium 3, info 1, all resolved; validate_project passes | CP4 |
| 2026-11-05 | architecture | prd.md (AC01-AC10), architecture.md/.json, migration-plan.md; validate_artifacts, check_dependencies, check_compatibility --strict, validate_project --phase architecture | all pass | CP5 |
| 2026-11-05 | implementation V1-V4 | Built app/unified/billing.py (one file, sections per module) and app/tests/test_billing.py (26 tests tagged M01-M07, AC01-AC10, 2 journey tests). Deviation: all four slices were written before the first run and proven in one full-suite run instead of one run per slice. run_tests.py --approval A01 | run 20261105T130401391086Z-067232: verdict passed, 26/26; verify_tests: 7 features verified | CP6 |
| 2026-11-05 | integration | verify_tests.py (26 passed, 7 features verified), --update-baseline, --rerun under A01 (run 20261105T130431319163Z-e1909c reproduced 26/26); added Not testable here (real gateway, refund failure path, real database, multi-process concurrency) | integration valid | CP7 |
