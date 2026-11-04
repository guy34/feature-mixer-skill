# Unified booking app: migration plan

Status: approved as a plan only (A03, A04; benchmark-operator, pre-approved in task) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).
No BookNow data was provided and Slotty is a closed product with no data to
move, so today this plan only applies if the user later supplies a BookNow
database.

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:booking | Booking | add status, series_id, cancelled_at; existing rows become `confirmed` | low | none | A04 (plan) |
| migration:booking | Booking | A user_id and slot_id (type unknown) → uuid via id-map tables, old value kept in `legacy_id` | high | rows whose ids do not resolve | A04 (plan) |
| migration:booking | Booking | B recurring option → series_id | high (no B data exists) | none in practice | A04 (plan) |
| migration:booking | Booking | A created_at naive UTC → timestamptz (assume UTC) | low | none | A04 (plan) |
| migration:slot | Slot | A price (type unknown) → integer minor units + currency | high | fractional values below one minor unit | A04 (plan) |
| migration:slot | Slot | A taken flag not stored; derived from active bookings | high | taken=true slots with no booking row | A04 (plan) |
| migration:waitlistentry | WaitlistEntry | create empty | none | none | not needed |

## Before running

- Backup: full dump of the BookNow database, restore verified on a scratch instance.
- Dry run: on the restored copy, with row counts per table before and after.
- Checks: booking count equal; no booking with unresolved user or slot; sum of prices equal after conversion (in minor units); every A slot with taken=true has a confirmed booking (list any that do not for the user to decide).

## Rollback

Migrations are forward-only on a new database; the BookNow database is left untouched, so rollback is discarding the new database and keeping the old app running until the checks pass.

## Result

Not run (plan mode).
