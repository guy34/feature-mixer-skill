# TaskBoard (A): reverse-engineering report

App id: A · Access: own-code · Licence: the user's own (no licence needed) · Code reuse: allowed
Slice studied: tasks, comments, notifications · Coverage: complete · Size: M

Basis: **observed** (seen in the code), **documented** (official docs or spec), **inferred**, **unknown**. The structured version is `source.json` in this folder.

## Summary

TaskBoard is the user's own task board. People sign in with email and password, keep tasks on a three-column board, assign them, comment, and get in-app notifications. It also has share links that let anyone edit a board without an account. Everything here was read in the code.

## Sources used

| Ref | Kind | Location | Accessed |
|---|---|---|---|
| A-R01 | local-directory | `sources/taskboard` | 2026-11-04 |

## Evidence

| Id | Source | Basis | Locator | What it shows |
|---|---|---|---|---|
| A-E01 | A-R01 | observed | `sources/taskboard/server/routes.js:8` | POST /api/login checks the password hash and starts a cookie session |
| A-E02 | A-R01 | observed | `sources/taskboard/db/schema.sql:1` | users table: uuid key, email, name, password hash, role owner or member |
| A-E03 | A-R01 | observed | `sources/taskboard/db/schema.sql:10` | tasks table: title, status todo/doing/done, assignee, creator, due date |
| A-E04 | A-R01 | observed | `sources/taskboard/server/routes.js:24` | PATCH /api/tasks/:id moves a task or assigns it and notifies the new assignee |
| A-E05 | A-R01 | observed | `sources/taskboard/db/schema.sql:20` | comments table: one flat list per task, no replies |
| A-E06 | A-R01 | observed | `sources/taskboard/server/routes.js:33` | In-app notifications: list and mark as read |
| A-E07 | A-R01 | observed | `sources/taskboard/server/routes.js:38` | Share links let anyone with the token edit a board without an account |
| A-E08 | A-R01 | observed | `sources/taskboard/package.json:4` | Node 18+, Express 4, React 18, express-session, pg |
| A-E09 | A-R01 | observed | `sources/taskboard/client/routes.js:2` | Client routes: /login, /board, /tasks/:id, /notifications, /settings |
| A-E10 | A-R01 | observed | `sources/taskboard/server/routes.js:2` | Sessions expire after 60 idle minutes (rolling cookie) |
| A-E11 | A-R01 | observed | `sources/taskboard/server/routes.js:40` | Routes without a session answer 401 with a JSON error |
| A-E12 | A-R01 | observed | `sources/taskboard/client/routes.js:11` | Button variants: primary, ghost |

## Features

### A-F01 Sign in with email and password

- **Source application:** TaskBoard (A)
- **Evidence:** A-E01, A-E02, A-E10
- **Description:** Users sign in with email and password and get a cookie session.
- **Observed behaviour:** Wrong email or password returns 401; success returns the user's id and name.
- **Business logic:** Sessions are rolling and expire after 60 idle minutes.
- **Data requirements:** User
- **Dependencies:** none
- **Integration requirements:** Needs the user store and a session store.
- **Basis and confidence:** observed, high

### A-F02 Task board

- **Source application:** TaskBoard (A)
- **Evidence:** A-E03, A-E04
- **Description:** Create tasks and move them between todo, doing and done.
- **Observed behaviour:** Tasks are listed and created over the API; PATCH changes status.
- **Business logic:** Status is one of todo, doing, done.
- **Data requirements:** Task
- **Dependencies:** A-F01
- **Integration requirements:** Needs signed-in users.
- **Basis and confidence:** observed, high

### A-F03 Task assignment

- **Source application:** TaskBoard (A)
- **Evidence:** A-E04
- **Description:** Assign a task to a person, who is notified.
- **Observed behaviour:** Setting assignee_id creates an in-app notification for the assignee.
- **Business logic:** Unassigning sets the assignee to empty; deleting a user unassigns their tasks.
- **Data requirements:** Task, Notification
- **Dependencies:** A-F02, A-F05
- **Basis and confidence:** observed, high

### A-F04 Flat comments on tasks

- **Source application:** TaskBoard (A)
- **Evidence:** A-E05
- **Description:** One list of comments per task, no replies.
- **Data requirements:** Comment
- **Dependencies:** A-F02
- **Basis and confidence:** observed, high

### A-F05 In-app notifications

- **Source application:** TaskBoard (A)
- **Evidence:** A-E06
- **Description:** A notification bell with read and unread items.
- **Data requirements:** Notification
- **Dependencies:** A-F01
- **Basis and confidence:** observed, high

### A-F06 Share links

- **Source application:** TaskBoard (A)
- **Evidence:** A-E07
- **Description:** Anyone holding a share token can edit a board without an account.
- **Business logic:** share_links.can_edit defaults to true.
- **Dependencies:** A-F02
- **Basis and confidence:** observed, high

### A-F07 Owner and member roles

- **Source application:** TaskBoard (A)
- **Evidence:** A-E02
- **Description:** Every user is an owner or a member.
- **Business logic:** The schema allows only owner and member; how the roles differ is not visible in the routes read.
- **Data requirements:** User
- **Dependencies:** A-F01
- **Basis and confidence:** observed, medium

## Screens and workflows

| Id | Screen | Route | Evidence |
|---|---|---|---|
| A-S01 | Sign in | `/login` | A-E09 |
| A-S02 | Board | `/board` | A-E09 |
| A-S03 | Task detail | `/tasks/:id` | A-E09 |
| A-S04 | Notifications | `/notifications` | A-E09 |
| A-S05 | Settings | `/settings` | A-E09 |

**A-W01 Assign a task and the assignee sees it:** A-S02 → A-S03 → A-S04. Edge cases: assignee deleted, assigning yourself.

## Navigation

`/login` → A-S01, `/board` → A-S02, `/tasks/:id` → A-S03, `/notifications` → A-S04, `/settings` → A-S05

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
|---|---|---|---|---|---|
| User | id (uuid) | id (uuid), email (text), name (text), password_hash (text), role (text), created_at (timestamptz) | - | observed | A-E02 |
| Task | id (uuid) | id (uuid), title (text), status (text), assignee_id (uuid), created_by (uuid), due_on (date), created_at (timestamptz) | assignee_id → User, created_by → User | observed | A-E03 |
| Comment | id (uuid) | id (uuid), task_id (uuid), author_id (uuid), body (text) | task_id → Task, author_id → User | observed | A-E05 |
| Notification | id (uuid) | id (uuid), user_id (uuid), message (text), read_at (timestamptz) | user_id → User | observed | A-E06 |

## API

| Method | Path | Auth | Features | Basis | Evidence |
|---|---|---|---|---|---|
| POST | `/api/login` | none | A-F01 | observed | A-E01 |
| GET | `/api/users/:id` | session | A-F07 | observed | A-E01 |
| GET | `/api/tasks` | session | A-F02 | observed | A-E04 |
| POST | `/api/tasks` | session | A-F02 | observed | A-E04 |
| PATCH | `/api/tasks/:id` | session | A-F02, A-F03 | observed | A-E04 |
| GET | `/api/tasks/:id/comments` | session | A-F04 | observed | A-E05 |
| GET | `/api/notifications` | session | A-F05 | observed | A-E06 |
| POST | `/api/notifications/:id/read` | session | A-F05 | observed | A-E06 |
| GET | `/share/:token` | none | A-F06 | observed | A-E07 |

## Authentication and authorization

Provider: self. Sign-in methods: password. Session: cookie. Model: rbac. Roles: owner, member. Basis: observed (A-E01, A-E02, A-E10).

## Integrations

None found.

## Architecture and stack

frontend: React single-page app with client-side routes; backend: Express JSON API with cookie sessions (observed).
Stack: frontend React 18; backend Node 18, Express 4; database PostgreSQL (pg).

## Configuration

`SESSION_IDLE_MINUTES` (idle session timeout)

## Error handling

no session: 401 with {error}; wrong password: 401 'bad login'

## Unknowns

None. Coverage is complete for the slice studied.
