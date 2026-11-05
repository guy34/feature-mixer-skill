# Compatibility report

Scope: kept features only. Apps: A, B.

| Severity | Count |
|---|---|
| high | 9 |
| medium | 4 |
| info | 1 |

## application:authorization-model:model

- **Conflict:** Authorization models differ (A: budget membership: members see a budget's expenses; owner manages members; B: none (single-user library function))
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one authorization model and express the others' rules in it
- **Recommended resolution:** One authorization model with one permission check function
- **User approval required:** yes
- **Status:** resolved (One model: budget membership with roles owner and member. Every expense belongs to a budget; each user gets a personal budget at sign-up (Spendly's single-user use). One can_access(user, action, record) function used by every route and query.)

## application:business-rule:conversion-target-currency

- **Conflict:** Tallyho converts foreign receipts to the user's home currency (documented), but its shared budget totals are in one budget currency (screenshot: EUR). Members of one budget can have different home currencies, so 'home currency' totals would disagree between members. Spendly records no currency at all.
- **Affected applications:** A, B
- **Affected features:** M02, M03, M06
- **Severity:** high
- **Possible solutions:** Convert to the budget's currency for the expense and its totals; keep the original amount and currency; Convert to each viewer's home currency at display time; No conversion: reject expenses not in the budget currency
- **Recommended resolution:** Convert to the budget's currency, store original amount, currency, rate and rate date; every member sees the same totals
- **User approval required:** yes
- **Status:** resolved (Convert to the budget's currency. Store original amount and currency, converted amount in budget currency, rate and rate date (receipt date). Totals use the converted amount; every member sees the same totals.)

## application:permission:access-after-member-removal

- **Conflict:** Tallyho documents that the owner can remove members, and the user saw that a removed member's earlier expenses stay in the budget; whether the removed member can still see the budget is not known. Left unclear, a removed person might keep seeing everyone's spending.
- **Affected applications:** A
- **Affected features:** M03, M07
- **Severity:** high
- **Possible solutions:** Keep their expenses in the budget, end their access at once; Delete or move their expenses out of the budget on removal; Let them keep read access to their own past expenses
- **Recommended resolution:** Keep their expenses (totals stay correct, as in Tallyho) and end all their access to the budget at once
- **User approval required:** yes
- **Status:** resolved (On removal, the member loses all access to the budget immediately; their earlier expenses stay in the budget, attributed to them, and keep counting in totals. Only the owner may remove; the owner cannot remove themself.)

## application:session:session

- **Conflict:** Session mechanisms differ (A: unknown for the app; bearer token in the authorization header for the api; B: none)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one session mechanism (http-only cookie sessions are the safer default for web apps); Use tokens only where a client cannot hold cookies
- **Recommended resolution:** One session mechanism for the whole app
- **User approval required:** yes
- **Status:** resolved (Server-side sessions in http-only, Secure, SameSite=Lax cookies for the web app. Tallyho's personal access tokens are not built (M11 deferred).)

## application:tenancy-model:tenancy

- **Conflict:** tenant boundaries differ (A: budget (inferred), B: none)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one tenant boundary (organisation, workspace...) and assign every row to a tenant; Keep single-tenant data in one default tenant, decided with the user
- **Recommended resolution:** One tenant model; every tenant-owned row has a tenant key and every query filters by it
- **User approval required:** yes
- **Status:** resolved (The budget is the tenant boundary: Expense, BudgetMember and Invitation carry budget_id and every query filters by the caller's memberships. Nothing is shared across budgets.)

## application:workflow:scanned-expense-category

- **Conflict:** Tallyho's scan fills merchant, date and total but no category is documented; Spendly rejects any expense without a known category. A scanned receipt would either fail to save or need a silent default.
- **Affected applications:** A, B
- **Affected features:** M01, M06, M09
- **Severity:** high
- **Possible solutions:** Require the user to pick a category on the review screen before saving; Default scanned expenses to 'other'; Guess a category from the merchant
- **Recommended resolution:** Require a category on the review screen (no silent default); Spendly's rule stays intact
- **User approval required:** yes
- **Status:** resolved (Category is required on the scan review screen; no silent default; Spendly's reject-unknown rule applies to scanned expenses too.)

## database:entity-meaning:expense

- **Conflict:** Expense may not mean the same thing in A, B: A describes it as 'A spending record in a budget, as exposed by the public API', B as 'A spending record: amount in cents, a category, an optional note'
- **Affected applications:** A, B
- **Affected features:** M01, M02, M05, M06, M09
- **Severity:** high
- **Possible solutions:** Keep them as separate entities with distinct names (for example UserAccount and LedgerAccount); Merge them only if the user confirms they describe the same thing
- **Recommended resolution:** Ask the user; never merge entities because their names match
- **User approval required:** yes
- **Status:** resolved (Same concept in both (one spending record). One Expense entity: Tallyho's merchant, currency, date, budget plus Spendly's integer amount, category and note.)

## database:field-type:expense.amount

- **Conflict:** Expense.amount types differ (A: number, B: integer)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M05, M06, M09
- **Severity:** high
- **Possible solutions:** Choose the wider type and convert the narrower data; Split into two fields if they mean different things
- **Recommended resolution:** One type per field; convert in a migration
- **User approval required:** yes
- **Status:** resolved (amount_minor: integer (bigint) minor units. Decimal user input such as 12.40 is parsed to 1240 using the currency's exponent; zero and negative rejected.)

## database:units:expense.amount.unit

- **Conflict:** Expense.amount unit differs (A: major units, B: minor units (cents))
- **Affected applications:** A, B
- **Affected features:** M01, M02, M05, M06, M09
- **Severity:** high
- **Possible solutions:** Store one unit (for example integer cents in UTC) and convert at import; Store the unit with the value
- **Recommended resolution:** One unit per field, converted in the migration and tested
- **User approval required:** yes
- **Status:** resolved (Minor units everywhere (Spendly's unit), with an ISO 4217 currency on every amount; display formats to major units.)

## application:business-rule:monthly-reset-meaning

- **Conflict:** 'Budgets reset monthly' does not say what resets, on which day or in which time zone.
- **Affected applications:** A
- **Affected features:** M08
- **Severity:** medium
- **Possible solutions:** Calendar-month period in the budget's time zone; spent counts expenses dated in it; nothing deleted; Rolling 30-day window; Archive expenses at month end
- **Recommended resolution:** Calendar-month period in the budget's time zone, by expense date; nothing deleted
- **User approval required:** no
- **Status:** resolved (Budget period is the calendar month in the budget's time zone; spent vs limit counts expenses dated in that month; nothing is deleted; past months stay viewable. To confirm with the user.)

## database:data:expense-currency-missing-in-b

- **Conflict:** Spendly expenses have no currency or date; Tallyho expenses need both.
- **Affected applications:** A, B
- **Affected features:** M05, M06
- **Severity:** medium
- **Possible solutions:** Currency defaults to the budget currency and date to today when not given; Make both required on every entry
- **Recommended resolution:** Default currency to the budget currency and date to today in the entry form; both stored as required columns
- **User approval required:** no
- **Status:** resolved (currency and date are required columns; the entry form defaults currency to the budget currency and date to today.)

## database:deletion-semantics:expense

- **Conflict:** deleting a Expense means different things (A: hard delete (no marker found), B: hard)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M05, M06, M09
- **Severity:** medium
- **Possible solutions:** Choose soft or hard delete for the merged entity and convert the other source's rows; Keep deleted rows from the soft-delete source as archived
- **Recommended resolution:** Soft delete for merged data unless the user decides otherwise
- **User approval required:** no
- **Status:** resolved (Hard delete, allowed to the member who added the expense or the budget owner (Tallyho's delete behaviour is unknown; Spendly has none).)

## database:duplicate-entity:expense

- **Conflict:** Expense exists in A:Expense, B:Expense; fields not shared: budget_id (only A), currency (only A), date (only A), merchant (only A), note (only B)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M05, M06, M09
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge only once it is confirmed they mean the same thing; then list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (Merged into one Expense entity (see entity-meaning).)

## database:unknown-type:expense.primary-key

- **Conflict:** Expense primary key type is not known for A, B; find it before deciding the merged key
- **Affected applications:** A, B
- **Affected features:** M01, M02, M05, M06, M09
- **Severity:** info
- **Possible solutions:** Read the source's schema or migrations for the type; Record it as unknown and decide in the architecture
- **Recommended resolution:** Find the real type before designing the merged entity
- **User approval required:** no
- **Status:** resolved (New uuid primary key; neither source's key is carried over (no data is migrated).)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Expense | A, B | convert amount to one type (A: number, B: integer) (high); add fields that only some sources have: budget_id (only A), currency (only A), date (only A), merchant (only A), note (only B) (low); A.Expense.amount: number to integer can lose or reject values (high); A.Expense.budget_id: unknown to uuid can lose or reject values (high); convert amount to one unit (A: major units, B: minor units (cents)) and test the conversion (high); decide soft or hard delete; rows marked deleted in one source must not reappear or vanish (high) | high | amount, budget_id | yes |
| Budget | A | A.Budget.limit: number to integer can lose or reject values (high); A.Budget.owner_id: unknown to uuid can lose or reject values (high) | high | limit, owner_id | yes |
| BudgetMember | A | A.BudgetMember.budget_id: unknown to uuid can lose or reject values (high); A.BudgetMember.user_id: unknown to uuid can lose or reject values (high) | high | budget_id, user_id | yes |
| User | A | merge rows from every source into one table (low) | low | - | yes |
