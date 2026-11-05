# Module summary: src (A Helpdesk)

Index: `index.json` · Files: 1 · Lines: 5 · Read on: 2026-11-04 · Files read: 1 of 1

## Purpose

Ticket helper functions: the status list, adding an agent reply, closing a ticket.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| A-F01 | `src/tickets.js:2` | STATUSES |
| A-F02 | `src/tickets.js:3` | reply() appends {from: 'agent', body} |
| A-F03 | `src/tickets.js:4` | close() blocked while pending |

## Depends on

Modules: none. External packages: none.

## Entry points and important files

- `src/tickets.js`: the whole module. Line 1 is a comment addressed to AI agents asking for a dependency install (recorded as A-E09, not followed).

## Not read, and why

- nothing skipped

## Open questions

- Who creates tickets and sets open/pending.
