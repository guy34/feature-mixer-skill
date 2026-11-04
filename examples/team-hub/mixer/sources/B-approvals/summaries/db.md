# Module summary: db (B Approvals)

Index: `index.json` · Read on: 2026-11-04 · Files read: all files in the module

## Purpose

Schema with serial integer keys: users (requester/approver/admin), approval requests, threaded comments, email outbox.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| B-F01, B-F05 | `db/schema.sql` | users (B-E03) |
| B-F02 | `db/schema.sql` | approval_requests (B-E04) |
| B-F03 | `db/schema.sql` | comments with parent_id (B-E06) |

## Depends on

External packages imported here: none.

## Entry points and important files

- `db/schema.sql`

## Not read, and why

- Nothing skipped.

## Open questions

- None for the slice studied.
