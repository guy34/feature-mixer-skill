# API specification (v1)

Style: REST, JSON bodies, every path under `/api/v1`. Auth: session cookie on every endpoint except signup and
login; state-changing requests also need the `X-CSRF-Token` header matching the CSRF cookie (HTML forms send a
hidden field). Errors: `{"error": {"code": "<snake_case>", "message": "<text>"}}` with the HTTP status. Paging on
list endpoints: `?limit=` (default 50, max 200) and `?offset=`; responses `{"items": [...], "total": n}`.
A record that exists but belongs to someone else returns 404 (never 403), so ids leak nothing.

| Method | Path | Body | Success | Errors | Feature |
| --- | --- | --- | --- | --- | --- |
| POST | /api/v1/auth/signup | {email, password (min 10 chars)} | 201 {user} + session cookie | 400 validation, 409 email_taken | accounts |
| POST | /api/v1/auth/login | {email, password} | 200 {user} + session cookie | 401 invalid_credentials | accounts |
| POST | /api/v1/auth/logout | - | 204, session deleted | 401 | accounts |
| GET | /api/v1/auth/me | - | 200 {user} | 401 | accounts |
| GET | /api/v1/books | ?q=&limit=&offset= | 200 {items: [{id,title,author,stars}], total} | 401 | M01 |
| POST | /api/v1/books | {title, author?} | 201 {book} | 400, 401 | M01 |
| GET | /api/v1/books/{id} | - | 200 {book, stars, lists:[{id,name}]} | 401, 404 | M01 |
| PATCH | /api/v1/books/{id} | {title?, author?} | 200 {book} | 400, 401, 404 | M01 |
| DELETE | /api/v1/books/{id} | - | 204 (rating and list entries cascade) | 401, 404 | M01 |
| PUT | /api/v1/books/{id}/rating | {stars: integer 1-5} | 200 {book_id, stars} (upsert) | 400 invalid_stars, 401, 404 | M02 |
| DELETE | /api/v1/books/{id}/rating | - | 204 | 401, 404 | M02 |
| GET | /api/v1/export | - | 200 `application/json`, `Content-Disposition: attachment; filename="library.json"`, [{id,title,author,stars}] | 401 | M04 |
| GET | /api/v1/lists | ?limit=&offset= | 200 {items: [{id,name,book_count}], total} | 401 | M05 |
| POST | /api/v1/lists | {name} | 201 {list} | 400, 401, 409 name_taken | M05 |
| GET | /api/v1/lists/{id} | - | 200 {list, books:[{id,title,author,stars}]} | 401, 404 | M05 |
| PATCH | /api/v1/lists/{id} | {name} | 200 {list} | 400, 401, 404, 409 | M05 |
| DELETE | /api/v1/lists/{id} | - | 204 (items cascade, books kept) | 401, 404 | M05 |
| PUT | /api/v1/lists/{id}/books/{book_id} | - | 200 (idempotent; no duplicate) | 401, 404 list or book not yours | M05 |
| DELETE | /api/v1/lists/{id}/books/{book_id} | - | 204 | 401, 404 | M05 |

`stars` must be a JSON integer 1-5: `true`, `3.0`, `"3"`, `0`, `6` and `10` are rejected with 400 `invalid_stars`.
Not provided (documented in Shelfie's old docs, never implemented): CSV export, 1-10 `score`, unversioned `/api/...` paths.
