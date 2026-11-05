# Scenario 10: one slice of a large monorepo

Mode: plan. Selection: auto-pick.

First generate the source: `python3 generate_monorepo.py sources/mono` (the benchmark operator does this).
**A (Mono)** is my own monorepo in `sources/mono`. I want a new, smaller app with the admin front end's
screens and the billing service. Everything under `third_party/` is someone else's project and must stay out.
