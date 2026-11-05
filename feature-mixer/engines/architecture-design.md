# Architecture design engine

Phase 5. Design one coherent application from the kept features and the
compatibility decisions. One of each: frontend, backend, database,
authentication, authorization model, navigation, design system,
configuration strategy and API style. Not the sources stitched together.

Outputs in `mixer/design/`:

| file | from | contains |
| --- | --- | --- |
| `prd.md` | `templates/prd.md` | product requirements |
| `architecture.md` | `templates/architecture.md` | technical specification, system architecture, schema, API, components, dependency map, roadmap |
| `architecture.json` | `schemas/architecture.schema.json` | the same decisions, structured, for the validators |
| `schema.sql` (or first migration) | | the database schema |
| `api.md` or `openapi.yaml` | | the API specification |

## 1. Choose the stack

Choose for this product, not by adding up the sources' stacks. In order:

1. Constraints the user gave (a required language, host, or existing
   codebase to build into).
2. What the kept features need (realtime, offline, heavy reporting, mobile).
3. Where `reuse` or `adapt` strategies are planned, the stack that code is in.
4. The stack most kept features already use, if it is maintained and fits.
5. Boring, well documented, managed options over novel ones.

Write each choice with its reason in `stack.reasons` and as a decision
(`D01`...). When the stack differs from a source's, set that source's kept
features to `rebuild` or `combine`, not `adapt`.

## 2. Choose the architecture style

Do not default to one shape. Compare the styles against this project's
drivers and record the result in `architecture.json` → `style`:

| style | fits when | costs |
| --- | --- | --- |
| modular monolith | one team, one release cadence, strong data consistency, modest scale; most merged apps start here | one deployable; module boundaries need discipline |
| microservices | independent teams or release cycles, very different scaling or reliability needs per part, mature operations | network calls, distributed data, observability, many deployables |
| service-oriented | a few coarse services around existing systems that must stay separate (an existing billing system) | integration contracts to maintain |
| event-driven | work that is naturally asynchronous (notifications, imports, fan-out), loose coupling, audit trails | eventual consistency, harder debugging, message infrastructure |
| hybrid | a core monolith plus one or two parts that clearly need another style (a monolith with an event-driven notification pipeline) | two sets of rules to keep |

Drivers to weigh: team size and ownership, release independence, scale and
load shape per feature, data consistency needs, latency, operations
maturity, the user's existing systems and constraints, and cost.

```json
"style": {
  "selected": "modular-monolith",
  "drivers": ["one small team", "strong consistency between tasks and approvals", "no independent scaling need"],
  "alternatives": [
    {"style": "microservices", "fit": "poor", "reason": "operational cost with no independent scaling need"},
    {"style": "event-driven", "fit": "partial", "reason": "notifications are asynchronous, but volume is low"}
  ],
  "reason": "Simplest design that meets every driver"
}
```

Then follow the style's rules, which the validator checks:

- every entity has one owning module (all styles)
- microservices and service-oriented: every module names its `service`,
  and there are at least two services
- event-driven (or any design with events): an `events` list with
  `name`, `producer` and `consumers`, all known modules
- hybrid: say which parts differ (services or events)

## 3. Unify the data model

For every entity the kept features use:

- one name (apply `compat/aliases.json`), one primary key type (the
  compatibility decision), timestamps in UTC, money as integer minor units
  plus currency
- the union of fields kept features need, each traced in `merged_from`
  (`["A:Task", "B:Ticket"]`)
- foreign keys with a chosen `on delete` behaviour, indexes on every foreign
  key and every filtered or sorted column
- check constraints for status values and limits taken from business rules
- the entity's `fields` in `architecture.json`, with `from` for renamed
  fields (`{"name": "name", "type": "text", "from": ["B:User.full_name"]}`),
  so `check_compatibility.py` can report any source field the unified schema
  would drop; rerun it now and update `design/migration-plan.md`
- the migration from each source's data, if data will be moved (high-risk
  steps need approval; see `engines/compatibility-analysis.md`)

## 4. Unify identity and access

- One identity system offering the sign-in methods kept features need.
- One session mechanism (http-only, secure cookies are the safe default for
  web apps; tokens only for clients that cannot hold cookies).
- One role set plus explicit permissions. Write the `role_mapping` from
  every source role to a unified role, and model special powers (approving,
  billing) as permissions, not more roles.
- Multi-tenant data: every tenant-owned entity carries the tenant key
  (`tenant_key` or a field such as `org_id`), every query filters by it, and
  shared resources are marked `shared: true` by the user's decision. Test
  that one tenant cannot read, list, search or change another's data.
- Account linking: a federated sign-in joins an existing account only on a
  provider-verified email; never on an unverified one.
- Give each unified endpoint its origin (`"from": ["A: GET /v1/x"]`) or none
  if it is new; the checker rejects an origin that the source does not have.
- One function answers "may this user do this to this record". Every route
  and every query uses it.

## 5. Structure the system

- **Modules.** Group kept features into modules with one responsibility
  each. Merged groups become one module (the notification engine). List
  each module's features, dependencies and the entities it owns. No cycles.
- **API.** One style (REST or GraphQL), one versioning scheme, one error
  shape (for example `{"error": {"code", "message"}}`), one pagination
  style, one auth scheme for every endpoint.
- **Navigation.** One route per screen; collisions from phase 4 resolved.
- **Design system.** One set of tokens (colour roles, type scale, spacing,
  radius) and one component library, with the union of variants kept
  screens need. Open fonts and icon sets, the user's own brand. Nothing
  visual is taken from a closed source.
- **Configuration.** Every setting is an environment variable read in one
  config module, with defaults for development and a `.env.example` listing
  every name with no values. Secrets never go in code or logs.
- **Shared components and state.** One owner per piece of shared state,
  namespaced by module.

## 6. Plan the build

Split the work into vertical slices (`V1`, `V2`...), each a thin path
through every layer that a user could try:

1. `V1`: the core loop end to end (sign in, do the main thing, see the
   result).
2. Then the remaining `must` features, grouped so each slice is testable.
3. Then `should`, then `could`.

Each slice lists its features (menu ids), and every kept feature is in
exactly one slice. Draw the feature dependency map (a Mermaid graph of menu
ids, from `depends_on`) in `architecture.md`.

## 7. Write and check

Fill `prd.md` and `architecture.md` from the templates and write
`architecture.json`. Then:

```bash
python3 scripts/validate_artifacts.py mixer/
python3 scripts/check_dependencies.py mixer/
python3 scripts/validate_project.py mixer/ --phase architecture
```

They check that every kept feature is in a module and a slice, that no
module, route or endpoint is duplicated, and that modules have no cycles.

## 8. Approval

Show the user: the style and the alternatives considered, the stack and
why, the merge plan, the modules, the merged data model and what moves where
(with data-loss risks), the role mapping, the API style, and the slices in
order.
Record approval with `python3 scripts/approvals.py approve-phase --mixer mixer/ --phase architecture
--granted-by "<name>" --user-confirmed`, checkpoint, and log every decision
with its `D` id. In `plan` mode, the run ends here: say plainly that nothing
was built or tested, and leave implementation and integration `pending`
(`validate_project.py` rejects a plan-mode run that claims a build).
