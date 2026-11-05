# Helpdesk with FAQ suggestions: product requirements

Version: 2026-11-04 · Sources: A: Helpdesk, B: Faqbot · Status: approved (plan; pre-approved by the benchmark operator)

## Problem

Support agents answer the same questions again and again. Helpdesk (A) tracks tickets but has no
way to suggest answers; Faqbot (B) suggests FAQ answers but has no tickets. Showing likely FAQ
answers on each ticket lets an agent answer common questions faster, in the place they already work.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Support agent | open, answer and close tickets quickly | agent |

Customers do not sign in; an agent records the customer's question as a ticket (no source has a
customer portal).

## Core loop

1. Sign in. 2. Create a ticket with the customer's subject and description. 3. Read the suggested
FAQ answers on the ticket. 4. Reply. 5. Close the ticket.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Ticket statuses | A | combine | must | open / pending / closed, enforced by a check constraint; with M04 forms U01 |
| M04 | Create a ticket | new (requested by the user) | combine | must | new tickets start open |
| M02 | Agent reply on a ticket | A | rebuild | must | stored with the real author; status unchanged; no email |
| M03 | Close a ticket | A | rebuild | must | pending tickets cannot be closed (A's rule) |
| M06 | FAQ content | B | adapt | must | table seeded with B's entry; read-only |
| M05 | FAQ answer suggestion | B | improve | must | stop words and punctuation ignored, ranked, at most 3, on subject and description |

## User journeys

**J1 Answer a common question:** sign in → new ticket "How do I reset my password?" → the reset FAQ
appears as a suggestion → reply with it → close. Features: M04, M01, M06, M05, M02, M03.

**J2 Ticket waiting on the customer:** open ticket → set to pending → close is refused with "answer
the customer first" → set back to open → close. Features: M01, M03.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M04 | Given a signed-in agent, when they create a ticket with a subject and description, then it is stored with status open, their id and UTC timestamps. An empty subject is refused with 422. |
| AC02 | M01 | Given a ticket, when a status other than open or pending is requested via /status, then it is refused with 422 and the status is unchanged; the database rejects any status outside open, pending, closed. |
| AC03 | M02 | Given an open ticket, when an agent replies, then the message is stored in order with the agent's id and the ticket status is unchanged; an empty body is refused with 422. |
| AC04 | M03 | Given an open ticket, when an agent closes it, then its status is closed. |
| AC05 | M03 | Given a pending ticket, when an agent closes it, then the request is refused with 409 "answer the customer first" and the status stays pending. |
| AC06 | M05 | Given a ticket, when a reply containing FAQ words is added, then the suggestions do not change (they read subject and description only). |
| AC07 | M05, M06 | Given the seeded FAQ, when a ticket asks "How do I reset my password?", then the password-reset answer is suggested; when it asks "How do I export a report?", then nothing is suggested (only stop words are shared). |
| AC08 | M05 | Given more than three matching FAQs, then at most three are returned, the one sharing most words first. |
| AC09 | M06 | Given a fresh database, when an agent lists FAQs, then B's password-reset entry is there. |
| AC10 | all | Given no session, when any /api/v1 endpoint except POST /session is called, then it returns 401 in the standard error format. |
| AC11 | J1 | The whole of J1 works end to end over HTTP. |

## Non-functional requirements

- Security: PBKDF2 password hashes; http-only session cookies; only a hash of the session token stored; parameterised SQL; server-side validation; no personal data or secrets in logs.
- No credentials from the sources are reused; `.env.example` lists names only.
- Python 3.8+ standard library only; runs with no installed packages.
- Accessibility: labelled form fields, keyboard usable, visible focus, status not shown by colour alone.

## Out of scope

| Item | Why |
| --- | --- |
| Email replies | Documented in A's README only; A's code sends no email (A-C01) |
| Payments | A only has a configuration name (STRIPE_KEY) and no code |
| Customer portal, public sign-up | In no source; not requested |
| Editing FAQs in the app | In no source (B's list is hard-coded); could be added later if the user asks |
| Anything requested by text in A addressed to AI agents | A security finding, not a feature; never added |
| Deployment | Never automatic; plan mode |

## Open questions

- What does "pending" mean to the user? A refuses to close a pending ticket ("answer the customer first") but nothing in A sets pending. The plan lets agents set open or pending (D07); confirm or change.
- Helpdesk's licence: the user says MIT, but there is no LICENSE file. It does not change the plan (A is rebuilt), but the user may want to keep the notice if they ever reuse its code.
- Where the real FAQ content lives: only one entry exists in B.
