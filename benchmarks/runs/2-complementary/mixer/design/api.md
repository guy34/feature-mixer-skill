# FileShare API

REST over JSON, unversioned single namespace `/api` (one client, one deployable). Errors are always
`{"error": {"code": "<snake_case>", "message": "<text>"}}`. Lists are returned whole (no pagination; a user's
file count is small at this scale). Auth: session cookie `fs_session` (http-only, SameSite=Strict) for owner
endpoints; share endpoints need only the token and, if set, the `X-Link-Password` header.

| Method | Path | Auth | Request | Response | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | /api/register | none | {username, password} | 201 {id, username} + cookie | 400 invalid, 409 username_taken |
| POST | /api/login | none | {username, password} | 200 {id, username} + cookie | 400, 401 bad_credentials |
| POST | /api/logout | session | - | 204 | 401 |
| GET | /api/files | session | - | 200 {files: [{id, name, size, content_type, created_at}]} | 401 |
| POST | /api/files?name=<filename> | session | raw body bytes | 201 file | 400 invalid_name, 411 length_required, 413 file_too_large, 401 |
| DELETE | /api/files/{id} | session (owner) | - | 204 | 401, 404 not_found |
| GET | /api/files/{id}/preview | session (owner) | - | 200 preview | 401, 404 |
| GET | /api/files/{id}/content | session (owner) | - | 200 bytes, Content-Type | 401, 404 |
| POST | /api/files/{id}/links | session (owner) | {expires_in_hours?, password?} | 201 {token, url, expires_at, has_password} | 400 invalid_expiry, 401, 404 |
| DELETE | /api/links/{token} | session (owner of the file) | - | 204 | 401, 404 |
| GET | /api/share/{token} | token (+ X-Link-Password) | - | 200 {name, size, content_type, preview} | 403 password_required / wrong_password, 404 not_found |
| GET | /api/share/{token}/content | token (+ X-Link-Password) | - | 200 bytes | 403, 404 |

Preview shape: `{"kind": "text", "first_lines": [...]}`, `{"kind": "image", "url": "..."}`,
`{"kind": "none", "reason": "no preview for this type"}`.
