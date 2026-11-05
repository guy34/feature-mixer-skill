# Unified Identity: product requirements

Version: 2026-11-05 · Sources: A: Passbook, B: Linkup, C: Roster · Status: approved

## Problem

Passbook (passwords), Linkup (OAuth) and Roster (roles) each hold part of
sign-in. People end up with several accounts and three unrelated role
names. One identity system gives each person one account, either sign-in
method, and one role model checked in one place.

## Users

| User | Goal | Role in the app |
| --- | --- | --- |
| Person with a password | sign in with email and password | editor (A user) |
| Person using a provider | sign in with Google-style OAuth | viewer (B member), or their existing role when joined |
| Administrator | manage who can do what | admin |

## Core loop

1. Register with a password, or sign in with a provider.
2. Get a session token.
3. whoami shows who you are and your role.
4. An admin changes roles; the change applies to the next whoami.
5. Log out.

## Features

| Menu id | Feature | From | Strategy | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| M01 | Email and password registration | A | combine | must | duplicates rejected |
| M02 | Password login with session token | A | combine | must | expiry, logout, constant-time compare |
| M03 | Sign in with an OAuth provider | B | combine | must | rebuilt; joins only on verified email |
| M04 | Role-based permissions | C | adapt | must | role mapping from A and B |
| M05 | Admin-only role changes | C | improve | must | actor from session, no self-raise |

## User journeys

**J1 Password:** register_password → login_password → whoami → logout. Features: M01, M02.
**J2 OAuth join:** register_password → login_oauth with verified email → whoami shows the same user. Features: M01, M03.
**J3 Roles:** bootstrap_admin → admin login → set_role on a user → user's whoami shows the new role. Features: M04, M05.

## Acceptance criteria

| Id | Feature | Given / when / then |
| --- | --- | --- |
| AC01 | M01 | Given a new email, when register_password is called, then a user id is returned and the user's role is editor. |
| AC02 | M01 | Given a registered email (any case), when it registers again, then it fails and the original password still works. |
| AC03 | M02 | Given a registered user, when login_password uses the right password, then a token is returned and whoami gives the user's id, normalised email and role. |
| AC04 | M02 | Given a registered user, when login_password uses a wrong password or an unknown email, then AuthError is raised. |
| AC05 | M02 | Given a token, when logout is called, then whoami with that token raises AuthError; an unknown or expired token also raises AuthError. |
| AC06 | M03 | Given no account, when login_oauth is called, then a new viewer account is created, and a repeat sign-in with the same provider and subject returns the same user. |
| AC07 | M03 | Given a password account, when login_oauth arrives with the same email and email_verified True, then the session belongs to that account and keeps its role. |
| AC08 | M03 | Given a password account, when login_oauth arrives with the same email and email_verified False, then a separate viewer account is created and the password account is unchanged. |
| AC09 | M04 | Given the mapping, when map_source_role is called, then A user -> editor, B member -> viewer, C roles unchanged, and an unknown role or app raises KeyError. |
| AC10 | M05 | Given an admin token, when set_role changes a user's role, then that user's whoami shows the new role. |
| AC11 | M05 | Given a non-admin or invalid token, when set_role is called, then PermissionError is raised and nothing changes. |
| AC12 | M05 | Given any user, when they try to raise their own role, then it is refused; an invalid role value is rejected. |
| AC13 | M05 | Given no admin, when bootstrap_admin is called, then an admin is created; a second call fails. |

## Non-functional requirements

Standard library only. Passwords hashed with salted PBKDF2-HMAC-SHA256;
constant-time comparison; tokens from `secrets`; no passwords or tokens in
logs or error messages; thread-safe with a lock. Supported: Python 3.8+.

## Out of scope

| Item | Why |
| --- | --- |
| OAuth redirect, code exchange and ID-token verification | Not in Linkup's provided code (unknown); login_oauth trusts its caller to pass a verified provider response |
| Persistence, HTTP API, UI | Not in any source slice; interface is in-process |
| Password reset, email verification for password accounts | Not in the sources |

## Open questions

- Password policy (minimum length) is not set: Passbook had none; only an empty password is refused.
- Should a password account whose email is later verified by a provider be marked verified? Not decided; no behaviour depends on it yet.
