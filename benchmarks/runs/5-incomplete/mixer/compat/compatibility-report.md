# Compatibility report

Scope: kept features only. Apps: A, B.

| Severity | Count |
|---|---|
| high | 5 |
| medium | 4 |

## application:authorization-model:accounts-and-roles

- **Conflict:** Neither source shows authentication: A takes user_id as a parameter (A-E02); B implies two audiences, teams that publish slots and customers that book (B-E01), but documents no auth.
- **Affected applications:** A, B
- **Affected features:** M01, M05
- **Severity:** high
- **Possible solutions:** Email-and-password accounts with roles customer and staff (staff publish slots); Magic-link sign-in with the same two roles; Delegate to a hosted identity provider
- **Recommended resolution:** Email-and-password accounts with server-side sessions in http-only cookies; roles customer and staff; staff manage slots, customers manage only their own bookings and waitlist entries.
- **User approval required:** yes
- **Status:** resolved (Email-and-password accounts with server-side sessions in http-only cookies; roles customer and staff; staff manage slots, customers manage only their own bookings and waitlist entries.)

## application:business-rule:cancellation-refund

- **Conflict:** A lets a paid booking be cancelled 24h+ before start but hard-deletes it and issues no refund (A-E03, A-E05); payments.py is missing so a refund elsewhere cannot be ruled out. In the unified app a customer could pay, cancel within the allowed window, and lose the money.
- **Affected applications:** A
- **Affected features:** M03, M04
- **Severity:** high
- **Possible solutions:** Full refund on any allowed cancellation (24h+ before start); No refund (keep A's observed behaviour); Partial refund / fee
- **Recommended resolution:** Full refund through Stripe on every allowed cancellation; cancellations under 24h stay refused. Booking becomes status 'cancelled' (not deleted) with the refund id recorded.
- **User approval required:** yes
- **Status:** resolved (Full refund through Stripe on every allowed cancellation; cancellations under 24h stay refused. Booking becomes status 'cancelled' (not deleted) with the refund id recorded.)

## application:business-rule:recurring-payment

- **Conflict:** A charges the full slot price once, at booking time, before writing the booking (A-E05). B lets a customer book up to 12 weekly occurrences in one request (B-E02) and says nothing about payment. How a series is paid is undefined.
- **Affected applications:** A, B
- **Affected features:** M01, M04, M06
- **Severity:** high
- **Possible solutions:** Charge every occurrence up front at series creation, one charge per occurrence, all-or-nothing; Save the card and charge each occurrence shortly before it starts; Charge the whole series as one payment
- **Recommended resolution:** Charge each occurrence up front at series creation (one Stripe charge per occurrence with its own idempotency key); if any charge fails, refund the ones that succeeded and create nothing. Keeps A's pay-at-booking rule and makes per-occurrence refunds simple. Saved-card charging is deferred (needs stored payment methods and off-session consent).
- **User approval required:** yes
- **Status:** resolved (Charge each occurrence up front at series creation (one Stripe charge per occurrence with its own idempotency key); if any charge fails, refund the ones that succeeded and create nothing. Keeps A's pay-at-booking rule and makes per-occurrence refunds simple. Saved-card charging is deferred (needs stored payment methods and off-session consent).)

## application:workflow:waitlist-release

- **Conflict:** B's waiting list needs to know when a place frees up (B-E05), but A's cancel hard-deletes the booking and emits nothing (A-E03). B does not document whether a freed place is auto-booked (which would charge a card without the customer's consent at that moment) or offered.
- **Affected applications:** A, B
- **Affected features:** M03, M08
- **Severity:** high
- **Possible solutions:** Offer the freed place to the first waiting customer with a time-limited hold; they pay to accept; Auto-book and auto-charge the first waiting customer; Notify everyone on the list; first to pay wins
- **Recommended resolution:** Cancellation emits slot-freed; the first waiting customer gets an offer and an exclusive hold (2 hours, ending no later than 24h before start); accepting runs the normal booking and payment flow; expiry passes the offer to the next. No automatic charges.
- **User approval required:** yes
- **Status:** resolved (Cancellation emits slot-freed; the first waiting customer gets an offer and an exclusive hold (2 hours, ending no later than 24h before start); accepting runs the normal booking and payment flow; expiry passes the offer to the next. No automatic charges.)

## database:manual:slot-double-booking

- **Conflict:** A checks slot.taken but never sets it (A-E02), and charges before inserting with no rollback. With recurring bookings and waiting-list offers competing for the same slot, double booking or a charge without a booking is likely.
- **Affected applications:** A
- **Affected features:** M01, M04
- **Severity:** high
- **Possible solutions:** Database-enforced single active booking per slot plus hold-then-charge-then-confirm; Application-level lock only
- **Recommended resolution:** A partial unique index on bookings(slot_id) where status in (held, confirmed); create the booking as 'held' inside a transaction, charge, then confirm; on payment failure delete the hold.
- **User approval required:** yes
- **Status:** resolved (A partial unique index on bookings(slot_id) where status in (held, confirmed); create the booking as 'held' inside a transaction, charge, then confirm; on payment failure delete the hold.)

## application:workflow:recurring-cancellation

- **Conflict:** A's 24h cancellation rule is per booking; B does not say whether a recurring series is cancelled as a whole or per occurrence.
- **Affected applications:** A, B
- **Affected features:** M03, M06
- **Severity:** medium
- **Possible solutions:** Each occurrence follows the 24h rule on its own; 'cancel series' cancels every remaining occurrence that is 24h+ away; Series can only be cancelled as a whole before the first occurrence
- **Recommended resolution:** Per-occurrence 24h rule; 'cancel series' cancels all remaining occurrences 24h+ away and refunds each.
- **User approval required:** no
- **Status:** resolved (Per-occurrence 24h rule; 'cancel series' cancels all remaining occurrences 24h+ away and refunds each.)

## application:workflow:recurring-partial-availability

- **Conflict:** B does not say what happens when some weeks of a requested series are already taken.
- **Affected applications:** B
- **Affected features:** M06
- **Severity:** medium
- **Possible solutions:** All-or-nothing: refuse and list the taken weeks; Book the free weeks and skip the taken ones
- **Recommended resolution:** All-or-nothing, listing the taken weeks so the customer can shorten the series or join their waiting lists.
- **User approval required:** no
- **Status:** resolved (All-or-nothing, listing the taken weeks so the customer can shorten the series or join their waiting lists.)

## database:duplicate-entity:booking

- **Conflict:** Booking exists in A:Booking, B:Booking; fields not shared: created_at (only A), recurring (only B), slot_id (only A), user_id (only A)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M03, M06, M07
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge into one entity; list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (Merge A:Booking and B:Booking into one Booking entity (A's user_id, slot_id, created_at plus status, series_id for recurring, payment and refund ids); field origins listed in architecture.json)

## database:duplicate-entity:slot

- **Conflict:** Slot exists in A:Slot, B:Slot; fields not shared: price (only A), starts_at (only A), taken (only A)
- **Affected applications:** A, B
- **Affected features:** M01, M02, M03, M04, M05, M08
- **Severity:** medium
- **Possible solutions:** Merge into one table holding the fields kept features need; Keep separate tables if the two only share a name, and rename one
- **Recommended resolution:** Merge into one entity; list every field's origin in architecture.json
- **User approval required:** no
- **Status:** resolved (Merge into one Slot entity (A's starts_at and price, plus ends_at, published_by, status); A's 'taken' flag replaced by the unique active-booking constraint)

## Migrations

Data-loss risk per step: none, low (every value kept), high (values can be lost, changed or rejected). Nothing here is ever run without the user's approval.

| Entity | Apps | Steps | Risk | Data that could be lost | Approved |
|---|---|---|---|---|---|
| Booking | A, B | add fields that only some sources have: created_at (only A), recurring (only B), slot_id (only A), user_id (only A) (low); A.Booking.user_id: unknown to uuid can lose or reject values (high); A.Booking.slot_id: unknown to uuid can lose or reject values (high); B.Booking.recurring: unknown to uuid can lose or reject values (high) | high | recurring, slot_id, user_id | yes |
| Slot | A, B | add fields that only some sources have: price (only A), starts_at (only A), taken (only A) (low); A.Slot fields not kept in Slot: taken (high); A.Slot.price: unknown to integer can lose or reject values (high) | high | price, taken | yes |
| WaitlistEntry | B | merge rows from every source into one table (low) | low | - | yes |
