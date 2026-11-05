# Shared expenses with receipt scanning: API

REST JSON under `/api/v1`. Auth: session cookie on every endpoint except sign-up and sign-in (401 without it).
Errors: `{"error": {"code": "...", "message": "..."}}` with 400 validation, 401 unauthenticated, 404 not found or
not a member (never 403, so budgets are not revealed), 409 conflict, 422 extraction failed, 429 throttled.
Pagination: cursor (`?cursor=&limit=`, default 50) on expense lists. Money: `{"amount_minor": 1240, "currency": "GBP"}`;
input also accepts `"amount": "12.40"`, parsed with the currency's exponent.

| Method | Path | Module | Auth | Features | Notes |
| --- | --- | --- | --- | --- | --- |
| POST | /api/v1/auth/signup | accounts | none | platform | creates the user and a personal budget |
| POST | /api/v1/auth/login | accounts | none | platform | rate-limited |
| POST | /api/v1/auth/logout | accounts | session | platform | |
| GET | /api/v1/me | accounts | session | platform | |
| GET | /api/v1/categories | categories | session | M09 | food, travel, home, other |
| GET | /api/v1/fx/quote | currency | session | M02 | `from`, `to`, `date`; preview only |
| GET | /api/v1/budgets | budgets | session | M03 | budgets the user is an active member of (from A: GET /v2/budgets) |
| POST | /api/v1/budgets | budgets | session | M03 | name, limit, currency, timezone; caller becomes owner |
| GET | /api/v1/budgets/{budget_id} | budgets | member | M03 | includes members (display name, email, role) |
| PATCH | /api/v1/budgets/{budget_id} | budgets | owner | M03 | name, limit, timezone |
| POST | /api/v1/budgets/{budget_id}/invitations | budgets | owner | M04 | email; sends a single-use link (72 h) |
| POST | /api/v1/invitations/{token}/accept | budgets | session, email matches | M04 | |
| DELETE | /api/v1/budgets/{budget_id}/members/{user_id} | budgets | owner | M07 | sets removed_at; owner cannot remove self |
| GET | /api/v1/budgets/{budget_id}/expenses | expenses | member | M05 | newest first (from A: GET /v2/expenses) |
| POST | /api/v1/budgets/{budget_id}/expenses | expenses | member | M05, M06, M02, M09 | merchant, amount, currency, date, category, note (from A: POST /v2/expenses) |
| PATCH | /api/v1/expenses/{expense_id} | expenses | adder or owner | M05 | |
| DELETE | /api/v1/expenses/{expense_id} | expenses | adder or owner | M05 | hard delete |
| GET | /api/v1/budgets/{budget_id}/summary | expenses | member | M08 | `?month=YYYY-MM`; spent vs limit in budget currency |
| POST | /api/v1/budgets/{budget_id}/receipt-scans | receipts | member | M01 | multipart image; returns extracted fields or 422 with manual-entry fallback |
| GET | /api/v1/receipt-scans/{scan_id} | receipts | uploader | M01 | |
| POST | /api/v1/receipt-scans/{scan_id}/confirm | receipts | uploader | M01, M09, M02 | reviewed fields + required category; creates one expense; idempotent |
