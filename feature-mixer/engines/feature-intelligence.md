# Feature intelligence engine

Phases 2 and 3. Put every feature from every source on one menu, work out
how they relate, recommend what to do with each group, and let the user
choose.

Output: `mixer/feature-menu.csv` (from `templates/feature-menu.csv`), and at
the end of selection `mixer/merge-plan.json` (from `templates/merge-plan.json`),
the list of unified features the app will actually have.

## Menu columns

The first ten columns are the v1 columns and keep their meaning.

| column | meaning |
| --- | --- |
| `id` | `M01`, `M02`... stable once assigned |
| `feature` | what it does, in plain words |
| `area` | accounts, tasks, reporting... |
| `source_app` | app id(s), `A` or `A;B`; `new` only for a feature the user asked for that no source has (its `notes` say "requested by the user"; it needs no source evidence) |
| `priority` | `must`, `should`, `could` |
| `complexity` | `S`, `M`, `L`, `XL` |
| `depends_on` | menu ids this needs, separated by `;` |
| `conflicts_with` | menu ids it cannot live with |
| `pick` | `keep`, `drop`, `later`, `skip` (cannot be rebuilt); empty while undecided |
| `notes` | short notes for the user |
| `merge_group` | a lower-case name shared by related features from different apps, e.g. `notifications` |
| `merge_type` | `identical`, `similar`, `complementary`, `unique`, `incompatible`, `separate` (`conflicting` and `independent` are accepted as other names for `incompatible` and `unique`) |
| `evidence_refs` | evidence ids from the source reports, e.g. `A-E03;A-E07` |
| `compatibility` | `compatible`, `adaptable`, `conflict`, `incompatible`, `unknown` |
| `implementation_strategy` | `reuse`, `rebuild`, `adapt`, `combine`, `improve`, `reject` |
| `confidence` | `high`, `medium`, `low`: the lowest confidence of its evidence |
| `integration_notes` | how it fits the unified app, and why this recommendation |
| `description` | one sentence the user can read in the selection view |
| `source_features` | the source feature ids it comes from, e.g. `A-F02` |

## Phase 2: build and classify

1. **One row per source feature.** Usually one menu row per `A-F..` id.
   Split a source feature into several rows only if the user could
   reasonably want part of it. Fill `source_features` and `evidence_refs`
   so every row traces back to its source.
2. **Group related features.** Features from different apps that serve the
   same purpose share a `merge_group`. Every row in a group has the same
   `merge_type`.
3. **Classify.**

| merge_type | when | what happens |
| --- | --- | --- |
| `identical` | same job, same behaviour (two email sign-ins) | keep one, drop the rest |
| `similar` | same job, different behaviour (flat vs threaded comments) | choose one alternative, or `combine` them deliberately |
| `complementary` | different parts of one capability (in-app, email and push notifications) | build one module that does all kept parts (`combine`) |
| `unique` | only one app has it | keep or drop on its own; no group needed |
| `incompatible` (also `conflicting`) | cannot coexist with something else (anyone-with-link editing vs a strict role model) | name the other side in `conflicts_with`; keep at most one |
| `unique` (also `independent`) | only one app has it, and nothing else relates to it | keep or drop on its own |
| `separate` | related to others in its group, but deliberately kept apart (public status page vs internal incident log; both about incidents, different audiences and permissions) | each kept row becomes its own unified feature; `integration_notes` must state the boundary; strategy is never `combine` |

Features that **share data but have different jobs** (task assignment and a
workload dashboard both use tasks) are not merged. Each stays `unique` (or
`separate` when you want the relationship recorded), the data they share
becomes one entity in the architecture, and `depends_on` records which
needs which.

Features that should be **improved before integration** (a source's flawed
or insecure version of a feature you still want) get strategy `improve`, and
`integration_notes` must say what changes (for example: "B emails the
password reset link without expiry; add 30-minute expiry and single use").

4. **Dependencies.** Fill `depends_on` from the source reports' feature
   dependencies, mapped to menu ids, plus anything the merge creates (a
   combined notification engine needs accounts).
5. **Strategy.** Pick the recommended `implementation_strategy`:

| strategy | meaning | allowed when |
| --- | --- | --- |
| `reuse` | take the source's code as it is | the source's `code_reuse` is `allowed` |
| `adapt` | take the source's code and change it to fit | the source's `code_reuse` is `allowed` |
| `rebuild` | write it fresh from the observed behaviour | always; the only option for closed apps |
| `combine` | write one new module that merges several sources' behaviour | always |
| `improve` | rebuild it with the changes `integration_notes` describes | always (it is a rebuild) |
| `reject` | do not integrate | always; required for `skip` rows |

`validate_project.py` refuses `reuse` and `adapt` for sources whose code may
not be reused. Prefer `rebuild` when the source's code is tied to a stack
the unified app will not use.

6. **Compatibility (first pass).** Set `compatibility` from what you can see
   now: `compatible` (fits as is), `adaptable` (fits with changes),
   `conflict` (needs a decision in phase 4), `incompatible`, or `unknown`.
   Phase 4 confirms it.
7. **Skip what cannot be rebuilt.** Licensed content, other users' content,
   a network of users, partner deals, hardware and regulated licences are
   `skip` with strategy `reject` and the reason in `notes`.
8. **Recommend.** For each group and each unique feature, write the
   recommendation and the reason in `integration_notes`. Do not set `pick`
   yourself (except in `auto-pick` mode).

### Worked example: notifications

| id | feature | source | merge_group | merge_type | strategy |
| --- | --- | --- | --- | --- | --- |
| M10 | In-app notifications | A | notifications | complementary | combine |
| M11 | Email notifications | B | notifications | complementary | combine |
| M12 | Push notifications | C | notifications | complementary | combine |

Recommendation: one notification engine. Every event creates one
notification record; each user's preferences decide which channels
(in-app, email, push) deliver it; one dedupe key stops double sends. That
is one module with three delivery adapters, not three notification systems.

Check the menu:

```bash
python3 scripts/validate_feature_menu.py mixer/feature-menu.csv --allow-no-keep
```

Set `extraction` to `done`, checkpoint, and log the counts per group and
type.

## Phase 3: selection

1. **Show the menu.**

   ```bash
   python3 scripts/validate_feature_menu.py mixer/feature-menu.csv --show --format md
   ```

   This lists, per group: id, pick, feature, source, description, priority,
   complexity, dependencies, conflicts, merge type, compatibility, evidence
   and strategy. Add your recommendations underneath, short.

2. **Take the user's choices.** They can pick one feature, several, or a whole
   group, choose between alternatives, combine complementary features,
   reject duplicates, or defer (`later`). Apply them with:

   ```bash
   python3 scripts/validate_feature_menu.py mixer/feature-menu.csv --set keep M01,M04,group:notifications
   python3 scripts/validate_feature_menu.py mixer/feature-menu.csv --set drop M06
   python3 scripts/validate_feature_menu.py mixer/feature-menu.csv --set later M08
   ```

   `--set` changes only what is named, refuses to keep a `skip` row, and
   announces when a `must` feature is dropped. If the user wants to
   combine two alternatives, set both rows' strategy to `combine` and
   explain how in `integration_notes`.

3. **Check the picks.** The validator reports missing dependencies (direct
   and through other features), circular dependencies, conflicts between kept
   features, more than one kept identical feature, similar features kept
   without `combine`, kept incompatible features, kept rows without evidence
   or with strategy `reject`, and features that depend on `skip` rows. Show
   the user any problems and the ways to fix them (keep the dependency, drop
   the dependent feature, or change the strategy). Never resolve them by
   changing picks the user did not ask to change. A kept feature whose
   dependency was dropped is the user's call: keep the dependency too, drop
   the feature, or rebuild what it needs, and say what each costs. Two kept
   features that exclude each other (`conflicts_with`, an `incompatible`
   group) are never both kept: the user chooses one, or a design that keeps
   them apart (`separate`, with the boundary written down).

4. **Write the merge plan.** Turn the kept rows into unified features in
   `mixer/merge-plan.json`: one `U01`... per capability the app will have.
   Each records its menu rows (`menu_ids`), the original source features and
   evidence, the `merge_type`, the `rationale` for merging (or not), the
   final unified `behaviour`, any `improvements`, its `depends_on`
   (other `U` ids), its `compatibility`, and `validation` (`untested` until
   the tests prove it). Rules the validator enforces:
   - every kept row is in exactly one unified feature, so nothing is built twice
   - kept rows of an `identical`, `similar` or `complementary` group share one
     unified feature; kept rows of a `separate` group each get their own
   - a unified feature built from several rows is never `unique`
   - evidence and source features come from its rows
   - no two unified features have the same name (duplicate functionality)
   - `validation` must match the verified test results at the end

   Platform pieces that no source provides but the app needs (for example
   accounts when only one source had them, or an API layer) are not unified
   features; they are modules in the architecture with no menu ids.
5. **Confirm.** When the validator passes and no row is undecided, show the
   final list (kept, dropped, deferred) and the unified features, and ask for
   approval. Record it with
   `python3 scripts/approvals.py approve-phase --mixer mixer/ --phase selection --granted-by "<name>" --user-confirmed`
   (it stores a fingerprint of the picks and the merge plan), checkpoint,
   and log every pick decision with its reason. Changing a pick or the merge
   plan afterwards is reported by `validate_project.py` until the user
   approves the change.

Never add a feature that is in no source and that the user did not ask for.
Platform pieces the app needs go in the architecture, not on the menu.

### auto-pick selection

Keep each source's core-loop features and every `must`, keep one row per
`identical` group (the most complete), combine `complementary` groups,
choose the `similar` alternative that is safer and more complete (security and
data integrity first, then completeness, then evidence; say why), drop `incompatible` rows
that conflict with something kept, and defer `could` features that add
risk. List every pick and every drop in the log and in your message. The
user's choice of `auto-pick` (`"selection": "auto-pick"`, in either mode) is
the approval for the selection; every other approval still applies.
