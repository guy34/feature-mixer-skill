# Compatibility report

Scope: kept features only. Apps: A, B.

| Severity | Count |
|---|---|
| critical | 1 |
| high | 12 |
| medium | 4 |

## database:primary-key:post

- **Conflict:** Post primary keys differ (A: uuid, B: integer)
- **Affected applications:** A, B
- **Affected features:** M03, M04, M05, M06, M07, M08, M09, M10
- **Severity:** critical
- **Possible solutions:** Pick one key type for the merged entity and re-key the other source's rows; Keep a legacy_id column holding the old key during migration
- **Recommended resolution:** Use one key type (uuid is usual for merged data) and add a legacy_id column while migrating
- **User approval required:** yes
- **Status:** resolved (uuid primary key for every post; B's integer ids kept in legacy_id (unique, nullable) during and after migration)

## api:contract:GET /api/posts/{} response

- **Conflict:** GET /api/posts/{} response fields disagree (body: A text, B str; id: A uuid, B integer)
- **Affected applications:** A, B
- **Affected features:** M03, M04
- **Severity:** high
- **Possible solutions:** Define one request and response shape and convert at the edges; Version the endpoint if existing clients need the old shape
- **Recommended resolution:** One contract per endpoint, written into the API spec
- **User approval required:** yes
- **Status:** resolved (One contract: {id: uuid, body: text, status: pending|published|rejected, author: {id: uuid, display_name: text}, created_at}. No integer-id compatibility layer (no B API clients are known))

## api:endpoint-auth:GET /api/posts/{}

- **Conflict:** GET /api/posts/{} uses different auth (A: cookie session, B: none)
- **Affected applications:** A, B
- **Affected features:** M03, M04
- **Severity:** high
- **Possible solutions:** Put every endpoint behind the one auth system the architecture chooses
- **Recommended resolution:** Same auth scheme for every endpoint
- **User approval required:** yes
- **Status:** resolved (One cookie-session auth; GET /api/posts/:id is public for published posts, author or moderator only for pending/rejected (404 otherwise))

## application:authorization-model:model

- **Conflict:** Authorization models differ (A: role-based: member, moderator; requiresession / requiremoderator guards; B: roles user, admin carried in the token; no role checks seen in the api)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one authorization model and express the others' rules in it
- **Recommended resolution:** One authorization model with one permission check function
- **User approval required:** yes
- **Status:** resolved (Role-based model with one can(user, action, resource) check used by every handler; actions: post.create, post.read_unpublished, moderation.list, moderation.decide)

## application:business-rule:max-post-length

- **Conflict:** A limits a post body to 5000 characters (constant and DB check); B allows 10000. B posts between 5001 and 10000 characters would be rejected by A's constraint during migration.
- **Affected applications:** A, B
- **Affected features:** M04, M05
- **Severity:** high
- **Possible solutions:** Unified limit 10000 (widen A's check; no existing post rejected); Unified limit 5000 and truncate or reject longer B posts (data loss); 5000 for new posts, longer legacy posts allowed through a legacy flag
- **Recommended resolution:** Unified limit 10000: widening loses nothing and moderators review every new post anyway
- **User approval required:** yes
- **Status:** resolved (Unified limit 10000 characters (server validation and DB check))

## application:roles:roles

- **Conflict:** Role sets differ (A: member, moderator; B: admin, user)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Map every source role to a unified role set and write the mapping down; Model special powers (such as approving) as permissions, not extra roles
- **Recommended resolution:** One role set plus explicit permissions; map every source role
- **User approval required:** yes
- **Status:** resolved (Unified roles member and moderator. Map A member->member, A moderator->moderator, B user->member, B admin->member (least privilege: admin had no observed powers); former B admins are listed for the user to promote by hand)

## application:route:/login

- **Conflict:** Route /login is used by A: A-S03, B: B-S02
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Merge both screens into one page with sections; Move one to a different path
- **Recommended resolution:** One route per screen in the unified navigation
- **User approval required:** yes
- **Status:** resolved (One /login screen for everyone)

## application:route:/posts

- **Conflict:** Route /posts is used by A: A-S01, B: B-S01
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Merge both screens into one page with sections; Move one to a different path
- **Recommended resolution:** One route per screen in the unified navigation
- **User approval required:** yes
- **Status:** resolved (One /posts screen listing published posts)

## application:session:session

- **Conflict:** Session mechanisms differ (A: server-side cookie session (req.session.userid); B: stateless jwt bearer token (no expiry seen))
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one session mechanism (http-only cookie sessions are the safer default for web apps); Use tokens only where a client cannot hold cookies
- **Recommended resolution:** One session mechanism for the whole app
- **User approval required:** yes
- **Status:** resolved (Server-side session in an http-only, secure, same-site cookie; no bearer tokens)

## application:workflow:publish-policy

- **Conflict:** A holds every new post as pending until a moderator publishes it; B publishes every post immediately. B's existing posts were never moderated.
- **Affected applications:** A, B
- **Affected features:** M04, M05, M07
- **Severity:** high
- **Possible solutions:** Pre-moderate every new post; migrate B's existing posts as published (grandfathered); Pre-moderate every new post and push B's existing posts into the moderation queue; Publish immediately and moderate afterwards (drops A's rule)
- **Recommended resolution:** Pre-moderate every new post; migrate B's existing posts as published, since they are already public
- **User approval required:** yes
- **Status:** resolved (Every new post is pending until a moderator decides; B's existing posts migrate as published)

## database:data-migration:user-accounts

- **Conflict:** B's users (integer ids, 'name', roles user/admin) author B's posts and must be merged into A's users (uuid, 'display_name', roles member/moderator). The same email may exist in both apps. Password hashing in both sources is unknown, so B's stored credentials may not verify in the unified app.
- **Affected applications:** A, B
- **Affected features:** M01, M04
- **Severity:** high
- **Possible solutions:** Re-key B users to uuid with legacy_id; name -> display_name; link accounts with the same email into A's record; force a password reset where hashes cannot be verified; Keep B users as separate accounts even when emails match (email must stay unique, so this fails)
- **Recommended resolution:** Re-key with legacy_id, map name to display_name, merge same-email accounts into A's record, and require a password reset for B accounts whose hash format is not supported
- **User approval required:** yes
- **Status:** resolved (Re-key B users to uuid with legacy_id; name -> display_name; same-email accounts merged into A's record; password reset required where B's hash format cannot be verified. Approved as a plan only; running it needs a separate approval)

## database:field-type:post.author_id

- **Conflict:** Post.author_id types differ (A: uuid, B: integer)
- **Affected applications:** A, B
- **Affected features:** M03, M04, M05, M06, M07, M08, M09, M10
- **Severity:** high
- **Possible solutions:** Choose the wider type and convert the narrower data; Split into two fields if they mean different things
- **Recommended resolution:** One type per field; convert in a migration
- **User approval required:** yes
- **Status:** resolved (author_id is uuid referencing users.id; B's integer author ids are rewritten through the user legacy_id map)

## database:nullability:post.author_id

- **Conflict:** A requires an author (author_id not null); B allows null author_id for anonymous posts. Anonymous posting (M08) was dropped, but B's existing anonymous posts still have no author.
- **Affected applications:** A, B
- **Affected features:** M04, M05
- **Severity:** high
- **Possible solutions:** Assign legacy anonymous posts to one reserved, sign-in-disabled system account and keep author_id not null; Make author_id nullable for legacy rows only; Do not migrate anonymous posts (data loss)
- **Recommended resolution:** Reserved system account 'Anonymous (OpenForum archive)' with sign-in disabled; author_id stays not null
- **User approval required:** yes
- **Status:** resolved (Legacy anonymous B posts are assigned to a reserved sign-in-disabled system account; author_id stays not null)

## api:duplicate-endpoint:GET /api/posts/{}

- **Conflict:** GET /api/posts/{} exists in A: /api/posts/:id, B: /api/posts/<int:post_id>
- **Affected applications:** A, B
- **Affected features:** M03, M04
- **Severity:** medium
- **Possible solutions:** Keep one endpoint and adapt clients of the other; Keep both under different paths if they serve different needs
- **Recommended resolution:** One endpoint per job in the unified API
- **User approval required:** no
- **Status:** resolved (One GET /api/posts/:id (uuid))

## application:auth-methods:methods

- **Conflict:** Sign-in methods differ (A: email + credentials; B: email + password)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** medium
- **Possible solutions:** Offer the union of kept sign-in methods through one identity system; Drop sign-in methods no kept feature needs
- **Recommended resolution:** One identity system that offers the sign-in methods kept features need
- **User approval required:** no
- **Status:** resolved (Email + password only, through the one identity system)

## application:security:b-token-signing-key

- **Conflict:** B signs JWTs with a hard-coded literal key and no expiry. B's token sign-in was dropped; any B tokens in the wild must stop working.
- **Affected applications:** B
- **Affected features:** M04
- **Severity:** medium
- **Possible solutions:** Do not reuse B's token code; B tokens become invalid at cut-over; Keep a temporary token bridge (would keep the weak key alive)
- **Recommended resolution:** No reuse of B's token code; B tokens are invalid after cut-over; the unified session secret comes only from configuration
- **User approval required:** no
- **Status:** resolved (B's token code is not reused; B tokens are invalid at cut-over; session secret from configuration only)

## database:duplicate-entity:post

- **Conflict:** Post exists in A:Post, B:Post; fields not shared: status (only A)
- **Affected applications:** A, B
- **Affected features:** M03, M04, M05, M06, M07, M08, M09, M10
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge into one entity; list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (One posts table; status from A; B rows get status published (see publish-policy))

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Post | A, B | re-key rows to one primary key type (A: uuid, B: integer) and rewrite foreign keys that point at them (high); convert author_id to one type (A: uuid, B: integer) (high); add fields that only some sources have: status (only A) (low); B.Post.author_id: integer to uuid can lose or reject values (high) | high | author_id | yes |
| User | A | merge rows from every source into one table (low) | low | - | yes |
