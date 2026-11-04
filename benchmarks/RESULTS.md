# Benchmark results (Feature Mixer 2.1.0)

## How these runs were done

- **Who ran them.** Six separate Claude agents, one per scenario, each given
  only a copy of the skill and the scenario's `task.md` and `sources/`. The
  answer keys were not in their folders, and each agent was told not to open
  anything else. They shared a machine with the repository, so this
  independence is by instruction, not enforced.
- **Which skill.** A copy of 2.1 taken before the fixes listed below. The
  runs are what found those defects. Scores are computed on the workspaces
  exactly as the agents left them (`runs/<scenario>/mixer`; the build for
  scenario 2 is in `runs/2-complementary/app`).
- **The user's role.** No user was present. A benchmark operator pre-approved
  Claude's recommendations at each checkpoint, chose auto-pick selection,
  and, for scenario 2 only, approved running the new app's own tests.
  Installing, network access and running any source code were not approved,
  and none happened.
- **Interruption.** All six runs stopped part-way at a usage limit, and were
  resumed from their saved state after it reset.
- **One sample each.** Model output varies between runs; these are single
  samples, not averages.

## Scores

Computed by `score.py` (definitions in [`README.md`](README.md)); raw
output in `runs/scores.json`.

| Scenario | Mode | Feature recall | Precision | Fabricated | Merge | Compat. | Honesty | Large repo | Integration | Tests verified |
|---|---|---|---|---|---|---|---|---|---|---|
| 1-overlapping | plan | 1.0 | 1.0 | 0 | 1.0 | 1.0 | 1.0 | n/a | n/a | n/a |
| 2-complementary | full | 1.0 | 1.0 | 0 | 1.0 | n/a | 1.0 | n/a | 1.0 | 1.0 |
| 3-conflicting | plan | 1.0 | 1.0 | 0 | 0.667 | 0.833 | 1.0 | n/a | n/a | n/a |
| 4-large | plan | 1.0 | 1.0 | 0 | 0.0 | n/a | 1.0 | 1.0 | n/a | n/a |
| 5-incomplete | plan | 1.0 | 0.75 | 0 | n/a | n/a | 0.875 | n/a | n/a | n/a |
| 6-heterogeneous | plan | 1.0 | 1.0 | 0 | 1.0 | 0.5 | 1.0 | n/a | n/a | n/a |

**Validation.** Every run's own final `validate_project.py` (with the skill
copy it used) exited 0. Re-validated with the final 2.1 scripts, five still
exit 0; scenario 3 exits 1, because the improved checker now finds the
critical user-key conflict automatically, and the run's stored decision for
it (which the agent had added by hand) has a different id.

**Compatibility after the fixes** (`runs/rescored-compatibility.json`): re-running
only the final 2.1 checker over the same source reports, with no new
reasoning, gives scenario 1: 1.0, scenario 3: 1.0, scenario 6: 0.667.

## What the numbers mean

- **Discovery and fabrication.** Every answer-key feature was found in every
  run, and no run invented a feature. Scenario 5's precision of 0.75 is extra
  features the agent reported that the key does not list (a reasonable
  sub-split), not wrong ones.
- **Scenario 2 (full build).** Ten features kept, built as a
  standard-library Python app in three slices; 38 tests run by
  `run_tests.py`, verified by `verify_tests.py` and re-run with `--rerun`;
  both business rules (10 MB limit, link expiry) carried over. Not tested:
  the pages' JavaScript in a browser, the socket server, production hashing
  cost. The run says so itself.
- **Scenario 3 merge (0.667).** The agent split posts into create, list and
  read groups instead of one; the scorer expects one group. Finer grain is
  defensible, so this is partly the scorer. The incompatible pair
  (moderation queue vs anonymous posting) was kept apart correctly.
- **Scenario 3 compatibility (0.833).** The checker missed the user-key
  conflict because the users table was linked only to a dropped feature. The
  agent noticed and added it by hand. Fixed (see below); the re-run finds it.
- **Scenario 4 merge (0.0).** The one group in the key (both deal
  pipelines) was not merged: DealFlow's pipeline was left `unique`. A real
  miss. Large-repository handling was complete: 408 files indexed, all 25
  modules accounted for, the 5 real modules read and summarised, the 20
  generated ones checked and skipped with a reason.
- **Scenario 5 honesty (0.875).** The payments feature, whose code is
  missing from the source, was correctly marked medium confidence and listed
  in unknowns, but its basis was `observed` (the agent saw the import and the
  README claim). The key wants `inferred`. Partial coverage was admitted for
  both sources, and calendar sync (whose page is missing) was deferred, not
  invented.
- **Scenario 6 compatibility (0.5, 0.667 after fixes).** The runtime mix
  (Python vs Node) was missed because neither source pinned a runtime
  version; fixed. The two remaining misses (duplicate Cart entity and its
  key) are correct behaviour: the run dropped PyShop's cart, so there was
  nothing left to merge. The answer key assumed both carts were kept; it was
  not changed after seeing the results.

## Defects the runs found, and what changed

| Found by | Problem | Fix | Test |
| --- | --- | --- | --- |
| all six | `mode` could not record plan (or full) together with auto-pick | separate `selection` field (`manual` / `auto-pick`); `"mode": "auto-pick"` still accepted | `SelectionModeTest` |
| 1, 4, 5, 6 | no way to make a checkpoint outside git | `scripts/checkpoint.py` (make, list, restore into a new folder; never commits or deletes) | `CheckpointTest` |
| 1, 3, 4, 5 | foreign keys written `User.id` or `users(id)` caused false conflicts | references accept those forms; docs say to use the entity name | `test_reference_spellings` |
| 3 | entities linked only to dropped features left out, hiding a critical conflict | entities that in-scope entities point at stay in scope | `test_referenced_entities_stay_in_scope` |
| 3 | a 6-character JWT key passed to `jwt.encode` was not found | literal keys in signing calls are found at any length | `test_short_signing_key_and_unknown_extensions` |
| 6 | `schema.prisma` (unknown extension) was skipped silently | every non-binary file is scanned | same test |
| 1 | `integer primary key autoincrement` not read as integer | types parsed by their leading words | `test_type_strings_with_constraints` |
| 4 | unknown field types reported as critical or high mismatches | reported as `unknown-type` (info) | `test_unknown_types_are_not_conflicts` |
| 1 | dropped rows listed as affected features | only kept rows, once a selection exists | `test_affected_features_only_kept_and_manual_categories` |
| 1 | every manual conflict filed under `application` | category follows the kind; decisions under the old id still count | same test, `test_decisions_under_an_old_manual_conflict_id_still_count` |
| 6 | a 1-1 framework tie called "used by the most sources" | ties are reported as ties | `test_framework_tie_is_reported_as_a_tie` |
| 6 | Python vs Node not flagged when no runtime version is pinned | runtime inferred from the manifest type | `test_runtime_from_manifest_type` |
| 2 | `str`/`text` and `bytes`/`blob` treated as different types | more type synonyms, a `binary` type | covered by the type tests |
| 3 | auto-pick's "best-evidenced alternative" would keep the weaker token sign-in | safety and data integrity first, then completeness, then evidence | documentation |
| 4 | no guidance for platform parts no source provides | they are architecture modules, not unified features | documentation |
| 2 | guidance said to `git init` and commit | version control is optional and needs the user's agreement | documentation |
| 5 | an agent read source files before scanning them | stronger wording; cannot be enforced by a script | `docs/LIMITATIONS.md` |

## What this does not show

- The scenarios are small and fictional. They test the workflow, its
  honesty and its checks, not real-world scale or messiness.
- Only one scenario built and tested an app. Integration quality on large or
  complex builds is not measured.
- `score.py` matches by keywords and conflict kinds; read the `details` in
  `runs/scores.json` before trusting a number.
- None of this is evidence that Feature Mixer is ready for production use on
  real applications.
