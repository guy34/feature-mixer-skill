# Unified Identity: product requirements

Version: 2026-11-05 · Sources: A: Passbook, B: Linkup, C: Roster · Status: approved (benchmark operator, pre-approved)

## Problem

Three apps each own one piece of sign-in: Passbook has email and password accounts, Linkup has provider sign-in, and
Roster has roles but no users. A person using several of them ends up with several accounts and no consistent
permissions. One identity module gives one account per person, both sign-in methods, and one role model.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Person with a password | sign up and sign in | editor (A's user) |
| Person using a provider | sign in with Google-style OAuth | viewer (B's member), or their existing role when linked |
| Administrator | manage who can do what | admin |

## Core loop

1. Sign up with a password, or sign in with a provider.
2. Get a session token and see who you are (`whoami`).
3. An admin adjusts roles; the person's permissions follow.
4. Log out.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Register with email and password | A | combine | must | no overwrite on duplicates |
| M02 | Log in with email and password | A | combine | must | sessions with expiry, logout, whoami |
| M03 | Sign in with an OAuth provider | B | combine | must | links only on a verified email |
| M04 | Roles and permission checks | C | adapt | must | plus source-role mapping |
| M05 | Change a user's role (admins only) | C | improve | must | caller from session, no self-raise |

## User journeys

**J1 Sign up, link, manage roles:** register with password → log in → sign in with a provider using the same verified
email (same account) → bootstrap admin raises the user's role → user sees the new role → log out. Features: M01, M02,
M03, M04, M05.

**J2 Unverified provider email:** sign in with a provider whose email is unverified → a separate viewer account. Features: M03, M04.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M01 | Given a new email, when it registers and logs in, then whoami returns its user id, normalised email and role editor. |
| AC02 | M01 | Given a registered email, when it registers again (any case), then AuthError is raised and the original password still works. |
| AC03 | M02 | Given an account, when the password is wrong or the email unknown, then login_password raises AuthError. |
| AC04 | M02 | Given a session, when it is logged out or has expired, then whoami raises AuthError. |
| AC05 | M03 | Given a password account, when a provider signs in with the same email and email_verified True, then the token belongs to that account (same user id, role kept). |
| AC06 | M03 | Given a password account, when a provider signs in with the same email but email_verified False, then a separate account is created. |
| AC07 | M03 | Given a new provider identity, when it signs in twice, then both tokens belong to one account with role viewer. |
| AC08 | M04 | map_source_role maps A user->editor, B member->viewer, C roles unchanged, and raises KeyError for an unknown role. |
| AC09 | M05 | Given a viewer or editor session, when it calls set_role, then PermissionError is raised and nothing changes. |
| AC10 | M05 | Given an admin session, when it sets another user's role, then that user's whoami shows the new role; an unknown role is refused. |
| AC11 | M05 | Nobody can raise their own role. |
| AC12 | M05 | bootstrap_admin creates an admin once; a second call is refused. |

## Non-functional requirements

Standard library only. Passwords hashed with PBKDF2-HMAC-SHA256 and a random salt; constant-time comparison; tokens
stored hashed; no personal data or secrets logged; thread-safe mutations.

## Out of scope

| Item | Why |
| --- | --- |
| Real OAuth redirect, code exchange and ID-token verification | not in Linkup's source; no network or provider account here; behind the caller of login_oauth |
| Persistence | sources are in-memory; not requested |
| Account deletion, password reset, email verification for password sign-up | in no source slice |

## Open questions

- Password sign-up does not verify email ownership (no source does). Under the user's linking rule, someone who
  registers another person's email first would receive that person's later verified provider sign-in
  (pre-registration takeover). Adding email verification for password accounts would close it; it needs the user.
- Whether an admin may demote themselves or the last admin; currently allowed (lowering is not raising).
- PBKDF2 at 100,000 iterations (A's value) is below current OWASP guidance (600,000); configurable, per-credential.
