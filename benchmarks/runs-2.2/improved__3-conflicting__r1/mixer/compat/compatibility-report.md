# Compatibility report

Scope: kept features only. Apps: A, B.

| Severity | Count |
|---|---|
| critical | 2 |
| high | 18 |
| medium | 6 |

## database:primary-key:post

- **Conflict:** Post primary keys differ (A: uuid, B: integer)
- **Affected applications:** A, B
- **Affected features:** M03, M04, M05, M08, M09, M10
- **Severity:** critical
- **Possible solutions:** Pick one key type for the merged entity and re-key the other source's rows; Keep a legacy_id column holding the old key during migration
- **Recommended resolution:** Use one key type (uuid is usual for merged data) and add a legacy_id column while migrating
- **User approval required:** yes
- **Status:** resolved (uuid primary key for every post (A's type). B's integer post ids are kept in legacy_id (with imported_from = 'B') during any import; nothing is re-keyed until a migration is separately approved.)

## database:primary-key:user

- **Conflict:** User primary keys differ (A: uuid, B: integer)
- **Affected applications:** A, B
- **Affected features:** M01, M03, M04, M05
- **Severity:** critical
- **Possible solutions:** Pick one key type for the merged entity and re-key the other source's rows; Keep a legacy_id column holding the old key during migration
- **Recommended resolution:** Use one key type (uuid is usual for merged data) and add a legacy_id column while migrating
- **User approval required:** yes
- **Status:** resolved (uuid primary key for every user (A's type). B's integer user ids kept in legacy_id (imported_from = 'B') during any import.)

## api:contract:GET /api/posts/{} response

- **Conflict:** GET /api/posts/{} response fields disagree (id: A uuid, B integer)
- **Affected applications:** A, B
- **Affected features:** M08, M09
- **Severity:** high
- **Possible solutions:** Define one request and response shape and convert at the edges; Version the endpoint if existing clients need the old shape
- **Recommended resolution:** One contract per endpoint, written into the API spec
- **User approval required:** yes
- **Status:** resolved (One contract: GET /api/v1/posts/{id} returns {id: uuid string, body, status, author: {id, display_name} or null for imported anonymous posts, created_at: UTC ISO 8601}. Integer ids are not accepted.)

## api:contract:POST /api/posts response

- **Conflict:** POST /api/posts response fields disagree (id: A uuid, B integer)
- **Affected applications:** A, B
- **Affected features:** M03, M04
- **Severity:** high
- **Possible solutions:** Define one request and response shape and convert at the edges; Version the endpoint if existing clients need the old shape
- **Recommended resolution:** One contract per endpoint, written into the API spec
- **User approval required:** yes
- **Status:** resolved (One contract: POST /api/v1/posts {body} returns 201 with the same post shape as GET.)

## api:endpoint-auth:GET /api/posts/{}

- **Conflict:** GET /api/posts/{} uses different auth (A: session, B: none)
- **Affected applications:** A, B
- **Affected features:** M08, M09
- **Severity:** high
- **Possible solutions:** Put every endpoint behind the one auth system the architecture chooses
- **Recommended resolution:** Same auth scheme for every endpoint
- **User approval required:** yes
- **Status:** resolved (One auth scheme (cookie session). Reading needs no session for a published post; a pending or rejected post needs the session of its author or a moderator, otherwise 404.)

## api:endpoint-auth:POST /api/posts

- **Conflict:** POST /api/posts uses different auth (A: session, B: optional bearer token)
- **Affected applications:** A, B
- **Affected features:** M03, M04
- **Severity:** high
- **Possible solutions:** Put every endpoint behind the one auth system the architecture chooses
- **Recommended resolution:** Same auth scheme for every endpoint
- **User approval required:** yes
- **Status:** resolved (Cookie session required (A). No bearer tokens, no anonymous posting (M07 deferred): without a session the answer is 401.)

## application:authorization-model:model

- **Conflict:** Authorization models differ (A: role-based; B: role claim in token (no permission checks in the code shown))
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one authorization model and express the others' rules in it
- **Recommended resolution:** One authorization model with one permission check function
- **User approval required:** yes
- **Status:** resolved (One role-based model with explicit permissions and one function can(user, action, post) used by every route and query.)

## application:business-rule:max_post_length

- **Conflict:** Rule max_post_length differs (A: 5000, B: 10000)
- **Affected applications:** A, B
- **Affected features:** M03, M04
- **Severity:** high
- **Possible solutions:** Choose one value and record why; Make it a setting if both are legitimate
- **Recommended resolution:** Pick one value with the user; make it configurable only if both are needed
- **User approval required:** yes
- **Status:** resolved (10000 characters for everyone (B's value). Reason: it keeps every existing post from both apps valid (5000 would reject B posts over 5000), and every post is reviewed before it is visible. Enforced in the handler (422) and by a check constraint.)

## application:business-rule:read_requires_account

- **Conflict:** Rule read_requires_account differs (A: true, B: false)
- **Affected applications:** A, B
- **Affected features:** M08, M09
- **Severity:** high
- **Possible solutions:** Choose one value and record why; Make it a setting if both are legitimate
- **Recommended resolution:** Pick one value with the user; make it configurable only if both are needed
- **User approval required:** yes
- **Status:** resolved (Published posts are public (B); pending and rejected posts are visible only to their author and moderators; everyone else gets 404. Fixes A's leak of unreviewed posts to every member.)

## application:roles:roles

- **Conflict:** Role sets differ (A: member, moderator; B: admin, user)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Map every source role to a unified role set and write the mapping down; Model special powers (such as approving) as permissions, not extra roles
- **Recommended resolution:** One role set plus explicit permissions; map every source role
- **User approval required:** yes
- **Status:** resolved (Unified roles member and moderator; moderate-posts is a permission of moderator. Mapping: A:member -> member, A:moderator -> moderator, B:user -> member, B:admin -> member (B's admin has no observed powers; an existing moderator promotes individual people by hand).)

## application:route:/login

- **Conflict:** Route /login is used by A: A-S03, B: B-S02
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Merge both screens into one page with sections; Move one to a different path
- **Recommended resolution:** One route per screen in the unified navigation
- **User approval required:** yes
- **Status:** resolved (One Login screen at /login.)

## application:route:/posts

- **Conflict:** Route /posts is used by A: A-S01, B: B-S01
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Merge both screens into one page with sections; Move one to a different path
- **Recommended resolution:** One route per screen in the unified navigation
- **User approval required:** yes
- **Status:** resolved (One PostList screen at /posts (published posts).)

## application:session:session

- **Conflict:** Session mechanisms differ (A: cookie session; B: jwt bearer token)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one session mechanism (http-only cookie sessions are the safer default for web apps); Use tokens only where a client cannot hold cookies
- **Recommended resolution:** One session mechanism for the whole app
- **User approval required:** yes
- **Status:** resolved (Server-side session in an http-only, secure, SameSite=Lax cookie with expiry; no JWT. B's token code and its hard-coded key are not carried over; existing B tokens stop working and B users sign in again.)

## database:data:imported-anonymous-posts

- **Conflict:** B allows posts with no author (author_id null, B-F04); the unified Post requires an author for new posts (A-F02) and anonymous posting is deferred (M07). Imported anonymous B posts would be rejected by a NOT NULL author.
- **Affected applications:** A, B
- **Affected features:** M03, M04
- **Severity:** high
- **Possible solutions:** Allow a null author only on imported B rows (check: author_id is not null or imported_from = 'B'); Assign imported anonymous posts to one placeholder account; Skip anonymous B posts on import (data loss)
- **Recommended resolution:** Allow a null author only on imported B rows, enforced by a check constraint; new posts always need an author
- **User approval required:** yes
- **Status:** resolved (author_id may be null only on imported B rows: check (author_id is not null or imported_from = 'B'). New posts always need an author.)

## database:data:imported-post-status

- **Conflict:** B's posts have no status and are all live (B-F03); the unified Post requires a status and every new post starts pending (A-F04). If B's existing posts are imported, they need a status, and the choice decides whether they stay visible.
- **Affected applications:** A, B
- **Affected features:** M04, M05
- **Severity:** high
- **Possible solutions:** Import B's posts as published, marked imported_from = B, so they stay visible; moderators may reject any later; Import B's posts as pending so moderators re-review everything (they disappear from public view until reviewed); Do not import B's posts
- **Recommended resolution:** Import as published with imported_from = B; they were already public, and moderators can reject any of them
- **User approval required:** yes
- **Status:** resolved (Import B's posts as published with imported_from = 'B' (they were already public); moderators may reject any later.)

## database:enum:user.role

- **Conflict:** User.role allows different values (A only: member, moderator; B only: admin, user; 4 values in all)
- **Affected applications:** A, B
- **Affected features:** M01, M03, M04, M05
- **Severity:** high
- **Possible solutions:** Define one value set and a mapping from every source value to it; Keep the field per source if the states really differ
- **Recommended resolution:** One value set with an explicit mapping; values without a mapping block the migration
- **User approval required:** yes
- **Status:** resolved (Value set {member, moderator}; mapping as in application:roles:roles. No source value is left unmapped.)

## database:field-type:post.author_id

- **Conflict:** Post.author_id types differ (A: uuid, B: integer)
- **Affected applications:** A, B
- **Affected features:** M03, M04, M05, M08, M09, M10
- **Severity:** high
- **Possible solutions:** Choose the wider type and convert the narrower data; Split into two fields if they mean different things
- **Recommended resolution:** One type per field; convert in a migration
- **User approval required:** yes
- **Status:** resolved (uuid referencing User.id; B's integer author ids are rewritten through the users' legacy_id map on import.)

## database:field-type:post.id

- **Conflict:** Post.id types differ (A: uuid, B: integer)
- **Affected applications:** A, B
- **Affected features:** M03, M04, M05, M08, M09, M10
- **Severity:** high
- **Possible solutions:** Choose the wider type and convert the narrower data; Split into two fields if they mean different things
- **Recommended resolution:** One type per field; convert in a migration
- **User approval required:** yes
- **Status:** resolved (uuid (see database:primary-key:post).)

## database:field-type:user.id

- **Conflict:** User.id types differ (A: uuid, B: integer)
- **Affected applications:** A, B
- **Affected features:** M01, M03, M04, M05
- **Severity:** high
- **Possible solutions:** Choose the wider type and convert the narrower data; Split into two fields if they mean different things
- **Recommended resolution:** One type per field; convert in a migration
- **User approval required:** yes
- **Status:** resolved (uuid (see database:primary-key:user).)

## database:units:post.created_at.timezone

- **Conflict:** Post.created_at timezone differs (A: stored with time zone, B: not stated)
- **Affected applications:** A, B
- **Affected features:** M03, M04, M05, M08, M09, M10
- **Severity:** high
- **Possible solutions:** Store one unit (for example integer cents in UTC) and convert at import; Store the unit with the value
- **Recommended resolution:** One unit per field, converted in the migration and tested
- **User approval required:** yes
- **Status:** resolved (Store created_at as timestamptz in UTC. A's values are already zoned. B's naive timestamps are converted from B's server time zone, which is unknown: the import migration may not run until the user states it (open question).)

## api:duplicate-endpoint:GET /api/posts/{}

- **Conflict:** GET /api/posts/{} exists in A: /api/posts/:id, B: /api/posts/<int:post_id>
- **Affected applications:** A, B
- **Affected features:** M08, M09
- **Severity:** medium
- **Possible solutions:** Keep one endpoint and adapt clients of the other; Keep both under different paths if they serve different needs
- **Recommended resolution:** One endpoint per job in the unified API
- **User approval required:** no
- **Status:** resolved (One endpoint GET /api/v1/posts/{id} in the posts module.)

## api:duplicate-endpoint:POST /api/posts

- **Conflict:** POST /api/posts exists in A: /api/posts, B: /api/posts
- **Affected applications:** A, B
- **Affected features:** M03, M04
- **Severity:** medium
- **Possible solutions:** Keep one endpoint and adapt clients of the other; Keep both under different paths if they serve different needs
- **Recommended resolution:** One endpoint per job in the unified API
- **User approval required:** no
- **Status:** resolved (One endpoint POST /api/v1/posts in the posts module.)

## application:security:b-hardcoded-signing-key

- **Conflict:** B signs and verifies JWTs with a literal key in api.py (scan: 2 medium findings) and passes no algorithms list to decode. B's sign-in (M02) is dropped, but nothing from B's auth code may be carried over.
- **Affected applications:** B
- **Affected features:** B-F01
- **Severity:** medium
- **Possible solutions:** Carry over nothing from B's token code; one cookie-session system configured from environment variables; If a token API is ever needed, a new key from the environment with a fixed algorithm and expiry
- **Recommended resolution:** Carry over nothing from B's token code; existing B tokens stop working after the merge and B users sign in again
- **User approval required:** no
- **Status:** resolved (Nothing from B's token code is reused; every secret comes from environment variables named in .env.example.)

## database:duplicate-entity:post

- **Conflict:** Post exists in A:Post, B:Post; fields not shared: status (only A)
- **Affected applications:** A, B
- **Affected features:** M03, M04, M05, M08, M09, M10
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge only once it is confirmed they mean the same thing; then list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (Merge: A's and B's Post are the same thing (a forum post). One Post table; fields' origins listed in architecture.json.)

## database:duplicate-entity:user

- **Conflict:** User exists in A:User, B:User
- **Affected applications:** A, B
- **Affected features:** M01, M03, M04, M05
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge only once it is confirmed they mean the same thing; then list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (Merge: same meaning (a person who signs in). One User table; B's name maps to display_name (aliases.json).)

## database:nullability:post.author_id

- **Conflict:** Post.author_id is A: required, B: optional
- **Affected applications:** A, B
- **Affected features:** M03, M04, M05, M08, M09, M10
- **Severity:** medium
- **Possible solutions:** Keep the field nullable; Make it required with a default for rows that have no value
- **Recommended resolution:** Do not make a field required until every source row has a value or a default is agreed
- **User approval required:** no
- **Status:** resolved (Required for new posts; null only for imported anonymous B posts (see database:data:imported-anonymous-posts).)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Post | A, B | re-key rows to one primary key type (A: uuid, B: integer) and rewrite foreign keys that point at them (high); convert author_id to one type (A: uuid, B: integer) (high); convert id to one type (A: uuid, B: integer) (high); add fields that only some sources have: status (only A) (low); B.Post.id: integer to uuid can lose or reject values (high); B.Post.author_id: integer to uuid can lose or reject values (high); author_id: rows from B may have no value; making it required rejects them unless a default is agreed (high); convert created_at to one timezone (A: stored with time zone, B: not stated) and test the conversion (high) | high | author_id, id | yes |
| User | A, B | re-key rows to one primary key type (A: uuid, B: integer) and rewrite foreign keys that point at them (high); convert id to one type (A: uuid, B: integer) (high); B.User.id: integer to uuid can lose or reject values (high); map every value of role to one value set (A only: member, moderator; B only: admin, user) (high) | high | id | yes |
