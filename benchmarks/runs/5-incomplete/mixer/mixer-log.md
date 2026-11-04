# Mixer log

Project: Unified booking app · Mode: plan (selection by auto-pick, per operator) · Sources: A BookNow, B Slotty

The decision history and integration log for this run. Add a line for every
phase, every decision and every approval. Never rewrite past lines; add a new
one that corrects them.

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | Mode plan (stop after architecture approval); selection by auto-pick | task.md says "Mode: plan"; operator says use auto-pick for selection | benchmark-operator (pre-approved in task) |
| 2026-11-04 | setup | Not approved: installing anything, network access, running any source code | operator decision | benchmark-operator |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-11-04 | setup | check_environment.py; browser/web_fetch/repository_access/external_api recorded as not-needed, network unavailable (not approved) | capabilities.json written | - |
| 2026-11-04 | recon | scan_source.py on sources/booknow and sources/slotty-docs | 2 files each, no findings, no AI-instruction text | - |
| 2026-11-04 | recon | index_repo.py on sources/booknow | 2 files, 19 lines, 1 module (root); imports `payments` which is not in the folder | - |
| 2026-11-04 | recon | A BookNow: local folder, 2 files read, 1/1 module analysed, scan clean, 3 features, coverage partial (payments.py and db layer missing), size S | done | CP1 |
| 2026-11-04 | recon | B Slotty (closed): overview.md + openapi.yaml read, scan clean, 5 features (all documented, calendar sync low confidence), coverage partial (calendar.md missing, spec has no schemas/auth/errors), size M | done | CP1 |
| 2026-11-04 | recon | Process note: the four source files were printed once (cat -A) before scan_source.py ran; the scans then found nothing. Deviation from "scan before reading" recorded honestly. | - | - |
| 2026-11-04 | extraction | 8 menu rows from 8 source features (A 3, B 5). Group booking: 2 similar (M01 A, M02 B). Unique: 6 (M03-M08). No identical, complementary, incompatible or separate rows. Strategies: improve 2, rebuild 6. | validate_feature_menu.py ok | CP2 |
| 2026-11-04 | selection | Auto-pick: keep M01 (A booking, core loop, must), M03 (A cancel, core loop, must), M04 (A Stripe payment, must), M05 (B publish slots, must; nothing else creates slots), M06 (B recurring, should, B core loop), M08 (B waiting list, should, B core loop) | core-loop and must rows kept per auto-pick rule | benchmark-operator (pre-approved in task), A01 |
| 2026-11-04 | selection | Auto-pick: drop M02 (B booking) | similar to M01; M01 is the better-evidenced alternative (observed code vs one-line spec summary) | benchmark-operator (pre-approved in task), A01 |
| 2026-11-04 | selection | Auto-pick: defer M07 (B calendar sync) to later | could, low confidence (calendar.md missing), needs external API/OAuth: a could feature that adds risk | benchmark-operator (pre-approved in task), A01 |
| 2026-11-04 | selection | Merge plan U01-U06 written (U01 slots, U02 payments, U03 booking, U04 cancellation, U05 recurring, U06 waiting list) | one unified feature per kept row | benchmark-operator (pre-approved in task), A01 |
| 2026-11-04 | selection | validate_project.py --phase selection exit 0; selection approved | done | CP3 |
| 2026-11-04 | compatibility | Corrected source.json data (no new reading): A Booking.slot_id foreign key now references entity "Slot" (was "Slot.id", which check_compatibility.py reads as a missing entity); B's inferred entities now list no fields instead of placeholder "unknown" fields. Re-indexed A with --previous: no stale features. | ok | - |
| 2026-11-04 | compatibility | Script found 2 medium (duplicate Booking, Slot); 7 manual conflicts added (5 high, 2 medium). Decisions: per-occurrence upfront charges for series, all-or-nothing (D01); full refund on allowed cancellation, soft cancel (D02); waitlist offer with 2h exclusive hold, no auto-charge (D03); per-occurrence 24h rule, cancel-series cancels remaining eligible (D04); all-or-nothing series with taken weeks listed (D05); unique active booking per slot + hold-charge-confirm (D06); email/password accounts, roles customer and staff (D07); merge Booking and Slot entities (D08, D09) | critical/high need approval; recommendations taken | benchmark-operator (pre-approved in task), A02 |
| 2026-11-04 | compatibility | Migrations migration:booking, migration:slot: additive, low risk, not destructive; approved as plans only | operator pre-approved migration plans as plans only | benchmark-operator (pre-approved in task), A03 |
| 2026-11-04 | compatibility | Dependencies: no conflicts; vulnerabilities not checked (no audit run: network and installs not approved) | - | - |
| 2026-11-04 | compatibility | check_compatibility.py --strict exit 0; validate_project.py --phase compatibility exit 0; approved | done | CP4 |
| 2026-11-04 | architecture | check_compatibility.py rerun with architecture.json: migration:booking and migration:slot re-rated high/destructive (unknown source types -> uuid/integer; A Slot.taken not kept). Resolutions updated; approved as plans only (A04); design/migration-plan.md written. Nothing run. | approved as plan | benchmark-operator (pre-approved in task), A04 |
| 2026-11-04 | architecture | D10-D15: Django 5 + htmx, PostgreSQL 16, scheduled command for offer expiry, modular monolith with slot-freed event (alternatives: microservices poor, service-oriented poor, event-driven partial, hybrid partial), REST /api/v1, calendar sync deferred. 6 modules, 6 entities, 15 endpoints, 8 routes, slices V1 (M05,M04,M01), V2 (M03), V3 (M06), V4 (M08). | approved | benchmark-operator (pre-approved in task), A05 |
| 2026-11-04 | architecture | validate_artifacts.py, check_dependencies.py, validate_project.py --phase architecture: all exit 0. Plan mode: run stops here. | done | CP5 |
