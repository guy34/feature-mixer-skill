# Approvals (B): reverse-engineering report

App id: B · Access: open-source · Licence: MIT · Code reuse: allowed
Slice studied: approvals, comments, email · Coverage: complete · Size: S

Basis: **observed** (seen in the code), **documented** (official docs or spec), **inferred**, **unknown**. The structured version is `source.json` in this folder.

## Summary

Approvals is an MIT-licensed tool for asking for sign-off. Requesters raise a request, an approver or admin approves or rejects it (never their own), the requester is emailed, and people discuss requests in threaded comments. Everything here was read in the code.

## Sources used

| Ref | Kind | Location | Accessed |
|---|---|---|---|
| B-R01 | local-directory | `sources/approvals` | 2026-11-04 |

## Evidence

| Id | Source | Basis | Locator | What it shows |
|---|---|---|---|---|
| B-E01 | B-R01 | documented | `sources/approvals/LICENSE:1` | Released under the MIT licence |
| B-E02 | B-R01 | observed | `sources/approvals/src/routes.js:7` | Sign in returns a JWT sent as a bearer token |
| B-E03 | B-R01 | observed | `sources/approvals/db/schema.sql:1` | users table: serial integer key, email, full_name, role requester/approver/admin |
| B-E04 | B-R01 | observed | `sources/approvals/db/schema.sql:8` | approval_requests: title, requester, approver, status pending/approved/rejected |
| B-E05 | B-R01 | observed | `sources/approvals/src/routes.js:20` | Only approvers and admins decide, never on their own request |
| B-E06 | B-R01 | observed | `sources/approvals/db/schema.sql:17` | Threaded comments: a reply has parent_id |
| B-E07 | B-R01 | observed | `sources/approvals/src/routes.js:26` | The requester is emailed through an outbox when a decision is made |
| B-E08 | B-R01 | observed | `sources/approvals/src/routes.js:3` | Tokens expire after 30 minutes |
| B-E09 | B-R01 | observed | `sources/approvals/client/routes.js:2` | Client routes: /login, /requests, /requests/:id, /settings |
| B-E10 | B-R01 | observed | `sources/approvals/package.json:5` | Node 16, Express 4, React 17, jsonwebtoken, nodemailer |
| B-E11 | B-R01 | observed | `sources/approvals/client/routes.js:9` | Button variants: primary, secondary, danger |

## Features

### B-F01 Sign in with email and password

- **Source application:** Approvals (B)
- **Evidence:** B-E02, B-E08
- **Description:** Email and password sign in returning a bearer token.
- **Business logic:** Tokens expire after 30 minutes.
- **Data requirements:** User
- **Dependencies:** none
- **Basis and confidence:** observed, high

### B-F02 Approval requests

- **Source application:** Approvals (B)
- **Evidence:** B-E04, B-E05
- **Description:** Ask for sign-off; an approver approves or rejects it.
- **Observed behaviour:** Requests start pending; a decision sets status, approver and time.
- **Business logic:** Only approvers and admins decide; nobody decides their own request.
- **Data requirements:** ApprovalRequest
- **Dependencies:** B-F01, B-F05
- **Basis and confidence:** observed, high

### B-F03 Threaded comments

- **Source application:** Approvals (B)
- **Evidence:** B-E06
- **Description:** Discussion on a request, with replies.
- **Data requirements:** Comment
- **Dependencies:** B-F02
- **Basis and confidence:** observed, high

### B-F04 Email notifications

- **Source application:** Approvals (B)
- **Evidence:** B-E07
- **Description:** The requester is emailed when their request is decided.
- **Data requirements:** EmailOutbox
- **Dependencies:** B-F02
- **Integration requirements:** Needs an email provider (nodemailer / SMTP).
- **Basis and confidence:** observed, high

### B-F05 Requester, approver and admin roles

- **Source application:** Approvals (B)
- **Evidence:** B-E03, B-E05
- **Description:** Three roles; approvers and admins can decide.
- **Data requirements:** User
- **Dependencies:** B-F01
- **Basis and confidence:** observed, high

## Screens and workflows

| Id | Screen | Route | Evidence |
|---|---|---|---|
| B-S01 | Login | `/login` | B-E09 |
| B-S02 | Request list | `/requests` | B-E09 |
| B-S03 | Request detail | `/requests/:id` | B-E09 |
| B-S04 | Settings | `/settings` | B-E09 |

**B-W01 Request and receive a decision:** B-S02 → B-S03. Edge cases: deciding your own request, deciding twice.

## Navigation

`/login` → B-S01, `/requests` → B-S02, `/requests/:id` → B-S03, `/settings` → B-S04

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
|---|---|---|---|---|---|
| User | id (serial) | id (integer), email (text), full_name (text), role (text) | - | observed | B-E03 |
| ApprovalRequest | id (serial) | id (integer), title (text), requester_id (integer), approver_id (integer), status (text), decided_at (timestamp) | requester_id → User, approver_id → User | observed | B-E04 |
| Comment | id (serial) | id (integer), request_id (integer), parent_id (integer), author_id (integer), body (text) | request_id → ApprovalRequest, parent_id → Comment, author_id → User | observed | B-E06 |
| EmailOutbox | id (serial) | id (integer), to_address (text), subject (text), body (text), sent_at (timestamp) | - | observed | B-E07 |

## API

| Method | Path | Auth | Features | Basis | Evidence |
|---|---|---|---|---|---|
| POST | `/api/v1/auth/token` | none | B-F01 | observed | B-E02 |
| GET | `/api/v1/users/:id` | bearer | B-F05 | observed | B-E03 |
| POST | `/api/v1/requests` | bearer | B-F02 | observed | B-E04 |
| POST | `/api/v1/requests/:id/decision` | bearer | B-F02, B-F04 | observed | B-E05 |
| GET | `/api/v1/requests/:id/comments` | bearer | B-F03 | observed | B-E06 |

## Authentication and authorization

Provider: self. Sign-in methods: password. Session: jwt-header. Model: rbac. Roles: requester, approver, admin. Basis: observed (B-E02, B-E03).

## Integrations

| Service | Purpose | Features | Evidence |
|---|---|---|---|
| SMTP email | decision emails | B-F04 | B-E07 |

## Architecture and stack

frontend: React single-page app; backend: Express JSON API with JWT bearer auth (observed).
Stack: frontend React 17; backend Node 16, Express 4; database SQL (serial keys).

## Configuration

`JWT_SECRET` (signs tokens)

## Error handling

not an approver: 403 'approvers only'; missing token: 401 'token required'

## Unknowns

None. Coverage is complete for the slice studied.
