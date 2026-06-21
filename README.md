# Line-of-Sight — Multi-tenant AI ROI Analytics (Backend)

A schema-agnostic, multi-tenant SaaS backend that ingests arbitrary CSV/Excel files,
lets an AI propose ROI formulas, validates them through a human gate, and computes
KPIs — with **database-enforced** tenant isolation. FastAPI + PostgreSQL (RLS) +
pgvector.

This is the backend MVP. It is fully runnable and tested end-to-end. A web frontend is
a separate effort (see *Next steps*).

## Why this design

| Requirement | How it's met |
|---|---|
| Company A must never see Company B's data | Row-Level Security `FORCE`-d on every table; app connects as a `NOBYPASSRLS` role; tenant pinned per-transaction with `SET LOCAL`. Unset context → **zero rows** (fail closed). |
| Support any industry | No business tables. Uploads land in `datasets` / `dataset_columns` / `dataset_rows` (JSONB). A hospital file and a retail file use the identical path. |
| Unknown schema per customer | Columns are profiled at ingest (type inference); rows stored as JSONB keyed by normalized column names; formulas reference **stable column UUIDs**, not names. |
| AI formulas without hallucinated math | The LLM only proposes a *string* + column mapping. A separate sandboxed evaluator (`asteval`, no `eval()`) does the arithmetic. A DB trigger blocks "validated" status unless every referenced column exists. |
| Semantic search | `pgvector` (HNSW, cosine), tenant-scoped by RLS. |
| Future CRM/LMS/HRIS integrations | `datasets.source_kind` + the JSONB layer; add connectors that write rows, no schema change. |

## Architecture at a glance

```
Client ──JWT──▶ FastAPI
                  │  resolve org from verified token
                  ▼
            tenant_session: SET LOCAL app.current_org_id   ← RLS context
                  │
   ┌──────────────┼───────────────────────────────┐
   ▼              ▼               ▼                 ▼
 datasets     metrics/        dashboards/        embeddings
 (JSONB    →  formulas    →   widgets/reports    (pgvector)
 ingest)      AI propose →
              validate gate →
              calculator (asteval)
                  │
                  ▼
              audit_logs (append-only)
```

Two DB roles: `app_user` (all request traffic, under RLS) and `provisioner`
(`BYPASSRLS`, used **only** for signup and migrations — no tenant context exists yet
when an org is first created).

## Run it

### Docker (recommended)
```bash
cp .env.example .env
docker compose up --build
# API at http://localhost:8000/docs
```

### Local
```bash
pip install -r requirements.txt
# Postgres 16 + pgvector running; create roles + extensions (see sql/bootstrap.sql)
python scripts/init_db.py          # applies sql/schema.sql
uvicorn app.main:app --reload
python scripts/e2e_demo.py         # full two-tenant walkthrough
pytest -q                          # isolation regression test
```

## The core API flow

```
POST /auth/signup                      → { token }                 (provisioner path)
POST /datasets (multipart file)        → ingest CSV/XLSX to JSONB
POST /metrics                          → create a named KPI
POST /metrics/{id}/propose {goal,ds}   → AI drafts a formula (placeholder)
POST /formulas/{id}/validate           → gate: only passes if columns resolve
POST /formulas/{id}/execute            → calculator pulls arrays, evaluates, audits
POST /dashboards · /widgets · /reports → assemble + snapshot
POST /search/index · /search/query     → tenant-scoped semantic search
GET  /audit                            → append-only trail
```

## What's deliberately a stub (wire to your providers)
- `app/ai_assistant.py` — uses Anthropic if `ANTHROPIC_API_KEY` set, else a deterministic
  heuristic so the system runs offline.
- `app/routers/search.py::embed()` — replace the hash stub with Voyage (`voyage-3`,
  1024-dim) or your embedding API. Match `EMBEDDING_DIM`.

## Code style

PEP 8, enforced with Black (88-col), isort, and flake8. Config lives in
`pyproject.toml` and `setup.cfg`.

```bash
make format   # auto-fix
make lint     # check (use in CI)
```

## Next steps (not in this MVP)
- Frontend (the Figma flow: login → workspace module → ingestion → dashboard → AI tracker).
- Production hardening: rate limiting, refresh tokens, COPY-based bulk ingest,
  `dataset_rows` partitioning at high volume, background jobs for large files.
- Real connectors (Cornerstone/Docebo CSV export, HRIS, CRM).
```
```

## Layout
```
app/        config, db (RLS sessions), security, models, ingestion,
            evaluator, ai_assistant, deps, routers/
sql/        schema.sql (DDL + RLS + triggers), bootstrap.sql (roles+extensions)
scripts/    init_db.py, e2e_demo.py
tests/      test_isolation.py
```
