# Unified expense app: API

REST, JSON, versioned under `/api/v1`. Session cookie auth (http-only,
secure, SameSite=Lax) plus CSRF header on every write; sign-up, sign-in and
email verification are the only unauthenticated endpoints. Non-members get
404 for budget resources and other users' personal expenses; a member
lacking the right gets 403.

Errors: `{"error": {"code": "validation_error", "message": "...", "fields": {"category": "must be one of food, travel, home, other"}}}`.
Codes: `validation_error` 400, `unauthenticated` 401, `forbidden` 403,
`not_found` 404, `conflict` 409, `gone` 410 (expired or used invitation),
`payload_too_large` 413, `ocr_unavailable` 503 (never blocks manual entry).

Pagination: `?cursor=<opaque>&limit=50` (max 200); responses carry
`{"items": [...], "next_cursor": "..." | null}`.

Money in every body: `{"amount_minor": 1240, "currency": "EUR"}`. Dates:
`YYYY-MM-DD`; timestamps ISO 8601 UTC.

| Method | Path | Module | Auth | Request | Response | Features |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/auth/signup | accounts | none | email, password, display_name | 201 user; verification email sent | platform |
| POST | /api/v1/auth/login | accounts | none | email, password | 204 + session cookie; 400 on wrong credentials (same message for unknown email) | platform |
| POST | /api/v1/auth/logout | accounts | session | - | 204 | platform |
| POST | /api/v1/auth/verify-email | accounts | signed token | token | 204 | platform |
| GET | /api/v1/me | accounts | session | - | id, email, display_name, email_verified | platform |
| GET | /api/v1/categories | categories | session | - | ["food","travel","home","other"] | M09 |
| POST | /api/v1/budgets | budgets | session | name, limit_minor, currency, time_zone | 201 budget; caller is owner | M03 |
| GET | /api/v1/budgets | budgets | session | - | budgets the caller is a current member of | M03 |
| GET | /api/v1/budgets/{budget_id} | budgets | current member | - | budget | M03 |
| PATCH | /api/v1/budgets/{budget_id} | budgets | owner | name, limit_minor, time_zone (currency fixed once expenses exist) | budget | M03 |
| GET | /api/v1/budgets/{budget_id}/summary | budget-period | current member | month=YYYY-MM (default current, budget time zone) | limit_minor, spent_minor, currency, month, by_category | M07, M03 |
| GET | /api/v1/budgets/{budget_id}/members | members | current member | - | members with role; former members flagged | M03, M05 |
| POST | /api/v1/budgets/{budget_id}/invitations | members | owner | email | 201; email sent; 409 if already a member | M04 |
| POST | /api/v1/invitations/{token}/accept | members | session, verified matching email | - | 200 membership; 410 used or expired; 403 other email | M04 |
| DELETE | /api/v1/budgets/{budget_id}/members/{user_id} | members | owner | - | 204; 400 when removing self | M05 |
| POST | /api/v1/expenses | expenses | session | amount_minor, currency, spent_on, category, merchant?, note?, budget_id? | 201 expense | M06, M08, M09 |
| GET | /api/v1/expenses | expenses | session | budget_id? (else personal), month?, category? | page of expenses | M06 |
| GET | /api/v1/expenses/{expense_id} | expenses | author or current member | - | expense (author shown as former member when applicable) | M06 |
| PATCH | /api/v1/expenses/{expense_id} | expenses | author while current member | any expense field | expense | M06, M08 |
| DELETE | /api/v1/expenses/{expense_id} | expenses | author or budget owner | - | 204; receipt image deleted | M06 |
| POST | /api/v1/receipts | receipts | session | multipart image (max 10 MB) | 201 draft: merchant, spent_on, date_flagged, amount_minor, currency, status | M01 |
| GET | /api/v1/receipts/{receipt_id} | receipts | uploader | - | draft | M01 |
| GET | /api/v1/receipts/{receipt_id}/image | receipts | uploader, or access to its expense | - | image (private, no caching) | M01 |
| POST | /api/v1/receipts/{receipt_id}/expense | receipts | uploader | amount_minor, currency, spent_on, date_confirmed=true, category, merchant?, note?, budget_id? | 201 expense; 400 without date confirmation or category | M01, M06, M09 |
