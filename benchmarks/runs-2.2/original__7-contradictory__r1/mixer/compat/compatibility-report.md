# Compatibility report

Scope: kept features only. Apps: A, B.

| Severity | Count |
|---|---|
| high | 3 |
| medium | 5 |
| low | 2 |

## application:authorization-model:model

- **Conflict:** Authorization models differ (A: none: every route is open; B: none)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one authorization model and express the others' rules in it
- **Recommended resolution:** One authorization model with one permission check function
- **User approval required:** yes
- **Status:** resolved (Neither app has any authorization (all routes open). Unified app: per-user ownership; one can(user, action, record) check used by every route and query; a user can only read or change their own books, ratings and lists. One role 'reader'; no admin role in v1.)

## application:rule:rating-scale

- **Conflict:** Shelfie's README and openapi.yaml say ratings are 1-10 in a field named 'score'; Shelfie's code (handler and DB CHECK) and Readr's code both use 1-5 in a field named 'stars'. Building from the docs would make every existing rating mean something different.
- **Affected applications:** A, B
- **Affected features:** M02
- **Severity:** high
- **Possible solutions:** Follow the code: 1-5 integer 'stars' (both apps agree); Follow Shelfie's docs: 1-10 'score' and rescale any imported data; Store 1-10 internally and show 5 stars
- **Recommended resolution:** Follow the code: integer 'stars' 1-5, enforced in the API and by a DB CHECK; correct the docs in the new app
- **User approval required:** yes
- **Status:** resolved (Follow the code, not Shelfie's stale docs: integer 'stars' 1-5, checked in the API (reject non-integers and booleans) and by a DB CHECK. The documented 1-10 'score' is not built.)

## application:session:session

- **Conflict:** Session mechanisms differ (A: none (shelfie_session_secret is required at startup but unused); B: none)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one session mechanism (http-only cookie sessions are the safer default for web apps); Use tokens only where a client cannot hold cookies
- **Recommended resolution:** One session mechanism for the whole app
- **User approval required:** yes
- **Status:** resolved (Neither app has sessions (Shelfie reads a secret it never uses). Unified app: email + password accounts, password hashed with a slow KDF, server-side session row referenced by an http-only, SameSite=Lax, Secure (in production) cookie signed with SESSION_SECRET.)

## api:api-contract:export-format

- **Conflict:** Shelfie's README and spec promise CSV at GET /api/v1/books/export.csv; the code serves JSON at GET /api/books/export. The CSV export was never built.
- **Affected applications:** A
- **Affected features:** M04
- **Severity:** medium
- **Possible solutions:** Build JSON export as the code does; Build CSV as the docs say; Offer both
- **Recommended resolution:** JSON export as the code does (user: trust what the apps do); CSV recorded as an open question, not built
- **User approval required:** no
- **Status:** resolved (JSON export as the code does; CSV (documented only, never built) is not built; left as an open question for the user.)

## application:architecture:documented-services-and-database

- **Conflict:** Shelfie's docs describe three services (catalog, ratings, gateway) each with its own database, on PostgreSQL; the code is one process with one SQLite file and no gateway.
- **Affected applications:** A
- **Affected features:** M01, M02, M04
- **Severity:** medium
- **Possible solutions:** Design from the code: one process, one database; Design from the docs: three services with a gateway
- **Recommended resolution:** Ignore the stale service and PostgreSQL claims; choose the architecture on this project's drivers in phase 5
- **User approval required:** no
- **Status:** resolved (Stale three-service / PostgreSQL docs are ignored; architecture chosen on this project's drivers in phase 5.)

## database:data-integrity:list-entries-and-foreign-keys

- **Conflict:** Readr allows the same book on a list twice and never checks that the list or book exist (SQLite foreign keys are off by default).
- **Affected applications:** B
- **Affected features:** M05
- **Severity:** medium
- **Possible solutions:** Unique (list_id, book_id), foreign keys on, ownership checks; Allow duplicates
- **Recommended resolution:** Primary key (list_id, book_id), PRAGMA foreign_keys=ON, cascade deletes, ownership checked on list and book
- **User approval required:** no
- **Status:** resolved (ReadingListItem primary key (list_id, book_id); PRAGMA foreign_keys=ON; ON DELETE CASCADE from list and book; ownership checked on both.)

## database:data-integrity:rating-cardinality-and-durability

- **Conflict:** Both apps append a new ratings row on every rating (no key, no uniqueness) and neither ever commits, so ratings pile up and are lost on exit; Shelfie's export repeats a book once per rating.
- **Affected applications:** A, B
- **Affected features:** M02, M04
- **Severity:** medium
- **Possible solutions:** One rating per user per book, upsert, commit every write; Keep append-only history
- **Recommended resolution:** Rating has a unique (user_id, book_id); PUT upserts; every write commits; export shows the current rating
- **User approval required:** no
- **Status:** resolved (Rating unique (user_id, book_id); PUT upserts, DELETE clears; every write commits in a transaction; export shows the current rating.)

## database:duplicate-entity:book

- **Conflict:** Book exists in A:Book, B:Book; fields not shared: author (only A)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M04, M05
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge into one entity; list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (One Book entity merged from A:Book and B:Book: id, owner_id (new), title, author (from A, nullable), timestamps.)

## api:api-version:path-prefix

- **Conflict:** Spec uses /api/v1/...; code uses /api/... with no version. Neither app has clients we know of.
- **Affected applications:** A
- **Affected features:** M01, M02, M04
- **Severity:** low
- **Possible solutions:** New app uses /api/v1 for every endpoint; Keep unversioned /api
- **Recommended resolution:** New app uses /api/v1 for every endpoint (one versioning scheme); there is no observed client of the old paths to keep compatible
- **User approval required:** no
- **Status:** resolved (Every endpoint under /api/v1; no compatibility shims for Shelfie's unversioned /api paths (no known clients).)

## application:configuration:undocumented-session-secret

- **Conflict:** Shelfie requires SHELFIE_SESSION_SECRET at startup but never uses it, and no doc mentions it.
- **Affected applications:** A
- **Affected features:** M01
- **Severity:** low
- **Possible solutions:** Give the new app a documented session secret it actually uses; Drop the variable
- **Recommended resolution:** One documented SESSION_SECRET in the config module and .env.example (name only), used to sign session cookies
- **User approval required:** no
- **Status:** resolved (Replaced by SESSION_SECRET, read in the config module, listed (name only) in .env.example, used to sign session cookies; startup fails with a clear message if unset outside development.)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Book | A, B | add fields that only some sources have: author (only A) (low) | low | - | no |
| Rating | A | merge rows from every source into one table (low) | low | - | no |
| ReadingList | B | merge rows from every source into one table (low) | low | - | no |
| ReadingListItem | B | merge rows from every source into one table (low) | low | - | no |
