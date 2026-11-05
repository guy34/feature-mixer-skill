-- Shared expenses with receipt scanning: first migration (PostgreSQL 16). Plan only; not run.
-- Money: bigint minor units + ISO 4217 currency. Timestamps: timestamptz (UTC).

CREATE TABLE app_user (
  id uuid PRIMARY KEY,
  email text NOT NULL UNIQUE,
  display_name text NOT NULL,
  password_hash text NOT NULL,
  home_currency char(3) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE budget (
  id uuid PRIMARY KEY,
  name text NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
  limit_minor bigint NOT NULL CHECK (limit_minor >= 0),
  currency char(3) NOT NULL,
  timezone text NOT NULL DEFAULT 'UTC',
  owner_id uuid NOT NULL REFERENCES app_user(id) ON DELETE RESTRICT,
  is_personal boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX budget_owner_idx ON budget(owner_id);

CREATE TABLE budget_member (
  id uuid PRIMARY KEY,
  budget_id uuid NOT NULL REFERENCES budget(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('owner', 'member')),
  joined_at timestamptz NOT NULL DEFAULT now(),
  removed_at timestamptz
);
CREATE UNIQUE INDEX budget_member_active_uq ON budget_member(budget_id, user_id) WHERE removed_at IS NULL;
CREATE UNIQUE INDEX budget_one_owner_uq ON budget_member(budget_id) WHERE role = 'owner' AND removed_at IS NULL;
CREATE INDEX budget_member_user_idx ON budget_member(user_id);

CREATE TABLE invitation (
  id uuid PRIMARY KEY,
  budget_id uuid NOT NULL REFERENCES budget(id) ON DELETE CASCADE,
  email text NOT NULL,
  token_hash text NOT NULL UNIQUE,
  invited_by uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  expires_at timestamptz NOT NULL,
  accepted_at timestamptz
);
CREATE INDEX invitation_budget_idx ON invitation(budget_id);

CREATE TABLE exchange_rate (
  id uuid PRIMARY KEY,
  base char(3) NOT NULL,
  quote char(3) NOT NULL,
  rate_date date NOT NULL,
  rate numeric(18, 8) NOT NULL CHECK (rate > 0),
  fetched_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (base, quote, rate_date)
);

CREATE TABLE receipt_scan (
  id uuid PRIMARY KEY,
  budget_id uuid NOT NULL REFERENCES budget(id) ON DELETE CASCADE,
  uploaded_by uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  image_key text,
  status text NOT NULL CHECK (status IN ('pending', 'extracted', 'failed', 'confirmed')),
  merchant text,
  date date,
  total_minor bigint,
  currency char(3),
  date_needs_confirmation boolean NOT NULL DEFAULT true,
  expense_id uuid,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX receipt_scan_budget_idx ON receipt_scan(budget_id);
CREATE INDEX receipt_scan_uploader_idx ON receipt_scan(uploaded_by);

CREATE TABLE expense (
  id uuid PRIMARY KEY,
  budget_id uuid NOT NULL REFERENCES budget(id) ON DELETE CASCADE,
  created_by uuid NOT NULL REFERENCES app_user(id) ON DELETE RESTRICT,
  merchant text NOT NULL DEFAULT '',
  amount_minor bigint NOT NULL CHECK (amount_minor > 0),
  currency char(3) NOT NULL,
  budget_amount_minor bigint NOT NULL CHECK (budget_amount_minor > 0),
  fx_rate numeric(18, 8) NOT NULL DEFAULT 1 CHECK (fx_rate > 0),
  fx_rate_date date,
  date date NOT NULL,
  category text NOT NULL CHECK (category IN ('food', 'travel', 'home', 'other')),
  note text NOT NULL DEFAULT '',
  scan_id uuid REFERENCES receipt_scan(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX expense_budget_date_idx ON expense(budget_id, date DESC);
CREATE INDEX expense_created_by_idx ON expense(created_by);
CREATE INDEX expense_scan_idx ON expense(scan_id);
ALTER TABLE receipt_scan ADD CONSTRAINT receipt_scan_expense_fk FOREIGN KEY (expense_id) REFERENCES expense(id) ON DELETE SET NULL;
