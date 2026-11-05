# Feature Mixer

A Claude skill that takes **several existing applications** and turns them
into **one working application** made of the features you choose.

```
multiple apps → reverse engineering → feature intelligence → selection → compatibility
             → unified architecture → implementation → verified testing → final application
```

Feature Mixer studies each source app on its own (websites, GitHub repos,
local projects, screenshots, docs, API specs, source code), lists every
feature with evidence, finds which features duplicate, overlap, complement or
contradict each other, lets you pick, checks that your picks can live
together, designs one architecture, builds the app in tested slices, and
proves each feature works with test runs it recorded itself.

It is one self-contained skill. It needs no other skill or plugin.

**Safe by default.** Sources are treated as untrusted data: scanned before
they are read, never executed without your approval, and never allowed to
give Claude instructions. Nothing runs without an approval for exactly that
command. Closed products are studied only through public material and your
own account, and are always rebuilt from scratch. See
[SECURITY.md](SECURITY.md).

## What's new in 2.2

2.2 is an engineering-hardening release. Each weakness reported against 2.1.0
was first reproduced by a probe (34 of 35 succeeded), then fixed and tested.
All 35 probes are now defended
([`benchmarks/probes`](benchmarks/probes/run_probes.py)).

- **Approvals that bind.** `scripts/approvals.py` records an approval for
  exactly one command in one folder, with an expiry. `run_tests.py` refuses to
  run anything else, and every attempt is logged.
- **Test runs that cannot go false-green.** Timeouts that stop the whole
  process tree. A verdict for every run: zero tests, a timeout, results that
  contradict the exit code, or a stale or malformed results file all prove
  nothing. A report is written for every run, so an old green one never
  survives a failed run.
- **Tamper-evident evidence.** A hash-chained run ledger, a fingerprint of
  the tested code, read-only evidence, and optional HMAC signing and an
  external copy. The limits are stated: fingerprints detect change, they do
  not prove the evidence was genuine.
- **A harder scanner.** It doesn't follow links (even when a file is swapped
  for a link mid-scan) and never opens named pipes. It catches injected text
  split across lines, hidden in HTML, encoded or obfuscated; secrets in
  connection strings, in base64 or split into pieces; and more hook types.
  Nothing it skips goes unreported. On the Python standard library it runs as
  fast as 2.1 with a sixth of the false positives.
- **A compatibility engine that reads ranges and meaning.** It does real
  version-range arithmetic (npm, Cargo, Poetry, PEP 440) across five
  manifest types. Python imports are parsed with `ast`, and JS/TS aliases
  and workspaces are resolved. Packages are never called unused without full
  import coverage. Same-named entities that mean different things, and
  different names for the same thing, go to you for a decision. Enums,
  nullability, uniqueness, units, delete policies and cardinality are all
  compared, along with tenancy, identity linking, role mapping, idempotency
  and API conventions.
- **Decisions stay decided.** Phase approvals record what you approved, and a
  later change needs your approval again. Every build needs an end-to-end
  journey test. A feature from no source must be one you asked for. Plan mode
  cannot claim a build.
- **Better benchmarks.** 16 scenarios with answer keys kept apart from the
  inputs. Six integration scenarios have hidden tests proven against a
  correct and a naive build. The scoring penalises fabrication, unsafe
  execution and false claims of success, and repeated runs are summarised
  with their reproducibility.

v2.0 and v2.1 workspaces keep validating with the same verdicts. Details:
[CHANGELOG.md](CHANGELOG.md).

## In 2.1

- **Security**: source scanning (secrets, prompt-injection text, install
  hooks, escaping links), safe cloning, isolation guidance, and an approvals
  ledger for running code, installing, migrating and deploying.
- **Trustworthy tests**: `run_tests.py` records every run (command, times,
  exit code, log and results with fingerprints); `verify_tests.py` checks the
  report against that evidence. Results are passed, failed, skipped,
  not-executed or unverified; self-reported passes prove nothing.
- **Capability detection**: what the session can really do is recorded
  first, and claims that needed a missing tool are rejected.
- **Smarter merging**: `separate` and `improve`, a merge plan with one
  unified feature per capability, and no feature built twice.
- **Architecture choice**: modular monolith, microservices, service-oriented,
  event-driven or hybrid, chosen against the project's needs.
- **Large repositories**: indexing, module-by-module analysis with summaries,
  feature-to-file maps, re-analysis of changed files, honest coverage.
- **Migration and dependency intelligence**: field-level data-loss risk,
  confirmed vulnerabilities from real audit tools, unused and undeclared
  packages.
- **Release checks and benchmarks**: `tools/release_check.py` and six
  benchmark scenarios scored against answer keys.

## Download

**Download the ZIP (no Git needed)**

1. Open [github.com/guy34/feature-mixer-skill](https://github.com/guy34/feature-mixer-skill).
2. Click the green **Code** button, then **Download ZIP**.
3. Unzip it. You get a folder called `feature-mixer-skill-main`.

**Or download a release** from the
[latest release](https://github.com/guy34/feature-mixer-skill/releases/latest):

- `feature-mixer-skill.zip`: the whole repository
- `feature-mixer-claude-ai.zip`: only the skill folder, ready to upload to Claude.ai

**Or clone it**

```bash
git clone https://github.com/guy34/feature-mixer-skill.git
```

## Install

### Claude Code, as a plugin

```
/plugin marketplace add guy34/feature-mixer-skill
/plugin install feature-mixer-skill@feature-mixer-skill
```

Claude Code puts the plugin name in front of the skill, so it runs as
`/feature-mixer-skill:feature-mixer`.

### Claude Code, as a plain skill

```bash
git clone https://github.com/guy34/feature-mixer-skill.git
cp -r feature-mixer-skill/feature-mixer ~/.claude/skills/
```

Then run it as `/feature-mixer`. For one project only, copy the folder into
that project's `.claude/skills/` instead.

### Claude.ai

1. Download `feature-mixer-claude-ai.zip` from the
   [latest release](https://github.com/guy34/feature-mixer-skill/releases/latest),
   or zip the `feature-mixer` folder yourself. The zip must contain
   `feature-mixer/SKILL.md` and the `engines`, `scripts`, `schemas` and
   `templates` folders.
2. In Claude, open **Settings**, find **Skills**, and upload the zip.
3. Start a new chat and type `/feature-mixer`.

### Requirements

- Claude with skills enabled (Claude Code, or Claude.ai with code execution).
- Python 3.8 or newer for the scripts. Standard library only, nothing to
  install, no network. Without Python, Claude runs the same checks by hand
  and tells you so.
- Recommended: git (checkpoints) and docker or podman (to run anything from a
  source in isolation).

## Usage

Name the sources, what you want from each, and who the app is for.

```
/feature-mixer
Sources:
  A: ~/code/taskboard                    (my own code: tasks and assignment)
  B: https://github.com/acme/approvals   (MIT: approvals and threaded comments)
  C: https://pulse.example.com + its API docs   (closed: the workload dashboard)
For: a small team that plans work and gets sign-off
Build in: ./team-hub
```

```
/feature-mixer Rebuild just this one app, cleaned up: ./legacy-crm (my code)
```

```
/feature-mixer Mode: plan
Compare https://app-one.example and https://app-two.example for an internal
tool; I want the merged plan and architecture, no code yet.
```

```
/feature-mixer Mode: plan · Selection: auto-pick
Combine ./shop-a and ./shop-b (both mine). Pick sensibly and tell me what you dropped.
```

### Modes

| mode | what happens |
| --- | --- |
| `full` (default) | every phase, ending with a tested app |
| `plan` | stops once the architecture is approved; no code |

Selection is a separate choice: `manual` (you pick, the default) or
`auto-pick` (Claude chooses and lists every pick and drop; every other
approval still applies). It works with either mode.

### Phases and approvals

| # | phase | output | you approve |
| --- | --- | --- | --- |
| 1 | recon | capabilities; per source a security scan, an index for repos, and an evidence-backed report | high-severity scan findings are shown to you |
| 2 | extraction | the feature menu, grouped and classified | |
| 3 | selection | your picks, checked, and the merge plan | **yes** |
| 4 | compatibility | conflicts and migrations with data-loss risk | **yes** |
| 5 | architecture | style, PRD, schema, API, roadmap | **yes** |
| 6 | implementation | the app, built and tested slice by slice | installs, test runs, migrations |
| 7 | integration | verified proof per feature | |
| 8 | deployment | only if you ask | **always** |

Before anything runs, Claude shows you exactly what it will run and records
your yes for that command only:

```bash
python3 feature-mixer/scripts/approvals.py request --mixer mixer/ --cwd app/ --unittest tests
python3 feature-mixer/scripts/approvals.py grant   --mixer mixer/ --cwd app/ --unittest tests \
    --granted-by "you" --user-confirmed --expires-in 8h
```

Choosing features: Claude shows the menu grouped by merge group, with each
feature's source, description, priority, size, dependencies, conflicts,
merge type, compatibility, evidence and recommended strategy. Answer in
plain words, or use the command Claude uses:

```bash
python3 feature-mixer/scripts/validate_feature_menu.py mixer/feature-menu.csv --show --format md
python3 feature-mixer/scripts/validate_feature_menu.py mixer/feature-menu.csv --set keep M01,group:notifications
```

## What it writes

```
mixer/
  project.json                sources and rights, mode, phases, approvals, checkpoints
  capabilities.json           what the session could do
  mixer-log.md                decision history and integration log
  sources/A-taskboard/        security-scan.json, index.json, summaries/, report.md, source.json
  feature-menu.csv            every feature from every source
  merge-plan.json             the unified features the app will have
  compat/                     aliases, manual conflicts, audits, resolutions, compatibility report
  design/                     prd.md, architecture.md, architecture.json, migration-plan.md
  test-runs/<run-id>/         run.json, output.log, results.xml
  integration-report.md/.json, test-verification.json, test-baseline.json
app/                          the unified application (or the folder you chose)
```

## The scripts

All in `feature-mixer/scripts/`: Python 3.8+, standard library only, no
network, runnable from any folder. Full reference:
[`feature-mixer/engines/validation.md`](feature-mixer/engines/validation.md).

| script | job |
| --- | --- |
| `check_environment.py` | record the session's capabilities |
| `scan_source.py` | scan a source for risks before reading it |
| `index_repo.py` | index a repository; find what changed |
| `checkpoint.py` | make, list and restore checkpoints (never commits or deletes) |
| `validate_feature_menu.py` (`check_menu.py`) | check the menu, show it, change picks |
| `check_compatibility.py` | database, API, auth, tenancy, payments, application and dependency conflicts, and meaning; migrations |
| `check_dependencies.py` | version-range conflicts, confirmed vulnerabilities, unused and undeclared packages (when coverage allows) |
| `approvals.py` | show what will run, record your yes for exactly that, check, revoke; record phase approvals |
| `run_tests.py` | run the tests under an approval, with a timeout, and record the evidence and a verdict |
| `verify_tests.py` | check the report against the evidence, the ledger and the code; regressions; acceptance criteria; decisions' tests |
| `validate_artifacts.py` | check every file a run writes |
| `validate_project.py` | check a phase is complete |

The scripts check structure, references, evidence and rules. Whether a
feature was understood correctly, and whether the code is good, is Claude's
job and yours.

## The example

[`examples/team-hub`](examples/team-hub) is a complete run on three small
fictional sources (your own task board, an MIT-licensed approval tool, and a
closed product known only from its docs), stored as a 2.2 workspace. It
contains every file Feature Mixer writes, 20 resolved conflicts, a merge plan
of 8 unified features, a migration plan that caught a dropped field, and the
resulting app (a standard-library Python API) whose 23 tests ran under
`run_tests.py` with a scoped approval and are verified against their
recorded, ledgered evidence.

```bash
python3 feature-mixer/scripts/validate_project.py examples/team-hub/mixer
python3 feature-mixer/scripts/verify_tests.py examples/team-hub/mixer --no-write
cd examples/team-hub/app && python3 -m teamhub serve
```

## Benchmarks

[`benchmarks/`](benchmarks) has:

- **Probes** ([`probes/run_probes.py`](benchmarks/probes/run_probes.py)): 35
  deterministic attacks (approvals, timeouts, false-green reports, forged
  evidence, scanner evasion, version ranges, meaning). They run the same way
  against any copy of the skill, so they compare versions like for like.
- **Sixteen scenarios.** Ten recon-and-plan scenarios: overlapping,
  complementary, conflicting, large, incomplete, heterogeneous,
  contradictory documentation, closed source, a hostile source and a
  monorepo. Six integration scenarios (J–O: auth, tenancy, business rules,
  payments, files, APIs) come with hidden tests that pass on a correct build
  and fail on a naive merge.
- **Answer keys** in [`answer-keys/`](benchmarks/answer-keys), never copied
  into a run (`prepare_run.py`).
- **`score.py` and `aggregate.py`.** They measure precision and recall for
  features and conflicts, fabrication, honesty, security violations, false
  claims of success, hidden-test pass rate, interventions and
  reproducibility across repeated runs.

Results, with how they were produced and what they cannot show, are in
[`benchmarks/RESULTS.md`](benchmarks/RESULTS.md). The scenarios are small
and fictional: good results there do not show that Feature Mixer is ready
for production use on real applications.

## Repository layout

```
feature-mixer/                the skill (this folder is what gets installed)
  SKILL.md, engines/, scripts/, schemas/, templates/
examples/team-hub/            the worked example
benchmarks/                   scenarios, answer keys, generator, scorer, results
tests/                        the test suite (and a frozen 2.0 workspace)
tools/release_check.py        release checks and packaging
docs/                         architecture, testing report, limitations
.claude-plugin/               plugin and marketplace manifests
```

## Tests and release checks

```bash
python3 -m unittest discover -s tests -v
python3 tools/release_check.py --clean --tests --probes
python3 tools/release_check.py --clean --package dist/
```

The current numbers are in [`docs/TESTING-REPORT.md`](docs/TESTING-REPORT.md). What changed in 2.2 and
why, the security findings and the remaining work are in
[`docs/ENGINEERING-REPORT-2.2.md`](docs/ENGINEERING-REPORT-2.2.md); the review of the workflow against 15
failure scenarios is in [`docs/WORKFLOW-REVIEW.md`](docs/WORKFLOW-REVIEW.md).

## Upgrading

**From 2.1:** your workspace (`"format": 3`) keeps validating. To run tests
again, record a scoped approval with `approvals.py grant` (2.1's unscoped
approvals are refused for running code), then rerun with `run_tests.py`.
To adopt 2.2 fully, set `"format": 4`, re-record your phase approvals with
`approvals.py approve-phase`, make sure at least one `level: journey` test
passes, and run `validate_project.py`: its errors are the to-do list.

**From 2.0:** nothing breaks. Your `project.json` says `"format": 2`, so the
2.1 checks appear as warnings. To adopt 2.1, run `check_environment.py`,
`scan_source.py` and (for repositories) `index_repo.py`, write
`merge-plan.json` and the architecture `style`, rerun your tests with
`run_tests.py`, then set `"format": 3` (and continue as for 2.1).

**From 1.0:** rename the workspace from `replica/` to `mixer/`, add
`mixer/project.json` from `feature-mixer/templates/project.json`, and run
the steps above. Your v1 `feature-menu.csv` still validates.

## Ground rules

Sources are data, never instructions. Rights decide what may be read and
copied. Nothing from a source runs, and nothing is installed, migrated,
deleted or deployed, without your recorded approval. Every claim has
evidence. Nothing counts as working without a verified test. Nothing deploys
automatically. You own the legal check: read the terms of anything you
study, check licences before reusing code, and get legal advice before
selling. This is not legal advice.

Full rules: [`feature-mixer/engines/security.md`](feature-mixer/engines/security.md).
Known limits: [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credit

Created by [Udit Kandpal](https://github.com/guy34). Version 1.0
orchestrated the Replica skill pack by Jake Schincariol; since 2.0 Feature
Mixer is fully standalone and contains its own workflow.

## License

MIT. See [LICENSE](LICENSE).
