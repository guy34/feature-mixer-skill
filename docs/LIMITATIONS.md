# Limitations and unimplemented features

What Feature Mixer 2.2 does not do, or does only approximately. Read this
before relying on it for real work. Each item says whether 2.2 changed it.

## Approvals and evidence

- **An approval record is not proof that a human agreed.** `run_tests.py`
  enforces that what runs is exactly what an approval names, within its
  expiry and use limit, and logs every attempt. The record and the log live
  in the workspace, so an agent that ignores the rules could write a record
  itself. (2.2: enforced scope and logging added; the consent itself is
  still a rule.)
- **Fingerprints are not authenticity.** The ledger, the report's
  fingerprint of `run.json` and the code fingerprint catch edits, reuse and
  stale evidence. A consistent rewrite of everything (files, record,
  report, whole ledger) is undetectable without an `--evidence-key` the
  writer could not read or an `--evidence-copy` out of its reach. A test
  asserts this limit, so it cannot silently change. `--rerun` (with
  approval) is the real proof, and it re-runs only unittest-harness runs
  automatically.
- **Tests run with the code under test.** A test can tamper with the
  harness's results in its own process. Isolation and a rerun are the answer.
- **Process termination.** Processes that leave the test's process group
  (`setsid`) are not killed. On Windows, `taskkill /T` reaches only processes
  still linked to the test; job objects are not used.
- **The scripts cannot read code.** They check that claims are structured,
  linked and consistent, not that Claude understood a feature correctly.
- **Capability records are self-reported for Claude's own tools.**

## Security scanning

- **Pattern-based.** Known false negatives: secrets assembled with string
  formatting or at run time, encodings other than base64, instructions in
  images or other languages, instructions phrased as ordinary prose. Known
  false positives: prompt discussion in AI-related code, documentation
  examples, test fixtures, random-looking identifiers (low-severity
  `possible-secret`). On the Python standard library (27,847 files) it
  reported 6 instruction-text, 3 secret and 68 low-severity possible-secret
  findings, all false positives or documentation examples. (2.2: many more
  variants detected, instruction false positives down from 35.)
- **Descriptor-safe walking is POSIX only.** On Windows the scanner and
  indexer use `os.walk` with link checks; a file swapped for a link between
  the check and the open is not caught there. Tested for parity on Linux,
  not run on Windows.
- **"Scan before reading" is an instruction, not a lock.**
- **No sandbox of its own**, and no security review of the built app.

## Analysis

- **Static import analysis is evidence.** Python is parsed with `ast`; JS/TS,
  Go, Rust and Java are read by pattern; other languages are listed as not
  supported. Plugins, configuration-loaded packages and computed imports
  are not seen; "possibly unused" is said only with full coverage. (2.2:
  `ast`, aliases, workspaces, dynamic imports, coverage.)
- **Version ranges** are exact for npm, Cargo, Poetry and PEP 440 release
  versions. Pre-releases are read as their release version, environment
  markers are not evaluated, and `!=` excludes only exact versions. Each of
  these is reported as uncertain. Go modules use minimal version selection
  and are not range-checked. (2.2: replaces the major-version heuristic.)
- **Meaning needs facts.** The checker compares descriptions, enums, units,
  delete policies and relations only when the source reports record them.
  Descriptions are compared by shared words, which is crude. Synonym prompts
  come from a fixed list and field overlap. A decision is always the user's.
- **Vulnerabilities need a tool run** (npm audit, pip-audit, osv-scanner).
- **Closed products**: their backend is documented or inferred, never
  observed (2.2: enforced).

## Building and testing

- **The build is Claude's work.** Quality depends on the model and the size
  of the job.
- **Instruction-only rules.** Changing requirements, long sessions,
  half-applied migrations, proprietary services and API response samples
  are handled by instructions that the scripts cannot fully enforce
  (`docs/WORKFLOW-REVIEW.md` marks which).
- **Browser end-to-end tests** run only where a browser driver can be
  installed (with approval); otherwise journeys are tested over HTTP.
- **Real integrations** are not testable unless the user connects them.

## Not implemented

- Automatic re-run of non-unittest test runs inside `verify_tests.py`.
- Job objects on Windows; cgroup-based process containment on Linux.
- Signatures that prove who granted an approval (for example, approvals
  signed by a key only the user holds).
- Screenshot or visual comparison between source screens and the new app.
- Automatic creation of containers or virtual machines; deployment automation.

## Benchmarks

- **Small, fictional scenarios.** 16 scenarios, up to about 1,100 files. They
  test the workflow and its honesty, not real-world scale or messiness.
- **Keyword matching** in `score.py` can miss a correct answer worded
  differently, or credit a wrong one that uses the right words.
- **Same author.** The answer keys, the hidden tests, the reference and
  naive builds and the skill were written by the same author. The hidden
  tests are shown to discriminate (they pass on a correct build and fail on a
  naive one), and runs never see keys or hidden tests. That shows the tests
  can tell a good build from a bad one; it does not make them independent.
- **Few runs.** See `benchmarks/RESULTS.md` for how many runs each number
  rests on. Model output varies.
- **Windows was not tested.**
