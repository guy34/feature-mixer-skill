# Unified online shop: migration plan

Status: approved as a plan only (benchmark-operator, pre-approved in task) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).
No such approval exists yet: the plan is approved, running it is not.

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:product | Product | copy A's products keeping `id` and `name` | low | none | plan only |
| migration:product | Product | `price` (Numeric) → `price_minor` (integer) = price × 100; `currency` set to the shop's currency | high | sub-cent precision; any price with more than 2 decimals is refused by the dry run instead of rounded | plan only |
| migration:cart | Cart | B's carts are not migrated; discarded at cut-over | high | open NodeCart carts (transient) | plan only |
| migration:cartitem | CartItem | B's cart items are not migrated; discarded with their carts | high | items in open NodeCart carts; their text ids/quantities are never converted | plan only |

PyShop's Cart/CartItem rows are not in scope (its add-to-cart feature M03 was dropped) and are also discarded.
Reviewly holds no data we can access (closed product); no review data is imported.

## Before running

- Backup: dump PyShop's database and NodeCart's database to files kept outside the app folder; verify each dump restores into a scratch database.
- Dry run: run the product copy against a restored copy; record product counts before and after, and list every price with more than 2 decimal places (expected: none). Abort if any.
- Checks: product count equal; sum(price × 100) equals sum(price_minor); no product id changed; no orphan CartItem (new database starts with no carts).
- Announce the cart reset to customers before cut-over.

## Rollback

The source databases are never modified: rollback is pointing traffic back to PyShop and NodeCart and dropping the new database. Possible until new orders are taken in the unified app; after that, new orders exist only in the unified database.

## Result

Not run (plan mode; running a migration was not approved).
