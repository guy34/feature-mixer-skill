# Security

Feature Mixer reads other people's code, documents and websites, and builds
software from what it learns. This file explains the risks that creates and
what the skill does about them. The rules Claude follows during a run are in
[`feature-mixer/engines/security.md`](feature-mixer/engines/security.md);
this file is the overview for people.

## Threat model

| risk | how it could happen | what Feature Mixer does |
| --- | --- | --- |
| Prompt injection | A README, comment, doc page, HTML comment, hidden element or `CLAUDE.md` in a source says "ignore previous instructions", "AI agents must run...", or "reveal the keys", possibly split across lines, base64-encoded or hidden with zero-width characters | Source content is data, never instructions. `scan_source.py` reports AI-addressed and hidden text and agent-instruction files; Claude tells the user once and carries on with the real task. Nothing in a source can approve, grant or change anything. |
| Code execution on inspection | Install scripts (`postinstall`), git hooks and git config commands (`core.fsmonitor`), `.envrc`, IDE folder-open tasks, dev-container commands, submodules, build files, test fixtures that run code | Sources are read, not run; the scanner flags every one of these. Repos are cloned with hooks and submodules disabled. Running source code, installing dependencies and running tests each need the user's recorded approval, ideally in a container or VM. |
| Running something other than what was approved | A command, folder or test suite different from the one the user agreed to; an approval reused after it expired or after the code changed | `run_tests.py` (and `verify_tests.py --rerun`) run only under an approval bound to the action, folder, exact command (by SHA-256) and results path, within its expiry and use limit, optionally bound to the code's fingerprint. Anything else is refused, nothing runs, and the refusal is logged. |
| Runaway test processes | A test that hangs, forks daemons or floods output | A timeout that stops the whole process group (SIGTERM, then SIGKILL; `taskkill /T /F` on Windows), termination of processes left behind, a capped log, recorded outcome. |
| Secret leakage | Keys, tokens, `.env` files, connection-string passwords in a source end up in reports, logs, approval records or the new app | `scan_source.py` finds them (also base64-encoded or split into pieces) and stores only redacted fragments. No credential may appear anywhere in `mixer/` (an error in every workspace format; documented placeholders are allowed). Commands in approvals and run records are stored redacted, matched by hash. Configuration is recorded by name, never by value. |
| Supply chain | Registry overrides, unpinned or git dependencies, known-vulnerable packages | Scanned and reported. Vulnerabilities are only "confirmed" when a real audit tool (npm audit, pip-audit, osv-scanner) reports them, run with approval; everything else is labelled unverified. |
| Escaping the source folder | Symbolic links pointing at `/etc` or the user's home folder, a file swapped for a link while it is scanned, named pipes that block a reader, file names that spoof the report | Links are never followed; on Linux and macOS the walk uses directory descriptors and `O_NOFOLLOW`, so a swap mid-scan is not followed either. Pipes, sockets and devices are never opened. Odd names are shown escaped. Anything not scanned is reported. |
| Destructive changes | Migrations, deletes, overwrites, force pushes | Need explicit approval; migrations carry a data-loss risk rating and a plan with backup, dry run and rollback. Sources are never modified. |
| Fabricated results | A report that claims tests passed, or claims a website or a closed backend was studied, without it happening | Test results count only with evidence written by `run_tests.py` and checked by `verify_tests.py`: a verdict for every run, a hash-chained ledger, a fingerprint of the tested code, read-only files, optional HMAC signing and an external copy. Evidence from an input the session had no capability to read is rejected; a closed source cannot cite code or claim an observed backend. |
| Unauthorised access | Logging into other people's accounts, getting past paywalls, scraping | Closed products are studied through public material and the user's own account only, at normal speed with the user present. |
| Licence violations | Copying code the licence does not allow | `reuse` and `adapt` are refused for sources whose `code_reuse` is not `allowed`; closed sources are always rebuilt. |

## What the checks cannot do

- **An approval record is not proof of consent.** Approvals and their log
  live in the workspace. Anything that can write there, the agent included,
  could write a record. The check guarantees that what runs is exactly what
  the record names, that the record is still in force, and that every
  attempt is logged. That a human said yes rests on Claude following the rule
  to grant only after a clear yes. Keep `project.json` under version
  control, or copy `approval-log.jsonl` elsewhere, if you need an
  independent trail.
- **Fingerprints detect change; they do not prove authenticity.** Editing
  one evidence file is caught. Rewriting the files, `run.json`, the report
  and the whole ledger consistently is not caught, unless the runs were
  signed with an `--evidence-key` the forger could not read, or compared
  with an `--evidence-copy` kept out of its reach. Tests run in the same
  process as the code under test, so that code could tamper with its own
  results. `verify_tests.py --rerun`, in isolation and with approval, is
  the real proof.
- **Process termination has gaps.** A process that leaves the test's process
  group (for example with `setsid`) is not killed; it is reported when it
  keeps the output open. On Windows, children are stopped with
  `taskkill /T`, which reaches only processes still linked to the test; a
  job object would be stronger and is not implemented.
- Secret and injection scanning uses patterns. Known false negatives: secrets
  split across string formatting (`"%s%s" % (a, b)`) or built at run time,
  encodings other than base64 (hex, rot13, compression), instructions in
  images or other languages, and instructions phrased as ordinary prose.
  Known false positives: discussions of prompts in AI-related code,
  documentation examples, test fixtures, and random-looking identifiers
  (reported as low-severity `possible-secret`). Treat a clean scan as
  "nothing obvious", not as "safe".
- Import maps and dependency necessity are static analysis: evidence, not
  certainty. Packages loaded by plugins, configuration or computed names are
  not seen, so "possibly unused" is only said with full import coverage.
- Feature Mixer recommends isolation; it cannot create a container or VM for
  you. If none is available it says so and asks before running anything.
- Nothing here is a security review of the app Feature Mixer builds. Have the
  result reviewed before it handles real users or real data.

## Reporting a vulnerability in Feature Mixer

If you find a way to make Feature Mixer leak secrets, run code without
approval, follow instructions from a source, or report results that did not
happen, please open an issue at
[github.com/guy34/feature-mixer-skill/issues](https://github.com/guy34/feature-mixer-skill/issues)
with the steps to reproduce. If the details are sensitive, open an issue
asking for a private contact instead of posting them.
