# Helpdesk with FAQ suggestions: architecture

Version: 2026-11-04 · Status: approved (pre-approved by the benchmark operator) · Structured copy: `architecture.json`

## Architecture style

| Style | Fit | Why |
| --- | --- | --- |
| modular monolith | good (selected) | one team, strong consistency between tickets, messages and statuses, no scaling need |
| microservices | poor | network calls and deployables for a tiny app |
| service-oriented | poor | no existing system must stay separate |
| event-driven | poor | suggestions are synchronous; the only async candidate (email) is deferred |
| hybrid | partial | revisit if M04 email delivery is added (queued sender beside the monolith) |

Selected: modular monolith, because one team builds five small, tightly related features with no independent scaling or release need.

## Stack

| Layer | Choice | Why (decision id) |
| --- | --- | --- |
| Frontend | server-rendered HTML, one CSS file | few screens, no build step (D02) |
| Backend | Python 3.8+ standard library | B adaptable, A rebuilt anyway, no installs approved (D01) |
| Database | SQLite with foreign keys and checks | integrity without a server (D03) |
| Tests | unittest | built in (D04) |
| Hosting | none planned | plan mode (D05) |

## Modules

| Module | Responsibility | Features | Depends on | Owns entities |
| --- | --- | --- | --- | --- |
| config | settings from environment variables | - | - | - |
| accounts | users, sign-in, sessions, roles, `can(user, action, record)` | - (platform) | config | User, Session |
| tickets | tickets, statuses, messages, replies, closing | M01, M02, M03 | accounts | Ticket, Message |
| faq | FAQ entries CRUD | M05 | accounts | FaqEntry |
| suggestions | rank FAQ entries against ticket text | M06 | tickets, faq, accounts | - |
| web | routing, JSON API, HTML pages, error shape | - | accounts, tickets, faq, suggestions, config | - |

### Feature dependency map

```mermaid
graph LR
  M02 --> M01
  M03 --> M01
  M06 --> M05
  M06 --> M01
  M04 -.later.-> M02
```

## Data model

| Entity | Merged from | Primary key | Key fields | Notes |
| --- | --- | --- | --- | --- |
| User | new | id integer | email (unique), name, password_hash, role (customer/agent/admin) | no source had accounts |
| Session | new | token_hash text | user_id → User (cascade), expires_at | only the token hash is stored |
| Ticket | A:Ticket | id integer | subject, customer_id → User (restrict), status check (open/pending/closed), timestamps | A's embedded messages become Message rows |
| Message | A:Message | id integer | ticket_id → Ticket (cascade), author_id → User (restrict), sender (customer/agent, from A's `from`), body (1-10000 chars) | |
| FaqEntry | B:FAQ | id integer | question (from q), answer (from a), updated_at | |

Indexes on every foreign key and on (status, updated_at) for the ticket list. Full DDL in `schema.sql`.

Migrations from source data: none needed. Neither source stores data; B's one hard-coded entry is seeded into a fresh database (low risk, non-destructive). See `migration-plan.md`.

## Authentication and authorization

One identity system: email and password, PBKDF2-HMAC-SHA256 (600,000 iterations, per-user salt). Session: random token in an http-only, SameSite=Lax cookie (Secure in production), SHA-256 hash stored, 12-hour expiry; CSRF token on state-changing requests. One function, `accounts.can(user, action, record)`, is called by every route and every query.

| Source role | Unified role | Extra permissions |
| --- | --- | --- |
| A: agent | agent | ticket.reply, ticket.close, suggestion.read, faq.read |
| A: customer (inferred) | customer | ticket.create, ticket.message and ticket.read on own tickets only |
| B: none | admin | everything agents can do, plus faq.write |

## API

REST under `/api/v1`, JSON, error shape `{"error": {"code", "message"}}`, `page`/`per_page` pagination, session cookie on every endpoint except sign-in. Details in `api.md`.

| Method | Path | Module | Auth | Features |
| --- | --- | --- | --- | --- |
| POST | /api/v1/session | accounts | none | - |
| DELETE | /api/v1/session | accounts | session | - |
| GET | /api/v1/tickets | tickets | session | M01 |
| POST | /api/v1/tickets | tickets | customer | M01 |
| GET | /api/v1/tickets/{id} | tickets | session | M01, M02 |
| POST | /api/v1/tickets/{id}/messages | tickets | session | M02 |
| POST | /api/v1/tickets/{id}/close | tickets | agent, admin | M03 |
| GET | /api/v1/tickets/{id}/suggestions | suggestions | agent, admin | M06 |
| GET | /api/v1/faqs | faq | agent, admin | M05 |
| POST | /api/v1/faqs | faq | admin | M05 |
| PATCH | /api/v1/faqs/{id} | faq | admin | M05 |
| DELETE | /api/v1/faqs/{id} | faq | admin | M05 |

## Navigation

| Route | Screen | Module |
| --- | --- | --- |
| /login | Sign in | web |
| /tickets | Ticket list | web |
| /tickets/new | New ticket | web |
| /tickets/{id} | Ticket detail with suggested answers | web |
| /faqs | FAQ entries | web |

## Design system

Tokens: colour roles surface, text, muted, accent, danger, success (the user's own palette, contrast checked to WCAG AA); type scale 14/16/20/24; spacing 4/8/16/24; radius 4/8. Components: button (primary, secondary, danger), text input, textarea, status badge (open, pending, closed; text label plus colour), message bubble (customer, agent), suggestion card with "Insert into reply", flash message (error, success). System font stack; no icon set. Nothing visual comes from either source.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| HELPDESK_DB_PATH | SQLite file | ./data/helpdesk.db |
| HELPDESK_SECRET_KEY | CSRF signing | random per start in development; required in production |
| HELPDESK_HOST | bind address | 127.0.0.1 |
| HELPDESK_PORT | port | 8000 |
| HELPDESK_ENV | development or production | development |

All read in `config`. `.env.example` lists the names with no values; `.env` is git-ignored. No file, variable or value is taken from A's folder; A's SMTP_PASSWORD and STRIPE_KEY are not used (email is deferred, payments are not a feature).

## Error handling

Every error uses the one shape. Validation happens on the server. Logs hold request method, path, status and user id only: no bodies, emails or secrets. No external services, so no retries are needed in this version.

## Roadmap

| Slice | Features | Done when | Status |
| --- | --- | --- | --- |
| V1 | M01, M02, M03 | a customer opens a ticket, an agent replies and closes it; AC01-AC04 pass | pending |
| V2 | M05, M06 | an admin edits FAQ entries and an agent sees ranked suggestions on a ticket; AC05-AC07 pass | pending |

## Decisions

| Id | Decision | Reason | Approved |
| --- | --- | --- | --- |
| D01 | Python standard-library backend | B adaptable, A rebuilt anyway, no installs | yes (benchmark operator) |
| D02 | Server-rendered HTML | few screens | yes |
| D03 | SQLite with constraints | integrity, no server | yes |
| D04 | unittest | built in | yes |
| D05 | No deployment | plan mode | yes |
| D06 | Modular monolith | one team, strong consistency | yes |
| D07 | Nothing copied from A's folder; env vars only | unconfirmed licence; live credentials and hostile hooks in A | yes |
| D08 | Suggestions ranked, max 3, never auto-sent | compatibility decision | yes |
| D09 | pending on customer ticket/message, open on agent reply, close only from open | compatibility decision | yes |
| D10 | One REST style and error shape | consistency | yes |
| D11 | No data migration; seed B's entry | no stored data in sources | yes |
