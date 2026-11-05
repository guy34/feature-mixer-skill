# Compatibility report

Scope: kept features only. Apps: A, B.

| Severity | Count |
|---|---|
| high | 4 |
| medium | 5 |
| low | 1 |

## application:authorization-model:model

- **Conflict:** Authorization models differ (A: no authentication or authorization; every endpoint is open (the documented gateway auth does not exist in the code); B: none: a local library with no users)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one authorization model and express the others' rules in it
- **Recommended resolution:** One authorization model with one permission check function
- **User approval required:** yes
- **Status:** resolved (Owner-only model: every Book, Rating, ReadingList and list entry belongs to one person (owner_id); every read and write checks owner_id against the signed-in person in one permission function; another person's ids answer 404. No roles. Neither source had any authorization (Shelfie's documented gateway auth does not exist in its code); this is needed because the user wants 'people' to keep libraries. Alternative not chosen: a single-person local app with no accounts.)

## application:session:session

- **Conflict:** Session mechanisms differ (A: none in use: shelfie_session_secret is required at startup but never used; B: none)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** high
- **Possible solutions:** Choose one session mechanism (http-only cookie sessions are the safer default for web apps); Use tokens only where a client cannot hold cookies
- **Recommended resolution:** One session mechanism for the whole app
- **User approval required:** yes
- **Status:** resolved (Email and password sign-in (password hashed with the standard library's scrypt), server-side session stored in the database, random token in an http-only, SameSite=Lax cookie; sign out deletes the session. Shelfie's unused SHELFIE_SESSION_SECRET is not carried over.)

## database:data-migration:existing-data-import

- **Conflict:** Both apps key books with their own integer ids in separate SQLite files (shelfie.db, readr.db). Importing both into one database would collide on ids and require re-keying Readr's books and rewriting its ratings and list_books rows; there is also no user to own imported rows. No database files were provided and nothing shows whether real data exists.
- **Affected applications:** A, B
- **Affected features:** M01, M05
- **Severity:** high
- **Possible solutions:** Start the unified app with an empty database; import is out of scope for now; Write an import that re-keys Readr's ids into the unified Book table and assigns all rows to one chosen person (destructive-risk migration needing its own plan and approval)
- **Recommended resolution:** Start empty; if the user has data worth keeping, plan the import separately with templates/migration-plan.md, a backup and a dry run
- **User approval required:** yes
- **Status:** resolved (Start the unified app with an empty database; no import of shelfie.db or readr.db in this plan (none was provided; whether real data exists is unknown). If the user has data, an import that re-keys Readr's ids is planned separately with templates/migration-plan.md, a backup and a dry run, and needs its own migration approval.)

## database:entity-meaning:book

- **Conflict:** Book may not mean the same thing in A, B: A describes it as 'A book in the library (Shelfie's catalog).', B as 'A book that can be rated or listed (title only).'
- **Affected applications:** A, B
- **Affected features:** M01, M02, M04, M05
- **Severity:** high
- **Possible solutions:** Keep them as separate entities with distinct names (for example UserAccount and LedgerAccount); Merge them only if the user confirms they describe the same thing
- **Recommended resolution:** Ask the user; never merge entities because their names match
- **User approval required:** yes
- **Status:** resolved (Same thing: both are a 'books' table with integer id and required title, referenced the same way by ratings (and by Readr's list_books). Merge into one Book (id, owner_id, title required, author optional). Field origins listed in architecture.json.)

## application:business-rule:export-format

- **Conflict:** Shelfie's README and spec promise CSV at /api/v1/books/export.csv; the code returns JSON at /api/books/export (A-C01, A-C02).
- **Affected applications:** A
- **Affected features:** M04
- **Severity:** medium
- **Possible solutions:** JSON as the code does; CSV as the docs claim (new work, not in any source's behaviour); both
- **Recommended resolution:** JSON only; CSV listed as a possible later addition if the user wants it
- **User approval required:** no
- **Status:** resolved (JSON export only ([{title, stars}] for the signed-in person's books); no CSV.)

## application:business-rule:rating-cardinality

- **Conflict:** Both apps append a new ratings row each time a book is rated, so a book collects several ratings and Shelfie's export repeats it. A shared, multi-person app needs a clear rule.
- **Affected applications:** A, B
- **Affected features:** M02, M04
- **Severity:** medium
- **Possible solutions:** One rating per person per book; rating again replaces it; Keep every rating as history and show the latest or the average
- **Recommended resolution:** One rating per person per book (unique key, upsert); history is not in the user's request
- **User approval required:** no
- **Status:** resolved (One rating per person per book (unique (owner, book)); rating again replaces it; a rating can be cleared.)

## application:business-rule:rating-scale

- **Conflict:** Shelfie's README and OpenAPI spec say ratings are 1-10 in a field called 'score'; Shelfie's code and Readr's code both use 1-5 'stars'. Documentation vs code, not code vs code (A-C03, A-C04).
- **Affected applications:** A, B
- **Affected features:** M02
- **Severity:** medium
- **Possible solutions:** 1-5 stars as both apps' code does; 1-10 as Shelfie's old docs say (would need a conversion and a decision from the user)
- **Recommended resolution:** 1-5 integer stars: what both apps actually do, and the user said to trust the code
- **User approval required:** no
- **Status:** resolved (Integer 1-5 'stars', enforced on the server and by a database CHECK; anything else is 400. The 1-10 'score' scale in Shelfie's old docs is not used.)

## database:data-integrity:write-persistence

- **Conflict:** Neither source ever commits a transaction, so (inferred from sqlite3 defaults; not run) writes would be lost when the process exits; neither enables SQLite foreign keys, so ratings and list entries can point at missing books.
- **Affected applications:** A, B
- **Affected features:** M02, M05
- **Severity:** medium
- **Possible solutions:** Commit every write and turn on PRAGMA foreign_keys in the unified app; Copy the sources' behaviour
- **Recommended resolution:** Commit every write, enable foreign keys, and test that data survives a restart
- **User approval required:** no
- **Status:** resolved (Commit every write; PRAGMA foreign_keys=ON on every connection; deleting a book removes its rating and list entries (cascade); data survives a restart.)

## database:duplicate-entity:book

- **Conflict:** Book exists in A:Book, B:Book; fields not shared: author (only A)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M04, M05
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge only once it is confirmed they mean the same thing; then list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (Merge into one Book table holding title (A, B) and author (A only, nullable).)

## api:api-shape:path-version-prefix

- **Conflict:** Shelfie's spec uses /api/v1/...; its code serves /api/... (A-C05). Readr has no API.
- **Affected applications:** A
- **Affected features:** M01, M02, M04
- **Severity:** low
- **Possible solutions:** Use /api/... as the code does; Adopt /api/v1/... for the new app
- **Recommended resolution:** Use /api/... (the observed shape); versioning is not needed for a new single app
- **User approval required:** no
- **Status:** resolved (Use /api/... without a version prefix, as Shelfie's code does.)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Book | A, B | add fields that only some sources have: author (only A) (low) | low | - | yes |
| Rating | A | merge rows from every source into one table (low) | low | - | no |
| ReadingList | B | merge rows from every source into one table (low) | low | - | no |
| ListBook | B | merge rows from every source into one table (low) | low | - | no |
