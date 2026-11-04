# Compatibility report

Scope: kept features only. Apps: A, B, C.

| Severity | Count |
|---|---|
| critical | 1 |
| high | 4 |
| medium | 2 |
| low | 2 |

## application:security:checkout-client-prices

- **Conflict:** B's /api/checkout passes request line_items to Stripe unchanged, so a customer can pay any price they choose
- **Affected applications:** B
- **Affected features:** M05
- **Severity:** critical
- **Possible solutions:** Build line items on the server from the cart and catalog prices; Drop checkout
- **Recommended resolution:** Server-built line items from the session user's cart and Product.price; the request carries no items or prices
- **User approval required:** yes
- **Status:** resolved (Rebuild checkout so line items come only from the session user's cart and Product.price_minor; the request carries no items or prices (D04))

## application:auth-gap:no-identity-system

- **Conflict:** No source has sign-in: A and B carts have a user_id with no User model, and C's reviews need a customer, but no source shows how users authenticate
- **Affected applications:** A, B, C
- **Affected features:** M01, M04, M07, M09
- **Severity:** high
- **Possible solutions:** Add one minimal accounts module (email + password, slow hash, server session in an http-only cookie); Use an external identity provider the user chooses
- **Recommended resolution:** One minimal accounts module (customer and shop-owner roles) built new for the unified app; it is platform, not a source feature
- **User approval required:** yes
- **Status:** resolved (Add a new accounts module: email + password (argon2id), server session in an http-only secure cookie, roles customer and owner, one permission check (D05))

## application:workflow:purchase-confirmation

- **Conflict:** C shows reviews only after a confirmed purchase, but B keeps no order and never confirms payment (no webhook)
- **Affected applications:** B, C
- **Affected features:** M05, M09
- **Severity:** high
- **Possible solutions:** Add an Order entity marked paid by a verified Stripe webhook; the review gate reads it; Drop the verified-purchase gate
- **Recommended resolution:** Order (pending -> paid) written at checkout and confirmed by a signature-verified Stripe webhook; reviews require a paid order containing the product
- **User approval required:** yes
- **Status:** resolved (Add Order/OrderItem; checkout writes a pending Order; a signature-verified Stripe webhook marks it paid; the review gate needs a paid order containing the product (D04, D08))

## database:field-type:cartitem-quantity

- **Conflict:** B stores CartItem.quantity as text; A (and any sensible cart) types it as Integer. Unvalidated text quantities can be non-numeric or negative
- **Affected applications:** A, B
- **Affected features:** M01, M04
- **Severity:** high
- **Possible solutions:** Integer quantity with a positive check on the server; Keep text and parse it on every read
- **Recommended resolution:** Integer quantity >= 1, checked on the server; B's existing cart rows are not migrated (see migration plan)
- **User approval required:** yes
- **Status:** resolved (CartItem.quantity is integer with a CHECK quantity >= 1, validated on the server; B's text quantities are not migrated (D06))

## database:foreign-key:cartitem-product-id

- **Conflict:** B stores CartItem.productId as a String with no Product model; the kept catalog is A's, whose Product.id is Integer. B's cart rows cannot point at A's products without conversion
- **Affected applications:** A, B
- **Affected features:** M01, M04
- **Severity:** high
- **Possible solutions:** Integer product_id with a real foreign key to products.id (A's keys kept); Re-key A's products to uuid strings to match B
- **Recommended resolution:** Integer product_id foreign key to products.id; A's catalog keeps its ids; B's text product ids are not carried over
- **User approval required:** yes
- **Status:** resolved (CartItem.product_id is an integer foreign key to products.id (A's keys kept); B's text product ids are not carried over (D02, D06))

## dependency:framework:backend-framework

- **Conflict:** Competing backend frameworks: Express (B); Flask (A)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** medium
- **Possible solutions:** Choose one framework for this layer and rebuild the others' features in it; Run them side by side only as a short, planned migration
- **Recommended resolution:** One backend framework; Express is used by the most sources
- **User approval required:** no
- **Status:** resolved (Flask (Python) is the one backend framework; NodeCart's Express endpoints are rebuilt in Flask. The script's 'Express is used by the most sources' is a 1-1 tie, so the choice follows where the adapted code and durable data are (D01))

## dependency:framework:data-layer

- **Conflict:** Competing data layers: Prisma (B); SQLAlchemy (A)
- **Affected applications:** A, B
- **Affected features:** not linked to a feature
- **Severity:** medium
- **Possible solutions:** Choose one framework for this layer and rebuild the others' features in it; Run them side by side only as a short, planned migration
- **Recommended resolution:** One data layer; Prisma is used by the most sources
- **User approval required:** no
- **Status:** resolved (SQLAlchemy is the one data layer; Prisma is not used (D01, D02))

## api:api-version:reviews-path

- **Conflict:** Reviewly documents /v2/products/{productId}/reviews; A and B use unversioned /api/... paths
- **Affected applications:** C
- **Affected features:** M06, M07
- **Severity:** low
- **Possible solutions:** Unversioned /api/products/{id}/reviews in the unified API; Version the whole unified API
- **Recommended resolution:** Unversioned /api/products/{id}/reviews; Reviewly's path is not copied
- **User approval required:** no
- **Status:** resolved (Unversioned /api/products/{id}/reviews; Reviewly's /v2 path is not copied (D07))

## database:naming-style:fields

- **Conflict:** Field naming styles differ (camelCase: B; snake_case: C)
- **Affected applications:** B, C
- **Affected features:** not linked to a feature
- **Severity:** low
- **Possible solutions:** Pick one naming style for tables and fields and map the others
- **Recommended resolution:** Use one style (snake_case is usual for SQL)
- **User approval required:** no
- **Status:** resolved (snake_case for every table and field; B's camelCase names map through compat/aliases.json)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Product | A | A.Product.price: number to integer can lose or reject values (high) | high | price | yes |
| Cart | B | B.Cart.id: text to integer can lose or reject values (high); B.Cart.userId: text to integer can lose or reject values (high) | high | id, userId | yes |
| CartItem | B | B.CartItem.id: text to integer can lose or reject values (high); B.CartItem.cartId: text to integer can lose or reject values (high); B.CartItem.productId: text to integer can lose or reject values (high); B.CartItem.quantity: text to integer can lose or reject values (high) | high | cartId, id, productId, quantity | yes |
