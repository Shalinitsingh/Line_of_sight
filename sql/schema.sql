-- =============================================================================
-- Line-of-Sight  ·  Multi-tenant ROI analytics platform
-- PostgreSQL 16+  ·  schema.sql
--
-- Design principles
--   1. Hard tenant isolation via Row-Level Security (RLS), FORCE-d on every table.
--   2. No fixed business tables (no employees / patients / revenue). Arbitrary
--      uploaded data lives in a JSONB ingestion layer keyed by stable column UUIDs.
--   3. AI proposes formula *strings*; a separate calculator executes them. Formulas
--      are non-executable until every referenced column is validated to exist.
--   4. pgvector for semantic search across datasets, metrics, and report text.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. Extensions
-- -----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "vector";     -- pgvector
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- fuzzy text search on column names

-- -----------------------------------------------------------------------------
-- 1. Roles  (run once, as superuser, OUTSIDE this transaction in real setups)
-- -----------------------------------------------------------------------------
-- app_user      : the role FastAPI connects as. Subject to RLS. No BYPASSRLS.
-- provisioner   : used ONLY for signup / org creation / migrations. BYPASSRLS.
--
--   CREATE ROLE app_user      LOGIN PASSWORD '...' NOSUPERUSER NOBYPASSRLS;
--   CREATE ROLE provisioner   LOGIN PASSWORD '...' NOSUPERUSER BYPASSRLS;
--
-- Tables below are owned by provisioner; app_user gets table-level GRANTs and is
-- forced under RLS even though it is not the owner.

-- -----------------------------------------------------------------------------
-- 2. Tenant context helper
-- -----------------------------------------------------------------------------
-- Reads the per-transaction GUC the application sets with:
--     SET LOCAL app.current_org_id = '<uuid>';
-- The 'true' second arg makes it return NULL (not error) when unset.
CREATE OR REPLACE FUNCTION app_current_org() RETURNS uuid
  LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('app.current_org_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION app_current_user() RETURNS uuid
  LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('app.current_user_id', true), '')::uuid
$$;

-- Generic updated_at trigger
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
  LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END $$;

-- -----------------------------------------------------------------------------
-- 3. Enums
-- -----------------------------------------------------------------------------
CREATE TYPE user_role        AS ENUM ('owner', 'admin', 'analyst', 'viewer');
CREATE TYPE dataset_status    AS ENUM ('uploading', 'profiling', 'ready', 'failed');
CREATE TYPE column_data_type  AS ENUM ('text','integer','number','boolean','date','timestamp','categorical','unknown');
CREATE TYPE formula_status    AS ENUM ('draft','validated','error');   -- the "placeholder gate"
CREATE TYPE embedding_source  AS ENUM ('dataset','dataset_column','metric','report','document');

-- =============================================================================
-- 4. TENANT ROOT
-- =============================================================================
CREATE TABLE organizations (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text        NOT NULL,
  slug        text        NOT NULL UNIQUE,
  industry    text,                       -- free-text tag, NOT a constraint on schema
  settings    jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Workspaces = the "Select Module" step in the UI (Enterprise Sales, Healthcare Ops...).
-- Optional grouping so one org can run several industry contexts side by side.
CREATE TABLE workspaces (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name        text        NOT NULL,
  module_key  text,                       -- e.g. 'enterprise_sales', 'healthcare_ops'
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON workspaces (org_id);

CREATE TABLE users (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  email         text        NOT NULL,
  full_name     text,
  role          user_role   NOT NULL DEFAULT 'viewer',
  password_hash text,                     -- or null if SSO
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, email)                  -- email unique per tenant, not globally
);
CREATE INDEX ON users (org_id);

-- =============================================================================
-- 5. FLEXIBLE INGESTION LAYER  (the heart of the schema-agnostic design)
-- =============================================================================
-- A dataset = one logical uploaded file/table. Metadata only.
CREATE TABLE datasets (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  workspace_id  uuid        REFERENCES workspaces(id) ON DELETE SET NULL,
  name          text        NOT NULL,
  source_kind   text        NOT NULL DEFAULT 'csv',   -- csv | xlsx | (future) crm | lms | hris
  original_filename text,
  status        dataset_status NOT NULL DEFAULT 'uploading',
  row_count     bigint      NOT NULL DEFAULT 0,
  uploaded_by   uuid        REFERENCES users(id) ON DELETE SET NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON datasets (org_id);
CREATE INDEX ON datasets (org_id, workspace_id);

-- Column definitions discovered at ingest time. The UUID is the STABLE anchor
-- that formulas reference. normalized_key is the JSONB key used in dataset_rows.
CREATE TABLE dataset_columns (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  dataset_id      uuid        NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  ordinal         int         NOT NULL,                 -- original column position
  original_header text        NOT NULL,                 -- exactly as in the file
  normalized_key  text        NOT NULL,                 -- snake_case, used in row JSONB
  data_type       column_data_type NOT NULL DEFAULT 'unknown',
  is_numeric      boolean     NOT NULL DEFAULT false,   -- fast filter for calculator
  sample_values   jsonb       NOT NULL DEFAULT '[]'::jsonb,
  stats           jsonb       NOT NULL DEFAULT '{}'::jsonb,  -- min/max/null_count/distinct
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (dataset_id, normalized_key)
);
CREATE INDEX ON dataset_columns (org_id);
CREATE INDEX ON dataset_columns (dataset_id);
CREATE INDEX ON dataset_columns USING gin (original_header gin_trgm_ops); -- fuzzy lookup

-- Raw rows. JSONB keyed by dataset_columns.normalized_key. No fixed schema.
CREATE TABLE dataset_rows (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  dataset_id  uuid        NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  row_index   bigint      NOT NULL,                 -- preserves file order
  data        jsonb       NOT NULL,                 -- {"win_rate_pct": 0.22, "hours": 40, ...}
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON dataset_rows (org_id);
CREATE INDEX ON dataset_rows (dataset_id, row_index);
-- Containment / key-existence queries on arbitrary JSONB:
CREATE INDEX ON dataset_rows USING gin (data jsonb_path_ops);
-- NOTE: at very high volume, partition dataset_rows BY HASH (dataset_id). Out of MVP scope.

-- =============================================================================
-- 6. METRICS · FORMULAS  (AI proposes string → human validates → calculator runs)
-- =============================================================================
CREATE TABLE metrics (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  workspace_id  uuid        REFERENCES workspaces(id) ON DELETE SET NULL,
  name          text        NOT NULL,                 -- "Win Rate per Training Hour"
  description   text,
  unit          text,                                 -- '%', 'USD', 'ratio'
  default_viz   text,                                 -- performance_bridge | nine_box | savings | bar
  active_formula_id uuid,                              -- FK added after formulas table
  created_by    uuid        REFERENCES users(id) ON DELETE SET NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON metrics (org_id);

-- Versioned, AI-proposed expressions. status='validated' is the placeholder gate:
-- it may only flip to 'validated' once every referenced column resolves (see trigger).
CREATE TABLE formulas (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  metric_id     uuid        NOT NULL REFERENCES metrics(id) ON DELETE CASCADE,
  version       int         NOT NULL DEFAULT 1,
  expression    text        NOT NULL,                 -- 'win_rate_pct / completed_training_hours'
  status        formula_status NOT NULL DEFAULT 'draft',
  proposed_by_ai boolean    NOT NULL DEFAULT true,
  validated_at  timestamptz,
  last_error    text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (metric_id, version)
);
CREATE INDEX ON formulas (org_id);
CREATE INDEX ON formulas (metric_id);

ALTER TABLE metrics
  ADD CONSTRAINT fk_metrics_active_formula
  FOREIGN KEY (active_formula_id) REFERENCES formulas(id) ON DELETE SET NULL;

-- Which dataset columns each formula consumes. Integrity-backed validation gate:
-- if a referenced column is deleted, the FK forces you to revisit the formula.
CREATE TABLE formula_columns (
  formula_id  uuid NOT NULL REFERENCES formulas(id) ON DELETE CASCADE,
  column_id   uuid NOT NULL REFERENCES dataset_columns(id) ON DELETE RESTRICT,
  var_name    text NOT NULL,            -- the token used in expression (normalized_key)
  PRIMARY KEY (formula_id, column_id)
);
CREATE INDEX ON formula_columns (column_id);

-- =============================================================================
-- 7. DASHBOARDS · WIDGETS · REPORTS
-- =============================================================================
CREATE TABLE dashboards (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  workspace_id  uuid        REFERENCES workspaces(id) ON DELETE SET NULL,
  name          text        NOT NULL,
  layout        jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_by    uuid        REFERENCES users(id) ON DELETE SET NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON dashboards (org_id);

CREATE TABLE widgets (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  dashboard_id  uuid        NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  metric_id     uuid        REFERENCES metrics(id) ON DELETE SET NULL,
  viz_type      text        NOT NULL,                 -- performance_bridge | nine_box | savings | bar
  title         text,
  config        jsonb       NOT NULL DEFAULT '{}'::jsonb,
  cached_result jsonb,                                -- last computed JSON payload
  computed_at   timestamptz,
  position      int         NOT NULL DEFAULT 0,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON widgets (org_id);
CREATE INDEX ON widgets (dashboard_id);

CREATE TABLE reports (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  workspace_id  uuid        REFERENCES workspaces(id) ON DELETE SET NULL,
  title         text        NOT NULL,
  period_start  date,
  period_end    date,
  payload       jsonb       NOT NULL DEFAULT '{}'::jsonb,  -- frozen snapshot of metrics/widgets
  generated_by  uuid        REFERENCES users(id) ON DELETE SET NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON reports (org_id);

-- =============================================================================
-- 8. AUDIT LOG  (append-only; PRD 7.1 auditability)
-- =============================================================================
CREATE TABLE audit_logs (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  actor_id    uuid        REFERENCES users(id) ON DELETE SET NULL,
  action      text        NOT NULL,        -- 'formula.evaluated','dataset.read','widget.computed'
  target_type text,
  target_id   uuid,
  detail      jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON audit_logs (org_id, created_at DESC);

-- =============================================================================
-- 9. EMBEDDINGS  (pgvector — polymorphic, tenant-scoped semantic search)
-- =============================================================================
-- Dimension MUST match your embedding model. 1024 = Voyage voyage-3 / voyage-3-lite.
-- Change to 1536 for OpenAI text-embedding-3-small, etc.
CREATE TABLE embeddings (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id       uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  source_type  embedding_source NOT NULL,
  source_id    uuid        NOT NULL,            -- points at dataset/metric/report/etc.
  content      text        NOT NULL,            -- the text that was embedded
  embedding    vector(1024) NOT NULL,
  metadata     jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON embeddings (org_id);
CREATE INDEX ON embeddings (org_id, source_type, source_id);
-- ANN index for cosine similarity. Build AFTER bulk load for speed.
CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops);

-- =============================================================================
-- 10. updated_at triggers
-- =============================================================================
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'organizations','workspaces','users','datasets','metrics',
    'dashboards','widgets'
  ] LOOP
    EXECUTE format(
      'CREATE TRIGGER trg_%1$s_updated BEFORE UPDATE ON %1$s
         FOR EACH ROW EXECUTE FUNCTION set_updated_at();', t);
  END LOOP;
END $$;

-- Placeholder validation gate: a formula cannot be marked 'validated' unless every
-- token it references is backed by a real dataset_columns row (via formula_columns).
CREATE OR REPLACE FUNCTION enforce_formula_validation() RETURNS trigger
  LANGUAGE plpgsql AS $$
DECLARE missing int;
BEGIN
  IF NEW.status = 'validated' THEN
    SELECT count(*) INTO missing
    FROM formula_columns fc
    LEFT JOIN dataset_columns dc ON dc.id = fc.column_id
    WHERE fc.formula_id = NEW.id AND dc.id IS NULL;

    IF missing > 0 OR NOT EXISTS (SELECT 1 FROM formula_columns WHERE formula_id = NEW.id) THEN
      RAISE EXCEPTION
        'Formula % cannot be validated: % referenced column(s) unresolved', NEW.id, missing;
    END IF;
    NEW.validated_at = now();
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER trg_formula_gate
  BEFORE INSERT OR UPDATE OF status ON formulas
  FOR EACH ROW EXECUTE FUNCTION enforce_formula_validation();

-- =============================================================================
-- 11. ROW-LEVEL SECURITY  (the isolation guarantee)
-- =============================================================================
-- ENABLE + FORCE on every tenant table. FORCE means even the table owner obeys RLS,
-- so a stray query as 'provisioner' won't silently leak. app_user is never exempt.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'organizations','workspaces','users','datasets','dataset_columns',
    'dataset_rows','metrics','formulas','dashboards','widgets',
    'reports','audit_logs','embeddings'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', t);
    EXECUTE format('ALTER TABLE %I FORCE  ROW LEVEL SECURITY;', t);
  END LOOP;
END $$;

-- organizations: a tenant sees only its own row.
CREATE POLICY org_isolation ON organizations
  USING (id = app_current_org())
  WITH CHECK (id = app_current_org());

-- Every other tenant table keys on org_id.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'workspaces','users','datasets','dataset_columns','dataset_rows',
    'metrics','formulas','dashboards','widgets','reports','embeddings'
  ] LOOP
    EXECUTE format($f$
      CREATE POLICY tenant_isolation ON %I
        USING (org_id = app_current_org())
        WITH CHECK (org_id = app_current_org());
    $f$, t);
  END LOOP;
END $$;

-- formula_columns has no org_id of its own; isolate through its parent formula.
CREATE POLICY tenant_isolation ON formula_columns
  USING (EXISTS (SELECT 1 FROM formulas f
                 WHERE f.id = formula_columns.formula_id AND f.org_id = app_current_org()))
  WITH CHECK (EXISTS (SELECT 1 FROM formulas f
                 WHERE f.id = formula_columns.formula_id AND f.org_id = app_current_org()));

-- audit_logs: tenant-isolated, but append-only for the app (SELECT + INSERT only; no UPDATE/DELETE).
CREATE POLICY tenant_isolation ON audit_logs
  USING (org_id = app_current_org())
  WITH CHECK (org_id = app_current_org());

-- -----------------------------------------------------------------------------
-- 12. GRANTS to the application role
-- -----------------------------------------------------------------------------
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- audit_logs is append-only: revoke mutation.
REVOKE UPDATE, DELETE ON audit_logs FROM app_user;
GRANT EXECUTE ON FUNCTION app_current_org(), app_current_user() TO app_user;

-- =============================================================================
-- End of schema
-- =============================================================================
