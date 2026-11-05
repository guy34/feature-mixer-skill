# Tallyho (A): reverse-engineering report

App id: A · Access: closed · Licence: proprietary · Code reuse: not-allowed
Slice studied: receipt scanning and shared budgets, plus the expense record they touch · Coverage: partial · Size: M

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in a screenshot), **documented** (help pages, the API description, or the user's own notes),
**inferred** (deduced, not seen), or **unknown**. The structured version is `source.json`.

Note on the user's notes (`my-notes.md`): they describe what the user saw in the product. Claude did not see it,
so they are recorded as **documented (user-reported)**, never as observed.

## Summary

Tallyho is a closed expense tracker used mostly on a phone. Its core loop: photograph a receipt, check the
extracted merchant, date and total, save it into a budget shared with other people, and watch spent against
the monthly limit. Only public help pages, a short public API description, two screenshots and the user's
notes were available; the live product, the user's account and the public site could not be inspected (no
browser or web fetch approved). Key findings: the date is often extracted wrongly (user-reported),
foreign-currency receipts are converted to a home currency, a removed member's expenses stay in the budget
(user-reported), and expenses carry a category whose values are unknown.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | documentation | `sources/tallyho/help` | 2026-11-04 | two public help pages, saved by the user |
| A-R02 | api-spec | `sources/tallyho/api.md` | 2026-11-04 | public API v2 description, five lines |
| A-R03 | screenshots | `sources/tallyho/screens` | 2026-11-04 | `scan.svg`, `budget.svg` (copies in `screens/`, reference only) |
| A-R04 | documentation | `sources/tallyho/my-notes.md` | 2026-11-04 | the user's own notes from using the app (user-reported) |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | documented | `help/receipts.md:2` | Photo of a receipt fills merchant, date, total; any field can be corrected |
| A-E02 | A-R01 | documented | `help/receipts.md:3` | Foreign-currency receipts converted to home currency |
| A-E03 | A-R03 | observed | `screens/scan.svg` | Review screen: merchant, total with original and approx. converted amount, Edit / Save; no date shown |
| A-E04 | A-R04 | documented (user-reported) | `my-notes.md:1` | Used on a phone; total usually right, date often wrong, fixed by hand |
| A-E05 | A-R01 | documented | `help/budgets.md:2` | Invite by email; all members see expenses; owner removes members |
| A-E06 | A-R01 | documented | `help/budgets.md:3` | Budgets reset monthly |
| A-E07 | A-R03 | observed | `screens/budget.svg` | Budget: member count, spent 412.30 of 600.00 EUR, members with owner, Invite / Remove member |
| A-E08 | A-R04 | documented (user-reported) | `my-notes.md:2` | Removed member's earlier expenses stayed in the budget |
| A-E09 | A-R02 | documented | `api.md:2` | GET /v2/expenses?budget_id: id, merchant, amount, currency, date, category |
| A-E10 | A-R02 | documented | `api.md:3` | POST /v2/expenses creates an expense (body not described) |
| A-E11 | A-R02 | documented | `api.md:4` | GET /v2/budgets: budgets the token's user belongs to |
| A-E12 | A-R02 | documented | `api.md:5` | Personal access token; 60 requests per minute |

## Features

### A-F01 Receipt scanning

- **Source application:** Tallyho (A)
- **Evidence:** A-E01, A-E03, A-E04
- **Description:** photograph a receipt; merchant, date and total are filled in and can be corrected before saving.
- **Observed behaviour:** the review screen (screenshot) shows merchant and total with Edit and Save. The user reports the date is often wrong.
- **Business logic:** extracted fields are merchant, date and total; category is not documented as extracted.
- **Data requirements:** Expense merchant, date, amount, currency.
- **Dependencies:** A-F08.
- **Integration requirements:** an OCR / receipt-extraction service (unknown provider), photo capture on a phone.
- **Basis and confidence:** observed (screen only; the extraction itself is unknown), medium

### A-F02 Foreign-currency conversion

- **Evidence:** A-E02, A-E03 · **Basis and confidence:** observed, medium
- Converts to the user's home currency; the screenshot shows the original amount next to an approximate converted one. Rate source, rate date and rounding are unknown. Needs an exchange-rate provider.

### A-F03 Shared budgets

- **Evidence:** A-E05, A-E07, A-E11 · **Basis and confidence:** observed, high
- A budget with a limit and currency, members and one owner; every member sees its expenses and spent vs limit.

### A-F04 Invite members by email

- **Evidence:** A-E05, A-E07 · **Basis and confidence:** observed (button only), medium
- Acceptance, expiry and inviting people without an account are unknown. Needs email.

### A-F05 Owner removes members

- **Evidence:** A-E05, A-E07, A-E08 · **Basis and confidence:** observed (button) plus user-reported behaviour, medium
- Only the owner removes members. The removed member's earlier expenses stay in the budget (user-reported). Whether they keep access is unknown.

### A-F06 Monthly budget reset

- **Evidence:** A-E06 · **Basis and confidence:** documented, medium
- "Budgets reset monthly"; what a reset does, the day and the time zone are unknown.

### A-F07 Expense category field

- **Evidence:** A-E09 · **Basis and confidence:** documented, medium
- Seen only as a field in the API response; allowed values unknown.

### A-F08 Record and list expenses

- **Evidence:** A-E09, A-E10 · **Basis and confidence:** documented, medium
- Expenses with merchant, amount, currency, date, category, listed per budget.

### A-F09 Public API with personal access tokens

- **Evidence:** A-E09 to A-E12 · **Basis and confidence:** documented, medium
- REST v2, PAT in the Authorization header, 60 requests per minute.

## Screens and workflows

| Id | Screen | Route | Components | States seen | Evidence |
| --- | --- | --- | --- | --- | --- |
| A-S01 | Scanned receipt (review) | unknown | fields, converted-amount hint, Edit, Save | filled | A-E03 |
| A-S02 | Budget detail | unknown | header with member count, spent vs limit, member list, Invite, Remove member | filled | A-E07 |

**A-W01 Scan a receipt:** (capture screen not seen) → A-S01 → save. Edge cases: wrong date corrected by hand; foreign currency converted.

**A-W02 Manage members:** A-S02 → Invite / Remove member. Edge cases: removed member's expenses stay; invite flow not seen.

## Navigation

Unknown beyond the two screens; no routes are visible.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Expense | id (unknown) | merchant, amount (decimal, inferred), currency, date, category | budget_id → Budget | documented | A-E09, A-E03 |
| Budget | id (unknown) | name, limit (decimal, inferred), currency, owner | members ↔ User | inferred | A-E07, A-E11 |
| BudgetMember | unknown | budget_id, user_id, role (owner/member) | Budget, User | inferred | A-E05, A-E07 |
| User | unknown | email, home_currency | | inferred | A-E02, A-E05 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/v2/expenses?budget_id=` | PAT | budget_id | list of expenses | unknown | A-E09 |
| POST | `/v2/expenses` | PAT | not described | not described | unknown | A-E10 |
| GET | `/v2/budgets` | PAT | - | budgets of the token's user | unknown | A-E11 |

Rate limit 60/min (A-E12). Pagination and error format unknown.

## Authentication and authorization

API: personal access token in the Authorization header (documented). App sign-in method and sessions: unknown.
Roles per budget: owner (invites, removes members) and member (sees all budget expenses). Evidence A-E05, A-E07, A-E12.

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| Receipt OCR (unknown provider) | extract merchant, date, total | A-F01 | A-E01 |
| Exchange rates (unknown provider) | convert to home currency | A-F02 | A-E02 |
| Email (unknown provider) | invitations | A-F04 | A-E05 |

## Architecture and stack

Unknown: closed product. Inferred only that it is a phone-capable client with a hosted backend and a versioned REST API.

## Configuration

None visible.

## Error handling

Wrong scan values are fixed by hand on the review screen. Everything else (rate-limit response, failed scans) is unknown.

## Unknowns

See `source.json` → `unknowns` (14 items): extraction engine and date errors, category on scans, exchange-rate
rules, home vs budget currency, what a monthly reset does, invite flow, access after removal, ownership,
field types, sign-in and token details, stack, category values, and the live product (not inspectable here).
What would fill them: a session in the user's Tallyho account with the user present and a browser approved,
and a few of the user's receipts where the date came out wrong.
