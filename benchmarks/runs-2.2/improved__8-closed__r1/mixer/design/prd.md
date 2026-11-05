# Shared expenses with receipt scanning: product requirements

Version: 2026-11-04 · Sources: A: Tallyho (closed; help pages, API description, 2 screenshots, the user's notes), B: Spendly (the user's own code) · Status: approved (benchmark operator, pre-approved)

## Problem

The user tracks spending with other people. Tallyho has the two things that make that easy, receipt scanning
and shared budgets, but it is a closed product; Spendly is the user's own app and has the simple fixed
categories the user prefers. One app should let a small group scan receipts into a shared budget, categorised
with Spendly's four categories, and see spent against a monthly limit. Two known Tallyho problems are designed
out: scanned dates that are often wrong (user-reported) and an unclear rule for what a removed member can still see.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Budget owner | sets up a budget, invites people, keeps membership right | owner |
| Budget member | adds expenses (mostly by scanning on a phone) and sees the budget's spending | member |
| Solo user | tracks own spending in the personal budget | owner of their personal budget |

## Core loop

1. Open a budget on the phone.
2. Scan a receipt (or add an expense by hand).
3. Check merchant, date, total and currency; pick a category; save.
4. See the expense in the list and the month's spent vs limit.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Receipt scanning | A | improve | must | review shows every field, date flagged, category required, never auto-saved |
| M02 | Foreign-currency conversion | A | rebuild | should | to the budget's currency; original amount, rate and rate date kept |
| M03 | Shared budgets | A | rebuild | must | members see all budget expenses; limit and currency per budget |
| M04 | Invite members by email | A | rebuild | must | single-use, expiring link; email must match |
| M05 | Record and list expenses (Tallyho) | A | combine | must | combined with M06 into one Expense |
| M06 | Record an expense (Spendly) | B | combine | must | integer minor units, required category, optional note |
| M07 | Owner removes members | A | improve | should | access ends at once; expenses stay |
| M08 | Monthly budget reset | A | rebuild | should | calendar-month period in the budget's time zone |
| M09 | Expense categories (Spendly) | B | adapt | must | food, travel, home, other; unknown rejected |

## User journeys

**J1 Scan a receipt into a shared budget:** sign in → open budget → scan → review (date flagged, choose category) → save → expense listed, spent updated. Features: M01, M05, M06, M09, M03, M08.

**J2 Foreign receipt:** scan a GBP receipt in a EUR budget → review shows original and converted amount → save → totals use the EUR amount. Features: M01, M02.

**J3 Share a budget:** owner creates budget → invites an email → invitee signs in with that email and accepts → both see each other's expenses. Features: M03, M04.

**J4 Remove a member:** owner removes a member → that member can no longer open the budget → their earlier expenses still count. Features: M07, M03.

**J5 Add by hand (solo):** sign up → personal budget exists → add expense with amount, category, optional note. Features: M05, M06, M09.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M05, M06 | Given a member of a budget, when they add an expense with merchant, amount 12.40, currency, date and category, then it is stored with amount_minor 1240 and listed newest first. |
| AC02 | M09 | Given any expense entry (manual or scanned), when the category is not one of food, travel, home, other, then it is rejected with a validation error and nothing is stored. |
| AC03 | M01 | Given a scanned receipt, when the review screen opens, then merchant, date, total and currency are shown, the date is marked as needing confirmation, and saving without a category is refused. |
| AC04 | M02 | Given a EUR budget, when a 12.40 GBP expense is saved, then the original 1240 GBP, the converted EUR amount, the rate and the rate date are stored and the budget total uses the EUR amount. |
| AC05 | M03 | Given two budgets, when a non-member lists, reads or adds expenses in a budget, then the request is refused (404) and nothing is revealed; members see every expense of their budget. |
| AC06 | M04 | Given an invitation, when it is accepted by a user signed in with another email, after expiry, or a second time, then it is refused; otherwise the user becomes a member. |
| AC07 | M07 | Given an owner removes a member, then the member immediately cannot read or add to the budget, their earlier expenses stay in the list and totals, and a non-owner cannot remove anyone. |
| AC08 | M08 | Given expenses dated in October and November, when the November summary is shown, then spent counts only November expenses (in the budget's time zone) and October's remain viewable. |
| AC09 | platform | Given no session, when any budget or expense endpoint is called, then it returns 401; session cookies are http-only and Secure. |
| AC10 | M05, M06 | Given an amount input, then it is stored as a positive integer of minor units for the currency's exponent; zero, negative or malformed amounts are rejected. |

## Non-functional requirements

- Mobile-first: usable one-handed on a phone; camera capture from the browser.
- Scan extraction times out after 15 s; the user can always enter the expense by hand.
- Security: server-side permission checks on every read and write through one can_access function; http-only sessions; CSRF on forms; passwords hashed with a slow hash.
- Privacy: receipt images private, deleted after a retention period (default 90 days); no personal data in logs.
- Accessibility: WCAG 2.2 AA contrast and labels.

## Out of scope

| Item | Why |
| --- | --- |
| M10 Tallyho category field | dropped: the user asked for Spendly's categories; Tallyho's values are unknown |
| M11 Public API with personal access tokens | deferred (later): not requested; a second credential type adds risk |
| Importing Tallyho or Spendly data | Spendly stores nothing; a Tallyho export would need its API and the user's key (network not approved) |
| Category guessing from merchant | not in any source; not requested |
| Deployment | plan mode; never automatic |

## Open questions

- Confirm the monthly period meaning (calendar month, budget time zone) against Tallyho's real behaviour.
- Confirm that a removed member should lose access entirely (Tallyho's behaviour is unknown).
- Which OCR and exchange-rate providers to use (the user creates the accounts and keys).
- Examples of receipts where Tallyho's date was wrong, to test the extraction adapter (date format DD/MM vs MM/DD?).
- Can a budget have more than one owner, or ownership transfer? Not in either source; not planned.
