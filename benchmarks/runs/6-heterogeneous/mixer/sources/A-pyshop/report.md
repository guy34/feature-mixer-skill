# PyShop (A): reverse-engineering report

App id: A · Access: own-code · Licence: proprietary (user's own, no licence file) · Code reuse: allowed
Slice studied: catalog and cart (core loop) · Coverage: complete · Size: S

Basis marks: **observed** (seen in the code), **documented**, **inferred**, **unknown**.
The structured version of this report is `source.json` in the same folder.

## Summary

PyShop is a small Flask + SQLAlchemy JSON API for a shop: a product catalog
and a cart. It declares two routes (list products, add to cart) and three
models (Product, Cart, CartItem) with integer keys. The handler bodies are
elided in the source, so behaviour beyond the declarations cannot be seen.
A category filter is mentioned in a comment but Product has no category
field. There is no auth, frontend or checkout.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| A-R01 | local-directory | sources/pyshop | 2026-11-04 | 3 files, all read; scanned first (no findings); nothing run |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| A-E01 | A-R01 | observed | `sources/pyshop/app.py:5` | GET /api/products declared; comment: browse catalog, filter by category; body elided |
| A-E02 | A-R01 | observed | `sources/pyshop/app.py:8` | POST /api/cart/items declared; body product_id int, quantity int; body elided |
| A-E03 | A-R01 | observed | `sources/pyshop/models.py:4-5` | Product: id Integer PK, name String, price Numeric |
| A-E04 | A-R01 | observed | `sources/pyshop/models.py:7-8` | Cart: id Integer PK, user_id Integer (no User model) |
| A-E05 | A-R01 | observed | `sources/pyshop/models.py:10-11` | CartItem: id Integer PK, cart_id FK carts.id, product_id Integer, quantity Integer |
| A-E06 | A-R01 | observed | `sources/pyshop/requirements.txt:1-2` | flask 3.0.0, sqlalchemy 2.0.25 |
| A-E07 | A-R01 | inferred | `sources/pyshop/models.py:4-5` | no category column, so the category filter has no visible data |

## Features

### A-F01 Product catalog

- **Source application:** PyShop (A)
- **Evidence:** A-E01, A-E03
- **Description:** list products (name, price)
- **Observed behaviour:** route declared; handler body elided
- **Business logic:** none visible
- **Data requirements:** Product.id, name, price
- **Dependencies:** none
- **Basis and confidence:** observed, medium

### A-F02 Category filter on the catalog

- **Source application:** PyShop (A)
- **Evidence:** A-E01, A-E07
- **Description:** filter products by category
- **Observed behaviour:** only named in a code comment
- **Business logic:** unknown
- **Data requirements:** a category on Product (not present)
- **Dependencies:** A-F01
- **Basis and confidence:** inferred, low

### A-F03 Add product to cart

- **Source application:** PyShop (A)
- **Evidence:** A-E02, A-E04, A-E05
- **Description:** add a product and quantity to the user's cart
- **Observed behaviour:** route declared with integer product_id and quantity; handler elided
- **Business logic:** quantity is an integer; validation not visible
- **Data requirements:** Cart, CartItem
- **Dependencies:** A-F01
- **Integration requirements:** a signed-in user (Cart.user_id)
- **Basis and confidence:** observed, medium

## Screens and workflows

None: the source is a JSON API with no frontend.

## Navigation

None (API only).

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Product | id (Integer) | name (String), price (Numeric) | - | observed | A-E03 |
| Cart | id (Integer) | user_id (Integer) | user_id → (no User model) | observed | A-E04 |
| CartItem | id (Integer) | cart_id (Integer), product_id (Integer), quantity (Integer) | cart_id → Cart | observed | A-E05 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/products` | unknown | - | not visible | unknown | A-E01 |
| POST | `/api/cart/items` | unknown | product_id int, quantity int | not visible | unknown | A-E02 |

## Authentication and authorization

None in the source. Cart.user_id (A-E04) implies users exist elsewhere (inferred).

## Integrations

None.

## Architecture and stack

Python, Flask 3.0.0, SQLAlchemy 2.0.25 (observed, A-E06). Database engine not configured.

## Configuration

None found.

## Error handling

Unknown: handler bodies are elided.

## Unknowns

- Handler bodies are elided: response shapes, validation and errors.
- Category filter: comment only; no category field.
- Users and auth: Cart.user_id but no User model or sign-in.
- Database engine and connection settings.
- No frontend.
