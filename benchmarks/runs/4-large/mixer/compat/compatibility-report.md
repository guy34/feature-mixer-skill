# Compatibility report

Scope: kept features only. Apps: A, B.

| Severity | Count |
|---|---|
| critical | 1 |
| high | 4 |
| medium | 3 |
| low | 2 |

## database:primary-key:deal

- **Conflict:** Deal primary keys differ (A: integer, B: unknown)
- **Affected applications:** A, B
- **Affected features:** M02, M03, M04, M05, M06
- **Severity:** critical
- **Possible solutions:** Pick one key type for the merged entity and re-key the other source's rows; Keep a legacy_id column holding the old key during migration
- **Recommended resolution:** Use one key type (uuid is usual for merged data) and add a legacy_id column while migrating
- **User approval required:** yes
- **Status:** resolved (uuid (stored as text) for every unified Deal; each imported row keeps legacy_source ('A' or 'B') and legacy_id (A's integer id; B's id as text, type unknown) during and after migration; Contact is re-keyed the same way so Deal.contact_id is uuid)

## application:rule:deal-stages

- **Conflict:** A's stages are lead, qualified, proposal, won, lost (fixed); B's default stages are new, contacted, negotiating, closed (caller-supplied). Existing stage values do not match, and B's 'closed' does not say whether the deal was won or lost.
- **Affected applications:** A, B
- **Affected features:** M03, M04
- **Severity:** high
- **Possible solutions:** One configurable stage table seeded with A's stages; map B's values new->lead, contacted->qualified, negotiating->proposal, and keep 'closed' as an extra closed stage with outcome 'unspecified'; Seed with B's stages and map A's won and lost both to closed (loses the outcome); Keep two separate pipelines, one per source
- **Recommended resolution:** One configurable stage table seeded with A's five stages plus a 'closed' stage (outcome unspecified) for B's closed deals, so no stage value is lost or invented; users can reclassify those deals later
- **User approval required:** yes
- **Status:** resolved (Accept the recommendation: configurable Stage table seeded with lead, qualified, proposal, won, lost plus closed (outcome unspecified) for B's closed deals)

## application:workflow:deal-owner

- **Conflict:** B's reminders email deal['owner_email'], but A's deals have no owner at all and neither app has users or authentication, so reminders cannot work for A's deals until an owner exists.
- **Affected applications:** A, B
- **Affected features:** M03, M04, M06
- **Severity:** high
- **Possible solutions:** Add a User entity and a required Deal.owner_id; B's owner_email values become users; A's deals are assigned to an owner the user names at migration; Keep a free-text owner_email on Deal and leave A's deals without reminders
- **Recommended resolution:** Add User and Deal.owner_id; create users from B's distinct owner_email values; assign A's existing deals to one default owner chosen by the user before migration
- **User approval required:** yes
- **Status:** resolved (Add User and required Deal.owner_id; create users from B's distinct owner_email values; A's existing deals get a default owner the user names before migration)

## database:field-type:deal.stage

- **Conflict:** Deal.stage types differ (A: text, B: unknown)
- **Affected applications:** A, B
- **Affected features:** M02, M03, M04, M05, M06
- **Severity:** high
- **Possible solutions:** Choose the wider type and convert the narrower data; Split into two fields if they mean different things
- **Recommended resolution:** One type per field; convert in a migration
- **User approval required:** yes
- **Status:** resolved (Deal.stage becomes stage_id (uuid, FK to Stage); A's text values map 1:1 to the seeded stages; B's values map new->lead, contacted->qualified, negotiating->proposal, closed->'closed' (outcome unspecified); any other B value is imported as an extra configured stage, never dropped)

## database:field-type:deal.title

- **Conflict:** Deal.title types differ (A: text, B: unknown)
- **Affected applications:** A, B
- **Affected features:** M02, M03, M04, M05, M06
- **Severity:** high
- **Possible solutions:** Choose the wider type and convert the narrower data; Split into two fields if they mean different things
- **Recommended resolution:** One type per field; convert in a migration
- **User approval required:** yes
- **Status:** resolved (Deal.title is text, not null, max 200; B's values (type unknown, used as text) are cast with str() on import and the dry run reports any that are empty or not strings)

## application:data:deal-contact

- **Conflict:** A's deals link to a contact; B's deals have no contact, so B's deals arrive without one.
- **Affected applications:** A, B
- **Affected features:** M03, M04
- **Severity:** medium
- **Possible solutions:** Keep Deal.contact_id nullable; Create a placeholder contact for B's deals
- **Recommended resolution:** Keep Deal.contact_id nullable (it already is in A's schema); show 'no contact' in the UI
- **User approval required:** no
- **Status:** resolved (Deal.contact_id stays nullable; B's deals import with no contact)

## application:rule:reminders-on-closed-deals

- **Conflict:** B's reminder job does not exclude closed deals, so after the merge won and lost deals would be emailed about forever; it also re-sends on every run.
- **Affected applications:** A, B
- **Affected features:** M03, M06
- **Severity:** medium
- **Possible solutions:** Skip deals in stages whose outcome is won, lost or unspecified-closed, and dedupe on (deal, moved_at); Keep B's behaviour
- **Recommended resolution:** Skip closed stages and send at most one reminder per deal per idle period
- **User approval required:** no
- **Status:** resolved (Reminders skip stages with a closed outcome and dedupe on (deal_id, moved_at))

## database:duplicate-entity:deal

- **Conflict:** Deal exists in A:Deal, B:Deal; fields not shared: contact_id (only A), moved_at (only B), owner_email (only B), value_cents (only A)
- **Affected applications:** A, B
- **Affected features:** M02, M03, M04, M05, M06
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge into one entity; list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (Merge A:Deal and B:Deal into one Deal entity; field origins listed in architecture.json)

## application:data:moved-at-timezone

- **Conflict:** B stores moved_at from datetime.utcnow(), a naive timestamp.
- **Affected applications:** B
- **Affected features:** M04, M06
- **Severity:** low
- **Possible solutions:** Store timezone-aware UTC; treat B's naive values as UTC on import
- **Recommended resolution:** Store timezone-aware UTC; treat B's naive values as UTC on import
- **User approval required:** no
- **Status:** resolved (Store timezone-aware UTC; B's naive values are read as UTC on import; A's deals get moved_at = import time)

## application:workflow:merge-vs-moved-at

- **Conflict:** A's contact merge rewrites deals; if it touched moved_at it would reset B's staleness clock.
- **Affected applications:** A, B
- **Affected features:** M02, M06
- **Severity:** low
- **Possible solutions:** Merge changes only contact_id on deals; Treat a merge as a move
- **Recommended resolution:** Merge changes only contact_id; moved_at changes only on stage moves
- **User approval required:** no
- **Status:** resolved (Contact merge changes only contact_id on deals; moved_at changes only on stage moves)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Deal | A, B | re-key rows to one primary key type (A: integer, B: unknown) and rewrite foreign keys that point at them (high); convert stage to one type (A: text, B: unknown) (high); convert title to one type (A: text, B: unknown) (high); add fields that only some sources have: contact_id (only A), moved_at (only B), owner_email (only B), value_cents (only A) (low); A.Deal.contact_id: integer to uuid can lose or reject values (high); A.Deal.stage: text to uuid can lose or reject values (high); B.Deal.title: unknown to text can lose or reject values (high); B.Deal.stage: unknown to uuid can lose or reject values (high); B.Deal.owner_email: unknown to uuid can lose or reject values (high) | high | contact_id, owner_email, stage, title | yes |
| Contact | A | merge rows from every source into one table (low) | low | - | yes |
