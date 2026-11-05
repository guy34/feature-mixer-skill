# Mixer log

Project: Unified Billing (Scenario M) · Mode: full · Selection: auto-pick · Sources: A Billfold, B Subscribe, C Orderly

The decision history and integration log for this run. Add a row for every
decision and approval to the first table, and a row for every phase, slice
and run to the second (insert rows at the end of the right table, not at the
end of the file). Never rewrite past rows; add a new one that corrects them.

No user is present in this run. A benchmark operator pre-approved Claude's recommendation at every
phase checkpoint (selection, compatibility, architecture) and pre-approved running the new app's own
test suite in app/. Not approved: installing packages, network access, running any source code,
deployment. The decisions written in task.md are the user's.

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-05 | setup | Mode full, selection auto-pick; build in app/, module at app/unified/billing.py; mock gateway (gateway.py) only | stated in the run instructions and task.md | user (task.md) / benchmark operator |
| 2026-11-05 | recon | Capabilities: browser, web_fetch, repository_access, external_api not-needed (all inputs local); network unavailable (not approved) | recorded with check_environment.py | n/a |
| 2026-11-05 | recon | All three sources treated as own-code, code_reuse allowed (no licence file; supplied by the user as their own apps for this task) | rights rule: own code may be reused | user (task.md) |
| 2026-11-05 | selection | Auto-pick: keep M01 (C order lifecycle), M02 (A charge), M03 (A webhooks), M04 (C cancel), M05 (B renewal); drop none; defer none | each is its source's core loop and all are must; no identical/similar/incompatible groups exist | benchmark operator (pre-approved) |
| 2026-11-05 | selection | Merge plan U01-U05, one unified feature per kept row, all 'improve' | sources are flawed for the user's invariants (double charge, double webhook, no refund) | benchmark operator (pre-approved) |
| 2026-11-05 | compatibility | D01 Order.status is the single payment state (A's paid flag dropped) | two sources of truth (critical) | benchmark operator (pre-approved) |
| 2026-11-05 | compatibility | D02 cancel: pending->cancelled, paid->refund once->refunded, else no-op | user requirement in task.md; C kept money (critical). Final status 'refunded' is Claude's choice: task.md does not name it | benchmark operator (pre-approved) |
| 2026-11-05 | compatibility | D03 client key required, first key per order recorded before charge and reused; key reuse across orders refused; GatewayTimeout re-raised with order pending | double charge on retry (critical) | benchmark operator (pre-approved) |
| 2026-11-05 | compatibility | D04 webhooks de-duplicated by event id, state-checked, ledger only on real transitions | redelivery applied twice (critical) | benchmark operator (pre-approved) |
| 2026-11-05 | compatibility | D05 refund marker before gateway.refund; never a second refund call | gateway.refund is not idempotent (critical) | benchmark operator (pre-approved) |
| 2026-11-05 | compatibility | D06 one atomic store write per state change; intents written before gateway calls | failed writes must leave the order unchanged (high) | benchmark operator (pre-approved) |
| 2026-11-05 | compatibility | D07-D10 amount_cents ints; renewal de-dup by period; one Order entity; string ids ord_<n> | medium/info conflicts | benchmark operator (pre-approved) |
| 2026-11-05 | architecture | Style modular-monolith (vs microservices poor, event-driven partial, service-oriented poor); stdlib Python, one module app/unified/billing.py (D11); Store contract D12; late-charge refund D13; slices V1 M01+M02, V2 M03, V3 M04, V4 M05 | drivers in architecture.json | benchmark operator (pre-approved) |
| 2026-11-05 | architecture | migration:order plan approved (amount->amount_cents, paid->status); nothing to run since no source persists data | flagged high-risk by check_compatibility.py after the schema draft | benchmark operator (pre-approved) |
| 2026-11-05 | implementation | A01: run the new app's own unittest suite in app/ (no installs, no network) | needed to prove features | benchmark operator (pre-approved) |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-05 | recon | A Billfold: sources/billfold (1 file) + task.md; scan: no findings; modules 1/1 analysed; 2 features; no capability limits | complete, size S | CP1 |
| 2026-11-05 | recon | B Subscribe: sources/subscribe (1 file) + task.md; scan: no findings; modules 1/1; 1 feature | complete, size S | CP1 |
| 2026-11-05 | recon | C Orderly: sources/orderly (1 file) + task.md; scan: no findings; modules 1/1; 2 features | complete, size S | CP1 |
| 2026-11-05 | recon | gateway.py (the task's mock gateway, not a source app) read as the integration contract: charge(amount_cents, key) idempotent by key, may raise GatewayTimeout after a successful charge; refund(charge_id) is NOT idempotent | input to design | CP1 |
| 2026-11-05 | extraction | Menu M01-M05 from A-F01, A-F02, B-F01, C-F01, C-F02; 5 unique rows, 0 merge groups (features share the Order entity but have different jobs); 4 marked conflict/adaptable for phase 4 | validate_feature_menu.py: consistent | CP2 |
| 2026-11-05 | selection | validate_feature_menu.py --set keep M01-M05; merge-plan.json written | picks consistent; 3 conflict warnings carried to phase 4 | CP3 |
| 2026-11-05 | compatibility | check_compatibility.py --write --strict | 10 conflicts, all resolved; no migrations | CP4 |
| 2026-11-05 | architecture | prd.md, architecture.md/.json, migration-plan.md; validate_artifacts + check_compatibility --strict | valid | CP5 |
| 2026-11-05 | implementation V1-V4 | Wrote app/unified/billing.py (store, orders, payments, refunds, webhooks, subscriptions, app facade) and 31 tagged tests; the four slices were written in one pass and checked with one full-suite run rather than one run per slice | run 20261105T130725609331Z: 31 passed, 0 failed, first attempt | CP6 |
| 2026-11-05 | integration | verify_tests.py, verify_tests.py --rerun (approval A01), --update-baseline | 31/31 passed, 5/5 features verified, every AC01-AC11 covered | CP7 |
