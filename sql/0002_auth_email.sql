-- Migration 0002: email-only identity + verification codes.
-- Safe to run on an existing database (idempotent). Apply as provisioner.

-- 1. Email becomes the global login identity (one account per email).
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS email_verified boolean NOT NULL DEFAULT false;

CREATE UNIQUE INDEX IF NOT EXISTS users_email_global_uniq ON users (lower(email));

-- 2. Verification / reset codes. Pre-auth (no tenant context), so NOT under RLS;
--    accessed only through the provisioner role from the auth router.
CREATE TABLE IF NOT EXISTS verification_codes (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email       text        NOT NULL,
  purpose     text        NOT NULL,          -- 'email_verify' | 'password_reset'
  code_hash   text        NOT NULL,          -- sha256 of the 6-digit code
  expires_at  timestamptz NOT NULL,
  consumed_at timestamptz,
  attempts    int         NOT NULL DEFAULT 0,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS verification_codes_lookup
  ON verification_codes (lower(email), purpose, created_at DESC);

-- app_user never needs these; keep them on the provisioner side only.
REVOKE ALL ON verification_codes FROM app_user;
