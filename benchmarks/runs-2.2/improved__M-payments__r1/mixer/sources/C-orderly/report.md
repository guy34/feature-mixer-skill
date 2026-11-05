# Orderly (C): reverse-engineering report

App id: C · Access: own-code · Licence: not stated (no licence file, no rights in task.md) · Code reuse: unknown
Slice studied: the whole source (sources/orderly, 1 file) · Coverage: complete · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the code), **documented** (the user's description in task.md), **inferred**, or **unknown**. The structured version of this report is `source.json` in the same folder.

## Summary

Orderly declares four order states (pending, paid, cancelled, refunded) and a cancel function. Observed: cancel overwrites the status with 'cancelled' for any order, including a paid one, and issues no refund; no code ever sets 'paid' or 'refunded', and there is no transition table.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| C-R01 | local-directory | `sources/orderly` | 2026-11-04 | scanned first (no findings); read in full |
| C-R02 | documentation | `task.md` | 2026-11-04 | the user's own description of the source, not the source's docs |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| C-E01 | C-R01 | observed | `sources/orderly/orders.py:1` | STATES = ('pending', 'paid', 'cancelled', 'refunded') |
| C-E02 | C-R01 | observed | `sources/orderly/orders.py:2-3` | cancel(order) sets status to 'cancelled' whatever the current status; its comment says a paid order is cancelled without a refund |
| C-E03 | C-R02 | documented | `task.md#scenario-m` | The user describes Orderly as orders with states pending, paid, cancelled, refunded |

## Features

### C-F01 Order lifecycle states

- **Source application:** Orderly (C)
- **Evidence:** C-E01, C-E03
- **Description:** Orders carry one of four states: pending, paid, cancelled, refunded
- **Observed behaviour:** The states are declared; no code sets 'paid' or 'refunded' and no transition table exists
- **Business logic:** Allowed values: pending, paid, cancelled, refunded. Transitions are not defined in the code.
- **Data requirements:** Order.status
- **Dependencies:** none
- **Integration requirements:** none
- **Basis and confidence:** observed, high

### C-F02 Cancel an order

- **Source application:** Orderly (C)
- **Evidence:** C-E02
- **Description:** Moves an order to cancelled
- **Observed behaviour:** cancel() overwrites status with 'cancelled' for any order, including paid and refunded ones
- **Business logic:** No refund for a paid order; no guard against cancelling twice or cancelling a refunded order.
- **Data requirements:** Order.status
- **Dependencies:** C-F01
- **Integration requirements:** none
- **Basis and confidence:** observed, high

## Screens and workflows

None: the source is a library function with no screens, routes or user interface (observed).

## Navigation

None (observed: no routes or menus).

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Order | none in the code (in-memory dict) | status (string) | none | observed | C-E01, C-E02 |

## API

No HTTP API (observed). Python entry points: `STATES`, `cancel(order)`.

## Authentication and authorization

None in the code (observed). No users, roles or permission checks.

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| none | - | - | - |

## Architecture and stack

Python (plain function and a constant); none (observed). No packages, no manifest, no runtime pin.

## Configuration

None (observed: no settings or environment variables).

## Error handling

- any: no error handling in the code (observed)

## Unknowns

- How orders are created, stored and looked up: no code for it
- Which code moves an order to paid or refunded: none in Orderly
- Rights: task.md states no rights and there is no licence file, so code_reuse is unknown and nothing is copied
