-- Runs as superuser on first container start (before init_db.py applies schema).
CREATE ROLE provisioner LOGIN PASSWORD 'provpass' NOSUPERUSER BYPASSRLS;
CREATE ROLE app_user    LOGIN PASSWORD 'apppass'  NOSUPERUSER NOBYPASSRLS;
GRANT ALL ON DATABASE lineofsight TO provisioner;
\c lineofsight
ALTER SCHEMA public OWNER TO provisioner;
GRANT ALL ON SCHEMA public TO provisioner;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
