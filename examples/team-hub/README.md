# Example: Team Hub, mixed from three apps

A complete Feature Mixer run, kept in the repo so you can see every file the
skill writes and check them with its validators.

| Source | What it is | Rights | What was taken |
| --- | --- | --- | --- |
| A TaskBoard (`sources/taskboard`) | the user's own task board | own code | sign-in, task board, assignment, in-app notifications, roles |
| B Approvals (`sources/approvals`) | an MIT-licensed approval tool | open source | approvals, threaded comments, email notifications, roles |
| C Pulse (`sources/pulse-docs`) | a closed product: public docs and API spec only | closed | workload dashboard, push notifications (rebuilt from docs) |

All three sources are small and fictional, written for this example. Pulse
is not a real product, and there is no Pulse code here, by design.

## What happened

1. **Recon**: one report per source in `mixer/sources/` (A and B from code,
   C from docs, with C marked partial and four unknowns listed).
2. **Extraction**: 17 features on `mixer/feature-menu.csv`, grouped: sign-in
   (identical), comments (similar), roles (similar), notifications
   (complementary), share links (incompatible), the template gallery (skip).
3. **Selection**: 11 kept, 3 dropped, 2 deferred, 1 skipped.
4. **Compatibility**: 20 conflicts found, among them uuid vs integer user
   keys (critical), cookie vs token sessions, three role sets, two `/login`
   routes, and one workflow conflict found by reasoning (closing a task with
   a pending approval). All decided in `mixer/compat/resolutions.json`.
5. **Architecture**: one Python app, seven modules, one notification engine,
   one role model, four build slices (`mixer/design/`).
6. **Implementation**: `app/`, built slice by slice.
7. **Integration**: 23 tests run by `run_tests.py`, which recorded the log,
   per-test results, exit code and fingerprints in `mixer/test-runs/`;
   `verify_tests.py` checked the report against them. Every kept feature and
   all 10 acceptance criteria are proven (`mixer/integration-report.md`).
8. **Deployment**: not requested, so not done.

Since v2.1 the workspace also has `mixer/capabilities.json`, a security
scan and (for A and B) an index with module summaries per source,
`mixer/merge-plan.json` (8 unified features), the architecture style with
the alternatives considered, a field-level migration plan
(`mixer/design/migration-plan.md`, which caught that B's request title would
be lost), and an approvals ledger in `mixer/project.json`.

## Check it yourself

From the repository root:

```bash
python3 feature-mixer/scripts/validate_project.py examples/team-hub/mixer
python3 feature-mixer/scripts/check_compatibility.py examples/team-hub/mixer --strict
python3 feature-mixer/scripts/validate_feature_menu.py examples/team-hub/mixer/feature-menu.csv --show
python3 feature-mixer/scripts/verify_tests.py examples/team-hub/mixer
cd examples/team-hub/app && python3 run_integration.py   # re-runs the tests (approval A01) and verifies
```

`run_integration.py` adds a new run folder under `mixer/test-runs/` each
time; the report always points at the latest run.

The checkpoint refs in `mixer/project.json` (`git:mixer-cp1-recon`...)
name the tags made during the run; the tags themselves are not part of this
repository.
