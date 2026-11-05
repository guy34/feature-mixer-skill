# Helpdesk with FAQ suggestions: API

REST, JSON, base path `/api/v1`. Auth: session cookie (`hd_session`, http-only)
on every endpoint except `POST /session`; state-changing requests also need
the `X-CSRF-Token` header. Errors: `{"error": {"code": "...", "message": "..."}}`
with codes `validation_error` (400), `unauthenticated` (401), `forbidden` (403),
`not_found` (404), `ticket_pending` (409). Lists: `?page=1&per_page=20` (max 100),
response `{"items": [...], "page", "per_page", "total"}`.

| Method | Path | Who | Request | Response | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | /session | anyone | email, password | user {id, name, role} + cookie | 400, 401 |
| DELETE | /session | signed in | - | 204 | 401 |
| GET | /tickets | customer (own), agent, admin | ?status | list of {id, subject, status, updated_at} | 401 |
| POST | /tickets | customer | subject, body | ticket (status pending) | 400, 401, 403 |
| GET | /tickets/{id} | owner customer, agent, admin | - | ticket with messages | 401, 404 |
| POST | /tickets/{id}/messages | owner customer (sets pending), agent/admin (sets open) | body | message, ticket status | 400, 401, 403, 404 |
| POST | /tickets/{id}/close | agent, admin | - | ticket (closed) | 401, 403, 404, 409 ticket_pending |
| GET | /tickets/{id}/suggestions | agent, admin | - | up to 3 {faq_id, question, answer, score} | 401, 403, 404 |
| GET | /faqs | agent, admin | - | list of FAQ entries | 401, 403 |
| POST | /faqs | admin | question, answer | entry | 400, 401, 403 |
| PATCH | /faqs/{id} | admin | question?, answer? | entry | 400, 401, 403, 404 |
| DELETE | /faqs/{id} | admin | - | 204 | 401, 403, 404 |

A customer asking for another customer's ticket gets 404 (not 403) so ticket
ids do not leak.
