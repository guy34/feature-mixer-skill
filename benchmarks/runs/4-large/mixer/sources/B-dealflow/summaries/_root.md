# Module summary: (root) (B DealFlow)

Index: `index.json` · Files: 1 · Lines: 14 · Read on: 2026-11-04 · Files read: 1 of 1

## Purpose

Deals pipeline with caller-supplied stages and stale-deal email reminders.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| B-F01 | `deals.py:4-9` | stages parameter, default new/contacted/negotiating/closed; sets moved_at |
| B-F02 | `deals.py:11-14` | emails owner_email for deals not moved in 14 days |

## Depends on

Modules: none. External packages: none (standard library datetime).

## Entry points and important files

- `deals.py`: move_deal, stale_deal_reminders.

## Not read, and why

- none

## Open questions

- Where custom stages are stored; what triggers reminders; deal schema.
