# Unified expense app: product requirements

Version: 2026-11-04 · Sources: A: Tallyho (closed, rebuilt from behaviour), B: Spendly (user's own code) · Status: approved (benchmark operator, pre-approved)

## Problem

The user tracks spending alone and with other people. Tallyho has receipt
scanning and shared budgets but is closed, and its scanned dates are often
wrong; Spendly is the user's own tiny app with the four categories they want
but no persistence, sharing or scanning. One app should let them scan or type
an expense, file it under one of Spendly's categories, and share budgets with
the people they spend with.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| The user | Record their own spending quickly, mostly on a phone | user; budget-owner of the budgets they create |
| People they share with (household, friends) | See and add to a shared budget | budget-member |
| Someone removed from a budget | Nothing further | former member: no access |

## Core loop

1. Sign in on the phone.
2. Scan a receipt (or type an expense).
3. Check the date, pick a category, choose a budget (or keep it personal), save.
4. See the budget's spent of limit for this month.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M06 + M08 | Expense recording (U01) | A + B | combine | must | Tallyho's merchant, currency, date, budget + Spendly's integer cents, category, note |
| M09 | Fixed categories food, travel, home, other (U02) | B | adapt | must | Spendly's list and rule, reused (own code) |
| M01 | Receipt scanning (U03) | A | improve | must | Rebuilt; date must be confirmed; category chosen by the user |
| M03 | Shared budgets (U04) | A | rebuild | must | One owner, members see all expenses, spent of limit in one currency |
| M04 | Invite by email (U05) | A | rebuild | must | Owner-only, single-use, 7-day expiry |
| M07 | Monthly budget period (U07) | A | rebuild | should | Calendar month in the budget's time zone |
| M05 | Owner removes members (U06) | A | improve | should | Expenses stay, marked former member; access revoked |

## User journeys

**J1 Record an expense by hand:** /expenses/new → amount, currency, date, category, note, optional budget → save → listed on /. Features: M06, M08, M09.

**J2 Share a budget:** /budgets/new → /budgets/{id}/members → invite by email → invitee opens /invitations/{token}, signs in, accepts → both see the budget's expenses and spent of limit. Features: M03, M04, M07.

**J3 Scan a receipt:** /scan → photo → /scan/{receipt_id} review (merchant, total, date flagged for checking) → confirm date, pick category, pick budget → save → expense listed and counted in the budget. Features: M01, M06, M09, M03.

**J4 Remove a member:** /budgets/{id}/members → Remove → confirmation explaining expenses stay → removed; their expenses show as former member; they lose access. Features: M05.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M08, M09 | Given a signed-in user, when they add an expense of 1240 minor units in EUR with category food, then it is stored and listed with exactly those values. |
| AC02 | M09 | Given any expense create or edit (typed or scanned), when the category is not one of food, travel, home, other (including wrong case or empty), then it is rejected with a validation error naming the allowed values and nothing is stored. |
| AC03 | M08 | Given an expense create, when the amount is zero, negative, non-integer or above the upper bound, then it is rejected with a validation error. |
| AC04 | M06 | Given a personal expense, when another user requests it, then the response is 404. |
| AC05 | M03 | Given a budget with members, when any current member lists its expenses, then they see every member's expenses; a non-member gets 404. |
| AC06 | M03 | Given a budget in EUR, when someone adds an expense in GBP to it, then it is rejected (conversion is deferred). |
| AC07 | M04 | Given the owner invites an email, then one email with a single-use link is sent; a member who is not the owner cannot invite (403). |
| AC08 | M04 | Given an invitation, when it is accepted by a verified account with the invited email within 7 days, then that account becomes a member; a second use, an expired link or a different email is refused. |
| AC09 | M07 | Given expenses dated 31 Jan and 1 Feb in the budget's time zone, when the February summary is requested, then only the 1 Feb expense counts; January's expense still exists and shows in January's summary. |
| AC10 | M01 | Given a receipt photo, when it is uploaded, then a draft with merchant, date and total is returned for review and no expense exists until the user confirms. |
| AC11 | M01 | Given a scan whose date is missing, in the future or older than 90 days, then the draft date is today and flagged; saving requires the user to confirm the date. |
| AC12 | M01 | Given a scan draft, when the user saves without choosing a category, then it is rejected; scanning never sets a category. |
| AC13 | M01 | Given the OCR reader fails or times out, then the review screen opens with empty fields for manual entry and the image is kept. |
| AC14 | M05 | Given the owner removes a member, then the member's expenses remain in the budget and the totals are unchanged, they are shown as from a former member, and the removed member gets 404 for the budget and every one of its expenses. |
| AC15 | M05 | Given a member who is not the owner, when they try to remove someone, then 403; the owner cannot remove themself. |
| AC16 | M01 | Given a receipt image, when anyone other than the uploader or a current member with access to its expense requests it, then 404. |

## Non-functional requirements

- Security: passwords hashed with Django's slow hasher; http-only secure session cookie; CSRF on all writes; one permission function used by every query; non-members get 404; invitation tokens stored hashed; no personal data or secrets in logs.
- Privacy: receipt images private, deleted with their expense or after 24 hours if never confirmed; OCR provider chosen by the user, preferring one that does not retain images.
- Performance: pages under 1 s at household scale; OCR timeout 20 s with manual fallback.
- Accessibility: WCAG 2.2 AA contrast, labelled fields, flagged date announced to screen readers, full keyboard use.
- Platforms: current mobile Safari and Chrome (camera via file input), desktop browsers.

## Out of scope

| Item | Why |
| --- | --- |
| M02 Foreign-currency conversion (deferred) | could; needs an exchange-rate provider and undocumented rules; currency is stored on every expense so it can be added later |
| M11 Public API with personal tokens (deferred) | could; not requested; adds token management and rate limiting |
| M10 Tallyho's category field (dropped) | user chose Spendly's categories; Tallyho's list is unknown |
| Importing Tallyho data | not requested; would need network, the user's token and a migration plan |
| Native mobile apps, deployment | not requested; no automatic deployment |

## Open questions

- Which OCR provider (needs the user's account and keys) - decide before V3.
- Does the user want removed members' expenses to stay in the budget (as Tallyho does, and as planned), or to move with the member? Their note was neutral.
- Home currency and conversion: when M02 is picked up, which rate source and which date's rate.
- Should members other than the owner be able to invite? Planned owner-only.
- Hosting and email provider (user's accounts).
