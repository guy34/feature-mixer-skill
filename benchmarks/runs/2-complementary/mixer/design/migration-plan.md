# FileShare: migration plan

Status: approved · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:file | File | one key type: id TEXT (uuid4 hex) | high (flagged by the script) | none: no source has persisted rows to re-key | A01 |
| migration:file | File | id and name as TEXT (A text = B str) | high (flagged by the script) | none: same value type | A01 |
| migration:file | File | add B's data as file_content.data BLOB | low | none | A01 |
| migration:filecontent | FileContent | B:File.data bytes -> BLOB; B's id/name live in File | high (flagged) | none: no B data persisted | A02 |
| migration:sharelink | ShareLink | C str fields -> TEXT; password_hash -> salted PBKDF2 | high (flagged) | old SHA-256 hashes would not carry over; none exist (C is in-memory) | A03 |

## Before running

- Backup: not applicable; there is no existing database. A's store is not in the source and B and C hold data only in memory.
- Dry run: the app's own test suite creates the schema in a temporary folder on every run.
- Checks: tests assert the tables exist and that rows round-trip (upload then list, preview, download).

## Rollback

Delete the new SQLite file (the app's own data only); no source data is touched.

## Result

Schema created fresh by `app/fileshare/db.py` at startup. No data migrated.
