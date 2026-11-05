# Module summary: (root) (B Linkup)

Index: `index.json` · Files: 1 · Lines: 7 · Read on: 2026-11-05 · Files read: 1 of 1

## Purpose

OAuth sign-in callback that finds or creates an account per (provider, subject).

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| B-F01 | `oauth.py` | callback(); email_verified ignored; no token issued |

## Depends on

Modules: none. External packages: none.

## Entry points and important files

- `oauth.py`: the whole slice.

## Not read, and why

- Nothing; every file was read.

## Open questions

- How the OAuth exchange and provider-response verification work (not in the provided code).
- Session mechanism after sign-in.
