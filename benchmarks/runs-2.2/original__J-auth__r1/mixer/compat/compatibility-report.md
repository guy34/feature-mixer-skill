# Compatibility report

Scope: kept features only. Apps: A, B, C.

| Severity | Count |
|---|---|
| critical | 2 |
| high | 7 |
| medium | 2 |

## application:account-linking:federated-email-join

- **Conflict:** B ignores email_verified; joining a federated sign-in to a password account by an unverified email would let anyone who controls a provider account claim another person's account
- **Affected applications:** A, B
- **Affected features:** M01, M03
- **Severity:** critical
- **Possible solutions:** Join only when the provider says the email is verified; otherwise create a separate account; Never join automatically; require the user to link from a signed-in session
- **Recommended resolution:** Join only when email_verified is true; otherwise a separate account (the user's decision)
- **User approval required:** yes
- **Status:** resolved (A federated sign-in joins an existing account only when the provider says the email is verified (email_verified is True); otherwise it creates a separate account, and an unverified email never takes ownership of an address)

## database:primary-key:user

- **Conflict:** User primary keys differ (A: integer, B: text)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M03
- **Severity:** critical
- **Possible solutions:** Pick one key type for the merged entity and re-key the other source's rows; Keep a legacy_id column holding the old key during migration
- **Recommended resolution:** Use one key type (uuid is usual for merged data) and add a legacy_id column while migrating
- **User approval required:** yes
- **Status:** resolved (One User entity with opaque string ids (random uuid4 hex) for every account; A's integer ids and B's 'lu-<n>' ids kept in legacy_id if data is ever imported)

## application:auth-provider:provider

- **Conflict:** Identity providers differ (A: local; B: external oauth provider (google-style))
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one identity provider and migrate accounts to it; Link accounts by verified email during migration
- **Recommended resolution:** One identity system for the unified app
- **User approval required:** yes
- **Status:** resolved (One identity system: local password provider plus external OAuth providers, all resolving to one User through an Identity table keyed by (provider, subject))

## application:authorization-model:model

- **Conflict:** Authorization models differ (A: one role string per user, no permission checks in this app; B: one role string per account, no permission checks in this app; C: rbac: role -> permission set)
- **Affected applications:** A, B, C
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one authorization model and express the others' rules in it
- **Recommended resolution:** One authorization model with one permission check function
- **User approval required:** yes
- **Status:** resolved (C's RBAC (role -> permission set) is the one authorization model; A's and B's unchecked role strings are mapped into it)

## application:business-rule:default_role

- **Conflict:** Rule default_role differs (A: "user", B: "member")
- **Affected applications:** A, B
- **Affected features:** M01, M03
- **Severity:** high
- **Possible solutions:** Choose one value and record why; Make it a setting if both are legitimate
- **Recommended resolution:** Pick one value with the user; make it configurable only if both are needed
- **User approval required:** yes
- **Status:** resolved (Password registration gets editor (A user -> editor); new OAuth accounts get viewer (B member -> viewer); a joined account keeps its existing role)

## application:business-rule:duplicate-registration

- **Conflict:** A overwrites an existing account when the same email registers again (account takeover)
- **Affected applications:** A
- **Affected features:** M01
- **Severity:** high
- **Possible solutions:** Reject a duplicate email with an error; Keep A's overwrite
- **Recommended resolution:** Reject duplicates; one account per email
- **User approval required:** yes
- **Status:** resolved (Reject a duplicate email (case-insensitive) with an error instead of overwriting the account)

## application:permissions:role-change-actor

- **Conflict:** C's set_role trusts a caller-supplied actor role, does not validate the new role and has no rule against raising your own role
- **Affected applications:** C
- **Affected features:** M05
- **Severity:** high
- **Possible solutions:** Resolve the actor from the session token, validate the role, refuse raising your own role; Keep C's behaviour
- **Recommended resolution:** Actor from session; only admins; role must exist; nobody raises their own role (user decision)
- **User approval required:** yes
- **Status:** resolved (set_role resolves the caller from the session token; only admins (manage_roles) may change roles; the role must be viewer/editor/admin; nobody can raise their own role)

## application:roles:roles

- **Conflict:** Role sets differ (A: user; B: member; C: admin, editor, viewer)
- **Affected applications:** A, B, C
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Map every source role to a unified role set and write the mapping down; Model special powers (such as approving) as permissions, not extra roles
- **Recommended resolution:** One role set plus explicit permissions; map every source role
- **User approval required:** yes
- **Status:** resolved (Unified roles viewer, editor, admin; mapping A user -> editor, B member -> viewer, C roles unchanged; any other source role raises KeyError)

## database:field-type:user.id

- **Conflict:** User.id types differ (A: integer, B: text)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M03
- **Severity:** high
- **Possible solutions:** Choose the wider type and convert the narrower data; Split into two fields if they mean different things
- **Recommended resolution:** One type per field; convert in a migration
- **User approval required:** yes
- **Status:** resolved (User.id is text (uuid4 hex) for all accounts; integer A ids widen to text in legacy_id)

## application:auth-methods:methods

- **Conflict:** Sign-in methods differ (A: password; B: oauth)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** medium
- **Possible solutions:** Offer the union of kept sign-in methods through one identity system; Drop sign-in methods no kept feature needs
- **Recommended resolution:** One identity system that offers the sign-in methods kept features need
- **User approval required:** no
- **Status:** resolved (Offer both password and OAuth sign-in through the one identity system)

## database:duplicate-entity:user

- **Conflict:** User exists in A:User, B:Account; fields not shared: hash (only A), provider (only B), salt (only A), subject (only B)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M03
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge into one entity; list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (Merge A:User and B:Account into one User entity; B's provider and subject move to an Identity entity linked to User)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| User | A, B | re-key rows to one primary key type (A: integer, B: text) and rewrite foreign keys that point at them (high); convert id to one type (A: integer, B: text) (high); add fields that only some sources have: hash (only A), provider (only B), salt (only A), subject (only B) (low); A.User.id: integer to text keeps every value (low); A.User.salt: binary to text can lose or reject values (high); A.User.hash: binary to text can lose or reject values (high); B.Account fields not kept in User: provider, subject (high) | high | hash, provider, salt, subject | yes |
| Session | A | A.Session.user_id: integer to text keeps every value (low) | low | - | no |
