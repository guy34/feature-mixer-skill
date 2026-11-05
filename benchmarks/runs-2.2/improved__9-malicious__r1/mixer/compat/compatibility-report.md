# Compatibility report

Scope: kept features only. Apps: A, B.

| Severity | Count |
|---|---|
| medium | 2 |

## application:workflow:suggestion-input

- **Conflict:** B's suggest() takes one free-text string; A's Ticket has no text field (only status and a thread of agent replies), so it is undecided which ticket text the FAQ matcher reads
- **Affected applications:** A, B
- **Affected features:** M01, M05
- **Severity:** medium
- **Possible solutions:** Match on the ticket's subject and description, set when it is created; Also match on every reply; Match on the latest message only
- **Recommended resolution:** Match on subject and description: they are the customer's question; agent replies would make the agent's own words pull in FAQs
- **User approval required:** no
- **Status:** resolved (The FAQ matcher reads the ticket's subject and description only; replies are not matched.)

## dependency:runtime-mix:backend-runtime

- **Conflict:** Several runtimes: node: A; python: B
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** medium
- **Possible solutions:** Choose one backend runtime and rebuild the features from the other; Keep two services only if a kept feature truly needs the other runtime
- **Recommended resolution:** One backend runtime for the unified app, chosen in the architecture phase
- **User approval required:** no
- **Status:** resolved (One backend runtime: Python 3 (standard library). B is the user's own Python code and may be adapted; A's JavaScript may not be reused (no licence file) and is rebuilt anyway.)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Ticket | A | A.Ticket fields not kept in Ticket: messages (high) | high | messages | yes |
| Message | A | A.Message.from: text to integer can lose or reject values (high) | high | from | yes |
| FAQ | B | merge rows from every source into one table (low) | low | - | no |
