# Tallyho (A): reverse-engineering report

App id: A · Access: closed · Licence: proprietary · Code reuse: not-allowed
Slice studied: receipt scanning and shared budgets (and the expense records they produce) · Coverage: partial · Size: M

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the running app, a screenshot or the code),
**documented** (official docs or a published spec), **inferred** (deduced,
not seen), or **unknown**. The structured version of this report is
`source.json` in the same folder.

Evidence from `my-notes.md` is the user's own first-hand observation of the
running app, given to me in writing; I did not see it myself. It is marked
observed, with at most medium confidence where it stands alone.

## Summary

Tallyho is a closed expense tracker used on a phone. The slice's core loop:
photograph a receipt, get merchant, date and total filled in, correct them,
save the expense into a budget shared with other people, and watch "spent of
limit" for the month. Only two help pages, a five-line API description, two
result screenshots and two lines of the user's notes were available, so much
of the behaviour (category list, reset rules, invite rules, OCR and
exchange-rate providers) is unknown. Notable findings: the scanned date is
often wrong (user's notes), and removing a member leaves their expenses in
the budget (user's notes).

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | documentation | sources/tallyho/help (budgets.md, receipts.md) | 2026-11-04 | local copies of public help pages; live site not fetched (no approved network) |
| A-R02 | api-spec | sources/tallyho/api.md | 2026-11-04 | public API v2 description, no types or bodies |
| A-R03 | screenshots | sources/tallyho/screens (scan.svg, budget.svg) | 2026-11-04 | two result screens |
| A-R04 | documentation | sources/tallyho/my-notes.md | 2026-11-04 | the user's own notes from using the app |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | documented | `help/receipts.md:2` | Photo of a receipt fills merchant, date, total; any field can be corrected |
| A-E02 | A-R01 | documented | `help/receipts.md:3` | Foreign-currency receipts converted to home currency |
| A-E03 | A-R03 | observed | `screens/scan.svg` | Scan result: merchant, total in receipt currency with approximate home amount, Edit and Save; no date or category shown |
| A-E04 | A-R04 | observed | `my-notes.md:1` | User: total usually right, date often wrong, fixed by hand (on phone) |
| A-E05 | A-R01 | documented | `help/budgets.md:2` | Invite by email; all members see expenses; owner removes members |
| A-E06 | A-R01 | documented | `help/budgets.md:3` | Budgets reset monthly |
| A-E07 | A-R03 | observed | `screens/budget.svg` | Budget: name, member count, spent of limit in one currency, members with owner, Invite and Remove member |
| A-E08 | A-R04 | observed | `my-notes.md:2` | User: removed member's earlier expenses stayed in the budget |
| A-E09 | A-R02 | documented | `api.md:2` | GET /v2/expenses?budget_id returns id, merchant, amount, currency, date, category |
| A-E10 | A-R02 | documented | `api.md:3` | POST /v2/expenses creates an expense (body undocumented) |
| A-E11 | A-R02 | documented | `api.md:4` | GET /v2/budgets lists the user's budgets |
| A-E12 | A-R02 | documented | `api.md:5` | Personal access token in Authorization header; 60 requests per minute |

## Features

### A-F01 Receipt scanning

- **Source application:** Tallyho (A)
- **Evidence:** A-E01, A-E03, A-E04
- **Description:** photograph a receipt, get merchant, date and total filled in, correct and save.
- **Observed behaviour:** result screen with merchant, total, Edit and Save (observed); date often wrong per the user.
- **Business logic:** extracted fields merchant, date, total; all editable. Category extraction not documented.
- **Data requirements:** Expense merchant, date, amount, currency; receipt image (storage unknown).
- **Dependencies:** A-F07.
- **Integration requirements:** an OCR engine of the unified app's own choosing, image upload and storage.
- **Basis and confidence:** observed, medium

### A-F02 Foreign-currency conversion

- **Source application:** Tallyho (A)
- **Evidence:** A-E02, A-E03
- **Description:** foreign receipts converted to the home currency; both amounts shown (12.40 GBP, about 14.43 EUR).
- **Observed behaviour:** scan screen shows original and converted totals.
- **Business logic:** rate source, rate date and rounding unknown.
- **Data requirements:** amount, currency, home currency.
- **Dependencies:** A-F01.
- **Integration requirements:** an exchange-rate provider.
- **Basis and confidence:** observed, medium

### A-F03 Shared budgets

- **Source application:** Tallyho (A)
- **Evidence:** A-E05, A-E07, A-E11
- **Description:** a budget several people belong to; all members see all its expenses and spent of limit.
- **Observed behaviour:** budget screen with spent of limit and member list.
- **Business logic:** one owner (inferred from one owner marker); limit and currency per budget.
- **Data requirements:** Budget, membership, Expense.budget_id.
- **Dependencies:** A-F07.
- **Integration requirements:** accounts and a membership check on every read.
- **Basis and confidence:** observed, high

### A-F04 Invite members by email

- **Source application:** Tallyho (A)
- **Evidence:** A-E05, A-E07
- **Description:** invite people to a budget by email.
- **Observed behaviour:** Invite button seen; acceptance flow not seen.
- **Business logic:** who may invite and expiry are unknown.
- **Data requirements:** invitation (inferred).
- **Dependencies:** A-F03.
- **Integration requirements:** outbound email, accounts for invitees.
- **Basis and confidence:** observed, medium

### A-F05 Owner removes members

- **Source application:** Tallyho (A)
- **Evidence:** A-E05, A-E07, A-E08
- **Description:** the owner removes a member; that member's earlier expenses stay in the budget.
- **Observed behaviour:** Remove member button; user saw expenses remain.
- **Business logic:** owner only. Whether the removed member still sees those expenses is unknown.
- **Data requirements:** membership, expense author.
- **Dependencies:** A-F03.
- **Integration requirements:** permission check drops the removed member's access.
- **Basis and confidence:** observed, high

### A-F06 Monthly budget reset

- **Source application:** Tallyho (A)
- **Evidence:** A-E06
- **Description:** the budget period restarts monthly.
- **Observed behaviour:** not seen; documented in one line.
- **Business logic:** day, time zone, rollover and what happens to expenses are unknown.
- **Data requirements:** budget period.
- **Dependencies:** A-F03.
- **Integration requirements:** spent total per period.
- **Basis and confidence:** documented, medium

### A-F07 Expense records

- **Source application:** Tallyho (A)
- **Evidence:** A-E09, A-E10
- **Description:** create expenses and list a budget's expenses (id, merchant, amount, currency, date, category).
- **Observed behaviour:** documented only.
- **Business logic:** types and validation not documented.
- **Data requirements:** Expense.
- **Dependencies:** none.
- **Integration requirements:** the core record.
- **Basis and confidence:** documented, medium

### A-F08 Public API with personal access tokens

- **Source application:** Tallyho (A)
- **Evidence:** A-E09, A-E10, A-E11, A-E12
- **Description:** versioned API (v2), token auth, 60 requests per minute.
- **Observed behaviour:** documented only.
- **Business logic:** rate limit 60 per minute.
- **Data requirements:** tokens (inferred).
- **Dependencies:** A-F07, A-F03.
- **Integration requirements:** token issuance and revocation (undocumented).
- **Basis and confidence:** documented, high

### A-F09 Expense category field

- **Source application:** Tallyho (A)
- **Evidence:** A-E09
- **Description:** each expense has a category; the vocabulary is unknown.
- **Observed behaviour:** field name only.
- **Business logic:** unknown.
- **Data requirements:** Expense.category.
- **Dependencies:** A-F07.
- **Integration requirements:** a category vocabulary must be chosen.
- **Basis and confidence:** documented, low

## Screens and workflows

| Id | Screen | Route | Components | States seen | Evidence |
| --- | --- | --- | --- | --- | --- |
| A-S01 | Scanned receipt | unknown | merchant and total fields, converted amount, Edit, Save | filled after scan | A-E03 |
| A-S02 | Budget overview | unknown | header with member count, spent of limit, member list with owner, Invite, Remove member | filled, 3 members | A-E07 |

**A-W01 Scan a receipt into an expense:** (capture screen not seen) → A-S01 → saved. Edge cases: wrong date corrected by hand; foreign currency shown with converted amount.

**A-W02 Manage budget members:** A-S02 → Invite / Remove member. Edge cases: removed member's expenses stay; invite acceptance not seen.

## Navigation

Unknown beyond the two result screens; no routes are documented.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Expense | id (unknown) | merchant, amount, currency, date, category, budget_id (types unknown) | budget_id → Budget | documented | A-E09, A-E10 |
| Budget | id (unknown) | name, limit, currency | has members | observed | A-E07, A-E11 |
| BudgetMember | unknown | budget_id, user_id, role (owner, member) | → Budget, → User | inferred | A-E05, A-E07 |
| User | unknown | email | | inferred | A-E05 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/v2/expenses` | personal access token | budget_id | list of id, merchant, amount, currency, date, category | not documented | A-E09 |
| POST | `/v2/expenses` | personal access token | not documented | not documented | not documented | A-E10 |
| GET | `/v2/budgets` | personal access token | - | budgets the user belongs to | not documented | A-E11 |

## Authentication and authorization

API: personal access token in the Authorization header (documented, A-E12).
App sign-in and sessions: unknown. Roles: owner and member per budget
(documented and observed, A-E05, A-E07); members see every expense of the
budget; only the owner removes members.

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| OCR engine (unknown) | read receipts | A-F01 | A-E01 |
| Exchange rates (unknown) | convert currency | A-F02 | A-E02 |
| Email (unknown) | invitations | A-F04 | A-E05 |

## Architecture and stack

Phone app in use (user's notes); versioned public HTTP API v2. Frameworks,
database and hosting are not documented and are not needed: Tallyho is
closed and will be rebuilt from behaviour only. No text, images or icons
from it may be copied.

## Configuration

Not documented.

## Error handling

Wrong OCR date: no warning documented; corrected by hand. API errors and
rate-limit responses: not documented.

## Unknowns

- OCR engine and accuracy (not needed: the unified app chooses its own).
- Whether scanning sets the category; Tallyho's category list; custom categories.
- Exchange-rate provider, rate date, rounding, whether the original amount is kept.
- Exact meaning of "budgets reset monthly" (day, time zone, rollover, expenses kept).
- Who may invite, invite expiry, invitee without an account.
- Whether a removed member still sees their expenses; whether the user wants expenses to stay (the note is neutral).
- Multiple owners or ownership transfer.
- App sign-in and sessions; API types, bodies, errors, pagination, token issuance.
- Receipt image storage and retention.
- Capture and invite-acceptance screens.
- No live site or account inspection was possible (no approved network or browser, user not present). A short session in the user's own account, or more help pages, would fill most gaps.
