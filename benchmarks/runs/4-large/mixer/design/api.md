# Unified CRM: API

REST + JSON under `/api/v1`. Session cookie auth (http-only, secure) with
CSRF token on unsafe methods; every endpoint except login requires a
session. Errors: `{"error": {"code": "...", "message": "..."}}` with 400
(validation, `unknown_stage`), 401, 403, 404, 409 (duplicate email). Lists
use cursor pagination: `?cursor=<opaque>&limit=<1..100>` returning
`{"items": [...], "next_cursor": "..."|null}`.

| Method | Path | Module | Auth | Request | Response | Features |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/auth/login | accounts | none, rate limited | email, password | user | - |
| POST | /api/v1/auth/logout | accounts | session | - | 204 | - |
| GET | /api/v1/me | accounts | session | - | user, permissions | - |
| GET | /api/v1/contacts | contacts | session | q (substring of name or email), cursor, limit | contacts page | M01 |
| POST | /api/v1/contacts | contacts | session | name, email?, company? | contact (201); 409 duplicate email | M01 |
| GET | /api/v1/contacts/{id} | contacts | session | - | contact with deals | M01 |
| PATCH | /api/v1/contacts/{id} | contacts | session | name?, email?, company? | contact | M01 |
| POST | /api/v1/contacts/{id}/merge | contact-merge | session + contacts.merge | drop_id | kept contact, deals_moved | M02 |
| GET | /api/v1/deals | pipeline | session | stage_id?, owner_id?, contact_id?, cursor, limit | deals page | M03, M04 |
| POST | /api/v1/deals | pipeline | session | title, contact_id?, value_cents?, currency?, stage_id?, owner_id? | deal (201) | M03, M04 |
| GET | /api/v1/deals/{id} | pipeline | session | - | deal | M03, M04 |
| PATCH | /api/v1/deals/{id} | pipeline | session | title?, value_cents?, contact_id?, owner_id? (stage only via move) | deal | M03, M04 |
| POST | /api/v1/deals/{id}/move | pipeline | session | stage_id | deal with moved_at; 400 unknown_stage | M03, M04 |
| GET | /api/v1/stages | pipeline | session | - | stages in position order | M04 |
| POST | /api/v1/stages | pipeline | session + stages.configure | name, position, outcome | stage (201) | M04 |
| PATCH | /api/v1/stages/{id} | pipeline | session + stages.configure | name?, position?, outcome?, is_active? | stage | M04 |
| GET | /api/v1/exports/contacts.csv | reporting | session + exports.download | - | text/csv with header | M05 |
| GET | /api/v1/exports/deals.csv | reporting | session + exports.download | - | text/csv with header | M05 |
| GET | /api/v1/reminders/log | reminders | session + admin | cursor, limit | reminder log page | M06 |
