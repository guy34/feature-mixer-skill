# Workflow review (v2.2, Phase 6)

The scripts can be right while the AI workflow decides badly. This review
walks the 15 failure scenarios through `SKILL.md` and the engines as they
were in 2.1.0, records what was already covered, what was missing, and what
2.2 changed. "Check" means a script now enforces it and a test proves that;
"instruction" means only the skill's text changed, so it depends on the model
following it and is measured by the benchmark runs, not by unit tests.

| # | scenario | 2.1.0 | gap found | 2.2 change | enforced by |
| --- | --- | --- | --- | --- | --- |
| 1 | three apps with almost no documentation | partial coverage and `unknowns` required; `inferred` never high | nothing told Claude to surface the uncertainty at selection | reconnaissance: mark deductions `inferred`, say so at selection | instruction; existing checks (partial ⇒ unknowns, inferred ≠ high) |
| 2 | nearly identical features, different business rules | `business-rule` conflicts when the rule is recorded with a value | a decision could pick a behaviour without anything proving it | decisions name their tests (`verified_by`); verify fails until they pass; "never combine rules side by side" | check: `verify_tests.py` (`test_integration_scenarios` L) |
| 3 | malicious prompt instructions in a source | sources are data; scanner patterns | split, hidden-HTML, encoded, zero-width and full-width text missed; secrets copied into findings | scanner rewrite; snippets redacted | check: `test_adversarial_sources` A, probes P18, P21 |
| 4 | a kept feature depends on a rejected one | validator errors with the path | none | engine says it is the user's call and lists the options with costs | existing check (`validate_feature_menu.py`) + instruction |
| 5 | a feature needs a proprietary external service | "the user creates accounts and keys; test modes" | nothing said tests against a fake prove only the app's side | adapter + fake, "not testable here", never "verified against the real service" | instruction |
| 6 | a source with no accessible backend | closed sources studied through public material | a closed source could claim code evidence or an `observed` backend | closed source: no code evidence, no `observed` entity/endpoint without the running product | check: `validate_artifacts.py` (`test_robustness` R) |
| 7 | the target has an existing database with valuable data | migration approval, backup, dry run | no proof the backup restores; no before/after comparison | tested restore, row counts, rehearsal on the restored copy | instruction; migration-plan template section |
| 8 | completely different stacks | runtime-mix and framework conflicts; architecture style choice | version checks used majors only; Go, Rust, pyproject unread | range arithmetic, five manifest kinds, runtime ranges | check: `test_compatibility_failures` F |
| 9 | the model misunderstands an API response | API tests on response shape | nothing tied a response shape to a real sample | record a real (redacted) sample as evidence, contract test against it, live response wins | instruction |
| 10 | unit tests pass, the end-to-end workflow is broken | `journey` listed as a test level | nothing required a journey test | v2.2 workspaces need at least one passing `level: journey` test | check: `validate_project.py` (`test_workflow_guards`) |
| 11 | the model invents a feature in no source | menu evidence must exist in a source report | a feature the user asked for had no legal form, which pushed toward citing unrelated evidence | `source_app` `new` allowed only with "requested by the user"; anything else is reported as invented | check: `validate_feature_menu.py` (`test_workflow_guards`) |
| 12 | context lost in a long session | resume from `project.json` and the log | no rule to re-read decisions before each slice; nothing caught drift | re-anchor before each slice; files win over memory; phase fingerprints catch drift | check (fingerprints) + instruction |
| 13 | the user changes requirements halfway | none | picks, decisions and design could change after approval without anyone noticing | `approvals.py approve-phase` stores what was approved; a later change is an error until approved again; change procedure in SKILL.md and implementation | check: `validate_project.py` (`test_workflow_guards`) |
| 14 | a migration partially succeeds, then fails | rollback in the plan | no rule against re-running or fixing forward | stop, restore, compare counts, ask; steps safe to re-run | instruction; migration-plan template |
| 15 | two selected features exclude each other | `conflicts_with` and `incompatible` groups are errors when both are kept | none | engine wording: never both; `separate` with a written boundary is the only way to keep both | existing check |

Also found and fixed while reviewing:

- **Plan mode could claim a build.** A `plan` run that marks
  implementation, integration or deployment as started is now an error, and
  the finish says plainly that nothing was built or tested.
- **"Done" from documents.** The ground rules now say planning documents are
  not a working app, and that zero tests, timeouts and contradictory results
  prove nothing; the scripts back this with run verdicts.

What this review cannot show: whether a model follows the instruction-only
rows. The benchmark runs (`benchmarks/RESULTS.md`) measure that on the
scenarios they cover; rows 5, 7, 9 and 14 are not yet covered by any
benchmark scenario that exercises them end to end.
