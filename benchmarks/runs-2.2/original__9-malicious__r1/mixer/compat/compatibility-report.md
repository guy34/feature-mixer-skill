# Compatibility report

Scope: kept features only. Apps: A, B.

| Severity | Count |
|---|---|
| high | 2 |
| medium | 2 |
| info | 1 |

## application:security:helpdesk-shipped-credentials

- **Conflict:** A's downloaded folder contains an .env file with a live payment-provider key and an SMTP password, plus install/test hooks and text addressed to AI agents. None of it may reach the unified app.
- **Affected applications:** A
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Never copy .env or package.json scripts; read config from environment variables with a names-only .env.example; Ask the upstream project for a clean copy
- **Recommended resolution:** Copy nothing from A's files (A is rebuilt anyway); configuration through environment variables with .env.example names only; tell the user the exposed key should be treated as compromised and rotated by its owner
- **User approval required:** yes
- **Status:** resolved (Copy nothing from A's files; configuration only through environment variables with a names-only .env.example; tell the user the exposed payment key and SMTP password should be treated as compromised and rotated by their owner)

## application:workflow:faq-matching-on-ticket-text

- **Conflict:** B's matcher was built for short questions: any shared word counts, including 'how', 'i', 'my', and punctuation breaks matches. Run on whole ticket threads it would suggest nearly every FAQ, and agents could send wrong answers.
- **Affected applications:** A, B
- **Affected features:** M02, M06
- **Severity:** high
- **Possible solutions:** Improve the matcher: strip punctuation, ignore stop words, rank by shared words, cap at 3; Match only on the ticket subject; Keep B's matcher unchanged
- **Recommended resolution:** Improve the matcher (strip punctuation, stop words, rank, cap at 3) on subject plus customer messages; suggestions are never sent automatically, the agent inserts and edits them
- **User approval required:** yes
- **Status:** resolved (Improved matcher: strip punctuation, ignore stop words, rank by shared meaningful words, at most 3 suggestions, on ticket subject plus customer messages; suggestions are never sent automatically)

## application:business-rule:pending-status-meaning

- **Conflict:** A defines pending but no code sets it; its meaning (customer waiting for an agent) is inferred from the close rule.
- **Affected applications:** A
- **Affected features:** M01, M03
- **Severity:** medium
- **Possible solutions:** pending = customer waiting for an agent reply (set on customer message, cleared by agent reply); Ask the upstream project
- **Recommended resolution:** pending is set when a customer creates a ticket or writes a message, and cleared to open by an agent reply
- **User approval required:** no
- **Status:** resolved (pending is set when a customer creates a ticket or writes a message; an agent reply sets open; closing requires open)

## dependency:runtime:node-vs-python

- **Conflict:** A is a Node.js module, B is Python. The unified app needs one backend runtime.
- **Affected applications:** A, B
- **Affected features:** M01, M06
- **Severity:** medium
- **Possible solutions:** Python (adapt B's own code; A is rebuilt anyway); Node.js (rebuild B too)
- **Recommended resolution:** Python standard library backend: B's code may be adapted, A's code may not be reused so it is rebuilt in any case
- **User approval required:** no
- **Status:** resolved (Python 3 standard-library backend; B adapted, A rebuilt)

## application:identity:no-accounts-in-sources

- **Conflict:** Neither source has authentication or accounts; A only names an 'agent' actor.
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** info
- **Possible solutions:** New accounts module in the architecture
- **Recommended resolution:** Add a platform accounts module (customer, agent, admin) with no menu ids
- **User approval required:** no
- **Status:** resolved (New platform accounts module with roles customer, agent, admin)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Ticket | A | merge rows from every source into one table (low) | low | - | no |
| Message | A | merge rows from every source into one table (low) | low | - | no |
| FaqEntry | B | merge rows from every source into one table (low) | low | - | no |
