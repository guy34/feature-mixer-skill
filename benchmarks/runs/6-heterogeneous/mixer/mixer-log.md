# Mixer log

Project: Unified online shop · Mode: plan (selection by auto-pick, per the benchmark operator) · Sources: A PyShop, B NodeCart, C Reviewly

The decision history and integration log for this run. Add a line for every
phase, every decision and every approval. Never rewrite past lines; add a new
one that corrects them.

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | Mode plan (stop after architecture); selection made by auto-pick | task.md says "Mode: plan"; operator says use auto-pick for the selection | benchmark-operator (pre-approved in task) |
| 2026-11-04 | setup | Rights: A own-code (reuse allowed), B own-code (reuse allowed), C closed (rebuild only, no reuse) | task.md; no licence files in A or B, which is fine for the user's own code | benchmark-operator (pre-approved in task) |
| 2026-11-04 | setup | Recorded A01 install-dependencies, A02 network, A03 run-source-code as NOT approved | operator explicitly withheld them; nothing was installed, fetched or run | benchmark-operator (not approved in task) |
| 2026-11-04 | setup | Capabilities: browser, web_fetch, repository_access, external_api recorded as not-needed | every input is a local file; no website, GitHub repo or API call is needed (and network is not approved) | - |
| 2026-11-04 | selection | auto-pick: keep M01 catalog (A, must, core loop), M04 cart (B, best-evidenced alternative of the similar cart group), M05 Stripe checkout (B, must), M06 list reviews, M07 leave review, M09 verified-purchase reviews (C core loop) | auto-pick rules: keep core loops and musts; one alternative per similar group | benchmark-operator (pre-approved in task) |
| 2026-11-04 | selection | auto-pick: drop M03 PyShop add-to-cart (must, but the alternative to M04; its integer typing goes into M04's improvement); existing PyShop carts are not carried over (carts are transient) | similar group: keep the best-evidenced alternative (B observed high vs A medium, handler elided) | benchmark-operator (pre-approved in task) |
| 2026-11-04 | selection | auto-pick: defer (later) M02 category filter and M08 shop replies | both could, low confidence (comment only / one sentence, no API) | benchmark-operator (pre-approved in task) |
| 2026-11-04 | selection | Merge plan U01-U06 written; selection approved | validator: complete and valid | benchmark-operator (pre-approved in task) |
| 2026-11-04 | compatibility | critical application:security:checkout-client-prices: server-built line items only (D04) | B lets the client set prices | benchmark-operator (pre-approved in task) |
| 2026-11-04 | compatibility | high auth-gap: new accounts module (D05); high purchase-confirmation: Order + verified webhook (D04, D08); high cartitem-quantity: integer >= 1; high cartitem-product-id: integer FK to A's products | found by reasoning (manual-conflicts.json) | benchmark-operator (pre-approved in task) |
| 2026-11-04 | compatibility | medium backend-framework / data-layer: Flask + SQLAlchemy (D01); low reviews-path: unversioned /api; low naming: snake_case via aliases | script recommendation of Express rested on a 1-1 tie, overridden with reasons | benchmark-operator (pre-approved in task) |
| 2026-11-04 | compatibility | migration:product (price numeric -> integer minor units), migration:cart and migration:cartitem (B carts discarded) approved as PLANS ONLY; not run | destructive (high risk); plan in design/migration-plan.md | benchmark-operator (pre-approved in task) |
| 2026-11-04 | architecture | Style modular monolith (alternatives: microservices poor, service-oriented poor, event-driven partial, hybrid partial) | one team, consistency between cart/order/review gate, modest scale | benchmark-operator (pre-approved in task) |
| 2026-11-04 | architecture | D01 Flask/SQLAlchemy backend; D02 PostgreSQL integer keys; D03 server-rendered pages; D04 Stripe with server-built items + verified webhook; D05 new accounts module; D06 migrate A products, discard B carts (plan only); D07 unversioned REST, one error shape; D08 refuse unverified reviews | see design/architecture.md Decisions | benchmark-operator (pre-approved in task) |
| 2026-11-04 | architecture | Modules accounts, catalog, cart, checkout, reviews; slices V1 (M01, M04), V2 (M05), V3 (M06, M07, M09); architecture approved; plan mode ends here | validator: complete and valid | benchmark-operator (pre-approved in task) |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-04 | recon | check_environment.py; scan_source.py on all 3 sources (0 findings; note: scanner skipped B's schema.prisma because .prisma is not in its text-extension list, so it was read manually); index_repo.py on A and B | capabilities recorded; scans acknowledged | - |
| 2026-11-04 | recon | A PyShop: read local folder (3/3 files, 1/1 module); no capability limits; 3 features (A-F02 inferred, low); coverage complete; size S. Handler bodies are elided in the source | valid | CP1 |
| 2026-11-04 | recon | B NodeCart: read local folder (3/3 files, 1/1 module); 2 features; coverage complete; size S. Checkout trusts client prices; quantity stored as text | valid | CP1 |
| 2026-11-04 | recon | C Reviewly: read public overview + OpenAPI spec only (closed product; no running app observed); 4 features (all documented; C-F03 low); coverage partial, 7 unknowns; size S | valid with warnings | CP1 |
| 2026-11-04 | extraction | Built feature-menu.csv: 9 rows from 9 source features (A 3, B 2, C 4). Groups: cart (M03 A, M04 B) similar. Unique: M01, M02, M05, M06, M07, M08, M09. No identical, complementary, separate or incompatible rows | validate_feature_menu.py --allow-no-keep: valid | CP2 |
| 2026-11-04 | selection | validate_feature_menu.py --set (keep 6, drop 1, later 2); validate_project.py --phase selection | valid | CP3 |
| 2026-11-04 | compatibility | check_compatibility.py --write --strict (exit 0; 9 conflicts resolved, 3 destructive migrations approved as plans); validate_project.py --phase compatibility (exit 0) | valid | CP4 |
| 2026-11-04 | architecture | prd.md, architecture.md/.json, schema.sql, api.md written; check_compatibility.py --strict, check_dependencies.py, validate_artifacts.py, validate_project.py --phase architecture all exit 0. No dependency audit (network not approved): vulnerabilities not checked | valid | CP5 |
