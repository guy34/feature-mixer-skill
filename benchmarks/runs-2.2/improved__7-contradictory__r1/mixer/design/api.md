# API

REST over JSON under `/api`, no version prefix (as Shelfie's code; its spec's `/api/v1` never existed).
Auth: session cookie on every endpoint except sign up and sign in (401 otherwise).
Errors: `{"error": {"code": "...", "message": "..."}}` with 400 (validation), 401, 404 (missing or not yours), 409 (email taken).
No pagination (personal libraries are small).

| Method | Path | Body | Success | Errors | Origin |
| --- | --- | --- | --- | --- | --- |
| POST | /api/signup | {email, password (min 10)} | 201 {id, email} + cookie | 400, 409 | new |
| POST | /api/signin | {email, password} | 200 {id, email} + cookie | 400, 401 | new |
| POST | /api/signout | - | 204 | 401 | new |
| GET | /api/me | - | 200 {id, email} | 401 | new |
| GET | /api/books | - | 200 [{id, title, author, stars}] | 401 | A: GET /api/books |
| POST | /api/books | {title, author?} | 201 book | 400, 401 | new |
| GET | /api/books/export | - | 200 [{title, stars}] | 401 | A: GET /api/books/export (JSON; not CSV) |
| GET | /api/books/{id} | - | 200 book with stars and list ids | 401, 404 | new |
| PATCH | /api/books/{id} | {title?, author?} | 200 book | 400, 401, 404 | new |
| DELETE | /api/books/{id} | - | 204 (rating and list entries removed) | 401, 404 | new |
| PUT | /api/books/{id}/rating | {stars: integer 1-5} | 200 {book_id, stars} | 400, 401, 404 | A: PUT /api/books/{id}/rating (stars 1-5; not score 1-10) |
| DELETE | /api/books/{id}/rating | - | 204 | 401, 404 | new |
| GET | /api/lists | - | 200 [{id, name, book_count}] | 401 | new |
| POST | /api/lists | {name} | 201 list | 400, 401 | new (B had the table only) |
| GET | /api/lists/{id} | - | 200 {id, name, books: [...]} | 401, 404 | new |
| PATCH | /api/lists/{id} | {name} | 200 list | 400, 401, 404 | new |
| DELETE | /api/lists/{id} | - | 204 | 401, 404 | new |
| PUT | /api/lists/{id}/books/{book_id} | - | 204 (idempotent) | 401, 404 | B: add_to_list() (function, not an endpoint) |
| DELETE | /api/lists/{id}/books/{book_id} | - | 204 | 401, 404 | new |
