# Compatibility analysis engine

Phase 4. Before anything is designed or built, find every place where the
kept features will not fit together, decide what to do about each, and get
the user's approval for the important decisions.

Never begin integration while a critical conflict is unresolved.

## 1. Prepare the inputs

The script compares what is in the source reports, so the reports must hold
the facts it needs: `entities` (with primary keys, field types and foreign
keys), `endpoints` (method, path, auth, request and response fields,
version), `auth` (provider, methods, session, model, roles), `routes`,
`state`, `components`, `rules` (key and value), `integrations`, and
`packages` / `runtimes`. Link each to its features with `features: [...]`.
If something is missing, go back to the source and extract it, or record it
as unknown.

Then add the meaning the script cannot work out on its own:

- `mixer/compat/aliases.json`: names that mean the same thing across apps.

  ```json
  {"entities": {"Ticket": "Task", "Person": "User"},
   "fields": {"full_name": "name", "assignee": "assignee_id"}}
  ```

- `mixer/compat/manual-conflicts.json`: conflicts you found by reasoning
  (`category` is optional: it follows from `kind`, or set `database`, `api`,
  `dependency` or `application` yourself),
  such as contradicting business rules written in prose, workflows that
  fight each other, or permissions that clash in practice.

  ```json
  [{"kind": "workflow", "subject": "closing-tasks", "apps": ["A", "B"],
    "severity": "high", "detail": "A lets anyone close a task; B requires an approval first",
    "solutions": ["Require approval for tasks that have one", "Drop the approval gate"],
    "recommended": "Require approval only when an approval was requested",
    "features": ["A-F02", "B-F01"]}]
  ```

## 2. Run the analysis

```bash
python3 scripts/check_compatibility.py mixer/ --write
```

It looks only at kept features once a selection exists (`--all` for
everything), and writes `mixer/compat/compatibility-report.md` and `.json`.

| area | what it checks | default severity |
| --- | --- | --- |
| database | duplicate entities across apps | medium |
| | primary key type differences | critical |
| | the same field with different types | high |
| | foreign keys to missing entities, or with a type unlike the key they point at | medium / high |
| | field naming styles (snake_case vs camelCase) | low |
| | migrations each merged entity needs, and whether they are destructive | listed separately |
| API | the same method and path in several apps | medium |
| | request or response fields with different types | high |
| | different auth on the same endpoint | high |
| | different API versions | medium |
| | different update methods (PUT vs PATCH) on the same path | low |
| application | different identity providers | high |
| | different sign-in methods | medium |
| | different session mechanisms | high |
| | different authorization models or role sets | high |
| | the same global state key | medium |
| | the same route used by different screens | high |
| | the same component with different variants | low |
| | the same business rule with different values | high |
| | the same third-party integration | low |
| dependencies | major version conflicts (framework packages) | high (medium for other packages) |
| | runtime version conflicts | high |
| | several runtimes, or competing frameworks in one layer | medium |
| | several libraries for the same job | low |
| | circular module dependencies in the plan | critical |
| | a vulnerability an audit tool reported (critical or high / moderate / low) | high / medium / low |

`scripts/check_dependencies.py` runs the dependency checks on their own,
including on raw folders (`--scan A=path`).

### Migrations and data loss

Each migration lists its steps with a data-loss risk:

- **none**: nothing changes for existing data
- **low**: every value is kept (adding fields, widening a type such as
  integer to text, date to timestamp)
- **high**: values can be lost, changed or rejected: re-keying, narrowing a
  type, or a source field the unified schema does not keep

Dropped fields are found once `design/architecture.json` lists each entity's
`fields` (with `from: ["A:User.name"]` where names change), so rerun the
analysis after the architecture is drafted. A high-risk migration is
destructive: it needs the user's approval (in `resolutions.json` or the
approvals ledger) and a plan from `templates/migration-plan.md` with backup,
dry run, checks and rollback. Never run a migration from this phase.

### Dependency intelligence

- **Vulnerabilities** come only from a real audit tool's output: `npm audit
  --json`, `pip-audit -f json` or `osv-scanner --format json`, saved as
  `mixer/compat/audit/<APP>-<tool>.json`. Running those tools needs the
  network and the user's approval (`network`, and for npm an installed
  dependency tree, so `install-dependencies` too, with `--ignore-scripts`).
  They are reported as **confirmed**. Without an audit, say "not checked",
  never "no vulnerabilities".
- **Warnings** about unpinned or non-registry versions (`*`, `latest`, git,
  `file:`) are **unverified**: nothing offline can check them.
- **Necessity**, with an `index.json` per source: packages declared but never
  imported, imported but not declared, and those only used by files of
  dropped features. Import scanning is approximate, so these are suggestions
  for the architecture, not facts.

Severity, when you set it yourself in manual conflicts:

- **critical**: integration would corrupt data, break security, or cannot
  work at all until decided
- **high**: a kept feature behaves wrongly or a security rule is unclear
  until decided
- **medium**: needs a decision but has a safe default
- **low**: tidy-up; decide during design
- **info**: worth knowing, no decision needed

## 3. Decide

Read the report. For every conflict it gives the description, the apps and
features affected, the severity, the possible solutions and a recommended
resolution. Add your own reasoning where the default recommendation does not
fit this project.

Write each decision to `mixer/compat/resolutions.json`, keyed by conflict id:

```json
{
  "database:primary-key:user": {
    "decision": "uuid for every user; B's integer ids kept in legacy_id during migration",
    "approved": true, "by": "user", "date": "2026-11-04"
  },
  "migration:user": {
    "decision": "re-key B's users and rewrite B's foreign keys; dry run on a copy first",
    "approved": true, "by": "user", "date": "2026-11-04"
  }
}
```

- `critical` and `high` conflicts count as resolved only with
  `"approved": true`, and only the user can approve them.
- High-risk migrations (`migration:<entity>`) need the same explicit
  approval. In this phase it approves the **plan**: record it in
  `resolutions.json` (or the ledger, action `migration`) with a note such as
  "plan approved; running it needs its own approval". Running the migration
  later is a separate `migration` approval in the ledger.
- `medium` and `low` conflicts need a decision but not a separate approval;
  include them in the summary you show the user.

If no resolution is acceptable, offer to drop or defer one of the conflicting
features and go back to selection.

## 4. Gate

```bash
python3 scripts/check_compatibility.py mixer/ --write --strict
python3 scripts/validate_project.py mixer/ --phase compatibility
```

Both must pass: no open critical or high conflict, every destructive
migration approved. Then update each kept menu row's `compatibility`
column, show the user the summary, record the approval, checkpoint, and log
every decision.
