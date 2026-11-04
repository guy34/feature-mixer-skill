# Unified Notes: API

REST, JSON, base path `/api/v1`. No auth (single local user, bound to 127.0.0.1).
Errors: `{"error": {"code": "<snake_case>", "message": "<text>"}}` with 400 (validation), 404 (unknown id), 409 (conflict).
No pagination in V1. Note shape: `{id, title, body, pinned, tags: [name], created_at, updated_at}`.

| Method | Path | Module | Request | Response | Errors | Features |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/notes` | notes | `?tag=<name>` optional | 200 list, pinned first then created_at desc | - | M01, M02 (tag filter M03) |
| POST | `/api/v1/notes` | notes | `{title, body}` | 201 note | 400 | M01, M02 |
| GET | `/api/v1/notes/{id}` | notes | - | 200 note | 404 | M01, M02 |
| PUT | `/api/v1/notes/{id}` | notes | `{title?, body?}` only | 200 note, updated_at refreshed | 400 unknown field, 404 | M01, M02 |
| DELETE | `/api/v1/notes/{id}` | notes | - | 204 | 404 | M01, M02 |
| GET | `/api/v1/tags` | tags | - | 200 list of `{name, count}` | - | M03 |
| POST | `/api/v1/notes/{id}/tags` | tags | `{name}` | 200 note (idempotent) | 400, 404 | M03 |
| DELETE | `/api/v1/notes/{id}/tags/{tag}` | tags | - | 204 | 404 | M03 |
| GET | `/api/v1/search` | search | `?q=` (required) | 200 list, same order | 400 empty q | M05 |
| GET | `/api/v1/notes/{id}/preview` | preview | - | 200 `{html}` sanitised | 404 | M07 |
| POST | `/api/v1/notes/{id}/pin` | pinning | - | 200 note | 404 | M08 |
| DELETE | `/api/v1/notes/{id}/pin` | pinning | - | 200 note | 404 | M08 |
| GET | `/api/v1/export` | export | - | 200 list of `{file, text}` | - | M09 |
