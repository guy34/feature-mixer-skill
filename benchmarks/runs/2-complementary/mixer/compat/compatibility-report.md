# Compatibility report

Scope: kept features only. Apps: A, B, C.

| Severity | Count |
|---|---|
| critical | 1 |
| high | 5 |
| medium | 4 |

## database:primary-key:file

- **Conflict:** File primary keys differ (A: text, B: unknown)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M03, M04, M05, M06
- **Severity:** critical
- **Possible solutions:** Pick one key type for the merged entity and re-key the other source's rows; Keep a legacy_id column holding the old key during migration
- **Recommended resolution:** Use one key type (uuid is usual for merged data) and add a legacy_id column while migrating
- **User approval required:** yes
- **Status:** resolved (One File table keyed by id TEXT holding a uuid4 hex. B never persisted files (it receives a dict) and A's store is not in the source, so there are no existing rows to re-key; no legacy_id needed.)

## application:identity:owner

- **Conflict:** No source authenticates anyone: A takes owner_id from the caller and C has no identity at all, yet the merged app must know who owns a file
- **Affected applications:** A, C
- **Affected features:** M01, M02, M03, M07, M10
- **Severity:** high
- **Possible solutions:** Minimal accounts: username + password (salted PBKDF2), opaque session token in an http-only cookie; Trust an owner id header (unsafe)
- **Recommended resolution:** Minimal accounts with a salted PBKDF2 password and a server-side session in an http-only cookie (standard library only)
- **User approval required:** yes
- **Status:** resolved (Minimal accounts: register/login with username + password hashed by salted PBKDF2-HMAC-SHA256; server-side session token (secrets.token_urlsafe) in an http-only SameSite=Strict cookie.)

## application:permission:file-access

- **Conflict:** A scopes every file action by owner_id; C has no owner concept, so any caller could create or revoke a link for any file_id
- **Affected applications:** A, C
- **Affected features:** M01, M02, M03, M07, M09, M10
- **Severity:** high
- **Possible solutions:** Owner-only link create/revoke; a token grants read-only access to that one file; Let anyone with the file id share it (weakens A's owner scoping)
- **Recommended resolution:** Owner-only link create/revoke; a valid token (and password, if set) grants read-only metadata, preview and download of that one file
- **User approval required:** yes
- **Status:** resolved (Owner-only link create/revoke and owner-only file list/delete/preview/content; a valid unexpired token (plus password if set) grants read-only metadata, preview and download of that one file.)

## application:security:link-password-hash

- **Conflict:** C stores link passwords as unsalted SHA-256 and compares with !=; the unified app's rule is a slow salted hash and constant-time compare
- **Affected applications:** C
- **Affected features:** M08, M09
- **Severity:** high
- **Possible solutions:** Salted PBKDF2-HMAC-SHA256 with hmac.compare_digest; Keep C's unsalted SHA-256
- **Recommended resolution:** Salted PBKDF2-HMAC-SHA256 (hashlib.pbkdf2_hmac) with hmac.compare_digest
- **User approval required:** yes
- **Status:** resolved (Salted PBKDF2-HMAC-SHA256 with hmac.compare_digest for link passwords.)

## database:field-type:file.id

- **Conflict:** File.id types differ (A: text, B: str)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M03, M04, M05, M06
- **Severity:** high
- **Possible solutions:** Choose the wider type and convert the narrower data; Split into two fields if they mean different things
- **Recommended resolution:** One type per field; convert in a migration
- **User approval required:** yes
- **Status:** resolved (id is TEXT in SQLite and str in Python; A's text and B's str are the same value type.)

## database:field-type:file.name

- **Conflict:** File.name types differ (A: text, B: str)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M03, M04, M05, M06
- **Severity:** high
- **Possible solutions:** Choose the wider type and convert the narrower data; Split into two fields if they mean different things
- **Recommended resolution:** One type per field; convert in a migration
- **User approval required:** yes
- **Status:** resolved (name is TEXT in SQLite and str in Python; no conversion needed.)

## application:route:thumbnail-url

- **Conflict:** B returns /thumbs/<id>.png but nothing creates or serves it, and resizing needs an imaging library the standard library lacks
- **Affected applications:** B
- **Affected features:** M05
- **Severity:** medium
- **Possible solutions:** Preview URL points at a route that serves the original image (owner route or link route); Defer image preview
- **Recommended resolution:** Serve the original image with its content type at /api/files/<id>/content (owner) or /s/<token>/content (link)
- **User approval required:** no
- **Status:** resolved (Image preview URL points at /api/files/<id>/content (owner) or /s/<token>/content (link); no resizing.)

## database:duplicate-entity:file

- **Conflict:** File exists in A:File, B:File; fields not shared: created_at (only A), data (only B), owner_id (only A), size (only A)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M03, M04, M05, M06
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge into one entity; list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (Merge into one File entity with A's fields (id, owner_id, name, size, created_at); B's data field lives in file_content (see database:storage:file-bytes).)

## database:lifecycle:file-delete-links

- **Conflict:** Deleting a file in A would leave C's links pointing at a missing file_id
- **Affected applications:** A, C
- **Affected features:** M03, M07, M09
- **Severity:** medium
- **Possible solutions:** Delete a file's share links with it (foreign key ON DELETE CASCADE); Keep links and return 404 when opened
- **Recommended resolution:** ON DELETE CASCADE from share_links.file_id to files.id
- **User approval required:** no
- **Status:** resolved (share_links.file_id REFERENCES files(id) ON DELETE CASCADE (foreign keys enabled per connection).)

## database:storage:file-bytes

- **Conflict:** A's files table has no column for the file's bytes, but B's preview needs them
- **Affected applications:** A, B
- **Affected features:** M01, M04, M05
- **Severity:** medium
- **Possible solutions:** Store bytes in a separate SQLite BLOB table keyed by file id (max 10 MB each); Store bytes on disk under a data folder
- **Recommended resolution:** Separate file_content table (file_id primary key, data BLOB) so listing never loads bytes
- **User approval required:** no
- **Status:** resolved (file_content(file_id PK REFERENCES files ON DELETE CASCADE, data BLOB).)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| File | A, B | re-key rows to one primary key type (A: text, B: unknown) and rewrite foreign keys that point at them (high); convert id to one type (A: text, B: str) (high); convert name to one type (A: text, B: str) (high); add fields that only some sources have: created_at (only A), data (only B), owner_id (only A), size (only A) (low); A.File.created_at: timestamp to text keeps every value (low) | high | - | yes |
| FileContent | B | B.File fields not kept in FileContent: id, name (high); B.File.data: bytes to blob can lose or reject values (high) | high | data, id, name | yes |
| ShareLink | C | C.ShareLink.token: str to text can lose or reject values (high); C.ShareLink.file_id: str to text can lose or reject values (high); C.ShareLink.password_hash: str | none to text can lose or reject values (high) | high | file_id, password_hash, token | yes |
