# Helpdesk with FAQ suggestions: API

REST over JSON, version prefix `/api/v1`. Auth: session cookie (http-only) on every endpoint except
`POST /session`. Errors: `{"error": {"code": "<machine code>", "message": "<text>"}}`. Lists:
`?page=1&per_page=20` (max 100), response `{"items": [...], "page": n, "per_page": n, "total": n}`.

| Method | Path | Body | Success | Errors | Features |
| --- | --- | --- | --- | --- | --- |
| POST | /api/v1/session | email, password | 204 + cookie | 400, 401 | platform |
| DELETE | /api/v1/session | - | 204 | 401 | platform |
| GET | /api/v1/tickets | ?status= | 200 list | 401, 422 | M01 |
| POST | /api/v1/tickets | subject, description | 201 ticket (status open) | 401, 422 | M04 |
| GET | /api/v1/tickets/{id} | - | 200 ticket + messages + suggestions | 401, 404 | M01, M05 |
| POST | /api/v1/tickets/{id}/status | status (open or pending) | 200 ticket | 401, 404, 409 (closed), 422 | M01 |
| POST | /api/v1/tickets/{id}/messages | body | 201 message | 401, 404, 409 (closed), 422 | M02 |
| POST | /api/v1/tickets/{id}/close | - | 200 ticket | 401, 404, 409 `answer the customer first` | M03 |
| GET | /api/v1/tickets/{id}/suggestions | - | 200 up to 3 {faq_id, question, answer, score} | 401, 404 | M05 |
| GET | /api/v1/faqs | - | 200 list | 401 | M06 |

None of these endpoints comes from a source endpoint: neither source has an HTTP layer.
