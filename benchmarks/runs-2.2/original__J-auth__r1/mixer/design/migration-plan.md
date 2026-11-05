# Unified Identity: migration plan

Status: approved (plan only) · Source of risks: `compat/compatibility-report.md` → Migrations

Nothing in this plan runs without the user's explicit approval, recorded in
`project.json` → `approvals` (action `migration`, target `migration:<entity>`).

## Steps

| Migration | Entity | Step | Risk | Data that could be lost | Approval |
| --- | --- | --- | --- | --- | --- |
| migration:user | User | re-key A users (integer) and B accounts (`lu-<n>`) to uuid text ids; old id kept in `legacy_id` | high | none (ids change; anything outside storing old ids stops matching) | plan: resolutions.json (benchmark operator, pre-approved); run: not approved |
| migration:user | User | A salt + hash -> one `password_hash` string `pbkdf2_sha256$<iterations>$<salt hex>$<hash hex>` | low | none | as above |
| migration:user | Identity | B (provider, subject) -> Identity rows pointing at the new User | low | none | as above |
| migration:user | User | A role user -> editor, B role member -> viewer | low | original role names (recoverable from the mapping) | as above |

## Before running

- Backup: both sources keep data only in process memory (A-E04, B-E01); there is no persisted data in this run, so nothing was migrated.
- Dry run: if real data appears, export it, import into a copy, compare counts per source.
- Checks: user counts equal A users + B accounts - verified-email joins; every Identity points at a User.

## Rollback

Keep the source exports; legacy_id maps every new id back to the old one.

## Result

Not run: no persisted source data exists, and no migration run was approved.

Note on the script's migration steps after architecture: "B.Account fields
not kept in User: provider, subject" means they move to the Identity entity
(not dropped); "A.User.salt/hash binary to text" is lossless because both are
hex-encoded into `password_hash`.
