# Unified online shop: API

REST + JSON under `/api`, unversioned. Errors: `{"error": {"code": "...", "message": "..."}}`. Lists: `?page=1&limit=20` (max 50), response `{"items": [...], "page", "limit", "total"}`. Session cookie auth unless marked public.

| Method | Path | Auth | Request | Response | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | /api/auth/signup | public | email, password (min 12) | 201 user {id, email} + session cookie | 400, 409 email taken |
| POST | /api/auth/login | public | email, password | 200 user + session cookie | 400, 401 |
| POST | /api/auth/logout | session | - | 204 | 401 |
| GET | /api/products | public | page, limit | items [{id, name, price_minor, currency}] | 400 |
| GET | /api/products/{id} | public | - | {id, name, price_minor, currency} | 404 |
| GET | /api/cart | session | - | {items: [{product_id, name, quantity, unit_price_minor}], total_minor, currency} | 401 |
| POST | /api/cart/items | session | product_id integer, quantity integer >= 1 | 201 cart | 400, 401, 404 product |
| POST | /api/checkout | session | none (any body is ignored) | 201 {order_id, checkout_url} | 401, 409 empty cart |
| POST | /api/stripe/webhook | Stripe signature | Stripe event | 200 | 400 bad signature |
| GET | /api/products/{id}/reviews | public | page, limit | items [{id, rating, comment, created_at, author}] | 404 |
| POST | /api/products/{id}/reviews | session | rating integer 1-5, comment text (max 2000) | 201 review | 400, 401, 403 no paid order, 404, 409 already reviewed |
