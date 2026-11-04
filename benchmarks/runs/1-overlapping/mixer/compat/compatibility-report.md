# Compatibility report

Scope: kept features only. Apps: A, B.

| Severity | Count |
|---|---|
| critical | 1 |
| high | 2 |
| medium | 4 |
| low | 2 |

## database:primary-key:note

- **Conflict:** Note primary keys differ (A: integer, B: uuid)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M04, M05, M06, M07, M08, M09
- **Severity:** critical
- **Possible solutions:** Pick one key type for the merged entity and re-key the other source's rows; Keep a legacy_id column holding the old key during migration
- **Recommended resolution:** Use one key type (uuid is usual for merged data) and add a legacy_id column while migrating
- **User approval required:** yes
- **Status:** resolved (uuid (text) primary key for Note and Tag in the unified app; A's integer ids kept in legacy_id during migration, B's uuids kept as-is)

## application:api:note-update-semantics

- **Conflict:** A's PUT sets only title and body; B's PUT merges the whole request body into the note (Object.assign), so a client can overwrite id, pinned or labels
- **Affected applications:** A, B
- **Affected features:** M01, M02
- **Severity:** high
- **Possible solutions:** Whitelist title and body on update; pin/unpin and tags through their own endpoints; Keep B's merge semantics
- **Recommended resolution:** Whitelist title and body; reject unknown fields with 400
- **User approval required:** yes
- **Status:** resolved (Update whitelists title and body; unknown fields rejected with 400; pin/unpin and tags have their own endpoints)

## application:business-rule:notes.list.order

- **Conflict:** Rule notes.list.order differs (A: "created_at desc", B: "pinned first (insertion order otherwise)")
- **Affected applications:** A, B
- **Affected features:** M01, M02, M08
- **Severity:** high
- **Possible solutions:** Choose one value and record why; Make it a setting if both are legitimate
- **Recommended resolution:** Pick one value with the user; make it configurable only if both are needed
- **User approval required:** yes
- **Status:** resolved (One order everywhere: pinned first, then created_at descending (keeps A's order for unpinned notes, adds B's pinning); not configurable)

## application:database:jotter-data-in-memory

- **Conflict:** B keeps notes only in process memory, so there is no stored B data to migrate; any live B data can only be captured from a running instance before it stops
- **Affected applications:** B
- **Affected features:** M02
- **Severity:** medium
- **Possible solutions:** Treat B as having no data to migrate; Capture a running instance's GET /api/notes output (needs approval to run or call it)
- **Recommended resolution:** Plan the B import from a JSON dump of GET /api/notes; if none exists, B has no data to migrate
- **User approval required:** no
- **Status:** resolved (B has no stored data; import only from a JSON dump of GET /api/notes if the user supplies one, otherwise nothing to migrate)

## application:database:labels-to-tags

- **Conflict:** B stores labels as a free-text array per note (duplicates allowed); the kept model is A's shared, uniquely named tags. Migrating labels collapses duplicates and case variants
- **Affected applications:** A, B
- **Affected features:** M03, M04
- **Severity:** medium
- **Possible solutions:** Map each distinct trimmed, case-folded label to one tag and link it; Discard B's labels
- **Recommended resolution:** Map labels to tags (trim, case-fold, de-duplicate); log merged variants
- **User approval required:** no
- **Status:** resolved (Map each distinct trimmed, case-folded label to one tag and link it; log merged variants)

## database:duplicate-entity:note

- **Conflict:** Note exists in A:Note, B:Note; fields not shared: created_at (only A), labels (only B), pinned (only B), updated_at (only B)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M04, M05, M06, M07, M08, M09
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge into one entity; list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (Merge into one Note table: id, legacy_id, title, body (B content), pinned, created_at, updated_at; field origins listed in architecture.json)

## dependency:runtime-mix:backend-runtime

- **Conflict:** Several runtimes: node: B; python: A
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** medium
- **Possible solutions:** Choose one backend runtime and rebuild the features from the other; Keep two services only if a kept feature truly needs the other runtime
- **Recommended resolution:** One backend runtime for the unified app, chosen in the architecture phase
- **User approval required:** no
- **Status:** resolved (One backend runtime: Python (A's runtime); B's features rebuilt in Python)

## application:application:export-filenames

- **Conflict:** B names export files <title>.md, so equal titles collide and titles with / or other unsafe characters produce bad paths
- **Affected applications:** B
- **Affected features:** M09
- **Severity:** low
- **Possible solutions:** Slugify title and append a short id; Keep raw titles
- **Recommended resolution:** Slugify title plus first 8 characters of the uuid
- **User approval required:** no
- **Status:** resolved (File name = slugified title + '-' + first 8 characters of the uuid + '.md')

## database:naming-style:fields

- **Conflict:** Field naming styles differ (camelCase: B; snake_case: A)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** low
- **Possible solutions:** Pick one naming style for tables and fields and map the others
- **Recommended resolution:** Use one style (snake_case is usual for SQL)
- **User approval required:** no
- **Status:** resolved (snake_case for all tables and fields; B's camelCase mapped (updatedAt -> updated_at))

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Note | A, B | re-key rows to one primary key type (A: integer, B: uuid) and rewrite foreign keys that point at them (high); add fields that only some sources have: created_at (only A), labels (only B), pinned (only B), updated_at (only B) (low); B.Note fields not kept in Note: labels (high); B.Note.updatedAt: date to timestamp keeps every value (low) | high | labels | yes |
| Tag | A | merge rows from every source into one table (low) | low | - | no |
| NoteTag | A | A.NoteTag.note_id: integer to uuid can lose or reject values (high); A.NoteTag.tag_id: integer to uuid can lose or reject values (high) | high | note_id, tag_id | yes |
