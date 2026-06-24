"""
Idempotent database initialisation, run on every backend start.

- If the base schema is missing (fresh database), apply sql/schema.sql.
- If it already exists (persisted volume), skip it (schema.sql is not re-runnable).
- Always apply the idempotent migrations so an older database is brought up to date
  without losing data.

Connection comes from PROVISIONER_DATABASE_URL so this works in Docker (host 'db')
and locally (host 127.0.0.1).
"""

import asyncio
import os
import pathlib

import asyncpg

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "sql" / "schema.sql"
MIGRATIONS = [ROOT / "sql" / "0002_auth_email.sql"]
PROV_URL = os.environ.get(
    "PROVISIONER_DATABASE_URL",
    "postgresql+asyncpg://provisioner:provpass@127.0.0.1:5432/lineofsight",
).replace("+asyncpg", "")  # asyncpg wants a plain postgresql:// DSN


async def main():
    conn = await asyncpg.connect(PROV_URL)
    try:
        exists = await conn.fetchval(
            "SELECT to_regclass('public.organizations') IS NOT NULL"
        )
        if not exists:
            await conn.execute(SCHEMA.read_text())
            print("base schema applied")
        else:
            print("base schema already present; skipping")

        for m in MIGRATIONS:
            await conn.execute(m.read_text())
            print(f"migration applied: {m.name}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
