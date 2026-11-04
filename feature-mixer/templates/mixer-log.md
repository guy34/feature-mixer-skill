# Mixer log

Project: <name> · Mode: full | plan | auto-pick · Sources: A <name>, B <name>

The decision history and integration log for this run. Add a row for every
decision and approval to the first table, and a row for every phase, slice
and run to the second (insert rows at the end of the right table, not at the
end of the file). Never rewrite past rows; add a new one that corrects them.

## Decisions and approvals

| Date | Phase | Decision | Why | Approved by |
| --- | --- | --- | --- | --- |
| 2026-01-01 | selection | Keep M01-M05, drop M06, defer M08 | <reason> | user |

## Integration log

| Date | Phase / slice | What ran | Result | Checkpoint |
| --- | --- | --- | --- | --- |
| 2026-01-01 | recon | Read A (repo @ 3f2a1c9) and B (docs + API spec) | A complete, B partial (2 unknowns) | CP1 |
