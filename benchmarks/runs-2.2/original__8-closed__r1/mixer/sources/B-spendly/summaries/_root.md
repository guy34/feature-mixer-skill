# Module (root) of Spendly (B)

Files: `spendly.py` (6 lines). Read in full.

- `CATEGORIES` (line 1): fixed list food, travel, home, other. Feature B-F02.
- `EXPENSES` (line 2): in-memory list, lost when the process ends.
- `add(amount_cents, category, note="")` (lines 3-6): rejects unknown
  categories with `ValueError("unknown category")`, then appends
  `{amount_cents, category, note}`. No amount check, no id, no date, no
  currency, no owner. Feature B-F01.

External imports: none. Depends on: nothing.
