# Compatibility report

Scope: kept features only. Apps: A, B, C.

| Severity | Count |
|---|---|
| critical | 1 |
| high | 11 |
| medium | 5 |
| low | 3 |

## database:primary-key:user

- **Conflict:** User primary keys differ (A: uuid, B: integer)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M08, M09
- **Severity:** critical
- **Possible solutions:** Pick one key type for the merged entity and re-key the other source's rows; Keep a legacy_id column holding the old key during migration
- **Recommended resolution:** Use one key type (uuid is usual for merged data) and add a legacy_id column while migrating
- **User approval required:** yes
- **Status:** resolved (Every user id is a uuid. B's integer ids are re-keyed during import and kept in legacy_id until the import is checked (D03).)

## api:contract:GET /api/users/{} response

- **Conflict:** GET /api/users/{} response fields disagree (id: A uuid, B integer)
- **Affected applications:** A, B
- **Affected features:** M08, M09
- **Severity:** high
- **Possible solutions:** Define one request and response shape and convert at the edges; Version the endpoint if existing clients need the old shape
- **Recommended resolution:** One contract per endpoint, written into the API spec
- **User approval required:** yes
- **Status:** resolved (One user shape: {id: uuid, email, name, role, can_approve}. B's full_name maps to name (D05).)

## api:endpoint-auth:GET /api/users/{}

- **Conflict:** GET /api/users/{} uses different auth (A: session, B: bearer)
- **Affected applications:** A, B
- **Affected features:** M08, M09
- **Severity:** high
- **Possible solutions:** Put every endpoint behind the one auth system the architecture chooses
- **Recommended resolution:** Same auth scheme for every endpoint
- **User approval required:** yes
- **Status:** resolved (Every endpoint uses the one cookie session (D02).)

## application:auth-provider:provider

- **Conflict:** Identity providers differ (A: self; B: self; C: google)
- **Affected applications:** A, B, C
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one identity provider and migrate accounts to it; Link accounts by verified email during migration
- **Recommended resolution:** One identity system for the unified app
- **User approval required:** yes
- **Status:** resolved (Team Hub runs its own accounts now (email and password). Google sign-in (M03) is deferred and will use the user's own Google OAuth app when picked up.)

## application:roles:roles

- **Conflict:** Role sets differ (A: member, owner; B: admin, approver, requester; C: admin, member)
- **Affected applications:** A, B, C
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Map every source role to a unified role set and write the mapping down; Model special powers (such as approving) as permissions, not extra roles
- **Recommended resolution:** One role set plus explicit permissions; map every source role
- **User approval required:** yes
- **Status:** resolved (Roles owner, admin, member plus an approve permission. A owner->owner, A member->member, B admin->admin, B requester->member, B approver->member with approve, C admin->admin, C member->member (D04).)

## application:route:/login

- **Conflict:** Route /login is used by A: A-S01, B: B-S01
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Merge both screens into one page with sections; Move one to a different path
- **Recommended resolution:** One route per screen in the unified navigation
- **User approval required:** yes
- **Status:** resolved (One sign-in screen at /login for every user (the example ships the API; the UI is out of scope).)

## application:route:/settings

- **Conflict:** Route /settings is used by A: A-S05, B: B-S04
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Merge both screens into one page with sections; Move one to a different path
- **Recommended resolution:** One route per screen in the unified navigation
- **User approval required:** yes
- **Status:** resolved (One /settings screen with account and notification sections.)

## application:session:session

- **Conflict:** Session mechanisms differ (A: cookie; B: jwt-header)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one session mechanism (http-only cookie sessions are the safer default for web apps); Use tokens only where a client cannot hold cookies
- **Recommended resolution:** One session mechanism for the whole app
- **User approval required:** yes
- **Status:** resolved (http-only cookie sessions, 30 minutes idle, for every client (D02).)

## application:workflow:closing-tasks-with-approvals

- **Conflict:** In A anyone allowed to edit a task can move it to done at any time. B's approvals were standalone. Once approvals attach to tasks, a task could be closed while its approval is still pending.
- **Affected applications:** A, B
- **Affected features:** M04, M13
- **Severity:** high
- **Possible solutions:** Block moving a task to done while it has a pending approval; Allow it and cancel the pending approval automatically; Allow it and only warn
- **Recommended resolution:** Block moving to done while an approval is pending; the approver decides first
- **User approval required:** yes
- **Status:** resolved (Block moving a task to done while it has a pending approval. Implemented as a status guard the approvals module registers with tasks.)

## database:field-type:user.id

- **Conflict:** User.id types differ (A: uuid, B: integer)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M08, M09
- **Severity:** high
- **Possible solutions:** Choose the wider type and convert the narrower data; Split into two fields if they mean different things
- **Recommended resolution:** One type per field; convert in a migration
- **User approval required:** yes
- **Status:** resolved (Same decision as database:primary-key:user: uuid (D03).)

## dependency:runtime:node

- **Conflict:** node: A uses >=18, B uses 16.x
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Target one runtime version that every kept feature can run on; Upgrade the source code that needs the older runtime
- **Recommended resolution:** Pick the newest runtime version the kept features support
- **User approval required:** yes
- **Status:** resolved (Not applicable: Team Hub is built on Python 3.8+ with the standard library (D01); no source code is carried over.)

## dependency:version:react

- **Conflict:** react: A uses ^18.2.0, B uses ^17.0.2
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Standardise on the newer major version and update the code that used the older one; Keep the older version only if a kept feature cannot move yet, and isolate it
- **Recommended resolution:** Use one version, normally the newer major, in the unified app
- **User approval required:** yes
- **Status:** resolved (Not applicable: no React code is carried over (D01).)

## api:api-version:GET /api/users/{}

- **Conflict:** GET /api/users/{} versions differ (A: none, B: v1)
- **Affected applications:** A, B
- **Affected features:** M08, M09
- **Severity:** medium
- **Possible solutions:** Start the unified API at one version; Keep a compatibility layer for old clients
- **Recommended resolution:** One versioning scheme for the unified API
- **User approval required:** no
- **Status:** resolved (One unversioned /api while there are no outside clients (D05).)

## api:duplicate-endpoint:GET /api/users/{}

- **Conflict:** GET /api/users/{} exists in A: /api/users/:id, B: /api/v1/users/:id
- **Affected applications:** A, B
- **Affected features:** M08, M09
- **Severity:** medium
- **Possible solutions:** Keep one endpoint and adapt clients of the other; Keep both under different paths if they serve different needs
- **Recommended resolution:** One endpoint per job in the unified API
- **User approval required:** no
- **Status:** resolved (One GET /api/me for the signed-in user; user listing waits for an admin screen.)

## application:auth-methods:methods

- **Conflict:** Sign-in methods differ (A: password; B: password; C: google-oauth)
- **Affected applications:** A, B, C
- **Affected features:** not linked to a feature
- **Severity:** medium
- **Possible solutions:** Offer the union of kept sign-in methods through one identity system; Drop sign-in methods no kept feature needs
- **Recommended resolution:** One identity system that offers the sign-in methods kept features need
- **User approval required:** no
- **Status:** resolved (Password now; Google later with M03.)

## database:duplicate-entity:user

- **Conflict:** User exists in A:User, B:User; fields not shared: created_at (only A), password_hash (only A)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M08, M09
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge into one entity; list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (One users table with the union of fields kept features use (D03).)

## dependency:version:react-dom

- **Conflict:** react-dom: A uses ^18.2.0, B uses ^17.0.2
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** medium
- **Possible solutions:** Standardise on the newer major version and update the code that used the older one; Keep the older version only if a kept feature cannot move yet, and isolate it
- **Recommended resolution:** Use one version, normally the newer major, in the unified app
- **User approval required:** no
- **Status:** resolved (Not applicable (D01).)

## application:component:button

- **Conflict:** button variants differ (A: ghost, primary; B: danger, primary, secondary)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** low
- **Possible solutions:** One component with the union of variants the kept screens use
- **Recommended resolution:** One component in the design system
- **User approval required:** no
- **Status:** resolved (Not applicable to the API-only example; a UI would use one Button with primary, secondary, ghost and danger.)

## dependency:duplicate-library:date-library

- **Conflict:** Several date librarys: dayjs (A); moment (B)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** low
- **Possible solutions:** Keep one library for this job and replace calls to the others
- **Recommended resolution:** Keep one library per job
- **User approval required:** no
- **Status:** resolved (Not applicable (D01): Python's datetime is used.)

## dependency:duplicate-library:http-client

- **Conflict:** Several HTTP clients: axios (A); node-fetch (B)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** low
- **Possible solutions:** Keep one library for this job and replace calls to the others
- **Recommended resolution:** Keep one library per job
- **User approval required:** no
- **Status:** resolved (Not applicable (D01).)

## Migrations

| Entity | Apps | Changes | Destructive | Approved |
|---|---|---|---|---|
| User | A, B | re-key rows to one primary key type (A: uuid, B: integer) and rewrite foreign keys that point at them; convert id to one type (A: uuid, B: integer); add fields that only some sources have: created_at (only A), password_hash (only A) | yes | yes |
