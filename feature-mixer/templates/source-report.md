# <App name> (<ID>): reverse-engineering report

App id: <ID> · Access: own-code | open-source | closed · Licence: <licence> · Code reuse: allowed | not-allowed | unknown
Slice studied: <the part of the app this report covers> · Coverage: complete | partial · Size: S | M | L | XL

Every statement below is marked with its basis where it is not obvious:
**observed** (seen in the running app, a screenshot or the code),
**documented** (official docs or a published spec), **inferred** (deduced,
not seen), or **unknown**. The structured version of this report is
`source.json` in the same folder.

## Summary

<Three to five sentences: what the app is for, who uses it, its core loop,
and the most important things found.>

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| <ID>-R01 | local-directory / github / website / documentation / api-spec / screenshots / own-account | <path or URL> | <date> | <commit, account used, limits> |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| <ID>-E01 | <ID>-R01 | observed | `src/routes/tasks.js:12` | <one sentence> |

## Features

### <ID>-F01 <Feature name>

- **Source application:** <App name> (<ID>)
- **Evidence:** <ID>-E01, <ID>-E02
- **Description:** <what it lets the user do>
- **Observed behaviour:** <what actually happens, step by step>
- **Business logic:** <rules, limits, states, calculations>
- **Data requirements:** <entities and fields it reads and writes>
- **Dependencies:** <other features it needs>
- **Integration requirements:** <what it needs from the unified app: auth, notifications, storage...>
- **Subfeatures:** <optional>
- **Basis and confidence:** observed, high

## Screens and workflows

| Id | Screen | Route | Components | States seen | Evidence |
| --- | --- | --- | --- | --- | --- |
| <ID>-S01 | <name> | `/path` | <components> | empty, filled, error | <ID>-E03 |

**<ID>-W01 <Goal>:** <ID>-S01 → <ID>-S02 → <ID>-S03. Edge cases: <list>.

## Navigation

<Menus, route structure, how screens connect.>

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| <Entity> | id (uuid) | title (text), ... | owner_id → User | observed | <ID>-E04 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/tasks` | session | - | list of tasks | 401 | <ID>-E05 |

## Authentication and authorization

Provider, sign-in methods, session mechanism, roles and the permission
model, with evidence.

## Integrations

| Service | Purpose | Features | Evidence |
| --- | --- | --- | --- |

## Architecture and stack

Frontend, backend, database, infrastructure, runtimes and key packages,
with the basis for each (for closed apps, only what is documented).

## Configuration

Environment variables, feature flags and settings (names and purpose only,
never secret values).

## Error handling

How the app behaves on invalid input, missing records, permission errors,
and external failures.

## Unknowns

- <What could not be determined, why, and what would settle it.>
