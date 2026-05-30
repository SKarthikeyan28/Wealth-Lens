-- =============================================================================
-- SG Personal Finance Optimizer — v1 schema
-- PostgreSQL 14+
--
-- Design notes:
--   * Singapore account types (CPF/SRS) are modeled as rows in `accounts`
--     distinguished by an enum, NOT as separate tables. Extensible and clean.
--   * `securities` is a shared reference table: many users -> same instrument.
--     Price history is stored once per instrument, not per user.
--   * `holdings` is the user-account <-> security join (quantity + cost).
--   * income / expenses feed savings-rate + Monte Carlo savings input.
--   * goals feed Monte Carlo targets. risk_profile stores the CRRA gamma.
--   * CPF contribution/interest RULES are deliberately NOT modeled here —
--     they belong in code, not the schema (policy changes, sub-account logic).
-- =============================================================================

-- gen_random_uuid() lives in pgcrypto on older PGs; built in from PG 13+.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- -----------------------------------------------------------------------------
-- Enums
-- -----------------------------------------------------------------------------

-- SG-specific account types live here. Add a value, not a table, to extend.
CREATE TYPE account_type AS ENUM (
    'CASH',          -- bank / cash savings
    'BROKERAGE',     -- general investment account (may hold USD assets, e.g. VWRA)
    'CPF_OA',        -- CPF Ordinary Account
    'CPF_SA',        -- CPF Special Account
    'CPF_MA',        -- CPF MediSave Account
    'SRS'            -- Supplementary Retirement Scheme
);

-- What the covariance engine groups instruments by.
CREATE TYPE asset_class AS ENUM (
    'EQUITY',
    'ETF',
    'REIT',
    'BOND',
    'PRECIOUS_METAL',
    'CASH_EQUIVALENT'
);

CREATE TYPE income_source AS ENUM (
    'SALARY',
    'BONUS',
    'DIVIDEND',
    'MISC'
);

-- -----------------------------------------------------------------------------
-- users  — auth + 2FA
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           CITEXT NOT NULL UNIQUE,         -- case-insensitive; needs `citext` ext, see below
    password_hash   TEXT   NOT NULL,                -- argon2 / bcrypt output
    totp_secret     TEXT,                           -- ENCRYPT AT REST in app layer; null until 2FA enabled
    totp_enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- accounts  — one row per user account; SG types via enum
-- -----------------------------------------------------------------------------
CREATE TABLE accounts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,                    -- user label, e.g. "DBS Multiplier"
    account_type  account_type NOT NULL,
    currency      CHAR(3) NOT NULL DEFAULT 'SGD',   -- ISO 4217; brokerage may be 'USD'
    cash_balance  NUMERIC(18,2) NOT NULL DEFAULT 0, -- for CASH/CPF/SRS balances entered manually
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_accounts_user ON accounts(user_id);

-- -----------------------------------------------------------------------------
-- securities  — shared instrument reference (one row per ticker, all users)
-- -----------------------------------------------------------------------------
CREATE TABLE securities (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker      TEXT NOT NULL,                      -- e.g. 'VWRA.L', 'C38U.SI'
    name        TEXT,
    asset_class asset_class NOT NULL,
    exchange    TEXT,                               -- e.g. 'LSE', 'SGX'
    currency    CHAR(3) NOT NULL,
    UNIQUE (ticker, exchange)                       -- same ticker can exist on diff exchanges
);

-- -----------------------------------------------------------------------------
-- holdings  — user account <-> security (the join). NOT duplicated per user.
-- -----------------------------------------------------------------------------
CREATE TABLE holdings (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id   UUID NOT NULL REFERENCES accounts(id)   ON DELETE CASCADE,
    security_id  UUID NOT NULL REFERENCES securities(id) ON DELETE RESTRICT,
    quantity     NUMERIC(18,6) NOT NULL CHECK (quantity >= 0),
    avg_cost     NUMERIC(18,6) NOT NULL CHECK (avg_cost >= 0),  -- per-unit cost in security currency
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (account_id, security_id)               -- one holding row per security per account
);
CREATE INDEX idx_holdings_account  ON holdings(account_id);
CREATE INDEX idx_holdings_security ON holdings(security_id);

-- -----------------------------------------------------------------------------
-- price_history  — daily closes per instrument; feeds the covariance engine
-- -----------------------------------------------------------------------------
CREATE TABLE price_history (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    security_id  UUID NOT NULL REFERENCES securities(id) ON DELETE CASCADE,
    price_date   DATE NOT NULL,
    close_price  NUMERIC(18,6) NOT NULL CHECK (close_price >= 0),
    UNIQUE (security_id, price_date)               -- no dup days per instrument
);
-- The composite index your returns/covariance queries need: pull a date range
-- of closes for a set of securities, ordered by date.
CREATE INDEX idx_price_security_date ON price_history(security_id, price_date);

-- -----------------------------------------------------------------------------
-- income  — feeds savings rate + Monte Carlo savings input
-- -----------------------------------------------------------------------------
CREATE TABLE income (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_type   income_source NOT NULL DEFAULT 'SALARY',
    amount        NUMERIC(18,2) NOT NULL CHECK (amount >= 0),
    currency      CHAR(3) NOT NULL DEFAULT 'SGD',
    received_on   DATE NOT NULL,
    note          TEXT
);
CREATE INDEX idx_income_user_date ON income(user_id, received_on);

-- -----------------------------------------------------------------------------
-- expenses  — feeds savings rate, runway, spending breakdown (+ future ML)
-- -----------------------------------------------------------------------------
CREATE TABLE expenses (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category      TEXT NOT NULL,                    -- kept TEXT not enum: categories are user-extensible
    amount        NUMERIC(18,2) NOT NULL CHECK (amount >= 0),
    currency      CHAR(3) NOT NULL DEFAULT 'SGD',
    spent_on      DATE NOT NULL,
    note          TEXT
);
CREATE INDEX idx_expenses_user_date     ON expenses(user_id, spent_on);
CREATE INDEX idx_expenses_user_category ON expenses(user_id, category);

-- -----------------------------------------------------------------------------
-- goals  — Monte Carlo targets
-- -----------------------------------------------------------------------------
CREATE TABLE goals (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    target_amount  NUMERIC(18,2) NOT NULL CHECK (target_amount > 0),
    currency       CHAR(3) NOT NULL DEFAULT 'SGD',
    target_date    DATE NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_goals_user ON goals(user_id);

-- -----------------------------------------------------------------------------
-- risk_profile  — CRRA gamma from the questionnaire (1:1 with user)
-- Separate from users: reassessed over time, conceptually distinct from auth.
-- -----------------------------------------------------------------------------
CREATE TABLE risk_profile (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    crra_gamma   NUMERIC(6,3) NOT NULL CHECK (crra_gamma > 0),  -- relative risk aversion coefficient
    assessed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- updated_at trigger for users (extend to other tables as needed)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
