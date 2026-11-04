# Implementation engine

Phase 6 (and phase 8, deployment, only when the user asks). Build the
approved architecture into a working application, one tested slice at a
time. The goal is a running app, not documents. The rules for running,
installing and changing anything are in `engines/security.md`; this file
says how to build.

## 1. Set up safely

- **Where.** Build in `project.json` → `target.path` (default `app/`, next
  to `mixer/`). If the user wants it inside an existing repository, work on
  a new branch (`feature-mixer/<name>`).
- **Sources stay untouched.** Never write to a source app's folder or repo.
  Code taken under `reuse` or `adapt` is copied into the target, with its
  licence notice added to `THIRD_PARTY_NOTICES.md`.
- **Approvals before acting.** Installing dependencies, running anything,
  migrations and destructive changes each need an approval in
  `project.json` → `approvals` first (`engines/security.md` section 5).
  Install with lock files and without install scripts where the package
  manager allows (`npm ci --ignore-scripts`, `pip install --no-deps` after
  review), inside the isolation `check_environment.py` found.
- **Version control** is optional. Never `git init`, commit or tag in a
  folder without the user's agreement; `scripts/checkpoint.py` works without
  git. Never overwrite existing files without saying which and getting a yes.
- **Checkpoints.** After each phase and each slice, run
  `python3 scripts/checkpoint.py mixer/ --phase implementation --include-target --note "V1 done"`.
  If the target is your own git repository and the user wants commits, you
  may also commit and tag `mixer-cp<n>-<slice>` there, with their approval.

## 2. Generate the project

From `architecture.json` and `architecture.md`:

1. The folder structure, one folder (or package) per module.
2. The development environment: dependency manifest with exact versions,
   the config module, `.env.example`, scripts to run, test, lint and
   migrate, and a README with setup steps.
3. The database schema as migrations that run from empty.
4. The shared pieces every slice uses: config, errors and the error format,
   the permission check, logging without personal data, the design system's
   tokens and base components.

## 3. Build slice by slice

For each slice in roadmap order:

1. Set the slice to `in-progress` in `architecture.json`.
2. Implement every layer the slice needs: migrations and models, services
   with the business rules, API routes, and screens or clients.
3. For merged features, build the one combined module the architecture
   describes (for example one notification engine with channel adapters),
   not a copy of each source's version. Keep each source's essential
   behaviour, drop duplicated logic, use the unified data model and
   interfaces, and apply the unified permissions.
4. For `reuse` or `adapt`, take only the code the kept features need, adapt
   it to the unified model, names and error format, and record where it
   came from. Never paste whole modules blindly.
5. For `rebuild`, write fresh code from the source report's behaviour and
   business logic. For closed sources, no copied text, images, icons or
   identifiers.
6. Handle errors and edge cases the reports list: empty, invalid and very
   long input, duplicates and double submits, missing records, permission
   denied, expired sessions, concurrent edits, time zones, and failures of
   external services (with retries where it is safe).
7. Write the slice's tests (see `engines/validation.md`), tag each with the
   menu features and acceptance criteria it proves, and run them through
   `scripts/run_tests.py` (with the approval id), then the whole suite. Fix
   until they pass. Never report a result you did not get from a run.
8. Set the slice to `done`, commit, tag, add the checkpoint, and log one
   line: features done, tests passed, anything harder than planned.

Do not start the next slice while the current one has failing tests.

## 4. Data and secrets

- **Migrations** run forwards from empty and, where possible, backwards.
  Anything with a high data-loss risk on real data (dropping, re-keying,
  narrowing a type) needs the explicit approval recorded in phase 4, the
  steps in `design/migration-plan.md`, a backup, and a dry run on a copy
  first. Never run a migration against real data without that approval.
- **Secrets and accounts** follow `engines/security.md` section 6: the user
  creates accounts and keys; test modes until they say otherwise.

## 5. When something fails

- Fix the cause, rerun the slice's tests, then the full suite.
- After three failed attempts at the same problem, stop. Set `implementation`
  to `failed` in `project.json`, log what was tried, and tell the user the
  options: a different approach, dropping or deferring the feature, or
  rolling back.
- To roll back, create a new branch from the last good checkpoint tag (or
  restore the snapshot into a new folder). Never `reset --hard`, force-push or
  delete work without the user's approval. Set the phase to `rolled-back`,
  then `in-progress` when the next attempt starts.

When every slice is `done`:

```bash
python3 scripts/validate_project.py mixer/ --phase implementation
```

## 6. Deployment (phase 8)

Only when the user asks to deploy, and only after this preflight:

- `validate_project.py mixer/ --phase integration` passes, with verified
  test evidence (`verify_tests.py`, ideally `--rerun`)
- the full test suite passes on a clean checkout
- production configuration is set by the user; no development secrets
- database backups are on, and migrations were dry-run against a copy
- the code, text and assets contain nothing taken from a closed source:
  search for each closed source's name, domain and distinctive copy
- licence notices are present for any reused code

Show the user exactly what will be deployed where and how to undo it. Deploy
only after an explicit yes, recorded as an approval with action `deployment`
and as `deployment.approved: true` in `project.json`. Passing checks do not
make an app production-ready; say what has and has not been tested for real
use (load, security review, real data, real integrations).
