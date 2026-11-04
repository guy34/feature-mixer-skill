# Module summary: (root) (B NodeCart)

Index: `index.json` · Files: 3 · Lines: 18 · Read on: 2026-11-04 · Files read: 3 of 3

## Purpose

The whole app: an Express route module for cart and Stripe checkout, and a Prisma schema.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| B-F01 | `server.js`, `schema.prisma` | quantity stored as text; no validation |
| B-F02 | `server.js` | client-supplied line_items; no webhook |

## Depends on

Modules: none. External packages: stripe (imported); express and @prisma/client declared in package.json but not imported in server.js (app and prisma are passed in).

## Entry points and important files

- `server.js`: routes; exports `(app, prisma) => {...}`
- `schema.prisma`: Cart, CartItem (not covered by scan_source.py's text-extension list; read manually)
- `package.json`: dependencies and engines; no lifecycle scripts

## Not read, and why

- none

## Open questions

- Where the Express app, Prisma client, products and auth are set up.
