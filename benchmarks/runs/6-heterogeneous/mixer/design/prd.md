# Unified online shop: product requirements

Version: 2026-11-04 · Sources: A: PyShop, B: NodeCart, C: Reviewly (closed, docs only) · Status: approved (benchmark-operator, pre-approved in task)

## Problem

The user runs two partial shops: PyShop has a catalog and cart but no payment;
NodeCart has a cart and Stripe payment but no catalog, and trusts the client
with prices. Neither has accounts or reviews. One shop that lists products,
takes a cart to a safe Stripe payment, and lets buyers review what they
bought replaces both and adds the review capability Reviewly documents.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Shopper | find a product, buy it, review it | customer |
| Shop owner | keep products and prices right | owner |

## Core loop

1. Browse products. 2. Add to cart. 3. Pay with Stripe Checkout. 4. After the order is paid, rate and review the product.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Product catalog | A | adapt | must | A's Product model; price in integer minor units |
| M04 | Shopping cart | B | improve | must | integer quantity, cart from session, product FK |
| M05 | Stripe checkout | B | improve | must | server-built line items, Order, verified webhook |
| M06 | List product reviews | C | rebuild | should | from Reviewly's docs only |
| M07 | Leave a review | C | rebuild | should | rating 1-5 and comment |
| M09 | Verified-purchase reviews | C | rebuild | should | needs a paid order with the product |
| (platform) | Accounts | new | build | must | no source has sign-in; needed by M04, M05, M07 |

## User journeys

**J1 Buy a product:** sign in → product list → product page → add to cart → cart → Stripe Checkout → confirmation. Features: M01, M04, M05.

**J2 Review a purchase:** sign in → product page (with a paid order) → rate and comment → review appears in the list. Features: M06, M07, M09.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M01 | Given products exist, when anyone GETs /api/products, then each product's id, name, price_minor and currency are returned. |
| AC02 | M04 | Given a signed-in customer, when they add product P with quantity 2, then their cart has P × 2; adding P again with 1 makes it 3. |
| AC03 | M04 | When the quantity is 0, negative, not an integer, or the product does not exist, then the API answers 400/404 and the cart is unchanged; when not signed in, 401. |
| AC04 | M05 | Given a cart, when the customer checks out, then a pending Order is created whose totals come from catalog prices, and any items or prices in the request body are ignored. |
| AC05 | M05 | When Stripe sends checkout.session.completed with a valid signature, the Order becomes paid; with an invalid signature the webhook answers 400 and nothing changes. |
| AC06 | M06 | When anyone GETs /api/products/{id}/reviews, then that product's reviews are listed, newest first, paginated. |
| AC07 | M07 | When a rating outside 1-5 is posted, then the API answers 400 and nothing is stored. |
| AC08 | M09 | Given a customer without a paid order containing the product, when they post a review, then the API answers 403; with one, 201 and the review is listed. |

## Non-functional requirements

Passwords hashed with argon2id; sessions in http-only secure cookies; CSRF protection on form posts; every endpoint checks permission through one function; no personal data or secrets in logs; Stripe in test mode until the user approves going live; pages usable at phone width and keyboard-accessible.

## Out of scope

| Item | Why |
| --- | --- |
| M03 PyShop add-to-cart | dropped: alternative to M04 (similar group); its integer typing is folded into M04 |
| M02 Category filter | deferred: only a code comment; no category data |
| M08 Shop replies to reviews | deferred: one sentence in Reviewly's overview, no API or rules |
| Reviewly integration or data | closed product: rebuilt from public docs, no API calls, no data import |
| Deployment | plan mode; never automatic |

## Open questions

- What does "purchase confirmed" mean for Reviewly (payment captured, or delivered)? We use "Order paid".
- Should the category filter come back, and how are categories defined?
- Hosting, domain and shop currency are not given.
