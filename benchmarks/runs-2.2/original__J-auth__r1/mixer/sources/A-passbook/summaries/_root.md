# Module summary: (root) (A Passbook)

Index: `index.json` · Files: 1 · Lines: 12 · Read on: 2026-11-05 · Files read: 1 of 1

## Purpose

Email and password accounts with in-memory storage and session tokens.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| A-F01 | `accounts.py` | register(); overwrites duplicates |
| A-F02 | `accounts.py` | login(); token sessions without expiry |

## Depends on

Modules: none. External packages: hashlib (standard library); also os, secrets.

## Entry points and important files

- `accounts.py`: the whole slice.

## Not read, and why

- Nothing; every file was read.

## Open questions

- Whether the full Passbook app has logout, reset or verification elsewhere.
