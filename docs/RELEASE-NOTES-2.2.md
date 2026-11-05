# Feature Mixer 2.2.0: engineering hardening

Every weakness reported against 2.1.0 was first reproduced by a deterministic
probe: 34 of 35 attacks succeeded. Each was then fixed and covered by tests.
All 35 probes are now defended, and the probes gate future releases.

## Highlights

- **Approvals that bind.** `scripts/approvals.py` records an approval for
  exactly one command in one folder, with an expiry and optional use limit.
  `run_tests.py` refuses everything else, runs nothing, and logs every
  attempt with secrets redacted.
- **No more false greens.**
  - Timeouts stop the whole process tree.
  - Every run gets a verdict, and only `passed` exits 0. Zero tests, a
    timeout, an exit code that disagrees with the results, and stale,
    malformed or self-contradicting result files all prove nothing.
  - A report is written for every run, so an old green report never
    outlives a failed run.
- **Tamper-evident evidence.** A hash-chained run ledger, a fingerprint of
  the tested code, read-only evidence files, one run at a time, and optional
  HMAC signing and an external copy. The limits are stated: fingerprints
  detect change, they do not prove the evidence was genuine.
- **A harder scanner.**
  - No link-following, even when a file is swapped mid-scan.
  - Named pipes are never opened.
  - It detects injected text split across lines, hidden in HTML, in base64,
    or disguised with zero-width or full-width characters.
  - It finds secrets in connection strings, in base64, or split into pieces,
    and documented placeholders are recognised as such.
  - It flags `.envrc`, VS Code folder-open tasks, dev-container commands and
    git `core.fsmonitor`.
  - Nothing it skips goes unreported.
  - On the Python standard library it runs as fast as 2.1, with
    instruction-text false positives down from 35 to 6.
- **A compatibility engine that reads ranges and meaning.**
  - Real version-range arithmetic for npm, Cargo, Poetry and PEP 440,
    across five manifest types.
  - Python imports parsed with `ast`; JS/TS aliases, workspaces and dynamic
    imports resolved.
  - Packages are never called unused without full import coverage.
  - Same-named entities that mean different things, and different names for
    the same thing, go to the user for a decision.
  - It compares enums, nullability, uniqueness, units, time zones, delete
    policies, cardinality, tenancy, identity linking, role mapping,
    idempotency and API conventions.
- **Decisions stay decided.** Phase approvals record what was approved, and
  a later change needs a new approval. Builds need a passing end-to-end
  journey test. A feature from no source must be one the user asked for.
  Plan mode cannot claim a build.
- **Better benchmarks.** 16 scenarios, with answer keys kept apart from the
  inputs and fake credentials generated at run time. Six integration
  scenarios (auth, tenancy, business rules, payments, files, APIs) have
  hidden tests shown to pass on a correct build and fail on a naive merge.
  The scoring penalises fabrication, unsafe execution and false claims of
  success, and repeated runs are summarised with their reproducibility.

## Compatibility

v2.0 and v2.1 workspaces keep validating, with the same verdicts as before.
Two changes apply to every workspace because they concern running code now:
running tests needs a scoped approval (`approvals.py grant`), and runs
recorded by the 2.2 runner follow the 2.2 evidence rules. Set
`"format": 4` to adopt every 2.2 check.

## Verified on

Linux, Python 3.8 to 3.13 (the whole suite on each), and
`claude plugin validate`. **Windows and macOS were not run.**

Full details: `CHANGELOG.md`, `docs/ENGINEERING-REPORT-2.2.md`,
`docs/TESTING-REPORT.md`, `benchmarks/RESULTS.md`, `docs/LIMITATIONS.md`.
