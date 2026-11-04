-- Unified booking app: PostgreSQL 16 schema (design only; not run)
CREATE EXTENSION IF NOT EXISTS citext;
CREATE TABLE app_user (
  id uuid PRIMARY KEY,
  email citext NOT NULL UNIQUE,
  password_hash text NOT NULL,
  role text NOT NULL CHECK (role IN ('customer','staff')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE slot (
  id uuid PRIMARY KEY,
  starts_at timestamptz NOT NULL,
  ends_at timestamptz NOT NULL CHECK (ends_at > starts_at),
  price_amount integer NOT NULL CHECK (price_amount >= 0),
  currency text NOT NULL,
  status text NOT NULL CHECK (status IN ('draft','published','withdrawn')),
  published_by uuid NOT NULL REFERENCES app_user(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX slot_status_starts_idx ON slot (status, starts_at);
CREATE INDEX slot_published_by_idx ON slot (published_by);
CREATE TABLE booking_series (
  id uuid PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE RESTRICT,
  weeks integer NOT NULL CHECK (weeks BETWEEN 2 AND 12),
  status text NOT NULL CHECK (status IN ('active','cancelled')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX booking_series_user_idx ON booking_series (user_id);
CREATE TABLE booking (
  id uuid PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE RESTRICT,
  slot_id uuid NOT NULL REFERENCES slot(id) ON DELETE RESTRICT,
  series_id uuid REFERENCES booking_series(id) ON DELETE RESTRICT,
  status text NOT NULL CHECK (status IN ('held','confirmed','cancelled')),
  created_at timestamptz NOT NULL DEFAULT now(),
  cancelled_at timestamptz
);
CREATE UNIQUE INDEX booking_one_active_per_slot ON booking (slot_id) WHERE status IN ('held','confirmed');
CREATE INDEX booking_user_idx ON booking (user_id, created_at);
CREATE INDEX booking_series_idx ON booking (series_id);
CREATE TABLE payment (
  id uuid PRIMARY KEY,
  booking_id uuid NOT NULL REFERENCES booking(id) ON DELETE RESTRICT,
  amount integer NOT NULL CHECK (amount >= 0),
  currency text NOT NULL,
  stripe_payment_intent_id text,
  idempotency_key text NOT NULL UNIQUE,
  status text NOT NULL CHECK (status IN ('pending','succeeded','failed','refunded')),
  stripe_refund_id text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX payment_booking_idx ON payment (booking_id);
CREATE TABLE waitlist_entry (
  id uuid PRIMARY KEY,
  slot_id uuid NOT NULL REFERENCES slot(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  status text NOT NULL CHECK (status IN ('waiting','offered','accepted','expired','left')),
  offer_expires_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX waitlist_one_open_per_user ON waitlist_entry (slot_id, user_id) WHERE status IN ('waiting','offered');
CREATE UNIQUE INDEX waitlist_one_offer_per_slot ON waitlist_entry (slot_id) WHERE status = 'offered';
CREATE INDEX waitlist_slot_order_idx ON waitlist_entry (slot_id, created_at);
CREATE INDEX waitlist_user_idx ON waitlist_entry (user_id);
CREATE INDEX waitlist_expiry_idx ON waitlist_entry (offer_expires_at) WHERE status = 'offered';
