# Module summary: (root) (A BookNow)

Index: `index.json` · Files: 2 · Lines: 19 · Read on: 2026-11-04 · Files read: 2 of 2

## Purpose

Booking and cancellation logic for BookNow, plus a one-line README.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| A-F01 | `bookings.py` | book(): taken check, charge, insert |
| A-F02 | `bookings.py` | cancel(): 24h window, hard delete, no refund |
| A-F03 | `bookings.py`, `README.md` | only the call site; payments.py missing |

## Depends on

Modules: none. External packages: `datetime` (stdlib), `payments` (local module, not included).

## Entry points and important files

- `bookings.py`: all observed logic
- `README.md`: states the three capabilities and Stripe

## Not read, and why

- `payments.py`: not present in the source folder

## Open questions

- How slots become taken; how payment failures and refunds are handled; db engine.
