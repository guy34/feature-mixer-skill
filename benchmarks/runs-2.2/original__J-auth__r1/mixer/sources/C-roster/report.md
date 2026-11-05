# Roster (C): reverse-engineering report

App id: C · Access: own-code · Licence: proprietary (user's own code) · Code reuse: allowed
Slice studied: roles and permissions · Coverage: complete · Size: S

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the code), **documented**, **inferred**, or **unknown**.
The structured version of this report is `source.json` in the same folder.

## Summary

Roster provides role-based permissions in one 7-line module
(`permissions.py`): three roles with fixed permission sets, a `can(role,
permission)` check that denies by default, and `set_role` that only an admin
may call. Findings: `set_role` trusts a caller-supplied actor role, does not
validate the new role, and has no rule about changing one's own role.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| C-R01 | local-directory | `sources/roster` | 2026-11-05 | 1 file; scanned first (no findings) |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| C-E01 | C-R01 | observed | `sources/roster/permissions.py:1` | viewer {read}, editor {read, write}, admin {read, write, manage_roles} |
| C-E02 | C-R01 | observed | `sources/roster/permissions.py:2-3` | can(): permission in role's set; unknown role -> none |
| C-E03 | C-R01 | observed | `sources/roster/permissions.py:4-7` | set_role(): PermissionError unless actor has manage_roles; new role not validated |

## Features

### C-F01 Role-based permissions

- **Source application:** Roster (C)
- **Evidence:** C-E01, C-E02
- **Description:** three roles with fixed permissions and one check function.
- **Observed behaviour:** can(role, permission) looks up ROLES; unknown roles have no permissions.
- **Business logic:** viewer read; editor read+write; admin read+write+manage_roles; deny by default.
- **Data requirements:** a role on each user record.
- **Dependencies:** none.
- **Integration requirements:** a user store with one role per user.
- **Basis and confidence:** observed, high

### C-F02 Admin-only role changes

- **Source application:** Roster (C)
- **Evidence:** C-E03
- **Description:** an admin changes a user's role.
- **Observed behaviour:** PermissionError("only admins manage roles") for non-admins, otherwise the role is written.
- **Business logic:** requires manage_roles; actor role is trusted input; no validation of the new role; no self-change rule.
- **Data requirements:** target's role.
- **Dependencies:** C-F01.
- **Integration requirements:** the caller's identity must come from a session.
- **Basis and confidence:** observed, high

## Screens and workflows

None in the slice.

## Navigation

None.

## Data model

No stored entity: `set_role` works on any dict with a `role` key. (observed)

## API

Python functions `can(role, permission)`, `set_role(actor_role, target, role)`. (observed)

## Authentication and authorization

RBAC, role -> permission set; roles viewer, editor, admin. No authentication
in this module. (observed, C-E01, C-E02)

## Integrations

None.

## Architecture and stack

Python, no imports, stateless functions. (observed)

## Configuration

None.

## Error handling

PermissionError for non-admin role changes; unknown roles silently have no
permissions. (observed)

## Unknowns

- How Roster stores users and their ids is unknown (no user store in the provided code).
