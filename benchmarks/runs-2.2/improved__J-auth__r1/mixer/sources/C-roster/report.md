# Roster (C): reverse-engineering report

App id: C · Access: own-code · Licence: proprietary (the user's own code) · Code reuse: allowed
Slice studied: roles and permissions · Coverage: complete · Size: S

Every statement is **observed** in the code unless marked otherwise. Structured copy: `source.json`.

## Summary

Roster is one Python module (`permissions.py`, 7 lines) defining three roles as permission sets (viewer: read;
editor: read, write; admin: read, write, manage_roles), a `can(role, permission)` check that denies unknown roles,
and `set_role` which only an actor holding `manage_roles` may call. It has no user store or sign-in, and `set_role`
does not validate the new role name.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| C-R01 | local-directory | sources/roster | 2026-11-04 | 1 file, scanned first: no findings |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| C-E01 | C-R01 | observed | `sources/roster/permissions.py:1` | the three roles and their permissions |
| C-E02 | C-R01 | observed | `sources/roster/permissions.py:2-3` | can(): membership test, unknown role denied |
| C-E03 | C-R01 | observed | `sources/roster/permissions.py:4-7` | set_role(): PermissionError unless manage_roles; new role not validated |

## Features

### C-F01 Roles and permission checks

- **Source application:** Roster (C)
- **Evidence:** C-E01, C-E02
- **Description:** three roles as permission sets and one permission check.
- **Observed behaviour:** `can(role, permission)`; deny by default.
- **Business logic:** viewer read; editor read+write; admin read+write+manage_roles.
- **Data requirements:** Role (name, permissions).
- **Dependencies:** none.
- **Integration requirements:** becomes the unified role set and the single permission check.
- **Basis and confidence:** observed, high

### C-F02 Change a user's role (admins only)

- **Source application:** Roster (C)
- **Evidence:** C-E03
- **Description:** an admin assigns a role.
- **Observed behaviour:** PermissionError unless the actor role has manage_roles; then writes the role.
- **Business logic:** admin only; new role not validated; actor given as a role string, not an authenticated user.
- **Data requirements:** Role; a target record with a `role` field.
- **Dependencies:** C-F01.
- **Integration requirements:** authenticated caller from a session, user store, role validation.
- **Basis and confidence:** observed, high

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Role | name (string) | permissions (set of string) | - | observed | C-E01 |

## API

No HTTP API: `can(role, permission)`, `set_role(actor_role, target, role)`.

## Authentication and authorization

No sign-in. Role-based access control with three roles; `manage_roles` gates role changes (C-E03).

## Integrations

None.

## Architecture and stack

Python 3, no imports (observed).

## Configuration

None.

## Error handling

`PermissionError("only admins manage roles")`; unknown roles are denied by `can` but stored by `set_role`.

## Unknowns

- No user store; where target records live is not in the source.
- Whether an admin may demote themselves or the last admin is not decided by the source.
