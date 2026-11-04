# Module summary: src/contacts (A MegaCRM)

Index: `index.json` · Files: 2 · Lines: 14 · Read on: 2026-11-04 · Files read: 2 of 2

## Purpose

Contact records: create, search, and merge duplicates.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| A-F01 | `src/contacts/service.py:4-8`, `src/contacts/schema.sql` | create and LIKE search on name or email |
| A-F02 | `src/contacts/service.py:10-13` | moves deals then deletes the dropped contact; docstring mentions notes that do not exist |

## Depends on

Modules: src/shared. External packages: none.

## Entry points and important files

- `src/contacts/service.py`: create_contact, search_contacts, merge_duplicates.
- `src/contacts/schema.sql`: contacts(id, name not null, email unique, company).

## Not read, and why

- none

## Open questions

- Is merge meant to run in a transaction, and should it merge fields of the dropped contact?
