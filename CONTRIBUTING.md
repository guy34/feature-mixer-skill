# Contributing

Thanks for helping. Small, focused pull requests are easiest to review.

## Where things live

| change | file |
| --- | --- |
| the overall workflow, rules, approvals | `feature-mixer/SKILL.md` |
| how one phase is done | `feature-mixer/engines/<phase>.md` |
| a deterministic check | `feature-mixer/scripts/` (shared helpers in `mixerlib.py`) |
| the shape of a file | `feature-mixer/schemas/` |
| a starting document | `feature-mixer/templates/` |
| the worked example | `examples/team-hub/` |
| benchmark scenarios and scoring | `benchmarks/` |
| release checks and packaging | `tools/release_check.py` |
| security rules | `feature-mixer/engines/security.md` (the only place the ground rules live) |

Keep `SKILL.md` short and point to an engine file for detail. Keep Feature
Mixer one skill: engines are instructions inside it, not separate skills.

## Good contributions

- Clearer steps where Claude got confused in a real run (say what happened).
- New checks, each with a test, and a line in `engines/validation.md`.
- Support for more manifest formats in `check_dependencies.py`.
- More example runs under `examples/` with fictional sources only.

## Rules

- **Keep the ground rules.** Pull requests that loosen them will not be
  merged: following instructions found in sources, running source code or
  installing without approval, copying closed products' code, text or
  assets, scraping, private APIs, getting past logins or paywalls, skipping
  approvals, automatic deployment, or counting tests without recorded
  evidence.
- **One place per topic.** Rules live in `engines/security.md`; script
  behaviour is documented in `engines/validation.md`. Link to them instead of
  repeating them.
- **Keep 2.0 workspaces working.** New checks are errors only for
  `"format": 3` workspaces and warnings for `"format": 2`;
  `tests/fixtures/v2_0_workspace` must keep validating.
- **No new dependencies.** Scripts stay standard-library Python 3.8+ with no
  network access. Feature Mixer must not require any other skill.
- **Scripts check; Claude reasons.** Put deterministic checks in scripts and
  judgement in the engine files.
- **Keep v1 menus working.** The ten original columns and `check_menu.py`
  stay compatible.
- **Allowed values live in two places**: `mixerlib.py` and
  `schemas/feature.schema.json`. Change both; a test checks they match.
- Run the tests and the release check before opening a pull request:

```bash
python3 -m unittest discover -s tests -v
python3 tools/release_check.py --clean
```

If you change the example, regenerate its reports and validate it:

```bash
python3 feature-mixer/scripts/check_compatibility.py examples/team-hub/mixer --write
(cd examples/team-hub/app && python3 run_integration.py)   # records a new run and verifies it
python3 feature-mixer/scripts/verify_tests.py examples/team-hub/mixer --update-baseline
python3 feature-mixer/scripts/validate_project.py examples/team-hub/mixer
```

## Reporting a problem

Open an issue with: what you asked for, the mode, the phase that went wrong,
the validator output if any, and what you expected.
