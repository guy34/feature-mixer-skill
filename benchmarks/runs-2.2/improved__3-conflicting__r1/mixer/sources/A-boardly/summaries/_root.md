# Module summary: (root) (A Boardly)

Index: `index.json` · Files: 3 · Lines: 13 · Read on: 2026-11-04 · Files read: 3 of 3

## Purpose

The whole Boardly slice: API handlers, database schema and client routes for a pre-moderated forum.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| A-F01 | `routes.js`, `schema.sql`, `client-routes.js` | password check lives in an unseen db layer |
| A-F02 | `routes.js`, `schema.sql` | status pending by default; 5000-character check |
| A-F03 | `routes.js` | no status filter on read |
| A-F04 | `routes.js`, `schema.sql`, `client-routes.js` | moderator only |
| A-F05 | `client-routes.js` | route only, no list endpoint |

## Depends on

Modules: none. External packages: none imported in the files (framework inferred from usage).

## Entry points and important files

- `routes.js`: every API handler
- `schema.sql`: users and posts tables
- `client-routes.js`: the three screens

## Not read, and why

- none: all three files read

## Open questions

- db layer, session middleware, password storage, list endpoint (see source.json unknowns)
