# Benchmarks

Reproducible scenarios for measuring how well Feature Mixer does its job, not
just whether its files are well-formed.

| scenario | sources | mode | what it tests |
| --- | --- | --- | --- |
| `1-overlapping` | two notes apps (Python, Node) | plan | duplicate and similar features, an entity key conflict |
| `2-complementary` | upload, preview and share-link apps | full | complementary parts of one capability, dependencies, business rules, building and verified testing |
| `3-conflicting` | two forums (own code, MIT) | plan | key, session, role, route, contract and rule conflicts; incompatible moderation vs anonymous posting |
| `4-large` | a generated 400-file CRM plus a small one | plan | indexing, module-by-module coverage, summaries |
| `5-incomplete` | code with a missing module; docs with a missing page | plan | honesty: partial coverage, low confidence, unknowns, no invention |
| `6-heterogeneous` | Python + Node + a closed product's docs | plan | framework, runtime and data-layer conflicts, cart merge |

Each scenario folder has `task.md` (what the user asks), `sources/` (small,
fictional source apps written for the benchmark) and `ground-truth.json`
(the answer key). `4-large` generates its big repository with
`generate_large.py` (seeded, so every run gets identical files).

## Running a scenario

1. Copy the skill folder and the scenario's `task.md` and `sources/` (never
   `ground-truth.json`) into a fresh folder. For `4-large`, run
   `python3 benchmarks/generate_large.py <folder>/sources`.
2. Run Feature Mixer there as a user would, treating `task.md` as the request.
3. Score it:

```bash
python3 benchmarks/score.py benchmarks/scenarios/<name>/ground-truth.json <folder>/mixer --json
```

## What the scorer measures

| metric | meaning |
| --- | --- |
| feature recall / precision | answer-key features found; reported features that match one |
| fabricated | reported features matching "should not exist" keywords |
| merge accuracy | groups merged with an accepted type, incompatible pairs kept apart, dependencies recorded |
| compatibility recall | answer-key conflicts found in the compatibility report |
| honesty | partial coverage admitted, weak evidence not marked high, gaps listed as unknowns, capabilities decided, nothing fabricated |
| large repository | index, coverage record, feature modules analysed, summaries |
| integration completeness | (full mode) kept features verified by `verify_tests.py` |
| test execution | (full mode) share of reported tests verified against evidence |
| validator exit | `validate_project.py` at the last phase of the mode |

Matching is by keywords per app, so read the `details` in the JSON before
trusting a number. See [`RESULTS.md`](RESULTS.md) for the recorded runs and
[`../docs/LIMITATIONS.md`](../docs/LIMITATIONS.md) for what these scores
cannot tell you.
