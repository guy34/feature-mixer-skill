# Unified booking app: API

REST, base `/api/v1`, JSON. Errors: `{"error": {"code": "...", "message": "..."}}`. Lists: `?cursor=` with `next_cursor` in the response. Auth: session cookie + CSRF header, except where noted.

| Method | Path | Request | Response | Errors |
| --- | --- | --- | --- | --- |
| POST | /auth/signup | email, password | user {id, email, role} | 422 validation, 409 email_taken |
| POST | /auth/login | email, password | user | 401 invalid_credentials |
| POST | /auth/logout | - | 204 | 401 |
| GET | /slots | from, to, cursor (public) | slots [{id, starts_at, ends_at, price_amount, currency, open}] | 422 |
| POST | /slots (staff) | starts_at, ends_at, price_amount, currency, status | slot | 403, 422 |
| PATCH | /slots/{id} (staff) | any slot field; status withdrawn | slot | 403, 404, 409 has_bookings |
| POST | /bookings | slot_id, payment_method (Stripe test token), Idempotency-Key header | booking {id, status confirmed, payment} | 409 slot_taken, 402 payment_failed, 404 |
| GET | /bookings | cursor | own bookings | 401 |
| POST | /bookings/{id}/cancel | - | booking {status cancelled, refund} | 403 too_late_to_cancel, 403 forbidden, 404 |
| POST | /payments/stripe-webhook | Stripe event (signature-verified) | 200 | 400 bad_signature |
| POST | /series | first_slot_id, weeks (2-12), payment_method, Idempotency-Key | series {id, bookings[]} | 409 series_weeks_taken (weeks[]), 402, 422 |
| POST | /series/{id}/cancel | - | series {cancelled occurrences, refused occurrences} | 403, 404 |
| POST | /slots/{id}/waitlist | - | entry {id, position} | 409 already_waiting, 409 slot_open |
| DELETE | /waitlist/{id} | - | 204 | 403, 404 |
| POST | /waitlist/{id}/accept | payment_method, Idempotency-Key | booking | 410 offer_expired, 402, 403 |
