# DealFlow (B): reverse-engineering report

App id: B · Access: own-code · Licence: none in repository (user's own code) · Code reuse: allowed
Slice studied: deals pipeline with custom stages and stale-deal reminders · Coverage: complete · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed**, **documented**, **inferred** or **unknown**. The structured
version of this report is `source.json` in the same folder.

## Summary

DealFlow is one Python module (14 lines; its docstring calls it
illustrative) with a deals pipeline whose stage list is a parameter
(default new, contacted, negotiating, closed) and a job that emails each
deal's owner when a deal has not moved for 14 days. The database and mailer
are injected; there is no schema, UI, auth or scheduler.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | `sources/dealflow` | 2026-11-04 | not a git repo; scanned (0 findings) and indexed |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | documented | `deals.py:1` | docstring: custom stages and stale-deal reminders |
| B-E02 | B-R01 | observed | `deals.py:4` | DEFAULT_STAGES |
| B-E03 | B-R01 | observed | `deals.py:6` | move_deal with stages parameter, sets moved_at |
| B-E04 | B-R01 | observed | `deals.py:11` | stale_deal_reminders, 14 days, owner_email |

## Features

### B-F01 Deals pipeline (custom stages)

- **Source application:** DealFlow (B)
- **Evidence:** B-E02, B-E03, B-E01
- **Description:** move deals through a caller-supplied stage list.
- **Observed behaviour:** ValueError on unknown stage; writes stage and moved_at (UTC).
- **Business logic:** any-to-any moves; stages customisable per call.
- **Data requirements:** Deal (stage, moved_at).
- **Dependencies:** none.
- **Integration requirements:** persistence; storage for stage lists.
- **Basis and confidence:** observed, high

### B-F02 Stale-deal email reminders

- **Source application:** DealFlow (B)
- **Evidence:** B-E04, B-E01
- **Description:** email owners about deals idle for 14+ days.
- **Observed behaviour:** one email per stale deal to owner_email.
- **Business logic:** no de-duplication across runs; closed deals not excluded.
- **Data requirements:** Deal (title, moved_at, owner_email).
- **Dependencies:** B-F01 (moved_at).
- **Integration requirements:** email provider, scheduler.
- **Basis and confidence:** observed, high

## Screens and workflows

None (no UI).

## Navigation

None.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Deal | unknown | title, stage, moved_at (datetime), owner_email | none visible | inferred from usage | B-E03, B-E04 |

## API

None.

## Authentication and authorization

None in the source; deals carry an owner_email only.

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| Email (injected mailer) | stale-deal reminders | B-F02 | B-E04 |

## Architecture and stack

Single Python module, standard library only, dependencies injected (observed).

## Configuration

None; the 14-day threshold is a parameter default.

## Error handling

Unknown stage: ValueError.

## Unknowns

- Deal schema and primary key (inferred from usage only).
- Where custom stage lists are stored.
- Owners, users and auth.
- Scheduler and email provider.
- Link from deals to contacts.
