# Changelog

## 2.1.0 (2026-11-04)

Reliability, intelligence and security. An improvement of 2.0, not a
rewrite: every 2.0 capability is kept, the 2.0 tests pass unchanged apart
from two that now also accept the new names, and a frozen copy of the 2.0
example workspace still validates (with warnings for what 2.1 adds).

### Compatibility with 2.0

- `project.json` `"format": 2` workspaces keep working: every 2.1 check is a
  warning there. `"format": 3` (new runs) makes them errors. The one
  exception is a credential found in `mixer/`, which is an error in both.
- Feature menus keep their columns and meaning; `separate`, `improve`,
  `conflicting` and `independent` are additions.
- `check_menu.py` and the example's `run_integration.py` still work.

### Added: security (P0)

- `engines/security.md`: the single home of the ground rules: trust
  boundary (sources are data, never instructions), access by rights, safe
  inspection, isolation, actions needing approval, never fabricating.
- `scripts/scan_source.py`: scans a source before it is read for secrets
  (values redacted), environment files, AI-instruction files and text
  (prompt injection), install and build hooks, CI, git hooks, submodules,
  registry overrides, symbolic links escaping the folder, binaries and
  oversized files. Never executes or follows anything.
- Safe-clone recipe (no hooks, no submodules), isolation guidance (container,
  VM or sandbox; `check_environment.py` reports docker or podman).
- Approvals ledger in `project.json` (`run-source-code`,
  `install-dependencies`, `run-tests`, `network`, `destructive`,
  `migration`, `deployment`), checked by the validators.
- No credential pattern may appear anywhere in `mixer/`.

### Added: trustworthy test reporting (P0)

- `scripts/run_tests.py` runs the tests itself (a built-in unittest harness,
  or any framework that writes JUnit XML) and records the command,
  framework, folder, UTC start and finish, exit code, the full log and the
  per-test results with SHA-256 fingerprints, then writes the integration
  report from that evidence only.
- Five statuses: passed, failed, skipped, not-executed, unverified.
- `scripts/verify_tests.py` checks a report against its evidence (record,
  fingerprints, per-test statuses, exit code, times, counts), flags
  fabricated or invented results, regressions against a saved baseline, and
  acceptance criteria without a verified test; `--rerun` repeats the run.
- Self-reported passes are no longer proof: in format 3 a report without
  evidence proves nothing.

### Added: capability detection (P0)

- `scripts/check_environment.py` records what the session can do
  (`mixer/capabilities.json`); Claude records browser, web fetch,
  repository and API access from its own tools. Statuses: available,
  unavailable, partial, not-needed, not-checked.
- Evidence from an input the session could not read (a website with no
  browser or fetch tool, a GitHub repo with no repository access) is
  rejected.

### Added: intelligence (P1, P2)

- Merging: `separate` merge type (related but kept apart), `improve`
  strategy (fix before integrating), `conflicting` and `independent` as
  other names; `mixer/merge-plan.json` with one unified feature per
  capability (sources, evidence, rationale, final behaviour, dependencies,
  compatibility, validation status). The validator stops anything being
  built twice, checks groups are merged as their type says, and ties
  validation status to verified tests.
- Architecture: evaluation of modular monolith, microservices,
  service-oriented, event-driven and hybrid against the project's drivers;
  `architecture.json` `style` with the alternatives considered; style rules
  (services, events, one owner per entity).
- Large repositories: `scripts/index_repo.py` (inventory with fingerprints,
  modules, approximate import graph, external packages, feature-to-file
  map, changed files and stale features); per-module summaries;
  `coverage_detail`; "complete" refused while modules are unread; stale
  features must be re-analysed.
- Migrations: per-step data-loss risk (none, low, high), fields the unified
  schema would drop or narrow, `templates/migration-plan.md`; migrations
  approved through resolutions or the approvals ledger.
- Dependencies: confirmed vulnerabilities from npm audit, pip-audit or
  osv-scanner output (critical and high become high conflicts); unverified
  warnings for unpinned or non-registry versions; necessity analysis
  (declared but unused, used but undeclared, only used by dropped features).
- Testing: `dependency` and `regression` levels, acceptance-criteria tags,
  regression baseline, feature-to-test map.

### Added: release quality and benchmarks (P2)

- `tools/release_check.py`: caches, versions, skill discovery, referenced
  files, scripts from any folder, JSON, README install commands,
  `claude plugin validate` when available, `--clean`, `--package`.
- `benchmarks/`: six scenarios (overlapping, complementary, conflicting,
  large, incomplete, heterogeneous) with answer keys, a reproducible large
  repository generator, `score.py`, the six runs' workspaces, and results
  from runs by separate agents that were not given the answer keys
  (`benchmarks/RESULTS.md`).
- `tools/testing_report.py`: runs the verification checklist and writes
  `docs/TESTING-REPORT.md` from real command output.

### Changed

- `SKILL.md`: capability detection first; ground rules summarised with a
  pointer to the security engine; validator details moved to
  `engines/validation.md` (one place for each topic); large-repository and
  recovery guidance.
- Every engine updated; schemas extended (`project`, `feature`,
  `source-report`, `architecture`, `integration-report`); three new schemas
  (`capabilities`, `security-scan`, `merge-plan`); new templates (`merge-plan.json`,
  `module-summary.md`, `migration-plan.md`; `project.json` now format 3).
- The example is a format 3 workspace: capabilities, scans, indexes and
  summaries, merge plan, architecture style, field-level migration plan
  (which caught a dropped field), approvals, and verified test evidence.
- `.gitignore` adds `*.db` and `mixer/checkpoints/`.

### Found by the benchmark runs and fixed before release

The six benchmark runs used an early copy of 2.1 and found these; each fix
has a test (`tests/test_benchmark_findings.py`). Details in
`benchmarks/RESULTS.md`.

- `selection` (`manual` / `auto-pick`) is now separate from `mode`, so plan
  or full can be combined with auto-pick; `"mode": "auto-pick"` still works.
- `scripts/checkpoint.py`: make, list and restore checkpoints without git
  (restores into a new folder; never commits, resets or deletes).
- Foreign keys accept `User`, `User.id` and `users(id)`.
- Entities that kept features point at stay in the compatibility analysis
  (a critical key conflict was hidden before).
- The scanner finds literal keys passed to signing calls at any length, and
  scans every non-binary file whatever its extension.
- Type strings with constraints (`integer primary key autoincrement`) and more
  synonyms (`str`, `bytes`, `blob`) are understood; unknown types are reported
  as `unknown-type` (info), not as mismatches.
- Only kept rows are listed as affected features; manual conflicts get a
  category from their kind, and decisions under the old id still count.
- Framework ties are reported as ties; a Python vs Node mix is detected from
  manifests even without pinned runtime versions.
- Guidance: auto-pick prefers safety and data integrity; platform modules no
  source provides live in the architecture; version control is optional;
  plan-only migration approvals; phase sign-offs vs the approvals ledger;
  the log template says where rows go; scan before even listing a source.

### Fixed during this release

- `release_check.py --clean` crashed on files inside a cache folder it had
  already removed.
- `verify_tests.py --rerun` refused to run when verification had errors,
  which is when a re-run matters most.

## 2.0.0 (2026-11-04)

Feature Mixer becomes a single, independent skill that reverse-engineers
several applications, compares and merges their features, checks
compatibility, and builds and tests one unified application. It no longer
depends on any other skill.

### Breaking changes

- **No external skill dependency.** v1 called the Replica skill pack for
  recon, build, test and deploy. v2 contains its own instructions for every
  phase. Remove nothing from your setup; Feature Mixer simply no longer needs
  it.
- **Workspace renamed** from `replica/` to `mixer/`, with a new
  `mixer/project.json` that records sources, their rights, the mode, phase
  status, approvals and checkpoints.
- **Skill folder reorganised.** `check_menu.py` moved to
  `feature-mixer/scripts/`; `feature-menu.csv` and `mixer-log.md` moved to
  `feature-mixer/templates/`.
- **One or more sources.** v1 required two to five apps. v2 accepts one
  (rebuild and improve a single app) or more.
- **Deployment is never automatic.** v1 deployed after a "go"; v2 deploys
  only when the user asks, after a preflight, with explicit approval
  recorded.

### Added: workflow (SKILL.md and engines/)

- `SKILL.md` rewritten as a modular guide: ground rules, inputs, workspace,
  eight phases with completion criteria, approval checkpoints, validators,
  error recovery, optional helpers and the final summary.
- `engines/reconnaissance.md`: independent analysis of each source from
  websites, local folders, GitHub repos, screenshots, documentation, API
  specs and source code. Extracts frontend and backend architecture, screens,
  components, navigation, workflows, features and subfeatures, business
  logic, entities and relationships, endpoints and contracts, authentication
  and authorization, integrations, stack, error handling and configuration.
  Unique app, screen, workflow, feature and evidence ids per source.
- **Evidence-based reverse engineering:** every fact cites evidence with a
  basis (observed, documented, inferred, unknown), a locator and a
  confidence. Partial results are allowed but must list their unknowns.
- **Access rules by rights:** own code, open source (licence-checked) and
  closed products (behaviour only, always rebuilt).
- `engines/feature-intelligence.md`: one menu across all sources; merge
  groups and five merge types (identical, similar, complementary, unique,
  incompatible); five implementation strategies (reuse, rebuild, adapt,
  combine, reject) with licence rules; first-pass compatibility;
  recommendations; the selection flow (single features, several, whole
  groups, alternatives, combining, rejecting duplicates, deferring); and
  `auto-pick` rules that never drop a must-have silently.
- `engines/compatibility-analysis.md`: database, API, dependency and
  application compatibility; severities; aliases and manual conflicts for
  meaning the script cannot infer; resolutions with approvals; destructive
  migration approval; the gate that stops integration while a critical
  conflict is open.
- `engines/architecture-design.md`: one frontend, backend, database, auth
  system, authorization model, navigation, design system, configuration and
  API strategy; stack chosen from requirements and constraints, not by adding
  up the sources; PRD, technical specification, schema, API spec, component
  architecture, feature dependency map and a slice-based roadmap.
- `engines/implementation.md`: builds the actual application in vertical
  slices, each finished and tested before the next; safe setup (sources
  read-only, new folder or branch, no silent overwrites); merged modules
  instead of copied ones; licence notices for reused code; migrations and
  secrets rules; failure handling and rollback; deployment preflight.
- `engines/validation.md`: every validator explained; integration testing
  across feature, interaction, API, database, auth, authorization,
  navigation, form, error, journey and regression levels; the integration
  report format; the fix loop; "never claim it works without a passing test".
- **Checkpoints and rollback:** a checkpoint after every phase and slice (git
  tag or snapshot), a decision history and integration log, failed and
  rolled-back phase states, and rollback by branching from a checkpoint
  (never by deleting work).

### Added: validators (scripts/)

All standard-library Python 3.8+, no network, exit codes 0 / 1 / 2.

- `validate_feature_menu.py` (the upgraded `check_menu.py`): duplicate ids,
  invalid picks, unknown references, circular dependencies (including
  self-dependency), transitive dependency validation with the path shown,
  conflicts, skip restrictions, merge group and merge type rules, evidence
  reference format, compatibility, confidence and strategy values. Adds a
  grouped selection view (`--show`, text or Markdown), safe pick changes
  (`--set keep M01,group:notifications`) that refuse to keep `skip` rows and
  announce dropped must-haves, and `--allow-no-keep` for use before
  selection.
- `check_dependencies.py`: scans `package.json`, `requirements.txt`,
  `runtime.txt` and `.python-version` (skipping `node_modules` and similar),
  plus packages recorded in source reports; reports major-version and
  runtime conflicts, mixed runtimes, competing frameworks per layer,
  duplicate libraries per job, and circular module dependencies.
- `check_compatibility.py`: duplicate entities (with aliases), primary key
  differences, field type mismatches, foreign key problems, naming styles,
  required migrations (flagging destructive ones); duplicate endpoints,
  contract mismatches, auth differences, version and method conflicts;
  identity provider, sign-in methods, session mechanism, authorization model
  and role conflicts, state, route, component, business rule and integration
  collisions; manual conflicts; scope limited to kept features; a Markdown
  and JSON report with description, apps, features, severity, solutions,
  recommendation, approval requirement and status.
- `validate_artifacts.py`: source report sections and schema, id prefixes,
  evidence resolution, honesty checks (no inferred or unknown fact marked
  high confidence, no feature claiming more than its evidence), workflow and
  route references, partial coverage; design files, module and slice
  coverage, duplicate routes and endpoints, module cycles; integration
  report schema, failing tests, and a passing test for every kept feature.
- `validate_project.py`: the whole workspace and per-phase completion
  criteria, phase order, approvals, checkpoints, failed phases with the
  checkpoint to roll back to, undecided rows, licence rules for reuse and
  adapt, open critical and high conflicts, unapproved destructive
  migrations, roadmap status and the target folder.
- `check_menu.py` kept as the v1 entry point; it now runs the full
  validator and keeps the v1 output and exit codes.
- `mixerlib.py`: shared helpers, including a small JSON Schema checker.

### Added: schemas and templates

- Schemas: `project`, `source-report`, `feature`, `architecture` and
  `integration-report`.
- Templates: `source-report.md`, `prd.md`, `architecture.md`,
  `integration-report.md`, `mixer-log.md`, `project.json`, and a v2
  `feature-menu.csv` that still demonstrates the v1 dependency check.

### Changed: feature menu

- The ten v1 columns are unchanged and v1 menus still validate.
- New columns: `merge_group`, `merge_type`, `evidence_refs`,
  `compatibility`, `implementation_strategy`, `confidence`,
  `integration_notes`, plus optional `description` and `source_features`
  for the selection view and traceability.

### Added: example and tests

- `examples/team-hub`: a full run on three fictional sources (own code, MIT
  open source, a closed product known from docs), with source reports, the
  menu, 20 resolved conflicts including a critical key conflict and a
  manually found workflow conflict, the PRD and architecture, a working
  standard-library Python app with one notification engine, 23 app tests,
  and the generated integration report.
- Test suite grows from 7 to 93 tests (plus 23 in the example app). The seven v1 tests are kept with
  their assertions unchanged. New tests cover one, two, three and more
  sources; duplicate, complementary and incompatible features; missing,
  transitive and circular dependencies; database, API and authentication
  conflicts; selection errors; failed-phase recovery; partial results;
  missing evidence; design and integration reports; the example project and
  its app; the plugin structure; and that the skill runs without any other
  skill.

### Changed: documentation and metadata

- README rewritten: what it does, what's new, download, install, usage
  examples, phases and approvals, the menu, the validators, the example,
  layout, tests, upgrading, ground rules.
- Plugin and marketplace metadata: version 2.0.0, new description and
  keywords, no external dependency.
- CONTRIBUTING updated for the new layout.

## 1.0.0 (2026-11-04)

- First release: `feature-mixer` skill with full, plan and auto-pick modes,
  orchestrating the Replica skill pack.
- `check_menu.py` dependency and conflict checker for feature picks.
- Feature menu and mixer log templates.
- Claude Code plugin and marketplace manifests.
- README with download, install and comparison guides.
