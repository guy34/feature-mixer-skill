# Validation engine

Phase 7, and the one reference for every script. The scripts make the checks
that must be exact; integration testing proves the app works.

All scripts are in `scripts/`: Python 3.8+, standard library only, no
network, runnable from any folder. Exit codes: `0` fine, `1` something to
fix (or, for the scanners, something to show the user), `2` a file or
argument could not be read.

v2.0 workspaces (`project.json` `"format": 2`) get warnings for the v2.1
checks; v2.1 workspaces (`"format": 3`) get errors for them; v2.2 workspaces
(`"format": 4`) also get errors for the v2.2 checks (recorded phase
approvals, journey tests, honesty of observed vs documented, evidence
ledger and code fingerprint). Runs recorded by the 2.2 `run_tests.py` are
held to the 2.2 evidence rules in every format. Credentials in `mixer/` are
an error in all.

## Before reading sources

| script | does |
| --- | --- |
| `check_environment.py --mixer mixer/ [--target app/] [--set NAME=STATUS "why"]` | records what the session can do in `capabilities.json`: terminal, test runners, git, node, docker or podman for isolation, audit tools, the Claude CLI, write access; Claude adds `browser`, `web_fetch`, `repository_access`, `external_api` with `--set` |
| `scan_source.py <folder> --out .../security-scan.json [--max-file-mb 5] [--max-files N] [--max-depth N]` | secrets (redacted; also base64-encoded, split into pieces, in connection strings; placeholders reported as info), random-looking literals (low), environment files, AI-instruction files and text (also split across lines, hidden in HTML, base64, zero-width or full-width characters), install, build, IDE, direnv, dev-container and git-config hooks, CI, submodules, registry overrides, links escaping the folder, unusual file names (shown escaped), named pipes and devices (never opened), binaries, oversized files (first part scanned), and every part not scanned (depth, file limit, unreadable: `complete: false`); never follows a link, walks by file descriptor where the OS allows; exit 1 when there are high findings to show the user. Pattern scanning misses things and flags harmless text |
| `approvals.py request / grant / check / list / revoke / approve-phase` | scoped approvals for running code and recorded phase sign-offs (`engines/security.md` section 5) |
| `checkpoint.py mixer/ --phase P [--include-target] [--note ...]`, `--list`, `--restore CPn --to NEW` | copies the workspace (and app) into `mixer/checkpoints/CPn/`, records the git commit if any, adds the row to `project.json`; restores only into a new folder; never commits, resets or deletes |
| `index_repo.py <folder> --out .../index.json [--previous old.json] [--source-json source.json] [--progress N] [--include-nested]` | file inventory with fingerprints, languages, modules and generated-code flags; imports (Python parsed with `ast`, including relative, optional and dynamic imports; JS/TS with path aliases, workspace packages, barrels and `import()`; Go, Rust, Java by pattern) with `import_coverage` per language and the count of unresolved dynamic imports; module dependency map and cycles; nested repositories as boundaries (not indexed); feature-to-file map; changed files and stale features since a previous index (exit 1 when features are stale); bounded memory, limits and unreadable parts reported (`complete`) |

## Checking work

### validate_feature_menu.py

```bash
python3 scripts/validate_feature_menu.py mixer/feature-menu.csv [--allow-no-keep]
python3 scripts/validate_feature_menu.py mixer/feature-menu.csv --show [--format md] [--only keep]
python3 scripts/validate_feature_menu.py mixer/feature-menu.csv --set keep M01,group:notifications
```

Errors: duplicate ids; invalid picks; unknown references; circular
dependencies; kept features whose dependencies are not kept, directly or
through others (with the path); kept features that conflict; features that
depend on `skip` rows; `skip` rows not rejected. For v2 columns also:
invalid merge types, strategies, compatibility or confidence; groups mixing
types; `unique` groups with several rows; more than one kept `identical`
feature; several kept `similar` features not all `combine`; several kept
`incompatible` features; `incompatible` without `conflicts_with`; kept
`separate` rows that are combined or have no boundary note; kept `improve`
rows with no note; kept rows without evidence, rejected, or incompatible
without `rebuild` or `adapt`; malformed evidence or source feature ids; a
row from no source (`source_app` `new`) whose notes do not say the user
requested it (an invented feature).
`conflicting` and `independent` are read as `incompatible` and `unique`.
`check_menu.py` is the same tool under its v1 name.

### check_compatibility.py and check_dependencies.py

```bash
python3 scripts/check_compatibility.py mixer/ [--all] [--write] [--json] [--strict]
python3 scripts/check_dependencies.py mixer/ [--audit A=npm-audit.json] [--json] [--strict]
python3 scripts/check_dependencies.py --scan A=../taskboard --scan B=../approvals
```

Every check, the severities, migration data-loss risk and dependency
intelligence are in `engines/compatibility-analysis.md`. Both exit 1 while a
critical conflict is unresolved; `--strict` also blocks on high.

### validate_artifacts.py

```bash
python3 scripts/validate_artifacts.py mixer/
python3 scripts/validate_artifacts.py --source mixer/sources/A-taskboard
```

- **Source reports**: sections; schema; ids unique and prefixed; evidence
  resolves to listed sources; every feature has evidence; nothing inferred
  or unknown is high confidence or claims more than its evidence; workflow
  steps and routes point at listed screens; partial coverage lists its
  unknowns; no evidence from an input the session had no capability to
  read; with an index: every module analysed or skipped before `complete`,
  a summary per analysed module, evidence pointing at indexed files, no
  stale features; high scan findings acknowledged. v2.2: a feature claiming
  `observed` needs at least one observed piece of evidence (documentation
  describes, it does not show); a closed source cites no code and marks no
  entity or endpoint `observed` unless it was seen in the running product;
  every `contradictions` entry (documentation vs code) resolves and no
  feature rests only on contradicted documentation.
- **Design**: sections; schema; modules unique, known and acyclic; one owner
  per entity; every kept feature in a module and a slice, nothing extra; no
  duplicate endpoints or routes; the architecture style with at least two
  alternatives and its own rules (services, events); the merge plan (see
  `engines/feature-intelligence.md`).
- **Integration**: everything `verify_tests.py` checks, the report's
  sections, and the merge plan's `validation` against verified results.
- **Secrets**: no credential in any file under `mixer/` (connection-string
  passwords included; documented placeholders such as `AKIA...EXAMPLE` are
  allowed).

### validate_project.py

```bash
python3 scripts/validate_project.py mixer/ [--phase PHASE]
```

Runs the checks above as each phase requires, plus `project.json` against
its schema, unique app ids and slugs, phases in order, phase approvals (and,
v2.2, that nothing a phase approval covered has changed since: the menu's
picks and merge plan, the compatibility decisions, the design; plan mode
never marks a build phase started),
checkpoints, failed phases (with the checkpoint to roll back to), the
capabilities file, a security scan for every source with code, undecided
menu rows, `reuse` or `adapt` only where `code_reuse` is `allowed`, open
critical and high conflicts, unapproved high-risk migrations, slices not
done, the target folder, an approval behind the test run, and a deployment
approval. Without `--phase` it checks up to the furthest phase that has
started; the errors for that phase are what is left to do.

## Running and verifying tests

### run_tests.py

Runs the tests itself, under a scoped approval, and writes the evidence, so
results never come from a claim:

```bash
# Python unittest (built-in harness that records every test)
python3 scripts/approvals.py grant --mixer mixer/ --cwd app/ --unittest tests --granted-by "<name>" --user-confirmed
python3 scripts/run_tests.py --mixer mixer/ --cwd app/ --unittest tests --approval A04

# any framework that writes JUnit XML (the approval names the exact command)
python3 scripts/run_tests.py --mixer mixer/ --cwd app/ --junit reports/junit.xml --framework pytest \
    --tags mixer/test-tags.json --approval A05 -- pytest --junitxml=reports/junit.xml
```

Nothing runs without an approval covering exactly this run (`engines/security.md`
section 5); a refusal exits 3 and is logged. Limits, all recorded in the run:
`--timeout` (default 1800 s: the whole process group gets SIGTERM, then
SIGKILL after `--kill-grace`; on Windows `taskkill /T /F`; processes the
tests leave behind are terminated too), `--max-log-mb` (default 50: the log
keeps its first and last halves and says how much was left out),
`--max-results-mb` (50), and `--expect-tests N`.

It saves `mixer/test-runs/<run-id>/` with `output.log`, `results.xml` and
`run.json` (command with secrets redacted and its SHA-256, folder, times,
exit code, outcome, results status, counts, verdict, fingerprints of the log,
the results and the tested code before and after, the approval, and an HMAC
signature with `--evidence-key FILE`), makes them read-only, appends the run
to the hash-chained `test-runs/ledger.jsonl`, and (with `--evidence-copy DIR`)
copies them elsewhere. Then it writes `integration-report.json` and `.md`
for this run **whatever its verdict**, so an earlier green report never
outlives a later run. A JUnit file present before the run is moved into the
run folder first: only a file written by this run counts. One run at a time
per workspace (a lock in `test-runs/`).

Verdicts, and only `passed` exits 0:

| verdict | meaning |
| --- | --- |
| `passed` | exit 0, at least one test executed, none failed, results consistent |
| `failed` | at least one test failed |
| `no-tests` | nothing executed: none discovered, or all skipped |
| `incomplete` | fewer tests executed than `--expect-tests` |
| `inconsistent` | the exit code and the results disagree, the file's totals contradict its test cases, or a test has an unknown result element |
| `invalid-results` | no results file from this run, malformed, or too large |
| `timed-out`, `interrupted` | stopped; whatever ran proves nothing |

Statuses:

| status | meaning |
| --- | --- |
| `passed` | executed, and the results file says it passed |
| `failed` | executed, and failed or errored |
| `skipped` | executed and skipped by the framework |
| `not-executed` | expected (in the tags file) but did not run |
| `unverified` | reported, but not backed by matching evidence |

Tag tests so results map to features. In unittest, use the docstring:

```python
def test_assignment_notifies_assignee(self):
    """features: M04, M10, M11
    acceptance: AC04
    expect: the assignee gets one in-app notification and one queued email
    level: interaction"""
```

For other frameworks, a tags file:
`{"tests": {"<test id>": {"features": ["M04"], "acceptance": ["AC04"], "expect": "...", "level": "api"}},
"expected_tests": ["<test id>", ...]}`.

### verify_tests.py

```bash
python3 scripts/verify_tests.py mixer/ [--rerun [--approval A06]] [--update-baseline]
                                       [--evidence-key FILE] [--evidence-copy DIR]
```

A result counts only when the report's execution block matches `run.json`
(including outcome, verdict and the run record's own fingerprint), the run
is in the ledger with an intact chain, the log and results files match
their fingerprints, re-reading the results gives the same counts and
verdict, the verdict is `passed` or `failed`, the test is in the results
file with the same status, every test in the results file is in the report
(a failing test left out is an error), and the exit code agrees. Anything
else is `unverified`. It also checks that the tested code has not changed
since the run (a fingerprint of the run's folder), regressions against
`mixer/test-baseline.json`, that every acceptance criterion in
`design/prd.md` has a verified passing test, and that every decision in
`compat/resolutions.json` with `"verified_by": ["AC03", "test_name"]` has
those tests passing.

What fingerprints can and cannot do: they detect a change relative to a
fingerprint you already trust. Editing one file is caught; rewriting the
files, `run.json`, the report and the whole ledger consistently is not,
unless the runs were signed with an `--evidence-key` the writer of the
forgery did not have, or compared with an `--evidence-copy` kept out of
its reach. None of this shows the evidence was genuine in the first place.
`--rerun` executes the recorded run again under an approval (the original
one if still valid, otherwise `--approval`) and compares: that is the
strongest proof. `--update-baseline` saves the verified statuses after a
clean verification.

## Integration testing

Use the target project's own test framework. Write tests as each slice is
built, then run the full set.

| level | what to prove |
| --- | --- |
| unit / feature | each kept feature does what its report and the PRD say, including business rules |
| interaction | features that touch each other work together (assigning a task sends one notification per chosen channel) |
| api | every endpoint: status codes, validation, response shape, error format, auth required |
| database | constraints, foreign keys, cascades, unique keys, migrations from empty, migrated data checks |
| auth / authorization | sign in and out, expiry, wrong password, every role and permission including denials, a second user cannot see the first user's data |
| dependency | the app starts and runs with exactly the declared dependencies; nothing relies on an undeclared package |
| navigation / form / error | routes, required fields and limits, double submit, external failures, missing records |
| journey | the core loop and each merged workflow end to end (a real browser where the project can install one; otherwise HTTP). v2.2 workspaces need at least one passing journey test: unit tests can all pass while the workflow is broken |
| regression | every PRD acceptance criterion, and every previously passing test |

Each retained feature maps to its tests through the tags; the report shows
the map, and the merge plan's `validation` must agree with it. If something
cannot be tested here (real email delivery, live payments), leave it out of
the passing set and list it under "Not testable here" for the user.

## Fix loop

1. Read the failure and find the cause.
2. Fix it, add or adjust a test that would have caught it.
3. Run the failing tests, then the full suite, with `run_tests.py`.
4. `verify_tests.py`; when clean, `--update-baseline`.

Then:

```bash
python3 scripts/validate_project.py mixer/ --phase integration
```

When it passes, update the merge plan's `validation`, set `integration` to
`done`, checkpoint, and give the final summary from `SKILL.md`. Passing
checks are evidence that the tested behaviour works, not that the app is
production-ready.
