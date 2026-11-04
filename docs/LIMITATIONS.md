# Limitations and unimplemented features

What Feature Mixer 2.1 does not do, or does only approximately. Read this
before relying on it for real work.

## Evidence and verification

- **Fingerprints are not authenticity.** `verify_tests.py` proves an
  integration report matches its recorded log and results. Someone who
  forges the log, the results and the run record consistently will pass.
  `verify_tests.py --rerun` (which runs code, so needs approval) is the real
  proof, and it can only re-run unittest-harness runs automatically; other
  frameworks must be re-run with `run_tests.py` and compared.
- **The scripts cannot read code.** They check that claims are structured,
  linked and consistent, not that Claude understood a feature correctly.
- **Capability records are self-reported for Claude's own tools.** A script
  cannot see whether a browser or fetch tool exists; Claude records it. The
  validators then hold every claim to that record.

## Security

- **Pattern-based scanning.** Secret and prompt-injection detection uses
  patterns: it misses unusual secrets and obfuscated instructions, and flags
  some harmless text.
- **No sandbox of its own.** Feature Mixer recommends a container or VM and
  asks before running anything, but cannot create isolation itself.
- **No security review of the built app.** Passing tests are not a security
  assessment.
- **"Scan before reading" is an instruction, not a lock.** Nothing stops a
  session from opening a source file before `scan_source.py` runs; one
  benchmark run did exactly that. The scan still runs and its findings still
  apply, but the order is up to Claude following the skill.

## Analysis

- **Approximate import maps.** `index_repo.py` finds Python and
  JavaScript/TypeScript imports with text patterns. Dynamic imports, aliases,
  other languages and build-tool path mapping are missed. Dependency
  necessity built on it is a suggestion.
- **Major-version heuristic.** Dependency conflicts compare major versions;
  complex ranges are simplified, and unreadable specs are skipped.
- **Name-based conflict detection.** Entities, endpoints and fields match by
  name (plus the aliases Claude writes). Concepts with unrelated names need
  aliases or manual conflicts.
- **Vulnerabilities need a tool run.** Without npm audit, pip-audit or
  osv-scanner output (which needs network and approval), no vulnerability is
  confirmed, and Feature Mixer says "not checked".
- **Closed products.** Only public material and the user's own account are
  studied, so their back end, data model and limits are mostly documented or
  inferred, never observed.

## Building and testing

- **The build is Claude's work.** Quality depends on the model and the size
  of the job. Large apps are built slice by slice over many steps and may
  need several sessions.
- **Browser end-to-end tests** run only where the project can install a
  browser driver (with approval). Otherwise journeys are tested over HTTP.
- **Real integrations** (email delivery, payments, push) are listed as not
  testable unless the user connects real services.

## Not implemented

- Automatic re-run of non-unittest test runs inside `verify_tests.py`.
- Screenshot or visual comparison between source screens and the new app.
- Language-aware parsing (abstract syntax trees) for imports and data models.
- Automatic creation of containers or virtual machines.
- Deployment automation (deliberately: deployment is manual and approved).

## Benchmarks

- **Small, fictional scenarios.** They test the workflow and its honesty, not
  real-world scale or messiness. Good scores there are not evidence of
  production readiness.
- **Keyword matching.** `score.py` matches features and conflicts by
  keywords and kinds; it can miss a correct answer worded differently, or
  credit a wrong one that uses the right words.
- **Answer keys were written by the same author as the skill.** The runs
  were done by separate agents that were told not to read the answer keys,
  but they shared a machine with them; independence is by instruction, not
  enforced.
- **One run per scenario.** Model output varies; these are single samples.
