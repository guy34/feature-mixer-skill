# Team Hub: product requirements

Version: 2026-11-04 · Sources: A TaskBoard, B Approvals, C Pulse · Status: approved

## Problem

A small team plans work in one tool, gets sign-off in another and checks
workload in a third. Nothing connects: a task can be closed while its
purchase is still waiting for approval, notifications arrive in three
different ways, and nobody sees the whole picture. Team Hub puts tasks,
approvals and workload in one place with one set of accounts and one way of
being notified.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Team member | Do assigned work, ask for sign-off | member |
| Approver | Approve or reject requests quickly | member with the approve permission |
| Team lead | See workload, manage people | owner or admin |

## Core loop

1. Create a task and assign it.
2. Ask for approval when it needs sign-off.
3. Discuss it in a thread; the approver decides.
4. Close the task; the dashboard shows what is left.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Sign in with email and password | A | rebuild | must | Cookie sessions, 30 minutes idle |
| M04 | Task board | A | rebuild | must | todo, doing, done |
| M05 | Task assignment | A | rebuild | must | Notifies the assignee |
| M07 | Threaded comments | B | rebuild | should | On tasks and approvals |
| M08 | Owner and member roles | A | combine | must | With M09: one role model |
| M09 | Requester, approver and admin roles | B | combine | must | Approving becomes a permission |
| M10 | In-app notifications | A | combine | should | One engine with M11 and M12 |
| M11 | Email notifications | B | combine | should | Email channel of the engine |
| M12 | Push notifications | C | combine | could | Push channel; rebuilt from public docs |
| M13 | Approval requests | B | rebuild | must | Attached to tasks |
| M14 | Workload dashboard | C | rebuild | should | Rebuilt from public docs |

## User journeys

**J1 Get a task done with sign-off:** create task → assign → request
approval → discuss → approver decides → close task. Features: M01, M04,
M05, M07, M13, M10, M11.

**J2 See the team's workload:** sign in as a lead → open the dashboard.
Features: M01, M14.

**J3 Choose how to be notified:** turn email off, opt a browser in to push.
Features: M10, M11, M12.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M01 | Given an account, when the right password is sent, then a session cookie is set; a wrong one gets 401. |
| AC02 | M01 | Given a session unused for over 30 minutes, when it is used, then it is refused. |
| AC03 | M04 | Given a task, when it moves to an unknown status, then the change is refused. |
| AC04 | M05, M10, M11 | Given a task, when it is assigned to someone else, then they get one in-app notification and one email, even if assigned twice. |
| AC05 | M13 | Given a pending approval, when the requester tries to decide it, then it is refused; an approver's decision notifies the requester. |
| AC06 | M13, M04 | Given a pending approval on a task, when the task is moved to done, then the move is refused. |
| AC07 | M07 | Given a comment, when someone replies, then the reply nests under it and the author is notified. |
| AC08 | M12 | Given an http:// push endpoint, when it is registered, then it is refused; https:// is accepted. |
| AC09 | M14 | Given open, done and overdue tasks, when the dashboard loads, then done tasks are not counted as open. |
| AC10 | M08, M09 | Given a member, when they try to add a user or decide an approval without the permission, then it is refused. |

## Non-functional requirements

Passwords hashed with PBKDF2; sessions in http-only cookies; no request
logging of paths or bodies; every error in one JSON format; runs on Python
3.8+ with nothing to install.

## Out of scope

| Item | Why |
| --- | --- |
| M02 B's token sign-in | Duplicate of M01 |
| M06 Flat comments | Replaced by threaded comments (M07) |
| M16 Share links | Editing without an account conflicts with the role model |
| M17 Template gallery | Pulse's community content; cannot be rebuilt |
| M03 Google sign-in, M15 weekly digest | Deferred (later) |
| A web interface | This example ships the API; the PRD's journeys are proven over HTTP |

## Open questions

- Which email provider and web push service to connect when the outbox is
  turned on.
