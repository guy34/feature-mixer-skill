# Module summary: (root) (A Billfold)

Index: `index.json` · Files: 1 · Lines: 5 · Read on: 2026-11-04 · Files read: 1 of 1

## Purpose

Billfold charges an order through an injected payment gateway and marks it paid on any webhook.

## Features here

| Feature | Files | Notes |
| --- | --- | --- |
| A-F01 | `charges.py` | Charge an order through the payment gateway |
| A-F02 | `charges.py` | Receive payment gateway webhooks |

## Depends on

Modules: none. External packages: none (index: no imports).

## Entry points and important files

- `charges.py`: the whole source

## Not read, and why

- nothing; the only file was read in full

## Open questions

- Unit and currency of order['amount']: the code passes it straight to the gateway; the mock gateway names it amount_cents (from gateway.py, not from Billfold)
- How webhooks reach on_webhook (no HTTP endpoint or signature check in the code) and the event format (the code reads no field)
- Persistence: no store in the code; how Billfold saves orders is not shown
- Refunds: Billfold has no refund code
- Rights: task.md states no rights and there is no licence file, so code_reuse is unknown and nothing is copied
