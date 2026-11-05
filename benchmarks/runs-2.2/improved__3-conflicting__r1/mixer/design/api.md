# Unified Community Forum: API

REST, JSON, base `/api/v1`. Auth: cookie session (`sid`, http-only, secure,
SameSite=Lax); state-changing requests also send `X-CSRF-Token`. Bearer
tokens are not accepted. Errors: `{"error": {"code": "...", "message": "..."}}`.
Pagination: `?cursor=<opaque>&limit=1..50` (default 20) → `{"items": [...], "next_cursor": "..." | null}`.

Post shape: `{"id": uuid, "body": string, "status": "pending"|"published"|"rejected", "author": {"id": uuid, "display_name": string} | null, "created_at": UTC ISO 8601}`.

| Method | Path | Auth | Request | Response | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | /session | none (rate limited) | {email, password} | 200 {user: {id, display_name, role}} + cookie | 400, 401 (one generic message), 429 |
| DELETE | /session | session | - | 204, cookie cleared | 401 |
| GET | /me | session | - | {id, email, display_name, role} | 401 |
| POST | /posts | session | {body: 1..10000 chars} | 201 Post (status pending) | 401, 422 |
| GET | /posts/{id} | public if published; author or moderator otherwise | - | 200 Post | 404 (missing, malformed id, or not readable) |
| GET | /posts | public | cursor, limit | published posts, newest first | 400 |
| GET | /moderation/queue | moderate-posts | cursor, limit | pending posts, oldest first | 401, 403 |
| POST | /moderation/posts/{id}/decision | moderate-posts | {decision: "published"|"rejected"} | 200 Post | 401, 403, 404, 409 (not pending), 422 |

Origins: POST /session ← A `POST /api/login`; POST /posts ← A and B
`POST /api/posts`; GET /posts/{id} ← A `GET /api/posts/:id`, B
`GET /api/posts/<int:post_id>`; moderation ← A `/api/moderation`. GET /posts,
DELETE /session and GET /me are new (neither source has them).
