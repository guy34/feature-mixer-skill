# Security

Feature Mixer reads other people's code, documents and websites, and builds
software from what it learns. This file explains the risks that creates and
what the skill does about them. The rules Claude follows during a run are in
[`feature-mixer/engines/security.md`](feature-mixer/engines/security.md);
this file is the overview for people.

## Threat model

| risk | how it could happen | what Feature Mixer does |
| --- | --- | --- |
| Prompt injection | A README, comment, doc page or `CLAUDE.md` in a source says "ignore previous instructions", "AI agents must run...", or "don't tell the user" | Source content is data, never instructions. `scan_source.py` reports AI-addressed text and agent-instruction files; Claude tells the user once and carries on with the real task. Nothing in a source can approve, grant or change anything. |
| Code execution on inspection | Install scripts (`postinstall`), git hooks, submodules, build files, test fixtures that run code | Sources are read, not run. Repos are cloned with hooks and submodules disabled. Running source code, installing dependencies and running tests each need the user's recorded approval, ideally in a container or VM. |
| Secret leakage | Keys, tokens, `.env` files or passwords in a source end up in reports, logs or the new app | `scan_source.py` finds them and stores only redacted fragments. No credential pattern may appear anywhere in `mixer/` (an error in every workspace format). Configuration is recorded by name, never by value. |
| Supply chain | Registry overrides, unpinned or git dependencies, known-vulnerable packages | Scanned and reported. Vulnerabilities are only "confirmed" when a real audit tool (npm audit, pip-audit, osv-scanner) reports them, run with approval; everything else is labelled unverified. |
| Escaping the source folder | Symbolic links pointing at `/etc` or the user's home folder | Links are never followed; links that escape are reported. |
| Destructive changes | Migrations, deletes, overwrites, force pushes | Need explicit approval; migrations carry a data-loss risk rating and a plan with backup, dry run and rollback. Sources are never modified. |
| Fabricated results | A report that claims tests passed, or claims a website was studied, without it happening | Test results count only with evidence written by `run_tests.py` and checked by `verify_tests.py`. Evidence from an input the session had no capability to read is rejected. |
| Unauthorised access | Logging into other people's accounts, getting past paywalls, scraping | Closed products are studied through public material and the user's own account only, at normal speed with the user present. |
| Licence violations | Copying code the licence does not allow | `reuse` and `adapt` are refused for sources whose `code_reuse` is not `allowed`; closed sources are always rebuilt. |

## What the checks cannot do

- A carefully forged log can match its own fingerprint. Fingerprints prove
  that a report matches its evidence, not that the evidence is genuine;
  `verify_tests.py --rerun` (run with approval) is the real proof.
- Secret and injection scanning uses patterns. It will miss some secrets and
  flag some harmless text. Treat a clean scan as "nothing obvious", not as
  "safe".
- Import maps and dependency necessity are approximate (text patterns).
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
