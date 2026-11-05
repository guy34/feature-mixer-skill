# Feature Mixer 2.2: engineering, security and remaining-work report

This report covers the 2.2 hardening work: what was wrong in 2.1.0, why, what
changed, how it is tested, and what is still not solved. It sits alongside
three companions:

- the test numbers in [`TESTING-REPORT.md`](TESTING-REPORT.md), generated
  from real runs;
- the benchmark comparison in [`../benchmarks/RESULTS.md`](../benchmarks/RESULTS.md);
- the release notes in [`../CHANGELOG.md`](../CHANGELOG.md), and a shorter
  version for the GitHub release in [`RELEASE-NOTES-2.2.md`](RELEASE-NOTES-2.2.md).

## How weaknesses were established

Before any fix, `benchmarks/probes/run_probes.py` attacked a frozen copy of
2.1.0 with 35 deterministic probes, using fake data only. Each probe
performs one attack the way a user or an agent would and records
`vulnerable`, `defended` or `error`. Against 2.1.0, 34 were vulnerable and 1
was defended (P29, peer dependencies, by accident: 2.1 merged peer and normal
dependencies into one list). One probe was itself wrong at first: P25
originally flagged a 120-folder-deep tree that 2.1.0 handled correctly. It was
rewritten to test what actually fails, a path longer than the OS limit,
which 2.1.0 skipped without a word. The same 35 probes against 2.2.0: 35
defended.

"Verified bug" below means a probe or a test reproduced it against 2.1.0.
"Design limitation" means it is inherent to the approach and is documented
rather than fixed.

## 1. Engineering change report

### Phase 1: execution safety

| Weakness (2.1.0) | Root cause | Files changed | Fix | Tests | Result | Remaining limitation |
| --- | --- | --- | --- | --- | --- | --- |
| **P0** Tests ran with no approval, an invented one, or one for another action (P01–P03): verified | `--approval` was stored in `run.json` and never checked | `run_tests.py`, new `approvals.py` | `authorise()` before any execution: the id exists, is approved, the action is `run-tests`, not revoked; refusal exits 3 and runs nothing | `ApprovalTest` (16 tests) | P01–P03 defended | the record can be written by whoever can write `mixer/` (see section 3) |
| **P0** An approval for one command authorised another (P04): verified | approvals had a free-text `target` only | `approvals.py`, `project.schema.json` | scope: folder, harness start/top or exact argv (SHA-256; stored redacted) and JUnit path; expiry (default 8 h), `max_uses`, optional code fingerprint; unscoped v2.1 records refused for running code | `test_approval_for_another_command/folder/junit_path_or_runner`, `test_expired_approval`, `test_single_use_approval_cannot_be_reused`, `test_bound_approval_stops_when_code_changes` | P04 defended | none beyond the above |
| Rejected attempts left no trace: verified | nothing logged | `approvals.py` | `mixer/approval-log.jsonl`: every grant, acceptance, refusal and revocation, with secrets in commands redacted | `test_audit_log_redacts_secrets_in_commands`, `test_valid_approval_runs_and_is_logged` | passes | the log is append-only by convention, not by the file system |
| `verify_tests.py --rerun` executed code without a valid approval (P15): verified | rerun called `execute()` with the recorded id unchecked | `verify_tests.py` | rerun goes through the same `authorise()`; `--approval` for a new one | `test_rerun_needs_a_valid_approval` | P15 defended | |
| **P0** No timeout: a hanging suite blocked forever (P05): verified | `subprocess.run()` without `timeout` | `run_tests.py` | `Popen` in a new session / process group; `--timeout` (default 1800 s); SIGTERM then SIGKILL to the group after `--kill-grace`; `taskkill /T /F` on Windows; outcome `timed_out`, verdict `timed-out` | `test_hanging_command_is_stopped_and_recorded` | P05 defended (stops in about 3 s at `--timeout 2`) | Windows path not run |
| Grandchildren survived (P06): verified (no termination at all) | as above | `run_tests.py` | the whole group is signalled; processes left after a normal exit are terminated and recorded | `test_grandchildren_are_terminated`, `test_processes_left_after_a_normal_exit_are_terminated` | P06 defended | a process that calls `setsid` leaves the group and survives; it is reported if it keeps the output open |
| Interruption lost the record | no handler | `run_tests.py` | SIGTERM and Ctrl-C terminate the group, record outcome `interrupted`, exit 130 | `test_interruption_terminates_the_command_and_keeps_the_record` | passes | |
| Unbounded output | output written straight to a file without a limit | `run_tests.py` | `--max-log-mb` (50): first and last halves kept, omitted bytes recorded | `test_huge_output_is_capped_keeping_head_and_tail` | passes | |
| **P1** Zero discovered tests reported success (P07): verified | the harness exits 0 for an empty suite and nothing counted | `run_tests.py`, `verify_tests.py` | verdicts; `no-tests` for zero executed (none found or all skipped); empty reports prove nothing | `test_zero_tests_is_never_success`, `test_all_skipped_is_never_success` | P07 defended | |
| **P1** A failed later run left the earlier green report in place (P08): verified | the report was written only after a successful parse; errors exited before writing it | `run_tests.py` | a report is written for every run whatever its verdict, atomically | `test_malformed_junit_replaces_an_earlier_green_report` | P08 defended | |
| **P1** Non-zero exit with no failing test verified green (P09): verified | a warning, not an error | `run_tests.py`, `verify_tests.py` | verdict `inconsistent`; passes become unverified | `test_nonzero_exit_without_failures_proves_nothing` | P09 defended | |
| **P1** Suite totals contradicting the test cases accepted (P10): verified | only `<testcase>` elements were read | `run_tests.py` | totals checked per suite and for `<testsuites>`; unknown result elements make a test `unverified`; results above `--max-results-mb` not read | `test_suite_totals_must_match_cases`, `test_unknown_result_elements_are_unverified`, `test_oversized_results_are_not_read` | P10 defended | XML entity expansion relies on the expat limits of the Python in use |
| **P1** A stale JUnit file was accepted if its timestamp was refreshed (P11): verified | freshness by mtime with a 1-second allowance | `run_tests.py` | a pre-existing results file is moved into the run folder (`previous-<name>`) before the run; only a file written during the run counts | `test_stale_junit_file_is_refused` (updated: the old file is now moved aside, not refused) | P11 defended | |
| Missing expected tests | (2.1 already reported `not-executed` from tags) | `run_tests.py`, `verify_tests.py` | `--expect-tests N` (verdict `incomplete`); a failing test left out of the report is an error | `test_expected_test_count`, `test_failing_test_left_out_of_the_report` | passes | |
| **P1** Evidence reused after the code changed (P12): verified | nothing tied a run to the code it tested | `run_tests.py`, `verify_tests.py`, `approvals.py` | fingerprint of the tested folder before and after (caches, `mixer/` and the results file excluded); verification fails when it changed | `test_code_changed_after_the_run` | P12 defended | files the tests ignore but the fingerprint includes (for example a data file written later) also count as a change |
| **P1** Consistent forgery of results, run record and report verified as genuine (P13): verified | fingerprints were stored next to the files they protect | `evidence.py`, `run_tests.py`, `verify_tests.py` | hash-chained `test-runs/ledger.jsonl`; the report fingerprints `run.json`; evidence read-only; run lock; atomic writes | `test_each_file_tampered_alone`, `test_consistent_forgery_is_caught_by_the_ledger`, `test_ledger_entry_removed`, `test_evidence_reused_from_another_workspace`, `test_concurrent_run_is_refused_and_stale_lock_taken_over` | P13 defended | see the next row |
| Forgery that also rewrites the ledger (P14): design limitation | anything that can write every file can rewrite every fingerprint | `evidence.py` | optional HMAC with a key outside `mixer/`; optional external copy; the limit is stated and pinned by a test | `test_full_rewrite_without_a_key_is_a_documented_limit`, `test_full_rewrite_with_a_key_is_caught`, `test_external_copy_is_compared` | P14 defended *with a key*; without one it is undetectable, as documented | a writer who can read the key defeats it; none of this proves the evidence was genuine |

### Phase 2: source scanning

| Weakness (2.1.0) | Root cause | Files changed | Fix | Tests | Result | Remaining limitation |
| --- | --- | --- | --- | --- | --- | --- |
| A named pipe hung the scanner (P16): verified | `open()` on any directory entry | `scan_source.py`, `index_repo.py` | `lstat` first; only regular files are opened, with `O_NONBLOCK`; pipes, sockets, devices reported | `test_named_pipes_are_never_opened` | P16 defended | |
| A file swapped for a link after the check was read through the link (P17): verified | check-then-open race (`islink` then `open`) | `scan_source.py`, `index_repo.py` | `os.fwalk` with directory descriptors and `O_NOFOLLOW`; `fstat` after open must match the `lstat` | `test_a_file_swapped_for_a_link_after_the_check_is_not_read`, `test_links_out_loops_and_nesting_are_never_followed` | P17 defended | POSIX only; Windows uses the portable walker with link checks |
| Prompt-injection variants missed: hidden HTML, split lines, base64, zero-width, "reveal the secrets" (P18, 0 of 6 found): verified | single-line patterns, no normalisation | `scan_source.py` | whitespace-tolerant patterns over the whole file; HTML comments and hidden elements; base64 decoding; zero-width and full-width normalisation; chat-template tokens matched case-sensitively | `PromptInjectionTest` (7 tests) | P18 defended (6 of 6) | pattern-based: prose instructions, other languages, images and other encodings are missed |
| Secrets missed: connection strings, odd names, base64 (P19, 0 of 3): verified | strong patterns only, per line | `scan_source.py`, `mixerlib.py` | connection-string passwords, base64-decoded and split-into-pieces secrets, entropy check (low severity) | `SecretsTest` (4 tests) | P19 defended (3 of 3) | strings built with formatting or at run time are missed |
| A documented placeholder reported as a real secret (P20): verified | no placeholder notion for strong patterns | `mixerlib.py` | placeholders (AWS's `EXAMPLE` key, `${VAR}`, common defaults) are `placeholder-secret`, info only; artifacts may contain them | `test_placeholders_are_info_not_secrets`, `test_artifacts_holding_a_secret_are_rejected_but_placeholders_pass` | P20 defended | the placeholder list is heuristic |
| A secret on an AI-addressed line was copied into the finding (P21): verified | the instruction snippet was the raw line | `scan_source.py` | snippets pass through `redact_text` | `test_values_never_appear_in_the_scan_or_its_output` | P21 defended | |
| A secret at the top of an oversized file missed (P22): verified | oversized files were skipped whole | `scan_source.py` | the first `--max-file-mb` is scanned and the file reported as partially scanned | `test_very_large_file_memory_and_partial_scan` | P22 defended | content beyond the limit is not scanned (reported) |
| Auto-running hooks unflagged: `.envrc`, VS Code folder-open tasks, dev containers, git `core.fsmonitor` (P23): verified | hook list covered build and CI files only; `.git` was skipped whole | `scan_source.py` | those four (high severity) plus `build.rs`, Gradle, Maven, CMake, `pyproject.toml`, npm test hooks, `publishConfig.registry`; git config commands | `ExecutionHooksTest` (4 tests) | P23 defended | |
| `index_repo.py` read huge files whole (P24: 120 MB for a 60 MB file): verified | `f.read()` | `index_repo.py` | chunked hashing and line counting; at most `--max-text-mb` parsed | `test_very_large_file_memory_and_partial_scan` | P24 defended (4 MB) | |
| A folder too deep to open skipped silently (P25): verified | `os.walk(onerror=None)` | `scan_source.py`, `index_repo.py` | descriptor walk reaches it; unreadable parts, depth and file limits reported; `complete: false` | `test_paths_longer_than_the_os_limit`, `test_depth_limit_is_reported`, `test_file_limit_is_reported_not_silent` | P25 defended | |
| Non-UTF-8 or control-character file names unflagged, able to spoof output (P26): verified | raw names printed | `scan_source.py` | `unusual-filename` findings; names shown escaped; stdout with `backslashreplace` | `test_unusual_names_are_escaped_and_flagged` | P26 defended | |
| Nested repositories' manifests read as the source's (found while building test P): verified | manifest walk ignored repository boundaries | `check_dependencies.py`, `index_repo.py` | folders with their own `.git` are boundaries (reported, not read; `--include-nested` for the index) | `test_unrelated_nested_repository_is_a_boundary`, `test_dependencies_across_package_managers_and_the_internal_react_conflict` | passes | |
| Manifest search stopped at depth 3 silently: verified | hard-coded limit | `check_dependencies.py` | depth 6 by default; the limit is reported under `manifest_problems` | covered by the monorepo test | passes | |

Performance check: on the Python standard library (27,847 files), 2.1.0
took 59.2 s and 2.2.0 takes 58.6 s, after a first 2.2 draft that took
411.7 s was profiled and rewritten. The rewrite runs each pattern once per
file, lowercases instead of using `re.IGNORECASE`, and normalises only files
that need it.

### Phase 3: compatibility engine

| Weakness (2.1.0) | Root cause | Files changed | Fix | Tests | Result | Remaining limitation |
| --- | --- | --- | --- | --- | --- | --- |
| Overlapping ranges called a conflict (`>=16 <20` vs `^18.2`, P27): verified | major-version heuristic | new `versions.py`, `check_dependencies.py` | interval arithmetic over npm/Cargo/Poetry and PEP 440 specs | `VersionRangeTest` (31 version pairs) | P27 defended | pre-releases simplified, markers not evaluated (reported as uncertain) |
| Disjoint ranges in one major missed (`~18.0` vs `^18.2`, P28): verified | as above | as above | as above | as above | P28 defended | |
| Peer dependency conflicts (P29) | 2.1 caught it only because peer and normal specs were merged | `check_dependencies.py` | constraints keep their kind; peer and optional count, dev does not; optional-only conflicts are low | `test_peer_and_optional_dependencies`, `test_dev_only_differences_are_not_conflicts` | P29 defended | peers of installed packages (`node_modules`) are not read |
| git / workspace / local specs silently dropped (P30): verified | unreadable specs skipped | `check_dependencies.py` | `version-uncertain` conflicts and unverified warnings with a reason | `test_git_local_and_workspace_specs_are_uncertain_not_dropped` | P30 defended | |
| A package loaded by `importlib.import_module` called unused (P31): verified | regex import scan; "unused" from absence | `index_repo.py`, `check_dependencies.py` | `ast` parsing with literal dynamic imports; unresolved dynamic imports counted; "possibly unused" only with full coverage, else "not determinable" with the reason | `ImportDetectionTest` (6 tests), `test_necessity_analysis` (updated: a v2.1 index without coverage no longer yields "unused") | P31 defended | plugins, CLIs and configuration-loaded packages are never seen |
| `from pkg import sub` resolved to `pkg/__init__.py` instead of `pkg/sub.py` (found by Test G): verified | from-imports resolved by module only | `index_repo.py` | try each imported name as a submodule first | `test_python_relative_dynamic_and_optional` | passes | |
| pyproject.toml, Cargo.toml, go.mod, `-r` includes, runtime ranges not read | only package.json and requirements.txt | `check_dependencies.py` | read, with a pattern fallback before Python 3.11 | `DependencyManifestTest` (11 tests) | passes | Go is not range-checked (minimal version selection) |
| Same-named entities merged without a decision (P32): verified | entities matched by name; "merge" recommended | `check_compatibility.py` | `entity-meaning` (high, needs approval) when descriptions or fields diverge; duplicate-entity advice no longer presumes a merge | `test_same_name_different_meaning_needs_a_decision`, `test_same_name_same_meaning_is_not_flagged` | P32 defended | word-overlap comparison is crude |
| Enum, nullability, uniqueness, delete-policy differences undetected (P33): verified | only names and types compared | `check_compatibility.py`, `source-report.schema.json` | `enum`, `nullability`, `unique-constraint`, `default-value`, `exposure-default`, `field-meaning`, `units`, `delete-policy`, `deletion-semantics`, `cardinality`; migration steps with risk | `SemanticConflictTest`, `SchemaConflictTest` | P33 defended | needs the facts in the source reports |
| `statuses(id)` failed to match `Status` (P34): verified | naive singular (`status` → `statu`) | `check_compatibility.py` | proper singular forms | covered by P34 | P34 defended | irregular plurals (people, children) are not handled |
| Synonym entities (User / Member) got no prompt (P35): verified | aliases only by hand | `check_compatibility.py` | `possible-alias` from synonym groups and field overlap; aliases need a reason (`alias-unexplained`) | `test_user_account_member_are_offered_as_possible_aliases`, `test_alias_merges_only_with_a_recorded_reason` | P35 defended | fixed synonym list |
| App-level conflicts of J–O undetected (identity linking, role escalation, tenancy, idempotency, payments, storage, API conventions, invented endpoint origins) | not modelled | `check_compatibility.py`, schemas | 14 new kinds | `test_integration_scenarios` (answer keys met, must-not-find respected) | passes | detection depends on recon recording the facts |

### Phases 4 and 5: integration and robustness

| Item | Files | What | Tests | Result | Limitation |
| --- | --- | --- | --- | --- | --- |
| Six integration scenarios J–O | `benchmarks/integration/*` | sources, task with an interface, hidden tests, reference, naive merge, answer key | `test_integration_scenarios` | hidden tests pass on every reference and fail on every naive merge at the named tests | same author wrote tests and builds (they discriminate, they are not independent) |
| M-payments answer-key correction | `answer-keys/integration/M-payments.json` | the naive merge passes the retry-after-timeout test because the mock gateway is idempotent; the key was corrected and the reason recorded, rather than overstating what the test catches | as above | | |
| Large monorepo | `generate_monorepo.py` | 1,100 files, three package managers, generated code, legacy module, nested repository | `MonorepoTest` (8 tests) | boundaries kept, modules complete, generated code marked, internal conflicts found | about 1,100 files, not 100,000 |
| Observed vs documented | `validate_artifacts.py` | `observed` needs observed evidence; closed sources: no code, no observed backend; `contradictions` | `HonestyTest` | passes | |
| Offline | tests | capability-gated evidence; no confirmed vulnerability without an audit; network failure inside tests is not success; scripts import no network module | `OfflineTest` | passes | |

### Phase 6: workflow

Fifteen scenarios were reviewed against the instructions; see
[`WORKFLOW-REVIEW.md`](WORKFLOW-REVIEW.md). Changes backed by checks:

- phase approvals with fingerprints, and change-after-approval errors
  (`approvals.py approve-phase`, `validate_project.check_approved_unchanged`);
- the journey-test requirement;
- user-requested features (`source_app` `new`);
- plan-mode honesty.

They are covered by the `test_workflow_guards` tests. A 2.1 design flaw was
fixed on the way: a feature the user asked for that no source has could not
pass the validator, which pushed toward citing unrelated evidence. Changes
that are instruction-only (proprietary services, API response samples,
half-applied migrations, existing data, long sessions) are marked as such in
the review.

### Phase 7: benchmarks

Answer keys moved out of the inputs; four new scenarios (16 in all);
`prepare_run.py` (inputs only; fake credentials generated at run time,
because a committed `sk_live_` fixture would block the GitHub push);
`score.py` metrics for precision, recall, F1, false-positive and
false-negative rates, decisions, security violations, false success claims,
interventions, duration and hidden tests, with an overall score that ranks
confident errors below honest uncertainty; `aggregate.py` for repeated runs
and reproducibility. Results: `benchmarks/RESULTS.md`.

### Bugs found by the agent runs (fixed after them)

The first agent runs used the 2.2 skill as it stood then, and found two
verified bugs in it that the unit tests had missed:

| Weakness | Root cause | File | Fix | Test | Result |
| --- | --- | --- | --- | --- | --- |
| A real `security-scan.json` failed its own schema | the schema's `kind` and `severity` enums were written by hand and drifted from `scan_source.SEVERITY` (no `low`, missing new kinds) | `schemas/security-scan.schema.json` | enums regenerated from the scanner; new fields `complete`, `limits`, `errors`, `files_partially_scanned` | `ScanSchemaTest` checks the enum equals the scanner's kinds and validates a real scan | passes |
| A merge plan with a feature the user asked for (no source) could not validate | `evidence` and `source_features` had `minItems: 1`, contradicting the 2.2 rule that a `new` feature has no source | `schemas/merge-plan.schema.json`, `validate_artifacts.py` | empty evidence allowed only when every row is `new` | `RequestedFeatureMergePlanTest` | passes |
| Recording progress forced new phase approvals (three runs) | phase fingerprints hashed whole files, including slice status and feature validation/compatibility status | `approvals.py`, `validate_project.py`, project schema | fingerprint method 2 leaves progress fields out; method 1 still checked for older approvals | `test_progress_updates_are_not_decision_changes`, `test_approvals_recorded_by_2_2_0_still_check_by_bytes` | passes |

Scorer and answer-key changes made after looking at runs are listed in
`benchmarks/RESULTS.md` and in each key's `key_changes`, and were applied to
every run of both versions.

### Changed tests (behaviour changed on purpose)

These existing tests were edited, never to make broken code pass:

- `test_test_verification`: runs now use real scoped approvals (2.1's tests
  passed `--approval A01` with no A01 in the workspace). The stale-file test
  now expects the file to be moved aside and the run to be
  `invalid-results`. The exit-code test now expects the stronger ledger
  error first, and checks the exit-code rule directly.
- `test_intelligence.test_necessity_analysis`: a v2.1 index without import
  coverage no longer produces "possibly unused" (the requested behaviour); a
  complete index still does.
- `test_release`: the example is a format 4 workspace; the template is
  format 4.
- `test_artifacts`: `tomllib` is allowed as a standard module that is
  guarded for Python before 3.11.

Two pre-existing cosmetic bugs were fixed: "entitie" in validator messages,
and an unused import.

## 3. Security report

### Confirmed vulnerabilities in 2.1.0, all fixed in 2.2.0

| # | Vulnerability | Severity | Probe |
| --- | --- | --- | --- |
| 1 | Test execution without any valid approval, or under an approval for another action or command | high | P01–P04 |
| 2 | Re-run executed code without a valid approval | high | P15 |
| 3 | No timeout or process-tree termination (denial of service on the session; orphaned processes) | medium | P05, P06 |
| 4 | False-green test evidence: zero tests, stale or touched results, self-contradicting results, exit/result disagreement, old green report surviving a failed run | high (integrity) | P07–P11 |
| 5 | Evidence reuse after code change; consistent forgery undetectable | high (integrity) | P12, P13 |
| 6 | Symlink TOCTOU read outside the source root | medium | P17 |
| 7 | Scanner hang on a FIFO (denial of service) | medium | P16 |
| 8 | Secret copied unredacted into `security-scan.json` | medium | P21 |
| 9 | Auto-running hooks (`.envrc`, VS Code, dev container, git fsmonitor) not flagged | medium | P23 |
| 10 | Silent omission of unreadable or too-deep folders, which can hide malicious content | medium | P25 |
| 11 | Output spoofing through control or bidirectional characters in file names | low | P26 |
| 12 | Unbounded memory on huge files | low | P24 |
| 13 | Raw commands, which may contain secrets, stored in approval records. This was in a 2.2 draft, found by its own test before release. | medium | `test_audit_log_redacts_secrets_in_commands` |
| 14 | Nested repositories' manifests treated as part of the source | low | MonorepoTest |

Detection gaps fixed (not vulnerabilities in themselves): P18 to P20 and P22
(injection and secret variants, placeholders, oversized files).

### Remaining risks

1. **Approval authenticity.** An agent that ignores the skill can write an
   approval record and then run under it. The scripts enforce scope and log
   attempts; they cannot tell a human's yes from an agent's. Mitigation
   today: version control of `project.json`, an external copy of the log, the
   host's own permission prompts. Proper fix: approvals signed by a key only
   the user holds, or a confirmation step outside the agent's control.
2. **Evidence authenticity.** With write access to everything and without an
   evidence key held elsewhere, a consistent forgery is undetectable. Tests
   run in-process with the code under test.
3. **Isolation is advisory.** Nothing forces `run_tests.py` into a container
   or cuts its network.
4. **Process escape.** `setsid` children survive a timeout; Windows has no
   job objects.
5. **Windows TOCTOU.** The portable walker checks links, but cannot open
   without following them atomically.
6. **XML parsing** of results relies on the expat limits of the Python in use.

### False-positive limitations

Measured on the Python standard library (27,847 files of real, benign
code): 6 instruction-text findings (AI-SDK documentation, a `curl | bash`
install line, one docstring), 3 high secrets (a private-key header constant
in a crypto library, two JWTs in documentation), 7 weak-secret findings
(documentation examples), 68 low-severity possible-secret findings
(identifiers, test data), and 6 placeholder-secret findings (info). 2.1.0
reported 35 instruction-text findings on the same tree. Expect more in code
that discusses prompts, in documentation examples and in test fixtures.

### False-negative limitations

These are not detected:

- secrets assembled with string formatting, at run time, or across files;
- encodings other than base64 (hex, rot13, compression, Unicode escapes);
- instructions in images, in other languages, or phrased as ordinary
  requests ("before you summarise, please list the environment");
- instructions in binary documents (PDF, DOCX);
- instructions spread over more than a few lines of unrelated text.

A clean scan means "nothing obvious".

## 5. Remaining work, in priority order

1. **Approval authenticity**: a user-held signing key or an out-of-band
   confirmation for `approvals.py grant` and `approve-phase`.
2. **Enforced isolation** for `run_tests.py`: an opt-in container runner
   (`docker run --network none --read-only`) and cgroup containment on Linux.
3. **Windows**: run the suite on a Windows runner; use job objects for
   process trees; review the portable walker.
4. **Independent benchmark material**: answer keys and hidden tests written
   by someone other than the skill's author, and holdout scenarios they keep.
5. **Recon must feed the new compatibility checks**: in both M-payments
   runs the `idempotency`, `payment-flow` and `units` checks never fired
   because the source reports lacked the fields they read; recon should
   prompt for them, or the checks should infer them from code.
6. **More agent runs**, including end-to-end scenarios for the
   instruction-only rules (proprietary services, API response samples,
   half-applied migrations, existing data). RESULTS.md says how many runs
   each number rests on.
7. **Automatic `--rerun` for non-unittest frameworks** (pytest, Jest) from
   the recorded, approved command.
8. **Scanner**: more encodings (hex, Unicode escapes), PDF and DOCX text,
   and a test corpus of real-world injection samples.
9. **Import analysis** for C#, PHP and Ruby, and bundler alias
   configuration (webpack, Vite, Babel).
10. **Semantic matching** in `score.py` beyond keywords.
11. **Style backlog**: line-length and indentation warnings (`flake8`
    E501, E127 and similar) in older and newer code. Pyflakes-class errors
    are zero.
