# NodeCart (B): reverse-engineering report

App id: B · Access: own-code · Licence: proprietary (user's own, no licence file) · Code reuse: allowed
Slice studied: cart and Stripe checkout (core loop) · Coverage: complete · Size: S

Basis marks: **observed** (seen in the code), **documented**, **inferred**, **unknown**.
The structured version of this report is `source.json` in the same folder.

## Summary

NodeCart is an Express + Prisma route module with a cart and a Stripe
Checkout endpoint. It stores ids as uuid strings and the cart quantity as
text. Checkout passes the client's line items straight to Stripe, so the
client chooses its own prices; no order is recorded and no webhook confirms
payment. There is no Product model, no auth and no frontend.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | sources/nodecart | 2026-11-04 | 3 files, all read; scanned first (no findings, but the scanner silently skipped schema.prisma as an unlisted extension; read manually); nothing run |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | observed | `sources/nodecart/server.js:4` | POST /api/cart/items stores body cartId, productId, String(quantity); no validation or ownership check |
| B-E02 | B-R01 | observed | `sources/nodecart/server.js:5` | POST /api/checkout: Stripe Checkout session, mode payment, line_items from the request body |
| B-E03 | B-R01 | observed | `sources/nodecart/server.js:2` | Stripe client from env var STRIPE_SECRET |
| B-E04 | B-R01 | observed | `sources/nodecart/schema.prisma:1-5` | Cart: id String uuid, userId String, items CartItem[] |
| B-E05 | B-R01 | observed | `sources/nodecart/schema.prisma:6-11` | CartItem: id String uuid, cartId, productId, quantity all String |
| B-E06 | B-R01 | observed | `sources/nodecart/package.json:1` | node >=20; express ^4.19.0, @prisma/client ^5.10.0, stripe ^14.0.0 |
| B-E07 | B-R01 | inferred | `sources/nodecart/schema.prisma:1-11` | no Product model; checkout not tied to the cart |

## Features

### B-F01 Add item to cart

- **Source application:** NodeCart (B)
- **Evidence:** B-E01, B-E04, B-E05
- **Description:** add a product and quantity to a cart
- **Observed behaviour:** creates a CartItem from the body and returns it
- **Business logic:** no validation; quantity stored as text; client picks cartId
- **Data requirements:** Cart, CartItem
- **Dependencies:** none
- **Integration requirements:** ownership checks and a product catalog in the unified app
- **Basis and confidence:** observed, high

### B-F02 Stripe checkout

- **Source application:** NodeCart (B)
- **Evidence:** B-E02, B-E03
- **Description:** pay through a Stripe Checkout session
- **Observed behaviour:** sends request items to Stripe as line_items, returns the session
- **Business logic:** prices come from the client unchecked; cart not read; no order; no webhook
- **Data requirements:** request items only
- **Dependencies:** none in the source (logically it needs a cart)
- **Integration requirements:** Stripe account and key (STRIPE_SECRET), test mode
- **Basis and confidence:** observed, high

## Screens and workflows

None: the source is a JSON API with no frontend.

## Navigation

None (API only).

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Cart | id (String uuid) | userId (String) | items → CartItem[] | observed | B-E04 |
| CartItem | id (String uuid) | cartId (String), productId (String), quantity (String) | cartId → Cart (no @relation declared) | observed | B-E05 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/cart/items` | unknown | cartId, productId, quantity (strings) | created CartItem | none handled | B-E01 |
| POST | `/api/checkout` | unknown | items (Stripe line_items) | Stripe session | none handled | B-E02 |

## Authentication and authorization

None in the source; the Express app is built elsewhere, so middleware is unknown. Cart.userId implies users (inferred).

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |
| Stripe | Checkout sessions | B-F02 | B-E02, B-E03 |

## Architecture and stack

Node.js >=20, Express ^4.19.0, Prisma ^5.10.0, Stripe SDK ^14.0.0 (observed, B-E06).

## Configuration

- `STRIPE_SECRET`: Stripe secret key (name only).

## Error handling

No try/catch; failures fall through to Express defaults defined outside this source.

## Unknowns

- No Product model; where products and prices live.
- Auth middleware outside server.js.
- Prisma datasource and relations not declared.
- Payment confirmation (no webhook, no order).
- No frontend.
