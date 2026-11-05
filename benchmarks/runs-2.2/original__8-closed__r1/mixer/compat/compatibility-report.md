# Compatibility report

Scope: kept features only. Apps: A, B.

| Severity | Count |
|---|---|
| high | 2 |
| medium | 7 |
| info | 3 |

## application:business-rule:removed-member-expenses

- **Conflict:** The user saw a removed member's earlier expenses stay in the budget (my-notes.md:2) and did not say whether that is wanted. Whether the removed member can still see them is unknown. Getting this wrong either changes budget totals retroactively or leaks budget data to someone who was removed.
- **Affected applications:** A
- **Affected features:** M05
- **Severity:** high
- **Possible solutions:** Keep the expenses in the budget, mark them 'former member', revoke the removed member's access to the whole budget, and tell the owner before removing; Move the removed member's expenses out of the budget into their personal expenses; Ask the owner at removal time which of the two to do
- **Recommended resolution:** Keep the expenses in the budget (totals stay right, matching Tallyho), mark them as from a former member, revoke all access for the removed member, and show the owner a confirmation that explains this; offering a choice can come later if the user wants it
- **User approval required:** yes
- **Status:** resolved (Keep the removed member's expenses in the budget (totals unchanged), mark them as from a former member, revoke all of the removed member's access to the budget and its expenses on every read, and show the owner a confirmation explaining this before removal. A per-removal choice can be added later if the user wants it.)

## database:business-rule:money-and-currency

- **Conflict:** Spendly stores amount_cents (integer cents) with no currency; Tallyho stores amount plus currency (shown with decimals, e.g. 12.40 GBP, type undocumented) and converts foreign receipts to a home currency. A budget's 'spent of limit' is shown in one currency. Summing mixed currencies or mixing decimal and integer amounts would give wrong totals.
- **Affected applications:** A, B
- **Affected features:** M01, M03, M06, M08
- **Severity:** high
- **Possible solutions:** Integer minor units plus ISO 4217 currency on every expense and budget; an expense in a budget must be in the budget's currency; conversion deferred (M02); Integer minor units plus currency, and build conversion now with an exchange-rate provider; Decimal amounts with currency
- **Recommended resolution:** Integer minor units plus ISO 4217 currency everywhere; an expense added to a budget must match the budget's currency (the scan review asks for the amount in the budget's currency when the receipt differs); conversion stays deferred
- **User approval required:** yes
- **Status:** resolved (Integer minor units (bigint) plus ISO 4217 currency on every expense and budget; an expense in a budget must be in the budget's currency; when a scanned receipt is in another currency the review screen flags it and asks for the amount in the budget's currency; conversion (M02) stays deferred.)

## application:authorization:invitation-rules

- **Conflict:** Tallyho does not document who may invite, expiry or reuse of invitations; a reusable or non-expiring link would let anyone holding it join a budget and see its expenses.
- **Affected applications:** A
- **Affected features:** M04
- **Severity:** medium
- **Possible solutions:** Owner-only invites, single-use token, 7-day expiry, accepted only by an account with the invited email; Any member may invite
- **Recommended resolution:** Owner-only, single-use, 7-day expiry, bound to the invited email
- **User approval required:** no
- **Status:** resolved (Owner-only invites; single-use random token stored hashed; 7-day expiry; accepted only by a signed-in account whose verified email matches the invitation.)

## application:business-rule:category-on-scanned-expenses

- **Conflict:** Spendly requires one of four categories on every expense; Tallyho's scan fills only merchant, date and total, so a scanned expense has no category from the scan.
- **Affected applications:** A, B
- **Affected features:** M01, M09
- **Severity:** medium
- **Possible solutions:** Category is a required choice on the scan review screen, no default; Default scanned expenses to 'other'; Guess the category from the merchant
- **Recommended resolution:** Required choice on the review screen with no default, so 'other' does not fill up silently; a merchant-based suggestion can come later
- **User approval required:** no
- **Status:** resolved (Category is a required choice on the scan review screen with no default; scanning never sets it.)

## application:business-rule:monthly-reset-semantics

- **Conflict:** Tallyho documents only that budgets 'reset monthly'; day, time zone, rollover and whether expenses are kept are unknown.
- **Affected applications:** A
- **Affected features:** M07
- **Severity:** medium
- **Possible solutions:** Spent total covers the current calendar month in the budget's time zone; expenses kept; no rollover; computed at read time; Reset on the budget's creation day each month; Scheduled job that archives and zeroes
- **Recommended resolution:** Calendar month in the budget's time zone, expenses kept, no rollover, computed at read time
- **User approval required:** no
- **Status:** resolved (Spent total = expenses dated in the current calendar month in the budget's time zone; expenses are kept; no rollover; computed at read time. These are the unified app's own rules, not Tallyho's (undocumented).)

## application:business-rule:personal-vs-budget-expenses

- **Conflict:** Spendly expenses belong to no one and no budget; Tallyho expenses are listed per budget. The unified app must say where an expense lives and who sees it.
- **Affected applications:** A, B
- **Affected features:** M03, M06, M08
- **Severity:** medium
- **Possible solutions:** Every expense has an author; budget is optional; without a budget only the author sees it; Every expense must be in a budget; each user gets a personal budget
- **Recommended resolution:** Author required, budget optional; a personal expense is visible to its author only
- **User approval required:** no
- **Status:** resolved (Every expense has an author; budget is optional; a personal expense is visible to its author only.)

## application:business-rule:scanned-date-trust

- **Conflict:** Tallyho's scanned date is often wrong (user's notes); saving it unchecked would put expenses in the wrong month and so the wrong budget period (M07).
- **Affected applications:** A
- **Affected features:** M01, M07
- **Severity:** medium
- **Possible solutions:** Mark the scanned date for checking and require confirmation; replace missing or implausible dates with today, flagged; Ignore the scanned date and always use today; Trust the scanned date
- **Recommended resolution:** Mark it for checking and require confirmation; implausible (future or more than 90 days old) or missing dates become today, flagged
- **User approval required:** no
- **Status:** resolved (Scanned date shown as 'check this date' and must be confirmed before saving; missing, future or more-than-90-days-old dates are replaced by today and flagged.)

## application:data-protection:receipt-images

- **Conflict:** Receipt photos are personal data (may show card digits, addresses); Tallyho's storage and retention are unknown, and sending them to an OCR provider is a data transfer.
- **Affected applications:** A
- **Affected features:** M01
- **Severity:** medium
- **Possible solutions:** Private object storage, access through the expense's permission check, delete with the expense; OCR provider chosen by the user with a no-retention option, or on-device/self-hosted OCR; Do not keep images after extraction
- **Recommended resolution:** Private storage behind the expense's permission check, deleted with the expense; OCR provider is the user's choice behind an adapter (decided at implementation, needs their account and keys)
- **User approval required:** no
- **Status:** resolved (Receipt images in private storage, served only through the expense's permission check, deleted with the expense; OCR provider behind an adapter, chosen by the user at implementation (their account and keys; prefer a no-retention option). Not decided in plan mode.)

## database:duplicate-entity:expense

- **Conflict:** Expense exists in A:Expense, B:Expense; fields not shared: budget_id (only A), currency (only A), date (only A), merchant (only A), note (only B)
- **Affected applications:** A, B
- **Affected features:** M01, M03, M06, M08, M09
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge into one entity; list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (One Expense entity: id, author_id, budget_id (nullable), amount_minor, currency, spent_on, merchant, category, note, receipt_id, created_at, updated_at; every field's origin in architecture.json.)

## database:unknown-type:expense.amount

- **Conflict:** Expense.amount type is not known for A
- **Affected applications:** A, B
- **Affected features:** M01, M03, M06, M08, M09
- **Severity:** info
- **Possible solutions:** Read the source's schema or migrations for the type; Record it as unknown and decide in the architecture
- **Recommended resolution:** Find the real type before designing the merged entity
- **User approval required:** no
- **Status:** resolved (Tallyho's type cannot be found (closed, undocumented); not needed because no Tallyho data is imported. Unified type: bigint minor units (Spendly's integer cents).)

## database:unknown-type:expense.category

- **Conflict:** Expense.category type is not known for A
- **Affected applications:** A, B
- **Affected features:** M01, M03, M06, M08, M09
- **Severity:** info
- **Possible solutions:** Read the source's schema or migrations for the type; Record it as unknown and decide in the architecture
- **Recommended resolution:** Find the real type before designing the merged entity
- **User approval required:** no
- **Status:** resolved (Tallyho's type and values are unknown; its category field is dropped (M10). Unified: text constrained to food, travel, home, other.)

## database:unknown-type:expense.primary-key

- **Conflict:** Expense primary key type is not known for A, B; find it before deciding the merged key
- **Affected applications:** A, B
- **Affected features:** M01, M03, M06, M08, M09
- **Severity:** info
- **Possible solutions:** Read the source's schema or migrations for the type; Record it as unknown and decide in the architecture
- **Recommended resolution:** Find the real type before designing the merged entity
- **User approval required:** no
- **Status:** resolved (Neither source has a known key (Spendly none, Tallyho undocumented). Unified: uuid generated by the app.)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Expense | A, B | add fields that only some sources have: budget_id (only A), currency (only A), date (only A), merchant (only A), note (only B) (low); A.Expense.merchant: unknown to text can lose or reject values (high); A.Expense.amount: unknown to integer can lose or reject values (high); A.Expense.currency: unknown to text can lose or reject values (high); A.Expense.date: unknown to date can lose or reject values (high); A.Expense.category: unknown to text can lose or reject values (high); A.Expense.budget_id: unknown to uuid can lose or reject values (high) | high | amount, budget_id, category, currency, date, merchant | yes |
| Budget | A | A.Budget.name: unknown to text can lose or reject values (high); A.Budget.limit: unknown to integer can lose or reject values (high); A.Budget.currency: unknown to text can lose or reject values (high) | high | currency, limit, name | yes |
| Membership | A | A.BudgetMember.budget_id: unknown to uuid can lose or reject values (high); A.BudgetMember.user_id: unknown to uuid can lose or reject values (high); A.BudgetMember.role: unknown to text can lose or reject values (high) | high | budget_id, role, user_id | yes |
| User | A | A.User.email: unknown to text can lose or reject values (high) | high | email | yes |
