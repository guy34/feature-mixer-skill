# Unified Community Forum: API

REST JSON under `/api`. Auth: one http-only session cookie (CSRF token header on unsafe methods). Errors: `{"error": {"code": "...", "message": "..."}}`. Pagination: `?cursor=<opaque>&limit=<1-50>` → `{"items": [...], "next_cursor": "..."|null}`.

Post object: `{"id": uuid, "body": text, "status": "pending"|"published"|"rejected", "author": {"id": uuid, "display_name": text}, "created_at": iso8601}`.

| Method | Path | Auth | Request | Success | Errors |
| --- | --- | --- | --- | --- | --- |
| POST | /api/session | none | {email, password} | 200 {user: {id, display_name, role}} + cookie | 401 invalid_credentials, 403 sign_in_disabled, 409 password_reset_required, 422 |
| GET | /api/session | session | - | 200 {user} | 401 |
| DELETE | /api/session | session | - | 204 | 401 |
| GET | /api/posts | public | cursor, limit | 200 page of published posts, newest first | 422 bad cursor |
| POST | /api/posts | post.create | {body} (1-10000 chars) | 201 post (status pending) | 401, 422 too_long / empty |
| GET | /api/posts/:id | public if published; author or moderator otherwise | - | 200 post | 404 (missing or not visible), 422 bad uuid |
| GET | /api/moderation/queue | moderation.list | cursor, limit | 200 pending posts, oldest first | 401, 403 |
| POST | /api/moderation/posts/:id/decision | moderation.decide | {decision: "publish"|"reject"} | 200 post | 401, 403, 404, 409 already_decided, 422 bad decision |
