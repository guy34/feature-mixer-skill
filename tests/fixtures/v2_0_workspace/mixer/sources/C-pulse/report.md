# Pulse (C): reverse-engineering report

App id: C · Access: closed · Licence: proprietary · Code reuse: not-allowed
Slice studied: dashboard, push notifications · Coverage: partial · Size: M

Basis: **observed** (seen in the code), **documented** (official docs or spec), **inferred**, **unknown**. The structured version is `source.json` in this folder.

## Summary

Pulse is a closed product, so only its public documentation and published API spec were read. It offers a workload dashboard, browser push notifications, a weekly digest email, Google sign-in and a community template gallery. Nothing was copied; behaviour is recorded as documented, and four gaps are listed under Unknowns.

## Sources used

| Ref | Kind | Location | Accessed |
|---|---|---|---|
| C-R01 | documentation | `sources/pulse-docs/docs/overview.md` | 2026-11-04 |
| C-R02 | documentation | `sources/pulse-docs/docs/push.md` | 2026-11-04 |
| C-R03 | api-spec | `sources/pulse-docs/openapi.yaml` | 2026-11-04 |

## Evidence

| Id | Source | Basis | Locator | What it shows |
|---|---|---|---|---|
| C-E01 | C-R01 | documented | `sources/pulse-docs/docs/overview.md:5` | Dashboard: open items per person, overdue items, waiting approvals; done items not open |
| C-E02 | C-R03 | documented | `sources/pulse-docs/openapi.yaml:8` | GET /v2/dashboard/workload returns open_by_person, overdue, pending_approvals |
| C-E03 | C-R02 | documented | `sources/pulse-docs/docs/push.md:3` | Push: opt in per browser; HTTPS endpoints; no push without opting in |
| C-E04 | C-R03 | documented | `sources/pulse-docs/openapi.yaml:21` | POST /v2/push/subscriptions registers an endpoint and returns a PushSubscription |
| C-E05 | C-R01 | documented | `sources/pulse-docs/docs/overview.md:14` | A weekly digest email every Monday |
| C-E06 | C-R01 | documented | `sources/pulse-docs/docs/overview.md:16` | Template gallery of boards shared by the Pulse community |
| C-E07 | C-R01 | documented | `sources/pulse-docs/docs/overview.md:22` | Sign in with Google; workspaces have admins and members |
| C-E08 | C-R03 | documented | `sources/pulse-docs/openapi.yaml:51` | API uses OAuth 2 with Google as the authorization server |

## Features

### C-F01 Workload dashboard

- **Source application:** Pulse (C)
- **Evidence:** C-E01, C-E02
- **Description:** Open items per person, overdue items and waiting approvals.
- **Business logic:** Done items are not counted as open. How overdue is judged across time zones is not documented.
- **Data requirements:** Task, ApprovalRequest
- **Dependencies:** none
- **Integration requirements:** Needs tasks with assignees and due dates, and approvals.
- **Basis and confidence:** documented, medium

### C-F02 Push notifications

- **Source application:** Pulse (C)
- **Evidence:** C-E03, C-E04
- **Description:** Browser push notifications people opt into per browser.
- **Business logic:** No push without opting in; endpoints must be HTTPS.
- **Data requirements:** PushSubscription
- **Dependencies:** none
- **Integration requirements:** Needs a notification source and a web push service.
- **Basis and confidence:** documented, medium

### C-F03 Weekly digest email

- **Source application:** Pulse (C)
- **Evidence:** C-E05
- **Description:** A Monday email summarising the past week.
- **Dependencies:** none
- **Integration requirements:** Needs email delivery and a scheduler.
- **Basis and confidence:** documented, medium

### C-F04 Template gallery

- **Source application:** Pulse (C)
- **Evidence:** C-E06
- **Description:** Board templates shared by the Pulse community.
- **Business logic:** The templates are other people's content.
- **Dependencies:** none
- **Basis and confidence:** documented, high

### C-F05 Sign in with Google

- **Source application:** Pulse (C)
- **Evidence:** C-E07, C-E08
- **Description:** Google accounts sign in to Pulse.
- **Dependencies:** none
- **Basis and confidence:** documented, high

## Screens and workflows

No screens recorded: none were seen (see Unknowns).

## Navigation

Not known.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
|---|---|---|---|---|---|
| PushSubscription | id (uuid) | id (uuid), endpoint (text), created_at (timestamp) | - | documented | C-E04 |

## API

| Method | Path | Auth | Features | Basis | Evidence |
|---|---|---|---|---|---|
| GET | `/v2/dashboard/workload` | oauth | C-F01 | documented | C-E02 |
| POST | `/v2/push/subscriptions` | oauth | C-F02 | documented | C-E04 |

## Authentication and authorization

Provider: google. Sign-in methods: google-oauth. Session: unknown. Model: unknown. Roles: admin, member. Basis: documented (C-E07, C-E08).

## Integrations

| Service | Purpose | Features | Evidence |
|---|---|---|---|
| Web Push | browser notifications | C-F02 | C-E03 |

## Architecture and stack

backend: Not documented beyond a public JSON API (documented).

## Configuration

None documented.

## Error handling

Not documented.

## Unknowns

- How Pulse keeps sessions: not in the public docs (would need Pulse's security docs).
- How overdue is judged across time zones: not documented.
- What the two Pulse roles may each do: only their names are documented.
- The look of Pulse's screens: no screenshots were provided, so no screens are listed.
